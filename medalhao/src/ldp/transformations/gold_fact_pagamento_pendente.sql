-- Gerado por gerar_sql.py | pipeline Lakeflow | gold.fact_pagamento_pendente
CREATE OR REFRESH MATERIALIZED VIEW pos_venda.gold_ldp.fact_pagamento_pendente (
  CONSTRAINT valor_total_positivo EXPECT (valor_total_pendente > 0),
  CONSTRAINT cliente_sk_nao_nulo EXPECT (cliente_sk IS NOT NULL)
)
COMMENT 'Fato: 1 linha por parcela de apolice pendente de pagamento (foto na data de extracao). Medidas: valores, dias de atraso, tentativas.'
AS
SELECT
  pendencia_id,
  numero_apolice,
  numero_parcela,
  xxhash64(cliente_id) AS cliente_sk,
  xxhash64(numero_apolice) AS apolice_sk,
  xxhash64(produto_codigo) AS produto_sk,
  xxhash64(coalesce(corretor_id, 'NAO_INFORMADO')) AS corretor_sk,
  xxhash64(ponto_venda_codigo) AS ponto_venda_sk,
  xxhash64(periodicidade_pagamento) AS periodicidade_sk,
  xxhash64(forma_pagamento) AS forma_pagamento_sk,
  xxhash64(status_cobranca) AS status_cobranca_sk,
  xxhash64(motivo_pendencia) AS motivo_pendencia_sk,
  xxhash64(faixa_atraso) AS faixa_atraso_sk,
  CAST(date_format(data_vencimento, 'yyyyMMdd') AS INT) AS data_vencimento_sk,
  CAST(date_format(data_emissao, 'yyyyMMdd') AS INT) AS data_emissao_apolice_sk,
  CAST(date_format(data_geracao_cobranca, 'yyyyMMdd') AS INT) AS data_geracao_cobranca_sk,
  CAST(date_format(data_ultima_tentativa, 'yyyyMMdd') AS INT) AS data_ultima_tentativa_sk,
  CAST(date_format(data_extracao, 'yyyyMMdd') AS INT) AS data_extracao_sk,
  canal_ultimo_contato,
  parcela_afetada_por_endosso,
  1 AS qtd_parcelas_pendentes,
  valor_parcela,
  valor_multa,
  valor_juros,
  valor_total_pendente,
  dias_atraso,
  tentativas_cobranca
FROM pos_venda.silver_ldp.pagamento_pendente;
