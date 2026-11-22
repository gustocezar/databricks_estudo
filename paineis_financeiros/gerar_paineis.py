#!/usr/bin/env python3
"""Gera os painéis AI/BI de KPIs financeiros do Pós-venda a partir das metric views (pos_venda.ontologia.mv_*).

  python3 gerar_paineis.py     -> src/diretoria.lvdash.json e src/analista.lvdash.json + conferência da estrutura

Uma página por fato (carteira em aberto, recuperação, safras, qualidade dos dados) para cada público: diretoria (abre numa
visão executiva) e analista/time de negócio (com filtros globais). O equivalente em Power BI está em powerbi/.

Regras de negócio aplicadas nos datasets:
  - saldo em aberto é SEMIADITIVO: aparece por dia (evolução) ou só na foto mais recente (quebras); nunca somado entre dias;
  - taxas e tickets são medidas do dataset (soma / soma), corretas em qualquer filtro;
  - as consultas usam nomes simples (dataset_catalog = pos_venda, dataset_schema = ontologia no bundle).
"""
import json
import pathlib

AQUI = pathlib.Path(__file__).resolve().parent
GENIE = {"diretoria": "01f1e477314b1903a4212843cf0dabf1", "analista": "01f1e4772cf610a8baf0c236595c284b"}

PALETA = ["#003F5C", "#2F6B9A", "#7A5195", "#BC5090", "#EF5675", "#FFA600", "#58B09C"]
RUIM, ALERTA, BOM = "#EF5675", "#FFA600", "#58B09C"
BRL = {"type": "number-currency", "currencyCode": "BRL", "abbreviation": "compact", "decimalPlaces": {"type": "max", "places": 2}}
BRL_EXATO = {"type": "number-currency", "currencyCode": "BRL", "decimalPlaces": {"type": "exact", "places": 2}}
PCT = {"type": "number-percent", "decimalPlaces": {"type": "max", "places": 1}}
INT = {"type": "number", "abbreviation": "compact", "decimalPlaces": {"type": "max", "places": 1}}

