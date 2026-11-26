# Trilha de aprendizagem · pos_venda

> Documento incremental. Cada fase nova entra no fim, com a mesma estrutura. Última atualização: **24/11/2026**.
> Mudanças pontuais vão para o [CHANGELOG](CHANGELOG.md); regras gerais que surgirem viram itens nas
> [lições aprendidas](03_LICOES_APRENDIDAS.md) e passos no [playbook](02_PLAYBOOK.md).

Esta trilha conta, na ordem em que aconteceu, como o domínio **pós-venda de seguro de vida** (parcelas pendentes de
pagamento) foi construído no Databricks Free Edition: dos dados sintéticos até os agentes Genie para o financeiro. Cada fase
tem **objetivo**, **o que fizemos**, **onde está**, **como conferir** e **o que aprendemos**. Para refazer a estrutura em outra
base, use o [playbook](02_PLAYBOOK.md); esta trilha é para entender o porquê.

```
 dados sintéticos ─► medalhão ─► carga diária ─► qualidade (pipeline + DQX Studio) ─► painel de qualidade
        │                                                                                   │
        └──────────────► governança (descrições, tags, domínio, Pages, Wikis, LGPD) ◄───────┘
                                     │
                         ontologia + metric views ─► Genie (analista e diretor) ─► painéis financeiros
                                     │
                         padrões semânticos, avaliação da Genie, metadados resilientes
```

| Fase | Tema | Pasta principal |
|---|---|---|
| 0 | Ambiente e limites do Free Edition | — |
| 1 | Dados sintéticos (one-table) | `01_gerar_one_table.py` |
| 2 | Medalhão e star schema em duas versões | `medalhao/` |
| 3 | Carga diária incremental com histórico | `carga_diaria/` |
| 4 | Incidentes e barreira de qualidade no pipeline | `carga_diaria/` |
| 5 | DQX Studio: instalação, regras, ciclos e replay | `dqx_studio/` |
| 6 | Painel de qualidade e roteiro de demonstração | `dqx_studio/painel/`, `dqx_studio/demo/` |
| 7 | Registro de Regras e tabelas monitoradas no Studio | `dqx_studio/regras/` |
| 8 | Governança: descrições, tags, domínio, Pages, Wikis, LGPD | `governanca/` |
| 9 | Ontologia e metric views | `governanca/` |
| 10 | Genie para o analista e o diretor financeiro | `governanca/genie.py` |
| 11 | Painéis de KPIs financeiros | `paineis_financeiros/` |
| 12 | Catálogo databricks-solutions e padrões semânticos | `referencias/`, `governanca/` |
| 13 | Avaliação independente da Genie | `governanca/genie/avaliacao_boas_praticas/` |
| 14 | Metadados resilientes e cobertura de 100% | `carga_diaria/views_preservadas.py` |
| 15 | Ontologia sem identificadores pessoais | `governanca/` |
| 16 | Avaliação contínua: Studio agendado com a carga | `dqx_studio/regras/registro_studio.py`, `carga_diaria/` |
| 17 | Dados pessoais marcados por tag, sem máscara | `governanca/ontologia.py`, `governanca/aplicar_semantica.py` |
| 18 | Prontidão para a Genie Ontology | `governanca/ontologia_readiness/` |
| 19 | Regras de negócio testadas (BDD) | `regras/` |
| 20 | Painéis por fato e opção Power BI | `paineis_financeiros/` |
| 21 | Projeto versionado no GitHub | `.gitignore`, `README.md` |
| 22 | Auditorias externas e RELY nas chaves | `paineis_financeiros/powerbi/auditoria/`, `governanca/genie/scanner/`, `governanca/aplicar_rely.py` |
| 23 | Custo e uso no padrão FOCUS (FinOps) | `finops/` |

---

## Fase 0 · Ambiente e limites do Free Edition

**Objetivo:** saber o que a plataforma permite antes de desenhar.

**O que fizemos:** usamos o workspace Free Edition com o CLI (perfil `dbx-workshop`), um único SQL warehouse
(`Serverless Starter Warehouse`, id `5f010b8396e591fb`) e só computação serverless. Tudo foi implantado por
Declarative Automation Bundles (`databricks bundle deploy`) e scripts Python locais que chamam a API e o warehouse.

**Como conferir:** `databricks current-user me --profile dbx-workshop` e `databricks warehouses list --profile dbx-workshop`.

**O que aprendemos:**
- **Cota diária de computação:** quando acaba, o warehouse recusa consultas ("free daily limit") até a meia-noite UTC.
  Os scripts detectam isso (`sql_util.CotaEsgotada`) e param com mensagem clara.
- Limites que moldaram o desenho: 1 warehouse 2X-Small, até 5 tarefas de job simultâneas, 1 pipeline ativo por tipo,
  até 3 apps, 1 projeto Lakebase, sem GPU e sem modelos Claude no Model Serving.
- Agendas começam **pausadas**; tudo roda sob demanda até a decisão de ligar.

## Fase 1 · Dados sintéticos (one-table)

**Objetivo:** ter uma base realista e sem dados reais para construir e demonstrar.

**O que fizemos:** `01_gerar_one_table.py` gera com `dbldatagen` 500.000 parcelas pendentes (91 colunas: cliente, apólice,
produto, coberturas, corretor, ponto de venda, cobrança) em `pos_venda.landing.pagamentos_pendentes_one_table`. Com
`injetar_defeitos = true`, entram defeitos de propósito: duplicatas, CPF inválido, e-mail e telefone nulos, UF em minúsculas.

**Como conferir:** `SELECT count(*) FROM pos_venda.landing.pagamentos_pendentes_one_table`.

**O que aprendemos:**
- Defeitos injetados de propósito são o que torna a demonstração de qualidade convincente.
- CPF e CNPJ sintéticos com dígito válido podem coincidir com documentos reais: uso só em teste.

## Fase 2 · Medalhão e star schema em duas versões

**Objetivo:** comparar notebooks SQL e Lakeflow (Spark Declarative Pipelines) para o mesmo modelo.

**O que fizemos:** `medalhao/gerar_sql.py` define a lógica uma vez e gera as duas versões: job de notebooks SQL
(`bronze_sql/silver_sql/gold_sql`) e pipeline Lakeflow com expectations (`bronze_ldp/silver_ldp/gold_ldp`). Gold em star
schema: fato `fact_pagamento_pendente`, 12 dimensões e a ponte `bridge_apolice_cobertura`, chaves `xxhash64` da chave de negócio.

**Onde está:** [medalhao/README.md](../medalhao/README.md).

**O que aprendemos:**
- Gerar o SQL a partir de um script evita divergência entre as duas implementações.
- Pipeline e notebook não podem escrever nas mesmas tabelas (o pipeline é dono do que cria): schemas separados.
- Esses schemas viraram **legado** quando a carga diária assumiu; a auditoria de metadados os separa dos principais.

## Fase 3 · Carga diária incremental com histórico

**Objetivo:** simular o sistema de origem mandando eventos todo dia e guardar a história.

**O que fizemos:** bundle `carga_diaria` com o job `pos_venda_carga_diaria` (5 tarefas): gera eventos `NOVA`,
`ATUALIZACAO` e `BAIXA` no bronze (append-only, idempotente), pipeline Lakeflow com Auto CDC para a silver
(`pendencia_evento`, `pendencia_hist` em SCD2, `pendencia_atual` em SCD1), dimensões e a fato
`fact_pagamento_pendente_snapshot` (1 linha por pendência em aberto por dia, valores recalculados as-of a data da foto).
PK e FK declaradas (informativas). Dados de 19/05/2026 a 24/12/2026.

