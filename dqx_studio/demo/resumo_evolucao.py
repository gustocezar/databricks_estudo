#!/usr/bin/env python3
"""Monta a evolucao semana a semana a partir do historico do DQX Studio (execucoes com TODAS as linhas das janelas).

  python3 resumo_evolucao.py      -> imprime a tabela em Markdown e grava ../regras/resultados/evolucao_studio.json

As execucoes de cada destino sao ordenadas pela data de criacao e numeradas como ciclos 1..5. Ficam de fora as execucoes
marcadas como "False positive" no Studio e o teste inicial da quarentena (comentado no app).
"""
import json
import pathlib
import sys

AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "regras"))
import carregar_regras as cr  # noqa: E402

DESTINOS = ["v_bronze_eventos_janela", "v_quarentena_janela", "v_silver_eventos_aptos_janela",
            "v_silver_hist_janela", "v_fato_snapshot_janela"]
SEMANAS = ["20–26/11", "27/11–03/12", "04–10/12", "11–17/12", "18–24/12"]
IGNORAR = {"a4ea8b1b7e054eb3"}          # teste inicial da quarentena (janela do ciclo 3), comentado no app


def revisao(run_id):
    st, r = cr.api("GET", f"/api/v1/runs/{run_id}/review-status")
    return (r or {}).get("status") if st == 200 else None


def coletar():
    st, runs = cr.api("GET", "/api/v1/dryrun/runs?limit=500")
    por = {d: [] for d in DESTINOS}
    for r in runs:
        d = r["source_table_fqn"].split(".")[-1]
        if d in por and r["status"] == "SUCCESS" and not r.get("sample_size") and r["run_id"] not in IGNORAR:
            por[d].append(r)
    out = {}
    for d, lst in por.items():
        lst = sorted((r for r in lst if revisao(r["run_id"]) != "False positive"), key=lambda r: r["created_at"])
        out[d] = []
        for i, r in enumerate(lst[:5]):
            st, res = cr.api("GET", f"/api/v1/dryrun/runs/{r['run_id']}/results")
            regras = sorted(((x["error"], x.get("error_count") or 0, x.get("warning_count") or 0) for x in (res or {}).get("error_summary") or []),
                            key=lambda x: -(x[1] * 10 ** 9 + x[2]))
            out[d].append({"ciclo": i + 1, "semana": SEMANAS[i], "run_id": r["run_id"], "linhas": r["total_rows"],
                           "erro": r["error_rows"], "aviso": r["warning_rows"],
                           "regras": [{"regra": a, "erro": b, "aviso": c} for a, b, c in regras]})
    return out


def markdown(ev):
    def pct(a, b):
        return f"{100 * a / b:.2f}%".replace(".", "§") if b else "–"     # virgula decimal (pt-BR) no fim
    linhas = ["| Ciclo | Semana | Bronze: linhas · erro · aviso | Quarentena: linhas = erro | Silver aptos: erro · aviso | Fato: linhas · erro |",
              "|---|---|---|---|---|---|"]
    for i in range(5):
        def g(d):
            return ev[d][i] if i < len(ev[d]) else None
        b, q, s, f = g("v_bronze_eventos_janela"), g("v_quarentena_janela"), g("v_silver_eventos_aptos_janela"), g("v_fato_snapshot_janela")
        linhas.append(
            f"| {i + 1} | {SEMANAS[i]} | "
            + (f"{b['linhas']:,} · **{b['erro']:,}** ({pct(b['erro'], b['linhas'])}) · {b['aviso']:,}" if b else "–") + " | "
            + (f"{q['linhas']:,} = {q['erro']:,}" if q else "–") + " | "
            + (f"**{s['erro']:,}** · {s['aviso']:,}" if s else "–") + " | "
            + (f"{f['linhas']:,} · **{f['erro']:,}**" if f else "–") + " |")
    linhas.append("")
    linhas.append("Regras com mais linhas por semana (erro/aviso):")
    linhas.append("")
    for d in ("v_bronze_eventos_janela", "v_silver_eventos_aptos_janela", "v_fato_snapshot_janela"):
        linhas.append(f"- **{d}**")
        for c in ev[d]:
            top = [f"{x['regra']} {x['erro'] or x['aviso']:,}{'' if x['erro'] else ' (aviso)'}" for x in c["regras"][:4]]
            linhas.append(f"  - semana {c['ciclo']} ({c['semana']}): " + ("; ".join(top) if top else "nenhuma violação"))
    return "\n".join(linhas).replace(",", ".").replace("§", ",")


if __name__ == "__main__":
    ev = coletar()
    (AQUI.parent / "regras" / "resultados" / "evolucao_studio.json").write_text(json.dumps(ev, indent=2, ensure_ascii=False), encoding="utf-8")
    print(markdown(ev))
