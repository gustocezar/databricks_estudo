#!/usr/bin/env python3
"""Gera o SQL do medalhão pos_venda (bronze -> silver -> gold/star schema) nas DUAS abordagens:

  * notebooks SQL   -> src/notebooks_sql/0N_<camada>_sql.sql   (CREATE OR REPLACE TABLE, roda num Job)
  * pipeline Lakeflow -> src/ldp/transformations/<camada>_<dataset>.sql (CREATE OR REFRESH MATERIALIZED VIEW)

A lógica (os SELECTs) é definida uma única vez aqui, então as duas versões produzem o mesmo resultado.
Cada abordagem grava em schemas próprios (*_sql e *_ldp), para não disputar a posse das tabelas.

Uso:  python3 gerar_sql.py            (lê as colunas da one-table no Unity Catalog via CLI)
"""
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
CAT = "pos_venda"
ONE_TABLE = f"{CAT}.landing.pagamentos_pendentes_one_table"
PROFILE = "dbx-workshop"

# ------------------------------------------------------------------ colunas da one-table (fonte da verdade = UC)
_raw = subprocess.check_output(["databricks", "tables", "get", ONE_TABLE, "--profile", PROFILE, "-o", "json"])
COLS = [c["name"] for c in json.loads(_raw)["columns"]]
assert "pendencia_id" in COLS and len(COLS) >= 91, COLS


def lista(cols, ind="  "):
    return (",\n" + ind).join(cols)


# ------------------------------------------------------------------ CPF válido (dígitos verificadores)
def cpf_valido(c):
    d1 = (f"((aggregate(zip_with(transform(sequence(1, 9), i -> CAST(substring({c}, i, 1) AS INT)), "
          f"sequence(10, 2, -1), (digito, peso) -> digito * peso), 0, (acc, val) -> acc + val) * 10) % 11) % 10 "
          f"= CAST(substring({c}, 10, 1) AS INT)")
    d2 = (f"((aggregate(zip_with(transform(sequence(1, 10), i -> CAST(substring({c}, i, 1) AS INT)), "
          f"sequence(11, 2, -1), (digito, peso) -> digito * peso), 0, (acc, val) -> acc + val) * 10) % 11) % 10 "
          f"= CAST(substring({c}, 11, 1) AS INT)")
    return f"CASE WHEN length({c}) = 11 AND {d1} AND {d2} THEN true ELSE false END"


# ------------------------------------------------------------------ definição dos datasets
# Placeholders: @B@ @S@ @G@ = schema qualificado (catalogo.bronze_xx / silver_xx / gold_xx); @DROP@ = WHERE dos drop-rows
DATASETS = []


def ds(layer, name, comment, body, constraints=(), drop_where=None):
    DATASETS.append(dict(layer=layer, name=name, comment=comment, body=body.strip("\n"),
                         constraints=list(constraints), drop_where=drop_where))


# ---- BRONZE: cópia fiel + metadados de ingestão
bronze_cols = lista([f"o.{c}" for c in COLS])
ds("bronze", "pagamentos_pendentes",
   "Bronze: copia fiel da one-table de pagamentos pendentes (seguro de vida) com metadados de ingestao.",
   f"""
SELECT
  {bronze_cols},
  current_timestamp() AS _ingestao_ts,
  date_format(current_timestamp(), 'yyyyMMddHHmmss') AS _lote_id,
  '{ONE_TABLE}' AS _origem,
  xxhash64({lista([f"o.{c}" for c in COLS], "    ")}) AS _hash_linha
FROM {ONE_TABLE} o""",
   constraints=[("pendencia_id_nao_nulo", "pendencia_id IS NOT NULL", "")])

