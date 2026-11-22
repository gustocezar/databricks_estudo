# Databricks notebook source
# MAGIC %md
# MAGIC # pos_venda · 01 · One Table — pagamentos pendentes (seguro de vida)
# MAGIC
# MAGIC Gera **dados 100% sintéticos** de uma seguradora de vida fictícia com `dbldatagen`.
# MAGIC
# MAGIC - **Grão:** 1 linha = 1 parcela (ou endosso) de apólice de vida **pendente de pagamento**
# MAGIC - **Volume:** 500.000 linhas (parâmetro `n_registros`)
# MAGIC - **Janela:** vencimentos dos últimos 6 meses até `data_extracao` (parâmetro `meses`)
# MAGIC - **Destino:** `pos_venda.landing.pagamentos_pendentes_one_table` (Delta, Unity Catalog)
# MAGIC - **Conteúdo:** cliente (CPF, RG, celular, telefone fixo, endereço completo, profissão), apólice, produto, coberturas,
# MAGIC   periodicidade, corretor, ponto de venda, endossos, datas e cobrança
# MAGIC
# MAGIC Com `injetar_defeitos = true`, entram defeitos de qualidade **de propósito** (duplicatas exatas, CPF inválido,
# MAGIC e-mail/telefone nulos, UF em minúsculas, CPF com e sem máscara) para a camada Silver tratar depois.
# MAGIC
# MAGIC Todos os nomes, CPFs, CNPJs, e-mails e telefones são fictícios. CPF/CNPJ têm dígito verificador válido
# MAGIC (exceto os defeitos injetados), então **podem coincidir por acaso com documentos reais**: não use fora de testes.

# COMMAND ----------

# MAGIC %pip install dbldatagen

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import json
import math
import datetime as dt

from pyspark.sql import functions as F, Window
import dbldatagen as dg

dbutils.widgets.text("catalogo", "pos_venda")
dbutils.widgets.text("schema", "landing")
dbutils.widgets.text("tabela", "pagamentos_pendentes_one_table")
dbutils.widgets.text("n_registros", "500000")
dbutils.widgets.text("meses", "6")
dbutils.widgets.text("data_extracao", "2026-11-18")
dbutils.widgets.text("seed", "20261118")
dbutils.widgets.text("n_apolices", "290000")
dbutils.widgets.text("injetar_defeitos", "true")

CATALOGO = dbutils.widgets.get("catalogo")
SCHEMA = dbutils.widgets.get("schema")
TABELA = dbutils.widgets.get("tabela")
N_REGISTROS = int(dbutils.widgets.get("n_registros"))
MESES = int(dbutils.widgets.get("meses"))
DATA_EXTRACAO = dbutils.widgets.get("data_extracao")
SEED = int(dbutils.widgets.get("seed"))
N_APOL = int(dbutils.widgets.get("n_apolices"))
DEFEITOS = dbutils.widgets.get("injetar_defeitos").strip().lower() == "true"

N_CLIENTES = int(N_APOL / 1.55)
N_CORRETORES = 2500
N_DUP = int(round(N_REGISTROS * 0.005)) if DEFEITOS else 0
N_UNICOS = N_REGISTROS - N_DUP

D = f"DATE'{DATA_EXTRACAO}'"                      # literal SQL da data de extração
JANELA_INI = f"add_months({D}, -{MESES})"          # início da janela (exclusivo)
FQ_TABELA = f"{CATALOGO}.{SCHEMA}.{TABELA}"
FQ_STG = f"{CATALOGO}.{SCHEMA}._stg_apolices"

spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOGO} COMMENT 'Dominio pos_venda (seguro de vida) - dados sinteticos'")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOGO}.{SCHEMA} COMMENT 'Zona de pouso: extracao one-table do core de vida'")
print("alvo:", FQ_TABELA, "| apolices:", N_APOL, "| clientes:", N_CLIENTES, "| corretores:", N_CORRETORES)


def U(salt, *cols):
    """Uniforme [0,1) determinística por linha: não muda se o plano for reavaliado."""
    args = ", ".join(cols)
    return F.expr(f"pmod(xxhash64({args}, {SEED + salt}), 1000000) / 1000000.0")


# COMMAND ----------

# MAGIC %md
# MAGIC ## Catálogos de referência (fictícios)

# COMMAND ----------

NOMES_F = ["Maria","Ana","Juliana","Fernanda","Patrícia","Camila","Aline","Luciana","Mariana","Beatriz",
           "Carolina","Renata","Larissa","Vanessa","Tatiane","Priscila","Adriana","Bruna","Letícia","Gabriela",
           "Amanda","Sandra","Daniela","Cláudia","Débora","Simone","Eliane","Rafaela","Natália","Viviane",
           "Isabela","Raquel","Cristiane","Michele","Paula","Sônia","Rosana","Elaine","Silvia","Helena"]
NOMES_M = ["José","João","Antônio","Carlos","Paulo","Pedro","Lucas","Marcos","Luiz","Gabriel",
           "Rafael","Daniel","Marcelo","Bruno","Eduardo","Felipe","Rodrigo","Fernando","Gustavo","André",
           "Ricardo","Fábio","Leonardo","Thiago","Sérgio","Alexandre","Roberto","Márcio","Vinícius","Diego",
           "Leandro","Renato","Henrique","Caio","Anderson","Wellington","Edson","Cláudio","Jorge","Mateus"]
SOBRENOMES = ["Silva","Santos","Oliveira","Souza","Rodrigues","Ferreira","Alves","Pereira","Lima","Gomes",
              "Costa","Ribeiro","Martins","Carvalho","Almeida","Lopes","Soares","Fernandes","Vieira","Barbosa",
              "Rocha","Dias","Nascimento","Andrade","Moreira","Nunes","Marques","Machado","Mendes","Freitas",
              "Cardoso","Ramos","Gonçalves","Santana","Teixeira","Araújo","Pinto","Correia","Monteiro","Moraes",
              "Cavalcanti","Campos","Batista","Miranda","Barros","Duarte","Azevedo","Castro","Melo","Fonseca"]
PROFISSOES = ["Analista","Professor","Engenheiro","Médico","Enfermeiro","Advogado","Contador","Vendedor","Motorista",
              "Empresário","Autônomo","Servidor Público","Desenvolvedor","Gerente","Administrador","Arquiteto",
              "Técnico","Designer","Dentista","Policial","Bancário","Comerciante","Aposentado","Consultor","Farmacêutico"]
EMAIL_DOMS = ["gmail.com","hotmail.com","outlook.com","yahoo.com.br","uol.com.br","icloud.com"]
RAZAO_PREF = ["Alfa","Horizonte","Prime","Vértice","Atlântica","Nova Era","Aliança","Mantiqueira","Planalto",
              "Sul Brasil","Centro","Litoral","Estrela","Pioneira","Confiança","Metropolitana"]
RAZAO_SUF = ["Corretora de Seguros Ltda","Seguros e Consultoria","Assessoria em Seguros","Corretagem de Seguros S/S"]

