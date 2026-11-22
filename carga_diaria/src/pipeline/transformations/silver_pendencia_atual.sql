-- Gerado por gerar_carga.py | silver.pendencia_atual (estado atual, SCD Tipo 1)
CREATE OR REFRESH STREAMING TABLE pos_venda.silver.pendencia_atual
COMMENT 'Silver estado atual: 1 linha por pendencia_id com o ultimo estado conhecido (SCD1). Base das dimensoes da gold.';

CREATE FLOW pendencia_atual_flow AS AUTO CDC INTO pos_venda.silver.pendencia_atual
FROM STREAM(pos_venda.silver.pendencia_evento)
KEYS (pendencia_id)
SEQUENCE BY data_extracao
STORED AS SCD TYPE 1;
