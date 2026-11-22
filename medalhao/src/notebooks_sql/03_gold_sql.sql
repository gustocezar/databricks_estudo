-- Databricks notebook source
-- MAGIC %md
-- MAGIC # pos_venda · medalhão (notebooks SQL) · GOLD
-- MAGIC Gerado por `gerar_sql.py`. Cada tabela e recriada a cada execucao (`CREATE OR REPLACE TABLE`).
-- MAGIC Destino: `pos_venda.gold_sql`.

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS pos_venda.gold_sql COMMENT 'pos_venda gold (abordagem notebooks SQL)';

-- COMMAND ----------

CREATE OR REPLACE TABLE pos_venda.gold_sql.dim_cliente
COMMENT 'Dimensao cliente (dados cadastrais padronizados). Chave substituta: xxhash64(cliente_id).'
AS
SELECT
  xxhash64(cliente_id) AS cliente_sk,
  cliente_id, cliente_nome, cliente_cpf, NOT dq_cpf_invalido AS cliente_cpf_valido,
  cliente_rg, cliente_rg_orgao_emissor, cliente_rg_uf_emissor, cliente_rg_data_emissao,
  cliente_data_nascimento, cliente_idade,
  CASE WHEN cliente_idade < 30 THEN '18-29' WHEN cliente_idade < 40 THEN '30-39' WHEN cliente_idade < 50 THEN '40-49'
       WHEN cliente_idade < 60 THEN '50-59' ELSE '60+' END AS cliente_faixa_etaria,
  cliente_sexo, cliente_estado_civil, cliente_profissao, cliente_renda_faixa, cliente_fumante,
  cliente_email, cliente_celular, cliente_telefone_fixo,
  cliente_logradouro, cliente_numero, cliente_complemento, cliente_bairro, cliente_cidade, cliente_uf, cliente_cep,
  cliente_endereco_completo, cliente_data_cadastro
FROM pos_venda.silver_sql.pagamento_pendente
QUALIFY row_number() OVER (PARTITION BY cliente_id ORDER BY data_vencimento DESC, pendencia_id) = 1;

-- COMMAND ----------

CREATE OR REPLACE TABLE pos_venda.gold_sql.dim_apolice
COMMENT 'Dimensao apolice de vida (vigencia, capital, premio, endossos e beneficiarios).'
AS
SELECT
  xxhash64(numero_apolice) AS apolice_sk,
  numero_apolice, status_apolice, data_emissao, data_inicio_vigencia, data_fim_vigencia_atual, dia_vencimento,
  capital_segurado_principal, capital_segurado_total, valor_premio_periodico,
  possui_ipta, possui_ifpd, possui_doencas_graves, possui_dit, possui_assistencia_funeral, qtd_coberturas,
  qtd_endossos, numero_ultimo_endosso, tipo_ultimo_endosso, data_ultimo_endosso,
  qtd_beneficiarios, parentesco_beneficiario_principal
FROM pos_venda.silver_sql.pagamento_pendente
QUALIFY row_number() OVER (PARTITION BY numero_apolice ORDER BY data_vencimento DESC, pendencia_id) = 1;

-- COMMAND ----------

CREATE OR REPLACE TABLE pos_venda.gold_sql.dim_produto
COMMENT 'Dimensao produto de seguro de vida.'
AS
SELECT
  xxhash64(produto_codigo) AS produto_sk,
  produto_codigo, produto_nome, categoria_produto, ramo, cobertura_principal_codigo, cobertura_principal_nome
FROM pos_venda.silver_sql.pagamento_pendente
QUALIFY row_number() OVER (PARTITION BY produto_codigo ORDER BY data_vencimento DESC, pendencia_id) = 1;

-- COMMAND ----------

