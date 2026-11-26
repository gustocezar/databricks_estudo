"""Modelo de entidade e relacionamento (ER) e linhagem de cada base do pos_venda, gerado do Unity Catalog.

  python3 governanca/modelo_dados.py gerar     # lê colunas, PK/FK e linhagem; escreve docs/modelo_dados/*.md e modelo_dados.json
  python3 governanca/modelo_dados.py conferir  # toda tabela numa base, toda FK do UC no modelo, chaves e linhagem conferidas
  python3 governanca/modelo_dados.py aplicar   # publica as chaves em pos_venda.conformidade.chaves_declaradas (lida pelo job diário)

Fontes:
  - PK e FK declaradas no Unity Catalog (information_schema): o star schema da gold e a PK do catálogo de regras;
  - chaves e relacionamentos lógicos declarados abaixo (CHAVES, RELACOES), para as bases sem constraint;
  - relacionamentos da ontologia (pos_venda.ontologia.relacoes), escritos pelo negócio;
  - linhagem real de tabela para tabela (system.access.table_lineage, últimos 90 dias).
O `gerar` confere que toda coluna citada em CHAVES e RELACOES existe; nome errado para o gerador.
A saída também alimenta as Wikis (aplicar_semantica.py: seções "Chave e relacionamentos" e "Linhagem").
"""
from __future__ import annotations

import collections
import json
import pathlib
import re
import sys

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(AQUI))
from sql_util import executar  # noqa: E402

CAT = "pos_venda"
DOCS = RAIZ / "docs" / "modelo_dados"
SAIDA_JSON = AQUI / "modelo_dados.json"
INTERNO = re.compile(r"^(__materialization_|event_log_)")

# base -> (schemas, papel, o que é)
BASES = {
    "origem": (["landing", "fonte"], "principal", "Chegada dos dados: o arquivo único simulado (landing) e o cadastro de apólices do sistema de origem (fonte)."),
    "bronze": (["bronze"], "principal", "Registro fiel do que a origem enviou, um evento por linha, append-only (P06)."),
    "silver": (["silver"], "principal", "Eventos aptos, histórico SCD2 e foto atual de cada pendência; o que a barreira reprovou vai para a quarentena (P09)."),
    "gold": (["gold"], "principal", "Star schema: a fato diária de pendências e as dimensões conformadas, com PK e FK declaradas no Unity Catalog (P05, P07)."),
    "ontologia": (["ontologia"], "principal", "Entidades de negócio sem identificador pessoal, catálogo de conceitos e metric views (P17, P18)."),
    "regras": (["regras"], "principal", "Funções de cálculo, catálogo de regras de qualidade com vigência, triagem e retroalimentação (P20, P41)."),
    "dq": (["dq"], "principal", "Janelas de avaliação do DQX Studio e visões do painel de qualidade (P11, P12)."),
    "bi": (["bi"], "principal", "Extratos para o Power BI, com paridade com o painel do Databricks (P23)."),
    "dqx_codigo": (["dqx_codigo"], "apoio", "Resultado do DQX como código (trilha A): válidos, quarentena e métricas por regra e versão (P38, P41)."),
    "conformidade": (["conformidade"], "apoio", "Conformidade dos dados e do workspace: regras, achados, histórico e sonda das views (P35 a P37)."),
    "finops": (["finops"], "apoio", "Custo e uso no padrão FOCUS, por projeto, funcionalidade e squad (P30 a P34)."),
    "sustentacao": (["sustentacao"], "apoio", "Tempo de execução por job, tarefa e pipeline, linha de base, desvios, SLA e volume (P40)."),
    "legado": (["bronze_sql", "silver_sql", "gold_sql", "bronze_ldp", "silver_ldp", "gold_ldp"], "legado",
               "Primeira versão do medalhão (notebooks SQL e Lakeflow), mantida para comparação; o fluxo diário usa bronze, silver e gold."),
}

