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
dbutils.widgets.dropdown("modo", "gravar", ["gravar", "ensaio"])                        # noqa: F821  ensaio: não grava nada

ENTRADA = dbutils.widgets.get("tabela_entrada")   # noqa: F821
DESTINO = dbutils.widgets.get("schema_destino")   # noqa: F821
PREFIXO = dbutils.widgets.get("prefixo")          # noqa: F821
ARQUIVO = dbutils.widgets.get("arquivo_checks")   # noqa: F821
FILTRO = dbutils.widgets.get("filtro").strip()    # noqa: F821
MODO = dbutils.widgets.get("modo")                # noqa: F821

# COMMAND ----------

import json
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

# COMMAND ----------

# Métricas por regra e versão (P41): a mesma regra pode ter versões com vigências diferentes, cada uma com o seu
# filtro pela data do dado. A versão vem do user_metadata que regras/catalogo/gerar_catalogo.py escreve no YAML;
# as linhas avaliadas de cada versão são só as da vigência dela.
execucao, agora = str(uuid.uuid4()), datetime.now(timezone.utc)
total = avaliado.count()


def violacoes(coluna):  # explode ignora nulo e lista vazia
    campos = avaliado.schema[coluna].dataType.elementType.fieldNames()
    versao = F.col("r.user_metadata").getItem("versao") if "user_metadata" in campos else F.lit(None).cast("string")
    return avaliado.select(F.explode(F.col(coluna)).alias("r")).select(F.col("r.name").alias("regra"), versao.alias("versao"))


por_regra = (violacoes(COL_ERRO).unionByName(violacoes(COL_AVISO)).groupBy("regra", "versao")
             .agg(F.count("*").alias("reprovadas")).withColumnRenamed("regra", "_regra").withColumnRenamed("versao", "_versao"))
avaliadas_por_filtro = {f: (df.where(f).count() if f else total) for f in {c.get("filter") or "" for c in checks}}
nomes = spark.createDataFrame(  # noqa: F821  regras sem reprovação também aparecem, com zero
    [(c.get("name"), (c.get("user_metadata") or {}).get("versao"), c.get("criticality", "error"), c.get("filter") or "",
      avaliadas_por_filtro[c.get("filter") or ""]) for c in checks],
    "regra string, versao string, criticidade string, filtro string, avaliadas bigint")
por_versao = (nomes.join(por_regra, (F.col("regra") == F.col("_regra")) & F.col("versao").eqNullSafe(F.col("_versao")), "left")
              .withColumn("reprovadas", F.coalesce("reprovadas", F.lit(0))).drop("_regra", "_versao"))

if MODO == "ensaio":   # não grava nada: devolve as contagens para quem chamou (gerar_catalogo.py ensaio)
    resultado = {"modo": MODO, "tabela": ENTRADA, "filtro": FILTRO, "arquivo_checks": ARQUIVO, "linhas": total,
                 "linhas_com_erro": quarentena.count(),
                 "regras": [r.asDict() for r in por_versao.orderBy("regra", "versao").collect()]}
    print(json.dumps(resultado, ensure_ascii=False, indent=1))
    dbutils.notebook.exit(json.dumps(resultado, ensure_ascii=False))  # noqa: F821

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {DESTINO}")  # noqa: F821  (pule se o schema já existe e você não pode criar)
validos.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{DESTINO}.{PREFIXO}_validos")
quarentena.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{DESTINO}.{PREFIXO}_quarentena")

# Métricas por regra: base do painel de qualidade e do plano de ação (cada regra com dono e critério de pronto)
metricas = (   # versao é coluna nova (26/11): fica no fim, e o append usa mergeSchema
    por_versao
    .select(F.lit(execucao).alias("execucao_id"), F.lit(agora).alias("executado_em"), F.lit(ENTRADA).alias("tabela"),
            "regra", "criticidade", F.col("avaliadas").alias("linhas_avaliadas"), "reprovadas", "versao")
    .withColumn("taxa", F.when(F.col("linhas_avaliadas") > 0, F.col("reprovadas") / F.col("linhas_avaliadas")))
    .select("execucao_id", "executado_em", "tabela", "regra", "criticidade", "linhas_avaliadas", "reprovadas", "taxa",
            "versao")
)
metricas.write.mode("append").option("mergeSchema", "true").saveAsTable(f"{DESTINO}.dq_metricas_regras")

# COMMAND ----------

# Governança junto com o dado (P13, P15, P16): a cada execução, as tabelas recriadas recebem de novo a descrição da
# entrada coluna a coluna, a tag dado_pessoal das colunas pessoais e as tags de domínio e LGPD da tabela.
def esc(t):
    return str(t).replace("\\", "\\\\").replace("'", "\\'")


