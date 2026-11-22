-- Gerado por gerar_carga.py | silver.pendencia_hist (HISTORICA, SCD Tipo 2)
CREATE OR REFRESH STREAMING TABLE pos_venda.silver.pendencia_hist
COMMENT 'Silver historica (SCD2): uma linha por versao da pendencia. Uma nova versao nasce quando o status de cobranca muda ou a parcela e paga. __START_AT/__END_AT = vigencia [inicio, fim).';

CREATE FLOW pendencia_hist_flow AS AUTO CDC INTO pos_venda.silver.pendencia_hist
FROM STREAM(pos_venda.silver.pendencia_evento)
KEYS (pendencia_id)
SEQUENCE BY data_extracao
STORED AS SCD TYPE 2
TRACK HISTORY ON status_cobranca, data_baixa;
