"""Fonte única das cores do projeto: lê docs/marca/marca.json. Os geradores importam daqui; não copie hex para outro lugar.

Ainda não é a marca da empresa (veja README.md desta pasta). Quando ela chegar, troque os valores no JSON e regere.
"""
from __future__ import annotations

import json
import pathlib

ARQUIVO = pathlib.Path(__file__).resolve().with_name("marca.json")
M = json.loads(ARQUIVO.read_text(encoding="utf-8"))

SERIES = M["series"]["claro"]           # ordem fixa: a cor segue a entidade, nunca a posição no ranking
SERIES_ESCURO = M["series"]["escuro"]
BOM, ALERTA, SERIO, CRITICO = (M["status"][k] for k in ("bom", "alerta", "serio", "critico"))   # só para estado, com rótulo
SEQ_INICIO, SEQ_FIM = M["sequencial"]["inicio"], M["sequencial"]["fim"]                        # magnitude: um tom, claro → escuro


def tema_aibi(**extra) -> dict:
    """uiSettings.theme dos painéis AI/BI (Lakeview)."""
    p = M["painel"]
    tema = {"canvasBackgroundColor": p["fundo"], "widgetBackgroundColor": p["cartao"], "widgetBorderColor": p["cartao"],
            "fontColor": p["texto"], "selectionColor": p["selecao"], "visualizationColors": SERIES,
            "widgetHeaderAlignment": "LEFT"}
    tema.update(extra)
    return tema


def tema_powerbi(nome: str) -> dict:
    """Tema JSON do Power BI (dataColors e cores de sentimento)."""
    p = M["painel"]
    return {"name": nome, "dataColors": SERIES, "background": p["cartao"]["light"], "foreground": p["texto"]["light"],
            "tableAccent": p["selecao"]["light"], "good": BOM, "neutral": ALERTA, "bad": CRITICO}


def css_apresentacao() -> str:
    """Bloco :root dos tokens das apresentações (deck.css)."""
    return ":root {\n" + "".join(f"  --{k}: {v};\n" for k, v in M["apresentacao"].items()) + "}"


if __name__ == "__main__":
    print(json.dumps({"series": SERIES, "status": M["status"], "eh_marca_da_empresa": M["eh_marca_da_empresa"]}, indent=1))
