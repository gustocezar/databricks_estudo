# Databricks notebook source
# MAGIC %md
# MAGIC # pos_venda · 20 · Gold · dimensões do star schema
# MAGIC Atualiza as dimensões a partir da `silver.pendencia_atual`. Na primeira execução cria cada tabela e declara a **PRIMARY KEY**
# MAGIC (informativa no Unity Catalog) com **RELY**: a chave é única por construção (`xxhash64` da chave de negócio, conferido por
# MAGIC `governanca/aplicar_rely.py verificar`), e o RELY deixa o otimizador eliminar junções com dimensões que a consulta não usa.
# MAGIC Nas execuções seguintes faz `INSERT OVERWRITE`, que mantém a tabela e as constraints.
# MAGIC As chaves substitutas são `xxhash64(chave de negócio)`: estáveis entre execuções, então a fato histórica continua válida.

# COMMAND ----------

import json

CAT = "pos_venda"
DIMS = [
    ('dim_cliente', 'cliente_sk', 'Dimensao cliente (cadastro padronizado). SK = xxhash64(cliente_id).', """
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
FROM pos_venda.silver.pendencia_atual
QUALIFY row_number() OVER (PARTITION BY cliente_id ORDER BY data_extracao DESC, pendencia_id) = 1
"""),
    ('dim_apolice', 'apolice_sk', 'Dimensao apolice de vida (vigencia, capital, premio, endossos, beneficiarios).', """
SELECT
  xxhash64(numero_apolice) AS apolice_sk,
  numero_apolice, status_apolice, data_emissao, data_inicio_vigencia, data_fim_vigencia_atual, dia_vencimento,
  capital_segurado_principal, capital_segurado_total, valor_premio_periodico,
  possui_ipta, possui_ifpd, possui_doencas_graves, possui_dit, possui_assistencia_funeral, qtd_coberturas,
  qtd_endossos, numero_ultimo_endosso, tipo_ultimo_endosso, data_ultimo_endosso,
  qtd_beneficiarios, parentesco_beneficiario_principal
FROM pos_venda.silver.pendencia_atual
QUALIFY row_number() OVER (PARTITION BY numero_apolice ORDER BY data_extracao DESC, pendencia_id) = 1
"""),
    ('dim_produto', 'produto_sk', 'Dimensao produto de seguro de vida.', """
SELECT xxhash64(produto_codigo) AS produto_sk, produto_codigo, produto_nome, categoria_produto, ramo,
       cobertura_principal_codigo, cobertura_principal_nome
FROM pos_venda.silver.pendencia_atual
QUALIFY row_number() OVER (PARTITION BY produto_codigo ORDER BY data_extracao DESC, pendencia_id) = 1
"""),
    ('dim_cobertura', 'cobertura_sk', 'Dimensao cobertura (catalogo fixo de coberturas de vida).', """
SELECT xxhash64(cobertura_codigo) AS cobertura_sk, cobertura_codigo, cobertura_nome, grupo_cobertura
FROM VALUES
  ('MORTE', 'Morte (natural ou acidental)', 'MORTE'),
  ('IPTA', 'Invalidez Permanente Total por Acidente', 'INVALIDEZ'),
  ('IFPD', 'Invalidez Funcional Permanente Total por Doenca', 'INVALIDEZ'),
  ('DGR', 'Doencas Graves', 'DOENCAS_GRAVES'),
  ('DIT', 'Diaria por Incapacidade Temporaria', 'INCAPACIDADE_TEMPORARIA'),
  ('AFU', 'Assistencia Funeral', 'ASSISTENCIA')
  AS t(cobertura_codigo, cobertura_nome, grupo_cobertura)
"""),
    ('bridge_apolice_cobertura', 'apolice_sk, cobertura_sk', 'Ponte N:N entre apolice e cobertura, com papel (principal/adicional) e capital da cobertura. PK composta.', """
WITH ap AS (
  SELECT numero_apolice, cobertura_principal_codigo, capital_segurado_principal,
         possui_ipta, possui_ifpd, possui_doencas_graves, possui_dit, possui_assistencia_funeral
  FROM pos_venda.silver.pendencia_atual
  QUALIFY row_number() OVER (PARTITION BY numero_apolice ORDER BY data_extracao DESC, pendencia_id) = 1
)
SELECT xxhash64(numero_apolice) AS apolice_sk, xxhash64(cobertura_principal_codigo) AS cobertura_sk,
       'PRINCIPAL' AS papel_cobertura, CAST(capital_segurado_principal AS DECIMAL(14,2)) AS capital_segurado_cobertura FROM ap
UNION ALL SELECT xxhash64(numero_apolice), xxhash64('IPTA'), 'ADICIONAL', CAST(capital_segurado_principal * 1.0 AS DECIMAL(14,2)) FROM ap WHERE possui_ipta
UNION ALL SELECT xxhash64(numero_apolice), xxhash64('IFPD'), 'ADICIONAL', CAST(capital_segurado_principal * 0.5 AS DECIMAL(14,2)) FROM ap WHERE possui_ifpd
UNION ALL SELECT xxhash64(numero_apolice), xxhash64('DGR'), 'ADICIONAL', CAST(capital_segurado_principal * 0.3 AS DECIMAL(14,2)) FROM ap WHERE possui_doencas_graves
UNION ALL SELECT xxhash64(numero_apolice), xxhash64('DIT'), 'ADICIONAL', CAST(NULL AS DECIMAL(14,2)) FROM ap WHERE possui_dit
UNION ALL SELECT xxhash64(numero_apolice), xxhash64('AFU'), 'ADICIONAL', CAST(NULL AS DECIMAL(14,2)) FROM ap WHERE possui_assistencia_funeral
"""),
    ('dim_corretor', 'corretor_sk', 'Dimensao corretor, com membro NAO_INFORMADO para vendas sem corretor (digital e televendas).', """
SELECT * FROM (
  SELECT xxhash64(corretor_id) AS corretor_sk, corretor_id, corretor_nome, corretor_tipo_pessoa, corretor_documento,
         corretor_registro_susep, corretor_regional, corretor_comissao_pct, corretor_status, corretor_data_credenciamento
  FROM pos_venda.silver.pendencia_atual
  WHERE corretor_id IS NOT NULL
  QUALIFY row_number() OVER (PARTITION BY corretor_id ORDER BY data_extracao DESC, pendencia_id) = 1
)
UNION ALL
SELECT xxhash64('NAO_INFORMADO'), 'NAO_INFORMADO', 'Venda sem corretor', CAST(NULL AS STRING), CAST(NULL AS STRING),
       CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS DECIMAL(5,2)), CAST(NULL AS STRING), CAST(NULL AS DATE)
"""),
    ('dim_ponto_venda', 'ponto_venda_sk', 'Dimensao ponto de venda (escritorio, agencia bancaria, plataforma digital, televendas).', """
SELECT xxhash64(ponto_venda_codigo) AS ponto_venda_sk, ponto_venda_codigo, ponto_venda_nome, ponto_venda_tipo, canal_venda,
       ponto_venda_cidade, ponto_venda_uf, ponto_venda_regional
FROM pos_venda.silver.pendencia_atual
QUALIFY row_number() OVER (PARTITION BY ponto_venda_codigo ORDER BY data_extracao DESC, pendencia_id) = 1
"""),
    ('dim_periodicidade', 'periodicidade_sk', 'Dimensao periodicidade de pagamento do premio (catalogo fixo).', """
SELECT xxhash64(periodicidade_pagamento) AS periodicidade_sk, periodicidade_pagamento, meses_periodicidade,
       CAST(12 / meses_periodicidade AS INT) AS parcelas_por_ano
FROM VALUES ('MENSAL', 1), ('TRIMESTRAL', 3), ('SEMESTRAL', 6), ('ANUAL', 12) AS t(periodicidade_pagamento, meses_periodicidade)
"""),
    ('dim_forma_pagamento', 'forma_pagamento_sk', 'Dimensao forma de pagamento (catalogo fixo).', """
SELECT xxhash64(forma_pagamento) AS forma_pagamento_sk, forma_pagamento, grupo_forma_pagamento
FROM VALUES ('DEBITO_CONTA', 'AUTOMATICO'), ('PIX_AUTOMATICO', 'AUTOMATICO'), ('CARTAO_CREDITO', 'CARTAO'), ('BOLETO', 'BOLETO')
  AS t(forma_pagamento, grupo_forma_pagamento)
"""),
    ('dim_status_cobranca', 'status_cobranca_sk', 'Dimensao status de cobranca (ciclo de vida da pendencia, incluindo PAGA).', """
SELECT xxhash64(status_cobranca) AS status_cobranca_sk, status_cobranca, fase_cobranca, ordem_fase, em_aberto
FROM VALUES
  ('PENDENTE', 'INICIAL', 1, true), ('EM_COBRANCA', 'INTERNA', 2, true), ('PROMESSA_PAGAMENTO', 'NEGOCIACAO', 3, true),
  ('NEGOCIADO', 'NEGOCIACAO', 4, true), ('COBRANCA_EXTERNA', 'EXTERNA', 5, true), ('PAGA', 'ENCERRADA', 6, false)
  AS t(status_cobranca, fase_cobranca, ordem_fase, em_aberto)
"""),
    ('dim_motivo_pendencia', 'motivo_pendencia_sk', 'Dimensao motivo da pendencia (catalogo fixo, com agrupamento).', """
SELECT xxhash64(motivo_pendencia) AS motivo_pendencia_sk, motivo_pendencia, grupo_motivo
FROM VALUES
  ('SALDO_INSUFICIENTE', 'FINANCEIRO'), ('LIMITE_INSUFICIENTE', 'FINANCEIRO'), ('CARTAO_RECUSADO', 'FINANCEIRO'),
  ('BOLETO_NAO_PAGO', 'FINANCEIRO'), ('DADOS_BANCARIOS_INVALIDOS', 'CADASTRAL'), ('CONTA_ENCERRADA', 'CADASTRAL'),
  ('CARTAO_EXPIRADO', 'CADASTRAL'), ('AUTORIZACAO_DEBITO_CANCELADA', 'AUTORIZACAO'), ('AUTORIZACAO_PIX_REVOGADA', 'AUTORIZACAO'),
  ('BOLETO_NAO_RECEBIDO', 'OPERACIONAL') AS t(motivo_pendencia, grupo_motivo)
"""),
    ('dim_faixa_atraso', 'faixa_atraso_sk', 'Dimensao faixa de atraso (catalogo fixo, ordenado).', """
SELECT xxhash64(faixa_atraso) AS faixa_atraso_sk, faixa_atraso, descricao_faixa, dias_min, dias_max, ordem_faixa
FROM VALUES
  ('00_VENCE_HOJE', 'Vence hoje', 0, 0, 0), ('01_1_A_15', '1 a 15 dias', 1, 15, 1), ('02_16_A_30', '16 a 30 dias', 16, 30, 2),
  ('03_31_A_60', '31 a 60 dias', 31, 60, 3), ('04_61_A_90', '61 a 90 dias', 61, 90, 4),
  ('05_91_A_120', '91 a 120 dias', 91, 120, 5), ('06_ACIMA_120', 'Acima de 120 dias', 121, CAST(NULL AS INT), 6)
  AS t(faixa_atraso, descricao_faixa, dias_min, dias_max, ordem_faixa)
"""),
    ('dim_data', 'data_sk', 'Dimensao data (calendario 2015-2030). Papeis na fato: referencia, vencimento, emissao, entrada, ultima tentativa.', """
SELECT CAST(date_format(d, 'yyyyMMdd') AS INT) AS data_sk, d AS data, year(d) AS ano,
  CASE WHEN month(d) <= 6 THEN 1 ELSE 2 END AS semestre, quarter(d) AS trimestre, month(d) AS mes,
  element_at(array('Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'), month(d)) AS nome_mes,
  date_format(d, 'yyyy-MM') AS ano_mes, day(d) AS dia, ((dayofweek(d) + 5) % 7) + 1 AS dia_semana,
  element_at(array('Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'), ((dayofweek(d) + 5) % 7) + 1) AS nome_dia_semana,
  weekofyear(d) AS semana_ano, dayofweek(d) IN (1, 7) AS fim_de_semana, d = last_day(d) AS ultimo_dia_mes
FROM (SELECT explode(sequence(DATE'2015-01-01', DATE'2030-12-31', INTERVAL 1 DAY)) AS d)
"""),
]

resultado = {}
for nome, pk, comentario, sql in DIMS:
    fq = f"{CAT}.gold.{nome}"
    if not spark.catalog.tableExists(fq):
        spark.sql(f"CREATE TABLE {fq} COMMENT '{comentario}' AS {sql}")
        for c in [x.strip() for x in pk.split(",")]:
            spark.sql(f"ALTER TABLE {fq} ALTER COLUMN {c} SET NOT NULL")
        spark.sql(f"ALTER TABLE {fq} ADD CONSTRAINT pk_{nome} PRIMARY KEY ({pk}) RELY")
        acao = "criada"
    else:
        spark.sql(f"INSERT OVERWRITE TABLE {fq} {sql}")
        acao = "atualizada"
    resultado[nome] = [acao, spark.table(fq).count()]

dbutils.notebook.exit(json.dumps(resultado))
