"""Implanta o genie-ontology-readiness v1.5.0 com histórico no Lakebase (Autoscaling) do projeto do DQX Studio.

Por que não "Deploy from Git": a v1.5.0 só descobre pelo recurso `lakebase-db` o Lakebase *Provisioned*; com Autoscaling
ela precisa de host, endpoint e database explícitos no app.yaml. O `main` do repositório já resolve isso, mas também
muda o cálculo da nota, o que deixaria o histórico incomparável. Este script:

  1. garante a database `ontology_readiness` no branch `dqx` do projeto `dqx-studio-db` (Free Edition: 1 projeto);
  2. garante os recursos do app: `sql-warehouse` e `lakebase-db` (CAN_CONNECT_AND_CREATE);
  3. exporta a tag v1.5.0, grava LAKEBASE_HOST, LAKEBASE_ENDPOINT_NAME e LAKEBASE_DATABASE no app.yaml;
  4. envia para /Workspace/Users/<você>/apps/genie-ontology-readiness e implanta.

    python3 implantar_app.py
Depois: `python3 avaliar.py rodar <rotulo>` grava a avaliação no histórico.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

PERFIL = "dbx-workshop"
APP = "genie-ontology-readiness"
TAG = "v1.5.0"
REPO = "https://github.com/databricks-solutions/genie-ontology-readiness"
WAREHOUSE = "5f010b8396e591fb"
PROJETO = "projects/dqx-studio-db"
BRANCH = f"{PROJETO}/branches/dqx"
ENDPOINT = f"{BRANCH}/endpoints/primary"
DB_ID, DB_PG = "ontology-readiness", "ontology_readiness"


def cli(*args, ok=True):
    r = subprocess.run(["databricks", *args, "--profile", PERFIL, "-o", "json"], capture_output=True, text=True)
    if ok and r.returncode != 0:
        sys.exit(f"databricks {' '.join(args[:3])}: {r.stderr.strip()[:300]}")
    return json.loads(r.stdout) if r.stdout.strip() else {}


def garantir_database():
    nomes = [d["name"] for d in cli("postgres", "list-databases", BRANCH) or []]
    if f"{BRANCH}/databases/{DB_ID}" in nomes:
        return "existente"
    dono = next(r["name"] for r in cli("postgres", "list-roles", BRANCH)
                if (r.get("status") or {}).get("identity_type") == "USER")
    cli("postgres", "create-database", BRANCH, "--database-id", DB_ID,
        "--json", json.dumps({"spec": {"postgres_database": DB_PG, "role": dono}}))
    return "criada"


def garantir_recursos():
    recursos = [
        {"name": "sql-warehouse", "sql_warehouse": {"id": WAREHOUSE, "permission": "CAN_USE"}},
        {"name": "lakebase-db", "postgres": {"branch": BRANCH, "database": f"{BRANCH}/databases/{DB_ID}",
                                             "permission": "CAN_CONNECT_AND_CREATE"}},
    ]
    atuais = {r["name"]: r for r in cli("apps", "get", APP).get("resources", [])}
    if all(atuais.get(r["name"]) == r for r in recursos):
        return "iguais"
    cli("apps", "create-update", APP, "--json", json.dumps({"update_mask": "resources", "app": {"resources": recursos}}))
    return "atualizados"


def app_yaml(texto, host):
    trocas = {
        "  - name: LAKEBASE_HOST\n    valueFrom: lakebase-db": f'  - name: LAKEBASE_HOST\n    value: "{host}"',
        '  - name: LAKEBASE_DATABASE\n    value: ""': f'  - name: LAKEBASE_DATABASE\n    value: "{DB_PG}"',
        '  - name: LAKEBASE_ENDPOINT_NAME\n    value: ""': f'  - name: LAKEBASE_ENDPOINT_NAME\n    value: "{ENDPOINT}"',
    }
    for velho, novo in trocas.items():
        if texto.count(velho) != 1:
            sys.exit(f"app.yaml da {TAG} mudou; revise o trecho: {velho.splitlines()[0]}")
        texto = texto.replace(velho, novo)
    return texto


def main():
    print("database:", garantir_database())
    print("recursos:", garantir_recursos())
    host = cli("postgres", "get-endpoint", ENDPOINT)["status"]["hosts"]["host"]
    me = cli("current-user", "me")["userName"]
    destino = f"/Workspace/Users/{me}/apps/{APP}"
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--branch", TAG, REPO, f"{tmp}/src"], check=True)
        yaml = Path(tmp, "src", "app", "app.yaml")
        yaml.write_text(app_yaml(yaml.read_text(), host))
        cli("workspace", "mkdirs", destino)
        r = subprocess.run(["databricks", "workspace", "import-dir", f"{tmp}/src/app", destino, "--overwrite",
                            "--profile", PERFIL], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"import-dir: {r.stderr.strip()[:300]}")
    d = cli("apps", "deploy", APP, "--source-code-path", destino)
    print("implantação:", d.get("deployment_id"), (d.get("status") or {}).get("state"))


if __name__ == "__main__":
    main()