# ------------------------------------------------------------------------------------------------ datasets
DS = {
    "ds_carteira_dia": {
        "displayName": "Carteira em aberto por dia (comparação com 30 dias antes)",
        "queryLines": [
            "WITH d AS (\n",
            "  SELECT `Data de referência` AS data, `Fim de mês` AS fim_mes, `Foto mais recente` AS atual,\n",
            "         MEASURE(`Saldo em aberto`) AS saldo, MEASURE(`Pendências em aberto`) AS pendencias,\n",
            "         MEASURE(`Saldo acima de 60 dias`) AS saldo_60, MEASURE(`Saldo em cobrança externa`) AS saldo_externo,\n",
            "         MEASURE(`Multa e juros em aberto`) AS encargos, MEASURE(`Clientes com pendência`) AS clientes\n",
            "  FROM mv_carteira_em_aberto GROUP BY ALL\n",
            ")\n",
            "SELECT d.*, saldo_60 / saldo AS pct_60, saldo / pendencias AS ticket,\n",
            "       lag(saldo, 30) OVER (ORDER BY data) AS saldo_30d, lag(saldo_60 / saldo, 30) OVER (ORDER BY data) AS pct_60_30d,\n",
            "       lag(pendencias, 30) OVER (ORDER BY data) AS pendencias_30d, lag(saldo / pendencias, 30) OVER (ORDER BY data) AS ticket_30d,\n",
            "       lag(encargos, 30) OVER (ORDER BY data) AS encargos_30d\n",
            "FROM d ORDER BY data"]},
    "ds_carteira_atual": {
        "displayName": "Carteira na foto mais recente, por produto, canal, faixa, status, motivo e forma",
        "queryLines": [
            "SELECT `Data de referência` AS data, `Produto` AS produto, `Canal de venda` AS canal, `Faixa de atraso` AS faixa_atraso,\n",
            "       `Status de cobrança` AS status, `Grupo do motivo` AS grupo_motivo, `Forma de pagamento` AS forma_pagamento,\n",
            "       MEASURE(`Saldo em aberto`) AS saldo, MEASURE(`Pendências em aberto`) AS pendencias,\n",
            "       MEASURE(`Saldo acima de 60 dias`) AS saldo_60, MEASURE(`Saldo em cobrança externa`) AS saldo_externo,\n",
            "       MEASURE(`Multa e juros em aberto`) AS encargos\n",
            "FROM mv_carteira_em_aberto WHERE `Foto mais recente` = true GROUP BY ALL"],
        "columns": [
            {"displayName": "Percentual acima de 60 dias", "description": "Saldo acima de 60 dias / saldo em aberto",
             "expression": "SUM(`saldo_60`) / SUM(`saldo`)"},
            {"displayName": "Ticket médio", "description": "Saldo em aberto / pendências em aberto",
             "expression": "SUM(`saldo`) / SUM(`pendencias`)"}]},
    "ds_recuperacao": {
        "displayName": "Recuperação (baixas) por mês, produto, canal, forma e faixa",
        "queryLines": [
            "SELECT `Mês da baixa` AS mes, `Produto` AS produto, `Canal de venda` AS canal,\n",
            "       CASE WHEN `Forma de pagamento` IN ('DEBITO_CONTA', 'BOLETO', 'CARTAO_CREDITO', 'PIX_AUTOMATICO') THEN `Forma de pagamento` ELSE 'NAO_CADASTRADA' END AS forma_pagamento,\n",
            "       `Faixa de atraso na baixa` AS faixa_baixa,\n",
            "       MEASURE(`Valor recuperado`) AS recuperado, MEASURE(`Pendências pagas`) AS pagas,\n",
            "       MEASURE(`Multa e juros recebidos`) AS encargos_recebidos\n",
            "FROM mv_recuperacao GROUP BY ALL"],
        "columns": [{"displayName": "Ticket médio recuperado", "description": "Valor recuperado / pendências pagas",
                     "expression": "SUM(`recuperado`) / SUM(`pagas`)"}]},
    "ds_safra": {
        "displayName": "Safras de entrada e recuperação",
        "queryLines": [
            "SELECT `Safra de entrada` AS safra, `Produto` AS produto, `Canal de venda` AS canal,\n",
            "       CASE WHEN `Forma de pagamento` IN ('DEBITO_CONTA', 'BOLETO', 'CARTAO_CREDITO', 'PIX_AUTOMATICO') THEN `Forma de pagamento` ELSE 'NAO_CADASTRADA' END AS forma_pagamento,\n",
            "       MEASURE(`Pendências que entraram`) AS entradas, MEASURE(`Pendências pagas da safra`) AS pagas,\n",
            "       MEASURE(`Valor das parcelas que entraram`) AS valor_entrada, MEASURE(`Valor recuperado da safra`) AS valor_recuperado\n",
            "FROM mv_safra_recuperacao GROUP BY ALL"],
        "columns": [{"displayName": "Taxa de recuperação", "description": "Pendências pagas / pendências que entraram",
                     "expression": "SUM(`pagas`) / SUM(`entradas`)"}]},
    # medidas de fechamento e comparação de períodos das metric views (padrões de databricks-solutions/uc-semantics-patterns).
    # Grão produto x canal: a soma das fatias é igual ao total da metric view em todos os meses (conferido).
    "ds_carteira_mes": {
        "displayName": "Fechamento mensal da carteira por produto e canal",
        "queryLines": [
            "WITH m AS (\n",
            "  SELECT `Mês de referência` AS mes, `Produto` AS produto, `Canal de venda` AS canal,\n",
            "         MEASURE(`Saldo no início do período`) AS saldo_inicio, MEASURE(`Saldo de fechamento`) AS saldo_fechamento,\n",
            "         MEASURE(`Saldo de fechamento do mês anterior`) AS saldo_mes_anterior,\n",
            "         MEASURE(`Pendências em aberto no fechamento`) AS pendencias_fechamento\n",
            "  FROM mv_carteira_em_aberto GROUP BY ALL\n",
            ")\n",
            "SELECT m.*, mes = MAX(mes) OVER () AS mes_atual FROM m"],
        "columns": [
            {"displayName": "Variação mensal do saldo", "description": "Fechamento sobre o fechamento do mês anterior (MoM)",
             "expression": "(SUM(`saldo_fechamento`) - SUM(`saldo_mes_anterior`)) / SUM(`saldo_mes_anterior`)"},
            {"displayName": "Variação do saldo no mês", "description": "Fechamento menos o saldo do primeiro dia do mês",
             "expression": "SUM(`saldo_fechamento`) - SUM(`saldo_inicio`)"}]},
    "ds_recuperacao_mes": {
        "displayName": "Recuperação mês a mês e acumulado no ano por produto, canal e forma",
        "queryLines": [
            "WITH m AS (\n",
            "  SELECT `Mês da baixa` AS mes, `Produto` AS produto, `Canal de venda` AS canal,\n",
            "         CASE WHEN `Forma de pagamento` IN ('DEBITO_CONTA', 'BOLETO', 'CARTAO_CREDITO', 'PIX_AUTOMATICO') THEN `Forma de pagamento` ELSE 'NAO_CADASTRADA' END AS forma_pagamento,\n",
            "         MEASURE(`Valor recuperado`) AS recuperado, MEASURE(`Valor recuperado no mês anterior`) AS recuperado_mes_anterior,\n",
            "         MEASURE(`Valor recuperado acumulado no ano`) AS acumulado_ano\n",
            "  FROM mv_recuperacao GROUP BY ALL\n",
            "), c AS (\n",
            "  SELECT m.*, last_day(mes) <= (SELECT max(data_baixa) FROM pagamento) AS mes_completo FROM m\n",
            ")\n",
            "SELECT c.*, mes = MAX(mes) OVER () AS mes_atual,\n",
            "       mes = MAX(CASE WHEN mes_completo THEN mes END) OVER () AS ultimo_mes_completo\n",
            "FROM c"],
        "columns": [
            {"displayName": "Variação mensal do recuperado", "description": "Recuperado no mês sobre o mês anterior (MoM)",
             "expression": "(SUM(`recuperado`) - SUM(`recuperado_mes_anterior`)) / SUM(`recuperado_mes_anterior`)"}]},
    "ds_qualidade": {
        "displayName": "Qualidade dos dados por dia",
        "queryLines": [
            "SELECT `Dia` AS dia, MEASURE(`Eventos recebidos`) AS recebidos, MEASURE(`Eventos aptos`) AS aptos,\n",
            "       MEASURE(`Eventos barrados`) AS barrados, MEASURE(`Eventos duplicados`) AS duplicados,\n",
            "       MEASURE(`E-mail ausente`) AS email_ausente, MEASURE(`CPF inválido`) AS cpf_invalido,\n",
            "       MEASURE(`CEP malformado`) AS cep_malformado, MEASURE(`Forma de pagamento não cadastrada`) AS vazamento\n",
            "FROM mv_qualidade_dados GROUP BY ALL ORDER BY dia"],
        "columns": [{"displayName": "Taxa de barrados", "description": "Eventos barrados / eventos recebidos",
                     "expression": "SUM(`barrados`) / SUM(`recebidos`)"}]},
}


# ------------------------------------------------------------------------------------------------ helpers de widget
def campo(c):
    return {"name": c, "expression": f"`{c}`"}


