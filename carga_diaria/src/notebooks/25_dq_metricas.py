# Databricks notebook source
# MAGIC %md
# MAGIC # pos_venda · 25 · Observabilidade de qualidade
# MAGIC Gera as tabelas de métricas de qualidade por dia (para painéis e para mostrar a evolução) e as **janelas dos últimos 7 dias**
# MAGIC (`pos_venda.dq.v_*_7d`) que o DQX Studio usa para medir a qualidade recente de cada camada.
# MAGIC
# MAGIC | Tabela | O que mostra |
# MAGIC |---|---|
# MAGIC | `gold.dq_barrados_por_motivo_dia` | eventos barrados na silver, por dia e por regra violada |
# MAGIC | `gold.dq_qualidade_diaria` | recebidos, aptos, barrados e métricas de aviso (CPF inválido, e-mail ausente, duplicatas...) por dia |
# MAGIC | `gold.dq_fato_orfas_diarias` | linhas da fato histórica sem dimensão de forma de pagamento (dado ruim que vazou) |

# COMMAND ----------

import json

CAT = "pos_venda"
BR = f"{CAT}.bronze.pagamentos_pendentes_eventos"
EV = f"{CAT}.silver.pendencia_evento"
QT = f"{CAT}.silver.pendencia_evento_quarentena"
ATUAL = f"{CAT}.silver.pendencia_atual"
HIST = f"{CAT}.silver.pendencia_hist"
FACT = f"{CAT}.gold.fact_pagamento_pendente_snapshot"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CAT}.dq COMMENT 'pos_venda - janelas e metricas de qualidade de dados (DQX)'")

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE {CAT}.gold.dq_barrados_por_motivo_dia
COMMENT 'Eventos barrados na silver (quarentena) por dia, motivo da rejeicao e tipo de evento.'
AS
SELECT data_extracao AS dia, motivo_rejeicao, tipo_evento, count(*) AS eventos, count(DISTINCT pendencia_id) AS pendencias,
       round(sum(valor_total_pendente), 2) AS valor_total
FROM {QT}
GROUP BY data_extracao, motivo_rejeicao, tipo_evento
""")

spark.sql(f"""
CREATE OR REPLACE TABLE {CAT}.gold.dq_qualidade_diaria
COMMENT 'Qualidade diaria do fluxo bronze > silver: recebidos, aptos, barrados e metricas de aviso (valores e percentuais).'
AS
WITH rec AS (
  SELECT data_extracao AS dia, count(*) AS eventos_recebidos,
         count(*) - count(DISTINCT pendencia_id, data_extracao, tipo_evento) - count_if(pendencia_id IS NULL) AS eventos_duplicados,
         count_if(cliente_uf <> upper(cliente_uf)) AS uf_minuscula
  FROM {BR} GROUP BY data_extracao
),
apt AS (
  SELECT data_extracao AS dia, count(*) AS eventos_aptos,
         count_if(dq_cpf_invalido) AS cpf_invalido, count_if(dq_email_ausente) AS email_ausente, count_if(dq_email_invalido) AS email_invalido,
         count_if(dq_rg_ausente) AS rg_ausente, count_if(dq_celular_ausente) AS celular_ausente,
         count_if(length(cliente_cep) <> 8) AS cep_malformado,
         count_if(forma_pagamento NOT IN ('DEBITO_CONTA', 'BOLETO', 'CARTAO_CREDITO', 'PIX_AUTOMATICO')) AS forma_pagamento_nao_cadastrada,
         count_if(canal_venda = 'CORRETOR' AND corretor_id IS NULL) AS canal_corretor_sem_corretor
  FROM {EV} GROUP BY data_extracao
),
bar AS (SELECT data_extracao AS dia, count(*) AS eventos_barrados FROM {QT} GROUP BY data_extracao)
SELECT r.dia,
       r.eventos_recebidos, coalesce(a.eventos_aptos, 0) AS eventos_aptos, coalesce(b.eventos_barrados, 0) AS eventos_barrados,
       round(100.0 * coalesce(a.eventos_aptos, 0) / r.eventos_recebidos, 3) AS pct_aptos,
       round(100.0 * coalesce(b.eventos_barrados, 0) / r.eventos_recebidos, 3) AS pct_barrados,
       r.eventos_duplicados, round(100.0 * r.eventos_duplicados / r.eventos_recebidos, 3) AS pct_duplicados,
       r.uf_minuscula,
       coalesce(a.cpf_invalido, 0) AS cpf_invalido, round(100.0 * coalesce(a.cpf_invalido, 0) / nullif(a.eventos_aptos, 0), 3) AS pct_cpf_invalido,
       coalesce(a.email_ausente, 0) AS email_ausente, round(100.0 * coalesce(a.email_ausente, 0) / nullif(a.eventos_aptos, 0), 3) AS pct_email_ausente,
       coalesce(a.email_invalido, 0) AS email_invalido, coalesce(a.rg_ausente, 0) AS rg_ausente, coalesce(a.celular_ausente, 0) AS celular_ausente,
       coalesce(a.cep_malformado, 0) AS cep_malformado, round(100.0 * coalesce(a.cep_malformado, 0) / nullif(a.eventos_aptos, 0), 3) AS pct_cep_malformado,
       coalesce(a.forma_pagamento_nao_cadastrada, 0) AS forma_pagamento_nao_cadastrada,
       round(100.0 * coalesce(a.forma_pagamento_nao_cadastrada, 0) / nullif(a.eventos_aptos, 0), 3) AS pct_forma_pagamento_nao_cadastrada,
       coalesce(a.canal_corretor_sem_corretor, 0) AS canal_corretor_sem_corretor