# ---- SILVER: deduplicada, padronizada e com flags de qualidade
OVERRIDES = {
    "cliente_cpf": "_cpf_dig",
    "cliente_rg": "upper(regexp_replace(cliente_rg, '[^0-9Xx]', ''))",
    "cliente_celular": "regexp_replace(cliente_celular, '[^0-9]', '')",
    "cliente_telefone_fixo": "regexp_replace(cliente_telefone_fixo, '[^0-9]', '')",
    "cliente_cep": "regexp_replace(cliente_cep, '[^0-9]', '')",
    "cliente_uf": "upper(cliente_uf)",
    "cliente_email": "lower(trim(cliente_email))",
}
silver_sel = lista([f"{OVERRIDES[c]} AS {c}" if c in OVERRIDES else c for c in COLS])
ds("silver", "pagamento_pendente",
   "Silver: 1 linha por pendencia_id, sem duplicatas, com CPF/RG/telefone/CEP/UF padronizados e flags de qualidade (dq_*).",
   f"""
WITH base AS (
  SELECT * FROM @B@.pagamentos_pendentes
  QUALIFY row_number() OVER (PARTITION BY pendencia_id ORDER BY _ingestao_ts, _hash_linha) = 1
),
dig AS (
  SELECT b.*, regexp_replace(b.cliente_cpf, '[^0-9]', '') AS _cpf_dig FROM base b
),
norm AS (
  SELECT d.*, {cpf_valido('d._cpf_dig')} AS _cpf_valido FROM dig d
)
SELECT
  {silver_sel},
  NOT _cpf_valido AS dq_cpf_invalido,
  cliente_rg IS NULL AS dq_rg_ausente,
  cliente_celular IS NULL AS dq_celular_ausente,
  cliente_email IS NULL AS dq_email_ausente,
  (cliente_email IS NOT NULL AND NOT (lower(trim(cliente_email)) RLIKE '^[^@ ]+@[^@ ]+[.][^@ ]+$')) AS dq_email_invalido,
  CAST(NOT _cpf_valido AS INT) + CAST(cliente_rg IS NULL AS INT) + CAST(cliente_celular IS NULL AS INT)
    + CAST(cliente_email IS NULL AS INT) AS dq_qtd_problemas,
  _ingestao_ts,
  _lote_id,
  _hash_linha,
  current_timestamp() AS _silver_ts
FROM norm
@DROP@""",
   constraints=[
       ("pendencia_id_obrigatorio", "pendencia_id IS NOT NULL", "ON VIOLATION DROP ROW"),
       ("valor_total_positivo", "valor_total_pendente > 0", "ON VIOLATION DROP ROW"),
       ("vencimento_ate_extracao", "data_vencimento <= data_extracao", "ON VIOLATION DROP ROW"),
       ("cpf_valido", "NOT dq_cpf_invalido", ""),
       ("email_valido", "NOT dq_email_invalido", ""),
   ],
   drop_where="WHERE pendencia_id IS NOT NULL AND valor_total_pendente > 0 AND data_vencimento <= data_extracao")

# ---- GOLD: star schema ---------------------------------------------------------------------------------------
def um_por(chave, ordem="data_vencimento DESC, pendencia_id"):
    return f"QUALIFY row_number() OVER (PARTITION BY {chave} ORDER BY {ordem}) = 1"


ds("gold", "dim_cliente", "Dimensao cliente (dados cadastrais padronizados). Chave substituta: xxhash64(cliente_id).", f"""
SELECT
  xxhash64(cliente_id) AS cliente_sk,
  cliente_id, cliente_nome, cliente_cpf, NOT dq_cpf_invalido AS cliente_cpf_valido,
  cliente_rg, cliente_rg_orgao_emissor, cliente_rg_uf_emissor, cliente_rg_data_emissao,
  cliente_data_nascimento, cliente_idade,
  CASE WHEN cliente_idade < 30 THEN '18-29' WHEN cliente_idade < 40 THEN '30-39' WHEN cliente_idade < 50 THEN '40-49'
       WHEN cliente_idade < 60 THEN '50-59' ELSE '60+' END AS cliente_faixa_etaria,
  cliente_sexo, cliente_estado_civil, cliente_profissao, cliente_renda_faixa, cliente_fumante,
  cliente_email, cliente_celular, cliente_telefone_fixo,
  cliente_logradouro, cliente_numero, cliente_complemento, cliente_bairro, cliente_cidade, cliente_uf, cliente_cep,
  cliente_endereco_completo, cliente_data_cadastro
FROM @S@.pagamento_pendente
{um_por('cliente_id')}""")

