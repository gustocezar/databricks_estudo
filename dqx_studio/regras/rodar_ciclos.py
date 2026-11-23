#!/usr/bin/env python3
"""Roda ciclos de carga (1 semana por ciclo) e, depois de cada um, executa as regras no DQX Studio.

  python3 -u rodar_ciclos.py 2 3 4 5            roda os ciclos 2 a 5 (job de carga + Studio)
  python3 -u rodar_ciclos.py 1 --so-studio       so as execucoes do Studio do ciclo 1 (a carga ja rodou)
  python3 -u rodar_ciclos.py 1 2 3 4 5 --replay  refaz o historico do Studio semana a semana, com TODAS as linhas:
                                                 aponta pos_venda.dq.janela_avaliacao para a semana do ciclo e avalia
                                                 as views pos_venda.dq.v_*_janela (um destino estavel por camada)
  python3 -u rodar_ciclos.py --dims              avalia as dimensoes e a silver atual inteiras (todas as linhas)

Observacao: o dry run do Studio le as PRIMEIRAS N linhas (df.limit), nao uma amostra aleatoria. Com amostra de 10 mil
linhas, problemas raros ou concentrados em alguns dias podem nao aparecer. Por isso o --replay usa sample_size=0
(convencao do app para "todas as linhas", a mesma das execucoes agendadas).

O Studio mede a qualidade RECENTE: as camadas que mudam no tempo sao avaliadas pelas janelas dos ultimos 7 dias
(pos_venda.dq.v_*_7d), e as dimensoes inteiras. Cada execucao grava metricas e a quarentena do Studio e fica no historico do app.
"""
import json
import pathlib
import subprocess
import sys
import time

import carregar_regras as cr
import definir_regras as dr

AQUI = pathlib.Path(__file__).resolve().parent
CARGA = AQUI.parent.parent / "carga_diaria"
sys.path.insert(0, str(CARGA))
import janela_avaliacao as ja  # noqa: E402
import views_preservadas as vp  # noqa: E402
CICLOS = {1: ("2026-11-20", "2026-11-26"), 2: ("2026-11-27", "2026-12-03"), 3: ("2026-12-04", "2026-12-10"),
          4: ("2026-12-11", "2026-12-17"), 5: ("2026-12-18", "2026-12-24"),
          6: ("2026-12-25", "2026-12-31"), 7: ("2027-01-01", "2027-01-07")}
# 6 e 7: catálogo de exemplos de todas as regras; seguem a grade semanal do painel (semanas a partir de 20/11)
G = "pos_venda.gold"
ALVOS = {   # o que o Studio executa  ->  de qual tabela vem o conjunto de regras
    "pos_venda.dq.v_bronze_eventos_7d": "pos_venda.bronze.pagamentos_pendentes_eventos",
    "pos_venda.dq.v_silver_pendencia_atual_7d": "pos_venda.silver.pendencia_atual",
    "pos_venda.dq.v_silver_pendencia_hist_7d": "pos_venda.silver.pendencia_hist",
    "pos_venda.dq.v_fato_snapshot_7d": f"{G}.fact_pagamento_pendente_snapshot",
    f"{G}.dim_cliente": f"{G}.dim_cliente", f"{G}.dim_apolice": f"{G}.dim_apolice", f"{G}.dim_corretor": f"{G}.dim_corretor",
    f"{G}.dim_ponto_venda": f"{G}.dim_ponto_venda", f"{G}.dim_produto": f"{G}.dim_produto", f"{G}.dim_data": f"{G}.dim_data",
    f"{G}.bridge_apolice_cobertura": f"{G}.bridge_apolice_cobertura",
}
ALVOS_JANELA = {   # replay semana a semana, todas as linhas (as 3 primeiras tem regras proprias cadastradas no Studio)
    "pos_venda.dq.v_bronze_eventos_janela": "pos_venda.dq.v_bronze_eventos_janela",
    "pos_venda.dq.v_silver_eventos_aptos_janela": "pos_venda.dq.v_silver_eventos_aptos_janela",
    "pos_venda.dq.v_fato_snapshot_janela": "pos_venda.dq.v_fato_snapshot_janela",
    "pos_venda.dq.v_quarentena_janela": "pos_venda.bronze.pagamentos_pendentes_eventos",
    "pos_venda.dq.v_silver_hist_janela": "pos_venda.silver.pendencia_hist",
}
ALVOS_INTEIROS = {"pos_venda.silver.pendencia_atual": "pos_venda.silver.pendencia_atual",
                  **{k: v for k, v in ALVOS.items() if k.startswith(G)}}


