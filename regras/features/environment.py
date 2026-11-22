"""Ganchos do behave: deixa `uc` importável e confere, antes do primeiro cenário, que as funções existem."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # pos_venda/regras

import uc  # noqa: E402

ESPERADAS = {"faixa_atraso", "valor_multa", "valor_juros", "valor_total_pendente", "cpf_valido"}


def before_all(context):
    linhas = uc.executar(f"SELECT routine_name FROM {uc.CATALOGO}.information_schema.routines "
                         f"WHERE routine_schema = '{uc.SCHEMA}'")
    faltam = ESPERADAS - {n for (n,) in linhas}
    if faltam:
        sys.exit(f"funções ausentes em {uc.CATALOGO}.{uc.SCHEMA}: {sorted(faltam)}; rode `.venv/bin/python funcoes.py`")
