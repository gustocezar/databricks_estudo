#!/usr/bin/env python3
"""Regras de qualidade (DQX) do dominio pos_venda: bronze, silver e gold (star schema).

Cada regra e um "check" no formato de metadados do DQX:
    {"name": ..., "criticality": "error" | "warn", "check": {"function": ..., "arguments": {...}}, "filter": ..., "user_metadata": {...}}

- criticality "error": viola uma garantia da camada (chave duplicada, FK sem dimensao, valor negativo...).
- criticality "warn" : problema de qualidade conhecido e esperado, para acompanhar (CPF invalido, e-mail ausente...).

Rodar este arquivo grava os checks em regras/checks/<catalogo>.<schema>.<tabela>.json e confere se toda coluna citada existe.
"""
import json
import pathlib
import subprocess

AQUI = pathlib.Path(__file__).resolve().parent
PROFILE = "dbx-workshop"
CAT = "pos_venda"

UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
       "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
STATUS = ["PENDENTE", "EM_COBRANCA", "PROMESSA_PAGAMENTO", "NEGOCIADO", "COBRANCA_EXTERNA", "PAGA"]
CANAIS_CONTATO = ["SMS", "EMAIL", "WHATSAPP", "TELEFONE", "CARTA", "NENHUM"]
FAIXAS = ["01_1_A_15", "02_16_A_30", "03_31_A_60", "04_61_A_90", "05_91_A_120", "06_ACIMA_120"]

REGRAS = {}   # tabela completa -> lista de checks
_camada = {}


LISTAS_DE_LITERAIS = {"is_in_list", "is_not_in_list", "is_not_null_and_is_in_list"}


def chk(tabela, funcao, nome, criticidade="error", filtro=None, **argumentos):
    # No DQX, um texto solto dentro de "allowed" e lido como NOME DE COLUNA. Para valores literais o texto precisa vir entre
    # aspas simples (ex.: "'NOVA'"). Sem isso o Studio falha com UNRESOLVED_COLUMN.
    if funcao in LISTAS_DE_LITERAIS:
        for k in ("allowed", "forbidden"):
            if k in argumentos:
                argumentos[k] = [f"'{x}'" if isinstance(x, str) else x for x in argumentos[k]]
    c = {"name": nome, "criticality": criticidade, "check": {"function": funcao, "arguments": argumentos},
         "user_metadata": {"dominio": "pos_venda", "camada": _camada[tabela]}}
    if filtro:
        c["filter"] = filtro
    REGRAS.setdefault(tabela, []).append(c)


def tabela(schema, nome):
    fq = f"{CAT}.{schema}.{nome}"
    _camada[fq] = schema
    REGRAS.setdefault(fq, [])
    return fq


def nao_nulos(t, colunas, criticidade="error"):
    for c in colunas:
        chk(t, "is_not_null", f"{c}_nao_nulo", criticidade, column=c)


def unica(t, colunas, nome=None, filtro=None):
    chk(t, "is_unique", nome or "pk_unica_" + "_".join(colunas), "error", filtro=filtro, columns=colunas)


def total_confere(t):
    chk(t, "sql_expression", "valor_total_igual_parcela_multa_juros", "error",
        expression="abs(valor_total_pendente - (valor_parcela + valor_multa + valor_juros)) < 0.01",
        msg="valor_total_pendente difere de parcela + multa + juros", name="valor_total_igual_parcela_multa_juros")


# Espelho da regra de barreira `valores_fora_da_regra` (carga_diaria): multa, juros e total iguais às funções de regra de
# negócio pos_venda.regras.* (contrato em pos_venda/regras/features). Quem executa o Studio precisa de EXECUTE no schema.
REGRAS_FN = f"{CAT}.regras"


def valores_seguem_regra(t):
    chk(t, "sql_expression", "valores_seguem_regras_de_calculo", "error",
        expression=(f"(valor_multa <=> {REGRAS_FN}.valor_multa(valor_parcela)) "
                    f"AND (valor_juros <=> {REGRAS_FN}.valor_juros(valor_parcela, dias_atraso)) "
                    f"AND (valor_total_pendente <=> {REGRAS_FN}.valor_total_pendente(valor_parcela, dias_atraso))"),
        msg="multa, juros ou total diferentes das funções pos_venda.regras (barreira: valores_fora_da_regra)",
        name="valores_seguem_regras_de_calculo")


