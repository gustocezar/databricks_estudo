# Trilha de aprendizagem · pos_venda

> Documento incremental. Cada fase nova entra no fim, com a mesma estrutura. Última atualização: **22/11/2026**.
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
