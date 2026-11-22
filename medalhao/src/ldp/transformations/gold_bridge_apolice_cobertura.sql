-- Gerado por gerar_sql.py | pipeline Lakeflow | gold.bridge_apolice_cobertura
CREATE OR REFRESH MATERIALIZED VIEW pos_venda.gold_ldp.bridge_apolice_cobertura
COMMENT 'Ponte N:N entre apolice e cobertura, com papel (principal/adicional) e capital da cobertura.'
AS
WITH ap AS (
  SELECT numero_apolice, cobertura_principal_codigo, capital_segurado_principal,
         possui_ipta, possui_ifpd, possui_doencas_graves, possui_dit, possui_assistencia_funeral
  FROM pos_venda.silver_ldp.pagamento_pendente
  QUALIFY row_number() OVER (PARTITION BY numero_apolice ORDER BY data_vencimento DESC, pendencia_id) = 1
)
SELECT xxhash64(numero_apolice) AS apolice_sk, xxhash64(cobertura_principal_codigo) AS cobertura_sk,
       'PRINCIPAL' AS papel_cobertura, CAST(capital_segurado_principal AS DECIMAL(14,2)) AS capital_segurado_cobertura
FROM ap
UNION ALL
SELECT xxhash64(numero_apolice), xxhash64('IPTA'), 'ADICIONAL', CAST(capital_segurado_principal * 1.0 AS DECIMAL(14,2)) FROM ap WHERE possui_ipta
UNION ALL
SELECT xxhash64(numero_apolice), xxhash64('IFPD'), 'ADICIONAL', CAST(capital_segurado_principal * 0.5 AS DECIMAL(14,2)) FROM ap WHERE possui_ifpd
UNION ALL
SELECT xxhash64(numero_apolice), xxhash64('DGR'), 'ADICIONAL', CAST(capital_segurado_principal * 0.3 AS DECIMAL(14,2)) FROM ap WHERE possui_doencas_graves
UNION ALL
SELECT xxhash64(numero_apolice), xxhash64('DIT'), 'ADICIONAL', CAST(NULL AS DECIMAL(14,2)) FROM ap WHERE possui_dit
UNION ALL
SELECT xxhash64(numero_apolice), xxhash64('AFU'), 'ADICIONAL', CAST(NULL AS DECIMAL(14,2)) FROM ap WHERE possui_assistencia_funeral;
