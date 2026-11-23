#!/usr/bin/env python3
"""Gera os notebooks e o SQL do pipeline de CARGA DIARIA do dominio pos_venda.

Fluxo (1 execucao = 1 dia, ou um intervalo de dias no backfill):
  10_gerar_eventos (notebook)   simula o sistema de origem: grava no BRONZE os eventos do dia
                                (pendencias novas, mudancas de status, baixas/pagamentos)
  silver Lakeflow (pipeline)    padroniza os eventos e mantem 3 tabelas: eventos, historica (SCD2) e atual (SCD1)
  20_gold_dims (notebook)       atualiza as dimensoes do star schema (com PK)
  30_fato_snapshot (notebook)   acrescenta a foto do dia na fato historica (PK = pendencia_id + data_referencia)

Uso: python3 gerar_carga.py   (le as colunas da one-table no Unity Catalog via CLI)
"""
import json
import pathlib
import shutil
import subprocess

import janela_avaliacao

ROOT = pathlib.Path(__file__).resolve().parent
CAT = "pos_venda"
REGRAS = f"{CAT}.regras"          # funções de regra de negócio (pos_venda/regras): fonte única dos cálculos
LANDING = f"{CAT}.landing.pagamentos_pendentes_one_table"
PROFILE = "dbx-workshop"

COLS = [c["name"] for c in json.loads(subprocess.check_output(
    ["databricks", "tables", "get", LANDING, "--profile", PROFILE, "-o", "json"]))["columns"]]
# colunas que variam por pendencia/dia (o resto e cadastro da apolice, cliente, corretor e ponto de venda)
PEND_COLS = {"pendencia_id", "data_extracao", "sistema_origem", "numero_parcela", "competencia", "data_vencimento",
             "data_geracao_cobranca", "dias_atraso", "faixa_atraso", "valor_parcela", "valor_multa", "valor_juros",
             "valor_total_pendente", "status_cobranca", "motivo_pendencia", "tentativas_cobranca",
             "data_ultima_tentativa", "canal_ultimo_contato", "parcela_afetada_por_endosso", "cliente_idade"}
assert PEND_COLS <= set(COLS), PEND_COLS - set(COLS)
POLICY_COLS = [c for c in COLS if c not in PEND_COLS]
EXTRA = ["tipo_evento", "data_baixa", "valor_pago", "_ingestao_ts", "_lote_id", "_origem"]

SRC_ATUAL = f"{CAT}.silver.pendencia_atual"


def render(txt):
    return (txt.replace("@@COLS@@", repr(COLS)).replace("@@POLICY_COLS@@", repr(POLICY_COLS))
            .replace("@@JANELA_DDL@@", repr(janela_avaliacao.ddl())).replace("@@JANELA_APONTAR@@", repr(janela_avaliacao.APONTAR_ULTIMOS_7))
            .replace("@@JANELA_VIEWS@@", repr(janela_avaliacao.lista_views()))
            .replace("@@VIEWS_PRESERVADAS@@", (ROOT / "views_preservadas.py").read_text(encoding="utf-8")))


# ====================================================================================== 00_setup
NB_SETUP = r'''# Databricks notebook source
# MAGIC %md
# MAGIC # pos_venda · 00 · Setup (rodar uma vez)
# MAGIC Cria os schemas `fonte`, `bronze`, `silver` e `gold` e o **cadastro de apólices** do sistema de origem simulado
# MAGIC (`fonte.apolices`), a partir das apólices da one-table `landing`. Esse cadastro é a base do gerador diário.

# COMMAND ----------

import json

CAT = "pos_venda"
LANDING = f"{CAT}.landing.pagamentos_pendentes_one_table"
SEED = 20261118
POLICY_COLS = @@POLICY_COLS@@

for s in ["fonte", "bronze", "silver", "gold"]:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CAT}.{s} COMMENT 'pos_venda - {s}'")

def U(salt, *cols):
    return f"(pmod(xxhash64({', '.join(cols)}, {SEED + salt}), 1000000) / 1000000.0)"

# COMMAND ----------

# perfil de pagador por apolice: define a chance de cada parcela virar pendencia
spark.sql(f"""
CREATE TABLE IF NOT EXISTS {CAT}.fonte.apolices
COMMENT 'Cadastro de apolices do sistema de origem simulado (apolice, cliente, corretor, ponto de venda). Base do gerador diario de pendencias.'
AS
WITH a AS (
  SELECT {", ".join(POLICY_COLS)}
  FROM {LANDING}
  QUALIFY row_number() OVER (PARTITION BY numero_apolice ORDER BY data_vencimento DESC, pendencia_id) = 1
),
b AS (
  SELECT a.* EXCEPT (dia_vencimento),
         CAST(1 + floor({U(212, "numero_apolice")} * 28) AS INT) AS dia_vencimento,   -- vencimento espalhado nos dias 1 a 28
         date_add(data_emissao, 10) AS _x, {U(201, "numero_apolice")} AS _u_perfil FROM a
)
SELECT b.* EXCEPT (_x, _u_perfil),
  CASE WHEN day(_x) <= dia_vencimento THEN make_date(year(_x), month(_x), dia_vencimento)
       ELSE make_date(year(add_months(_x, 1)), month(add_months(_x, 1)), dia_vencimento) END AS data_primeira_parcela,
  CASE WHEN _u_perfil < 0.40 THEN 'BOM' WHEN _u_perfil < 0.75 THEN 'REGULAR' ELSE 'CRONICO' END AS perfil_pagador,
  CASE WHEN _u_perfil < 0.40 THEN 0.02 WHEN _u_perfil < 0.75 THEN 0.48 ELSE 0.88 END AS p_inadimplencia
FROM b
""")

n = spark.table(f"{CAT}.fonte.apolices").count()
dbutils.notebook.exit(json.dumps({"apolices_no_cadastro": n}))
'''