# =============================================================================================== BRONZE
b = tabela("bronze", "pagamentos_pendentes_eventos")
nao_nulos(b, ["pendencia_id", "data_extracao", "tipo_evento", "numero_apolice", "numero_parcela", "cliente_id", "data_vencimento"])
chk(b, "is_in_list", "tipo_evento_valido", column="tipo_evento", allowed=["NOVA", "ATUALIZACAO", "BAIXA"])
chk(b, "is_in_list", "status_cobranca_valido", column="status_cobranca", allowed=STATUS)
chk(b, "is_not_less_than", "valor_parcela_positivo", column="valor_parcela", limit=0.01)
chk(b, "is_not_less_than", "dias_atraso_minimo_1", column="dias_atraso", limit=1)
total_confere(b)
valores_seguem_regra(b)
chk(b, "sql_expression", "baixa_tem_data_e_valor_pago", "error",
    expression="tipo_evento <> 'BAIXA' OR (data_baixa IS NOT NULL AND valor_pago IS NOT NULL)",
    msg="evento BAIXA sem data_baixa ou valor_pago", name="baixa_tem_data_e_valor_pago")
chk(b, "sql_expression", "vencimento_ate_data_do_evento", "error", expression="data_vencimento < data_extracao",
    msg="vencimento nao e anterior ao dia do evento", name="vencimento_ate_data_do_evento")
chk(b, "regex_match", "cpf_formato_com_ou_sem_mascara", "warn", column="cliente_cpf",
    regex=r"^([0-9]{11}|[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2})$")
chk(b, "is_valid_email", "email_valido", "warn", column="cliente_email")
chk(b, "is_not_null", "email_preenchido", "warn", column="cliente_email")   # is_valid_email deixa passar e-mail vazio
FORMAS = ["DEBITO_CONTA", "BOLETO", "CARTAO_CREDITO", "PIX_AUTOMATICO"]
MOTIVOS = ["SALDO_INSUFICIENTE", "LIMITE_INSUFICIENTE", "CARTAO_RECUSADO", "BOLETO_NAO_PAGO", "DADOS_BANCARIOS_INVALIDOS", "CONTA_ENCERRADA",
           "CARTAO_EXPIRADO", "AUTORIZACAO_DEBITO_CANCELADA", "AUTORIZACAO_PIX_REVOGADA", "BOLETO_NAO_RECEBIDO"]
unica(b, ["pendencia_id", "data_extracao", "tipo_evento"], "evento_unico_por_dia_pendencia_tipo")
b_dup = REGRAS[b][-1]; b_dup["criticality"] = "warn"      # duplicata no bronze e esperada (reenvio); a silver deduplica
chk(b, "sql_expression", "atraso_confere_com_as_datas", "error", expression="dias_atraso = datediff(data_extracao, data_vencimento)",
    msg="dias_atraso difere de data_extracao - data_vencimento", name="atraso_confere_com_as_datas")
chk(b, "is_in_list", "uf_valida", column="cliente_uf", allowed=UFS, case_sensitive=False)   # no bronze a caixa nao invalida a UF
chk(b, "regex_match", "uf_em_maiusculas", "warn", column="cliente_uf", regex=r"^[A-Z]{2}$")  # mas e acompanhada como aviso
chk(b, "sql_expression", "cliente_maior_de_idade", "error", expression="cliente_idade >= 18", msg="cliente menor de 18 anos", name="cliente_maior_de_idade")
chk(b, "is_in_list", "forma_pagamento_cadastrada", column="forma_pagamento", allowed=FORMAS)
chk(b, "is_in_list", "motivo_pendencia_cadastrado", column="motivo_pendencia", allowed=MOTIVOS)
chk(b, "sql_expression", "canal_corretor_tem_corretor", "warn", expression="canal_venda <> 'CORRETOR' OR corretor_id IS NOT NULL",
    msg="venda pelo canal CORRETOR sem corretor", name="canal_corretor_tem_corretor")

