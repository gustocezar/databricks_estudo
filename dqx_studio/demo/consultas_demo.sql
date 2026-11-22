-- =====================================================================================================================
-- pos_venda · Demonstração de qualidade de dados (DQX)
-- Consultas para rodar no SQL Editor (warehouse "Serverless Starter Warehouse") durante a demonstração.
-- Linha do tempo simulada:
--   ciclo 1  20–26/11  semana limpa (linha de base)
--   ciclo 2  27/11–03/12  CPF inválido, duplicatas, e-mail ausente           (avisos: passam para a silver)
--   ciclo 3  04–10/12  valor <= 0, status inválido, total inconsistente, sem id   (erros: barrados)
--   ciclo 4  11–17/12  vencimento futuro, menor de idade, UF inválida, baixa sem data, atraso errado (barrados)
--                      + forma de pagamento nova, CEP malformado, canal CORRETOR sem corretor        (vazam)
--   ciclo 5  18–24/12  recuperação: os incidentes caem até zerar
-- Execuções marcadas como "False positive" no Studio (regra de PK aplicada por engano à silver de eventos nos ciclos 1 e 2)
-- ficam fora das consultas 4, 6 e 7 pelo filtro "run_id NOT IN (... pk_unica_pendencia_id ...)".
-- =====================================================================================================================


-- 1) EVOLUÇÃO DIÁRIA — recebidos, barrados e avisos por dia (gold.dq_qualidade_diaria, gerada pela carga diária)
SELECT dia, eventos_recebidos, eventos_barrados, pct_barrados, pct_duplicados, pct_cpf_invalido, pct_email_ausente,
       cep_malformado, forma_pagamento_nao_cadastrada, canal_corretor_sem_corretor
FROM pos_venda.gold.dq_qualidade_diaria
WHERE dia >= DATE'2026-11-20'
ORDER BY dia;


-- 2) BARRADOS POR MOTIVO E POR SEMANA — qual regra de erro segurou cada incidente
SELECT CASE WHEN dia <= DATE'2026-11-26' THEN '1 · 20–26/11'
            WHEN dia <= DATE'2026-12-03' THEN '2 · 27/11–03/12'
            WHEN dia <= DATE'2026-12-10' THEN '3 · 04–10/12'
            WHEN dia <= DATE'2026-12-17' THEN '4 · 11–17/12'
            ELSE '5 · 18–24/12' END AS ciclo,
       motivo_rejeicao, sum(eventos) AS eventos, sum(pendencias) AS pendencias, round(sum(valor_total), 2) AS valor_retido
FROM pos_venda.gold.dq_barrados_por_motivo_dia
WHERE dia >= DATE'2026-11-20'
GROUP BY ALL
ORDER BY ciclo, eventos DESC;


-- 3) DADOS NÃO APTOS — eventos barrados antes da silver, com o motivo e o cadastro do cliente
SELECT data_extracao, motivo_rejeicao, pendencia_id, tipo_evento, numero_apolice, numero_parcela, status_cobranca,
       valor_parcela, valor_multa, valor_juros, valor_total_pendente, data_vencimento, dias_atraso, data_baixa, valor_pago,
       cliente_nome, cliente_cpf, cliente_idade, cliente_uf, cliente_cidade, forma_pagamento, canal_venda, _quarentena_ts
FROM pos_venda.silver.pendencia_evento_quarentena
ORDER BY data_extracao DESC, motivo_rejeicao
LIMIT 500;


-- 3b) UM EXEMPLO DE CADA MOTIVO — bom para explicar cada regra na tela
SELECT * EXCEPT (rn)
FROM (SELECT motivo_rejeicao, data_extracao, pendencia_id, tipo_evento, status_cobranca, valor_parcela, valor_multa,
             valor_juros, valor_total_pendente, data_vencimento, dias_atraso, data_baixa, valor_pago,
             cliente_nome, cliente_idade, cliente_uf,
             row_number() OVER (PARTITION BY motivo_rejeicao ORDER BY data_extracao, pendencia_id) AS rn
      FROM pos_venda.silver.pendencia_evento_quarentena)
WHERE rn = 1
ORDER BY motivo_rejeicao;


