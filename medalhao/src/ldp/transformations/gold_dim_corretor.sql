-- Gerado por gerar_sql.py | pipeline Lakeflow | gold.dim_corretor
CREATE OR REFRESH MATERIALIZED VIEW pos_venda.gold_ldp.dim_corretor
COMMENT 'Dimensao corretor, com membro NAO_INFORMADO para vendas sem corretor (canais digital e televendas).'
AS
SELECT * FROM (
  SELECT
    xxhash64(corretor_id) AS corretor_sk,
    corretor_id, corretor_nome, corretor_tipo_pessoa, corretor_documento, corretor_registro_susep,
    corretor_regional, corretor_comissao_pct, corretor_status, corretor_data_credenciamento
  FROM pos_venda.silver_ldp.pagamento_pendente
  WHERE corretor_id IS NOT NULL
  QUALIFY row_number() OVER (PARTITION BY corretor_id ORDER BY data_vencimento DESC, pendencia_id) = 1
)
UNION ALL
SELECT xxhash64('NAO_INFORMADO'), 'NAO_INFORMADO', 'Venda sem corretor', CAST(NULL AS STRING), CAST(NULL AS STRING),
       CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS DECIMAL(5,2)), CAST(NULL AS STRING), CAST(NULL AS DATE);