# =============================================================================================== SILVER
s = tabela("silver", "pendencia_atual")
unica(s, ["pendencia_id"])
nao_nulos(s, ["pendencia_id", "cliente_id", "numero_apolice", "numero_parcela", "data_vencimento", "status_cobranca", "valor_parcela"])
chk(s, "is_in_list", "status_cobranca_valido", column="status_cobranca", allowed=STATUS)
chk(s, "is_in_list", "faixa_atraso_valida", column="faixa_atraso", allowed=FAIXAS)
chk(s, "is_in_list", "uf_valida", column="cliente_uf", allowed=UFS)
chk(s, "is_not_less_than", "valor_parcela_positivo", column="valor_parcela", limit=0.01)
chk(s, "is_in_range", "tentativas_entre_1_e_10", column="tentativas_cobranca", min_limit=1, max_limit=10)
total_confere(s)
valores_seguem_regra(s)
chk(s, "sql_expression", "vencimento_ate_extracao", "error", expression="data_vencimento <= data_extracao",
    msg="vencimento depois da data de extracao", name="vencimento_ate_extracao")
chk(s, "sql_expression", "paga_tem_data_baixa", "error",
    expression="(status_cobranca = 'PAGA') = (data_baixa IS NOT NULL)", msg="status PAGA e data_baixa nao batem",
    name="paga_tem_data_baixa")
chk(s, "sql_expression", "cliente_maior_de_idade", "error", expression="cliente_idade >= 18",
    msg="cliente menor de 18 anos", name="cliente_maior_de_idade")
chk(s, "sql_expression", "cpf_valido", "warn", expression="NOT dq_cpf_invalido", msg="CPF com digito verificador invalido", name="cpf_valido")
chk(s, "regex_match", "cep_8_digitos", "warn", column="cliente_cep", regex=r"^[0-9]{8}$")
chk(s, "regex_match", "celular_11_digitos", "warn", column="cliente_celular", regex=r"^[0-9]{11}$")
chk(s, "regex_match", "telefone_fixo_10_digitos", "warn", column="cliente_telefone_fixo", regex=r"^[0-9]{10}$")
chk(s, "regex_match", "rg_formato", "warn", column="cliente_rg", regex=r"^[0-9]{8}[0-9X]$")
chk(s, "is_valid_email", "email_valido", "warn", column="cliente_email")
chk(s, "is_not_null", "email_preenchido", "warn", column="cliente_email")   # is_valid_email deixa passar e-mail vazio
chk(s, "is_not_null", "rg_preenchido", "warn", column="cliente_rg")
chk(s, "is_in_list", "forma_pagamento_cadastrada", column="forma_pagamento", allowed=FORMAS)
chk(s, "is_in_list", "motivo_pendencia_cadastrado", column="motivo_pendencia", allowed=MOTIVOS)
chk(s, "sql_expression", "canal_corretor_tem_corretor", "warn", expression="canal_venda <> 'CORRETOR' OR corretor_id IS NOT NULL",
    msg="venda pelo canal CORRETOR sem corretor", name="canal_corretor_tem_corretor")

h = tabela("silver", "pendencia_hist")
unica(h, ["pendencia_id", "__START_AT"], "pk_unica_pendencia_id_inicio_vigencia")
unica(h, ["pendencia_id"], "uma_versao_corrente_por_pendencia", filtro="__END_AT IS NULL")
nao_nulos(h, ["pendencia_id", "__START_AT", "status_cobranca", "tipo_evento"])
chk(h, "is_in_list", "status_cobranca_valido", column="status_cobranca", allowed=STATUS)
chk(h, "is_in_list", "tipo_evento_valido", column="tipo_evento", allowed=["NOVA", "ATUALIZACAO", "BAIXA"])
chk(h, "sql_expression", "vigencia_fim_depois_do_inicio", "error", expression="__END_AT IS NULL OR __END_AT > __START_AT",
    msg="fim de vigencia nao e posterior ao inicio", name="vigencia_fim_depois_do_inicio")
chk(h, "sql_expression", "versao_paga_e_a_corrente", "error", expression="status_cobranca <> 'PAGA' OR __END_AT IS NULL",
    msg="versao PAGA deveria ser a ultima (corrente)", name="versao_paga_e_a_corrente")