def sql(stmt, exigir=False):
    body = json.dumps({"warehouse_id": "5f010b8396e591fb", "statement": stmt, "wait_timeout": "50s", "on_wait_timeout": "CONTINUE"})
    r = json.loads(subprocess.run(["databricks", "api", "post", "/api/2.0/sql/statements", "--profile", "dbx-workshop", "--json", body],
                                  capture_output=True, text=True).stdout)
    t0 = time.time()
    while r.get("status", {}).get("state") in ("PENDING", "RUNNING") and time.time() - t0 < 300:
        time.sleep(4)
        r = json.loads(subprocess.run(["databricks", "api", "get", f"/api/2.0/sql/statements/{r['statement_id']}", "--profile", "dbx-workshop"],
                                      capture_output=True, text=True).stdout)
    if r["status"]["state"] != "SUCCEEDED":
        if exigir:
            raise RuntimeError(f"SQL falhou: {json.dumps(r.get('status'))[:600]}\n{stmt[:300]}")
        return []
    cols = [c["name"] for c in r.get("manifest", {}).get("schema", {}).get("columns", [])]   # DDL nao devolve colunas
    return [dict(zip(cols, row)) for row in r.get("result", {}).get("data_array", [])]


def rodar_job(ini, fim):
    print(f"  [job] carga {ini} -> {fim} ...", flush=True)
    t0 = time.time()
    r = subprocess.run(["databricks", "bundle", "run", "carga_diaria", "-t", "dev", "--profile", "dbx-workshop",
                        "--params", f"data_inicio={ini},data_fim={fim}"], cwd=CARGA, capture_output=True, text=True)
    out = r.stdout + r.stderr
    ok = "TERMINATED SUCCESS" in out
    print(f"  [job] {'OK' if ok else 'FALHOU'} em {int(time.time() - t0)}s", flush=True)
    if not ok:
        print(out[-2500:])
    return ok


def executar_studio(ciclo, alvos=ALVOS, amostra=10000, arquivo="studio", espera=1500):
    runs = {}
    for alvo, regras_de in alvos.items():
        st, r = cr.api("POST", "/api/v1/dryrun", {"table_fqn": alvo, "checks": dr.REGRAS[regras_de], "sample_size": amostra, "skip_history": False})
        if st == 200:
            runs[alvo] = r["run_id"]
        else:
            print(f"  [erro submeter] {alvo}: HTTP {st} {json.dumps(r)[:300]}", flush=True)
    resumo, pend, t0 = {}, dict(runs), time.time()
    while pend and time.time() - t0 < espera:
        time.sleep(20)
        for alvo, rid in list(pend.items()):
            st, s = cr.api("GET", f"/api/v1/dryrun/runs/{rid}/status")
            if st == 200 and (s.get("result_state") or s.get("state") in ("TERMINATED", "INTERNAL_ERROR")):
                st2, res = cr.api("GET", f"/api/v1/dryrun/runs/{rid}/results")
                res = res if st2 == 200 else {}
                resumo[alvo] = {"run_id": rid, "estado": s.get("result_state") or s.get("state"), "total": res.get("total_rows"),
                                "erro": res.get("error_rows"), "aviso": res.get("warning_rows"),
                                "regras_violadas": [{"regra": x.get("error"), "linhas": x.get("count"), "erro": x.get("error_count"),
                                                     "aviso": x.get("warning_count")} for x in (res.get("error_summary") or [])]}
                del pend[alvo]
    (AQUI / "resultados" / f"ciclo_{ciclo}_{arquivo}.json").write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  [studio] ciclo {ciclo}: {len(resumo)} execucoes concluidas, {len(pend)} pendentes", flush=True)
    for alvo, r in resumo.items():
        topo = sorted(r["regras_violadas"], key=lambda x: -(x["linhas"] or 0))[:3]
        print(f"     {alvo.split('.')[-1]:<30} {r['estado']:<8} total={r['total']} erro={r['erro']} aviso={r['aviso']}  "
              + "; ".join(f"{t['regra']}={t['linhas']}" for t in topo), flush=True)
    return resumo


