# Avaliação das ações de observabilidade do workspace

> Avaliação de 23/11/2026. Os números vivos estão na visão `pos_venda.conformidade.acoes_observabilidade`.

**Pergunta:** as ações de observabilidade que já rodam no workspace podem entrar no framework?

**Resposta:** sim, em parte. Das 8 ações:
- 3 foram **internalizadas**: a lógica passou a viver em `pos_venda.conformidade` e `pos_venda.finops`, com meta e
  histórico;
- 2 seguem como estão (**manter**);
- 1 precisa de ajuste (**consertar**);
- 1 não serve no Free Edition (**aposentar**);
- 1 continua **só leitura**, por decisão do dono.

Nada do bundle `observabilidade-framework` nem de `finops.observability` foi alterado. As recomendações abaixo
ficam para o dono decidir.

## O que roda hoje

O bundle `observabilidade-framework` (target `dev`) tem 6 jobs, 5 alertas SQL e grava em `main.observabilidade_dev`:
12 tabelas, 17 visões e o volume `relatorios`. Ao lado dele está o framework FinOps anterior, `finops.observability`,
com 28 visões.

| Ação | O que faz | O que encontramos | Veredito | Onde ficou |
|---|---|---|---|---|
| Materialização diária das tabelas de sistema (job, 6h) | Recria 10 tabelas de saúde (clusters, policies, warehouses, custo) e o histórico de tamanho das tabelas | Roda sem falha, mas 7 das 10 tabelas ficam vazias: tratam de clusters clássicos, spot e policies, que o Free Edition não tem. O histórico de tamanho funciona | internalizar | Regras PLT01 a PLT05 em `pos_venda.conformidade`; armazenamento em `pos_venda.finops` |
| Detecção de anomalias: auditoria e segurança (job, 7h) | Consulta clusters sem policy, warehouses e eventos de permissão; o resultado fica só na saída do notebook | Roda sem falha; a parte de clusters volta vazia | internalizar | PLT04 (auto-stop do warehouse) |
| Triagem automática de falhas de job (job, 7h30) | Classifica as falhas e mantém `vw_triagem_falhas_jobs` | Roda sem falha e classifica as falhas recentes | manter | P28 (matriz de resiliência) consulta a triagem; o custo das falhas está em `pos_venda.finops.uso_jobs_diario` |
| Relatório executivo semanal (job, segunda 7h) | Grava um relatório em arquivo no volume `relatorios` | Roda sem falha; não envia nada para fora do workspace | manter | Próximo passo natural: incluir o resumo de `boas_praticas_dados` |
| Alertas SQL (5) | Queries lentas (de hora em hora), jobs com falha (3 vezes ao dia), custo diário alto, recursos sem tag e tráfego no AI Gateway (1 vez ao dia) | Rodam como jobs ocultos, que não aparecem na lista de jobs. São a maior parte do custo de observabilidade, quase tudo do alerta horário | consertar | Regra PLT06 (até 4 disparos por dia) |
| Rightsizing semanal de clusters (job, segunda 8h) | Sugere o tamanho de cluster a partir de `system.compute.node_timeline` | Falha em toda execução (`NameError: name 'null' is not defined`) e não há cluster clássico para dimensionar | aposentar | Nenhum |
| Visões `vw_*` em `main.observabilidade_dev` (job sem agenda) | 17 visões sobre as tabelas de sistema | Todas respondem, mas as de custo repetem `pos_venda.finops` sem a atribuição por projeto; `vw_governanca_cobertura_tags` conta registros, não custo; `vw_inventario_tabelas` não traz descrição, tags nem dono | internalizar | `pos_venda.finops` e `pos_venda.conformidade.ativos` |
| Framework FinOps anterior, `finops.observability` | 28 visões FOCUS e de histórias executivas | 19 não respondem: congelaram um esquema antigo do `usage_metadata` do billing (L76) | manter só leitura | A sonda diária (USO03) mede as quebradas sem mexer nelas |

