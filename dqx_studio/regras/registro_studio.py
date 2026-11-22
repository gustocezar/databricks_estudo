#!/usr/bin/env python3
"""Leva as regras do pos_venda para o Registro de Regras e as Tabelas Monitoradas do DQX Studio (o que o menu do app mostra).

  python3 registro_studio.py planejar   mostra os modelos e as aplicações (não grava nada)
  python3 registro_studio.py aplicar    cria os modelos (aprovados), registra as tabelas, aplica, publica
  python3 registro_studio.py executar   executa cada tabela monitorada com todas as linhas (aparece em Resultados)
  ... aplicar|executar <tabela> [...]    só as tabelas informadas (nome curto, ex.: v_bronze_eventos_janela); as outras
                                        ficam como estão (regra nova sem republicar as 12)
  python3 registro_studio.py agendar    agenda as 12 tabelas para 06:30 (Brasília), depois da carga das 05:00, e deixa PAUSADO
  python3 registro_studio.py ligar      despausa os agendamentos (faça junto com a agenda do job pos_venda_carga_diaria)
  python3 registro_studio.py pausar     pausa os agendamentos
  python3 registro_studio.py agenda     mostra o estado dos agendamentos (próxima e última execução)

Ideia: cada checagem de definir_regras.py vira a APLICAÇÃO de um MODELO reutilizável do Registro.
  - modelo = função DQX + parâmetros fixos (lista de valores, limites, tabela de referência...) + slots de coluna;
  - aplicação = modelo + mapeamento slot -> coluna(s) numa tabela monitorada (várias colunas = vários grupos).
Ex.: "Campo obrigatório preenchido" (is_not_null) é UM modelo aplicado a 63 colunas em 12 tabelas.
Idempotente: reaproveita modelos iguais (skip_duplicates) e tabelas já registradas.
"""
import collections
import json
import sys
import time

import carregar_regras as cr
import definir_regras as dr

ALVOS = ["pos_venda.dq.v_bronze_eventos_janela", "pos_venda.dq.v_silver_eventos_aptos_janela", "pos_venda.dq.v_fato_snapshot_janela",
         "pos_venda.silver.pendencia_atual", "pos_venda.silver.pendencia_hist"] + \
        [f"pos_venda.gold.{t}" for t in ["dim_cliente", "dim_apolice", "dim_corretor", "dim_ponto_venda", "dim_produto", "dim_data",
                                         "bridge_apolice_cobertura"]]
DIMENSAO = {"is_not_null": "Completeness", "is_not_null_and_not_empty": "Completeness", "is_unique": "Uniqueness",
            "foreign_key": "Consistency", "sql_expression": "Consistency"}
TIPO_PARAM = {"allowed": "list", "ref_columns": "list", "ref_table": "ref_table", "regex": "regex", "case_sensitive": "boolean",
              "limit": "number", "min_limit": "number", "max_limit": "number", "msg": "string"}


def nome_generico(f, crit, params):
    if f == "is_not_null":
        return "Campo obrigatório preenchido" if crit == "error" else "Campo recomendado preenchido (aviso)"
    if f == "is_unique":
        return "Chave única" if crit == "error" else "Registro sem duplicata (aviso)"
    if f == "foreign_key":
        return f"Chave existe em {params['ref_table'].split('.')[-1]}"
    if f == "is_not_less_than":
        return f"Valor mínimo {params['limit']}"
    return None


def modelo_e_grupo(check):
    """Devolve (chave do modelo, definição para o Registro, grupo de mapeamento slot -> coluna)."""
    f, args, crit = check["check"]["function"], dict(check["check"]["arguments"]), check["criticality"]
    filtro = check.get("filter")
    if f == "sql_expression":
        params = {"msg": args["msg"]} if args.get("msg") else {}
        chave = ("sql", check["name"], args["expression"], crit, filtro)
        nome = check["name"]
        definicao = {"mode": "sql", "polarity": "pass",
                     "definition": {"body": {"predicate": args["expression"]}, "slots": [],
                                    "parameters": [{"name": k, "type": TIPO_PARAM[k], "value": v} for k, v in params.items()],
                                    **({"filter": filtro} if filtro else {})}}
        return chave, nome, definicao, {}
    corpo, slots, grupo = {}, [], {}
    if "column" in args:
        corpo["column"] = "{{coluna}}"
        slots.append({"name": "coluna", "family": "any", "position": 0, "cardinality": "one", "arg_key": "column"})
        grupo["coluna"] = args.pop("column")
    if "columns" in args:
        corpo["columns"] = "{{colunas}}"
        slots.append({"name": "colunas", "family": "any", "position": len(slots), "cardinality": "many", "arg_key": "columns"})
        grupo["colunas"] = ",".join(args.pop("columns"))
    params = dict(sorted(args.items()))
    generico = nome_generico(f, crit, params)
    chave = ("native", generico or check["name"], f, crit, json.dumps(params, sort_keys=True, ensure_ascii=False), filtro)
    nome = generico or check["name"]
    definicao = {"mode": "dqx_native", "polarity": None,
                 "definition": {"body": {"function": f, "arguments": corpo}, "slots": slots,
                                "parameters": [{"name": k, "type": TIPO_PARAM.get(k, "string"), "value": v} for k, v in params.items()],
                                **({"filter": filtro} if filtro else {})}}
    return chave, nome, definicao, grupo