# =============================================================================================== GOLD · FATO
f = tabela("gold", "fact_pagamento_pendente_snapshot")
FKS = [("cliente_sk", "dim_cliente", "cliente_sk"), ("apolice_sk", "dim_apolice", "apolice_sk"), ("produto_sk", "dim_produto", "produto_sk"),
       ("corretor_sk", "dim_corretor", "corretor_sk"), ("ponto_venda_sk", "dim_ponto_venda", "ponto_venda_sk"),
       ("periodicidade_sk", "dim_periodicidade", "periodicidade_sk"), ("forma_pagamento_sk", "dim_forma_pagamento", "forma_pagamento_sk"),
       ("status_cobranca_sk", "dim_status_cobranca", "status_cobranca_sk"), ("motivo_pendencia_sk", "dim_motivo_pendencia", "motivo_pendencia_sk"),
       ("faixa_atraso_sk", "dim_faixa_atraso", "faixa_atraso_sk"), ("data_referencia_sk", "dim_data", "data_sk"),
       ("data_vencimento_sk", "dim_data", "data_sk")]
unica(f, ["data_referencia_sk", "pendencia_id"])
nao_nulos(f, ["data_referencia_sk", "pendencia_id"] + [c for c, _, _ in FKS if c != "data_referencia_sk"])
for col, dim, dcol in FKS:
    chk(f, "foreign_key", f"fk_{col}", columns=[col], ref_columns=[dcol], ref_table=f"{CAT}.gold.{dim}")
chk(f, "is_not_less_than", "valor_parcela_positivo", column="valor_parcela", limit=0.01)
chk(f, "is_not_less_than", "dias_atraso_minimo_1", column="dias_atraso", limit=1)
chk(f, "is_in_range", "tentativas_entre_1_e_10", column="tentativas_cobranca", min_limit=1, max_limit=10)
chk(f, "is_in_list", "canal_contato_valido", column="canal_ultimo_contato", allowed=CANAIS_CONTATO)
chk(f, "sql_expression", "qtd_pendencias_igual_1", "error", expression="qtd_pendencias = 1", msg="grao da fato: qtd_pendencias deve ser 1", name="qtd_pendencias_igual_1")
total_confere(f)
valores_seguem_regra(f)
chk(f, "sql_expression", "multa_e_2_por_cento_da_parcela", "error",
    expression="abs(valor_multa - round(valor_parcela * 0.02, 2)) < 0.01", msg="multa diferente de 2% da parcela", name="multa_e_2_por_cento_da_parcela")
chk(f, "sql_expression", "entrada_depois_do_vencimento", "error", expression="data_entrada_pendencia_sk > data_vencimento_sk",
    msg="pendencia entra antes do vencimento", name="entrada_depois_do_vencimento")
chk(f, "sql_expression", "foto_nao_anterior_a_entrada", "error", expression="data_referencia_sk >= data_entrada_pendencia_sk",
    msg="foto anterior a entrada da pendencia", name="foto_nao_anterior_a_entrada")

# =============================================================================================== GOLD · DIMENSOES
c = tabela("gold", "dim_cliente")
unica(c, ["cliente_sk"]); unica(c, ["cliente_id"])
nao_nulos(c, ["cliente_sk", "cliente_id", "cliente_nome", "cliente_cpf", "cliente_data_nascimento"])
chk(c, "is_in_list", "sexo_valido", column="cliente_sexo", allowed=["F", "M"])
chk(c, "is_in_list", "estado_civil_valido", column="cliente_estado_civil", allowed=["SOLTEIRO", "CASADO", "UNIAO_ESTAVEL", "DIVORCIADO", "VIUVO"])
chk(c, "is_in_list", "renda_faixa_valida", column="cliente_renda_faixa", allowed=["ATE_3_SM", "3_A_6_SM", "6_A_10_SM", "10_A_20_SM", "ACIMA_20_SM"])
chk(c, "is_in_list", "uf_valida", column="cliente_uf", allowed=UFS)
chk(c, "sql_expression", "cliente_maior_de_idade", "error", expression="cliente_idade >= 18", msg="cliente menor de 18 anos", name="cliente_maior_de_idade")
chk(c, "sql_expression", "rg_emitido_depois_do_nascimento", "error",
    expression="cliente_rg_data_emissao IS NULL OR cliente_rg_data_emissao >= cliente_data_nascimento",
    msg="RG emitido antes do nascimento", name="rg_emitido_depois_do_nascimento")
