-- Gerado por gerar_sql.py | pipeline Lakeflow | gold.dim_produto
CREATE OR REFRESH MATERIALIZED VIEW pos_venda.gold_ldp.dim_produto
COMMENT 'Dimensao produto de seguro de vida.'
AS
SELECT
  xxhash64(produto_codigo) AS produto_sk,
  produto_codigo, produto_nome, categoria_produto, ramo, cobertura_principal_codigo, cobertura_principal_nome
FROM pos_venda.silver_ldp.pagamento_pendente
QUALIFY row_number() OVER (PARTITION BY produto_codigo ORDER BY data_vencimento DESC, pendencia_id) = 1;