# (cidade, uf, ddd, 1o dígito do CEP, peso)
CIDADES = [
    ("São Paulo","SP","11",0,120),("Campinas","SP","19",1,25),("Santos","SP","13",1,15),("Ribeirão Preto","SP","16",1,15),
    ("Sorocaba","SP","15",1,15),("São José dos Campos","SP","12",1,15),("Rio de Janeiro","RJ","21",2,70),("Niterói","RJ","21",2,15),
    ("Vitória","ES","27",2,15),("Belo Horizonte","MG","31",3,40),("Uberlândia","MG","34",3,15),("Salvador","BA","71",4,30),
    ("Aracaju","SE","79",4,8),("Recife","PE","81",5,25),("Maceió","AL","82",5,10),("João Pessoa","PB","83",5,10),
    ("Natal","RN","84",5,10),("Fortaleza","CE","85",6,30),("Teresina","PI","86",6,10),("São Luís","MA","98",6,10),
    ("Belém","PA","91",6,15),("Manaus","AM","92",6,15),("Brasília","DF","61",7,35),("Goiânia","GO","62",7,20),
    ("Cuiabá","MT","65",7,10),("Campo Grande","MS","67",7,10),("Porto Velho","RO","69",7,5),("Curitiba","PR","41",8,30),
    ("Londrina","PR","43",8,15),("Florianópolis","SC","48",8,15),("Joinville","SC","47",8,15),("Porto Alegre","RS","51",9,30),
    ("Caxias do Sul","RS","54",9,10),
]
# (idx, codigo, nome, categoria, fator_taxa, cobertura_cod, cobertura_nome, peso)
PRODUTOS = [
    (0,"VID-ESS","Vida Essencial","TEMPORARIO",0.85,"MORTE","Morte (natural ou acidental)",28),
    (1,"VID-COM","Vida Completo","TEMPORARIO",1.05,"MORTE","Morte (natural ou acidental)",22),
    (2,"VID-INT","Vida Inteira","VITALICIO",2.10,"MORTE","Morte (natural ou acidental)",10),
    (3,"VID-FAM","Vida Familia","FAMILIAR",1.30,"MORTE","Morte (natural ou acidental)",14),
    (4,"VID-REN","Vida Renda Protegida","RENDA",1.15,"DIT","Diaria por Incapacidade Temporaria",6),
    (5,"VID-DGR","Vida Doencas Graves","DOENCAS_GRAVES",1.60,"DGR","Doencas Graves",8),
    (6,"VID-PRE","Vida Premium","PREMIUM",1.45,"MORTE","Morte (natural ou acidental)",7),
    (7,"VID-RES","Vida Resgatavel","RESGATAVEL",1.90,"MORTE","Morte (natural ou acidental)",5),
]
TIPOS_ENDOSSO = ["ALTERACAO_CAPITAL","INCLUSAO_COBERTURA","EXCLUSAO_COBERTURA","ALTERACAO_BENEFICIARIO",
                 "ALTERACAO_PERIODICIDADE","ALTERACAO_DADOS_CADASTRAIS","REAJUSTE_ANUAL"]

cidades_df = spark.createDataFrame(
    [(i, c[0], c[1], c[2], c[3]) for i, c in enumerate(CIDADES)],
    "cidade_idx int, cidade string, uf string, ddd string, cep_dig int")
produtos_df = spark.createDataFrame(
    [(p[0], p[1], p[2], p[3], float(p[4]), p[5], p[6]) for p in PRODUTOS],
    "produto_idx int, produto_codigo string, produto_nome string, categoria_produto string, "
    "fator_taxa double, cobertura_principal_codigo string, cobertura_principal_nome string")

LOGRADOURO_TIPOS = ["Rua", "Rua", "Rua", "Avenida", "Avenida", "Alameda", "Travessa", "Praça", "Estrada"]
LOGRADOURO_NOMES = ["das Flores", "Sete de Setembro", "Marechal Deodoro", "XV de Novembro", "Presidente Vargas",
                    "Santos Dumont", "Tiradentes", "do Comércio", "São João", "das Palmeiras", "Getúlio Vargas",
                    "Dom Pedro II", "da Liberdade", "Barão do Rio Branco", "José Bonifácio", "Rui Barbosa",
                    "das Acácias", "da Independência", "Castro Alves", "Duque de Caxias", "da Paz", "Santa Catarina",
                    "Brasil", "das Laranjeiras", "Quinze de Novembro", "Voluntários da Pátria", "Floriano Peixoto",
                    "Bandeirantes", "Ipiranga", "Paulista"]
BAIRROS = ["Centro", "Jardim América", "Vila Nova", "Bela Vista", "Santa Maria", "São José", "Jardim Primavera",
           "Parque Industrial", "Vila Rosa", "Boa Vista", "Jardim Europa", "Santo Antônio", "Nossa Senhora de Fátima",
           "Cidade Nova", "Vila Esperança", "Jardim Paulista", "Alto da Boa Vista", "Vila Industrial", "Jardim Botânico",
           "Planalto", "Vila São Pedro", "Jardim Celeste", "Parque das Nações", "Vila Operária", "São Francisco",
           "Jardim das Flores", "Santa Luzia", "Vila Mariana Nova", "Bom Retiro", "Lourdes"]
UFS_RG = sorted({c[1] for c in CIDADES})
UF_REGIONAL = {"SP": "SUDESTE", "RJ": "SUDESTE", "MG": "SUDESTE", "ES": "SUDESTE", "PR": "SUL", "SC": "SUL", "RS": "SUL",
               "BA": "NORDESTE", "SE": "NORDESTE", "PE": "NORDESTE", "AL": "NORDESTE", "PB": "NORDESTE", "RN": "NORDESTE",
               "CE": "NORDESTE", "PI": "NORDESTE", "MA": "NORDESTE", "DF": "CENTRO-OESTE", "GO": "CENTRO-OESTE",
               "MT": "CENTRO-OESTE", "MS": "CENTRO-OESTE", "PA": "NORTE", "AM": "NORTE", "RO": "NORTE"}


def ARR(valores):
    return F.array(*[F.lit(v) for v in valores])


# Pontos de venda (dimensão pequena, gerada no driver com semente fixa)
import random
_rnd = random.Random(SEED + 500)
_pesos_cidades = [c[4] for c in CIDADES]
N_PDV_ESC, N_PDV_AG = 700, 450
_pdv = []
for i in range(N_PDV_ESC):                       # escritórios de corretores
    c = _rnd.choices(CIDADES, weights=_pesos_cidades)[0]
    _pdv.append(("CORRETOR", i, f"PDV-ESC-{i + 1:04d}", f"Escritório {_rnd.choice(SOBRENOMES)} Seguros",
                 "ESCRITORIO_CORRETOR", c[0], c[1], UF_REGIONAL[c[1]]))
for i in range(N_PDV_AG):                        # agências bancárias (bancassurance)
    c = _rnd.choices(CIDADES, weights=_pesos_cidades)[0]
    _pdv.append(("BANCASSURANCE", i, f"AG-{1000 + i:04d}", f"Agência {c[0]} {1000 + i}",
                 "AGENCIA_BANCARIA", c[0], c[1], UF_REGIONAL[c[1]]))
for i, (cod, nome) in enumerate([("DIG-SITE", "Site Institucional"), ("DIG-APP", "Aplicativo Mobile"),
                                 ("DIG-MKT", "Marketplace Parceiro")]):
    _pdv.append(("DIGITAL", i, cod, nome, "PLATAFORMA_DIGITAL", "São Paulo", "SP", "SUDESTE"))
for i, (cid, uf) in enumerate([("São Paulo", "SP"), ("Rio de Janeiro", "RJ"), ("Belo Horizonte", "MG"), ("Porto Alegre", "RS")]):
    _pdv.append(("TELEVENDAS", i, f"TLV-{i + 1:02d}", f"Central de Televendas {cid}", "CENTRAL_TELEVENDAS", cid, uf, UF_REGIONAL[uf]))
pdv_df = spark.createDataFrame(_pdv,
    "canal_venda string, pdv_pos int, ponto_venda_codigo string, ponto_venda_nome string, ponto_venda_tipo string, "
    "ponto_venda_cidade string, ponto_venda_uf string, ponto_venda_regional string")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Dígitos verificadores de CPF e CNPJ

# COMMAND ----------