# chave lógica (para tabelas sem PK no UC): tabela -> colunas que identificam a linha; "nota" quando não é única
CHAVES = {
    "landing.pagamentos_pendentes_one_table": (["pendencia_id", "data_extracao"], "foto diária da origem; pode repetir"),
    "fonte.apolices": (["numero_apolice"], None),
    "bronze.pagamentos_pendentes_eventos": (["pendencia_id", "data_extracao", "tipo_evento"], "não única: 10.277 repetidas no ensaio de 24/11"),
    "silver.pendencia_evento": (["pendencia_id", "data_extracao", "tipo_evento"], "não única: a origem reenvia eventos idênticos; duplicata é aviso (dq_qualidade_diaria.eventos_duplicados)"),
    "silver.pendencia_evento_quarentena": (["pendencia_id", "data_extracao", "tipo_evento"], "não única: a origem reenvia eventos idênticos; duplicata é aviso (dq_qualidade_diaria.eventos_duplicados); o motivo está em motivo_rejeicao"),
    "silver.pendencia_hist": (["pendencia_id", "__START_AT"], "SCD tipo 2: uma linha por versão"),
    "silver.pendencia_atual": (["pendencia_id"], None),
    "regras.triagem_regras": (["triagem_id"], None),
    "regras.v_falhas_regras": (["dia", "fonte", "regra_id"], None),
    "regras.v_triagem_pendente": (["semana", "fonte", "regra_id", "versao"], None),
    "regras.v_mudancas_regras": (["regra_id", "versao"], None),
    "regras.v_retroalimentacao": (["regra_id"], None),
    "dqx_codigo.dq_metricas_regras": (["execucao_id", "regra"], "a coluna versao entra na próxima execução gravada (mergeSchema)"),
    "dqx_codigo.eventos_validos": (["pendencia_id", "data_extracao", "tipo_evento"], "não única: a origem reenvia eventos idênticos; duplicata é aviso (dq_qualidade_diaria.eventos_duplicados)"),
    "dqx_codigo.eventos_quarentena": (["pendencia_id", "data_extracao", "tipo_evento"], "não única: a origem reenvia eventos idênticos; duplicata é aviso (dq_qualidade_diaria.eventos_duplicados)"),
    "conformidade.config_regras": (["regra_id"], None),
    "conformidade.config_camadas": (["esquema"], None),
    "conformidade.ativos": (["catalogo", "esquema", "ativo"], None),
    "conformidade.colunas": (["esquema", "ativo", "coluna"], None),
    "conformidade.historico": (["registrado_em", "regra_id"], None),
    "conformidade.sonda_views": (["sondado_em", "catalogo", "esquema", "ativo"], None),
    "conformidade.boas_praticas_dados": (["regra_id"], None),
    "conformidade.chaves_declaradas": (["tabela"], None),
    "conformidade.chaves_unicas": (["verificado_em", "tabela"], None),
    "sustentacao.jobs_monitorados": (["job_id"], None),
    "sustentacao.execucoes_job": (["job_run_id"], None),
    "sustentacao.execucoes_tarefa": (["task_run_id"], None),
    "sustentacao.atualizacoes_pipeline": (["update_id"], None),
    "sustentacao.matriz_tarefas": (["tarefa"], None),
    "sustentacao.linha_base": (["job", "tarefa"], None),
    "sustentacao.sla_diario": (["dia", "job_id"], None),
    "sustentacao.volume_execucao": (["job_run_id"], None),
    "sustentacao.ultima_execucao": (["job_id"], None),
    "gold.dq_qualidade_diaria": (["dia"], None),
    "gold.dq_barrados_por_motivo_dia": (["dia", "motivo_rejeicao", "tipo_evento"], None),
    "gold.dq_fato_orfas_diarias": (["dia_sk"], None),
    # ontologia: entidades sem identificador pessoal (as metric views não têm chave: são medidas e dimensões)
    "ontologia.cliente": (["cliente_sk"], None), "ontologia.apolice": (["apolice_sk"], None),
    "ontologia.produto": (["produto_sk"], None), "ontologia.corretor": (["corretor_sk"], None),
    "ontologia.ponto_venda": (["ponto_venda_sk"], None), "ontologia.apolice_cobertura": (["apolice_sk", "cobertura_sk", "papel_cobertura"], None),
    "ontologia.pendencia": (["pendencia_id"], None), "ontologia.pagamento": (["pendencia_id"], None),
    "ontologia.evento_cobranca": (["pendencia_id", "data_extracao", "tipo_evento"], None), "ontologia.posicao_carteira": (["data_referencia", "pendencia_id"], None),
    "ontologia.entidades": (["entidade"], None), "ontologia.relacoes": (["sujeito", "predicado", "objeto"], None),
    "ontologia.glossario": (["termo"], None),
    # dq: janelas (mesma chave da origem) e visões do painel
    "dq.janela_avaliacao": (["origem"], None),
    "dq.v_bronze_eventos_7d": (["pendencia_id", "data_extracao", "tipo_evento"], "janela de 7 dias do bronze; repete como o bronze"),
    "dq.v_bronze_eventos_janela": (["pendencia_id", "data_extracao", "tipo_evento"], "janela do bronze; repete como o bronze"),
    "dq.v_quarentena_janela": (["pendencia_id", "data_extracao", "tipo_evento"], "não única: a origem reenvia eventos idênticos; duplicata é aviso (dq_qualidade_diaria.eventos_duplicados)"),
    "dq.v_silver_eventos_aptos_janela": (["pendencia_id", "data_extracao", "tipo_evento"], "não única: a origem reenvia eventos idênticos; duplicata é aviso (dq_qualidade_diaria.eventos_duplicados)"),
    "dq.v_silver_pendencia_atual_7d": (["pendencia_id"], None),
    "dq.v_fato_snapshot_7d": (["pendencia_id", "data_referencia_sk"], None),
    "dq.v_fato_snapshot_janela": (["pendencia_id", "data_referencia_sk"], None),
    "dq.v_painel_diario": (["dia"], None),
    "dq.v_painel_barrados": (["dia", "motivo_rejeicao", "tipo_evento"], None),
    "dq.v_painel_studio_execucoes": (["run_id"], None),
    "dq.v_painel_studio_regras": (["run_id", "regra"], None),
    # bi: extratos agregados (a chave é o grão)
    "bi.calendario": (["data"], None), "bi.qualidade_diaria": (["dia"], None), "bi.forma_pagamento": (["forma_pagamento"], None),
    # conformidade, finops e sustentação: o grão de cada visão
    "conformidade.recursos": (["recurso_id"], None), "conformidade.acoes_observabilidade": (["acao"], None),
    "conformidade.config_tags_governadas": (["tag"], None),
    "conformidade.plataforma_por_catalogo": (["catalogo", "dimensao"], None),
    "conformidade.squad_por_schema": (["esquema", "dimensao"], None),
    "finops.config_ativos": (["id"], None), "finops.config_atribuicao": (["ordem"], None),
    "finops.boas_praticas_custo": (["codigo"], None), "finops.custo_sql_por_consulta": (["statement_id", "hora"], None),
    "finops.plataforma_warehouses": (["warehouse_id"], None), "finops.plataforma_custo_diario": (["dia", "funcionalidade"], None),
    "finops.plataforma_top_recursos": (["posicao"], None), "finops.uso_paineis_diario": (["dia", "painel_id"], None),
    "finops.uso_jobs_diario": (["dia", "job"], None), "finops.squad_uso_diario": (["dia", "projeto", "indicador"], None),
    "finops.squad_custo_unitario": (["mes", "projeto", "indicador"], None),
    "sustentacao.config_sla": (["job"], None), "sustentacao.config_sustentacao": (["projeto"], None),
    "sustentacao.volume_diario": (["dia"], None), "sustentacao.desvios": (["job_run_id", "tarefa"], None),
    "bi.produto": (["produto"], None),
    "bi.canal_venda": (["canal_venda"], None),
}

