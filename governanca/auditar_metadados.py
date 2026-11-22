#!/usr/bin/env python3
"""Audita os metadados do catálogo pos_venda no Unity Catalog: descrições (tabelas e colunas) e tags (catálogo,
schemas, tabelas e colunas). Descrições pela API REST; tags em lote pelo information_schema (3 consultas no warehouse).
Sem warehouse (cota do Free Edition), lê as tags pela API REST, uma chamada por objeto (lento, sujeito a limite de
requisições); falha de leitura aparece como "não lida", nunca como "sem tag".

  python3 auditar_metadados.py      -> grava auditoria_metadados.json e imprime o resumo em Markdown
"""
import concurrent.futures as cf
import json
import pathlib
import re
import ssl
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

AQUI = pathlib.Path(__file__).resolve().parent
PERFIL, HOST, CAT = "dbx-workshop", "https://dbc-15c48c79-7aa2.cloud.databricks.com", "pos_venda"
CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem")
TOKEN = json.loads(subprocess.check_output(["databricks", "auth", "token", "--profile", PERFIL, "-o", "json"]))["access_token"]

# camadas do fluxo diário (o que a ontologia e a Genie vão usar) x legado (medalhão estático da primeira versão)
PRINCIPAIS = ["landing", "fonte", "bronze", "silver", "gold", "dq", "ontologia", "regras", "bi"]
LEGADO = ["bronze_sql", "silver_sql", "gold_sql", "bronze_ldp", "silver_ldp", "gold_ldp"]
# colunas com dado pessoal (LGPD) — candidatas a tag de classificação
PII = re.compile(r"(cpf|(^|_)rg($|_)|email|celular|telefone|(^|_)nome($|_)|logradouro|endereco|bairro|cep|data_nascimento|"
                 r"documento|numero$|complemento)")
NAO_PII = re.compile(r"(produto_nome|ponto_venda_nome|_valido$|_ausente$|_invalido$|numero_apolice|numero_parcela|"
                     r"_malformado$|^pct_|^taxa_|cobertura_|^nome_mes$|^nome_dia_semana$|"
                     r"numero_ultimo_endosso|cpf_valido)")


def get(caminho, params=None, tentativas=5):
    url = HOST + caminho + ("?" + urllib.parse.urlencode(params) if params else "")
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
            with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
                return json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and i < tentativas - 1:
                time.sleep(2 * (i + 1))
                continue
            return {"_erro": e.code}
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2 * (i + 1))
    return {"_erro": "rede"}


def tags(tipo, nome):
    """Tags de um objeto pela API REST. None = não foi possível ler (não confundir com "sem tag")."""
    r = get(f"/api/2.1/unity-catalog/entity-tag-assignments/{tipo}/{urllib.parse.quote(nome, safe='.')}/tags")
    if "_erro" in r:
        return None
    return {t["tag_key"]: t.get("tag_value") for t in r.get("tag_assignments", [])}


def tags_em_lote():
    """Todas as tags do catálogo em 3 consultas ao information_schema. None se o warehouse não responder."""
    import sql_util
    consultas = {
        "schemas": f"SELECT schema_name AS s, NULL AS t, NULL AS c, tag_name, tag_value FROM {CAT}.information_schema.schema_tags",
        "tables": f"SELECT schema_name AS s, table_name AS t, NULL AS c, tag_name, tag_value FROM {CAT}.information_schema.table_tags",
        "columns": f"SELECT schema_name AS s, table_name AS t, column_name AS c, tag_name, tag_value "
                   f"FROM {CAT}.information_schema.column_tags",
    }
    lote = {}
    for tipo, sql in consultas.items():
        try:
            estado, erro, linhas = sql_util.executar(sql)
        except Exception as e:                      # cota esgotada ou rede
            print(f"tags em lote indisponíveis ({type(e).__name__}); usando a API REST")
            return None
        if estado != "SUCCEEDED":
            print(f"tags em lote indisponíveis ({erro[:120]}); usando a API REST")
            return None
        for x in linhas:
            nome = ".".join(v for v in (CAT, x["s"], x["t"], x["c"]) if v)
            lote.setdefault((tipo, nome), {})[x["tag_name"]] = x["tag_value"] or ""
    return lote


def tabelas(schema):
    out, token = [], None
    while True:
        p = {"catalog_name": CAT, "schema_name": schema, "max_results": 50}
        if token:
            p["page_token"] = token
        r = get("/api/2.1/unity-catalog/tables", p)
        out += r.get("tables", [])
        token = r.get("next_page_token")
        if not token:
            return out


