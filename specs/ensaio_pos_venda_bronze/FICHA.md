# Ficha da base · ensaio com a bronze do pos_venda

> Preenchida no ensaio de 24/11/2026 (T0.1, T0.2, T1.1 a T1.3). Consultas só de leitura.

## Ambiente

| Item | Valor |
|---|---|
| Workspace (perfil do CLI) | `dbx-workshop` |
| Usuário | o do perfil (e-mail omitido: repositório público) |
| Plano | Free Edition |
| Serverless disponível? | sim |
| Vagas de app livres | 1 de 3 (`dqx-studio` e `genie-ontology-readiness` em uso) |

## Permissões

| Objeto | O que o perfil tem | Fonte |
|---|---|---|
| catálogo `pos_venda` | **dono** (`catalog_owner = current_user()`): tem todos os privilégios e pode conceder | `system.information_schema.catalogs` |
| schema `pos_venda.bronze` | **dono** | `system.information_schema.schemata` |
| outros principais com acesso | 3 service principals: `SELECT`, `USE CATALOG` e `USE SCHEMA` no catálogo ou na bronze | `SHOW GRANTS ON CATALOG pos_venda`, `SHOW GRANTS ON SCHEMA pos_venda.bronze` |
| pode conceder `USE CATALOG` e `CREATE SCHEMA` a um service principal? | **sim**, por ser dono | idem |

`SHOW GRANTS` não lista o dono do objeto. Só a consulta ao dono mostrou que o perfil pode conceder (L93).

## Colunas

97 colunas, todas com descrição (`information_schema.columns`). Os conceitos do modelo estão todos presentes com o
mesmo nome. A lista completa sai de `databricks experimental aitools tools discover-schema`.

## Perfil

| Medida | Valor | Consulta |
|---|---|---|
| linhas no total | 1.718.895 | `count(*)` |
| dias de extração | 236 (19/05/2026 a 09/01/2027) | `count(DISTINCT data_extracao)`, `min`, `max` |
| linhas por dia (mín, mediana, máx) | 2.529 · 7.717,5 · 8.839 | `count(*)` por `data_extracao` |
| chave repetida (pendência + dia + tipo) | 10.277 combinações | `GROUP BY pendencia_id, data_extracao, tipo_evento HAVING count(*) > 1` |
| nulos nas obrigatórias | `pendencia_id` 290 · `data_vencimento` 25 · `tipo_evento` 118 · `valor_parcela` 0 · `status_cobranca` 0 | `sum(CASE WHEN col IS NULL …)` |
| status distintos | 6 canônicos + 4 variantes: `EM COBRANCA` (180), `CANCELADO` (173), `PAGO` (159), `pendente` (154) | `GROUP BY status_cobranca` |
| tipos de evento | `NOVA`, `ATUALIZACAO`, `BAIXA` + `ESTORNO` (114) e nulo (118) | `GROUP BY tipo_evento` |
| formas de pagamento | 4 do catálogo + `VALE_REFEICAO` (418), `TRANSFERENCIA_INTERNACIONAL` (408), `CRIPTOMOEDA` (394) | `GROUP BY forma_pagamento` |
| periodicidades | 4 do domínio + `QUINZENAL` (136), `BIMESTRAL` (121) | `GROUP BY periodicidade_pagamento` |
| vencimento | 18/05/2026 a 05/02/2027 | `min`, `max` |
| valor da parcela | −1.750,84 a 14.892,62; 1.033 linhas com valor ≤ 0 | `min`, `max`, `sum(CASE WHEN valor_parcela <= 0 …)` |
| dias de atraso | 0 a 96 | `min`, `max` |

## Perguntas (Passo 0 do playbook)

| Pergunta | Esta base |
|---|---|
| Como chega? | eventos diários append-only (`NOVA`, `ATUALIZACAO`, `BAIXA`), com tipos fora do domínio |
| Tem chave da pendência? | sim, `pendencia_id`, com 290 nulos |
| Tem data do evento ou da foto? | sim, `data_extracao` |
| O que muda no tempo? | status, valores e atraso |
| Medidas | saldo (posição, semiaditivo) e recuperado (fluxo) |
| Dado pessoal | sim: CPF, nome, contato e RG, todos com a tag `dado_pessoal` |
| O que torna o dado inutilizável? | chave nula, tipo e status fora do domínio, valor ≤ 0, totais e datas incoerentes |
| Quem consome? | diretoria e analista financeiro (no ensaio, os mesmos do pos_venda) |
| Tem regulação ou auditoria? | SUSEP e LGPD (simulado) |
| Onde roda? | Free Edition |

**Perfil pronto escolhido:** A (eventos de cobrança com carteira). **Trilha do DQX:** B possível (dono do
catálogo); A também serve.
