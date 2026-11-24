# Playbook · domínio de dados com qualidade, governança e IA no Databricks

> Documento incremental. Última atualização: **24/11/2026**. Cada módulo tem um **critério de saída** verificável;
> quando o projeto mudar, atualize o módulo afetado e registre no [CHANGELOG](CHANGELOG.md).

Este playbook transforma o que foi feito no pos_venda num **framework reaproveitável**. Ele serve para duas coisas:

1. **Recriar o pos_venda do zero**, de forma repetível: siga o [roteiro de reconstrução](#roteiro-de-reconstrução-do-pos_venda).
2. **Construir outro domínio** (outra base): comece pelo [perfil da base](#passo-0--perfil-da-base). As respostas dizem
   quais módulos usar e como configurar cada um.

---

## Princípios

| # | Princípio | Como aparece no pos_venda |
|---|---|---|
| 1 | **Tudo é código e idempotente**: gerar → aplicar → conferir. Rodar de novo não duplica nem quebra. | `gerar_carga.py`, `gerar_ontologia_sql.py`, `gerar_paineis.py`, `genie.py`; bundles DAB |
| 2 | **Definição única**: cada regra de negócio vive num lugar e é gerada para todos os consumidores. | metric views servem Genie e painéis; `gerar_sql.py` gera SQL e Lakeflow |
| 3 | **Toda etapa termina com uma checagem automática** (critério de saída). | `aplicar_e_testar.py`, `genie.py validar/avaliar`, `auditar_metadados.py` |
| 4 | **Governança é código, e nenhuma etapa pode desfazê-la.** | `aplicar_semantica.py`; `views_preservadas.garantir_view` no job |
| 5 | **Qualidade no começo e no fim**: barreira no pipeline (erro barra) e monitoramento (aviso alerta). | quarentena na silver + DQX Studio nas janelas |
| 6 | **A métrica respeita a natureza do dado** (aditiva, semiaditiva, coorte). | saldo de fechamento semiaditivo; recuperado aditivo; safra por coorte |
| 7 | **Preparado para falhar**: cota, token, rede e serviços desligados têm resposta prevista. | [matriz de resiliência](#matriz-de-resiliência) |
| 8 | **Documentação acompanha o código**, de forma incremental. | esta pasta `docs/` |

---

## Passo 0 · Perfil da base

Responda para cada base (tabela, sistema de origem ou domínio). As respostas escolhem os módulos e os parâmetros.

| Pergunta | Respostas possíveis | O que muda no desenho |
|---|---|---|
| **Como os dados chegam?** | foto completa periódica · eventos incrementais · CDC de banco · arquivos | foto: compare fotos ou SCD; eventos: bronze append-only + Auto CDC; CDC: Lakeflow Connect ou Federation; arquivos: Auto Loader |
| **Frequência e volume por carga?** | diário pequeno · diário grande · contínuo | agenda do job; no DQX, janelas de 7 dias com todas as linhas ou amostra; streaming só se a latência exigir |
| **O que muda no tempo?** | nada · status · cadastro | nada: tabela simples; status: SCD1 (estado atual) + SCD2 (história); cadastro: dimensão SCD2 |
| **Natureza das medidas?** | fluxo (pagamentos, vendas) · posição (saldo, estoque, carteira) · coorte (safra) | fluxo: fato transacional, medidas aditivas, MoM/YTD; posição: fato snapshot diária, medidas semiaditivas; coorte: tabela por safra com taxa |
| **Tem dado pessoal?** | não · pseudônimo · identificável (CPF, nome, contato) | classificação LGPD por tag; ontologia sem identificadores; máscaras ABAC antes de abrir a Genie; exclusão de colunas na Genie |
| **O que torna o dado inutilizável?** | lista de problemas | vira **regra de erro** (barreira/quarentena); o resto vira **regra de aviso** |
| **Quem consome?** | diretoria · analista · operação · sistemas | um espaço Genie e um painel por público; API ou Lakebase para sistemas |
| **Tem regulação ou auditoria?** | não · sim (ex.: SUSEP, LGPD, BACEN) | severidade e aprovação de regras no Studio, histórico de execuções como evidência, linhagem |
| **Pode conceder privilégio no catálogo a um app?** | sim (dono ou `MANAGE`) · não | sim: DQX Studio como app (M5, trilha B) ou código; não: **DQX como código** (M5, trilha A, `dqx_codigo/`) |
| **Onde roda?** | Free Edition · workspace pago | Free: 1 warehouse, cota diária, sem Claude no Model Serving, até 3 apps; pago: warehouses separados, ABAC, Data Classification |

### Perfis prontos

| Perfil | Exemplo | Módulos | Configuração-chave |
|---|---|---|---|
| **A · Eventos de cobrança com carteira** | pagamentos pendentes (pos_venda) | M1–M9 | bronze append; silver SCD1+SCD2; fato snapshot diária; medidas semiaditivas; janelas DQX |
| **B · Cadastro** | apólices, clientes, corretores | M1–M4, M6 | dimensões SCD2 com chave `xxhash64`; classificação LGPD forte; sem metric view própria |
| **C · Fluxo transacional** | baixas, vendas, sinistros pagos | M1–M8 | fato transacional; medidas aditivas; MoM, MTD, YTD e ranking |
| **D · Posição e saldo** | estoque, saldo de conta, reservas | M1–M8 | fato snapshot; `Saldo de fechamento` (semiaditivo `last`); nunca somar dias |
| **E · Base sensível** | qualquer base com CPF e contato | M6 antes de M8 | ontologia sem identificadores; máscaras; Genie com colunas excluídas |

---

## Módulos

Cada módulo: **quando usar**, **passos**, **modelo no pos_venda** (para copiar), **critério de saída** e **armadilhas**.

### M1 · Ambiente e bundles

- **Quando usar:** sempre.
- **Passos:** perfil do CLI; warehouse definido; um bundle por bloco (carga, painel, painéis financeiros); agendas `PAUSED` por padrão (variável do bundle); projeto num repositório Git desde o início, com `.gitignore` para `.venv`, caches e `.databricks/`, e varredura de tokens e dados pessoais antes de enviar a um repositório público (L70).
- **Modelo:** `carga_diaria/databricks.yml` (variável `carga_schedule_status`); `.gitignore` da raiz.
- **Critério de saída:** `databricks bundle validate -t dev` sem erro; `git status` limpo depois do commit.
- **Armadilhas:** no Free Edition, só um warehouse: bundles oficiais que criam warehouse precisam de patch (ex.: DQX Studio).

### M2 · Ingestão e bronze

- **Quando usar:** sempre.
- **Passos:** bronze **append-only** com colunas técnicas (`_ingestao_ts`, `_lote_id`, `_origem`); carga idempotente (ignorar lote já carregado).
- **Modelo:** notebook `10_gerar_eventos` gerado por `carga_diaria/gerar_carga.py`.
- **Critério de saída:** rodar o mesmo dia duas vezes não muda a contagem.
- **Armadilhas:** não padronize no bronze: ele é a prova do que chegou.

### M3 · Silver: padronização, barreira e histórico

- **Quando usar:** sempre.
- **Passos:** padronizar (CPF, telefone, CEP, UF, e-mail); **barreira** com as regras de erro do perfil (o que falha vai para
  a quarentena com o motivo); SCD1 para estado atual e SCD2 para história (Auto CDC).
- **Modelo:** `carga_diaria/src/pipeline/transformations/*.sql`.
- **Critério de saída:** eventos recebidos = aptos + barrados (por dia); quarentena tem o motivo em toda linha.
- **Armadilhas:** regra que não está na barreira **vaza** e aparece depois como chave órfã.

### M4 · Gold: star schema

- **Quando usar:** perfis A, B, C, D.
- **Passos:** dimensões com chave `xxhash64(chave de negócio)`; membro `NAO_INFORMADO`; fato no grão do perfil (snapshot diária
  ou transacional); PK e FK declaradas, a PK com `RELY` depois de provar unicidade e ausência de nulos (FK sem `RELY` quando
  houver órfãs de propósito); `dim_data` com papéis.
- **Modelo:** notebooks `20_gold_dims` e `30_fato_snapshot`; `governanca/aplicar_rely.py` para tabelas que já existem.
- **Critério de saída:** nenhuma FK órfã fora dos incidentes conhecidos (`gold.dq_fato_orfas_diarias`);
  `aplicar_rely.py conferir` = 14 PK com `RELY` e 15 FK sem; o plano de uma consulta que não usa a dimensão não lê a dimensão.
- **Armadilhas:** chave substituta sequencial quebra a fato histórica quando a dimensão é reescrita; não existe `ALTER
  CONSTRAINT ... RELY`: a PK é removida e declarada de novo, e o `CASCADE` apaga as FKs que apontam para ela (L72).

### M5 · Qualidade: métricas, DQX e janelas

- **Quando usar:** sempre (perfil regulado: obrigatório com aprovação).
- **Escolha a trilha (P38):** a **A**, DQX como código, não precisa de app nem de privilégio no catálogo; a **B**, DQX
  Studio como app, precisa conceder `USE CATALOG` e `CREATE SCHEMA` ao service principal do app. As duas usam as
  mesmas regras, com os mesmos nomes da barreira.
- **Trilha A · DQX como código:**
  1. métricas diárias de qualidade na gold, como na trilha B;
  2. candidatas com `DQProfiler` e `DQGenerator`, revisadas; regras em YAML no repositório, com erro ou aviso;
  3. job (bundle `dqx_codigo/`) que avalia **todas as linhas** da janela e grava válidos, quarentena e
     `dq_metricas_regras`;
  4. painel de qualidade sobre `dq_metricas_regras`; o job vira tarefa no fim da carga.
  - **Modelo:** [`dqx_codigo/`](../dqx_codigo/README.md).
  - **Critério de saída:** job SUCCESS; erros do DQX = quarentena da barreira na mesma janela; toda regra aparece nas
    métricas, mesmo com zero.
- **Trilha B · DQX Studio como app** (a do pos_venda). **Passos:**
  1. métricas diárias de qualidade na gold (recebidos, aptos, barrados, avisos);
  2. regras do DQX geradas por código, com criticidade erro ou aviso;
  3. views de **janela** sobre uma tabela de controle (`dq.janela_avaliacao`), avaliadas com **todas as linhas**;
  4. Registro de Regras + tabelas monitoradas para aparecer no menu do Studio; recalcular notas;
  5. agendamento por tabela monitorada logo depois da carga (`registro_studio.py agendar`, nasce pausado; `ligar`/`pausar`
     junto com a agenda do job), e uma tarefa no fim do job que liga o app do Studio se ele estiver parado.
- **Modelo:** `carga_diaria/janela_avaliacao.py`, `dqx_studio/regras/` (`definir_regras.py`, `registro_studio.py`, `rodar_ciclos.py`).
- **Critério de saída:** `registro_studio.py executar` com todas as execuções SUCCESS e nota calculada; quarentena do pipeline = reprovados no Studio.
- **Armadilhas:** dry run com amostra lê as primeiras N linhas; `skip_duplicates` funde severidades; regras antigas na mesma tabela travam o Registro.

### M6 · Governança

- **Quando usar:** sempre; antes de M8 se houver dado pessoal.
- **Passos:**
  1. auditar (`auditar_metadados.py`);
  2. descrições por nome de coluna com exceções por tabela (`descricoes_colunas.py` → `aplicar_descricoes.py`); schemas
     antigos com as mesmas colunas reaproveitam o dicionário (`aplicar_descricoes.py legado`); não descreva objetos internos
     de pipeline (`__materialization_mat_*`, `event_log_*`);
  3. governed tags, domínio e subdomínios, tags por camada/tipo/entidade, certificação, classificação LGPD, Pages e Wikis (`aplicar_semantica.py`, conteúdo em `ontologia.py`);
  4. toda view recriada por job passa por `views_preservadas.garantir_view` (com `ddl=` quando a view tem lista de colunas com `COMMENT`);
  5. a camada de negócio (ontologia) não expõe identificadores pessoais, nem pseudônimos: ligue entidades pela chave substituta (`*_sk`);
  6. **dado pessoal: marcar sempre, mascarar quando o uso permitir.** Marque toda coluna com `dado_pessoal = <categoria>` e a
     tabela com `contem_dado_pessoal` (derivados da classificação `class.*`), em **todo** schema que continue no catálogo,
     inclusive os antigos (no pos_venda os legados recebem só essas tags). Máscara por tag (ABAC) é opcional: no pos_venda
     ficou sem máscara porque a validação de qualidade precisa dos valores reais. Se abrir a camadas com dado pessoal para
     mais gente, controle o acesso por grants ou máscaras com exceção para quem valida.
  7. **domínio e responsável em chaves padrão**, além da tag do Discover: `domain`, `subject_area` (subdomínio) e
     `data_owner` (papel responsável), como governed tags com valores permitidos (`DOMINIO_PADRAO`, `RESPONSAVEL` em
     `ontologia.py`). Ferramentas de avaliação e catálogos externos só leem essas chaves.
- **Critério de saída:** auditoria com 100% de descrição nas camadas principais, **0 PII sem tag em todos os schemas**,
  0 tags não lidas e toda tabela principal com `domain` e `data_owner`.
- **Armadilhas:** `CREATE OR REPLACE VIEW` apaga tags, tags de coluna e Wiki; tag de coluna de view só pela API.

### M7 · Camada semântica: ontologia e metric views

- **Quando usar:** quando houver consumo por Genie ou painel.
- **Passos:**
  1. schema de ontologia com entidades sem identificadores, relações e glossário;
  2. metric views por assunto, com descrição em **todo** campo e sinônimos;
  3. padrões do perfil (uc-semantics-patterns): semiaditivo `last`/`first`, `offset` para mês anterior, `cumulative` para MTD/YTD, `RANK()` para ranking;
  4. meses e semanas como `date`.
- **Modelo:** `governanca/gerar_ontologia_sql.py` (dicionário `DESCR` injeta descrições no YAML).
- **Critério de saída:** cada medida nova conferida contra SQL escrito à mão (no pos_venda: 64 de 64 combinações produto × mês).
- **Armadilhas:** semiaditivo é por fatia; ranking não combina com medidas de janela; recriar metric view apaga tags e Wiki
  (rode `aplicar_semantica.py` depois).

### M8 · Consumo: Genie e painéis

- **Quando usar:** quando houver público definido no perfil.
- **Passos:**
  1. **Genie** por público: instruções < 2.000 caracteres (desambiguação, período, regra semiaditiva, privacidade), exemplos de SQL, perguntas de avaliação vindas das Pages; validar todo SQL antes de publicar.
  2. **Painéis** gerados por código sobre as metric views, com conferência da estrutura e teste de cada dataset; **uma página por fato** em cada público (diretoria abre numa visão executiva); KPI com comparação; link para a Genie do público.
  3. **Outra ferramenta de BI (ex.: Power BI)**, quando pedirem para avaliar: visões agregadas em `bi` **a partir das mesmas metric views** + projeto PBIP gerado por código (modelo TMDL, relatórios PBIR com as mesmas páginas), validado contra os esquemas oficiais e com paridade de números contra o painel.
- **Modelo:** `governanca/genie.py`, `paineis_financeiros/gerar_paineis.py`, `paineis_financeiros/powerbi/gerar_powerbi.py`.
- **Critério de saída:** `genie.py avaliar` com 100%; todos os datasets dos painéis SUCCEEDED; `gerar_powerbi.py` com conferência ok e `referencia` com paridade 100%.
- **Armadilhas:** gabarito desatualizado reprova resposta certa; mês incompleto distorce variação de fluxo (compare só meses completos); texto de painel ou instrução com data fixa ("foto de 24/12") envelhece com a carga diária: diga "foto mais recente"; no Power BI o saldo semiaditivo precisa de medida com último dia do contexto (não `SUM`).

### M9 · Avaliação e operação

- **Quando usar:** antes de abrir para usuários e a cada mudança semântica.
- **Passos:**
  1. benchmarks oficiais (Genie Eval) e avaliação independente (genie-best-practices-agent, modo offline);
  2. triagem com veredito por achado;
  3. ligar agendas só depois dos critérios de saída;
  4. reauditar metadados após cada carga grande;
  5. prontidão da ontologia com o app genie-ontology-readiness, com a identidade do usuário (escopo `sql`) e os espaços
     Genie compartilhados com o app; registre a nota por pilar e as lacunas aceitas;
  6. histórico das avaliações no Lakebase: `implantar_app.py` (database própria no projeto Lakebase existente, versão
     fixa do app) e `avaliar.py rodar <rótulo>` antes e depois de cada mudança de governança, para comparar no app;
  7. régua de 12 itens do Genie Workbench sem o app (`genie-agent-scanner`, só leitura) e auditoria Power BI on Databricks
     (`pba`), com triagem: aprovação sem dado de entrada não é aprovação (L71, L73).
- **Modelo:** `governanca/genie/avaliacao_boas_praticas/`, `governanca/ontologia_readiness/` (`RESULTADO.md`, `implantar_app.py`, `avaliar.py`),
  `governanca/genie/scanner/TRIAGEM.md`, `paineis_financeiros/powerbi/auditoria/README.md`.
- **Critério de saída:** triagem registrada; achados que procedem aplicados ou justificados; prontidão ≥ 90 ou lacunas
  justificadas (no pos_venda: 92,7).

### M10 · Regras de negócio testadas (BDD)

- **Quando usar:** quando uma regra de cálculo aparece em mais de um lugar (pipeline, barreira, gold, Genie) ou quando um
  erro dela custa caro (valores financeiros, documento do cliente).
- **Passos:**
  1. extraia a regra exatamente como o pipeline calcula hoje e escreva uma função SQL no Unity Catalog, com descrição da
     função e de cada parâmetro no próprio DDL;
  2. escreva cenários em português (Gherkin, `# language: pt`): exemplos do negócio, limites de cada faixa, arredondamento
     e os incidentes conhecidos;
  3. rode os cenários pela Statement Execution API (`behave`, sem Spark);
  4. meça a paridade linha a linha contra as tabelas que já calculam a regra e o impacto de cada decisão nova;
  5. só com 100% de paridade troque o cálculo do pipeline e da gold pela função; na barreira, **acrescente** a regra da
     função depois das regras que apontam a causa (não substitua no mesmo lugar) e meça a reclassificação na quarentena;
  6. ponha os cenários como portão no início do job (`05_portao_regras`) e dê as funções à Genie
     (`instructions.sql_functions`), com um exemplo e uma pergunta de avaliação por espaço; espelhe a regra no DQX Studio
     (`definir_regras.py` + `registro_studio.py aplicar <tabelas>`), com `USE SCHEMA` e `EXECUTE` no schema das funções
     para o service principal do app e o executor dos agendamentos, e teste com disparo agendado real;
  7. valide sem gerar dia novo: job só com portão, silver e gold de um intervalo, comparado linha a linha com uma cópia.
- **Modelo:** `regras/` (`funcoes.py`, `features/`, `paridade.py`).
- **Critério de saída:** 100% dos cenários (local e no portão do job); 0 divergência na paridade e na comparação
  antes/depois da gold; decisões novas registradas com o impacto medido; Genie e painéis sem regressão.
- **Armadilhas:** espera síncrona da API perto do timeout de leitura do SDK (60 s) quebra por rede; o `{}` do parse do
  behave não casa texto vazio (passo próprio para `""`).

### M11 · Custo e uso (FinOps)

- **Quando usar:** quando alguém precisa saber quanto custa cada funcionalidade e de quem é o custo, ou quando
  plataforma e squads dividem o mesmo workspace.
- **Passos:**
  1. Base FOCUS a partir de `system.billing.usage` e `list_prices`, escolhendo os campos do `usage_metadata` um a um.
  2. Regras de atribuição: tag, nome do recurso, compartilhado; o SQL warehouse é rateado por consulta.
  3. Visões por público: plataforma, squad e uso, com a Genie separando UI de API.
  4. Boas práticas com meta (Well-Architected CO-01 a CO-04).
  5. `conferir` depois de cada mudança.
- **Modelo:** `finops/gerar_finops.py` (`REGRAS`, `ativos`, `aplicar`, `conferir`) e `finops/README.md`.
- **Critério de saída:**
  - cada visão responde;
  - linhas e custo da base FOCUS = billing;
  - custo por funcionalidade e por projeto = base;
  - SQL rateado = SQL da base;
  - não atribuído medido e explicado.
- **Armadilhas:**
  - struct inteiro de tabela de sistema numa visão (L76);
  - job oculto de alerta SQL, sem nome (L77, L79);
  - contar avaliações automáticas como adoção (L78);
  - no Free Edition o `BilledCost` é 0 e a medida é o custo a preço de lista.

### M12 · Conformidade contínua e observabilidade

- **Quando usar:** quando as regras de governança (descrição, tags, dado pessoal) precisam continuar valendo depois
  da primeira aplicação, ou quando o workspace já tem observabilidade de outra pessoa.
- **Passos:**
  1. Dê um papel a cada schema (`CAMADAS`: principal, legado, apoio) e separe as tabelas internas do Lakeflow (L80).
  2. Escreva as regras com meta, severidade, origem e como corrigir (`REGRAS`). Prefira regras que já têm prática no
     framework (P08, P13 a P16, P31).
  3. Leia pela API o que as tabelas de sistema não têm: os valores das tags governadas (`politicas`) e os alertas SQL
     (`alertas`).
  4. `aplicar`; depois `registrar` (sonda das views e histórico do dia) e `conferir`.
  5. Faça a triagem das pendências antes de corrigir. Falso positivo vira ajuste no gerador, não exceção à mão.
  6. Avalie a observabilidade que já existe, ação por ação, com veredito e custo (`acoes_observabilidade`).
- **Modelo:** `conformidade/gerar_conformidade.py` e `conformidade/README.md`.
- **Critério de saída:**
  - cada visão responde;
  - o inventário tem todo ativo do `information_schema`;
  - as regras de descrição verificam todo ativo e toda coluna que não sejam internos;
  - pendências = achados não conformes = metric view;
  - nenhuma regra "sem dados";
  - histórico do dia com uma linha por regra.
- **Armadilhas:**
  - tabelas internas do Lakeflow contadas como ativos (L80);
  - alerta SQL que roda como job oculto (L79);
  - checagem de cluster clássico que volta vazia no Free Edition (L81);
  - a sonda usa `DESCRIBE QUERY`: pega a view que não resolve, mas não um erro que só aparece ao executar.

### M13 · Sustentação: tempo de execução, linha de base e SLA

- **Quando usar:** quando um job diário vai para produção e alguém depende da hora em que ele termina, ou quando
  precisa responder "por que a carga demorou hoje?".
- **Passos:**
  1. Junte as fatias de hora em hora das tabelas `system.lakeflow.*_timeline` por `run_id`, com o resultado e as
     durações da última fatia (L90). Separe setup de execução (L89).
  2. Ligue jobs e pipelines ao projeto pelas regras que já existem (`finops.config_atribuicao`), sem lista nova.
  3. Defina a linha de base (mediana e p95 das últimas N execuções com sucesso, com um mínimo para valer) e o desvio
     (acima do p95 ou de 1,5 vez a mediana das N anteriores).
  4. Ligue o volume de cada execução pelo momento da gravação, para separar lentidão de volume.
  5. Ponha a hora meta (SLA) e meça só a execução da agenda. Com a agenda pausada, use a folga projetada (L91).
  6. Escreva o sintoma e a ação de cada tarefa, ligados à matriz de resiliência.
  7. Gere o painel e o alerta. O alerta nasce pausado e dispara no máximo 4 vezes por dia (PLT06).
  8. `testar` antes de criar; depois `aplicar` e `conferir`.
- **Modelo:** `sustentacao/gerar_sustentacao.py`, `sustentacao/README.md` e o
  [manual de sustentação](07_SUSTENTACAO.md) (rotina, runbooks, reprocessamento, RACI).
- **Critério de saída:**
  - cada visão responde e toda coluna tem descrição;
  - execuções de job e de tarefa e updates do pipeline batem com as tabelas de sistema;
  - o volume por execução soma o total do bronze e da fato;
  - a mediana de cada tarefa é igual ao cálculo direto;
  - toda tarefa tem linha na matriz;
  - o alerta está implantado e pausado.
- **Armadilhas:**
  - contar fatias de hora como execuções (L90);
  - chamar de lentidão a espera por computação ou o backfill (L89);
  - medir o SLA em execução manual (L91);
  - linha de base com tarefas `SKIPPED`, que têm duração 0;
  - alerta que dispara por segundos acima de um p95 de base curta: ponha um piso no alerta (L92).

---

## Matriz de resiliência

| Falha | Sintoma | Resposta prevista |
|---|---|---|
| Cota diária do Free Edition | "free daily limit" ou warehouse recusa | scripts param com `CotaEsgotada`; esperar a renovação (meia-noite UTC); não rodar cargas no dia de demonstração |
| Token expirado no meio do processo | HTTP 401 | cliente da API renova o token e repete (`carregar_regras.py`) |
| Rede instável | DNS ou timeout | retentativas com espera crescente; processos retomáveis por ciclo |
| Lakebase do DQX Studio desligado | app com `lakebase_connection_unavailable` | `databricks postgres update-endpoint ... spec.disabled=false` e reiniciar o app |
| App do Studio parado | app para após 24 h no Free Edition; agendamento do Studio não dispara | a tarefa `ligar_dqx_studio` no fim do job liga o app; à mão: `databricks apps start dqx-studio` |
| Recriação de view pelo job | tags e Wiki somem | `garantir_view`: só recria se a definição mudou, e devolve a governança |
| Recriação de metric view | tags e Wiki somem | rodar `aplicar_semantica.py` (e republicar as Wikis) |
| Mudança semântica | Genie erra ou benchmark reprova | atualizar gabaritos e exemplos; rodar `genie.py validar` e `avaliar` |
| Modelo indisponível no workspace | ferramenta pede Claude e falha | usar endpoint disponível que suporte saída estruturada (ex.: `llama-4-maverick`) e limitar `max_tokens` |
| Execuções extras no Studio | painel mostra semana que não existe | filtrar a origem das execuções (ex.: `registry_rule_id`) e manter as checagens de consistência |
| Regra do Studio chama função sem permissão | execução manual ou agendada falha ao resolver `pos_venda.regras.*` | `GRANT USE SCHEMA, EXECUTE ON SCHEMA pos_venda.regras` ao service principal do app e ao executor dos agendamentos (o preflight só confere SELECT) |
| Portão das regras reprovado | tarefa `portao_regras` falha e a carga do dia não roda | ler o cenário que falhou no log da tarefa; corrigir a função (ou o cenário, se a regra de negócio mudou) e rodar o job de novo |
| Timeout de leitura na Statement Execution API | `ReadTimeoutError` (60 s) num cenário BDD | espera síncrona de 20 s, consulta do estado e nova tentativa só em erro de transporte (`regras/uc.py`) |
| Dia novo carregado | textos com data fixa ("foto de 24/12") ficam errados; teste que contava 35 dias reprova; painel de qualidade abre uma "Semana 6" | escreva "foto mais recente" em painéis e instruções da Genie; checagens dependentes da data (`count = dias desde o início`); confira roteiro e gabaritos depois da carga |
| App do DQX Studio recém-ligado | as submissões do replay voltam HTTP 502, com o app em RUNNING | esperar "Application startup complete" em `databricks apps logs dqx-studio` (o app reinstala os pacotes ao subir) e rodar de novo (L85) |
| View quebrada por mudança em tabela de sistema ou em outro schema | `DESCRIBE QUERY` falha; a regra USO03 da conformidade cai | `gerar_conformidade.py registrar` lista as quebradas em `sonda_views`; recriar a partir do código ou apagar (L76) |
| Alerta SQL de hora em hora | warehouse acorda o dia todo; custo SQL "sem dono" | `databricks alerts-v2 list-alerts`; espaçar a agenda (regra PLT06, L79) |
| Carga diária atrasada para a meta das 06:15 | `sla_diario` com "atrasada", "falhou" ou "sem execução da agenda"; o alerta de sustentação dispara às 06:20 | ver em `matriz_tarefas` a tarefa que travou, seguir a ação dela e avisar quem usa a foto do dia (o DQX Studio avalia às 06:30) |
| Tarefa acima do normal | linha em `desvios` com a causa provável | espera por computação (setup): nada a corrigir no código; volume maior: conferir `volume_execucao`; lentidão com o mesmo volume: ler o log ou o event log da tarefa (L89) |
| Projeto Power BI não abre no Desktop | erro de TMDL/PBIR com arquivo e linha | corrigir em `gerar_powerbi.py` (não no arquivo gerado), gerar de novo e rodar a conferência contra os esquemas oficiais |

---

## Roteiro de reconstrução do pos_venda

Ordem para recriar tudo do zero num workspace (perfil `dbx-workshop`). Cada passo tem a checagem de saída.

| # | Passo | Comando | Saída esperada |
|---|---|---|---|
| 1 | Dados sintéticos | rodar o notebook `01_gerar_one_table.py` (serverless) | 500.000 linhas na one-table |
| 2 | (opcional, legado) medalhão | `cd medalhao && databricks bundle deploy -t dev` e `bundle run medalhao_sql` | schemas `*_sql` e `*_ldp` |
| 3 | Carga diária: gerar e implantar | `cd carga_diaria && python3 gerar_carga.py && databricks bundle deploy -t dev` | validate OK, job PAUSED |
| 4 | Setup e backfill | `databricks bundle run carga_setup -t dev` e `bundle run carga_diaria -t dev --params data_inicio=2026-05-19,data_fim=2026-11-18` | silver e fato preenchidas |
| 5 | DQX Studio | instalar pelo bundle oficial com o patch do warehouse ([dqx_studio/README.md](../dqx_studio/README.md)) | app RUNNING, setup `ready` |
| 6 | Ciclos com incidentes e histórico | `cd dqx_studio/regras && python3 definir_regras.py && python3 -u rodar_ciclos.py 2 3 4 5` e depois `rodar_ciclos.py 1 2 3 4 5 --replay`; o catálogo de exemplos: carga de 26/12 a 09/01 e `rodar_ciclos.py 6 7 8 --replay` e `--dims` | 40 execuções completas no histórico (8 semanas) |
| 7 | Registro de Regras | `python3 registro_studio.py aplicar && python3 registro_studio.py executar` (depois do passo 18: uma regra chama `pos_venda.regras`) | 70 modelos, 12 tabelas, execuções SUCCESS com nota |
| 8 | Painel de qualidade | `cd dqx_studio/painel && python3 aplicar_e_testar.py && python3 gerar_painel.py && databricks bundle deploy -t dev` | "RESULTADO: tudo certo" |
| 9 | Ontologia e metric views | `cd governanca && python3 gerar_ontologia_sql.py && python3 aplicar_sql.py ontologia_sql.json` | 21 comandos ok |
| 10 | Descrições | `python3 aplicar_descricoes.py` | colunas descritas |
| 11 | Semântica e LGPD | `python3 aplicar_semantica.py` | domínio, tags, Pages e Wikis |
| 12 | Auditoria | `python3 auditar_metadados.py` | 100% descrito, 0 PII sem tag |
| 13 | Genie | `python3 genie.py gerar && python3 genie.py validar && python3 genie.py criar && python3 genie.py avaliar` | 100% das perguntas |
| 14 | Painéis financeiros | `cd paineis_financeiros && python3 gerar_paineis.py && databricks bundle deploy -t dev` | conferência ok, 2 painéis × 5 páginas (uma por fato) publicados |
| 14b | Opção Power BI (opcional) | `cd paineis_financeiros/powerbi && ../../regras/.venv/bin/python gerar_powerbi.py visoes && python3 gerar_powerbi.py && ../../regras/.venv/bin/python gerar_powerbi.py referencia` | schema `bi` com 8 visões; 102 arquivos válidos; paridade 21/21 |
| 15 | Avaliação independente (opcional) | `governanca/genie/avaliacao_boas_praticas/extrair.py` e `rodar.py` | relatórios + triagem |
| 16 | Agendar o Studio (nasce pausado) | `cd dqx_studio/regras && python3 registro_studio.py agendar` | 12 tabelas agendadas para 06:30, pausadas |
| 17 | Ligar as agendas (quando decidir) | `databricks bundle deploy -t dev --var="carga_schedule_status=UNPAUSED"` e `python3 registro_studio.py ligar` | job UNPAUSED e 12 agendamentos ativos |
| 18 | Regras de negócio (BDD) | `cd regras && .venv/bin/python funcoes.py && .venv/bin/behave && .venv/bin/python paridade.py` (antes do passo 3 numa reconstrução: o job depende das funções) | 5 funções, 36/36 cenários, paridade 100% |
| 19 | Prontidão com histórico (opcional) | `cd governanca/ontologia_readiness && python3 implantar_app.py && python3 avaliar.py rodar base` | `history_ready`, nota gravada |
| 20 | Sustentação | `python3 sustentacao/gerar_sustentacao.py testar && python3 sustentacao/gerar_sustentacao.py aplicar && python3 sustentacao/gerar_sustentacao.py conferir`; depois `cd sustentacao && databricks bundle deploy -t dev` | conferência ok; painel publicado; alerta pausado |

Todos os comandos `databricks` levam `--profile dbx-workshop`.

---

## Como adaptar para outra base

Para uma base bruta de pendências já no Databricks, com ou sem agente de código, siga o
[guia 06](06_GUIA_BASE_BRUTA.md): ele usa estes passos com a ficha, o mapeamento e as duas trilhas do DQX.

1. Preencha o [perfil da base](#passo-0--perfil-da-base) e escolha o perfil pronto mais próximo.
2. Copie as pastas dos módulos escolhidos e troque os parâmetros:

| Onde | O que trocar |
|---|---|
| `carga_diaria/gerar_carga.py` | catálogo, tabelas de origem, colunas de cadastro × colunas que variam, tipos de evento |
| `carga_diaria/src/pipeline/transformations/` | regras de padronização e de erro (barreira) |
| `carga_diaria/janela_avaliacao.py` | views de janela por camada |
| `dqx_studio/regras/definir_regras.py` | regras de erro e aviso por tabela (trilha B, app) |
| `dqx_codigo/checks_pendencias.yml` | regras de erro e aviso em YAML (trilha A, código), com as colunas e os domínios da nova base |
| `governanca/descricoes_colunas.py`, `ontologia.py` | glossário, Pages, Wikis, classificação LGPD, domínio, `DOMINIO_PADRAO` e `RESPONSAVEL` |
| `governanca/gerar_ontologia_sql.py` | entidades, relações, metric views e descrições (`DESCR`) |
| `governanca/genie.py` | públicos, instruções, exemplos, perguntas de avaliação |
| `paineis_financeiros/gerar_paineis.py` | datasets, KPIs e páginas |
| `regras/funcoes.py`, `regras/features/`, `regras/paridade.py` | regras de cálculo do domínio, cenários e tabelas de paridade |

3. Rode o [roteiro](#roteiro-de-reconstrução-do-pos_venda) com os critérios de saída de cada módulo.
4. Registre o que mudou no [CHANGELOG](CHANGELOG.md) e as novas lições em [03_LICOES_APRENDIDAS.md](03_LICOES_APRENDIDAS.md).
