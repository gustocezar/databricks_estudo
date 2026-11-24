"""Sustentação: tempo de execução dos jobs e pipelines diários do pos_venda, no schema pos_venda.sustentacao.

Responde, para quem sustenta a carga em produção:
- quanto tempo levou cada execução, cada tarefa e cada atualização do pipeline Lakeflow (início, fim, duração, setup,
  resultado e tentativas), a partir de system.lakeflow.job_run_timeline, job_task_run_timeline e pipeline_update_timeline;
- qual é a duração normal (linha de base: mediana e p95 das últimas N execuções com sucesso);
- quais execuções passaram do normal (desvios: acima do p95 ou de 1,5 vez a mediana), quanto passaram e a causa provável
  (espera por computação, volume maior ou lentidão com o mesmo volume);
- se a carga terminou antes da hora meta (SLA) e quanto atrasou; com a agenda pausada, a folga projetada;
- o volume de cada execução (eventos da bronze e linhas da fato), para separar lentidão de aumento de volume;
- o sintoma e a ação de cada tarefa (matriz de resiliência do playbook, P28).

Reaproveita, sem duplicar: a atribuição de jobs e pipelines ao projeto vem de pos_venda.finops.config_atribuicao; a duração
média, as falhas e o custo por job e dia continuam em pos_venda.finops.uso_jobs_diario; o frescor das tabelas (USO01) e o
timeout dos jobs (PLT03) continuam em pos_venda.conformidade. Não altera nada fora de pos_venda.sustentacao.

Gera também o painel AI/BI "pos_venda · Sustentação" e o alerta SQL diário (pausado), implantados pelo bundle desta pasta.

Uso:
    python3 sustentacao/gerar_sustentacao.py gerar      # sustentacao.sql, src/pos_venda_sustentacao.lvdash.json, resources/sustentacao.yml
    python3 sustentacao/gerar_sustentacao.py testar     # roda cada visão e cada conjunto do painel sem criar nada (só leitura)
    python3 sustentacao/gerar_sustentacao.py aplicar    # cria o schema e as visões (só recria a que mudou)
    python3 sustentacao/gerar_sustentacao.py conferir   # cada visão responde + contagens batem -> conferencia.json
"""
import datetime
import json
import pathlib
import re
import sys

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(RAIZ / "governanca"))
from sql_util import CotaEsgotada, executar  # noqa: E402

S = "pos_venda.sustentacao"
ESQ = "sustentacao"
PERFIL = "dbx-workshop"
PROJETO = "pos_venda"          # jobs e pipelines do projeto, pela atribuição da FinOps (pos_venda.finops.config_atribuicao)
FUSO = "America/Sao_Paulo"     # horário de Brasília: agenda da carga, meta do SLA e colunas *_local
N_BASE = 20                    # linha de base: últimas N execuções com sucesso
MIN_BASE = 5                   # abaixo disso a base não vale, e não se aponta desvio
FATOR_MEDIANA = 1.5            # desvio: acima do p95 ou acima de 1,5 vez a mediana
FATOR_TIMEOUT = 2              # timeout sugerido: 2 vezes o p95 do job (regra PLT03 da conformidade)
JANELA_ALERTA_H = 24           # o alerta olha os desvios das últimas 24 horas
MIN_EXCESSO_ALERTA_S = 60      # o alerta só avisa desvio que passou do limite por 60 s ou mais e não é explicado por volume
DIAS_SLA = 30                  # calendário do SLA: últimos 30 dias
BRONZE = "pos_venda.bronze.pagamentos_pendentes_eventos"         # _ingestao_ts = momento da gravação
FATO = "pos_venda.gold.fact_pagamento_pendente_snapshot"           # _carga_ts = momento da gravação
JOBS_COM_VOLUME = ["pos_venda_carga_diaria"]
CARGA = "pos_venda_carga_diaria"
PIPELINE_CARGA = "pos_venda_carga_silver_lakeflow"   # o pipeline que a tarefa silver_lakeflow da carga atualiza

# jobs com hora meta (SLA). A hora da agenda vem do próprio job (system.lakeflow.jobs).
SLA = [
    (CARGA, "06:15", "A carga precisa terminar antes da avaliação agendada do DQX Studio às 06:30, que lê a foto do dia (P11)."),
]

# alerta SQL: 1 disparo por dia às 06:20, depois da meta e antes do Studio (PLT06: até 4 por dia). Nasce pausado (P02).
ALERTA_CRON = "0 20 6 * * ?"
ALERTA_NOME = "pos_venda · Sustentação: SLA ou desvio da carga"

# matriz de resiliência por tarefa (P28): o que a tarefa faz, o sintoma de falha e de lentidão e a ação
TAREFAS = [
    (CARGA, 1, "portao_regras",
     "Roda os cenários BDD das regras de negócio contra as funções pos_venda.regras; se um falhar, nada mais roda.",
     "A tarefa falha e as seguintes não rodam.",
     "Ler no log da tarefa o cenário que falhou, corrigir a função ou o cenário (se a regra mudou) e rodar o job de novo.",
     "Setup de cerca de 3 min é o normal: é a primeira tarefa e espera a computação serverless. Execução acima do p95 "
     "aponta cenário novo ou espera da Statement Execution API.",
     "Comparar setup_s e execucao_s em execucoes_tarefa. Se a demora for da API, ver L58.",
     "Matriz do playbook: Portão das regras reprovado; L58"),
    (CARGA, 2, "gerar_eventos",
     "Grava no bronze os eventos de cada dia do intervalo, só acrescentando e com guarda de idempotência.",
     "Falha ao gravar o bronze.",
     "Ver se o dia já está no bronze: a guarda pula dia gravado, e nulo na subconsulta travava a guarda (L82). Depois, rodar de novo o intervalo.",
     "A duração cresce com os dias do intervalo (backfill).",
     "Ver dias_processados e eventos_gravados em volume_execucao: com mais dias, é volume e não lentidão.",
     "L82; volume_execucao"),
    (CARGA, 3, "silver_lakeflow",
     "Atualiza o pipeline Lakeflow da silver: eventos, quarentena, histórica (SCD2) e atual.",
     "O update falha ou é cancelado, e a tarefa termina com erro.",
     "Ler o event log do update (o update_id está em atualizacoes_pipeline), corrigir e reparar a execução a partir desta "
     "tarefa. Full refresh só com decisão do dono: a silver histórica é refeita do bronze.",
     "Espera antes do update (espera_s) ou update acima do p95.",
     "espera_s alto é a subida da computação do pipeline. Update acima do p95 com o mesmo volume é lentidão: ver o event log.",
     "atualizacoes_pipeline; L89"),
    (CARGA, 4, "gold_dimensoes",
     "Recria as dimensões do star schema a partir da silver atual.",
     "A tarefa falha e a fato do dia não é gravada.",
     "Ler o erro no log, conferir a silver atual e a quarentena e reparar a execução a partir desta tarefa.",
     "Setup de cerca de 2,5 min é o normal: depois do pipeline, a computação dos notebooks é pedida de novo.",
     "Olhar execucao_s. Se só o setup subiu, é espera por computação serverless, e não o código.",
     "L89"),
    (CARGA, 5, "gold_fato_snapshot",
     "Apaga e regrava na fato histórica as fotos do intervalo (PK = pendência + dia).",
     "A tarefa falha e a foto do dia fica faltando.",
     "Reparar a execução a partir desta tarefa. A tarefa apaga e regrava o intervalo, então rodar de novo não duplica.",
     "A duração cresce com as fotos do intervalo (cerca de 250 mil linhas por foto).",
     "Ver fotos_gravadas e linhas_fato_gravadas em volume_execucao.",
     "volume_execucao"),
    (CARGA, 6, "dq_metricas",
     "Recria as tabelas dq_* da gold e as views de janela do DQX Studio, devolvendo tags e Wiki.",
     "A tarefa falha, ou as views perdem as tags.",
     "Rodar de novo: garantir_view só recria a view que mudou e devolve a governança. Se sumirem tags, rodar governanca/aplicar_semantica.py.",
     "Execução acima do p95.",
     "Ver quantas views foram recriadas no log: recriar uma view custa mais que confirmar que está igual.",
     "Matriz do playbook: Recriação de view pelo job; L31"),
    (CARGA, 7, "ligar_dqx_studio",
     "Liga o app dqx-studio, que para sozinho após 24 h no Free Edition, para a avaliação agendada das 06:30.",
     "A tarefa falha ao ligar o app, ou o Lakebase está desligado.",
     "databricks apps start dqx-studio; se o Lakebase estiver desligado, ligar o endpoint e reiniciar o app.",
     "Alguns segundos quando o app já está ligado; cerca de 2 min quando o app está parado e precisa subir.",
     "Nada a fazer se o app estava parado. Antes de usar o app, esperar \"Application startup complete\" no log (L85).",
     "Matriz do playbook: App do Studio parado; Lakebase do DQX Studio desligado; L85"),
]


def q(s):
    return s.replace("'", "''")


def local(c):
    """Horário de Brasília como TIMESTAMP_NTZ, sem depender do fuso da sessão."""
    return f"convert_timezone('{FUSO}', {c})"


def minutos(h):
    """'HH:mm' -> minutos desde a meia-noite."""
    return f"(CAST(split({h}, ':')[0] AS INT) * 60 + CAST(split({h}, ':')[1] AS INT))"


AGORA = local("current_timestamp()")
HOJE = f"CAST({AGORA} AS DATE)"

