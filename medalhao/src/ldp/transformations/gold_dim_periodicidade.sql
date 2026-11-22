-- Gerado por gerar_sql.py | pipeline Lakeflow | gold.dim_periodicidade
CREATE OR REFRESH MATERIALIZED VIEW pos_venda.gold_ldp.dim_periodicidade
COMMENT 'Dimensao periodicidade de pagamento do premio.'
AS
SELECT xxhash64(periodicidade_pagamento) AS periodicidade_sk, periodicidade_pagamento, meses_periodicidade,
       CAST(12 / meses_periodicidade AS INT) AS parcelas_por_ano
FROM pos_venda.silver_ldp.pagamento_pendente
QUALIFY row_number() OVER (PARTITION BY periodicidade_pagamento ORDER BY data_vencimento DESC, pendencia_id) = 1;
