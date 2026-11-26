"""Valida a documentação do pos_venda: contagens, referências P##/L##, campos das práticas, gatilhos, links e fases.

    python3 docs/validar_docs.py     # sai com 1 se alguma checagem falhar (roda no CI, sem rede)

Confere o que dá para conferir sem rede: o que cada documento afirma ("41 práticas", "97 lições", "30 fases") contra o
que existe em 04_FRAMEWORK.md, 03_LICOES_APRENDIDAS.md e 01_TRILHA_DE_APRENDIZAGEM.md, e se cada P## e L## citado existe.
"""
from __future__ import annotations

import os
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
DOCS = RAIZ / "docs"
FORA = ("referencias", ".venv", "node_modules", ".git")
CAMPOS_P = ("**Origem:**", "**Como aplicamos:**", "**Por quê:**", "**Reaplique quando:**", "**Prova")


def mds():
    for p in RAIZ.rglob("*.md"):
        if not any(x in p.parts for x in FORA):
            yield p


def main():
    falhas = []

    def check(nome, ok, det=""):
        print(f"{'ok   ' if ok else 'FALHA'} {nome}{': ' + det if det else ''}")
        if not ok:
            falhas.append(nome)

    fw = (DOCS / "04_FRAMEWORK.md").read_text(encoding="utf-8")
    lic = (DOCS / "03_LICOES_APRENDIDAS.md").read_text(encoding="utf-8")
    tri = (DOCS / "01_TRILHA_DE_APRENDIZAGEM.md").read_text(encoding="utf-8")

    # práticas
    blocos = re.split(r"\n(?=### P\d{2} · )", fw)
    praticas = {re.match(r"### (P\d{2})", b).group(1): b for b in blocos if re.match(r"### P\d{2} · ", b)}
    nums = sorted(int(p[1:]) for p in praticas)
    check("práticas numeradas de P01 sem buraco", nums == list(range(1, len(nums) + 1)), f"{len(nums)} práticas")
    sem_campo = [p for p, b in praticas.items() if not all(c in b for c in CAMPOS_P)]
    check("toda prática com origem, como, por quê, reaplique e prova", not sem_campo, f"faltando em {sem_campo}" if sem_campo else "")
    mapa = fw.split("## Mapa de gatilhos", 1)[1].split("\n---", 1)[0] if "## Mapa de gatilhos" in fw else ""
    no_mapa = set(re.findall(r"P\d{2}", mapa))
    for a_, b_ in re.findall(r"P(\d{2}) a P(\d{2})", mapa):      # faixas como "P24 a P26"
        no_mapa |= {f"P{i:02d}" for i in range(int(a_), int(b_) + 1)}
    fora_mapa = sorted(set(praticas) - no_mapa)
    check("toda prática no mapa de gatilhos", not fora_mapa, f"fora: {fora_mapa}" if fora_mapa else "")

    # lições
    ls = [int(x) for x in re.findall(r"^- \*\*L(\d+)\*\*", lic, re.M)]
    check("lições sem número repetido", len(ls) == len(set(ls)), f"{len(ls)} lições")
    check("lições de L01 sem buraco", sorted(ls) == list(range(1, max(ls) + 1)), f"maior L{max(ls)}")

    # fases
    fases = [int(x) for x in re.findall(r"^## Fase (\d+) ·", tri, re.M)]
    check("fases da trilha de 0 sem buraco", sorted(fases) == list(range(0, max(fases) + 1)), f"{len(fases)} fases (0 a {max(fases)})")

    # o que os documentos afirmam
    afirma = []
    for p in mds():
        t = p.read_text(encoding="utf-8")
        rel = p.relative_to(RAIZ)
        if "CHANGELOG" in p.name:
            continue      # o CHANGELOG guarda os números de cada dia, de propósito
        t = re.sub(r'"[^"\n]*"', "", t)      # citação entre aspas (como a da L99) não é afirmação
        for n in re.findall(r"\*\*(\d+) práticas\*\*|(?<![\d.])(\d+) práticas (?:aplicadas|\(`P##`\))|as (\d+) práticas", t):
            v = int(next(x for x in n if x))
            if v != len(praticas):
                afirma.append(f"{rel}: {v} práticas")
        for n in re.findall(r"(?<![\d.])(\d+) lições", t):
            if int(n) not in (len(ls),) and int(n) > 20:
                afirma.append(f"{rel}: {n} lições")
        for a, b in re.findall(r"fases (\d+) a (\d+)", t):
            if (int(a), int(b)) != (0, max(fases)) and int(a) == 0:
                afirma.append(f"{rel}: fases {a} a {b}")
    check("contagens afirmadas = contagens reais", not afirma, "; ".join(afirma[:6]))

    # referências P## e L## citadas existem
    ruins = []
    for p in mds():
        t = p.read_text(encoding="utf-8")
        for x in set(re.findall(r"\bP(\d{2})\b", t)):
            if int(x) > len(praticas):
                ruins.append(f"{p.relative_to(RAIZ)}: P{x}")
        for x in set(re.findall(r"\bL(\d{2,3})\b", t)):
            if int(x) > max(ls):
                ruins.append(f"{p.relative_to(RAIZ)}: L{x}")
    check("todo P## e L## citado existe", not ruins, "; ".join(sorted(ruins)[:6]))

    # links relativos
    quebrados = []
    for p in mds():
        if "modelos" in p.parts:
            continue      # os modelos do spec valem a partir da pasta da base
        for alvo in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", p.read_text(encoding="utf-8")):
            if not alvo.startswith(("http", "mailto")) and not os.path.exists(os.path.normpath(os.path.join(p.parent, alvo))):
                quebrados.append(f"{p.relative_to(RAIZ)}: {alvo}")
    check("links relativos resolvem", not quebrados, "; ".join(quebrados[:5]))

    # CHANGELOG: toda entrada com conferência
    ch = (DOCS / "CHANGELOG.md").read_text(encoding="utf-8")
    # a convenção de registrar a conferência vale desde 21/11/2026; as entradas de 20/11 criaram a documentação
    sem_conf = []
    for dia in re.split(r"\n(?=## \d{2}/\d{2}/\d{4})", ch)[1:]:
        d, m, a = map(int, re.match(r"## (\d{2})/(\d{2})/(\d{4})", dia).groups())
        if (a, m, d) < (2026, 11, 21):
            continue
        for e in re.split(r"\n(?=### )", dia)[1:]:
            if not re.search(r"\*\*(Conferência|Resultado|Prova)", e):
                sem_conf.append(e.splitlines()[0][:60])
    check("toda entrada do CHANGELOG com conferência", not sem_conf, f"sem: {sem_conf[:3]}" if sem_conf else "")

    # modelo de dados: toda base com documento
    md = DOCS / "modelo_dados"
    check("modelo de dados gerado", (md / "README.md").exists() and len(list(md.glob("*.md"))) >= 10,
          f"{len(list(md.glob('*.md')))} documentos em docs/modelo_dados")

    print(f"\n{'documentação ok' if not falhas else str(len(falhas)) + ' checagem(ns) falharam'}")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
