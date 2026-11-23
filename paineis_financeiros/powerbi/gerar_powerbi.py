#!/usr/bin/env python3
"""Opção Power BI dos painéis financeiros do Pós-venda (para comparar com os painéis AI/BI do Databricks).

Os mesmos quatro fatos (carteira em aberto, recuperação, safras e qualidade dos dados) e as mesmas duas audiências
(time de negócio e diretoria) dos painéis AI/BI, num projeto do Power BI Desktop (PBIP: modelo em TMDL e relatórios
em PBIR, tudo em texto). Os dados vêm de visões em `pos_venda.bi`, agregadas a partir das MESMAS metric views
(`pos_venda.ontologia.mv_*`) que alimentam os painéis do Databricks: a regra de negócio fica num lugar só.

    python3 gerar_powerbi.py visoes       # cria/atualiza o schema pos_venda.bi e as visões (precisa do warehouse)
    python3 gerar_powerbi.py              # gera projeto/ (modelo + 2 relatórios) e confere contra os esquemas oficiais
    python3 gerar_powerbi.py referencia   # valores que o Power BI deve mostrar = os do painel do Databricks (paridade)

Abrir: projeto/pos_venda_negocio.pbip ou projeto/pos_venda_diretoria.pbip no Power BI Desktop (Windows). Ver README.md.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys
import uuid

AQUI = pathlib.Path(__file__).resolve().parent
PROJETO = AQUI / "projeto"
ESQUEMAS = AQUI / ".esquemas"            # cache dos esquemas JSON oficiais (baixados na primeira conferência)
HOST = "dbc-15c48c79-7aa2.cloud.databricks.com"
HTTP_PATH = "/sql/1.0/warehouses/5f010b8396e591fb"
CATALOGO, SCHEMA = "pos_venda", "bi"
MODELO = "pos_venda.SemanticModel"
NS = uuid.UUID("6f1d3c3e-2a7b-4c55-9d1e-0b5e5a0c7f10")    # tags de linhagem determinísticas (diff limpo entre gerações)

FORMAS = ("DEBITO_CONTA", "BOLETO", "CARTAO_CREDITO", "PIX_AUTOMATICO")
FORMA_SQL = ("CASE WHEN `Forma de pagamento` IN ('" + "', '".join(FORMAS) + "') THEN `Forma de pagamento` "
             "ELSE 'NAO_CADASTRADA' END")
MV = f"{CATALOGO}.ontologia"

# ================================================================================================ visões pos_venda.bi
# (nome, comentário, [(coluna, comentário)], SELECT). Grão escolhido para importar rápido e responder a todos os visuais.
VISOES = [
    ("calendario", "Calendário contínuo dos anos com dados (dimensão de datas do Power BI).",
     [("data", "Dia do calendário."), ("mes", "Primeiro dia do mês."), ("ano", "Ano."), ("mes_do_ano", "Mês do ano (1 a 12).")],
     f"""SELECT d AS data, CAST(date_trunc('MONTH', d) AS DATE) AS mes, year(d) AS ano, month(d) AS mes_do_ano
FROM (SELECT explode(sequence(make_date(year(min(dia)), 1, 1), make_date(year(max(dia)), 12, 31))) AS d
      FROM {CATALOGO}.gold.dq_qualidade_diaria)"""),
    ("produto", "Produtos de seguro de vida (dimensão do Power BI).",
     [("produto", "Nome do produto."), ("categoria_produto", "Categoria do produto.")],
     f"SELECT produto_nome AS produto, categoria_produto FROM {CATALOGO}.gold.dim_produto"),
    ("canal_venda", "Canais de venda (dimensão do Power BI).",
     [("canal_venda", "Canal em que a apólice foi vendida.")],
     f"SELECT DISTINCT canal_venda FROM {CATALOGO}.gold.dim_ponto_venda"),
    ("forma_pagamento", "Formas de pagamento do catálogo e NAO_CADASTRADA (dado que vazou da barreira de qualidade).",
     [("forma_pagamento", "Forma de pagamento da parcela."), ("grupo_forma_pagamento", "Agrupamento da forma de pagamento.")],
     f"""SELECT forma_pagamento, grupo_forma_pagamento FROM {CATALOGO}.gold.dim_forma_pagamento
UNION ALL SELECT 'NAO_CADASTRADA', 'NAO_CADASTRADA'"""),
    ("carteira_diaria", "Carteira em aberto por dia, produto, canal, faixa, status, grupo do motivo e forma, calculada pela metric "
     "view mv_carteira_em_aberto. Saldos são SEMIADITIVOS: some dentro de um dia, nunca entre dias.",
     [("data_referencia", "Dia da foto."), ("produto", "Produto."), ("canal_venda", "Canal de venda."),
      ("faixa_atraso", "Faixa de atraso no dia."), ("status_cobranca", "Status de cobrança no dia."),
      ("grupo_motivo", "Grupo do motivo da pendência."), ("forma_pagamento", "Forma de pagamento (NAO_CADASTRADA = vazamento)."),
      ("saldo_em_aberto", "Saldo em aberto (parcela + multa + juros)."), ("pendencias_em_aberto", "Pendências em aberto."),
      ("valor_parcelas_em_aberto", "Valor original das parcelas em aberto."), ("multa_juros_em_aberto", "Multa e juros em aberto."),
      ("saldo_acima_60_dias", "Saldo das pendências com mais de 60 dias de atraso."),
      ("saldo_cobranca_externa", "Saldo em cobrança externa.")],
     f"""SELECT `Data de referência` AS data_referencia, `Produto` AS produto, `Canal de venda` AS canal_venda,
       `Faixa de atraso` AS faixa_atraso, `Status de cobrança` AS status_cobranca, `Grupo do motivo` AS grupo_motivo,
       `Forma de pagamento` AS forma_pagamento,
       MEASURE(`Saldo em aberto`) AS saldo_em_aberto, MEASURE(`Pendências em aberto`) AS pendencias_em_aberto,
       MEASURE(`Valor das parcelas em aberto`) AS valor_parcelas_em_aberto, MEASURE(`Multa e juros em aberto`) AS multa_juros_em_aberto,
       MEASURE(`Saldo acima de 60 dias`) AS saldo_acima_60_dias, MEASURE(`Saldo em cobrança externa`) AS saldo_cobranca_externa
FROM {MV}.mv_carteira_em_aberto GROUP BY ALL"""),
    ("recuperacao_diaria", "Recuperação (baixas) por dia da baixa, produto, canal, forma e faixa de atraso na baixa, calculada pela "
     "metric view mv_recuperacao. Aditiva no tempo.",
     [("data_baixa", "Dia da baixa."), ("produto", "Produto."), ("canal_venda", "Canal de venda."),
      ("forma_pagamento", "Forma de pagamento (fora do catálogo = NAO_CADASTRADA)."), ("faixa_atraso_na_baixa", "Faixa de atraso no pagamento."),
      ("valor_recuperado", "Valor pago nas baixas."), ("pendencias_pagas", "Pendências pagas."),
      ("multa_juros_recebidos", "Multa e juros pagos.")],
     f"""SELECT `Data da baixa` AS data_baixa, `Produto` AS produto, `Canal de venda` AS canal_venda,
       {FORMA_SQL} AS forma_pagamento, `Faixa de atraso na baixa` AS faixa_atraso_na_baixa,
       MEASURE(`Valor recuperado`) AS valor_recuperado, MEASURE(`Pendências pagas`) AS pendencias_pagas,
       MEASURE(`Multa e juros recebidos`) AS multa_juros_recebidos
FROM {MV}.mv_recuperacao GROUP BY ALL"""),
    ("safras", "Safras de entrada por produto, canal e forma, calculadas pela metric view mv_safra_recuperacao.",
     [("safra_entrada", "Mês em que a pendência entrou."), ("produto", "Produto."), ("canal_venda", "Canal de venda."),
      ("forma_pagamento", "Forma de pagamento (fora do catálogo = NAO_CADASTRADA)."),
      ("pendencias_entraram", "Pendências que entraram."), ("pendencias_pagas", "Pendências da safra já pagas."),
      ("valor_parcelas_entraram", "Valor original das parcelas que entraram."), ("valor_recuperado", "Valor pago pelas pendências da safra.")],
     f"""SELECT `Safra de entrada` AS safra_entrada, `Produto` AS produto, `Canal de venda` AS canal_venda,
       {FORMA_SQL} AS forma_pagamento,
       MEASURE(`Pendências que entraram`) AS pendencias_entraram, MEASURE(`Pendências pagas da safra`) AS pendencias_pagas,
       MEASURE(`Valor das parcelas que entraram`) AS valor_parcelas_entraram, MEASURE(`Valor recuperado da safra`) AS valor_recuperado
FROM {MV}.mv_safra_recuperacao GROUP BY ALL"""),
    ("qualidade_diaria", "Qualidade diária dos eventos do sistema de origem, calculada pela metric view mv_qualidade_dados.",
     [("dia", "Dia de extração."), ("eventos_recebidos", "Eventos recebidos."), ("eventos_aptos", "Eventos aptos (entraram na silver)."),
      ("eventos_barrados", "Eventos barrados (quarentena)."), ("eventos_duplicados", "Eventos duplicados."),
      ("email_ausente", "Aviso: e-mail ausente."), ("cpf_invalido", "Aviso: CPF inválido (contagem)."),
      ("cep_malformado", "Aviso: CEP malformado."), ("forma_pagamento_nao_cadastrada", "Eventos aptos com forma fora do catálogo.")],
     f"""SELECT `Dia` AS dia, MEASURE(`Eventos recebidos`) AS eventos_recebidos, MEASURE(`Eventos aptos`) AS eventos_aptos,
       MEASURE(`Eventos barrados`) AS eventos_barrados, MEASURE(`Eventos duplicados`) AS eventos_duplicados,
       MEASURE(`E-mail ausente`) AS email_ausente, MEASURE(`CPF inválido`) AS cpf_invalido,
       MEASURE(`CEP malformado`) AS cep_malformado, MEASURE(`Forma de pagamento não cadastrada`) AS forma_pagamento_nao_cadastrada