def soma(c):
    return {"name": f"sum({c})", "expression": f"SUM(`{c}`)"}


def medida(m):
    return {"name": f"measure({m})", "expression": f"MEASURE(`{m}`)"}


def frame(t, d=None):
    f = {"showTitle": True, "title": t}
    if d:
        f.update({"showDescription": True, "description": d})
    return f


def pos(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def texto(nome, linhas, p):
    return {"widget": {"name": nome, "multilineTextboxSpec": {"lines": linhas}}, "position": p}


def consulta(ds, campos, desagregado=False, filtros=None):
    q = {"datasetName": ds, "fields": campos, "disaggregated": desagregado}
    if filtros:
        q["filters"] = [{"expression": f} for f in filtros]
    return [{"name": "main_query", "query": q}]


def kpi_atual(nome, valor, alvo, titulo, fmt, p, descricao):
    """KPI da foto mais recente, comparado com 30 dias antes (linha única do ds_carteira_dia)."""
    enc = {"value": {"fieldName": valor, "displayName": titulo, "format": fmt},
           "target": {"fieldName": alvo, "displayName": "30 dias antes", "format": fmt}}
    return {"widget": {"name": nome, "queries": consulta("ds_carteira_dia", [campo(valor), campo(alvo)], True, ["`atual` = true"]),
                       "spec": {"version": 2, "widgetType": "counter", "encodings": enc, "frame": frame(titulo, descricao)}},
            "position": p}


def kpi(nome, ds, f, titulo, fmt, p, descricao=None, filtros=None):
    enc = {"value": {"fieldName": f["name"], "displayName": titulo}}
    if fmt:
        enc["value"]["format"] = fmt
    return {"widget": {"name": nome, "queries": consulta(ds, [f], filtros=filtros),
                       "spec": {"version": 2, "widgetType": "counter", "encodings": enc, "frame": frame(titulo, descricao)}},
            "position": p}


def grafico(nome, tipo, ds, x, ys, titulo, p, x_tipo="categorical", x_rot=None, fmt=None, cor=None, cor_mapa=None,
            descricao=None, anotacoes=None, mark=None, horizontal=False):
    """ys: lista de (campo, rótulo)."""
    campos = [x] + [c for c, _ in ys] + ([cor] if cor else [])
    eixo_x = {"fieldName": x["name"], "scale": {"type": x_tipo}, "displayName": x_rot or x["name"]}
    if len(ys) == 1:
        eixo_y = {"fieldName": ys[0][0]["name"], "scale": {"type": "quantitative"}, "displayName": ys[0][1]}
    else:
        eixo_y = {"scale": {"type": "quantitative"}, "fields": [{"fieldName": c["name"], "displayName": r} for c, r in ys]}
    if fmt:
        eixo_y["format"] = fmt
    enc = {"x": eixo_y, "y": eixo_x} if horizontal else {"x": eixo_x, "y": eixo_y}
    if cor:
        esc = {"type": "categorical"}
        if cor_mapa:
            esc["mappings"] = [{"value": k, "color": v} for k, v in cor_mapa.items()]
        enc["color"] = {"fieldName": cor["name"], "scale": esc, "displayName": cor.get("_rot", cor["name"])}
        cor.pop("_rot", None)
    spec = {"version": 3, "widgetType": tipo, "encodings": enc, "frame": frame(titulo, descricao)}
    if anotacoes:
        spec["annotations"] = anotacoes
    if mark:
        spec["mark"] = mark
    return {"widget": {"name": nome, "queries": consulta(ds, campos), "spec": spec}, "position": p}


def tabela(nome, ds, colunas, titulo, p, descricao=None):
    """colunas: (campo, rótulo, formato|None). Agrega por dimensão (disaggregated=false)."""
    cols = []
    for c, r, fmt in colunas:
        d = {"fieldName": c["name"], "displayName": r}
        if fmt:
            d["format"] = fmt
        cols.append(d)
    return {"widget": {"name": nome, "queries": consulta(ds, [c for c, *_ in colunas]),
                       "spec": {"version": 2, "widgetType": "table", "encodings": {"columns": cols}, "frame": frame(titulo, descricao)}},
            "position": p}


def filtro(nome, coluna, datasets, titulo, p):
    qs = [{"name": f"f_{coluna}_{d}", "query": {"datasetName": d, "fields": [campo(coluna)], "disaggregated": False}} for d in datasets]
    enc = {"fields": [{"fieldName": coluna, "displayName": titulo, "queryName": q["name"]} for q in qs]}
    return {"widget": {"name": nome, "queries": qs, "spec": {"version": 2, "widgetType": "filter-multi-select", "encodings": enc,
                                                              "frame": frame(titulo)}}, "position": p}


def anot(dia, rot, cor):
    return {"type": "vertical-line", "encodings": {"x": {"dataValue": f"{dia}T00:00:00.000", "dataType": "DATETIME"},
                                                   "label": {"value": rot}, "color": {"value": {"hex": cor}}}}


def rot(f, r):
    f = dict(f)
    f["_rot"] = r
    return f


FORMAS = {"DEBITO_CONTA": "#003F5C", "CARTAO_CREDITO": "#7A5195", "BOLETO": "#2F6B9A", "PIX_AUTOMATICO": "#58B09C", "NAO_CADASTRADA": RUIM}

# ================================================================================================ textos e peças comuns
# Os textos não citam datas fixas: a carga diária muda a foto mais recente todo dia.
NOTA_SALDO = ("O saldo é uma posição diária: aparece por dia ou na **foto mais recente** e nunca se soma entre dias. "
              "O mês corrente ainda não fechou: nele vale a foto mais recente. Dados sintéticos.")
DATA = {"name": "data", "expression": "`data`"}
MES = {"name": "mes", "expression": "`mes`"}
SAFRA = {"name": "safra", "expression": "`safra`"}
DIA = {"name": "dia", "expression": "`dia`"}
ANOT_VAZAMENTO = [anot("2026-12-13", "Vazamento de dados (forma de pagamento)", ALERTA)]


def cabecalho(nome, titulo, texto_, altura=2):
    return texto(nome, [f"## {titulo}\n", "\n", texto_], pos(0, 0, 12, altura))


# Peças reaproveitadas pelas duas audiências (cada uso recebe um nome próprio: o nome do widget é único no painel)
def k_saldo(n, y): return kpi_atual(n, "saldo", "saldo_30d", "Saldo em aberto", BRL, pos(0, y, 3, 3), "Foto mais recente vs. 30 dias antes")
def k_pct60(n, x, y): return kpi_atual(n, "pct_60", "pct_60_30d", "% do saldo acima de 60 dias", PCT, pos(x, y, 3, 3), "Risco: atraso longo")
def k_pend(n, x, y): return kpi_atual(n, "pendencias", "pendencias_30d", "Pendências em aberto", INT, pos(x, y, 3, 3), "Parcelas em atraso, vs. 30 dias antes")
def k_mom_saldo(n, x, y): return kpi(n, "ds_carteira_mes", medida("Variação mensal do saldo"), "Variação mensal do saldo", PCT, pos(x, y, 3, 3),
                                     "Mês corrente (foto mais recente) vs. fechamento do mês anterior", filtros=["`mes_atual` = true"])
def k_cresc(n, x, y): return kpi(n, "ds_carteira_mes", medida("Variação do saldo no mês"), "Crescimento da carteira no mês", BRL, pos(x, y, 3, 3),
                                 "Foto mais recente menos o saldo do dia 1º do mês", filtros=["`mes_atual` = true"])
def k_ytd(n, x, y): return kpi(n, "ds_recuperacao_mes", soma("acumulado_ano"), "Recuperado no ano", BRL, pos(x, y, 3, 3),
                               "Acumulado do ano até a foto mais recente", filtros=["`mes_atual` = true"])
def k_mom_rec(n, x, y): return kpi(n, "ds_recuperacao_mes", medida("Variação mensal do recuperado"), "Variação mensal do recuperado", PCT,
                                   pos(x, y, 3, 3), "Último mês completo vs. o mês anterior", filtros=["`ultimo_mes_completo` = true"])
def k_taxa(n, x, y): return kpi(n, "ds_safra", medida("Taxa de recuperação"), "Taxa de recuperação", PCT, pos(x, y, 3, 3),
                                "Pendências pagas / que entraram (todas as safras)")
def g_saldo_dia(n, p): return grafico(n, "line", "ds_carteira_dia", DATA, [(soma("saldo"), "Saldo em aberto"), (soma("saldo_60"), "Acima de 60 dias")],
                                      "Evolução diária do saldo em aberto", p, x_tipo="temporal", x_rot="Data de referência", fmt=BRL,
                                      descricao="Posição de cada dia (sem somar dias)", anotacoes=ANOT_VAZAMENTO)
def g_aging(n, p): return grafico(n, "bar", "ds_carteira_atual", campo("faixa_atraso"), [(soma("saldo"), "Saldo em aberto")], "Aging da carteira hoje",
                                  p, x_rot="Faixa de atraso", fmt=BRL, descricao="Saldo por faixa de atraso na foto mais recente")
def g_recup_mes(n, p): return grafico(n, "bar", "ds_recuperacao", MES, [(soma("recuperado"), "Valor recuperado")], "Valor recuperado por mês", p,
                                      x_tipo="temporal", x_rot="Mês da baixa", fmt=BRL,
                                      descricao="Baixas (parcela + multa + juros pagos); o mês corrente está incompleto")
def g_taxa_safra(n, p): return grafico(n, "line", "ds_safra", SAFRA, [(medida("Taxa de recuperação"), "Taxa de recuperação")],
                                       "Taxa de recuperação por safra", p, x_tipo="temporal", x_rot="Safra de entrada", fmt=PCT,
                                       descricao="Safras recentes tiveram menos tempo para pagar")
def g_barrados(n, p): return grafico(n, "line", "ds_qualidade", DIA, [(medida("Taxa de barrados"), "Taxa de barrados")],
                                     "Confiabilidade dos dados: taxa de eventos barrados", p, x_tipo="temporal", x_rot="Dia", fmt=PCT,
                                     descricao="Eventos que não entraram nos números por violar regras de qualidade")
def g_avisos(n, p): return grafico(n, "line", "ds_qualidade", DIA,
                                   [(soma("cpf_invalido"), "CPF inválido"), (soma("email_ausente"), "E-mail ausente"),
                                    (soma("cep_malformado"), "CEP malformado"), (soma("vazamento"), "Forma de pagamento não cadastrada")],
                                   "Avisos de qualidade por dia", p, x_tipo="temporal", x_rot="Dia",
                                   descricao="Eventos que entraram nos números, mas com dado incompleto ou fora do padrão")
def kpis_qualidade(prefixo, y):
    return [kpi(f"{prefixo}_recebidos", "ds_qualidade", soma("recebidos"), "Eventos recebidos", INT, pos(0, y, 3, 3), "Todo o período"),
            kpi(f"{prefixo}_barrados", "ds_qualidade", soma("barrados"), "Eventos barrados", INT, pos(3, y, 3, 3), "Foram para a quarentena"),
            kpi(f"{prefixo}_taxa_barrados", "ds_qualidade", medida("Taxa de barrados"), "Taxa de barrados", PCT, pos(6, y, 3, 3),
                "Barrados / recebidos"),
            kpi(f"{prefixo}_vazamento", "ds_qualidade", soma("vazamento"), "Forma de pagamento não cadastrada", INT, pos(9, y, 3, 3),
                "Eventos que vazaram a barreira (incidente de dez/2026)")]


# ================================================================================================ DIRETORIA
DIR_RESUMO = [
    texto("cab_dir", ["# Pós-venda · KPIs financeiros da diretoria\n", "\n",
                      "Carteira de parcelas de seguro de vida em atraso. Esta página resume os quatro fatos; cada um tem a sua página "
                      "(carteira em aberto, recuperação, safras e qualidade dos dados). A primeira linha compara a foto mais recente "
                      "com 30 dias antes; a segunda, o mês corrente com o fechamento do mês anterior. " + NOTA_SALDO +
                      " Use **Ask Genie** para perguntas fora do painel."], pos(0, 0, 12, 3)),
    k_saldo("kpi_saldo", 3), k_pct60("kpi_pct60", 3, 3), k_pend("kpi_pendencias", 6, 3), k_taxa("kpi_taxa", 9, 3),
    k_mom_saldo("kpi_mom_saldo", 0, 6), k_cresc("kpi_var_mes", 3, 6), k_ytd("kpi_ytd", 6, 6), k_mom_rec("kpi_mom_recup", 9, 6),
    g_saldo_dia("saldo_diario", pos(0, 9, 6, 6)), g_recup_mes("recuperado_mes", pos(6, 9, 6, 6)),
    g_taxa_safra("taxa_safra", pos(0, 15, 6, 5)), g_barrados("barrados_dia", pos(6, 15, 6, 5)),
]
DIR_CARTEIRA = [
    cabecalho("cab_dir_carteira", "Carteira em aberto",
              "Posição diária das pendências em aberto: risco (atraso acima de 60 dias), crescimento e fechamento de cada mês. " + NOTA_SALDO),
    k_saldo("dc_saldo", 2), k_pct60("dc_pct60", 3, 2), k_pend("dc_pend", 6, 2), k_mom_saldo("dc_mom", 9, 2),
    g_saldo_dia("dc_saldo_diario", pos(0, 5, 8, 6)), g_aging("dc_aging", pos(8, 5, 4, 6)),
    grafico("dc_fechamento", "bar", "ds_carteira_mes", MES, [(soma("saldo_fechamento"), "Saldo de fechamento")], "Saldo de fechamento por mês",
            pos(0, 11, 6, 6), x_tipo="temporal", x_rot="Mês de referência", fmt=BRL, descricao="Último dia de cada mês; mês corrente = foto mais recente"),
    grafico("dc_mom_mes", "bar", "ds_carteira_mes", MES, [(medida("Variação mensal do saldo"), "Variação mensal do saldo")],
            "Variação mensal do saldo de fechamento", pos(6, 11, 6, 6), x_tipo="temporal", x_rot="Mês de referência", fmt=PCT,
            descricao="Crescimento mês a mês; a carteira sintética não baixa pendências por perda"),
    grafico("dc_externa", "bar", "ds_carteira_atual", campo("produto"), [(soma("saldo_externo"), "Saldo em cobrança externa")],
            "Saldo em cobrança externa por produto (hoje)", pos(0, 17, 6, 6), x_rot="Produto", fmt=BRL),
    grafico("dc_status", "bar", "ds_carteira_atual", campo("status"), [(soma("saldo"), "Saldo em aberto")], "Saldo por status de cobrança (hoje)",
            pos(6, 17, 6, 6), x_rot="Status", fmt=BRL),
]
DIR_RECUPERACAO = [
    cabecalho("cab_dir_recup", "Recuperação",
              "Pagamentos (baixas) das pendências: valor recuperado por mês, acumulado no ano e variação sobre o mês anterior. "
              "A variação mensal compara só meses completos."),
    k_ytd("dr_ytd", 0, 2), k_mom_rec("dr_mom", 3, 2),
    kpi("dr_ticket", "ds_recuperacao", medida("Ticket médio recuperado"), "Ticket médio recuperado", BRL_EXATO, pos(6, 2, 3, 3),
        "Valor recuperado / pendências pagas"),
    kpi("dr_encargos", "ds_recuperacao", soma("encargos_recebidos"), "Multa e juros recebidos", BRL, pos(9, 2, 3, 3), "Todas as baixas"),
    g_recup_mes("dr_recup_mes", pos(0, 5, 6, 6)),
    grafico("dr_ytd_linha", "line", "ds_recuperacao_mes", MES, [(soma("acumulado_ano"), "Acumulado no ano")], "Valor recuperado acumulado no ano",
            pos(6, 5, 6, 6), x_tipo="temporal", x_rot="Mês da baixa", fmt=BRL, descricao="Soma das baixas desde 1º de janeiro (dados desde 19/05/2026)"),
    grafico("dr_recup_forma", "bar", "ds_recuperacao", MES, [(soma("recuperado"), "Valor recuperado")], "Valor recuperado por mês e forma de pagamento",
            pos(0, 11, 12, 6), x_tipo="temporal", x_rot="Mês da baixa", fmt=BRL, cor=rot(campo("forma_pagamento"), "Forma de pagamento"),
            cor_mapa=FORMAS),
]
DIR_SAFRAS = [
    cabecalho("cab_dir_safras", "Safras",
              "Safra = mês em que a pendência entrou na carteira. A taxa de recuperação é a parte da safra que já foi paga; "
              "compare safras de mesma idade (as recentes tiveram menos tempo)."),
    k_taxa("sf_taxa", 0, 2),
    kpi("sf_entradas", "ds_safra", soma("entradas"), "Pendências que entraram", INT, pos(3, 2, 3, 3), "Todas as safras"),
    kpi("sf_pagas", "ds_safra", soma("pagas"), "Pendências pagas", INT, pos(6, 2, 3, 3), "Todas as safras"),
    kpi("sf_valor", "ds_safra", soma("valor_recuperado"), "Valor recuperado das safras", BRL, pos(9, 2, 3, 3), "Pago pelas pendências das safras"),
    g_taxa_safra("sf_taxa_safra", pos(0, 5, 12, 6)),
    grafico("sf_taxa_canal", "bar", "ds_safra", campo("canal"), [(medida("Taxa de recuperação"), "Taxa de recuperação")],
            "Taxa de recuperação por canal de venda", pos(0, 11, 6, 6), x_rot="Canal de venda", fmt=PCT),
    grafico("sf_taxa_forma", "bar", "ds_safra", campo("forma_pagamento"), [(medida("Taxa de recuperação"), "Taxa de recuperação")],
            "Taxa de recuperação por forma de pagamento", pos(6, 11, 6, 6), x_rot="Forma de pagamento", fmt=PCT),
]
DIR_QUALIDADE = [
    cabecalho("cab_dir_qualidade", "Qualidade dos dados",
              "Quanto dos eventos do sistema de origem entra nos números. Eventos barrados vão para a quarentena e não entram; "
              "avisos entram, mas com dado incompleto. O detalhe por regra está no painel **pos_venda · Qualidade de dados**."),
    *kpis_qualidade("dq", 2),
    g_barrados("dq_barrados_dia", pos(0, 5, 12, 6)),
    g_avisos("dq_avisos", pos(0, 11, 12, 6)),
]

# ================================================================================================ ANALISTA (time de negócio)
AN_CARTEIRA = [
    cabecalho("cab_an_carteira", "Carteira em aberto (foto mais recente)",
              "Composição do saldo da foto mais recente por faixa de atraso, status, motivo, forma de pagamento, produto e canal. "
              "No fim da página, o fechamento de cada mês com a variação sobre o mês anterior. "
              "Use os filtros (produto, canal, forma de pagamento) na página Filtros; clique numa barra para filtrar as demais."),
    k_saldo("kpi_an_saldo", 2), k_pend("kpi_an_pend", 3, 2),
    kpi_atual("kpi_an_ticket", "ticket", "ticket_30d", "Ticket médio da pendência", BRL_EXATO, pos(6, 2, 3, 3), "Saldo / pendências"),
    kpi_atual("kpi_an_encargos", "encargos", "encargos_30d", "Multa e juros em aberto", BRL, pos(9, 2, 3, 3), "vs. 30 dias antes"),
    grafico("an_aging", "bar", "ds_carteira_atual", campo("faixa_atraso"),
            [(soma("saldo"), "Saldo em aberto")], "Saldo por faixa de atraso", pos(0, 5, 6, 6), x_rot="Faixa de atraso", fmt=BRL),
    grafico("an_status", "bar", "ds_carteira_atual", campo("status"), [(soma("saldo"), "Saldo em aberto")], "Saldo por status de cobrança",
            pos(6, 5, 6, 6), x_rot="Status", fmt=BRL),
    grafico("an_motivo", "bar", "ds_carteira_atual", campo("grupo_motivo"), [(soma("saldo"), "Saldo em aberto")],
            "Saldo por grupo de motivo", pos(0, 11, 6, 6), x_rot="Grupo do motivo", fmt=BRL,
            descricao="Cadastral pede atualização de dados; financeiro pede negociação"),
    grafico("an_forma", "bar", "ds_carteira_atual", campo("forma_pagamento"), [(soma("saldo"), "Saldo em aberto")],
            "Saldo por forma de pagamento", pos(6, 11, 6, 6), x_rot="Forma de pagamento", fmt=BRL,
            descricao="NAO_CADASTRADA = dado que vazou da barreira de qualidade"),
    tabela("an_produto_canal", "ds_carteira_atual",
           [(campo("produto"), "Produto", None), (campo("canal"), "Canal", None), (soma("saldo"), "Saldo em aberto", BRL_EXATO),
            (soma("pendencias"), "Pendências", None), (medida("Percentual acima de 60 dias"), "% acima de 60 dias", PCT),
            (medida("Ticket médio"), "Ticket médio", BRL_EXATO)],
           "Carteira por produto e canal", pos(0, 17, 12, 7)),
    tabela("an_fechamento_mensal", "ds_carteira_mes",
           [(campo("mes"), "Mês", None), (campo("produto"), "Produto", None), (campo("canal"), "Canal", None),
            (soma("saldo_inicio"), "Saldo no início do mês", BRL_EXATO), (soma("saldo_fechamento"), "Saldo de fechamento", BRL_EXATO),
            (soma("saldo_mes_anterior"), "Fechamento do mês anterior", BRL_EXATO), (medida("Variação mensal do saldo"), "Variação mensal", PCT),
            (soma("pendencias_fechamento"), "Pendências no fechamento", None)],
           "Fechamento mensal por produto e canal", pos(0, 24, 12, 7),
           descricao="Último dia de cada mês (mês corrente = foto mais recente); variação sobre o fechamento do mês anterior"),
]
AN_RECUPERACAO = [
    cabecalho("cab_an_recup", "Recuperação",
              "Baixas por mês, forma de pagamento, faixa de atraso no pagamento, produto e canal. "
              "No fim da página, a recuperação mês a mês e o acumulado no ano."),
    kpi("kpi_an_recuperado", "ds_recuperacao", soma("recuperado"), "Valor recuperado", BRL, pos(0, 2, 3, 3), "Todas as baixas"),
    kpi("kpi_an_pagas", "ds_recuperacao", soma("pagas"), "Pendências pagas", INT, pos(3, 2, 3, 3), "Todas as baixas"),
    kpi("kpi_an_ticket_rec", "ds_recuperacao", medida("Ticket médio recuperado"), "Ticket médio recuperado", BRL_EXATO, pos(6, 2, 3, 3),
        "Valor recuperado / pendências pagas"),
    kpi("kpi_an_encargos_rec", "ds_recuperacao", soma("encargos_recebidos"), "Multa e juros recebidos", BRL, pos(9, 2, 3, 3), "Todas as baixas"),
    grafico("an_recup_mes_forma", "bar", "ds_recuperacao", MES, [(soma("recuperado"), "Valor recuperado")],
            "Valor recuperado por mês e forma de pagamento", pos(0, 5, 8, 6), x_tipo="temporal", x_rot="Mês da baixa", fmt=BRL,
            cor=rot(campo("forma_pagamento"), "Forma de pagamento"), cor_mapa=FORMAS),
    grafico("an_recup_faixa", "bar", "ds_recuperacao", campo("faixa_baixa"), [(soma("pagas"), "Pendências pagas")],
            "Em que faixa de atraso as pendências são pagas", pos(8, 5, 4, 6), x_rot="Faixa de atraso na baixa"),
    tabela("an_recup_produto_canal", "ds_recuperacao",
           [(campo("produto"), "Produto", None), (campo("canal"), "Canal", None), (soma("recuperado"), "Valor recuperado", BRL_EXATO),
            (soma("pagas"), "Pendências pagas", None), (medida("Ticket médio recuperado"), "Ticket médio", BRL_EXATO),
            (soma("encargos_recebidos"), "Multa e juros recebidos", BRL_EXATO)],
           "Recuperação por produto e canal", pos(0, 11, 12, 7)),
    tabela("an_recup_mes_a_mes", "ds_recuperacao_mes",
           [(campo("mes"), "Mês da baixa", None), (campo("mes_completo"), "Mês completo", None),
            (soma("recuperado"), "Valor recuperado", BRL_EXATO), (soma("recuperado_mes_anterior"), "Mês anterior", BRL_EXATO),
            (medida("Variação mensal do recuperado"), "Variação mensal", PCT), (soma("acumulado_ano"), "Acumulado no ano", BRL_EXATO)],
           "Recuperação mês a mês e acumulado no ano", pos(0, 18, 12, 6),
           descricao="O mês corrente está incompleto: compare a variação mensal só entre meses completos"),
]
AN_SAFRAS = [
    cabecalho("cab_an_safras", "Safras",
              "Taxa de recuperação por safra de entrada (mês em que a pendência entrou). Compare safras de mesma idade."),
    k_taxa("kpi_an_taxa", 0, 2),
    kpi("kpi_an_entradas", "ds_safra", soma("entradas"), "Pendências que entraram", INT, pos(3, 2, 3, 3), "Todas as safras"),
    kpi("kpi_an_pagas_safra", "ds_safra", soma("pagas"), "Pendências pagas", INT, pos(6, 2, 3, 3), "Todas as safras"),
    kpi("kpi_an_valor_safra", "ds_safra", soma("valor_recuperado"), "Valor recuperado das safras", BRL, pos(9, 2, 3, 3),
        "Pago pelas pendências das safras"),
    grafico("an_taxa_safra_canal", "line", "ds_safra", SAFRA, [(medida("Taxa de recuperação"), "Taxa de recuperação")],
            "Taxa de recuperação por safra e canal", pos(0, 5, 6, 6), x_tipo="temporal", x_rot="Safra de entrada", fmt=PCT,
            cor=rot(campo("canal"), "Canal de venda")),
    grafico("an_taxa_forma", "bar", "ds_safra", campo("forma_pagamento"), [(medida("Taxa de recuperação"), "Taxa de recuperação")],
            "Taxa de recuperação por forma de pagamento", pos(6, 5, 6, 6), x_rot="Forma de pagamento", fmt=PCT),
    tabela("an_safra_produto", "ds_safra",
           [(campo("safra"), "Safra", None), (campo("produto"), "Produto", None), (soma("entradas"), "Entraram", None),
            (soma("pagas"), "Pagas", None), (medida("Taxa de recuperação"), "Taxa", PCT),
            (soma("valor_recuperado"), "Valor recuperado", BRL_EXATO)],
           "Safras por produto", pos(0, 11, 12, 7)),
]
AN_QUALIDADE = [
    cabecalho("cab_an_qualidade", "Qualidade dos dados",
              "Eventos recebidos do sistema de origem, quantos foram barrados (não entram nos números) e os avisos de dado incompleto. "
              "Os filtros de produto, canal e forma não se aplicam aqui. O detalhe por regra está no painel **pos_venda · Qualidade de dados**."),
    *kpis_qualidade("an_dq", 2),
    grafico("an_dq_dia", "bar", "ds_qualidade", DIA, [(soma("aptos"), "Aptos"), (soma("barrados"), "Barrados")],
            "Eventos recebidos por dia: aptos e barrados", pos(0, 5, 12, 6), x_tipo="temporal", x_rot="Dia"),
    g_avisos("an_dq_avisos", pos(0, 11, 12, 6)),
]
FILTROS = [
    filtro("f_produto", "produto", ["ds_carteira_atual", "ds_recuperacao", "ds_safra", "ds_carteira_mes", "ds_recuperacao_mes"],
           "Produto", pos(0, 0, 4, 2)),
    filtro("f_canal", "canal", ["ds_carteira_atual", "ds_recuperacao", "ds_safra", "ds_carteira_mes", "ds_recuperacao_mes"],
           "Canal de venda", pos(4, 0, 4, 2)),
    filtro("f_forma", "forma_pagamento", ["ds_carteira_atual", "ds_recuperacao", "ds_safra", "ds_recuperacao_mes"],
           "Forma de pagamento", pos(8, 0, 4, 2)),
]


def pagina(nome, titulo, layout, tipo="PAGE_TYPE_CANVAS"):
    return {"name": nome, "displayName": titulo, "pageType": tipo, "layoutVersion": "GRID_V1", "layout": layout}


def painel(paginas, datasets, genie):
    return {"datasets": [{"name": d, **DS[d]} for d in datasets], "pages": paginas,
            "uiSettings": {"theme": {
                "canvasBackgroundColor": {"light": "#F7F8FA", "dark": "#1F272D"},
                "widgetBackgroundColor": {"light": "#FFFFFF", "dark": "#11171C"},
                "widgetBorderColor": {"light": "#FFFFFF", "dark": "#11171C"},
                "fontColor": {"light": "#11171C", "dark": "#E8ECF0"},
                "selectionColor": {"light": "#2272B4", "dark": "#8ACAFF"},
                "visualizationColors": PALETA, "widgetHeaderAlignment": "LEFT"},
                "genieSpace": {"isEnabled": True, "overrideId": genie, "enablementMode": "ENABLED"}}}


TODOS_DS = ["ds_carteira_dia", "ds_carteira_atual", "ds_recuperacao", "ds_safra", "ds_qualidade", "ds_carteira_mes", "ds_recuperacao_mes"]
# Uma página por fato (carteira em aberto, recuperação, safras, qualidade dos dados) em cada audiência; a diretoria abre num resumo.
PAINEIS = {
    "diretoria": painel([pagina("diretoria", "Visão executiva", DIR_RESUMO), pagina("dir_carteira", "Carteira em aberto", DIR_CARTEIRA),
                         pagina("dir_recuperacao", "Recuperação", DIR_RECUPERACAO), pagina("dir_safras", "Safras", DIR_SAFRAS),
                         pagina("dir_qualidade", "Qualidade dos dados", DIR_QUALIDADE)], TODOS_DS, GENIE["diretoria"]),
    "analista": painel([pagina("carteira", "Carteira em aberto", AN_CARTEIRA), pagina("recuperacao", "Recuperação", AN_RECUPERACAO),
                        pagina("safras", "Safras", AN_SAFRAS), pagina("qualidade", "Qualidade dos dados", AN_QUALIDADE),
                        pagina("filtros", "Filtros", FILTROS, "PAGE_TYPE_GLOBAL_FILTERS")], TODOS_DS, GENIE["analista"]),
}


def conferir(p):
    erros = []
    VERSOES = {"counter": 2, "table": 2, "bar": 3, "line": 3, "filter-multi-select": 2}
    nomes_ds = {d["name"] for d in p["datasets"]}
    for d in p["datasets"]:
        for ln in d["queryLines"][:-1]:
            if not ln.endswith((" ", "\n")):
                erros.append(f"{d['name']}: linha sem quebra final")
        if any(x in "".join(d["queryLines"]) for x in ("pos_venda.", "main.")):
            erros.append(f"{d['name']}: catálogo/schema na consulta")
    nomes_w = [item["widget"]["name"] for pg in p["pages"] for item in pg["layout"]]
    erros += [f"widget repetido: {n}" for n in sorted({n for n in nomes_w if nomes_w.count(n) > 1})]
    for pg in p["pages"]:
        linhas = {}
        for item in pg["layout"]:
            w, ps = item["widget"], item["position"]
            for y in range(ps["y"], ps["y"] + ps["height"]):
                linhas[y] = linhas.get(y, 0) + ps["width"]
            if "spec" not in w:
                continue
            spec = w["spec"]
            if VERSOES.get(spec["widgetType"]) != spec["version"]:
                erros.append(f"{w['name']}: versão")
            qs = {q["name"]: q for q in w["queries"]}
            for q in w["queries"]:
                if q["query"]["datasetName"] not in nomes_ds:
                    erros.append(f"{w['name']}: dataset {q['query']['datasetName']} não está no painel")
            if spec["widgetType"].startswith("filter"):
                for f in spec["encodings"]["fields"]:
                    if f["fieldName"] not in {x["name"] for x in qs[f["queryName"]]["query"]["fields"]}:
                        erros.append(f"{w['name']}: filtro sem campo")
                continue
            nomes = {x["name"] for x in w["queries"][0]["query"]["fields"]}
            for k, v in spec["encodings"].items():
                refs = [c["fieldName"] for c in v] if k == "columns" else (
                    ([v["fieldName"]] if "fieldName" in v else []) + [f["fieldName"] for f in v.get("fields", [])])
                erros += [f"{w['name']}: {r} sem campo" for r in refs if r not in nomes]
            if spec["widgetType"] == "counter" and "color" in spec["encodings"]["value"]:
                erros.append(f"{w['name']}: contador com cor")
        if pg["pageType"] == "PAGE_TYPE_CANVAS":
            erros += [f"{pg['name']}: y={y} soma {s}" for y, s in linhas.items() if s != 12]
    return erros


if __name__ == "__main__":
    (AQUI / "src").mkdir(exist_ok=True)
    for nome, p in PAINEIS.items():
        (AQUI / "src" / f"{nome}.lvdash.json").write_text(json.dumps(p, indent=2, ensure_ascii=False), encoding="utf-8")
        n = sum(len(pg["layout"]) for pg in p["pages"])
        print(f"{nome}: {len(p['datasets'])} datasets | {len(p['pages'])} páginas | {n} widgets | conferência:", conferir(p) or "ok")
