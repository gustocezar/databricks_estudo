#!/usr/bin/env python3
"""Espaços Genie do domínio Pós-venda: analista financeiro e diretor financeiro.

  python3 genie.py gerar     monta as configurações (genie/<espaco>.json) e a lista de SQL a validar
  python3 genie.py validar   roda no warehouse todo SQL de exemplo e de avaliação (precisa da cota) -> genie/validacao.json
  python3 genie.py criar     cria ou atualiza os 2 espaços, só com o SQL que passou na validação
  python3 genie.py avaliar   faz cada pergunta de avaliação à Genie (Conversation API) e compara com o resultado esperado

Fontes: metric views de pos_venda.ontologia (definição única das métricas), mais detalhe sem dados pessoais para o analista.
"""
import json
import pathlib
import subprocess
import sys
import time
import uuid

import sql_util

AQUI = pathlib.Path(__file__).resolve().parent
PASTA = AQUI / "genie"
PERFIL, WAREHOUSE = "dbx-workshop", "5f010b8396e591fb"
NS = uuid.UUID("6f1c2a3e-0000-4000-8000-0000000000aa")
O = "pos_venda.ontologia"
MV_C, MV_R, MV_S, MV_Q = f"{O}.mv_carteira_em_aberto", f"{O}.mv_recuperacao", f"{O}.mv_safra_recuperacao", f"{O}.mv_qualidade_dados"


def hid(*partes):
    return uuid.uuid5(NS, "|".join(partes)).hex


# ------------------------------------------------------------------------------------------------ instruções (texto)
INSTR_COMUM = """## DISAMBIGUATION
- "hoje", "atual" ou sem data: `Foto mais recente` = true na mv_carteira_em_aberto; diga a data.
- "fechamento" ou "fim do mês": `Saldo de fechamento` por `Mês de referência`.
- "mês a mês", "MoM" ou variação entre fins de mês: `Variação mensal do saldo` ou `Variação mensal do valor recuperado`, com o mês (`Mês de referência`, `Mês da baixa`), não a data do dia.
- Variação entre duas datas: `Saldo em aberto` em cada data; `Variação do saldo no período` só por mês.
- "acumulado no ano" ou "YTD": `Valor recuperado acumulado no ano` com o mês da baixa.
- "ranking" ou "posição": `Posição no ranking...`, sem medidas de fechamento, início, mês anterior ou acumulado na mesma consulta.
- "recuperado", "pago", "baixas": mv_recuperacao (data da baixa).
- "taxa de recuperação": mv_safra_recuperacao por `Safra de entrada`.
- Outros períodos (ex.: "em outubro", "semanas de dezembro"): filtre pela data do dia (`Dia`, `Data de referência`, `Data da baixa`, `Data de entrada`), nunca pela dimensão truncada (`Semana`, `Mês`, `Safra de entrada`).
- Só quebre por dia, semana ou mês se pedido; senão, um total do período.

## DATA QUALITY NOTES
- Dados sintéticos desde 19/05/2026, uma foto por dia; a carga diária acrescenta dias, então a data de "hoje" é a da linha com `Foto mais recente` = true (diga essa data na resposta).
- Forma de pagamento NAO_CADASTRADA (dez/2026) é dado que vazou da barreira de qualidade.
- Safras recentes tiveram menos tempo para pagar (taxa menor).

## CONSTRAINTS
- Saldo é semiaditivo: nunca some datas diferentes; para um período use `Saldo de fechamento`, `Saldo no início do período` ou `Saldo médio diário`.
- Nunca mostre nome, CPF, RG, e-mail, telefone ou endereço de clientes ou corretores.

## Instructions you must follow when providing summaries
- R$ e percentuais com 2 casas decimais.
- Sempre diga a data de referência ou o período usado."""

INSTR = {
    "analista": "## PURPOSE\n- Analistas financeiros do Pós-venda (seguro de vida): saldo, aging, cobrança, recuperação e dados não aptos.\n"
                "- Detalhe por pendência na view pendencia (sem dados pessoais).\n\n" + INSTR_COMUM,
    "diretor": "## PURPOSE\n- Diretoria financeira do Pós-venda (seguro de vida): visão executiva de risco da carteira, recuperação e "
               "confiabilidade dos dados. Respostas curtas, com tendência e comparação.\n\n" + INSTR_COMUM,
}

