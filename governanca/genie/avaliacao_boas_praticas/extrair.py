"""Gera space_config e data_context no formato do genie-best-practices-agent, sem Spark (SDK + warehouse)."""
import json, sys, datetime, decimal
from pathlib import Path
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import Disposition, Format

WH = "5f010b8396e591fb"
w = WorkspaceClient()
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
ESPACOS = {"analista": "01f1e4772cf610a8baf0c236595c284b", "diretor": "01f1e477314b1903a4212843cf0dabf1"}

def sql(q):
    r = w.statement_execution.execute_statement(warehouse_id=WH, statement=q, wait_timeout="50s")
    while r.status.state.value in ("PENDING", "RUNNING"):
        import time; time.sleep(2); r = w.statement_execution.get_statement(r.statement_id)
    if r.status.state.value != "SUCCEEDED":
        raise RuntimeError(r.status.error.message if r.status.error else r.status.state.value)
    cols = [c.name for c in r.manifest.schema.columns]
    return [dict(zip(cols, x)) for x in (r.result.data_array or [])] if r.result else []

def entrada(fqn):
    cat, sch, tab = fqn.split(".")
    ti = w.tables.get(full_name=fqn)
    tipo = ti.table_type.value if ti.table_type else "UNKNOWN"
    e = {"full_name": fqn, "catalog": cat, "schema": sch, "table_name": tab, "table_type": tipo, "comment": ti.comment,
         "row_count": None, "columns": [], "primary_keys": [], "foreign_keys": []}
    if tipo == "METRIC_VIEW" or (tipo == "VIEW" and (ti.view_definition or "").lstrip().startswith("version")):
        e["table_type"] = "METRIC_VIEW"
        e["view_definition"] = f"-- Metric view definition (YAML) for: {fqn}\n{ti.view_definition}"
        for c in ti.columns:
            e["columns"].append({"name": c.name, "data_type": c.type_text, "nullable": c.nullable, "comment": c.comment, "example_values": []})
        return e
    if tipo == "VIEW" and ti.view_definition:
        e["view_definition"] = f"-- SQL definition for view: {fqn}\n{ti.view_definition}"
    if tipo in ("MANAGED", "EXTERNAL"):
        try: e["row_count"] = sql(f"DESCRIBE DETAIL {fqn}")[0].get("numRows")
        except Exception: pass
        e["primary_keys"] = [r["column_name"] for r in sql(f"""SELECT kcu.column_name FROM {cat}.information_schema.table_constraints tc
            JOIN {cat}.information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name AND tc.constraint_schema = kcu.constraint_schema
            WHERE tc.table_schema = '{sch}' AND tc.table_name = '{tab}' AND tc.constraint_type = 'PRIMARY KEY' ORDER BY kcu.ordinal_position""")]
    amostra = sql(f"SELECT * FROM {fqn} LIMIT 2000")
    for c in ti.columns:
        vistos = []
        for r in amostra:
            v = r.get(c.name)
            if v is not None and v not in vistos:
                vistos.append(v)
            if len(vistos) >= 15: break
        e["columns"].append({"name": c.name, "data_type": c.type_text, "nullable": c.nullable, "comment": c.comment, "example_values": vistos})
    return e

for nome, sid in ESPACOS.items():
    sp = w.genie.get_space(space_id=sid, include_serialized_space=True)
    cfg = json.loads(sp.serialized_space)
    ids = [x["identifier"] for x in cfg["data_sources"].get("metric_views", [])] + [x["identifier"] for x in cfg["data_sources"].get("tables", [])]
    ctx = {"space_id": sid, "space_name": sp.title, "tables": [entrada(i) for i in ids]}
    (out / f"{nome}_space_config.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False, default=str))
    (out / f"{nome}_data_context.json").write_text(json.dumps(ctx, indent=2, ensure_ascii=False, default=str))
    print(nome, sp.title, "| objetos:", [(t["table_name"], t["table_type"], len(t["columns"])) for t in ctx["tables"]])