FROM rec r LEFT JOIN apt a ON a.dia = r.dia LEFT JOIN bar b ON b.dia = r.dia
ORDER BY r.dia
""")

spark.sql(f"""
CREATE OR REPLACE TABLE {CAT}.gold.dq_fato_orfas_diarias
COMMENT 'Fato historica: linhas por foto diaria e quantas ficaram sem dimensao de forma de pagamento (dado nao cadastrado que vazou para a gold).'
AS
SELECT CAST(f.data_referencia_sk AS INT) AS dia_sk, to_date(CAST(f.data_referencia_sk AS STRING), 'yyyyMMdd') AS dia,
       count(*) AS linhas_na_foto, count_if(x.forma_pagamento_sk IS NULL) AS fk_forma_pagamento_orfa
FROM {FACT} f LEFT JOIN {CAT}.gold.dim_forma_pagamento x ON f.forma_pagamento_sk = x.forma_pagamento_sk
WHERE f.data_referencia_sk >= 20261120
GROUP BY f.data_referencia_sk
""")

# COMMAND ----------

# views preservadas: CREATE OR REPLACE VIEW apaga tags e Wiki, entao so recria quando a definicao muda
# (e, nesse caso, devolve tags, tags de coluna e Wiki). Codigo de pos_venda/carga_diaria/views_preservadas.py:
"""Cria ou atualiza views do Unity Catalog sem perder a governança.

`CREATE OR REPLACE VIEW` apaga as tags da view, as tags das colunas e a Wiki (as descrições de coluna de um
`SELECT *` são herdadas da tabela de origem e sobrevivem). Teste de 20/11/2026: `CREATE OR REPLACE TABLE ... AS
SELECT` mantém tudo; a view perde as tags. Por isso:

  - se a view já existe com a mesma definição, não faz nada (o caso de todo dia);
  - se não existe, cria;
  - se a definição mudou, guarda tags, tags de coluna, descrições explícitas e Wiki, recria e devolve tudo.

Usado pelo job diário (embutido no notebook 25 por gerar_carga.py), pelo replay (dqx_studio/regras/rodar_ciclos.py)
e pelas views do painel (dqx_studio/painel/aplicar_e_testar.py).

  sql(texto) -> list[dict]                     executa SQL e devolve as linhas
  api(metodo, caminho, corpo=None) -> (status, dict)   REST do workspace; opcional (sem ela, tags e Wiki não voltam)
