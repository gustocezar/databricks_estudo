# Databricks notebook source
# MAGIC %md
# MAGIC # pos_venda · 05 · Portão das regras de negócio
# MAGIC Roda os cenários BDD (`features/*.feature`, em português) contra as funções `pos_venda.regras.*` antes da carga.
# MAGIC Se algum cenário falhar, a tarefa falha e **a carga do dia não roda**: o pipeline e a gold usam essas funções.
# MAGIC A suíte é uma cópia gerada de `pos_venda/regras` (por `gerar_carga.py`); a original roda igual na máquina local.

# COMMAND ----------

# MAGIC %pip install behave==1.3.3 --quiet

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import contextlib
import io
import json
import re
import sys
from pathlib import Path

dbutils.widgets.text("suite", "")
SUITE = Path(dbutils.widgets.get("suite").strip())
if not (SUITE / "features").is_dir():
    raise Exception(f"suíte de cenários não encontrada em {SUITE}")
sys.path.insert(0, str(SUITE))

from behave.__main__ import main as behave_main

saida = io.StringIO()
with contextlib.redirect_stdout(saida):
    rc = behave_main([str(SUITE / "features"), "--no-color", "--format", "progress", "--no-junit"])
texto = saida.getvalue()
print(texto)
resumo = {k: int(v) for v, k in re.findall(r"(\d+) scenarios? (passed|failed|error)", texto)}
if rc != 0:
    raise Exception(f"Portão das regras reprovado ({resumo}); a carga não roda. Veja os cenários acima.")
dbutils.notebook.exit(json.dumps({"portao": "aprovado", "cenarios": resumo}))