def planejar():
    modelos, aplicacoes = {}, collections.defaultdict(lambda: collections.defaultdict(list))
    for t in ALVOS:
        for c in dr.REGRAS[t]:
            chave, nome, definicao, grupo = modelo_e_grupo(c)
            if chave not in modelos:
                f = c["check"]["function"]
                modelos[chave] = {**definicao, "author_kind": "human", "allow_duplicate": True, "user_metadata": {
                    "name": nome, "description": f"Pós-venda: {c['name']}" + (f" — {c['check']['arguments'].get('msg')}" if f == "sql_expression" else ""),
                    "dimension": DIMENSAO.get(f, "Validity"), "severity": "High" if c["criticality"] == "error" else "Medium",
                    "dominio": "pos_venda"}}
                modelos[chave]["_origem"] = t.split(".")[-1]
            if grupo not in aplicacoes[t][chave]:
                aplicacoes[t][chave].append(grupo)
    # nomes repetidos (mesmo nome, definição diferente): acrescenta a tabela de origem para distinguir na tela
    nomes = collections.Counter(m["user_metadata"]["name"] for m in modelos.values())
    for m in modelos.values():          # variações nomeadas pela diferença real
        nome = m["user_metadata"]["name"]
        if nomes[nome] > 1:
            params = {p["name"]: p["value"] for p in m["definition"]["parameters"]}
            if params.get("case_sensitive") is False:
                m["user_metadata"]["name"] = f"{nome} (aceita minúsculas)"
            elif m["definition"].get("filter"):
                m["user_metadata"]["name"] = f"{nome} (com filtro)"
    vistos = collections.Counter()
    for k, m in modelos.items():
        nome = m["user_metadata"]["name"]
        vistos[nome] += 1
        if vistos[nome] > 1:
            m["user_metadata"]["name"] = f"{nome} ({m['_origem']})"
    for m in modelos.values():
        m.pop("_origem", None)
    return modelos, aplicacoes


def listar(caminho):
    st, r = cr.api("GET", caminho)
    if st != 200:
        raise RuntimeError(f"GET {caminho}: {st} {str(r)[:300]}")
    return r if isinstance(r, list) else r.get("items", r.get("rules", r.get("tables", [])))


def _escolher(nomes):
    """Tabelas monitoradas pelo nome curto (ex.: v_bronze_eventos_janela); sem nomes = todas."""
    if not nomes:
        return list(ALVOS)
    escolhidas = [t for t in ALVOS if t.split(".")[-1] in nomes]
    faltam = set(nomes) - {t.split(".")[-1] for t in escolhidas}
    if faltam:
        sys.exit(f"tabelas não monitoradas: {sorted(faltam)}")
    return escolhidas


