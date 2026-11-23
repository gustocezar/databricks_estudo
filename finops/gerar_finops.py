"""Visões de custo e uso (FinOps) no schema pos_venda.finops, com base FOCUS 1.4.

Grupos de visões:
- base FOCUS 1.4 (`focus_custo_uso`): o dataset Cost and Usage da especificação FinOps FOCUS, a partir de
  system.billing.usage e system.billing.list_prices, mais colunas `x_` do projeto (projeto, time, BRL, funcionalidade);
- custo por funcionalidade do Databricks, custo SQL por consulta e custo por projeto;
- uso: painéis, Genie (UI × API), consultas e jobs;
- time de plataforma e time de squad;
- boas práticas de custo (Well-Architected da Databricks, powerbi-analyzer, dbx-adoption-monitor);
- metric view `mv_finops_custo`.

Origem: a base FOCUS adapta `focus/focus_query_1_4.sql` do repositório databricks-solutions/cloud-infra-costs
(commit 70905cf). Diferenças: só `list_prices` (Free Edition), BilledCost = 0 enquanto não houver fatura (a
especificação exige o valor faturado), ResourceId da Genie = espaço, e as colunas `x_`. O custo por consulta segue
o rateio por tempo de execução de databricks-solutions/dbx-adoption-monitor (02_dbsql_cost_per_query.sql).

Não altera nada em `finops.observability` (decisão do dono): só lê o câmbio e o desconto de v_focus_price_config.

Uso:
    python3 finops/gerar_finops.py ativos     # atualiza ativos.json (nomes de painéis, espaços Genie, Lakebase, alertas)
    python3 finops/gerar_finops.py gerar      # escreve finops/finops.sql
    python3 finops/gerar_finops.py aplicar    # cria o schema e as visões (só recria a que mudou)
    python3 finops/gerar_finops.py conferir   # cada visão responde + totais batem com o faturamento
"""
import json
import pathlib
import re
import subprocess
import sys

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(RAIZ / "governanca"))
from sql_util import CotaEsgotada, executar  # noqa: E402

S = "pos_venda.finops"
PERFIL = "dbx-workshop"
JANELA = 30          # dias das visões de boas práticas, top recursos e warehouses

# ------------------------------------------------------------------------------------------------ atribuição
# Ordem: a primeira regra que casar vale. tipo_recurso: tag_projeto (custom_tags['project']), job, alerta (alerta SQL),
# pipeline, app, genie, painel, lakebase, endpoint, warehouse, servico, consulta (texto da consulta SQL). padrao: LIKE.
# tipo_time: squad, plataforma, compartilhado. O que não casar fica "não atribuído".
SQUAD_PV, PLATAFORMA, COMPART = "Squad pós-venda", "Plataforma · engenharia-dados", "Plataforma (compartilhado)"
REGRAS = [
    (10, "tag_projeto", "observabilidade-framework", "observabilidade-framework", PLATAFORMA, "plataforma"),
    (20, "job", "pos_venda%", "pos_venda", SQUAD_PV, "squad"),
    (21, "job", "dqx-studio%", "pos_venda", SQUAD_PV, "squad"),
    (22, "job", "%ligar_dqx_studio%", "pos_venda", SQUAD_PV, "squad"),
    (23, "job", "grant-lakebase-sp", "pos_venda", SQUAD_PV, "squad"),
    (24, "job", "%[Observabilidade]%", "observabilidade-framework", PLATAFORMA, "plataforma"),
    (25, "alerta", "%[Observabilidade]%", "observabilidade-framework", PLATAFORMA, "plataforma"),   # alertas SQL (L79)
    (30, "pipeline", "pos_venda%", "pos_venda", SQUAD_PV, "squad"),
    (31, "pipeline", "%dbx-agentic-psp%", "dbx-agentic-psp", "Squad dbx-agentic-psp", "squad"),
    (40, "app", "dqx-studio", "pos_venda", SQUAD_PV, "squad"),
    (41, "app", "genie-ontology-readiness", "pos_venda", SQUAD_PV, "squad"),
    (42, "app", "dr-silva%", "dr-silva", "Squad dr-silva", "squad"),
    (43, "app", "dbx-community-rj", "dbx-community-rj", "Squad dbx-community-rj", "squad"),
    (44, "app", "central-dado-hub", "central-dado-hub", "Squad central-dado-hub", "squad"),
    (50, "genie", "Pós-venda%", "pos_venda", SQUAD_PV, "squad"),
    (51, "genie", "DQX Studio%", "pos_venda", SQUAD_PV, "squad"),
    (52, "genie", "%Observabilidade%", "observabilidade-framework", PLATAFORMA, "plataforma"),
    (53, "genie", "%FOCUS%", "observabilidade-framework", PLATAFORMA, "plataforma"),
    (54, "genie", "DBX Agentic PSP%", "dbx-agentic-psp", "Squad dbx-agentic-psp", "squad"),
    (60, "painel", "pos_venda%", "pos_venda", SQUAD_PV, "squad"),
    (61, "painel", "%DQX Quality%", "pos_venda", SQUAD_PV, "squad"),
    (62, "painel", "%[Observabilidade]%", "observabilidade-framework", PLATAFORMA, "plataforma"),
    (63, "painel", "%FOCUS%", "observabilidade-framework", PLATAFORMA, "plataforma"),
    (64, "painel", "%Databricks %", "observabilidade-framework", PLATAFORMA, "plataforma"),
    (70, "lakebase", "dqx-studio%", "pos_venda", SQUAD_PV, "squad"),
    (80, "consulta", "pos_venda", "pos_venda", SQUAD_PV, "squad"),
    (81, "consulta", "finops", "observabilidade-framework", PLATAFORMA, "plataforma"),
    (82, "consulta", "system", "observabilidade-framework", PLATAFORMA, "plataforma"),   # monitoramento sobre tabelas de sistema
    (90, "warehouse", "%", "compartilhado", COMPART, "compartilhado"),
    (91, "endpoint", "%", "compartilhado", COMPART, "compartilhado"),
    (92, "servico", "%", "compartilhado", COMPART, "compartilhado"),
]

FUNCIONALIDADE = {
    "SQL": "SQL warehouse (DBSQL)", "JOBS": "Jobs (Lakeflow Jobs)", "DLT": "Pipelines declarativos (Lakeflow)",
    "GENIE": "Genie", "LAKEBASE": "Lakebase (Postgres)", "DATABASE": "Lakebase (Postgres)", "APPS": "Databricks Apps",
    "DEFAULT_STORAGE": "Armazenamento padrão", "PREDICTIVE_OPTIMIZATION": "Otimização preditiva",
    "NETWORKING": "Rede (egress e conectividade)", "MODEL_SERVING": "Model Serving", "AI_GATEWAY": "AI Gateway",
    "AI_FUNCTIONS": "AI Functions", "VECTOR_SEARCH": "Vector Search", "INTERACTIVE": "Computação interativa",
    "ALL_PURPOSE": "Cluster all-purpose", "NOTEBOOKS": "Notebooks serverless",
}
ENDPOINT = ("MODEL_SERVING", "AI_GATEWAY", "AI_FUNCTIONS", "VECTOR_SEARCH")


def lista_sql(itens):
    return ", ".join(f"'{i}'" for i in itens)


def q(s):
    return s.replace("'", "''")


# ------------------------------------------------------------------------------------------------ descrições
FOCUS_DESCR = {
    "AllocatedMethodId": "FOCUS 1.4 (condicional): método de alocação; não disponível nas tabelas de sistema (NULL).",
    "AllocatedMethodDetails": "FOCUS 1.4 (recomendada): detalhes da alocação; não disponível (NULL).",
    "AllocatedResourceId": "FOCUS 1.4 (condicional): recurso que recebeu a alocação; não disponível (NULL).",
    "AllocatedResourceName": "FOCUS 1.4 (condicional): nome do recurso que recebeu a alocação; não disponível (NULL).",
    "AllocatedTags": "FOCUS 1.4 (condicional): tags do recurso alocado; não disponível (NULL).",
    "AvailabilityZone": "FOCUS 1.4 (recomendada): zona de disponibilidade; não disponível (NULL).",
    "BilledCost": "FOCUS 1.4 (obrigatória): custo faturado, em BillingCurrency. 0 no Free Edition, que não emite fatura; a especificação exige o valor faturado, não estimado.",
    "BillingAccountId": "FOCUS 1.4 (obrigatória): conta Databricks (account_id).",
    "BillingAccountName": "FOCUS 1.4 (obrigatória): nome da conta; as tabelas de sistema não trazem, então repete o account_id.",
    "BillingAccountType": "FOCUS 1.4 (condicional): tipo da conta de cobrança; não disponível (NULL).",
    "BillingCurrency": "FOCUS 1.4 (obrigatória): moeda de cobrança (USD, a moeda dos preços de lista).",
    "BillingPeriodEnd": "FOCUS 1.4 (obrigatória): fim exclusivo do período de cobrança (primeiro dia do mês seguinte).",
    "BillingPeriodStart": "FOCUS 1.4 (obrigatória): início do período de cobrança (primeiro dia do mês).",
    "CapacityReservationId": "FOCUS 1.4 (condicional): reserva de capacidade; não se aplica (NULL).",
    "CapacityReservationStatus": "FOCUS 1.4 (condicional): situação da reserva de capacidade; não se aplica (NULL).",
    "ChargeCategory": "FOCUS 1.4 (obrigatória): categoria da cobrança; sempre Usage (consumo).",
    "ChargeClass": "FOCUS 1.4 (obrigatória, aceita nulo): Correction só para correções de período fechado; NULL aqui.",
    "ChargeDescription": "FOCUS 1.4 (obrigatória): descrição da cobrança (o SKU).",
    "ChargeFrequency": "FOCUS 1.4 (recomendada): frequência da cobrança; sempre Usage-Based.",
    "ChargePeriodEnd": "FOCUS 1.4 (obrigatória): fim da janela de consumo (usage_end_time).",
    "ChargePeriodStart": "FOCUS 1.4 (obrigatória): início da janela de consumo (usage_start_time).",
    "CommitmentDiscountCategory": "FOCUS 1.4 (condicional): categoria do desconto por compromisso; não disponível (NULL).",
    "CommitmentDiscountId": "FOCUS 1.4 (condicional): desconto por compromisso; não disponível (NULL).",
    "CommitmentDiscountName": "FOCUS 1.4 (condicional): nome do desconto por compromisso; não disponível (NULL).",
    "CommitmentDiscountQuantity": "FOCUS 1.4 (condicional): quantidade do compromisso; não disponível (NULL).",
    "CommitmentDiscountStatus": "FOCUS 1.4 (condicional): situação do compromisso; não disponível (NULL).",
    "CommitmentDiscountType": "FOCUS 1.4 (condicional): tipo do compromisso; não disponível (NULL).",
    "CommitmentDiscountUnit": "FOCUS 1.4 (condicional): unidade do compromisso; não disponível (NULL).",
    "CommitmentProgramEligibilityDetails": "FOCUS 1.4 (condicional): elegibilidade a programas de compromisso; não disponível (NULL).",
    "ConsumedQuantity": "FOCUS 1.4 (condicional): quantidade consumida, na ConsumedUnit (DBU, DSU, GB).",
    "ConsumedUnit": "FOCUS 1.4 (condicional): unidade consumida (DBU, DSU ou GB).",
    "ContractApplied": "FOCUS 1.4 (condicional): contrato aplicado; não disponível (NULL).",
    "ContractedCost": "FOCUS 1.4 (obrigatória): custo após desconto negociado = ListCost × (1 − desconto global da configuração).",
    "ContractedUnitPrice": "FOCUS 1.4 (condicional): preço unitário após desconto negociado, em USD.",
    "EffectiveCost": "FOCUS 1.4 (obrigatória): custo efetivo amortizado; igual ao ContractedCost (sem descontos por compromisso).",
    "HostProviderName": "FOCUS 1.4 (obrigatória): nuvem que hospeda o recurso (ex.: Amazon Web Services).",
    "InvoiceDetailId": "FOCUS 1.4 (condicional): item da fatura; não disponível (NULL).",
    "InvoiceId": "FOCUS 1.4 (condicional): fatura; não disponível (NULL).",
    "InvoiceIssuerName": "FOCUS 1.4 (obrigatória): emissor da fatura (Databricks).",
    "ListCost": "FOCUS 1.4 (obrigatória): custo a preço de lista em USD = quantidade × preço de lista vigente no consumo. É a medida usada nas visões de custo.",
    "ListUnitPrice": "FOCUS 1.4 (condicional): preço de lista unitário em USD (system.billing.list_prices); NULL quando o SKU não tem preço (ex.: GENIE_FREE_USAGE).",
    "PricingCategory": "FOCUS 1.4 (condicional): categoria de preço; Standard.",
    "PricingCurrency": "FOCUS 1.4 (condicional): moeda do preço (USD).",
    "PricingCurrencyContractedUnitPrice": "FOCUS 1.4 (condicional): preço contratado na moeda do preço.",
    "PricingCurrencyEffectiveCost": "FOCUS 1.4 (condicional): custo efetivo na moeda do preço.",
    "PricingCurrencyListUnitPrice": "FOCUS 1.4 (condicional): preço de lista na moeda do preço.",
    "PricingQuantity": "FOCUS 1.4 (obrigatória): quantidade precificada (igual à consumida).",
    "PricingUnit": "FOCUS 1.4 (obrigatória): unidade de preço (DBU, DSU ou GB).",
    "RegionId": "FOCUS 1.4 (condicional): região do metastore.",
    "RegionName": "FOCUS 1.4 (condicional): nome da região do metastore.",
    "ResourceId": "FOCUS 1.4 (condicional): recurso que gerou o consumo (job, pipeline, warehouse, app, espaço Genie, projeto Lakebase, endpoint) ou o produto.",
    "ResourceName": "FOCUS 1.4 (condicional): nome do recurso; cai no id quando o nome não existe.",
    "ResourceType": "FOCUS 1.4 (condicional): tipo do recurso (Job, SQL Warehouse, Application, Genie Agent...).",
    "ServiceCategory": "FOCUS 1.4 (obrigatória): categoria do serviço, nos valores da especificação (Analytics, Databases, Storage...).",
    "ServiceName": "FOCUS 1.4 (obrigatória): serviço Databricks (billing_origin_product).",
    "ServiceProviderName": "FOCUS 1.4 (obrigatória): provedor do serviço (Databricks).",
    "ServiceSubcategory": "FOCUS 1.4 (recomendada): subcategoria do serviço.",
    "SkuId": "FOCUS 1.4 (condicional): SKU.",
    "SkuMeter": "FOCUS 1.4 (condicional): medidor do SKU (usage_type).",
    "SkuPriceDetails": "FOCUS 1.4 (condicional): características do produto (product_features) em JSON, com prefixo x_.",
    "SkuPriceId": "FOCUS 1.4 (condicional): identificador do preço (o SKU).",
    "SubAccountId": "FOCUS 1.4 (condicional): workspace.",
    "SubAccountName": "FOCUS 1.4 (condicional): nome do workspace.",
    "SubAccountType": "FOCUS 1.4 (condicional): tipo da subconta (Workspace).",
    "Tags": "FOCUS 1.4 (condicional): tags do consumo (custom_tags).",
    "x_DataUso": "Coluna própria: dia do consumo (usage_date).",
    "x_Funcionalidade": "Coluna própria: funcionalidade do Databricks em português (SQL warehouse, Jobs, Genie, Lakebase...).",
    "x_Serverless": "Coluna própria: verdadeiro quando o consumo é serverless (product_features.is_serverless).",
    "x_Photon": "Coluna própria: verdadeiro quando usou Photon (product_features.is_photon).",
    "x_TipoRecurso": "Coluna própria: tipo usado na atribuição (job, pipeline, app, genie, lakebase, endpoint, warehouse, servico).",
    "x_Recurso": "Coluna própria: nome do recurso usado na atribuição.",
    "x_Projeto": "Coluna própria: projeto dono do custo, pela tag project ou pelas regras de finops/gerar_finops.py.",
    "x_Time": "Coluna própria: time dono do custo.",
    "x_TipoTime": "Coluna própria: squad, plataforma, compartilhado ou não atribuído.",
    "x_OrigemAtribuicao": "Coluna própria: como o custo foi atribuído (tag, regra, compartilhado ou sem regra).",
    "x_CanalGenie": "Coluna própria: canal da Genie (UI = pessoas, API = automação e avaliações).",
    "x_ExecucaoJob": "Coluna própria: execução do job (job_run_id).",
    "x_ExecutadoPor": "Coluna própria: identidade que executou o consumo (identity_metadata.run_as).",
    "x_CambioUsdBrl": "Coluna própria: câmbio USD→BRL da configuração (finops.observability.v_focus_price_config).",
    "x_CustoListaBRL": "Coluna própria: ListCost convertido para reais pelo câmbio da configuração.",
    "x_CustoEfetivoBRL": "Coluna própria: EffectiveCost convertido para reais.",
    "x_Plano": "Coluna própria: plano do workspace (Free Edition).",
    "x_SemPreco": "Coluna própria: verdadeiro quando o SKU não tem preço de lista (uso gratuito, ex.: GENIE_FREE_USAGE).",
}

