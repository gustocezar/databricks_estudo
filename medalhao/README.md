# pos_venda · medalhão (bronze → silver → gold/star schema)

Duas implementações independentes do mesmo pipeline de dados, a partir da one-table
`pos_venda.landing.pagamentos_pendentes_one_table` (500.000 linhas, 91 colunas, dados sintéticos).

| | A) Notebooks SQL | B) Lakeflow (SDP) |
|---|---|---|
| Recurso | job `pos_venda_medalhao_sql` (3 tarefas: bronze → silver → gold) | pipeline `pos_venda_medalhao_lakeflow` (16 views materializadas) |
| Grava em | `pos_venda.bronze_sql / silver_sql / gold_sql` | `pos_venda.bronze_ldp / silver_ldp / gold_ldp` |
| Como funciona | `CREATE OR REPLACE TABLE` a cada execução | `CREATE OR REFRESH MATERIALIZED VIEW` + expectations de qualidade |
| Agenda | no próprio job (06:00) | no job auxiliar `pos_venda_medalhao_lakeflow_job` (06:30) |

As duas escrevem em schemas diferentes de propósito: o pipeline é dono das tabelas que cria e um notebook não
consegue sobrescrevê-las (e vice-versa).

## Camadas

- **Bronze** `pagamentos_pendentes`: cópia fiel da one-table + `_ingestao_ts`, `_lote_id`, `_origem`, `_hash_linha`.
- **Silver** `pagamento_pendente`: 1 linha por `pendencia_id` (remove duplicatas), CPF/RG/celular/telefone/CEP/UF
  padronizados, e-mail em minúsculas, flags `dq_*` (CPF inválido, RG/celular/e-mail ausentes).
- **Gold (star schema)**: fato `fact_pagamento_pendente` (1 linha = 1 parcela pendente) + dimensões `dim_cliente`,
  `dim_apolice`, `dim_produto`, `dim_cobertura`, `dim_corretor` (com membro `NAO_INFORMADO`), `dim_ponto_venda`,
  `dim_periodicidade`, `dim_forma_pagamento`, `dim_status_cobranca`, `dim_motivo_pendencia`, `dim_faixa_atraso`,
  `dim_data` (papéis: vencimento, emissão, geração da cobrança, última tentativa, extração) e a ponte
  `bridge_apolice_cobertura`. Chaves substitutas: `xxhash64(chave_de_negócio)`.

## Rodar sob demanda

```bash
cd pos_venda/medalhao
databricks bundle deploy -t dev --profile dbx-workshop     # só quando mudar algo
databricks bundle run medalhao_sql -t dev --profile dbx-workshop   # A) notebooks SQL
databricks bundle run medalhao_ldp -t dev --profile dbx-workshop   # B) pipeline Lakeflow
```

## Ligar e desligar (agenda diária)

Cada abordagem tem uma agenda. As duas começam **PAUSED** (desligadas): só rodam quando você manda.

```bash
# ligar só a versão SQL
databricks bundle deploy -t dev --profile dbx-workshop --var="sql_schedule_status=UNPAUSED"
# ligar só o Lakeflow
databricks bundle deploy -t dev --profile dbx-workshop --var="ldp_schedule_status=UNPAUSED"
# ligar as duas
databricks bundle deploy -t dev --profile dbx-workshop --var="sql_schedule_status=UNPAUSED" --var="ldp_schedule_status=UNPAUSED"
# desligar tudo de novo (valores padrão = PAUSED)
databricks bundle deploy -t dev --profile dbx-workshop
```

Atalho sem reimplantar (muda direto no job; o próximo `bundle deploy` volta ao valor do bundle):

```bash
databricks jobs update --json '{"job_id": <ID>, "new_settings": {"schedule": {"quartz_cron_expression": "0 0 6 * * ?", "timezone_id": "America/Sao_Paulo", "pause_status": "UNPAUSED"}}}' --profile dbx-workshop
```

## Regenerar o SQL

O SQL das duas versões sai de `gerar_sql.py` (a lógica é definida uma vez só). Depois de editar:

```bash
python3 gerar_sql.py && databricks bundle deploy -t dev --profile dbx-workshop
```

## Limites da Free Edition que importam aqui

Só computação serverless; até 5 tarefas de job simultâneas; um pipeline ativo por tipo; um SQL warehouse 2X-Small.
Fonte: <https://docs.databricks.com/aws/en/getting-started/free-edition-limitations>.
