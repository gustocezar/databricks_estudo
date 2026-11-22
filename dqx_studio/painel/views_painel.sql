-- =====================================================================================================================
-- pos_venda · views que alimentam o painel "pos_venda · Qualidade de dados"
-- Todas ficam em pos_venda.dq para o painel usar nomes simples (dataset_catalog = pos_venda, dataset_schema = dq).
-- Aplicar com:  python3 aplicar_e_testar.py   (cria as views e testa cada consulta do painel)
--
-- Semanas: a simulação começa em 20/11/2026; "Semana N" = dias 20/11 + 7*(N-1) até + 6.
-- =====================================================================================================================


-- 1) Métricas diárias do fluxo bronze > silver + linhas órfãs da fato (taxas em 0–1 para o formato percentual)
CREATE OR REPLACE VIEW pos_venda.dq.v_painel_diario
COMMENT 'Painel de qualidade: métricas diárias (recebidos, barrados, avisos) e linhas órfãs da fato, com a semana da simulação.'
AS
WITH d AS (
  SELECT q.*, CAST(floor(datediff(q.dia, DATE'2026-11-20') / 7) AS INT) AS k
  FROM pos_venda.gold.dq_qualidade_diaria q
  WHERE q.dia >= DATE'2026-11-20'
)
SELECT d.dia,
       d.k + 1 AS semana_n,
       concat('Semana ', d.k + 1, ' · ', date_format(date_add(DATE'2026-11-20', 7 * d.k), 'dd/MM'), '–',
              date_format(date_add(DATE'2026-11-20', 7 * d.k + 6), 'dd/MM')) AS semana,
       d.eventos_recebidos, d.eventos_aptos, d.eventos_barrados, d.eventos_duplicados,
       d.cpf_invalido, d.email_ausente, d.cep_malformado, d.forma_pagamento_nao_cadastrada, d.canal_corretor_sem_corretor,
       d.pct_barrados / 100 AS taxa_barrados,
       d.pct_duplicados / 100 AS taxa_duplicados,
       d.pct_cpf_invalido / 100 AS taxa_cpf_invalido,
       d.pct_email_ausente / 100 AS taxa_email_ausente,
       d.pct_cep_malformado / 100 AS taxa_cep_malformado,
       coalesce(o.fk_forma_pagamento_orfa, 0) AS fato_linhas_orfas,
       o.linhas_na_foto AS fato_linhas_na_foto
FROM d
LEFT JOIN pos_venda.gold.dq_fato_orfas_diarias o ON o.dia = d.dia;


-- 2) Eventos barrados por dia, motivo e tipo de evento
CREATE OR REPLACE VIEW pos_venda.dq.v_painel_barrados
COMMENT 'Painel de qualidade: eventos barrados na silver por dia, motivo da rejeição e tipo de evento, com a semana da simulação.'
AS
WITH b AS (
  SELECT b.*, CAST(floor(datediff(b.dia, DATE'2026-11-20') / 7) AS INT) AS k
  FROM pos_venda.gold.dq_barrados_por_motivo_dia b
  WHERE b.dia >= DATE'2026-11-20'
)
SELECT dia, k + 1 AS semana_n,
       concat('Semana ', k + 1, ' · ', date_format(date_add(DATE'2026-11-20', 7 * k), 'dd/MM'), '–',
              date_format(date_add(DATE'2026-11-20', 7 * k + 6), 'dd/MM')) AS semana,
       motivo_rejeicao, tipo_evento, eventos, pendencias, valor_total
FROM b;


-- 3) Dados NÃO aptos: a quarentena do pipeline, linha a linha, com o motivo e o cadastro do cliente
CREATE OR REPLACE VIEW pos_venda.dq.v_painel_quarentena
COMMENT 'Painel de qualidade: eventos barrados antes da silver (quarentena), com o motivo e os dados do cliente.'
AS
WITH q AS (
  SELECT q.*, CAST(floor(datediff(q.data_extracao, DATE'2026-11-20') / 7) AS INT) AS k
  FROM pos_venda.silver.pendencia_evento_quarentena q
)
SELECT data_extracao AS dia, k + 1 AS semana_n,
       concat('Semana ', k + 1, ' · ', date_format(date_add(DATE'2026-11-20', 7 * k), 'dd/MM'), '–',
              date_format(date_add(DATE'2026-11-20', 7 * k + 6), 'dd/MM')) AS semana,
       motivo_rejeicao, pendencia_id, tipo_evento, numero_apolice, numero_parcela, produto_nome, status_cobranca,
       valor_parcela, valor_multa, valor_juros, valor_total_pendente, data_vencimento, dias_atraso, data_baixa, valor_pago,
       forma_pagamento, canal_venda, cliente_nome, cliente_cpf, cliente_idade, cliente_uf, cliente_cidade, _quarentena_ts
FROM q;


