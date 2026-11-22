#!/usr/bin/env python3
"""Cria as views do painel (views_painel.sql) e testa cada consulta do painel como o AI/BI vai executá-la.

  python3 aplicar_e_testar.py            cria/atualiza as views e testa os 6 datasets + checagens de consistência
  python3 aplicar_e_testar.py --so-testar só testa

Usa o warehouse do projeto pelo CLI (perfil dbx-workshop). As consultas do painel rodam com catalog=pos_venda e
schema=dq, igual ao dataset_catalog / dataset_schema do bundle. Termina com código 1 se algo falhar.
"""
import json
import pathlib
import re
import subprocess
import sys
import time

AQUI = pathlib.Path(__file__).resolve().parent
PERFIL, WAREHOUSE = "dbx-workshop", "5f010b8396e591fb"


def executar(sql, catalogo=None, schema=None):
    corpo = {"warehouse_id": WAREHOUSE, "statement": sql, "wait_timeout": "50s", "on_wait_timeout": "CONTINUE"}
    if catalogo:
        corpo.update({"catalog": catalogo, "schema": schema})
    out = subprocess.run(["databricks", "api", "post", "/api/2.0/sql/statements", "--profile", PERFIL, "--json", json.dumps(corpo)],
                         capture_output=True, text=True)
    if not out.stdout.strip():
        msg = (out.stderr or "").strip()
        if "free daily limit" in msg or "could not be processed" in msg:
            sys.exit(f"warehouse indisponível: {msg[:200]}\n(no Free Edition a cota diária de computação renova no dia seguinte)")
        sys.exit(f"falha na chamada: {msg[:400]}")
    r = json.loads(out.stdout)
    while r.get("status", {}).get("state") in ("PENDING", "RUNNING"):
        time.sleep(3)
        r = json.loads(subprocess.run(["databricks", "api", "get", f"/api/2.0/sql/statements/{r['statement_id']}", "--profile", PERFIL],
                                      capture_output=True, text=True).stdout)
    estado = r["status"]["state"]
    cols = [c["name"] for c in r.get("manifest", {}).get("schema", {}).get("columns", [])]
    linhas = [dict(zip(cols, x)) for x in r.get("result", {}).get("data_array", []) or []]
    return estado, r["status"].get("error", {}).get("message", ""), r.get("manifest", {}).get("total_row_count"), linhas


def consultar(sql):
    estado, erro, _, ls = executar(sql)
    if estado != "SUCCEEDED":
        raise RuntimeError(f"{erro[:400]}\n{sql[:200]}")
    return ls


def main():
    falhas = 0
    if "--so-testar" not in sys.argv:
        # recria a view só se a definição mudou (CREATE OR REPLACE VIEW apaga tags e Wiki) e grava a descrição das colunas
        sys.path.insert(0, str(AQUI.parent.parent / "carga_diaria"))
        import views_preservadas as vp
        import descricoes_painel as dp
        api = vp.api_cli(PERFIL)
        texto = re.sub(r"--[^\n]*", "", (AQUI / "views_painel.sql").read_text(encoding="utf-8"))
        for stmt in [s.strip() for s in texto.split(";") if s.strip()]:
            m = re.match(r"CREATE OR REPLACE VIEW\s+(\S+)\s+COMMENT\s+'((?:[^'\\]|\\.)*)'\s+AS\s+(.*)$", stmt, re.S)
            nome, comentario, consulta = m.groups()
            try:
                acao = vp.garantir_view(nome, comentario, consulta, consultar, api)
                n, faltam = vp.descrever_colunas(nome, dp.descricoes(nome, consultar), consultar)
                print(f"view  {acao:<9} {nome} | {n} descrições gravadas" + (f" | SEM DESCRIÇÃO: {faltam}" if faltam else ""))
                falhas += bool(faltam)
            except RuntimeError as e:
                print(f"view  FALHOU    {nome}\n      {e}")
                falhas += 1
        if falhas:
            sys.exit(1)

    painel = json.loads((AQUI / "src" / "pos_venda_qualidade.lvdash.json").read_text(encoding="utf-8"))
    for ds in painel["datasets"]:
        estado, erro, n, linhas = executar("".join(ds["queryLines"]), "pos_venda", "dq")
        ok = estado == "SUCCEEDED" and (n or 0) > 0
        falhas += not ok
        print(f"dados {estado:<9} {ds['name']:<22} linhas={n}" + (f"\n      {erro[:500]}" if erro else "")
              + ("" if ok else "  <-- FALHOU OU VAZIO"))
        if ok:
            print("      ex:", json.dumps(linhas[0], ensure_ascii=False)[:220])

    # checagens de consistência (os números que a demonstração cita)
    checagens = [
        ("5 camadas x 5 semanas no Studio, sem repetição",
         "SELECT count(*) = 25 AND count(DISTINCT destino, semana_n) = 25 AS ok FROM v_painel_studio_execucoes"),
        ("quarentena 100% reprovada no Studio",
         "SELECT sum(error_rows) = sum(total_rows) AND sum(total_rows) = 3049 AS ok FROM v_painel_studio_execucoes WHERE camada_curta = 'quarentena'"),
        ("órfãs da fato no Studio = métrica do pipeline (semanas 4 e 5)",
         "SELECT (SELECT sum(error_rows) FROM v_painel_studio_execucoes WHERE camada_curta = 'fato') = "
         "(SELECT sum(fato_linhas_orfas) FROM v_painel_diario WHERE dia BETWEEN DATE'2026-12-11' AND DATE'2026-12-24') AS ok"),
        ("um dia de métricas por dia carregado desde 20/11, sem buraco",
         "SELECT count(*) = datediff(max(dia), DATE'2026-11-20') + 1 AND count(*) >= 35 AS ok FROM v_painel_diario"),
        ("quarentena do painel = quarentena do pipeline", "SELECT count(*) = 3049 AS ok FROM v_painel_quarentena"),
    ]
    for desc, sql in checagens:
        estado, erro, _, linhas = executar(sql, "pos_venda", "dq")
        ok = estado == "SUCCEEDED" and linhas and str(linhas[0]["ok"]).lower() == "true"
        falhas += not ok
        print(f"check {'OK' if ok else 'FALHOU':<9} {desc}" + (f"\n      {erro[:300]}" if erro else ""))
    print("RESULTADO:", "tudo certo" if not falhas else f"{falhas} falha(s)")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