**Onde está:** [carga_diaria/README.md](../carga_diaria/README.md); notebooks e SQL gerados por `gerar_carga.py`.

**O que aprendemos:**
- **Saldo de carteira é semiaditivo:** a fato snapshot tem uma linha por dia; somar dias diferentes infla o número.
  Essa regra atravessa todo o resto (Pages, metric views, Genie, painéis).
- Chaves `xxhash64` são estáveis entre execuções: a fato histórica continua válida quando as dimensões são reescritas.
- Rodar o mesmo dia duas vezes não duplica nada (bronze ignora dias carregados, Auto CDC absorve repetidos, fato regrava o intervalo).
- A simulação nunca baixa pendências por perda: a carteira só cresce. Isso é aceito e dito na demonstração.

## Fase 4 · Incidentes e barreira de qualidade no pipeline

**Objetivo:** mostrar problemas de qualidade aparecendo, sendo barrados e se recuperando.

**O que fizemos:** 5 ciclos semanais (20/11 a 24/12/2026) com incidentes programados: semana limpa, pico de avisos,
erros barrados, erros que vazam (forma de pagamento nova) e recuperação. A barreira tem 10 regras de erro no pipeline:
o que não passa vai para `silver.pendencia_evento_quarentena` com o motivo. Métricas diárias em `gold.dq_qualidade_diaria`,
`gold.dq_barrados_por_motivo_dia` e `gold.dq_fato_orfas_diarias` (notebook 25).

**Onde está:** tabela "A história" no [ROTEIRO](../dqx_studio/demo/ROTEIRO.md).

**O que aprendemos:**
- Separe **erro** (barra) de **aviso** (entra com ressalva). O que não está na barreira **vaza** e aparece depois como
  chave órfã na fato: o melhor exemplo para mostrar por que a qualidade precisa estar no começo.

## Fase 5 · DQX Studio: instalação, regras, ciclos e replay

**Objetivo:** ter uma ferramenta visual de qualidade com histórico, regras aprovadas e linhas reprovadas.

**O que fizemos:**
- Instalamos o DQX Studio (Databricks Labs) como App pelo bundle oficial, com um patch para usar o warehouse existente
  (o Free Edition só permite um). Estado do app no Lakebase.
- `definir_regras.py` gera as regras por tabela; `carregar_regras.py` fala com a API do Studio (com renovação de token em 401).
- Criamos as views de **janela** (`pos_venda.dq.v_*_janela`), que leem o intervalo guardado em `dq.janela_avaliacao`.
  O job aponta a janela para os últimos 7 dias; o replay (`rodar_ciclos.py --replay`) aponta para cada semana do passado.
- Rodamos o histórico das 5 semanas com **todas as linhas** (amostra 0).

**Onde está:** [dqx_studio/README.md](../dqx_studio/README.md), `dqx_studio/regras/`.

**O que aprendemos:**
- O dry run do Studio usa as **primeiras N linhas** (`limit`), não amostra aleatória: com amostra, os incidentes de alguns
  dias somem. Para histórico confiável, avalie janelas com todas as linhas.
- Uma regra mal mapeada gera falso positivo (pk única numa view de eventos): corrigimos a regra e marcamos as 2 execuções.
- O endpoint Lakebase desliga quando a cota acaba; o app volta com `spec.disabled=false` e reinício.

## Fase 6 · Painel de qualidade e roteiro de demonstração

**Objetivo:** contar a história da qualidade para quem não abre o Studio.

**O que fizemos:** 6 views `pos_venda.dq.v_painel_*` unem as métricas do pipeline e as tabelas do Studio; painel AI/BI
"pos_venda · Qualidade de dados" (3 páginas + filtros) gerado por `gerar_painel.py` e testado por `aplicar_e_testar.py`
(cada consulta como o AI/BI executa, mais 5 checagens de consistência). Roteiro de demonstração em atos.

**Onde está:** [painel/README.md](../dqx_studio/painel/README.md), [ROTEIRO.md](../dqx_studio/demo/ROTEIRO.md).

**O que aprendemos:**
- Gerar o JSON do painel por código e conferir a estrutura (versões dos widgets, grade de 12 colunas, campos × encodings)
  evita painéis quebrados. Opções de widget não documentadas foram removidas.
- Checagens de consistência no script de teste pegam regressões que ninguém veria no painel (ex.: a "semana 6" da Fase 14).

## Fase 7 · Registro de Regras e tabelas monitoradas no Studio

**Objetivo:** fazer as regras, as tabelas e as linhas reprovadas aparecerem no menu do Studio.

**O que fizemos:** as regras de tabela única (API antiga) não aparecem no menu. `registro_studio.py` migrou para o
Registro: 69 modelos, 12 tabelas monitoradas, 194 checagens aprovadas, execução com todas as linhas e recálculo das notas.

**O que aprendemos:**
- `skip_duplicates` funde modelos de severidades diferentes; a trava contra duplicata deixa checagens presas em rascunho se
  as regras antigas continuam na mesma tabela. Recrie sem deduplicação e remova as antigas (com backup).
- A nota só aparece depois de `POST /api/v1/dq-results/refresh-scores`.

## Fase 8 · Governança: descrições, tags, domínio, Pages, Wikis, LGPD

**Objetivo:** dar contexto de negócio aos dados para pessoas e para IA.

**O que fizemos:**
- `auditar_metadados.py` mede descrições e tags por schema (principais × legado) e PII sem classificação.
- `descricoes_colunas.py` + `aplicar_descricoes.py`: descrição por nome de coluna, com exceções por tabela.
- `aplicar_semantica.py`: governed tags, domínio **Pós-venda** com 3 subdomínios, tags por camada/tipo/entidade,
  certificação, classificação LGPD (`class.br_cpf`, `class.name`...), 18 Pages (conceitos de negócio) e 51 Wikis de tabela.

**O que aprendemos:**
- Pages atômicas com seção **Como validar** viram as perguntas de avaliação da Genie.
- Tags com acento funcionam, mas SQL exige o nome exato e a API pede `%2F` no `/` do subdomínio.
- Wikis e Pages não têm texto com dado pessoal.

## Fase 9 · Ontologia e metric views

**Objetivo:** uma camada de negócio estável, sem dados pessoais, com as métricas definidas uma vez.

**O que fizemos:** schema `pos_venda.ontologia` com 10 entidades (views), `entidades`, `relacoes` (triplas
sujeito–predicado–objeto), `glossario` e 4 metric views (`mv_carteira_em_aberto`, `mv_recuperacao`, `mv_safra_recuperacao`,
`mv_qualidade_dados`), tudo gerado por `gerar_ontologia_sql.py`.

**O que aprendemos:**
- A metric view é a fonte única: Genie e painéis leem as mesmas medidas, então o número bate entre eles.
- Medidas semiaditivas precisam de dimensões auxiliares (`Foto mais recente`, `Fim de mês`) ou de janelas (Fase 12).

## Fase 10 · Genie para o analista e o diretor financeiro

**Objetivo:** perguntas em linguagem natural com a regra certa.

**O que fizemos:** `genie.py` monta 2 espaços (Analista e Diretor) com metric views, instruções de texto (< 2.000
caracteres), exemplos de SQL e perguntas de avaliação; valida todo SQL no warehouse antes de publicar e compara a resposta da
Genie com o esperado pelo resultado inteiro.

**O que aprendemos:**
- Instruções curtas e específicas (desambiguação, período, semiaditivo) resolvem mais que instruções longas.
- Comparar resultados inteiros evita falso negativo; a Conversation API pede `--no-wait` e JSON com `strict=False`.

