#!/usr/bin/env python3
"""Carrega as regras de definir_regras.py no DQX Studio pela API e, opcionalmente, roda um dry run em cada tabela.

  python3 carregar_regras.py cadastrar     valida, salva, submete e aprova as regras (idempotente: pula tabelas que ja tem regras)
  python3 carregar_regras.py dryrun        roda um dry run (amostra de ate 10.000 linhas) em cada tabela e grava resultados/

Usa o token OAuth do Databricks CLI (perfil dbx-workshop). Nada e enviado para fora do seu workspace.
"""
import json
import pathlib
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request

import definir_regras as dr

AQUI = pathlib.Path(__file__).resolve().parent
PROFILE = "dbx-workshop"
URL = "https://dqx-studio-7474645927052439.aws.databricksapps.com"


def token():
    out = subprocess.check_output(["databricks", "auth", "token", "--profile", PROFILE, "-o", "json"])
    return json.loads(out)["access_token"]


TOKEN = token()
# o Python do python.org no macOS nao traz CAs; usa o pacote de certificados do sistema (verificacao continua ligada)
CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem")


def api(metodo, caminho, corpo=None, timeout=180, tentativas=8):
    global TOKEN
    for i in range(tentativas):
        try:
            st, r = _api(metodo, caminho, corpo, timeout)
            if st == 401 and i < tentativas - 1:      # o token OAuth do CLI vale ~1h: renova e tenta de novo
                TOKEN = token()
                continue
            return st, r
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:     # oscilacao de rede / handshake
            if i == tentativas - 1:
                raise
            time.sleep(5 * (i + 1))


def _api(metodo, caminho, corpo=None, timeout=180):
    req = urllib.request.Request(URL + caminho, method=metodo, data=None if corpo is None else json.dumps(corpo).encode(),
                                 headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            txt = r.read().decode()
            return r.status, (json.loads(txt) if txt else None)
    except urllib.error.HTTPError as e:
        txt = e.read().decode(errors="ignore")
        try:
            return e.code, json.loads(txt)
        except Exception:
            return e.code, txt[:400]


def _norm(ck):
    return json.dumps(ck, sort_keys=True, ensure_ascii=False)


def cadastrar(limpar=False):
    """No Studio cada check e uma regra separada (rule_id proprio). Cria/atualiza uma regra por check, submete e aprova."""
    for fq, checks in dr.REGRAS.items():
        nomes = [x["name"] for x in checks]
        assert len(nomes) == len(set(nomes)), f"nomes de check repetidos em {fq}"
    st, lista = api("GET", "/api/v1/rules")
    lista = lista if st == 200 and isinstance(lista, list) else []
    nossas = [e for e in lista if e["table_fqn"] in dr.REGRAS]
    if limpar:
        for e in nossas:
            api("DELETE", f"/api/v1/rules/{e['rule_id']}")
        print(f"removidas {len(nossas)} regras antigas")
        nossas = []
    # regras que deixaram de existir na definicao (mesma tabela, nome de check que sumiu) sao removidas do Studio
    definidas = {(fq, x["name"]) for fq, checks in dr.REGRAS.items() for x in checks}
    obsoletas = [e for e in nossas if e.get("checks") and (e["table_fqn"], e["checks"][0].get("name")) not in definidas]
    for e in obsoletas:
        st, _ = api("DELETE", f"/api/v1/rules/{e['rule_id']}")
        print(f"  removida (obsoleta): {e['table_fqn']} :: {e['checks'][0].get('name')} -> HTTP {st}")
    nossas = [e for e in nossas if e not in obsoletas]
    existentes = {}
    for e in nossas:
        if e.get("checks"):
            existentes.setdefault((e["table_fqn"], e["checks"][0].get("name")), []).append(e)
    tot = {"criadas": 0, "atualizadas": 0, "iguais": 0, "erros": 0}
    for fq, checks in dr.REGRAS.items():
        c_ = {"criadas": 0, "atualizadas": 0, "iguais": 0, "erros": 0}
        for ck in checks:
            cand = existentes.get((fq, ck["name"]), [])
            aprovada = next((e for e in cand if e["status"] == "approved"), None)
            if aprovada and _norm(aprovada["checks"][0]) == _norm(ck):
                c_["iguais"] += 1
                continue
            corpo = {"table_fqn": fq, "checks": [ck], "source": "import"}
            if cand:
                corpo["rule_id"] = cand[0]["rule_id"]
            st, saved = api("POST", "/api/v1/rules", corpo)
            if st != 200 or not saved:
                c_["erros"] += 1
                print(f"   [ERRO salvar] {fq}/{ck['name']}: HTTP {st} {json.dumps(saved)[:240]}")
                continue
            ok = True
            for ent in saved:
                s1, r1 = api("POST", f"/api/v1/rules/{ent['rule_id']}/submit", {"status": "pending_approval"})
                s2, r2 = api("POST", f"/api/v1/rules/{ent['rule_id']}/approve", {"status": "approved"})
                if s1 != 200 or s2 != 200:
                    ok = False
                    print(f"   [ERRO fluxo] {fq}/{ck['name']}: submit={s1} {json.dumps(r1)[:160]} | approve={s2} {json.dumps(r2)[:160]}")
            c_["erros" if not ok else ("atualizadas" if cand else "criadas")] += 1
        for k in tot:
            tot[k] += c_[k]
        print(f"  {fq}: {len(checks)} regras | {c_}")
    print("TOTAL:", tot)


def dryrun():
    (AQUI / "resultados").mkdir(exist_ok=True)
    runs = {}
    for fq, checks in dr.REGRAS.items():
        st, r = api("POST", "/api/v1/dryrun", {"table_fqn": fq, "checks": checks, "sample_size": 10000, "skip_history": False})
        if st == 200:
            runs[fq] = r["run_id"]
            print(f"  submetido {fq}: run_id={r['run_id']}")
        else:
            print(f"  [ERRO] {fq}: HTTP {st} {json.dumps(r)[:400]}")
    pend = dict(runs)
    t0 = time.time()
    resultados = {}
    while pend and time.time() - t0 < 1500:
        time.sleep(20)
        for fq, rid in list(pend.items()):
            st, s = api("GET", f"/api/v1/dryrun/runs/{rid}/status")
            estado = (s or {}).get("state") if st == 200 else f"HTTP {st}"
            if estado in ("TERMINATED", "SKIPPED", "INTERNAL_ERROR", "SUCCESS", "FAILED", "CANCELED") or (s or {}).get("result_state"):
                st2, res = api("GET", f"/api/v1/dryrun/runs/{rid}/results")
                resultados[fq] = {"status": s, "resultado": res if st2 == 200 else {"http": st2, "corpo": res}}
                (AQUI / "resultados" / f"{fq}.json").write_text(json.dumps(resultados[fq], indent=2, ensure_ascii=False), encoding="utf-8")
                r = resultados[fq]["resultado"]
                print(f"  concluido {fq}: estado={estado}/{(s or {}).get('result_state')} total={r.get('total_rows')} validas={r.get('valid_rows')} "
                      f"erro={r.get('error_rows')} aviso={r.get('warning_rows')}")
                del pend[fq]
        print(f"   ...aguardando {len(pend)} execucoes ({int(time.time()-t0)}s)")
    return resultados


if __name__ == "__main__":
    acao = sys.argv[1] if len(sys.argv) > 1 else "cadastrar"
    if acao == "cadastrar":
        cadastrar(limpar="--limpar" in sys.argv)
    else:
        dryrun()