# ------------------------------------------------------------------------------------------------ descrições
D = {   # mesmo nome, mesma descrição em todas as visões
    "fuso": "Fuso das colunas *_local, da agenda e da meta (America/Sao_Paulo, horário de Brasília).",
    "n_base": "Quantas execuções com sucesso, das mais recentes, formam a linha de base.",
    "minimo_base": "Mínimo de execuções com sucesso para a linha de base valer; abaixo disso não se aponta desvio.",
    "fator_mediana": "Fator sobre a mediana: acima dele a execução é desvio, mesmo abaixo do p95.",
    "fator_timeout": "Fator sobre o p95 do job para sugerir o timeout (regra PLT03 da conformidade).",
    "janela_alerta_h": "Horas para trás em que o alerta procura desvios.",
    "min_excesso_alerta_s": "Segundos acima do limite para o desvio entrar no alerta (abaixo disso, ou explicado por volume, fica só no painel).",
    "dias_sla": "Dias do calendário do SLA (sla_diario).",
    "projeto": "Projeto dono do job ou do pipeline, pela atribuição da FinOps (pos_venda.finops.config_atribuicao).",
    "agenda_alerta": "Agenda (cron Quartz, horário de Brasília) do alerta SQL de sustentação.",
    "job": "Nome do job (sem o prefixo [dev usuário] do bundle).",
    "job_id": "Identificador do job.",
    "hora_meta": "Hora meta (HH:mm, horário de Brasília) para a execução da agenda terminar.",
    "motivo_meta": "Por que a hora meta é esta.",
    "agenda_cron": "Agenda do job (cron Quartz), de system.lakeflow.jobs; nulo se o job não tem agenda.",
    "agenda_fuso": "Fuso da agenda do job.",
    "hora_agenda": "Hora de início da agenda diária (HH:mm), lida do cron; nula se a agenda não é diária simples.",
    "agenda_pausada": "Verdadeiro quando a agenda do job está pausada (situação de hoje); nulo quando o job não tem agenda.",
    "timeout_s": "Timeout do job em segundos (0 = sem timeout).",
    "apagado": "Verdadeiro quando o job foi apagado do workspace.",
    "job_run_id": "Execução do job (run_id em job_run_timeline).",
    "task_run_id": "Execução da tarefa (run_id em job_task_run_timeline).",
    "tarefa": "Tarefa do job (task_key). Em linha_base e desvios: '(job inteiro)' para o job e '(update)' para o pipeline.",
    "gatilho": "O que disparou a execução: CRON (agenda), ONETIME (manual ou API), PERIODIC, JOB_TASK (update do pipeline pela tarefa) etc.",
    "da_agenda": "Verdadeiro quando a execução veio da agenda (gatilho CRON). Só estas contam para o SLA.",
    "inicio": "Início da execução em UTC.",
    "fim": "Fim da execução em UTC.",
    "inicio_local": "Início no horário de Brasília.",
    "fim_local": "Fim no horário de Brasília.",
    "dia_local": "Dia do início no horário de Brasília.",
    "duracao_s": "Duração de ponta a ponta, em segundos (fim - início).",
    "duracao_min": "Duração de ponta a ponta, em minutos.",
    "fila_s": "Tempo na fila antes de começar, em segundos (system.lakeflow).",
    "setup_s": "Tempo de preparação (subida da computação), em segundos (system.lakeflow).",
    "execucao_s": "Tempo de execução propriamente dito, em segundos (system.lakeflow).",
    "limpeza_s": "Tempo de limpeza no fim, em segundos (system.lakeflow).",
    "resultado": "Resultado da execução (SUCCEEDED, FAILED, CANCELLED, SKIPPED, COMPLETED...) ou EM ANDAMENTO.",
    "codigo_termino": "Código de término (SUCCESS, USER_CANCELLED, DISABLED...).",
    "sucesso": "Verdadeiro quando terminou com sucesso (SUCCEEDED no job e na tarefa, COMPLETED no pipeline).",
    "data_inicio_param": "Parâmetro data_inicio da execução (primeiro dia do intervalo carregado).",
    "data_fim_param": "Parâmetro data_fim da execução (último dia do intervalo carregado).",
    "dias_processados": "Dias do intervalo carregado (data_fim - data_inicio + 1); nulo em job sem esses parâmetros.",
    "fatias": "Linhas da tabela de sistema somadas nesta execução: execução que passa da virada da hora vem em fatias (L90).",
    "tentativa": "Número da tentativa da tarefa na mesma execução do job (1 = primeira).",
    "tentativas": "Total de tentativas da tarefa na mesma execução do job.",
    "pipeline_id": "Identificador do pipeline Lakeflow.",
    "pipeline": "Nome do pipeline Lakeflow.",
    "update_id": "Atualização (update) do pipeline.",
    "tipo_update": "Tipo do update (REFRESH, FULL_REFRESH...).",
    "espera_s": "Segundos entre o início da tarefa do job e o início do update: a subida da computação do pipeline.",
    "refresh_completo": "Verdadeiro quando o update refez tabelas do zero (full refresh).",
    "dia": "Dia.",
    "eventos_bronze": "Eventos gravados no bronze com esta data_extracao.",
    "linhas_fato": "Linhas da fato histórica na foto deste dia (data_referencia_sk).",
    "eventos_gravados": "Eventos gravados no bronze durante a execução (_ingestao_ts entre o início e o fim).",
    "dias_com_eventos": "Dias distintos de data_extracao gravados na execução.",
    "linhas_fato_gravadas": "Linhas gravadas na fato durante a execução (_carga_ts entre o início e o fim).",
    "fotos_gravadas": "Fotos (dias) gravadas na fato durante a execução.",
    "segundos_por_dia_processado": "Duração dividida pelos dias do intervalo, em segundos.",
    "segundos_por_mil_eventos": "Duração dividida pelos eventos gravados, em segundos por mil eventos.",
    "tipo": "job, tarefa ou pipeline.",
    "execucoes_base": "Execuções com sucesso na linha de base (as N mais recentes; em desvios, as N anteriores à execução).",
    "mediana_s": "Mediana da duração na linha de base, em segundos.",
    "p95_s": "Percentil 95 da duração na linha de base, em segundos (com poucas execuções fica perto do máximo).",
    "minimo_s": "Menor duração na linha de base, em segundos.",
    "maximo_s": "Maior duração na linha de base, em segundos.",
    "mediana_min": "Mediana da duração na linha de base, em minutos.",
    "p95_min": "Percentil 95 da duração na linha de base, em minutos.",
    "mediana_setup_s": "Mediana do tempo de preparação (setup) na linha de base, em segundos.",
    "mediana_execucao_s": "Mediana do tempo de execução (sem o setup) na linha de base, em segundos.",
    "limite_desvio_s": "Acima desta duração é desvio: o menor entre o p95 e 1,5 vez a mediana, em segundos.",
    "base_suficiente": "Verdadeiro quando a linha de base tem o mínimo de execuções (minimo_base).",
    "primeira_base": "Início (horário de Brasília) da execução mais antiga da linha de base.",
    "ultima_base": "Início (horário de Brasília) da execução mais recente da linha de base.",
    "timeout_sugerido_min": "Timeout sugerido para o job: 2 vezes o p95, em minutos, arredondado para cima (só para tipo job).",
    "execucao_id": "Execução avaliada: job_run_id, task_run_id ou update_id, conforme o tipo.",
    "mediana_base_s": "Mediana das N execuções com sucesso anteriores, em segundos.",
    "p95_base_s": "Percentil 95 das N execuções com sucesso anteriores, em segundos.",
    "acima_p95": "Verdadeiro quando a duração passou do p95 da base.",
    "acima_fator_mediana": "Verdadeiro quando a duração passou de 1,5 vez a mediana da base.",
    "excesso_s": "Quanto a duração passou do limite de desvio, em segundos.",
    "acima_mediana_pct": "Quanto a duração ficou acima da mediana da base, em %.",
    "excesso_setup_s": "Quanto o setup passou da mediana de setup da base, em segundos.",
    "mediana_dias_base": "Mediana dos dias processados nas execuções da base.",
    "provavel_causa": "Causa provável: espera por computação (setup), volume maior (mais dias que a base) ou lentidão com o mesmo volume.",
    "execucoes_agenda": "Execuções da agenda (gatilho CRON) no dia.",
    "execucoes_manuais": "Execuções manuais ou por API no dia (não contam para o SLA).",
    "em_andamento": "Execuções da agenda ainda em andamento no dia.",
    "meta_local": "Dia e hora meta no horário de Brasília.",
    "fim_agenda_local": "Fim da primeira execução da agenda com sucesso no dia (horário de Brasília).",
    "atraso_min": "Minutos depois da meta em que a execução da agenda terminou (0 = no prazo; nulo sem execução da agenda com sucesso).",
    "situacao": "no prazo, atrasada, atrasada (em andamento), em andamento, falhou, aguardando, sem execução da agenda ou agenda pausada.",
    "sla_estourado": "Verdadeiro quando a situação é atrasada, atrasada (em andamento), falhou ou sem execução da agenda.",
    "timeout_min": "Timeout do job em minutos (0 = sem timeout).",
    "dias_desde_ultima": "Dias entre a última execução e hoje.",
    "acima_mediana_min": "Quanto a última execução ficou acima da mediana do job, em minutos (negativo = abaixo).",
    "atraso_meta_min": "Minutos depois da meta em que a última execução terminou, só se ela veio da agenda.",
    "folga_projetada_min": "Folga até a meta se a execução começar na hora da agenda e durar o p95: meta - agenda - p95, em minutos.",
    "ordem": "Ordem da tarefa no job.",
    "o_que_faz": "O que a tarefa faz.",
    "sintoma_falha": "Como a falha aparece.",
    "acao_falha": "O que fazer quando a tarefa falha.",
    "sintoma_lentidao": "Como a lentidão aparece e o que é normal.",
    "acao_lentidao": "O que fazer quando a tarefa passa do normal.",
    "referencia": "Linha da matriz de resiliência do playbook (P28), lição (L##) ou visão onde olhar.",
    "ultima_situacao": "Resultado da execução mais recente da tarefa.",
    "ultima_execucao_local": "Início da execução mais recente da tarefa (horário de Brasília).",
    "tipo_ocorrencia": "SLA (meta estourada hoje) ou desvio (execução acima do normal nas últimas horas).",
    "quando_local": "Quando aconteceu (horário de Brasília): a meta do dia ou o início da execução.",
    "detalhe": "O que aconteceu, com os números.",
    "acao": "O que fazer (da matriz de resiliência por tarefa).",
}


def cols(*nomes, extra=None):
    extra = extra or {}
    return [(n, extra.get(n) or D[n]) for n in nomes]