# ====================================================================================== 10_gerar_eventos
NB_GERAR = r'''# Databricks notebook source
# MAGIC %md
# MAGIC # pos_venda · 10 · Gerador diário de pendências (sistema de origem simulado)
# MAGIC Para cada dia em `[data_inicio, data_fim]` grava no **bronze** (`bronze.pagamentos_pendentes_eventos`, append-only) os eventos do dia:
# MAGIC - `NOVA`: parcela que venceu ontem e não foi paga, entrando na carteira de pendentes;
# MAGIC - `ATUALIZACAO`: mudança de status de cobrança (pendente → em cobrança → promessa/negociado/cobrança externa);
# MAGIC - `BAIXA`: pagamento da parcela (a pendência sai da carteira).
# MAGIC
# MAGIC Determinístico (hash) e idempotente: dias já carregados no bronze são ignorados. Cerca de 0,5% das linhas são reenviadas em duplicidade (defeito proposital).

# COMMAND ----------

import json

dbutils.widgets.text("data_inicio", "2026-11-18")
dbutils.widgets.text("data_fim", "2026-11-18")
INI = dbutils.widgets.get("data_inicio").strip()
FIM = dbutils.widgets.get("data_fim").strip()

CAT = "pos_venda"
FONTE = f"{CAT}.fonte.apolices"
BRONZE = f"{CAT}.bronze.pagamentos_pendentes_eventos"
SEED = 20261118
INICIO_SIM = "2026-05-19"      # primeiro dia da simulacao (6 meses antes de 2026-11-18)
P_PAGO = 0.65                  # chance de a pendencia ser paga um dia (os 35% restantes seguem em aberto)
COLS = @@COLS@@

def U(salt, *cols):
    return f"(pmod(xxhash64({', '.join(cols)}, {SEED + salt}), 1000000) / 1000000.0)"

def u(salt):
    return U(salt, "numero_apolice", "numero_parcela")

# COMMAND ----------

# ---- colunas que mudam por pendencia / dia (valores "as-of" a data do evento)
VTOTAL = "CAST(valor_premio_periodico + round(valor_premio_periodico * 0.02, 2) + round(valor_premio_periodico * 0.01 * x / 30.0, 2) AS DECIMAL(14,2))"
OV = {
    "pendencia_id": "concat('PD', substring(numero_apolice, 4), lpad(cast(numero_parcela AS string), 3, '0'))",
    "data_extracao": "data_evento",
    "sistema_origem": "'CORE_VIDA'",
    "competencia": "date_format(data_vencimento, 'yyyy-MM')",
    "data_geracao_cobranca": "date_sub(data_vencimento, 10)",
    "dias_atraso": "x",
    "faixa_atraso": ("CASE WHEN x = 0 THEN '00_VENCE_HOJE' WHEN x <= 15 THEN '01_1_A_15' WHEN x <= 30 THEN '02_16_A_30' "
                     "WHEN x <= 60 THEN '03_31_A_60' WHEN x <= 90 THEN '04_61_A_90' WHEN x <= 120 THEN '05_91_A_120' ELSE '06_ACIMA_120' END"),
    "valor_parcela": "valor_premio_periodico",
    "valor_multa": "CAST(round(valor_premio_periodico * 0.02, 2) AS DECIMAL(14,2))",
    "valor_juros": "CAST(round(valor_premio_periodico * 0.01 * x / 30.0, 2) AS DECIMAL(14,2))",
    "valor_total_pendente": VTOTAL,
    "motivo_pendencia": (
        "CASE forma_pagamento "
        f" WHEN 'DEBITO_CONTA' THEN CASE WHEN {u(210)} < 0.60 THEN 'SALDO_INSUFICIENTE' WHEN {u(210)} < 0.75 THEN 'CONTA_ENCERRADA' WHEN {u(210)} < 0.90 THEN 'DADOS_BANCARIOS_INVALIDOS' ELSE 'AUTORIZACAO_DEBITO_CANCELADA' END "
        f" WHEN 'BOLETO' THEN CASE WHEN {u(210)} < 0.85 THEN 'BOLETO_NAO_PAGO' ELSE 'BOLETO_NAO_RECEBIDO' END "
        f" WHEN 'CARTAO_CREDITO' THEN CASE WHEN {u(210)} < 0.50 THEN 'CARTAO_RECUSADO' WHEN {u(210)} < 0.80 THEN 'CARTAO_EXPIRADO' ELSE 'LIMITE_INSUFICIENTE' END "
        f" ELSE CASE WHEN {u(210)} < 0.70 THEN 'SALDO_INSUFICIENTE' ELSE 'AUTORIZACAO_PIX_REVOGADA' END END"),
    "tentativas_cobranca": "CAST(least(10, 1 + floor(x / 10) + CASE WHEN status_cobranca = 'PENDENTE' THEN 0 ELSE 1 END) AS INT)",
    "data_ultima_tentativa": f"date_add(data_vencimento, CAST(floor({u(209)} * x) AS INT))",
    "canal_ultimo_contato": (
        f"CASE WHEN {u(211)} < 0.30 THEN 'SMS' WHEN {u(211)} < 0.55 THEN 'EMAIL' WHEN {u(211)} < 0.75 THEN 'WHATSAPP' "
        f"WHEN {u(211)} < 0.90 THEN 'TELEFONE' WHEN {u(211)} < 0.95 THEN 'CARTA' ELSE 'NENHUM' END"),
    "parcela_afetada_por_endosso": "coalesce(qtd_endossos > 0 AND data_vencimento >= data_ultimo_endosso, false)",
    "cliente_idade": "CAST(floor(months_between(data_evento, cliente_data_nascimento) / 12) AS INT)",
}
select_cols = ",\n  ".join(f"{OV[c]} AS {c}" if c in OV else c for c in COLS)
extras = f"""tipo_evento,
  CASE WHEN tipo_evento = 'BAIXA' THEN data_evento END AS data_baixa,
  CASE WHEN tipo_evento = 'BAIXA' THEN {VTOTAL} END AS valor_pago,
  current_timestamp() AS _ingestao_ts,
  concat('L', date_format(data_evento, 'yyyyMMdd')) AS _lote_id,
  'CORE_VIDA_SIM' AS _origem"""

# ---------------------------------------------------------------------------------------------------- incidentes de qualidade
# Casos de uso que a demonstracao de qualidade precisa: cada incidente tem janelas de datas e uma taxa de pico (perfil triangular:
# sobe, atinge o pico no meio da janela e desce). Antes de 2026-11-20 nada e injetado. Deterministico (hash por evento).
dbutils.widgets.text("incidentes", "true")
INCIDENTES_ON = dbutils.widgets.get("incidentes").strip().lower() == "true"
JANELAS = {
    "I01": [("2026-11-28", "2026-12-02", 0.12), ("2026-12-18", "2026-12-24", 0.012)],   # CPF invalido em lote (digito errado)
    "I02": [("2026-11-29", "2026-12-02", 0.06)],                                          # reenvio massivo de eventos (duplicatas)
    "I12": [("2026-11-27", "2026-12-03", 0.15)],                                          # e-mail ausente (campanha sem e-mail)
    "I03": [("2026-12-05", "2026-12-09", 0.02), ("2026-12-18", "2026-12-20", 0.003)],     # valor da parcela zero ou negativo (bug de ETL)
    "I04": [("2026-12-04", "2026-12-08", 0.012), ("2026-12-18", "2026-12-19", 0.002)],    # status fora do dominio (PAGO, EM COBRANCA...)
    "I07": [("2026-12-06", "2026-12-10", 0.025)],                                         # total inconsistente (bug no calculo de juros)
    "I05": [("2026-12-07", "2026-12-09", 0.006)],                                         # pendencia sem id
    "I06": [("2026-12-11", "2026-12-14", 0.015)],                                         # vencimento no futuro
    "I08": [("2026-12-12", "2026-12-16", 0.010)],                                         # cliente menor de idade
    "I09": [("2026-12-11", "2026-12-15", 0.018), ("2026-12-18", "2026-12-21", 0.004)],    # UF invalida
    "I10": [("2026-12-13", "2026-12-17", 0.04)],                                          # baixa sem data de baixa (so em eventos BAIXA)
    "I14": [("2026-12-12", "2026-12-16", 0.012)],                                         # dias de atraso nao conferem com as datas
    "I11": [("2026-12-13", "2026-12-17", 0.03), ("2026-12-18", "2026-12-22", 0.006)],     # forma de pagamento nova (vaza para a gold)
    "I13": [("2026-12-11", "2026-12-17", 0.09)],                                          # CEP malformado
    "I15": [("2026-12-14", "2026-12-17", 0.05)],                                          # canal CORRETOR sem corretor
}
# Semanas 6 e 7 (26/12/2026 a 08/01/2027): catalogo de exemplos para todas as regras de qualidade, pelo fluxo normal.
# Semana 6 = erros de origem (vao para a quarentena) e avisos; semana 7 = vazamentos que passam pela barreira e chegam
# as dimensoes e a fato. Os incidentes antigos voltam com taxa baixa; os novos (I16 a I34) entram no fim do dicionario,
# para nao mudar o sal dos antigos.
S6, S7 = ("2026-12-26", "2027-01-01"), ("2027-01-02", "2027-01-08")
for _inc, _jan in {"I01": [(*S6, 0.03)], "I02": [(*S6, 0.03)], "I12": [(*S6, 0.06)], "I03": [(*S6, 0.012), (*S7, 0.004)],
                   "I04": [(*S6, 0.012), (*S7, 0.004)], "I07": [(*S6, 0.012)], "I05": [(*S6, 0.006)],
                   "I06": [(*S6, 0.012), (*S7, 0.004)], "I08": [(*S6, 0.01)], "I09": [(*S6, 0.012)], "I10": [(*S6, 0.03)],
                   "I14": [(*S6, 0.012)], "I11": [(*S7, 0.012)], "I13": [(*S6, 0.04)], "I15": [(*S6, 0.04)]}.items():
    JANELAS[_inc] = JANELAS[_inc] + _jan
JANELAS.update({
    "I16": [(*S6, 0.008)],                  # tipo de evento nulo ou fora do dominio (ESTORNO)
    "I17": [(*S6, 0.012)],                  # multa fora da regra, com total coerente (so a funcao de regra pega)
    "I18": [(*S7, 0.004)],                  # cliente sem id (passa a barreira)
    "I19": [(*S7, 0.004)],                  # apolice sem numero (passa a barreira)
    "I20": [(*S7, 0.004)],                  # parcela sem numero (passa a barreira)
    "I21": [(*S7, 0.003)],                  # vencimento nulo numa atualizacao (passa a barreira e chega a fato)
    "I22": [(*S6, 0.012)],                  # faixa de atraso fora do dominio no arquivo de origem
    "I23": [(*S6, 0.012)],                  # tentativas de cobranca fora de 1 a 10
    "I24": [(*S7, 0.004)],                  # status PAGA numa atualizacao, sem data de baixa
    "I25": [(*S7, 0.02)],                   # canal de contato fora do dominio (chega a fato)
    "I26": [(*S6, 0.01), (*S7, 0.01)],      # motivo de pendencia nao cadastrado (vira chave orfa na fato)
    "I27": [(*S7, 0.008)],                  # periodicidade nova (vira chave orfa na fato)
    "I28": [(*S6, 0.02), (*S7, 0.02)],      # cadastro do cliente com defeito (chega a dim_cliente)
    "I29": [(*S6, 0.015)],                  # UF em minusculas (a silver padroniza)
    "I30": [(*S7, 0.02)],                   # cadastro da apolice com defeito (chega a dim_apolice)
    "I31": [(*S7, 0.006)],                  # produto novo com cadastro incompleto (dim_produto e ponte)
    "I32": [(*S7, 0.006)],                  # ponto de venda novo inconsistente (dim_ponto_venda)
    "I33": [(*S7, 0.006)],                  # corretor novo inconsistente (dim_corretor)
    "I34": [(*S7, 0.02)],                   # chave digitada errado na NOVA e corrigida depois (chave orfa na fato)
})
ORDEM_INC = list(JANELAS)


def taxa(inc):
    """Expressao SQL da taxa do incidente na data_extracao da linha (0 fora das janelas)."""
    from datetime import date
    partes = []
    for ini, fim, pico in JANELAS[inc]:
        span = (date.fromisoformat(fim) - date.fromisoformat(ini)).days
        partes.append(f"CASE WHEN data_extracao BETWEEN DATE'{ini}' AND DATE'{fim}' THEN {pico} * "
                      f"greatest(0.0, 1.0 - abs(datediff(data_extracao, DATE'{ini}') - {span / 2}) / {span / 2 + 1}) ELSE 0.0 END")
    return partes[0] if len(partes) == 1 else "greatest(" + ", ".join(partes) + ")"


OUT_COLS = COLS + ["tipo_evento", "data_baixa", "valor_pago", "_ingestao_ts", "_lote_id", "_origem"]
FLAGS = ",\n    ".join(f"({U(400 + k, 'numero_apolice', 'numero_parcela', 'tipo_evento')} < {taxa(i)}) AS ap_{i}"
                       for k, i in enumerate(ORDEM_INC))
MOD = {
    "pendencia_id": "CASE WHEN ap_I05 THEN CAST(NULL AS STRING) ELSE pendencia_id END",
    "status_cobranca": "CASE WHEN ap_I04 AND tipo_evento <> 'BAIXA' THEN element_at(array('PAGO', 'EM COBRANCA', 'pendente', 'CANCELADO'), CAST(floor(u_v * 4) AS INT) + 1) ELSE status_cobranca END",
    "valor_parcela": "CASE WHEN ap_I03 THEN CASE WHEN u_v < 0.5 THEN CAST(0 AS DECIMAL(14,2)) ELSE CAST(-valor_parcela AS DECIMAL(14,2)) END ELSE valor_parcela END",
    "valor_total_pendente": ("CASE WHEN ap_I03 THEN CAST((CASE WHEN u_v < 0.5 THEN 0 ELSE -valor_parcela END) + valor_multa + valor_juros AS DECIMAL(14,2)) "
                             "WHEN ap_I07 THEN CAST(round(valor_total_pendente * 1.10, 2) AS DECIMAL(14,2)) ELSE valor_total_pendente END"),
    "data_vencimento": "CASE WHEN ap_I06 THEN date_add(data_extracao, 1 + CAST(floor(u_v * 30) AS INT)) ELSE data_vencimento END",
    "dias_atraso": "CASE WHEN ap_I14 THEN dias_atraso + 2 + CAST(floor(u_v * 5) AS INT) ELSE dias_atraso END",
    "cliente_idade": "CASE WHEN ap_I08 THEN 5 + CAST(floor(u_v * 13) AS INT) ELSE cliente_idade END",
    "cliente_data_nascimento": "CASE WHEN ap_I08 THEN date_sub(data_extracao, 365 * (5 + CAST(floor(u_v * 13) AS INT))) ELSE cliente_data_nascimento END",
    "cliente_uf": "CASE WHEN ap_I09 THEN element_at(array('XX', 'ZZ', 'S1', '00'), CAST(floor(u_v * 4) AS INT) + 1) ELSE cliente_uf END",
    "data_baixa": "CASE WHEN ap_I10 AND tipo_evento = 'BAIXA' THEN CAST(NULL AS DATE) ELSE data_baixa END",
    "forma_pagamento": "CASE WHEN ap_I11 THEN element_at(array('CRIPTOMOEDA', 'VALE_REFEICAO', 'TRANSFERENCIA_INTERNACIONAL'), CAST(floor(u_v * 3) AS INT) + 1) ELSE forma_pagamento END",
    "cliente_cpf": ("CASE WHEN ap_I01 THEN concat(substring(cliente_cpf, 1, length(cliente_cpf) - 1), "
                    "CAST((CAST(right(cliente_cpf, 1) AS INT) + 1 + CAST(floor(u_v * 8) AS INT)) % 10 AS STRING)) ELSE cliente_cpf END"),
    "cliente_email": "CASE WHEN ap_I12 THEN CAST(NULL AS STRING) ELSE cliente_email END",
    "cliente_cep": "CASE WHEN ap_I13 THEN substring(cliente_cep, 1, 4) ELSE cliente_cep END",
    "corretor_id": "CASE WHEN ap_I15 AND canal_venda = 'CORRETOR' THEN CAST(NULL AS STRING) ELSE corretor_id END",
}


def mod(col, cond, val):
    MOD[col] = f"CASE WHEN {cond} THEN {val} ELSE {MOD.get(col, col)} END"


B = "CAST(floor(u_v * 10) AS INT)"   # balde 0..9 do evento, para escolher um defeito por linha
mod("tipo_evento", "ap_I16", "CASE WHEN u_v < 0.5 THEN CAST(NULL AS STRING) ELSE 'ESTORNO' END")
mod("valor_multa", "ap_I17", "CAST(round(valor_parcela * 0.05, 2) AS DECIMAL(14,2))")
mod("valor_total_pendente", "ap_I17", "CAST(valor_parcela + round(valor_parcela * 0.05, 2) + valor_juros AS DECIMAL(14,2))")
mod("cliente_id", "ap_I18", "CAST(NULL AS STRING)")
mod("numero_apolice", "ap_I19", "CAST(NULL AS STRING)")
mod("numero_parcela", "ap_I20", "CAST(NULL AS BIGINT)")
mod("data_vencimento", "ap_I21 AND tipo_evento = 'ATUALIZACAO'", "CAST(NULL AS DATE)")
mod("faixa_atraso", "ap_I22", "element_at(array('SEM_FAIXA', '07_ACIMA_365', '01-15'), CAST(floor(u_v * 3) AS INT) + 1)")
mod("tentativas_cobranca", "ap_I23", "CAST(CASE WHEN u_v < 0.5 THEN 0 ELSE 12 + floor(u_v * 5) END AS INT)")
mod("status_cobranca", "ap_I24 AND tipo_evento = 'ATUALIZACAO'", "'PAGA'")
mod("canal_ultimo_contato", "ap_I25", "element_at(array('FAX', 'TELEGRAMA', 'VISITA_DOMICILIAR'), CAST(floor(u_v * 3) AS INT) + 1)")
mod("motivo_pendencia", "ap_I26", "element_at(array('MOTIVO_NAO_INFORMADO', 'ERRO_SISTEMA_BANCO'), CAST(floor(u_v * 2) AS INT) + 1)")
mod("periodicidade_pagamento", "ap_I27", "element_at(array('QUINZENAL', 'BIMESTRAL'), CAST(floor(u_v * 2) AS INT) + 1)")
# I28: um defeito de cadastro por evento, pelo balde
mod("cliente_sexo", f"ap_I28 AND {B} = 0", "'X'")
mod("cliente_estado_civil", f"ap_I28 AND {B} = 1", "'NAO_INFORMADO'")
mod("cliente_renda_faixa", f"ap_I28 AND {B} = 2", "'SEM_INFORMACAO'")
mod("cliente_rg_data_emissao", f"ap_I28 AND {B} = 3", "date_sub(cliente_data_nascimento, 400)")
mod("cliente_celular", f"ap_I28 AND {B} = 4", "substring(regexp_replace(cliente_celular, '[^0-9]', ''), 1, 10)")
mod("cliente_telefone_fixo", f"ap_I28 AND {B} = 5", "substring(regexp_replace(cliente_telefone_fixo, '[^0-9]', ''), 1, 9)")
mod("cliente_rg", f"ap_I28 AND {B} = 6", "CASE WHEN u_v < 0.63 THEN '12.345' ELSE CAST(NULL AS STRING) END")
mod("cliente_email", f"ap_I28 AND {B} = 7", "concat(split(cliente_email, '@')[0], '.semarroba.com')")
mod("cliente_nome", f"ap_I28 AND {B} = 8", "CAST(NULL AS STRING)")
mod("cliente_cpf", f"ap_I28 AND {B} = 9", "CASE WHEN u_v < 0.95 THEN substring(regexp_replace(cliente_cpf, '[^0-9]', ''), 1, 10) ELSE CAST(NULL AS STRING) END")
mod("cliente_uf", "ap_I29", "lower(cliente_uf)")
# I30: um defeito de cadastro da apolice por evento
mod("status_apolice", f"ap_I30 AND {B} IN (0, 8)", "CASE WHEN " + B + " = 0 THEN 'EM_ANALISE' ELSE CAST(NULL AS STRING) END")
mod("dia_vencimento", f"ap_I30 AND {B} = 1", "CASE WHEN u_v < 0.15 THEN 31 ELSE 0 END")
mod("valor_premio_periodico", f"ap_I30 AND {B} = 2", "CAST(0 AS DECIMAL(14,2))")
mod("qtd_coberturas", f"ap_I30 AND {B} = 3", "0")
mod("qtd_beneficiarios", f"ap_I30 AND {B} = 4", "CASE WHEN u_v < 0.45 THEN 0 ELSE 6 END")
mod("data_fim_vigencia_atual", f"ap_I30 AND {B} IN (5, 9)", "CASE WHEN " + B + " = 5 THEN date_sub(data_inicio_vigencia, 30) ELSE CAST(NULL AS DATE) END")
mod("capital_segurado_total", f"ap_I30 AND {B} = 6", "CAST(capital_segurado_principal - 1000 AS DECIMAL(14,2))")
mod("qtd_endossos", f"ap_I30 AND {B} = 7", "2")
mod("numero_ultimo_endosso", f"ap_I30 AND {B} = 7", "CAST(NULL AS STRING)")
mod("data_emissao", f"ap_I30 AND {B} = 8 AND u_v >= 0.85", "CAST(NULL AS DATE)")
mod("data_inicio_vigencia", f"ap_I30 AND {B} = 9 AND u_v < 0.95", "CAST(NULL AS DATE)")
# I31: produto novo (codigo proprio, para nao estragar os produtos reais), um defeito por codigo
P5 = "CAST(floor(u_v * 5) AS INT)"
mod("produto_codigo", "ap_I31", f"element_at(array('VIDA_QA_NOME', 'VIDA_QA_CATEGORIA', 'VIDA_QA_COB_NULA', 'VIDA_QA_COB_INEXISTENTE', 'VIDA_QA_COB_DUPLICADA'), {P5} + 1)")
mod("produto_nome", f"ap_I31 AND {P5} = 0", "CAST(NULL AS STRING)")
mod("categoria_produto", f"ap_I31 AND {P5} = 1", "CAST(NULL AS STRING)")
mod("cobertura_principal_codigo", f"ap_I31 AND {P5} IN (2, 3, 4)", f"element_at(array(CAST(NULL AS STRING), 'COB_INEXISTENTE', 'IPTA'), {P5} - 1)")
mod("possui_ipta", f"ap_I31 AND {P5} = 4", "true")
# I32: ponto de venda novo, um defeito por codigo
P4 = "CAST(floor(u_v * 4) AS INT)"
mod("ponto_venda_codigo", "ap_I32", f"element_at(array('PV_QA_TIPO', 'PV_QA_CANAL', 'PV_QA_INCOERENTE', 'PV_QA_NOME'), {P4} + 1)")
mod("ponto_venda_tipo", f"ap_I32 AND {P4} IN (0, 2)", f"CASE WHEN {P4} = 0 THEN 'QUIOSQUE' ELSE 'AGENCIA_BANCARIA' END")
mod("canal_venda", f"ap_I32 AND {P4} IN (1, 2)", f"CASE WHEN {P4} = 1 THEN 'PORTA_A_PORTA' ELSE 'CORRETOR' END")
mod("ponto_venda_nome", f"ap_I32 AND {P4} = 3", "CAST(NULL AS STRING)")
# I33: corretor novo (so quando a venda tem corretor), um defeito por codigo
P3 = "CAST(floor(u_v * 3) AS INT)"
mod("corretor_id", "ap_I33 AND corretor_id IS NOT NULL", f"element_at(array('COR_QA_COMISSAO', 'COR_QA_STATUS', 'COR_QA_NOME'), {P3} + 1)")
mod("corretor_comissao_pct", f"ap_I33 AND corretor_id IS NOT NULL AND {P3} = 0", "CAST(45 AS DECIMAL(5,2))")
mod("corretor_status", f"ap_I33 AND corretor_id IS NOT NULL AND {P3} = 1", "'DESCREDENCIADO'")
mod("corretor_nome", f"ap_I33 AND corretor_id IS NOT NULL AND {P3} = 2", "CAST(NULL AS STRING)")
# I34: chave digitada errado na NOVA; o proximo evento traz a chave certa, e a versao antiga fica orfa na fato
mod("cliente_id", f"ap_I34 AND tipo_evento = 'NOVA' AND {P5} = 0", "concat(cliente_id, '-ERR')")
mod("numero_apolice", f"ap_I34 AND tipo_evento = 'NOVA' AND {P5} = 1", "concat(numero_apolice, '-ERR')")
mod("produto_codigo", f"ap_I34 AND tipo_evento = 'NOVA' AND {P5} = 2", "concat(produto_codigo, '-ERR')")
mod("corretor_id", f"ap_I34 AND tipo_evento = 'NOVA' AND {P5} = 3 AND corretor_id IS NOT NULL", "concat(corretor_id, '-ERR')")
mod("ponto_venda_codigo", f"ap_I34 AND tipo_evento = 'NOVA' AND {P5} = 4", "concat(ponto_venda_codigo, '-ERR')")
FLAGS_SQL = (",\n    " + FLAGS) if INCIDENTES_ON else ""
saida = ",\n  ".join(f"{MOD[c]} AS {c}" if (INCIDENTES_ON and c in MOD) else c for c in OUT_COLS)
TAXA_DUP = f"(0.005 + {taxa('I02')})" if INCIDENTES_ON else "0.005"

tabela_existe = spark.catalog.tableExists(BRONZE)
guarda = f"AND data_evento NOT IN (SELECT DISTINCT data_extracao FROM {BRONZE} WHERE data_extracao IS NOT NULL)" if tabela_existe else ""

SQL_EVENTOS = f"""
WITH ap AS (
  SELECT a.*,
         CASE WHEN months_between(date_sub(DATE'{FIM}', 1), a.data_primeira_parcela) < 0 THEN -1
              ELSE CAST(floor(months_between(date_sub(DATE'{FIM}', 1), a.data_primeira_parcela)) AS INT) DIV a.meses_periodicidade END AS j_max
  FROM {FONTE} a
),
dues AS (
  SELECT ap.*, explode(sequence(greatest(0, j_max - 7), j_max)) AS j FROM ap WHERE j_max >= 0
),
base AS (
  SELECT d.*, j + 1 AS numero_parcela, add_months(data_primeira_parcela, j * meses_periodicidade) AS data_vencimento FROM dues d
),
pend AS (   -- uma linha por pendencia (parcela nao paga no vencimento), com o "destino" dela definido por hash
  SELECT b.*,
         {u(203)} < {P_PAGO} AS pago,
         CAST(2 + floor(pow({u(204)}, 2.0) * 58) AS INT) AS dias_ate_baixa,
         CASE WHEN {u(205)} < 0.50 THEN 'A' WHEN {u(205)} < 0.65 THEN 'B' WHEN {u(205)} < 0.80 THEN 'C' ELSE 'D' END AS trilha,
         CAST(2 + floor({u(206)} * 9) AS INT) AS n1,
         CAST(2 + floor({u(206)} * 9) AS INT) + 3 + CAST(floor({u(207)} * 15) AS INT) AS n2,
         CAST(61 + floor({u(208)} * 30) AS INT) AS n3
  FROM base b
  WHERE date_add(data_vencimento, 1) BETWEEN DATE'{INICIO_SIM}' AND DATE'{FIM}'
    AND {u(202)} < p_inadimplencia
),
ev AS (     -- eventos: x = dias de atraso no dia do evento
  SELECT *, 1 AS x, 'NOVA' AS tipo_evento FROM pend
  UNION ALL SELECT *, n1, 'ATUALIZACAO' FROM pend WHERE n1 < IF(pago, dias_ate_baixa, 100000)
  UNION ALL SELECT *, n2, 'ATUALIZACAO' FROM pend WHERE trilha IN ('B', 'C') AND n2 < IF(pago, dias_ate_baixa, 100000)
  UNION ALL SELECT *, n3, 'ATUALIZACAO' FROM pend WHERE trilha = 'D' AND n3 < IF(pago, dias_ate_baixa, 100000)
  UNION ALL SELECT *, dias_ate_baixa, 'BAIXA' FROM pend WHERE pago
),
ev2 AS (
  SELECT ev.*, date_add(data_vencimento, x) AS data_evento,
    CASE WHEN tipo_evento = 'BAIXA' THEN 'PAGA'
         WHEN x < n1 THEN 'PENDENTE'
         WHEN trilha = 'D' THEN CASE WHEN x >= n3 THEN 'COBRANCA_EXTERNA' ELSE 'EM_COBRANCA' END
         WHEN trilha IN ('B', 'C') THEN CASE WHEN x >= n2 THEN CASE trilha WHEN 'B' THEN 'PROMESSA_PAGAMENTO' ELSE 'NEGOCIADO' END ELSE 'EM_COBRANCA' END
         ELSE 'EM_COBRANCA' END AS status_cobranca
  FROM ev
),
base_dia AS (
  SELECT
  {select_cols},
  {extras}
  FROM ev2
  WHERE data_evento BETWEEN DATE'{INI}' AND DATE'{FIM}' {guarda}
),
flags AS (
  SELECT b.*, {U(450, 'numero_apolice', 'numero_parcela', 'tipo_evento')} AS u_v{FLAGS_SQL}
  FROM base_dia b
),
dia AS (
  SELECT
  {saida}
  FROM flags
)
SELECT * FROM dia
UNION ALL
SELECT * FROM dia WHERE pmod(xxhash64(pendencia_id, data_extracao, tipo_evento, {SEED + 301}), 10000) / 10000.0 < {TAXA_DUP}
"""

# COMMAND ----------

if tabela_existe:
    spark.sql(f"INSERT INTO {BRONZE} {SQL_EVENTOS}")
else:
    spark.sql(f"""CREATE TABLE {BRONZE}
      COMMENT 'Bronze: eventos diarios de pendencias de pagamento (seguro de vida) recebidos do sistema de origem. Append-only.'
      AS {SQL_EVENTOS}""")

res = spark.sql(f"""SELECT tipo_evento, count(*) AS linhas, count(DISTINCT data_extracao) AS dias
                    FROM {BRONZE} WHERE data_extracao BETWEEN DATE'{INI}' AND DATE'{FIM}' GROUP BY tipo_evento""").collect()
tot = spark.table(BRONZE).count()
dbutils.notebook.exit(json.dumps({"intervalo": [INI, FIM], "bronze_total": tot,
                                  "no_intervalo": {r["tipo_evento"]: [r["linhas"], r["dias"]] for r in res}}))
'''