# tabelas sem tabela de origem: geradas no código a partir de valores fixos (catálogos, calendário, ontologia)
GERADA_NO_CODIGO = {
    **{f"gold.{d}": "carga_diaria/gerar_carga.py (dim com catálogo fixo)" for d in
       ("dim_cobertura", "dim_data", "dim_faixa_atraso", "dim_forma_pagamento", "dim_motivo_pendencia", "dim_periodicidade",
        "dim_status_cobranca")},
    **{f"ontologia.{t}": "governanca/gerar_ontologia_sql.py (conceitos de governanca/ontologia.py)" for t in
       ("entidades", "glossario", "relacoes")},
}

# relacionamentos lógicos: (de, colunas, para, colunas, cardinalidade de -> para, frase)
RELACOES = [
    ("gold.dq_barrados_por_motivo_dia", ["motivo_rejeicao"], "regras.catalogo_regras", ["regra_id"], "N:1", "barrados por uma regra de erro do catálogo"),
    ("gold.dq_fato_orfas_diarias", ["dia_sk"], "gold.dim_data", ["data_sk"], "1:1", "a foto diária de um dia do calendário"),
    ("landing.pagamentos_pendentes_one_table", ["numero_apolice"], "fonte.apolices", ["numero_apolice"], "N:1", "o evento é de uma apólice do cadastro"),
    ("bronze.pagamentos_pendentes_eventos", ["numero_apolice"], "fonte.apolices", ["numero_apolice"], "N:1", "o evento é de uma apólice do cadastro"),
    ("silver.pendencia_evento", ["pendencia_id"], "silver.pendencia_atual", ["pendencia_id"], "N:1", "os eventos aptos formam a foto atual da pendência"),
    ("silver.pendencia_hist", ["pendencia_id"], "silver.pendencia_atual", ["pendencia_id"], "N:1", "cada versão SCD2 é de uma pendência"),
    ("silver.pendencia_evento_quarentena", ["pendencia_id"], "silver.pendencia_atual", ["pendencia_id"], "N:0..1", "evento barrado; a pendência pode nem existir na silver"),
    ("gold.fact_pagamento_pendente_snapshot", ["pendencia_id"], "silver.pendencia_atual", ["pendencia_id"], "N:1", "a foto diária vem da pendência da silver"),
    ("regras.triagem_regras", ["regra_id"], "regras.catalogo_regras", ["regra_id"], "N:1", "a triagem classifica as falhas de uma regra (e versão)"),
    ("regras.v_falhas_regras", ["regra_id", "versao"], "regras.catalogo_regras", ["regra_id", "versao"], "N:1", "falhas do dia pela versão vigente"),
    ("regras.v_triagem_pendente", ["regra_id", "versao"], "regras.catalogo_regras", ["regra_id", "versao"], "N:1", "semana a triar de uma versão"),
    ("regras.v_mudancas_regras", ["regra_id", "versao"], "regras.catalogo_regras", ["regra_id", "versao"], "1:1", "versão que começou a valer"),
    ("regras.v_retroalimentacao", ["regra_id"], "regras.catalogo_regras", ["regra_id"], "1:N", "indicadores da regra em todas as versões"),
    ("silver.pendencia_evento_quarentena", ["motivo_rejeicao"], "regras.catalogo_regras", ["regra_id"], "N:1", "o motivo de rejeição é uma regra de erro do catálogo"),
    ("dqx_codigo.dq_metricas_regras", ["regra"], "regras.catalogo_regras", ["regra_id"], "N:1", "métrica de uma regra do catálogo"),
    ("conformidade.achados", ["regra_id"], "conformidade.config_regras", ["regra_id"], "N:1", "cada verificação é de uma regra"),
    ("conformidade.achados", ["catalogo", "esquema", "ativo"], "conformidade.ativos", ["catalogo", "esquema", "ativo"], "N:0..1", "a verificação é sobre um ativo (ou job, warehouse, alerta)"),
    ("conformidade.pendencias", ["regra_id"], "conformidade.config_regras", ["regra_id"], "N:1", "pendência de uma regra"),
    ("conformidade.historico", ["regra_id"], "conformidade.config_regras", ["regra_id"], "N:1", "foto diária de uma regra"),
    ("conformidade.boas_praticas_dados", ["regra_id"], "conformidade.config_regras", ["regra_id"], "1:1", "situação atual da regra"),
    ("conformidade.sonda_views", ["catalogo", "esquema", "ativo"], "conformidade.ativos", ["catalogo", "esquema", "ativo"], "N:1", "sonda diária de uma view"),
    ("conformidade.colunas", ["esquema", "ativo"], "conformidade.ativos", ["esquema", "ativo"], "N:1", "coluna de um ativo do pos_venda"),
    ("conformidade.squad_por_schema", ["esquema"], "conformidade.config_camadas", ["esquema"], "N:1", "conformidade de um schema com papel"),
    ("conformidade.chaves_unicas", ["tabela"], "conformidade.chaves_declaradas", ["tabela"], "N:1", "teste diário de uma chave declarada"),
    ("sustentacao.execucoes_job", ["job_id"], "sustentacao.jobs_monitorados", ["job_id"], "N:1", "execução de um job monitorado"),
    ("sustentacao.execucoes_tarefa", ["job_run_id"], "sustentacao.execucoes_job", ["job_run_id"], "N:1", "tarefa de uma execução"),
    ("sustentacao.atualizacoes_pipeline", ["task_run_id"], "sustentacao.execucoes_tarefa", ["task_run_id"], "N:1", "update do pipeline disparado por uma tarefa"),
    ("sustentacao.desvios", ["job_run_id"], "sustentacao.execucoes_job", ["job_run_id"], "N:1", "desvio numa execução"),
    ("sustentacao.volume_execucao", ["job_run_id"], "sustentacao.execucoes_job", ["job_run_id"], "1:1", "volume de uma execução"),
    ("sustentacao.ultima_execucao", ["job_run_id"], "sustentacao.execucoes_job", ["job_run_id"], "1:1", "última execução de cada job"),
    ("sustentacao.sla_diario", ["job_id"], "sustentacao.jobs_monitorados", ["job_id"], "N:1", "SLA diário de um job"),
    ("sustentacao.linha_base", ["tarefa"], "sustentacao.matriz_tarefas", ["tarefa"], "N:1", "linha de base da tarefa e o que fazer"),
    ("bi.carteira_diaria", ["produto"], "bi.produto", ["produto"], "N:1", "saldo do dia de um produto"),
    ("bi.carteira_diaria", ["canal_venda"], "bi.canal_venda", ["canal_venda"], "N:1", "saldo do dia de um canal"),
    ("bi.recuperacao_diaria", ["produto"], "bi.produto", ["produto"], "N:1", "recuperação de um produto"),
    ("bi.recuperacao_diaria", ["canal_venda"], "bi.canal_venda", ["canal_venda"], "N:1", "recuperação de um canal"),
    ("bi.safras", ["produto"], "bi.produto", ["produto"], "N:1", "safra de um produto"),
    ("bi.safras", ["canal_venda"], "bi.canal_venda", ["canal_venda"], "N:1", "safra de um canal"),
    ("finops.squad_custo_mensal", ["projeto"], "finops.config_atribuicao", ["projeto"], "N:N", "o projeto vem das regras de atribuição"),
    ("finops.squad_custo_unitario", ["projeto"], "finops.config_atribuicao", ["projeto"], "N:N", "o projeto vem das regras de atribuição"),
    ("finops.squad_uso_diario", ["projeto"], "finops.config_atribuicao", ["projeto"], "N:N", "o projeto vem das regras de atribuição"),
    ("finops.custo_por_projeto_diario", ["projeto"], "finops.config_atribuicao", ["projeto"], "N:N", "o projeto vem das regras de atribuição"),
    ("finops.uso_jobs_diario", ["projeto"], "finops.config_atribuicao", ["projeto"], "N:N", "o projeto vem das regras de atribuição"),
    ("finops.uso_paineis_diario", ["projeto"], "finops.config_atribuicao", ["projeto"], "N:N", "o projeto vem das regras de atribuição"),
    ("ontologia.apolice_cobertura", ["apolice_sk"], "ontologia.apolice", ["apolice_sk"], "N:1", "coberturas da apólice"),
    ("ontologia.posicao_carteira", ["apolice_sk"], "ontologia.apolice", ["apolice_sk"], "N:1", "a posição é de uma apólice"),
    ("ontologia.posicao_carteira", ["cliente_sk"], "ontologia.cliente", ["cliente_sk"], "N:1", "a posição é de um cliente"),
    ("ontologia.posicao_carteira", ["pendencia_id"], "ontologia.pendencia", ["pendencia_id"], "N:1", "uma linha por dia enquanto a pendência está aberta"),
    ("ontologia.pagamento", ["pendencia_id"], "ontologia.pendencia", ["pendencia_id"], "0..1:1", "nem toda pendência é paga"),
    ("ontologia.evento_cobranca", ["pendencia_id"], "ontologia.pendencia", ["pendencia_id"], "N:1", "NOVA, ATUALIZACAO e BAIXA da pendência"),
    ("ontologia.pagamento", ["numero_apolice"], "ontologia.apolice", ["numero_apolice"], "N:1", "o pagamento é de uma apólice"),
    ("ontologia.pendencia", ["produto_codigo"], "ontologia.produto", ["produto_codigo"], "N:1", "a pendência é de um produto"),
    ("dq.v_bronze_eventos_janela", ["pendencia_id", "data_extracao", "tipo_evento"], "bronze.pagamentos_pendentes_eventos", ["pendencia_id", "data_extracao", "tipo_evento"], "1:1", "janela do bronze"),
    ("dq.v_quarentena_janela", ["pendencia_id", "data_extracao", "tipo_evento"], "silver.pendencia_evento_quarentena", ["pendencia_id", "data_extracao", "tipo_evento"], "1:1", "janela da quarentena"),
    ("dq.v_silver_eventos_aptos_janela", ["pendencia_id", "data_extracao", "tipo_evento"], "silver.pendencia_evento", ["pendencia_id", "data_extracao", "tipo_evento"], "1:1", "janela dos eventos aptos"),
    ("dq.v_silver_pendencia_atual_7d", ["pendencia_id"], "silver.pendencia_atual", ["pendencia_id"], "1:1", "janela da foto atual"),
    ("dq.v_fato_snapshot_janela", ["pendencia_id", "data_referencia_sk"], "gold.fact_pagamento_pendente_snapshot", ["pendencia_id", "data_referencia_sk"], "1:1", "janela da fato"),
    ("dq.v_painel_studio_regras", ["run_id"], "dq.v_painel_studio_execucoes", ["run_id"], "N:1", "regras de uma execução do Studio"),
    ("dq.v_painel_barrados", ["motivo_rejeicao"], "regras.catalogo_regras", ["regra_id"], "N:1", "barrados por uma regra de erro"),
    ("bi.carteira_diaria", ["data_referencia"], "bi.calendario", ["data"], "N:1", "saldo de um dia do calendário"),
    ("bi.recuperacao_diaria", ["data_baixa"], "bi.calendario", ["data"], "N:1", "recuperação de um dia"),
    ("bi.qualidade_diaria", ["dia"], "bi.calendario", ["data"], "1:1", "qualidade de um dia"),
    ("bi.carteira_diaria", ["forma_pagamento"], "bi.forma_pagamento", ["forma_pagamento"], "N:1", "saldo de uma forma de pagamento"),
    ("bi.recuperacao_diaria", ["forma_pagamento"], "bi.forma_pagamento", ["forma_pagamento"], "N:1", "recuperação de uma forma de pagamento"),
    ("bi.safras", ["forma_pagamento"], "bi.forma_pagamento", ["forma_pagamento"], "N:1", "safra de uma forma de pagamento"),
    ("conformidade.ativos", ["esquema"], "conformidade.config_camadas", ["esquema"], "N:0..1", "papel do schema (só os do pos_venda)"),
    ("sustentacao.config_sla", ["job"], "sustentacao.jobs_monitorados", ["job"], "1:1", "meta de horário de um job"),
]