D = {   # descrições das colunas das demais visões (mesmo nome, mesma descrição)
    "moeda_cobranca": "Moeda dos preços de lista (USD).", "cambio_usd_brl": "Câmbio USD→BRL usado nas colunas em reais.",
    "data_cambio": "Data do câmbio.", "desconto_global_pct": "Desconto negociado global, em %, aplicado ao ContractedCost.",
    "modo_preco": "Modo de preço da configuração (LIST = preço de lista).", "plano": "Plano do workspace.",
    "faturado": "Verdadeiro quando há fatura a reconciliar; falso no Free Edition (BilledCost = 0).",
    "origem_config": "De onde vêm o câmbio e o desconto.",
    "ordem": "Prioridade da regra (a menor vence).", "tipo_recurso": "Tipo de recurso a que a regra se aplica.",
    "padrao": "Padrão LIKE comparado com o nome do recurso.", "projeto": "Projeto dono do custo ou do uso.",
    "time": "Time dono do custo ou do uso.", "tipo_time": "squad, plataforma, compartilhado ou não atribuído.",
    "tipo": "Tipo do ativo (painel, genie, lakebase).", "id": "Identificador do ativo.", "nome": "Nome do ativo.",
    "mes": "Primeiro dia do mês.", "dia": "Dia.", "hora": "Hora (início).",
    "categoria_focus": "ServiceCategory da FOCUS.", "subcategoria_focus": "ServiceSubcategory da FOCUS.",
    "produto": "Produto Databricks (billing_origin_product).", "funcionalidade": "Funcionalidade do Databricks em português.",
    "serverless": "Verdadeiro quando serverless.", "unidade": "Unidade de consumo (DBU, DSU, GB).",
    "quantidade": "Quantidade consumida na unidade.", "custo_lista_usd": "Custo a preço de lista, em USD (FOCUS ListCost).",
    "custo_lista_brl": "Custo a preço de lista, em reais.", "custo_efetivo_usd": "Custo efetivo, em USD (FOCUS EffectiveCost).",
    "custo_faturado_usd": "Custo faturado, em USD (FOCUS BilledCost; 0 no Free Edition).",
    "pct_do_mes": "Participação no custo de lista do mês, em %.", "recursos": "Recursos distintos com consumo.",
    "warehouse_id": "SQL warehouse.", "statement_id": "Consulta (statement_id do query.history); NULL na linha de warehouse ocioso.",
    "origem": "De onde veio a consulta (Painel AI/BI, Genie, Alerta SQL, Job, Pipeline, CLI/SDK, App, Power BI, Outro) ou 'Warehouse ocioso'.",
    "situacao": "Situação de execução da consulta.", "duracao_s": "Duração total da consulta, em segundos.",
    "fila_s": "Espera por capacidade e por computação, em segundos.", "peso_ms": "Tempo de trabalho usado no rateio do custo da hora, em ms.",
    "origem_atribuicao": "Como o custo chegou ao projeto (direta, rateio por consulta, compartilhado, tag, regra, sem regra).",
    "dias_com_custo": "Dias com custo no período.",
    "painel_id": "Painel AI/BI.", "painel": "Nome do painel.", "views_publicado": "Aberturas da versão publicada.",
    "views_rascunho": "Aberturas da versão de edição (rascunho).", "consultas_painel": "Consultas executadas pelo painel.",
    "usuarios": "Usuários distintos.", "espaco_id": "Espaço Genie.", "espaco": "Nome do espaço Genie.",
    "canal": "Canal: UI (pessoas) ou API (automação e avaliações).", "perguntas": "Perguntas enviadas à Genie.",
    "leituras_resposta": "Leituras de resposta (polling da API ou abertura na UI).", "aberturas": "Aberturas do espaço.",
    "dbus": "DBUs consumidos.", "execucoes": "Execuções.", "falhas": "Execuções com falha.",
    "taxa_falha_pct": "Execuções com falha sobre o total, em %.", "duracao_p50_s": "Mediana da duração, em segundos.",
    "duracao_p95_s": "Percentil 95 da duração, em segundos.", "fila_media_s": "Espera média na fila, em segundos.",
    "pct_com_fila": "Consultas que esperaram mais de 1 s, em %.", "gb_lidos": "Gigabytes lidos.",
    "job_id": "Job.", "job": "Nome do job.", "sucessos": "Execuções com sucesso.",
    "duracao_media_min": "Duração média da execução, em minutos.", "custo_falhas_usd": "Custo a preço de lista das execuções com falha, em USD.",
    "custo_por_execucao_usd": "Custo de lista médio por execução, em USD.",
    "media_7d_usd": "Média do custo de lista dos 7 dias anteriores, em USD.", "variacao_vs_media_pct": "Variação sobre a média dos 7 dias anteriores, em %.",
    "anomalia": "Verdadeiro quando o dia passa de 1,5 vez a média dos 7 dias anteriores e de US$ 1.",
    "pct_do_total": "Participação no total do período, em %.", "posicao": "Posição no ranking por custo.",
    "recurso": "Nome do recurso.", "warehouse": "Nome do warehouse.", "tipo_warehouse": "Tipo do warehouse.",
    "tamanho": "Tamanho do warehouse.", "min_clusters": "Clusters mínimos.", "max_clusters": "Clusters máximos.",
    "auto_stop_min": "Minutos sem uso até desligar.", "consultas_30d": "Consultas nos últimos 30 dias.",
    "custo_30d_usd": "Custo de lista nos últimos 30 dias, em USD.", "ocioso_pct": "Parte do custo em horas sem consulta, em %.",
    "fila_p95_s": "Percentil 95 da espera na fila, em segundos.",
    "custo_mes_anterior_usd": "Custo de lista do mês anterior, em USD.", "variacao_mensal_pct": "Variação sobre o mês anterior, em %.",
    "pct_do_projeto": "Participação no custo do projeto no mês, em %.",
    "indicador": "Indicador de custo unitário ou de uso.", "custo_unitario_usd": "Custo de lista por unidade, em USD.",
    "valor": "Valor do indicador.",
    "codigo": "Código da prática (WAF CO-xx-yy, powerbi-analyzer SS-xxx, FOCUS ou dbx-adoption-monitor).",
    "pratica": "Boa prática.", "fonte": "De onde vem a prática.", "publico": "Para quem é a prática (plataforma ou squad).",
    "metrica": "O que é medido.", "meta": "Meta da prática.", "leitura": "Como ler o resultado.",
    "recomendacao": "O que fazer quando não atende.",
}


def cols(*nomes, extra=None):
    extra = extra or {}
    return [(n, extra.get(n) or FOCUS_DESCR.get(n) or D[n]) for n in nomes]