## Fase 11 · Painéis de KPIs financeiros

**Objetivo:** visão executiva (Diretoria) e operacional (Analista) sobre as metric views.

**O que fizemos:** `gerar_paineis.py` gera 2 painéis AI/BI no bundle `paineis_financeiros` (dataset_catalog `pos_venda`,
dataset_schema `ontologia`), com link para a Genie de cada público.

**O que aprendemos:** KPIs "vs. 30 dias antes" funcionam por dia; comparações mensais vieram depois com as medidas de janela.

## Fase 12 · Catálogo databricks-solutions e padrões semânticos

**Objetivo:** aproveitar aceleradores oficiais em vez de reinventar.

**O que fizemos:** catalogamos os 147 repositórios da organização databricks-solutions (finalidade, uso, benefício para o
projeto) em `referencias/databricks_solutions/` e numa página publicada. Aplicamos os padrões do
[uc-semantics-patterns](https://github.com/databricks-solutions/uc-semantics-patterns): saldo de fechamento (semiaditivo),
mês anterior e variação mensal (offset), acumulado no mês e no ano (cumulative) e ranking. Levamos as medidas aos painéis.

**O que aprendemos:**
- O "último dia" do semiaditivo é **por fatia**: em fatias que somem antes do fim do mês sobra saldo (produto × canal × forma
  sobrou R$ 240,33 em dezembro). Grão produto × canal bate no total.
- Ranking não pode ir na mesma consulta que medidas de janela; o `offset` só enxerga o mês anterior quando o filtro é na
  dimensão de mês; o acumulado ordenado por dia respeita o filtro de mês, ordenado por mês não.
- Recriar metric view apaga tags e Wiki: restaure depois (`aplicar_semantica.py`).

**Revisão de 22/11:** relemos o catálogo depois do Power BI e das funções de regra. Quatro repositórios já estão
aplicados (`uc-semantics-patterns`, `genie-best-practices-agent`, `genie-ontology-readiness`, `agentic-bdd-uc-functions`);
sete propostas ficaram priorizadas em `referencias/databricks_solutions/REVISAO_2026-11-22.md`, a começar pela auditoria
do Power BI (`powerbi-analyzer`), pela nota da Genie sem instalar app (`genie-agent-scanner`) e por `RELY` nas PKs da gold.
Em 23/11, o catálogo virou também um guia de opções para LLM (`OPCOES_PARA_LLM.md` e `opcoes.json`): os 147 repositórios
com recomendação, prioridade, camada do framework e regras de escolha.

## Fase 13 · Avaliação independente da Genie

**Objetivo:** uma segunda opinião sobre os espaços Genie.

**O que fizemos:** rodamos o [genie-best-practices-agent](https://github.com/databricks-solutions/genie-best-practices-agent)
em modo offline (extrator próprio, sem Spark) com `llama-4-maverick`, e a avaliação oficial da Genie (Genie Eval). Triagem dos
achados em [TRIAGEM.md](../governanca/genie/avaliacao_boas_praticas/TRIAGEM.md). Aplicamos: descrição dos 87 campos das metric
views e meses como `date`.

**O que aprendemos:**
- Gabarito desatualizado reprova resposta certa: ao mudar a semântica, atualize os gabaritos.
- Mudar tipo (`timestamp` → `date`) mudou o comportamento da Genie (passou a filtrar pela semana truncada): descrição do
  campo e exemplo de SQL corrigiram.
- Relatório de IA tem falso positivo ("CPF inválido" é contagem, não CPF): confira cada achado nos metadados.

## Fase 14 · Metadados resilientes e cobertura de 100%

**Objetivo:** a carga diária não pode desfazer a governança.

**O que fizemos:** testamos o que cada recriação apaga; criamos `carga_diaria/views_preservadas.py` (`garantir_view`), usado
pelo job, pelo replay e pelo painel de qualidade: só recria a view se a definição mudou e, nesse caso, devolve descrições,
tags, tags de coluna e Wiki. Descrevemos as 89 colunas das views do painel. Corrigimos a "semana 6" falsa do painel de
qualidade (execuções do Registro contadas como semana nova).

**Como conferir:** `python3 governanca/auditar_metadados.py` → 1.933 de 1.933 colunas principais descritas.

**O que aprendemos:**
- `CREATE OR REPLACE TABLE ... AS SELECT` mantém descrições e tags; `CREATE OR REPLACE VIEW` apaga tags, tags de coluna e
  Wiki (descrições de `SELECT *` são herdadas da origem e sobrevivem).
- Tags de coluna de view não podem ser gravadas por SQL; só pela API de entity tag assignments.

## Fase 15 · Ontologia sem identificadores pessoais

**Objetivo:** cumprir a promessa da camada de ontologia (sem identificadores pessoais).

**O que fizemos (21/11/2026):** retiramos `cliente_id` das views `ontologia.pendencia` e `ontologia.pagamento`. As views
foram recriadas com `garantir_view(..., ddl=...)`, que executa o DDL completo gerado (com a descrição de cada coluna) e devolve
tags e Wiki. Tiramos a exclusão da coluna no espaço Genie do analista e ajustamos a Page "Cliente" para ligar pendências pelo
`cliente_sk`.

Depois, por decisão do usuário, `cliente_id` saiu também da entidade `ontologia.cliente`, e a relação "Cliente possui
Apólice" passou a usar `cliente_sk`.

**Como conferir:** nenhuma coluna `cliente_id` no schema `ontologia`; as três views mantêm as 5 tags e a Wiki publicada;
`genie.py avaliar` → 27/27; `auditar_metadados.py` → 1.930 de 1.930 colunas descritas e 0 PII sem tag.

**O que aprendemos:**
- Views com lista de colunas e `COMMENT` precisam recriar com o DDL completo: por isso `garantir_view` ganhou o parâmetro `ddl`.
- Código técnico (`cliente_id`) também é dado pessoal pela LGPD quando leva à pessoa; o que mais pesa é ele circular fora
  do Databricks. Na camada de negócio, ligue entidades pela chave substituta (`cliente_sk`).

## Fase 16 · Avaliação contínua: Studio agendado com a carga

**Objetivo:** a qualidade ser avaliada todo dia depois da carga, sem ninguém rodar script.

**O que fizemos (21/11/2026):**
- `registro_studio.py agendar` agenda as 12 tabelas monitoradas para **06:30 (Brasília)**, 1 h 30 depois da carga das 05:00
  (que leva de 13 a 16 minutos), só regras de qualidade (`dq_only`) e com todas as linhas. Nasce **pausado**, como o job;
  `ligar`, `pausar` e `agenda` controlam e mostram o estado.
- Removemos o agendamento antigo `pos_venda_janela_diaria` (por schema, com as regras de tabela única), guardando a configuração.
- O job ganhou a tarefa `ligar_dqx_studio` (notebook `40_ligar_dqx_studio`): o agendador roda dentro do app, e no Free
  Edition o app para sozinho após 24 h.

**Como conferir:** `python3 dqx_studio/regras/registro_studio.py agenda` → 12 tabelas, `30 6 * * *`, pausadas.
Testes feitos: um disparo real agendado na `dim_data` (`run_type = 'scheduled'`, SUCCESS, 5.844 linhas) e a tarefa do job
ligando o app parado (`STOPPED -> ACTIVE`).

**O que aprendemos:**
- Teste o agendamento com um disparo real, não só a configuração.
- Execuções agendadas não entram no painel de qualidade (ele conta só as manuais, `dryrun`), então o histórico do replay
  continua com 5 semanas.

## Fase 17 · Dados pessoais marcados por tag, sem máscara

**Objetivo:** deixar claro, no catálogo, onde estão os dados pessoais, sem atrapalhar a validação de qualidade.

**Decisão (21/11/2026):** não mascarar. As regras de qualidade (CPF válido, e-mail, telefone, CEP) e a validação precisam dos
valores reais. Em vez de máscara, cada coluna e cada tabela dizem que têm dado pessoal.

**O que fizemos:** governed tags em português derivadas da classificação técnica `class.*`:
`dado_pessoal` na coluna, com a categoria (identificacao, contato, endereco, perfil, sensivel); `contem_dado_pessoal = sim`
e `contem_dado_sensivel = sim` na tabela. Tudo no `aplicar_semantica.py`, idempotente.

**Como conferir:** 380 colunas marcadas em 18 tabelas (15 com dado sensível, o campo fumante); nenhuma coluna classificada
sem `dado_pessoal`. Em 21/11 os schemas legados (`*_sql`, `*_ldp`) também foram marcados: mais 152 colunas em 8 tabelas;
a auditoria mostra 0 dado pessoal sem tag nos 13 schemas.

**O que aprendemos:**
- Governed tag sem lista de valores recusa qualquer valor: defina os valores permitidos na política da tag.
- Dado pessoal não depende da camada: schemas antigos que continuam no catálogo também precisam da marcação (L55).
- Marcar é sempre possível; mascarar depende do uso. Quando as camadas com dado pessoal forem abertas a mais gente, a
  proteção vem por grants ou por máscara com exceção para quem valida.

## Fase 18 · Prontidão para a Genie Ontology

**Objetivo:** uma nota independente para a camada semântica que montamos.

**O que fizemos (21/11/2026):** instalamos o [genie-ontology-readiness](https://github.com/databricks-solutions/genie-ontology-readiness)
v1.5.0 como app (direto do Git, sem Lakebase), demos leitura no catálogo `pos_venda`, ligamos a autorização do usuário e
compartilhamos os espaços Genie com o app.

**Resultado:** 81,3 de 100 (Established): Unity Catalog, relações e Genie em 100; adoção 95; metadados 83,5; métricas 76;
domínios 0. Depois das tags de domínio e responsável (`domain = pos_venda`, `subject_area` com os 3 subdomínios,
`data_owner = financeiro_pos_venda`): **90,5 (Optimized)**, com domínios em 92. Com as 682 colunas dos schemas legados
descritas: **92,7** (metadados 93,5). Desde então cada avaliação fica gravada no **Lakebase** (database própria no projeto
do DQX Studio) e pode ser comparada no app ou com `avaliar.py comparar`. Detalhe e opções em
[RESULTADO.md](../governanca/ontologia_readiness/RESULTADO.md).

**O que aprendemos:**
- Só com o service principal do app a nota foi 61,1: Genie e adoção ficaram sem dados (tabelas de sistema) e contaram zero.
- A v1.5.0 reconhece domínio só por tags com nome padrão (`domain`, `subject_area`...), não pela tag do Discover ("Pós-venda").
  Mantivemos as duas: a do Discover organiza o catálogo; as padrão servem às ferramentas.
- Valor recém-incluído numa governed tag demora alguns segundos para valer: o script espera e repete (L47).
- Nem toda lacuna se corrige: os objetos mais acessados incluem o bronze bruto e views técnicas de qualidade, que não devem
  ser certificados (L48); e as tabelas internas dos pipelines entram na contagem de metadados, mas não se editam (L52).
- Histórico só é útil com a régua fixa: mantivemos a v1.5.0 do app e passamos o Lakebase por configuração (L49, L51).
- Uma auditoria que confunde "não consegui ler" com "não tem" gera alarme falso: as tags agora são lidas em lote pelo
  `information_schema` (28 s em vez de 15 min) e falhas aparecem como "não lidas" (L53).

## Fase 19 · Regras de negócio testadas (BDD)

**Objetivo:** tirar as regras de cálculo do texto SQL espalhado no pipeline e dar a elas um contrato que o negócio lê.

**O que fizemos (21/11/2026):** com o padrão do [agentic-bdd-uc-functions](https://github.com/databricks-solutions/agentic-bdd-uc-functions),
criamos o schema `pos_venda.regras` com 5 funções SQL (`faixa_atraso`, `valor_multa`, `valor_juros`,
`valor_total_pendente`, `cpf_valido`), 36 cenários em português e uma paridade linha a linha contra os dados gravados.
O pipeline **não** mudou (etapa 1). Detalhe em [regras/README.md](../regras/README.md).

**Resultado:** 36/36 cenários; paridade 100% (29,9 milhões de linhas da gold e 1,6 milhão da silver, 0 divergência); a
função reprova os 517 totais que a barreira barrou.

**O que aprendemos:**
- Escrever o cenário obriga a decidir o que o SQL deixava implícito: a parcela que vence hoje já paga multa; dias
  negativos davam faixa e juros; CPF com dígitos repetidos passava. Cada decisão ficou explícita, com impacto medido (0
  linha hoje) (L57).
- Paridade antes de trocar: a função só substitui o cálculo do pipeline depois de provar que devolve o mesmo valor em
  todas as linhas (L56).
- A API síncrona tem limite de espera; com espera curta, consulta do estado e nova tentativa em erro de rede, os
  cenários ficam estáveis (L58).

**Etapa 2 (22/11/2026):** o job diário ganhou o portão `05_portao_regras` (os mesmos 36 cenários, rodando no
Databricks antes da carga); a silver valida o CPF com `regras.cpf_valido`; a barreira ganhou `valores_fora_da_regra`;
a gold calcula faixa, multa, juros e total pelas funções; a Genie recebeu as funções como ativos confiáveis. Validação
sem gerar dia novo: job com só portão, silver e gold (18 a 24/12) → 0 diferença com a cópia anterior; Genie 29/29;
painéis 13/13.

- Trocar a regra antiga da barreira pela função no mesmo lugar esconderia a causa de 319 eventos (I14): a regra nova
  entrou depois da checagem de atraso (L59).
- Mudança de pipeline se valida sem mexer nos números da demonstração: job só com as tarefas afetadas e comparação
  linha a linha antes/depois (L60).
- Na Genie, as funções entram em `instructions.sql_functions`; ela passou a chamar a função nas simulações (L61).
- O DQX Studio espelha a regra (`valores_seguem_regras_de_calculo`, modelo 70 do Registro) nas janelas de bronze, silver
  e fato; quem executa o Studio ganhou `EXECUTE` nas funções. Na janela do bronze ela acusa 60 eventos do I03 (parcela
  zerada ou negativa com multa e juros da parcela original) que a regra da soma não pegava, porque a soma fechava (L62).


**Dia novo pelo caminho todo (22/11/2026):** o job completo carregou 25/12 (16 min, 7 tarefas SUCCESS): portão 36/36,
8.559 eventos, 0 na quarentena, 0 divergência na silver e na gold (253.914 linhas do dia) contra as funções; a silver
marcou 139 CPFs inválidos, o mesmo número da função no bronze. No DQX Studio, a janela 19–25/12 deu 44 violações da regra
espelhada no bronze (I03 de 19 e 20/12, as mesmas da regra de valor mínimo) e 0 na silver e na fato.

- Um dia sem incidente prova que a regra não reprova evento bom, não que ela pega erro (L64).
- O dia novo envelheceu textos com data fixa (Genie, roteiro, teste do painel de qualidade): agora dizem "foto mais
  recente" e a checagem é relativa à data (L65).

## Fase 20 · Painéis por fato e opção Power BI

**Objetivo:** mostrar cada fato ao time de negócio e à diretoria, no Databricks e no Power BI, para avaliar as duas
ferramentas com os mesmos números.

**O que fizemos (22/11/2026):** os dois painéis AI/BI passaram a ter **uma página por fato** (carteira em aberto,
recuperação, safras, qualidade dos dados); o da diretoria abre numa visão executiva. Para o Power BI, o schema
`pos_venda.bi` ganhou 8 visões agregadas a partir das mesmas metric views, e `gerar_powerbi.py` gera um projeto PBIP
(modelo TMDL com 47 medidas e 12 relações; relatórios PBIR do time de negócio e da diretoria com as mesmas páginas).
Detalhe em [paineis_financeiros/README.md](../paineis_financeiros/README.md) e [powerbi/README.md](../paineis_financeiros/powerbi/README.md).

**Resultado:** 14/14 datasets dos painéis respondem e os dois foram publicados no mesmo link; projeto Power BI com 102
arquivos válidos nos esquemas oficiais; paridade 21/21 entre o painel do Databricks e a lógica das medidas DAX; schema
`bi` 100% descrito e com tags de domínio e dono. **Não verificado:** abrir no Power BI Desktop (precisa de Windows).

**O que aprendemos:**
- Uma página por fato em cada público atende sem multiplicar painéis nem trocar links (L66).
- A segunda ferramenta lê extratos das metric views; o DAX só cuida do que é do motor, como o saldo semiaditivo (L67).
- Sem o Power BI na máquina, a prova possível é esquema oficial + teste negativo + paridade de números; o resto fica
  declarado (L68).

## Fase 21 · Projeto versionado no GitHub

**Objetivo:** tirar o projeto da pasta que o app criou para a sessão e guardá-lo num repositório Git, com histórico.

**O que fizemos (22/11/2026):** antes do primeiro envio, varremos os 325 arquivos por tokens (`dapi`, `gho_`, chaves
privadas), e-mails e caminhos locais. Não havia token nem senha. Apareceram o e-mail do autor (metadados de backup das
regras e um caminho de workspace), amostras de clientes sintéticos nos resultados do DQX e um caminho local num log; o
usuário decidiu publicar tudo, porque os clientes são sintéticos (dbldatagen). O `.gitignore` deixa de fora só o que se
recria: o ambiente Python de `regras/` (29 MB), os caches e os esquemas baixados do Power BI. A raiz ganhou um `README.md`
que aponta para a documentação.

**Onde está:** <https://github.com/gustocezar/databricks_estudo> (público).

**Como conferir:** `git status` limpo depois do commit; `gh repo view gustocezar/databricks_estudo` com o branch `main`.

**O que aprendemos:**
- Repositório público é publicação: varra segredos e dados pessoais antes do primeiro envio e deixe a decisão do que
  publicar explícita (L70).
- Com o projeto no Git, o pré-requisito do CI/CD (`databricks-dab-examples`) deixou de faltar.

## Fase 22 · Auditorias externas e RELY nas chaves

**Objetivo:** aplicar as três propostas pequenas da revisão do catálogo databricks-solutions (fase 12, revisão de 22/11).

**O que fizemos (22/11/2026):**
- **Power BI:** auditamos o modelo e o lado Databricks com o `powerbi-analyzer` (`pba`). O `pba` só lê PBIP em
  `model.bim`, então o gerador ganhou a saída `bim`. O perfil OAuth precisou de um invólucro.
- **Genie:** pontuamos os dois espaços com o `genie-agent-scanner`, a régua de 12 itens do Genie Workbench, sem instalar
  o app.
- **Gold:** declaramos `RELY` nas 14 chaves primárias, depois de provar unicidade e ausência de nulos. As 15 estrangeiras
  foram recriadas sem `RELY`, e a carga diária passou a criar as chaves já com `RELY`.

**Onde está:** [auditoria Power BI](../paineis_financeiros/powerbi/auditoria/README.md),
[triagem da Genie](../governanca/genie/scanner/TRIAGEM.md), `governanca/aplicar_rely.py` e `governanca/rely/`.

**Resultado:**

| Proposta | Resultado |
|---|---|
| `pba` | modelo 80/100; lado Databricks 75/100, com achados só do warehouse do Free Edition |
| Scanner da Genie | 8/12 nos dois espaços, com teto de 10/12 sem o Workbench |
| `RELY` | consulta "saldo por dia" de 9 para 0 junções; "saldo por produto" de 9 para 1; fonte do Power BI de 9 para 6; os três resultados idênticos e o tempo igual (~1,5 s) |

**Como conferir:** `python3 governanca/aplicar_rely.py conferir` (14 PK com `RELY`, 15 FK sem) e os JSON de medição em
`governanca/rely/`.

**O que aprendemos:**
- Uma auditoria sem o dado de entrada aprova em branco. "Sem histórico" quer dizer "não avaliado" (L71).
- `RELY` exige remover e declarar a chave de novo, e o `CASCADE` leva as estrangeiras junto. O ganho aparece no plano antes
  de aparecer no relógio (L72).
- A régua da Genie não lê as descrições do Unity Catalog. Por isso o item 3 é falso positivo aqui (L73).
- O deploy do bundle segue o `.gitignore` (L74).

## Fase 23 · Custo e uso no padrão FOCUS (FinOps)

**Objetivo:** ver o custo e o uso do workspace por funcionalidade do Databricks, por projeto e por time (plataforma e
squad), no padrão FinOps FOCUS, com boas práticas medidas.

**O que fizemos (23/11/2026):**
- **Framework anterior intocado.** O framework FinOps que já existia (`finops.observability`) ficou como estava, por
  decisão do dono. 19 das suas 28 visões falhavam porque a base congelou um esquema antigo do billing (L76).
- **Schema novo `pos_venda.finops`.** Tem 19 visões e uma metric view, todas geradas por `finops/gerar_finops.py`.
- **Base FOCUS 1.4.** Adaptada da consulta oficial do `cloud-infra-costs`.
- **Atribuição em camadas.** Tag, depois regra por nome, depois rateio do warehouse por consulta (padrão do
  `dbx-adoption-monitor`).
- **Visões por público.** Para a plataforma e para o squad, mais as de uso (Genie separando pessoas de automação).
- **Boas práticas.** 15 práticas do Well-Architected da Databricks, do `powerbi-analyzer` e do `dbx-adoption-monitor`.

**Onde está:** [finops/README.md](../finops/README.md).

**Resultado:**
- **Conferência.** Os totais batem com o billing: 27.613 linhas e US$ 1.217,11 a preço de lista desde 22/06.
- **Quem gasta.**

  | Quem | Parte do custo |
  |---|---|
  | Plataforma (framework de Observabilidade) | 77,1% |
  | Não atribuído | 10,3% |
  | Squad pós-venda | 5,3% |
  | Outros squads | 6,0% |

- **Boas práticas.** 11 de 15 atendem.
- **Genie.** 100% das perguntas de novembro foram de automação.

**Como conferir:** `python3 finops/gerar_finops.py conferir`. Ela verifica que cada visão responde e que os totais batem
com o faturamento.

**O que aprendemos:**
- Numa visão sobre tabela de sistema, escolha os campos do struct; o struct inteiro quebra quando a tabela muda (L76).
- Atribua em camadas e meça o que sobrou sem dono; job oculto de alerta SQL não tem nome (L77, L79).
- Adoção se mede pelo canal UI; o resto é teste (L78).

## Fase 24 · Conformidade dos dados e observabilidade do workspace

**Objetivo:** avaliar se as ações de observabilidade que já rodavam no workspace entram no framework, e monitorar se
os dados seguem as regras do projeto: descrições, tags, dado pessoal e boas práticas.

**O que fizemos (23/11/2026):**
- **Inventário da observabilidade existente.** O bundle `observabilidade-framework` tem 6 jobs, 5 alertas SQL e grava
  em `main.observabilidade_dev`. Ao lado dele está o framework FinOps anterior, `finops.observability`.
- **Veredito por ação.** Cada ação recebeu o que faz, o que encontramos, o custo em 30 dias e um veredito:
  internalizar, manter, consertar, aposentar ou só leitura. Nada do bundle foi alterado.
- **Schema novo `pos_venda.conformidade`.** Gerado por `conformidade/gerar_conformidade.py`, tem 28 regras em 7
  dimensões, com meta, severidade, origem e como corrigir; visões para o squad e para a plataforma; a metric view
  `mv_conformidade`; a sonda diária das views; e o histórico.

**Onde está:** [conformidade/README.md](../conformidade/README.md) e
[AVALIACAO_OBSERVABILIDADE.md](../conformidade/AVALIACAO_OBSERVABILIDADE.md).

**Resultado:**
- **Avaliação.** Das 8 ações, 3 foram internalizadas, 2 mantidas, 1 vai para conserto (os alertas), 1 para aposentar
  (o rightsizing, que falha em toda execução) e 1 fica só leitura.
- **Alertas.** Os 5 alertas SQL rodam como jobs ocultos e eram as consultas "sem dono" da fase 23. Custaram
  US$ 816,20 desde julho; só o alerta horário, US$ 29,73 em 7 dias.
- **Conformidade.** São 8.992 verificações: 13 regras atendem, 12 pedem atenção e 3 são críticas.
  - LGPD, colunas descritas e valores de tag governada: 100%.
  - Pendências reais: 17 ativos principais sem `subject_area`, 22 views quebradas (19 em `finops.observability`),
    10 de 11 jobs sem timeout e 5 jobs sem as tags `project` e `team`.

**Como conferir:** `python3 conformidade/gerar_conformidade.py conferir`. São 9 checagens, entre elas: o inventário
igual ao `information_schema`, pendências iguais aos não conformes e à metric view, e nenhuma regra "sem dados".

**O que aprendemos:**
- Alerta SQL novo roda como job oculto. Ache pelo `query_source.alert_id` e limite a agenda (L79).
- Separe as tabelas internas do Lakeflow antes de contar: eram 382 falsos "sem descrição" (L80).
- Checagem sem objeto para verificar não é conformidade: mostre "sem dados" (L81).

## Fase 25 · Catálogo de exemplos de qualidade pelo fluxo normal

**Objetivo:** dar exemplo a todos os indicadores do DQX Studio, das fatos e das regras, com o mínimo de dado e pelo
fluxo que já existe: gerador de eventos, barreira, silver, dimensões e fato.

**O que fizemos (23/11/2026):**
- **Medição.** Das 388 regras nas últimas execuções do Studio, 348 estavam sem exemplo. A gold estava toda em zero,
  porque a barreira e o recálculo da fato impedem o erro de chegar lá.
- **Incidentes novos.** O gerador (`carga_diaria/gerar_carga.py`) ganhou 19 incidentes (I16 a I34) e duas semanas:
  - a 6, de erros e avisos;
  - a 7, de vazamentos: cadastro ruim, código novo de produto, ponto de venda e corretor, chave digitada errado e
    corrigida depois.
- **Carga mínima.** 15 dias (26/12/2026 a 09/01/2027): 110.368 eventos e 3,9 milhões de linhas novas na fato. O dia
  09/01 trouxe os incidentes I35 a I38 para as 5 regras que ainda faltavam.
- **Studio.** Replay das semanas 6 a 8 com todas as linhas, mais as 8 tabelas inteiras.
- **Guarda corrigida.** A guarda de idempotência do gerador não trava mais com data nula (L82).
- **Painel de qualidade.** Ganhou as semanas 6 e 7, e as checagens deixaram de usar números fixos.

**Onde está:** [dqx_studio/demo/ROTEIRO.md](../dqx_studio/demo/ROTEIRO.md) (semanas 6 e 7 e a cobertura das regras).

**Resultado:**
- **Regras com exemplo.** 138 das 224 regras das 13 tabelas avaliadas têm exemplo; antes eram cerca de 32.
- **Regras em zero.** As 86 restantes são todas garantias da arquitetura (L84).
- **Quarentena.** Os 11 motivos aparecem (3.596 eventos barrados nas semanas novas).
- **Fato.** Todas as faixas e todos os status em aberto têm pendências na foto de 08/01/2027; as chaves órfãs
  aparecem para cliente, apólice, produto, corretor, ponto de venda, forma de pagamento, motivo e periodicidade.
- **Painéis e apps.** Os painéis financeiros mostram a foto de 08/01/2027 (saldo em aberto R$ 33.079.336,07). O app
  de prontidão gravou a avaliação 4, com 94,5.

**Como conferir:** `python3 dqx_studio/painel/aplicar_e_testar.py` passa nos 6 conjuntos de dados e nas 5 checagens.
Ele confere 5 camadas por semana, a quarentena igual à do pipeline e um dia de métrica por dia carregado.

**O que aprendemos:**
- Em `NOT IN` com subconsulta, filtre os nulos (L82).
- Defeito de entidade compartilhada vai num código novo (L83).
- Zero numa garantia da arquitetura é prova, não falta de dado (L84).
- App recém-ligado responde 502 até terminar de subir (L85).

## Fase 26 · Reconferência com os dados novos e guia para outra base

**Objetivo:** reconferir a Genie e o Power BI depois da carga de 26/12 a 09/01. Também preparar o framework para ser
aplicado, com um agente de código como o Copilot, a uma base bruta de pendências já no Databricks, com a qualidade em
duas trilhas.

**O que fizemos (24/11/2026):**
- **Genie.** A avaliação completa (`genie.py avaliar`) rodou de novo, com o gabarito recalculado na hora: 28 de 29.
- **Power BI.** A paridade (`gerar_powerbi.py referencia`) rodou na foto de 09/01/2027: 20 de 21.
- **Causa das duas diferenças.** As duas vêm dos vazamentos da semana 7:
  - o painel somava o início do mês de cada grupo produto × canal, e 17 grupos nasceram depois de 01/01 (L86);
  - a Genie filtrou produto não nulo e deixou de fora R$ 779,34 de produto órfão (L87).
- **DQX como código.** O modelo da trilha A ficou em `dqx_codigo/`: as 11 regras de erro da barreira em YAML e 3 avisos,
  um notebook que separa válidos e quarentena e grava as métricas por regra, e um bundle sob demanda (P38).
- **Guia para outra base.** O guia `docs/06_GUIA_BASE_BRUTA.md` tem as etapas 0 a 7, a ficha da base, o mapeamento e a
  escolha da trilha pela permissão. O Copilot recebeu instruções (`.github/copilot-instructions.md`) e um prompt
  (`.github/prompts/aplicar-base-bruta.prompt.md`) (P39).
- **Playbook.** O M5 passou a ter as duas trilhas, e o Passo 0 ganhou a pergunta sobre conceder privilégio a um app.

**Onde está:** [06_GUIA_BASE_BRUTA.md](06_GUIA_BASE_BRUTA.md), [dqx_codigo/](../dqx_codigo/README.md),
`governanca/genie/avaliacao.json` e `paineis_financeiros/powerbi/VALORES_DE_REFERENCIA.md`.

**Resultado:**
- **Genie.** 28/29 na reconferência. Com o membro "não identificado" na ontologia (L87), voltou a 29/29.
- **Power BI.** 20/21 na reconferência. Com o painel lendo início e fechamento nas datas da carteira inteira (L86),
  voltou a 21/21; o crescimento de janeiro é R$ 1.405.736,27 nos dois.
- **DQX como código.** O job rodou na janela de 26/12 a 01/01 e deu 3.229 linhas em quarentena, o mesmo número da
  barreira. As tabelas saem descritas e com a tag de dado pessoal. A primeira execução falhou no `is_in_list` (L88).
- **Conformidade.** O schema `dqx_codigo` entrou como "apoio": 9.494 verificações, sem pendência nova.
- **Guia.** Os links do guia resolvem.

**Como conferir:**
- `python3 governanca/genie.py avaliar` (gasta cota);
- `regras/.venv/bin/python paineis_financeiros/powerbi/gerar_powerbi.py referencia`;
- `databricks bundle validate` em `dqx_codigo/`.

**O que aprendemos:**
- Medida semiaditiva de início ou fechamento se calcula no total, não somando grupos (L86).
- Chave órfã precisa de membro explícito, senão um filtro de nulo esconde dinheiro (L87).
- Reconfira o consumo depois de toda carga que traga grupos ou chaves novas.
- No DQX, domínio de texto vai em `sql_expression` com `IN` (L88).

## Fase 27 · Sustentação: tempo de execução dos jobs diários

**Objetivo:** responder, para quem sustenta a carga em produção, quanto tempo cada execução, tarefa e update do
pipeline levou, o que é normal, o que passou do normal e por quê, e se a carga termina antes da hora meta.

**O que fizemos (24/11/2026):**
- **Ponto de partida.** Só havia a duração média por job e dia, as falhas e o custo, em
  `pos_venda.finops.uso_jobs_diario`, e as regras USO01 (frescor) e PLT03 (timeout) na conformidade.
- **Sondagem das tabelas de sistema.** Usamos `job_run_timeline`, `job_task_run_timeline` e
  `pipeline_update_timeline`, que trazem setup, execução, parâmetros e a tarefa que disparou o update, além do bronze
  e da fato. Três achados viraram lições:
  - a duração não acompanha o volume (L89);
  - a execução que passa da hora vem em fatias (L90);
  - com a agenda pausada, o SLA não se mede em execução manual (L91).
- **Schema novo `pos_venda.sustentacao`.** Gerado por `sustentacao/gerar_sustentacao.py`, tem 14 visões:
  - execuções por job, tarefa e pipeline;
  - volume por dia e por execução;
  - linha de base, desvios com a causa provável e SLA dia a dia;
  - a última execução de cada job;
  - a matriz de resiliência por tarefa (P28);
  - o que o alerta avisa.

  A atribuição dos jobs vem da FinOps, sem lista nova.
- **Painel e alerta.** O bundle `sustentacao/` traz o painel "pos_venda · Sustentação", com a página "Sustentação", e
  o alerta SQL diário das 06:20, pausado (P02, PLT06).
- **Conformidade.** O schema `sustentacao` entrou em `CAMADAS` como "apoio".

**Onde está:** [sustentacao/README.md](../sustentacao/README.md).

**Resultado:**
- **Base.** 13 execuções da carga (12 com sucesso). A mediana é de 6,81 min na `silver_lakeflow` e de 3,65 min na
  `gold_dimensoes`.
- **Volume.** Um backfill de 184 dias levou 14,5 min; 1 dia, cerca de 14 min. O tempo é setup da computação
  serverless e subida do pipeline, não volume.
- **SLA.** Com a agenda pausada, todos os dias aparecem como "agenda pausada". A folga projetada mostra se a meta das
  06:15 cabe.
- **Conferência.**
  - `conferir`: 13 de 13 checagens. O volume por execução soma o bronze e a fato.
  - Carga: mediana de 14,53 min, p95 de 16,05 min e folga projetada de 59,0 min (provisórios).
  - Implantação: painel publicado e alerta pausado.
  - Conformidade: nenhuma pendência nova.
- **Alerta.** Na primeira conferência, avisaria 3 vezes por ruído. Com o piso de 60 s e sem desvio explicado por
  volume, avisaria 2 casos reais em 30 dias (L92).

**Como conferir:** `python3 sustentacao/gerar_sustentacao.py conferir`. As checagens confirmam que:
- as execuções e os updates batem com as tabelas de sistema;
- o volume por execução soma o bronze e a fato;
- as medianas são iguais ao cálculo direto;
- toda tarefa está na matriz;
- toda coluna tem descrição.

Para o painel e o alerta, `databricks bundle validate` em `sustentacao/`.

**O que aprendemos:**
- Separe setup de execução, e meça o volume, antes de chamar algo de lentidão (L89).
- Junte as fatias por `run_id` e tire as tarefas `SKIPPED` da linha de base (L90).
- O SLA vale para a execução da agenda. Antes de ligar a agenda, olhe a folga projetada (L91).
- Com a base curta, o alerta precisa de um piso, ou dispara por segundos acima do p95 (L92).

## Fase 28 · Operação ligada: agendas, timeouts, CI e ensaio do spec

**Objetivo:** pôr a operação no ar e fechar as pendências do time. O pedido do dono foi ligar as agendas, pôr timeout
nos jobs, dar área de negócio aos ativos sem ela, criar o CI dos bundles e ensaiar o spec antes de usá-lo com o
Copilot.

**O que fizemos (24/11/2026):**
- **Timeouts.** A carga diária ganhou timeout de 33 min, o valor sugerido pela sustentação (2 × p95). O setup e o
  medalhão SQL ficaram com 30 min, e o medalhão Lakeflow com 60 min, porque têm pouco histórico (P40, PLT03).
- **Área de negócio.** Os 17 ativos sem `subject_area` ganharam a tag: as visões do Power BI (`bi`), as visões do
  painel de qualidade (`dq.v_painel_*`) e os metadados da ontologia. A regra fica em `SUB_SEM_WIKI` de
  `governanca/ontologia.py` (TAG01).
- **Agendas ligadas.** A carga roda às 05:00, o DQX Studio avalia às 06:30 (12 tabelas) e o alerta de sustentação
  dispara às 06:20. O medalhão da primeira versão continua pausado. Para ligar o Studio, foi preciso reabilitar o
  endpoint do Lakebase e reiniciar o app (L19).
- **CI.** O `.github/workflows/ci.yml` roda a varredura, a compilação, os YAML e os links em todo push. Com os segredos
  do Databricks, também valida os bundles e roda os cenários BDD; o deploy é manual.
- **Ensaio do spec.** As etapas 0 a 2 rodaram só com leitura sobre a bronze, tratada como base nova
  (`specs/ensaio_pos_venda_bronze/`). O ensaio ajustou o spec: a consulta do dono, as consultas do perfil na ficha, as
  variantes de grafia no de-para e um aviso de chave repetida (L93).

**Onde está:** `carga_diaria/resources/*.job.yml`, `medalhao/resources/*.job.yml`, `governanca/ontologia.py` e
`aplicar_semantica.py`, `.github/workflows/ci.yml`, `specs/ensaio_pos_venda_bronze/` e os modelos do spec.

**O que aprendemos:**
- `SHOW GRANTS` não mostra o dono; consulte `catalog_owner` antes de decidir a trilha do DQX (L93).
- O Lakebase do Studio volta desabilitado depois de dias parado; reabilite o endpoint antes de ligar a agenda (L19).

**Os dois primeiros dias (26/11/2026):**
- **A operação rodou sozinha.**
  - A carga terminou às 05:15 e às 05:17, dentro do SLA das 06:15 e longe do timeout de 33 min.
  - O Studio rodou 24 avaliações, todas SUCCESS.
  - O alerta de sustentação ficou em OK.
- **Rodada de conformidade:**
  - os 4 jobs do pós-venda ganharam as tags de custo `project` e `team` (PLT01);
  - as 3 tabelas `dq_*` da gold foram certificadas depois de bater com bronze, silver, quarentena e fato (EST02);
  - o `registrar` virou o job `pos_venda_conformidade_sonda`, às 06:45, com `spark.sql` num notebook (P37).
- **Uma queda de rede ensinou L94.** O `registrar` local gravou 11 views boas como quebradas. Agora ele aborta quando a
  chamada falha, e a foto falsa saiu do histórico.
- **Frescor da ontologia (L96).** As tabelas de catálogo da ontologia passaram a declarar `atualizacao=sob_demanda`, porque
  só mudam quando a ontologia muda. Com `diaria`, a regra USO01 as acusava 2 dias depois de cada mudança.

## Fase 29 · Regras com vigência, questionário do negócio e triagem

**Objetivo:** o pedido do dono foi ter questionários para o negócio criar regras de avaliação de qualidade, métricas e
observabilidade, e uma retroalimentação que verifique sempre o que está dando errado. Isso lembrando que uma regra pode
valer só por um período, porque em algum momento ela mudou.

**O que fizemos (26/11/2026):**
- **Catálogo de regras** (`regras/catalogo/catalogo_regras.yml`).
  - As 14 regras de qualidade têm versão e vigência pela **data do dado**, com dono, limite aceito, motivo, origem e
    aprovação.
  - O YAML do DQX como código agora é gerado do catálogo: cada versão vira uma checagem com `filter` pela data e a versão
    no `user_metadata`.
- **Objetos em `pos_venda.regras`:**
  - o catálogo e a triagem (a triagem tem `CHECK` nas 4 classificações);
  - a função `versao_vigente(regra, dia)`;
  - as visões `v_falhas_regras`, `v_triagem_pendente`, `v_mudancas_regras` e `v_retroalimentacao`.
- **Questionário do negócio** (`regras/questionario/QUESTIONARIO_NEGOCIO.md`).
  - Tem 5 blocos: dado certo, quanto erro é aceitável, perguntas aos números, vigência e retroalimentação.
  - Cada pergunta aponta o campo do catálogo que preenche.
  - O fim do questionário lista 7 perguntas em aberto para o dono, tiradas do dado real.
- **Ensaio de vigência** (fictício: `QUINZENAL` aceita a partir de 05/01/2027).
  - O DQX rodou em modo `ensaio`, que não grava nada. Na janela de 14 dias, ele bateu com o SQL nas 15 checagens.
  - A versão 1 reprovou 105 eventos e a versão 2, 68 (L95).
- **Garantias.**
  - O gerador tem 17 testes sem rede, e o `conferir` tem 11 checagens no Databricks.
  - Há 8 cenários BDD do catálogo, fora do portão da carga.
  - O CI roda os testes do catálogo em todo push.

- **Marca e cores.**
  - Antes de qualquer coisa visual, procure a marca da empresa (`docs/marca/`). Ainda não há marca.
  - As 5 paletas do projeto viraram uma fonte única, `docs/marca/marca.json`, que os 4 geradores e as 2 apresentações
    leem.
  - A paleta de séries nova passou no validador; a antiga reprovou para daltônicos (L97).

**Onde está:** `regras/catalogo/`, `regras/questionario/`, `dqx_codigo/aplicar_dqx.py` (modo `ensaio` e coluna
`versao`) e `dqx_codigo/ensaio/`.

**O que aprendemos:**
- Para versionar uma regra no tempo, mantenha o nome (o motivo estável) e use `filter` pela data do dado; o DQX aceita
  duas checagens com o mesmo nome (L95).
- A regra nova nunca julga o dado antigo: a vigência é pela data do dado, não pela data da execução (P41).
- Falha sem triagem não melhora nada. A pauta semanal é `v_triagem_pendente`, e o falso positivo alto devolve a regra
  ao questionário.

## Fase 30 · Validação do projeto: modelo de dados, Wikis, apps e documentação

**Objetivo:** validar o projeto inteiro (código, dados, documentação, apresentações, linhagem, framework e playbook), com
um pedido do dono: toda base precisa de modelo de entidade e relacionamento, de Wiki e de tudo o que for necessário.

**O que fizemos (26/11/2026):**
- **Modelo de dados (P42).**
  - `governanca/modelo_dados.py` gera `docs/modelo_dados/`, com um diagrama ER por base, a partir das PK/FK e da
    linhagem do Unity Catalog, mais as chaves e os relacionamentos lógicos das bases sem constraint.
  - Resultado: 155 entidades em 13 bases, 107 relacionamentos e 125 entidades com chave.
- **Wikis.** De 51 para 155 de 155 ativos, todas com chave, relacionamentos e linhagem.
- **Apps.**
  - O de prontidão estava parado e sem implantação ativa (L98). Religado, foi reavaliado e deu 94,7, contra 94,5 em
    23/11; só os metadados subiram.
  - O DQX Studio rodou 24 de 24 avaliações em 25 e 26/11.
- **Documentação.** `docs/validar_docs.py` (no CI) achou contagens velhas e 6 práticas fora do mapa de gatilhos, e tudo
  foi corrigido (L99).
- **Teste diário das chaves.** A unicidade das chaves virou a tarefa `chaves` do job da sonda, às 06:45. A lista vem de
  `conformidade.chaves_declaradas` (publicada por `modelo_dados.py aplicar`), e a tarefa falha se uma PK do Unity
  Catalog repetir. Na primeira execução, 115 de 115 chaves deram únicas.
- **Dois defeitos reais, achados pelo teste de unicidade das chaves:**
  - a PK com RELY da ponte apólice × cobertura ficou falsa com o produto de teste `VIDA_QA_COB_DUPLICADA`. Passou a ser o
    grão real, com o papel da cobertura, e `aplicar_rely.py conferir` voltou a 14 de 14 (L100);
  - a dimensão `bi.produto` do Power BI repetia produtos e tinha nome nulo. Agora tem 10 produtos únicos, e a paridade
    continua em 100% (L101). O playbook ganhou o catálogo de regras (M5), o modelo ER e as Wikis (M6) e a marca (M8). O doc 05
  ganhou a skill `dataviz`.

- **Spec versão 2 e passo a passo.** O spec ganhou critérios para o modelo ER e as Wikis (E5), a marca (E6) e o teste
  diário das chaves (E7), além de 5 tarefas novas (agora são 47). Ganhou também o
  [passo a passo](../specs/aplicar-base-bruta/PASSO_A_PASSO.md), com os comandos de cada tarefa em ordem e o que
  esperar de cada um.

**Onde está:** `governanca/modelo_dados.py`, `docs/modelo_dados/`, `governanca/aplicar_semantica.py` (`wiki_auto`,
`secao_modelo`), `governanca/ontologia.py` (`WIKI_BASE`), `docs/validar_docs.py`.

**O que aprendemos:**
- Modelo de dados desenhado à mão envelhece. Gerado do catálogo, com chave lógica conferida nos dados, ele acompanha o
  dado (P42).
- Número repetido em vários documentos se confere por script (L99).
- App parado no Free Edition volta com a última implantação; espere o start terminar (L98).
- Chave declarada com RELY se reconfere depois de carga grande, e dimensão de BI se testa como única (L100, L101).
