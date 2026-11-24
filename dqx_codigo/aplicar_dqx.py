# Databricks notebook source
# MAGIC %md
# MAGIC # DQX como código: checagens em tabela, sem app
# MAGIC
# MAGIC Aplica as checagens de `checks_pendencias.yml` com a biblioteca **databricks-labs-dqx** e grava três tabelas no
# MAGIC schema de destino:
# MAGIC
# MAGIC | Tabela | Conteúdo |
# MAGIC |---|---|
# MAGIC | `<prefixo>_validos` | linhas sem erro; os avisos ficam na coluna de avisos do DQX |
# MAGIC | `<prefixo>_quarentena` | linhas com ao menos um erro, com o nome de cada regra violada |
# MAGIC | `dq_metricas_regras` | uma linha por execução e regra: linhas avaliadas, reprovadas e taxa (acumula o histórico) |
# MAGIC
# MAGIC Não precisa de app, Lakebase nem service principal. Precisa de: `SELECT` na tabela de entrada, `USE CATALOG` e
# MAGIC `USE SCHEMA` nela, e `CREATE TABLE` + `MODIFY` no schema de destino (veja `README.md`).

# COMMAND ----------

# MAGIC %pip install databricks-labs-dqx==0.17.2 pyyaml

# COMMAND ----------

dbutils.library.restartPython()  # noqa: F821 (dbutils existe no Databricks)

# COMMAND ----------

dbutils.widgets.text("tabela_entrada", "pos_venda.bronze.pagamentos_pendentes_eventos")  # noqa: F821
dbutils.widgets.text("schema_destino", "pos_venda.dqx_codigo")                          # noqa: F821
dbutils.widgets.text("prefixo", "eventos")                                              # noqa: F821
dbutils.widgets.text("arquivo_checks", "checks_pendencias.yml")                         # noqa: F821
dbutils.widgets.text("filtro", "")                                                      # noqa: F821  ex.: data_extracao >= current_date() - 7

ENTRADA = dbutils.widgets.get("tabela_entrada")   # noqa: F821
DESTINO = dbutils.widgets.get("schema_destino")   # noqa: F821
PREFIXO = dbutils.widgets.get("prefixo")          # noqa: F821
ARQUIVO = dbutils.widgets.get("arquivo_checks")   # noqa: F821
FILTRO = dbutils.widgets.get("filtro").strip()    # noqa: F821

# COMMAND ----------

import os
import uuid
from datetime import datetime, timezone

import yaml
from databricks.labs.dqx.engine import DQEngine
from databricks.sdk import WorkspaceClient
from pyspark.sql import functions as F

# o YAML fica ao lado deste notebook (Workspace Files, Repos ou bundle)
caminho = ARQUIVO if ARQUIVO.startswith("/") else os.path.join(os.getcwd(), ARQUIVO)
with open(caminho, encoding="utf-8") as f:
    checks = yaml.safe_load(f)

dq_engine = DQEngine(WorkspaceClient())
validacao = DQEngine.validate_checks(checks)
if validacao.has_errors:
    raise ValueError(f"checagens inválidas: {validacao.errors}")
print(f"{len(checks)} checagens carregadas de {caminho}")

# COMMAND ----------

df = spark.table(ENTRADA)  # noqa: F821 (spark existe no Databricks)
if FILTRO:
    df = df.where(FILTRO)

avaliado = dq_engine.apply_checks_by_metadata(df, checks)

# Nomes das colunas de resultado: o padrão documentado é _errors e _warnings; confira no primeiro uso.
COL_ERRO = next(c for c in ("_errors", "_error") if c in avaliado.columns)
COL_AVISO = next(c for c in ("_warnings", "_warning") if c in avaliado.columns)
tem_erro = F.coalesce(F.size(F.col(COL_ERRO)), F.lit(0)) > 0

validos = avaliado.where(~tem_erro).drop(COL_ERRO)   # aviso entra marcado (coluna de avisos)
quarentena = avaliado.where(tem_erro)                # erro fica de fora, com o motivo

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {DESTINO}")  # noqa: F821  (pule se o schema já existe e você não pode criar)
validos.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{DESTINO}.{PREFIXO}_validos")
quarentena.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{DESTINO}.{PREFIXO}_quarentena")

# COMMAND ----------

# Métricas por regra: base do painel de qualidade e do plano de ação (cada regra com dono e critério de pronto)
execucao, agora = str(uuid.uuid4()), datetime.now(timezone.utc)
total = avaliado.count()
def nomes_violados(coluna):  # explode ignora nulo e lista vazia
    return avaliado.select(F.explode(F.col(coluna)).alias("r")).select(F.col("r.name").alias("regra"))


por_regra = nomes_violados(COL_ERRO).unionByName(nomes_violados(COL_AVISO)).groupBy("regra").agg(
    F.count("*").alias("reprovadas"))
nomes = spark.createDataFrame(  # noqa: F821  regras sem reprovação também aparecem, com zero
    [(c.get("name"), c.get("criticality", "error")) for c in checks], "regra string, criticidade string")
metricas = (
    nomes.join(por_regra, "regra", "left")
    .select(F.lit(execucao).alias("execucao_id"), F.lit(agora).alias("executado_em"), F.lit(ENTRADA).alias("tabela"),
            "regra", "criticidade", F.lit(total).alias("linhas_avaliadas"),
            F.coalesce("reprovadas", F.lit(0)).alias("reprovadas"))
    .withColumn("taxa", F.when(F.col("linhas_avaliadas") > 0, F.col("reprovadas") / F.col("linhas_avaliadas")))
)
metricas.write.mode("append").saveAsTable(f"{DESTINO}.dq_metricas_regras")
display(metricas.orderBy(F.desc("reprovadas")))  # noqa: F821
