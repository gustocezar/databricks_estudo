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
