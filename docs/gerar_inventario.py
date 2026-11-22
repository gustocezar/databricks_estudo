#!/usr/bin/env python3
"""Gera docs/INVENTARIO.md: o retrato atual do projeto pos_venda, para a documentação acompanhar as mudanças.

  python3 docs/gerar_inventario.py                 projeto local + workspace (só leitura, pela API REST; não usa o warehouse)
  python3 docs/gerar_inventario.py --sem-workspace só o projeto local

Lê: scripts e bundles do repositório; schemas e objetos de `pos_venda` (tabelas, views, metric views); painéis, espaços
Genie, jobs e apps do domínio; e a última auditoria de metadados (`governanca/auditoria_metadados.json`).
Rode depois de cada mudança e registre no CHANGELOG o que o inventário mostrar de diferente.
"""
import ast
import datetime as dt
import json
import pathlib
import subprocess
import sys
from collections import Counter

RAIZ = pathlib.Path(__file__).resolve().parent.parent          # pasta pos_venda
PERFIL, CATALOGO = "dbx-workshop", "pos_venda"
IGNORAR = {"referencias", ".databricks", "resultados", "__pycache__", "src", ".venv", "venv", "site-packages"}


def cli(*args):
    r = subprocess.run(["databricks", *args, "--profile", PERFIL, "-o", "json"], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[:200])
    d = json.loads(r.stdout or "[]")
    return d


def lista(d, chave):
    return d if isinstance(d, list) else d.get(chave, [])


def resumo_script(p):
    texto = p.read_text(encoding="utf-8", errors="ignore")
    try:
        doc = ast.get_docstring(ast.parse(texto))
    except SyntaxError:
        doc = None
    if doc:
        return doc.strip().splitlines()[0]
    # notebook do Databricks: usa o título da primeira célula markdown
    return next((ln[len("# MAGIC # "):].strip() for ln in texto.splitlines() if ln.startswith("# MAGIC # ")), "")


def local():
    linhas = ["## Projeto local", "", "| Pasta | Script | Para quê |", "|---|---|---|"]
    for p in sorted(RAIZ.rglob("*.py")):
        rel = p.relative_to(RAIZ)
        if set(rel.parts) & IGNORAR or rel.parts[0] == "docs":
            continue
        linhas.append(f"| `{rel.parent}` | `{rel.name}` | {resumo_script(p).replace('|', '/')} |")
    linhas += ["", "| Bundle | Arquivo |", "|---|---|"]
    for p in sorted(RAIZ.rglob("databricks.yml")):
        rel = p.relative_to(RAIZ)
        if not set(rel.parts) & {".databricks"}:
            nome = next((ln.split(":", 1)[1].strip() for ln in p.read_text(encoding="utf-8").splitlines()
                         if ln.strip().startswith("name:")), "?")
            linhas.append(f"| `{nome}` | `{rel}` |")
    return linhas


def workspace():
    linhas = ["## Workspace (Unity Catalog e recursos)", ""]
    try:
        schemas = [s["name"] for s in lista(cli("schemas", "list", CATALOGO), "schemas")]
    except RuntimeError as e:
        return linhas + [f"Não foi possível ler o workspace: {e}"]
    linhas += ["| Schema | Tabelas | Views | Metric views | Outros |", "|---|---|---|---|---|"]
    for s in sorted(schemas):
        if s == "information_schema":
            continue
        tipos = Counter(t.get("table_type", "?") for t in lista(cli("tables", "list", CATALOGO, s), "tables"))
        tab = tipos.pop("MANAGED", 0) + tipos.pop("EXTERNAL", 0)
        vw, mv = tipos.pop("VIEW", 0), tipos.pop("METRIC_VIEW", 0)
        outros = ", ".join(f"{k} {v}" for k, v in tipos.items()) or "—"
        linhas.append(f"| `{s}` | {tab} | {vw} | {mv} | {outros} |")

    paineis = [d for d in lista(cli("lakeview", "list"), "dashboards") if d.get("display_name", "").startswith("pos_venda")]
    linhas += ["", "### Painéis AI/BI", "", "| Painel | ID |", "|---|---|"]
    linhas += [f"| {d['display_name']} | `{d['dashboard_id']}` |" for d in sorted(paineis, key=lambda x: x["display_name"])]

    espacos = [g for g in lista(cli("genie", "list-spaces"), "spaces") if "Pós-venda" in g.get("title", "")]
    linhas += ["", "### Espaços Genie", "", "| Espaço | ID |", "|---|---|"]
    linhas += [f"| {g['title']} | `{g['space_id']}` |" for g in sorted(espacos, key=lambda x: x["title"])]

    jobs = [j for j in lista(cli("jobs", "list"), "jobs") if "pos_venda" in j.get("settings", {}).get("name", "")]
    linhas += ["", "### Jobs", "", "| Job | ID | Agenda |", "|---|---|---|"]
    for j in sorted(jobs, key=lambda x: x["settings"]["name"]):
        ag = j["settings"].get("schedule", {}).get("pause_status", "sem agenda")
        linhas.append(f"| {j['settings']['name']} | `{j['job_id']}` | {ag} |")

    apps = lista(cli("apps", "list"), "apps")
    linhas += ["", "### Apps do workspace (o Free Edition permite 3; o dqx-studio para sozinho após 24 h)", "",
               "| App | Estado |", "|---|---|"]
    linhas += [f"| {a['name']} | {a.get('compute_status', {}).get('state', '?')} |" for a in apps]
    return linhas


def auditoria():
    arq = RAIZ / "governanca" / "auditoria_metadados.json"
    if not arq.exists():
        return ["## Metadados", "", "Sem auditoria: rode `python3 governanca/auditar_metadados.py`."]
    a = json.loads(arq.read_text(encoding="utf-8"))
    quando = dt.datetime.fromtimestamp(arq.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
    cols = desc = tabs = 0
    for s in a.get("schemas", []):
        if s.get("grupo", "principal") != "principal":
            continue
        for t in s.get("tabelas", []):
            tabs += 1
            for c in t.get("colunas", []):
                cols += 1
                desc += bool(c.get("comentario"))
    pct = f"{100 * desc / cols:.0f}%" if cols else "—"
    return ["## Metadados (última auditoria)", "", f"Auditoria de {quando}: {tabs} tabelas e views nas camadas principais, "
            f"{desc} de {cols} colunas descritas ({pct}). Detalhe em `governanca/auditar_metadados.py`."]


def main():
    agora = dt.datetime.now().strftime("%d/%m/%Y %H:%M")
    out = ["# Inventário · pos_venda", "",
           f"> Gerado por `docs/gerar_inventario.py` em {agora}. Não edite à mão: rode o script de novo.", ""]
    out += local() + [""]
    if "--sem-workspace" not in sys.argv:
        out += workspace() + [""]
    out += auditoria() + [""]
    (RAIZ / "docs" / "INVENTARIO.md").write_text("\n".join(out), encoding="utf-8")
    print(f"docs/INVENTARIO.md atualizado ({len(out)} linhas)")


if __name__ == "__main__":
    main()
