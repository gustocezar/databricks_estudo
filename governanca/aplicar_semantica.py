#!/usr/bin/env python3
"""Aplica a camada semântica do domínio Pós-venda no Unity Catalog (Discover), a partir de ontologia.py.

  python3 aplicar_semantica.py            governed tags, domínio + subdomínios, tags, certificação, Pages e Wikis
  python3 aplicar_semantica.py --so-tags  só as tags (schemas, tabelas, colunas e certificação)

Usa só APIs REST de metadados (sem warehouse). Idempotente: procura antes de criar e atualiza o que já existe.
Lê a lista de tabelas/colunas de auditoria_metadados.json (rode auditar_metadados.py antes).
"""
import concurrent.futures as cf
import json
import pathlib
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import ontologia as O

AQUI = pathlib.Path(__file__).resolve().parent
PERFIL, HOST = "dbx-workshop", "https://dbc-15c48c79-7aa2.cloud.databricks.com"
CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem")
PRINCIPAIS = ["landing", "fonte", "bronze", "silver", "gold", "dq", "ontologia", "regras", "bi"]
LEGADO = ["bronze_sql", "silver_sql", "gold_sql", "bronze_ldp", "silver_ldp", "gold_ldp"]   # medalhão antigo: só dado pessoal
_TOKEN = [None]


def token(renovar=False):
    if renovar or not _TOKEN[0]:
        _TOKEN[0] = json.loads(subprocess.check_output(["databricks", "auth", "token", "--profile", PERFIL, "-o", "json"]))["access_token"]
    return _TOKEN[0]


