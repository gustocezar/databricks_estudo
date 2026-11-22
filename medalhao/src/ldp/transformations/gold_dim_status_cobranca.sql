-- Gerado por gerar_sql.py | pipeline Lakeflow | gold.dim_status_cobranca
CREATE OR REFRESH MATERIALIZED VIEW pos_venda.gold_ldp.dim_status_cobranca
COMMENT 'Dimensao status de cobranca, com a fase da regua de cobranca.'
AS
SELECT xxhash64(status_cobranca) AS status_cobranca_sk, status_cobranca,
       CASE status_cobranca WHEN 'PENDENTE' THEN 'INICIAL' WHEN 'EM_COBRANCA' THEN 'INTERNA'
            WHEN 'PROMESSA_PAGAMENTO' THEN 'NEGOCIACAO' WHEN 'NEGOCIADO' THEN 'NEGOCIACAO' ELSE 'EXTERNA' END AS fase_cobranca,
       CASE status_cobranca WHEN 'PENDENTE' THEN 1 WHEN 'EM_COBRANCA' THEN 2 WHEN 'PROMESSA_PAGAMENTO' THEN 3
            WHEN 'NEGOCIADO' THEN 4 ELSE 5 END AS ordem_fase
FROM pos_venda.silver_ldp.pagamento_pendente
QUALIFY row_number() OVER (PARTITION BY status_cobranca ORDER BY data_vencimento DESC, pendencia_id) = 1;