ds("gold", "dim_apolice", "Dimensao apolice de vida (vigencia, capital, premio, endossos e beneficiarios).", f"""
SELECT
  xxhash64(numero_apolice) AS apolice_sk,
  numero_apolice, status_apolice, data_emissao, data_inicio_vigencia, data_fim_vigencia_atual, dia_vencimento,
  capital_segurado_principal, capital_segurado_total, valor_premio_periodico,
  possui_ipta, possui_ifpd, possui_doencas_graves, possui_dit, possui_assistencia_funeral, qtd_coberturas,
  qtd_endossos, numero_ultimo_endosso, tipo_ultimo_endosso, data_ultimo_endosso,
  qtd_beneficiarios, parentesco_beneficiario_principal
FROM @S@.pagamento_pendente
{um_por('numero_apolice')}""")

ds("gold", "dim_produto", "Dimensao produto de seguro de vida.", f"""
SELECT
  xxhash64(produto_codigo) AS produto_sk,
  produto_codigo, produto_nome, categoria_produto, ramo, cobertura_principal_codigo, cobertura_principal_nome
FROM @S@.pagamento_pendente
{um_por('produto_codigo')}""")

ds("gold", "dim_cobertura", "Dimensao cobertura (catalogo de coberturas de vida).", """
SELECT xxhash64(cobertura_codigo) AS cobertura_sk, cobertura_codigo, cobertura_nome, grupo_cobertura
FROM VALUES
  ('MORTE', 'Morte (natural ou acidental)', 'MORTE'),
  ('IPTA', 'Invalidez Permanente Total por Acidente', 'INVALIDEZ'),
  ('IFPD', 'Invalidez Funcional Permanente Total por Doenca', 'INVALIDEZ'),
  ('DGR', 'Doencas Graves', 'DOENCAS_GRAVES'),
  ('DIT', 'Diaria por Incapacidade Temporaria', 'INCAPACIDADE_TEMPORARIA'),
  ('AFU', 'Assistencia Funeral', 'ASSISTENCIA')
  AS t(cobertura_codigo, cobertura_nome, grupo_cobertura)""")

ds("gold", "bridge_apolice_cobertura", "Ponte N:N entre apolice e cobertura, com papel (principal/adicional) e capital da cobertura.", f"""
WITH ap AS (
  SELECT numero_apolice, cobertura_principal_codigo, capital_segurado_principal,
         possui_ipta, possui_ifpd, possui_doencas_graves, possui_dit, possui_assistencia_funeral
  FROM @S@.pagamento_pendente
  {um_por('numero_apolice')}
)
SELECT xxhash64(numero_apolice) AS apolice_sk, xxhash64(cobertura_principal_codigo) AS cobertura_sk,
       'PRINCIPAL' AS papel_cobertura, CAST(capital_segurado_principal AS DECIMAL(14,2)) AS capital_segurado_cobertura
FROM ap
UNION ALL
SELECT xxhash64(numero_apolice), xxhash64('IPTA'), 'ADICIONAL', CAST(capital_segurado_principal * 1.0 AS DECIMAL(14,2)) FROM ap WHERE possui_ipta
UNION ALL
SELECT xxhash64(numero_apolice), xxhash64('IFPD'), 'ADICIONAL', CAST(capital_segurado_principal * 0.5 AS DECIMAL(14,2)) FROM ap WHERE possui_ifpd
UNION ALL
SELECT xxhash64(numero_apolice), xxhash64('DGR'), 'ADICIONAL', CAST(capital_segurado_principal * 0.3 AS DECIMAL(14,2)) FROM ap WHERE possui_doencas_graves
UNION ALL
SELECT xxhash64(numero_apolice), xxhash64('DIT'), 'ADICIONAL', CAST(NULL AS DECIMAL(14,2)) FROM ap WHERE possui_dit
UNION ALL
SELECT xxhash64(numero_apolice), xxhash64('AFU'), 'ADICIONAL', CAST(NULL AS DECIMAL(14,2)) FROM ap WHERE possui_assistencia_funeral""")

