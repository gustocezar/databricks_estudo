CREATE SCHEMA IF NOT EXISTS pos_venda.sustentacao COMMENT 'Sustentação dos jobs e pipelines diários do pos_venda: execuções por job, tarefa e pipeline, linha de base, desvios, SLA, volume e matriz de resiliência. Gerado por sustentacao/gerar_sustentacao.py.';

CREATE OR REPLACE VIEW pos_venda.sustentacao.config_sustentacao (
  fuso COMMENT 'Fuso das colunas *_local, da agenda e da meta (America/Sao_Paulo, horário de Brasília).',
  n_base COMMENT 'Quantas execuções com sucesso, das mais recentes, formam a linha de base.',
  minimo_base COMMENT 'Mínimo de execuções com sucesso para a linha de base valer; abaixo disso não se aponta desvio.',
  fator_mediana COMMENT 'Fator sobre a mediana: acima dele a execução é desvio, mesmo abaixo do p95.',
  fator_timeout COMMENT 'Fator sobre o p95 do job para sugerir o timeout (regra PLT03 da conformidade).',
  janela_alerta_h COMMENT 'Horas para trás em que o alerta procura desvios.',
  min_excesso_alerta_s COMMENT 'Segundos acima do limite para o desvio entrar no alerta (abaixo disso, ou explicado por volume, fica só no painel).',
  dias_sla COMMENT 'Dias do calendário do SLA (sla_diario).',
  projeto COMMENT 'Projeto dono do job ou do pipeline, pela atribuição da FinOps (pos_venda.finops.config_atribuicao).',
  agenda_alerta COMMENT 'Agenda (cron Quartz, horário de Brasília) do alerta SQL de sustentação.'
)
COMMENT 'Parâmetros da sustentação: fuso, tamanho da linha de base, critério de desvio, janela do alerta e calendário do SLA.'
AS SELECT 'America/Sao_Paulo' AS fuso, 20 AS n_base, 5 AS minimo_base, 1.5 AS fator_mediana, 2 AS fator_timeout, 24 AS janela_alerta_h, 60 AS min_excesso_alerta_s, 30 AS dias_sla, 'pos_venda' AS projeto, '0 20 6 * * ?' AS agenda_alerta;

CREATE OR REPLACE VIEW pos_venda.sustentacao.config_sla (
  job COMMENT 'Nome do job (sem o prefixo [dev usuário] do bundle).',
  hora_meta COMMENT 'Hora meta (HH:mm, horário de Brasília) para a execução da agenda terminar.',
  motivo_meta COMMENT 'Por que a hora meta é esta.'
)
COMMENT 'Jobs com hora meta (SLA): a execução da agenda precisa terminar até esta hora, no horário de Brasília.'
AS SELECT * FROM VALUES
    ('pos_venda_carga_diaria', '06:15', 'A carga precisa terminar antes da avaliação agendada do DQX Studio às 06:30, que lê a foto do dia (P11).')
  AS t(job, hora_meta, motivo_meta);

