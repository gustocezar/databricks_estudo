"""Janela de avaliacao do DQX Studio (dominio pos_venda).

Uma tabela de controle guarda o intervalo avaliado (data_inicio, data_fim) e as views pos_venda.dq.v_*_janela leem
so esse intervalo. Assim cada camada tem UM destino estavel no Studio, e o historico de execucoes do app mostra a
evolucao da qualidade de semana em semana.

  - o job diario (25_dq_metricas) aponta a janela para os ultimos 7 dias carregados;
  - o replay (pos_venda/dqx_studio/regras/rodar_ciclos.py --replay) aponta para cada semana do passado.

Usado por gerar_carga.py (embute o SQL no notebook) e por rodar_ciclos.py (executa o SQL no warehouse).
"""
CAT = "pos_venda"
TABELA = f"{CAT}.dq.janela_avaliacao"
_INI = f"(SELECT data_inicio FROM {TABELA})"
_FIM = f"(SELECT data_fim FROM {TABELA})"
_SK = "CAST(date_format({}, 'yyyyMMdd') AS INT)"

# view -> (comentario, consulta)
VIEWS = {
    f"{CAT}.dq.v_bronze_eventos_janela": (
        "Bronze: todos os eventos recebidos na janela de avaliacao (aptos e nao aptos).",
        f"SELECT * FROM {CAT}.bronze.pagamentos_pendentes_eventos WHERE data_extracao BETWEEN {_INI} AND {_FIM}"),
    f"{CAT}.dq.v_silver_eventos_aptos_janela": (
        "Silver: eventos que passaram na barreira de qualidade e entraram na silver na janela de avaliacao.",
        f"SELECT * FROM {CAT}.silver.pendencia_evento WHERE data_extracao BETWEEN {_INI} AND {_FIM}"),
    f"{CAT}.dq.v_silver_hist_janela": (
        "Silver historica (SCD2): versoes iniciadas na janela de avaliacao.",
        f"SELECT * FROM {CAT}.silver.pendencia_hist WHERE __START_AT BETWEEN {_INI} AND {_FIM}"),
    f"{CAT}.dq.v_fato_snapshot_janela": (
        "Gold (fato historica): fotos diarias da janela de avaliacao.",
        f"SELECT * FROM {CAT}.gold.fact_pagamento_pendente_snapshot "
        f"WHERE data_referencia_sk BETWEEN {_SK.format(_INI)} AND {_SK.format(_FIM)}"),
    f"{CAT}.dq.v_quarentena_janela": (
        "Quarentena: eventos NAO aptos barrados antes da silver na janela de avaliacao, com o motivo da rejeicao.",
        f"SELECT * FROM {CAT}.silver.pendencia_evento_quarentena WHERE data_extracao BETWEEN {_INI} AND {_FIM}"),
}


def ddl():
    """Cria a tabela de controle. As views vêm de lista_views(), aplicadas com views_preservadas.garantir_view
    (recria só quando a definição muda, para não apagar tags e Wiki todo dia)."""
    return [f"""CREATE TABLE IF NOT EXISTS {TABELA} (
  data_inicio DATE NOT NULL COMMENT 'primeiro dia avaliado',
  data_fim DATE NOT NULL COMMENT 'ultimo dia avaliado',
  origem STRING COMMENT 'quem apontou a janela (job diario ou replay)',
  atualizado_em TIMESTAMP)
COMMENT 'Janela de avaliacao do DQX Studio: intervalo de dias que as views pos_venda.dq.v_*_janela expoem.'"""]


def lista_views():
    """[(view, comentário, consulta)] das views da janela."""
    return [(v, c, q) for v, (c, q) in VIEWS.items()]


def apontar(ini_sql, fim_sql, origem):
    """Aponta a janela (um unico comando, atomico). ini_sql/fim_sql sao expressoes SQL do tipo DATE."""
    return f"INSERT OVERWRITE {TABELA} SELECT {ini_sql}, {fim_sql}, '{origem}', current_timestamp()"


# janela do job diario: os ultimos 7 dias carregados no bronze
APONTAR_ULTIMOS_7 = apontar(f"date_sub((SELECT max(data_extracao) FROM {CAT}.bronze.pagamentos_pendentes_eventos), 6)",
                            f"(SELECT max(data_extracao) FROM {CAT}.bronze.pagamentos_pendentes_eventos)", "job diario")