ds("gold", "dim_corretor", "Dimensao corretor, com membro NAO_INFORMADO para vendas sem corretor (canais digital e televendas).", f"""
SELECT * FROM (
  SELECT
    xxhash64(corretor_id) AS corretor_sk,
    corretor_id, corretor_nome, corretor_tipo_pessoa, corretor_documento, corretor_registro_susep,
    corretor_regional, corretor_comissao_pct, corretor_status, corretor_data_credenciamento
  FROM @S@.pagamento_pendente
  WHERE corretor_id IS NOT NULL
  {um_por('corretor_id')}
)
UNION ALL
SELECT xxhash64('NAO_INFORMADO'), 'NAO_INFORMADO', 'Venda sem corretor', CAST(NULL AS STRING), CAST(NULL AS STRING),
       CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS DECIMAL(5,2)), CAST(NULL AS STRING), CAST(NULL AS DATE)""")

ds("gold", "dim_ponto_venda", "Dimensao ponto de venda (escritorio de corretor, agencia bancaria, plataforma digital, televendas).", f"""
SELECT
  xxhash64(ponto_venda_codigo) AS ponto_venda_sk,
  ponto_venda_codigo, ponto_venda_nome, ponto_venda_tipo, canal_venda,
  ponto_venda_cidade, ponto_venda_uf, ponto_venda_regional
FROM @S@.pagamento_pendente
{um_por('ponto_venda_codigo')}""")

ds("gold", "dim_periodicidade", "Dimensao periodicidade de pagamento do premio.", f"""
SELECT xxhash64(periodicidade_pagamento) AS periodicidade_sk, periodicidade_pagamento, meses_periodicidade,
       CAST(12 / meses_periodicidade AS INT) AS parcelas_por_ano
FROM @S@.pagamento_pendente
{um_por('periodicidade_pagamento')}""")

ds("gold", "dim_forma_pagamento", "Dimensao forma de pagamento.", f"""
SELECT xxhash64(forma_pagamento) AS forma_pagamento_sk, forma_pagamento,
       CASE forma_pagamento WHEN 'DEBITO_CONTA' THEN 'AUTOMATICO' WHEN 'PIX_AUTOMATICO' THEN 'AUTOMATICO'
            WHEN 'CARTAO_CREDITO' THEN 'CARTAO' ELSE 'BOLETO' END AS grupo_forma_pagamento
FROM @S@.pagamento_pendente
{um_por('forma_pagamento')}""")

ds("gold", "dim_status_cobranca", "Dimensao status de cobranca, com a fase da regua de cobranca.", f"""
SELECT xxhash64(status_cobranca) AS status_cobranca_sk, status_cobranca,
       CASE status_cobranca WHEN 'PENDENTE' THEN 'INICIAL' WHEN 'EM_COBRANCA' THEN 'INTERNA'
            WHEN 'PROMESSA_PAGAMENTO' THEN 'NEGOCIACAO' WHEN 'NEGOCIADO' THEN 'NEGOCIACAO' ELSE 'EXTERNA' END AS fase_cobranca,
       CASE status_cobranca WHEN 'PENDENTE' THEN 1 WHEN 'EM_COBRANCA' THEN 2 WHEN 'PROMESSA_PAGAMENTO' THEN 3
            WHEN 'NEGOCIADO' THEN 4 ELSE 5 END AS ordem_fase
FROM @S@.pagamento_pendente
{um_por('status_cobranca')}""")

ds("gold", "dim_motivo_pendencia", "Dimensao motivo da pendencia de pagamento, com agrupamento.", f"""
SELECT xxhash64(motivo_pendencia) AS motivo_pendencia_sk, motivo_pendencia,
       CASE WHEN motivo_pendencia IN ('SALDO_INSUFICIENTE', 'LIMITE_INSUFICIENTE', 'CARTAO_RECUSADO', 'BOLETO_NAO_PAGO') THEN 'FINANCEIRO'
            WHEN motivo_pendencia IN ('DADOS_BANCARIOS_INVALIDOS', 'CONTA_ENCERRADA', 'CARTAO_EXPIRADO') THEN 'CADASTRAL'
            WHEN motivo_pendencia IN ('AUTORIZACAO_DEBITO_CANCELADA', 'AUTORIZACAO_PIX_REVOGADA') THEN 'AUTORIZACAO'
            ELSE 'OPERACIONAL' END AS grupo_motivo
FROM @S@.pagamento_pendente
{um_por('motivo_pendencia')}""")

