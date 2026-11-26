"""Ganchos do behave do catálogo: reaproveita o cliente `uc` de regras/ e confere que o catálogo existe."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # pos_venda/regras

import uc  # noqa: E402


def before_all(context):
    n = uc.executar(f"SELECT count(*) FROM {uc.CATALOGO}.information_schema.tables "
                    f"WHERE table_schema = '{uc.SCHEMA}' AND table_name IN ('catalogo_regras', 'triagem_regras')")[0][0]
    if int(n) != 2:
        sys.exit("catálogo ausente: rode `python3 regras/catalogo/gerar_catalogo.py aplicar`")
