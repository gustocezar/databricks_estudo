-- Gerado por gerar_carga.py | visao temporaria: bronze + motivo de rejeicao (NULL = evento apto)
CREATE TEMPORARY VIEW bronze_avaliado AS
SELECT b.*, CASE
    WHEN b.pendencia_id IS NULL THEN 'pendencia_id_nulo'
    WHEN b.tipo_evento IS NULL OR b.tipo_evento NOT IN ('NOVA', 'ATUALIZACAO', 'BAIXA') THEN 'tipo_evento_invalido'
    WHEN b.status_cobranca IS NULL OR b.status_cobranca NOT IN ('PENDENTE', 'EM_COBRANCA', 'PROMESSA_PAGAMENTO', 'NEGOCIADO', 'COBRANCA_EXTERNA', 'PAGA') THEN 'status_cobranca_invalido'
    WHEN b.valor_parcela IS NULL OR b.valor_parcela <= 0 THEN 'valor_parcela_nao_positivo'
    WHEN abs(b.valor_total_pendente - (b.valor_parcela + b.valor_multa + b.valor_juros)) >= 0.01 THEN 'valor_total_inconsistente'
    WHEN b.data_vencimento >= b.data_extracao THEN 'vencimento_nao_anterior_ao_evento'
    WHEN b.dias_atraso <> datediff(b.data_extracao, b.data_vencimento) THEN 'atraso_nao_confere_com_as_datas'
    WHEN NOT (b.valor_multa <=> pos_venda.regras.valor_multa(b.valor_parcela))
      OR NOT (b.valor_juros <=> pos_venda.regras.valor_juros(b.valor_parcela, b.dias_atraso))
      OR NOT (b.valor_total_pendente <=> pos_venda.regras.valor_total_pendente(b.valor_parcela, b.dias_atraso)) THEN 'valores_fora_da_regra'
    WHEN b.tipo_evento = 'BAIXA' AND (b.data_baixa IS NULL OR b.valor_pago IS NULL) THEN 'baixa_sem_data_ou_valor_pago'
    WHEN upper(trim(b.cliente_uf)) NOT IN ('AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO') THEN 'uf_invalida'
    WHEN b.cliente_idade < 18 THEN 'cliente_menor_de_idade'
  END AS _motivo_rejeicao
FROM STREAM(pos_venda.bronze.pagamentos_pendentes_eventos) b;
