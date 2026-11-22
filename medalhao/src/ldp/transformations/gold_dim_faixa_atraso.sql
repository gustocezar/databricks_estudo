-- Gerado por gerar_sql.py | pipeline Lakeflow | gold.dim_faixa_atraso
CREATE OR REFRESH MATERIALIZED VIEW pos_venda.gold_ldp.dim_faixa_atraso
COMMENT 'Dimensao faixa de atraso (catalogo fixo, ordenado).'
AS
SELECT xxhash64(faixa_atraso) AS faixa_atraso_sk, faixa_atraso, descricao_faixa, dias_min, dias_max, ordem_faixa
FROM VALUES
  ('00_VENCE_HOJE', 'Vence hoje', 0, 0, 0),
  ('01_1_A_15', '1 a 15 dias', 1, 15, 1),
  ('02_16_A_30', '16 a 30 dias', 16, 30, 2),
  ('03_31_A_60', '31 a 60 dias', 31, 60, 3),
  ('04_61_A_90', '61 a 90 dias', 61, 90, 4),
  ('05_91_A_120', '91 a 120 dias', 91, 120, 5),
  ('06_ACIMA_120', 'Acima de 120 dias', 121, CAST(NULL AS INT), 6)
  AS t(faixa_atraso, descricao_faixa, dias_min, dias_max, ordem_faixa);