# ------------------------------------------------------------------------------------------------ funções de regra (ativos confiáveis)
# Regras de cálculo do pós-venda (pos_venda/regras): a Genie usa a função para simular valores em vez de refazer a conta.
# cpf_valido fica de fora: os espaços não têm dado pessoal.
FUNCOES = [f"pos_venda.regras.{f}" for f in ("faixa_atraso", "valor_multa", "valor_juros", "valor_total_pendente")]

# ------------------------------------------------------------------------------------------------ SQL de exemplo (formas de consulta)
EXEMPLOS = {
    "simulacao_valor_pendente": ("Quanto fica uma parcela de R$ 250,00 com 45 dias de atraso: faixa, multa, juros e total pendente?",
        "SELECT pos_venda.regras.faixa_atraso(45) AS faixa_atraso, pos_venda.regras.valor_multa(CAST(250.00 AS DECIMAL(14,2))) AS multa, "
        "pos_venda.regras.valor_juros(CAST(250.00 AS DECIMAL(14,2)), 45) AS juros, "
        "pos_venda.regras.valor_total_pendente(CAST(250.00 AS DECIMAL(14,2)), 45) AS total_pendente"),
    "carteira_atual_por_dimensao": ("Qual o saldo em aberto atual por fase da cobrança?",
        f"SELECT mv_carteira_em_aberto.`Data de referência`, mv_carteira_em_aberto.`Fase da cobrança`, "
        f"MEASURE(mv_carteira_em_aberto.`Saldo em aberto`) AS saldo, MEASURE(mv_carteira_em_aberto.`Pendências em aberto`) AS pendencias "
        f"FROM {MV_C} WHERE mv_carteira_em_aberto.`Foto mais recente` = true GROUP BY ALL ORDER BY saldo DESC"),
    "evolucao_fim_de_mes": ("Mostre o saldo em aberto de fechamento de cada mês por grupo do motivo.",
        f"SELECT mv_carteira_em_aberto.`Mês de referência`, mv_carteira_em_aberto.`Grupo do motivo`, "
        f"MEASURE(mv_carteira_em_aberto.`Saldo de fechamento`) AS saldo_fechamento FROM {MV_C} "
        f"GROUP BY ALL ORDER BY ALL"),
    "variacao_mensal_saldo": ("Qual a variação mensal do saldo de fechamento?",
        f"SELECT mv_carteira_em_aberto.`Mês de referência`, MEASURE(mv_carteira_em_aberto.`Saldo de fechamento`) AS saldo_fechamento, "
        f"MEASURE(mv_carteira_em_aberto.`Saldo de fechamento do mês anterior`) AS mes_anterior, "
        f"MEASURE(mv_carteira_em_aberto.`Variação mensal do saldo`) AS variacao FROM {MV_C} GROUP BY ALL ORDER BY ALL"),
    "variacao_entre_fechamentos": ("Qual a variação do saldo entre o fim de agosto e o fim de setembro de 2026?",
        f"SELECT mv_carteira_em_aberto.`Mês de referência`, MEASURE(mv_carteira_em_aberto.`Saldo de fechamento do mês anterior`) AS fechamento_anterior, "
        f"MEASURE(mv_carteira_em_aberto.`Saldo de fechamento`) AS fechamento, MEASURE(mv_carteira_em_aberto.`Variação mensal do saldo`) AS variacao "
        f"FROM {MV_C} WHERE mv_carteira_em_aberto.`Mês de referência` = DATE'2026-09-01' GROUP BY ALL"),
    "recuperado_acumulado_ano": ("Quanto recuperamos por mês e no acumulado do ano?",
        f"SELECT mv_recuperacao.`Mês da baixa`, MEASURE(mv_recuperacao.`Valor recuperado`) AS recuperado, "
        f"MEASURE(mv_recuperacao.`Valor recuperado acumulado no ano`) AS acumulado_ano FROM {MV_R} GROUP BY ALL ORDER BY ALL"),
    "ranking_recuperacao": ("Qual a posição de cada produto no ranking de valor recuperado em dezembro de 2026?",
        f"SELECT mv_recuperacao.`Produto`, MEASURE(mv_recuperacao.`Valor recuperado`) AS recuperado, "
        f"MEASURE(mv_recuperacao.`Posição no ranking de recuperação`) AS posicao FROM {MV_R} "
        f"WHERE mv_recuperacao.`Mês da baixa` = DATE'2026-12-01' GROUP BY ALL ORDER BY posicao"),
    "comparar_duas_datas": ("Compare a quantidade de pendências em aberto em 31/10/2026 e 30/11/2026 por canal de venda.",
        f"SELECT mv_carteira_em_aberto.`Canal de venda`, mv_carteira_em_aberto.`Data de referência`, "
        f"MEASURE(mv_carteira_em_aberto.`Pendências em aberto`) AS pendencias FROM {MV_C} "
        f"WHERE mv_carteira_em_aberto.`Data de referência` IN (DATE'2026-10-31', DATE'2026-11-30') GROUP BY ALL ORDER BY ALL"),
    "ranking_top_n": ("Quais 5 regionais têm o maior percentual do saldo acima de 60 dias na posição atual?",
        f"SELECT mv_carteira_em_aberto.`Regional`, MEASURE(mv_carteira_em_aberto.`Percentual do saldo acima de 60 dias`) AS pct_acima_60 "
        f"FROM {MV_C} WHERE mv_carteira_em_aberto.`Foto mais recente` = true GROUP BY ALL ORDER BY pct_acima_60 DESC LIMIT 5"),
    "recuperacao_mensal": ("Quanto foi recuperado por mês e por categoria do produto?",
        f"SELECT mv_recuperacao.`Mês da baixa`, mv_recuperacao.`Categoria do produto`, MEASURE(mv_recuperacao.`Valor recuperado`) AS recuperado, "
        f"MEASURE(mv_recuperacao.`Pendências pagas`) AS pagas FROM {MV_R} GROUP BY ALL ORDER BY ALL"),
    "taxa_por_safra": ("Qual a taxa de recuperação por safra de entrada e periodicidade?",
        f"SELECT mv_safra_recuperacao.`Safra de entrada`, mv_safra_recuperacao.`Periodicidade`, "
        f"MEASURE(mv_safra_recuperacao.`Taxa de recuperação`) AS taxa FROM {MV_S} GROUP BY ALL ORDER BY ALL"),
    "qualidade_semanal": ("Como variou a taxa de e-mail ausente em cada semana de novembro de 2026?",
        f"SELECT mv_qualidade_dados.`Semana`, MEASURE(mv_qualidade_dados.`Taxa de e-mail ausente`) AS taxa FROM {MV_Q} "
        f"WHERE mv_qualidade_dados.`Dia` BETWEEN DATE'2026-11-01' AND DATE'2026-11-30' GROUP BY ALL ORDER BY ALL"),
    "detalhe_pendencias": ("Liste as pendências da apólice VID000289125 com status e valores.",
        f"SELECT pendencia.pendencia_id, pendencia.numero_parcela, pendencia.status_cobranca, pendencia.data_vencimento, "
        f"pendencia.data_baixa, pendencia.valor_parcela, pendencia.valor_pago FROM {O}.pendencia "
        f"WHERE pendencia.numero_apolice = 'VID000289125' ORDER BY pendencia.numero_parcela"),
}