cat, sch, tab = ENTRADA.split(".")
coment = {r["col_name"]: r["comment"] for r in spark.sql(f"DESCRIBE TABLE {ENTRADA}").collect()  # noqa: F821
          if r["col_name"] and not r["col_name"].startswith("#") and r["comment"]}
tags_col = spark.sql(f"""SELECT column_name, tag_name, tag_value FROM {cat}.information_schema.column_tags  -- noqa
    WHERE schema_name = '{sch}' AND table_name = '{tab}' AND tag_name = 'dado_pessoal'""").collect()  # noqa: F821
tags_tab = spark.sql(f"""SELECT tag_name, tag_value FROM {cat}.information_schema.table_tags
    WHERE schema_name = '{sch}' AND table_name = '{tab}'
      AND tag_name IN ('domain', 'data_owner', 'subject_area', 'contem_dado_pessoal', 'contem_dado_sensivel')""").collect()  # noqa: F821
EXTRAS = {
    COL_ERRO: "Regras de erro (criticality error) que a linha violou, uma estrutura por regra: nome, mensagem e colunas.",
    COL_AVISO: "Regras de aviso (criticality warn) que a linha violou; a linha entra, marcada com cada aviso.",
    "execucao_id": "Identificador da execução do DQX como código; agrupa as métricas da mesma rodada.",
    "executado_em": "Data e hora (UTC) em que a execução aplicou as checagens.",
    "tabela": "Tabela de entrada avaliada, no formato catálogo.schema.tabela.",
    "regra": "Nome estável da regra; é o mesmo motivo de rejeição da barreira do pipeline.",
    "criticidade": "Criticidade da regra: error barra a linha, warn deixa entrar marcada.",
    "linhas_avaliadas": "Quantidade de linhas da janela avaliadas nesta execução.",
    "reprovadas": "Linhas que violaram a regra nesta execução; zero aparece para mostrar que foi checada.",
    "taxa": "Reprovadas dividido por linhas avaliadas, entre 0 e 1.",
    "versao": "Versão da regra no catálogo (regras/catalogo); cada versão vale só na sua vigência pela data do dado.",
}
DESCR = {
    f"{PREFIXO}_validos": f"Linhas de {ENTRADA} sem erro nas checagens do DQX como código; avisos na coluna {COL_AVISO}. Gerada por dqx_codigo/aplicar_dqx.py.",
    f"{PREFIXO}_quarentena": f"Linhas de {ENTRADA} com ao menos um erro nas checagens do DQX como código; cada regra violada em {COL_ERRO}. Gerada por dqx_codigo/aplicar_dqx.py.",
    "dq_metricas_regras": "Histórico do DQX como código: uma linha por execução e regra, com linhas avaliadas, reprovadas e taxa. Base do painel de qualidade e do plano de ação.",
}
spark.sql(f"COMMENT ON SCHEMA {DESTINO} IS 'Resultados do DQX como código (trilha A, sem app): válidos, quarentena e métricas por regra. Gerado por dqx_codigo/aplicar_dqx.py.'")  # noqa: F821
for nome, descr in DESCR.items():
    alvo = f"{DESTINO}.{nome}"
    spark.sql(f"COMMENT ON TABLE {alvo} IS '{esc(descr)}'")  # noqa: F821
    colunas = spark.table(alvo).columns  # noqa: F821
    for c in colunas:
        texto = EXTRAS.get(c) or coment.get(c)
        if texto:
            spark.sql(f"ALTER TABLE {alvo} ALTER COLUMN `{c}` COMMENT '{esc(texto)}'")  # noqa: F821
    if nome != "dq_metricas_regras":
        for r in tags_col:
            if r["column_name"] in colunas:
                spark.sql(f"ALTER TABLE {alvo} ALTER COLUMN `{r['column_name']}` SET TAGS ('dado_pessoal' = '{esc(r['tag_value'])}')")  # noqa: F821
        if tags_tab:
            pares = ", ".join(f"'{r['tag_name']}' = '{esc(r['tag_value'])}'" for r in tags_tab)
            spark.sql(f"ALTER TABLE {alvo} SET TAGS ({pares})")  # noqa: F821
print("descrições e tags aplicadas em", ", ".join(DESCR))

# COMMAND ----------

display(spark.table(f"{DESTINO}.dq_metricas_regras").where(F.col("execucao_id") == execucao).orderBy(F.desc("reprovadas")))  # noqa: F821