def main():
    schemas = [s for s in get("/api/2.1/unity-catalog/schemas", {"catalog_name": CAT}).get("schemas", [])
               if s["name"] not in ("information_schema", "default")]
    resultado = {"catalogo": {"nome": CAT, "comentario": get(f"/api/2.1/unity-catalog/catalogs/{CAT}").get("comment"),
                              "tags": tags("catalogs", CAT)}, "schemas": []}
    lote = tags_em_lote()
    jobs = {}

    def marcar(tipo, nome, alvo, ex):
        if lote is not None:
            alvo["tags"] = lote.get((tipo, nome), {})
        else:
            jobs[ex.submit(tags, tipo, nome)] = alvo

    with cf.ThreadPoolExecutor(8) as ex:
        for s in schemas:
            sch = {"nome": s["name"], "grupo": "principal" if s["name"] in PRINCIPAIS else "legado" if s["name"] in LEGADO else "outro",
                   "comentario": s.get("comment"), "tags": None, "tabelas": []}
            marcar("schemas", s["full_name"], sch, ex)
            for t in tabelas(s["name"]):
                tab = {"nome": t["full_name"], "tipo": t.get("table_type"), "comentario": t.get("comment"), "tags": None, "colunas": []}
                marcar("tables", t["full_name"], tab, ex)
                for c in t.get("columns", []):
                    col = {"nome": c["name"], "tipo": c.get("type_text"), "comentario": c.get("comment"), "tags": None,
                           "pii": bool(PII.search(c["name"])) and not NAO_PII.search(c["name"])}
                    tab["colunas"].append(col)
                    marcar("columns", f"{t['full_name']}.{c['name']}", col, ex)
                sch["tabelas"].append(tab)
            resultado["schemas"].append(sch)
        for f in cf.as_completed(jobs):
            jobs[f]["tags"] = f.result()
    resultado["tags_lidas_por"] = "information_schema" if lote is not None else "api_rest"
    (AQUI / "auditoria_metadados.json").write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    print(resumo(resultado))


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "–"


def resumo(r):
    L = [f"Catálogo `{CAT}`: descrição {'sim' if r['catalogo']['comentario'] else 'NÃO'} · tags {r['catalogo']['tags'] or 'nenhuma'}", "",
         "| Schema | Grupo | Desc. schema | Tags schema | Tabelas | c/ descrição | c/ tags | Colunas | c/ descrição | c/ tags | PII sem tag | Tags não lidas |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    tot = dict(t=0, td=0, tt=0, c=0, cd=0, ct=0, pii=0, nl=0)
    for s in sorted(r["schemas"], key=lambda s: (s["grupo"] != "principal", s["nome"])):
        t = len(s["tabelas"]); td = sum(1 for x in s["tabelas"] if x["comentario"]); tt = sum(1 for x in s["tabelas"] if x["tags"])
        cols = [c for x in s["tabelas"] for c in x["colunas"]]
        c = len(cols); cd = sum(1 for x in cols if x["comentario"]); ct = sum(1 for x in cols if x["tags"])
        pii = sum(1 for x in cols if x["pii"] and x["tags"] == {})          # lida e sem tag
        nl = sum(1 for x in cols + s["tabelas"] if x["tags"] is None)        # leitura falhou
        if s["grupo"] == "principal":
            for k, v in dict(t=t, td=td, tt=tt, c=c, cd=cd, ct=ct, pii=pii, nl=nl).items():
                tot[k] += v
        L.append(f"| {s['nome']} | {s['grupo']} | {'sim' if s['comentario'] else 'não'} | {len(s['tags'] or {})} | {t} | {td} ({pct(td, t)}) | "
                 f"{tt} | {c} | {cd} ({pct(cd, c)}) | {ct} | {pii} | {nl} |")
    L.append(f"| **principais** | | | | **{tot['t']}** | **{tot['td']} ({pct(tot['td'], tot['t'])})** | **{tot['tt']}** | **{tot['c']}** | "
             f"**{tot['cd']} ({pct(tot['cd'], tot['c'])})** | **{tot['ct']}** | **{tot['pii']}** | **{tot['nl']}** |")
    if tot["nl"]:
        L += ["", f"ATENÇÃO: {tot['nl']} objetos principais com tags não lidas (erro de API); rode de novo antes de concluir."]
    sem = [x["nome"] for s in r["schemas"] if s["grupo"] == "principal" for x in s["tabelas"] if not x["comentario"]]
    L += ["", f"Tabelas/views principais sem descrição ({len(sem)}): " + (", ".join(f"`{n}`" for n in sem) or "nenhuma")]
    return "\n".join(L)


if __name__ == "__main__":
    main()
