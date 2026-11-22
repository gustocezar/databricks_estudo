-- Gerado por gerar_sql.py | pipeline Lakeflow | gold.dim_data
CREATE OR REFRESH MATERIALIZED VIEW pos_venda.gold_ldp.dim_data
COMMENT 'Dimensao data (calendario 2015-2030) usada nos papeis: vencimento, emissao, extracao, ultima tentativa.'
AS
SELECT
  CAST(date_format(d, 'yyyyMMdd') AS INT) AS data_sk,
  d AS data,
  year(d) AS ano,
  CASE WHEN month(d) <= 6 THEN 1 ELSE 2 END AS semestre,
  quarter(d) AS trimestre,
  month(d) AS mes,
  element_at(array('Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro',
                   'Outubro', 'Novembro', 'Dezembro'), month(d)) AS nome_mes,
  date_format(d, 'yyyy-MM') AS ano_mes,
  day(d) AS dia,
  ((dayofweek(d) + 5) % 7) + 1 AS dia_semana,
  element_at(array('Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'),
             ((dayofweek(d) + 5) % 7) + 1) AS nome_dia_semana,
  weekofyear(d) AS semana_ano,
  dayofweek(d) IN (1, 7) AS fim_de_semana,
  d = last_day(d) AS ultimo_dia_mes
FROM (SELECT explode(sequence(DATE'2015-01-01', DATE'2030-12-31', INTERVAL 1 DAY)) AS d);