def aplicar(nomes=()):
    alvos = _escolher(nomes)
    modelos, aplicacoes = planejar()
    chaves = list(modelos)
    existentes_nome = {(x.get("user_metadata") or {}).get("name"): x["rule_id"] for x in listar("/api/v1/registry-rules")
                       if (x.get("user_metadata") or {}).get("dominio") == "pos_venda"}
    rule_id = {k: existentes_nome[modelos[k]["user_metadata"]["name"]] for k in chaves if modelos[k]["user_metadata"]["name"] in existentes_nome}
    novos = [k for k in chaves if k not in rule_id]
    corpo = {"rules": [modelos[k] for k in novos] or [modelos[chaves[0]]], "also_submit": True, "auto_approve": True,
             "skip_duplicates": False, "source": "import"}
    chaves = novos
    st, r = cr.api("POST", "/api/v1/registry-rules/batch-import", corpo, timeout=600)
    if st != 200:
        sys.exit(f"batch-import: HTTP {st} {json.dumps(r, ensure_ascii=False)[:800]}")
    for item in (r.get("created") or []) + (r.get("reused") or []) if novos else []:
        rule_id[chaves[item["input_index"]]] = item["rule"]["rule_id"]
    print(f"Registro: {len(r.get('created') or [])} modelos criados, {len(r.get('reused') or [])} reaproveitados, "
          f"{len(r.get('failed') or [])} falhas")
    for falha in r.get("failed") or []:
        print("   FALHA", modelos[chaves[falha["index"]]]["user_metadata"]["name"], "->", falha["error"][:200])
    chaves = list(modelos)
    status = {x["rule_id"]: x.get("status") for x in listar("/api/v1/registry-rules")}
    print("   status dos modelos:", collections.Counter(status.get(v) for v in rule_id.values()))

    existentes = {}
    for m in listar("/api/v1/monitored-tables"):
        tab = m.get("table", m)
        existentes[tab.get("table_fqn")] = tab.get("binding_id")
    ids = {}
    for t in alvos:
        bid = existentes.get(t)
        if not bid:
            st, r = cr.api("POST", "/api/v1/monitored-tables", {"table_fqn": t})
            if st != 200:
                print(f"   registrar {t}: HTTP {st} {str(r)[:300]}")
                continue
            bid = (r.get("table") or r)["binding_id"]
        ids[t] = bid
        apps = [{"rule_id": rule_id[k], "column_mapping": grupos} for k, grupos in aplicacoes[t].items() if k in rule_id]
        st, r = cr.api("PUT", f"/api/v1/monitored-tables/{bid}/applied-rules", {"applications": apps}, timeout=600)
        ok_apply = st == 200
        st2, r2 = cr.api("POST", f"/api/v1/monitored-tables/{bid}/submit", timeout=600)
        st3, r3 = cr.api("POST", f"/api/v1/monitored-tables/{bid}/approve", {"rationale": "Regras do domínio Pós-venda (migração)"}, timeout=600)
        n_checks = sum(len(g) for g in aplicacoes[t].values())
        print(f"{t.split('.', 1)[1]:<38} {len(apps):>2} modelos / {n_checks:>3} checagens | aplicar {st} | submeter {st2} | aprovar {st3}"
              + ("" if ok_apply else f"  {str(r)[:200]}") + ("" if st3 == 200 else f"  {str(r3)[:200]}"))
    arq = cr.AQUI / "resultados" / "registro_studio.json"
    todos = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {}
    arq.write_text(json.dumps({**todos, **ids}, indent=1), encoding="utf-8")   # mescla: aplicar parcial não perde as outras


def limpar():
    n_t = n_r = 0
    for m in listar("/api/v1/monitored-tables"):
        tab = m.get("table", m)
        if tab.get("table_fqn") in ALVOS:
            st, r = cr.api("DELETE", f"/api/v1/monitored-tables/{tab['binding_id']}")
            n_t += st == 200
            if st != 200:
                print("   remover tabela", tab["table_fqn"], st, str(r)[:200])
    for x in listar("/api/v1/registry-rules"):
        if (x.get("user_metadata") or {}).get("dominio") == "pos_venda":
            st, r = cr.api("DELETE", f"/api/v1/registry-rules/{x['rule_id']}")
            n_r += st == 200
            if st != 200:
                print("   remover modelo", (x.get("user_metadata") or {}).get("name"), st, str(r)[:200])
    print(f"removidas {n_t} tabelas monitoradas e {n_r} modelos do Registro (pos_venda)")


def executar(nomes=()):
    ids = json.loads((cr.AQUI / "resultados" / "registro_studio.json").read_text(encoding="utf-8"))
    if nomes:
        ids = {t: b for t, b in ids.items() if t in set(_escolher(nomes))}
    runs = {}
    for t, bid in ids.items():
        st, r = cr.api("POST", f"/api/v1/monitored-tables/{bid}/run", {"source": "approved", "sample_size": 0})
        if st == 200:
            runs[t] = r["run_id"]
        else:
            print(f"   executar {t}: HTTP {st} {str(r)[:300]}")
    pend, t0 = dict(runs), time.time()
    while pend and time.time() - t0 < 3600:
        time.sleep(20)
        for t, rid in list(pend.items()):
            st, s = cr.api("GET", f"/api/v1/dryrun/runs/{rid}/status")
            if st == 200 and (s.get("result_state") or s.get("state") in ("TERMINATED", "INTERNAL_ERROR")):
                st2, res = cr.api("GET", f"/api/v1/dryrun/runs/{rid}/results")
                res = res if st2 == 200 else {}
                print(f"{t.split('.', 1)[1]:<38} {s.get('result_state') or s.get('state'):<8} linhas={res.get('total_rows')} "
                      f"erro={res.get('error_rows')} aviso={res.get('warning_rows')}", flush=True)
                del pend[t]
    print("pendentes:", list(pend))
    # a tela do app recalcula a nota quando uma execução termina; aqui fazemos o mesmo pela API
    st, r = cr.api("POST", "/api/v1/dq-results/refresh-scores", {"table_fqns": list(ids)}, timeout=600)
    print("notas recalculadas:", st, r)