# ------------------------------------------------------------------------------------------------ visões
def visoes():
    V = []
    V.append(("config_sustentacao", "Parâmetros da sustentação: fuso, tamanho da linha de base, critério de desvio, janela do alerta e calendário do SLA.",
              cols("fuso", "n_base", "minimo_base", "fator_mediana", "fator_timeout", "janela_alerta_h", "min_excesso_alerta_s", "dias_sla", "projeto",
                   "agenda_alerta"),
              f"SELECT '{FUSO}' AS fuso, {N_BASE} AS n_base, {MIN_BASE} AS minimo_base, {FATOR_MEDIANA} AS fator_mediana, "
              f"{FATOR_TIMEOUT} AS fator_timeout, {JANELA_ALERTA_H} AS janela_alerta_h, {MIN_EXCESSO_ALERTA_S} AS min_excesso_alerta_s, {DIAS_SLA} AS dias_sla, '{PROJETO}' AS projeto, "
              f"'{ALERTA_CRON}' AS agenda_alerta"))

    V.append(("config_sla", "Jobs com hora meta (SLA): a execução da agenda precisa terminar até esta hora, no horário de Brasília.",
              cols("job", "hora_meta", "motivo_meta"),
              "SELECT * FROM VALUES\n    " + ",\n    ".join(f"('{q(j)}', '{h}', '{q(m)}')" for j, h, m in SLA) + "\n  AS t(job, hora_meta, motivo_meta)"))

    V.append(("jobs_monitorados", "Jobs do projeto pos_venda (atribuição da FinOps), com a agenda, o timeout e a hora meta do SLA.",
              cols("job_id", "job", "projeto", "agenda_cron", "agenda_fuso", "hora_agenda", "agenda_pausada", "timeout_s", "apagado",
                   "hora_meta", "motivo_meta"),
              f"""WITH j AS (
  SELECT job_id, CASE WHEN startswith(name, '[dev ') THEN ltrim(substr(name, instr(name, ']') + 1)) ELSE name END AS job,
    trigger.schedule.quartz_cron_expression AS agenda_cron, trigger.schedule.timezone_id AS agenda_fuso,
    CASE WHEN trigger.schedule.quartz_cron_expression IS NOT NULL THEN coalesce(paused, trigger.paused, false) END AS agenda_pausada,
    timeout_seconds AS timeout_s, delete_time IS NOT NULL AS apagado
  FROM system.lakeflow.jobs QUALIFY row_number() OVER (PARTITION BY job_id ORDER BY change_time DESC) = 1),
p AS (
  SELECT j.*, g.projeto FROM j JOIN pos_venda.finops.config_atribuicao g ON g.tipo_recurso = 'job' AND j.job LIKE g.padrao
  QUALIFY row_number() OVER (PARTITION BY j.job_id ORDER BY g.ordem) = 1)
SELECT p.job_id, p.job, p.projeto, p.agenda_cron, p.agenda_fuso,
  CASE WHEN p.agenda_cron LIKE '0 % % * * ?' THEN concat(lpad(split(p.agenda_cron, ' ')[2], 2, '0'), ':', lpad(split(p.agenda_cron, ' ')[1], 2, '0')) END AS hora_agenda,
  p.agenda_pausada, p.timeout_s, p.apagado, s.hora_meta, s.motivo_meta
FROM p LEFT JOIN {S}.config_sla s ON s.job = p.job
WHERE p.projeto = '{PROJETO}'"""))

    V.append(("execucoes_job", "Uma linha por execução de job do projeto: início e fim (UTC e horário de Brasília), duração, fila, setup, resultado, gatilho e o intervalo carregado (system.lakeflow.job_run_timeline).",
              cols("job_id", "job", "job_run_id", "gatilho", "da_agenda", "inicio", "fim", "inicio_local", "fim_local", "dia_local", "duracao_s",
                   "duracao_min", "fila_s", "setup_s", "execucao_s", "resultado", "codigo_termino", "sucesso", "data_inicio_param",
                   "data_fim_param", "dias_processados", "fatias"),
              f"""WITH r AS (
  SELECT job_id, run_id, min(period_start_time) AS inicio, max(period_end_time) AS fim,
    max_by(result_state, period_end_time) AS resultado, max_by(termination_code, period_end_time) AS codigo_termino,
    max_by(trigger_type, period_end_time) AS gatilho, max_by(job_parameters, period_end_time) AS parametros,
    max_by(queue_duration_seconds, period_end_time) AS fila_s, max_by(setup_duration_seconds, period_end_time) AS setup_s,
    max_by(execution_duration_seconds, period_end_time) AS execucao_s, count(*) AS fatias
  FROM system.lakeflow.job_run_timeline GROUP BY job_id, run_id),
e AS (
  SELECT j.job_id, j.job, r.run_id AS job_run_id, r.gatilho, coalesce(r.gatilho = 'CRON', false) AS da_agenda, r.inicio, r.fim,
    {local("r.inicio")} AS inicio_local, {local("r.fim")} AS fim_local, CAST({local("r.inicio")} AS DATE) AS dia_local,
    round((unix_millis(r.fim) - unix_millis(r.inicio)) / 1000.0, 1) AS duracao_s,
    round((unix_millis(r.fim) - unix_millis(r.inicio)) / 60000.0, 2) AS duracao_min,
    r.fila_s, r.setup_s, r.execucao_s, coalesce(r.resultado, 'EM ANDAMENTO') AS resultado, r.codigo_termino,
    coalesce(r.resultado = 'SUCCEEDED', false) AS sucesso,
    try_cast(r.parametros['data_inicio']['value'] AS DATE) AS data_inicio_param,
    try_cast(r.parametros['data_fim']['value'] AS DATE) AS data_fim_param, r.fatias
  FROM r JOIN {S}.jobs_monitorados j ON j.job_id = r.job_id)
SELECT job_id, job, job_run_id, gatilho, da_agenda, inicio, fim, inicio_local, fim_local, dia_local, duracao_s, duracao_min, fila_s, setup_s,
  execucao_s, resultado, codigo_termino, sucesso, data_inicio_param, data_fim_param,
  datediff(data_fim_param, data_inicio_param) + 1 AS dias_processados, fatias
FROM e"""))

    V.append(("execucoes_tarefa", "Uma linha por execução de tarefa dos jobs do projeto: início, fim, duração, setup, execução, resultado e tentativas (system.lakeflow.job_task_run_timeline).",
              cols("job_id", "job", "job_run_id", "task_run_id", "tarefa", "gatilho", "da_agenda", "inicio", "fim", "inicio_local", "fim_local",
                   "dia_local", "duracao_s", "duracao_min", "setup_s", "execucao_s", "limpeza_s", "resultado", "codigo_termino", "sucesso",
                   "tentativa", "tentativas", "dias_processados", "fatias"),
              f"""WITH t AS (
  SELECT job_id, job_run_id, run_id, task_key, min(period_start_time) AS inicio, max(period_end_time) AS fim,
    max_by(result_state, period_end_time) AS resultado, max_by(termination_code, period_end_time) AS codigo_termino,
    max_by(setup_duration_seconds, period_end_time) AS setup_s, max_by(execution_duration_seconds, period_end_time) AS execucao_s,
    max_by(cleanup_duration_seconds, period_end_time) AS limpeza_s, count(*) AS fatias
  FROM system.lakeflow.job_task_run_timeline GROUP BY job_id, job_run_id, run_id, task_key)
SELECT e.job_id, e.job, t.job_run_id, t.run_id AS task_run_id, t.task_key AS tarefa, e.gatilho, e.da_agenda, t.inicio, t.fim,
  {local("t.inicio")} AS inicio_local, {local("t.fim")} AS fim_local, CAST({local("t.inicio")} AS DATE) AS dia_local,
  round((unix_millis(t.fim) - unix_millis(t.inicio)) / 1000.0, 1) AS duracao_s,
  round((unix_millis(t.fim) - unix_millis(t.inicio)) / 60000.0, 2) AS duracao_min,
  t.setup_s, t.execucao_s, t.limpeza_s, coalesce(t.resultado, 'EM ANDAMENTO') AS resultado, t.codigo_termino,
  coalesce(t.resultado = 'SUCCEEDED', false) AS sucesso,
  row_number() OVER (PARTITION BY t.job_run_id, t.task_key ORDER BY t.inicio) AS tentativa,
  count(*) OVER (PARTITION BY t.job_run_id, t.task_key) AS tentativas, e.dias_processados, t.fatias
FROM t JOIN {S}.execucoes_job e ON e.job_run_id = t.job_run_id"""))

    V.append(("atualizacoes_pipeline", "Uma linha por atualização (update) dos pipelines Lakeflow do projeto: duração, espera antes do update, resultado e a tarefa do job que disparou (system.lakeflow.pipeline_update_timeline).",
              cols("pipeline_id", "pipeline", "update_id", "tipo_update", "gatilho", "job", "job_run_id", "task_run_id", "inicio", "fim",
                   "inicio_local", "fim_local", "dia_local", "duracao_s", "duracao_min", "espera_s", "resultado", "sucesso", "refresh_completo",
                   "dias_processados", "fatias"),
              f"""WITH p AS (
  SELECT pipeline_id, name AS pipeline FROM system.lakeflow.pipelines
  QUALIFY row_number() OVER (PARTITION BY pipeline_id ORDER BY change_time DESC) = 1),
pp AS (
  SELECT p.*, g.projeto FROM p JOIN pos_venda.finops.config_atribuicao g ON g.tipo_recurso = 'pipeline' AND p.pipeline LIKE g.padrao
  QUALIFY row_number() OVER (PARTITION BY p.pipeline_id ORDER BY g.ordem) = 1),
u AS (
  SELECT pipeline_id, update_id, min(period_start_time) AS inicio, max(period_end_time) AS fim,
    max_by(result_state, period_end_time) AS resultado, max_by(update_type, period_end_time) AS tipo_update,
    max_by(trigger_type, period_end_time) AS gatilho, max_by(trigger_details.job_task.job_task_run_id, period_end_time) AS task_run_id,
    max(coalesce(size(full_refresh_selection), 0)) AS tabelas_refresh_completo, count(*) AS fatias
  FROM system.lakeflow.pipeline_update_timeline GROUP BY pipeline_id, update_id)
SELECT pp.pipeline_id, pp.pipeline, u.update_id, u.tipo_update, u.gatilho, t.job, t.job_run_id, u.task_run_id, u.inicio, u.fim,
  {local("u.inicio")} AS inicio_local, {local("u.fim")} AS fim_local, CAST({local("u.inicio")} AS DATE) AS dia_local,
  round((unix_millis(u.fim) - unix_millis(u.inicio)) / 1000.0, 1) AS duracao_s,
  round((unix_millis(u.fim) - unix_millis(u.inicio)) / 60000.0, 2) AS duracao_min,
  round((unix_millis(u.inicio) - unix_millis(t.inicio)) / 1000.0, 1) AS espera_s,
  coalesce(u.resultado, 'EM ANDAMENTO') AS resultado, coalesce(u.resultado = 'COMPLETED', false) AS sucesso,
  coalesce(u.tipo_update = 'FULL_REFRESH', false) OR u.tabelas_refresh_completo > 0 AS refresh_completo, t.dias_processados, u.fatias
FROM u JOIN pp ON pp.pipeline_id = u.pipeline_id AND pp.projeto = '{PROJETO}'
LEFT JOIN {S}.execucoes_tarefa t ON t.task_run_id = u.task_run_id"""))

    V.append(("volume_diario", "Volume por dia: eventos do bronze por data_extracao e linhas da fato histórica por foto (data_referencia_sk).",
              cols("dia", "eventos_bronze", "linhas_fato", extra={"dia": "Dia do evento (data_extracao) e da foto da fato."}),
              f"""WITH b AS (SELECT data_extracao AS dia, count(*) AS eventos_bronze FROM {BRONZE} GROUP BY data_extracao),
f AS (
  SELECT to_date(CAST(data_referencia_sk AS STRING), 'yyyyMMdd') AS dia, linhas_fato
  FROM (SELECT data_referencia_sk, count(*) AS linhas_fato FROM {FATO} GROUP BY data_referencia_sk))
SELECT coalesce(b.dia, f.dia) AS dia, coalesce(b.eventos_bronze, 0) AS eventos_bronze, coalesce(f.linhas_fato, 0) AS linhas_fato
FROM b FULL OUTER JOIN f ON f.dia = b.dia"""))

    jobs_vol = ", ".join(f"'{q(j)}'" for j in JOBS_COM_VOLUME)
    V.append(("volume_execucao", "Volume de cada execução da carga diária: dias do intervalo, eventos gravados no bronze e linhas gravadas na fato, com a duração. Separa lentidão de aumento de volume.",
              cols("job_id", "job", "job_run_id", "inicio_local", "dia_local", "resultado", "sucesso", "duracao_s", "duracao_min", "setup_s",
                   "execucao_s", "data_inicio_param", "data_fim_param", "dias_processados", "eventos_gravados", "dias_com_eventos",
                   "linhas_fato_gravadas", "fotos_gravadas", "segundos_por_dia_processado", "segundos_por_mil_eventos"),
              f"""WITH b AS (SELECT _ingestao_ts AS ts, count(*) AS eventos, count(DISTINCT data_extracao) AS dias FROM {BRONZE} GROUP BY _ingestao_ts),
f AS (SELECT _carga_ts AS ts, count(*) AS linhas, count(DISTINCT data_referencia_sk) AS fotos FROM {FATO} GROUP BY _carga_ts),
e AS (SELECT * FROM {S}.execucoes_job WHERE job IN ({jobs_vol})),
eb AS (SELECT e.job_run_id, sum(b.eventos) AS eventos, sum(b.dias) AS dias FROM e JOIN b ON b.ts BETWEEN e.inicio AND e.fim GROUP BY e.job_run_id),
ef AS (SELECT e.job_run_id, sum(f.linhas) AS linhas, sum(f.fotos) AS fotos FROM e JOIN f ON f.ts BETWEEN e.inicio AND e.fim GROUP BY e.job_run_id)
SELECT e.job_id, e.job, e.job_run_id, e.inicio_local, e.dia_local, e.resultado, e.sucesso, e.duracao_s, e.duracao_min, e.setup_s, e.execucao_s,
  e.data_inicio_param, e.data_fim_param, e.dias_processados, coalesce(eb.eventos, 0) AS eventos_gravados, coalesce(eb.dias, 0) AS dias_com_eventos,
  coalesce(ef.linhas, 0) AS linhas_fato_gravadas, coalesce(ef.fotos, 0) AS fotos_gravadas,
  round(e.duracao_s / nullif(e.dias_processados, 0), 1) AS segundos_por_dia_processado,
  round(1000 * e.duracao_s / nullif(eb.eventos, 0), 3) AS segundos_por_mil_eventos
FROM e LEFT JOIN eb ON eb.job_run_id = e.job_run_id LEFT JOIN ef ON ef.job_run_id = e.job_run_id"""))

    uniao = f"""SELECT 'job' AS tipo, job, '(job inteiro)' AS tarefa, job_run_id AS execucao_id, job_run_id, inicio, inicio_local, dia_local, duracao_s,
    setup_s, execucao_s, dias_processados FROM {S}.execucoes_job WHERE sucesso
  UNION ALL
  SELECT 'tarefa', job, tarefa, task_run_id, job_run_id, inicio, inicio_local, dia_local, duracao_s, setup_s, execucao_s, dias_processados
  FROM {S}.execucoes_tarefa WHERE sucesso
  UNION ALL
  SELECT 'pipeline', pipeline, '(update)', update_id, job_run_id, inicio, inicio_local, dia_local, duracao_s, CAST(NULL AS BIGINT), CAST(NULL AS BIGINT),
    dias_processados FROM {S}.atualizacoes_pipeline WHERE sucesso"""

    V.append(("linha_base", f"Linha de base de duração por job, tarefa e pipeline: mediana e p95 das últimas {N_BASE} execuções com sucesso, o limite de desvio e o timeout sugerido. Com menos de {MIN_BASE} execuções a base não vale.",
              cols("tipo", "job", "tarefa", "execucoes_base", "mediana_s", "p95_s", "minimo_s", "maximo_s", "mediana_min", "p95_min",
                   "mediana_setup_s", "mediana_execucao_s", "limite_desvio_s", "base_suficiente", "primeira_base", "ultima_base",
                   "timeout_sugerido_min", extra={"job": "Nome do job; para tipo pipeline, o nome do pipeline."}),
              f"""WITH x AS (
  {uniao}),
u AS (SELECT * FROM x QUALIFY row_number() OVER (PARTITION BY tipo, job, tarefa ORDER BY inicio DESC) <= {N_BASE}),
b AS (
  SELECT tipo, job, tarefa, count(*) AS execucoes_base, percentile(duracao_s, 0.5) AS med, percentile(duracao_s, 0.95) AS p95,
    min(duracao_s) AS minimo_s, max(duracao_s) AS maximo_s, percentile(setup_s, 0.5) AS mediana_setup_s,
    percentile(execucao_s, 0.5) AS mediana_execucao_s, min(inicio_local) AS primeira_base, max(inicio_local) AS ultima_base
  FROM u GROUP BY tipo, job, tarefa)
SELECT tipo, job, tarefa, execucoes_base, round(med, 1) AS mediana_s, round(p95, 1) AS p95_s, minimo_s, maximo_s,
  round(med / 60, 2) AS mediana_min, round(p95 / 60, 2) AS p95_min, round(mediana_setup_s, 1) AS mediana_setup_s,
  round(mediana_execucao_s, 1) AS mediana_execucao_s, round(least(p95, {FATOR_MEDIANA} * med), 1) AS limite_desvio_s,
  execucoes_base >= {MIN_BASE} AS base_suficiente, primeira_base, ultima_base,
  CASE WHEN tipo = 'job' THEN CAST(ceil({FATOR_TIMEOUT} * p95 / 60) AS INT) END AS timeout_sugerido_min
FROM b"""))

    V.append(("desvios", f"Execuções com sucesso acima do normal: duração acima do p95 ou de {FATOR_MEDIANA} vez a mediana das {N_BASE} execuções anteriores (mínimo de {MIN_BASE}), com o excesso e a causa provável.",
              cols("tipo", "job", "tarefa", "execucao_id", "job_run_id", "inicio_local", "dia_local", "duracao_s", "execucoes_base", "mediana_base_s",
                   "p95_base_s", "limite_desvio_s", "acima_p95", "acima_fator_mediana", "excesso_s", "acima_mediana_pct", "setup_s",
                   "excesso_setup_s", "dias_processados", "mediana_dias_base", "eventos_gravados", "provavel_causa",
                   extra={"job": "Nome do job; para tipo pipeline, o nome do pipeline.",
                          "execucoes_base": "Execuções com sucesso anteriores a esta na base móvel (até N)."}),
              f"""WITH x AS (
  {uniao}),
w AS (
  SELECT x.*, count(*) OVER w AS execucoes_base, percentile(duracao_s, 0.5) OVER w AS med, percentile(duracao_s, 0.95) OVER w AS p95,
    percentile(setup_s, 0.5) OVER w AS med_setup, percentile(dias_processados, 0.5) OVER w AS med_dias
  FROM x WINDOW w AS (PARTITION BY tipo, job, tarefa ORDER BY inicio ROWS BETWEEN {N_BASE} PRECEDING AND 1 PRECEDING)),
d AS (SELECT w.*, least(p95, {FATOR_MEDIANA} * med) AS limite FROM w WHERE execucoes_base >= {MIN_BASE})
SELECT d.tipo, d.job, d.tarefa, d.execucao_id, d.job_run_id, d.inicio_local, d.dia_local, d.duracao_s, d.execucoes_base,
  round(d.med, 1) AS mediana_base_s, round(d.p95, 1) AS p95_base_s, round(d.limite, 1) AS limite_desvio_s,
  d.duracao_s > d.p95 AS acima_p95, d.duracao_s > {FATOR_MEDIANA} * d.med AS acima_fator_mediana,
  round(d.duracao_s - d.limite, 1) AS excesso_s, round(100 * (d.duracao_s / d.med - 1), 1) AS acima_mediana_pct, d.setup_s,
  round(d.setup_s - d.med_setup, 1) AS excesso_setup_s, d.dias_processados, d.med_dias AS mediana_dias_base, v.eventos_gravados,
  CASE WHEN d.setup_s - d.med_setup >= 0.5 * (d.duracao_s - d.med) THEN 'espera por computação (setup)'
       WHEN d.dias_processados > {FATOR_MEDIANA} * d.med_dias THEN concat('volume maior: ', d.dias_processados, ' dias no intervalo (base: ', CAST(d.med_dias AS INT), ')')
       ELSE 'lentidão com o mesmo volume' END AS provavel_causa
FROM d LEFT JOIN {S}.volume_execucao v ON v.job_run_id = d.job_run_id
WHERE d.duracao_s > d.limite"""))

    V.append(("sla_diario", f"SLA dos jobs com hora meta, dia a dia (últimos {DIAS_SLA} dias, horário de Brasília): execuções da agenda e manuais, fim, atraso e situação. Só a execução da agenda conta para o SLA.",
              cols("dia", "job_id", "job", "hora_agenda", "hora_meta", "agenda_pausada", "execucoes_agenda", "execucoes_manuais", "em_andamento",
                   "meta_local", "fim_agenda_local", "atraso_min", "situacao", "sla_estourado", extra={"dia": "Dia no horário de Brasília."}),
              f"""WITH h AS (SELECT {HOJE} AS hoje, {AGORA} AS agora),
cal AS (SELECT explode(sequence(date_sub(hoje, {DIAS_SLA - 1}), hoje)) AS dia FROM h),
j AS (SELECT * FROM {S}.jobs_monitorados WHERE hora_meta IS NOT NULL AND NOT apagado),
g AS (
  SELECT c.dia, j.job_id, j.job, j.hora_agenda, j.hora_meta, j.agenda_pausada,
    count_if(e.da_agenda) AS execucoes_agenda, count_if(NOT e.da_agenda) AS execucoes_manuais,
    count_if(e.da_agenda AND e.resultado = 'EM ANDAMENTO') AS em_andamento,
    min(CASE WHEN e.da_agenda AND e.sucesso THEN e.fim_local END) AS fim_agenda_local
  FROM cal c CROSS JOIN j LEFT JOIN {S}.execucoes_job e ON e.job_id = j.job_id AND e.dia_local = c.dia
  GROUP BY c.dia, j.job_id, j.job, j.hora_agenda, j.hora_meta, j.agenda_pausada),
s AS (
  SELECT g.*, CAST(concat(CAST(g.dia AS STRING), ' ', g.hora_meta, ':00') AS TIMESTAMP_NTZ) AS meta_local, h.hoje, h.agora FROM g CROSS JOIN h),
t AS (
  SELECT s.*,
    CASE WHEN fim_agenda_local IS NOT NULL THEN greatest(0, round(timestampdiff(SECOND, meta_local, fim_agenda_local) / 60.0, 1)) END AS atraso_min,
    CASE WHEN fim_agenda_local IS NOT NULL AND fim_agenda_local <= meta_local THEN 'no prazo'
         WHEN fim_agenda_local IS NOT NULL THEN 'atrasada'
         WHEN em_andamento > 0 AND agora > meta_local THEN 'atrasada (em andamento)'
         WHEN em_andamento > 0 THEN 'em andamento'
         WHEN execucoes_agenda > 0 THEN 'falhou'
         WHEN agenda_pausada THEN 'agenda pausada'
         WHEN dia = hoje AND agora <= meta_local THEN 'aguardando'
         ELSE 'sem execução da agenda' END AS situacao
  FROM s)
SELECT dia, job_id, job, hora_agenda, hora_meta, agenda_pausada, execucoes_agenda, execucoes_manuais, em_andamento, meta_local, fim_agenda_local,
  atraso_min, situacao, situacao IN ('atrasada', 'atrasada (em andamento)', 'falhou', 'sem execução da agenda') AS sla_estourado
FROM t"""))

    V.append(("ultima_execucao", "Última execução de cada job do projeto, comparada com a linha de base, com o atraso sobre a meta (se veio da agenda), a folga projetada até a meta e o timeout sugerido.",
              cols("job_id", "job", "hora_agenda", "agenda_pausada", "hora_meta", "timeout_min", "timeout_sugerido_min", "job_run_id", "gatilho",
                   "inicio_local", "fim_local", "duracao_min", "resultado", "dias_desde_ultima", "execucoes_base", "mediana_min", "p95_min",
                   "base_suficiente", "acima_mediana_min", "atraso_meta_min", "folga_projetada_min"),
              f"""WITH u AS (SELECT * FROM {S}.execucoes_job QUALIFY row_number() OVER (PARTITION BY job_id ORDER BY inicio DESC) = 1),
b AS (SELECT * FROM {S}.linha_base WHERE tipo = 'job')
SELECT j.job_id, j.job, j.hora_agenda, j.agenda_pausada, j.hora_meta, round(j.timeout_s / 60.0, 1) AS timeout_min, b.timeout_sugerido_min,
  u.job_run_id, u.gatilho, u.inicio_local, u.fim_local, u.duracao_min, u.resultado, datediff({HOJE}, u.dia_local) AS dias_desde_ultima,
  b.execucoes_base, b.mediana_min, b.p95_min, b.base_suficiente, round(u.duracao_min - b.mediana_min, 2) AS acima_mediana_min,
  CASE WHEN u.da_agenda AND j.hora_meta IS NOT NULL THEN greatest(0, round(timestampdiff(SECOND,
    CAST(concat(CAST(u.dia_local AS STRING), ' ', j.hora_meta, ':00') AS TIMESTAMP_NTZ), u.fim_local) / 60.0, 1)) END AS atraso_meta_min,
  CASE WHEN j.hora_meta IS NOT NULL AND j.hora_agenda IS NOT NULL AND b.base_suficiente
       THEN round({minutos("j.hora_meta")} - {minutos("j.hora_agenda")} - b.p95_min, 1) END AS folga_projetada_min
FROM {S}.jobs_monitorados j LEFT JOIN u ON u.job_id = j.job_id LEFT JOIN b ON b.job = j.job
WHERE NOT j.apagado"""))

    linhas = ",\n    ".join(f"('{q(j)}', {o}, '{t}', '{q(a)}', '{q(b)}', '{q(c)}', '{q(d)}', '{q(e)}', '{q(r)}')"
                           for j, o, t, a, b, c, d, e, r in TAREFAS)
    V.append(("matriz_tarefas", "Matriz de resiliência por tarefa da carga diária (P28): o que a tarefa faz, sintoma e ação na falha e na lentidão, com a linha de base e a última execução.",
              cols("job", "ordem", "tarefa", "o_que_faz", "sintoma_falha", "acao_falha", "sintoma_lentidao", "acao_lentidao", "referencia",
                   "execucoes_base", "mediana_min", "p95_min", "mediana_setup_s", "ultima_situacao", "ultima_execucao_local"),
              f"""WITH m AS (
  SELECT * FROM VALUES
    {linhas}
  AS t(job, ordem, tarefa, o_que_faz, sintoma_falha, acao_falha, sintoma_lentidao, acao_lentidao, referencia)),
b AS (SELECT * FROM {S}.linha_base WHERE tipo = 'tarefa'),
u AS (SELECT job, tarefa, resultado, inicio_local FROM {S}.execucoes_tarefa QUALIFY row_number() OVER (PARTITION BY job, tarefa ORDER BY inicio DESC) = 1)
SELECT m.job, m.ordem, m.tarefa, m.o_que_faz, m.sintoma_falha, m.acao_falha, m.sintoma_lentidao, m.acao_lentidao, m.referencia,
  b.execucoes_base, b.mediana_min, b.p95_min, b.mediana_setup_s, u.resultado AS ultima_situacao, u.inicio_local AS ultima_execucao_local
FROM m LEFT JOIN b ON b.job = m.job AND b.tarefa = m.tarefa LEFT JOIN u ON u.job = m.job AND u.tarefa = m.tarefa"""))

    V.append(("alerta_sustentacao", f"O que o alerta SQL diário avisa: SLA estourado hoje e desvios da carga diária nas últimas {JANELA_ALERTA_H} horas que passaram do limite por {MIN_EXCESSO_ALERTA_S} s ou mais sem ser volume, com a ação da matriz por tarefa. Vazia = nada a fazer.",
              cols("tipo_ocorrencia", "job", "tarefa", "quando_local", "detalhe", "acao"),
              alerta_sql(JANELA_ALERTA_H)))
    return V


