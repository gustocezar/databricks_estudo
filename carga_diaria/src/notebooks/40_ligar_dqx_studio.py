# Databricks notebook source
# MAGIC %md
# MAGIC # pos_venda · 40 · Ligar o DQX Studio para a avaliação agendada
# MAGIC
# MAGIC As 12 tabelas monitoradas do DQX Studio estão agendadas para **06:30 (Brasília)**, depois desta carga. O agendador roda
# MAGIC dentro do app, e no Free Edition o app para sozinho 24 h depois de iniciado. Esta tarefa liga o `dqx-studio` se ele
# MAGIC estiver parado, para a avaliação das 06:30 acontecer. Os agendamentos são ligados e pausados com
# MAGIC `python3 dqx_studio/regras/registro_studio.py ligar|pausar`, junto com a agenda deste job.

# COMMAND ----------

import json
from databricks.sdk import WorkspaceClient

APP = "dqx-studio"
w = WorkspaceClient()
app = w.apps.get(APP)
antes = app.compute_status.state.value if app.compute_status and app.compute_status.state else "DESCONHECIDO"
if antes not in ("ACTIVE", "STARTING"):
    app = w.apps.start(APP).result()          # espera o app ficar ativo
depois = app.compute_status.state.value if app.compute_status and app.compute_status.state else "DESCONHECIDO"
print(f"{APP}: {antes} -> {depois}")
dbutils.notebook.exit(json.dumps({"app": APP, "antes": antes, "depois": depois}))
