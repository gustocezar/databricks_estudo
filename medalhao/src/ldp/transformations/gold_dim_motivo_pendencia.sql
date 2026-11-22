-- Gerado por gerar_sql.py | pipeline Lakeflow | gold.dim_motivo_pendencia
CREATE OR REFRESH MATERIALIZED VIEW pos_venda.gold_ldp.dim_motivo_pendencia
COMMENT 'Dimensao motivo da pendencia de pagamento, com agrupamento.'
AS
SELECT xxhash64(motivo_pendencia) AS motivo_pendencia_sk, motivo_pendencia,
       CASE WHEN motivo_pendencia IN ('SALDO_INSUFICIENTE', 'LIMITE_INSUFICIENTE', 'CARTAO_RECUSADO', 'BOLETO_NAO_PAGO') THEN 'FINANCEIRO'
            WHEN motivo_pendencia IN ('DADOS_BANCARIOS_INVALIDOS', 'CONTA_ENCERRADA', 'CARTAO_EXPIRADO') THEN 'CADASTRAL'
            WHEN motivo_pendencia IN ('AUTORIZACAO_DEBITO_CANCELADA', 'AUTORIZACAO_PIX_REVOGADA') THEN 'AUTORIZACAO'
            ELSE 'OPERACIONAL' END AS grupo_motivo
FROM pos_venda.silver_ldp.pagamento_pendente
QUALIFY row_number() OVER (PARTITION BY motivo_pendencia ORDER BY data_vencimento DESC, pendencia_id) = 1;
