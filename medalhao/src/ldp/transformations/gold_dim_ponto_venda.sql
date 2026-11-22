-- Gerado por gerar_sql.py | pipeline Lakeflow | gold.dim_ponto_venda
CREATE OR REFRESH MATERIALIZED VIEW pos_venda.gold_ldp.dim_ponto_venda
COMMENT 'Dimensao ponto de venda (escritorio de corretor, agencia bancaria, plataforma digital, televendas).'
AS
SELECT
  xxhash64(ponto_venda_codigo) AS ponto_venda_sk,
  ponto_venda_codigo, ponto_venda_nome, ponto_venda_tipo, canal_venda,
  ponto_venda_cidade, ponto_venda_uf, ponto_venda_regional
FROM pos_venda.silver_ldp.pagamento_pendente
QUALIFY row_number() OVER (PARTITION BY ponto_venda_codigo ORDER BY data_vencimento DESC, pendencia_id) = 1;