def linhas(sql):
    estado, erro, ls = executar(sql)
    if estado != "SUCCEEDED":
        raise SystemExit(f"{sql[:100]}... -> {estado}: {erro[:300]}")
    return ls


def ler_uc():
    tabelas = linhas(f"""SELECT table_schema s, table_name t, table_type tipo, coalesce(comment, '') comentario
FROM {CAT}.information_schema.tables WHERE table_schema <> 'information_schema'""")
    colunas = linhas(f"""SELECT table_schema s, table_name t, column_name c, data_type d, ordinal_position o
FROM {CAT}.information_schema.columns WHERE table_schema <> 'information_schema' ORDER BY s, t, o""")
    pks = linhas(f"""SELECT k.table_schema s, k.table_name t, k.column_name c, k.ordinal_position o
FROM {CAT}.information_schema.table_constraints tc JOIN {CAT}.information_schema.key_column_usage k
  ON k.constraint_name = tc.constraint_name AND k.constraint_schema = tc.constraint_schema
WHERE tc.constraint_type = 'PRIMARY KEY' ORDER BY s, t, o""")
    fks = linhas(f"""SELECT k.table_schema s, k.table_name t, k.column_name c, pk.table_schema ps, pk.table_name pt, pk.column_name pc
FROM {CAT}.information_schema.referential_constraints rc
JOIN {CAT}.information_schema.key_column_usage k ON k.constraint_name = rc.constraint_name AND k.constraint_schema = rc.constraint_schema
JOIN {CAT}.information_schema.key_column_usage pk ON pk.constraint_name = rc.unique_constraint_name
  AND pk.constraint_schema = rc.unique_constraint_schema AND pk.ordinal_position = k.position_in_unique_constraint""")
    ont = linhas(f"SELECT sujeito, predicado, objeto, cardinalidade, chave, descricao FROM {CAT}.ontologia.relacoes")
    lin = linhas(f"""SELECT DISTINCT source_table_schema ss, source_table_name st, target_table_schema ts, target_table_name tt
FROM system.access.table_lineage
WHERE source_table_catalog = '{CAT}' AND target_table_catalog = '{CAT}' AND event_date >= current_date() - 90
  AND source_table_name IS NOT NULL AND target_table_name IS NOT NULL""")
    return tabelas, colunas, pks, fks, ont, lin


