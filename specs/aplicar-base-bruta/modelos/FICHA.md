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
| pode conceder `USE CATALOG` e `CREATE SCHEMA` a um service principal? | sim / não | |

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