FROM {MV}.mv_qualidade_dados GROUP BY ALL"""),
]


def ddl_visoes() -> list[str]:
    q = lambda s: s.replace("'", "\\'")   # noqa: E731
    out = [f"CREATE SCHEMA IF NOT EXISTS {CATALOGO}.{SCHEMA} COMMENT '{q('Extratos agregados das metric views de pos_venda.ontologia para ferramentas de BI externas (Power BI). Mesmos números dos painéis AI/BI.')}'"]
    for nome, comentario, cols, sql in VISOES:
        colunas = ",\n  ".join(f"{c} COMMENT '{q(d)}'" for c, d in cols)
        out.append(f"CREATE OR REPLACE VIEW {CATALOGO}.{SCHEMA}.{nome} (\n  {colunas}\n) COMMENT '{q(comentario)}' AS\n{sql}")
    return out


def cliente_sql():
    sys.path.insert(0, str(AQUI.parents[1] / "regras"))
    import uc  # noqa: E402  (pos_venda/regras/uc.py: Statement Execution API, perfil dbx-workshop)
    return uc


def criar_visoes():
    """Cria o schema e as visões. Só recria a visão cuja definição mudou: CREATE OR REPLACE apaga as tags de governança
    (domínio, dono); nesse caso, rode depois `governanca/aplicar_semantica.py --so-tags`."""
    uc = cliente_sql()
    plano = lambda t: re.sub(r"\s+", " ", t or "").strip()      # noqa: E731
    atuais = {n: plano(d) for n, d in uc.executar(
        f"SELECT table_name, view_definition FROM {CATALOGO}.information_schema.views WHERE table_schema = '{SCHEMA}'", espera="30s")}
    ddl = ddl_visoes()
    uc.executar(ddl[0], espera="30s")
    recriadas = []
    for (nome, _, _, sql), s in zip(VISOES, ddl[1:]):
        if atuais.get(nome) == plano(sql):
            print("igual    ", nome)
            continue
        uc.executar(s, espera="30s")
        recriadas.append(nome)
        print("recriada ", nome)
    if recriadas:
        print("ATENÇÃO: visões recriadas perdem as tags; rode `python3 ../../governanca/aplicar_semantica.py --so-tags`")
    for nome, *_ in VISOES:
        n = uc.executar(f"SELECT count(*) FROM {CATALOGO}.{SCHEMA}.{nome}", espera="30s")[0][0]
        print(f"   {nome:20} {int(n):>10,} linhas".replace(",", "."))


# ================================================================================================ modelo semântico
BRL, PCT, INT = "R$ #,0.00", "0.0%", "#,0"
C = "'Carteira diária'"
SALDO = f"{C}[saldo_em_aberto]"


def foto(coluna, deslocamento=""):
    """Soma da coluna da carteira na foto do contexto (último dia com dado), com deslocamento opcional (ex.: '- 30')."""
    return (f"VAR _d = [Data da foto]\nRETURN\n    IF (\n        NOT ISBLANK ( _d ),\n"
            f"        CALCULATE ( SUM ( {C}[{coluna}] ), REMOVEFILTERS ( 'Calendário' ), 'Calendário'[Data] = _d{' ' + deslocamento if deslocamento else ''} )\n    )")


def rotulo(atual, antes, pp=False):
    if pp:
        corpo = f'FORMAT ( ( _a - _b ) * 100, "+0.0;-0.0" ) & " p.p. vs. 30 dias antes"'
    else:
        corpo = 'FORMAT ( DIVIDE ( _a - _b, _b ), "+0.0%;-0.0%" ) & " vs. 30 dias antes"'
    return f"VAR _a = [{atual}]\nVAR _b = [{antes}]\nRETURN\n    IF ( NOT ISBLANK ( _a ) && NOT ISBLANK ( _b ), {corpo} )"


# Cada tabela: nome, visão, colunas (nome no modelo, coluna SQL, tipo, opções) e medidas (nome, DAX, formato, pasta, descrição, oculta)
TABELAS = [
    {"nome": "Calendário", "visao": "calendario", "datas": True, "descricao": "Calendário contínuo (tabela de datas).",
     "colunas": [("Data", "data", "dateTime", {"formato": "dd/mm/yyyy", "chave": True}),
                 ("Mês", "mes", "dateTime", {"formato": "mmm yyyy"}),
                 ("Ano", "ano", "int64", {"formato": "0"}),
                 ("Mês (número)", "mes_do_ano", "int64", {"oculta": True})],
     "medidas": []},
    {"nome": "Produto", "visao": "produto", "descricao": "Produtos de seguro de vida.",
     "colunas": [("Produto", "produto", "string", {}), ("Categoria do produto", "categoria_produto", "string", {})], "medidas": []},
    {"nome": "Canal de venda", "visao": "canal_venda", "descricao": "Canais de venda.",
     "colunas": [("Canal de venda", "canal_venda", "string", {})], "medidas": []},
    {"nome": "Forma de pagamento", "visao": "forma_pagamento", "descricao": "Formas de pagamento (NAO_CADASTRADA = vazamento).",
     "colunas": [("Forma de pagamento", "forma_pagamento", "string", {}),
                 ("Grupo da forma de pagamento", "grupo_forma_pagamento", "string", {})], "medidas": []},
    {"nome": "Carteira diária", "visao": "carteira_diaria",
     "descricao": "Carteira em aberto por dia (foto diária). Saldo SEMIADITIVO: as medidas pegam o último dia do contexto.",
     "colunas": [("Data", "data_referencia", "dateTime", {"oculta": True}), ("Produto", "produto", "string", {"oculta": True}),
                 ("Canal de venda", "canal_venda", "string", {"oculta": True}),
                 ("Forma de pagamento", "forma_pagamento", "string", {"oculta": True}),
                 ("Faixa de atraso", "faixa_atraso", "string", {}), ("Status de cobrança", "status_cobranca", "string", {}),
                 ("Grupo do motivo", "grupo_motivo", "string", {}),
                 ("saldo_em_aberto", "saldo_em_aberto", "decimal", {"oculta": True}),
                 ("pendencias_em_aberto", "pendencias_em_aberto", "int64", {"oculta": True}),
                 ("valor_parcelas_em_aberto", "valor_parcelas_em_aberto", "decimal", {"oculta": True}),
                 ("multa_juros_em_aberto", "multa_juros_em_aberto", "decimal", {"oculta": True}),
                 ("saldo_acima_60_dias", "saldo_acima_60_dias", "decimal", {"oculta": True}),
                 ("saldo_cobranca_externa", "saldo_cobranca_externa", "decimal", {"oculta": True})],
     "medidas": [
         ("Data da foto", f"CALCULATE ( MAX ( {C}[Data] ), ALL ( {C} ), VALUES ( 'Calendário'[Data] ) )", "dd/mm/yyyy", "Carteira",
          "Último dia com foto no contexto (sem filtro de data: a foto mais recente).", False),
         ("Saldo em aberto", foto("saldo_em_aberto"), BRL, "Carteira",
          "Saldo em aberto na foto do contexto (último dia). Nunca soma dias diferentes.", False),
         ("Pendências em aberto", foto("pendencias_em_aberto"), INT, "Carteira", "Pendências em aberto na foto do contexto.", False),
         ("Valor das parcelas em aberto", foto("valor_parcelas_em_aberto"), BRL, "Carteira", "Valor original das parcelas, sem encargos.", False),
         ("Multa e juros em aberto", foto("multa_juros_em_aberto"), BRL, "Carteira", "Multa e juros acumulados na foto do contexto.", False),
         ("Saldo acima de 60 dias", foto("saldo_acima_60_dias"), BRL, "Carteira", "Saldo com mais de 60 dias de atraso.", False),
         ("Saldo em cobrança externa", foto("saldo_cobranca_externa"), BRL, "Carteira", "Saldo com status COBRANCA_EXTERNA.", False),
         ("% do saldo acima de 60 dias", "DIVIDE ( [Saldo acima de 60 dias], [Saldo em aberto] )", PCT, "Carteira",
          "Indicador de risco: saldo acima de 60 dias / saldo em aberto.", False),
         ("Ticket médio da pendência", "DIVIDE ( [Saldo em aberto], [Pendências em aberto] )", BRL, "Carteira",
          "Saldo em aberto / pendências em aberto.", False),
         ("Saldo 30 dias antes", foto("saldo_em_aberto", "- 30"), BRL, "Carteira · comparação", "Saldo 30 dias antes da foto.", False),
         ("Pendências 30 dias antes", foto("pendencias_em_aberto", "- 30"), INT, "Carteira · comparação", "", False),
         ("Multa e juros 30 dias antes", foto("multa_juros_em_aberto", "- 30"), BRL, "Carteira · comparação", "", False),
         ("Saldo acima de 60 dias 30 dias antes", foto("saldo_acima_60_dias", "- 30"), BRL, "Carteira · comparação", "", True),
         ("% acima de 60 dias 30 dias antes", "DIVIDE ( [Saldo acima de 60 dias 30 dias antes], [Saldo 30 dias antes] )", PCT,
          "Carteira · comparação", "", False),
         ("Ticket médio 30 dias antes", "DIVIDE ( [Saldo 30 dias antes], [Pendências 30 dias antes] )", BRL, "Carteira · comparação", "", False),
         ("Fechamento do mês anterior",
          "VAR _d = [Data da foto]\nRETURN\n    IF (\n        NOT ISBLANK ( _d ),\n"
          f"        CALCULATE ( SUM ( {SALDO} ), REMOVEFILTERS ( 'Calendário' ), 'Calendário'[Data] = EOMONTH ( _d, -1 ) )\n    )",
          BRL, "Carteira · mês", "Saldo no último dia do mês anterior ao da foto.", False),
         ("Saldo no início do mês",
          "VAR _d = [Data da foto]\nVAR _ini =\n    CALCULATE (\n        MIN ( 'Carteira diária'[Data] ),\n        ALL ( 'Carteira diária' ),\n"
          "        DATESBETWEEN ( 'Calendário'[Data], EOMONTH ( _d, -1 ) + 1, _d )\n    )\nRETURN\n    IF (\n        NOT ISBLANK ( _d ),\n"
          f"        CALCULATE ( SUM ( {SALDO} ), REMOVEFILTERS ( 'Calendário' ), 'Calendário'[Data] = _ini )\n    )",
          BRL, "Carteira · mês", "Saldo no primeiro dia com foto do mês da foto (maio/2026 começa em 19/05).", False),
         ("Variação mensal do saldo", "DIVIDE ( [Saldo em aberto] - [Fechamento do mês anterior], [Fechamento do mês anterior] )", PCT,
          "Carteira · mês", "Saldo da foto sobre o fechamento do mês anterior (MoM).", False),
         ("Crescimento da carteira no mês", "IF ( NOT ISBLANK ( [Saldo em aberto] ), [Saldo em aberto] - [Saldo no início do mês] )", BRL,
          "Carteira · mês", "Saldo da foto menos o saldo do início do mês.", False),
         ("Rótulo saldo", rotulo("Saldo em aberto", "Saldo 30 dias antes"), None, "Rótulos", "Subtítulo do cartão.", True),
         ("Rótulo pendências", rotulo("Pendências em aberto", "Pendências 30 dias antes"), None, "Rótulos", "", True),
         ("Rótulo ticket", rotulo("Ticket médio da pendência", "Ticket médio 30 dias antes"), None, "Rótulos", "", True),
         ("Rótulo multa e juros", rotulo("Multa e juros em aberto", "Multa e juros 30 dias antes"), None, "Rótulos", "", True),
         ("Rótulo acima de 60 dias", rotulo("% do saldo acima de 60 dias", "% acima de 60 dias 30 dias antes", pp=True), None, "Rótulos", "", True),
     ]},
    {"nome": "Recuperação", "visao": "recuperacao_diaria", "descricao": "Baixas (pagamentos) por dia da baixa. Aditiva no tempo.",
     "colunas": [("Data da baixa", "data_baixa", "dateTime", {"oculta": True}), ("Produto", "produto", "string", {"oculta": True}),
                 ("Canal de venda", "canal_venda", "string", {"oculta": True}),
                 ("Forma de pagamento", "forma_pagamento", "string", {"oculta": True}),
                 ("Faixa de atraso na baixa", "faixa_atraso_na_baixa", "string", {}),
                 ("valor_recuperado", "valor_recuperado", "decimal", {"oculta": True}),
                 ("pendencias_pagas", "pendencias_pagas", "int64", {"oculta": True}),
                 ("multa_juros_recebidos", "multa_juros_recebidos", "decimal", {"oculta": True})],
     "medidas": [
         ("Valor recuperado", "SUM ( 'Recuperação'[valor_recuperado] )", BRL, "Recuperação", "Valor pago nas baixas.", False),
         ("Pendências pagas", "SUM ( 'Recuperação'[pendencias_pagas] )", INT, "Recuperação", "Quantidade de baixas.", False),
         ("Multa e juros recebidos", "SUM ( 'Recuperação'[multa_juros_recebidos] )", BRL, "Recuperação", "", False),
         ("Ticket médio recuperado", "DIVIDE ( [Valor recuperado], [Pendências pagas] )", BRL, "Recuperação", "", False),
         ("Recuperado no mês anterior", "CALCULATE ( [Valor recuperado], DATEADD ( 'Calendário'[Data], -1, MONTH ) )", BRL,
          "Recuperação · mês", "Use agrupado por Calendário[Mês].", False),
         ("Variação mensal do recuperado", "DIVIDE ( [Valor recuperado] - [Recuperado no mês anterior], [Recuperado no mês anterior] )",
          PCT, "Recuperação · mês", "Use agrupado por Calendário[Mês] (MoM).", False),
         ("Recuperado acumulado no ano", "TOTALYTD ( [Valor recuperado], 'Calendário'[Data] )", BRL, "Recuperação · mês",
          "De 1º de janeiro até o fim do período (YTD).", False),
         ("Variação mensal do recuperado (último mês completo)",
          "VAR _ultima = CALCULATE ( MAX ( 'Recuperação'[Data da baixa] ), ALL ( 'Recuperação' ) )\n"
          "VAR _fim = IF ( _ultima = EOMONTH ( _ultima, 0 ), _ultima, EOMONTH ( _ultima, -1 ) )\n"
          "RETURN\n    CALCULATE (\n        [Variação mensal do recuperado],\n        REMOVEFILTERS ( 'Calendário' ),\n"
          "        DATESBETWEEN ( 'Calendário'[Data], EOMONTH ( _fim, -1 ) + 1, _fim )\n    )",
          PCT, "Recuperação · mês", "Último mês completo vs. o mês anterior.", False),
         ("Mês completo",
          "VAR _ultima = CALCULATE ( MAX ( 'Recuperação'[Data da baixa] ), ALL ( 'Recuperação' ) )\nRETURN\n"
          "    IF ( NOT ISBLANK ( [Valor recuperado] ), IF ( MAX ( 'Calendário'[Data] ) <= _ultima, \"Sim\", \"Não\" ) )",
          None, "Recuperação · mês", "Sim quando o mês já terminou na data da última baixa.", False),
     ]},
    {"nome": "Safras", "visao": "safras", "descricao": "Safras de entrada (mês em que a pendência entrou) e quanto já foi pago.",
     "colunas": [("Safra de entrada", "safra_entrada", "dateTime", {"formato": "mmm yyyy"}),
                 ("Produto", "produto", "string", {"oculta": True}), ("Canal de venda", "canal_venda", "string", {"oculta": True}),
                 ("Forma de pagamento", "forma_pagamento", "string", {"oculta": True}),
                 ("pendencias_entraram", "pendencias_entraram", "int64", {"oculta": True}),
                 ("pendencias_pagas", "pendencias_pagas", "int64", {"oculta": True}),
                 ("valor_parcelas_entraram", "valor_parcelas_entraram", "decimal", {"oculta": True}),
                 ("valor_recuperado", "valor_recuperado", "decimal", {"oculta": True})],
     "medidas": [
         ("Pendências que entraram", "SUM ( 'Safras'[pendencias_entraram] )", INT, "Safras", "", False),
         ("Pendências pagas da safra", "SUM ( 'Safras'[pendencias_pagas] )", INT, "Safras", "", False),
         ("Taxa de recuperação", "DIVIDE ( [Pendências pagas da safra], [Pendências que entraram] )", PCT, "Safras",
          "Pendências pagas / pendências que entraram.", False),
         ("Valor das parcelas que entraram", "SUM ( 'Safras'[valor_parcelas_entraram] )", BRL, "Safras", "", False),
         ("Valor recuperado da safra", "SUM ( 'Safras'[valor_recuperado] )", BRL, "Safras", "", False),
     ]},
    {"nome": "Qualidade", "visao": "qualidade_diaria", "descricao": "Qualidade diária dos eventos do sistema de origem.",
     "colunas": [("Dia", "dia", "dateTime", {"oculta": True})] +
                [(c, c, "int64", {"oculta": True}) for c in ("eventos_recebidos", "eventos_aptos", "eventos_barrados", "eventos_duplicados",
                                                               "email_ausente", "cpf_invalido", "cep_malformado",
                                                               "forma_pagamento_nao_cadastrada")],
     "medidas": [(n, f"SUM ( 'Qualidade'[{c}] )", INT, "Qualidade", d, False) for n, c, d in (
         ("Eventos recebidos", "eventos_recebidos", "Eventos recebidos do sistema de origem."),
         ("Eventos aptos", "eventos_aptos", "Passaram na barreira e entraram nos números."),
         ("Eventos barrados", "eventos_barrados", "Foram para a quarentena e não entram nos números."),
         ("Eventos duplicados", "eventos_duplicados", ""), ("E-mail ausente", "email_ausente", "Aviso."),
         ("CPF inválido", "cpf_invalido", "Aviso (contagem; não contém CPF)."), ("CEP malformado", "cep_malformado", "Aviso."),
         ("Forma de pagamento não cadastrada", "forma_pagamento_nao_cadastrada", "Eventos aptos com forma fora do catálogo."))] +
                [("Taxa de barrados", "DIVIDE ( [Eventos barrados], [Eventos recebidos] )", PCT, "Qualidade", "Barrados / recebidos.", False)]},
]
RELACOES = [(t, c, d, k) for t in ("Carteira diária", "Recuperação", "Safras")
            for c, d, k in (("Produto", "Produto", "Produto"), ("Canal de venda", "Canal de venda", "Canal de venda"),
                            ("Forma de pagamento", "Forma de pagamento", "Forma de pagamento"))] + [
    ("Carteira diária", "Data", "Calendário", "Data"), ("Recuperação", "Data da baixa", "Calendário", "Data"),
    ("Qualidade", "Dia", "Calendário", "Data")]


def guid(*partes):
    return str(uuid.uuid5(NS, "/".join(partes)))


def nome_tmdl(n):
    return n if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", n) else "'" + n.replace("'", "''") + "'"


def bloco(texto, recuo):
    return "\n".join(("\t" * recuo + linha) if linha else "" for linha in texto.splitlines())


def tmdl_tabela(t) -> str:
    L = [f"/// {t['descricao']}", f"table {nome_tmdl(t['nome'])}", f"\tlineageTag: {guid('t', t['nome'])}"]
    if t.get("datas"):
        L.append("\tdataCategory: Time")
    L.append("")
    for nome, dax, fmt, pasta, desc, oculta in t["medidas"]:
        if desc:
            L.append(f"\t/// {desc}")
        if "\n" in dax:
            L += [f"\tmeasure {nome_tmdl(nome)} =", bloco(dax, 3)]
        else:
            L.append(f"\tmeasure {nome_tmdl(nome)} = {dax}")
        if fmt:
            L.append(f"\t\tformatString: {fmt}")
        if oculta:
            L.append("\t\tisHidden")
        L += [f"\t\tdisplayFolder: {pasta}", f"\t\tlineageTag: {guid('m', t['nome'], nome)}", ""]
    for nome, origem, tipo, op in t["colunas"]:
        L += [f"\tcolumn {nome_tmdl(nome)}", f"\t\tdataType: {tipo}"]
        if op.get("formato"):
            L.append(f"\t\tformatString: {op['formato']}")
        elif tipo == "decimal":
            L.append(f"\t\tformatString: {BRL}")
        elif tipo == "int64":
            L.append(f"\t\tformatString: {INT}")
        if op.get("chave"):
            L.append("\t\tisKey")
        if op.get("oculta"):
            L.append("\t\tisHidden")
        L += [f"\t\tlineageTag: {guid('c', t['nome'], nome)}", "\t\tsummarizeBy: none", f"\t\tsourceColumn: {origem}", "",
              "\t\tannotation SummarizationSetBy = Automatic", ""]
    L += [f"\tpartition {nome_tmdl(t['nome'])} = m", "\t\tmode: import", "\t\tsource =", bloco(m_tabela(t), 4), "",
          "\tannotation PBI_ResultType = Table", ""]
    return "\n".join(L)


def m_tabela(t) -> str:
    """Consulta Power Query (M) da tabela: a visão de pos_venda.bi pelo conector Databricks."""
    return (f'let\n    Fonte = DatabricksMultiCloud.Catalogs(Host, HttpPath, [Catalog = null, Database = null, EnableAutomaticProxyDiscovery = null]),\n'
            f'    Catalogo = Fonte{{[Name = "{CATALOGO}", Kind = "Database"]}}[Data],\n'
            f'    Esquema = Catalogo{{[Name = "{SCHEMA}", Kind = "Schema"]}}[Data],\n'
            f'    Dados = Esquema{{[Name = "{t["visao"]}"]}}[Data]\nin\n    Dados')


def modelo_bim() -> dict:
    """O mesmo modelo em TMSL (model.bim), só para ferramentas que não leem TMDL, como o powerbi-analyzer (pba).

    Não vai para projeto/: o Power BI Desktop usa a pasta definition/ (TMDL)."""
    tabelas = []
    for t in TABELAS:
        cols = []
        for nome, origem, tipo, op in t["colunas"]:
            c = {"name": nome, "dataType": tipo, "sourceColumn": origem, "summarizeBy": "none"}
            fmt = op.get("formato") or {"decimal": BRL, "int64": INT}.get(tipo)
            if fmt:
                c["formatString"] = fmt
            if op.get("chave"):
                c["isKey"] = True
            if op.get("oculta"):
                c["isHidden"] = True
            cols.append(c)
        medidas = []
        for nome, dax, fmt, pasta, desc, oculta in t["medidas"]:
            m = {"name": nome, "expression": dax, "displayFolder": pasta}
            if fmt:
                m["formatString"] = fmt
            if desc:
                m["description"] = desc
            if oculta:
                m["isHidden"] = True
            medidas.append(m)
        tab = {"name": t["nome"], "description": t["descricao"], "columns": cols, "measures": medidas,
               "partitions": [{"name": t["nome"], "mode": "import", "source": {"type": "m", "expression": m_tabela(t)}}]}
        if t.get("datas"):
            tab["dataCategory"] = "Time"
        tabelas.append(tab)
    relacoes = [{"name": guid("r", t, c), "fromTable": t, "fromColumn": c, "toTable": d, "toColumn": k} for t, c, d, k in RELACOES]
    expressoes = [{"name": n, "kind": "m",
                   "expression": f'"{v}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]'}
                  for n, v in (("Host", HOST), ("HttpPath", HTTP_PATH))]
    return {"name": "pos_venda", "compatibilityLevel": 1600,
            "model": {"culture": "pt-BR", "discourageImplicitMeasures": True, "tables": tabelas,
                      "relationships": relacoes, "expressions": expressoes}}


def escrever_modelo():
    base = PROJETO / MODELO
    defn = base / "definition"
    (defn / "tables").mkdir(parents=True, exist_ok=True)
    js(base / "definition.pbism", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
                                   "version": "4.0", "settings": {}})
    js(base / ".platform", plataforma("SemanticModel", "pos_venda"))
    (defn / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1600\n\n", encoding="utf-8")
    ordem = json.dumps(["Host", "HttpPath"] + [t["nome"] for t in TABELAS], ensure_ascii=False)
    (defn / "model.tmdl").write_text(
        "model Model\n\tculture: pt-BR\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tdiscourageImplicitMeasures\n"
        "\tsourceQueryCulture: pt-BR\n\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n"
        f"annotation PBI_QueryOrder = {ordem}\n\n" + "".join(f"ref table {nome_tmdl(t['nome'])}\n" for t in TABELAS) + "\n",
        encoding="utf-8")
    exp = ""
    for nome, valor in (("Host", HOST), ("HttpPath", HTTP_PATH)):
        exp += (f'expression {nome} = "{valor}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]\n'
                f"\tlineageTag: {guid('p', nome)}\n\n\tannotation PBI_ResultType = Text\n\n")
    (defn / "expressions.tmdl").write_text(exp, encoding="utf-8")
    rel = ""
    for t, c, d, k in RELACOES:
        rel += f"relationship {guid('r', t, c)}\n\tfromColumn: {nome_tmdl(t)}.{nome_tmdl(c)}\n\ttoColumn: {nome_tmdl(d)}.{nome_tmdl(k)}\n\n"
    (defn / "relationships.tmdl").write_text(rel, encoding="utf-8")
    for t in TABELAS:
        (defn / "tables" / f"{t['nome']}.tmdl").write_text(tmdl_tabela(t), encoding="utf-8")


# ================================================================================================ relatórios (PBIR)
U = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
VERSOES = {"report": "3.0.0", "page": "2.0.0", "visualContainer": "2.2.0", "pagesMetadata": "1.0.0", "versionMetadata": "1.0.0"}
LARGURA, MARGEM, LINHA = 1280, 12, 40
COL = (LARGURA - 2 * MARGEM) / 12
PALETA = ["#003F5C", "#2F6B9A", "#7A5195", "#BC5090", "#EF5675", "#FFA600", "#58B09C"]
CAMPOS = {t["nome"]: ({c[0] for c in t["colunas"]}, {m[0] for m in t["medidas"]}) for t in TABELAS}


def campo(ref):
    """'Tabela[Campo]' -> expressão de campo do PBIR (coluna ou medida, conforme o modelo)."""
    t, n = re.fullmatch(r"(.+)\[(.+)\]", ref).groups()
    colunas, medidas = CAMPOS[t]
    tipo = "Measure" if n in medidas else "Column" if n in colunas else None
    if not tipo:
        raise KeyError(f"{ref} não existe no modelo")
    return {tipo: {"Expression": {"SourceRef": {"Entity": t}}, "Property": n}}, t, n


def proj(ref, rotulo=None):
    f, t, n = campo(ref)
    p = {"field": f, "queryRef": f"{t}.{n}", "nativeQueryRef": n}
    if rotulo:
        p["displayName"] = rotulo
    return p


def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def texto_lit(s):
    return lit("'" + s.replace("'", "''") + "'")


def caixa(titulo, sub=None, sub_medida=None):
    o = {"title": [{"properties": {"show": lit("true"), "text": texto_lit(titulo)}}]}
    if sub or sub_medida:
        valor = {"expr": campo(sub_medida)[0]} if sub_medida else texto_lit(sub)
        o["subTitle"] = [{"properties": {"show": lit("true"), "text": valor}}]
    return o


def pos_px(x, y, w, h):
    return {"x": round(MARGEM + x * COL, 1), "y": MARGEM + y * LINHA, "width": round(w * COL - 8, 1), "height": h * LINHA - 8}


def texto(titulo, corpo, x, y, w, h):
    return {"tipo": "textbox", "pos": (x, y, w, h), "visual": {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": [
        {"textRuns": [{"value": titulo, "textStyle": {"fontWeight": "bold", "fontSize": "16pt"}}]},
        {"textRuns": [{"value": corpo, "textStyle": {"fontSize": "10pt"}}]}]}}]}}}


def cartao(medida, titulo, x, y, sub=None, sub_medida=None, w=3, h=3):
    v = {"visualType": "card", "query": {"queryState": {"Values": {"projections": [proj(medida)]}}},
         "objects": {"categoryLabels": [{"properties": {"show": lit("false")}}]},
         "visualContainerObjects": caixa(titulo, sub, sub_medida), "drillFilterOtherVisuals": True}
    return {"tipo": "card", "pos": (x, y, w, h), "visual": v, "titulo": titulo}


def grafico(tipo, categoria, medidas, titulo, x, y, w, h, serie=None, sub=None, ordenar_categoria=False):
    q = {"Category": {"projections": [proj(categoria)]}, "Y": {"projections": [proj(m, r) for m, r in medidas]}}
    if serie:
        q["Series"] = {"projections": [proj(serie)]}
    v = {"visualType": tipo, "query": {"queryState": q}, "visualContainerObjects": caixa(titulo, sub), "drillFilterOtherVisuals": True}
    if ordenar_categoria:
        v["query"]["sortDefinition"] = {"sort": [{"field": campo(categoria)[0], "direction": "Ascending"}], "isDefaultSort": True}
    return {"tipo": tipo, "pos": (x, y, w, h), "visual": v, "titulo": titulo}


def linha(*a, **k):
    return grafico("lineChart", *a, ordenar_categoria=True, **k)


def colunas(*a, empilhado=False, por_categoria=False, **k):
    return grafico("columnChart" if empilhado else "clusteredColumnChart", *a, ordenar_categoria=por_categoria, **k)


def barras(*a, **k):
    return grafico("clusteredBarChart", *a, **k)


def tabela(campos, titulo, x, y, w, h, sub=None):
    v = {"visualType": "tableEx", "query": {"queryState": {"Values": {"projections": [proj(c, r) for c, r in campos]}}},
         "visualContainerObjects": caixa(titulo, sub), "drillFilterOtherVisuals": True}
    return {"tipo": "tableEx", "pos": (x, y, w, h), "visual": v, "titulo": titulo}


# ------------------------------------------------------------------------------------------------ peças das páginas
CD, RC, SF, QL = "Carteira diária", "Recuperação", "Safras", "Qualidade"
DATA, MES, SAFRA = "Calendário[Data]", "Calendário[Mês]", "Safras[Safra de entrada]"
NOTA_SALDO = ("O saldo é uma posição diária: aparece por dia ou na foto mais recente e nunca se soma entre dias. "
              "O mês corrente ainda não fechou: nele vale a foto mais recente. Dados sintéticos.")


def c_saldo(x, y): return cartao(f"{CD}[Saldo em aberto]", "Saldo em aberto", x, y, sub_medida=f"{CD}[Rótulo saldo]")
def c_pct60(x, y): return cartao(f"{CD}[% do saldo acima de 60 dias]", "% do saldo acima de 60 dias", x, y, sub_medida=f"{CD}[Rótulo acima de 60 dias]")
def c_pend(x, y): return cartao(f"{CD}[Pendências em aberto]", "Pendências em aberto", x, y, sub_medida=f"{CD}[Rótulo pendências]")
def c_mom_saldo(x, y): return cartao(f"{CD}[Variação mensal do saldo]", "Variação mensal do saldo", x, y,
                                     sub="Mês corrente (foto mais recente) vs. fechamento do mês anterior")
def c_cresc(x, y): return cartao(f"{CD}[Crescimento da carteira no mês]", "Crescimento da carteira no mês", x, y,
                                 sub="Foto mais recente menos o saldo do dia 1º do mês")
def c_ytd(x, y): return cartao(f"{RC}[Recuperado acumulado no ano]", "Recuperado no ano", x, y, sub="Acumulado do ano até a foto mais recente")
def c_mom_rec(x, y): return cartao(f"{RC}[Variação mensal do recuperado (último mês completo)]", "Variação mensal do recuperado", x, y,
                                   sub="Último mês completo vs. o mês anterior")
def c_taxa(x, y): return cartao(f"{SF}[Taxa de recuperação]", "Taxa de recuperação", x, y, sub="Pendências pagas / que entraram (todas as safras)")
def g_saldo_dia(x, y, w, h): return linha(DATA, [(f"{CD}[Saldo em aberto]", "Saldo em aberto"), (f"{CD}[Saldo acima de 60 dias]", "Acima de 60 dias")],
                                          "Evolução diária do saldo em aberto", x, y, w, h, sub="Posição de cada dia (sem somar dias)")
def g_aging(x, y, w, h): return colunas(f"{CD}[Faixa de atraso]", [(f"{CD}[Saldo em aberto]", "Saldo em aberto")], "Aging da carteira hoje",
                                        x, y, w, h, sub="Saldo por faixa de atraso na foto mais recente", por_categoria=True)
def g_recup_mes(x, y, w, h): return colunas(MES, [(f"{RC}[Valor recuperado]", "Valor recuperado")], "Valor recuperado por mês", x, y, w, h,
                                            sub="Baixas (parcela + multa + juros pagos); o mês corrente está incompleto", por_categoria=True)
def g_taxa_safra(x, y, w, h): return linha(SAFRA, [(f"{SF}[Taxa de recuperação]", "Taxa de recuperação")], "Taxa de recuperação por safra",
                                           x, y, w, h, sub="Safras recentes tiveram menos tempo para pagar")
def g_barrados(x, y, w, h): return linha(DATA, [(f"{QL}[Taxa de barrados]", "Taxa de barrados")], "Confiabilidade dos dados: taxa de eventos barrados",
                                         x, y, w, h, sub="Eventos que não entraram nos números por violar regras de qualidade")
def g_avisos(x, y, w, h): return linha(DATA, [(f"{QL}[CPF inválido]", None), (f"{QL}[E-mail ausente]", None), (f"{QL}[CEP malformado]", None),
                                              (f"{QL}[Forma de pagamento não cadastrada]", None)], "Avisos de qualidade por dia", x, y, w, h,
                                       sub="Eventos que entraram nos números, mas com dado incompleto ou fora do padrão")
def g_recup_forma(x, y, w, h): return colunas(MES, [(f"{RC}[Valor recuperado]", "Valor recuperado")], "Valor recuperado por mês e forma de pagamento",
                                              x, y, w, h, serie="Forma de pagamento[Forma de pagamento]", empilhado=True, por_categoria=True)
def c_qualidade(y):
    return [cartao(f"{QL}[Eventos recebidos]", "Eventos recebidos", 0, y, sub="Todo o período"),
            cartao(f"{QL}[Eventos barrados]", "Eventos barrados", 3, y, sub="Foram para a quarentena"),
            cartao(f"{QL}[Taxa de barrados]", "Taxa de barrados", 6, y, sub="Barrados / recebidos"),
            cartao(f"{QL}[Forma de pagamento não cadastrada]", "Forma de pagamento não cadastrada", 9, y,
                   sub="Eventos que vazaram a barreira (incidente de dez/2026)")]


def cab(titulo, corpo, h=2):
    return texto(titulo, corpo, 0, 0, 12, h)


# ------------------------------------------------------------------------------------------------ páginas (iguais às do Databricks)
NEGOCIO = [
    ("Carteira em aberto", [
        cab("Carteira em aberto (foto mais recente)",
            "Composição do saldo da foto mais recente por faixa de atraso, status, motivo, forma de pagamento, produto e canal. No fim da "
            "página, o fechamento de cada mês com a variação sobre o mês anterior. Filtros de produto, canal e forma no painel Filtros."),
        c_saldo(0, 2), c_pend(3, 2),
        cartao(f"{CD}[Ticket médio da pendência]", "Ticket médio da pendência", 6, 2, sub_medida=f"{CD}[Rótulo ticket]"),
        cartao(f"{CD}[Multa e juros em aberto]", "Multa e juros em aberto", 9, 2, sub_medida=f"{CD}[Rótulo multa e juros]"),
        colunas(f"{CD}[Faixa de atraso]", [(f"{CD}[Saldo em aberto]", "Saldo em aberto")], "Saldo por faixa de atraso", 0, 5, 6, 6, por_categoria=True),
        colunas(f"{CD}[Status de cobrança]", [(f"{CD}[Saldo em aberto]", "Saldo em aberto")], "Saldo por status de cobrança", 6, 5, 6, 6),
        colunas(f"{CD}[Grupo do motivo]", [(f"{CD}[Saldo em aberto]", "Saldo em aberto")], "Saldo por grupo de motivo", 0, 11, 6, 6,
                sub="Cadastral pede atualização de dados; financeiro pede negociação"),
        colunas("Forma de pagamento[Forma de pagamento]", [(f"{CD}[Saldo em aberto]", "Saldo em aberto")], "Saldo por forma de pagamento",
                6, 11, 6, 6, sub="NAO_CADASTRADA = dado que vazou da barreira de qualidade"),
        tabela([("Produto[Produto]", "Produto"), ("Canal de venda[Canal de venda]", "Canal"), (f"{CD}[Saldo em aberto]", "Saldo em aberto"),
                (f"{CD}[Pendências em aberto]", "Pendências"), (f"{CD}[% do saldo acima de 60 dias]", "% acima de 60 dias"),
                (f"{CD}[Ticket médio da pendência]", "Ticket médio")], "Carteira por produto e canal", 0, 17, 12, 7),
        tabela([(MES, "Mês"), ("Produto[Produto]", "Produto"), ("Canal de venda[Canal de venda]", "Canal"),
                (f"{CD}[Saldo no início do mês]", "Saldo no início do mês"), (f"{CD}[Saldo em aberto]", "Saldo de fechamento"),
                (f"{CD}[Fechamento do mês anterior]", "Fechamento do mês anterior"), (f"{CD}[Variação mensal do saldo]", "Variação mensal"),
                (f"{CD}[Pendências em aberto]", "Pendências no fechamento")], "Fechamento mensal por produto e canal", 0, 24, 12, 7,
               sub="Último dia de cada mês (mês corrente = foto mais recente); variação sobre o fechamento do mês anterior"),
    ]),
    ("Recuperação", [
        cab("Recuperação", "Baixas por mês, forma de pagamento, faixa de atraso no pagamento, produto e canal. "
                           "No fim da página, a recuperação mês a mês e o acumulado no ano."),
        cartao(f"{RC}[Valor recuperado]", "Valor recuperado", 0, 2, sub="Todas as baixas"),
        cartao(f"{RC}[Pendências pagas]", "Pendências pagas", 3, 2, sub="Todas as baixas"),
        cartao(f"{RC}[Ticket médio recuperado]", "Ticket médio recuperado", 6, 2, sub="Valor recuperado / pendências pagas"),
        cartao(f"{RC}[Multa e juros recebidos]", "Multa e juros recebidos", 9, 2, sub="Todas as baixas"),
        g_recup_forma(0, 5, 8, 6),
        colunas(f"{RC}[Faixa de atraso na baixa]", [(f"{RC}[Pendências pagas]", "Pendências pagas")],
                "Em que faixa de atraso as pendências são pagas", 8, 5, 4, 6, por_categoria=True),
        tabela([("Produto[Produto]", "Produto"), ("Canal de venda[Canal de venda]", "Canal"), (f"{RC}[Valor recuperado]", "Valor recuperado"),
                (f"{RC}[Pendências pagas]", "Pendências pagas"), (f"{RC}[Ticket médio recuperado]", "Ticket médio"),
                (f"{RC}[Multa e juros recebidos]", "Multa e juros recebidos")], "Recuperação por produto e canal", 0, 11, 12, 7),
        tabela([(MES, "Mês da baixa"), (f"{RC}[Mês completo]", "Mês completo"), (f"{RC}[Valor recuperado]", "Valor recuperado"),
                (f"{RC}[Recuperado no mês anterior]", "Mês anterior"), (f"{RC}[Variação mensal do recuperado]", "Variação mensal"),
                (f"{RC}[Recuperado acumulado no ano]", "Acumulado no ano")], "Recuperação mês a mês e acumulado no ano", 0, 18, 12, 6,
               sub="O mês corrente está incompleto: compare a variação mensal só entre meses completos"),
    ]),
    ("Safras", [
        cab("Safras", "Taxa de recuperação por safra de entrada (mês em que a pendência entrou). Compare safras de mesma idade."),
        c_taxa(0, 2), cartao(f"{SF}[Pendências que entraram]", "Pendências que entraram", 3, 2, sub="Todas as safras"),
        cartao(f"{SF}[Pendências pagas da safra]", "Pendências pagas", 6, 2, sub="Todas as safras"),
        cartao(f"{SF}[Valor recuperado da safra]", "Valor recuperado das safras", 9, 2, sub="Pago pelas pendências das safras"),
        linha(SAFRA, [(f"{SF}[Taxa de recuperação]", "Taxa de recuperação")], "Taxa de recuperação por safra e canal", 0, 5, 6, 6,
              serie="Canal de venda[Canal de venda]"),
        colunas("Forma de pagamento[Forma de pagamento]", [(f"{SF}[Taxa de recuperação]", "Taxa de recuperação")],
                "Taxa de recuperação por forma de pagamento", 6, 5, 6, 6),
        tabela([(SAFRA, "Safra"), ("Produto[Produto]", "Produto"), (f"{SF}[Pendências que entraram]", "Entraram"),
                (f"{SF}[Pendências pagas da safra]", "Pagas"), (f"{SF}[Taxa de recuperação]", "Taxa"),
                (f"{SF}[Valor recuperado da safra]", "Valor recuperado")], "Safras por produto", 0, 11, 12, 7),
    ]),
    ("Qualidade dos dados", [
        cab("Qualidade dos dados", "Eventos recebidos do sistema de origem, quantos foram barrados (não entram nos números) e os avisos de dado "
                                   "incompleto. Os filtros de produto, canal e forma não se aplicam aqui."),
        *c_qualidade(2),
        colunas(DATA, [(f"{QL}[Eventos aptos]", "Aptos"), (f"{QL}[Eventos barrados]", "Barrados")], "Eventos recebidos por dia: aptos e barrados",
                0, 5, 12, 6, empilhado=True, por_categoria=True),
        g_avisos(0, 11, 12, 6),
    ]),
]
DIRETORIA = [
    ("Visão executiva", [
        texto("Pós-venda · KPIs financeiros da diretoria",
              "Carteira de parcelas de seguro de vida em atraso. Esta página resume os quatro fatos; cada um tem a sua página (carteira em "
              "aberto, recuperação, safras e qualidade dos dados). A primeira linha compara a foto mais recente com 30 dias antes; a segunda, "
              "o mês corrente com o fechamento do mês anterior. " + NOTA_SALDO, 0, 0, 12, 3),
        c_saldo(0, 3), c_pct60(3, 3), c_pend(6, 3), c_taxa(9, 3),
        c_mom_saldo(0, 6), c_cresc(3, 6), c_ytd(6, 6), c_mom_rec(9, 6),
        g_saldo_dia(0, 9, 6, 6), g_recup_mes(6, 9, 6, 6), g_taxa_safra(0, 15, 6, 5), g_barrados(6, 15, 6, 5),
    ]),
    ("Carteira em aberto", [
        cab("Carteira em aberto", "Posição diária das pendências em aberto: risco (atraso acima de 60 dias), crescimento e fechamento de cada mês. "
            + NOTA_SALDO),
        c_saldo(0, 2), c_pct60(3, 2), c_pend(6, 2), c_mom_saldo(9, 2),
        g_saldo_dia(0, 5, 8, 6), g_aging(8, 5, 4, 6),
        colunas(MES, [(f"{CD}[Saldo em aberto]", "Saldo de fechamento")], "Saldo de fechamento por mês", 0, 11, 6, 6,
                sub="Último dia de cada mês; mês corrente = foto mais recente", por_categoria=True),
        colunas(MES, [(f"{CD}[Variação mensal do saldo]", "Variação mensal do saldo")], "Variação mensal do saldo de fechamento", 6, 11, 6, 6,
                sub="Crescimento mês a mês; a carteira sintética não baixa pendências por perda", por_categoria=True),
        barras("Produto[Produto]", [(f"{CD}[Saldo em cobrança externa]", "Saldo em cobrança externa")],
               "Saldo em cobrança externa por produto (hoje)", 0, 17, 6, 6),
        colunas(f"{CD}[Status de cobrança]", [(f"{CD}[Saldo em aberto]", "Saldo em aberto")], "Saldo por status de cobrança (hoje)", 6, 17, 6, 6),
    ]),
    ("Recuperação", [
        cab("Recuperação", "Pagamentos (baixas) das pendências: valor recuperado por mês, acumulado no ano e variação sobre o mês anterior. "
                           "A variação mensal compara só meses completos."),
        c_ytd(0, 2), c_mom_rec(3, 2),
        cartao(f"{RC}[Ticket médio recuperado]", "Ticket médio recuperado", 6, 2, sub="Valor recuperado / pendências pagas"),
        cartao(f"{RC}[Multa e juros recebidos]", "Multa e juros recebidos", 9, 2, sub="Todas as baixas"),
        g_recup_mes(0, 5, 6, 6),
        linha(MES, [(f"{RC}[Recuperado acumulado no ano]", "Acumulado no ano")], "Valor recuperado acumulado no ano", 6, 5, 6, 6,
              sub="Soma das baixas desde 1º de janeiro (dados desde 19/05/2026)"),
        g_recup_forma(0, 11, 12, 6),
    ]),
    ("Safras", [
        cab("Safras", "Safra = mês em que a pendência entrou na carteira. A taxa de recuperação é a parte da safra que já foi paga; "
                      "compare safras de mesma idade (as recentes tiveram menos tempo)."),
        c_taxa(0, 2), cartao(f"{SF}[Pendências que entraram]", "Pendências que entraram", 3, 2, sub="Todas as safras"),
        cartao(f"{SF}[Pendências pagas da safra]", "Pendências pagas", 6, 2, sub="Todas as safras"),
        cartao(f"{SF}[Valor recuperado da safra]", "Valor recuperado das safras", 9, 2, sub="Pago pelas pendências das safras"),
        g_taxa_safra(0, 5, 12, 6),
        colunas("Canal de venda[Canal de venda]", [(f"{SF}[Taxa de recuperação]", "Taxa de recuperação")],
                "Taxa de recuperação por canal de venda", 0, 11, 6, 6),
        colunas("Forma de pagamento[Forma de pagamento]", [(f"{SF}[Taxa de recuperação]", "Taxa de recuperação")],
                "Taxa de recuperação por forma de pagamento", 6, 11, 6, 6),
    ]),
    ("Qualidade dos dados", [
        cab("Qualidade dos dados", "Quanto dos eventos do sistema de origem entra nos números. Eventos barrados vão para a quarentena e não "
                                   "entram; avisos entram, mas com dado incompleto. O detalhe por regra está no painel pos_venda · Qualidade de dados."),
        *c_qualidade(2), g_barrados(0, 5, 12, 6), g_avisos(0, 11, 12, 6),
    ]),
]
RELATORIOS = {
    "pos_venda_negocio": ("pos_venda · KPIs financeiros · Time de negócio", NEGOCIO,
                          ["Produto[Produto]", "Canal de venda[Canal de venda]", "Forma de pagamento[Forma de pagamento]"]),
    "pos_venda_diretoria": ("pos_venda · KPIs financeiros · Diretoria", DIRETORIA, []),
}


def js(caminho: pathlib.Path, obj):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def plataforma(tipo, nome):
    return {"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": tipo, "displayName": nome}, "config": {"version": "2.0", "logicalId": guid("item", tipo, nome)}}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower().encode("ascii", "ignore").decode()).strip("_")


def escrever_relatorio(pasta, titulo, paginas, filtros):
    base = PROJETO / f"{pasta}.Report"
    d = base / "definition"
    js(PROJETO / f"{pasta}.pbip", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
                                   "version": "1.0", "artifacts": [{"report": {"path": f"{pasta}.Report"}}],
                                   "settings": {"enableAutoRecovery": True}})
    js(base / ".platform", plataforma("Report", titulo))
    js(base / "definition.pbir", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
                                  "version": "4.0", "datasetReference": {"byPath": {"path": f"../{MODELO}"}}})
    js(d / "version.json", {"$schema": f"{U}/versionMetadata/{VERSOES['versionMetadata']}/schema.json", "version": "2.0.0"})
    tema = {"name": "pos_venda", "dataColors": PALETA, "background": "#FFFFFF", "foreground": "#11171C", "tableAccent": "#2272B4"}
    js(base / "StaticResources" / "RegisteredResources" / "pos_venda_tema.json", tema)
    rel = {"$schema": f"{U}/report/{VERSOES['report']}/schema.json",
           "themeCollection": {"customTheme": {"name": "pos_venda_tema.json", "type": "RegisteredResources",
                                               "reportVersionAtImport": {"visual": VERSOES["visualContainer"], "page": VERSOES["page"],
                                                                         "report": VERSOES["report"]}}},
           "resourcePackages": [{"name": "RegisteredResources", "type": "RegisteredResources",
                                 "items": [{"name": "pos_venda_tema.json", "path": "pos_venda_tema.json", "type": "CustomTheme"}]}]}
    if filtros:
        rel["filterConfig"] = {"filters": [{"name": f"f_{slug(f)}", "field": campo(f)[0], "type": "Categorical"} for f in filtros]}
    js(d / "report.json", rel)
    nomes = []
    for i, (nome_pg, visuais) in enumerate(paginas):
        pid = f"p{i + 1:02d}_{slug(nome_pg)}"
        nomes.append(pid)
        altura = MARGEM * 2 + max(v["pos"][1] + v["pos"][3] for v in visuais) * LINHA
        js(d / "pages" / pid / "page.json", {"$schema": f"{U}/page/{VERSOES['page']}/schema.json", "name": pid, "displayName": nome_pg,
                                             "displayOption": "FitToWidth", "height": altura, "width": LARGURA})
        for j, v in enumerate(visuais):
            vid = f"v{j + 1:02d}_{v['tipo'].lower()}"
            p = pos_px(*v["pos"])
            js(d / "pages" / pid / "visuals" / vid / "visual.json",
               {"$schema": f"{U}/visualContainer/{VERSOES['visualContainer']}/schema.json", "name": vid,
                "position": {**p, "z": j * 1000, "tabOrder": j * 1000}, "visual": v["visual"]})
    js(d / "pages" / "pages.json", {"$schema": f"{U}/pagesMetadata/{VERSOES['pagesMetadata']}/schema.json",
                                    "pageOrder": nomes, "activePageName": nomes[0]})


def gerar():
    if PROJETO.exists():
        shutil.rmtree(PROJETO)
    escrever_modelo()
    for pasta, (titulo, paginas, filtros) in RELATORIOS.items():
        escrever_relatorio(pasta, titulo, paginas, filtros)
    (PROJETO / ".gitignore").write_text("**/.pbi/localSettings.json\n**/.pbi/cache.abf\n", encoding="utf-8")


# ================================================================================================ conferência
def conferir() -> list[str]:
    erros = []
    # 1) layout: cada página fecha 12 colunas por linha da grade e não sobrepõe visuais
    for pasta, (_, paginas, _) in RELATORIOS.items():
        for nome_pg, visuais in paginas:
            ocupado = {}
            for v in visuais:
                x, y, w, h = v["pos"]
                for yy in range(y, y + h):
                    for xx in range(x, x + w):
                        if (yy, xx) in ocupado:
                            erros.append(f"{pasta}/{nome_pg}: sobreposição em ({xx},{yy})")
                        ocupado[(yy, xx)] = 1
            for yy in {yy for yy, _ in ocupado}:
                if sum(1 for (a, _) in ocupado if a == yy) != 12:
                    erros.append(f"{pasta}/{nome_pg}: linha {yy} não fecha 12 colunas")
    # 2) DAX: toda medida citada entre colchetes sem tabela existe no modelo; toda Tabela[campo] existe
    medidas = {m[0] for t in TABELAS for m in t["medidas"]}
    for t in TABELAS:
        for nome, dax, *_ in t["medidas"]:
            for ref in re.findall(r"(?<![\]'A-Za-zÀ-ú])\[([^\]]+)\]", dax):
                if ref not in medidas:
                    erros.append(f"medida {nome}: [{ref}] não existe")
            for tab, col in re.findall(r"'([^']+)'\[([^\]]+)\]", dax):
                if tab not in CAMPOS or (col not in CAMPOS[tab][0] and col not in CAMPOS[tab][1]):
                    erros.append(f"medida {nome}: '{tab}'[{col}] não existe")
    # 3) relações apontam para colunas existentes
    for t, c, d, k in RELACOES:
        if c not in CAMPOS[t][0] or k not in CAMPOS[d][0]:
            erros.append(f"relação {t}.{c} -> {d}.{k} inválida")
    # 4) colunas SQL das visões = sourceColumn do modelo
    cols_visao = {n: {c for c, _ in cols} for n, _, cols, _ in VISOES}
    for t in TABELAS:
        faltam = {o for _, o, _, _ in t["colunas"]} - cols_visao[t["visao"]]
        if faltam:
            erros.append(f"{t['nome']}: colunas fora da visão {t['visao']}: {sorted(faltam)}")
    # 5) JSON contra os esquemas oficiais da Microsoft (Fabric/PBIP)
    erros += validar_esquemas()
    return erros


def baixar_esquemas():
    base = "https://raw.githubusercontent.com/microsoft/json-schemas/main/fabric"
    arquivos = [f"item/report/definition/report/{VERSOES['report']}/schema.json",
                f"item/report/definition/page/{VERSOES['page']}/schema.json",
                f"item/report/definition/pagesMetadata/{VERSOES['pagesMetadata']}/schema.json",
                f"item/report/definition/visualContainer/{VERSOES['visualContainer']}/schema.json",
                f"item/report/definition/versionMetadata/{VERSOES['versionMetadata']}/schema.json",
                "item/report/definition/filterConfiguration/1.2.0/schema-embedded.json",
                "item/report/definition/semanticQuery/1.3.0/schema.json",
                "item/report/definition/visualConfiguration/2.2.0/schema-embedded.json",
                "item/report/definition/formattingObjectDefinitions/1.4.0/schema.json",
                "item/report/definitionProperties/2.0.0/schema.json",
                "item/semanticModel/definitionProperties/1.0.0/schema.json",
                "pbip/pbipProperties/1.0.0/schema.json"]
    for a in arquivos:
        destino = ESQUEMAS / a
        if not destino.exists():
            destino.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["curl", "-sfL", f"{base}/{a}", "-o", str(destino)], check=True)


def validar_esquemas() -> list[str]:
    try:
        import jsonschema
        from referencing import Registry, Resource
    except ImportError:
        return ["(aviso) jsonschema não instalado: validação contra os esquemas oficiais não rodou"]
    baixar_esquemas()
    raiz = "https://developer.microsoft.com/json-schemas/fabric/"
    def obter(uri):
        caminho = ESQUEMAS / uri.replace(raiz, "").replace("schema.embedded.json", "schema-embedded.json")
        return Resource.from_contents(json.loads(caminho.read_text()))
    registro = Registry(retrieve=obter)
    erros, n = [], 0
    for f in sorted(PROJETO.rglob("*")):
        if f.suffix not in (".json", ".pbip", ".pbir", ".pbism") or "StaticResources" in f.parts:
            continue
        doc = json.loads(f.read_text())
        uri = doc.get("$schema", "")
        if not uri.startswith(raiz):
            continue
        esquema = json.loads((ESQUEMAS / uri.replace(raiz, "")).read_text())
        validador = jsonschema.validators.validator_for(esquema)(esquema, registry=registro)
        for e in validador.iter_errors(doc):
            erros.append(f"{f.relative_to(PROJETO)}: {e.message[:160]} em {list(e.absolute_path)[:6]}")
        n += 1
    print(f"esquemas oficiais: {n} arquivos validados")
    return erros


# ================================================================================================ valores de referência
def referencia():
    """O que o painel do Databricks mostra (datasets do gerar_paineis.py sobre as metric views) x o mesmo cálculo das medidas DAX
    feito em SQL sobre as visões pos_venda.bi. Iguais = as visões e a lógica das medidas reproduzem o painel."""
    uc = cliente_sql()
    sys.path.insert(0, str(AQUI.parent))
    import gerar_paineis as gp  # noqa: E402
    from databricks.sdk.service.sql import StatementState
    w = uc.cliente()

    def ds(nome):
        r = w.statement_execution.execute_statement(warehouse_id=uc.WAREHOUSE, catalog=CATALOGO, schema="ontologia",
                                                    statement="".join(gp.DS[nome]["queryLines"]), wait_timeout="30s")
        while r.status.state in (StatementState.PENDING, StatementState.RUNNING):
            r = w.statement_execution.get_statement(r.statement_id)
        cols = [c.name for c in r.manifest.schema.columns]
        return [dict(zip(cols, linha)) for linha in (r.result.data_array or [])]

    f = lambda v: float(v) if v not in (None, "") else 0.0      # noqa: E731
    dia, mes, rmes = ds("ds_carteira_dia"), ds("ds_carteira_mes"), ds("ds_recuperacao_mes")
    rec, saf, qual = ds("ds_recuperacao"), ds("ds_safra"), ds("ds_qualidade")
    atual = next(r for r in dia if r["atual"] == "true")
    m_at = [r for r in mes if r["mes_atual"] == "true"]
    r_at = [r for r in rmes if r["mes_atual"] == "true"]
    r_uc = [r for r in rmes if r["ultimo_mes_completo"] == "true"]
    sfm, sma, sin = (sum(f(r[k]) for r in m_at) for k in ("saldo_fechamento", "saldo_mes_anterior", "saldo_inicio"))
    rr, rra = sum(f(r["recuperado"]) for r in r_uc), sum(f(r["recuperado_mes_anterior"]) for r in r_uc)
    databricks = {
        "Foto mais recente": atual["data"][:10],
        "Saldo em aberto": f(atual["saldo"]), "Saldo 30 dias antes": f(atual["saldo_30d"]),
        "Pendências em aberto": f(atual["pendencias"]), "% do saldo acima de 60 dias": f(atual["pct_60"]),
        "Ticket médio da pendência": f(atual["ticket"]), "Multa e juros em aberto": f(atual["encargos"]),
        "Variação mensal do saldo": (sfm - sma) / sma, "Crescimento da carteira no mês": sfm - sin,
        "Recuperado no ano": sum(f(r["acumulado_ano"]) for r in r_at), "Variação mensal do recuperado (último mês completo)": (rr - rra) / rra,
        "Valor recuperado": sum(f(r["recuperado"]) for r in rec), "Pendências pagas": sum(f(r["pagas"]) for r in rec),
        "Multa e juros recebidos": sum(f(r["encargos_recebidos"]) for r in rec),
        "Taxa de recuperação": sum(f(r["pagas"]) for r in saf) / sum(f(r["entradas"]) for r in saf),
        "Pendências que entraram": sum(f(r["entradas"]) for r in saf), "Valor recuperado da safra": sum(f(r["valor_recuperado"]) for r in saf),
        "Eventos recebidos": sum(f(r["recebidos"]) for r in qual), "Eventos barrados": sum(f(r["barrados"]) for r in qual),
        "Taxa de barrados": sum(f(r["barrados"]) for r in qual) / sum(f(r["recebidos"]) for r in qual),
        "Forma de pagamento não cadastrada": sum(f(r["vazamento"]) for r in qual),
    }
    B = f"{CATALOGO}.{SCHEMA}"
    sql = f"""WITH d AS (SELECT max(data_referencia) AS d FROM {B}.carteira_diaria),