def base_de(schema):
    return next((b for b, (ss, _, _) in BASES.items() if schema in ss), None)


def tipo_curto(d):
    return re.sub(r"[^a-z0-9]", "", d.lower().split("(")[0].split("<")[0]) or "string"


def ent(nome):          # nome de entidade válido no Mermaid
    return nome.replace(".", "__")


def montar(tabelas, colunas, pks, fks, ont, lin):
    cols = collections.defaultdict(list)
    for r in colunas:
        cols[f"{r['s']}.{r['t']}"].append((r["c"], r["d"]))
    info = {f"{r['s']}.{r['t']}": r for r in tabelas if not INTERNO.match(r["t"])}
    pk = collections.defaultdict(list)
    for r in pks:
        pk[f"{r['s']}.{r['t']}"].append(r["c"])
    erros, pk_leg = [], {}
    for nome, (ks, _) in CHAVES.items():
        if nome not in info:
            erros.append(f"CHAVES: tabela {nome} não existe")
            continue
        faltam = [k for k in ks if k not in {c for c, _ in cols[nome]}]
        if faltam:
            erros.append(f"CHAVES: {nome} sem as colunas {faltam}")
    rel = []
    agrupado = collections.defaultdict(list)
    for r in fks:
        agrupado[(f"{r['s']}.{r['t']}", f"{r['ps']}.{r['pt']}", r["pc"])].append(r["c"])
    for (de, para, pc), cs in agrupado.items():
        for c in cs:
            rel.append({"de": de, "colunas_de": [c], "para": para, "colunas_para": [pc], "card": "N:1",
                        "frase": f"{c} aponta para a dimensão", "tipo": "FK no Unity Catalog"})
    for de, cd, para, cp, card, frase in RELACOES:
        for t, cs in ((de, cd), (para, cp)):
            if t not in info:
                erros.append(f"RELACOES: tabela {t} não existe")
            elif [c for c in cs if c not in {x for x, _ in cols[t]}]:
                erros.append(f"RELACOES: {t} sem as colunas {[c for c in cs if c not in {x for x, _ in cols[t]}]}")
        rel.append({"de": de, "colunas_de": cd, "para": para, "colunas_para": cp, "card": card, "frase": frase, "tipo": "lógico"})
    # legado: mesmo star schema da gold, sem constraints (chave e relacionamento pelo mesmo nome de coluna)
    nome_leg = lambda leg, t: f"{leg}.{'fact_pagamento_pendente' if t == 'fact_pagamento_pendente_snapshot' else t}"
    tem = lambda t, cs: t in info and all(c in {x for x, _ in cols[t]} for c in cs)
    for leg in ("gold_sql", "gold_ldp"):
        for t in [n.split(".")[1] for n in pk if n.startswith("gold.")]:
            alvo = nome_leg(leg, t)
            if tem(alvo, pk[f"gold.{t}"]) and alvo not in pk:
                pk_leg[alvo] = pk[f"gold.{t}"]
        for r in [x for x in rel if x["tipo"] == "FK no Unity Catalog" and x["de"].startswith("gold.")]:
            de, para = nome_leg(leg, r["de"].split(".")[1]), nome_leg(leg, r["para"].split(".")[1])
            if tem(de, r["colunas_de"]) and tem(para, r["colunas_para"]):
                rel.append({**r, "de": de, "para": para, "tipo": "lógico (espelho da gold)"})
    if erros:
        raise SystemExit("modelo inválido:\n  - " + "\n  - ".join(erros))
    sobe, desce = collections.defaultdict(set), collections.defaultdict(set)
    for r in lin:
        a, b = f"{r['ss']}.{r['st']}", f"{r['ts']}.{r['tt']}"
        if a != b and not INTERNO.match(r["st"]) and not INTERNO.match(r["tt"]):
            sobe[b].add(a)
            desce[a].add(b)
    modelo = {}
    for nome, r in info.items():
        chave = pk.get(nome) or pk_leg.get(nome) or (CHAVES.get(nome, ([], None))[0])
        origem_chave = ("PK no Unity Catalog" if nome in pk else "lógica (espelho da gold)" if nome in pk_leg
                        else "lógica" if nome in CHAVES else None)
        modelo[nome] = {
            "base": base_de(r["s"]), "tipo": r["tipo"], "comentario": r["comentario"],
            "chave": chave, "chave_origem": origem_chave,
            "chave_nota": CHAVES.get(nome, (None, None))[1], "colunas": len(cols[nome]),
            "relacoes": [x for x in rel if nome in (x["de"], x["para"])],
            "vem_de": sorted(sobe[nome]), "alimenta": sorted(desce[nome]), "gerada_por": GERADA_NO_CODIGO.get(nome),
        }
    return modelo, rel, cols, ont