# ------------------------------------------------------------------------------------------------ visões
def ativos():
    try:
        return json.loads((AQUI / "ativos.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit("rode antes: python3 finops/gerar_finops.py ativos")


def visoes():
    A = ativos()
    func = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in FUNCIONALIDADE.items())
    regras = ",\n  ".join(f"({o}, '{t}', '{q(p)}', '{q(pr)}', '{q(ti)}', '{tt}')" for o, t, p, pr, ti, tt in REGRAS)
    linhas_ativos = [("painel", i, n) for i, n in A["paineis"].items()] + [("genie", i, n) for i, n in A["genie"].items()] + \
                    [("lakebase", i, n) for i, n in A["lakebase"].items()] + [("alerta", i, n) for i, n in A.get("alertas", {}).items()]
    vals_ativos = ",\n  ".join(f"('{t}', '{i}', '{q(n)}')" for t, i, n in linhas_ativos)
    V = []

    V.append(("config_custo", "Parâmetros de custo do FinOps: moeda, câmbio, desconto e plano. Lê finops.observability.v_focus_price_config (só leitura).",
              cols("moeda_cobranca", "cambio_usd_brl", "data_cambio", "desconto_global_pct", "modo_preco", "plano", "faturado", "origem_config"),
              """SELECT 'USD' AS moeda_cobranca,
  CAST(coalesce(c.usd_to_brl_rate, 5.50) AS DECIMAL(10,4)) AS cambio_usd_brl,
  c.fx_rate_date AS data_cambio,
  CAST(coalesce(c.global_discount_pct, 0) AS DECIMAL(10,4)) AS desconto_global_pct,
  coalesce(c.default_price_mode, 'LIST') AS modo_preco,
  'Free Edition' AS plano,
  false AS faturado,
  'finops.observability.v_focus_price_config (somente leitura)' AS origem_config
FROM (SELECT 1 AS um) d
LEFT JOIN (SELECT * FROM finops.observability.v_focus_price_config ORDER BY fx_rate_date DESC LIMIT 1) c ON true"""))

    V.append(("config_atribuicao", "Regras de atribuição de custo e uso a projeto e time (editar em finops/gerar_finops.py, lista REGRAS). A primeira regra que casar vale.",
              cols("ordem", "tipo_recurso", "padrao", "projeto", "time", "tipo_time"),
              f"""SELECT * FROM VALUES
  {regras}
AS r(ordem, tipo_recurso, padrao, projeto, time, tipo_time)"""))

    V.append(("config_ativos", f"Nomes de painéis, espaços Genie, projetos Lakebase e alertas SQL (foto da API em {A['gerado_em']}, por `gerar_finops.py ativos`).",
              cols("tipo", "id", "nome"),
              f"""SELECT * FROM VALUES
  {vals_ativos}
AS a(tipo, id, nome)"""))

    focus_sql = f"""WITH cfg AS (SELECT * FROM {S}.config_custo),
precos AS (
  SELECT sku_name, usage_unit, cloud, price_start_time,
         coalesce(price_end_time, TIMESTAMP '2999-12-31') AS price_end_time,
         CAST(pricing.default AS DECIMAL(30, 15)) AS preco
  FROM system.billing.list_prices WHERE currency_code = 'USD'),
pipelines AS (
  SELECT pipeline_id, name FROM system.lakeflow.pipelines
  QUALIFY row_number() OVER (PARTITION BY pipeline_id ORDER BY change_time DESC) = 1),
warehouses AS (
  SELECT warehouse_id, warehouse_name FROM system.compute.warehouses
  QUALIFY row_number() OVER (PARTITION BY warehouse_id ORDER BY change_time DESC) = 1),
u AS (
  SELECT u.record_id, u.account_id, u.workspace_id, w.workspace_name, u.sku_name, u.cloud,
    u.usage_start_time, u.usage_end_time, u.usage_date, u.usage_quantity, u.usage_unit, u.usage_type,
    u.custom_tags, u.billing_origin_product, u.product_features,
    u.usage_metadata.job_id AS job_id, u.usage_metadata.job_name AS job_name, u.usage_metadata.job_run_id AS job_run_id,
    u.usage_metadata.dlt_pipeline_id AS dlt_pipeline_id, u.usage_metadata.warehouse_id AS warehouse_id,
    u.usage_metadata.app_id AS app_id, u.usage_metadata.app_name AS app_name,
    u.usage_metadata.endpoint_id AS endpoint_id, u.usage_metadata.endpoint_name AS endpoint_name,
    u.usage_metadata.project_id AS lakebase_project_id, u.usage_metadata.database_instance_id AS database_instance_id,
    u.usage_metadata.genie.agent_id AS genie_space_id, u.usage_metadata.genie.channel AS genie_canal,
    u.usage_metadata.cluster_id AS cluster_id, u.usage_metadata.notebook_id AS notebook_id,
    u.identity_metadata.run_as AS run_as,
    p.preco, pl.name AS pipeline_name, wh.warehouse_name
  FROM system.billing.usage u
  LEFT JOIN precos p ON u.sku_name = p.sku_name AND u.usage_unit = p.usage_unit AND u.cloud = p.cloud
    AND u.usage_end_time > p.price_start_time AND u.usage_end_time <= p.price_end_time
  LEFT JOIN system.access.workspaces_latest w ON u.account_id = w.account_id AND u.workspace_id = w.workspace_id
  LEFT JOIN pipelines pl ON u.usage_metadata.dlt_pipeline_id = pl.pipeline_id
  LEFT JOIN warehouses wh ON u.usage_metadata.warehouse_id = wh.warehouse_id),
r AS (
  SELECT u.*,
    CASE
      WHEN billing_origin_product = 'JOBS' THEN 'job'
      WHEN billing_origin_product = 'DLT' THEN 'pipeline'
      WHEN billing_origin_product = 'APPS' THEN 'app'
      WHEN billing_origin_product = 'GENIE' THEN 'genie'
      WHEN billing_origin_product IN ('LAKEBASE', 'DATABASE') THEN 'lakebase'
      WHEN billing_origin_product IN ({lista_sql(ENDPOINT)}) THEN 'endpoint'
      WHEN billing_origin_product = 'SQL' AND warehouse_id IS NOT NULL THEN 'warehouse'
      ELSE 'servico' END AS tipo_recurso,
    CASE
      WHEN billing_origin_product = 'JOBS' THEN coalesce(job_name, job_id)
      WHEN billing_origin_product = 'DLT' THEN coalesce(pipeline_name, dlt_pipeline_id)
      WHEN billing_origin_product = 'APPS' THEN coalesce(app_name, app_id)
      WHEN billing_origin_product = 'GENIE' THEN coalesce(ga.nome, genie_space_id, 'Genie (sem espaço)')
      WHEN billing_origin_product IN ('LAKEBASE', 'DATABASE') THEN coalesce(la.nome, lakebase_project_id, database_instance_id)
      WHEN billing_origin_product IN ({lista_sql(ENDPOINT)}) THEN coalesce(endpoint_name, endpoint_id)
      WHEN billing_origin_product = 'SQL' THEN coalesce(warehouse_name, warehouse_id)
      ELSE billing_origin_product END AS recurso,
    custom_tags['project'] AS tag_projeto, custom_tags['team'] AS tag_time
  FROM u
  LEFT JOIN {S}.config_ativos ga ON ga.tipo = 'genie' AND ga.id = u.genie_space_id
  LEFT JOIN {S}.config_ativos la ON la.tipo = 'lakebase' AND la.id = u.lakebase_project_id),
a AS (
  SELECT r.record_id, g.projeto, g.time, g.tipo_time,
    CASE WHEN g.tipo_recurso = 'tag_projeto' THEN 'tag' WHEN g.tipo_time = 'compartilhado' THEN 'compartilhado' ELSE 'regra' END AS origem
  FROM r JOIN {S}.config_atribuicao g
    ON (g.tipo_recurso = 'tag_projeto' AND r.tag_projeto LIKE g.padrao)
    OR (g.tipo_recurso = r.tipo_recurso AND r.recurso LIKE g.padrao)
  QUALIFY row_number() OVER (PARTITION BY r.record_id ORDER BY g.ordem) = 1)
SELECT
  CAST(NULL AS STRING) AS AllocatedMethodId,
  CAST(NULL AS STRING) AS AllocatedMethodDetails,
  CAST(NULL AS STRING) AS AllocatedResourceId,
  CAST(NULL AS STRING) AS AllocatedResourceName,
  CAST(NULL AS STRING) AS AllocatedTags,
  CAST(NULL AS STRING) AS AvailabilityZone,
  CAST(CASE WHEN cfg.faturado THEN coalesce(r.usage_quantity * r.preco, 0) * (1 - cfg.desconto_global_pct / 100) ELSE 0 END AS DECIMAL(30, 15)) AS BilledCost,
  r.account_id AS BillingAccountId,
  r.account_id AS BillingAccountName,
  CAST(NULL AS STRING) AS BillingAccountType,
  cfg.moeda_cobranca AS BillingCurrency,
  CAST(date_trunc('MONTH', r.usage_date) + INTERVAL 1 MONTH AS TIMESTAMP) AS BillingPeriodEnd,
  CAST(date_trunc('MONTH', r.usage_date) AS TIMESTAMP) AS BillingPeriodStart,
  CAST(NULL AS STRING) AS CapacityReservationId,
  CAST(NULL AS STRING) AS CapacityReservationStatus,
  'Usage' AS ChargeCategory,
  CAST(NULL AS STRING) AS ChargeClass,
  r.sku_name AS ChargeDescription,
  'Usage-Based' AS ChargeFrequency,
  r.usage_end_time AS ChargePeriodEnd,
  r.usage_start_time AS ChargePeriodStart,
  CAST(NULL AS STRING) AS CommitmentDiscountCategory,
  CAST(NULL AS STRING) AS CommitmentDiscountId,
  CAST(NULL AS STRING) AS CommitmentDiscountName,
  CAST(NULL AS DECIMAL(30, 15)) AS CommitmentDiscountQuantity,
  CAST(NULL AS STRING) AS CommitmentDiscountStatus,
  CAST(NULL AS STRING) AS CommitmentDiscountType,
  CAST(NULL AS STRING) AS CommitmentDiscountUnit,
  CAST(NULL AS STRING) AS CommitmentProgramEligibilityDetails,
  CAST(r.usage_quantity AS DECIMAL(30, 15)) AS ConsumedQuantity,
  r.usage_unit AS ConsumedUnit,
  CAST(NULL AS STRING) AS ContractApplied,
  CAST(coalesce(r.usage_quantity * r.preco, 0) * (1 - cfg.desconto_global_pct / 100) AS DECIMAL(30, 15)) AS ContractedCost,
  CAST(r.preco * (1 - cfg.desconto_global_pct / 100) AS DECIMAL(30, 15)) AS ContractedUnitPrice,
  CAST(coalesce(r.usage_quantity * r.preco, 0) * (1 - cfg.desconto_global_pct / 100) AS DECIMAL(30, 15)) AS EffectiveCost,
  CASE r.cloud WHEN 'AWS' THEN 'Amazon Web Services' WHEN 'AZURE' THEN 'Microsoft Azure' WHEN 'GCP' THEN 'Google Cloud Platform' ELSE r.cloud END AS HostProviderName,
  CAST(NULL AS STRING) AS InvoiceDetailId,
  CAST(NULL AS STRING) AS InvoiceId,
  'Databricks' AS InvoiceIssuerName,
  CAST(coalesce(r.usage_quantity * r.preco, 0) AS DECIMAL(30, 15)) AS ListCost,
  CAST(r.preco AS DECIMAL(30, 15)) AS ListUnitPrice,
  'Standard' AS PricingCategory,
  cfg.moeda_cobranca AS PricingCurrency,
  CAST(r.preco * (1 - cfg.desconto_global_pct / 100) AS DECIMAL(30, 15)) AS PricingCurrencyContractedUnitPrice,
  CAST(coalesce(r.usage_quantity * r.preco, 0) * (1 - cfg.desconto_global_pct / 100) AS DECIMAL(30, 15)) AS PricingCurrencyEffectiveCost,
  CAST(r.preco AS DECIMAL(30, 15)) AS PricingCurrencyListUnitPrice,
  CAST(r.usage_quantity AS DECIMAL(30, 15)) AS PricingQuantity,
  r.usage_unit AS PricingUnit,
  split(current_metastore(), ':')[1] AS RegionId,
  split(current_metastore(), ':')[1] AS RegionName,
  CASE
    WHEN r.billing_origin_product = 'JOBS' THEN coalesce(r.job_id, r.billing_origin_product)
    WHEN r.billing_origin_product = 'DLT' THEN coalesce(r.dlt_pipeline_id, r.billing_origin_product)
    WHEN r.billing_origin_product = 'SQL' AND r.sku_name LIKE '%JOBS_SERVERLESS%' THEN coalesce(r.dlt_pipeline_id, r.billing_origin_product)
    WHEN r.billing_origin_product = 'SQL' THEN coalesce(r.warehouse_id, r.billing_origin_product)
    WHEN r.billing_origin_product = 'APPS' THEN coalesce(r.app_id, r.billing_origin_product)
    WHEN r.billing_origin_product = 'GENIE' THEN coalesce(r.genie_space_id, r.billing_origin_product)
    WHEN r.billing_origin_product IN ('LAKEBASE', 'DATABASE') THEN coalesce(r.lakebase_project_id, r.database_instance_id, r.billing_origin_product)
    WHEN r.billing_origin_product IN ({lista_sql(ENDPOINT)}) THEN coalesce(r.endpoint_id, r.endpoint_name, r.billing_origin_product)
    WHEN r.billing_origin_product IN ('INTERACTIVE', 'NOTEBOOKS') THEN coalesce(r.notebook_id, r.billing_origin_product)
    WHEN r.billing_origin_product = 'ALL_PURPOSE' THEN coalesce(r.cluster_id, r.billing_origin_product)
    ELSE r.billing_origin_product END AS ResourceId,
  r.recurso AS ResourceName,
  CASE r.billing_origin_product
    WHEN 'JOBS' THEN 'Job' WHEN 'DLT' THEN 'Spark Declarative Pipeline' WHEN 'SQL' THEN 'SQL Warehouse'
    WHEN 'APPS' THEN 'Application' WHEN 'GENIE' THEN 'Genie Agent' WHEN 'LAKEBASE' THEN 'Database Project'
    WHEN 'DATABASE' THEN 'Database Instance' WHEN 'MODEL_SERVING' THEN 'Model Serving Endpoint' WHEN 'AI_GATEWAY' THEN 'AI Gateway'
    WHEN 'AI_FUNCTIONS' THEN 'AI Function' WHEN 'VECTOR_SEARCH' THEN 'Vector Search Endpoint' WHEN 'DEFAULT_STORAGE' THEN 'Storage'
    WHEN 'PREDICTIVE_OPTIMIZATION' THEN 'Predictive Optimization' WHEN 'NETWORKING' THEN 'Networking'
    WHEN 'ALL_PURPOSE' THEN 'Cluster' WHEN 'INTERACTIVE' THEN 'Compute' WHEN 'NOTEBOOKS' THEN 'Notebook'
    ELSE coalesce(r.billing_origin_product, 'Other') END AS ResourceType,
  CASE
    WHEN r.billing_origin_product IN ('ALL_PURPOSE', 'INTERACTIVE', 'NOTEBOOKS', 'SHARED_SERVERLESS_COMPUTE') THEN 'Compute'
    WHEN r.billing_origin_product IN ('JOBS', 'DLT') THEN 'Analytics'
    WHEN r.billing_origin_product IN ('MODEL_SERVING', 'VECTOR_SEARCH', 'FOUNDATION_MODEL_TRAINING', 'AGENT_EVALUATION', 'AI_GATEWAY',
                                      'AI_FUNCTIONS', 'AGENT_BRICKS', 'AI_RUNTIME', 'SUPERVISOR_AGENT', 'GENIE', 'FEATURE_STORE') THEN 'AI and Machine Learning'
    WHEN r.billing_origin_product IN ('DEFAULT_STORAGE') THEN 'Storage'
    WHEN r.billing_origin_product IN ('DATABASE', 'LAKEBASE', 'ONLINE_TABLES', 'SQL', 'LAKEHOUSE_REAL_TIME') THEN 'Databases'
    WHEN r.billing_origin_product IN ('LAKEHOUSE_MONITORING', 'DATA_QUALITY_MONITORING', 'PREDICTIVE_OPTIMIZATION', 'CLEAN_ROOM',
                                      'DATA_SHARING', 'DISASTER_RECOVERY') THEN 'Management and Governance'
    WHEN r.billing_origin_product IN ('FINE_GRAINED_ACCESS_CONTROL', 'DATA_CLASSIFICATION') THEN 'Security'
    WHEN r.billing_origin_product IN ('NETWORKING') THEN 'Networking'
    WHEN r.billing_origin_product IN ('LAKEFLOW_CONNECT') THEN 'Integration'
    WHEN r.billing_origin_product IN ('BASE_ENVIRONMENTS') THEN 'Developer Tools'
    WHEN r.billing_origin_product IN ('APPS') THEN 'Web'
    ELSE 'Other' END AS ServiceCategory,
  r.billing_origin_product AS ServiceName,
  'Databricks' AS ServiceProviderName,
  CASE
    WHEN r.billing_origin_product IN ('JOBS', 'DLT') THEN 'Data Processing'
    WHEN r.billing_origin_product IN ('MODEL_SERVING', 'AI_GATEWAY', 'AI_FUNCTIONS') THEN 'AI Platforms'
    WHEN r.billing_origin_product IN ('GENIE', 'AGENT_BRICKS', 'SUPERVISOR_AGENT', 'AI_RUNTIME', 'FOUNDATION_MODEL_TRAINING') THEN 'Generative AI'
    WHEN r.billing_origin_product = 'DEFAULT_STORAGE' THEN 'Object Storage'
    WHEN r.billing_origin_product IN ('SQL', 'LAKEHOUSE_REAL_TIME') THEN 'Data Warehouses'
    WHEN r.billing_origin_product IN ('DATABASE', 'LAKEBASE', 'ONLINE_TABLES') THEN 'Relational Databases'
    WHEN r.billing_origin_product = 'PREDICTIVE_OPTIMIZATION' THEN 'Cost Management'
    WHEN r.billing_origin_product = 'NETWORKING' THEN 'Network Connectivity'
    WHEN r.billing_origin_product = 'APPS' THEN 'Application Platforms'
    WHEN r.billing_origin_product IN ('ALL_PURPOSE') THEN 'Virtual Machines'
    WHEN r.billing_origin_product IN ('INTERACTIVE', 'NOTEBOOKS', 'SHARED_SERVERLESS_COMPUTE') THEN 'Serverless Compute'
    ELSE 'Other (Other)' END AS ServiceSubcategory,
  r.sku_name AS SkuId,
  r.usage_type AS SkuMeter,
  to_json(map_from_entries(filter(transform(map_entries(from_json(to_json(r.product_features), 'map<string, string>')),
    e -> named_struct('key', concat('x_', e.key), 'value', e.value)), kv -> kv.value IS NOT NULL))) AS SkuPriceDetails,
  r.sku_name AS SkuPriceId,
  r.workspace_id AS SubAccountId,
  r.workspace_name AS SubAccountName,
  'Workspace' AS SubAccountType,
  r.custom_tags AS Tags,
  r.usage_date AS x_DataUso,
  CASE r.billing_origin_product {func} ELSE initcap(replace(r.billing_origin_product, '_', ' ')) END AS x_Funcionalidade,
  coalesce(r.product_features.is_serverless, false) AS x_Serverless,
  coalesce(r.product_features.is_photon, false) AS x_Photon,
  r.tipo_recurso AS x_TipoRecurso,
  r.recurso AS x_Recurso,
  coalesce(a.projeto, r.tag_projeto, 'não atribuído') AS x_Projeto,
  coalesce(a.time, r.tag_time, 'Não atribuído') AS x_Time,
  coalesce(a.tipo_time, CASE WHEN r.tag_projeto IS NOT NULL THEN 'squad' END, 'não atribuído') AS x_TipoTime,
  coalesce(a.origem, CASE WHEN r.tag_projeto IS NOT NULL THEN 'tag' END, 'sem regra') AS x_OrigemAtribuicao,
  CASE r.genie_canal WHEN 'UI' THEN 'UI (pessoas)' WHEN 'API' THEN 'API (automação)' ELSE r.genie_canal END AS x_CanalGenie,
  r.job_run_id AS x_ExecucaoJob,
  r.run_as AS x_ExecutadoPor,
  cfg.cambio_usd_brl AS x_CambioUsdBrl,
  CAST(coalesce(r.usage_quantity * r.preco, 0) * cfg.cambio_usd_brl AS DECIMAL(30, 6)) AS x_CustoListaBRL,
  CAST(coalesce(r.usage_quantity * r.preco, 0) * (1 - cfg.desconto_global_pct / 100) * cfg.cambio_usd_brl AS DECIMAL(30, 6)) AS x_CustoEfetivoBRL,
  cfg.plano AS x_Plano,
  r.preco IS NULL AS x_SemPreco
FROM r
CROSS JOIN cfg
LEFT JOIN a ON a.record_id = r.record_id"""
    colunas_focus = list(FOCUS_DESCR)
    V.append(("focus_custo_uso", "Dataset FOCUS 1.4 Cost and Usage do workspace (system.billing.usage × list_prices), com colunas x_ de funcionalidade, projeto, time e reais. Base de todas as visões de custo. Adaptado de databricks-solutions/cloud-infra-costs.",
              cols(*colunas_focus), focus_sql))

    V.append(("custo_sql_por_consulta", "Custo do SQL warehouse rateado por consulta: o custo de cada hora é dividido pelas consultas da hora, na proporção do tempo de trabalho (padrão do dbx-adoption-monitor). Horas sem consulta ficam como 'Warehouse ocioso'.",
              cols("hora", "warehouse_id", "statement_id", "origem", "projeto", "time", "tipo_time", "situacao", "duracao_s", "fila_s", "peso_ms", "gb_lidos",
                   "custo_lista_usd", "custo_efetivo_usd", "custo_lista_brl"),
              f"""WITH horas AS (
  SELECT ResourceId AS warehouse_id, date_trunc('HOUR', ChargePeriodStart) AS hora,
    sum(ListCost) AS custo_lista_usd, sum(EffectiveCost) AS custo_efetivo_usd, sum(x_CustoListaBRL) AS custo_lista_brl
  FROM {S}.focus_custo_uso WHERE x_TipoRecurso = 'warehouse' GROUP BY ALL),
jobs AS (
  SELECT job_id, max_by(name, ts) AS name FROM (
    SELECT job_id, name, change_time AS ts FROM system.lakeflow.jobs
    UNION ALL
    SELECT usage_metadata.job_id, usage_metadata.job_name, usage_end_time FROM system.billing.usage
    WHERE usage_metadata.job_id IS NOT NULL AND usage_metadata.job_name IS NOT NULL) GROUP BY job_id),
pipelines AS (SELECT pipeline_id, name FROM system.lakeflow.pipelines QUALIFY row_number() OVER (PARTITION BY pipeline_id ORDER BY change_time DESC) = 1),
c0 AS (
  SELECT h.*, ga.nome AS nome_genie, pa.nome AS nome_painel, al.nome AS nome_alerta, j.name AS nome_job, p.name AS nome_pipeline,
    CASE
      WHEN lower(h.statement_text) LIKE '%pos_venda.finops.%' THEN 'finops'
      WHEN lower(h.statement_text) LIKE '%pos_venda.%' THEN 'pos_venda'
      WHEN lower(h.statement_text) LIKE '%finops.%' THEN 'finops'
      WHEN lower(h.statement_text) LIKE '%system.%' THEN 'system'
      ELSE 'outro' END AS marca_texto
  FROM system.query.history h
  LEFT JOIN {S}.config_ativos ga ON ga.tipo = 'genie' AND ga.id = h.query_source.genie_space_id
  LEFT JOIN {S}.config_ativos pa ON pa.tipo = 'painel' AND pa.id = h.query_source.dashboard_id
  LEFT JOIN {S}.config_ativos al ON al.tipo = 'alerta' AND al.id = h.query_source.alert_id
  LEFT JOIN jobs j ON j.job_id = h.query_source.job_info.job_id
  LEFT JOIN pipelines p ON p.pipeline_id = h.query_source.pipeline_info.pipeline_id
  WHERE h.compute.warehouse_id IS NOT NULL),
c AS (
  SELECT h.statement_id, h.compute.warehouse_id AS warehouse_id, date_trunc('HOUR', h.start_time) AS hora, h.execution_status AS situacao,
    h.total_duration_ms / 1000.0 AS duracao_s,
    (coalesce(h.waiting_at_capacity_duration_ms, 0) + coalesce(h.waiting_for_compute_duration_ms, 0)) / 1000.0 AS fila_s,
    greatest(coalesce(h.total_task_duration_ms, 0) + coalesce(h.result_fetch_duration_ms, 0) + coalesce(h.compilation_duration_ms, 0), 1) AS peso_ms,
    coalesce(h.read_bytes, 0) / 1e9 AS gb_lidos,
    CASE
      WHEN h.query_source.genie_space_id IS NOT NULL THEN 'Genie'
      WHEN h.query_source.dashboard_id IS NOT NULL OR h.query_source.legacy_dashboard_id IS NOT NULL THEN 'Painel AI/BI'
      WHEN h.query_source.alert_id IS NOT NULL THEN 'Alerta SQL'
      WHEN h.query_source.job_info.job_id IS NOT NULL THEN 'Job'
      WHEN h.query_source.pipeline_info.pipeline_id IS NOT NULL THEN 'Pipeline'
      WHEN h.client_application ILIKE '%power bi%' THEN 'Power BI'
      WHEN h.client_application IN ('Databricks CLI', 'Databricks SQL Connector for Python') THEN 'CLI/SDK'
      WHEN h.client_application ILIKE '%genie-ontology-readiness%' THEN 'App'
      WHEN h.client_application ILIKE '%catalog explorer%' THEN 'Catalog Explorer'
      ELSE 'Outro' END AS origem,
    -- a origem com nome conhecido decide; sem nome (painel fora da foto, alerta novo), decide o texto da consulta
    CASE
      WHEN h.nome_genie IS NOT NULL THEN 'genie'
      WHEN h.nome_painel IS NOT NULL THEN 'painel'
      WHEN h.nome_alerta IS NOT NULL THEN 'alerta'
      WHEN h.nome_job IS NOT NULL THEN 'job'
      WHEN h.nome_pipeline IS NOT NULL THEN 'pipeline'
      ELSE 'consulta' END AS tipo_recurso,
    coalesce(h.nome_genie, h.nome_painel, h.nome_alerta, h.nome_job, h.nome_pipeline, h.marca_texto) AS recurso
  FROM c0 h),
ca AS (
  SELECT c.*, g.projeto, g.time, g.tipo_time FROM c
  LEFT JOIN {S}.config_atribuicao g ON g.tipo_recurso = c.tipo_recurso AND c.recurso LIKE g.padrao
  QUALIFY row_number() OVER (PARTITION BY c.statement_id ORDER BY g.ordem) = 1)
SELECT ca.hora, ca.warehouse_id, ca.statement_id, ca.origem,
  coalesce(ca.projeto, 'não atribuído') AS projeto, coalesce(ca.time, 'Não atribuído') AS time, coalesce(ca.tipo_time, 'não atribuído') AS tipo_time,
  ca.situacao, ca.duracao_s, ca.fila_s, ca.peso_ms, ca.gb_lidos,
  coalesce(hr.custo_lista_usd * ca.peso_ms / sum(ca.peso_ms) OVER (PARTITION BY ca.warehouse_id, ca.hora), 0) AS custo_lista_usd,
  coalesce(hr.custo_efetivo_usd * ca.peso_ms / sum(ca.peso_ms) OVER (PARTITION BY ca.warehouse_id, ca.hora), 0) AS custo_efetivo_usd,
  coalesce(hr.custo_lista_brl * ca.peso_ms / sum(ca.peso_ms) OVER (PARTITION BY ca.warehouse_id, ca.hora), 0) AS custo_lista_brl
FROM ca LEFT JOIN horas hr ON hr.warehouse_id = ca.warehouse_id AND hr.hora = ca.hora
UNION ALL
SELECT hr.hora, hr.warehouse_id, CAST(NULL AS STRING), 'Warehouse ocioso', 'compartilhado', '{COMPART}', 'compartilhado',
  CAST(NULL AS STRING), CAST(NULL AS DOUBLE), CAST(NULL AS DOUBLE), CAST(NULL AS BIGINT), CAST(NULL AS DOUBLE),
  hr.custo_lista_usd, hr.custo_efetivo_usd, hr.custo_lista_brl
FROM horas hr LEFT ANTI JOIN (SELECT DISTINCT warehouse_id, hora FROM c) x ON x.warehouse_id = hr.warehouse_id AND x.hora = hr.hora"""))

    V.append(("custo_por_funcionalidade", "Custo por funcionalidade do Databricks por mês, com a categoria FOCUS, serverless e a participação no mês.",
              cols("mes", "categoria_focus", "subcategoria_focus", "produto", "funcionalidade", "serverless", "unidade", "quantidade",
                   "custo_lista_usd", "custo_lista_brl", "custo_efetivo_usd", "custo_faturado_usd", "pct_do_mes", "recursos"),
              f"""SELECT CAST(BillingPeriodStart AS DATE) AS mes, ServiceCategory AS categoria_focus, ServiceSubcategory AS subcategoria_focus,
  ServiceName AS produto, x_Funcionalidade AS funcionalidade, x_Serverless AS serverless, PricingUnit AS unidade,
  sum(ConsumedQuantity) AS quantidade, sum(ListCost) AS custo_lista_usd, sum(x_CustoListaBRL) AS custo_lista_brl,
  sum(EffectiveCost) AS custo_efetivo_usd, sum(BilledCost) AS custo_faturado_usd,
  round(100 * sum(ListCost) / nullif(sum(sum(ListCost)) OVER (PARTITION BY CAST(BillingPeriodStart AS DATE)), 0), 2) AS pct_do_mes,
  count(DISTINCT ResourceId) AS recursos
FROM {S}.focus_custo_uso GROUP BY ALL"""))

    V.append(("custo_por_projeto_diario", "Custo por dia, projeto, time e funcionalidade. O SQL warehouse entra rateado por consulta; o resto vem direto da base FOCUS. A soma bate com focus_custo_uso.",
              cols("dia", "projeto", "time", "tipo_time", "funcionalidade", "origem_atribuicao", "custo_lista_usd", "custo_efetivo_usd", "custo_lista_brl"),
              f"""SELECT x_DataUso AS dia, x_Projeto AS projeto, x_Time AS time, x_TipoTime AS tipo_time, x_Funcionalidade AS funcionalidade,
  x_OrigemAtribuicao AS origem_atribuicao, sum(ListCost) AS custo_lista_usd, sum(EffectiveCost) AS custo_efetivo_usd, sum(x_CustoListaBRL) AS custo_lista_brl
FROM {S}.focus_custo_uso WHERE x_TipoRecurso <> 'warehouse' GROUP BY ALL
UNION ALL
SELECT CAST(hora AS DATE), projeto, time, tipo_time, '{FUNCIONALIDADE['SQL']}',
  CASE WHEN statement_id IS NULL THEN 'compartilhado' ELSE 'rateio por consulta' END,
  sum(custo_lista_usd), sum(custo_efetivo_usd), sum(custo_lista_brl)
FROM {S}.custo_sql_por_consulta GROUP BY ALL"""))

    # ---------------------------------------------------------------------------------------------- uso
    V.append(("uso_paineis_diario", "Uso dos painéis AI/BI por dia (system.access.audit): aberturas da versão publicada e do rascunho, consultas e usuários distintos. Padrão do dbx-adoption-monitor.",
              cols("dia", "painel_id", "painel", "projeto", "time", "tipo_time", "views_publicado", "views_rascunho", "consultas_painel", "usuarios"),
              f"""WITH e AS (
  SELECT event_date AS dia, request_params.dashboard_id AS painel_id,
    count_if(action_name = 'getPublishedDashboard') AS views_publicado,
    count_if(action_name = 'getDashboard') AS views_rascunho,
    count_if(action_name = 'executeQuery') AS consultas_painel,
    count(DISTINCT user_identity.email) AS usuarios
  FROM system.access.audit
  WHERE service_name = 'dashboards' AND action_name IN ('getPublishedDashboard', 'getDashboard', 'executeQuery')
    AND request_params.dashboard_id IS NOT NULL
  GROUP BY ALL),
n AS (SELECT e.*, coalesce(a.nome, e.painel_id) AS painel FROM e LEFT JOIN {S}.config_ativos a ON a.tipo = 'painel' AND a.id = e.painel_id),
t AS (
  SELECT n.*, g.projeto, g.time, g.tipo_time FROM n
  LEFT JOIN {S}.config_atribuicao g ON g.tipo_recurso = 'painel' AND n.painel LIKE g.padrao
  QUALIFY row_number() OVER (PARTITION BY n.dia, n.painel_id ORDER BY g.ordem) = 1)
SELECT dia, painel_id, painel, coalesce(projeto, 'não atribuído') AS projeto, coalesce(time, 'Não atribuído') AS time,
  coalesce(tipo_time, 'não atribuído') AS tipo_time, views_publicado, views_rascunho, consultas_painel, usuarios
FROM t"""))

    V.append(("uso_genie_diario", "Uso da Genie por dia, espaço e canal: perguntas, leituras, aberturas e usuários (audit) com os DBUs e o custo (base FOCUS). Separa pessoas (UI) de automação e avaliações (API), como recomenda o dbx-adoption-monitor.",
              cols("dia", "espaco_id", "espaco", "projeto", "time", "tipo_time", "canal", "perguntas", "leituras_resposta", "aberturas", "usuarios",
                   "dbus", "custo_lista_usd"),
              f"""WITH ev AS (
  SELECT event_date AS dia, request_params.space_id AS espaco_id,
    CASE WHEN user_agent ILIKE '%mozilla%' THEN 'UI (pessoas)' ELSE 'API (automação)' END AS canal,
    count_if(action_name IN ('genieStartConversationMessage', 'genieCreateConversationMessage')) AS perguntas,
    count_if(action_name = 'genieGetConversationMessage') AS leituras_resposta,
    count_if(action_name IN ('getSpace', 'genieGetSpace')) AS aberturas,
    count(DISTINCT user_identity.email) AS usuarios
  FROM system.access.audit
  WHERE service_name = 'aibiGenie' AND request_params.space_id IS NOT NULL
  GROUP BY ALL),
co AS (
  SELECT x_DataUso AS dia, ResourceId AS espaco_id, x_CanalGenie AS canal, sum(ConsumedQuantity) AS dbus, sum(ListCost) AS custo_lista_usd
  FROM {S}.focus_custo_uso WHERE x_TipoRecurso = 'genie' AND ResourceId <> 'GENIE' GROUP BY ALL),
j AS (
  SELECT coalesce(ev.dia, co.dia) AS dia, coalesce(ev.espaco_id, co.espaco_id) AS espaco_id, coalesce(ev.canal, co.canal) AS canal,
    coalesce(ev.perguntas, 0) AS perguntas, coalesce(ev.leituras_resposta, 0) AS leituras_resposta, coalesce(ev.aberturas, 0) AS aberturas,
    coalesce(ev.usuarios, 0) AS usuarios, coalesce(co.dbus, 0) AS dbus, coalesce(co.custo_lista_usd, 0) AS custo_lista_usd
  FROM ev FULL OUTER JOIN co ON ev.dia = co.dia AND ev.espaco_id = co.espaco_id AND ev.canal = co.canal),
n AS (SELECT j.*, coalesce(a.nome, j.espaco_id) AS espaco FROM j LEFT JOIN {S}.config_ativos a ON a.tipo = 'genie' AND a.id = j.espaco_id),
t AS (
  SELECT n.*, g.projeto, g.time, g.tipo_time FROM n
  LEFT JOIN {S}.config_atribuicao g ON g.tipo_recurso = 'genie' AND n.espaco LIKE g.padrao
  QUALIFY row_number() OVER (PARTITION BY n.dia, n.espaco_id, n.canal ORDER BY g.ordem) = 1)
SELECT dia, espaco_id, espaco, coalesce(projeto, 'não atribuído') AS projeto, coalesce(time, 'Não atribuído') AS time,
  coalesce(tipo_time, 'não atribuído') AS tipo_time, canal, perguntas, leituras_resposta, aberturas, usuarios, dbus, custo_lista_usd
FROM t"""))

    V.append(("uso_consultas_diario", "Consultas SQL por dia, origem e projeto: execuções, falhas, duração, fila e custo rateado (a partir de custo_sql_por_consulta).",
              cols("dia", "origem", "projeto", "time", "tipo_time", "execucoes", "falhas", "duracao_p50_s", "duracao_p95_s", "fila_media_s",
                   "pct_com_fila", "gb_lidos", "custo_lista_usd"),
              f"""SELECT CAST(hora AS DATE) AS dia, origem, projeto, time, tipo_time,
  count(*) AS execucoes, count_if(situacao = 'FAILED') AS falhas,
  round(percentile_approx(duracao_s, 0.5), 2) AS duracao_p50_s, round(percentile_approx(duracao_s, 0.95), 2) AS duracao_p95_s,
  round(avg(fila_s), 2) AS fila_media_s, round(100 * avg(CASE WHEN fila_s > 1 THEN 1 ELSE 0 END), 2) AS pct_com_fila,
  round(sum(gb_lidos), 3) AS gb_lidos, sum(custo_lista_usd) AS custo_lista_usd
FROM {S}.custo_sql_por_consulta WHERE statement_id IS NOT NULL GROUP BY ALL"""))

    V.append(("uso_jobs_diario", "Execuções de job por dia: sucessos, falhas, duração e custo (system.lakeflow.job_run_timeline × base FOCUS), com o custo das execuções com falha.",
              cols("dia", "job_id", "job", "projeto", "time", "tipo_time", "execucoes", "sucessos", "falhas", "duracao_media_min",
                   "custo_lista_usd", "custo_falhas_usd", "custo_por_execucao_usd"),
              f"""WITH execs AS (
  SELECT job_id, run_id, min(period_start_time) AS inicio, max(period_end_time) AS fim,
    max_by(result_state, period_end_time) AS resultado
  FROM system.lakeflow.job_run_timeline GROUP BY job_id, run_id),
jobs AS (SELECT job_id, name FROM system.lakeflow.jobs QUALIFY row_number() OVER (PARTITION BY job_id ORDER BY change_time DESC) = 1),
custo AS (SELECT x_ExecucaoJob AS run_id, sum(ListCost) AS custo_lista_usd FROM {S}.focus_custo_uso WHERE x_TipoRecurso = 'job' AND x_ExecucaoJob IS NOT NULL GROUP BY ALL),
e AS (
  SELECT CAST(x.inicio AS DATE) AS dia, x.job_id, x.run_id, coalesce(j.name, x.job_id) AS job, x.resultado,
    (unix_timestamp(x.fim) - unix_timestamp(x.inicio)) / 60.0 AS minutos, coalesce(c.custo_lista_usd, 0) AS custo
  FROM execs x LEFT JOIN jobs j ON j.job_id = x.job_id LEFT JOIN custo c ON c.run_id = x.run_id),
t AS (
  SELECT e.*, g.projeto, g.time, g.tipo_time FROM e
  LEFT JOIN {S}.config_atribuicao g ON g.tipo_recurso = 'job' AND e.job LIKE g.padrao
  QUALIFY row_number() OVER (PARTITION BY e.job_id, e.run_id ORDER BY g.ordem) = 1)
SELECT dia, job_id, job, coalesce(projeto, 'não atribuído') AS projeto, coalesce(time, 'Não atribuído') AS time,
  coalesce(tipo_time, 'não atribuído') AS tipo_time,
  count(*) AS execucoes, count_if(resultado = 'SUCCEEDED') AS sucessos,
  count_if(resultado IN ('FAILED', 'ERROR', 'TIMED_OUT', 'INTERNAL_ERROR')) AS falhas,
  round(avg(minutos), 2) AS duracao_media_min, sum(custo) AS custo_lista_usd,
  sum(CASE WHEN resultado IN ('FAILED', 'ERROR', 'TIMED_OUT', 'INTERNAL_ERROR') THEN custo ELSE 0 END) AS custo_falhas_usd,
  sum(custo) / count(*) AS custo_por_execucao_usd
FROM t GROUP BY ALL"""))

    # ---------------------------------------------------------------------------------------------- plataforma
    V.append(("plataforma_custo_diario", "Time de plataforma: custo diário por funcionalidade, com a média dos 7 dias anteriores e a marcação de anomalia.",
              cols("dia", "funcionalidade", "custo_lista_usd", "custo_lista_brl", "media_7d_usd", "variacao_vs_media_pct", "anomalia"),
              f"""WITH d AS (
  SELECT x_DataUso AS dia, x_Funcionalidade AS funcionalidade, sum(ListCost) AS custo_lista_usd, sum(x_CustoListaBRL) AS custo_lista_brl
  FROM {S}.focus_custo_uso GROUP BY ALL),
m AS (
  SELECT d.*, avg(custo_lista_usd) OVER (PARTITION BY funcionalidade ORDER BY dia ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING) AS media_7d_usd
  FROM d)
SELECT dia, funcionalidade, custo_lista_usd, custo_lista_brl, media_7d_usd,
  round(100 * (custo_lista_usd - media_7d_usd) / nullif(media_7d_usd, 0), 1) AS variacao_vs_media_pct,
  coalesce(custo_lista_usd > 1.5 * media_7d_usd AND custo_lista_usd > 1, false) AS anomalia
FROM m"""))

    V.append(("plataforma_atribuicao_mensal", "Time de plataforma: quanto do custo de cada mês tem dono (tag, regra), é compartilhado ou não tem regra. Mede a prática WAF CO-03-01 (tags para atribuição).",
              cols("mes", "origem_atribuicao", "tipo_time", "custo_lista_usd", "pct_do_mes", "recursos"),
              f"""SELECT CAST(BillingPeriodStart AS DATE) AS mes, x_OrigemAtribuicao AS origem_atribuicao, x_TipoTime AS tipo_time,
  sum(ListCost) AS custo_lista_usd,
  round(100 * sum(ListCost) / nullif(sum(sum(ListCost)) OVER (PARTITION BY CAST(BillingPeriodStart AS DATE)), 0), 2) AS pct_do_mes,
  count(DISTINCT ResourceId) AS recursos
FROM {S}.focus_custo_uso GROUP BY ALL"""))

    V.append(("plataforma_top_recursos", f"Time de plataforma: recursos que mais custaram nos últimos {JANELA} dias, com projeto e time. O SQL warehouse aparece como compartilhado; o rateio dele por consulta está em custo_por_projeto_diario.",
              cols("posicao", "tipo_recurso", "recurso", "funcionalidade", "projeto", "time", "tipo_time", "custo_lista_usd", "custo_lista_brl", "pct_do_total", "dias_com_custo"),
              f"""WITH r AS (
  SELECT x_TipoRecurso AS tipo_recurso, x_Recurso AS recurso, x_Funcionalidade AS funcionalidade, x_Projeto AS projeto, x_Time AS time,
    x_TipoTime AS tipo_time, sum(ListCost) AS custo_lista_usd, sum(x_CustoListaBRL) AS custo_lista_brl, count(DISTINCT x_DataUso) AS dias_com_custo
  FROM {S}.focus_custo_uso WHERE x_DataUso >= current_date() - INTERVAL {JANELA} DAYS GROUP BY ALL)
SELECT row_number() OVER (ORDER BY custo_lista_usd DESC) AS posicao, tipo_recurso, recurso, funcionalidade, projeto, time, tipo_time,
  custo_lista_usd, custo_lista_brl, round(100 * custo_lista_usd / nullif(sum(custo_lista_usd) OVER (), 0), 2) AS pct_do_total, dias_com_custo
FROM r"""))

    V.append(("plataforma_warehouses", f"Time de plataforma: configuração atual de cada SQL warehouse com custo, consultas, fila e ociosidade dos últimos {JANELA} dias (práticas WAF CO-02-02 e powerbi-analyzer SS-005).",
              cols("warehouse_id", "warehouse", "tipo_warehouse", "tamanho", "min_clusters", "max_clusters", "auto_stop_min", "consultas_30d",
                   "custo_30d_usd", "ocioso_pct", "fila_p95_s", "pct_com_fila"),
              f"""WITH w AS (
  SELECT warehouse_id, warehouse_name, warehouse_type, warehouse_size, min_clusters, max_clusters, auto_stop_minutes
  FROM system.compute.warehouses WHERE delete_time IS NULL
  QUALIFY row_number() OVER (PARTITION BY warehouse_id ORDER BY change_time DESC) = 1),
c AS (
  SELECT warehouse_id, count(statement_id) AS consultas_30d, sum(custo_lista_usd) AS custo_30d_usd,
    round(100 * sum(CASE WHEN statement_id IS NULL THEN custo_lista_usd ELSE 0 END) / nullif(sum(custo_lista_usd), 0), 2) AS ocioso_pct,
    round(percentile_approx(fila_s, 0.95), 2) AS fila_p95_s,
    round(100 * avg(CASE WHEN statement_id IS NULL THEN NULL WHEN fila_s > 1 THEN 1 ELSE 0 END), 2) AS pct_com_fila
  FROM {S}.custo_sql_por_consulta WHERE hora >= current_date() - INTERVAL {JANELA} DAYS GROUP BY warehouse_id)
SELECT w.warehouse_id, w.warehouse_name AS warehouse, w.warehouse_type AS tipo_warehouse, w.warehouse_size AS tamanho,
  w.min_clusters, w.max_clusters, w.auto_stop_minutes AS auto_stop_min,
  coalesce(c.consultas_30d, 0) AS consultas_30d, coalesce(c.custo_30d_usd, 0) AS custo_30d_usd, c.ocioso_pct, c.fila_p95_s, c.pct_com_fila
FROM w LEFT JOIN c ON c.warehouse_id = w.warehouse_id"""))

    # ---------------------------------------------------------------------------------------------- squad
    V.append(("squad_custo_mensal", "Time de squad: custo mensal de cada projeto por funcionalidade, participação no projeto e variação sobre o mês anterior.",
              cols("mes", "projeto", "time", "funcionalidade", "custo_lista_usd", "custo_lista_brl", "pct_do_projeto", "custo_mes_anterior_usd", "variacao_mensal_pct"),
              f"""WITH m AS (
  SELECT CAST(date_trunc('MONTH', dia) AS DATE) AS mes, projeto, time, funcionalidade,
    sum(custo_lista_usd) AS custo_lista_usd, sum(custo_lista_brl) AS custo_lista_brl
  FROM {S}.custo_por_projeto_diario WHERE tipo_time = 'squad' GROUP BY ALL),
a AS (
  SELECT m.*, lag(custo_lista_usd) OVER (PARTITION BY projeto, funcionalidade ORDER BY mes) AS custo_mes_anterior_usd FROM m)
SELECT mes, projeto, time, funcionalidade, custo_lista_usd, custo_lista_brl,
  round(100 * custo_lista_usd / nullif(sum(custo_lista_usd) OVER (PARTITION BY mes, projeto), 0), 2) AS pct_do_projeto,
  custo_mes_anterior_usd, round(100 * (custo_lista_usd - custo_mes_anterior_usd) / nullif(custo_mes_anterior_usd, 0), 1) AS variacao_mensal_pct
FROM a"""))

    V.append(("squad_custo_unitario", "Time de squad: custo unitário por mês e projeto (por execução de job, consulta SQL, visualização de painel, pergunta à Genie e dia de app).",
              cols("mes", "projeto", "indicador", "custo_lista_usd", "quantidade", "unidade", "custo_unitario_usd"),
              f"""WITH j AS (
  SELECT CAST(date_trunc('MONTH', dia) AS DATE) AS mes, projeto, sum(custo_lista_usd) AS custo, sum(execucoes) AS qtd
  FROM {S}.uso_jobs_diario WHERE tipo_time = 'squad' GROUP BY ALL),
q AS (
  SELECT CAST(date_trunc('MONTH', dia) AS DATE) AS mes, projeto, sum(custo_lista_usd) AS custo, sum(execucoes) AS qtd
  FROM {S}.uso_consultas_diario WHERE tipo_time = 'squad' GROUP BY ALL),
pc AS (
  SELECT CAST(date_trunc('MONTH', dia) AS DATE) AS mes, projeto, sum(custo_lista_usd) AS custo
  FROM {S}.uso_consultas_diario WHERE tipo_time = 'squad' AND origem = 'Painel AI/BI' GROUP BY ALL),
pv AS (
  SELECT CAST(date_trunc('MONTH', dia) AS DATE) AS mes, projeto, sum(views_publicado + views_rascunho) AS qtd
  FROM {S}.uso_paineis_diario WHERE tipo_time = 'squad' GROUP BY ALL),
g AS (
  SELECT CAST(date_trunc('MONTH', dia) AS DATE) AS mes, projeto, sum(custo_lista_usd) AS custo, sum(perguntas) AS qtd
  FROM {S}.uso_genie_diario WHERE tipo_time = 'squad' GROUP BY ALL),
ap AS (
  SELECT CAST(date_trunc('MONTH', dia) AS DATE) AS mes, projeto, sum(custo_lista_usd) AS custo, count(DISTINCT dia) AS qtd
  FROM {S}.custo_por_projeto_diario WHERE tipo_time = 'squad' AND funcionalidade = '{FUNCIONALIDADE['APPS']}' GROUP BY ALL)
SELECT mes, projeto, 'Execução de job' AS indicador, custo AS custo_lista_usd, qtd AS quantidade, 'execuções' AS unidade, custo / nullif(qtd, 0) AS custo_unitario_usd FROM j
UNION ALL SELECT mes, projeto, 'Consulta SQL', custo, qtd, 'consultas', custo / nullif(qtd, 0) FROM q
UNION ALL SELECT coalesce(pc.mes, pv.mes), coalesce(pc.projeto, pv.projeto), 'Visualização de painel', coalesce(pc.custo, 0), coalesce(pv.qtd, 0),
  'visualizações', coalesce(pc.custo, 0) / nullif(pv.qtd, 0) FROM pc FULL OUTER JOIN pv ON pc.mes = pv.mes AND pc.projeto = pv.projeto
UNION ALL SELECT mes, projeto, 'Pergunta à Genie', custo, qtd, 'perguntas', custo / nullif(qtd, 0) FROM g
UNION ALL SELECT mes, projeto, 'Dia de app ativo', custo, qtd, 'dias', custo / nullif(qtd, 0) FROM ap"""))

    V.append(("squad_uso_diario", "Time de squad: uso diário dos ativos de cada projeto em formato longo (painéis, Genie por canal, consultas, execuções de job).",
              cols("dia", "projeto", "time", "indicador", "valor"),
              f"""SELECT dia, projeto, time, 'Visualizações de painel' AS indicador, CAST(sum(views_publicado + views_rascunho) AS DOUBLE) AS valor
FROM {S}.uso_paineis_diario WHERE tipo_time = 'squad' GROUP BY ALL
UNION ALL SELECT dia, projeto, time, concat('Perguntas à Genie · ', canal), CAST(sum(perguntas) AS DOUBLE) FROM {S}.uso_genie_diario WHERE tipo_time = 'squad' GROUP BY ALL
UNION ALL SELECT dia, projeto, time, 'Usuários da Genie (UI)', CAST(sum(usuarios) AS DOUBLE) FROM {S}.uso_genie_diario WHERE tipo_time = 'squad' AND canal = 'UI (pessoas)' GROUP BY ALL
UNION ALL SELECT dia, projeto, time, 'Consultas SQL', CAST(sum(execucoes) AS DOUBLE) FROM {S}.uso_consultas_diario WHERE tipo_time = 'squad' GROUP BY ALL
UNION ALL SELECT dia, projeto, time, 'Execuções de job', CAST(sum(execucoes) AS DOUBLE) FROM {S}.uso_jobs_diario WHERE tipo_time = 'squad' GROUP BY ALL
UNION ALL SELECT dia, projeto, time, 'Falhas de job', CAST(sum(falhas) AS DOUBLE) FROM {S}.uso_jobs_diario WHERE tipo_time = 'squad' GROUP BY ALL"""))

    # ---------------------------------------------------------------------------------------------- boas práticas
    J = f"current_date() - INTERVAL {JANELA} DAYS"
    V.append(("boas_praticas_custo", f"Boas práticas de custo medidas nos últimos {JANELA} dias: pilar de custo do Well-Architected da Databricks (databricks-waf), powerbi-analyzer, dbx-adoption-monitor e FOCUS. Uma linha por prática, com meta e situação.",
              cols("codigo", "pratica", "fonte", "publico", "metrica", "valor", "meta", "situacao", "leitura", "recomendacao"),
              f"""WITH f AS (SELECT * FROM {S}.focus_custo_uso WHERE x_DataUso >= {J}),
computo AS (SELECT * FROM f WHERE ServiceName IN ('SQL', 'JOBS', 'DLT', 'ALL_PURPOSE', 'INTERACTIVE', 'NOTEBOOKS', 'MODEL_SERVING', 'APPS')),
k AS (
  SELECT
    100 * sum(CASE WHEN x_Serverless THEN ListCost ELSE 0 END) / nullif(sum(ListCost), 0) AS pct_serverless,
    100 * sum(CASE WHEN ServiceName IN ('ALL_PURPOSE', 'INTERACTIVE') THEN ListCost ELSE 0 END) / nullif(sum(ListCost), 0) AS pct_all_purpose
  FROM computo),
t AS (
  SELECT
    100 * sum(CASE WHEN size(Tags) > 0 THEN ListCost ELSE 0 END) / nullif(sum(ListCost), 0) AS pct_tag,
    100 * sum(CASE WHEN x_OrigemAtribuicao IN ('tag', 'regra') THEN ListCost ELSE 0 END) / nullif(sum(ListCost), 0) AS pct_dono,
    100 * sum(CASE WHEN x_TipoTime = 'não atribuído' THEN ListCost ELSE 0 END) / nullif(sum(ListCost), 0) AS pct_sem_dono,
    100 * count_if(x_SemPreco AND ServiceName <> 'GENIE') / nullif(count(*), 0) AS pct_sem_preco
  FROM f),
b AS (
  SELECT 100 * sum(CASE WHEN u.usage_metadata.budget_policy_id IS NOT NULL THEN u.usage_quantity ELSE 0 END) / nullif(sum(u.usage_quantity), 0) AS pct_budget
  FROM system.billing.usage u WHERE u.usage_date >= {J} AND u.product_features.is_serverless),
w AS (SELECT count(*) AS total, count_if(auto_stop_min <= 10 AND auto_stop_min > 0) AS ok FROM {S}.plataforma_warehouses),
wq AS (SELECT max(ocioso_pct) AS ocioso_pct, max(pct_com_fila) AS pct_com_fila FROM {S}.plataforma_warehouses),
an AS (SELECT count(DISTINCT dia) AS dias FROM {S}.plataforma_custo_diario WHERE anomalia AND dia >= {J}),
st AS (
  SELECT sum(CASE WHEN x_DataUso >= {J} THEN ConsumedQuantity ELSE 0 END) AS atual,
         sum(CASE WHEN x_DataUso < {J} AND x_DataUso >= current_date() - INTERVAL {2 * JANELA} DAYS THEN ConsumedQuantity ELSE 0 END) AS anterior
  FROM {S}.focus_custo_uso WHERE ServiceName = 'DEFAULT_STORAGE'),
po AS (SELECT coalesce(sum(ConsumedQuantity), 0) AS dbus FROM f WHERE ServiceName = 'PREDICTIVE_OPTIMIZATION'),
jf AS (SELECT 100 * sum(custo_falhas_usd) / nullif(sum(custo_lista_usd), 0) AS pct_falhas FROM {S}.uso_jobs_diario WHERE dia >= {J}),
gn AS (SELECT 100 * sum(CASE WHEN canal = 'API (automação)' THEN perguntas ELSE 0 END) / nullif(sum(perguntas), 0) AS pct_api FROM {S}.uso_genie_diario WHERE dia >= {J}),
pn AS (SELECT 100 * sum(views_rascunho) / nullif(sum(views_publicado + views_rascunho), 0) AS pct_rascunho FROM {S}.uso_paineis_diario WHERE dia >= {J}),
linhas AS (
  SELECT 'CO-01-06' AS codigo, 'Usar serviços serverless' AS pratica, 'Well-Architected Databricks (databricks-waf)' AS fonte, 'plataforma' AS publico,
    '% do custo de computação em serverless' AS metrica, round(k.pct_serverless, 1) AS valor, '>= 90%' AS meta, k.pct_serverless >= 90 AS ok,
    'Serverless dispensa dimensionar e desligar clusters e cobra só o uso.' AS leitura, 'Migrar jobs e consultas de clusters clássicos para serverless.' AS recomendacao FROM k
  UNION ALL SELECT 'CO-01-02', 'Usar computação de job, não all-purpose', 'Well-Architected Databricks (databricks-waf)', 'plataforma',
    '% do custo de computação em clusters all-purpose ou interativos', round(k.pct_all_purpose, 1), '<= 10%', k.pct_all_purpose <= 10,
    'Cluster all-purpose custa mais por DBU que job compute e costuma ficar ligado à toa.', 'Rodar cargas agendadas como jobs; deixar all-purpose para exploração.' FROM k
  UNION ALL SELECT 'CO-02-02', 'Desligar automaticamente o que não está em uso', 'Well-Architected Databricks (databricks-waf)', 'plataforma',
    'Warehouses com auto stop de até 10 minutos', CAST(w.ok AS DOUBLE), concat(CAST(w.total AS STRING), ' de ', CAST(w.total AS STRING)), w.ok = w.total,
    'Warehouse ligado sem consulta custa como se estivesse trabalhando.', 'Reduzir auto_stop_minutes para 10 ou menos.' FROM w
  UNION ALL SELECT 'CO-03-01', 'Usar tags para atribuir custo', 'Well-Architected Databricks (databricks-waf)', 'plataforma',
    '% do custo com tag de projeto ou time', round(t.pct_tag, 1), '>= 80%', t.pct_tag >= 80,
    'Sem tag, o custo só tem dono por regra de nome (finops/gerar_finops.py), que quebra quando o nome muda.', 'Pôr as tags project e team nos jobs, pipelines, apps e warehouses (ou usar budget policies serverless).' FROM t
  UNION ALL SELECT 'CO-03-01b', 'Todo custo com dono', 'FOCUS (alocação) e este projeto', 'plataforma',
    '% do custo sem projeto (nem tag, nem regra, nem compartilhado)', round(t.pct_sem_dono, 1), '<= 10%', t.pct_sem_dono <= 10,
    'Custo sem dono não entra em nenhum showback de squad.', 'Criar regra em REGRAS ou tag no recurso; recursos já removidos ficam aqui.' FROM t
  UNION ALL SELECT 'CO-03-02', 'Orçamento e políticas de orçamento', 'Well-Architected Databricks (databricks-waf)', 'plataforma',
    '% do consumo serverless com budget policy', round(b.pct_budget, 1), '>= 80%', coalesce(b.pct_budget, 0) >= 80,
    'Budget policy marca o consumo serverless com o dono e permite alertas por orçamento.', 'Criar budget policies por squad e exigir nos usuários.' FROM b
  UNION ALL SELECT 'CO-03-03', 'Monitorar custos contra o esperado', 'Well-Architected Databricks (databricks-waf)', 'plataforma',
    'Dias com anomalia (custo > 1,5 × média de 7 dias)', CAST(an.dias AS DOUBLE), 'revisar cada dia', true,
    'Atende por existir monitoramento; o número é a fila de dias a investigar em plataforma_custo_diario.', 'Investigar os dias marcados e ajustar a origem do pico.' FROM an
  UNION ALL SELECT 'CO-03-05', 'Monitorar volume e crescimento do armazenamento', 'Well-Architected Databricks (databricks-waf)', 'plataforma',
    concat('Crescimento do armazenamento (DSU) sobre os ', '{JANELA}', ' dias anteriores, em %'), round(100 * (st.atual - st.anterior) / nullif(st.anterior, 0), 1), '<= 20%',
    coalesce(100 * (st.atual - st.anterior) / nullif(st.anterior, 0), 0) <= 20,
    'Armazenamento cresce em silêncio; tabelas temporárias e histórico longo inflam a conta.', 'Rever tabelas grandes sem uso e a retenção do histórico Delta.' FROM st
  UNION ALL SELECT 'CO-03-06', 'VACUUM e retenção do histórico Delta', 'Well-Architected Databricks (databricks-waf)', 'plataforma',
    'DBUs de otimização preditiva no período (VACUUM e OPTIMIZE automáticos)', round(po.dbus, 2), '> 0', po.dbus > 0,
    'Com a otimização preditiva ativa, o Databricks roda VACUUM e OPTIMIZE sozinho.', 'Ativar a otimização preditiva no catálogo.' FROM po
  UNION ALL SELECT 'SS-005', 'Fila do warehouse sob controle', 'powerbi-analyzer (cheat sheet Power BI on Databricks)', 'plataforma',
    '% das consultas que esperaram mais de 1 s', wq.pct_com_fila, '<= 10%', coalesce(wq.pct_com_fila, 0) <= 10,
    'Fila alta indica warehouse pequeno ou sem escala para a concorrência.', 'Aumentar max_clusters ou o tamanho; no Free Edition o warehouse é fixo.' FROM wq
  UNION ALL SELECT 'WH-OCIOSO', 'Pouco custo de warehouse ocioso', 'dbx-adoption-monitor (custo por consulta)', 'plataforma',
    '% do custo do warehouse em horas sem consulta', wq.ocioso_pct, '<= 30%', coalesce(wq.ocioso_pct, 0) <= 30,
    'Hora paga sem consulta é desperdício; o rateio por consulta mostra quanto.', 'Reduzir o auto stop e concentrar cargas em janelas.' FROM wq
  UNION ALL SELECT 'JOB-FALHA', 'Pouco custo em execuções com falha', 'Este projeto (lição de operação)', 'squad',
    '% do custo de jobs em execuções que falharam', round(jf.pct_falhas, 1), '<= 5%', coalesce(jf.pct_falhas, 0) <= 5,
    'Execução que falha cobra e não entrega.', 'Corrigir as falhas recorrentes em uso_jobs_diario.' FROM jf
  UNION ALL SELECT 'GENIE-CANAL', 'Separar uso humano da Genie de automação', 'dbx-adoption-monitor', 'squad',
    '% das perguntas à Genie vindas da API (automação e avaliações)', round(gn.pct_api, 1), 'medir', true,
    'Avaliações automáticas inflam o uso; adoção real é o canal UI.', 'Ler adoção pelo canal UI (pessoas) em uso_genie_diario.' FROM gn
  UNION ALL SELECT 'PAINEL-PUBLICADO', 'Consumo pelo painel publicado', 'dbx-adoption-monitor', 'squad',
    '% das aberturas no rascunho (edição) em vez do publicado', round(pn.pct_rascunho, 1), '<= 30%', coalesce(pn.pct_rascunho, 0) <= 30,
    'Aberturas no rascunho são edição; consumo de negócio é o publicado.', 'Compartilhar o link publicado com o negócio.' FROM pn
  UNION ALL SELECT 'FOCUS-PRECO', 'Todo consumo com preço de lista', 'FOCUS 1.4 (ListCost)', 'plataforma',
    '% das linhas pagas sem preço de lista', round(t.pct_sem_preco, 2), '0%', coalesce(t.pct_sem_preco, 0) = 0,
    'Linha sem preço some do custo; GENIE_FREE_USAGE é gratuito e fica fora da conta.', 'Conferir SKUs novos em system.billing.list_prices.' FROM t)
SELECT codigo, pratica, fonte, publico, metrica, valor, meta,
  CASE WHEN valor IS NULL THEN 'sem dado' WHEN ok THEN 'atende' ELSE 'atenção' END AS situacao, leitura, recomendacao
FROM linhas"""))
    return V


MV = f"""CREATE OR REPLACE VIEW {S}.mv_finops_custo
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: {S}.focus_custo_uso
comment: "Custo do workspace no padrão FOCUS 1.4. Use Custo de lista (USD ou BRL) para comparar: no Free Edition o custo faturado é 0. Quantidade consumida mistura unidades (DBU, DSU, GB): filtre a unidade antes de somar."
dimensions:
  - name: Mês
    expr: "CAST(BillingPeriodStart AS DATE)"
    comment: "Primeiro dia do mês do consumo."
  - name: Dia
    expr: x_DataUso
    comment: "Dia do consumo."
  - name: Funcionalidade
    expr: x_Funcionalidade
    comment: "Funcionalidade do Databricks (SQL warehouse, Jobs, Genie, Lakebase, Apps...)."
  - name: Categoria FOCUS
    expr: ServiceCategory
    comment: "Categoria de serviço da especificação FOCUS."
  - name: Produto
    expr: ServiceName
    comment: "Produto Databricks (billing_origin_product)."
  - name: Projeto
    expr: x_Projeto
    comment: "Projeto dono do custo (tag ou regra de atribuição)."
  - name: Time
    expr: x_Time
    comment: "Time dono do custo."
  - name: Tipo de time
    expr: x_TipoTime
    comment: "squad, plataforma, compartilhado ou não atribuído."
  - name: Origem da atribuição
    expr: x_OrigemAtribuicao
    comment: "tag, regra, compartilhado ou sem regra."
  - name: Serverless
    expr: x_Serverless
    comment: "Verdadeiro quando o consumo é serverless."
  - name: Unidade
    expr: PricingUnit
    comment: "Unidade de consumo (DBU, DSU, GB)."
  - name: Recurso
    expr: x_Recurso
    comment: "Nome do recurso que gerou o consumo."
measures:
  - name: Custo de lista (USD)
    expr: SUM(ListCost)
    comment: "Custo a preço de lista em dólares (FOCUS ListCost)."
  - name: Custo de lista (BRL)
    expr: SUM(x_CustoListaBRL)
    comment: "Custo a preço de lista em reais, pelo câmbio da configuração."
  - name: Custo efetivo (USD)
    expr: SUM(EffectiveCost)
    comment: "Custo após descontos (FOCUS EffectiveCost)."
  - name: Custo faturado (USD)
    expr: SUM(BilledCost)
    comment: "Custo faturado (FOCUS BilledCost); 0 no Free Edition."
  - name: Quantidade consumida
    expr: SUM(ConsumedQuantity)
    comment: "Quantidade consumida; filtre uma Unidade antes de somar."
  - name: Recursos
    expr: COUNT(DISTINCT ResourceId)
    comment: "Recursos distintos com consumo."
$$"""


def ddl(nome, comentario, colunas, consulta):
    lista = ",\n  ".join(f"{c} COMMENT '{q(d)}'" for c, d in colunas)
    return f"CREATE OR REPLACE VIEW {S}.{nome} (\n  {lista}\n)\nCOMMENT '{q(comentario)}'\nAS {consulta}"


def norm(t):
    return re.sub(r"\s+", " ", t or "").strip()


def sql(s, exigir=True):
    estado, erro, linhas = executar(s)
    if exigir and estado != "SUCCEEDED":
        raise RuntimeError(f"{s[:120]}... -> {estado}: {erro[:400]}")
    return linhas


def cmd_ativos():
    def cli(*args):
        r = subprocess.run(["databricks", *args, "--profile", PERFIL, "-o", "json"], capture_output=True, text=True)
        return json.loads(r.stdout or "[]")
    paineis = {d["dashboard_id"]: d.get("display_name", "") for d in cli("lakeview", "list")}
    genie = {s["space_id"]: s.get("title", "") for s in (cli("genie", "list-spaces") or {}).get("spaces", [])}
    lakebase = {p.get("uid"): (p.get("name") or "").replace("projects/", "") for p in cli("postgres", "list-projects")}
    al = cli("alerts-v2", "list-alerts")
    al = al if isinstance(al, list) else (al or {}).get("alerts", [])
    alertas = {a["id"]: re.sub(r"^\[dev [^\]]+\]\s*", "", a.get("display_name", "")) for a in al}   # sem o usuário do bundle
    import datetime
    d = {"gerado_em": datetime.date.today().isoformat(), "paineis": paineis, "genie": genie, "lakebase": lakebase, "alertas": alertas}
    (AQUI / "ativos.json").write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"ativos.json: {len(paineis)} painéis, {len(genie)} espaços Genie, {len(lakebase)} projetos Lakebase, {len(alertas)} alertas SQL")