CREATE OR REPLACE TABLE pos_venda.gold_sql.dim_cobertura
COMMENT 'Dimensao cobertura (catalogo de coberturas de vida).'
AS
SELECT xxhash64(cobertura_codigo) AS cobertura_sk, cobertura_codigo, cobertura_nome, grupo_cobertura
FROM VALUES
  ('MORTE', 'Morte (natural ou acidental)', 'MORTE'),
  ('IPTA', 'Invalidez Permanente Total por Acidente', 'INVALIDEZ'),
  ('IFPD', 'Invalidez Funcional Permanente Total por Doenca', 'INVALIDEZ'),
  ('DGR', 'Doencas Graves', 'DOENCAS_GRAVES'),
  ('DIT', 'Diaria por Incapacidade Temporaria', 'INCAPACIDADE_TEMPORARIA'),
  ('AFU', 'Assistencia Funeral', 'ASSISTENCIA')
  AS t(cobertura_codigo, cobertura_nome, grupo_cobertura);

-- COMMAND ----------

CREATE OR REPLACE TABLE pos_venda.gold_sql.bridge_apolice_cobertura
COMMENT 'Ponte N:N entre apolice e cobertura, com papel (principal/adicional) e capital da cobertura.'
AS
WITH ap AS (
  SELECT numero_apolice, cobertura_principal_codigo, capital_segurado_principal,
         possui_ipta, possui_ifpd, possui_doencas_graves, possui_dit, possui_assistencia_funeral
  FROM pos_venda.silver_sql.pagamento_pendente
  QUALIFY row_number() OVER (PARTITION BY numero_apolice ORDER BY data_vencimento DESC, pendencia_id) = 1
)
SELECT xxhash64(numero_apolice) AS apolice_sk, xxhash64(cobertura_principal_codigo) AS cobertura_sk,
       'PRINCIPAL' AS papel_cobertura, CAST(capital_segurado_principal AS DECIMAL(14,2)) AS capital_segurado_cobertura
FROM ap
UNION ALL
SELECT xxhash64(numero_apolice), xxhash64('IPTA'), 'ADICIONAL', CAST(capital_segurado_principal * 1.0 AS DECIMAL(14,2)) FROM ap WHERE possui_ipta
UNION ALL
SELECT xxhash64(numero_apolice), xxhash64('IFPD'), 'ADICIONAL', CAST(capital_segurado_principal * 0.5 AS DECIMAL(14,2)) FROM ap WHERE possui_ifpd
UNION ALL
SELECT xxhash64(numero_apolice), xxhash64('DGR'), 'ADICIONAL', CAST(capital_segurado_principal * 0.3 AS DECIMAL(14,2)) FROM ap WHERE possui_doencas_graves
UNION ALL
SELECT xxhash64(numero_apolice), xxhash64('DIT'), 'ADICIONAL', CAST(NULL AS DECIMAL(14,2)) FROM ap WHERE possui_dit
UNION ALL
SELECT xxhash64(numero_apolice), xxhash64('AFU'), 'ADICIONAL', CAST(NULL AS DECIMAL(14,2)) FROM ap WHERE possui_assistencia_funeral;

-- COMMAND ----------

CREATE OR REPLACE TABLE pos_venda.gold_sql.dim_corretor
COMMENT 'Dimensao corretor, com membro NAO_INFORMADO para vendas sem corretor (canais digital e televendas).'
AS
SELECT * FROM (
  SELECT
    xxhash64(corretor_id) AS corretor_sk,
    corretor_id, corretor_nome, corretor_tipo_pessoa, corretor_documento, corretor_registro_susep,
    corretor_regional, corretor_comissao_pct, corretor_status, corretor_data_credenciamento
  FROM pos_venda.silver_sql.pagamento_pendente
  WHERE corretor_id IS NOT NULL
  QUALIFY row_number() OVER (PARTITION BY corretor_id ORDER BY data_vencimento DESC, pendencia_id) = 1
)
UNION ALL
SELECT xxhash64('NAO_INFORMADO'), 'NAO_INFORMADO', 'Venda sem corretor', CAST(NULL AS STRING), CAST(NULL AS STRING),
       CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS DECIMAL(5,2)), CAST(NULL AS STRING), CAST(NULL AS DATE);

-- COMMAND ----------