chk(c, "sql_expression", "cpf_valido", "warn", expression="cliente_cpf_valido", msg="CPF com digito verificador invalido", name="cpf_valido")
chk(c, "regex_match", "cpf_11_digitos", "warn", column="cliente_cpf", regex=r"^[0-9]{11}$")
chk(c, "regex_match", "cep_8_digitos", "warn", column="cliente_cep", regex=r"^[0-9]{8}$")
chk(c, "regex_match", "celular_11_digitos", "warn", column="cliente_celular", regex=r"^[0-9]{11}$")
chk(c, "is_valid_email", "email_valido", "warn", column="cliente_email")
chk(c, "is_not_null", "email_preenchido", "warn", column="cliente_email")   # is_valid_email deixa passar e-mail vazio
chk(c, "is_not_null", "rg_preenchido", "warn", column="cliente_rg")

a = tabela("gold", "dim_apolice")
unica(a, ["apolice_sk"]); unica(a, ["numero_apolice"])
nao_nulos(a, ["apolice_sk", "numero_apolice", "status_apolice", "data_emissao", "data_inicio_vigencia", "data_fim_vigencia_atual"])
chk(a, "is_in_list", "status_apolice_valido", column="status_apolice", allowed=["ATIVA", "SUSPENSA", "REDUZIDA", "CANCELADA_INADIMPLENCIA"])
chk(a, "is_in_range", "dia_vencimento_entre_1_e_28", column="dia_vencimento", min_limit=1, max_limit=28)
chk(a, "is_not_less_than", "premio_positivo", column="valor_premio_periodico", limit=0.01)
chk(a, "is_not_less_than", "ao_menos_uma_cobertura", column="qtd_coberturas", limit=1)
chk(a, "is_in_range", "beneficiarios_entre_1_e_4", column="qtd_beneficiarios", min_limit=1, max_limit=4)
chk(a, "sql_expression", "fim_vigencia_depois_do_inicio", "error", expression="data_fim_vigencia_atual > data_inicio_vigencia",
    msg="fim de vigencia nao e posterior ao inicio", name="fim_vigencia_depois_do_inicio")
chk(a, "sql_expression", "capital_total_maior_ou_igual_ao_principal", "error", expression="capital_segurado_total >= capital_segurado_principal",
    msg="capital total menor que o capital principal", name="capital_total_maior_ou_igual_ao_principal")
chk(a, "sql_expression", "endosso_tem_numero", "warn", expression="qtd_endossos = 0 OR numero_ultimo_endosso IS NOT NULL",
    msg="apolice com endosso sem numero do ultimo endosso", name="endosso_tem_numero")

r = tabela("gold", "dim_corretor")
unica(r, ["corretor_sk"]); unica(r, ["corretor_id"])
nao_nulos(r, ["corretor_sk", "corretor_id", "corretor_nome"])
chk(r, "is_in_range", "comissao_entre_0_e_30_por_cento", column="corretor_comissao_pct", min_limit=0, max_limit=0.30)
chk(r, "is_in_list", "status_corretor_valido", column="corretor_status", allowed=["ATIVO", "INATIVO", "SUSPENSO"])

p = tabela("gold", "dim_ponto_venda")
unica(p, ["ponto_venda_sk"]); unica(p, ["ponto_venda_codigo"])
nao_nulos(p, ["ponto_venda_sk", "ponto_venda_codigo", "ponto_venda_nome"])
chk(p, "is_in_list", "tipo_valido", column="ponto_venda_tipo", allowed=["ESCRITORIO_CORRETOR", "AGENCIA_BANCARIA", "PLATAFORMA_DIGITAL", "CENTRAL_TELEVENDAS"])
chk(p, "is_in_list", "canal_valido", column="canal_venda", allowed=["CORRETOR", "BANCASSURANCE", "DIGITAL", "TELEVENDAS"])
chk(p, "sql_expression", "tipo_coerente_com_canal", "error",
    expression=("(canal_venda = 'CORRETOR' AND ponto_venda_tipo = 'ESCRITORIO_CORRETOR') OR (canal_venda = 'BANCASSURANCE' AND ponto_venda_tipo = 'AGENCIA_BANCARIA') "
                "OR (canal_venda = 'DIGITAL' AND ponto_venda_tipo = 'PLATAFORMA_DIGITAL') OR (canal_venda = 'TELEVENDAS' AND ponto_venda_tipo = 'CENTRAL_TELEVENDAS')"),
    msg="tipo do ponto de venda incompativel com o canal", name="tipo_coerente_com_canal")