-- 4) DADOS NÃO APTOS VISTOS PELO DQX STUDIO — cada linha reprovada com a regra violada (quarentena do Studio)
SELECT q.created_at, q.source_table_fqn, e.value:name::string AS regra, e.value:message::string AS mensagem,
       q.row_data:data_extracao::string AS dia, q.row_data:pendencia_id::string AS pendencia_id,
       q.row_data:cliente_nome::string AS cliente, q.row_data:valor_total_pendente::string AS valor_total
FROM main.dqx_studio.dq_quarantine_records q, LATERAL variant_explode(q.errors) AS e
WHERE q.source_table_fqn LIKE 'pos_venda.dq.v_%_janela'
  AND q.run_id NOT IN (SELECT run_id FROM main.dqx_studio.dq_validation_runs WHERE source_table_fqn LIKE '%eventos_aptos_janela' AND checks_json LIKE '%pk_unica_pendencia_id%')
ORDER BY q.created_at DESC
LIMIT 500;


-- 5) RECONCILIAÇÃO — tudo que o pipeline barrou também reprova em alguma regra de erro do Studio (erro = total)
SELECT created_at, total_rows AS eventos_na_quarentena, error_rows AS reprovados_no_studio, valid_rows AS aprovados_no_studio
FROM main.dqx_studio.dq_validation_runs
WHERE source_table_fqn = 'pos_venda.dq.v_quarentena_janela' AND sample_size = 0 AND status = 'SUCCESS'
ORDER BY created_at;


-- 6) EVOLUÇÃO NO STUDIO POR CAMADA — execuções com todas as linhas, uma por semana (na ordem dos ciclos)
SELECT replace(source_table_fqn, 'pos_venda.dq.', '') AS destino, created_at, total_rows, error_rows, warning_rows,
       round(100.0 * error_rows / nullif(total_rows, 0), 3) AS pct_erro,
       round(100.0 * warning_rows / nullif(total_rows, 0), 3) AS pct_aviso
FROM main.dqx_studio.dq_validation_runs
WHERE source_table_fqn LIKE 'pos_venda.dq.v_%_janela' AND sample_size = 0 AND status = 'SUCCESS'
  AND run_id NOT IN (SELECT run_id FROM main.dqx_studio.dq_validation_runs WHERE source_table_fqn LIKE '%eventos_aptos_janela' AND checks_json LIKE '%pk_unica_pendencia_id%')
ORDER BY destino, created_at;


-- 7) REGRAS MAIS VIOLADAS NO STUDIO — somando as execuções completas das janelas
SELECT replace(r.source_table_fqn, 'pos_venda.dq.', '') AS destino, s.error AS regra,
       sum(s.error_count) AS linhas_em_erro, sum(s.warning_count) AS linhas_em_aviso
FROM main.dqx_studio.dq_validation_runs r,
     LATERAL explode(from_json(r.error_summary_json, 'array<struct<error:string,count:bigint,error_count:bigint,warning_count:bigint>>')) AS t(s)
WHERE r.source_table_fqn LIKE 'pos_venda.dq.v_%_janela' AND r.sample_size = 0 AND r.status = 'SUCCESS'
  AND r.run_id NOT IN (SELECT run_id FROM main.dqx_studio.dq_validation_runs WHERE source_table_fqn LIKE '%eventos_aptos_janela' AND checks_json LIKE '%pk_unica_pendencia_id%')
GROUP BY ALL
ORDER BY destino, linhas_em_erro DESC, linhas_em_aviso DESC;


-- 8) VAZAMENTO PARA A GOLD — forma de pagamento sem cadastro passou pela barreira e virou FK órfã na fato
SELECT dia, linhas_na_foto, fk_forma_pagamento_orfa
FROM pos_venda.gold.dq_fato_orfas_diarias
WHERE dia >= DATE'2026-12-10'
ORDER BY dia;

-- 8b) quais valores vazaram (o Studio pega na silver com a regra forma_pagamento_cadastrada)
SELECT forma_pagamento, count(*) AS eventos, min(data_extracao) AS primeiro_dia, max(data_extracao) AS ultimo_dia
FROM pos_venda.silver.pendencia_evento
WHERE forma_pagamento NOT IN ('DEBITO_CONTA', 'BOLETO', 'CARTAO_CREDITO', 'PIX_AUTOMATICO')
GROUP BY forma_pagamento;


-- 9) JANELA QUE O STUDIO ESTÁ AVALIANDO AGORA (o job diário aponta para os últimos 7 dias)
SELECT * FROM pos_venda.dq.janela_avaliacao;
