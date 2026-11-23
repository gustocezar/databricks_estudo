# Databricks notebook source
# MAGIC %md
# MAGIC # pos_venda · 30 · Gold · fato histórica (snapshot diário)
# MAGIC **Grão:** 1 linha por pendência **em aberto** por dia (`PK = pendencia_id + data_referencia_sk`).
# MAGIC A foto de cada dia vem da `silver.pendencia_hist` (SCD2): vale a versão da pendência vigente naquele dia.
# MAGIC Dias de atraso, multa, juros, faixa e tentativas são recalculados **as-of** o dia da foto; faixa, multa, juros e
# MAGIC total vêm das funções `pos_venda.regras.*` (as mesmas testadas pelo portão `05_portao_regras`).
# MAGIC Idempotente: apaga e regrava só os dias do intervalo. A tabela é agrupada (liquid clustering) por `data_referencia_sk`.

# COMMAND ----------

import json

dbutils.widgets.text("data_inicio", "2026-11-18")
dbutils.widgets.text("data_fim", "2026-11-18")
INI = dbutils.widgets.get("data_inicio").strip()
FIM = dbutils.widgets.get("data_fim").strip()
INI_SK, FIM_SK = int(INI.replace("-", "")), int(FIM.replace("-", ""))

CAT = "pos_venda"
SEED = 20261118
HIST = f"{CAT}.silver.pendencia_hist"
FACT = f"{CAT}.gold.fact_pagamento_pendente_snapshot"

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {FACT} (
  data_referencia_sk INT NOT NULL COMMENT 'Dia da foto (yyyyMMdd)',
  pendencia_id STRING NOT NULL,
  numero_apolice STRING, numero_parcela INT,
  cliente_sk BIGINT, apolice_sk BIGINT, produto_sk BIGINT, corretor_sk BIGINT, ponto_venda_sk BIGINT,
  periodicidade_sk BIGINT, forma_pagamento_sk BIGINT, status_cobranca_sk BIGINT, motivo_pendencia_sk BIGINT, faixa_atraso_sk BIGINT,
  data_vencimento_sk INT, data_emissao_apolice_sk INT, data_entrada_pendencia_sk INT, data_ultima_tentativa_sk INT,
  canal_ultimo_contato STRING, parcela_afetada_por_endosso BOOLEAN,
  qtd_pendencias INT, valor_parcela DECIMAL(14,2), valor_multa DECIMAL(14,2), valor_juros DECIMAL(14,2),
  valor_total_pendente DECIMAL(14,2), dias_atraso INT, tentativas_cobranca INT,
  _carga_ts TIMESTAMP,
  CONSTRAINT pk_fact_pagamento_pendente_snapshot PRIMARY KEY (data_referencia_sk, pendencia_id) RELY
)
CLUSTER BY (data_referencia_sk)
COMMENT 'Fato historica (snapshot diario): pendencias de pagamento em aberto por dia. Grao: pendencia x dia.'
""")

spark.sql(f"DELETE FROM {FACT} WHERE data_referencia_sk BETWEEN {INI_SK} AND {FIM_SK}")
REGRAS = f"{CAT}.regras"   # faixa, multa, juros e total vêm das funções de regra (contrato: pos_venda/regras/features)

def dsk(c):
    return f"CAST(date_format({c}, 'yyyyMMdd') AS INT)"

spark.sql(f"""
INSERT INTO {FACT}
WITH v AS (
  SELECT h.*,
         greatest(h.__START_AT, DATE'{INI}') AS _d_ini,
         least(date_sub(coalesce(h.__END_AT, date_add(DATE'{FIM}', 1)), 1), DATE'{FIM}') AS _d_fim
  FROM {HIST} h
  WHERE h.status_cobranca <> 'PAGA'
),
s AS (SELECT v.*, explode(sequence(_d_ini, _d_fim)) AS _d FROM v WHERE _d_ini <= _d_fim),
c AS (SELECT s.*, datediff(_d, data_vencimento) AS _x FROM s)
SELECT
  {dsk('_d')} AS data_referencia_sk,
  pendencia_id, numero_apolice, CAST(numero_parcela AS INT) AS numero_parcela,
  xxhash64(cliente_id) AS cliente_sk,
  xxhash64(numero_apolice) AS apolice_sk,
  xxhash64(produto_codigo) AS produto_sk,
  xxhash64(coalesce(corretor_id, 'NAO_INFORMADO')) AS corretor_sk,
  xxhash64(ponto_venda_codigo) AS ponto_venda_sk,
  xxhash64(periodicidade_pagamento) AS periodicidade_sk,
  xxhash64(forma_pagamento) AS forma_pagamento_sk,
  xxhash64(status_cobranca) AS status_cobranca_sk,
  xxhash64(motivo_pendencia) AS motivo_pendencia_sk,
  xxhash64({REGRAS}.faixa_atraso(CAST(_x AS INT))) AS faixa_atraso_sk,
  {dsk('data_vencimento')} AS data_vencimento_sk,
  {dsk('data_emissao')} AS data_emissao_apolice_sk,
  {dsk('date_add(data_vencimento, 1)')} AS data_entrada_pendencia_sk,
  {dsk('date_add(data_vencimento, CAST(floor((pmod(xxhash64(numero_apolice, numero_parcela, ' + str(SEED + 209) + '), 1000000) / 1000000.0) * _x) AS INT))')} AS data_ultima_tentativa_sk,
  canal_ultimo_contato,
  parcela_afetada_por_endosso,
  1 AS qtd_pendencias,
  CAST(valor_parcela AS DECIMAL(14,2)) AS valor_parcela,
  {REGRAS}.valor_multa(CAST(valor_parcela AS DECIMAL(14,2))) AS valor_multa,
  {REGRAS}.valor_juros(CAST(valor_parcela AS DECIMAL(14,2)), CAST(_x AS INT)) AS valor_juros,
  {REGRAS}.valor_total_pendente(CAST(valor_parcela AS DECIMAL(14,2)), CAST(_x AS INT)) AS valor_total_pendente,
  CAST(_x AS INT) AS dias_atraso,
  CAST(least(10, 1 + floor(_x / 10) + CASE WHEN status_cobranca = 'PENDENTE' THEN 0 ELSE 1 END) AS INT) AS tentativas_cobranca,
  current_timestamp() AS _carga_ts