c AS (SELECT data_referencia AS dt, sum(saldo_em_aberto) s, sum(pendencias_em_aberto) p, sum(saldo_acima_60_dias) s60,
             sum(multa_juros_em_aberto) mj FROM {B}.carteira_diaria GROUP BY 1),
ini AS (SELECT min(dt) AS i FROM c, d WHERE dt BETWEEN trunc(d.d, 'MM') AND d.d),
u AS (SELECT max(data_baixa) AS u FROM {B}.recuperacao_diaria),
fim AS (SELECT CASE WHEN u = last_day(u) THEN u ELSE last_day(add_months(u, -1)) END AS f FROM u),
rm AS (SELECT trunc(data_baixa, 'MM') AS m, sum(valor_recuperado) v FROM {B}.recuperacao_diaria GROUP BY 1),
cal AS (SELECT max(ano) AS ano FROM {B}.calendario)
SELECT CAST((SELECT d FROM d) AS STRING),
  (SELECT max(s) FROM c WHERE dt = (SELECT d FROM d)), (SELECT max(s) FROM c WHERE dt = date_sub((SELECT d FROM d), 30)), (SELECT max(p) FROM c WHERE dt = (SELECT d FROM d)),
  (SELECT max(s60 / s) FROM c WHERE dt = (SELECT d FROM d)), (SELECT max(s / p) FROM c WHERE dt = (SELECT d FROM d)), (SELECT max(mj) FROM c WHERE dt = (SELECT d FROM d)),
  (SELECT max(s) FROM c WHERE dt = (SELECT d FROM d)) / (SELECT max(s) FROM c WHERE dt = last_day(add_months((SELECT d FROM d), -1))) - 1,
  (SELECT max(s) FROM c WHERE dt = (SELECT d FROM d)) - (SELECT s FROM c, ini WHERE dt = ini.i),
  (SELECT sum(valor_recuperado) FROM {B}.recuperacao_diaria, cal WHERE year(data_baixa) = cal.ano),
  (SELECT max(v) FROM rm, fim WHERE m = trunc(fim.f, 'MM')) / (SELECT max(v) FROM rm, fim WHERE m = add_months(trunc(fim.f, 'MM'), -1)) - 1,
  (SELECT sum(valor_recuperado) FROM {B}.recuperacao_diaria), (SELECT sum(pendencias_pagas) FROM {B}.recuperacao_diaria),
  (SELECT sum(multa_juros_recebidos) FROM {B}.recuperacao_diaria),
  (SELECT sum(pendencias_pagas) / sum(pendencias_entraram) FROM {B}.safras), (SELECT sum(pendencias_entraram) FROM {B}.safras),
  (SELECT sum(valor_recuperado) FROM {B}.safras),
  (SELECT sum(eventos_recebidos) FROM {B}.qualidade_diaria), (SELECT sum(eventos_barrados) FROM {B}.qualidade_diaria),
  (SELECT sum(eventos_barrados) / sum(eventos_recebidos) FROM {B}.qualidade_diaria),
  (SELECT sum(forma_pagamento_nao_cadastrada) FROM {B}.qualidade_diaria)
