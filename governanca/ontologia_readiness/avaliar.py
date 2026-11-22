"""Avaliação de prontidão para a Genie Ontology (app genie-ontology-readiness v1.5.0), gravada no histórico.

Usa a rota que salva no histórico do Lakebase (`POST /api/assess/runs`), com a identidade de quem roda (token do CLI),
e guarda a resposta em JSON ao lado deste arquivo. O `GET /api/assess` não salva no histórico.

    python3 avaliar.py rodar <rotulo>        # avalia o catálogo pos_venda e salva avaliacao_<rotulo>.json
    python3 avaliar.py historico             # lista as avaliações gravadas no Lakebase (as suas)
    python3 avaliar.py comparar <id1> <id2>  # diferença por pilar entre duas avaliações do histórico
"""
import json
import subprocess
import sys
import time
from pathlib import Path

APP = "https://genie-ontology-readiness-7474645927052439.aws.databricksapps.com"
PERFIL = "dbx-workshop"
CATALOGOS = ["pos_venda"]
AQUI = Path(__file__).parent


def token():
    out = subprocess.run(["databricks", "auth", "token", "--profile", PERFIL, "-o", "json"],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)["access_token"]


def chamar(metodo, caminho, corpo=None, tempo=120):
    """curl (o Python do macOS pode não ter os certificados raiz); o token vai pela entrada padrão, fora da linha de comando."""
    cfg = f'header = "Authorization: Bearer {token()}"\nheader = "Content-Type: application/json"\n'
    cmd = ["curl", "-sS", "-f", "-m", str(tempo), "-X", metodo, "-K", "-", APP + caminho]
    if corpo is not None:
        cmd[-1:-1] = ["--data", json.dumps(corpo)]
    r = subprocess.run(cmd, input=cfg, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"{metodo} {caminho}: {r.stderr.strip()[:300]}")
    return r.stdout


def eventos(run_id, depois):
    """Uma janela SSE de eventos da execução (o app corta a janela e pede reconexão)."""
    texto = chamar("GET", f"/api/assess/runs/{run_id}/events?after={depois}", tempo=400)
    for linha in texto.splitlines():
        if linha.startswith("data: ") and linha[6:].strip() != "[DONE]":
            yield json.loads(linha[6:])


def rodar(rotulo):
    run_id = json.loads(chamar("POST", "/api/assess/runs", {"catalogs": CATALOGOS}))["run_id"]
    print("execução", run_id)
    depois, final, t0 = 0, None, time.time()
    while final is None and time.time() - t0 < 1800:
        fim = False
        for ev in eventos(run_id, depois):
            tipo = ev.get("type")
            if "seq" in ev:
                depois = ev["seq"] + 1
            if tipo == "pillar":
                p = ev["pillar"]
                print(f"  {p['key']:14} {p.get('score')}")
            elif tipo == "complete":
                final = ev
            elif tipo == "error":
                raise SystemExit(f"erro na avaliação: {json.dumps(ev)[:300]}")
            elif tipo == "reconnect":
                depois = ev.get("next", depois)
            elif tipo == "end":
                fim = True
        if fim and final is None:
            raise SystemExit("a execução terminou sem resultado")
    if final is None:
        raise SystemExit("tempo esgotado")
    resultado = {k: final[k] for k in ("overall", "pillars", "top_gaps")}
    resultado["historico"] = {"snapshot_id": final.get("snapshot_id"), "salvo": final.get("snapshot_saved"),
                              "escopo": final.get("scope")}
    arq = AQUI / f"avaliacao_{rotulo}.json"
    arq.write_text(json.dumps(resultado, ensure_ascii=False, indent=1))
    o = final["overall"]
    print(f"geral {o['score']} ({o['level_label']}) · histórico id={final.get('snapshot_id')} salvo={final.get('snapshot_saved')}")
    print("arquivo", arq.name)


def historico():
    for s in json.loads(chamar("GET", "/api/assess/history"))["snapshots"]:
        print(s.get("id"), s.get("created_at"), s.get("overall_score"), s.get("overall_level"), s.get("scope") or "")


def comparar(a, b):
    def pilares(i):
        sc = json.loads(chamar("GET", f"/api/assess/snapshot/{i}"))
        sc = sc.get("scorecard", sc)
        return sc["overall"]["score"], {p["key"]: p.get("score") for p in sc["pillars"]}
    ga, pa = pilares(a)
    gb, pb = pilares(b)
    for k in pa:
        print(f"  {k:14} {pa[k]!s:>6} -> {pb.get(k)!s:>6}")
    print(f"  {'geral':14} {ga!s:>6} -> {gb!s:>6}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "historico"
    if cmd == "rodar":
        rodar(sys.argv[2] if len(sys.argv) > 2 else time.strftime("%Y%m%d_%H%M"))
    elif cmd == "comparar":
        comparar(sys.argv[2], sys.argv[3])
    else:
        historico()