# ====================================================================================== gold: dimensoes
def um_por(chave, ordem="data_extracao DESC, pendencia_id"):
    return f"QUALIFY row_number() OVER (PARTITION BY {chave} ORDER BY {ordem}) = 1"


DIMS = []  # (nome, pk, comentario, sql)


def dim(nome, pk, comentario, sql):
    DIMS.append((nome, pk, comentario, sql.strip("\n")))


dim("dim_cliente", "cliente_sk", "Dimensao cliente (cadastro padronizado). SK = xxhash64(cliente_id).", f"""
SELECT
  xxhash64(cliente_id) AS cliente_sk,
  cliente_id, cliente_nome, cliente_cpf, NOT dq_cpf_invalido AS cliente_cpf_valido,
  cliente_rg, cliente_rg_orgao_emissor, cliente_rg_uf_emissor, cliente_rg_data_emissao,
  cliente_data_nascimento, cliente_idade,
  CASE WHEN cliente_idade < 30 THEN '18-29' WHEN cliente_idade < 40 THEN '30-39' WHEN cliente_idade < 50 THEN '40-49'
       WHEN cliente_idade < 60 THEN '50-59' ELSE '60+' END AS cliente_faixa_etaria,
  cliente_sexo, cliente_estado_civil, cliente_profissao, cliente_renda_faixa, cliente_fumante,
  cliente_email, cliente_celular, cliente_telefone_fixo,
  cliente_logradouro, cliente_numero, cliente_complemento, cliente_bairro, cliente_cidade, cliente_uf, cliente_cep,
  cliente_endereco_completo, cliente_data_cadastro
FROM {SRC_ATUAL}
{um_por('cliente_id')}""")