# ------------------------------------------------------------------------------------------------ avaliação (benchmarks)
B = {  # chave -> (pergunta, SQL esperado)
    "saldo_hoje": ("Qual o saldo em aberto hoje?",
        f"SELECT MEASURE(`Saldo em aberto`) AS saldo FROM {MV_C} WHERE `Foto mais recente` = true"),
    "aging_hoje": ("Qual o saldo em aberto por faixa de atraso na posição atual?",
        f"SELECT `Faixa de atraso`, MEASURE(`Saldo em aberto`) AS saldo FROM {MV_C} WHERE `Foto mais recente` = true GROUP BY ALL ORDER BY ALL"),
    "top3_produtos_60d": ("Quais os 3 produtos com maior saldo acima de 60 dias hoje?",
        f"SELECT `Produto`, MEASURE(`Saldo acima de 60 dias`) AS saldo FROM {MV_C} WHERE `Foto mais recente` = true "
        f"GROUP BY ALL ORDER BY saldo DESC LIMIT 3"),
    "saldo_canal_3011": ("Qual era o saldo em aberto em 30/11/2026 por canal de venda?",
        f"SELECT `Canal de venda`, MEASURE(`Saldo em aberto`) AS saldo FROM {MV_C} WHERE `Data de referência` = DATE'2026-11-30' "
        f"GROUP BY ALL ORDER BY saldo DESC"),
    "recuperado_dez_forma": ("Quanto foi recuperado em dezembro de 2026 por forma de pagamento?",
        f"SELECT `Forma de pagamento`, MEASURE(`Valor recuperado`) AS recuperado FROM {MV_R} WHERE `Mês da baixa` = DATE'2026-12-01' "
        f"GROUP BY ALL ORDER BY recuperado DESC"),
    "ticket_recuperado_nov": ("Qual foi o ticket médio recuperado em novembro de 2026?",
        f"SELECT MEASURE(`Ticket médio recuperado`) AS ticket FROM {MV_R} WHERE `Mês da baixa` = DATE'2026-11-01'"),
    "taxa_safras_set_nov": ("Qual a taxa de recuperação das safras de setembro, outubro e novembro de 2026?",
        f"SELECT `Safra de entrada`, MEASURE(`Taxa de recuperação`) AS taxa FROM {MV_S} "
        f"WHERE `Safra de entrada` BETWEEN DATE'2026-09-01' AND DATE'2026-11-01' GROUP BY ALL ORDER BY ALL"),
    "entradas_out": ("Quantas pendências entraram em outubro de 2026?",
        f"SELECT MEASURE(`Pendências que entraram`) AS entradas FROM {MV_S} WHERE `Safra de entrada` = DATE'2026-10-01'"),
    "grupo_motivo_hoje": ("Qual grupo de motivo concentra o maior saldo em aberto hoje?",
        f"SELECT `Grupo do motivo`, MEASURE(`Saldo em aberto`) AS saldo FROM {MV_C} WHERE `Foto mais recente` = true "
        f"GROUP BY ALL ORDER BY saldo DESC LIMIT 1"),
    "atraso_medio_status": ("Qual o atraso médio em dias das pendências em aberto hoje por status de cobrança?",
        f"SELECT `Status de cobrança`, MEASURE(`Atraso médio em dias`) AS atraso FROM {MV_C} WHERE `Foto mais recente` = true "
        f"GROUP BY ALL ORDER BY atraso DESC"),
    "barrados_dez_motivo": ("Quantos eventos foram barrados em dezembro de 2026 por motivo da rejeição?",
        "SELECT motivo_rejeicao, sum(eventos) AS eventos FROM pos_venda.gold.dq_barrados_por_motivo_dia "
        "WHERE dia BETWEEN DATE'2026-12-01' AND DATE'2026-12-31' GROUP BY motivo_rejeicao ORDER BY eventos DESC"),
    "top10_pagas_dez": ("Quais as 10 pendências pagas em dezembro de 2026 com maior valor pago?",
        f"SELECT pendencia_id, numero_apolice, data_baixa, valor_pago FROM {O}.pendencia "
        f"WHERE data_baixa BETWEEN DATE'2026-12-01' AND DATE'2026-12-31' ORDER BY valor_pago DESC LIMIT 10"),
    "saldo_fim_mes": ("Como evoluiu o saldo em aberto no fim de cada mês?",
        f"SELECT `Mês de referência`, MEASURE(`Saldo de fechamento`) AS saldo_fechamento FROM {MV_C} GROUP BY ALL ORDER BY ALL"),
    "pct60_hoje": ("Qual o percentual do saldo acima de 60 dias hoje?",
        f"SELECT MEASURE(`Percentual do saldo acima de 60 dias`) AS pct FROM {MV_C} WHERE `Foto mais recente` = true"),
    "pct60_2411": ("Qual era o percentual do saldo acima de 60 dias em 24/11/2026?",
        f"SELECT MEASURE(`Percentual do saldo acima de 60 dias`) AS pct FROM {MV_C} WHERE `Data de referência` = DATE'2026-11-24'"),
    "recuperado_mes": ("Quanto recuperamos por mês em 2026?",
        f"SELECT `Mês da baixa`, MEASURE(`Valor recuperado`) AS recuperado FROM {MV_R} WHERE year(`Mês da baixa`) = 2026 "
        f"GROUP BY ALL ORDER BY ALL"),
    "taxa_safra": ("Qual a taxa de recuperação por safra de entrada?",
        f"SELECT `Safra de entrada`, MEASURE(`Taxa de recuperação`) AS taxa FROM {MV_S} GROUP BY ALL ORDER BY ALL"),
    "cobranca_externa_produto": ("Qual o saldo em cobrança externa por produto hoje?",
        f"SELECT `Produto`, MEASURE(`Saldo em cobrança externa`) AS saldo FROM {MV_C} WHERE `Foto mais recente` = true "
        f"GROUP BY ALL ORDER BY saldo DESC"),
    "saldo_medio_dez": ("Qual foi o saldo médio diário em dezembro de 2026?",
        f"SELECT MEASURE(`Saldo médio diário`) AS saldo_medio FROM {MV_C} WHERE `Mês de referência` = DATE'2026-12-01'"),
    "barrados_semana_dez": ("Qual foi a taxa de eventos barrados em cada semana de dezembro de 2026?",
        f"SELECT `Semana`, MEASURE(`Taxa de barrados`) AS taxa FROM {MV_Q} WHERE `Dia` BETWEEN DATE'2026-12-01' AND DATE'2026-12-31' "
        f"GROUP BY ALL ORDER BY ALL"),
    "pendencias_clientes_hoje": ("Quantas pendências e quantos clientes estão em aberto hoje?",
        f"SELECT MEASURE(`Pendências em aberto`) AS pendencias, MEASURE(`Clientes com pendência`) AS clientes FROM {MV_C} "
        f"WHERE `Foto mais recente` = true"),
    "variacao_out_nov": ("Qual a variação do saldo em aberto entre o fim de outubro e o fim de novembro de 2026?",
        f"SELECT `Mês de referência`, MEASURE(`Saldo de fechamento do mês anterior`) AS fechamento_outubro, "
        f"MEASURE(`Saldo de fechamento`) AS fechamento_novembro, MEASURE(`Variação mensal do saldo`) AS variacao "
        f"FROM {MV_C} WHERE `Mês de referência` = DATE'2026-11-01' GROUP BY ALL"),
    "vazamento_dez": ("Quantos eventos com forma de pagamento não cadastrada entraram em dezembro de 2026?",
        f"SELECT MEASURE(`Forma de pagamento não cadastrada`) AS eventos FROM {MV_Q} WHERE `Mês` = DATE'2026-12-01'"),
    # padrões de uc-semantics-patterns (fechamento, MoM, acumulado e ranking)
    "mom_saldo_nov": ("Quanto o saldo de fechamento de novembro de 2026 variou em relação ao fechamento de outubro, em percentual?",
        f"SELECT MEASURE(`Variação mensal do saldo`) AS variacao FROM {MV_C} WHERE `Mês de referência` = DATE'2026-11-01'"),
    "recuperado_ytd_nov": ("Quanto recuperamos no acumulado do ano até novembro de 2026?",
        f"SELECT MEASURE(`Valor recuperado`) AS acumulado FROM {MV_R} WHERE `Data da baixa` BETWEEN DATE'2026-01-01' AND DATE'2026-11-30'"),
    "ranking_recuperacao_canal": ("Qual a posição de cada canal de venda no ranking de valor recuperado em novembro de 2026?",
        f"SELECT `Canal de venda`, MEASURE(`Posição no ranking de recuperação`) AS posicao FROM {MV_R} "
        f"WHERE `Mês da baixa` = DATE'2026-11-01' GROUP BY ALL ORDER BY posicao"),
    "simulacao_faixa_total_120d": ("Em que faixa de atraso fica uma parcela de R$ 1.000,00 com 120 dias de atraso e qual o total pendente dela?",
        "SELECT pos_venda.regras.faixa_atraso(120) AS faixa_atraso, "
        "pos_venda.regras.valor_total_pendente(CAST(1000.00 AS DECIMAL(14,2)), 120) AS total_pendente"),
    "simulacao_juros_90d": ("Quanto de juros uma parcela de R$ 500,00 acumula com 90 dias de atraso?",
        "SELECT pos_venda.regras.valor_juros(CAST(500.00 AS DECIMAL(14,2)), 90) AS juros"),
}