CREATE OR REPLACE TABLE pos_venda.gold_sql.dim_ponto_venda
COMMENT 'Dimensao ponto de venda (escritorio de corretor, agencia bancaria, plataforma digital, televendas).'
AS
SELECT
  xxhash64(ponto_venda_codigo) AS ponto_venda_sk,
  ponto_venda_codigo, ponto_venda_nome, ponto_venda_tipo, canal_venda,
  ponto_venda_cidade, ponto_venda_uf, ponto_venda_regional
FROM pos_venda.silver_sql.pagamento_pendente
QUALIFY row_number() OVER (PARTITION BY ponto_venda_codigo ORDER BY data_vencimento DESC, pendencia_id) = 1;

-- COMMAND ----------

CREATE OR REPLACE TABLE pos_venda.gold_sql.dim_periodicidade
COMMENT 'Dimensao periodicidade de pagamento do premio.'
AS
SELECT xxhash64(periodicidade_pagamento) AS periodicidade_sk, periodicidade_pagamento, meses_periodicidade,
       CAST(12 / meses_periodicidade AS INT) AS parcelas_por_ano
FROM pos_venda.silver_sql.pagamento_pendente
QUALIFY row_number() OVER (PARTITION BY periodicidade_pagamento ORDER BY data_vencimento DESC, pendencia_id) = 1;

-- COMMAND ----------

CREATE OR REPLACE TABLE pos_venda.gold_sql.dim_forma_pagamento
COMMENT 'Dimensao forma de pagamento.'
AS
SELECT xxhash64(forma_pagamento) AS forma_pagamento_sk, forma_pagamento,
       CASE forma_pagamento WHEN 'DEBITO_CONTA' THEN 'AUTOMATICO' WHEN 'PIX_AUTOMATICO' THEN 'AUTOMATICO'
            WHEN 'CARTAO_CREDITO' THEN 'CARTAO' ELSE 'BOLETO' END AS grupo_forma_pagamento
FROM pos_venda.silver_sql.pagamento_pendente
QUALIFY row_number() OVER (PARTITION BY forma_pagamento ORDER BY data_vencimento DESC, pendencia_id) = 1;

-- COMMAND ----------

CREATE OR REPLACE TABLE pos_venda.gold_sql.dim_status_cobranca
COMMENT 'Dimensao status de cobranca, com a fase da regua de cobranca.'
AS
SELECT xxhash64(status_cobranca) AS status_cobranca_sk, status_cobranca,
       CASE status_cobranca WHEN 'PENDENTE' THEN 'INICIAL' WHEN 'EM_COBRANCA' THEN 'INTERNA'
            WHEN 'PROMESSA_PAGAMENTO' THEN 'NEGOCIACAO' WHEN 'NEGOCIADO' THEN 'NEGOCIACAO' ELSE 'EXTERNA' END AS fase_cobranca,
       CASE status_cobranca WHEN 'PENDENTE' THEN 1 WHEN 'EM_COBRANCA' THEN 2 WHEN 'PROMESSA_PAGAMENTO' THEN 3
            WHEN 'NEGOCIADO' THEN 4 ELSE 5 END AS ordem_fase
FROM pos_venda.silver_sql.pagamento_pendente
QUALIFY row_number() OVER (PARTITION BY status_cobranca ORDER BY data_vencimento DESC, pendencia_id) = 1;

-- COMMAND ----------

CREATE OR REPLACE TABLE pos_venda.gold_sql.dim_motivo_pendencia
COMMENT 'Dimensao motivo da pendencia de pagamento, com agrupamento.'
AS
SELECT xxhash64(motivo_pendencia) AS motivo_pendencia_sk, motivo_pendencia,
       CASE WHEN motivo_pendencia IN ('SALDO_INSUFICIENTE', 'LIMITE_INSUFICIENTE', 'CARTAO_RECUSADO', 'BOLETO_NAO_PAGO') THEN 'FINANCEIRO'
            WHEN motivo_pendencia IN ('DADOS_BANCARIOS_INVALIDOS', 'CONTA_ENCERRADA', 'CARTAO_EXPIRADO') THEN 'CADASTRAL'
            WHEN motivo_pendencia IN ('AUTORIZACAO_DEBITO_CANCELADA', 'AUTORIZACAO_PIX_REVOGADA') THEN 'AUTORIZACAO'
            ELSE 'OPERACIONAL' END AS grupo_motivo