dim("dim_apolice", "apolice_sk", "Dimensao apolice de vida (vigencia, capital, premio, endossos, beneficiarios).", f"""
SELECT
  xxhash64(numero_apolice) AS apolice_sk,
  numero_apolice, status_apolice, data_emissao, data_inicio_vigencia, data_fim_vigencia_atual, dia_vencimento,
  capital_segurado_principal, capital_segurado_total, valor_premio_periodico,
  possui_ipta, possui_ifpd, possui_doencas_graves, possui_dit, possui_assistencia_funeral, qtd_coberturas,
  qtd_endossos, numero_ultimo_endosso, tipo_ultimo_endosso, data_ultimo_endosso,
  qtd_beneficiarios, parentesco_beneficiario_principal
FROM {SRC_ATUAL}
{um_por('numero_apolice')}""")

dim("dim_produto", "produto_sk", "Dimensao produto de seguro de vida.", f"""
SELECT xxhash64(produto_codigo) AS produto_sk, produto_codigo, produto_nome, categoria_produto, ramo,
       cobertura_principal_codigo, cobertura_principal_nome
FROM {SRC_ATUAL}
{um_por('produto_codigo')}""")

dim("dim_cobertura", "cobertura_sk", "Dimensao cobertura (catalogo fixo de coberturas de vida).", """
SELECT xxhash64(cobertura_codigo) AS cobertura_sk, cobertura_codigo, cobertura_nome, grupo_cobertura
FROM VALUES
  ('MORTE', 'Morte (natural ou acidental)', 'MORTE'),
  ('IPTA', 'Invalidez Permanente Total por Acidente', 'INVALIDEZ'),
  ('IFPD', 'Invalidez Funcional Permanente Total por Doenca', 'INVALIDEZ'),
  ('DGR', 'Doencas Graves', 'DOENCAS_GRAVES'),
  ('DIT', 'Diaria por Incapacidade Temporaria', 'INCAPACIDADE_TEMPORARIA'),
  ('AFU', 'Assistencia Funeral', 'ASSISTENCIA')
  AS t(cobertura_codigo, cobertura_nome, grupo_cobertura)""")