DIM_MV = {  # dimensões categóricas para assistência de formato e correspondência de valores
    MV_C: ["Canal de venda", "Categoria do produto", "Fase da cobrança", "Faixa de atraso", "Forma de pagamento",
           "Grupo da forma de pagamento", "Grupo do motivo", "Motivo da pendência", "Periodicidade", "Produto", "Regional",
           "Status da apólice", "Status de cobrança", "UF do ponto de venda"],
    MV_R: ["Canal de venda", "Categoria do produto", "Faixa de atraso na baixa", "Forma de pagamento", "Motivo da pendência", "Produto"],
    MV_S: ["Canal de venda", "Forma de pagamento", "Motivo da pendência", "Periodicidade", "Produto", "Status atual"],
    MV_Q: [],
}

ESPACOS = {
    "analista": {
        "titulo": "Pós-venda · Analista financeiro (cobrança e recuperação)",
        "descricao": ("Para analistas financeiros do Pós-venda (seguro de vida): saldo em aberto e aging da carteira, pendências por "
                      "produto, canal, forma de pagamento e motivo, valor recuperado nas baixas, taxa de recuperação por safra, detalhe "
                      "por pendência (sem dados pessoais) e eventos barrados pela qualidade. Dados sintéticos."),
        "mvs": [MV_C, MV_R, MV_S, MV_Q],
        "tabelas": [f"{O}.pendencia", "pos_venda.gold.dq_barrados_por_motivo_dia"],
        "amostras": ["Qual o saldo em aberto hoje por faixa de atraso?",
                     "Quais produtos e canais concentram o saldo acima de 60 dias?",
                     "Quanto recuperamos em dezembro por forma de pagamento e qual o ticket médio?",
                     "Qual a taxa de recuperação das safras de setembro a novembro?",
                     "Quais motivos de pendência mais cresceram no último mês?"],
        "exemplos": ["carteira_atual_por_dimensao", "comparar_duas_datas", "ranking_top_n", "recuperacao_mensal", "taxa_por_safra",
                     "detalhe_pendencias", "ranking_recuperacao", "simulacao_valor_pendente"],
        "avaliacao": ["saldo_hoje", "aging_hoje", "top3_produtos_60d", "saldo_canal_3011", "recuperado_dez_forma", "ticket_recuperado_nov",
                      "taxa_safras_set_nov", "entradas_out", "grupo_motivo_hoje", "atraso_medio_status", "barrados_dez_motivo",
                      "top10_pagas_dez", "ranking_recuperacao_canal", "simulacao_faixa_total_120d"],
        "funcoes": FUNCOES,
    },
    "diretor": {
        "titulo": "Pós-venda · Diretor financeiro (visão executiva)",
        "descricao": ("Para a diretoria financeira do Pós-venda (seguro de vida): evolução do saldo em aberto, risco da carteira "
                      "(atraso acima de 60 dias e cobrança externa), recuperação por mês e por safra, e confiabilidade dos dados que "
                      "alimentam os números. Dados sintéticos."),
        "mvs": [MV_C, MV_R, MV_S, MV_Q],
        "tabelas": [],
        "amostras": ["Como evoluiu o saldo de fechamento mês a mês e qual a variação mensal?",
                     "Qual o percentual do saldo acima de 60 dias hoje e como estava há 30 dias?",
                     "Quanto recuperamos por mês e qual a taxa de recuperação por safra?",
                     "Qual o risco em cobrança externa por produto?",
                     "A qualidade dos dados afetou os números de dezembro?"],
        "exemplos": ["evolucao_fim_de_mes", "comparar_duas_datas", "recuperacao_mensal", "taxa_por_safra", "qualidade_semanal",
                     "variacao_mensal_saldo", "variacao_entre_fechamentos", "recuperado_acumulado_ano", "simulacao_valor_pendente"],
        "avaliacao": ["saldo_fim_mes", "pct60_hoje", "pct60_2411", "recuperado_mes", "taxa_safra", "cobranca_externa_produto",
                      "saldo_medio_dez", "barrados_semana_dez", "pendencias_clientes_hoje", "variacao_out_nov", "vazamento_dez",
                      "saldo_hoje", "mom_saldo_nov", "recuperado_ytd_nov", "simulacao_juros_90d"],
        "funcoes": FUNCOES,
    },
}


