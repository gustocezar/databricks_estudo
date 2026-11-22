#!/usr/bin/env python3
"""Gera o painel AI/BI "pos_venda · Qualidade de dados" (src/pos_venda_qualidade.lvdash.json).

  python3 gerar_painel.py      gera o JSON e confere a estrutura (campos x encodings, versões, grade de 12 colunas)

As consultas usam nomes simples de view (pos_venda.dq vem de dataset_catalog / dataset_schema no bundle).
"""
import json
import pathlib

AQUI = pathlib.Path(__file__).resolve().parent
SAIDA = AQUI / "src" / "pos_venda_qualidade.lvdash.json"

# ---- paleta: azul-marinho > azul > roxo > magenta > rosa > âmbar > verde-água (cores semânticas fixas à parte)
PALETA = ["#003F5C", "#2F6B9A", "#7A5195", "#BC5090", "#EF5675", "#FFA600", "#58B09C"]
RUIM, AVISO, BOM = "#FF7E5C", "#FFA600", "#58B09C"
CAMADAS = {"1 · Bronze (tudo que chegou)": "#2F6B9A", "2 · Quarentena (não aptos)": RUIM,
           "3 · Silver (eventos aptos)": "#7A5195", "4 · Silver histórica (SCD2)": BOM, "5 · Gold (fato histórica)": "#003F5C"}

INT = {"type": "number", "abbreviation": "compact", "decimalPlaces": {"type": "max", "places": 1}}
PCT = {"type": "number-percent", "decimalPlaces": {"type": "max", "places": 2}}
BRL = {"type": "number-currency", "currencyCode": "BRL", "abbreviation": "compact", "decimalPlaces": {"type": "max", "places": 2}}

DIA = {"name": "daily(dia)", "expression": 'DATE_TRUNC("DAY", `dia`)'}


def campo(c):
    return {"name": c, "expression": f"`{c}`"}


def agg(fn, c):
    sql = {"sum": "SUM", "avg": "AVG", "max": "MAX", "min": "MIN", "count": "COUNT"}[fn]
    return {"name": f"{fn}({c})", "expression": f"{sql}(`{c}`)"}


def consulta(ds, campos, desagregado=False, nome="main_query"):
    return [{"name": nome, "query": {"datasetName": ds, "fields": campos, "disaggregated": desagregado}}]


def frame(titulo, descricao=None):
    f = {"showTitle": True, "title": titulo}
    if descricao:
        f.update({"showDescription": True, "description": descricao})
    return f