def cmd_gerar():
    V = visoes()
    partes = [f"CREATE SCHEMA IF NOT EXISTS {S} COMMENT 'Visões FinOps (FOCUS 1.4): custo e uso do workspace, por funcionalidade, projeto e time. Gerado por finops/gerar_finops.py.'"]
    partes += [ddl(*v) for v in V] + [MV]
    (AQUI / "finops.sql").write_text(";\n\n".join(partes) + ";\n", encoding="utf-8")
    print(f"finops/finops.sql: schema + {len(V)} visões + 1 metric view")
    return V


def cmd_aplicar():
    V = cmd_gerar()
    sql(f"CREATE SCHEMA IF NOT EXISTS {S} COMMENT 'Visões FinOps (FOCUS 1.4): custo e uso do workspace, por funcionalidade, projeto e time. Gerado por finops/gerar_finops.py.'")
    atuais = {r["table_name"]: norm(r["view_definition"]) for r in
              sql("SELECT table_name, view_definition FROM pos_venda.information_schema.views WHERE table_schema = 'finops'")}
    for nome, comentario, colunas, consulta in V:
        if atuais.get(nome) == norm(consulta):
            sql(f"COMMENT ON TABLE {S}.{nome} IS '{q(comentario)}'")     # mantém a descrição em dia sem recriar
            print(f"igual     {nome}")
            continue
        sql(ddl(nome, comentario, colunas, consulta))
        print(f"{'recriada' if nome in atuais else 'criada  '}  {nome}")
    sql(MV)
    print("aplicada  mv_finops_custo")