def montar(chave, validos=None):
    e = ESPACOS[chave]
    ok = (lambda k: True) if validos is None else (lambda k: validos.get(k) is True)
    mvs = []
    for m in sorted(e["mvs"]):
        item = {"identifier": m}
        if DIM_MV[m]:
            item["column_configs"] = [{"column_name": d, "enable_format_assistance": True, "enable_entity_matching": True}
                                      for d in sorted(DIM_MV[m])]
        mvs.append(item)
    tabelas = []
    for t in sorted(e["tabelas"]):
        item = {"identifier": t}
        if t.endswith(".pendencia"):
            item["column_configs"] = sorted(
                [{"column_name": c, "enable_format_assistance": True, "enable_entity_matching": True}
                 for c in ["canal_venda", "forma_pagamento", "motivo_pendencia", "periodicidade_pagamento", "produto_nome", "status_cobranca"]],
                key=lambda c: c["column_name"])   # cliente_id saiu da view ontologia.pendencia em 21/11/2026
        tabelas.append(item)
    espaco = {
        "version": 2,
        "config": {"sample_questions": sorted([{"id": hid(chave, "amostra", q), "question": [q]} for q in e["amostras"]],
                                              key=lambda x: x["id"])},
        "data_sources": {"metric_views": mvs, **({"tables": tabelas} if tabelas else {})},
        "instructions": {
            "text_instructions": [{"id": hid(chave, "instr"), "content": [INSTR[chave]]}],
            "example_question_sqls": sorted([{"id": hid(chave, "ex", k), "question": [EXEMPLOS[k][0]], "sql": [EXEMPLOS[k][1]]}
                                             for k in e["exemplos"] if ok("ex:" + k)], key=lambda x: x["id"]),
            "sql_functions": sorted([{"id": hid(chave, "fn", f), "identifier": f} for f in e.get("funcoes", [])],
                                    key=lambda x: x["id"]),
        },
        "benchmarks": {"questions": sorted([{"id": hid(chave, "bm", k), "question": [B[k][0]],
                                             "answer": [{"format": "SQL", "content": [B[k][1]]}]}
                                            for k in e["avaliacao"] if ok("bm:" + k)], key=lambda x: x["id"])},
    }
    return espaco


