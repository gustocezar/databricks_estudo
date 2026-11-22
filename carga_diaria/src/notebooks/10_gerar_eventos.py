# Databricks notebook source
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
COLS = ['pendencia_id', 'data_extracao', 'sistema_origem', 'numero_apolice', 'numero_parcela', 'competencia', 'data_vencimento', 'data_geracao_cobranca', 'dias_atraso', 'faixa_atraso', 'valor_parcela', 'valor_multa', 'valor_juros', 'valor_total_pendente', 'status_cobranca', 'motivo_pendencia', 'tentativas_cobranca', 'data_ultima_tentativa', 'canal_ultimo_contato', 'parcela_afetada_por_endosso', 'ramo', 'status_apolice', 'produto_codigo', 'produto_nome', 'categoria_produto', 'canal_venda', 'data_emissao', 'data_inicio_vigencia', 'data_fim_vigencia_atual', 'dia_vencimento', 'periodicidade_pagamento', 'meses_periodicidade', 'forma_pagamento', 'valor_premio_periodico', 'capital_segurado_principal', 'capital_segurado_total', 'cobertura_principal_codigo', 'cobertura_principal_nome', 'possui_ipta', 'possui_ifpd', 'possui_doencas_graves', 'possui_dit', 'possui_assistencia_funeral', 'qtd_coberturas', 'qtd_endossos', 'numero_ultimo_endosso', 'tipo_ultimo_endosso', 'data_ultimo_endosso', 'qtd_beneficiarios', 'parentesco_beneficiario_principal', 'ponto_venda_codigo', 'ponto_venda_nome', 'ponto_venda_tipo', 'ponto_venda_cidade', 'ponto_venda_uf', 'ponto_venda_regional', 'corretor_id', 'corretor_nome', 'corretor_tipo_pessoa', 'corretor_documento', 'corretor_registro_susep', 'corretor_regional', 'corretor_comissao_pct', 'corretor_status', 'corretor_data_credenciamento', 'cliente_id', 'cliente_nome', 'cliente_cpf', 'cliente_data_nascimento', 'cliente_idade', 'cliente_sexo', 'cliente_estado_civil', 'cliente_email', 'cliente_celular', 'cliente_telefone_fixo', 'cliente_rg', 'cliente_rg_orgao_emissor', 'cliente_rg_uf_emissor', 'cliente_rg_data_emissao', 'cliente_logradouro', 'cliente_numero', 'cliente_complemento', 'cliente_bairro', 'cliente_cep', 'cliente_cidade', 'cliente_uf', 'cliente_endereco_completo', 'cliente_renda_faixa', 'cliente_profissao', 'cliente_fumante', 'cliente_data_cadastro']

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
FLAGS_SQL = (",\n    " + FLAGS) if INCIDENTES_ON else ""
saida = ",\n  ".join(f"{MOD[c]} AS {c}" if (INCIDENTES_ON and c in MOD) else c for c in OUT_COLS)
TAXA_DUP = f"(0.005 + {taxa('I02')})" if INCIDENTES_ON else "0.005"

tabela_existe = spark.catalog.tableExists(BRONZE)
guarda = f"AND data_evento NOT IN (SELECT DISTINCT data_extracao FROM {BRONZE})" if tabela_existe else ""

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
