# Databricks notebook source
# MAGIC %md
# MAGIC # Sonda diária da conformidade
# MAGIC
# MAGIC Faz no job o mesmo que `python3 conformidade/gerar_conformidade.py registrar` faz na máquina (P35, P37):
# MAGIC
# MAGIC 1. testa cada view, metric view e materialized view do workspace com `DESCRIBE QUERY`, que analisa a view sem
# MAGIC    executá-la, e grava o resultado em `pos_venda.conformidade.sonda_views` (regra USO03);
# MAGIC 2. grava a foto do dia de `boas_praticas_dados` em `pos_venda.conformidade.historico`, uma linha por regra.
# MAGIC
# MAGIC O script local roda o SQL pelo CLI, que não existe dentro do job; aqui o mesmo SQL roda com `spark.sql`.
# MAGIC Se mudar a sonda, mude também `cmd_registrar` em `gerar_conformidade.py`. As visões e as regras continuam
# MAGIC sendo criadas pelo `aplicar` local, e os alertas e as políticas de tag são a foto do último `aplicar`.

# COMMAND ----------

import concurrent.futures as cf
import datetime

S = "pos_venda.conformidade"
EXCLUIDOS = ("system", "samples", "__databricks_internal")   # o mesmo de gerar_conformidade.py
excluidos_sql = ", ".join(f"'{c}'" for c in EXCLUIDOS)

agora = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None, microsecond=0)
views = spark.sql(f"""
SELECT table_catalog, table_schema, table_name, table_type FROM system.information_schema.tables
WHERE table_type IN ('VIEW', 'METRIC_VIEW', 'MATERIALIZED_VIEW') AND table_catalog NOT IN ({excluidos_sql})
  AND table_schema <> 'information_schema'""").collect()
if not views:
    raise RuntimeError("nenhuma view para sondar: confira o acesso ao information_schema")


def sondar(v):
    nome = f"`{v.table_catalog}`.`{v.table_schema}`.`{v.table_name}`"
    try:
        spark.sql(f"DESCRIBE QUERY /* sonda-conformidade */ SELECT * FROM {nome}").collect()
        return (agora, v.table_catalog, v.table_schema, v.table_name, v.table_type, True, None)
    except Exception as e:  # noqa: BLE001 - a sonda registra qualquer erro da view
        return (agora, v.table_catalog, v.table_schema, v.table_name, v.table_type, False, str(e)[:500])


with cf.ThreadPoolExecutor(4) as ex:
    linhas = list(ex.map(sondar, views))

esquema = "sondado_em TIMESTAMP, catalogo STRING, esquema STRING, ativo STRING, tipo STRING, responde BOOLEAN, erro STRING"
spark.createDataFrame(linhas, esquema).write.mode("append").saveAsTable(f"{S}.sonda_views")
quebradas = [f"{x[1]}.{x[2]}.{x[3]}" for x in linhas if not x[5]]
print(f"sonda: {len(linhas)} views, {len(linhas) - len(quebradas)} respondem, {len(quebradas)} não respondem")

# COMMAND ----------

spark.sql(f"DELETE FROM {S}.historico WHERE registrado_em = current_date()")
spark.sql(f"""INSERT INTO {S}.historico
SELECT current_date(), regra_id, dimensao, regra, aplicavel, conformes, falhas, pct_conforme, meta_pct, situacao
FROM {S}.boas_praticas_dados""")
resumo = spark.sql(f"SELECT situacao, count(*) AS regras FROM {S}.historico WHERE registrado_em = current_date() GROUP BY 1").collect()
print("histórico do dia gravado:", {r.situacao: r.regras for r in resumo})
