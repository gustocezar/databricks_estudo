# Databricks notebook source
# MAGIC %md
# MAGIC # pos_venda · 00 · Setup (rodar uma vez)
# MAGIC Cria os schemas `fonte`, `bronze`, `silver` e `gold` e o **cadastro de apólices** do sistema de origem simulado
# MAGIC (`fonte.apolices`), a partir das apólices da one-table `landing`. Esse cadastro é a base do gerador diário.

# COMMAND ----------

import json

CAT = "pos_venda"
LANDING = f"{CAT}.landing.pagamentos_pendentes_one_table"
SEED = 20261118
POLICY_COLS = ['numero_apolice', 'ramo', 'status_apolice', 'produto_codigo', 'produto_nome', 'categoria_produto', 'canal_venda', 'data_emissao', 'data_inicio_vigencia', 'data_fim_vigencia_atual', 'dia_vencimento', 'periodicidade_pagamento', 'meses_periodicidade', 'forma_pagamento', 'valor_premio_periodico', 'capital_segurado_principal', 'capital_segurado_total', 'cobertura_principal_codigo', 'cobertura_principal_nome', 'possui_ipta', 'possui_ifpd', 'possui_doencas_graves', 'possui_dit', 'possui_assistencia_funeral', 'qtd_coberturas', 'qtd_endossos', 'numero_ultimo_endosso', 'tipo_ultimo_endosso', 'data_ultimo_endosso', 'qtd_beneficiarios', 'parentesco_beneficiario_principal', 'ponto_venda_codigo', 'ponto_venda_nome', 'ponto_venda_tipo', 'ponto_venda_cidade', 'ponto_venda_uf', 'ponto_venda_regional', 'corretor_id', 'corretor_nome', 'corretor_tipo_pessoa', 'corretor_documento', 'corretor_registro_susep', 'corretor_regional', 'corretor_comissao_pct', 'corretor_status', 'corretor_data_credenciamento', 'cliente_id', 'cliente_nome', 'cliente_cpf', 'cliente_data_nascimento', 'cliente_sexo', 'cliente_estado_civil', 'cliente_email', 'cliente_celular', 'cliente_telefone_fixo', 'cliente_rg', 'cliente_rg_orgao_emissor', 'cliente_rg_uf_emissor', 'cliente_rg_data_emissao', 'cliente_logradouro', 'cliente_numero', 'cliente_complemento', 'cliente_bairro', 'cliente_cep', 'cliente_cidade', 'cliente_uf', 'cliente_endereco_completo', 'cliente_renda_faixa', 'cliente_profissao', 'cliente_fumante', 'cliente_data_cadastro']

for s in ["fonte", "bronze", "silver", "gold"]:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CAT}.{s} COMMENT 'pos_venda - {s}'")

def U(salt, *cols):
    return f"(pmod(xxhash64({', '.join(cols)}, {SEED + salt}), 1000000) / 1000000.0)"

# COMMAND ----------

# perfil de pagador por apolice: define a chance de cada parcela virar pendencia
spark.sql(f"""
CREATE TABLE IF NOT EXISTS {CAT}.fonte.apolices
COMMENT 'Cadastro de apolices do sistema de origem simulado (apolice, cliente, corretor, ponto de venda). Base do gerador diario de pendencias.'
AS
WITH a AS (
  SELECT {", ".join(POLICY_COLS)}
  FROM {LANDING}
  QUALIFY row_number() OVER (PARTITION BY numero_apolice ORDER BY data_vencimento DESC, pendencia_id) = 1
),
b AS (
  SELECT a.* EXCEPT (dia_vencimento),
         CAST(1 + floor({U(212, "numero_apolice")} * 28) AS INT) AS dia_vencimento,   -- vencimento espalhado nos dias 1 a 28
         date_add(data_emissao, 10) AS _x, {U(201, "numero_apolice")} AS _u_perfil FROM a
)
SELECT b.* EXCEPT (_x, _u_perfil),
  CASE WHEN day(_x) <= dia_vencimento THEN make_date(year(_x), month(_x), dia_vencimento)
       ELSE make_date(year(add_months(_x, 1)), month(add_months(_x, 1)), dia_vencimento) END AS data_primeira_parcela,
  CASE WHEN _u_perfil < 0.40 THEN 'BOM' WHEN _u_perfil < 0.75 THEN 'REGULAR' ELSE 'CRONICO' END AS perfil_pagador,
  CASE WHEN _u_perfil < 0.40 THEN 0.02 WHEN _u_perfil < 0.75 THEN 0.48 ELSE 0.88 END AS p_inadimplencia
FROM b
""")

n = spark.table(f"{CAT}.fonte.apolices").count()
dbutils.notebook.exit(json.dumps({"apolices_no_cadastro": n}))