def gerar():
    PASTA.mkdir(exist_ok=True)
    for k in ESPACOS:
        (PASTA / f"{k}.json").write_text(json.dumps(montar(k), indent=1, ensure_ascii=False), encoding="utf-8")
        e = ESPACOS[k]
        print(f"{k}: {len(e['mvs'])} metric views + {len(e['tabelas'])} tabelas | {len(e['amostras'])} perguntas de exemplo | "
              f"{len(e['exemplos'])} SQL de exemplo | {len(e['avaliacao'])} perguntas de avaliação | instruções {len(INSTR[k])} caracteres")


def validar():
    res = {}
    for k, (_, s) in EXEMPLOS.items():
        res["ex:" + k] = s
    for k, (_, s) in B.items():
        res["bm:" + k] = s
    saida = {}
    for k, s in res.items():
        try:
            estado, erro, linhas = sql_util.executar(s)
        except sql_util.CotaEsgotada as e:
            sys.exit(f"warehouse indisponível (cota diária do Free Edition): {e}")
        ok = estado == "SUCCEEDED" and len(linhas) > 0
        saida[k] = {"ok": ok, "erro": erro[:300], "linhas": len(linhas), "amostra": linhas[:3]}
        print(f"{'OK ' if ok else 'ERRO'} {k:<32} linhas={len(linhas)}" + (f"  {erro[:160]}" if erro else ""), flush=True)
    (PASTA / "validacao.json").write_text(json.dumps(saida, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"RESULTADO: {sum(v['ok'] for v in saida.values())}/{len(saida)} consultas válidas")


def cli(args, corpo=None):
    cmd = ["databricks"] + args + ["--profile", PERFIL, "-o", "json"]
    if corpo is not None:
        cmd += ["--json", json.dumps(corpo)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:600])
    return json.loads(r.stdout or "{}", strict=False)   # o SQL gerado pela Genie vem com quebras de linha cruas