pr = tabela("gold", "dim_produto")
unica(pr, ["produto_sk"]); unica(pr, ["produto_codigo"])
nao_nulos(pr, ["produto_sk", "produto_codigo", "produto_nome", "categoria_produto", "cobertura_principal_codigo"])

d = tabela("gold", "dim_data")
unica(d, ["data_sk"]); unica(d, ["data"])
chk(d, "sql_expression", "data_sk_igual_a_data", "error", expression="data_sk = CAST(date_format(data, 'yyyyMMdd') AS INT)",
    msg="data_sk nao corresponde a data", name="data_sk_igual_a_data")

br = tabela("gold", "bridge_apolice_cobertura")
unica(br, ["apolice_sk", "cobertura_sk"])
nao_nulos(br, ["apolice_sk", "cobertura_sk", "papel_cobertura"])
chk(br, "is_in_list", "papel_valido", column="papel_cobertura", allowed=["PRINCIPAL", "ADICIONAL"])
chk(br, "foreign_key", "fk_apolice_sk", columns=["apolice_sk"], ref_columns=["apolice_sk"], ref_table=f"{CAT}.gold.dim_apolice")
chk(br, "foreign_key", "fk_cobertura_sk", columns=["cobertura_sk"], ref_columns=["cobertura_sk"], ref_table=f"{CAT}.gold.dim_cobertura")

# ---- janelas de avaliacao (views pos_venda.dq.v_*_janela, ver carga_diaria/janela_avaliacao.py)
# Mesmas regras da tabela de origem. O agendamento do Studio (escopo: schema pos_venda.dq) avalia essas views
# com TODAS as linhas, so a semana recente, em vez de varrer as tabelas inteiras todo dia.
JANELAS = {
    f"{CAT}.dq.v_bronze_eventos_janela": f"{CAT}.bronze.pagamentos_pendentes_eventos",
    f"{CAT}.dq.v_silver_eventos_aptos_janela": f"{CAT}.silver.pendencia_atual",
    f"{CAT}.dq.v_fato_snapshot_janela": f"{CAT}.gold.fact_pagamento_pendente_snapshot",
}
for _v, _origem in JANELAS.items():
    REGRAS[_v] = [json.loads(json.dumps(c_)) for c_ in REGRAS[_origem]]
# A silver de EVENTOS tem varios eventos por pendencia (NOVA, ATUALIZACAO, BAIXA): a PK da silver atual (pendencia_id)
# nao vale aqui. O grao do evento e (pendencia_id, data_extracao, tipo_evento); repeticao = duplicata da origem (aviso).
_ev = f"{CAT}.dq.v_silver_eventos_aptos_janela"
_camada[_ev] = "silver"
REGRAS[_ev] = [c_ for c_ in REGRAS[_ev] if c_["name"] != "pk_unica_pendencia_id"]
chk(_ev, "is_unique", "evento_unico_por_dia_pendencia_tipo", criticidade="warn",
    columns=["pendencia_id", "data_extracao", "tipo_evento"])


def colunas_citadas(check):
    a = check["check"]["arguments"]
    out = []
    for k in ("column", "columns"):
        v = a.get(k)
        out += ([v] if isinstance(v, str) else v or [])
    return out


if __name__ == "__main__":
    pasta = AQUI / "checks"
    pasta.mkdir(exist_ok=True)
    for f_ in pasta.glob("*.json"):
        f_.unlink()
    problemas = []
    for fq, checks in REGRAS.items():
        info = json.loads(subprocess.check_output(["databricks", "tables", "get", fq, "--profile", PROFILE, "-o", "json"]))
        existentes = {x["name"] for x in info["columns"]}
        for ck in checks:
            for col in colunas_citadas(ck):
                if col not in existentes:
                    problemas.append((fq, ck["name"], col))
        (pasta / f"{fq}.json").write_text(json.dumps(checks, indent=2, ensure_ascii=False), encoding="utf-8")
    total = sum(len(v) for v in REGRAS.values())
    print(f"{len(REGRAS)} tabelas | {total} regras | erro: {sum(1 for v in REGRAS.values() for c_ in v if c_['criticality']=='error')} | warn: {sum(1 for v in REGRAS.values() for c_ in v if c_['criticality']=='warn')}")
    for fq, v in REGRAS.items():
        print(f"  {fq:<62} {len(v):>3} regras")
    print("colunas inexistentes:", problemas or "nenhuma")
