# Inventário · pos_venda

> Gerado por `docs/gerar_inventario.py` em 22/11/2026 21:23. Não edite à mão: rode o script de novo.

## Projeto local

| Pasta | Script | Para quê |
|---|---|---|
| `.` | `01_gerar_one_table.py` | pos_venda · 01 · One Table — pagamentos pendentes (seguro de vida) |
| `carga_diaria` | `gerar_carga.py` | Gera os notebooks e o SQL do pipeline de CARGA DIARIA do dominio pos_venda. |
| `carga_diaria` | `janela_avaliacao.py` | Janela de avaliacao do DQX Studio (dominio pos_venda). |
| `carga_diaria` | `views_preservadas.py` | Cria ou atualiza views do Unity Catalog sem perder a governança. |
| `dqx_studio/demo` | `resumo_evolucao.py` | Monta a evolucao semana a semana a partir do historico do DQX Studio (execucoes com TODAS as linhas das janelas). |
| `dqx_studio/painel` | `aplicar_e_testar.py` | Cria as views do painel (views_painel.sql) e testa cada consulta do painel como o AI/BI vai executá-la. |
| `dqx_studio/painel` | `descricoes_painel.py` | Descrição das colunas das views do painel de qualidade (pos_venda.dq.v_painel_*). |
| `dqx_studio/painel` | `gerar_painel.py` | Gera o painel AI/BI "pos_venda · Qualidade de dados" (src/pos_venda_qualidade.lvdash.json). |
| `dqx_studio/regras` | `carregar_regras.py` | Carrega as regras de definir_regras.py no DQX Studio pela API e, opcionalmente, roda um dry run em cada tabela. |
| `dqx_studio/regras` | `definir_regras.py` | Regras de qualidade (DQX) do dominio pos_venda: bronze, silver e gold (star schema). |
| `dqx_studio/regras` | `registro_studio.py` | Leva as regras do pos_venda para o Registro de Regras e as Tabelas Monitoradas do DQX Studio (o que o menu do app mostra). |
| `dqx_studio/regras` | `rodar_ciclos.py` | Roda ciclos de carga (1 semana por ciclo) e, depois de cada um, executa as regras no DQX Studio. |
| `governanca` | `aplicar_descricoes.py` | Grava a descrição de cada coluna das camadas principais do pos_venda (dicionário descricoes_colunas.py). |
| `governanca` | `aplicar_rely.py` | RELY nas 14 chaves primárias da gold, com prova de unicidade e medição antes/depois. |
| `governanca` | `aplicar_semantica.py` | Aplica a camada semântica do domínio Pós-venda no Unity Catalog (Discover), a partir de ontologia.py. |
| `governanca` | `aplicar_sql.py` | Executa uma lista de comandos SQL (arquivo .json com lista de strings) no warehouse do projeto. |
| `governanca` | `auditar_metadados.py` | Audita os metadados do catálogo pos_venda no Unity Catalog: descrições (tabelas e colunas) e tags (catálogo, |
| `governanca` | `descricoes_colunas.py` | Descrições de coluna do domínio Pós-venda (uma por nome de coluna, com exceções por tabela). |
| `governanca/genie/avaliacao_boas_praticas` | `extrair.py` | Gera space_config e data_context no formato do genie-best-practices-agent, sem Spark (SDK + warehouse). |
| `governanca/genie/avaliacao_boas_praticas` | `rodar.py` | Uso: rodar.py <repo> <base> <endpoint> <espaco>:<bench 0/1> [...] |
| `governanca` | `genie.py` | Espaços Genie do domínio Pós-venda: analista financeiro e diretor financeiro. |
| `governanca` | `gerar_ontologia_sql.py` | Gera ontologia.sql: a camada de ontologia (pos_venda.ontologia) e as metric views financeiras. |
| `governanca` | `ontologia.py` | Ontologia do domínio Pós-venda (seguro de vida): fonte única do conhecimento de negócio. |
| `governanca/ontologia_readiness` | `avaliar.py` | Avaliação de prontidão para a Genie Ontology (app genie-ontology-readiness v1.5.0), gravada no histórico. |
| `governanca/ontologia_readiness` | `implantar_app.py` | Implanta o genie-ontology-readiness v1.5.0 com histórico no Lakebase (Autoscaling) do projeto do DQX Studio. |
| `governanca` | `sql_util.py` | Execução de SQL no warehouse do projeto pelo CLI (perfil dbx-workshop), com detecção da cota diária do Free Edition. |
| `medalhao` | `gerar_sql.py` | Gera o SQL do medalhão pos_venda (bronze -> silver -> gold/star schema) nas DUAS abordagens: |
| `paineis_financeiros` | `gerar_paineis.py` | Gera os painéis AI/BI de KPIs financeiros do Pós-venda a partir das metric views (pos_venda.ontologia.mv_*). |
| `paineis_financeiros/powerbi/auditoria` | `pba_oauth.py` | Roda o powerbi-analyzer (pba) com um perfil OAuth do Databricks CLI. |
| `paineis_financeiros/powerbi` | `gerar_powerbi.py` | Opção Power BI dos painéis financeiros do Pós-venda (para comparar com os painéis AI/BI do Databricks). |
| `regras/features` | `environment.py` | Ganchos do behave: deixa `uc` importável e confere, antes do primeiro cenário, que as funções existem. |
| `regras/features/steps` | `regras_steps.py` | Passos dos cenários: traduzem a frase de negócio em uma chamada à função do Unity Catalog e conferem a resposta. |
| `regras` | `funcoes.py` | Regras de negócio do pós-venda como funções SQL do Unity Catalog (fonte única da regra). |
| `regras` | `paridade.py` | Paridade: as funções de regra devolvem exatamente o que o pipeline já gravou? |
| `regras` | `uc.py` | Cliente mínimo da Statement Execution API (SDK do Databricks), usado pelas funções, pelos cenários e pela paridade. |

| Bundle | Arquivo |
|---|---|
| `pos_venda_carga_diaria` | `carga_diaria/databricks.yml` |
| `pos_venda_painel_qualidade` | `dqx_studio/painel/databricks.yml` |
| `pos_venda_medalhao` | `medalhao/databricks.yml` |
| `pos_venda_paineis_financeiros` | `paineis_financeiros/databricks.yml` |

## Workspace (Unity Catalog e recursos)

| Schema | Tabelas | Views | Metric views | Outros |
|---|---|---|---|---|
| `bi` | 0 | 8 | 0 | — |
| `bronze` | 1 | 0 | 0 | — |
| `bronze_ldp` | 0 | 0 | 0 | MATERIALIZED_VIEW 1 |
| `bronze_sql` | 1 | 0 | 0 | — |
| `default` | 0 | 0 | 0 | — |
| `dq` | 1 | 15 | 0 | — |
| `fonte` | 1 | 0 | 0 | — |
| `gold` | 17 | 0 | 0 | — |
| `gold_ldp` | 0 | 0 | 0 | MATERIALIZED_VIEW 14 |
| `gold_sql` | 14 | 0 | 0 | — |
| `landing` | 1 | 0 | 0 | — |
| `ontologia` | 3 | 10 | 4 | — |
| `regras` | 0 | 0 | 0 | — |
| `silver` | 0 | 0 | 0 | STREAMING_TABLE 4 |
| `silver_ldp` | 0 | 0 | 0 | MATERIALIZED_VIEW 1 |
| `silver_sql` | 1 | 0 | 0 | — |

### Painéis AI/BI

| Painel | ID |
|---|---|
| pos_venda · KPIs financeiros · Analista | `01f1e47bee3a1c5ebd180bfff03034a7` |
| pos_venda · KPIs financeiros · Diretoria | `01f1e47bee241a5da58e8c357f99d8f5` |
| pos_venda · Qualidade de dados | `01f1e410f7f419f19ad6d416805a9bb2` |

### Espaços Genie

| Espaço | ID |
|---|---|
| Pós-venda · Analista financeiro (cobrança e recuperação) | `01f1e4772cf610a8baf0c236595c284b` |
| Pós-venda · Diretor financeiro (visão executiva) | `01f1e477314b1903a4212843cf0dabf1` |

### Jobs

| Job | ID | Agenda |
|---|---|---|
| pos_venda_carga_diaria | `288828593679314` | PAUSED |
| pos_venda_carga_setup | `539329578539712` | sem agenda |
| pos_venda_medalhao_lakeflow_job | `827822094941996` | PAUSED |
| pos_venda_medalhao_sql | `446390966394300` | PAUSED |

### Apps do workspace (o Free Edition permite 3; o dqx-studio para sozinho após 24 h)

| App | Estado |
|---|---|
| dqx-studio | STOPPED |
| genie-ontology-readiness | STOPPED |

## Metadados (última auditoria)

Auditoria de 22/11/2026 16:18: 65 tabelas e views nas camadas principais, 1977 de 1977 colunas descritas (100%). Detalhe em `governanca/auditar_metadados.py`.