def cmd_conferir():
    V = visoes()
    erros = 0
    print("== cada visão responde")
    for nome, *_ in V + [("mv_finops_custo",)]:
        consulta = (f"SELECT MEASURE(`Custo de lista (USD)`) AS n FROM {S}.{nome}" if nome.startswith("mv_")
                    else f"SELECT count(*) AS n FROM {S}.{nome}")
        try:
            n = sql(consulta)[0]["n"]
            print(f"  ok    {nome:30} {n}")
        except RuntimeError as e:
            erros += 1
            print(f"  ERRO  {nome:30} {str(e)[-200:]}")
    print("== totais")
    r = sql(f"""WITH base AS (
  SELECT count(*) AS linhas, sum(u.usage_quantity * p.preco) AS custo FROM system.billing.usage u
  LEFT JOIN (SELECT sku_name, usage_unit, cloud, price_start_time, coalesce(price_end_time, TIMESTAMP '2999-12-31') AS price_end_time,
             CAST(pricing.default AS DECIMAL(30, 15)) AS preco FROM system.billing.list_prices WHERE currency_code = 'USD') p
    ON u.sku_name = p.sku_name AND u.usage_unit = p.usage_unit AND u.cloud = p.cloud
   AND u.usage_end_time > p.price_start_time AND u.usage_end_time <= p.price_end_time)
SELECT (SELECT linhas FROM base) AS linhas_billing, (SELECT count(*) FROM {S}.focus_custo_uso) AS linhas_focus,
  (SELECT custo FROM base) AS custo_billing, (SELECT sum(ListCost) FROM {S}.focus_custo_uso) AS custo_focus,
  (SELECT sum(custo_lista_usd) FROM {S}.custo_por_funcionalidade) AS custo_funcionalidade,
  (SELECT sum(custo_lista_usd) FROM {S}.custo_por_projeto_diario) AS custo_projeto,
  (SELECT sum(ListCost) FROM {S}.focus_custo_uso WHERE x_TipoRecurso = 'warehouse') AS custo_sql_focus,
  (SELECT sum(custo_lista_usd) FROM {S}.custo_sql_por_consulta) AS custo_sql_rateado,
  (SELECT count(*) FROM {S}.focus_custo_uso WHERE ServiceCategory NOT IN ('AI and Machine Learning', 'Analytics', 'Business Applications', 'Compute',
     'Databases', 'Developer Tools', 'Identity', 'Integration', 'Internet of Things', 'Management and Governance', 'Media', 'Migration', 'Mobile',
     'Multicloud', 'Networking', 'Security', 'Storage', 'Web', 'Other')) AS categoria_fora_da_focus,
  (SELECT count(*) FROM {S}.focus_custo_uso WHERE BilledCost IS NULL OR EffectiveCost IS NULL OR ListCost IS NULL OR ContractedCost IS NULL
     OR ChargeCategory IS NULL OR ServiceName IS NULL OR ChargePeriodStart IS NULL OR BillingCurrency IS NULL) AS obrigatorias_nulas""")[0]
    f = {k: (float(v) if v is not None else None) for k, v in r.items()}
    def igual(a, b, tol=1e-6):
        return a is not None and b is not None and abs(a - b) <= tol * max(1, abs(a))
    checks = [
        ("linhas da base FOCUS = linhas do billing", f["linhas_focus"] == f["linhas_billing"], f"{f['linhas_focus']:.0f} = {f['linhas_billing']:.0f}"),
        ("custo FOCUS = uso × preço de lista", igual(f["custo_focus"], f["custo_billing"]), f"{f['custo_focus']:.4f} = {f['custo_billing']:.4f}"),
        ("custo por funcionalidade = FOCUS", igual(f["custo_funcionalidade"], f["custo_focus"]), f"{f['custo_funcionalidade']:.4f}"),
        ("custo por projeto (com rateio SQL) = FOCUS", igual(f["custo_projeto"], f["custo_focus"]), f"{f['custo_projeto']:.4f}"),
        ("SQL rateado por consulta = SQL da FOCUS", igual(f["custo_sql_rateado"], f["custo_sql_focus"]), f"{f['custo_sql_rateado']:.4f} = {f['custo_sql_focus']:.4f}"),
        ("ServiceCategory só com valores da FOCUS", f["categoria_fora_da_focus"] == 0, f"{f['categoria_fora_da_focus']:.0f} linhas fora"),
        ("colunas obrigatórias sem nulo", f["obrigatorias_nulas"] == 0, f"{f['obrigatorias_nulas']:.0f} linhas com nulo"),
    ]
    for nome, ok, det in checks:
        erros += not ok
        print(f"  {'ok  ' if ok else 'ERRO'}  {nome:46} {det}")
    (AQUI / "conferencia.json").write_text(json.dumps({"totais": f, "checks": [{"check": n, "ok": bool(o), "detalhe": d} for n, o, d in checks]},
                                                      ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("conferência:", "ok" if not erros else f"{erros} problema(s)")
    return erros


if __name__ == "__main__":
    acao = sys.argv[1] if len(sys.argv) > 1 else "gerar"
    try:
        {"ativos": cmd_ativos, "gerar": cmd_gerar, "aplicar": cmd_aplicar}.get(acao, lambda: None)()
        if acao == "conferir":
            sys.exit(1 if cmd_conferir() else 0)
        if acao not in ("ativos", "gerar", "aplicar", "conferir"):
            sys.exit(__doc__)
    except CotaEsgotada as e:
        sys.exit(f"warehouse indisponível (cota diária do Free Edition): {e}")