def pos(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def texto(nome, linhas, p):
    return {"widget": {"name": nome, "multilineTextboxSpec": {"lines": linhas}}, "position": p}


def contador(nome, ds, valor, titulo, p, fmt=None, periodo=None, rotulo=None, descricao=None):
    campos = [valor] + ([periodo] if periodo else [])
    enc = {"value": {"fieldName": valor["name"], "displayName": rotulo or titulo}}
    if fmt:
        enc["value"]["format"] = fmt
    if periodo:
        enc["period"] = {"fieldName": periodo["name"]}
    return {"widget": {"name": nome, "queries": consulta(ds, campos),
                       "spec": {"version": 2, "widgetType": "counter", "encodings": enc, "frame": frame(titulo, descricao)}},
            "position": p}


def anotacao(dia, rotulo, cor):
    return {"type": "vertical-line",
            "encodings": {"x": {"dataValue": f"{dia}T00:00:00.000", "dataType": "DATETIME"},
                          "label": {"value": rotulo}, "color": {"value": {"hex": cor}}}}


def grafico(nome, tipo, ds, x, y, titulo, p, cor=None, x_scale="temporal", y_fields=None, fmt_y=None,
            anotacoes=None, mark=None, descricao=None, x_rotulo=None, y_rotulo=None, cor_mapa=None):
    campos = [x] + ([y] if y else []) + (y_fields or []) + ([cor] if cor else [])
    enc = {"x": {"fieldName": x["name"], "scale": {"type": x_scale}, "displayName": x_rotulo or x["name"]}}
    if y_fields:
        enc["y"] = {"scale": {"type": "quantitative"},
                    "fields": [{"fieldName": f["name"], "displayName": f["_rotulo"]} for f in y_fields]}
    else:
        enc["y"] = {"fieldName": y["name"], "scale": {"type": "quantitative"}, "displayName": y_rotulo or y["name"]}
    if fmt_y:
        enc["y"]["format"] = fmt_y
    if cor:
        escala = {"type": "categorical"}
        if cor_mapa:
            escala["mappings"] = [{"value": k, "color": v} for k, v in cor_mapa.items()]
        enc["color"] = {"fieldName": cor["name"], "scale": escala, "displayName": cor.get("_rotulo", cor["name"])}
    spec = {"version": 3, "widgetType": tipo, "encodings": enc, "frame": frame(titulo, descricao)}
    if anotacoes:
        spec["annotations"] = anotacoes
    if mark:
        spec["mark"] = mark
    for f in campos:
        f.pop("_rotulo", None)
    return {"widget": {"name": nome, "queries": consulta(ds, campos), "spec": spec}, "position": p}


def barras_horizontais(nome, ds, categoria, medida, titulo, p, rotulo_medida, descricao=None):
    enc = {"x": {"fieldName": medida["name"], "scale": {"type": "quantitative"}, "displayName": rotulo_medida},
           "y": {"fieldName": categoria["name"], "scale": {"type": "categorical"},
                 "displayName": "Motivo"}}
    return {"widget": {"name": nome, "queries": consulta(ds, [categoria, medida]),
                       "spec": {"version": 3, "widgetType": "bar", "encodings": enc, "frame": frame(titulo, descricao)}},
            "position": p}


def mapa_calor(nome, ds, x, y, valor, titulo, p, x_rotulo, y_rotulo, descricao=None, inicio="#FDF1E0", fim=RUIM):
    enc = {"x": {"fieldName": x["name"], "scale": {"type": "categorical"}, "displayName": x_rotulo},
           "y": {"fieldName": y["name"], "scale": {"type": "categorical"}, "displayName": y_rotulo},
           "color": {"fieldName": valor["name"],
                     "scale": {"type": "quantitative",
                               "colorRamp": {"mode": "custom-sequential", "colors": {"start": inicio, "end": fim}}}},
           "label": {"show": True}}
    return {"widget": {"name": nome, "queries": consulta(ds, [x, y, valor]),
                       "spec": {"version": 3, "widgetType": "heatmap", "encodings": enc, "frame": frame(titulo, descricao)}},
            "position": p}


def tabela(nome, ds, colunas, titulo, p, descricao=None):
    """colunas: lista de (coluna, rótulo, formato|None, destaque_hex|None)."""
    cols = []
    for c, r, fmt, cor in colunas:
        d = {"fieldName": c, "displayName": r}
        if fmt:
            d["format"] = fmt
        if cor:
            d["style"] = {"type": "basic", "rules": [{"condition": {"operand": {"type": "data-value", "value": "0"}, "operator": ">"},
                                                      "backgroundColor": {"hex": cor}}]}
        cols.append(d)
    return {"widget": {"name": nome, "queries": consulta(ds, [campo(c) for c, *_ in colunas], desagregado=True),
                       "spec": {"version": 2, "widgetType": "table", "encodings": {"columns": cols}, "frame": frame(titulo, descricao)}},
            "position": p}


def filtro(nome, tipo, coluna, datasets, titulo, p):
    qs = [{"name": f"f_{coluna}_{ds}", "query": {"datasetName": ds, "fields": [campo(coluna)], "disaggregated": False}} for ds in datasets]
    enc = {"fields": [{"fieldName": coluna, "displayName": titulo, "queryName": q["name"]} for q in qs]}
    return {"widget": {"name": nome, "queries": qs,
                       "spec": {"version": 2, "widgetType": tipo, "encodings": enc, "frame": frame(titulo)}},
            "position": p}


def rot(f, r):
    f = dict(f)
    f["_rotulo"] = r
    return f


# ====================================================================================================== datasets
DATASETS = [
    {"name": "ds_diario", "displayName": "Qualidade diária (bronze > silver) e órfãs da fato",
     "queryLines": ["SELECT * FROM v_painel_diario ", "ORDER BY dia"],
     "columns": [{"displayName": "Taxa de barrados", "description": "Eventos barrados / eventos recebidos no período",
                  "expression": "SUM(`eventos_barrados`) * 1.0 / SUM(`eventos_recebidos`)"}]},
    {"name": "ds_barrados", "displayName": "Barrados por dia, motivo e tipo de evento",
     "queryLines": ["SELECT * FROM v_painel_barrados ", "ORDER BY dia, motivo_rejeicao"]},
    {"name": "ds_quarentena", "displayName": "Dados não aptos (quarentena do pipeline)",
     "queryLines": ["SELECT * FROM v_painel_quarentena ", "ORDER BY dia DESC, motivo_rejeicao, pendencia_id"]},
    {"name": "ds_studio_exec", "displayName": "DQX Studio: execuções completas por semana",
     "queryLines": ["SELECT * EXCEPT (error_summary_json) FROM v_painel_studio_execucoes ", "ORDER BY semana_n, camada"],
     "columns": [{"displayName": "Quarentena reprovada no Studio",
                  "description": "Linhas da quarentena do pipeline que reprovam em alguma regra de erro do Studio",
                  "expression": "SUM(CASE WHEN `camada_curta` = 'quarentena' THEN `error_rows` ELSE 0 END) * 1.0 / "
                                "SUM(CASE WHEN `camada_curta` = 'quarentena' THEN `total_rows` ELSE 0 END)"}]},
    {"name": "ds_studio_regras", "displayName": "DQX Studio: regras violadas por semana",
     "queryLines": ["SELECT * FROM v_painel_studio_regras ", "WHERE camada_curta <> 'quarentena' ", "ORDER BY semana_n, regra_rotulo"]},
    {"name": "ds_studio_reprovadas", "displayName": "DQX Studio: linhas reprovadas com a regra",
     "queryLines": ["SELECT * FROM v_painel_studio_reprovadas ", "ORDER BY semana_n DESC, camada, regra"]},
]

# ====================================================================================================== página 1
p1 = [
    texto("cabecalho_visao", [
        "# pos_venda · Qualidade dos pagamentos pendentes\n", "\n",
        "Cinco semanas de cargas diárias simuladas. **Semana 1** é a linha de base. Na **semana 2** sobem os *avisos* "
        "(CPF inválido, e-mail ausente, duplicatas): o dado entra, sinalizado. Nas **semanas 3 e 4** chegam *erros* "
        "(valor ≤ 0, status inválido, total inconsistente, vencimento futuro, menor de idade, UF inválida...), barrados na "
        "quarentena antes da silver. Em 13/12 uma **forma de pagamento nova vaza**: não estava na barreira, entra na silver "
        "e vira chave órfã na fato. Na **semana 5** os incidentes caem até zerar, mas as órfãs ficam enquanto as pendências "
        "seguem abertas."], pos(0, 0, 12, 3)),
    contador("kpi_recebidos", "ds_diario", agg("sum", "eventos_recebidos"), "Eventos recebidos", pos(0, 3, 3, 3), INT, DIA,
             rotulo="Recebidos", descricao="Bronze, no período filtrado"),
    contador("kpi_barrados", "ds_diario", agg("sum", "eventos_barrados"), "Eventos barrados", pos(3, 3, 3, 3), INT, DIA,
             rotulo="Barrados", descricao="Foram para a quarentena"),
    contador("kpi_taxa_barrados", "ds_diario", {"name": "measure(Taxa de barrados)", "expression": "MEASURE(`Taxa de barrados`)"},
             "Taxa de barrados", pos(6, 3, 3, 3), PCT, DIA, rotulo="% barrados", descricao="Barrados / recebidos"),
    contador("kpi_orfas", "ds_diario", agg("max", "fato_linhas_orfas"), "Pico de linhas órfãs na fato", pos(9, 3, 3, 3), None, DIA,
             rotulo="Órfãs (pico diário)", descricao="Forma de pagamento sem dimensão"),
    grafico("barrados_por_dia", "bar", "ds_diario", DIA, agg("sum", "eventos_barrados"), "Eventos barrados por dia", pos(0, 6, 8, 6),
            x_rotulo="Dia", y_rotulo="Eventos barrados",
            anotacoes=[anotacao("2026-11-27", "Semana 2: só avisos", AVISO), anotacao("2026-12-04", "Semana 3: chegam os erros", RUIM),
                       anotacao("2026-12-13", "Forma de pagamento nova vaza", "#7A5195")],
            descricao="Quantos eventos a barreira de qualidade segurou a cada dia"),
    barras_horizontais("barrados_por_motivo", "ds_barrados", campo("motivo_rejeicao"), agg("sum", "eventos"),
                       "Barrados por motivo", pos(8, 6, 4, 6), "Eventos", descricao="Primeira regra de erro violada"),
    grafico("avisos_por_dia", "line", "ds_diario", DIA, None, "Avisos que passam (% dos eventos)", pos(0, 12, 6, 6),
            x_rotulo="Dia", fmt_y=PCT,
            y_fields=[rot(agg("avg", "taxa_email_ausente"), "E-mail ausente"), rot(agg("avg", "taxa_cpf_invalido"), "CPF inválido"),
                      rot(agg("avg", "taxa_duplicados"), "Duplicatas"), rot(agg("avg", "taxa_cep_malformado"), "CEP malformado")],
            descricao="Problemas sinalizados como aviso: entram na silver, com alerta"),
    grafico("orfas_por_dia", "bar", "ds_diario", DIA, agg("sum", "fato_linhas_orfas"), "Fato histórica: linhas com forma de pagamento órfã",
            pos(6, 12, 6, 6), x_rotulo="Dia", y_rotulo="Linhas órfãs na foto do dia",
            anotacoes=[anotacao("2026-12-13", "Vazamento começa", "#7A5195"), anotacao("2026-12-22", "Último dia na origem", BOM)],
            descricao="Dado não cadastrado que passou pela barreira e chegou à gold"),
    mapa_calor("motivo_por_semana", "ds_barrados", campo("semana"), campo("motivo_rejeicao"), agg("sum", "eventos"),
               "Eventos barrados por motivo e semana", pos(0, 18, 12, 6), "Semana", "Motivo da rejeição",
               descricao="Cada incidente aparece na semana em que foi injetado"),
]

# ====================================================================================================== página 2
p2 = [
    texto("cabecalho_studio", [
        "## DQX Studio · evolução semana a semana\n", "\n",
        "Cada camada foi avaliada pelo Studio uma vez por semana, com **todas as linhas** da janela (views "
        "`pos_venda.dq.v_*_janela`). Erros na **silver** e na **fato** só aparecem quando algo **vazou** da barreira; "
        "a **quarentena** reprova 100% nas regras de erro: pipeline e Studio usam a mesma régua."], pos(0, 0, 12, 2)),
    contador("kpi_studio_linhas", "ds_studio_exec", agg("sum", "total_rows"), "Linhas avaliadas pelo Studio", pos(0, 2, 3, 3), INT,
             rotulo="Linhas avaliadas", descricao="Execuções completas (sem amostra)"),
    contador("kpi_studio_erros", "ds_studio_exec", agg("sum", "error_rows"), "Linhas reprovadas", pos(3, 2, 3, 3), INT,
             rotulo="Em erro", descricao="Violam ao menos uma regra de erro"),
    contador("kpi_studio_avisos", "ds_studio_exec", agg("sum", "warning_rows"), "Linhas com aviso", pos(6, 2, 3, 3), INT,
             rotulo="Com aviso", descricao="Passam, mas sinalizadas"),
    contador("kpi_studio_reconciliacao", "ds_studio_exec",
             {"name": "measure(Quarentena reprovada no Studio)", "expression": "MEASURE(`Quarentena reprovada no Studio`)"},
             "Quarentena reprovada no Studio", pos(9, 2, 3, 3), PCT, rotulo="Reprovadas",
             descricao="Reconciliação pipeline × Studio"),
    grafico("studio_erros_semana", "bar", "ds_studio_exec", campo("semana"), agg("sum", "error_rows"), "Linhas em erro por semana e camada",
            pos(0, 5, 6, 6), cor=rot(campo("camada"), "Camada"), x_scale="categorical", mark={"layout": "group"},
            x_rotulo="Semana", y_rotulo="Linhas em erro", cor_mapa=CAMADAS),
    grafico("studio_avisos_semana", "bar", "ds_studio_exec", campo("semana"), agg("sum", "warning_rows"), "Linhas com aviso por semana e camada",
            pos(6, 5, 6, 6), cor=rot(campo("camada"), "Camada"), x_scale="categorical", mark={"layout": "group"},
            x_rotulo="Semana", y_rotulo="Linhas com aviso", cor_mapa=CAMADAS),
    mapa_calor("studio_regras_semana", "ds_studio_regras", campo("semana"), campo("regra_rotulo"), agg("sum", "linhas"),
               "Regras violadas por semana (linhas)", pos(0, 11, 12, 9), "Semana", "Camada · regra (criticidade)",
               descricao="Bronze, silver e fato; a quarentena repete as regras do bronze e fica de fora"),
    tabela("studio_execucoes", "ds_studio_exec", [
        ("semana", "Semana", None, None), ("camada", "Camada", None, None), ("total_rows", "Linhas", INT, None),
        ("error_rows", "Em erro", None, RUIM), ("warning_rows", "Com aviso", None, None), ("taxa_erro", "% erro", PCT, None),
        ("taxa_aviso", "% aviso", PCT, None), ("created_at", "Executada em", None, None), ("run_id", "Execução no Studio", None, None)],
        "Execuções completas no DQX Studio", pos(0, 20, 12, 7),
        descricao="Abra o Histórico de Execuções do Studio e filtre pela tabela para ver cada uma"),
]

# ====================================================================================================== página 3
p3 = [
    texto("cabecalho_nao_aptos", [
        "## Dados não aptos\n", "\n",
        "Eventos que a barreira de qualidade **barrou** antes da silver, com o motivo e o cadastro do cliente "
        "(`silver.pendencia_evento_quarentena`), e as linhas que o **DQX Studio reprovou**, com a regra e a mensagem. "
        "Use os filtros (dia, motivo, camada) na página de filtros."], pos(0, 0, 12, 2)),
    contador("kpi_qt_eventos", "ds_quarentena", {"name": "count(*)", "expression": "COUNT(`*`)"}, "Eventos na quarentena",
             pos(0, 2, 4, 3), INT, DIA, rotulo="Eventos"),
    contador("kpi_qt_valor", "ds_quarentena", agg("sum", "valor_total_pendente"), "Valor pendente retido", pos(4, 2, 4, 3), BRL, DIA,
             rotulo="Valor retido"),
    contador("kpi_qt_apolices", "ds_quarentena",
             {"name": "countdistinct(numero_apolice)", "expression": "COUNT(DISTINCT `numero_apolice`)"},
             "Apólices afetadas", pos(8, 2, 4, 3), INT, rotulo="Apólices"),
    tabela("quarentena_linhas", "ds_quarentena", [
        ("dia", "Dia", None, None), ("motivo_rejeicao", "Motivo", None, None), ("pendencia_id", "Pendência", None, None),
        ("tipo_evento", "Evento", None, None), ("numero_apolice", "Apólice", None, None), ("numero_parcela", "Parcela", None, None),
        ("status_cobranca", "Status", None, None), ("valor_parcela", "Parcela (R$)", None, None),
        ("valor_total_pendente", "Total (R$)", None, None), ("data_vencimento", "Vencimento", None, None),
        ("dias_atraso", "Dias de atraso", None, None), ("data_baixa", "Baixa", None, None), ("valor_pago", "Pago (R$)", None, None),
        ("cliente_nome", "Cliente", None, None), ("cliente_cpf", "CPF", None, None), ("cliente_idade", "Idade", None, None),
        ("cliente_uf", "UF", None, None), ("forma_pagamento", "Forma de pagamento", None, None)],
        "Eventos barrados (quarentena do pipeline)", pos(0, 5, 12, 9)),
    tabela("studio_reprovadas", "ds_studio_reprovadas", [
        ("semana", "Semana", None, None), ("camada", "Camada", None, None), ("regra", "Regra violada", None, None),
        ("mensagem", "Mensagem", None, None), ("referencia", "Dia / foto", None, None), ("pendencia_id", "Pendência", None, None),
        ("numero_apolice", "Apólice", None, None), ("cliente_nome", "Cliente", None, None), ("valor_total_pendente", "Total (R$)", None, None)],
        "Linhas reprovadas pelo DQX Studio (regra de erro)", pos(0, 14, 12, 8)),
]

# ====================================================================================================== filtros globais
filtros = [
    filtro("filtro_dia", "filter-date-range-picker", "dia", ["ds_diario", "ds_barrados", "ds_quarentena"], "Dia", pos(0, 0, 4, 2)),
    filtro("filtro_motivo", "filter-multi-select", "motivo_rejeicao", ["ds_barrados", "ds_quarentena"], "Motivo da rejeição", pos(4, 0, 4, 2)),
    filtro("filtro_camada", "filter-multi-select", "camada", ["ds_studio_exec", "ds_studio_regras", "ds_studio_reprovadas"],
           "Camada (Studio)", pos(8, 0, 4, 2)),
]


def pagina(nome, titulo, layout, tipo="PAGE_TYPE_CANVAS"):
    return {"name": nome, "displayName": titulo, "pageType": tipo, "layoutVersion": "GRID_V1", "layout": layout}


PAINEL = {
    "datasets": DATASETS,
    "pages": [pagina("visao_geral", "Visão geral", p1), pagina("studio", "DQX Studio · evolução", p2),
              pagina("nao_aptos", "Dados não aptos", p3), pagina("filtros", "Filtros", filtros, "PAGE_TYPE_GLOBAL_FILTERS")],
    "uiSettings": {"theme": {
        "canvasBackgroundColor": {"light": "#F7F8FA", "dark": "#1F272D"},
        "widgetBackgroundColor": {"light": "#FFFFFF", "dark": "#11171C"},
        "widgetBorderColor": {"light": "#FFFFFF", "dark": "#11171C"},
        "fontColor": {"light": "#11171C", "dark": "#E8ECF0"},
        "selectionColor": {"light": "#2272B4", "dark": "#8ACAFF"},
        "visualizationColors": PALETA,
        "widgetHeaderAlignment": "LEFT"}},
}


# ====================================================================================================== conferência
def conferir(p):
    erros = []
    VERSOES = {"counter": 2, "table": 2, "bar": 3, "line": 3, "heatmap": 3, "filter-date-range-picker": 2, "filter-multi-select": 2}
    nomes_ds = {d["name"] for d in p["datasets"]}
    for d in p["datasets"]:
        for ln in d["queryLines"]:
            if not ln.endswith((" ", "\n")) and ln is not d["queryLines"][-1]:
                erros.append(f"{d['name']}: linha sem espaço final: {ln!r}")
            if "pos_venda." in ln or "main." in ln:
                erros.append(f"{d['name']}: consulta com catálogo/schema: {ln!r}")
    for pg in p["pages"]:
        linhas = {}
        for item in pg["layout"]:
            w, ps = item["widget"], item["position"]
            for y in range(ps["y"], ps["y"] + ps["height"]):
                linhas.setdefault(y, 0)
                linhas[y] += ps["width"]
            if "spec" not in w:
                continue
            spec = w["spec"]
            if VERSOES.get(spec["widgetType"]) != spec["version"]:
                erros.append(f"{w['name']}: versão {spec['version']} para {spec['widgetType']}")
            consultas = {q["name"]: q for q in w["queries"]}
            for q in w["queries"]:
                if q["query"]["datasetName"] not in nomes_ds:
                    erros.append(f"{w['name']}: dataset inexistente {q['query']['datasetName']}")
            if spec["widgetType"].startswith("filter"):
                for f in spec["encodings"]["fields"]:
                    nomes = {x["name"] for x in consultas[f["queryName"]]["query"]["fields"]}
                    if f["fieldName"] not in nomes:
                        erros.append(f"{w['name']}: filtro sem campo {f['fieldName']}")
                continue
            nomes = {x["name"] for x in w["queries"][0]["query"]["fields"]}
            refs = []
            enc = spec["encodings"]
            for k, v in enc.items():
                if k == "columns":
                    refs += [c["fieldName"] for c in v]
                elif isinstance(v, dict):
                    if "fieldName" in v:
                        refs.append(v["fieldName"])
                    refs += [f["fieldName"] for f in v.get("fields", [])]
            for r in refs:
                if r not in nomes:
                    erros.append(f"{w['name']}: encoding {r} sem campo na consulta")
            if spec["widgetType"] == "counter" and "color" in enc.get("value", {}):
                erros.append(f"{w['name']}: contador com cor")
        for y, soma in linhas.items():
            if soma != 12 and pg["pageType"] == "PAGE_TYPE_CANVAS":
                erros.append(f"página {pg['name']}: linha y={y} soma {soma} colunas")
    return erros


if __name__ == "__main__":
    SAIDA.parent.mkdir(exist_ok=True)
    SAIDA.write_text(json.dumps(PAINEL, indent=2, ensure_ascii=False), encoding="utf-8")
    problemas = conferir(PAINEL)
    n_w = sum(1 for pg in PAINEL["pages"] for _ in pg["layout"])
    print(f"{SAIDA.relative_to(AQUI)} | {len(PAINEL['datasets'])} datasets | {len(PAINEL['pages'])} páginas | {n_w} widgets")
    print("conferência:", problemas or "ok")
