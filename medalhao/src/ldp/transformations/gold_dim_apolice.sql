-- Gerado por gerar_sql.py | pipeline Lakeflow | gold.dim_apolice
CREATE OR REFRESH MATERIALIZED VIEW pos_venda.gold_ldp.dim_apolice
COMMENT 'Dimensao apolice de vida (vigencia, capital, premio, endossos e beneficiarios).'
AS
SELECT
  xxhash64(numero_apolice) AS apolice_sk,
  numero_apolice, status_apolice, data_emissao, data_inicio_vigencia, data_fim_vigencia_atual, dia_vencimento,
  capital_segurado_principal, capital_segurado_total, valor_premio_periodico,
  possui_ipta, possui_ifpd, possui_doencas_graves, possui_dit, possui_assistencia_funeral, qtd_coberturas,
  qtd_endossos, numero_ultimo_endosso, tipo_ultimo_endosso, data_ultimo_endosso,
  qtd_beneficiarios, parentesco_beneficiario_principal
FROM pos_venda.silver_ldp.pagamento_pendente
QUALIFY row_number() OVER (PARTITION BY numero_apolice ORDER BY data_vencimento DESC, pendencia_id) = 1;