def add_cpf(df, base_col, out_col):
    """CPF de 11 dígitos (só números) a partir de uma base numérica de 9 dígitos."""
    return (df
        .withColumn("_c9", F.lpad(F.col(base_col).cast("string"), 9, "0"))
        .withColumn("_a", F.expr("transform(sequence(1, 9), i -> cast(substring(_c9, i, 1) as int))"))
        .withColumn("_d1", F.expr("(aggregate(zip_with(_a, sequence(10, 2, -1), (x, w) -> x * w), 0, (s, v) -> s + v) * 10 % 11) % 10"))
        .withColumn("_d2", F.expr("(aggregate(zip_with(concat(_a, array(_d1)), sequence(11, 2, -1), (x, w) -> x * w), 0, (s, v) -> s + v) * 10 % 11) % 10"))
        .withColumn(out_col, F.concat(F.col("_c9"), F.col("_d1").cast("string"), F.col("_d2").cast("string")))
        .drop("_c9", "_a", "_d1", "_d2"))


def add_cnpj(df, base_col, out_col):
    """CNPJ de 14 dígitos (só números): base de 8 dígitos + filial 0001 + 2 dígitos verificadores."""
    return (df
        .withColumn("_c12", F.concat(F.lpad(F.col(base_col).cast("string"), 8, "0"), F.lit("0001")))
        .withColumn("_a", F.expr("transform(sequence(1, 12), i -> cast(substring(_c12, i, 1) as int))"))
        .withColumn("_r1", F.expr("aggregate(zip_with(_a, array(5,4,3,2,9,8,7,6,5,4,3,2), (x, w) -> x * w), 0, (s, v) -> s + v) % 11"))
        .withColumn("_d1", F.expr("CASE WHEN _r1 < 2 THEN 0 ELSE 11 - _r1 END"))
        .withColumn("_r2", F.expr("aggregate(zip_with(concat(_a, array(_d1)), array(6,5,4,3,2,9,8,7,6,5,4,3,2), (x, w) -> x * w), 0, (s, v) -> s + v) % 11"))
        .withColumn("_d2", F.expr("CASE WHEN _r2 < 2 THEN 0 ELSE 11 - _r2 END"))
        .withColumn(out_col, F.concat(F.col("_c12"), F.col("_d1").cast("string"), F.col("_d2").cast("string")))
        .drop("_c12", "_a", "_r1", "_d1", "_r2", "_d2"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Corretores (dbldatagen)

# COMMAND ----------

corr_spec = (
    dg.DataGenerator(spark, name="corretores", rows=N_CORRETORES, partitions=4, randomSeed=SEED + 1, randomSeedMethod="hash_fieldname")
    .withIdOutput()
    .withColumn("tipo_pessoa", "string", values=["PJ", "PF"], weights=[6, 4], random=True)
    .withColumn("regional", "string", values=["SUDESTE", "SUL", "NORDESTE", "CENTRO-OESTE", "NORTE"],
                weights=[45, 18, 22, 10, 5], random=True)
    .withColumn("comissao_pct", "integer", values=[5, 8, 10, 12, 15, 20, 25, 30],
                weights=[5, 10, 25, 20, 20, 10, 7, 3], random=True)
    .withColumn("status_corretor", "string", values=["ATIVO", "INATIVO", "SUSPENSO"], weights=[92, 6, 2], random=True)
    .withColumn("dias_credenc", "integer", minValue=60, maxValue=7300, random=True)
    .withColumn("cpf_base", "long", minValue=100000000, maxValue=999999999, random=True)
    .withColumn("cnpj_base", "long", minValue=10000000, maxValue=99999999, random=True)
    .withColumn("susep_base", "long", minValue=100000000, maxValue=999999999, random=True)
    .withColumn("nome_pf_f", "string", values=NOMES_F, random=True)
    .withColumn("nome_pf_m", "string", values=NOMES_M, random=True)
    .withColumn("sob1", "string", values=SOBRENOMES, random=True)
    .withColumn("sob2", "string", values=SOBRENOMES, random=True)
    .withColumn("razao_pref", "string", values=RAZAO_PREF, random=True)
    .withColumn("razao_suf", "string", values=RAZAO_SUF, random=True)
)
corr = add_cnpj(add_cpf(corr_spec.build(), "cpf_base", "cpf_corr"), "cnpj_base", "cnpj_corr")
corretores = (corr
    .withColumn("corretor_idx", F.col("id").cast("int"))
    .withColumn("corretor_id", F.concat(F.lit("COR"), F.lpad((F.col("id") + 1).cast("string"), 6, "0")))
    .withColumn("corretor_nome", F.when(F.col("tipo_pessoa") == "PJ", F.concat_ws(" ", "razao_pref", "razao_suf"))
                .otherwise(F.concat_ws(" ", F.when(F.col("id") % 2 == 0, F.col("nome_pf_f")).otherwise(F.col("nome_pf_m")), "sob1", "sob2")))
    .withColumn("corretor_tipo_pessoa", F.col("tipo_pessoa"))
    .withColumn("corretor_documento", F.when(F.col("tipo_pessoa") == "PJ", F.col("cnpj_corr")).otherwise(F.col("cpf_corr")))
    .withColumn("corretor_registro_susep", F.col("susep_base").cast("string"))
    .withColumn("corretor_regional", F.col("regional"))
    .withColumn("corretor_comissao_pct", (F.col("comissao_pct") / 100.0).cast("decimal(5,2)"))
    .withColumn("corretor_status", F.col("status_corretor"))
    .withColumn("corretor_data_credenciamento", F.expr(f"date_sub({D}, dias_credenc)"))
    .select("corretor_idx", "corretor_id", "corretor_nome", "corretor_tipo_pessoa", "corretor_documento",
            "corretor_registro_susep", "corretor_regional", "corretor_comissao_pct", "corretor_status",
            "corretor_data_credenciamento"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Clientes (dbldatagen)

# COMMAND ----------

pesos_idade = [max(1, int(100 * math.exp(-((a - 42) / 12.0) ** 2 / 2))) for a in range(18, 75)]

cli_spec = (
    dg.DataGenerator(spark, name="clientes", rows=N_CLIENTES, partitions=8, randomSeed=SEED + 2, randomSeedMethod="hash_fieldname")
    .withIdOutput()
    .withColumn("sexo", "string", values=["F", "M"], weights=[52, 48], random=True)
    .withColumn("nome_f", "string", values=NOMES_F, random=True)
    .withColumn("nome_m", "string", values=NOMES_M, random=True)
    .withColumn("sob1", "string", values=SOBRENOMES, random=True)
    .withColumn("sob2", "string", values=SOBRENOMES, random=True)
    .withColumn("cpf_base", "long", minValue=100000000, maxValue=999999999, random=True)
    .withColumn("estado_civil", "string", values=["SOLTEIRO", "CASADO", "UNIAO_ESTAVEL", "DIVORCIADO", "VIUVO"],
                weights=[30, 45, 12, 10, 3], random=True)
    .withColumn("cidade_idx", "integer", values=list(range(len(CIDADES))), weights=[c[4] for c in CIDADES], random=True)
    .withColumn("renda_faixa", "string", values=["ATE_3_SM", "3_A_6_SM", "6_A_10_SM", "10_A_20_SM", "ACIMA_20_SM"],
                weights=[18, 32, 25, 18, 7], random=True)
    .withColumn("profissao", "string", values=PROFISSOES, random=True)
    .withColumn("email_dom", "string", values=EMAIL_DOMS, weights=[45, 20, 15, 8, 7, 5], random=True)
    .withColumn("idade_alvo", "integer", values=list(range(18, 75)), weights=pesos_idade, random=True)
    .withColumn("dias_nasc_extra", "integer", minValue=0, maxValue=364, random=True)
    .withColumn("fumante_int", "integer", values=[0, 1], weights=[88, 12], random=True)
)

cli = add_cpf(cli_spec.build(), "cpf_base", "cpf_ok")
cli = (cli
    .join(F.broadcast(cidades_df), "cidade_idx", "left")
    .withColumn("cliente_ref", F.col("id").cast("int"))
    .withColumn("cliente_id", F.concat(F.lit("CLI"), F.lpad((F.col("id") + 1).cast("string"), 9, "0")))
    .withColumn("cliente_nome", F.when(F.col("sexo") == "F", F.concat_ws(" ", "nome_f", "sob1", "sob2"))
                .otherwise(F.concat_ws(" ", "nome_m", "sob1", "sob2")))
    .withColumn("_prim", F.expr("translate(lower(CASE WHEN sexo = 'F' THEN nome_f ELSE nome_m END), "
                                "'áàâãäéèêëíìîïóòôõöúùûüç', 'aaaaaeeeeiiiiooooouuuuc')"))
    .withColumn("_sob", F.expr("translate(lower(sob1), 'áàâãäéèêëíìîïóòôõöúùûüç', 'aaaaaeeeeiiiiooooouuuuc')"))
    .withColumn("cliente_email", F.concat(F.col("_prim"), F.lit("."), F.col("_sob"),
                                          F.floor(U(101, "id") * 99).cast("string"), F.lit("@"), F.col("email_dom")))
    .withColumn("_tel8", F.lpad(F.floor(U(102, "id") * 100000000).cast("string"), 8, "0"))
    .withColumn("cliente_celular", F.concat(F.lit("("), F.col("ddd"), F.lit(") 9"), F.substring("_tel8", 1, 4),
                                            F.lit("-"), F.substring("_tel8", 5, 4)))
    .withColumn("_fx8", F.concat(F.floor(U(122, "id") * 4 + 2).cast("string"),
                                 F.lpad(F.floor(U(123, "id") * 10000000).cast("string"), 7, "0")))
    .withColumn("cliente_telefone_fixo", F.when(U(124, "id") < 0.45, F.lit(None).cast("string"))
                .otherwise(F.concat(F.lit("("), F.col("ddd"), F.lit(") "), F.substring("_fx8", 1, 4),
                                    F.lit("-"), F.substring("_fx8", 5, 4))))
    .withColumn("_rg8", F.lpad(F.floor(U(126, "id") * 90000000 + 10000000).cast("string"), 8, "0"))
    .withColumn("_rgdv", F.element_at(ARR(list("0123456789X")), (F.floor(U(127, "id") * 11) + 1).cast("int")))
    .withColumn("cliente_rg", F.concat(F.substring("_rg8", 1, 2), F.lit("."), F.substring("_rg8", 3, 3), F.lit("."),
                                       F.substring("_rg8", 6, 3), F.lit("-"), F.col("_rgdv")))
    .withColumn("_u_org", U(129, "id"))
    .withColumn("cliente_rg_orgao_emissor", F.when(F.col("_u_org") < 0.88, F.lit("SSP")).when(F.col("_u_org") < 0.94, F.lit("DETRAN"))
                .when(F.col("_u_org") < 0.97, F.lit("PC")).otherwise(F.lit("IFP")))
    .withColumn("cliente_rg_uf_emissor", F.when(U(130, "id") < 0.85, F.col("uf"))
                .otherwise(F.element_at(ARR(UFS_RG), (F.floor(U(131, "id") * len(UFS_RG)) + 1).cast("int"))))
    .withColumn("cliente_logradouro", F.concat(
        F.element_at(ARR(LOGRADOURO_TIPOS), (F.floor(U(132, "id") * len(LOGRADOURO_TIPOS)) + 1).cast("int")), F.lit(" "),
        F.element_at(ARR(LOGRADOURO_NOMES), (F.floor(U(133, "id") * len(LOGRADOURO_NOMES)) + 1).cast("int"))))
    .withColumn("cliente_numero", F.when(U(134, "id") < 0.03, F.lit("S/N"))
                .otherwise((F.floor(F.pow(U(135, "id"), F.lit(2.0)) * 3000) + 1).cast("int").cast("string")))
    .withColumn("_uc", U(136, "id"))
    .withColumn("cliente_complemento", F.when(F.col("_uc") < 0.45, F.lit(None).cast("string"))
                .when(F.col("_uc") < 0.80, F.concat(F.lit("Apto "), (F.floor(U(137, "id") * 300) + 1).cast("int").cast("string")))
                .when(F.col("_uc") < 0.90, F.concat(F.lit("Casa "), (F.floor(U(137, "id") * 4) + 1).cast("int").cast("string")))
                .when(F.col("_uc") < 0.95, F.concat(F.lit("Bloco "), F.element_at(ARR(list("ABCDE")), (F.floor(U(138, "id") * 5) + 1).cast("int")),
                                                    F.lit(" Apto "), (F.floor(U(137, "id") * 200) + 1).cast("int").cast("string")))
                .otherwise(F.concat(F.lit("Sala "), (F.floor(U(137, "id") * 500) + 1).cast("int").cast("string"))))
    .withColumn("cliente_bairro", F.element_at(ARR(BAIRROS), (F.floor(U(139, "id") * len(BAIRROS)) + 1).cast("int")))
    .withColumn("_cep7", F.lpad(F.floor(U(103, "id") * 10000000).cast("string"), 7, "0"))
    .withColumn("_cep8", F.concat(F.col("cep_dig").cast("string"), F.col("_cep7")))
    .withColumn("cliente_cep", F.concat(F.substring("_cep8", 1, 5), F.lit("-"), F.substring("_cep8", 6, 3)))
    .withColumn("cliente_cidade", F.col("cidade"))
    .withColumn("cliente_uf", F.col("uf"))
    .withColumn("cliente_sexo", F.col("sexo"))
    .withColumn("cliente_estado_civil", F.col("estado_civil"))
    .withColumn("cliente_renda_faixa", F.col("renda_faixa"))
    .withColumn("cliente_profissao", F.col("profissao"))
    .withColumn("cliente_fumante", F.col("fumante_int") == 1)
    .withColumn("_nasc_prelim", F.expr(f"date_sub({D}, idade_alvo * 365 + dias_nasc_extra)"))
    .withColumn("cliente_cpf", F.col("cpf_ok"))
    .withColumn("cliente_endereco_completo", F.concat_ws(" - ",
        F.concat_ws(", ", F.col("cliente_logradouro"), F.col("cliente_numero"), F.col("cliente_complemento")),
        F.col("cliente_bairro"), F.concat(F.col("cidade"), F.lit("/"), F.col("uf")), F.col("cliente_cep"))))

if DEFEITOS:
    cli = (cli
        # CPF inválido (troca o último dígito) em ~1,5% dos clientes
        .withColumn("cliente_cpf", F.when(U(111, "id") < 0.015,
                    F.concat(F.substring("cpf_ok", 1, 10), ((F.substring("cpf_ok", 11, 1).cast("int") + 1) % 10).cast("string")))
                    .otherwise(F.col("cpf_ok")))
        # ~35% com máscara 000.000.000-00
        .withColumn("cliente_cpf", F.when(U(112, "id") < 0.35,
                    F.concat(F.substring("cliente_cpf", 1, 3), F.lit("."), F.substring("cliente_cpf", 4, 3), F.lit("."),
                             F.substring("cliente_cpf", 7, 3), F.lit("-"), F.substring("cliente_cpf", 10, 2)))
                    .otherwise(F.col("cliente_cpf")))
        .withColumn("cliente_email", F.when(U(113, "id") < 0.025, F.lit(None).cast("string")).otherwise(F.col("cliente_email")))
        .withColumn("cliente_celular", F.when(U(114, "id") < 0.04, F.lit(None).cast("string"))
                    .when(U(117, "id") < 0.12, F.regexp_replace("cliente_celular", r"\D", ""))   # ~12% sem máscara
                    .otherwise(F.col("cliente_celular")))
        .withColumn("cliente_rg", F.when(U(118, "id") < 0.50, F.regexp_replace("cliente_rg", r"[.\-]", ""))  # ~50% sem máscara
                    .otherwise(F.col("cliente_rg")))
        .withColumn("cliente_cep", F.when(U(119, "id") < 0.06, F.regexp_replace("cliente_cep", "-", "")).otherwise(F.col("cliente_cep")))
        .withColumn("cliente_uf", F.when(U(115, "id") < 0.01, F.lower(F.col("cliente_uf"))).otherwise(F.col("cliente_uf"))))

clientes = cli.select("cliente_ref", "cliente_id", "cliente_nome", "cliente_cpf", "_nasc_prelim", "cliente_sexo",
                      "cliente_estado_civil", "cliente_email", "cliente_celular", "cliente_telefone_fixo", "cliente_rg",
                      "cliente_rg_orgao_emissor", "cliente_rg_uf_emissor", "cliente_logradouro", "cliente_numero",
                      "cliente_complemento", "cliente_bairro", "cliente_cep", "cliente_cidade", "cliente_uf",
                      "cliente_endereco_completo", "cliente_renda_faixa", "cliente_profissao", "cliente_fumante")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Apólices (dbldatagen) — junta cliente, produto e corretor, e grava em staging

# COMMAND ----------

apol_spec = (
    dg.DataGenerator(spark, name="apolices", rows=N_APOL, partitions=8, randomSeed=SEED + 3, randomSeedMethod="hash_fieldname")
    .withIdOutput()
    .withColumn("cliente_ref", "integer", minValue=0, maxValue=N_CLIENTES - 1, random=True)
    .withColumn("produto_idx", "integer", values=[p[0] for p in PRODUTOS], weights=[p[7] for p in PRODUTOS], random=True)
    .withColumn("periodicidade_pagamento", "string", values=["MENSAL", "TRIMESTRAL", "SEMESTRAL", "ANUAL"],
                weights=[78, 8, 6, 8], random=True)
    .withColumn("forma_pagamento", "string", values=["DEBITO_CONTA", "BOLETO", "CARTAO_CREDITO", "PIX_AUTOMATICO"],
                weights=[40, 25, 27, 8], random=True)
    .withColumn("canal_venda", "string", values=["CORRETOR", "BANCASSURANCE", "DIGITAL", "TELEVENDAS"],
                weights=[58, 20, 14, 8], random=True)
    .withColumn("status_apolice", "string", values=["ATIVA", "SUSPENSA", "REDUZIDA", "CANCELADA_INADIMPLENCIA"],
                weights=[80, 10, 5, 5], random=True)
    .withColumn("capital_base", "integer", values=[50000, 100000, 150000, 200000, 300000, 500000, 1000000],
                weights=[10, 25, 20, 18, 15, 9, 3], random=True)
    .withColumn("dia_vencimento", "integer", values=[5, 10, 15, 20, 25, 28], weights=[20, 20, 20, 15, 15, 10], random=True)
    .withColumn("qtd_end_raw", "integer", values=[0, 1, 2, 3], weights=[78, 15, 5, 2], random=True)
    .withColumn("tipo_ultimo_endosso", "string", values=TIPOS_ENDOSSO, weights=[18, 16, 8, 20, 10, 16, 12], random=True)
    .withColumn("qtd_beneficiarios", "integer", values=[1, 2, 3, 4], weights=[45, 30, 17, 8], random=True)
    .withColumn("parentesco_beneficiario_principal", "string",
                values=["CONJUGE", "FILHO", "PAIS", "IRMAO", "OUTROS"], weights=[45, 30, 12, 5, 8], random=True)
)

DIAS_ATE_ANIV = "12 * (cast(floor(months_between(" + D + ", data_inicio_vigencia) / 12) as int) + 1)"

apol = (apol_spec.build()
    .withColumn("numero_apolice", F.concat(F.lit("VID"), F.lpad((F.col("id") + 1).cast("string"), 9, "0")))
    .withColumn("dias_emissao", F.when(U(11, "id") < 0.14, (F.lit(20) + F.floor(U(12, "id") * 160)).cast("int"))
                .otherwise((F.lit(180) + F.floor(U(13, "id") * 2400)).cast("int")))
    .withColumn("data_emissao", F.expr(f"date_sub({D}, dias_emissao)"))
    .withColumn("data_inicio_vigencia", F.col("data_emissao"))
    .withColumn("data_fim_vigencia_atual", F.expr(f"add_months(data_inicio_vigencia, {DIAS_ATE_ANIV})"))
    .withColumn("_x", F.expr("date_add(data_emissao, 10)"))
    .withColumn("data_primeira_parcela", F.expr(
        "CASE WHEN day(_x) <= dia_vencimento THEN make_date(year(_x), month(_x), dia_vencimento) "
        "ELSE make_date(year(add_months(_x, 1)), month(add_months(_x, 1)), dia_vencimento) END"))
    .withColumn("meses_periodicidade", F.expr(
        "CASE periodicidade_pagamento WHEN 'MENSAL' THEN 1 WHEN 'TRIMESTRAL' THEN 3 WHEN 'SEMESTRAL' THEN 6 ELSE 12 END"))
    .withColumn("fator_fracionamento", F.expr(
        "CASE meses_periodicidade WHEN 1 THEN 1.0 WHEN 3 THEN 0.99 WHEN 6 THEN 0.975 ELSE 0.95 END"))
    .withColumn("_u_n", U(41, "id"))
    .withColumn("n_alvo", F.expr(
        "CASE periodicidade_pagamento "
        " WHEN 'MENSAL' THEN CASE WHEN _u_n < 0.40 THEN 1 WHEN _u_n < 0.65 THEN 2 WHEN _u_n < 0.80 THEN 3 "
        "                         WHEN _u_n < 0.89 THEN 4 WHEN _u_n < 0.95 THEN 5 ELSE 6 END "
        " WHEN 'TRIMESTRAL' THEN CASE WHEN _u_n < 0.70 THEN 1 ELSE 2 END "
        " ELSE 1 END"))
    # coberturas adicionais
    .withColumn("possui_ipta", U(21, "id") < 0.45)
    .withColumn("possui_ifpd", U(22, "id") < 0.30)
    .withColumn("possui_doencas_graves", U(23, "id") < 0.20)
    .withColumn("possui_dit", U(24, "id") < 0.18)
    .withColumn("possui_assistencia_funeral", U(25, "id") < 0.55)
    # endossos (apólices muito novas não têm endosso)
    .withColumn("qtd_endossos", F.when(F.col("dias_emissao") < 90, F.lit(0)).otherwise(F.col("qtd_end_raw")))
    .withColumn("data_ultimo_endosso", F.when(F.col("qtd_endossos") > 0,
                F.expr("date_add(data_emissao, 30 + cast(floor("
                       "pmod(xxhash64(id, " + str(SEED + 61) + "), 1000000) / 1000000.0 * (dias_emissao - 35)) as int))")))
    .withColumn("numero_ultimo_endosso", F.when(F.col("qtd_endossos") > 0,
                F.concat(F.col("numero_apolice"), F.lit("-E"), F.lpad(F.col("qtd_endossos").cast("string"), 2, "0"))))
    .withColumn("tipo_ultimo_endosso", F.when(F.col("qtd_endossos") > 0, F.col("tipo_ultimo_endosso")))
    # corretor: só nos canais CORRETOR e BANCASSURANCE; concentração em poucos corretores
    .withColumn("corretor_idx", F.when(F.col("canal_venda").isin("CORRETOR", "BANCASSURANCE"),
                F.floor(F.lit(N_CORRETORES) * F.pow(U(31, "id"), F.lit(1.8))).cast("int")))
    .join(F.broadcast(produtos_df), "produto_idx", "left"))

# regras dependentes do produto (a cobertura principal não vira adicional)
apol = (apol
    .withColumn("possui_doencas_graves", F.when(F.col("cobertura_principal_codigo") == "DGR", F.lit(False)).otherwise(F.col("possui_doencas_graves")))
    .withColumn("possui_dit", F.when(F.col("cobertura_principal_codigo") == "DIT", F.lit(False)).otherwise(F.col("possui_dit")))
    .withColumn("n_adicionais", sum(F.col(c).cast("int") for c in
                ["possui_ipta", "possui_ifpd", "possui_doencas_graves", "possui_dit", "possui_assistencia_funeral"]))
    .withColumn("qtd_coberturas", F.col("n_adicionais") + 1)
    .withColumn("capital_segurado_principal", F.col("capital_base").cast("decimal(14,2)"))
    .withColumn("capital_segurado_total", (F.col("capital_base") * (1
                + F.col("possui_ipta").cast("int") * 1.0
                + F.col("possui_ifpd").cast("int") * 0.5
                + F.col("possui_doencas_graves").cast("int") * 0.3)).cast("decimal(14,2)")))

# primeira emissão por cliente -> data de cadastro e consistência de idade (>= 18 anos na emissão)
w_cli = Window.partitionBy("cliente_ref")
apol = apol.withColumn("_min_emissao", F.min("data_emissao").over(w_cli))

_u_pdv = U(141, "id")
apol = (apol.join(clientes, "cliente_ref", "inner").join(corretores, "corretor_idx", "left")
    .withColumn("pdv_pos", F.when(F.col("canal_venda") == "CORRETOR", F.floor(F.lit(N_PDV_ESC) * F.pow(_u_pdv, F.lit(1.5))).cast("int"))
                .when(F.col("canal_venda") == "BANCASSURANCE", F.floor(F.lit(N_PDV_AG) * F.pow(_u_pdv, F.lit(1.5))).cast("int"))
                .when(F.col("canal_venda") == "DIGITAL", F.floor(F.lit(3) * _u_pdv).cast("int"))
                .otherwise(F.floor(F.lit(4) * _u_pdv).cast("int")))
    .join(F.broadcast(pdv_df), ["canal_venda", "pdv_pos"], "left")
    .drop("pdv_pos"))

apol = (apol
    .withColumn("cliente_data_cadastro", F.expr("date_sub(_min_emissao, cast(floor(pmod(xxhash64(cliente_ref, " + str(SEED + 71) + "), 1000000) / 1000000.0 * 20) as int))"))
    .withColumn("cliente_data_nascimento", F.expr(
        "least(_nasc_prelim, date_sub(add_months(_min_emissao, -216), cast(floor(pmod(xxhash64(cliente_ref, " + str(SEED + 72) + "), 1000000) / 1000000.0 * 365) as int)))"))
    .withColumn("cliente_idade", F.expr(f"cast(floor(months_between({D}, cliente_data_nascimento) / 12) as int)"))
    .withColumn("cliente_rg_data_emissao", F.expr(
        "date_add(cliente_data_nascimento, cast(14 * 365 + floor(pmod(xxhash64(cliente_ref, " + str(SEED + 128) + "), 1000000) / 1000000.0 "
        "* (datediff(" + D + ", cliente_data_nascimento) - 15 * 365)) as int))"))
    .withColumn("_idade_emissao", F.expr("cast(floor(months_between(data_emissao, cliente_data_nascimento) / 12) as int)"))
    .withColumn("premio_mensal_base", F.round(F.expr(
        "capital_base / 1000.0 * (0.09 + 0.011 * (_idade_emissao - 18)) * fator_taxa "
        "* (CASE WHEN cliente_fumante THEN 1.35 ELSE 1.0 END) * (1 + 0.07 * n_adicionais)"), 2))
    .withColumn("valor_premio_periodico", F.round(F.col("premio_mensal_base") * F.col("meses_periodicidade")
                                                  * F.col("fator_fracionamento"), 2).cast("decimal(14,2)"))
    .withColumn("ramo", F.lit("VIDA_INDIVIDUAL"))
    .drop("_x", "_u_n", "_min_emissao", "_nasc_prelim", "qtd_end_raw", "id"))

if DEFEITOS:   # ~5% dos clientes sem RG (e sem órgão, UF e data de emissão)
    _rg_nulo = U(116, "cliente_ref") < 0.05
    for _c in ["cliente_rg", "cliente_rg_orgao_emissor", "cliente_rg_uf_emissor", "cliente_rg_data_emissao"]:
        apol = apol.withColumn(_c, F.when(_rg_nulo, F.lit(None)).otherwise(F.col(_c)))

apol.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(FQ_STG)
stg = spark.table(FQ_STG)
print("staging de apolices:", stg.count(), "linhas")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Explode em pendências (1 linha = 1 parcela vencida e não paga) dentro da janela de 6 meses

# COMMAND ----------

pend = (stg
    .withColumn("_m", F.expr(f"CASE WHEN months_between({D}, data_primeira_parcela) < 0 THEN -1 "
                             f"ELSE cast(floor(months_between({D}, data_primeira_parcela)) as int) END"))
    .withColumn("_j_max", F.expr("CASE WHEN _m < 0 THEN -1 ELSE _m div meses_periodicidade END"))
    .withColumn("_k", F.expr("explode(sequence(0, n_alvo - 1))"))
    .withColumn("_j", F.col("_j_max") - F.col("_k"))
    .withColumn("data_vencimento", F.expr("add_months(data_primeira_parcela, _j * meses_periodicidade)"))
    .filter(F.expr(f"_j >= 0 AND data_vencimento > {JANELA_INI} AND data_vencimento <= {D}"))
    .withColumn("numero_parcela", (F.col("_j") + 1).cast("int")))

n_pre = pend.count()
print("pendencias antes do corte:", n_pre, "| necessarias (unicas):", N_UNICOS)
if n_pre < N_UNICOS:
    raise ValueError(f"Poucas pendencias ({n_pre}) para {N_UNICOS}. Aumente o parametro n_apolices (atual {N_APOL}).")

pend = (pend
    .withColumn("competencia", F.date_format("data_vencimento", "yyyy-MM"))
    .withColumn("data_geracao_cobranca", F.expr("date_sub(data_vencimento, 10)"))
    .withColumn("dias_atraso", F.datediff(F.expr(D), F.col("data_vencimento")))
    .withColumn("faixa_atraso", F.expr(
        "CASE WHEN dias_atraso = 0 THEN '00_VENCE_HOJE' WHEN dias_atraso <= 15 THEN '01_1_A_15' "
        "WHEN dias_atraso <= 30 THEN '02_16_A_30' WHEN dias_atraso <= 60 THEN '03_31_A_60' "
        "WHEN dias_atraso <= 90 THEN '04_61_A_90' WHEN dias_atraso <= 120 THEN '05_91_A_120' ELSE '06_ACIMA_120' END"))
    .withColumn("valor_parcela", F.col("valor_premio_periodico"))
    .withColumn("valor_multa", F.when(F.col("dias_atraso") > 0, F.round(F.col("valor_parcela") * 0.02, 2)).otherwise(F.lit(0.0)).cast("decimal(14,2)"))
    .withColumn("valor_juros", F.round(F.col("valor_parcela") * 0.01 * F.col("dias_atraso") / 30.0, 2).cast("decimal(14,2)"))
    .withColumn("valor_total_pendente", (F.col("valor_parcela") + F.col("valor_multa") + F.col("valor_juros")).cast("decimal(14,2)"))
    .withColumn("_u_st", U(51, "numero_apolice", "numero_parcela"))
    .withColumn("_u_mo", U(52, "numero_apolice", "numero_parcela"))
    .withColumn("_u_tt", U(53, "numero_apolice", "numero_parcela"))
    .withColumn("_u_ct", U(54, "numero_apolice", "numero_parcela"))
    .withColumn("status_cobranca", F.expr(
        "CASE "
        " WHEN dias_atraso <= 15 THEN CASE WHEN _u_st < 0.70 THEN 'PENDENTE' WHEN _u_st < 0.92 THEN 'EM_COBRANCA' ELSE 'PROMESSA_PAGAMENTO' END "
        " WHEN dias_atraso <= 60 THEN CASE WHEN _u_st < 0.30 THEN 'PENDENTE' WHEN _u_st < 0.70 THEN 'EM_COBRANCA' WHEN _u_st < 0.85 THEN 'PROMESSA_PAGAMENTO' ELSE 'NEGOCIADO' END "
        " WHEN dias_atraso <= 120 THEN CASE WHEN _u_st < 0.35 THEN 'EM_COBRANCA' WHEN _u_st < 0.55 THEN 'NEGOCIADO' WHEN _u_st < 0.65 THEN 'PROMESSA_PAGAMENTO' ELSE 'COBRANCA_EXTERNA' END "
        " ELSE CASE WHEN _u_st < 0.55 THEN 'COBRANCA_EXTERNA' WHEN _u_st < 0.75 THEN 'NEGOCIADO' ELSE 'EM_COBRANCA' END "
        "END"))
    .withColumn("motivo_pendencia", F.expr(
        "CASE forma_pagamento "
        " WHEN 'DEBITO_CONTA' THEN CASE WHEN _u_mo < 0.60 THEN 'SALDO_INSUFICIENTE' WHEN _u_mo < 0.75 THEN 'CONTA_ENCERRADA' WHEN _u_mo < 0.90 THEN 'DADOS_BANCARIOS_INVALIDOS' ELSE 'AUTORIZACAO_DEBITO_CANCELADA' END "
        " WHEN 'BOLETO' THEN CASE WHEN _u_mo < 0.85 THEN 'BOLETO_NAO_PAGO' ELSE 'BOLETO_NAO_RECEBIDO' END "
        " WHEN 'CARTAO_CREDITO' THEN CASE WHEN _u_mo < 0.50 THEN 'CARTAO_RECUSADO' WHEN _u_mo < 0.80 THEN 'CARTAO_EXPIRADO' ELSE 'LIMITE_INSUFICIENTE' END "
        " ELSE CASE WHEN _u_mo < 0.70 THEN 'SALDO_INSUFICIENTE' ELSE 'AUTORIZACAO_PIX_REVOGADA' END "
        "END"))
    .withColumn("tentativas_cobranca", F.expr("cast(least(10, floor(dias_atraso / 10) + floor(_u_tt * 3) + 1) as int)"))
    .withColumn("data_ultima_tentativa", F.expr("date_add(data_vencimento, cast(floor(_u_tt * dias_atraso) as int))"))
    .withColumn("canal_ultimo_contato", F.expr(
        "CASE WHEN _u_ct < 0.30 THEN 'SMS' WHEN _u_ct < 0.55 THEN 'EMAIL' WHEN _u_ct < 0.75 THEN 'WHATSAPP' "
        "WHEN _u_ct < 0.90 THEN 'TELEFONE' WHEN _u_ct < 0.95 THEN 'CARTA' ELSE 'NENHUM' END"))
    .withColumn("parcela_afetada_por_endosso", F.expr("coalesce(qtd_endossos > 0 AND data_vencimento >= data_ultimo_endosso, false)"))
    .withColumn("data_extracao", F.expr(D))
    .withColumn("sistema_origem", F.lit("CORE_VIDA"))
    .withColumn("_ordem_corte", F.expr(f"xxhash64(numero_apolice, numero_parcela, {SEED + 99})")))

# corta para exatamente N_UNICOS linhas (ordem pseudoaleatória estável) e numera por data de vencimento
w_corte = Window.orderBy("_ordem_corte", "numero_apolice", "numero_parcela")
w_id = Window.orderBy("data_vencimento", "numero_apolice", "numero_parcela")
pend = (pend
    .withColumn("_rn", F.row_number().over(w_corte))
    .filter(F.col("_rn") <= N_UNICOS)
    .withColumn("_seq", F.row_number().over(w_id))
    .withColumn("pendencia_id", F.concat(F.lit("PD"), F.lpad(F.col("_seq").cast("string"), 9, "0"))))

COLUNAS = [
    # pendência / cobrança
    "pendencia_id", "data_extracao", "sistema_origem", "numero_apolice", "numero_parcela", "competencia",
    "data_vencimento", "data_geracao_cobranca", "dias_atraso", "faixa_atraso",
    "valor_parcela", "valor_multa", "valor_juros", "valor_total_pendente",
    "status_cobranca", "motivo_pendencia", "tentativas_cobranca", "data_ultima_tentativa", "canal_ultimo_contato",
    "parcela_afetada_por_endosso",
    # apólice / produto / cobertura / periodicidade / endosso
    "ramo", "status_apolice", "produto_codigo", "produto_nome", "categoria_produto", "canal_venda",
    "data_emissao", "data_inicio_vigencia", "data_fim_vigencia_atual", "dia_vencimento",
    "periodicidade_pagamento", "meses_periodicidade", "forma_pagamento", "valor_premio_periodico",
    "capital_segurado_principal", "capital_segurado_total", "cobertura_principal_codigo", "cobertura_principal_nome",
    "possui_ipta", "possui_ifpd", "possui_doencas_graves", "possui_dit", "possui_assistencia_funeral", "qtd_coberturas",
    "qtd_endossos", "numero_ultimo_endosso", "tipo_ultimo_endosso", "data_ultimo_endosso",
    "qtd_beneficiarios", "parentesco_beneficiario_principal",
    # ponto de venda
    "ponto_venda_codigo", "ponto_venda_nome", "ponto_venda_tipo", "ponto_venda_cidade", "ponto_venda_uf", "ponto_venda_regional",
    # corretor
    "corretor_id", "corretor_nome", "corretor_tipo_pessoa", "corretor_documento", "corretor_registro_susep",
    "corretor_regional", "corretor_comissao_pct", "corretor_status", "corretor_data_credenciamento",
    # cliente
    "cliente_id", "cliente_nome", "cliente_cpf", "cliente_data_nascimento", "cliente_idade", "cliente_sexo",
    "cliente_estado_civil", "cliente_email", "cliente_celular", "cliente_telefone_fixo",
    "cliente_rg", "cliente_rg_orgao_emissor", "cliente_rg_uf_emissor", "cliente_rg_data_emissao",
    "cliente_logradouro", "cliente_numero", "cliente_complemento", "cliente_bairro", "cliente_cep", "cliente_cidade",
    "cliente_uf", "cliente_endereco_completo",
    "cliente_renda_faixa", "cliente_profissao", "cliente_fumante", "cliente_data_cadastro",
]
final = pend.select(*COLUNAS).orderBy("pendencia_id")

(final.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(FQ_TABELA))
print("tabela gravada:", FQ_TABELA)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Duplicatas exatas (defeito proposital) — copia N linhas já gravadas

# COMMAND ----------

if N_DUP > 0:
    base = spark.table(FQ_TABELA)
    dups = base.orderBy(F.expr(f"xxhash64(pendencia_id, {SEED + 7})")).limit(N_DUP)
    dups.write.mode("append").saveAsTable(FQ_TABELA)
    print("duplicatas anexadas:", N_DUP)

spark.sql(f"DROP TABLE IF EXISTS {FQ_STG}")
spark.sql(f"""COMMENT ON TABLE {FQ_TABELA} IS
  'One table sintetica de pagamentos pendentes de seguro de vida (dominio pos_venda). Grao: 1 parcela pendente por linha. Gerada com dbldatagen; contem defeitos de qualidade propositais quando injetar_defeitos=true.'""")
spark.sql(f"""ALTER TABLE {FQ_TABELA} SET TBLPROPERTIES (
  'dominio' = 'pos_venda', 'camada' = 'landing', 'origem' = 'sintetico_dbldatagen',
  'data_extracao' = '{DATA_EXTRACAO}', 'janela_meses' = '{MESES}')""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validação

# COMMAND ----------

t = spark.table(FQ_TABELA)
res = {"tabela": FQ_TABELA, "n_pre_corte": n_pre}
res["linhas"] = t.count()
res["colunas"] = len(t.columns)
res["pendencia_id_distintos"] = t.select("pendencia_id").distinct().count()
res["linhas_distintas_completas"] = t.distinct().count()

a = t.agg(
    F.min("data_vencimento").alias("venc_min"), F.max("data_vencimento").alias("venc_max"),
    F.countDistinct("numero_apolice").alias("apolices"), F.countDistinct("cliente_id").alias("clientes"),
    F.countDistinct("corretor_id").alias("corretores"), F.sum("valor_total_pendente").alias("soma_total_pendente"),
    F.avg("valor_parcela").alias("parcela_media"), F.min("valor_parcela").alias("parcela_min"),
    F.max("valor_parcela").alias("parcela_max"), F.min("dias_atraso").alias("atraso_min"),
    F.max("dias_atraso").alias("atraso_max")).first().asDict()
res["agregados"] = json.loads(json.dumps(a, default=str))

def dist(col):
    return {str(r[0]): r[1] for r in t.groupBy(col).count().orderBy(F.desc("count")).collect()}
for c in ["periodicidade_pagamento", "status_cobranca", "faixa_atraso", "status_apolice", "canal_venda",
          "produto_nome", "forma_pagamento", "motivo_pendencia", "competencia", "qtd_endossos"]:
    res["dist_" + c] = dist(c)

n = res["linhas"]
res["nulos_pct"] = {c: round(100.0 * t.filter(F.col(c).isNull()).count() / n, 2)
                    for c in ["cliente_email", "cliente_celular", "cliente_telefone_fixo", "cliente_rg", "cliente_complemento",
                              "corretor_id", "numero_ultimo_endosso", "ponto_venda_codigo"]}

cl = t.select("cliente_id", "cliente_cpf").distinct()
cl = cl.withColumn("_d", F.regexp_replace("cliente_cpf", r"\D", "")).withColumn("_b", F.substring("_d", 1, 9).cast("long"))
cl = add_cpf(cl, "_b", "_esperado")
res["clientes_distintos"] = cl.count()
res["cpf_invalidos"] = cl.filter(F.col("_d") != F.col("_esperado")).count()
res["cpf_com_mascara"] = cl.filter(F.col("cliente_cpf").contains(".")).count()
res["uf_minuscula"] = t.filter(F.col("cliente_uf") != F.upper("cliente_uf")).count()

res["viol_apolice_varios_clientes"] = t.groupBy("numero_apolice").agg(F.countDistinct("cliente_id").alias("n")).filter("n > 1").count()
res["viol_apolice_varios_produtos"] = t.groupBy("numero_apolice").agg(F.countDistinct("produto_codigo").alias("n")).filter("n > 1").count()
res["viol_apolice_varias_periodicidades"] = t.groupBy("numero_apolice").agg(F.countDistinct("periodicidade_pagamento").alias("n")).filter("n > 1").count()
res["viol_cliente_varios_nomes"] = t.groupBy("cliente_id").agg(F.countDistinct("cliente_nome").alias("n")).filter("n > 1").count()
res["viol_atraso_negativo"] = t.filter("dias_atraso < 0").count()
res["viol_venc_fora_janela"] = t.filter(F.expr(f"data_vencimento <= {JANELA_INI} OR data_vencimento > {D}")).count()
res["viol_emissao_apos_vencimento"] = t.filter("data_emissao > data_vencimento").count()
res["viol_menor_18_na_emissao"] = t.filter(F.expr("months_between(data_emissao, cliente_data_nascimento) / 12 < 18")).count()
res["viol_cadastro_apos_emissao"] = t.filter("cliente_data_cadastro > data_emissao").count()
res["viol_total_diferente_soma"] = t.filter(F.expr("abs(valor_total_pendente - (valor_parcela + valor_multa + valor_juros)) > 0.005")).count()

# independência entre colunas sorteadas (detecta correlação espúria entre geradores)
cn = t.select("cliente_id", "cliente_nome").distinct().withColumn("_p", F.split("cliente_nome", " "))
res["pct_clientes_sobrenome_repetido"] = round(100.0 * cn.filter("size(_p) = 3 AND _p[1] = _p[2]").count() / cn.count(), 2)
res["xtab_periodicidade_x_forma_pagto"] = {f"{r[0]}|{r[1]}": r[2] for r in t.groupBy("periodicidade_pagamento", "forma_pagamento").count().collect()}
res["xtab_periodicidade_x_canal"] = {f"{r[0]}|{r[1]}": r[2] for r in t.groupBy("periodicidade_pagamento", "canal_venda").count().collect()}
res["viol_cliente_varios_enderecos"] = t.groupBy("cliente_id").agg(F.countDistinct("cliente_endereco_completo").alias("n")).filter("n > 1").count()
res["viol_cliente_varios_rg"] = t.groupBy("cliente_id").agg(F.countDistinct("cliente_rg").alias("n")).filter("n > 1").count()
res["viol_apolice_varios_pdv"] = t.groupBy("numero_apolice").agg(F.countDistinct("ponto_venda_codigo").alias("n")).filter("n > 1").count()
res["viol_pdv_tipo_x_canal"] = t.filter(~F.expr(
    "(canal_venda = 'CORRETOR' AND ponto_venda_tipo = 'ESCRITORIO_CORRETOR') OR (canal_venda = 'BANCASSURANCE' AND ponto_venda_tipo = 'AGENCIA_BANCARIA') "
    "OR (canal_venda = 'DIGITAL' AND ponto_venda_tipo = 'PLATAFORMA_DIGITAL') OR (canal_venda = 'TELEVENDAS' AND ponto_venda_tipo = 'CENTRAL_TELEVENDAS')")).count()
res["viol_endereco_uf_diferente"] = t.filter(~F.expr("cliente_endereco_completo LIKE concat('%/', upper(cliente_uf), ' - %')")).count()
res["viol_rg_emitido_antes_nascimento"] = t.filter("cliente_rg_data_emissao < cliente_data_nascimento OR cliente_rg_data_emissao > data_extracao").count()
res["pdvs_distintos"] = t.select("ponto_venda_codigo").distinct().count()
res["celular_sem_mascara"] = t.select("cliente_id", "cliente_celular").distinct().filter(F.col("cliente_celular").isNotNull() & ~F.col("cliente_celular").contains("(")).count()
res["rg_sem_mascara"] = t.select("cliente_id", "cliente_rg").distinct().filter(F.col("cliente_rg").isNotNull() & ~F.col("cliente_rg").contains(".")).count()
res["cep_sem_hifen"] = t.select("cliente_id", "cliente_cep").distinct().filter(~F.col("cliente_cep").contains("-")).count()
res["amostra_cadastro"] = [json.loads(json.dumps(r.asDict(), default=str, ensure_ascii=False)) for r in
    t.filter("cliente_complemento IS NOT NULL AND cliente_rg IS NOT NULL").orderBy("pendencia_id")
     .select("cliente_nome", "cliente_cpf", "cliente_rg", "cliente_rg_orgao_emissor", "cliente_rg_uf_emissor", "cliente_rg_data_emissao",
             "cliente_sexo", "cliente_profissao", "cliente_celular", "cliente_telefone_fixo", "cliente_email", "cliente_logradouro",
             "cliente_numero", "cliente_complemento", "cliente_bairro", "cliente_cidade", "cliente_uf", "cliente_cep",
             "cliente_endereco_completo", "canal_venda", "ponto_venda_codigo", "ponto_venda_nome", "ponto_venda_tipo",
             "ponto_venda_cidade", "ponto_venda_uf", "ponto_venda_regional").limit(3).collect()]
res["xtab_status_apolice_x_produto"] = {f"{r[0]}|{r[1]}": r[2] for r in t.groupBy("status_apolice", "categoria_produto").count().collect()}

dbutils.notebook.exit(json.dumps(res, default=str, ensure_ascii=False))