"""
import json
import re
import subprocess
import urllib.parse


def _norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip().rstrip(";").strip()


def _q(s):
    return (s or "").replace("\\", "\\\\").replace("'", "\\'")


def _foto(nome, sql, api):
    cat, sch, tab = nome.split(".")
    f = {
        "descricoes": {r["column_name"]: r["comment"] for r in sql(
            f"SELECT column_name, comment FROM {cat}.information_schema.columns "
            f"WHERE table_schema = '{sch}' AND table_name = '{tab}' AND comment IS NOT NULL")},
        "tags": [(r["tag_name"], r["tag_value"]) for r in sql(
            f"SELECT tag_name, tag_value FROM {cat}.information_schema.table_tags "
            f"WHERE schema_name = '{sch}' AND table_name = '{tab}'")],
        "tags_coluna": [(r["column_name"], r["tag_name"], r["tag_value"]) for r in sql(
            f"SELECT column_name, tag_name, tag_value FROM {cat}.information_schema.column_tags "
            f"WHERE schema_name = '{sch}' AND table_name = '{tab}'")],
        "wiki": None,
    }
    if api:
        st, w = api("GET", f"/api/2.0/knowledge/tables/{nome}/page")
        if st == 200 and w.get("body"):
            f["wiki"] = {"body": w["body"], "description": w.get("description") or "", "state": w.get("state") or "PUBLISHED"}
    return f


def _tag(api, tipo, entidade, chave, valor):
    corpo = {"entity_type": tipo, "entity_name": entidade, "tag_key": chave}
    if valor not in (None, ""):
        corpo["tag_value"] = valor
    st, r = api("POST", "/api/2.1/unity-catalog/entity-tag-assignments", corpo)
    return st == 200 or "already" in json.dumps(r).lower()


def _devolver(nome, foto, sql, api, log):
    cat, sch, tab = nome.split(".")
    agora = {r["column_name"]: r["comment"] for r in sql(
        f"SELECT column_name, comment FROM {cat}.information_schema.columns WHERE table_schema = '{sch}' AND table_name = '{tab}'")}
    n_desc = 0
    for col, txt in foto["descricoes"].items():
        if col in agora and agora[col] != txt:
            sql(f"COMMENT ON COLUMN {nome}.`{col}` IS '{_q(txt)}'")
            n_desc += 1
    ok_tags = ok_col = 0
    wiki = "sem Wiki"
    if api:
        ok_tags = sum(_tag(api, "tables", nome, k, v) for k, v in foto["tags"])
        ok_col = sum(_tag(api, "columns", f"{nome}.{c}", k, v) for c, k, v in foto["tags_coluna"] if c in agora)
        if foto["wiki"]:
            st, _ = api("PATCH", f"/api/2.0/knowledge/tables/{nome}/page?update_mask=body,description,state", foto["wiki"])
            wiki = "Wiki devolvida" if st == 200 else f"Wiki falhou ({st})"
    log(f"  {nome}: recriada; devolvidas {n_desc} descrições, {ok_tags}/{len(foto['tags'])} tags, "
        f"{ok_col}/{len(foto['tags_coluna'])} tags de coluna, {wiki}")


def garantir_view(nome, comentario, consulta, sql, api=None, log=print, ddl=None):
    """Cria a view se não existe, recria só se a definição mudou (devolvendo a governança). Retorna o que fez.

    ddl: DDL completo a executar no lugar do `CREATE OR REPLACE VIEW nome COMMENT .. AS consulta` montado aqui
    (por exemplo, com a lista de colunas e seus COMMENT). A comparação de definição continua usando `consulta`.
    """
    cat, sch, tab = nome.split(".")
    atual = sql(f"SELECT view_definition FROM {cat}.information_schema.views WHERE table_schema = '{sch}' AND table_name = '{tab}'")
    if atual and _norm(atual[0]["view_definition"]) == _norm(consulta):
        return "igual"
    foto = _foto(nome, sql, api) if atual else None
    sql(ddl or f"CREATE OR REPLACE VIEW {nome} COMMENT '{_q(comentario)}' AS {consulta}")
    if foto is None:
        log(f"  {nome}: criada (rode governanca/aplicar_semantica.py para tags e Wiki)")
        return "criada"
    _devolver(nome, foto, sql, api, log)
    return "recriada"


def descrever_colunas(nome, descricoes, sql):
    """Grava a descrição das colunas que ainda não a têm igual (views com colunas calculadas não herdam descrição)."""
    cat, sch, tab = nome.split(".")
    agora = {r["column_name"]: r["comment"] for r in sql(
        f"SELECT column_name, comment FROM {cat}.information_schema.columns WHERE table_schema = '{sch}' AND table_name = '{tab}'")}
    n = 0
    for col, txt in descricoes.items():
        if col in agora and agora[col] != txt:
            sql(f"COMMENT ON COLUMN {nome}.`{col}` IS '{_q(txt)}'")
            n += 1
    return n, [c for c in agora if c not in descricoes and not agora[c]]


def api_cli(perfil):
    """REST do workspace pelo Databricks CLI (uso local: replay e painel)."""
    def api(metodo, caminho, corpo=None):
        cmd = ["databricks", "api", metodo.lower(), caminho, "--profile", perfil]
        if corpo is not None:
            cmd += ["--json", json.dumps(corpo)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            return 400, {"erro": (r.stderr or r.stdout)[:300]}
        try:
            return 200, json.loads(r.stdout or "{}")
        except ValueError:
            return 200, {}
    return api


def api_sdk():
    """REST do workspace pelo SDK (uso no notebook do job, com a identidade do job)."""
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()

    def api(metodo, caminho, corpo=None):
        base, _, qs = caminho.partition("?")
        try:
            return 200, w.api_client.do(metodo, base, query=dict(urllib.parse.parse_qsl(qs)) or None, body=corpo) or {}
        except Exception as e:  # noqa: BLE001 - devolve o erro para o log em vez de parar a carga
            return 400, {"erro": str(e)[:300]}
    return api


def _sql(q):
    return [r.asDict() for r in spark.sql(q).collect()]


_api = api_sdk()

# COMMAND ----------

# janelas dos ultimos 7 dias (relativas ao ultimo dia carregado) para o DQX Studio medir a qualidade recente
J = 7
VIEWS_7D = [
    (f"{CAT}.dq.v_bronze_eventos_7d", "Bronze: eventos dos ultimos 7 dias carregados (janela usada pelo DQX Studio).",
     f"SELECT * FROM {BR} WHERE data_extracao > date_sub((SELECT max(data_extracao) FROM {BR}), {J})"),
    (f"{CAT}.dq.v_silver_pendencia_atual_7d", "Silver (estado atual): pendencias com evento nos ultimos 7 dias.",
     f"SELECT * FROM {ATUAL} WHERE data_extracao > date_sub((SELECT max(data_extracao) FROM {ATUAL}), {J})"),
    (f"{CAT}.dq.v_silver_pendencia_hist_7d", "Silver historica (SCD2): versoes iniciadas nos ultimos 7 dias.",
     f"SELECT * FROM {HIST} WHERE __START_AT > date_sub((SELECT max(__START_AT) FROM {HIST}), {J})"),
    (f"{CAT}.dq.v_fato_snapshot_7d", "Gold (fato historica): fotos diarias dos ultimos 7 dias.",
     f"SELECT * FROM {FACT} WHERE data_referencia_sk > (SELECT max(data_referencia_sk) FROM {FACT}) - 7"),
]
for _nome, _comentario, _consulta in VIEWS_7D:
    print(_nome, garantir_view(_nome, _comentario, _consulta, _sql, _api))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Janela de avaliação do DQX Studio
# MAGIC `pos_venda.dq.janela_avaliacao` guarda o intervalo avaliado e as views `pos_venda.dq.v_*_janela` leem só esse intervalo.
# MAGIC O job aponta a janela para os **últimos 7 dias carregados**. O Studio avalia essas views com **todas as linhas**.

# COMMAND ----------

for stmt in ["CREATE TABLE IF NOT EXISTS pos_venda.dq.janela_avaliacao (\n  data_inicio DATE NOT NULL COMMENT 'primeiro dia avaliado',\n  data_fim DATE NOT NULL COMMENT 'ultimo dia avaliado',\n  origem STRING COMMENT 'quem apontou a janela (job diario ou replay)',\n  atualizado_em TIMESTAMP)\nCOMMENT 'Janela de avaliacao do DQX Studio: intervalo de dias que as views pos_venda.dq.v_*_janela expoem.'"]:
    spark.sql(stmt)
for _nome, _comentario, _consulta in [('pos_venda.dq.v_bronze_eventos_janela', 'Bronze: todos os eventos recebidos na janela de avaliacao (aptos e nao aptos).', 'SELECT * FROM pos_venda.bronze.pagamentos_pendentes_eventos WHERE data_extracao BETWEEN (SELECT data_inicio FROM pos_venda.dq.janela_avaliacao) AND (SELECT data_fim FROM pos_venda.dq.janela_avaliacao)'), ('pos_venda.dq.v_silver_eventos_aptos_janela', 'Silver: eventos que passaram na barreira de qualidade e entraram na silver na janela de avaliacao.', 'SELECT * FROM pos_venda.silver.pendencia_evento WHERE data_extracao BETWEEN (SELECT data_inicio FROM pos_venda.dq.janela_avaliacao) AND (SELECT data_fim FROM pos_venda.dq.janela_avaliacao)'), ('pos_venda.dq.v_silver_hist_janela', 'Silver historica (SCD2): versoes iniciadas na janela de avaliacao.', 'SELECT * FROM pos_venda.silver.pendencia_hist WHERE __START_AT BETWEEN (SELECT data_inicio FROM pos_venda.dq.janela_avaliacao) AND (SELECT data_fim FROM pos_venda.dq.janela_avaliacao)'), ('pos_venda.dq.v_fato_snapshot_janela', 'Gold (fato historica): fotos diarias da janela de avaliacao.', "SELECT * FROM pos_venda.gold.fact_pagamento_pendente_snapshot WHERE data_referencia_sk BETWEEN CAST(date_format((SELECT data_inicio FROM pos_venda.dq.janela_avaliacao), 'yyyyMMdd') AS INT) AND CAST(date_format((SELECT data_fim FROM pos_venda.dq.janela_avaliacao), 'yyyyMMdd') AS INT)"), ('pos_venda.dq.v_quarentena_janela', 'Quarentena: eventos NAO aptos barrados antes da silver na janela de avaliacao, com o motivo da rejeicao.', 'SELECT * FROM pos_venda.silver.pendencia_evento_quarentena WHERE data_extracao BETWEEN (SELECT data_inicio FROM pos_venda.dq.janela_avaliacao) AND (SELECT data_fim FROM pos_venda.dq.janela_avaliacao)')]:
    print(_nome, garantir_view(_nome, _comentario, _consulta, _sql, _api))
spark.sql("INSERT OVERWRITE pos_venda.dq.janela_avaliacao SELECT date_sub((SELECT max(data_extracao) FROM pos_venda.bronze.pagamentos_pendentes_eventos), 6), (SELECT max(data_extracao) FROM pos_venda.bronze.pagamentos_pendentes_eventos), 'job diario', current_timestamp()")
display(spark.table(f"{CAT}.dq.janela_avaliacao"))

# COMMAND ----------

res = {
    "dias_com_metrica": spark.table(f"{CAT}.gold.dq_qualidade_diaria").count(),
    "linhas_barradas": spark.table(QT).count(),
    "motivos_distintos": spark.sql(f"SELECT count(DISTINCT motivo_rejeicao) FROM {QT}").first()[0],
}
dbutils.notebook.exit(json.dumps(res))