dim("bridge_apolice_cobertura", "apolice_sk, cobertura_sk",
    "Ponte N:N entre apolice e cobertura, com papel (principal/adicional) e capital da cobertura. PK composta.", f"""
WITH ap AS (
  SELECT numero_apolice, cobertura_principal_codigo, capital_segurado_principal,
         possui_ipta, possui_ifpd, possui_doencas_graves, possui_dit, possui_assistencia_funeral
  FROM {SRC_ATUAL}
  {um_por('numero_apolice')}
)
SELECT xxhash64(numero_apolice) AS apolice_sk, xxhash64(cobertura_principal_codigo) AS cobertura_sk,
       'PRINCIPAL' AS papel_cobertura, CAST(capital_segurado_principal AS DECIMAL(14,2)) AS capital_segurado_cobertura FROM ap
UNION ALL SELECT xxhash64(numero_apolice), xxhash64('IPTA'), 'ADICIONAL', CAST(capital_segurado_principal * 1.0 AS DECIMAL(14,2)) FROM ap WHERE possui_ipta
UNION ALL SELECT xxhash64(numero_apolice), xxhash64('IFPD'), 'ADICIONAL', CAST(capital_segurado_principal * 0.5 AS DECIMAL(14,2)) FROM ap WHERE possui_ifpd
UNION ALL SELECT xxhash64(numero_apolice), xxhash64('DGR'), 'ADICIONAL', CAST(capital_segurado_principal * 0.3 AS DECIMAL(14,2)) FROM ap WHERE possui_doencas_graves
UNION ALL SELECT xxhash64(numero_apolice), xxhash64('DIT'), 'ADICIONAL', CAST(NULL AS DECIMAL(14,2)) FROM ap WHERE possui_dit
UNION ALL SELECT xxhash64(numero_apolice), xxhash64('AFU'), 'ADICIONAL', CAST(NULL AS DECIMAL(14,2)) FROM ap WHERE possui_assistencia_funeral""")

dim("dim_corretor", "corretor_sk", "Dimensao corretor, com membro NAO_INFORMADO para vendas sem corretor (digital e televendas).", f"""
SELECT * FROM (
  SELECT xxhash64(corretor_id) AS corretor_sk, corretor_id, corretor_nome, corretor_tipo_pessoa, corretor_documento,
         corretor_registro_susep, corretor_regional, corretor_comissao_pct, corretor_status, corretor_data_credenciamento
  FROM {SRC_ATUAL}
  WHERE corretor_id IS NOT NULL
  {um_por('corretor_id')}
)
UNION ALL
SELECT xxhash64('NAO_INFORMADO'), 'NAO_INFORMADO', 'Venda sem corretor', CAST(NULL AS STRING), CAST(NULL AS STRING),
       CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS DECIMAL(5,2)), CAST(NULL AS STRING), CAST(NULL AS DATE)""")

dim("dim_ponto_venda", "ponto_venda_sk", "Dimensao ponto de venda (escritorio, agencia bancaria, plataforma digital, televendas).", f"""
SELECT xxhash64(ponto_venda_codigo) AS ponto_venda_sk, ponto_venda_codigo, ponto_venda_nome, ponto_venda_tipo, canal_venda,
       ponto_venda_cidade, ponto_venda_uf, ponto_venda_regional
FROM {SRC_ATUAL}
{um_por('ponto_venda_codigo')}""")

dim("dim_periodicidade", "periodicidade_sk", "Dimensao periodicidade de pagamento do premio (catalogo fixo).", """
SELECT xxhash64(periodicidade_pagamento) AS periodicidade_sk, periodicidade_pagamento, meses_periodicidade,
       CAST(12 / meses_periodicidade AS INT) AS parcelas_por_ano
FROM VALUES ('MENSAL', 1), ('TRIMESTRAL', 3), ('SEMESTRAL', 6), ('ANUAL', 12) AS t(periodicidade_pagamento, meses_periodicidade)""")

dim("dim_forma_pagamento", "forma_pagamento_sk", "Dimensao forma de pagamento (catalogo fixo).", """
SELECT xxhash64(forma_pagamento) AS forma_pagamento_sk, forma_pagamento, grupo_forma_pagamento
FROM VALUES ('DEBITO_CONTA', 'AUTOMATICO'), ('PIX_AUTOMATICO', 'AUTOMATICO'), ('CARTAO_CREDITO', 'CARTAO'), ('BOLETO', 'BOLETO')
  AS t(forma_pagamento, grupo_forma_pagamento)""")

dim("dim_status_cobranca", "status_cobranca_sk", "Dimensao status de cobranca (ciclo de vida da pendencia, incluindo PAGA).", """
SELECT xxhash64(status_cobranca) AS status_cobranca_sk, status_cobranca, fase_cobranca, ordem_fase, em_aberto
FROM VALUES
  ('PENDENTE', 'INICIAL', 1, true), ('EM_COBRANCA', 'INTERNA', 2, true), ('PROMESSA_PAGAMENTO', 'NEGOCIACAO', 3, true),
  ('NEGOCIADO', 'NEGOCIACAO', 4, true), ('COBRANCA_EXTERNA', 'EXTERNA', 5, true), ('PAGA', 'ENCERRADA', 6, false)
  AS t(status_cobranca, fase_cobranca, ordem_fase, em_aberto)""")

dim("dim_motivo_pendencia", "motivo_pendencia_sk", "Dimensao motivo da pendencia (catalogo fixo, com agrupamento).", """
SELECT xxhash64(motivo_pendencia) AS motivo_pendencia_sk, motivo_pendencia, grupo_motivo
FROM VALUES
  ('SALDO_INSUFICIENTE', 'FINANCEIRO'), ('LIMITE_INSUFICIENTE', 'FINANCEIRO'), ('CARTAO_RECUSADO', 'FINANCEIRO'),
  ('BOLETO_NAO_PAGO', 'FINANCEIRO'), ('DADOS_BANCARIOS_INVALIDOS', 'CADASTRAL'), ('CONTA_ENCERRADA', 'CADASTRAL'),
  ('CARTAO_EXPIRADO', 'CADASTRAL'), ('AUTORIZACAO_DEBITO_CANCELADA', 'AUTORIZACAO'), ('AUTORIZACAO_PIX_REVOGADA', 'AUTORIZACAO'),
  ('BOLETO_NAO_RECEBIDO', 'OPERACIONAL') AS t(motivo_pendencia, grupo_motivo)""")

dim("dim_faixa_atraso", "faixa_atraso_sk", "Dimensao faixa de atraso (catalogo fixo, ordenado).", """
SELECT xxhash64(faixa_atraso) AS faixa_atraso_sk, faixa_atraso, descricao_faixa, dias_min, dias_max, ordem_faixa
FROM VALUES
  ('00_VENCE_HOJE', 'Vence hoje', 0, 0, 0), ('01_1_A_15', '1 a 15 dias', 1, 15, 1), ('02_16_A_30', '16 a 30 dias', 16, 30, 2),
  ('03_31_A_60', '31 a 60 dias', 31, 60, 3), ('04_61_A_90', '61 a 90 dias', 61, 90, 4),
  ('05_91_A_120', '91 a 120 dias', 91, 120, 5), ('06_ACIMA_120', 'Acima de 120 dias', 121, CAST(NULL AS INT), 6)
  AS t(faixa_atraso, descricao_faixa, dias_min, dias_max, ordem_faixa)""")

dim("dim_data", "data_sk", "Dimensao data (calendario 2015-2030). Papeis na fato: referencia, vencimento, emissao, entrada, ultima tentativa.", """
SELECT CAST(date_format(d, 'yyyyMMdd') AS INT) AS data_sk, d AS data, year(d) AS ano,
  CASE WHEN month(d) <= 6 THEN 1 ELSE 2 END AS semestre, quarter(d) AS trimestre, month(d) AS mes,
  element_at(array('Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'), month(d)) AS nome_mes,
  date_format(d, 'yyyy-MM') AS ano_mes, day(d) AS dia, ((dayofweek(d) + 5) % 7) + 1 AS dia_semana,
  element_at(array('Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'), ((dayofweek(d) + 5) % 7) + 1) AS nome_dia_semana,
  weekofyear(d) AS semana_ano, dayofweek(d) IN (1, 7) AS fim_de_semana, d = last_day(d) AS ultimo_dia_mes
FROM (SELECT explode(sequence(DATE'2015-01-01', DATE'2030-12-31', INTERVAL 1 DAY)) AS d)""")

dims_py = "DIMS = [\n" + "".join(f'    ({n!r}, {pk!r}, {c!r}, """\n{s}\n"""),\n' for n, pk, c, s in DIMS) + "]\n"