def resumo_pipeline(ciclo, ini, fim):
    q = sql(f"""SELECT dia, eventos_recebidos, eventos_aptos, eventos_barrados, pct_barrados, eventos_duplicados, cpf_invalido, email_ausente,
                       cep_malformado, forma_pagamento_nao_cadastrada FROM pos_venda.gold.dq_qualidade_diaria
                WHERE dia BETWEEN DATE'{ini}' AND DATE'{fim}' ORDER BY dia""")
    b = sql(f"""SELECT motivo_rejeicao, sum(eventos) AS eventos FROM pos_venda.gold.dq_barrados_por_motivo_dia
                WHERE dia BETWEEN DATE'{ini}' AND DATE'{fim}' GROUP BY motivo_rejeicao ORDER BY 2 DESC""")
    (AQUI / "resultados" / f"ciclo_{ciclo}_pipeline.json").write_text(json.dumps({"diario": q, "barrados_por_motivo": b}, indent=2, ensure_ascii=False))
    tot = sum(int(x["eventos_recebidos"]) for x in q) or 1
    bar = sum(int(x["eventos_barrados"]) for x in q)
    print(f"  [pipeline] ciclo {ciclo}: {tot} eventos recebidos, {bar} barrados ({100 * bar / tot:.2f}%) | motivos: "
          + ", ".join(f"{x['motivo_rejeicao']}={x['eventos']}" for x in b[:6]), flush=True)


if __name__ == "__main__":
    (AQUI / "resultados").mkdir(exist_ok=True)
    so_studio = "--so-studio" in sys.argv
    if "--replay" in sys.argv or "--dims" in sys.argv:
        for stmt in ja.ddl():
            sql(stmt, exigir=True)
        # views da janela: recria só se a definição mudou (e devolve tags e Wiki); ver carga_diaria/views_preservadas.py
        for nome, comentario, consulta in ja.lista_views():
            print(nome, vp.garantir_view(nome, comentario, consulta, lambda q: sql(q, exigir=True), vp.api_cli("dbx-workshop")))
    if "--dims" in sys.argv:
        print("=== TABELAS INTEIRAS (silver atual + dimensoes) ===", flush=True)
        executar_studio("inteiras", ALVOS_INTEIROS, amostra=0, arquivo="studio_completo", espera=3600)
        sys.exit(0)
    if "--replay" in sys.argv:
        for n in [int(a) for a in sys.argv[1:] if a.isdigit()]:
            ini, fim = CICLOS[n]
            print(f"=== REPLAY CICLO {n}: janela {ini} -> {fim} (todas as linhas) ===", flush=True)
            sql(ja.apontar(f"DATE'{ini}'", f"DATE'{fim}'", f"replay ciclo {n}"), exigir=True)
            so = next((a.split("=", 1)[1].split(",") for a in sys.argv if a.startswith("--so=")), None)
            alvos = {k: v for k, v in ALVOS_JANELA.items() if not so or k.split(".")[-1] in so}
            executar_studio(n, alvos, amostra=0, arquivo="studio_completo" + ("_" + "_".join(so) if so else ""), espera=3600)
        sql(ja.APONTAR_ULTIMOS_7, exigir=True)      # devolve a janela ao padrao do job diario
        print("janela devolvida aos ultimos 7 dias carregados", flush=True)
        sys.exit(0)
    for n in [int(a) for a in sys.argv[1:] if a.isdigit()]:
        ini, fim = CICLOS[n]
        print(f"=== CICLO {n}: {ini} -> {fim} ===", flush=True)
        if not so_studio and not rodar_job(ini, fim):
            sys.exit(1)
        resumo_pipeline(n, ini, fim)
        executar_studio(n)
