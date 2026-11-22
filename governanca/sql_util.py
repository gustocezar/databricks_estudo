"""Execução de SQL no warehouse do projeto pelo CLI (perfil dbx-workshop), com detecção da cota diária do Free Edition."""
import json
import subprocess
import sys
import time

PERFIL, WAREHOUSE = "dbx-workshop", "5f010b8396e591fb"


class CotaEsgotada(Exception):
    pass


def executar(sql, catalogo=None, schema=None, espera=600):
    """Retorna (estado, mensagem_de_erro, linhas: list[dict])."""
    corpo = {"warehouse_id": WAREHOUSE, "statement": sql, "wait_timeout": "50s", "on_wait_timeout": "CONTINUE"}
    if catalogo:
        corpo.update({"catalog": catalogo, "schema": schema})
    for tentativa in range(4):
        out = subprocess.run(["databricks", "api", "post", "/api/2.0/sql/statements", "--profile", PERFIL, "--json", json.dumps(corpo)],
                             capture_output=True, text=True)
        if out.stdout.strip():
            break
        msg = (out.stderr or "").strip()
        if "free daily limit" in msg or "could not be processed by the warehouse" in msg:
            raise CotaEsgotada(msg[:200])
        time.sleep(5 * (tentativa + 1))
    else:
        return "FAILED", f"chamada falhou: {msg[:300]}", []
    r = json.loads(out.stdout)
    t0 = time.time()
    while r.get("status", {}).get("state") in ("PENDING", "RUNNING") and time.time() - t0 < espera:
        time.sleep(3)
        o = subprocess.run(["databricks", "api", "get", f"/api/2.0/sql/statements/{r['statement_id']}", "--profile", PERFIL],
                           capture_output=True, text=True).stdout
        if o.strip():
            r = json.loads(o)
    estado = r.get("status", {}).get("state", "FAILED")
    erro = r.get("status", {}).get("error", {}).get("message", "")
    cols = [c["name"] for c in r.get("manifest", {}).get("schema", {}).get("columns", [])]
    linhas = [dict(zip(cols, x)) for x in (r.get("result", {}) or {}).get("data_array", []) or []]
    return estado, erro, linhas


def executar_lista(comandos, rotulo=lambda s: s.splitlines()[0][:90]):
    falhas = 0
    for s in comandos:
        try:
            estado, erro, _ = executar(s)
        except CotaEsgotada as e:
            sys.exit(f"warehouse indisponível (cota diária do Free Edition): {e}")
        falhas += estado != "SUCCEEDED"
        print(f"{estado:<10} {rotulo(s)}" + (f"\n           {erro[:400]}" if estado != "SUCCEEDED" else ""), flush=True)
    return falhas
