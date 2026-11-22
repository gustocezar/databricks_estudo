-- Databricks notebook source
-- MAGIC %md
-- MAGIC # pos_venda · medalhão (notebooks SQL) · SILVER
-- MAGIC Gerado por `gerar_sql.py`. Cada tabela e recriada a cada execucao (`CREATE OR REPLACE TABLE`).
-- MAGIC Destino: `pos_venda.silver_sql`.

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS pos_venda.silver_sql COMMENT 'pos_venda silver (abordagem notebooks SQL)';

-- COMMAND ----------

CREATE OR REPLACE TABLE pos_venda.silver_sql.pagamento_pendente
COMMENT 'Silver: 1 linha por pendencia_id, sem duplicatas, com CPF/RG/telefone/CEP/UF padronizados e flags de qualidade (dq_*).'
AS
WITH base AS (
  SELECT * FROM pos_venda.bronze_sql.pagamentos_pendentes
  QUALIFY row_number() OVER (PARTITION BY pendencia_id ORDER BY _ingestao_ts, _hash_linha) = 1
),
dig AS (
  SELECT b.*, regexp_replace(b.cliente_cpf, '[^0-9]', '') AS _cpf_dig FROM base b
),
norm AS (
  SELECT d.*, CASE WHEN length(d._cpf_dig) = 11 AND ((aggregate(zip_with(transform(sequence(1, 9), i -> CAST(substring(d._cpf_dig, i, 1) AS INT)), sequence(10, 2, -1), (digito, peso) -> digito * peso), 0, (acc, val) -> acc + val) * 10) % 11) % 10 = CAST(substring(d._cpf_dig, 10, 1) AS INT) AND ((aggregate(zip_with(transform(sequence(1, 10), i -> CAST(substring(d._cpf_dig, i, 1) AS INT)), sequence(11, 2, -1), (digito, peso) -> digito * peso), 0, (acc, val) -> acc + val) * 10) % 11) % 10 = CAST(substring(d._cpf_dig, 11, 1) AS INT) THEN true ELSE false END AS _cpf_valido FROM dig d
)
SELECT
  pendencia_id,
  data_extracao,
  sistema_origem,
  numero_apolice,
  numero_parcela,
  competencia,
  data_vencimento,
  data_geracao_cobranca,
  dias_atraso,
  faixa_atraso,
  valor_parcela,
  valor_multa,
  valor_juros,
  valor_total_pendente,
  status_cobranca,
  motivo_pendencia,
  tentativas_cobranca,
  data_ultima_tentativa,
  canal_ultimo_contato,
  parcela_afetada_por_endosso,
  ramo,
  status_apolice,
  produto_codigo,
  produto_nome,
  categoria_produto,
  canal_venda,
  data_emissao,
  data_inicio_vigencia,
  data_fim_vigencia_atual,
  dia_vencimento,
  periodicidade_pagamento,
  meses_periodicidade,
  forma_pagamento,
  valor_premio_periodico,
  capital_segurado_principal,
  capital_segurado_total,
  cobertura_principal_codigo,
  cobertura_principal_nome,
  possui_ipta,
  possui_ifpd,
  possui_doencas_graves,
  possui_dit,
  possui_assistencia_funeral,
  qtd_coberturas,
  qtd_endossos,
  numero_ultimo_endosso,
  tipo_ultimo_endosso,
  data_ultimo_endosso,
  qtd_beneficiarios,
  parentesco_beneficiario_principal,
  ponto_venda_codigo,
  ponto_venda_nome,
  ponto_venda_tipo,
  ponto_venda_cidade,
  ponto_venda_uf,
  ponto_venda_regional,
  corretor_id,
  corretor_nome,
  corretor_tipo_pessoa,
  corretor_documento,
  corretor_registro_susep,
  corretor_regional,
  corretor_comissao_pct,
  corretor_status,
  corretor_data_credenciamento,
  cliente_id,
  cliente_nome,
  _cpf_dig AS cliente_cpf,
  cliente_data_nascimento,
  cliente_idade,
  cliente_sexo,
  cliente_estado_civil,
  lower(trim(cliente_email)) AS cliente_email,
  regexp_replace(cliente_celular, '[^0-9]', '') AS cliente_celular,
  regexp_replace(cliente_telefone_fixo, '[^0-9]', '') AS cliente_telefone_fixo,
  upper(regexp_replace(cliente_rg, '[^0-9Xx]', '')) AS cliente_rg,
  cliente_rg_orgao_emissor,
  cliente_rg_uf_emissor,
  cliente_rg_data_emissao,
  cliente_logradouro,
  cliente_numero,
  cliente_complemento,
  cliente_bairro,
  regexp_replace(cliente_cep, '[^0-9]', '') AS cliente_cep,
  cliente_cidade,
  upper(cliente_uf) AS cliente_uf,
  cliente_endereco_completo,
  cliente_renda_faixa,
  cliente_profissao,
  cliente_fumante,
  cliente_data_cadastro,
  NOT _cpf_valido AS dq_cpf_invalido,
  cliente_rg IS NULL AS dq_rg_ausente,
  cliente_celular IS NULL AS dq_celular_ausente,
  cliente_email IS NULL AS dq_email_ausente,
  (cliente_email IS NOT NULL AND NOT (lower(trim(cliente_email)) RLIKE '^[^@ ]+@[^@ ]+[.][^@ ]+$')) AS dq_email_invalido,
  CAST(NOT _cpf_valido AS INT) + CAST(cliente_rg IS NULL AS INT) + CAST(cliente_celular IS NULL AS INT)
    + CAST(cliente_email IS NULL AS INT) AS dq_qtd_problemas,
  _ingestao_ts,
  _lote_id,
  _hash_linha,
  current_timestamp() AS _silver_ts
FROM norm
WHERE pendencia_id IS NOT NULL AND valor_total_pendente > 0 AND data_vencimento <= data_extracao;

-- COMMAND ----------

-- Conferencia: contagem das tabelas desta camada
SELECT 'pagamento_pendente' AS tabela, count(*) AS linhas FROM pos_venda.silver_sql.pagamento_pendente;