# ---------------------------------------------------------------------------------------------------- agendamento
# Mesmo ritmo do job pos_venda_carga_diaria (05:00, America/Sao_Paulo; leva ~15 min): o Studio avalia às 06:30.
# Só regras de qualidade (sem profiling) e todas as linhas, como nas execuções completas do histórico.
AGENDA = {"schedule_cron": "30 6 * * *", "schedule_tz": "America/Sao_Paulo", "schedule_kind": "dq_only", "schedule_sample_size": 0}
AGENDA_ANTIGA = "pos_venda_janela_diaria"     # agendamento por schema (regras de tabela única), substituído por este


def _ids():
    return json.loads((cr.AQUI / "resultados" / "registro_studio.json").read_text(encoding="utf-8"))


def _visao():
    """Linhas da visão geral de agendamentos que são das nossas tabelas monitoradas."""
    ids = _ids()
    st, linhas = cr.api("GET", "/api/v1/schedules/overview")
    alvo = set(ids.values()) | set(ids)
    return [x for x in (linhas or []) if x.get("source_type") == "table" and (x.get("source_id") in alvo or x.get("name") in alvo)]


def _pausar_todos(pausado):
    falhas = 0
    for x in _visao():
        st, r = cr.api("PATCH", f"/api/v1/schedules/overview/table/{x['source_id']}/paused", {"paused": pausado})
        if st != 200:
            print(f"   {x.get('name')}: HTTP {st} {str(r)[:200]}")
            falhas += 1
    return falhas


def ligar():
    falhas = _pausar_todos(False)
    agenda()
    sys.exit(1 if falhas else 0)


def pausar():
    falhas = _pausar_todos(True)
    agenda()
    sys.exit(1 if falhas else 0)


def agenda():
    linhas = _visao()
    for x in sorted(linhas, key=lambda y: y.get("name") or ""):
        print(f"{(x.get('name') or x['source_id']):<45} cron={x.get('cron')} {x.get('timezone')} pausado={x.get('paused')} "
              f"próxima={x.get('next_run_at')} última={x.get('last_run_at')} {x.get('run_status') or ''}")
    print(f"{len(linhas)} tabelas agendadas")
    return linhas


def agendar():
    ids = _ids()
    tabelas = list(ids)
    st, pre = cr.api("POST", "/api/v1/schedule-grants/preflight", {"table_fqns": tabelas})
    print("permissões do agendador (preflight):", st, json.dumps(pre, ensure_ascii=False)[:600])
    falhas = 0
    for t, bid in ids.items():
        st, r = cr.api("PATCH", f"/api/v1/monitored-tables/{bid}/schedule", AGENDA)
        print(f"{t.split('.', 1)[1]:<38} agendar {st}" + ("" if st == 200 else f"  {str(r)[:300]}"))
        falhas += st != 200
    falhas += _pausar_todos(True)          # nasce pausado, como a agenda do job; ligue os dois juntos
    st, antiga = cr.api("GET", f"/api/v1/schedules/{AGENDA_ANTIGA}")
    if st == 200:
        (cr.AQUI / "resultados" / f"agendamento_antigo_{AGENDA_ANTIGA}.json").write_text(
            json.dumps(antiga, indent=1, ensure_ascii=False), encoding="utf-8")
        st, r = cr.api("DELETE", f"/api/v1/schedules/{AGENDA_ANTIGA}")
        print(f"agendamento antigo {AGENDA_ANTIGA}: removido ({st}); configuração guardada em resultados/")
    agenda()
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    acao = sys.argv[1] if len(sys.argv) > 1 else "planejar"
    if acao == "planejar":
        m, a = planejar()
        print(f"{len(m)} modelos para {sum(len(g) for t in a.values() for g in t.values())} checagens em {len(a)} tabelas")
        for k, v in sorted(m.items(), key=lambda kv: kv[1]["user_metadata"]["name"])[:80]:
            usos = sum(len(a[t].get(k, [])) for t in a)
            print(f"  {v['user_metadata']['severity']:<6} {v['user_metadata']['dimension']:<12} {usos:>3}x  {v['user_metadata']['name']}")
    elif acao in ("aplicar", "executar"):
        {"aplicar": aplicar, "executar": executar}[acao](sys.argv[2:])
    else:
        {"limpar": limpar, "agendar": agendar, "agenda": agenda, "ligar": ligar, "pausar": pausar}[acao]()