FROM pos_venda.silver_sql.pagamento_pendente
QUALIFY row_number() OVER (PARTITION BY motivo_pendencia ORDER BY data_vencimento DESC, pendencia_id) = 1;

-- COMMAND ----------

CREATE OR REPLACE TABLE pos_venda.gold_sql.dim_faixa_atraso
COMMENT 'Dimensao faixa de atraso (catalogo fixo, ordenado).'
AS
SELECT xxhash64(faixa_atraso) AS faixa_atraso_sk, faixa_atraso, descricao_faixa, dias_min, dias_max, ordem_faixa
FROM VALUES
  ('00_VENCE_HOJE', 'Vence hoje', 0, 0, 0),
  ('01_1_A_15', '1 a 15 dias', 1, 15, 1),
  ('02_16_A_30', '16 a 30 dias', 16, 30, 2),
  ('03_31_A_60', '31 a 60 dias', 31, 60, 3),
  ('04_61_A_90', '61 a 90 dias', 61, 90, 4),
  ('05_91_A_120', '91 a 120 dias', 91, 120, 5),
  ('06_ACIMA_120', 'Acima de 120 dias', 121, CAST(NULL AS INT), 6)
  AS t(faixa_atraso, descricao_faixa, dias_min, dias_max, ordem_faixa);

-- COMMAND ----------

CREATE OR REPLACE TABLE pos_venda.gold_sql.dim_data
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

-- COMMAND ----------

CREATE OR REPLACE TABLE pos_venda.gold_sql.fact_pagamento_pendente
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
FROM pos_venda.silver_sql.pagamento_pendente;

-- COMMAND ----------

-- Conferencia: contagem das tabelas desta camada
SELECT 'dim_cliente' AS tabela, count(*) AS linhas FROM pos_venda.gold_sql.dim_cliente
UNION ALL
SELECT 'dim_apolice' AS tabela, count(*) AS linhas FROM pos_venda.gold_sql.dim_apolice
UNION ALL
SELECT 'dim_produto' AS tabela, count(*) AS linhas FROM pos_venda.gold_sql.dim_produto
UNION ALL
SELECT 'dim_cobertura' AS tabela, count(*) AS linhas FROM pos_venda.gold_sql.dim_cobertura
UNION ALL
SELECT 'bridge_apolice_cobertura' AS tabela, count(*) AS linhas FROM pos_venda.gold_sql.bridge_apolice_cobertura
UNION ALL
SELECT 'dim_corretor' AS tabela, count(*) AS linhas FROM pos_venda.gold_sql.dim_corretor
UNION ALL
SELECT 'dim_ponto_venda' AS tabela, count(*) AS linhas FROM pos_venda.gold_sql.dim_ponto_venda
UNION ALL
SELECT 'dim_periodicidade' AS tabela, count(*) AS linhas FROM pos_venda.gold_sql.dim_periodicidade
UNION ALL
SELECT 'dim_forma_pagamento' AS tabela, count(*) AS linhas FROM pos_venda.gold_sql.dim_forma_pagamento
UNION ALL
SELECT 'dim_status_cobranca' AS tabela, count(*) AS linhas FROM pos_venda.gold_sql.dim_status_cobranca
UNION ALL
SELECT 'dim_motivo_pendencia' AS tabela, count(*) AS linhas FROM pos_venda.gold_sql.dim_motivo_pendencia
UNION ALL
SELECT 'dim_faixa_atraso' AS tabela, count(*) AS linhas FROM pos_venda.gold_sql.dim_faixa_atraso
UNION ALL
SELECT 'dim_data' AS tabela, count(*) AS linhas FROM pos_venda.gold_sql.dim_data
UNION ALL
SELECT 'fact_pagamento_pendente' AS tabela, count(*) AS linhas FROM pos_venda.gold_sql.fact_pagamento_pendente;