def diagrama(base, modelo, rel, cols):
    nomes = sorted(n for n, m in modelo.items() if m["base"] == base)
    fk_cols = collections.defaultdict(set)
    for r in rel:
        fk_cols[r["de"]].update(r["colunas_de"])
    linhas_m = ["```mermaid", "erDiagram"]
    for n in nomes:
        m = modelo[n]
        chave, fks = set(m["chave"]), fk_cols[n]
        escolhidas = [c for c in cols[n] if c[0] in chave or c[0] in fks]
        extras = [c for c in cols[n] if c[0] not in chave and c[0] not in fks][:max(0, 6 - len(escolhidas))]
        linhas_m.append(f"  {ent(n)} {{")
        for c, d in escolhidas + extras:
            marca = ",".join(x for x, ok in (("PK", c in chave), ("FK", c in fks)) if ok)
            linhas_m.append(f"    {tipo_curto(d)} {re.sub(r'[^A-Za-z0-9_]', '_', c)}{(' ' + marca) if marca else ''}")
        resto = m["colunas"] - len(escolhidas) - len(extras)
        if resto > 0:
            linhas_m.append(f'    string mais_{resto}_colunas "veja a Wiki"')
        linhas_m.append("  }")
    simb = {"N:1": "}o--||", "N:0..1": "}o--o|", "1:1": "||--||", "1:N": "||--o{", "N:N": "}o--o{", "0..1:1": "|o--||"}
    feitos = set()
    for r in rel:
        if modelo.get(r["de"], {}).get("base") == base or modelo.get(r["para"], {}).get("base") == base:
            k = (r["de"], r["para"], tuple(r["colunas_de"]))
            if k in feitos:
                continue
            feitos.add(k)
            linhas_m.append(f'  {ent(r["de"])} {simb.get(r["card"], "}o--||")} {ent(r["para"])} : "{"+".join(r["colunas_de"])}"')
    linhas_m.append("```")
    return "\n".join(linhas_m)