NB_DIMS = r'''# Databricks notebook source
# MAGIC %md
# MAGIC # pos_venda · 20 · Gold · dimensões do star schema
# MAGIC Atualiza as dimensões a partir da `silver.pendencia_atual`. Na primeira execução cria cada tabela e declara a **PRIMARY KEY**
# MAGIC (informativa no Unity Catalog) com **RELY**: a chave é única por construção (`xxhash64` da chave de negócio, conferido por
# MAGIC `governanca/aplicar_rely.py verificar`), e o RELY deixa o otimizador eliminar junções com dimensões que a consulta não usa.
# MAGIC Nas execuções seguintes faz `INSERT OVERWRITE`, que mantém a tabela e as constraints.
# MAGIC As chaves substitutas são `xxhash64(chave de negócio)`: estáveis entre execuções, então a fato histórica continua válida.

# COMMAND ----------

import json

CAT = "pos_venda"
@@DIMS@@
resultado = {}
for nome, pk, comentario, sql in DIMS:
    fq = f"{CAT}.gold.{nome}"
    if not spark.catalog.tableExists(fq):
        spark.sql(f"CREATE TABLE {fq} COMMENT '{comentario}' AS {sql}")
        for c in [x.strip() for x in pk.split(",")]:
            spark.sql(f"ALTER TABLE {fq} ALTER COLUMN {c} SET NOT NULL")
        spark.sql(f"ALTER TABLE {fq} ADD CONSTRAINT pk_{nome} PRIMARY KEY ({pk}) RELY")
        acao = "criada"
    else:
        spark.sql(f"INSERT OVERWRITE TABLE {fq} {sql}")
        acao = "atualizada"
    resultado[nome] = [acao, spark.table(fq).count()]

dbutils.notebook.exit(json.dumps(resultado))
'''.replace("@@DIMS@@", dims_py)

# ====================================================================================== 30_fato_snapshot
NB_FATO = r'''# Databricks notebook source
# MAGIC %md
# MAGIC # pos_venda · 30 · Gold · fato histórica (snapshot diário)
# MAGIC **Grão:** 1 linha por pendência **em aberto** por dia (`PK = pendencia_id + data_referencia_sk`).
# MAGIC A foto de cada dia vem da `silver.pendencia_hist` (SCD2): vale a versão da pendência vigente naquele dia.
# MAGIC Dias de atraso, multa, juros, faixa e tentativas são recalculados **as-of** o dia da foto; faixa, multa, juros e
# MAGIC total vêm das funções `pos_venda.regras.*` (as mesmas testadas pelo portão `05_portao_regras`).
# MAGIC Idempotente: apaga e regrava só os dias do intervalo. A tabela é agrupada (liquid clustering) por `data_referencia_sk`.

# COMMAND ----------

import json

dbutils.widgets.text("data_inicio", "2026-11-18")
dbutils.widgets.text("data_fim", "2026-11-18")
INI = dbutils.widgets.get("data_inicio").strip()
FIM = dbutils.widgets.get("data_fim").strip()
INI_SK, FIM_SK = int(INI.replace("-", "")), int(FIM.replace("-", ""))

CAT = "pos_venda"
SEED = 20261118
HIST = f"{CAT}.silver.pendencia_hist"
FACT = f"{CAT}.gold.fact_pagamento_pendente_snapshot"

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {FACT} (
  data_referencia_sk INT NOT NULL COMMENT 'Dia da foto (yyyyMMdd)',
  pendencia_id STRING NOT NULL,
  numero_apolice STRING, numero_parcela INT,
  cliente_sk BIGINT, apolice_sk BIGINT, produto_sk BIGINT, corretor_sk BIGINT, ponto_venda_sk BIGINT,
  periodicidade_sk BIGINT, forma_pagamento_sk BIGINT, status_cobranca_sk BIGINT, motivo_pendencia_sk BIGINT, faixa_atraso_sk BIGINT,
  data_vencimento_sk INT, data_emissao_apolice_sk INT, data_entrada_pendencia_sk INT, data_ultima_tentativa_sk INT,
  canal_ultimo_contato STRING, parcela_afetada_por_endosso BOOLEAN,
  qtd_pendencias INT, valor_parcela DECIMAL(14,2), valor_multa DECIMAL(14,2), valor_juros DECIMAL(14,2),
  valor_total_pendente DECIMAL(14,2), dias_atraso INT, tentativas_cobranca INT,
  _carga_ts TIMESTAMP,
  CONSTRAINT pk_fact_pagamento_pendente_snapshot PRIMARY KEY (data_referencia_sk, pendencia_id) RELY
)
CLUSTER BY (data_referencia_sk)
COMMENT 'Fato historica (snapshot diario): pendencias de pagamento em aberto por dia. Grao: pendencia x dia.'
""")

spark.sql(f"DELETE FROM {FACT} WHERE data_referencia_sk BETWEEN {INI_SK} AND {FIM_SK}")
REGRAS = f"{CAT}.regras"   # faixa, multa, juros e total vêm das funções de regra (contrato: pos_venda/regras/features)

def dsk(c):
    return f"CAST(date_format({c}, 'yyyyMMdd') AS INT)"

spark.sql(f"""
INSERT INTO {FACT}
WITH v AS (
  SELECT h.*,
         greatest(h.__START_AT, DATE'{INI}') AS _d_ini,
         least(date_sub(coalesce(h.__END_AT, date_add(DATE'{FIM}', 1)), 1), DATE'{FIM}') AS _d_fim
  FROM {HIST} h
  WHERE h.status_cobranca <> 'PAGA'
),
s AS (SELECT v.*, explode(sequence(_d_ini, _d_fim)) AS _d FROM v WHERE _d_ini <= _d_fim),
c AS (SELECT s.*, datediff(_d, data_vencimento) AS _x FROM s)
SELECT
  {dsk('_d')} AS data_referencia_sk,
  pendencia_id, numero_apolice, CAST(numero_parcela AS INT) AS numero_parcela,
  xxhash64(cliente_id) AS cliente_sk,
  xxhash64(numero_apolice) AS apolice_sk,
  xxhash64(produto_codigo) AS produto_sk,
  xxhash64(coalesce(corretor_id, 'NAO_INFORMADO')) AS corretor_sk,
  xxhash64(ponto_venda_codigo) AS ponto_venda_sk,
  xxhash64(periodicidade_pagamento) AS periodicidade_sk,
  xxhash64(forma_pagamento) AS forma_pagamento_sk,
  xxhash64(status_cobranca) AS status_cobranca_sk,
  xxhash64(motivo_pendencia) AS motivo_pendencia_sk,
  xxhash64({REGRAS}.faixa_atraso(CAST(_x AS INT))) AS faixa_atraso_sk,
  {dsk('data_vencimento')} AS data_vencimento_sk,
  {dsk('data_emissao')} AS data_emissao_apolice_sk,
  {dsk('date_add(data_vencimento, 1)')} AS data_entrada_pendencia_sk,
  {dsk('date_add(data_vencimento, CAST(floor((pmod(xxhash64(numero_apolice, numero_parcela, ' + str(SEED + 209) + '), 1000000) / 1000000.0) * _x) AS INT))')} AS data_ultima_tentativa_sk,
  canal_ultimo_contato,
  parcela_afetada_por_endosso,
  1 AS qtd_pendencias,
  CAST(valor_parcela AS DECIMAL(14,2)) AS valor_parcela,
  {REGRAS}.valor_multa(CAST(valor_parcela AS DECIMAL(14,2))) AS valor_multa,
  {REGRAS}.valor_juros(CAST(valor_parcela AS DECIMAL(14,2)), CAST(_x AS INT)) AS valor_juros,
  {REGRAS}.valor_total_pendente(CAST(valor_parcela AS DECIMAL(14,2)), CAST(_x AS INT)) AS valor_total_pendente,
  CAST(_x AS INT) AS dias_atraso,
  CAST(least(10, 1 + floor(_x / 10) + CASE WHEN status_cobranca = 'PENDENTE' THEN 0 ELSE 1 END) AS INT) AS tentativas_cobranca,
  current_timestamp() AS _carga_ts
FROM c
""")

# chaves estrangeiras (informativas) para as dimensoes; criadas uma vez e SEM RELY: a de forma de pagamento tem orfas de
# proposito (NAO_CADASTRADA), e RELY numa estrangeira deixaria o otimizador trocar LEFT JOIN por INNER JOIN
FKS = [("cliente_sk", "dim_cliente", "cliente_sk"), ("apolice_sk", "dim_apolice", "apolice_sk"), ("produto_sk", "dim_produto", "produto_sk"),
       ("corretor_sk", "dim_corretor", "corretor_sk"), ("ponto_venda_sk", "dim_ponto_venda", "ponto_venda_sk"),
       ("periodicidade_sk", "dim_periodicidade", "periodicidade_sk"), ("forma_pagamento_sk", "dim_forma_pagamento", "forma_pagamento_sk"),
       ("status_cobranca_sk", "dim_status_cobranca", "status_cobranca_sk"), ("motivo_pendencia_sk", "dim_motivo_pendencia", "motivo_pendencia_sk"),
       ("faixa_atraso_sk", "dim_faixa_atraso", "faixa_atraso_sk"), ("data_referencia_sk", "dim_data", "data_sk"),
       ("data_vencimento_sk", "dim_data", "data_sk"), ("data_emissao_apolice_sk", "dim_data", "data_sk"),
       ("data_entrada_pendencia_sk", "dim_data", "data_sk"), ("data_ultima_tentativa_sk", "dim_data", "data_sk")]
fk_status = {}
for col, dim, dcol in FKS:
    nome = f"fk_fact_{col}"
    try:
        spark.sql(f"ALTER TABLE {FACT} ADD CONSTRAINT {nome} FOREIGN KEY ({col}) REFERENCES {CAT}.gold.{dim}({dcol})")
        fk_status[nome] = "criada"
    except Exception as e:
        msg = str(e)
        fk_status[nome] = "ja existia" if ("already exists" in msg or "ALREADY_EXISTS" in msg) else "ERRO: " + msg[:160]

n = spark.sql(f"SELECT count(*) AS n, count(DISTINCT data_referencia_sk) AS dias FROM {FACT} WHERE data_referencia_sk BETWEEN {INI_SK} AND {FIM_SK}").first()
dbutils.notebook.exit(json.dumps({"intervalo": [INI, FIM], "linhas_no_intervalo": n["n"], "dias": n["dias"], "fks": fk_status}))
'''