def alerta_sql(janela_h, hoje_apenas=True):
    filtro_sla = f"dia = {HOJE}" if hoje_apenas else f"dia >= date_sub({HOJE}, {max(1, janela_h // 24)})"
    return f"""SELECT 'SLA' AS tipo_ocorrencia, job, CAST(NULL AS STRING) AS tarefa, meta_local AS quando_local,
  concat('Situação: ', situacao, coalesce(concat('; terminou ', atraso_min, ' min depois da meta das ', hora_meta), ''),
         '; execuções da agenda no dia: ', execucoes_agenda) AS detalhe,
  'Ver a última execução em execucoes_tarefa e a matriz por tarefa; se a carga não rodou, rodar o job e avisar quem usa a foto do dia.' AS acao
FROM {S}.sla_diario WHERE sla_estourado AND {filtro_sla}
UNION ALL
SELECT 'desvio', d.job, d.tarefa, d.inicio_local,
  concat(d.tipo, ' durou ', round(d.duracao_s / 60, 1), ' min; mediana ', round(d.mediana_base_s / 60, 1), ' min, p95 ',
         round(d.p95_base_s / 60, 1), ' min (', d.execucoes_base, ' execuções); passou ', round(d.excesso_s / 60, 1),
         ' min do limite; causa provável: ', d.provavel_causa),
  coalesce(m.acao_lentidao, 'Comparar com a linha de base e o volume da execução (volume_execucao).')
FROM {S}.desvios d LEFT JOIN {S}.matriz_tarefas m ON m.job = d.job AND m.tarefa = d.tarefa
WHERE d.inicio_local >= timestampadd(HOUR, -{janela_h}, {AGORA})
  -- só os jobs diários (com hora meta) e o que eles disparam; o task runner do DQX Studio roda sob demanda e faria ruído
  AND d.job_run_id IN (SELECT job_run_id FROM {S}.execucoes_job WHERE job IN (SELECT job FROM {S}.config_sla))
  -- piso de ruído: com poucas execuções o p95 fica no máximo, e passar dele por segundos não pede ação
  AND d.excesso_s >= {MIN_EXCESSO_ALERTA_S} AND d.provavel_causa NOT LIKE 'volume maior%'"""