## Quanto custa

Custo a preço de lista, medido em `pos_venda.finops`. A janela é de 30 dias até 23/11/2026; o total vai desde
22/06.

| Ação | Execuções (30 dias) | Falhas | Custo em 30 dias |
|---|---|---|---|
| Alertas SQL (5) | 136 consultas | — | US$ 38,64 (só o alerta horário: US$ 29,73 em 7 dias) |
| Materialização diária | 5 | 0 | US$ 5,33 |
| Detecção de anomalias | 6 | 0 | US$ 0,86 |
| Triagem de falhas | 4 | 0 | US$ 0,41 |
| Relatório executivo | 1 | 0 | US$ 0,11 |
| Rightsizing | 1 | 1 | US$ 0,00 |

- **Projeto inteiro.** O projeto `observabilidade-framework` custou US$ 49,29 nos últimos 30 dias e US$ 939,31 desde
  22/06, 77% de todo o custo do workspace.
- **Alertas.** Desde julho, as consultas dos alertas somam US$ 816,20, medidos às 16h (UTC) de 23/11.
- **Por que o alerta horário custa tanto.** Cada disparo acorda o warehouse, que fica ligado até o auto-stop de 10
  minutos. O custo do warehouse é rateado pelo tempo de execução das consultas: numa hora em que só o alerta rodou, a
  hora inteira fica com ele (L79).

## Como os alertas foram encontrados

Os alertas SQL novos (API `alerts-v2`) agendam a consulta por um job oculto. Esse job não aparece em
`databricks jobs list`, e `databricks jobs get` responde "does not exist". A API antiga, `databricks alerts list`,
volta vazia.

O que liga a consulta ao alerta é `system.query.history`: o campo `query_source.alert_id` traz o identificador do
alerta. No primeiro levantamento, consultamos só a API antiga e contamos 0 alertas; a contagem foi corrigida ao
seguir o custo dos jobs "apagados" (L79).

## Recomendações ao dono do bundle

Nenhuma foi aplicada.

1. **Espaçar o alerta de queries lentas** para até 4 disparos por dia, ou pausá-lo no Free Edition. É a maior
   economia isolada: cerca de US$ 4 por dia no ritmo atual.
2. **Pausar o rightsizing** enquanto o workspace for Free Edition. Consertar o notebook só ao migrar para clusters
   clássicos.
3. **Enxugar a materialização diária.** Tirar as 7 consultas de cluster que voltam vazias e manter o histórico de
   tamanho das tabelas.
4. **Pôr timeout e as tags `project` e `team` nos jobs.** Hoje 10 de 11 jobs estão sem timeout, e os jobs do
   pós-venda e do DQX Studio não têm as tags (regras PLT01 e PLT03).
5. **Apagar as 3 cópias quebradas** em `workspace.default` (`vw_billing_*`). Elas falham pela mesma causa das 19 de
   `finops.observability`.

## O que foi internalizado no framework

| Do bundle | Para |
|---|---|
| Checagens de warehouse, tags e policies (`policy_compliance_monitoring`, `workspace_health_summary`) | Regras PLT01 a PLT05, com meta, severidade, histórico e como corrigir |
| Frequência dos alertas | Regra PLT06 |
| Inventário de tabelas (`vw_inventario_tabelas`) | `pos_venda.conformidade.ativos`: descrição, tags, dono, PK, lineage e Predictive Optimization |
| Cobertura de tags (`vw_governanca_cobertura_tags`) | `pos_venda.finops` (custo com tag, ponderado pelo custo) e PLT01 e PLT05 (por recurso) |
| Visões de custo (`vw_billing_*`, `vw_custo_*`) | `pos_venda.finops` (FOCUS 1.4 e atribuição por projeto) |
| Saber se as visões ainda respondem | Sonda diária `registrar` e regra USO03, para o workspace inteiro |

As práticas correspondentes são P35 a P37 do [framework](../docs/04_FRAMEWORK.md).
