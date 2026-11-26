# Prontidão para a Genie Ontology · pos_venda (21/11/2026)

Ferramenta: [databricks-solutions/genie-ontology-readiness](https://github.com/databricks-solutions/genie-ontology-readiness)
**v1.5.0**, instalada como app `genie-ontology-readiness`
(<https://genie-ontology-readiness-7474645927052439.aws.databricksapps.com>), com **histórico no Lakebase** desde
21/11/2026 (ver abaixo). Avaliação do catálogo `pos_venda`. Respostas completas:
`avaliacao_pos_venda.json` (só o app), `avaliacao_pos_venda_2.json` (com a sua identidade),
`avaliacao_pos_venda_3.json` (depois das tags de domínio e responsável) e `avaliacao_<rótulo>.json` gravados por
`avaliar.py` (cada um com o id da avaliação no histórico).

| Comando | O que faz |
|---|---|
| `python3 avaliar.py rodar <rótulo>` | avalia o `pos_venda` com a sua identidade, **grava no histórico** e salva `avaliacao_<rótulo>.json` |
| `python3 avaliar.py historico` | lista as avaliações gravadas (as suas) |
| `python3 avaliar.py comparar <id1> <id2>` | nota por pilar entre duas avaliações do histórico |
| `python3 implantar_app.py` | (re)implanta o app v1.5.0 com o Lakebase (idempotente) |

**Nota atual: 94,7 (Optimized, "Ontology-ready"), reavaliada em 26/11/2026** (histórico id 5; `avaliacao_pos_venda_5.json`).

## Instalação e acessos

| Item | Situação |
|---|---|
| App | RUNNING, v1.5.0 implantada de `/Workspace/Users/<você>/apps/genie-ontology-readiness` por `implantar_app.py`; recursos `sql-warehouse` (CAN_USE) e `lakebase-db` (CAN_CONNECT_AND_CREATE) |
| Histórico | Lakebase Autoscaling: projeto `dqx-studio-db` (o único permitido no Free Edition), branch `dqx`, database própria `ontology_readiness`, schema `genie_ontology_readiness` criado pelo app |
| Leitura no catálogo `pos_venda` | concedida ao service principal do app (USE CATALOG, USE SCHEMA, SELECT) |
| Tabelas de sistema (`system.access`, `system.query`) | **negada** ao app (no Free Edition o usuário não administra o catálogo `system`) |
| Autorização do usuário (escopo `sql`) | ligada: a avaliação roda com a identidade de quem consulta, que lê as tabelas de sistema |
| Espaços Genie Analista e Diretor | compartilhados com o app (CAN_READ) |
| `main` e `workspace` | **não** concedidos (o `main` tem as linhas reprovadas do DQX Studio, com dado pessoal) |

## Nota

| Pilar | Peso | Só o app | Com a sua identidade | Com domínio e responsável | Com legado descrito | O que falta |
|---|---|---|---|---|---|---|
| Unity Catalog | 15 | 100 | 100 | 100 | 100 | — |
| Metadados | 22 | 86,1 | 83,5 | 83,5 | **93,5** | 382 colunas e 2 tabelas de objetos internos dos pipelines (ver abaixo: não editar) |
| Relações e modelagem | 12 | 100 | 100 | 100 | 100 | — (14 PK, 15 FK) |
| Métricas | 20 | 76 | 76 | 76 | 76 | a nota cresce com a quantidade de metric views até 10; as 4 estão 100% descritas |
| Agentes Genie | 16 | 0 (sem acesso) | 100 | 100 | 100 | — (8 agentes no log, 4 ativos em 30 dias) |
| Domínios e responsáveis | 10 | 0 | 0 | **92** | 92 | 3 dos 10 objetos mais acessados sem certificação (ver abaixo: não certificar) |
| Adoção | 5 | 0 (sem acesso) | 95 | 95 | 95 | — |
| **Geral** | | **61,1** | **81,3 (Established)** | **90,5 (Optimized)** | **92,7 (Optimized)** | |
| Histórico (Lakebase) | | — | — | id 1 | id 2 | `python3 avaliar.py comparar 1 2` |

Avaliação id 3 (depois das tags de dado pessoal nos legados): **92,7**, igual à id 2. O app não pontua tag de dado
pessoal; só a contagem de tabelas com governed tag foi de 57 para 65.

Pilares sem dados contam como zero: por isso a nota só do app é tão menor.

**Depois da operação ligada (23 e 26/11).** A avaliação id 4 (23/11) deu 94,5 e a id 5 (26/11), 94,7. Entre as duas, só os
metadados subiram (94,5 → 95,1), com as tags de área de negócio, a certificação das tabelas `dq_*`, o catálogo de regras
e as Wikis. Os outros pilares ficaram iguais:

| Pilar | id 4 (23/11) | id 5 (26/11) |
|---|---|---|
| Unity Catalog | 100 | 100 |
| Metadados | 94,5 | 95,1 |
| Relações e modelagem | 100 | 100 |
| Métricas | 84 | 84 |
| Agentes Genie | 100 | 100 |
| Domínios e responsáveis | 92 | 92 |
| Adoção | 95 | 95 |
| **Geral** | **94,5** | **94,7** |

O pilar mais baixo continua sendo **Métricas (84)**, que cresce com a quantidade de metric views. Em 26/11, o app estava
parado e sem implantação ativa; ao ligar, ele voltou com a última implantação (v1.5.0) e respondeu. Comando:
`python3 avaliar.py comparar 4 5`.

## Como o pilar de domínios pontua (v1.5.0)

`40 + 40 × min(domínios distintos, 5) / 5`, mais 20 se houver tabela com tag de responsável. Domínios distintos = valores
distintos das tags de domínio. Ex.: `domain = pos_venda` em todas as tabelas + `subject_area` com os 3 subdomínios
(cobranca, carteira, qualidade) + `data_owner` → 4 valores → 40 + 32 + 20 = **92**.

## Histórico no Lakebase

Antes cada avaliação valia só para o momento em que rodava. Agora toda avaliação iniciada pela tela do app ou por
`avaliar.py` fica gravada (tabela `ontology_assessment_snapshots`), e o app mostra a tendência e compara duas avaliações.

| Decisão | Motivo |
|---|---|
| Reaproveitar o projeto `dqx-studio-db` com uma **database separada** | o Free Edition permite 1 projeto Lakebase; a database separada isola os dados do Studio e usa o mesmo compute (sem custo extra) |
| Manter a **v1.5.0** em vez do `main` | o `main` (sem release) já lê Lakebase Autoscaling pelo recurso, mas muda `probes.py` e `scoring.py`: a nota deixaria de ser comparável com 81,3 e 90,5 |
| Implantar da pasta do workspace, não do Git | a v1.5.0 só descobre pelo recurso o Lakebase *Provisioned*; com Autoscaling precisa de `LAKEBASE_HOST`, `LAKEBASE_ENDPOINT_NAME` e `LAKEBASE_DATABASE` no `app.yaml`, que o deploy pelo Git não deixa mudar |
| Gravar pela rota `POST /api/assess/runs` | o `GET /api/assess` (usado nas três primeiras avaliações) responde, mas **não** grava no histórico |

Conferência: `/api/config` com `history_ready: true`; log do app "Lakebase pool ready — assessment history + plans
enabled"; avaliação de base **id 1 = 90,5** gravada (`avaliacao_base_lakebase.json`).

Cuidados:
- o endpoint é o do DQX Studio: se a cota desligar o Lakebase (L19), o app continua avaliando, mas sem gravar; religue
  o endpoint e reinicie o app;
- trocar o recurso `lakebase-db` de database começa um histórico vazio; apagar a database apaga o histórico;
- um "Deploy from Git" pela tela volta ao `app.yaml` original e desliga o histórico: use `implantar_app.py`.

## Tags de domínio e responsável (aplicadas em 21/11/2026)

Governed tags com nome padrão, sem acento, ao lado da tag "Pós-venda" do Discover (que continua sendo a do domínio no
catálogo). Valores em `governanca/ontologia.py` (`DOMINIO_PADRAO`, `RESPONSAVEL`, `VALORES_DOMINIO_PADRAO`), aplicadas por
`aplicar_semantica.py`:

| Tag | Onde | Valor | Objetos |
|---|---|---|---|
| `domain` | schemas e tabelas das camadas principais | `pos_venda` | 7 schemas, 57 tabelas |
| `subject_area` | tabelas com subdomínio | `cobranca`, `carteira`, `qualidade` | 17, 16 e 15 tabelas |
| `data_owner` | tabelas das camadas principais | `financeiro_pos_venda` (papel) | 57 tabelas |

Para trocar o responsável: mude `RESPONSAVEL` em `ontologia.py` e rode `python3 aplicar_semantica.py --so-tags` (o script
inclui o valor novo na política da tag antes de gravar).

**Domínios distintos = 4** (pos_venda + 3 subdomínios) → 40 + 32 + 20 = 92, como previsto.

## Lacuna aceita: os mais acessados sem certificação

O app ordena as tabelas por usuários distintos em `system.access.table_lineage` (90 dias) e confere a tag
`system.certification_status`. No `pos_venda` as 10 primeiras estão **empatadas** (3 usuários: você, o app e o agendador),
e 3 delas não são certificadas de propósito:

| Objeto | Por que não certificar |
|---|---|
| `bronze.pagamentos_pendentes_eventos` | eventos brutos, com os defeitos injetados para a demonstração de qualidade |
| `dq.v_bronze_eventos_janela` | view de janela do DQX Studio sobre o bronze bruto |
| `dq.v_silver_eventos_aptos_janela` | view técnica de janela para avaliação de qualidade |

Certificado significa "fonte confiável para responder perguntas". Certificar esses objetos levaria a Genie a confiar em dado
que existe justamente para mostrar problemas. A frase de impacto do pilar ("você não atribui domínios e responsáveis") é
texto fixo do app e não reflete a nota 92.

## Schemas legados descritos (21/11/2026)

Decisão do usuário: **descrever** (não aposentar) os schemas `bronze_sql`, `silver_sql`, `gold_sql`, `bronze_ldp`,
`silver_ldp` e `gold_ldp`. O dicionário (`descricoes_colunas.py`) já cobria 670 das 682 colunas pelos nomes; entraram 6
nomes do legado (`_hash_linha`, `dq_qtd_problemas`, `data_geracao_cobranca_sk`, `data_extracao_sk`,
`qtd_parcelas_pendentes`) e o mapa `LEGADO`, que aplica também as exceções por tabela (ex.: `dim_data.dia`).
Comando: `python3 aplicar_descricoes.py legado` (materialized views coluna a coluna, 6 em paralelo, com nova tentativa
em conflito de atualização). Resultado: **682/682**, metadados 83,5 → 93,5, geral 90,5 → 92,7.

Dado pessoal nos legados **marcado** (decisão do usuário, mesma regra das camadas principais): 152 colunas com
`dado_pessoal` (identificação 48, endereço 42, perfil 38, contato 18, sensível 6), 158 tags `class.*`, 8 tabelas com
`contem_dado_pessoal` e 6 com `contem_dado_sensivel`. Os legados recebem **só** essas tags: continuam fora da ontologia
(sem domínio, camada ou certificação).

## Lacuna aceita: objetos internos dos pipelines

O app conta todas as tabelas do `information_schema`, inclusive as que os pipelines criam e administram:

| Objeto | Onde | Colunas sem descrição |
|---|---|---|
| `__materialization_mat_*` (dados das materialized views e streaming tables) | `bronze_ldp`, `silver_ldp`, `gold_ldp`, `silver` | 362 (97 + 102 + 152 + 11 colunas técnicas extras em `silver`) |
| `event_log_*` (log do pipeline; também as 2 tabelas sem descrição) | `bronze_ldp`, `silver` | 20 |

Esses objetos pertencem ao pipeline e são recriados por ele; descrição feita à mão neles não é suportada e não ajuda
quem consulta (a Genie e os painéis usam as views e tabelas publicadas, que estão 100% descritas).

## Opções que continuam abertas (decisão do usuário)

1. **Métricas:** criar metric views só se houver necessidade de negócio (ex.: corretor, régua de cobrança por canal de
   contato). Criar para subir a nota não melhora a ontologia.
