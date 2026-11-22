-- Gerado por gerar_sql.py | pipeline Lakeflow | gold.dim_cliente
CREATE OR REFRESH MATERIALIZED VIEW pos_venda.gold_ldp.dim_cliente
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
FROM pos_venda.silver_ldp.pagamento_pendente
QUALIFY row_number() OVER (PARTITION BY cliente_id ORDER BY data_vencimento DESC, pendencia_id) = 1;