def criar():
    validacao = json.loads((PASTA / "validacao.json").read_text(encoding="utf-8"))
    validos = {k: v["ok"] for k, v in validacao.items()}
    me = cli(["current-user", "me"])["userName"]
    pasta_ws = f"/Workspace/Users/{me}/pos_venda/genie"
    subprocess.run(["databricks", "workspace", "mkdirs", pasta_ws, "--profile", PERFIL], check=True)
    existentes = {s.get("title"): s["space_id"] for s in cli(["genie", "list-spaces"]).get("spaces", [])}
    ids = {}
    for k, e in ESPACOS.items():
        espaco = montar(k, validos)
        corpo = {"warehouse_id": WAREHOUSE, "title": e["titulo"], "description": e["descricao"],
                 "serialized_space": json.dumps(espaco, ensure_ascii=False)}
        if e["titulo"] in existentes:
            sid = existentes[e["titulo"]]
            cli(["genie", "update-space", sid], {k2: v for k2, v in corpo.items() if k2 != "title"} | {"title": e["titulo"]})
            acao = "atualizado"
        else:
            sid = cli(["genie", "create-space"], corpo | {"parent_path": pasta_ws})["space_id"]
            acao = "criado"
        ids[k] = sid
        n_ex = len(espaco["instructions"]["example_question_sqls"])
        n_bm = len(espaco["benchmarks"]["questions"])
        print(f"{k}: {acao} {sid} | {n_ex} SQL de exemplo e {n_bm} perguntas de avaliação válidas")
        subprocess.run(["databricks", "workspace-entity-tag-assignments", "create-tag-assignment", "geniespaces", sid, "aidevkit_project",
                        "--tag-value", "ai-dev-kit", "--profile", PERFIL], capture_output=True)
    (PASTA / "espacos.json").write_text(json.dumps(ids, indent=1), encoding="utf-8")


