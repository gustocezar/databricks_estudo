-- Gerado por gerar_sql.py | pipeline Lakeflow | gold.dim_forma_pagamento
CREATE OR REFRESH MATERIALIZED VIEW pos_venda.gold_ldp.dim_forma_pagamento
COMMENT 'Dimensao forma de pagamento.'
AS
SELECT xxhash64(forma_pagamento) AS forma_pagamento_sk, forma_pagamento,
       CASE forma_pagamento WHEN 'DEBITO_CONTA' THEN 'AUTOMATICO' WHEN 'PIX_AUTOMATICO' THEN 'AUTOMATICO'
            WHEN 'CARTAO_CREDITO' THEN 'CARTAO' ELSE 'BOLETO' END AS grupo_forma_pagamento
FROM pos_venda.silver_ldp.pagamento_pendente
QUALIFY row_number() OVER (PARTITION BY forma_pagamento ORDER BY data_vencimento DESC, pendencia_id) = 1;
