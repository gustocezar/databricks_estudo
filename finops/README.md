# FinOps · custo e uso do workspace no padrão FOCUS

Visões de custo e de uso do workspace no schema **`pos_venda.finops`**, todas geradas por
[`gerar_finops.py`](gerar_finops.py). A base segue a especificação
[FinOps FOCUS 1.4](https://focus.finops.org/what-is-focus/) ([especificação](https://github.com/FinOps-Open-Cost-and-Usage-Spec/FOCUS_Spec)). As outras visões respondem a perguntas diferentes:

- quanto custa cada funcionalidade do Databricks;
- de quem é cada custo;
- quem usa painéis, Genie e consultas;
- o que o time de plataforma e o time de squad precisam ver;
- quais boas práticas de custo estão atendidas.

```
system.billing.usage × list_prices ─► focus_custo_uso (FOCUS 1.4 + colunas x_: projeto, time, BRL)
         │
         ├─► custo_por_funcionalidade · custo_sql_por_consulta ─► custo_por_projeto_diario
         ├─► plataforma_*  (custo diário e anomalias, cobertura de atribuição, top recursos, warehouses)
         ├─► squad_*       (custo mensal, custo unitário, uso)
         ├─► uso_*         (painéis, Genie UI × API, consultas, jobs) ◄── audit, query.history, lakeflow
         └─► boas_praticas_custo · mv_finops_custo (metric view)
```

**Não altera o `finops.observability`.** O framework FinOps que já existe no workspace (28 visões `v_focus_*`) fica
como está, por decisão do dono. Deste schema só lemos o câmbio e o desconto de `v_focus_price_config`. Em 23/11, 19
das 28 visões falhavam: a base `v_focus_cost_usage` guardou o struct `usage_metadata` inteiro, e o struct ganhou campos
(50 na época, 58 hoje). A base nova escolhe os campos um a um, então não quebra quando a tabela de sistema muda (L76).

## As visões

| Visão | Para quem | Responde |
|---|---|---|
| `focus_custo_uso` | todos | dataset FOCUS 1.4 Cost and Usage: as 65 colunas mais as colunas `x_` (projeto, time, funcionalidade, BRL, canal da Genie) |
| `custo_por_funcionalidade` | todos | custo por mês e funcionalidade do Databricks (SQL warehouse, Jobs, Genie, Lakebase, Apps...), com a categoria FOCUS e a participação no mês |
| `custo_sql_por_consulta` | plataforma e squad | custo do warehouse rateado por consulta, pelo tempo de trabalho; horas sem consulta ficam como "Warehouse ocioso" |
| `custo_por_projeto_diario` | plataforma e squad | custo por dia, projeto, time e funcionalidade; o SQL entra rateado por consulta e o total bate com a base |
| `uso_paineis_diario` | squad | aberturas da versão publicada e do rascunho, consultas e usuários de cada painel |
| `uso_genie_diario` | squad | perguntas, leituras, aberturas e usuários por espaço, separando **UI (pessoas)** de **API (automação e avaliações)**, com os DBUs |
| `uso_consultas_diario` | plataforma e squad | consultas por origem (painel, Genie, job, CLI, Power BI): execuções, falhas, duração, fila e custo |
| `uso_jobs_diario` | squad | execuções, falhas, duração, custo por execução e custo das execuções com falha |
| `plataforma_custo_diario` | plataforma | custo diário por funcionalidade com a média dos 7 dias anteriores e a marcação de anomalia |
| `plataforma_atribuicao_mensal` | plataforma | quanto do custo tem dono (tag ou regra), é compartilhado ou não tem regra |
| `plataforma_top_recursos` | plataforma | recursos que mais custaram nos últimos 30 dias |
| `plataforma_warehouses` | plataforma | configuração de cada warehouse com custo, ociosidade e fila dos últimos 30 dias |
| `squad_custo_mensal` | squad | custo mensal do projeto por funcionalidade e variação sobre o mês anterior |
| `squad_custo_unitario` | squad | custo por execução de job, consulta, visualização de painel, pergunta à Genie e dia de app |
| `squad_uso_diario` | squad | uso diário dos ativos do projeto (painéis, Genie por canal, consultas, jobs) |
| `boas_praticas_custo` | plataforma e squad | práticas de custo com métrica, meta e situação (detalhe abaixo) |
| `mv_finops_custo` | todos | metric view para Genie e painéis: custo de lista, efetivo e faturado por funcionalidade, projeto e time |
| `config_custo`, `config_atribuicao`, `config_ativos` | quem mantém | parâmetros (câmbio, desconto, plano), regras de atribuição e nomes de painéis, espaços Genie e projetos Lakebase |

Todas as colunas têm descrição no Unity Catalog.

## Como a base FOCUS foi montada

A consulta de referência é [`focus/focus_query_1_4.sql`](https://github.com/databricks-solutions/cloud-infra-costs)
do repositório databricks-solutions/cloud-infra-costs (commit `70905cf`), que mapeia as tabelas de sistema para
FOCUS 1.4. A base deste projeto segue essa consulta, com quatro diferenças:

| Coluna | Aqui | Por quê |
|---|---|---|
| `BilledCost` | 0 | A FOCUS exige o valor faturado, não estimado, e o Free Edition não emite fatura. Em workspace pago, `config_custo.faturado = true` usa o custo efetivo até a fatura sair |
| `ContractedCost`, `EffectiveCost` | `ListCost × (1 − desconto global)` | O desconto vem de `finops.observability.v_focus_price_config`. Não há `account_prices`, um recurso em preview, nem descontos por compromisso |
| `ResourceId` da Genie | o espaço (`usage_metadata.genie.agent_id`) | A consulta de referência deixava `GENIE` |
| Colunas `x_` | projeto, time, tipo de time, origem da atribuição, funcionalidade, serverless, canal da Genie, custos em BRL | A FOCUS exige o prefixo `x_` em colunas próprias |

**A medida de custo das visões é o `ListCost`**, o custo a preço de lista em USD: no Free Edition é o que o consumo
custaria num workspace pago. O SKU `GENIE_FREE_USAGE` não tem preço; ele aparece com `x_SemPreco = true` e custo 0, mas
os DBUs ficam registrados.

## Atribuição: de quem é cada custo

Cada linha de consumo ganha um projeto e um time, nesta ordem:

1. **Tag `project` no recurso.** Hoje só os jobs do framework de Observabilidade têm essa tag, com `team=engenharia-dados`.
2. **Regras pelo nome do recurso** (`REGRAS` em `gerar_finops.py`). Exemplos: jobs `pos_venda%`, os apps `dqx-studio` e
   `genie-ontology-readiness`, os espaços Genie "Pós-venda…", os painéis "pos_venda…" e o projeto Lakebase `dqx-studio-db`.
3. **Compartilhado:** SQL warehouse, armazenamento, rede, otimização preditiva e endpoints de modelos. O warehouse é
   depois **rateado por consulta**: cada consulta ganha o dono pela origem (espaço Genie, painel, job) ou pelo catálogo
   que cita (`pos_venda.` ou `finops.`).
4. **Não atribuído:** o resto, inclusive os projetos Lakebase que já foram removidos.

| Tipo de time | Quem |
|---|---|
| `squad` | pós-venda, dr-silva, dbx-community-rj, central-dado-hub, dbx-agentic-psp |
| `plataforma` | engenharia-dados (framework de Observabilidade e FinOps) |
| `compartilhado` | recursos usados por todos, ainda não rateados (exceto o warehouse, rateado por consulta) |

Para mudar uma atribuição, edite `REGRAS` e rode `aplicar`. Para que os nomes de painéis, espaços Genie e projetos
Lakebase acompanhem o workspace, rode `ativos` antes.

## Boas práticas medidas

| Código | Prática | Fonte |
|---|---|---|
| CO-01-06 | Usar serviços serverless | Well-Architected da Databricks ([databricks-waf](https://github.com/databricks-solutions/databricks-waf)) |
| CO-01-02 | Usar job compute, não all-purpose | idem |
| CO-02-02 | Auto stop de até 10 minutos | idem |
| CO-03-01 | Tags para atribuir custo | idem |
| CO-03-01b | Todo custo com dono | FOCUS (alocação) e este projeto |
| CO-03-02 | Budget policies no consumo serverless | idem WAF |
| CO-03-03 | Monitorar custo contra o esperado (anomalias) | idem |
| CO-03-05 | Crescimento do armazenamento | idem |
| CO-03-06 | VACUUM e retenção (otimização preditiva) | idem |
| SS-005 | Fila do warehouse | [powerbi-analyzer](https://github.com/databricks-solutions/powerbi-analyzer) |
| WH-OCIOSO | Custo de warehouse sem consulta | [dbx-adoption-monitor](https://github.com/databricks-solutions/dbx-adoption-monitor) (custo por consulta) |
| JOB-FALHA | Custo de execuções com falha | este projeto |
| GENIE-CANAL | Separar uso humano da Genie de automação | dbx-adoption-monitor |
| PAINEL-PUBLICADO | Consumo pelo painel publicado, não pelo rascunho | dbx-adoption-monitor |
| FOCUS-PRECO | Todo consumo pago com preço de lista | FOCUS 1.4 |

## Rodar

```bash
cd pos_venda
python3 finops/gerar_finops.py ativos     # nomes de painéis, espaços Genie e projetos Lakebase (ativos.json)
python3 finops/gerar_finops.py aplicar    # schema e visões; só recria a visão cuja definição mudou
python3 finops/gerar_finops.py conferir   # cada visão responde + os totais batem com o faturamento (conferencia.json)
```

`gerar` só escreve [`finops.sql`](finops.sql), para leitura.

## Conferência

`conferir` grava o resultado em [`conferencia.json`](conferencia.json). Resultado em 23/11/2026:

| Checagem | Resultado |
|---|---|
| Cada visão responde | 19/19 visões e a metric view |
| Linhas da base FOCUS = linhas de `system.billing.usage` | 27.613 = 27.613 (o número cresce a cada ingestão do billing) |
| Custo da base = uso × preço de lista, calculado à parte | US$ 1.217,11 = US$ 1.217,11 |
| Custo por funcionalidade e por projeto = base | iguais (diferença abaixo de 1 milionésimo) |
| SQL rateado por consulta = SQL da base | US$ 938,40 = US$ 938,40 |
| `ServiceCategory` só com valores da FOCUS 1.4 | 0 linhas fora |
| Colunas obrigatórias da FOCUS sem nulo | 0 linhas com nulo |

## O que os números mostram (22/06 a 23/11/2026, a preço de lista)

| Quem | Custo de lista | Parte |
|---|---|---|
| Plataforma: framework de Observabilidade (jobs de monitoramento sobre tabelas de sistema) | US$ 938,80 | 77,1% |
| Não atribuído (US$ 92,07 de três projetos Lakebase já removidos) | US$ 125,74 | 10,3% |
| Squad pós-venda | US$ 64,85 | 5,3% |
| Outros squads (dr-silva, dbx-community-rj, dbx-agentic-psp, central-dado-hub) | US$ 73,34 | 6,0% |
| Compartilhado (armazenamento, rede, otimização preditiva, modelos) | US$ 14,38 | 1,2% |

- **Por funcionalidade**, o SQL warehouse leva 77%. Depois vêm:
  - Lakebase: US$ 93,62;
  - Jobs: US$ 87,70;
  - Apps: US$ 75,33.
  
  A Genie consumiu 309 DBUs, quase todos no SKU gratuito `GENIE_FREE_USAGE`.
- **Boas práticas (últimos 30 dias): 11 atendem e 4 pedem atenção.**
  - Tags cobrem 22,4% do custo (meta: 80%).
  - Nenhum consumo serverless tem budget policy.
  - O armazenamento cresceu 506% sobre os 30 dias anteriores.
  - 64,5% das aberturas de painel foram no rascunho, e não na versão publicada.
- **Genie:** as 249 perguntas de novembro aos espaços do pós-venda vieram todas pela API, isto é, das avaliações
  automáticas. O uso por pessoas (UI) foi zero.
- **Custo unitário do pós-venda em novembro:**
  - US$ 0,0063 por consulta SQL (5.758 consultas);
  - US$ 0,09 por execução de job (150 execuções);
  - US$ 2,98 por dia de app ativo.

**Achado da atribuição:** na primeira versão, 80% do custo ficou sem dono. A causa eram 2.122 consultas de cinco jobs que
já não existem em `system.lakeflow.jobs` e que não têm nome no billing. Todas liam só tabelas de sistema (consultas
lentas, falhas, custo sem tag). A regra passou a decidir pelo texto da consulta quando a origem não tem nome, e o não
atribuído caiu para 10,3% (L77).