ESQUEMA = (f"CREATE SCHEMA IF NOT EXISTS {S} COMMENT 'Sustentação dos jobs e pipelines diários do pos_venda: execuções por job, tarefa e "
           f"pipeline, linha de base, desvios, SLA, volume e matriz de resiliência. Gerado por sustentacao/gerar_sustentacao.py.'")


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


# ------------------------------------------------------------------------------------------------ painel AI/BI
PAINEL = AQUI / "src" / "pos_venda_sustentacao.lvdash.json"
# Okabe-Ito (seguro para daltonismo); cores semânticas fixas à parte
PALETA = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00", "#56B4E9", "#F0E442"]
RUIM, BOM = "#D55E00", "#009E73"
MIN = {"type": "number", "decimalPlaces": {"type": "max", "places": 1}}
INT = {"type": "number", "abbreviation": "compact", "decimalPlaces": {"type": "max", "places": 1}}


def campo(c):
    return {"name": c, "expression": f"`{c}`"}


def pos(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def frame(titulo, descricao=None):
    f = {"showTitle": True, "title": titulo}
    if descricao:
        f.update({"showDescription": True, "description": descricao})
    return f


def texto(nome, linhas, p):
    return {"widget": {"name": nome, "multilineTextboxSpec": {"lines": linhas}}, "position": p}


def contador(nome, ds, coluna, titulo, p, fmt=None, descricao=None):
    enc = {"value": {"fieldName": coluna, "displayName": titulo}}
    if fmt:
        enc["value"]["format"] = fmt
    return {"widget": {"name": nome, "queries": [{"name": "main_query", "query": {"datasetName": ds, "fields": [campo(coluna)], "disaggregated": True}}],
                       "spec": {"version": 2, "widgetType": "counter", "encodings": enc, "frame": frame(titulo, descricao)}},
            "position": p}


def tabela(nome, ds, colunas, titulo, p, descricao=None):
    """colunas: lista de (coluna, rótulo, formato|None)."""
    enc = {"columns": [dict({"fieldName": c, "displayName": r}, **({"format": f} if f else {})) for c, r, f in colunas]}
    return {"widget": {"name": nome, "queries": [{"name": "main_query", "query": {"datasetName": ds, "fields": [campo(c) for c, *_ in colunas],
                                                                                "disaggregated": True}}],
                       "spec": {"version": 2, "widgetType": "table", "encodings": enc, "frame": frame(titulo, descricao)}},
            "position": p}


def barras_empilhadas(nome, ds, x, y, cor, titulo, p, x_rotulo, y_rotulo, descricao=None):
    fy = {"name": f"sum({y})", "expression": f"SUM(`{y}`)"}
    enc = {"x": {"fieldName": x, "scale": {"type": "categorical", "sort": {"by": "alphabetical"}}, "displayName": x_rotulo},
           "y": {"fieldName": fy["name"], "scale": {"type": "quantitative"}, "displayName": y_rotulo, "format": MIN},
           "color": {"fieldName": cor, "scale": {"type": "categorical"}, "displayName": "Tarefa"}}
    return {"widget": {"name": nome, "queries": [{"name": "main_query", "query": {"datasetName": ds, "fields": [campo(x), fy, campo(cor)],
                                                                                "disaggregated": False}}],
                       "spec": {"version": 3, "widgetType": "bar", "encodings": enc, "frame": frame(titulo, descricao)}},
            "position": p}


def barras_agrupadas(nome, ds, x, ys, titulo, p, x_rotulo, descricao=None):
    """ys: lista de (coluna, rótulo)."""
    fys = [{"name": f"sum({c})", "expression": f"SUM(`{c}`)"} for c, _ in ys]
    enc = {"x": {"fieldName": x, "scale": {"type": "categorical", "sort": {"by": "alphabetical"}}, "displayName": x_rotulo},
           "y": {"scale": {"type": "quantitative"}, "format": MIN,
                 "fields": [{"fieldName": f["name"], "displayName": r} for f, (_, r) in zip(fys, ys)]}}
    return {"widget": {"name": nome, "queries": [{"name": "main_query", "query": {"datasetName": ds, "fields": [campo(x)] + fys, "disaggregated": False}}],
                       "spec": {"version": 3, "widgetType": "bar", "encodings": enc, "frame": frame(titulo, descricao)}},
            "position": p}


def dispersao(nome, ds, x, y, cor, titulo, p, x_rotulo, y_rotulo, descricao=None):
    enc = {"x": {"fieldName": x, "scale": {"type": "quantitative"}, "displayName": x_rotulo, "format": INT},
           "y": {"fieldName": y, "scale": {"type": "quantitative"}, "displayName": y_rotulo, "format": MIN},
           "color": {"fieldName": cor, "scale": {"type": "categorical"}, "displayName": "Intervalo"}}
    return {"widget": {"name": nome, "queries": [{"name": "main_query", "query": {"datasetName": ds, "fields": [campo(x), campo(y), campo(cor)],
                                                                                "disaggregated": True}}],
                       "spec": {"version": 3, "widgetType": "scatter", "encodings": enc, "frame": frame(titulo, descricao)}},
            "position": p}


def datasets_painel():
    c, pl = q(CARGA), q(PIPELINE_CARGA)
    return [
        ("ds_resumo", "Resumo da carga diária", f"""SELECT
  (SELECT count(*) FROM execucoes_job WHERE job = '{c}') AS execucoes_carga,
  (SELECT execucoes_base FROM linha_base WHERE tipo = 'job' AND job = '{c}') AS execucoes_base,
  (SELECT mediana_min FROM linha_base WHERE tipo = 'job' AND job = '{c}') AS mediana_min,
  (SELECT p95_min FROM linha_base WHERE tipo = 'job' AND job = '{c}') AS p95_min,
  (SELECT folga_projetada_min FROM ultima_execucao WHERE job = '{c}') AS folga_projetada_min,
  (SELECT count(*) FROM desvios WHERE dia_local >= date_sub(current_date(), 30) AND job IN ('{c}', '{pl}')) AS desvios_30d,
  (SELECT count(*) FROM alerta_sustentacao) AS ocorrencias_alerta"""),
        ("ds_tarefas", "Duração por tarefa em cada execução da carga", f"""SELECT date_format(e.inicio_local, 'yyyy-MM-dd HH:mm') AS execucao, t.tarefa,
  t.duracao_min, t.setup_s, t.execucao_s, t.resultado
FROM execucoes_tarefa t JOIN execucoes_job e ON e.job_run_id = t.job_run_id
WHERE t.job = '{c}' AND t.resultado <> 'SKIPPED'
ORDER BY execucao, t.inicio"""),
        ("ds_base", "Linha de base por tarefa", f"""SELECT tipo, tarefa, execucoes_base, mediana_min, p95_min, round(limite_desvio_s / 60, 2) AS limite_min,
  mediana_setup_s, mediana_execucao_s, CASE WHEN base_suficiente THEN 'sim' ELSE 'não (poucas execuções)' END AS base_vale
FROM linha_base
WHERE job = '{c}' OR (tipo = 'pipeline' AND job = '{pl}')
ORDER BY CASE tipo WHEN 'job' THEN 0 WHEN 'pipeline' THEN 2 ELSE 1 END, mediana_min DESC"""),
        ("ds_volume", "Volume × duração por execução", f"""SELECT inicio_local, concat(dias_processados, CASE WHEN dias_processados = 1 THEN ' dia' ELSE ' dias' END) AS intervalo,
  dias_processados, eventos_gravados, linhas_fato_gravadas, duracao_min, setup_s, segundos_por_dia_processado
FROM volume_execucao WHERE sucesso ORDER BY inicio_local"""),
        ("ds_desvios", "Desvios", f"""SELECT inicio_local, tipo, tarefa, job, round(duracao_s / 60, 2) AS duracao_min, round(mediana_base_s / 60, 2) AS mediana_min,
  round(p95_base_s / 60, 2) AS p95_min, round(excesso_s / 60, 2) AS excesso_min, acima_mediana_pct, execucoes_base, provavel_causa
FROM desvios WHERE job IN ('{c}', '{pl}') ORDER BY inicio_local DESC"""),
        ("ds_sla", "SLA diário", """SELECT dia, job, hora_agenda, hora_meta, situacao, execucoes_agenda, execucoes_manuais, fim_agenda_local, atraso_min
FROM sla_diario ORDER BY dia DESC"""),
        ("ds_pipeline", "Updates do pipeline", f"""SELECT date_format(inicio_local, 'yyyy-MM-dd HH:mm') AS update_local, round(espera_s / 60, 2) AS espera_min, duracao_min,
  resultado, refresh_completo
FROM atualizacoes_pipeline WHERE pipeline = '{pl}' ORDER BY update_local"""),
        ("ds_matriz", "Matriz por tarefa", """SELECT ordem, tarefa, mediana_min, p95_min, ultima_situacao, sintoma_falha, acao_falha, sintoma_lentidao, acao_lentidao, referencia
FROM matriz_tarefas ORDER BY ordem"""),
        ("ds_ultima", "Última execução por job", """SELECT job, inicio_local, duracao_min, resultado, gatilho, mediana_min, p95_min, acima_mediana_min, hora_agenda,
  CASE WHEN agenda_pausada THEN 'pausada' WHEN hora_agenda IS NULL THEN 'sem agenda' ELSE 'ligada' END AS agenda, hora_meta, atraso_meta_min,
  folga_projetada_min, timeout_min, timeout_sugerido_min, dias_desde_ultima
FROM ultima_execucao ORDER BY inicio_local DESC NULLS LAST"""),
        ("ds_alerta", "Ocorrências para o alerta", """SELECT tipo_ocorrencia, job, tarefa, quando_local, detalhe, acao FROM alerta_sustentacao ORDER BY quando_local DESC"""),
    ]


def painel():
    linhas = lambda s: [l + "\n" for l in s.split("\n")]  # noqa: E731
    ds = [{"name": n, "displayName": d, "queryLines": linhas(s)} for n, d, s in datasets_painel()]
    hm = SLA[0][1]
    L = [
        texto("titulo", ["## Sustentação · tempo de execução da carga diária"], pos(0, 0, 12, 1)),
        texto("subtitulo", [
            f"Execuções, tarefas e updates do pipeline a partir de `system.lakeflow`. Linha de base: mediana e p95 das últimas {N_BASE} execuções "
            f"com sucesso (mínimo {MIN_BASE}). Desvio: acima do p95 ou de {FATOR_MEDIANA} vez a mediana. Meta: a carga termina até {hm} "
            f"(horário de Brasília), antes da avaliação do DQX Studio às 06:30. **Histórico curto:** as agendas estão pausadas e as "
            f"execuções foram manuais, em horários variados e com intervalos de 1 a 184 dias; trate a base como indicativa."],
            pos(0, 1, 12, 2)),
        contador("k_execucoes", "ds_resumo", "execucoes_carga", "Execuções da carga", pos(0, 3, 2, 3)),
        contador("k_mediana", "ds_resumo", "mediana_min", "Mediana da carga (min)", pos(2, 3, 2, 3), MIN),
        contador("k_p95", "ds_resumo", "p95_min", "p95 da carga (min)", pos(4, 3, 2, 3), MIN),
        contador("k_folga", "ds_resumo", "folga_projetada_min", f"Folga projetada até {hm} (min)", pos(6, 3, 2, 3), MIN,
                 "Meta menos a hora da agenda menos o p95. Vale para quando a agenda for ligada."),
        contador("k_desvios", "ds_resumo", "desvios_30d", "Desvios em 30 dias", pos(8, 3, 2, 3)),
        contador("k_alerta", "ds_resumo", "ocorrencias_alerta", "Ocorrências para o alerta", pos(10, 3, 2, 3),
                 descricao=f"SLA estourado hoje ou desvio da carga nas últimas {JANELA_ALERTA_H} h, {MIN_EXCESSO_ALERTA_S} s ou mais acima do limite e sem ser volume. É o que o alerta das 06:20 avisa."),
        barras_empilhadas("g_tarefas", "ds_tarefas", "execucao", "duracao_min", "tarefa", "Duração por tarefa em cada execução da carga",
                          pos(0, 6, 12, 6), "Execução (início, horário de Brasília)", "Minutos",
                          "Barras empilhadas: cada cor é uma tarefa. Tarefas puladas (SKIPPED) ficam de fora."),
        tabela("t_base", "ds_base", [("tipo", "Tipo", None), ("tarefa", "Tarefa", None), ("execucoes_base", "Execuções", None),
                                      ("mediana_min", "Mediana (min)", MIN), ("p95_min", "p95 (min)", MIN), ("limite_min", "Limite de desvio (min)", MIN),
                                      ("mediana_setup_s", "Setup mediano (s)", MIN), ("mediana_execucao_s", "Execução mediana (s)", MIN),
                                      ("base_vale", "Base vale?", None)],
               "Linha de base", pos(0, 12, 6, 7), "Setup = subida da computação; execução = o código. Separar os dois mostra se a demora é espera ou trabalho."),
        dispersao("g_volume", "ds_volume", "eventos_gravados", "duracao_min", "intervalo", "Volume × duração da carga", pos(6, 12, 6, 7),
                  "Eventos gravados no bronze", "Duração (min)",
                  "Cada ponto é uma execução com sucesso. Se a duração não sobe com o volume, o tempo é fixo (setup e subida do pipeline)."),
        tabela("t_desvios", "ds_desvios", [("inicio_local", "Início", None), ("tipo", "Tipo", None), ("tarefa", "Tarefa", None),
                                            ("duracao_min", "Duração (min)", MIN), ("mediana_min", "Mediana (min)", MIN), ("p95_min", "p95 (min)", MIN),
                                            ("excesso_min", "Passou do limite (min)", MIN), ("acima_mediana_pct", "Acima da mediana (%)", MIN),
                                            ("execucoes_base", "Execuções na base", None), ("provavel_causa", "Causa provável", None)],
               "Desvios", pos(0, 19, 12, 5), f"Base móvel: as {N_BASE} execuções com sucesso anteriores a cada uma."),
        tabela("t_sla", "ds_sla", [("dia", "Dia", None), ("situacao", "Situação", None), ("hora_agenda", "Agenda", None), ("hora_meta", "Meta", None),
                                    ("execucoes_agenda", "Da agenda", None), ("execucoes_manuais", "Manuais", None),
                                    ("fim_agenda_local", "Fim (agenda)", None), ("atraso_min", "Atraso (min)", MIN)],
               "SLA dia a dia", pos(0, 24, 6, 7), "Só a execução da agenda conta para o SLA. Com a agenda pausada, a situação é 'agenda pausada'."),
        barras_agrupadas("g_pipeline", "ds_pipeline", "update_local", [("espera_min", "Espera antes do update"), ("duracao_min", "Update")],
                         "Pipeline da silver: espera e update", pos(6, 24, 6, 7), "Update (início)",
                         "Espera = da tarefa silver_lakeflow começar até o update começar (subida da computação do pipeline)."),
        tabela("t_matriz", "ds_matriz", [("ordem", "#", None), ("tarefa", "Tarefa", None), ("mediana_min", "Mediana (min)", MIN),
                                          ("p95_min", "p95 (min)", MIN), ("ultima_situacao", "Última", None), ("sintoma_falha", "Sintoma de falha", None),
                                          ("acao_falha", "Ação na falha", None), ("sintoma_lentidao", "Lentidão: o que é normal", None),
                                          ("acao_lentidao", "Ação na lentidão", None), ("referencia", "Referência", None)],
               "Matriz de resiliência por tarefa (P28)", pos(0, 31, 12, 8)),
        tabela("t_ultima", "ds_ultima", [("job", "Job", None), ("inicio_local", "Última execução", None), ("duracao_min", "Duração (min)", MIN),
                                          ("resultado", "Resultado", None), ("gatilho", "Gatilho", None), ("mediana_min", "Mediana (min)", MIN),
                                          ("acima_mediana_min", "Acima da mediana (min)", MIN), ("agenda", "Agenda", None),
                                          ("hora_meta", "Meta", None), ("atraso_meta_min", "Atraso na meta (min)", MIN),
                                          ("folga_projetada_min", "Folga projetada (min)", MIN), ("timeout_min", "Timeout (min)", MIN),
                                          ("timeout_sugerido_min", "Timeout sugerido (min)", None), ("dias_desde_ultima", "Dias desde a última", None)],
               "Última execução de cada job do projeto", pos(0, 39, 12, 6),
               "Timeout sugerido = 2 × p95 (regra PLT03 da conformidade). Atraso na meta só para execução da agenda."),
        tabela("t_alerta", "ds_alerta", [("tipo_ocorrencia", "Tipo", None), ("job", "Job", None), ("tarefa", "Tarefa", None),
                                          ("quando_local", "Quando", None), ("detalhe", "Detalhe", None), ("acao", "Ação", None)],
               "O que o alerta avisaria agora", pos(0, 45, 12, 4), "Vazio = nada a fazer."),
    ]
    return {
        "datasets": ds,
        "pages": [{"name": "sustentacao", "displayName": "Sustentação", "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1", "layout": L}],
        "uiSettings": {"theme": {
            "canvasBackgroundColor": {"light": "#FAFAFA", "dark": "#1F272D"}, "widgetBackgroundColor": {"light": "#FFFFFF", "dark": "#11171C"},
            "widgetBorderColor": {"light": "#FFFFFF", "dark": "#11171C"}, "fontColor": {"light": "#11171C", "dark": "#E8ECF0"},
            "selectionColor": {"light": "#2272B4", "dark": "#8ACAFF"}, "visualizationColors": PALETA, "widgetHeaderAlignment": "LEFT"}},
    }


def conferir_painel(p):
    """Estrutura: campos × encodings, versões e grade de 12 colunas sem buraco."""
    erros = []
    nomes_ds = {d["name"] for d in p["datasets"]}
    versoes = {"counter": 2, "table": 2, "bar": 3, "scatter": 3}
    linhas = {}
    for item in p["pages"][0]["layout"]:
        w, ps = item["widget"], item["position"]
        linhas.setdefault(ps["y"], []).append((ps["x"], ps["width"], ps["height"]))
        if "spec" not in w:
            continue
        spec = w["spec"]
        if spec["version"] != versoes[spec["widgetType"]]:
            erros.append(f"{w['name']}: versão {spec['version']} para {spec['widgetType']}")
        campos = {f["name"] for qq in w["queries"] for f in qq["query"]["fields"]}
        if any(qq["query"]["datasetName"] not in nomes_ds for qq in w["queries"]):
            erros.append(f"{w['name']}: conjunto de dados inexistente")
        enc = spec["encodings"]
        usados = [c["fieldName"] for c in enc.get("columns", [])]
        for k in ("x", "y", "color", "value"):
            if k in enc:
                usados += [f["fieldName"] for f in enc[k].get("fields", [])] or [enc[k]["fieldName"]]
        faltam = [u for u in usados if u not in campos]
        if faltam:
            erros.append(f"{w['name']}: encodings sem campo na consulta: {faltam}")
    for y, itens in linhas.items():
        itens.sort()
        x = 0
        for xi, wi, _ in itens:
            if xi < x:
                erros.append(f"linha y={y}: sobreposição em x={xi}")
            x = max(x, xi + wi)
    ocupado = {}
    for item in p["pages"][0]["layout"]:
        ps = item["position"]
        for yy in range(ps["y"], ps["y"] + ps["height"]):
            for xx in range(ps["x"], ps["x"] + ps["width"]):
                if (xx, yy) in ocupado:
                    erros.append(f"{item['widget']['name']} sobrepõe {ocupado[(xx, yy)]} em ({xx},{yy})")
                ocupado[(xx, yy)] = item["widget"]["name"]
    altura = max(y for _, y in ocupado) + 1
    buracos = [(x, y) for y in range(altura) for x in range(12) if (x, y) not in ocupado]
    if buracos:
        erros.append(f"{len(buracos)} células vazias na grade, a primeira em {buracos[0]}")
    return erros


# ------------------------------------------------------------------------------------------------ bundle (painel + alerta)
def bundle_yml():
    hm = SLA[0][1]
    return f"""# Gerado por sustentacao/gerar_sustentacao.py: não edite à mão.
resources:
  dashboards:
    painel_sustentacao:
      display_name: "pos_venda · Sustentação"
      file_path: ../src/pos_venda_sustentacao.lvdash.json
      warehouse_id: ${{var.warehouse_id}}
      # as consultas usam nomes simples de view; catálogo e schema vêm daqui
      dataset_catalog: pos_venda
      dataset_schema: {ESQ}
      embed_credentials: true

  alerts:
    alerta_sustentacao:
      display_name: "{ALERTA_NOME}"
      custom_summary: "Sustentação do pos_venda: SLA estourado ou desvio de duração"
      custom_description: >-
        A carga diária passou da meta das {hm} (horário de Brasília) ou alguma execução passou do normal
        (acima do p95 ou de {FATOR_MEDIANA} vez a mediana). Veja {S}.alerta_sustentacao e a página Sustentação do painel.
      query_text: "SELECT count(*) AS ocorrencias FROM {S}.alerta_sustentacao"
      warehouse_id: ${{var.warehouse_id}}
      evaluation:
        comparison_operator: GREATER_THAN
        source:
          name: ocorrencias
          display: ocorrencias
        threshold:
          value:
            double_value: 0
        empty_result_state: OK
        notification:
          notify_on_ok: false
          subscriptions:
            - user_email: ${{workspace.current_user.userName}}
      schedule:
        # 1 disparo por dia (regra PLT06: até 4), depois da meta e antes da avaliação do DQX Studio às 06:30
        quartz_cron_schedule: "{ALERTA_CRON}"
        timezone_id: {FUSO}
        pause_status: ${{var.alerta_status}}
"""


# ------------------------------------------------------------------------------------------------ comandos
def cmd_gerar():
    V = visoes()
    partes = [ESQUEMA] + [ddl(*v) for v in V]
    (AQUI / "sustentacao.sql").write_text(";\n\n".join(partes) + ";\n", encoding="utf-8")
    p = painel()
    erros = conferir_painel(p)
    if erros:
        sys.exit("painel com problema:\n  " + "\n  ".join(erros))
    PAINEL.parent.mkdir(exist_ok=True)
    PAINEL.write_text(json.dumps(p, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (AQUI / "resources").mkdir(exist_ok=True)
    (AQUI / "resources" / "sustentacao.yml").write_text(bundle_yml(), encoding="utf-8")
    print(f"sustentacao/sustentacao.sql: schema + {len(V)} visões; painel com {len(p['datasets'])} conjuntos e "
          f"{len(p['pages'][0]['layout'])} widgets (estrutura ok); resources/sustentacao.yml (painel + alerta)")
    return V


def inline(consulta, V):
    """Troca as referências a {S}.<visão> por CTEs com a consulta da visão, para testar sem criar nada."""
    corpo = {n: c for n, _, _, c in V}
    ordem = [n for n, *_ in V]
    precisa, fila = set(), [consulta]
    while fila:
        t = fila.pop()
        for n in ordem:
            if f"{S}.{n}" in t and n not in precisa:
                precisa.add(n)
                fila.append(corpo[n])
    ctes = [f"{n} AS (\n{corpo[n].replace(S + '.', '')}\n)" for n in ordem if n in precisa]
    principal = consulta.replace(S + ".", "")
    return ("WITH " + ",\n".join(ctes) + ",\n__v AS (\n" + principal + "\n)\nSELECT * FROM __v") if ctes else principal


def cmd_testar():
    """Roda cada visão e cada conjunto do painel com as dependências embutidas: não cria objeto nenhum."""
    V = cmd_gerar()
    erros = 0
    print("== visões (sem criar)")
    for nome, _, colunas, consulta in V:
        try:
            linhas = sql(f"SELECT count(*) AS n FROM (\n{inline(consulta, V)}\n)")
            print(f"  ok    {nome:24} {linhas[0]['n']} linhas")
        except RuntimeError as e:
            erros += 1
            print(f"  ERRO  {nome:24} {str(e)[-300:]}")
    print("== conjuntos do painel (sem criar)")
    for nome, _, consulta in datasets_painel():
        tabela_ref = re.sub(r"\b(FROM|JOIN)\s+([a-z_]+)\b", lambda m: f"{m.group(1)} {S}.{m.group(2)}", consulta)
        try:
            linhas = sql(f"SELECT count(*) AS n FROM (\n{inline(tabela_ref, V)}\n)")
            print(f"  ok    {nome:24} {linhas[0]['n']} linhas")
        except RuntimeError as e:
            erros += 1
            print(f"  ERRO  {nome:24} {str(e)[-300:]}")
    print("teste:", "ok" if not erros else f"{erros} problema(s)")
    return erros


def cmd_aplicar():
    V = cmd_gerar()
    sql(ESQUEMA)
    atuais = {r["table_name"]: norm(r["view_definition"]) for r in
              sql(f"SELECT table_name, view_definition FROM pos_venda.information_schema.views WHERE table_schema = '{ESQ}'")}
    coment = {}
    for r in sql(f"SELECT table_name, column_name, comment FROM pos_venda.information_schema.columns WHERE table_schema = '{ESQ}'"):
        coment.setdefault(r["table_name"], {})[r["column_name"]] = r["comment"] or ""
    for nome, comentario, colunas, consulta in V:
        if atuais.get(nome) == norm(consulta) and coment.get(nome) == {c: d for c, d in colunas}:
            sql(f"COMMENT ON TABLE {S}.{nome} IS '{q(comentario)}'")     # mantém a descrição em dia sem recriar
            print(f"igual     {nome}")
            continue
        sql(ddl(nome, comentario, colunas, consulta))
        print(f"{'recriada' if nome in atuais else 'criada  '}  {nome}")


def cmd_conferir():
    V = visoes()
    erros = 0
    contagem = {}
    print("== cada visão responde")
    for nome, *_ in V:
        try:
            contagem[nome] = int(sql(f"SELECT count(*) AS n FROM {S}.{nome}")[0]["n"] or 0)
            print(f"  ok    {nome:24} {contagem[nome]}")
        except RuntimeError as e:
            erros += 1
            print(f"  ERRO  {nome:24} {str(e)[-200:]}")
    print("== cada conjunto do painel responde (com catálogo e schema do bundle, como no painel)")
    conjuntos = {}
    for nome, _, consulta in datasets_painel():
        estado, erro, linhas = executar(consulta, catalogo="pos_venda", schema=ESQ)
        conjuntos[nome] = len(linhas) if estado == "SUCCEEDED" else None
        erros += estado != "SUCCEEDED"
        print(f"  {'ok  ' if estado == 'SUCCEEDED' else 'ERRO'}  {nome:24} {conjuntos[nome] if estado == 'SUCCEEDED' else erro[:200]}")
    print("== contagens")
    c = q(CARGA)
    r = sql(f"""WITH j AS (SELECT job_id FROM {S}.jobs_monitorados),
p AS (SELECT DISTINCT pipeline_id FROM {S}.atualizacoes_pipeline)
SELECT
  (SELECT count(DISTINCT run_id) FROM system.lakeflow.job_run_timeline WHERE job_id IN (SELECT job_id FROM j)) AS runs_sistema,
  (SELECT count(*) FROM {S}.execucoes_job) AS runs_visao,
  (SELECT count(DISTINCT run_id) FROM system.lakeflow.job_task_run_timeline WHERE job_id IN (SELECT job_id FROM j)) AS tarefas_sistema,
  (SELECT count(*) FROM {S}.execucoes_tarefa) AS tarefas_visao,
  (SELECT count(DISTINCT update_id) FROM system.lakeflow.pipeline_update_timeline WHERE pipeline_id IN (SELECT pipeline_id FROM p)) AS updates_sistema,
  (SELECT count(*) FROM {S}.atualizacoes_pipeline) AS updates_visao,
  (SELECT count(*) FROM {S}.atualizacoes_pipeline WHERE gatilho = 'JOB_TASK' AND job_run_id IS NULL) AS updates_sem_tarefa,
  (SELECT count(*) FROM {BRONZE}) AS linhas_bronze,
  (SELECT sum(eventos_bronze) FROM {S}.volume_diario) AS bronze_volume_diario,
  (SELECT sum(eventos_gravados) FROM {S}.volume_execucao) AS bronze_volume_execucao,
  (SELECT count(*) FROM {FATO}) AS linhas_fato,
  (SELECT sum(linhas_fato) FROM {S}.volume_diario) AS fato_volume_diario,
  (SELECT sum(linhas_fato_gravadas) FROM {S}.volume_execucao) AS fato_volume_execucao,
  (SELECT count(*) FROM {S}.execucoes_job WHERE job = '{c}') AS execucoes_carga,
  (SELECT count(*) FROM {S}.execucoes_job WHERE job = '{c}' AND sucesso) AS sucessos_carga,
  (SELECT execucoes_base FROM {S}.linha_base WHERE tipo = 'job' AND job = '{c}') AS base_carga,
  (SELECT max(execucoes_base) FROM {S}.linha_base) AS maior_base,
  (SELECT count(*) FROM {S}.desvios WHERE execucoes_base < {MIN_BASE} OR duracao_s <= limite_desvio_s) AS desvios_invalidos,
  (SELECT count(DISTINCT tarefa) FROM {S}.execucoes_tarefa WHERE job = '{c}') AS tarefas_carga,
  (SELECT count(DISTINCT t.tarefa) FROM {S}.execucoes_tarefa t JOIN {S}.matriz_tarefas m ON m.job = t.job AND m.tarefa = t.tarefa
     WHERE t.job = '{c}') AS tarefas_na_matriz,
  (SELECT count(*) FROM {S}.sla_diario) AS linhas_sla,
  (SELECT count(*) FROM {S}.jobs_monitorados WHERE hora_meta IS NOT NULL AND NOT apagado) AS jobs_com_sla,
  (SELECT count(*) FROM pos_venda.information_schema.columns WHERE table_schema = '{ESQ}' AND (comment IS NULL OR comment = '')) AS colunas_sem_descricao,
  (SELECT count(*) FROM pos_venda.information_schema.tables WHERE table_schema = '{ESQ}' AND (comment IS NULL OR comment = '')) AS visoes_sem_descricao""")[0]
    n = {k: (int(v) if v is not None else None) for k, v in r.items()}
    # a mediana da linha de base é a mesma calculada direto na tabela de sistema (últimas N com sucesso)
    m = sql(f"""WITH t AS (
  SELECT run_id, task_key, min(period_start_time) AS inicio, (unix_millis(max(period_end_time)) - unix_millis(min(period_start_time))) / 1000.0 AS d,
    max_by(result_state, period_end_time) AS r
  FROM system.lakeflow.job_task_run_timeline WHERE job_id IN (SELECT job_id FROM {S}.jobs_monitorados WHERE job = '{c}') GROUP BY run_id, task_key),
u AS (SELECT * FROM t WHERE r = 'SUCCEEDED' QUALIFY row_number() OVER (PARTITION BY task_key ORDER BY inicio DESC) <= {N_BASE})
SELECT u.task_key, round(percentile(u.d, 0.5), 1) AS direto, b.mediana_s AS visao, count(*) AS n, b.execucoes_base
FROM u JOIN {S}.linha_base b ON b.tipo = 'tarefa' AND b.job = '{c}' AND b.tarefa = u.task_key
GROUP BY u.task_key, b.mediana_s, b.execucoes_base""")
    medianas_iguais = all(abs(float(x["direto"]) - float(x["visao"])) < 0.11 and x["n"] == x["execucoes_base"] for x in m) and len(m) > 0
    # teste do alerta: a mesma consulta, com 30 dias em vez de 24 h, mostra que ele dispararia
    a30 = sql(f"SELECT count(*) AS n FROM (\n{alerta_sql(24 * 30, hoje_apenas=False)}\n)")[0]["n"]
    n["alerta_30_dias"] = int(a30)
    n["alerta_agora"] = contagem.get("alerta_sustentacao")
    checks = [
        ("execuções de job = run_id da tabela de sistema", n["runs_visao"] == n["runs_sistema"], f"{n['runs_visao']} = {n['runs_sistema']}"),
        ("execuções de tarefa = run_id da tabela de sistema", n["tarefas_visao"] == n["tarefas_sistema"], f"{n['tarefas_visao']} = {n['tarefas_sistema']}"),
        ("updates do pipeline = update_id da tabela de sistema", n["updates_visao"] == n["updates_sistema"], f"{n['updates_visao']} = {n['updates_sistema']}"),
        ("todo update disparado por job tem a tarefa", n["updates_sem_tarefa"] == 0, f"{n['updates_sem_tarefa']} sem tarefa"),
        ("bronze: volume por dia = volume por execução = tabela", n["linhas_bronze"] == n["bronze_volume_diario"] == n["bronze_volume_execucao"],
         f"{n['linhas_bronze']} = {n['bronze_volume_diario']} = {n['bronze_volume_execucao']}"),
        ("fato: volume por dia = volume por execução = tabela", n["linhas_fato"] == n["fato_volume_diario"] == n["fato_volume_execucao"],
         f"{n['linhas_fato']} = {n['fato_volume_diario']} = {n['fato_volume_execucao']}"),
        ("linha de base da carga = sucessos (até N)", n["base_carga"] == min(n["sucessos_carga"], N_BASE) and n["maior_base"] <= N_BASE,
         f"{n['base_carga']} = min({n['sucessos_carga']}, {N_BASE}); maior base {n['maior_base']}"),
        ("medianas por tarefa = cálculo direto na tabela de sistema", medianas_iguais, f"{len(m)} tarefas comparadas"),
        ("desvios só com base suficiente e acima do limite", n["desvios_invalidos"] == 0, f"{n['desvios_invalidos']} fora da regra"),
        ("toda tarefa da carga tem sintoma e ação na matriz", n["tarefas_na_matriz"] == n["tarefas_carga"],
         f"{n['tarefas_na_matriz']} de {n['tarefas_carga']}"),
        ("SLA: um dia por linha no calendário", n["linhas_sla"] == DIAS_SLA * n["jobs_com_sla"], f"{n['linhas_sla']} = {DIAS_SLA} × {n['jobs_com_sla']}"),
        ("toda coluna e toda visão descritas", n["colunas_sem_descricao"] == 0 and n["visoes_sem_descricao"] == 0,
         f"{n['colunas_sem_descricao']} colunas e {n['visoes_sem_descricao']} visões sem descrição"),
        ("alerta: a consulta responde (e com 30 dias acharia ocorrências)", n["alerta_agora"] is not None,
         f"agora {n['alerta_agora']}; com 30 dias {n['alerta_30_dias']}"),
    ]
    for nome, ok, det in checks:
        erros += not ok
        print(f"  {'ok  ' if ok else 'ERRO'}  {nome:58} {det}")
    base = sql(f"""SELECT tipo, job, tarefa, execucoes_base, mediana_min, p95_min, mediana_setup_s, mediana_execucao_s, base_suficiente
FROM {S}.linha_base WHERE job IN ('{c}', '{q(PIPELINE_CARGA)}') ORDER BY tipo, tarefa""")
    resumo = sql(f"SELECT * FROM {S}.ultima_execucao WHERE job = '{c}'")
    desv = sql(f"SELECT tipo, tarefa, inicio_local, duracao_s, mediana_base_s, p95_base_s, excesso_s, provavel_causa FROM {S}.desvios ORDER BY inicio_local")
    vol = sql(f"""SELECT inicio_local, dias_processados, eventos_gravados, linhas_fato_gravadas, duracao_min, segundos_por_dia_processado
FROM {S}.volume_execucao WHERE sucesso ORDER BY inicio_local""")
    (AQUI / "conferencia.json").write_text(json.dumps({
        "conferido_em": datetime.date.today().isoformat(), "visoes": contagem, "conjuntos_painel": conjuntos, "contagens": n,
        "checks": [{"check": nome, "ok": bool(o), "detalhe": d} for nome, o, d in checks],
        "medianas_por_tarefa": m, "linha_base_carga": base, "ultima_execucao_carga": resumo, "desvios": desv, "volume_por_execucao": vol},
        ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    print("conferência:", "ok" if not erros else f"{erros} problema(s)")
    return erros


if __name__ == "__main__":
    acao = sys.argv[1] if len(sys.argv) > 1 else "gerar"
    try:
        if acao == "gerar":
            cmd_gerar()
        elif acao == "testar":
            sys.exit(1 if cmd_testar() else 0)
        elif acao == "aplicar":
            cmd_aplicar()
        elif acao == "conferir":
            sys.exit(1 if cmd_conferir() else 0)
        else:
            sys.exit(__doc__)
    except CotaEsgotada as e:
        sys.exit(f"warehouse indisponível (cota diária do Free Edition): {e}")
