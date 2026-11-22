-- Gerado por gerar_carga.py | silver.pendencia_evento_quarentena (eventos NAO aptos, com o motivo)
CREATE OR REFRESH STREAMING TABLE pos_venda.silver.pendencia_evento_quarentena
COMMENT 'Quarentena: eventos do bronze que violaram uma regra de erro e foram barrados antes da silver. Guarda a linha original e o motivo da rejeicao.'
AS
SELECT * EXCEPT (_motivo_rejeicao), _motivo_rejeicao AS motivo_rejeicao, current_timestamp() AS _quarentena_ts
FROM STREAM(bronze_avaliado)
WHERE _motivo_rejeicao IS NOT NULL;
