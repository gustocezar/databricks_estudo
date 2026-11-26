# Databricks notebook source
# MAGIC %md
# MAGIC # Unicidade diária das chaves (P42, L100)
# MAGIC
# MAGIC Testa nos dados cada chave declarada no modelo de dados (`pos_venda.conformidade.chaves_declaradas`, publicada por
# MAGIC `governanca/modelo_dados.py aplicar`) e grava o resultado em `pos_venda.conformidade.chaves_unicas`.
# MAGIC
# MAGIC - **PK do Unity Catalog repetida:** a tarefa falha. Com RELY, o otimizador conta com a unicidade e pode devolver
# MAGIC   número errado sem erro nenhum (L100: a ponte apólice × cobertura ficou assim de 23 a 26/11).
# MAGIC - **Chave lógica repetida:** fica registrada como aviso; ou o grão do modelo está errado, ou o dado repete.

# COMMAND ----------

import concurrent.futures as cf
import datetime

S = "pos_venda.conformidade"
agora = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None, microsecond=0)
chaves = spark.sql(f"SELECT tabela, colunas, origem_chave FROM {S}.chaves_declaradas WHERE testar").collect()
if not chaves:
    raise RuntimeError("nenhuma chave para testar: rode governanca/modelo_dados.py aplicar")


def testar(c):
    cols = ", ".join(f"`{x}`" for x in c.colunas)
    try:
        r = spark.sql(f"SELECT count(*) AS n, count(DISTINCT struct({cols})) AS d FROM {c.tabela}").collect()[0]
        return (agora, c.tabela, list(c.colunas), c.origem_chave, int(r.n), int(r.d), int(r.n) - int(r.d), r.n == r.d, None)
    except Exception as e:  # noqa: BLE001 - tabela que sumiu ou coluna renomeada fica registrada
        return (agora, c.tabela, list(c.colunas), c.origem_chave, None, None, None, False, str(e)[:500])


with cf.ThreadPoolExecutor(4) as ex:
    res = list(ex.map(testar, chaves))

# COMMAND ----------

spark.sql(f"""CREATE TABLE IF NOT EXISTS {S}.chaves_unicas (
  verificado_em TIMESTAMP COMMENT 'Momento do teste (UTC).',
  tabela STRING COMMENT 'Tabela ou visão testada, no formato catálogo.schema.tabela.',
  colunas ARRAY<STRING> COMMENT 'Colunas da chave testada.',
  origem_chave STRING COMMENT 'PK no Unity Catalog ou chave lógica do modelo de dados.',
  linhas BIGINT COMMENT 'Linhas da tabela no momento do teste.',
  distintas BIGINT COMMENT 'Combinações distintas da chave.',
  repetidas BIGINT COMMENT 'Linhas a mais que a chave distinta: zero quando a chave é única.',
  unica BOOLEAN COMMENT 'Verdadeiro quando a chave é única nos dados.',
  erro STRING COMMENT 'Erro do teste, quando a tabela ou a coluna não respondeu.'
) COMMENT 'Unicidade diária das chaves declaradas no modelo de dados (P42, L100). Gravada pela tarefa chaves do job pos_venda_conformidade_sonda.'""")
esquema = ("verificado_em TIMESTAMP, tabela STRING, colunas ARRAY<STRING>, origem_chave STRING, linhas BIGINT, "
           "distintas BIGINT, repetidas BIGINT, unica BOOLEAN, erro STRING")
spark.createDataFrame(res, esquema).write.mode("append").saveAsTable(f"{S}.chaves_unicas")

pk_ruins = [f"{r[1]} ({r[6]} repetidas)" for r in res if r[3] == "PK no Unity Catalog" and not r[7]]
logicas = [f"{r[1]} ({r[6] if r[8] is None else 'erro'})" for r in res if r[3] != "PK no Unity Catalog" and not r[7]]
print(f"{len(res)} chaves testadas: {sum(1 for r in res if r[7])} únicas; PK repetida: {pk_ruins or 'nenhuma'}; "
      f"chave lógica repetida ou com erro: {logicas or 'nenhuma'}")
if pk_ruins:
    raise RuntimeError(f"PK do Unity Catalog repetida (RELY falso, número pode sair errado): {pk_ruins}")
