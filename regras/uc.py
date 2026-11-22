"""Cliente mínimo da Statement Execution API (SDK do Databricks), usado pelas funções, pelos cenários e pela paridade.

Uma chamada = um SELECT no warehouse do projeto. Sem Spark, sem cluster. Variáveis (opcionais):
  DATABRICKS_PROFILE (padrão dbx-workshop) · DATABRICKS_WAREHOUSE_ID · REGRAS_CATALOGO · REGRAS_SCHEMA
"""
from __future__ import annotations

import os
import time
from functools import lru_cache

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

CATALOGO = os.environ.get("REGRAS_CATALOGO", "pos_venda")
SCHEMA = os.environ.get("REGRAS_SCHEMA", "regras")
WAREHOUSE = os.environ.get("DATABRICKS_WAREHOUSE_ID", "5f010b8396e591fb")


@lru_cache(maxsize=1)
def cliente() -> WorkspaceClient:
    if os.environ.get("DATABRICKS_RUNTIME_VERSION"):     # dentro do Databricks (portão do job): autenticação do runtime
        return WorkspaceClient()
    return WorkspaceClient(profile=os.environ.get("DATABRICKS_PROFILE", "dbx-workshop"))


def _com_nova_tentativa(chamada, tentativas: int = 4):
    """Falha de rede passageira (timeout de leitura, conexão caída) não é falha de regra: espera e repete."""
    for i in range(tentativas):
        try:
            return chamada()
        except Exception as e:                       # noqa: BLE001 — só repete erros de transporte
            transitorio = any(p in f"{type(e).__name__} {e}".lower()
                              for p in ("timeout", "timed out", "connection", "temporarily", "503", "502"))
            if not transitorio or i == tentativas - 1:
                raise
            time.sleep(2 * (i + 1))


def executar(sql: str, espera: str = "20s") -> list[list]:
    """Executa e devolve as linhas (lista de listas de texto). Erro do warehouse vira exceção com a mensagem.

    A espera síncrona fica bem abaixo do timeout de leitura do SDK (60 s); se a consulta demorar, o estado é consultado.
    """
    w = cliente()
    r = _com_nova_tentativa(lambda: w.statement_execution.execute_statement(
        warehouse_id=WAREHOUSE, statement=sql, wait_timeout=espera))
    while r.status.state in (StatementState.PENDING, StatementState.RUNNING):
        time.sleep(1)
        r = _com_nova_tentativa(lambda: w.statement_execution.get_statement(r.statement_id))
    if r.status.state != StatementState.SUCCEEDED:
        msg = r.status.error.message if r.status.error else r.status.state
        if "free daily limit" in str(msg):
            raise RuntimeError("warehouse sem cota (Free Edition): tente depois da meia-noite UTC")
        raise RuntimeError(f"falhou: {msg}")
    return (r.result.data_array if r.result else None) or []


def valor(expr: str):
    """SELECT de uma expressão que chama uma função do schema de regras: `valor("faixa_atraso(10)")`."""
    linhas = executar(f"SELECT {CATALOGO}.{SCHEMA}.{expr}")
    return linhas[0][0] if linhas else None
