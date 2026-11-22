-- Gerado por gerar_sql.py | pipeline Lakeflow | gold.dim_cobertura
CREATE OR REFRESH MATERIALIZED VIEW pos_venda.gold_ldp.dim_cobertura
COMMENT 'Dimensao cobertura (catalogo de coberturas de vida).'
AS
SELECT xxhash64(cobertura_codigo) AS cobertura_sk, cobertura_codigo, cobertura_nome, grupo_cobertura
FROM VALUES
  ('MORTE', 'Morte (natural ou acidental)', 'MORTE'),
  ('IPTA', 'Invalidez Permanente Total por Acidente', 'INVALIDEZ'),
  ('IFPD', 'Invalidez Funcional Permanente Total por Doenca', 'INVALIDEZ'),
  ('DGR', 'Doencas Graves', 'DOENCAS_GRAVES'),
  ('DIT', 'Diaria por Incapacidade Temporaria', 'INCAPACIDADE_TEMPORARIA'),
  ('AFU', 'Assistencia Funeral', 'ASSISTENCIA')
  AS t(cobertura_codigo, cobertura_nome, grupo_cobertura);