def doc_base(base, modelo, rel, cols, ont):
    schemas, papel, oque = BASES[base]
    nomes = sorted(n for n, m in modelo.items() if m["base"] == base)
    out = [f"# Base {base} · modelo de entidade e relacionamento",
           "",
           f"> Gerado por `governanca/modelo_dados.py` a partir do Unity Catalog. Não edite: rode `python3 governanca/modelo_dados.py gerar`.",
           f"> Schemas: {', '.join(f'`{CAT}.{s}`' for s in schemas)} · papel: **{papel}**.",
           "", oque, "", "## Diagrama", "",
           "Chave: `PK` (declarada no Unity Catalog ou lógica, ver a tabela abaixo) e `FK` (coluna que aponta para outra entidade).",
           "Relacionamentos com outras bases aparecem com o nome completo da entidade (`schema__tabela`).", "",
           diagrama(base, modelo, rel, cols), "", "## Entidades", "",
           "| Entidade | Tipo | Chave | Colunas | Descrição |", "|---|---|---|---|---|"]
    for n in nomes:
        m = modelo[n]
        chave = ", ".join(f"`{c}`" for c in m["chave"]) or "sem chave declarada"
        if m["chave_origem"]:
            chave += f" ({m['chave_origem']}{'; ' + m['chave_nota'] if m['chave_nota'] else ''})"
        out.append(f"| `{n}` | {m['tipo'].lower().replace('_', ' ')} | {chave} | {m['colunas']} | {m['comentario'][:160].replace('|', '/')} |")
    rs = [r for r in rel if modelo.get(r["de"], {}).get("base") == base or modelo.get(r["para"], {}).get("base") == base]
    out += ["", "## Relacionamentos", ""]
    if rs:
        out += ["| De | Para | Colunas | Cardinalidade | Tipo | O que significa |", "|---|---|---|---|---|---|"]
        for r in rs:
            out.append(f"| `{r['de']}` | `{r['para']}` | {', '.join(r['colunas_de'])} → {', '.join(r['colunas_para'])} | {r['card']} | {r['tipo']} | {r['frase']} |")
    else:
        out.append("Sem relacionamento entre entidades: cada objeto é uma visão independente sobre outras bases (veja a linhagem).")
    if base == "ontologia":
        out += ["", "### Relacionamentos de negócio (`pos_venda.ontologia.relacoes`)", "",
                "| Sujeito | Predicado | Objeto | Cardinalidade | Chave | Descrição |", "|---|---|---|---|---|---|"]
        out += [f"| {r['sujeito']} | {r['predicado']} | {r['objeto']} | {r['cardinalidade']} | `{r['chave']}` | {r['descricao']} |" for r in ont]
    out += ["", "## Linhagem (Unity Catalog, últimos 90 dias)", "", "| Entidade | Vem de | Alimenta |", "|---|---|---|"]
    for n in nomes:
        m = modelo[n]
        origem = ", ".join(f"`{x}`" for x in m["vem_de"]) or (f"gerada no código: {m['gerada_por']}" if m.get("gerada_por") else "—")
        out.append(f"| `{n}` | {origem} | {', '.join(f'`{x}`' for x in m['alimenta'][:8]) or '—'}"
                   f"{' …' if len(m['alimenta']) > 8 else ''} |")
    return "\n".join(out) + "\n"


def doc_indice(modelo, rel, lin):
    por_base = collections.Counter(m["base"] for m in modelo.values())
    arestas = collections.Counter()
    for r in lin:
        a, b = base_de(r["ss"]), base_de(r["ts"])
        if a and b and a != b and not INTERNO.match(r["st"]) and not INTERNO.match(r["tt"]):
            arestas[(a, b)] += 1
    g = ["```mermaid", "flowchart LR"] + [f"  {a} -->|{n}| {b}" for (a, b), n in sorted(arestas.items())] + ["```"]
    out = ["# Modelo de dados do pos_venda", "",
           "> Gerado por `governanca/modelo_dados.py` (Unity Catalog: colunas, PK, FK e `system.access.table_lineage`). Não edite.",
           "> Cada base tem o seu modelo de entidade e relacionamento, a lista de entidades com chave e a linhagem.", "",
           "## Bases", "", "| Base | Schemas | Papel | Entidades | Com chave | Relacionamentos |", "|---|---|---|---|---|---|"]
    for b, (ss, papel, _) in BASES.items():
        ns = [n for n, m in modelo.items() if m["base"] == b]
        rs = {(r["de"], r["para"], tuple(r["colunas_de"])) for r in rel if modelo.get(r["de"], {}).get("base") == b}
        out.append(f"| [{b}]({b}.md) | {', '.join(ss)} | {papel} | {len(ns)} | {sum(1 for n in ns if modelo[n]['chave'])} | {len(rs)} |")
    out += ["", "## Linhagem entre as bases", "", "Número de ligações de tabela para tabela, de uma base para outra.", "", *g, ""]
    return "\n".join(out)