FROM c
""")

# chaves estrangeiras (informativas) para as dimensoes; criadas uma vez e SEM RELY: a de forma de pagamento tem orfas de
# proposito (NAO_CADASTRADA), e RELY numa estrangeira deixaria o otimizador trocar LEFT JOIN por INNER JOIN
FKS = [("cliente_sk", "dim_cliente", "cliente_sk"), ("apolice_sk", "dim_apolice", "apolice_sk"), ("produto_sk", "dim_produto", "produto_sk"),
       ("corretor_sk", "dim_corretor", "corretor_sk"), ("ponto_venda_sk", "dim_ponto_venda", "ponto_venda_sk"),
       ("periodicidade_sk", "dim_periodicidade", "periodicidade_sk"), ("forma_pagamento_sk", "dim_forma_pagamento", "forma_pagamento_sk"),
       ("status_cobranca_sk", "dim_status_cobranca", "status_cobranca_sk"), ("motivo_pendencia_sk", "dim_motivo_pendencia", "motivo_pendencia_sk"),
       ("faixa_atraso_sk", "dim_faixa_atraso", "faixa_atraso_sk"), ("data_referencia_sk", "dim_data", "data_sk"),
       ("data_vencimento_sk", "dim_data", "data_sk"), ("data_emissao_apolice_sk", "dim_data", "data_sk"),
       ("data_entrada_pendencia_sk", "dim_data", "data_sk"), ("data_ultima_tentativa_sk", "dim_data", "data_sk")]
fk_status = {}
for col, dim, dcol in FKS:
    nome = f"fk_fact_{col}"
    try:
        spark.sql(f"ALTER TABLE {FACT} ADD CONSTRAINT {nome} FOREIGN KEY ({col}) REFERENCES {CAT}.gold.{dim}({dcol})")
        fk_status[nome] = "criada"
    except Exception as e:
        msg = str(e)
        fk_status[nome] = "ja existia" if ("already exists" in msg or "ALREADY_EXISTS" in msg) else "ERRO: " + msg[:160]

n = spark.sql(f"SELECT count(*) AS n, count(DISTINCT data_referencia_sk) AS dias FROM {FACT} WHERE data_referencia_sk BETWEEN {INI_SK} AND {FIM_SK}").first()
dbutils.notebook.exit(json.dumps({"intervalo": [INI, FIM], "linhas_no_intervalo": n["n"], "dias": n["dias"], "fks": fk_status}))