FROM (SELECT 1) AS um"""
    linha_bi = uc.executar(sql, espera="50s")[0]
    bi = dict(zip(databricks.keys(), [linha_bi[0]] + [f(v) for v in linha_bi[1:]]))
    linhas, ok = [], True
    for k, v in databricks.items():
        b = bi[k]
        igual = v == b if isinstance(v, str) else abs(v - b) <= max(0.005, abs(v) * 1e-9)
        ok &= igual
        linhas.append((k, v, b, igual))

    def fmt(k, v):
        if isinstance(v, str):
            return v
        if k.startswith(("%", "Taxa", "Variação")):
            return f"{v * 100:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")
        if k.startswith(("Pendências", "Eventos", "Forma")):
            return f"{v:,.0f}".replace(",", ".")
        return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    md = ["# Valores de referência · Power BI x Databricks", "",
          f"Gerado por `python3 gerar_powerbi.py referencia`. Foto mais recente: **{databricks['Foto mais recente']}**. "
          "Depois de atualizar o Power BI, os cartões devem mostrar exatamente a coluna *Databricks* (sem filtro).", "",
          "| Indicador | Databricks (painel AI/BI) | Visões pos_venda.bi com a lógica das medidas DAX | Igual | Power BI (anotar na avaliação) |",
          "|---|---|---|---|---|"]
    md += [f"| {k} | {fmt(k, v)} | {fmt(k, b)} | {'sim' if i else '**NÃO**'} | |" for k, v, b, i in linhas]
    (AQUI / "VALORES_DE_REFERENCIA.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    for k, v, b, i in linhas:
        print(f"{'OK ' if i else 'DIF'} {k:52} {fmt(k, v):>22} {fmt(k, b):>22}")
    print("PARIDADE:", "100%" if ok else "há diferenças")
    return 0 if ok else 1


if __name__ == "__main__":
    acao = sys.argv[1] if len(sys.argv) > 1 else "gerar"
    if acao == "visoes":
        criar_visoes()
    elif acao == "referencia":
        sys.exit(referencia())
    elif acao == "ddl":
        print(";\n\n".join(ddl_visoes()) + ";")
    elif acao == "bim":
        destino = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else AQUI / "auditoria" / "modelo_bim"
        js(destino / "model.bim", modelo_bim())
        print(f"{destino / 'model.bim'}: {len(TABELAS)} tabelas, {sum(len(t['medidas']) for t in TABELAS)} medidas, {len(RELACOES)} relações")
    else:
        gerar()
        n_vis = sum(len(v) for _, (_, pgs, _) in RELATORIOS.items() for _, v in pgs)
        print(f"projeto/: modelo ({len(TABELAS)} tabelas, {sum(len(t['medidas']) for t in TABELAS)} medidas, {len(RELACOES)} relações) + "
              f"{len(RELATORIOS)} relatórios ({sum(len(p) for _, (_, p, _) in RELATORIOS.items())} páginas, {n_vis} visuais)")
        erros = conferir()
        print("conferência:", "ok" if not erros else f"{len(erros)} problema(s)")
        for e in erros[:40]:
            print("  -", e)
        sys.exit(1 if [e for e in erros if not e.startswith("(aviso)")] else 0)
