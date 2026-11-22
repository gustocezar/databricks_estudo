#!/usr/bin/env python3
"""Grava a descrição de cada coluna das camadas principais do pos_venda (dicionário descricoes_colunas.py).

  python3 aplicar_descricoes.py             todas as tabelas e views das camadas principais
  python3 aplicar_descricoes.py gold silver só os schemas informados
  python3 aplicar_descricoes.py legado      os schemas do medalhão legado (*_sql e *_ldp), com o mesmo dicionário

Estratégia por tipo de objeto (o Unity Catalog não aceita o mesmo comando em todos):
  1) tabela Delta: um ALTER TABLE ... ALTER COLUMN a COMMENT '...', b COMMENT '...' por tabela;
  2) se o comando em lote falhar, ou for streaming table / view: COMMENT ON COLUMN <obj>.<col> IS '...' por coluna.
Pula colunas que já têm a mesma descrição. Usa auditoria_metadados.json (rode auditar_metadados.py antes).
Obs.: views recriadas pelo job diário (pos_venda.dq.v_*) perdem as descrições a cada recriação.
"""
import json
import pathlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import descricoes_colunas as DC
import sql_util

AQUI = pathlib.Path(__file__).resolve().parent
PRINCIPAIS = ["landing", "fonte", "bronze", "silver", "gold", "dq"]
PARALELO = 6                   # comandos COMMENT simultâneos no caminho coluna a coluna
LEGADO = list(DC.LEGADO)       # bronze_sql, bronze_ldp, silver_sql, ... (substituídos pela carga diária)


def q(t):
    return "'" + t.replace("\\", "\\\\").replace("'", "\\'") + "'"


def main():
    args = sys.argv[1:]
    schemas = ([s for s in LEGADO] if "legado" in args else []) + [a for a in args if a in PRINCIPAIS + LEGADO]
    schemas = schemas or PRINCIPAIS
    audit = json.loads((AQUI / "auditoria_metadados.json").read_text(encoding="utf-8"))
    tot = {"tabelas": 0, "colunas": 0, "ja_tinham": 0, "lote": 0, "por_coluna": 0, "falhas": 0}
    falhas = []
    for s in audit["schemas"]:
        if s["nome"] not in schemas:
            continue
        for t in s["tabelas"]:
            curto = t["nome"].split(".", 1)[1]
            pend = []
            for c in t["colunas"]:
                d = DC.descricao(curto, c["nome"])
                if not d:
                    continue
                if (c.get("comentario") or "") == d:
                    tot["ja_tinham"] += 1
                    continue
                pend.append((c["nome"], d))
            if not pend:
                continue
            tot["tabelas"] += 1
            tot["colunas"] += len(pend)
            feito = False
            if t["tipo"] in ("MANAGED", "EXTERNAL"):
                lote = f"ALTER TABLE {t['nome']} ALTER COLUMN " + ", ".join(f"`{c}` COMMENT {q(d)}" for c, d in pend)
                try:
                    estado, erro, _ = sql_util.executar(lote)
                except sql_util.CotaEsgotada as e:
                    sys.exit(f"warehouse indisponível (cota diária do Free Edition): {e}")
                if estado == "SUCCEEDED":
                    tot["lote"] += len(pend)
                    feito = True
                    print(f"lote      {t['nome']:<60} {len(pend)} colunas", flush=True)
            if not feito:
                # um COMMENT por coluna leva ~5 s; em paralelo (PARALELO comandos) a materialized view sai em segundos
                def comentar(par, nome=t["nome"]):
                    c, d = par
                    for tentativa in range(4):
                        r = sql_util.executar(f"COMMENT ON COLUMN {nome}.`{c}` IS {q(d)}")
                        # objetos de pipeline recusam duas alterações ao mesmo tempo: espera e repete
                        if r[0] == "SUCCEEDED" or "CONCURRENT_UPDATE" not in r[1]:
                            break
                        time.sleep(3 * (tentativa + 1))
                    return c, r
                ok = 0
                try:
                    with ThreadPoolExecutor(max_workers=PARALELO) as pool:
                        for c, (estado, erro, _) in pool.map(comentar, pend):
                            if estado == "SUCCEEDED":
                                ok += 1
                            else:
                                falhas.append((t["nome"], c, erro[:200]))
                except sql_util.CotaEsgotada as e:
                    sys.exit(f"warehouse indisponível (cota diária do Free Edition): {e}")
                tot["por_coluna"] += ok
                tot["falhas"] += len(pend) - ok
                print(f"coluna    {t['nome']:<60} {ok}/{len(pend)} ({t['tipo']})", flush=True)
    print("RESULTADO:", json.dumps(tot, ensure_ascii=False))
    if falhas:
        tipos = {}
        for n, c, e in falhas:
            tipos.setdefault(e[:120], []).append(f"{n}.{c}")
        for e, cols in tipos.items():
            print(f"  falha ({len(cols)} colunas): {e}\n    ex.: {cols[0]}")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