# ====================================================================================== silver (pipeline Lakeflow)
# A validação do CPF é a função {REGRAS}.cpf_valido (contrato em pos_venda/regras/features/cpf.feature).

OVERRIDES = {
    "cliente_cpf": "_cpf_dig",
    "cliente_rg": "upper(regexp_replace(cliente_rg, '[^0-9Xx]', ''))",
    "cliente_celular": "regexp_replace(cliente_celular, '[^0-9]', '')",
    "cliente_telefone_fixo": "regexp_replace(cliente_telefone_fixo, '[^0-9]', '')",
    "cliente_cep": "regexp_replace(cliente_cep, '[^0-9]', '')",
    "cliente_uf": "upper(cliente_uf)",
    "cliente_email": "lower(trim(cliente_email))",
}
silver_sel = ",\n  ".join(f"{OVERRIDES[c]} AS {c}" if c in OVERRIDES else c for c in COLS)
SILVER_EVENTO = f"""-- Gerado por gerar_carga.py | silver.pendencia_evento (todos os eventos, padronizados)
CREATE OR REFRESH STREAMING TABLE {CAT}.silver.pendencia_evento (
  CONSTRAINT pendencia_id_obrigatorio EXPECT (pendencia_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valor_total_positivo EXPECT (valor_total_pendente > 0) ON VIOLATION DROP ROW,
  CONSTRAINT tipo_evento_valido EXPECT (tipo_evento IN ('NOVA', 'ATUALIZACAO', 'BAIXA')) ON VIOLATION DROP ROW,
  CONSTRAINT cpf_valido EXPECT (NOT dq_cpf_invalido),
  CONSTRAINT email_valido EXPECT (NOT dq_email_invalido)
)
COMMENT 'Silver: todos os eventos de pendencia recebidos (append), com CPF/RG/telefone/CEP/UF padronizados e flags de qualidade (dq_*).'
AS
WITH dig AS (
  SELECT b.*, regexp_replace(b.cliente_cpf, '[^0-9]', '') AS _cpf_dig
  FROM STREAM(bronze_avaliado) b
  WHERE b._motivo_rejeicao IS NULL
),
norm AS (
  SELECT d.*, {REGRAS}.cpf_valido(d._cpf_dig) AS _cpf_valido FROM dig d
)
SELECT
  {silver_sel},
  tipo_evento, data_baixa, valor_pago,
  NOT _cpf_valido AS dq_cpf_invalido,
  cliente_rg IS NULL AS dq_rg_ausente,
  cliente_celular IS NULL AS dq_celular_ausente,
  cliente_email IS NULL AS dq_email_ausente,
  (cliente_email IS NOT NULL AND NOT (lower(trim(cliente_email)) RLIKE '^[^@ ]+@[^@ ]+[.][^@ ]+$')) AS dq_email_invalido,
  _ingestao_ts, _lote_id, _origem,
  current_timestamp() AS _silver_ts
FROM norm;
"""

SILVER_HIST = f"""-- Gerado por gerar_carga.py | silver.pendencia_hist (HISTORICA, SCD Tipo 2)
CREATE OR REFRESH STREAMING TABLE {CAT}.silver.pendencia_hist
COMMENT 'Silver historica (SCD2): uma linha por versao da pendencia. Uma nova versao nasce quando o status de cobranca muda ou a parcela e paga. __START_AT/__END_AT = vigencia [inicio, fim).';

CREATE FLOW pendencia_hist_flow AS AUTO CDC INTO {CAT}.silver.pendencia_hist
FROM STREAM({CAT}.silver.pendencia_evento)
KEYS (pendencia_id)
SEQUENCE BY data_extracao
STORED AS SCD TYPE 2
TRACK HISTORY ON status_cobranca, data_baixa;
"""

SILVER_ATUAL = f"""-- Gerado por gerar_carga.py | silver.pendencia_atual (estado atual, SCD Tipo 1)
CREATE OR REFRESH STREAMING TABLE {CAT}.silver.pendencia_atual
COMMENT 'Silver estado atual: 1 linha por pendencia_id com o ultimo estado conhecido (SCD1). Base das dimensoes da gold.';

CREATE FLOW pendencia_atual_flow AS AUTO CDC INTO {CAT}.silver.pendencia_atual
FROM STREAM({CAT}.silver.pendencia_evento)
KEYS (pendencia_id)
SEQUENCE BY data_extracao
STORED AS SCD TYPE 1;
"""

# ---- barreira de qualidade: avalia cada evento do bronze e separa aptos de nao aptos (quarentena)
UFS_VALIDAS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
               "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
STATUS_VALIDOS = ["PENDENTE", "EM_COBRANCA", "PROMESSA_PAGAMENTO", "NEGOCIADO", "COBRANCA_EXTERNA", "PAGA"]
_ufs = ", ".join(f"'{u}'" for u in UFS_VALIDAS)
_st = ", ".join(f"'{x}'" for x in STATUS_VALIDOS)
# A ordem importa: o motivo e o da PRIMEIRA regra violada. Os nomes batem com as regras de erro cadastradas no DQX Studio.
MOTIVO_REJEICAO = f"""CASE
    WHEN b.pendencia_id IS NULL THEN 'pendencia_id_nulo'
    WHEN b.tipo_evento IS NULL OR b.tipo_evento NOT IN ('NOVA', 'ATUALIZACAO', 'BAIXA') THEN 'tipo_evento_invalido'
    WHEN b.status_cobranca IS NULL OR b.status_cobranca NOT IN ({_st}) THEN 'status_cobranca_invalido'
    WHEN b.valor_parcela IS NULL OR b.valor_parcela <= 0 THEN 'valor_parcela_nao_positivo'
    WHEN abs(b.valor_total_pendente - (b.valor_parcela + b.valor_multa + b.valor_juros)) >= 0.01 THEN 'valor_total_inconsistente'
    WHEN b.data_vencimento >= b.data_extracao THEN 'vencimento_nao_anterior_ao_evento'
    WHEN b.dias_atraso <> datediff(b.data_extracao, b.data_vencimento) THEN 'atraso_nao_confere_com_as_datas'
    WHEN NOT (b.valor_multa <=> {REGRAS}.valor_multa(b.valor_parcela))
      OR NOT (b.valor_juros <=> {REGRAS}.valor_juros(b.valor_parcela, b.dias_atraso))
      OR NOT (b.valor_total_pendente <=> {REGRAS}.valor_total_pendente(b.valor_parcela, b.dias_atraso)) THEN 'valores_fora_da_regra'
    WHEN b.tipo_evento = 'BAIXA' AND (b.data_baixa IS NULL OR b.valor_pago IS NULL) THEN 'baixa_sem_data_ou_valor_pago'
    WHEN upper(trim(b.cliente_uf)) NOT IN ({_ufs}) THEN 'uf_invalida'
    WHEN b.cliente_idade < 18 THEN 'cliente_menor_de_idade'
  END"""

SILVER_AVALIADO = f"""-- Gerado por gerar_carga.py | visao temporaria: bronze + motivo de rejeicao (NULL = evento apto)
CREATE TEMPORARY VIEW bronze_avaliado AS
SELECT b.*, {MOTIVO_REJEICAO} AS _motivo_rejeicao
FROM STREAM({CAT}.bronze.pagamentos_pendentes_eventos) b;
"""

SILVER_QUARENTENA = f"""-- Gerado por gerar_carga.py | silver.pendencia_evento_quarentena (eventos NAO aptos, com o motivo)
CREATE OR REFRESH STREAMING TABLE {CAT}.silver.pendencia_evento_quarentena
COMMENT 'Quarentena: eventos do bronze que violaram uma regra de erro e foram barrados antes da silver. Guarda a linha original e o motivo da rejeicao.'
AS
SELECT * EXCEPT (_motivo_rejeicao), _motivo_rejeicao AS motivo_rejeicao, current_timestamp() AS _quarentena_ts
FROM STREAM(bronze_avaliado)
WHERE _motivo_rejeicao IS NOT NULL;
"""