-- 4) Execuções do DQX Studio com TODAS as linhas (replay semana a semana das janelas pos_venda.dq.v_*_janela)
--    Ficam de fora: execuções com amostra, o teste inicial (antes de 05:44 UTC), as 2 marcadas como falso positivo e as
--    execuções do Registro de Regras (checks com registry_rule_id), que reavaliam a semana corrente e apareceriam como semana 6.
CREATE OR REPLACE VIEW pos_venda.dq.v_painel_studio_execucoes
COMMENT 'Painel de qualidade: execuções do DQX Studio com todas as linhas, uma por semana e por camada.'
AS
WITH r AS (
  SELECT run_id, source_table_fqn, created_at, total_rows, error_rows, warning_rows, error_summary_json
  FROM main.dqx_studio.dq_validation_runs
  WHERE source_table_fqn IN ('pos_venda.dq.v_bronze_eventos_janela', 'pos_venda.dq.v_quarentena_janela',
                             'pos_venda.dq.v_silver_eventos_aptos_janela', 'pos_venda.dq.v_silver_hist_janela',
                             'pos_venda.dq.v_fato_snapshot_janela')
    AND run_type = 'dryrun' AND sample_size = 0 AND status = 'SUCCESS'
    AND created_at >= TIMESTAMP'2026-11-19T05:44:00Z'
    AND NOT (source_table_fqn = 'pos_venda.dq.v_silver_eventos_aptos_janela' AND checks_json LIKE '%pk_unica_pendencia_id%')
    AND checks_json NOT LIKE '%registry_rule_id%'
  QUALIFY row_number() OVER (PARTITION BY run_id ORDER BY updated_at DESC) = 1
),
n AS (SELECT r.*, CAST(row_number() OVER (PARTITION BY source_table_fqn ORDER BY created_at) AS INT) AS semana_n FROM r)
SELECT run_id, semana_n,
       concat('Semana ', semana_n, ' · ', date_format(date_add(DATE'2026-11-20', 7 * (semana_n - 1)), 'dd/MM'), '–',
              date_format(date_add(DATE'2026-11-20', 7 * (semana_n - 1) + 6), 'dd/MM')) AS semana,
       CASE source_table_fqn
         WHEN 'pos_venda.dq.v_bronze_eventos_janela' THEN '1 · Bronze (tudo que chegou)'
         WHEN 'pos_venda.dq.v_quarentena_janela' THEN '2 · Quarentena (não aptos)'
         WHEN 'pos_venda.dq.v_silver_eventos_aptos_janela' THEN '3 · Silver (eventos aptos)'
         WHEN 'pos_venda.dq.v_silver_hist_janela' THEN '4 · Silver histórica (SCD2)'
         ELSE '5 · Gold (fato histórica)' END AS camada,
       CASE source_table_fqn
         WHEN 'pos_venda.dq.v_bronze_eventos_janela' THEN 'bronze'
         WHEN 'pos_venda.dq.v_quarentena_janela' THEN 'quarentena'
         WHEN 'pos_venda.dq.v_silver_eventos_aptos_janela' THEN 'silver'
         WHEN 'pos_venda.dq.v_silver_hist_janela' THEN 'silver hist'
         ELSE 'fato' END AS camada_curta,
       source_table_fqn AS destino, created_at, total_rows, error_rows, warning_rows,
       error_rows / nullif(total_rows, 0) AS taxa_erro,
       warning_rows / nullif(total_rows, 0) AS taxa_aviso,
       error_summary_json
FROM n;


-- 5) Regras violadas em cada execução completa do Studio (uma linha por execução e regra)
CREATE OR REPLACE VIEW pos_venda.dq.v_painel_studio_regras
COMMENT 'Painel de qualidade: regras violadas por semana e camada nas execuções completas do DQX Studio.'
AS
SELECT e.run_id, e.semana_n, e.semana, e.camada, e.camada_curta,
       s.error AS regra,
       CASE WHEN s.error_count > 0 THEN 'erro' ELSE 'aviso' END AS criticidade,
       concat(e.camada_curta, ' · ', s.error, CASE WHEN s.error_count > 0 THEN ' (erro)' ELSE ' (aviso)' END) AS regra_rotulo,
       s.count AS linhas, s.error_count AS linhas_erro, s.warning_count AS linhas_aviso
FROM pos_venda.dq.v_painel_studio_execucoes e,
     LATERAL explode(from_json(e.error_summary_json,
       'array<struct<error:string,count:bigint,error_count:bigint,warning_count:bigint>>')) AS t(s);


-- 6) Linhas reprovadas pelo Studio (quarentena do Studio), com a regra violada e a mensagem
CREATE OR REPLACE VIEW pos_venda.dq.v_painel_studio_reprovadas
COMMENT 'Painel de qualidade: linhas que o DQX Studio reprovou (regra de erro) nas execuções completas, com a regra e a mensagem.'
AS
SELECT e.semana_n, e.semana, e.camada, e.camada_curta,
       x.value:name::string AS regra,
       x.value:message::string AS mensagem,
       coalesce(q.row_data:data_extracao::string, q.row_data:data_referencia_sk::string) AS referencia,
       q.row_data:pendencia_id::string AS pendencia_id,
       q.row_data:numero_apolice::string AS numero_apolice,
       q.row_data:cliente_nome::string AS cliente_nome,
       q.row_data:valor_total_pendente::string AS valor_total_pendente,
       q.created_at
FROM main.dqx_studio.dq_quarantine_records q
JOIN pos_venda.dq.v_painel_studio_execucoes e ON e.run_id = q.run_id,
     LATERAL variant_explode(q.errors) AS x;