def api(metodo, caminho, corpo=None, params=None, tentativas=6):
    url = HOST + caminho + ("?" + urllib.parse.urlencode(params, safe=",") if params else "")
    for i in range(tentativas):
        req = urllib.request.Request(url, method=metodo, data=None if corpo is None else json.dumps(corpo).encode(),
                                     headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
                txt = r.read().decode()
                return r.status, json.loads(txt) if txt else {}
        except urllib.error.HTTPError as e:
            txt = e.read().decode(errors="ignore")
            if e.code == 401 and i < tentativas - 1:
                token(renovar=True)
                continue
            if e.code in (429, 500, 502, 503, 504) and i < tentativas - 1:
                time.sleep(2 * (i + 1))
                continue
            try:
                return e.code, json.loads(txt)
            except Exception:
                return e.code, {"message": txt[:300]}
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(3 * (i + 1))
    return 0, {"message": "rede indisponível"}


def paginar(caminho, chave, params=None):
    out, tok = [], None
    while True:
        p = dict(params or {})
        if tok:
            p["page_token"] = tok
        st, r = api("GET", caminho, params=p)
        if st != 200:
            raise RuntimeError(f"GET {caminho}: {st} {r}")
        out += r.get(chave, [])
        tok = r.get("next_page_token")
        if not tok:
            return out


# ---------------------------------------------------------------------------------------------------- governed tags
def garantir_tag_policy(tag_key, descricao):
    r = subprocess.run(["databricks", "tag-policies", "get-tag-policy", tag_key, "--profile", PERFIL, "-o", "json"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        return "existente"
    r = subprocess.run(["databricks", "tag-policies", "create-tag-policy", tag_key, "--description", descricao,
                        "--profile", PERFIL, "-o", "json"], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"tag policy {tag_key}: {r.stderr.strip()[:300]}")
    return "criada"


def garantir_valores_tag(tag_key, valores):
    """Governed tag sem lista de valores recusa qualquer valor: garante os valores permitidos."""
    r = subprocess.run(["databricks", "tag-policies", "get-tag-policy", tag_key, "--profile", PERFIL, "-o", "json"],
                       capture_output=True, text=True)
    atuais = {v.get("name") for v in json.loads(r.stdout or "{}").get("values", [])}
    if atuais == set(valores):
        return "valores ok"
    corpo = {"tag_key": tag_key, "values": [{"name": v} for v in valores]}
    r = subprocess.run(["databricks", "tag-policies", "update-tag-policy", tag_key, "values", "--json", json.dumps(corpo),
                        "--profile", PERFIL, "-o", "json"], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"valores da tag {tag_key}: {r.stderr.strip()[:300]}")
    return f"valores definidos {sorted(valores)}"


# ---------------------------------------------------------------------------------------------------- domínios
def garantir_dominio(tag_key, subtitle, description, uid, pai=None, icon=None):
    params = {"parent_domain_id": pai} if pai else None
    existente = next((d for d in paginar("/api/2.0/domains", "domains", params) if d.get("tag_key") == tag_key), None)
    corpo = {"subtitle": subtitle, "description": description, "business_owner_ids": [uid], "technical_owner_ids": [uid]}
    if icon:
        corpo["icon"] = icon
    if existente:
        mask = ",".join(corpo)
        st, r = api("PATCH", f"/api/2.0/{existente['name']}", corpo, {"update_mask": mask})
        if st != 200:
            raise RuntimeError(f"atualizar domínio {tag_key}: {st} {r}")
        return r, "atualizado"
    corpo["tag_key"] = tag_key
    if pai:
        corpo["parent_domain_id"] = pai
    st, r = api("POST", "/api/2.0/domains", corpo)
    if st != 200:
        raise RuntimeError(f"criar domínio {tag_key}: {st} {r}")
    return r, "criado"


# ---------------------------------------------------------------------------------------------------- tags em entidades
def aplicar_tag(tipo, nome, chave, valor=None):
    corpo = {"entity_type": tipo, "entity_name": nome, "tag_key": chave}
    if valor is not None:
        corpo["tag_value"] = valor
    for tentativa in range(4):
        st, r = api("POST", "/api/2.1/unity-catalog/entity-tag-assignments", corpo)
        msg = json.dumps(r)
        # valor recém-incluído na governed tag leva alguns segundos para valer (L47): espera e repete
        if not (st == 400 and "is not an allowed value" in msg):
            break
        time.sleep(5 * (tentativa + 1))
    if st == 200:
        return "criada"
    if st in (400, 409) and ("ALREADY_EXISTS" in msg or "already exists" in msg.lower() or "already assigned" in msg.lower()):
        if valor is None:
            return "existente"
        caminho = (f"/api/2.1/unity-catalog/entity-tag-assignments/{tipo}/{urllib.parse.quote(nome, safe='.')}"
                   f"/tags/{urllib.parse.quote(chave, safe='')}")
        st2, r2 = api("PATCH", caminho, {"tag_value": valor}, {"update_mask": "tag_value"})
        return "atualizada" if st2 == 200 else f"erro {st2} {json.dumps(r2)[:160]}"
    return f"erro {st} {msg[:160]}"


def tags_dado_pessoal(tab):
    """Classe técnica (class.*) e marcação legível de dado pessoal (LGPD) das colunas, e o resumo na tabela."""
    t, cats = [], set()
    for c in tab["colunas"]:
        for classe in O.CLASSIFICACAO.get(c["nome"], []):
            t.append(("columns", f"{tab['nome']}.{c['nome']}", classe, None))
        cat = O.categoria_dado_pessoal(c["nome"])
        if cat:
            t.append(("columns", f"{tab['nome']}.{c['nome']}", "dado_pessoal", cat))
            cats.add(cat)
    if cats:
        t.append(("tables", tab["nome"], "contem_dado_pessoal", "sim"))
    if "sensivel" in cats:
        t.append(("tables", tab["nome"], "contem_dado_sensivel", "sim"))
    return t


def plano_de_tags(audit, sub_tag):
    """Lista de (tipo, nome, chave, valor) para schemas, tabelas, colunas e certificação.

    Schemas legados (*_sql, *_ldp) recebem só as tags de dado pessoal: continuam fora da ontologia (sem domínio,
    camada ou certificação), mas quem os consulta vê onde há dado pessoal.
    """
    t = []
    for s in audit["schemas"]:
        if s["nome"] in LEGADO:
            for tab in s["tabelas"]:
                t += tags_dado_pessoal(tab)
            continue
        if s["nome"] not in PRINCIPAIS:
            continue
        fq_s = f"{O.CAT}.{s['nome']}"
        t.append(("schemas", fq_s, O.DOMINIO["tag_key"], None))                  # domínio (herdado pelas tabelas)
        t.append(("schemas", fq_s, "camada", O.CAMADA_SCHEMA[s["nome"]]))
        t.append(("schemas", fq_s, "domain", O.DOMINIO_PADRAO))                    # domínio, chave padrão sem acento
        for tab in s["tabelas"]:
            t.append(("tables", tab["nome"], "domain", O.DOMINIO_PADRAO))
            t.append(("tables", tab["nome"], "data_owner", O.RESPONSAVEL))
            w = O.W.get(tab["nome"])
            if not w or not w["sub"]:   # sem Wiki ou sem subdomínio nela: pelo schema ou pela tabela (O.SUB_SEM_WIKI)
                curto = tab["nome"].split(".", 1)[1]
                sub = O.SUB_SEM_WIKI_TABELA.get(curto) or O.SUB_SEM_WIKI.get(s["nome"])
                if sub:
                    t.append(("tables", tab["nome"], sub_tag[sub], None))
                    t.append(("tables", tab["nome"], "subject_area", sub))
            if w:
                if w["sub"]:
                    t.append(("tables", tab["nome"], sub_tag[w["sub"]], None))   # subdomínio
                    t.append(("tables", tab["nome"], "subject_area", w["sub"]))  # subdomínio, chave padrão sem acento
                t.append(("tables", tab["nome"], "tipo_ativo", w["tipo"]))
                if w.get("entidade"):
                    t.append(("tables", tab["nome"], "entidade", w["entidade"]))
            t.append(("tables", tab["nome"], "atualizacao", "diaria" if s["nome"] not in ("landing", "fonte") else "carga_unica"))
            if tab["nome"] in O.CERTIFICADAS:
                t.append(("tables", tab["nome"], "system.certification_status", "certified"))
            t += tags_dado_pessoal(tab)
    return t


# ---------------------------------------------------------------------------------------------------- Pages e Wikis
def aplicar_pages(dominio_por_sub):
    existentes = {p["display_name"]: p for p in paginar("/api/2.0/knowledge/pages", "pages")}
    res = []
    for p in O.PAGES:
        corpo = {"display_name": p["titulo"], "body": p["corpo"].strip(), "synonyms": p["sinonimos"],
                 "description": p["descricao"], "state": "PUBLISHED"}
        atual = existentes.get(p["titulo"])
        if atual:
            st, r = api("PATCH", f"/api/2.0/knowledge/{atual['name']}", corpo,
                        {"update_mask": "body,description,synonyms,state"})
            res.append((p["titulo"], "atualizada" if st == 200 else f"erro {st} {json.dumps(r)[:200]}"))
        else:
            corpo["domain"] = dominio_por_sub[p["sub"]]
            st, r = api("POST", "/api/2.0/knowledge/pages", corpo)
            res.append((p["titulo"], "criada" if st == 200 else f"erro {st} {json.dumps(r)[:200]}"))
    return res


def corpo_wiki(nome, w, colunas_pii):
    pages = "\n".join(f"- **{p}** (Page do domínio Pós-venda)" for p in w["pages"])
    pii = ""
    if colunas_pii:
        pii = (f"\n## Dados pessoais (LGPD)\n{len(colunas_pii)} colunas têm tag de classificação `class.*` "
               f"({', '.join(sorted(colunas_pii)[:8])}{'...' if len(colunas_pii) > 8 else ''}). "
               "Use em análises agregadas; não liste esses valores em respostas ou relatórios.\n")
    return f"""## Para que serve
{w['proposito']}

## Grão e chave
{w['grao']}

## Atualização e linhagem
{w['atualizacao']}

## Qualidade
{w['qualidade']}
{pii}
## Pode
- {w['pode']}

## Não pode
- {w['nao_pode']}

## Exemplo de consulta
```sql
{w['exemplo']}
```

## Conceitos relacionados
{pages}

Domínio **Pós-venda**{(' · subdomínio **' + O.SUB[w['sub']]['nome'] + '**') if w['sub'] else ''} · dados sintéticos para demonstração."""


def aplicar_wikis(audit):
    pii = {t["nome"]: [c["nome"] for c in t["colunas"] if c["nome"] in O.CLASSIFICACAO]
           for s in audit["schemas"] for t in s["tabelas"]}
    existentes = set(pii)

    def um(nome, w):
        if nome not in existentes:
            return nome, "tabela não existe (pulada)"
        corpo = {"body": corpo_wiki(nome, w, pii.get(nome, [])), "description": w["descricao"][:1000], "state": "PUBLISHED"}
        st, r = api("PATCH", f"/api/2.0/knowledge/tables/{nome}/page", corpo, {"update_mask": "body,description,state"})
        return nome, "publicada" if st == 200 else f"erro {st} {json.dumps(r)[:200]}"

    with cf.ThreadPoolExecutor(6) as ex:
        return list(ex.map(lambda kv: um(*kv), O.W.items()))


# ---------------------------------------------------------------------------------------------------- principal
def main():
    audit = json.loads((AQUI / "auditoria_metadados.json").read_text(encoding="utf-8"))
    sub_tag = {k: f"{O.DOMINIO['tag_key']}/{v['nome']}" for k, v in O.SUB.items()}
    relatorio = {}

    if "--so-tags" not in sys.argv:
        uid = int(json.loads(subprocess.check_output(["databricks", "current-user", "me", "--profile", PERFIL, "-o", "json"]))["id"])
        print("== governed tags do domínio")
        print("  ", O.DOMINIO["tag_key"], garantir_tag_policy(O.DOMINIO["tag_key"], O.DOMINIO["description"][:250]))
        for k, tg in sub_tag.items():
            print("  ", tg, garantir_tag_policy(tg, O.SUB[k]["description"][:250]))
        print("== domínio e subdomínios")
        dom, acao = garantir_dominio(O.DOMINIO["tag_key"], O.DOMINIO["subtitle"], O.DOMINIO["description"], uid, icon=O.DOMINIO["icon"])
        print("  ", O.DOMINIO["tag_key"], acao, dom["name"])
        dominio_por_sub, relatorio["dominio"] = {}, dom["name"]
        for k, v in O.SUB.items():
            sd, acao = garantir_dominio(sub_tag[k], v["subtitle"], v["description"], uid, pai=dom["domain_id"])
            dominio_por_sub[k] = sd["name"]
            print("  ", sub_tag[k], acao, sd["name"])
        relatorio["subdominios"] = dominio_por_sub

    print("== governed tags de dado pessoal (LGPD) e de domínio/responsável (chaves padrão)")
    valores = {**O.VALORES_DADO_PESSOAL, **O.VALORES_DOMINIO_PADRAO}
    for chave, descricao in {**O.TAG_DADO_PESSOAL, **O.TAG_DOMINIO_PADRAO}.items():
        print("  ", chave, garantir_tag_policy(chave, descricao[:250]), "|", garantir_valores_tag(chave, valores[chave]))
    print("== tags (domínio nos schemas, camada, subdomínio, tipo, entidade, certificação, classificação LGPD, dado pessoal)")
    plano = plano_de_tags(audit, sub_tag)
    with cf.ThreadPoolExecutor(12) as ex:
        resultados = list(ex.map(lambda t: (t, aplicar_tag(*t)), plano))
    resumo = {}
    for (tipo, _, chave, _), res in resultados:
        k = (tipo, "erro" if res.startswith("erro") else res)
        resumo[k] = resumo.get(k, 0) + 1
    for k, n in sorted(resumo.items()):
        print(f"   {k[0]:<8} {k[1]:<11} {n}")
    erros = [(t, r) for t, r in resultados if r.startswith("erro")]
    for t, r in erros[:10]:
        print("   ERRO", t, r)
    relatorio["tags"] = {f"{a}|{b}": n for (a, b), n in resumo.items()}

    if "--so-tags" not in sys.argv:
        print("== Pages")
        relatorio["pages"] = aplicar_pages(dominio_por_sub)
        for t, r in relatorio["pages"]:
            print(f"   {r:<11} {t}")
        print("== Wikis")
        relatorio["wikis"] = aplicar_wikis(audit)
        ok = sum(1 for _, r in relatorio["wikis"] if r == "publicada")
        print(f"   publicadas: {ok}/{len(relatorio['wikis'])}")
        for n, r in relatorio["wikis"]:
            if r != "publicada":
                print("  ", r, n)
    (AQUI / "semantica_aplicada.json").write_text(json.dumps(relatorio, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