CREATE OR REPLACE VIEW pos_venda.sustentacao.jobs_monitorados (
  job_id COMMENT 'Identificador do job.',
  job COMMENT 'Nome do job (sem o prefixo [dev usuário] do bundle).',
  projeto COMMENT 'Projeto dono do job ou do pipeline, pela atribuição da FinOps (pos_venda.finops.config_atribuicao).',
  agenda_cron COMMENT 'Agenda do job (cron Quartz), de system.lakeflow.jobs; nulo se o job não tem agenda.',
  agenda_fuso COMMENT 'Fuso da agenda do job.',
  hora_agenda COMMENT 'Hora de início da agenda diária (HH:mm), lida do cron; nula se a agenda não é diária simples.',
  agenda_pausada COMMENT 'Verdadeiro quando a agenda do job está pausada (situação de hoje); nulo quando o job não tem agenda.',
  timeout_s COMMENT 'Timeout do job em segundos (0 = sem timeout).',
  apagado COMMENT 'Verdadeiro quando o job foi apagado do workspace.',
  hora_meta COMMENT 'Hora meta (HH:mm, horário de Brasília) para a execução da agenda terminar.',
  motivo_meta COMMENT 'Por que a hora meta é esta.'
)
COMMENT 'Jobs do projeto pos_venda (atribuição da FinOps), com a agenda, o timeout e a hora meta do SLA.'
AS WITH j AS (
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
FROM p LEFT JOIN pos_venda.sustentacao.config_sla s ON s.job = p.job
WHERE p.projeto = 'pos_venda';

CREATE OR REPLACE VIEW pos_venda.sustentacao.execucoes_job (
  job_id COMMENT 'Identificador do job.',
  job COMMENT 'Nome do job (sem o prefixo [dev usuário] do bundle).',
  job_run_id COMMENT 'Execução do job (run_id em job_run_timeline).',
  gatilho COMMENT 'O que disparou a execução: CRON (agenda), ONETIME (manual ou API), PERIODIC, JOB_TASK (update do pipeline pela tarefa) etc.',
  da_agenda COMMENT 'Verdadeiro quando a execução veio da agenda (gatilho CRON). Só estas contam para o SLA.',
  inicio COMMENT 'Início da execução em UTC.',
  fim COMMENT 'Fim da execução em UTC.',
  inicio_local COMMENT 'Início no horário de Brasília.',
  fim_local COMMENT 'Fim no horário de Brasília.',
  dia_local COMMENT 'Dia do início no horário de Brasília.',
  duracao_s COMMENT 'Duração de ponta a ponta, em segundos (fim - início).',
  duracao_min COMMENT 'Duração de ponta a ponta, em minutos.',
  fila_s COMMENT 'Tempo na fila antes de começar, em segundos (system.lakeflow).',
  setup_s COMMENT 'Tempo de preparação (subida da computação), em segundos (system.lakeflow).',
  execucao_s COMMENT 'Tempo de execução propriamente dito, em segundos (system.lakeflow).',
  resultado COMMENT 'Resultado da execução (SUCCEEDED, FAILED, CANCELLED, SKIPPED, COMPLETED...) ou EM ANDAMENTO.',
  codigo_termino COMMENT 'Código de término (SUCCESS, USER_CANCELLED, DISABLED...).',
  sucesso COMMENT 'Verdadeiro quando terminou com sucesso (SUCCEEDED no job e na tarefa, COMPLETED no pipeline).',
  data_inicio_param COMMENT 'Parâmetro data_inicio da execução (primeiro dia do intervalo carregado).',
  data_fim_param COMMENT 'Parâmetro data_fim da execução (último dia do intervalo carregado).',
  dias_processados COMMENT 'Dias do intervalo carregado (data_fim - data_inicio + 1); nulo em job sem esses parâmetros.',
  fatias COMMENT 'Linhas da tabela de sistema somadas nesta execução: execução que passa da virada da hora vem em fatias (L90).'
)
COMMENT 'Uma linha por execução de job do projeto: início e fim (UTC e horário de Brasília), duração, fila, setup, resultado, gatilho e o intervalo carregado (system.lakeflow.job_run_timeline).'
AS WITH r AS (
  SELECT job_id, run_id, min(period_start_time) AS inicio, max(period_end_time) AS fim,
    max_by(result_state, period_end_time) AS resultado, max_by(termination_code, period_end_time) AS codigo_termino,
    max_by(trigger_type, period_end_time) AS gatilho, max_by(job_parameters, period_end_time) AS parametros,
    max_by(queue_duration_seconds, period_end_time) AS fila_s, max_by(setup_duration_seconds, period_end_time) AS setup_s,
    max_by(execution_duration_seconds, period_end_time) AS execucao_s, count(*) AS fatias
  FROM system.lakeflow.job_run_timeline GROUP BY job_id, run_id),
e AS (
  SELECT j.job_id, j.job, r.run_id AS job_run_id, r.gatilho, coalesce(r.gatilho = 'CRON', false) AS da_agenda, r.inicio, r.fim,
    convert_timezone('America/Sao_Paulo', r.inicio) AS inicio_local, convert_timezone('America/Sao_Paulo', r.fim) AS fim_local, CAST(convert_timezone('America/Sao_Paulo', r.inicio) AS DATE) AS dia_local,
    round((unix_millis(r.fim) - unix_millis(r.inicio)) / 1000.0, 1) AS duracao_s,
    round((unix_millis(r.fim) - unix_millis(r.inicio)) / 60000.0, 2) AS duracao_min,
    r.fila_s, r.setup_s, r.execucao_s, coalesce(r.resultado, 'EM ANDAMENTO') AS resultado, r.codigo_termino,
    coalesce(r.resultado = 'SUCCEEDED', false) AS sucesso,
    try_cast(r.parametros['data_inicio']['value'] AS DATE) AS data_inicio_param,
    try_cast(r.parametros['data_fim']['value'] AS DATE) AS data_fim_param, r.fatias
  FROM r JOIN pos_venda.sustentacao.jobs_monitorados j ON j.job_id = r.job_id)
SELECT job_id, job, job_run_id, gatilho, da_agenda, inicio, fim, inicio_local, fim_local, dia_local, duracao_s, duracao_min, fila_s, setup_s,
  execucao_s, resultado, codigo_termino, sucesso, data_inicio_param, data_fim_param,
  datediff(data_fim_param, data_inicio_param) + 1 AS dias_processados, fatias
FROM e;

CREATE OR REPLACE VIEW pos_venda.sustentacao.execucoes_tarefa (
  job_id COMMENT 'Identificador do job.',
  job COMMENT 'Nome do job (sem o prefixo [dev usuário] do bundle).',
  job_run_id COMMENT 'Execução do job (run_id em job_run_timeline).',
  task_run_id COMMENT 'Execução da tarefa (run_id em job_task_run_timeline).',
  tarefa COMMENT 'Tarefa do job (task_key). Em linha_base e desvios: ''(job inteiro)'' para o job e ''(update)'' para o pipeline.',
  gatilho COMMENT 'O que disparou a execução: CRON (agenda), ONETIME (manual ou API), PERIODIC, JOB_TASK (update do pipeline pela tarefa) etc.',
  da_agenda COMMENT 'Verdadeiro quando a execução veio da agenda (gatilho CRON). Só estas contam para o SLA.',
  inicio COMMENT 'Início da execução em UTC.',
  fim COMMENT 'Fim da execução em UTC.',
  inicio_local COMMENT 'Início no horário de Brasília.',
  fim_local COMMENT 'Fim no horário de Brasília.',
  dia_local COMMENT 'Dia do início no horário de Brasília.',
  duracao_s COMMENT 'Duração de ponta a ponta, em segundos (fim - início).',
  duracao_min COMMENT 'Duração de ponta a ponta, em minutos.',
  setup_s COMMENT 'Tempo de preparação (subida da computação), em segundos (system.lakeflow).',
  execucao_s COMMENT 'Tempo de execução propriamente dito, em segundos (system.lakeflow).',
  limpeza_s COMMENT 'Tempo de limpeza no fim, em segundos (system.lakeflow).',
  resultado COMMENT 'Resultado da execução (SUCCEEDED, FAILED, CANCELLED, SKIPPED, COMPLETED...) ou EM ANDAMENTO.',
  codigo_termino COMMENT 'Código de término (SUCCESS, USER_CANCELLED, DISABLED...).',
  sucesso COMMENT 'Verdadeiro quando terminou com sucesso (SUCCEEDED no job e na tarefa, COMPLETED no pipeline).',
  tentativa COMMENT 'Número da tentativa da tarefa na mesma execução do job (1 = primeira).',
  tentativas COMMENT 'Total de tentativas da tarefa na mesma execução do job.',
  dias_processados COMMENT 'Dias do intervalo carregado (data_fim - data_inicio + 1); nulo em job sem esses parâmetros.',
  fatias COMMENT 'Linhas da tabela de sistema somadas nesta execução: execução que passa da virada da hora vem em fatias (L90).'
)
COMMENT 'Uma linha por execução de tarefa dos jobs do projeto: início, fim, duração, setup, execução, resultado e tentativas (system.lakeflow.job_task_run_timeline).'
AS WITH t AS (
  SELECT job_id, job_run_id, run_id, task_key, min(period_start_time) AS inicio, max(period_end_time) AS fim,
    max_by(result_state, period_end_time) AS resultado, max_by(termination_code, period_end_time) AS codigo_termino,
    max_by(setup_duration_seconds, period_end_time) AS setup_s, max_by(execution_duration_seconds, period_end_time) AS execucao_s,
    max_by(cleanup_duration_seconds, period_end_time) AS limpeza_s, count(*) AS fatias
  FROM system.lakeflow.job_task_run_timeline GROUP BY job_id, job_run_id, run_id, task_key)
SELECT e.job_id, e.job, t.job_run_id, t.run_id AS task_run_id, t.task_key AS tarefa, e.gatilho, e.da_agenda, t.inicio, t.fim,
  convert_timezone('America/Sao_Paulo', t.inicio) AS inicio_local, convert_timezone('America/Sao_Paulo', t.fim) AS fim_local, CAST(convert_timezone('America/Sao_Paulo', t.inicio) AS DATE) AS dia_local,
  round((unix_millis(t.fim) - unix_millis(t.inicio)) / 1000.0, 1) AS duracao_s,
  round((unix_millis(t.fim) - unix_millis(t.inicio)) / 60000.0, 2) AS duracao_min,
  t.setup_s, t.execucao_s, t.limpeza_s, coalesce(t.resultado, 'EM ANDAMENTO') AS resultado, t.codigo_termino,
  coalesce(t.resultado = 'SUCCEEDED', false) AS sucesso,
  row_number() OVER (PARTITION BY t.job_run_id, t.task_key ORDER BY t.inicio) AS tentativa,
  count(*) OVER (PARTITION BY t.job_run_id, t.task_key) AS tentativas, e.dias_processados, t.fatias
FROM t JOIN pos_venda.sustentacao.execucoes_job e ON e.job_run_id = t.job_run_id;

CREATE OR REPLACE VIEW pos_venda.sustentacao.atualizacoes_pipeline (
  pipeline_id COMMENT 'Identificador do pipeline Lakeflow.',
  pipeline COMMENT 'Nome do pipeline Lakeflow.',
  update_id COMMENT 'Atualização (update) do pipeline.',
  tipo_update COMMENT 'Tipo do update (REFRESH, FULL_REFRESH...).',
  gatilho COMMENT 'O que disparou a execução: CRON (agenda), ONETIME (manual ou API), PERIODIC, JOB_TASK (update do pipeline pela tarefa) etc.',
  job COMMENT 'Nome do job (sem o prefixo [dev usuário] do bundle).',
  job_run_id COMMENT 'Execução do job (run_id em job_run_timeline).',
  task_run_id COMMENT 'Execução da tarefa (run_id em job_task_run_timeline).',
  inicio COMMENT 'Início da execução em UTC.',
  fim COMMENT 'Fim da execução em UTC.',
  inicio_local COMMENT 'Início no horário de Brasília.',
  fim_local COMMENT 'Fim no horário de Brasília.',
  dia_local COMMENT 'Dia do início no horário de Brasília.',
  duracao_s COMMENT 'Duração de ponta a ponta, em segundos (fim - início).',
  duracao_min COMMENT 'Duração de ponta a ponta, em minutos.',
  espera_s COMMENT 'Segundos entre o início da tarefa do job e o início do update: a subida da computação do pipeline.',
  resultado COMMENT 'Resultado da execução (SUCCEEDED, FAILED, CANCELLED, SKIPPED, COMPLETED...) ou EM ANDAMENTO.',
  sucesso COMMENT 'Verdadeiro quando terminou com sucesso (SUCCEEDED no job e na tarefa, COMPLETED no pipeline).',
  refresh_completo COMMENT 'Verdadeiro quando o update refez tabelas do zero (full refresh).',
  dias_processados COMMENT 'Dias do intervalo carregado (data_fim - data_inicio + 1); nulo em job sem esses parâmetros.',
  fatias COMMENT 'Linhas da tabela de sistema somadas nesta execução: execução que passa da virada da hora vem em fatias (L90).'
)
COMMENT 'Uma linha por atualização (update) dos pipelines Lakeflow do projeto: duração, espera antes do update, resultado e a tarefa do job que disparou (system.lakeflow.pipeline_update_timeline).'
AS WITH p AS (
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
  convert_timezone('America/Sao_Paulo', u.inicio) AS inicio_local, convert_timezone('America/Sao_Paulo', u.fim) AS fim_local, CAST(convert_timezone('America/Sao_Paulo', u.inicio) AS DATE) AS dia_local,
  round((unix_millis(u.fim) - unix_millis(u.inicio)) / 1000.0, 1) AS duracao_s,
  round((unix_millis(u.fim) - unix_millis(u.inicio)) / 60000.0, 2) AS duracao_min,
  round((unix_millis(u.inicio) - unix_millis(t.inicio)) / 1000.0, 1) AS espera_s,
  coalesce(u.resultado, 'EM ANDAMENTO') AS resultado, coalesce(u.resultado = 'COMPLETED', false) AS sucesso,
  coalesce(u.tipo_update = 'FULL_REFRESH', false) OR u.tabelas_refresh_completo > 0 AS refresh_completo, t.dias_processados, u.fatias
FROM u JOIN pp ON pp.pipeline_id = u.pipeline_id AND pp.projeto = 'pos_venda'
LEFT JOIN pos_venda.sustentacao.execucoes_tarefa t ON t.task_run_id = u.task_run_id;

CREATE OR REPLACE VIEW pos_venda.sustentacao.volume_diario (
  dia COMMENT 'Dia do evento (data_extracao) e da foto da fato.',
  eventos_bronze COMMENT 'Eventos gravados no bronze com esta data_extracao.',
  linhas_fato COMMENT 'Linhas da fato histórica na foto deste dia (data_referencia_sk).'
)
COMMENT 'Volume por dia: eventos do bronze por data_extracao e linhas da fato histórica por foto (data_referencia_sk).'
AS WITH b AS (SELECT data_extracao AS dia, count(*) AS eventos_bronze FROM pos_venda.bronze.pagamentos_pendentes_eventos GROUP BY data_extracao),
f AS (
  SELECT to_date(CAST(data_referencia_sk AS STRING), 'yyyyMMdd') AS dia, linhas_fato
  FROM (SELECT data_referencia_sk, count(*) AS linhas_fato FROM pos_venda.gold.fact_pagamento_pendente_snapshot GROUP BY data_referencia_sk))
SELECT coalesce(b.dia, f.dia) AS dia, coalesce(b.eventos_bronze, 0) AS eventos_bronze, coalesce(f.linhas_fato, 0) AS linhas_fato
FROM b FULL OUTER JOIN f ON f.dia = b.dia;

CREATE OR REPLACE VIEW pos_venda.sustentacao.volume_execucao (
  job_id COMMENT 'Identificador do job.',
  job COMMENT 'Nome do job (sem o prefixo [dev usuário] do bundle).',
  job_run_id COMMENT 'Execução do job (run_id em job_run_timeline).',
  inicio_local COMMENT 'Início no horário de Brasília.',
  dia_local COMMENT 'Dia do início no horário de Brasília.',
  resultado COMMENT 'Resultado da execução (SUCCEEDED, FAILED, CANCELLED, SKIPPED, COMPLETED...) ou EM ANDAMENTO.',
  sucesso COMMENT 'Verdadeiro quando terminou com sucesso (SUCCEEDED no job e na tarefa, COMPLETED no pipeline).',
  duracao_s COMMENT 'Duração de ponta a ponta, em segundos (fim - início).',
  duracao_min COMMENT 'Duração de ponta a ponta, em minutos.',
  setup_s COMMENT 'Tempo de preparação (subida da computação), em segundos (system.lakeflow).',
  execucao_s COMMENT 'Tempo de execução propriamente dito, em segundos (system.lakeflow).',
  data_inicio_param COMMENT 'Parâmetro data_inicio da execução (primeiro dia do intervalo carregado).',
  data_fim_param COMMENT 'Parâmetro data_fim da execução (último dia do intervalo carregado).',
  dias_processados COMMENT 'Dias do intervalo carregado (data_fim - data_inicio + 1); nulo em job sem esses parâmetros.',
  eventos_gravados COMMENT 'Eventos gravados no bronze durante a execução (_ingestao_ts entre o início e o fim).',
  dias_com_eventos COMMENT 'Dias distintos de data_extracao gravados na execução.',
  linhas_fato_gravadas COMMENT 'Linhas gravadas na fato durante a execução (_carga_ts entre o início e o fim).',
  fotos_gravadas COMMENT 'Fotos (dias) gravadas na fato durante a execução.',
  segundos_por_dia_processado COMMENT 'Duração dividida pelos dias do intervalo, em segundos.',
  segundos_por_mil_eventos COMMENT 'Duração dividida pelos eventos gravados, em segundos por mil eventos.'
)
COMMENT 'Volume de cada execução da carga diária: dias do intervalo, eventos gravados no bronze e linhas gravadas na fato, com a duração. Separa lentidão de aumento de volume.'
AS WITH b AS (SELECT _ingestao_ts AS ts, count(*) AS eventos, count(DISTINCT data_extracao) AS dias FROM pos_venda.bronze.pagamentos_pendentes_eventos GROUP BY _ingestao_ts),
f AS (SELECT _carga_ts AS ts, count(*) AS linhas, count(DISTINCT data_referencia_sk) AS fotos FROM pos_venda.gold.fact_pagamento_pendente_snapshot GROUP BY _carga_ts),
e AS (SELECT * FROM pos_venda.sustentacao.execucoes_job WHERE job IN ('pos_venda_carga_diaria')),
eb AS (SELECT e.job_run_id, sum(b.eventos) AS eventos, sum(b.dias) AS dias FROM e JOIN b ON b.ts BETWEEN e.inicio AND e.fim GROUP BY e.job_run_id),
ef AS (SELECT e.job_run_id, sum(f.linhas) AS linhas, sum(f.fotos) AS fotos FROM e JOIN f ON f.ts BETWEEN e.inicio AND e.fim GROUP BY e.job_run_id)
SELECT e.job_id, e.job, e.job_run_id, e.inicio_local, e.dia_local, e.resultado, e.sucesso, e.duracao_s, e.duracao_min, e.setup_s, e.execucao_s,
  e.data_inicio_param, e.data_fim_param, e.dias_processados, coalesce(eb.eventos, 0) AS eventos_gravados, coalesce(eb.dias, 0) AS dias_com_eventos,
  coalesce(ef.linhas, 0) AS linhas_fato_gravadas, coalesce(ef.fotos, 0) AS fotos_gravadas,
  round(e.duracao_s / nullif(e.dias_processados, 0), 1) AS segundos_por_dia_processado,
  round(1000 * e.duracao_s / nullif(eb.eventos, 0), 3) AS segundos_por_mil_eventos
FROM e LEFT JOIN eb ON eb.job_run_id = e.job_run_id LEFT JOIN ef ON ef.job_run_id = e.job_run_id;

CREATE OR REPLACE VIEW pos_venda.sustentacao.linha_base (
  tipo COMMENT 'job, tarefa ou pipeline.',
  job COMMENT 'Nome do job; para tipo pipeline, o nome do pipeline.',
  tarefa COMMENT 'Tarefa do job (task_key). Em linha_base e desvios: ''(job inteiro)'' para o job e ''(update)'' para o pipeline.',
  execucoes_base COMMENT 'Execuções com sucesso na linha de base (as N mais recentes; em desvios, as N anteriores à execução).',
  mediana_s COMMENT 'Mediana da duração na linha de base, em segundos.',
  p95_s COMMENT 'Percentil 95 da duração na linha de base, em segundos (com poucas execuções fica perto do máximo).',
  minimo_s COMMENT 'Menor duração na linha de base, em segundos.',
  maximo_s COMMENT 'Maior duração na linha de base, em segundos.',
  mediana_min COMMENT 'Mediana da duração na linha de base, em minutos.',
  p95_min COMMENT 'Percentil 95 da duração na linha de base, em minutos.',
  mediana_setup_s COMMENT 'Mediana do tempo de preparação (setup) na linha de base, em segundos.',
  mediana_execucao_s COMMENT 'Mediana do tempo de execução (sem o setup) na linha de base, em segundos.',
  limite_desvio_s COMMENT 'Acima desta duração é desvio: o menor entre o p95 e 1,5 vez a mediana, em segundos.',
  base_suficiente COMMENT 'Verdadeiro quando a linha de base tem o mínimo de execuções (minimo_base).',
  primeira_base COMMENT 'Início (horário de Brasília) da execução mais antiga da linha de base.',
  ultima_base COMMENT 'Início (horário de Brasília) da execução mais recente da linha de base.',
  timeout_sugerido_min COMMENT 'Timeout sugerido para o job: 2 vezes o p95, em minutos, arredondado para cima (só para tipo job).'
)
COMMENT 'Linha de base de duração por job, tarefa e pipeline: mediana e p95 das últimas 20 execuções com sucesso, o limite de desvio e o timeout sugerido. Com menos de 5 execuções a base não vale.'
AS WITH x AS (
  SELECT 'job' AS tipo, job, '(job inteiro)' AS tarefa, job_run_id AS execucao_id, job_run_id, inicio, inicio_local, dia_local, duracao_s,
    setup_s, execucao_s, dias_processados FROM pos_venda.sustentacao.execucoes_job WHERE sucesso
  UNION ALL
  SELECT 'tarefa', job, tarefa, task_run_id, job_run_id, inicio, inicio_local, dia_local, duracao_s, setup_s, execucao_s, dias_processados
  FROM pos_venda.sustentacao.execucoes_tarefa WHERE sucesso
  UNION ALL
  SELECT 'pipeline', pipeline, '(update)', update_id, job_run_id, inicio, inicio_local, dia_local, duracao_s, CAST(NULL AS BIGINT), CAST(NULL AS BIGINT),
    dias_processados FROM pos_venda.sustentacao.atualizacoes_pipeline WHERE sucesso),
u AS (SELECT * FROM x QUALIFY row_number() OVER (PARTITION BY tipo, job, tarefa ORDER BY inicio DESC) <= 20),
b AS (
  SELECT tipo, job, tarefa, count(*) AS execucoes_base, percentile(duracao_s, 0.5) AS med, percentile(duracao_s, 0.95) AS p95,
    min(duracao_s) AS minimo_s, max(duracao_s) AS maximo_s, percentile(setup_s, 0.5) AS mediana_setup_s,
    percentile(execucao_s, 0.5) AS mediana_execucao_s, min(inicio_local) AS primeira_base, max(inicio_local) AS ultima_base
  FROM u GROUP BY tipo, job, tarefa)
SELECT tipo, job, tarefa, execucoes_base, round(med, 1) AS mediana_s, round(p95, 1) AS p95_s, minimo_s, maximo_s,
  round(med / 60, 2) AS mediana_min, round(p95 / 60, 2) AS p95_min, round(mediana_setup_s, 1) AS mediana_setup_s,
  round(mediana_execucao_s, 1) AS mediana_execucao_s, round(least(p95, 1.5 * med), 1) AS limite_desvio_s,
  execucoes_base >= 5 AS base_suficiente, primeira_base, ultima_base,
  CASE WHEN tipo = 'job' THEN CAST(ceil(2 * p95 / 60) AS INT) END AS timeout_sugerido_min
FROM b;

CREATE OR REPLACE VIEW pos_venda.sustentacao.desvios (
  tipo COMMENT 'job, tarefa ou pipeline.',
  job COMMENT 'Nome do job; para tipo pipeline, o nome do pipeline.',
  tarefa COMMENT 'Tarefa do job (task_key). Em linha_base e desvios: ''(job inteiro)'' para o job e ''(update)'' para o pipeline.',
  execucao_id COMMENT 'Execução avaliada: job_run_id, task_run_id ou update_id, conforme o tipo.',
  job_run_id COMMENT 'Execução do job (run_id em job_run_timeline).',
  inicio_local COMMENT 'Início no horário de Brasília.',
  dia_local COMMENT 'Dia do início no horário de Brasília.',
  duracao_s COMMENT 'Duração de ponta a ponta, em segundos (fim - início).',
  execucoes_base COMMENT 'Execuções com sucesso anteriores a esta na base móvel (até N).',
  mediana_base_s COMMENT 'Mediana das N execuções com sucesso anteriores, em segundos.',
  p95_base_s COMMENT 'Percentil 95 das N execuções com sucesso anteriores, em segundos.',
  limite_desvio_s COMMENT 'Acima desta duração é desvio: o menor entre o p95 e 1,5 vez a mediana, em segundos.',
  acima_p95 COMMENT 'Verdadeiro quando a duração passou do p95 da base.',
  acima_fator_mediana COMMENT 'Verdadeiro quando a duração passou de 1,5 vez a mediana da base.',
  excesso_s COMMENT 'Quanto a duração passou do limite de desvio, em segundos.',
  acima_mediana_pct COMMENT 'Quanto a duração ficou acima da mediana da base, em %.',
  setup_s COMMENT 'Tempo de preparação (subida da computação), em segundos (system.lakeflow).',
  excesso_setup_s COMMENT 'Quanto o setup passou da mediana de setup da base, em segundos.',
  dias_processados COMMENT 'Dias do intervalo carregado (data_fim - data_inicio + 1); nulo em job sem esses parâmetros.',
  mediana_dias_base COMMENT 'Mediana dos dias processados nas execuções da base.',
  eventos_gravados COMMENT 'Eventos gravados no bronze durante a execução (_ingestao_ts entre o início e o fim).',
  provavel_causa COMMENT 'Causa provável: espera por computação (setup), volume maior (mais dias que a base) ou lentidão com o mesmo volume.'
)
COMMENT 'Execuções com sucesso acima do normal: duração acima do p95 ou de 1.5 vez a mediana das 20 execuções anteriores (mínimo de 5), com o excesso e a causa provável.'
AS WITH x AS (
  SELECT 'job' AS tipo, job, '(job inteiro)' AS tarefa, job_run_id AS execucao_id, job_run_id, inicio, inicio_local, dia_local, duracao_s,
    setup_s, execucao_s, dias_processados FROM pos_venda.sustentacao.execucoes_job WHERE sucesso
  UNION ALL
  SELECT 'tarefa', job, tarefa, task_run_id, job_run_id, inicio, inicio_local, dia_local, duracao_s, setup_s, execucao_s, dias_processados
  FROM pos_venda.sustentacao.execucoes_tarefa WHERE sucesso
  UNION ALL
  SELECT 'pipeline', pipeline, '(update)', update_id, job_run_id, inicio, inicio_local, dia_local, duracao_s, CAST(NULL AS BIGINT), CAST(NULL AS BIGINT),
    dias_processados FROM pos_venda.sustentacao.atualizacoes_pipeline WHERE sucesso),
w AS (
  SELECT x.*, count(*) OVER w AS execucoes_base, percentile(duracao_s, 0.5) OVER w AS med, percentile(duracao_s, 0.95) OVER w AS p95,
    percentile(setup_s, 0.5) OVER w AS med_setup, percentile(dias_processados, 0.5) OVER w AS med_dias
  FROM x WINDOW w AS (PARTITION BY tipo, job, tarefa ORDER BY inicio ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING)),
d AS (SELECT w.*, least(p95, 1.5 * med) AS limite FROM w WHERE execucoes_base >= 5)
SELECT d.tipo, d.job, d.tarefa, d.execucao_id, d.job_run_id, d.inicio_local, d.dia_local, d.duracao_s, d.execucoes_base,
  round(d.med, 1) AS mediana_base_s, round(d.p95, 1) AS p95_base_s, round(d.limite, 1) AS limite_desvio_s,
  d.duracao_s > d.p95 AS acima_p95, d.duracao_s > 1.5 * d.med AS acima_fator_mediana,
  round(d.duracao_s - d.limite, 1) AS excesso_s, round(100 * (d.duracao_s / d.med - 1), 1) AS acima_mediana_pct, d.setup_s,
  round(d.setup_s - d.med_setup, 1) AS excesso_setup_s, d.dias_processados, d.med_dias AS mediana_dias_base, v.eventos_gravados,
  CASE WHEN d.setup_s - d.med_setup >= 0.5 * (d.duracao_s - d.med) THEN 'espera por computação (setup)'
       WHEN d.dias_processados > 1.5 * d.med_dias THEN concat('volume maior: ', d.dias_processados, ' dias no intervalo (base: ', CAST(d.med_dias AS INT), ')')
       ELSE 'lentidão com o mesmo volume' END AS provavel_causa
FROM d LEFT JOIN pos_venda.sustentacao.volume_execucao v ON v.job_run_id = d.job_run_id
WHERE d.duracao_s > d.limite;

CREATE OR REPLACE VIEW pos_venda.sustentacao.sla_diario (
  dia COMMENT 'Dia no horário de Brasília.',
  job_id COMMENT 'Identificador do job.',
  job COMMENT 'Nome do job (sem o prefixo [dev usuário] do bundle).',
  hora_agenda COMMENT 'Hora de início da agenda diária (HH:mm), lida do cron; nula se a agenda não é diária simples.',
  hora_meta COMMENT 'Hora meta (HH:mm, horário de Brasília) para a execução da agenda terminar.',
  agenda_pausada COMMENT 'Verdadeiro quando a agenda do job está pausada (situação de hoje); nulo quando o job não tem agenda.',
  execucoes_agenda COMMENT 'Execuções da agenda (gatilho CRON) no dia.',
  execucoes_manuais COMMENT 'Execuções manuais ou por API no dia (não contam para o SLA).',
  em_andamento COMMENT 'Execuções da agenda ainda em andamento no dia.',
  meta_local COMMENT 'Dia e hora meta no horário de Brasília.',
  fim_agenda_local COMMENT 'Fim da primeira execução da agenda com sucesso no dia (horário de Brasília).',
  atraso_min COMMENT 'Minutos depois da meta em que a execução da agenda terminou (0 = no prazo; nulo sem execução da agenda com sucesso).',
  situacao COMMENT 'no prazo, atrasada, atrasada (em andamento), em andamento, falhou, aguardando, sem execução da agenda ou agenda pausada.',
  sla_estourado COMMENT 'Verdadeiro quando a situação é atrasada, atrasada (em andamento), falhou ou sem execução da agenda.'
)
COMMENT 'SLA dos jobs com hora meta, dia a dia (últimos 30 dias, horário de Brasília): execuções da agenda e manuais, fim, atraso e situação. Só a execução da agenda conta para o SLA.'
AS WITH h AS (SELECT CAST(convert_timezone('America/Sao_Paulo', current_timestamp()) AS DATE) AS hoje, convert_timezone('America/Sao_Paulo', current_timestamp()) AS agora),
cal AS (SELECT explode(sequence(date_sub(hoje, 29), hoje)) AS dia FROM h),
j AS (SELECT * FROM pos_venda.sustentacao.jobs_monitorados WHERE hora_meta IS NOT NULL AND NOT apagado),
g AS (
  SELECT c.dia, j.job_id, j.job, j.hora_agenda, j.hora_meta, j.agenda_pausada,
    count_if(e.da_agenda) AS execucoes_agenda, count_if(NOT e.da_agenda) AS execucoes_manuais,
    count_if(e.da_agenda AND e.resultado = 'EM ANDAMENTO') AS em_andamento,
    min(CASE WHEN e.da_agenda AND e.sucesso THEN e.fim_local END) AS fim_agenda_local
  FROM cal c CROSS JOIN j LEFT JOIN pos_venda.sustentacao.execucoes_job e ON e.job_id = j.job_id AND e.dia_local = c.dia
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
FROM t;

CREATE OR REPLACE VIEW pos_venda.sustentacao.ultima_execucao (
  job_id COMMENT 'Identificador do job.',
  job COMMENT 'Nome do job (sem o prefixo [dev usuário] do bundle).',
  hora_agenda COMMENT 'Hora de início da agenda diária (HH:mm), lida do cron; nula se a agenda não é diária simples.',
  agenda_pausada COMMENT 'Verdadeiro quando a agenda do job está pausada (situação de hoje); nulo quando o job não tem agenda.',
  hora_meta COMMENT 'Hora meta (HH:mm, horário de Brasília) para a execução da agenda terminar.',
  timeout_min COMMENT 'Timeout do job em minutos (0 = sem timeout).',
  timeout_sugerido_min COMMENT 'Timeout sugerido para o job: 2 vezes o p95, em minutos, arredondado para cima (só para tipo job).',
  job_run_id COMMENT 'Execução do job (run_id em job_run_timeline).',
  gatilho COMMENT 'O que disparou a execução: CRON (agenda), ONETIME (manual ou API), PERIODIC, JOB_TASK (update do pipeline pela tarefa) etc.',
  inicio_local COMMENT 'Início no horário de Brasília.',
  fim_local COMMENT 'Fim no horário de Brasília.',
  duracao_min COMMENT 'Duração de ponta a ponta, em minutos.',
  resultado COMMENT 'Resultado da execução (SUCCEEDED, FAILED, CANCELLED, SKIPPED, COMPLETED...) ou EM ANDAMENTO.',
  dias_desde_ultima COMMENT 'Dias entre a última execução e hoje.',
  execucoes_base COMMENT 'Execuções com sucesso na linha de base (as N mais recentes; em desvios, as N anteriores à execução).',
  mediana_min COMMENT 'Mediana da duração na linha de base, em minutos.',
  p95_min COMMENT 'Percentil 95 da duração na linha de base, em minutos.',
  base_suficiente COMMENT 'Verdadeiro quando a linha de base tem o mínimo de execuções (minimo_base).',
  acima_mediana_min COMMENT 'Quanto a última execução ficou acima da mediana do job, em minutos (negativo = abaixo).',
  atraso_meta_min COMMENT 'Minutos depois da meta em que a última execução terminou, só se ela veio da agenda.',
  folga_projetada_min COMMENT 'Folga até a meta se a execução começar na hora da agenda e durar o p95: meta - agenda - p95, em minutos.'
)
COMMENT 'Última execução de cada job do projeto, comparada com a linha de base, com o atraso sobre a meta (se veio da agenda), a folga projetada até a meta e o timeout sugerido.'
AS WITH u AS (SELECT * FROM pos_venda.sustentacao.execucoes_job QUALIFY row_number() OVER (PARTITION BY job_id ORDER BY inicio DESC) = 1),
b AS (SELECT * FROM pos_venda.sustentacao.linha_base WHERE tipo = 'job')
SELECT j.job_id, j.job, j.hora_agenda, j.agenda_pausada, j.hora_meta, round(j.timeout_s / 60.0, 1) AS timeout_min, b.timeout_sugerido_min,
  u.job_run_id, u.gatilho, u.inicio_local, u.fim_local, u.duracao_min, u.resultado, datediff(CAST(convert_timezone('America/Sao_Paulo', current_timestamp()) AS DATE), u.dia_local) AS dias_desde_ultima,
  b.execucoes_base, b.mediana_min, b.p95_min, b.base_suficiente, round(u.duracao_min - b.mediana_min, 2) AS acima_mediana_min,
  CASE WHEN u.da_agenda AND j.hora_meta IS NOT NULL THEN greatest(0, round(timestampdiff(SECOND,
    CAST(concat(CAST(u.dia_local AS STRING), ' ', j.hora_meta, ':00') AS TIMESTAMP_NTZ), u.fim_local) / 60.0, 1)) END AS atraso_meta_min,
  CASE WHEN j.hora_meta IS NOT NULL AND j.hora_agenda IS NOT NULL AND b.base_suficiente
       THEN round((CAST(split(j.hora_meta, ':')[0] AS INT) * 60 + CAST(split(j.hora_meta, ':')[1] AS INT)) - (CAST(split(j.hora_agenda, ':')[0] AS INT) * 60 + CAST(split(j.hora_agenda, ':')[1] AS INT)) - b.p95_min, 1) END AS folga_projetada_min
FROM pos_venda.sustentacao.jobs_monitorados j LEFT JOIN u ON u.job_id = j.job_id LEFT JOIN b ON b.job = j.job
WHERE NOT j.apagado;

CREATE OR REPLACE VIEW pos_venda.sustentacao.matriz_tarefas (
  job COMMENT 'Nome do job (sem o prefixo [dev usuário] do bundle).',
  ordem COMMENT 'Ordem da tarefa no job.',
  tarefa COMMENT 'Tarefa do job (task_key). Em linha_base e desvios: ''(job inteiro)'' para o job e ''(update)'' para o pipeline.',
  o_que_faz COMMENT 'O que a tarefa faz.',
  sintoma_falha COMMENT 'Como a falha aparece.',
  acao_falha COMMENT 'O que fazer quando a tarefa falha.',
  sintoma_lentidao COMMENT 'Como a lentidão aparece e o que é normal.',
  acao_lentidao COMMENT 'O que fazer quando a tarefa passa do normal.',
  referencia COMMENT 'Linha da matriz de resiliência do playbook (P28), lição (L##) ou visão onde olhar.',
  execucoes_base COMMENT 'Execuções com sucesso na linha de base (as N mais recentes; em desvios, as N anteriores à execução).',
  mediana_min COMMENT 'Mediana da duração na linha de base, em minutos.',
  p95_min COMMENT 'Percentil 95 da duração na linha de base, em minutos.',
  mediana_setup_s COMMENT 'Mediana do tempo de preparação (setup) na linha de base, em segundos.',
  ultima_situacao COMMENT 'Resultado da execução mais recente da tarefa.',
  ultima_execucao_local COMMENT 'Início da execução mais recente da tarefa (horário de Brasília).'
)
COMMENT 'Matriz de resiliência por tarefa da carga diária (P28): o que a tarefa faz, sintoma e ação na falha e na lentidão, com a linha de base e a última execução.'
AS WITH m AS (
  SELECT * FROM VALUES
    ('pos_venda_carga_diaria', 1, 'portao_regras', 'Roda os cenários BDD das regras de negócio contra as funções pos_venda.regras; se um falhar, nada mais roda.', 'A tarefa falha e as seguintes não rodam.', 'Ler no log da tarefa o cenário que falhou, corrigir a função ou o cenário (se a regra mudou) e rodar o job de novo.', 'Setup de cerca de 3 min é o normal: é a primeira tarefa e espera a computação serverless. Execução acima do p95 aponta cenário novo ou espera da Statement Execution API.', 'Comparar setup_s e execucao_s em execucoes_tarefa. Se a demora for da API, ver L58.', 'Matriz do playbook: Portão das regras reprovado; L58'),
    ('pos_venda_carga_diaria', 2, 'gerar_eventos', 'Grava no bronze os eventos de cada dia do intervalo, só acrescentando e com guarda de idempotência.', 'Falha ao gravar o bronze.', 'Ver se o dia já está no bronze: a guarda pula dia gravado, e nulo na subconsulta travava a guarda (L82). Depois, rodar de novo o intervalo.', 'A duração cresce com os dias do intervalo (backfill).', 'Ver dias_processados e eventos_gravados em volume_execucao: com mais dias, é volume e não lentidão.', 'L82; volume_execucao'),
    ('pos_venda_carga_diaria', 3, 'silver_lakeflow', 'Atualiza o pipeline Lakeflow da silver: eventos, quarentena, histórica (SCD2) e atual.', 'O update falha ou é cancelado, e a tarefa termina com erro.', 'Ler o event log do update (o update_id está em atualizacoes_pipeline), corrigir e reparar a execução a partir desta tarefa. Full refresh só com decisão do dono: a silver histórica é refeita do bronze.', 'Espera antes do update (espera_s) ou update acima do p95.', 'espera_s alto é a subida da computação do pipeline. Update acima do p95 com o mesmo volume é lentidão: ver o event log.', 'atualizacoes_pipeline; L89'),
    ('pos_venda_carga_diaria', 4, 'gold_dimensoes', 'Recria as dimensões do star schema a partir da silver atual.', 'A tarefa falha e a fato do dia não é gravada.', 'Ler o erro no log, conferir a silver atual e a quarentena e reparar a execução a partir desta tarefa.', 'Setup de cerca de 2,5 min é o normal: depois do pipeline, a computação dos notebooks é pedida de novo.', 'Olhar execucao_s. Se só o setup subiu, é espera por computação serverless, e não o código.', 'L89'),
    ('pos_venda_carga_diaria', 5, 'gold_fato_snapshot', 'Apaga e regrava na fato histórica as fotos do intervalo (PK = pendência + dia).', 'A tarefa falha e a foto do dia fica faltando.', 'Reparar a execução a partir desta tarefa. A tarefa apaga e regrava o intervalo, então rodar de novo não duplica.', 'A duração cresce com as fotos do intervalo (cerca de 250 mil linhas por foto).', 'Ver fotos_gravadas e linhas_fato_gravadas em volume_execucao.', 'volume_execucao'),
    ('pos_venda_carga_diaria', 6, 'dq_metricas', 'Recria as tabelas dq_* da gold e as views de janela do DQX Studio, devolvendo tags e Wiki.', 'A tarefa falha, ou as views perdem as tags.', 'Rodar de novo: garantir_view só recria a view que mudou e devolve a governança. Se sumirem tags, rodar governanca/aplicar_semantica.py.', 'Execução acima do p95.', 'Ver quantas views foram recriadas no log: recriar uma view custa mais que confirmar que está igual.', 'Matriz do playbook: Recriação de view pelo job; L31'),
    ('pos_venda_carga_diaria', 7, 'ligar_dqx_studio', 'Liga o app dqx-studio, que para sozinho após 24 h no Free Edition, para a avaliação agendada das 06:30.', 'A tarefa falha ao ligar o app, ou o Lakebase está desligado.', 'databricks apps start dqx-studio; se o Lakebase estiver desligado, ligar o endpoint e reiniciar o app.', 'Alguns segundos quando o app já está ligado; cerca de 2 min quando o app está parado e precisa subir.', 'Nada a fazer se o app estava parado. Antes de usar o app, esperar "Application startup complete" no log (L85).', 'Matriz do playbook: App do Studio parado; Lakebase do DQX Studio desligado; L85')
  AS t(job, ordem, tarefa, o_que_faz, sintoma_falha, acao_falha, sintoma_lentidao, acao_lentidao, referencia)),
b AS (SELECT * FROM pos_venda.sustentacao.linha_base WHERE tipo = 'tarefa'),
u AS (SELECT job, tarefa, resultado, inicio_local FROM pos_venda.sustentacao.execucoes_tarefa QUALIFY row_number() OVER (PARTITION BY job, tarefa ORDER BY inicio DESC) = 1)
SELECT m.job, m.ordem, m.tarefa, m.o_que_faz, m.sintoma_falha, m.acao_falha, m.sintoma_lentidao, m.acao_lentidao, m.referencia,
  b.execucoes_base, b.mediana_min, b.p95_min, b.mediana_setup_s, u.resultado AS ultima_situacao, u.inicio_local AS ultima_execucao_local
FROM m LEFT JOIN b ON b.job = m.job AND b.tarefa = m.tarefa LEFT JOIN u ON u.job = m.job AND u.tarefa = m.tarefa;

CREATE OR REPLACE VIEW pos_venda.sustentacao.alerta_sustentacao (
  tipo_ocorrencia COMMENT 'SLA (meta estourada hoje) ou desvio (execução acima do normal nas últimas horas).',
  job COMMENT 'Nome do job (sem o prefixo [dev usuário] do bundle).',
  tarefa COMMENT 'Tarefa do job (task_key). Em linha_base e desvios: ''(job inteiro)'' para o job e ''(update)'' para o pipeline.',
  quando_local COMMENT 'Quando aconteceu (horário de Brasília): a meta do dia ou o início da execução.',
  detalhe COMMENT 'O que aconteceu, com os números.',
  acao COMMENT 'O que fazer (da matriz de resiliência por tarefa).'
)
COMMENT 'O que o alerta SQL diário avisa: SLA estourado hoje e desvios da carga diária nas últimas 24 horas que passaram do limite por 60 s ou mais sem ser volume, com a ação da matriz por tarefa. Vazia = nada a fazer.'
AS SELECT 'SLA' AS tipo_ocorrencia, job, CAST(NULL AS STRING) AS tarefa, meta_local AS quando_local,
  concat('Situação: ', situacao, coalesce(concat('; terminou ', atraso_min, ' min depois da meta das ', hora_meta), ''),
         '; execuções da agenda no dia: ', execucoes_agenda) AS detalhe,
  'Ver a última execução em execucoes_tarefa e a matriz por tarefa; se a carga não rodou, rodar o job e avisar quem usa a foto do dia.' AS acao
FROM pos_venda.sustentacao.sla_diario WHERE sla_estourado AND dia = CAST(convert_timezone('America/Sao_Paulo', current_timestamp()) AS DATE)
UNION ALL
SELECT 'desvio', d.job, d.tarefa, d.inicio_local,
  concat(d.tipo, ' durou ', round(d.duracao_s / 60, 1), ' min; mediana ', round(d.mediana_base_s / 60, 1), ' min, p95 ',
         round(d.p95_base_s / 60, 1), ' min (', d.execucoes_base, ' execuções); passou ', round(d.excesso_s / 60, 1),
         ' min do limite; causa provável: ', d.provavel_causa),
  coalesce(m.acao_lentidao, 'Comparar com a linha de base e o volume da execução (volume_execucao).')
FROM pos_venda.sustentacao.desvios d LEFT JOIN pos_venda.sustentacao.matriz_tarefas m ON m.job = d.job AND m.tarefa = d.tarefa
WHERE d.inicio_local >= timestampadd(HOUR, -24, convert_timezone('America/Sao_Paulo', current_timestamp()))
  -- só os jobs diários (com hora meta) e o que eles disparam; o task runner do DQX Studio roda sob demanda e faria ruído
  AND d.job_run_id IN (SELECT job_run_id FROM pos_venda.sustentacao.execucoes_job WHERE job IN (SELECT job FROM pos_venda.sustentacao.config_sla))
  -- piso de ruído: com poucas execuções o p95 fica no máximo, e passar dele por segundos não pede ação
  AND d.excesso_s >= 60 AND d.provavel_causa NOT LIKE 'volume maior%';