# ====================================================================================== 25_dq_metricas
NB_DQ = r'''# Databricks notebook source
# MAGIC %md
# MAGIC # pos_venda · 25 · Observabilidade de qualidade
# MAGIC Gera as tabelas de métricas de qualidade por dia (para painéis e para mostrar a evolução) e as **janelas dos últimos 7 dias**
# MAGIC (`pos_venda.dq.v_*_7d`) que o DQX Studio usa para medir a qualidade recente de cada camada.
# MAGIC
# MAGIC | Tabela | O que mostra |
# MAGIC |---|---|
# MAGIC | `gold.dq_barrados_por_motivo_dia` | eventos barrados na silver, por dia e por regra violada |
# MAGIC | `gold.dq_qualidade_diaria` | recebidos, aptos, barrados e métricas de aviso (CPF inválido, e-mail ausente, duplicatas...) por dia |
# MAGIC | `gold.dq_fato_orfas_diarias` | linhas da fato histórica sem dimensão de forma de pagamento (dado ruim que vazou) |

# COMMAND ----------

import json

CAT = "pos_venda"
BR = f"{CAT}.bronze.pagamentos_pendentes_eventos"
EV = f"{CAT}.silver.pendencia_evento"
QT = f"{CAT}.silver.pendencia_evento_quarentena"
ATUAL = f"{CAT}.silver.pendencia_atual"
HIST = f"{CAT}.silver.pendencia_hist"
FACT = f"{CAT}.gold.fact_pagamento_pendente_snapshot"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CAT}.dq COMMENT 'pos_venda - janelas e metricas de qualidade de dados (DQX)'")

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE {CAT}.gold.dq_barrados_por_motivo_dia
COMMENT 'Eventos barrados na silver (quarentena) por dia, motivo da rejeicao e tipo de evento.'
AS
SELECT data_extracao AS dia, motivo_rejeicao, tipo_evento, count(*) AS eventos, count(DISTINCT pendencia_id) AS pendencias,
       round(sum(valor_total_pendente), 2) AS valor_total
FROM {QT}
GROUP BY data_extracao, motivo_rejeicao, tipo_evento
""")

spark.sql(f"""
CREATE OR REPLACE TABLE {CAT}.gold.dq_qualidade_diaria
COMMENT 'Qualidade diaria do fluxo bronze > silver: recebidos, aptos, barrados e metricas de aviso (valores e percentuais).'
AS
WITH rec AS (
  SELECT data_extracao AS dia, count(*) AS eventos_recebidos,
         count(*) - count(DISTINCT pendencia_id, data_extracao, tipo_evento) - count_if(pendencia_id IS NULL) AS eventos_duplicados,
         count_if(cliente_uf <> upper(cliente_uf)) AS uf_minuscula
  FROM {BR} GROUP BY data_extracao
),
apt AS (
  SELECT data_extracao AS dia, count(*) AS eventos_aptos,
         count_if(dq_cpf_invalido) AS cpf_invalido, count_if(dq_email_ausente) AS email_ausente, count_if(dq_email_invalido) AS email_invalido,
         count_if(dq_rg_ausente) AS rg_ausente, count_if(dq_celular_ausente) AS celular_ausente,
         count_if(length(cliente_cep) <> 8) AS cep_malformado,
         count_if(forma_pagamento NOT IN ('DEBITO_CONTA', 'BOLETO', 'CARTAO_CREDITO', 'PIX_AUTOMATICO')) AS forma_pagamento_nao_cadastrada,
         count_if(canal_venda = 'CORRETOR' AND corretor_id IS NULL) AS canal_corretor_sem_corretor
  FROM {EV} GROUP BY data_extracao
),
bar AS (SELECT data_extracao AS dia, count(*) AS eventos_barrados FROM {QT} GROUP BY data_extracao)
SELECT r.dia,
       r.eventos_recebidos, coalesce(a.eventos_aptos, 0) AS eventos_aptos, coalesce(b.eventos_barrados, 0) AS eventos_barrados,
       round(100.0 * coalesce(a.eventos_aptos, 0) / r.eventos_recebidos, 3) AS pct_aptos,
       round(100.0 * coalesce(b.eventos_barrados, 0) / r.eventos_recebidos, 3) AS pct_barrados,
       r.eventos_duplicados, round(100.0 * r.eventos_duplicados / r.eventos_recebidos, 3) AS pct_duplicados,
       r.uf_minuscula,
       coalesce(a.cpf_invalido, 0) AS cpf_invalido, round(100.0 * coalesce(a.cpf_invalido, 0) / nullif(a.eventos_aptos, 0), 3) AS pct_cpf_invalido,
       coalesce(a.email_ausente, 0) AS email_ausente, round(100.0 * coalesce(a.email_ausente, 0) / nullif(a.eventos_aptos, 0), 3) AS pct_email_ausente,
       coalesce(a.email_invalido, 0) AS email_invalido, coalesce(a.rg_ausente, 0) AS rg_ausente, coalesce(a.celular_ausente, 0) AS celular_ausente,
       coalesce(a.cep_malformado, 0) AS cep_malformado, round(100.0 * coalesce(a.cep_malformado, 0) / nullif(a.eventos_aptos, 0), 3) AS pct_cep_malformado,
       coalesce(a.forma_pagamento_nao_cadastrada, 0) AS forma_pagamento_nao_cadastrada,
       round(100.0 * coalesce(a.forma_pagamento_nao_cadastrada, 0) / nullif(a.eventos_aptos, 0), 3) AS pct_forma_pagamento_nao_cadastrada,
       coalesce(a.canal_corretor_sem_corretor, 0) AS canal_corretor_sem_corretor
FROM rec r LEFT JOIN apt a ON a.dia = r.dia LEFT JOIN bar b ON b.dia = r.dia
ORDER BY r.dia
""")

spark.sql(f"""
CREATE OR REPLACE TABLE {CAT}.gold.dq_fato_orfas_diarias
COMMENT 'Fato historica: linhas por foto diaria e quantas ficaram sem dimensao de forma de pagamento (dado nao cadastrado que vazou para a gold).'
AS
SELECT CAST(f.data_referencia_sk AS INT) AS dia_sk, to_date(CAST(f.data_referencia_sk AS STRING), 'yyyyMMdd') AS dia,
       count(*) AS linhas_na_foto, count_if(x.forma_pagamento_sk IS NULL) AS fk_forma_pagamento_orfa
FROM {FACT} f LEFT JOIN {CAT}.gold.dim_forma_pagamento x ON f.forma_pagamento_sk = x.forma_pagamento_sk
WHERE f.data_referencia_sk >= 20261120
GROUP BY f.data_referencia_sk
""")

# COMMAND ----------

# views preservadas: CREATE OR REPLACE VIEW apaga tags e Wiki, entao so recria quando a definicao muda
# (e, nesse caso, devolve tags, tags de coluna e Wiki). Codigo de pos_venda/carga_diaria/views_preservadas.py:
@@VIEWS_PRESERVADAS@@

def _sql(q):
    return [r.asDict() for r in spark.sql(q).collect()]


_api = api_sdk()

# COMMAND ----------

# janelas dos ultimos 7 dias (relativas ao ultimo dia carregado) para o DQX Studio medir a qualidade recente
J = 7
VIEWS_7D = [
    (f"{CAT}.dq.v_bronze_eventos_7d", "Bronze: eventos dos ultimos 7 dias carregados (janela usada pelo DQX Studio).",
     f"SELECT * FROM {BR} WHERE data_extracao > date_sub((SELECT max(data_extracao) FROM {BR}), {J})"),
    (f"{CAT}.dq.v_silver_pendencia_atual_7d", "Silver (estado atual): pendencias com evento nos ultimos 7 dias.",
     f"SELECT * FROM {ATUAL} WHERE data_extracao > date_sub((SELECT max(data_extracao) FROM {ATUAL}), {J})"),
    (f"{CAT}.dq.v_silver_pendencia_hist_7d", "Silver historica (SCD2): versoes iniciadas nos ultimos 7 dias.",
     f"SELECT * FROM {HIST} WHERE __START_AT > date_sub((SELECT max(__START_AT) FROM {HIST}), {J})"),
    (f"{CAT}.dq.v_fato_snapshot_7d", "Gold (fato historica): fotos diarias dos ultimos 7 dias.",
     f"SELECT * FROM {FACT} WHERE data_referencia_sk > (SELECT max(data_referencia_sk) FROM {FACT}) - 7"),
]
for _nome, _comentario, _consulta in VIEWS_7D:
    print(_nome, garantir_view(_nome, _comentario, _consulta, _sql, _api))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Janela de avaliação do DQX Studio
# MAGIC `pos_venda.dq.janela_avaliacao` guarda o intervalo avaliado e as views `pos_venda.dq.v_*_janela` leem só esse intervalo.
# MAGIC O job aponta a janela para os **últimos 7 dias carregados**. O Studio avalia essas views com **todas as linhas**.

# COMMAND ----------

for stmt in @@JANELA_DDL@@:
    spark.sql(stmt)
for _nome, _comentario, _consulta in @@JANELA_VIEWS@@:
    print(_nome, garantir_view(_nome, _comentario, _consulta, _sql, _api))
spark.sql(@@JANELA_APONTAR@@)
display(spark.table(f"{CAT}.dq.janela_avaliacao"))

# COMMAND ----------

res = {
    "dias_com_metrica": spark.table(f"{CAT}.gold.dq_qualidade_diaria").count(),
    "linhas_barradas": spark.table(QT).count(),
    "motivos_distintos": spark.sql(f"SELECT count(DISTINCT motivo_rejeicao) FROM {QT}").first()[0],
}
dbutils.notebook.exit(json.dumps(res))
'''


NB_STUDIO = r'''# Databricks notebook source
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
'''


# ====================================================================================== 05_portao_regras
NB_PORTAO = r'''# Databricks notebook source
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
'''


# ====================================================================================== escrita dos arquivos
nb_dir = ROOT / "src" / "notebooks"
pl_dir = ROOT / "src" / "pipeline" / "transformations"
for d in (nb_dir, pl_dir):
    d.mkdir(parents=True, exist_ok=True)
for name, txt in {"00_setup.py": NB_SETUP, "05_portao_regras.py": NB_PORTAO, "10_gerar_eventos.py": NB_GERAR, "20_gold_dims.py": NB_DIMS, "25_dq_metricas.py": NB_DQ,
                  "30_fato_snapshot.py": NB_FATO, "40_ligar_dqx_studio.py": NB_STUDIO}.items():
    (nb_dir / name).write_text(render(txt), encoding="utf-8")
for name, txt in {"silver_bronze_avaliado.sql": SILVER_AVALIADO, "silver_pendencia_evento_quarentena.sql": SILVER_QUARENTENA,
                  "silver_pendencia_evento.sql": SILVER_EVENTO, "silver_pendencia_hist.sql": SILVER_HIST,
                  "silver_pendencia_atual.sql": SILVER_ATUAL}.items():
    (pl_dir / name).write_text(txt, encoding="utf-8")
# suíte BDD das regras (pos_venda/regras) copiada para dentro do bundle, para o portão do job
SUITE_ORIGEM, SUITE_DESTINO = ROOT.parent / "regras", ROOT / "src" / "portao_regras"
shutil.rmtree(SUITE_DESTINO, ignore_errors=True)
for rel in ["uc.py", "features/environment.py", "features/steps/regras_steps.py",
            *[f"features/{f.name}" for f in sorted((SUITE_ORIGEM / "features").glob("*.feature"))]]:
    (SUITE_DESTINO / rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SUITE_ORIGEM / rel, SUITE_DESTINO / rel)
(SUITE_DESTINO / "LEIA-ME.md").write_text("Cópia gerada de `pos_venda/regras` por `gerar_carga.py`. Não edite aqui: edite em "
                                          "`pos_venda/regras` e rode `python3 gerar_carga.py`.\n", encoding="utf-8")
print(f"ok | colunas da one-table: {len(COLS)} | colunas do cadastro: {len(POLICY_COLS)} | dimensoes: {len(DIMS)}")
