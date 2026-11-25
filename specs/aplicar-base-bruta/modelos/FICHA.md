# Ficha da base · <nome da base>

> Preenchida nas tarefas T0.1, T0.2 e T1.1 a T1.3 (contrato: [SPEC](../aplicar-base-bruta/SPEC.md)). Os números saem de
> consultas só de leitura; anote cada consulta usada.

## Ambiente

| Item | Valor |
|---|---|
| Workspace (perfil do CLI) | |
| Usuário | |
| Plano | Free Edition / pago |
| Serverless disponível? | sim / não |
| Vagas de app livres | |

## Permissões

| Objeto | Privilégios que você tem | Fonte (`SHOW GRANTS …`) |
|---|---|---|
| catálogo da base | | |
| schema da base | | |
| tabela da base | | |
| catálogo de destino | | |
| sou dono do catálogo e do schema? (`SHOW GRANTS` não mostra o dono; L93) | sim / não | consulta do dono, abaixo |
| pode conceder `USE CATALOG` e `CREATE SCHEMA` a um service principal? | sim / não | |

## Consultas do perfil (modelo)

Troque `<tabela>`, `<catalogo>` e `<schema>`. Todas são só leitura.

```sql
-- dono (decide se você pode conceder privilégios; L93)
SELECT (SELECT catalog_owner = current_user() FROM system.information_schema.catalogs WHERE catalog_name = '<catalogo>') AS sou_dono_catalogo, (SELECT schema_owner = current_user() FROM system.information_schema.schemata WHERE catalog_name = '<catalogo>' AND schema_name = '<schema>') AS sou_dono_schema;
-- volume e período
SELECT count(*) linhas, count(DISTINCT data_extracao) dias, min(data_extracao), max(data_extracao) FROM <tabela>;
-- linhas por dia
SELECT min(n), percentile(n, 0.5), max(n) FROM (SELECT data_extracao, count(*) n FROM <tabela> GROUP BY 1);
-- nulos nas obrigatórias
SELECT sum(CASE WHEN pendencia_id IS NULL THEN 1 ELSE 0 END) sem_id, sum(CASE WHEN data_vencimento IS NULL THEN 1 ELSE 0 END) sem_venc,
       sum(CASE WHEN valor_parcela IS NULL THEN 1 ELSE 0 END) sem_valor, sum(CASE WHEN status_cobranca IS NULL THEN 1 ELSE 0 END) sem_status FROM <tabela>;
-- chave repetida
SELECT count(*) FROM (SELECT pendencia_id, data_extracao, tipo_evento FROM <tabela> GROUP BY ALL HAVING count(*) > 1);
-- domínios (repita para tipo, forma e periodicidade)
SELECT status_cobranca, count(*) FROM <tabela> GROUP BY 1 ORDER BY 2 DESC;
-- faixas
SELECT min(data_vencimento), max(data_vencimento), min(valor_parcela), max(valor_parcela),
       sum(CASE WHEN valor_parcela <= 0 THEN 1 ELSE 0 END), min(dias_atraso), max(dias_atraso) FROM <tabela>;
```

## Colunas

Cole aqui a saída do `discover-schema` (nome, tipo, nulos, exemplo).

## Perfil

| Medida | Valor | Consulta |
|---|---|---|
| linhas no total | | |
| linhas por dia de extração (mín, mediana, máx) | | |
| chaves duplicadas no mesmo dia | | |
| nulos nas colunas obrigatórias | | |
| status distintos | | |
| formas de pagamento distintas | | |
| periodicidades distintas | | |
| faixa de vencimento e de extração | | |
| valores de parcela (mín, máx, ≤ 0) | | |

## Perguntas (Passo 0 do playbook)

| Pergunta | pos_venda (referência) | Esta base |
|---|---|---|
| Como chega? | eventos diários (`NOVA`, `ATUALIZACAO`, `BAIXA`), append-only | |
| Tem chave da pendência? | `pendencia_id` | |
| Tem data do evento ou da foto? | `data_extracao` | |
| O que muda no tempo? | status, valores e atraso | |
| Medidas | saldo (posição, semiaditivo) e recuperado (fluxo) | |
| Dado pessoal | CPF, nome, contato, RG (sintéticos) | |
| O que torna o dado inutilizável? | as 11 regras de erro da barreira | |
| Quem consome? | diretoria e analista financeiro | |
| Tem regulação ou auditoria? | SUSEP e LGPD (simulado) | |
| Onde roda? | Free Edition | |

**Perfil pronto escolhido (A a E):**   **Trilha do DQX (A ou B):**