ds("gold", "dim_faixa_atraso", "Dimensao faixa de atraso (catalogo fixo, ordenado).", """
SELECT xxhash64(faixa_atraso) AS faixa_atraso_sk, faixa_atraso, descricao_faixa, dias_min, dias_max, ordem_faixa
FROM VALUES
  ('00_VENCE_HOJE', 'Vence hoje', 0, 0, 0),
  ('01_1_A_15', '1 a 15 dias', 1, 15, 1),
  ('02_16_A_30', '16 a 30 dias', 16, 30, 2),
  ('03_31_A_60', '31 a 60 dias', 31, 60, 3),
  ('04_61_A_90', '61 a 90 dias', 61, 90, 4),
  ('05_91_A_120', '91 a 120 dias', 91, 120, 5),
  ('06_ACIMA_120', 'Acima de 120 dias', 121, CAST(NULL AS INT), 6)
  AS t(faixa_atraso, descricao_faixa, dias_min, dias_max, ordem_faixa)""")

ds("gold", "dim_data", "Dimensao data (calendario 2015-2030) usada nos papeis: vencimento, emissao, extracao, ultima tentativa.", """
SELECT
  CAST(date_format(d, 'yyyyMMdd') AS INT) AS data_sk,
  d AS data,
  year(d) AS ano,
  CASE WHEN month(d) <= 6 THEN 1 ELSE 2 END AS semestre,
  quarter(d) AS trimestre,
  month(d) AS mes,
  element_at(array('Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro',
                   'Outubro', 'Novembro', 'Dezembro'), month(d)) AS nome_mes,
  date_format(d, 'yyyy-MM') AS ano_mes,
  day(d) AS dia,
  ((dayofweek(d) + 5) % 7) + 1 AS dia_semana,
  element_at(array('Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'),
             ((dayofweek(d) + 5) % 7) + 1) AS nome_dia_semana,
  weekofyear(d) AS semana_ano,
  dayofweek(d) IN (1, 7) AS fim_de_semana,
  d = last_day(d) AS ultimo_dia_mes
FROM (SELECT explode(sequence(DATE'2015-01-01', DATE'2030-12-31', INTERVAL 1 DAY)) AS d)""")


def dsk(col):
    return f"CAST(date_format({col}, 'yyyyMMdd') AS INT)"


ds("gold", "fact_pagamento_pendente",
   "Fato: 1 linha por parcela de apolice pendente de pagamento (foto na data de extracao). Medidas: valores, dias de atraso, tentativas.",
   f"""
SELECT
  pendencia_id,
  numero_apolice,
  numero_parcela,
  xxhash64(cliente_id) AS cliente_sk,
  xxhash64(numero_apolice) AS apolice_sk,
  xxhash64(produto_codigo) AS produto_sk,
  xxhash64(coalesce(corretor_id, 'NAO_INFORMADO')) AS corretor_sk,
  xxhash64(ponto_venda_codigo) AS ponto_venda_sk,
  xxhash64(periodicidade_pagamento) AS periodicidade_sk,
  xxhash64(forma_pagamento) AS forma_pagamento_sk,
  xxhash64(status_cobranca) AS status_cobranca_sk,
  xxhash64(motivo_pendencia) AS motivo_pendencia_sk,
  xxhash64(faixa_atraso) AS faixa_atraso_sk,
  {dsk('data_vencimento')} AS data_vencimento_sk,
  {dsk('data_emissao')} AS data_emissao_apolice_sk,
  {dsk('data_geracao_cobranca')} AS data_geracao_cobranca_sk,
  {dsk('data_ultima_tentativa')} AS data_ultima_tentativa_sk,
  {dsk('data_extracao')} AS data_extracao_sk,
  canal_ultimo_contato,
  parcela_afetada_por_endosso,
  1 AS qtd_parcelas_pendentes,
  valor_parcela,
  valor_multa,
  valor_juros,
  valor_total_pendente,
  dias_atraso,
  tentativas_cobranca
FROM @S@.pagamento_pendente""",
   constraints=[("valor_total_positivo", "valor_total_pendente > 0", ""),
                ("cliente_sk_nao_nulo", "cliente_sk IS NOT NULL", "")])