def avaliar():
    """Pergunta cada item de avaliação à Genie e compara a 1a coluna numérica do resultado com o SQL esperado."""
    ids = json.loads((PASTA / "espacos.json").read_text(encoding="utf-8"))
    validacao = json.loads((PASTA / "validacao.json").read_text(encoding="utf-8"))
    relatorio = []
    so = set(sys.argv[2:])          # opcional: só estas perguntas (chaves de B)
    for k, sid in ids.items():
        for b in ESPACOS[k]["avaliacao"]:
            if not validacao.get("bm:" + b, {}).get("ok") or (so and b not in so):
                continue
            pergunta = B[b][0]
            try:
                conv = cli(["genie", "start-conversation", sid, pergunta, "--no-wait"])
            except RuntimeError as e:
                relatorio.append({"espaco": k, "pergunta": pergunta, "status": f"erro: {e}"[:200]})
                continue
            cid, mid = conv["conversation_id"], conv["message_id"]
            msg, t0 = {}, time.time()
            while time.time() - t0 < 300:
                msg = cli(["genie", "get-message", sid, cid, mid])
                if msg.get("status") in ("COMPLETED", "FAILED", "CANCELLED", "QUERY_RESULT_EXPIRED"):
                    break
                time.sleep(5)
            sql_genie = next((a.get("query", {}).get("query") for a in msg.get("attachments", []) or [] if a.get("query")), None)
            obtido = []
            try:   # compara o resultado INTEIRO (sem depender da ordem das linhas)
                _, _, esperado = sql_util.executar(B[b][1])
                if sql_genie:
                    _, _, obtido = sql_util.executar(sql_genie)
            except sql_util.CotaEsgotada:
                sys.exit("cota esgotada durante a avaliação")
            igual = _mesmos_numeros(esperado, obtido)
            relatorio.append({"espaco": k, "pergunta": pergunta, "status": msg.get("status"), "acertou": igual,
                              "sql_genie": sql_genie, "esperado": esperado[:10], "obtido": obtido[:10]})
            print(f"{'ACERTOU' if igual else 'REVISAR'} [{k}] {pergunta}", flush=True)
    (PASTA / "avaliacao.json").write_text(json.dumps(relatorio, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    ok = sum(1 for r in relatorio if r.get("acertou"))
    print(f"RESULTADO: {ok}/{len(relatorio)} respostas iguais ao esperado")


def _mesmos_numeros(a, b):
    def nums(linhas):
        out = []
        for l in linhas:
            for v in l.values():
                try:
                    out.append(round(float(v), 2))
                except (TypeError, ValueError):
                    pass
        return sorted(out)
    na, nb = nums(a), nums(b)
    return bool(na) and all(x in nb for x in na)


if __name__ == "__main__":
    {"gerar": gerar, "validar": validar, "criar": criar, "avaliar": avaliar}[sys.argv[1] if len(sys.argv) > 1 else "gerar"]()