def cmd_gerar():
    tabelas, colunas, pks, fks, ont, lin = ler_uc()
    modelo, rel, cols, ont = montar(tabelas, colunas, pks, fks, ont, lin)
    sem_base = sorted(n for n, m in modelo.items() if not m["base"])
    if sem_base:
        raise SystemExit(f"tabelas fora de qualquer base (ponha o schema em BASES): {sem_base}")
    DOCS.mkdir(parents=True, exist_ok=True)
    for b in BASES:
        (DOCS / f"{b}.md").write_text(doc_base(b, modelo, rel, cols, ont), encoding="utf-8")
    (DOCS / "README.md").write_text(doc_indice(modelo, rel, lin), encoding="utf-8")
    SAIDA_JSON.write_text(json.dumps(modelo, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(f"{len(modelo)} entidades em {len(BASES)} bases; {len(rel)} relacionamentos; "
          f"{sum(1 for m in modelo.values() if m['chave'])} com chave; docs/modelo_dados/ e governanca/modelo_dados.json")


def cmd_conferir():
    tabelas, colunas, pks, fks, ont, lin = ler_uc()
    modelo, rel, cols, ont = montar(tabelas, colunas, pks, fks, ont, lin)
    gravado = json.loads(SAIDA_JSON.read_text(encoding="utf-8"))
    ok = True

    def check(nome, cond, det):
        nonlocal ok
        ok &= bool(cond)
        print(f"{'ok   ' if cond else 'FALHA'} {nome}: {det}")

    check("toda tabela do pos_venda numa base", all(m["base"] for m in modelo.values()), f"{len(modelo)} entidades")
    check("modelo gravado = Unity Catalog agora", set(gravado) == set(modelo), f"{len(gravado)} gravadas, {len(modelo)} no UC")
    nfk = len({(r["s"], r["t"], r["c"]) for r in fks})
    check("toda FK do Unity Catalog no modelo", sum(1 for r in rel if r["tipo"] == "FK no Unity Catalog") == nfk, f"{nfk} FKs")
    for b in BASES:
        check(f"documento da base {b}", (DOCS / f"{b}.md").exists(), f"docs/modelo_dados/{b}.md")
    sem_chave = sorted(n for n, m in modelo.items() if m["base"] in ("origem", "bronze", "silver", "gold", "regras")
                       and m["tipo"] not in ("VIEW", "METRIC_VIEW") and not m["chave"])
    check("tabela das bases do fluxo com chave", not sem_chave, f"sem chave: {sem_chave}")
    orfas = sorted(n for n, m in modelo.items() if m["base"] in ("bronze", "silver", "gold", "ontologia", "bi")
                   and not m["vem_de"] and not m.get("gerada_por"))
    check("tabela do fluxo com linhagem de entrada", not orfas, f"sem linhagem: {orfas}")
    repetidas = []
    for n, m in sorted(modelo.items()):
        nota = (m.get("chave_nota") or "")
        if m["chave_origem"] in ("PK no Unity Catalog", "lógica", "lógica (espelho da gold)") and "repet" not in nota and "não única" not in nota:
            cs = ", ".join(f"`{c}`" for c in m["chave"])
            r = linhas(f"SELECT count(*) AS n, count(DISTINCT struct({cs})) AS d FROM {CAT}.{n}")[0]
            if r["n"] != r["d"]:
                repetidas.append(f"{n} ({int(r['n']) - int(r['d'])} repetidas)")
    check("chave (PK do UC e lógica) única nos dados", not repetidas, f"repetidas: {repetidas}" if repetidas else "todas únicas")
    if not ok:
        sys.exit(1)


def q(s):
    return str(s).replace("\\", "\\\\").replace("'", "''")


def cmd_aplicar():
    """Publica a lista de chaves para o job diário (conformidade/src/chaves_diarias.py), que testa a unicidade nos dados."""
    modelo = json.loads(SAIDA_JSON.read_text(encoding="utf-8"))
    linhas_v = []
    for n, m in sorted(modelo.items()):
        if not m["chave"]:
            continue
        nota = m.get("chave_nota") or ""
        testar = "repet" not in nota and "não única" not in nota
        cols = ", ".join(f"'{q(c)}'" for c in m["chave"])
        linhas_v.append(f"('{CAT}.{n}', '{m['base']}', array({cols}), '{q(m['chave_origem'])}', "
                        f"{'NULL' if not nota else repr_txt(nota)}, {str(testar).lower()})")
    t = f"{CAT}.conformidade.chaves_declaradas"
    for sql in (f"""CREATE OR REPLACE TABLE {t} (
  tabela STRING NOT NULL COMMENT 'Tabela ou visão, no formato catálogo.schema.tabela.',
  base STRING COMMENT 'Base do modelo de dados (docs/modelo_dados): origem, bronze, silver, gold, regras e as demais.',
  colunas ARRAY<STRING> COMMENT 'Colunas que formam a chave, na ordem do modelo de dados.',
  origem_chave STRING COMMENT 'PK no Unity Catalog (declarada, algumas com RELY) ou chave lógica do modelo de dados.',
  nota STRING COMMENT 'Observação da chave, por exemplo por que ela não é única de propósito.',
  testar BOOLEAN COMMENT 'Verdadeiro quando a chave deve ser única e o job diário testa a unicidade nos dados.'
) COMMENT 'Chaves declaradas no modelo de dados (P42), publicadas por governanca/modelo_dados.py aplicar. O job pos_venda_conformidade_sonda testa a unicidade de cada uma todo dia (tarefa chaves).'""",
                f"INSERT INTO {t} VALUES\n" + ",\n".join(linhas_v)):
        estado, erro, _ = executar(sql)
        if estado != "SUCCEEDED":
            raise SystemExit(f"{sql[:80]}... -> {estado}: {erro[:300]}")
    print(f"{len(linhas_v)} chaves publicadas em {t} ({sum(1 for x in linhas_v if x.endswith('true)'))} testadas por dia)")


def repr_txt(s):
    return f"'{q(s)}'"


if __name__ == "__main__":
    {"gerar": cmd_gerar, "conferir": cmd_conferir, "aplicar": cmd_aplicar}[sys.argv[1] if len(sys.argv) > 1 else "gerar"]()