# ------------------------------------------------------------------ emissão dos arquivos
SCHEMAS = {"sql": {"bronze": f"{CAT}.bronze_sql", "silver": f"{CAT}.silver_sql", "gold": f"{CAT}.gold_sql"},
           "ldp": {"bronze": f"{CAT}.bronze_ldp", "silver": f"{CAT}.silver_ldp", "gold": f"{CAT}.gold_ldp"}}


def resolve(body, variante, d):
    s = SCHEMAS[variante]
    drop = d["drop_where"] if (variante == "sql" and d["drop_where"]) else ""
    return (body.replace("@B@", s["bronze"]).replace("@S@", s["silver"]).replace("@G@", s["gold"]).replace("@DROP@", drop))


def esc(txt):
    return txt.replace("'", "''")


nb_dir = ROOT / "src" / "notebooks_sql"
ldp_dir = ROOT / "src" / "ldp" / "transformations"
for p in (nb_dir, ldp_dir):
    p.mkdir(parents=True, exist_ok=True)
    for f in p.glob("*.sql"):
        f.unlink()

# --- notebooks SQL (1 por camada)
ORDEM = {"bronze": 1, "silver": 2, "gold": 3}
for layer in ("bronze", "silver", "gold"):
    s = SCHEMAS["sql"][layer]
    cells = [f"-- Databricks notebook source\n-- MAGIC %md\n-- MAGIC # pos_venda · medalhão (notebooks SQL) · {layer.upper()}\n"
             f"-- MAGIC Gerado por `gerar_sql.py`. Cada tabela e recriada a cada execucao (`CREATE OR REPLACE TABLE`).\n"
             f"-- MAGIC Destino: `{s}`.\n",
             f"-- COMMAND ----------\n\nCREATE SCHEMA IF NOT EXISTS {s} COMMENT 'pos_venda {layer} (abordagem notebooks SQL)';\n"]
    for d in [x for x in DATASETS if x["layer"] == layer]:
        body = resolve(d["body"], "sql", d)
        cells.append(f"-- COMMAND ----------\n\nCREATE OR REPLACE TABLE {s}.{d['name']}\nCOMMENT '{esc(d['comment'])}'\nAS\n{body};\n")
    cells.append(f"-- COMMAND ----------\n\n-- Conferencia: contagem das tabelas desta camada\n"
                 + "\nUNION ALL\n".join(f"SELECT '{d['name']}' AS tabela, count(*) AS linhas FROM {s}.{d['name']}"
                                         for d in DATASETS if d["layer"] == layer) + ";\n")
    (nb_dir / f"0{ORDEM[layer]}_{layer}_sql.sql").write_text("\n".join(cells), encoding="utf-8")

# --- pipeline Lakeflow (1 arquivo por dataset)
for d in DATASETS:
    s = SCHEMAS["ldp"][d["layer"]]
    cons = ""
    if d["constraints"]:
        cons = " (\n  " + ",\n  ".join(f"CONSTRAINT {n} EXPECT ({c}){(' ' + a) if a else ''}" for n, c, a in d["constraints"]) + "\n)"
    body = resolve(d["body"], "ldp", d)
    sql = (f"-- Gerado por gerar_sql.py | pipeline Lakeflow | {d['layer']}.{d['name']}\n"
           f"CREATE OR REFRESH MATERIALIZED VIEW {s}.{d['name']}{cons}\nCOMMENT '{esc(d['comment'])}'\nAS\n{body};\n")
    (ldp_dir / f"{d['layer']}_{d['name']}.sql").write_text(sql, encoding="utf-8")

manifest = {"colunas_one_table": len(COLS),
            "datasets": [{"layer": d["layer"], "name": d["name"]} for d in DATASETS]}
(ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"ok: {len(DATASETS)} datasets | notebooks: {sorted(p.name for p in nb_dir.glob('*.sql'))} | arquivos do pipeline: {len(list(ldp_dir.glob('*.sql')))}")
