# Repositórios da databricks-solutions e o pos_venda

147 repositórios públicos lidos em 2026-11-20 e revistos em 2026-11-22. Relevância avaliada para o pos_venda. O que aplicar e por quê: `REVISAO_2026-11-22.md`.

## Situação no projeto

**Aplicado (4):** [agentic-bdd-uc-functions](https://github.com/databricks-solutions/agentic-bdd-uc-functions), [genie-best-practices-agent](https://github.com/databricks-solutions/genie-best-practices-agent), [genie-ontology-readiness](https://github.com/databricks-solutions/genie-ontology-readiness), [uc-semantics-patterns](https://github.com/databricks-solutions/uc-semantics-patterns)

**Proposto (5):** [dbx-adoption-monitor](https://github.com/databricks-solutions/dbx-adoption-monitor), [power-bi-on-databricks-quickstarts](https://github.com/databricks-solutions/power-bi-on-databricks-quickstarts), [powerbi-analyzer](https://github.com/databricks-solutions/powerbi-analyzer), [regulatory_data_governance](https://github.com/databricks-solutions/regulatory_data_governance), [technical-services-solutions](https://github.com/databricks-solutions/technical-services-solutions)

**Adiado (6):** [data-classification-review-app](https://github.com/databricks-solutions/data-classification-review-app), [databricks-dab-examples](https://github.com/databricks-solutions/databricks-dab-examples), [databricks-genie-workbench](https://github.com/databricks-solutions/databricks-genie-workbench), [databricks-waf](https://github.com/databricks-solutions/databricks-waf), [genierails](https://github.com/databricks-solutions/genierails), [uc-declarative-abac](https://github.com/databricks-solutions/uc-declarative-abac)

## Relevância Alta (6)

### [powerbi-analyzer](https://github.com/databricks-solutions/powerbi-analyzer) · BI externo (Power BI, Grafana) · ★4 · Free Edition: Sim

- **Finalidade:** CLI que audita uma instalação de Power BI sobre Databricks com 42 regras da cheat sheet.
- **Como usar:** Instalar com uv e rodar pba sobre .pbix, workspace ou config.
- **Casos de uso:** Auditoria de boas práticas.
- **Benefício para o pos_venda:** Audita o projeto Power BI do pos_venda e o lado Databricks contra as 42 regras da cheat sheet; cobre parte do que hoje só o Power BI Desktop verificaria e dá um relatório de boas práticas para a avaliação das duas ferramentas.
- **Nota Free Edition:** `pba pbix` lê .pbip sem credencial (roda no Mac); `pba databricks` lê system.query.history, legível neste workspace.
- **Situação no projeto:** proposto. Proposta 1 da revisão de 22/11.

### [genie-best-practices-agent](https://github.com/databricks-solutions/genie-best-practices-agent) · Genie e camada semântica · ★5 · Free Edition: A confirmar

- **Finalidade:** Agente que avalia a configuração de um espaço Genie e os metadados do UC contra as boas práticas, com benchmarks opcionais.
- **Como usar:** Configurar o ID do espaço e o perfil do CLI, rodar o pipeline LangGraph e ler o relatório por trilha de avaliação.
- **Casos de uso:** Revisão de espaço Genie antes de liberar para o negócio; auditoria de instruções, exemplos SQL e descrições de colunas.
- **Benefício para o pos_venda:** Segunda opinião independente sobre os espaços do CFO e do analista: instruções de texto, exemplos SQL, descrições e sinônimos.
- **Nota Free Edition:** Roda localmente com LangGraph; precisa de um endpoint de LLM no workspace.
- **Situação no projeto:** aplicado. Fase 13: triagem em governanca/genie/avaliacao_boas_praticas/.

### [genie-ontology-readiness](https://github.com/databricks-solutions/genie-ontology-readiness) · Genie e camada semântica · ★29 · Free Edition: A confirmar

- **Finalidade:** App que avalia a prontidão do workspace para a Genie Ontology em 7 pilares (UC, metadados, relações, metric views, Genie, domínios, adoção) e gera um plano.
- **Como usar:** Implantar pela UI de Apps a partir do Git, rodar a aba Assess, depois Plan e Learn.
- **Casos de uso:** Diagnóstico de maturidade semântica, roteiro de capacitação, explicação técnica e de negócio de cada recurso.
- **Benefício para o pos_venda:** Mede a camada de ontologia que acabamos de montar (domínio Pós-venda, 18 Pages, 51 wikis, tags, metric views, 2 espaços Genie) e aponta lacunas como chaves PK/FK declaradas e adoção.
- **Nota Free Edition:** App com chamada à Foundation Model API do workspace; avaliação somente leitura.
- **Situação no projeto:** aplicado. Fase 18: app v1.5.0 (a versão mais recente em 22/11), nota 92,7, histórico no Lakebase.

### [uc-semantics-patterns](https://github.com/databricks-solutions/uc-semantics-patterns) · Genie e camada semântica · ★32 · Free Edition: Sim

- **Finalidade:** Coleção de padrões prontos de metric views (UC Business Semantics) para cálculos que não são óbvios em YAML.
- **Como usar:** Abrir a pasta do padrão, copiar o YAML e a consulta de exemplo, trocar tabelas e colunas pelas suas.
- **Casos de uso:** Comparação de períodos (MoM, YoY), acumulado no período (MTD, YTD), saldos semiaditivos (abertura e fechamento), ranking, segmentação estática e dinâmica, calendários, curva ABC, conversão de moeda.
- **Benefício para o pos_venda:** Resolve com padrão oficial o saldo em aberto semiaditivo que hoje tratamos com três medidas (foto mais recente, fim de mês, média diária); acrescenta MoM/YoY e ranking de corretores e produtos nas metric views que a Genie e os painéis já usam.
- **Situação no projeto:** aplicado. Fase 12: saldo de fechamento, mês anterior e variação, acumulados no mês e no ano, ranking. Ainda não usados: médias móveis e curva ABC (proposta 5 da revisão).

### [regulatory_data_governance](https://github.com/databricks-solutions/regulatory_data_governance) · Qualidade, governança e segurança · ★2 · Free Edition: A confirmar

- **Finalidade:** Starter kit em português para a Resolução Conjunta BACEN nº 18: app de monitoramento de qualidade com motor de regras ligado ao DQX Studio, pipelines medallion dos CADOCs 3040/3050, painéis AI/BI e sala Genie.
- **Como usar:** Copiar target.yml.example, preencher perfil e URL do DQX Studio, rodar databricks bundle deploy e os jobs rc18_end_to_end e r18_compliance_app.
- **Casos de uso:** Governança de dados regulatórios, críticas de qualidade com aprovação, linhagem externa, evidências para auditoria.
- **Benefício para o pos_venda:** Arquitetura mais próxima do pos_venda (medallion, DQX Studio, AI/BI, Genie, em português), mas para a Resolução BACEN nº 18; o pós-venda segue a SUSEP. Não instalar: reaproveitar a dimensão de qualidade em user_metadata de cada regra e a linhagem externa no Unity Catalog.
- **Nota Free Edition:** Exige DQX Studio e Lakebase no mesmo workspace, que o projeto já tem; o deploy cria vários recursos e consome cota.
- **Situação no projeto:** proposto. Propostas 4 (dimensão de qualidade nas regras) e 7 (linhagem externa com Power BI) da revisão de 22/11.

### [technical-services-solutions](https://github.com/databricks-solutions/technical-services-solutions) · Workshops, demos e coleções · ★14 · Free Edition: A confirmar

- **Finalidade:** Coleção do time de Technical Services: governança (ABAC), business semantics, Genie (otimização e scanner de agentes), migrações, prontidão para produção.
- **Como usar:** Entrar na pasta do tema e seguir o README de cada projeto.
- **Casos de uso:** Aceleradores pontuais por tema.
- **Benefício para o pos_venda:** genie/genie-agent-scanner aplica a régua de 12 itens do Genie Workbench sem app, Lakebase ou LLM aos dois espaços Genie. data-warehousing/pbi-aibi-converter e aibi-migration convertem .pbip em painel AI/BI com LLM (Claude, ausente no Free Edition); servem só de referência, porque os dois painéis já saem do mesmo gerador.
- **Situação no projeto:** proposto. Proposta 2 da revisão de 22/11 (genie-agent-scanner).

## Relevância Média (17)

### [advance-document-processing](https://github.com/databricks-solutions/advance-document-processing) · Agentes e IA generativa · ★2 · Free Edition: A confirmar

- **Finalidade:** Pipelines de referência para documentos com ai_parse_document, ai_classify, ai_extract, LLMs de visão e Auto Loader, em notebooks e bundles.
- **Como usar:** Escolher o pipeline (classificação e extração de páginas, citações, base de conhecimento) e implantar o bundle.
- **Casos de uso:** Extrair campos de PDFs, classificar páginas, montar base de conhecimento.
- **Benefício para o pos_venda:** Próximo passo natural do pós-venda: ler comprovantes de pagamento, boletos e cartas de cobrança e conciliar com as pendências.
- **Nota Free Edition:** Usa ai_parse_document e AI Functions; confira disponibilidade e cota.

### [mlops-quickstart](https://github.com/databricks-solutions/mlops-quickstart) · Avaliação, MLOps e modelos · ★13 · Free Edition: A confirmar

- **Finalidade:** Exemplo de MLOps de ponta a ponta (feature table, treino, registro no UC, inferência, CI/CD) com o dataset Iris.
- **Como usar:** Seguir o vídeo e adaptar com o Genie Code para seus dados.
- **Casos de uso:** Primeiro modelo em produção com esteira.
- **Benefício para o pos_venda:** Esqueleto para um modelo de propensão de regularização das pendências, que priorizaria a cobrança.
- **Nota Free Edition:** Treino leve em serverless; serving pode não estar disponível.

### [power-bi-on-databricks-quickstarts](https://github.com/databricks-solutions/power-bi-on-databricks-quickstarts) · BI externo (Power BI, Grafana) · ★101 · Free Edition: Sim

- **Finalidade:** Referências e boas práticas de Power BI sobre Databricks SQL.
- **Como usar:** Abrir o quickstart do tema e a cheat sheet.
- **Casos de uso:** Desempenho de Power BI em DBSQL.
- **Benefício para o pos_venda:** Referência das regras que o powerbi-analyzer verifica. Com importação (942 mil linhas na maior tabela) valem parâmetros de conexão (já usados), chaves com RELY (07), integridade referencial (16) e OAuth M2M (13) para atualizar no serviço; os de DirectQuery e agregações valem se a carteira for consultada ao vivo.
- **Situação no projeto:** proposto. Proposta 3 da revisão de 22/11: RELY nas 14 PKs da gold (não na FK de forma de pagamento, que tem órfãs de propósito).

### [ai-dev-kit](https://github.com/databricks-solutions/ai-dev-kit) · Ferramentas para coding agents · ★1995 · Free Edition: Sim

- **Finalidade:** Toolkit de skills para agentes de código no Databricks; as skills agora são as Databricks AI Tools, instaladas por databricks aitools install.
- **Como usar:** Rodar o instalador ou databricks aitools install e manter atualizado.
- **Casos de uso:** Construir pipelines, painéis, Genie, apps com assistentes de código.
- **Benefício para o pos_venda:** É a origem das skills Databricks usadas neste projeto; manter atualizado traz correções de APIs (Genie, metric views, painéis).

### [aibi-dashboard-wanderbricks](https://github.com/databricks-solutions/aibi-dashboard-wanderbricks) · Genie e camada semântica · ★6 · Free Edition: Sim

- **Finalidade:** Painel de referência do blog 'Design Beautiful Dashboards in AI/BI', pronto para importar.
- **Como usar:** Baixar o .lvdash.json e importar em Dashboards > Importar arquivo.
- **Casos de uso:** Referência de layout, hierarquia visual, filtros e tema para painéis AI/BI.
- **Benefício para o pos_venda:** Modelo visual para refinar os três painéis do projeto (Qualidade, Diretoria e Analista): KPIs no topo, páginas, tema e filtros.
- **Nota Free Edition:** Usa o dataset samples.wanderbricks e importação de painel.

### [databricks-aibi-design-first-accelerator](https://github.com/databricks-solutions/databricks-aibi-design-first-accelerator) · Genie e camada semântica · ★3 · Free Edition: A confirmar

- **Finalidade:** Do catálogo de KPIs (e ERD ou schema existente) para tabelas, metric views, painéis AI/BI e espaço Genie, por uma sequência de prompts.
- **Como usar:** Preencher accelerator.yaml e kpi_spec.md, fazer bundle deploy e rodar o prompt mestre no Genie Code ou na App (modo brownfield usa o schema atual).
- **Casos de uso:** POC de BI governado em horas, padronizar a camada semântica a partir de uma especificação de KPIs.
- **Benefício para o pos_venda:** Permite regenerar ou comparar a camada semântica do pos_venda a partir de um kpi_spec.md escrito pelo negócio, útil para evoluir os KPIs da gold sem refazer tudo à mão.
- **Nota Free Edition:** Usa Genie Code ou uma App em Flask; gera tabelas, metric views e painéis.

### [databricks-forge](https://github.com/databricks-solutions/databricks-forge) · Genie e camada semântica · ★7 · Free Edition: A confirmar

- **Finalidade:** Transforma metadados do Unity Catalog numa lista priorizada e com valor financeiro de casos de uso de dados e IA, e ativa como Genie, painéis, metric views e documentação.
- **Como usar:** Implantar como App, apontar para catálogos e rodar a descoberta; escolher recomendações e ativar.
- **Casos de uso:** Descobrir próximos casos de uso, gerar backlog para a diretoria, documentar o catálogo.
- **Benefício para o pos_venda:** Com os metadados ricos que já temos (descrições em 92% das colunas, tags e domínio), sugere os próximos casos de uso do pós-venda com estimativa de valor.
- **Nota Free Edition:** App em Next.js com Lakebase e warehouse serverless; lê metadados do UC.

### [databricks-genie-workbench](https://github.com/databricks-solutions/databricks-genie-workbench) · Genie e camada semântica · ★110 · Free Edition: A confirmar

- **Finalidade:** App para criar, pontuar (IQ scan por regras) e otimizar Genie Agents com benchmarks (Genie Space Optimizer). Substitui o MaxGenie.
- **Como usar:** Clonar como Git folder no workspace e rodar o notebook instalador; apontar para o espaço Genie e rodar o scan e o Auto-Optimize.
- **Casos de uso:** Avaliar a qualidade de um espaço Genie, achar instruções e exemplos faltantes, otimizar com base nas perguntas de benchmark, guardar histórico.
- **Benefício para o pos_venda:** Dá nota e plano de melhoria para os dois espaços (Analista financeiro e Diretoria) e automatiza o ciclo de benchmark que fizemos à mão no genie.py (24/24).
- **Nota Free Edition:** Ocuparia a última vaga de app (2 de 3 em uso) e depende do Unity AI Gateway, não confirmado no Free Edition.
- **Situação no projeto:** adiado. O genie-agent-scanner aplica a mesma régua sem instalar; voltar se o scan pedir o Auto-Optimize.

### [ingestion-workbench](https://github.com/databricks-solutions/ingestion-workbench) · Ingestão e streaming · ★5 · Free Edition: A confirmar

- **Finalidade:** Copia tabelas de SQL Server, Oracle, PostgreSQL e MySQL para Delta via Lakehouse Federation, de forma incremental e guiada por metadados, com app de operação.
- **Como usar:** Implantar, descrever tabelas como linhas de metadados e acompanhar os jobs na app.
- **Casos de uso:** Ingestão em massa de bancos transacionais, estates com milhares de tabelas.
- **Benefício para o pos_venda:** Caminho de produção para trocar o gerador sintético pelo banco real do sistema de cobrança e apólices.
- **Nota Free Edition:** Usa Lakehouse Federation para bancos externos; no Free Edition não há origem real nem rede privada.

### [databricks-dab-examples](https://github.com/databricks-solutions/databricks-dab-examples) · Pipelines e engenharia de dados · ★54 · Free Edition: Sim

- **Finalidade:** Projetos de exemplo de Declarative Automation Bundles com boas práticas de desenvolvimento, testes e CI/CD.
- **Como usar:** Começar por flights/flights-simple; copiar a estrutura de targets, testes e workflows.
- **Casos de uso:** Ambientes dev e prod, testes unitários de bibliotecas, CI/CD de jobs e pipelines.
- **Benefício para o pos_venda:** Modelo para amadurecer os bundles carga_diaria, painel e paineis_financeiros com targets dev/prod, testes e pipeline de CI.
- **Situação no projeto:** adiado. O pré-requisito (projeto num repositório Git) foi cumprido em 22/11; falta decidir a esteira de CI/CD.

### [lakeflow_framework](https://github.com/databricks-solutions/lakeflow_framework) · Pipelines e engenharia de dados · ★30 · Free Edition: A confirmar

- **Finalidade:** Framework guiado por metadados para Spark Declarative Pipelines (SDP) em batch e streaming, cobrindo bronze, silver e gold, implantado por bundles.
- **Como usar:** Descrever fluxos em arquivos de configuração e padrões, implantar com bundle; a documentação traz quick start.
- **Casos de uso:** Padronizar dezenas de tabelas medallion, SCD, data vault, modelo dimensional.
- **Benefício para o pos_venda:** Alternativa para trocar os notebooks escritos à mão do carga_diaria por pipelines declarados, com expectations nativas ao lado do DQX.
- **Nota Free Edition:** Usa Spark Declarative Pipelines serverless; confira consumo da cota diária.

### [agentic-bdd-uc-functions](https://github.com/databricks-solutions/agentic-bdd-uc-functions) · Qualidade, governança e segurança · ★1 · Free Edition: Sim

- **Finalidade:** Testes BDD (Behave, Gherkin) de funções do Unity Catalog pela Statement Execution API, rodando em CI sem Spark.
- **Como usar:** Escrever cenários .feature, implementar os passos, rodar localmente ou no GitHub Actions.
- **Casos de uso:** Testar regras de negócio escritas como funções SQL, documentação viva das regras.
- **Benefício para o pos_venda:** Transforma regras do pós-venda (valor total = parcela + multa + juros, faixas de atraso) em funções testadas por cenários legíveis pelo negócio.
- **Nota Free Edition:** Usa a Statement Execution API e funções do UC, que funcionam no Free Edition.
- **Situação no projeto:** aplicado. Fase 19: regras de negócio como funções do Unity Catalog testadas por cenários (regras/).

### [data-classification-review-app](https://github.com/databricks-solutions/data-classification-review-app) · Qualidade, governança e segurança · ★2 · Free Edition: A confirmar

- **Finalidade:** App que distribui a revisão da classificação automática de dados sensíveis (PII) entre os donos dos dados.
- **Como usar:** Implantar a partir dos artefatos prontos, dar permissões e enviar as colunas para revisão dos stewards.
- **Casos de uso:** Confirmar ou rejeitar colunas marcadas como PII, trilha de revisão por domínio.
- **Benefício para o pos_venda:** Formaliza a revisão das tags class.br_cpf, class.br_rg e class.name que aplicamos na dim_cliente, com o dono do dado aprovando.
- **Nota Free Edition:** Depende do recurso Data Classification do Unity Catalog.
- **Situação no projeto:** adiado. Decisão do usuário: não mascarar dado pessoal, usado na validação. Retomar se a Genie abrir a mais pessoas.

### [dbx-adoption-monitor](https://github.com/databricks-solutions/dbx-adoption-monitor) · Qualidade, governança e segurança · ★1 · Free Edition: Sim

- **Finalidade:** Bundle que inventaria e mede adoção de painéis AI/BI, Genie, Apps, model serving e vector search, com modelo dimensional, metric views e painel.
- **Como usar:** Fazer bundle deploy e rodar o workflow; abrir o painel publicado.
- **Casos de uso:** Medir uso de painéis e Genie por usuário, apps acessadas, retorno do investimento em BI.
- **Benefício para o pos_venda:** Copiar só as metric views de adoção de painéis e Genie para medir o uso na avaliação Databricks × Power BI; separar os eventos das avaliações automáticas da Genie, que são a maioria.
- **Nota Free Edition:** system.access.audit é legível neste workspace (7 dias: 71 eventos de painéis, 1.421 da Genie, 21 de apps).
- **Situação no projeto:** proposto. Proposta 6 da revisão de 22/11.

### [genierails](https://github.com/databricks-solutions/genierails) · Qualidade, governança e segurança · ★7 · Free Edition: A confirmar

- **Finalidade:** Leva espaços Genie para produção como código: máscaras para cada coluna sensível, testes em dev e liberação de acesso só quando a cobertura é total.
- **Como usar:** Seguir o Get started; a ferramenta gera as políticas e um gate de cobertura bloqueia a liberação.
- **Casos de uso:** Abrir a Genie a usuários de negócio sem expor dados sensíveis.
- **Benefício para o pos_venda:** Caminho seguro para abrir os espaços do pós-venda a mais pessoas: nenhuma coluna com CPF ou RG fica sem máscara.
- **Nota Free Edition:** Usa Terraform, Data Classification e ABAC; mais indicado para workspace pago.
- **Situação no projeto:** adiado. Decisão do usuário: não mascarar dado pessoal, usado na validação. Retomar se a Genie abrir a mais pessoas.

### [uc-declarative-abac](https://github.com/databricks-solutions/uc-declarative-abac) · Qualidade, governança e segurança · ★1 · Free Edition: A confirmar

- **Finalidade:** Define o modelo de controle de acesso por atributos (ABAC) em YAML versionado: máscaras de coluna, filtros de linha e grants por tag.
- **Como usar:** Escrever os YAML, rodar a CLI uc-abac (ou GitHub Action) que compara com o estado atual e aplica só a diferença.
- **Casos de uso:** Mascarar PII por tag, filtros por região ou carteira, governança como código.
- **Benefício para o pos_venda:** Usa as tags de classificação já aplicadas para mascarar CPF e RG para o analista e liberar ao time de cobrança, sem escrever política tabela a tabela.
- **Nota Free Edition:** Depende de ABAC (políticas por tag) disponível no workspace.
- **Situação no projeto:** adiado. Decisão do usuário: não mascarar dado pessoal, usado na validação. Retomar se a Genie abrir a mais pessoas.

### [caspers](https://github.com/databricks-solutions/caspers) · Workshops, demos e coleções · ★71 · Free Edition: A confirmar

- **Finalidade:** Empresa simulada completa (ghost kitchen) com streaming, AI/BI, Genie, Agent Bricks, Apps e Lakebase; uma skill gera a mesma demo para outros domínios.
- **Como usar:** Autenticar o CLI e implantar; usar a branch skill para gerar outro domínio.
- **Casos de uso:** Demo de plataforma de ponta a ponta.
- **Benefício para o pos_venda:** Referência de narrativa de demo e de simulação em streaming para tornar o gerador do pós-venda mais realista.
- **Nota Free Edition:** Cria catálogos, streams, agentes e apps; consome bastante cota.

## Relevância Baixa (73)

### [agent-control-plane](https://github.com/databricks-solutions/agent-control-plane) · Agentes e IA generativa · ★13 · Free Edition: A confirmar

- **Finalidade:** App de governança e observabilidade de agentes, endpoints e uso do Unity Gateway entre workspaces.
- **Como usar:** Seguir o Quick Start e os pré-requisitos.
- **Casos de uso:** Inventário e custo de agentes em produção.
- **Benefício para o pos_venda:** Não se aplica sem agentes em produção.

### [agent-monitoring-demo-app](https://github.com/databricks-solutions/agent-monitoring-demo-app) · Agentes e IA generativa · ★16 · Free Edition: A confirmar

- **Finalidade:** Template de agente com chat em Databricks Apps e monitoramento por MLflow 3.
- **Como usar:** Seguir o Quick Start e implantar.
- **Casos de uso:** Começar um agente com tracing desde o início.
- **Benefício para o pos_venda:** Base para um agente do pós-venda com observabilidade.

### [agentbricks-utilities](https://github.com/databricks-solutions/agentbricks-utilities) · Agentes e IA generativa · ★0 · Free Edition: A confirmar

- **Finalidade:** Utilitários que estendem Agent Bricks e AI Functions para cobrir lacunas do produto.
- **Como usar:** Instalar e usar o utilitário desejado.
- **Casos de uso:** Melhorias de Agent Bricks em POCs.
- **Benefício para o pos_venda:** Pontual.

### [agentic-customer-support](https://github.com/databricks-solutions/agentic-customer-support) · Agentes e IA generativa · ★12 · Free Edition: A confirmar

- **Finalidade:** Sistema multiagente de atendimento (telecom) com supervisor, vector search, ferramentas e monitoramento.
- **Como usar:** Configurar o ambiente e seguir geração de dados e deploy.
- **Casos de uso:** Copiloto de atendente, respostas com dados estruturados e documentos.
- **Benefício para o pos_venda:** Modelo para um copiloto de atendimento de pós-venda que consulta pendências e políticas.

### [agentops-stacks](https://github.com/databricks-solutions/agentops-stacks) · Agentes e IA generativa · ★7 · Free Edition: A confirmar

- **Finalidade:** Template de bundle e plugin para projetos multiagente LangGraph em produção (dev, staging, prod, CI/CD, avaliação).
- **Como usar:** Gerar o projeto pela CLI ou pelo assistente de código.
- **Casos de uso:** Padronizar projetos de agentes.
- **Benefício para o pos_venda:** Só se o pós-venda ganhar agentes próprios.

### [agents-with-mcp-on-databricks-apps](https://github.com/databricks-solutions/agents-with-mcp-on-databricks-apps) · Agentes e IA generativa · ★6 · Free Edition: A confirmar

- **Finalidade:** Laboratório de agentes com LangGraph, funções do UC, MCP, Unity AI Gateway e memória gerenciada.
- **Como usar:** Clonar no workspace e seguir os labs 1 a 4.
- **Casos de uso:** Aprender a construir agentes governados.
- **Benefício para o pos_venda:** Aprendizado para uma eventual camada de agentes sobre o pós-venda.

### [ai-governance](https://github.com/databricks-solutions/ai-governance) · Agentes e IA generativa · ★5 · Free Edition: A confirmar

- **Finalidade:** Workshop do Unity AI Gateway (escolha, custo e controle de modelos, ferramentas e agentes) como App.
- **Como usar:** Implantar o bundle e conduzir o workshop.
- **Casos de uso:** Governança de IA corporativa.
- **Benefício para o pos_venda:** Não se aplica agora.

### [custom-mcp-databricks-app](https://github.com/databricks-solutions/custom-mcp-databricks-app) · Agentes e IA generativa · ★30 · Free Edition: A confirmar

- **Finalidade:** Servidor MCP próprio hospedado em Databricks Apps, com prompts e ferramentas.
- **Como usar:** Adicionar prompts em markdown e ferramentas em Python; implantar e registrar no Claude.
- **Casos de uso:** Dar a assistentes de código acesso governado ao workspace.
- **Benefício para o pos_venda:** Poderia expor ferramentas do pós-venda (consultar pendência, rodar a carga) para assistentes.

### [databricks-agent-foundry](https://github.com/databricks-solutions/databricks-agent-foundry) · Agentes e IA generativa · ★2 · Free Edition: A confirmar

- **Finalidade:** Blocos e contrato para equipes construírem apps e agentes iguais entre dev, staging e prod.
- **Como usar:** O time de plataforma faz fork; os times de aplicação geram repos com agent-foundry init.
- **Casos de uso:** Governança de vários times de agentes.
- **Benefício para o pos_venda:** Não se aplica ao escopo atual.

### [databricks-bot-service](https://github.com/databricks-solutions/databricks-bot-service) · Agentes e IA generativa · ★1 · Free Edition: A confirmar

- **Finalidade:** Exemplo de bot do Microsoft Teams ligado a um endpoint de agente.
- **Como usar:** Configurar o bot e o endpoint.
- **Casos de uso:** Levar agentes para o Teams.
- **Benefício para o pos_venda:** Permitiria ao CFO perguntar pelo Teams, se houver um agente sobre a Genie.

### [databricks-genai-app-template](https://github.com/databricks-solutions/databricks-genai-app-template) · Agentes e IA generativa · ★5 · Free Edition: A confirmar

- **Finalidade:** Template de app de chat (React + FastAPI) para agentes, com histórico opcional em Lakebase.
- **Como usar:** Configurar config/app.json com o endpoint do agente e implantar.
- **Casos de uso:** Front-end de agente pronto.
- **Benefício para o pos_venda:** Front-end se um agente do pós-venda for criado.

### [hospital-control-tower-agentic-nba](https://github.com/databricks-solutions/hospital-control-tower-agentic-nba) · Agentes e IA generativa · ★0 · Free Edition: A confirmar

- **Finalidade:** Apesar do nome, o README descreve uma plataforma de inteligência de investimentos: agente conversacional para gestores de portfólio que consulta dados e políticas.
- **Como usar:** Setup com um comando ou via Git folder.
- **Casos de uso:** Copiloto para executivos de finanças com dados e documentos.
- **Benefício para o pos_venda:** Inspiração para um assistente do CFO que junte a Genie com documentos de política de cobrança.

### [mcp-workshop](https://github.com/databricks-solutions/mcp-workshop) · Agentes e IA generativa · ★2 · Free Edition: A confirmar

- **Finalidade:** Workshop de MCP: servidores gerenciados, externos, próprios e integração com IDE.
- **Como usar:** Rodar o setup interativo que cria o ambiente do participante.
- **Casos de uso:** Aprender MCP no Databricks.
- **Benefício para o pos_venda:** Aprendizado.

### [prompt-playground](https://github.com/databricks-solutions/prompt-playground) · Agentes e IA generativa · ★1 · Free Edition: A confirmar

- **Finalidade:** App sem código para testar prompts do Prompt Registry contra endpoints de modelo.
- **Como usar:** Implantar com o bundle e dar permissões ao service principal.
- **Casos de uso:** Iterar prompts com o negócio.
- **Benefício para o pos_venda:** Não se aplica agora.

### [aibi-dashboards-external-embedding](https://github.com/databricks-solutions/aibi-dashboards-external-embedding) · Apps e ferramentas de app · ★9 · Free Edition: A confirmar

- **Finalidade:** Template para embutir painéis AI/BI em aplicação externa com login e segurança por linha.
- **Como usar:** Configurar o .env, o backend Flask (gera token) e o frontend React.
- **Casos de uso:** Painéis para corretores ou parceiros dentro do portal deles.
- **Benefício para o pos_venda:** Permitiria mostrar a cada corretor só as pendências dele num portal externo.
- **Nota Free Edition:** Embedding externo depende de configuração do workspace.

### [apx](https://github.com/databricks-solutions/apx) · Apps e ferramentas de app · ★93 · Free Edition: A confirmar

- **Finalidade:** Toolkit (CLI em Rust) para criar, desenvolver e implantar Databricks Apps com FastAPI e React.
- **Como usar:** Seguir o quickstart do apx para gerar e rodar o projeto.
- **Casos de uso:** Apps full-stack com tipagem e recarga rápida.
- **Benefício para o pos_venda:** Opção para uma app própria do pós-venda.

### [brickhouse-brands-demo](https://github.com/databricks-solutions/brickhouse-brands-demo) · Apps e ferramentas de app · ★24 · Free Edition: A confirmar

- **Finalidade:** Demo de gestão de estoque com React, FastAPI e Lakebase.
- **Como usar:** Autenticar o CLI, configurar e implantar.
- **Casos de uso:** Exemplo de app operacional completa.
- **Benefício para o pos_venda:** Referência de app operacional, sem ganho direto.

### [claude-databricks-app-template](https://github.com/databricks-solutions/claude-databricks-app-template) · Apps e ferramentas de app · ★66 · Free Edition: A confirmar

- **Finalidade:** Template de App FastAPI + React com fluxo /dba no Claude Code, da ideia ao deploy.
- **Como usar:** Usar como template no GitHub e rodar /dba.
- **Casos de uso:** Criar apps com assistente de código.
- **Benefício para o pos_venda:** Opção para criar rapidamente uma app do pós-venda.

### [databricks-api-explorer](https://github.com/databricks-solutions/databricks-api-explorer) · Apps e ferramentas de app · ★7 · Free Edition: Sim

- **Finalidade:** Navegador interativo das APIs REST do Databricks (workspace e conta), com formulários e execução de SQL.
- **Como usar:** Rodar localmente com o perfil do CLI ou implantar como App.
- **Casos de uso:** Explorar endpoints antes de automatizar.
- **Benefício para o pos_venda:** Ajuda a explorar APIs pouco documentadas que usamos (domínios, knowledge pages, tag policies).
- **Nota Free Edition:** Roda localmente com o perfil do CLI.

### [databricks-apps-cookbook](https://github.com/databricks-solutions/databricks-apps-cookbook) · Apps e ferramentas de app · ★186 · Free Edition: A confirmar

- **Finalidade:** Receitas prontas para apps Dash, Streamlit, Reflex e FastAPI no Databricks Apps (ler e gravar tabelas, chamar modelos, disparar jobs).
- **Como usar:** Ver a receita no site apps-cookbook.dev e copiar o trecho para a sua app.
- **Casos de uso:** App de tratativa com gravação, formulários, gatilho de workflow.
- **Benefício para o pos_venda:** Atalho se o pós-venda precisar de uma tela operacional (ex.: registrar tratativa de pendência).

### [databricks-apps-examples](https://github.com/databricks-solutions/databricks-apps-examples) · Apps e ferramentas de app · ★27 · Free Edition: A confirmar

- **Finalidade:** Exemplos de apps feitos pelo campo (shell, write-back, autenticação, vector search).
- **Como usar:** Escolher a pasta do exemplo e seguir o README.
- **Casos de uso:** Inspiração para apps com gravação e autenticação.
- **Benefício para o pos_venda:** Mesmo benefício do cookbook, com exemplos de write-back.

### [microbricks](https://github.com/databricks-solutions/microbricks) · Apps e ferramentas de app · ★4 · Free Edition: A confirmar

- **Finalidade:** Blueprint de microsserviços em Databricks Apps com Lakebase por serviço, OBO e CI/CD.
- **Como usar:** Seguir o quickstart e os workflows de GitHub Actions.
- **Casos de uso:** Arquitetura de microsserviços na plataforma.
- **Benefício para o pos_venda:** Excesso para o escopo atual.

### [custom-mlflow-review-app](https://github.com/databricks-solutions/custom-mlflow-review-app) · Avaliação, MLOps e modelos · ★11 · Free Edition: A confirmar

- **Finalidade:** Template de app de revisão do MLflow customizada para especialistas rotularem traces.
- **Como usar:** Usar o comando /review-app no Claude Code ou seguir o guia.
- **Casos de uso:** Coleta de rótulos de especialistas.
- **Benefício para o pos_venda:** Só com agentes no projeto.

### [databricks-ab-testing](https://github.com/databricks-solutions/databricks-ab-testing) · Avaliação, MLOps e modelos · ★2 · Free Edition: A confirmar

- **Finalidade:** Framework de testes A/B com atribuição determinística e avaliação estatística para modelos, agentes e apps.
- **Como usar:** Seguir o guia de deploy e a documentação de arquitetura.
- **Casos de uso:** Comparar versões de modelo ou de agente.
- **Benefício para o pos_venda:** Poderia testar réguas de cobrança alternativas, se virarem um serviço.

### [judge-builder](https://github.com/databricks-solutions/judge-builder) · Avaliação, MLOps e modelos · ★1 · Free Edition: A confirmar

- **Finalidade:** Plataforma para criar e alinhar juízes LLM com feedback humano.
- **Como usar:** Criar o juiz, convidar especialistas e otimizar.
- **Casos de uso:** Avaliação automática alinhada ao negócio.
- **Benefício para o pos_venda:** Só com agentes no projeto.

### [mlflow-demo](https://github.com/databricks-solutions/mlflow-demo) · Avaliação, MLOps e modelos · ★5 · Free Edition: A confirmar

- **Finalidade:** Demo dos recursos GenAI do MLflow 3 (avaliação, monitoramento, melhoria de qualidade).
- **Como usar:** Instalação automatizada como App com notebooks guiados.
- **Casos de uso:** Aprender avaliação de apps de IA.
- **Benefício para o pos_venda:** Aprendizado.

### [model-landscape](https://github.com/databricks-solutions/model-landscape) · Avaliação, MLOps e modelos · ★1 · Free Edition: A confirmar

- **Finalidade:** Observabilidade de modelos nativa (SDK mlflow-lens e App de drift sobre tabelas de inferência).
- **Como usar:** Seguir o deploy rápido da documentação.
- **Casos de uso:** Drift e degradação de modelos em produção.
- **Benefício para o pos_venda:** Útil depois que existir um modelo de propensão.

### [vibescaler](https://github.com/databricks-solutions/vibescaler) · Avaliação, MLOps e modelos · ★7 · Free Edition: A confirmar

- **Finalidade:** App em que especialistas definem o que é boa resposta e o sistema vira um avaliador automático.
- **Como usar:** Implantar como App e conduzir a sessão com os especialistas.
- **Casos de uso:** Qualidade de agentes por especialistas.
- **Benefício para o pos_venda:** Só com agentes no projeto.

### [agentic-starter-journey](https://github.com/databricks-solutions/agentic-starter-journey) · Ferramentas para coding agents · ★0 · Free Edition: A confirmar

- **Finalidade:** Runbooks para agentes de código, da conta vazia ao projeto implantado.
- **Como usar:** Apontar o agente para a página do runbook.
- **Casos de uso:** Onboarding automatizado.
- **Benefício para o pos_venda:** Pouco ganho; o projeto já está implantado.

### [consort](https://github.com/databricks-solutions/consort) · Ferramentas para coding agents · ★38 · Free Edition: A confirmar

- **Finalidade:** Conjunto de agentes por papel, orientado a especificação e testes, com branches reais de Lakebase.
- **Como usar:** Seguir o quick start e instalar o kit.
- **Casos de uso:** Disciplina de engenharia em código gerado por IA.
- **Benefício para o pos_venda:** Não necessário.

### [databricks-exec-code-mcp](https://github.com/databricks-solutions/databricks-exec-code-mcp) · Ferramentas para coding agents · ★14 · Free Edition: Não

- **Finalidade:** Servidor MCP que roda código em clusters e cria bundles a partir de prompts.
- **Como usar:** Configurar o MCP no assistente.
- **Casos de uso:** Testar código no cluster pelo assistente.
- **Benefício para o pos_venda:** O Free Edition não tem clusters clássicos.
- **Nota Free Edition:** Usa a Command Execution API em clusters clássicos.

### [genie-code-skills-demo](https://github.com/databricks-solutions/genie-code-skills-demo) · Ferramentas para coding agents · ★15 · Free Edition: A confirmar

- **Finalidade:** Skills, instruções e MCP do Genie Code para impor padrões de engenharia de dados.
- **Como usar:** Instalar as skills, configurar MCP opcional e instruções.
- **Casos de uso:** Padronizar código gerado por IA no workspace.
- **Benefício para o pos_venda:** Permitiria codificar os padrões do pos_venda (nomes, DQX, tags) para o Genie Code seguir.

### [solution-builder](https://github.com/databricks-solutions/solution-builder) · Ferramentas para coding agents · ★63 · Free Edition: A confirmar

- **Finalidade:** App e CLI em que um agente constrói soluções a partir de blueprints validados (inclui serviços financeiros).
- **Como usar:** Rodar a app completa ou a skill de CLI.
- **Casos de uso:** Demos e POCs rápidos.
- **Benefício para o pos_venda:** Alternativa para gerar demos de outros casos de seguros.

### [vibe-coding-workshop-app](https://github.com/databricks-solutions/vibe-coding-workshop-app) · Ferramentas para coding agents · ★5 · Free Edition: Sim

- **Finalidade:** App de workshop de vibe coding que roda no Free Edition.
- **Como usar:** Instalar e seguir os comandos do README.
- **Casos de uso:** Treinar o time em desenvolvimento assistido.
- **Benefício para o pos_venda:** Aprendizado.
- **Nota Free Edition:** O README afirma que roda no Free Edition.

### [vibe-coding-workshop-template](https://github.com/databricks-solutions/vibe-coding-workshop-template) · Ferramentas para coding agents · ★7 · Free Edition: A confirmar

- **Finalidade:** Template de produto de dados com 77 skills: medallion, camada semântica, Genie, ML e agentes, com Lakebase e AppKit.
- **Como usar:** Clonar o template e escolher o ponto de partida.
- **Casos de uso:** Construir produtos de dados com assistente.
- **Benefício para o pos_venda:** Boas práticas parecidas com o que já fizemos; útil para comparar.

### [aibi-genie-enablement-lab](https://github.com/databricks-solutions/aibi-genie-enablement-lab) · Genie e camada semântica · ★1 · Free Edition: A confirmar

- **Finalidade:** Laboratório para público não técnico que mostra por que definir métricas uma vez (metric views) evita números divergentes.
- **Como usar:** Instrutor clona o repo, roda setup/00_instructor_setup; cada aluno segue os notebooks em sua pasta.
- **Casos de uso:** Treinamento de analistas de negócio em AI/BI e Genie, narrativa de 'uma métrica, uma verdade'.
- **Benefício para o pos_venda:** Roteiro pronto para treinar a equipe financeira que vai usar a Genie e os painéis do pós-venda.

### [dbx-unifiedchat](https://github.com/databricks-solutions/dbx-unifiedchat) · Genie e camada semântica · ★16 · Free Edition: A confirmar

- **Finalidade:** Sistema multiagente (LangGraph, Genie, Lakebase) que responde perguntas que cruzam vários domínios e espaços Genie.
- **Como usar:** Seguir o Quick Start, registrar os espaços Genie e implantar a App de chat.
- **Casos de uso:** Uma única conversa sobre dados de várias áreas, síntese de respostas de vários espaços.
- **Benefício para o pos_venda:** Poderia unir os espaços Analista e Diretoria e a qualidade de dados num chat único; vale mais quando houver outros domínios além do pós-venda.

### [genie-a2a-agent](https://github.com/databricks-solutions/genie-a2a-agent) · Genie e camada semântica · ★0 · Free Edition: A confirmar

- **Finalidade:** Servidor do protocolo A2A (agente para agente) que expõe um espaço Genie como agente.
- **Como usar:** Configurar o ID do espaço, rodar deploy.sh e descobrir o agente pelo Agent Card.
- **Casos de uso:** Integrar a Genie em ecossistemas multiagente de outros fornecedores.
- **Benefício para o pos_venda:** Permitiria que um agente corporativo externo consultasse o espaço do pós-venda; hoje não há esse cenário.

### [genie-api-cache-queue](https://github.com/databricks-solutions/genie-api-cache-queue) · Genie e camada semântica · ★16 · Free Edition: A confirmar

- **Finalidade:** Camada de cache semântico, fila com retentativa e roteamento na frente da API da Genie, implantada como App.
- **Como usar:** Deploy com o bundle, criar um gateway por espaço Genie e trocar a URL base dos clientes.
- **Casos de uso:** Apps com muitos usuários perguntando à Genie, picos de uso, roteamento entre vários espaços.
- **Benefício para o pos_venda:** Só ajuda se a Genie do pós-venda for embutida numa app com muitos usuários; no uso atual (CFO e analista) não é necessário.

### [genie-visualization-interface](https://github.com/databricks-solutions/genie-visualization-interface) · Genie e camada semântica · ★2 · Free Edition: A confirmar

- **Finalidade:** Interface de conversa com a Genie (Angular + Node) que recomenda gráficos e mapas.
- **Como usar:** Configurar app.yaml com o espaço Genie e implantar como App.
- **Casos de uso:** Front-end próprio para a Genie com gráficos automáticos.
- **Benefício para o pos_venda:** Opcional: a interface nativa da Genie já atende o CFO e o analista.

### [realtime-apps-feature-demo](https://github.com/databricks-solutions/realtime-apps-feature-demo) · Ingestão e streaming · ★1 · Free Edition: Não

- **Finalidade:** Telemetria de rede elétrica com Structured Streaming Real-Time Mode, sink nativo para Lakebase e App com latência abaixo de 500 ms.
- **Como usar:** Configurar perfil, catálogo e segredos; fazer deploy e rodar.
- **Casos de uso:** Painéis operacionais em tempo real.
- **Benefício para o pos_venda:** Padrão para uma visão de pagamentos em tempo real, fora do alcance do Free Edition.
- **Nota Free Edition:** Usa computação clássica para o Real-Time Mode.

### [salesforce-zerobus](https://github.com/databricks-solutions/salesforce-zerobus) · Ingestão e streaming · ★6 · Free Edition: A confirmar

- **Finalidade:** Conector de CDC do Salesforce para Delta via Pub/Sub API e Zerobus (Python e Go).
- **Como usar:** Entrar em python/ ou go_salesforce_zerobus/, configurar e fazer bundle deploy.
- **Casos de uso:** Trazer alterações do CRM quase em tempo real.
- **Benefício para o pos_venda:** Só se o CRM do pós-venda for Salesforce.

### [spark-jdbc-ingestor](https://github.com/databricks-solutions/spark-jdbc-ingestor) · Ingestão e streaming · ★2 · Free Edition: A confirmar

- **Finalidade:** Biblioteca para ingestão JDBC simples e eficiente, com filtros e ingestão parcial.
- **Como usar:** Instalar via pip, instanciar JdbcIngestor com URL, usuário e driver.
- **Casos de uso:** Ingestão de bancos SQL sem conector gerenciado.
- **Benefício para o pos_venda:** Alternativa simples para ingerir o banco de origem quando houver um.

### [zerobus-ingest-examples](https://github.com/databricks-solutions/zerobus-ingest-examples) · Ingestão e streaming · ★6 · Free Edition: A confirmar

- **Finalidade:** Exemplos e demos do Zerobus Ingest, API de ingestão por push direto para tabelas Delta.
- **Como usar:** Escolher uma demo (REST ou gRPC) e seguir o README dela.
- **Casos de uso:** Eventos em tempo real de sistemas externos, telemetria, logs.
- **Benefício para o pos_venda:** Em produção, eventos de pagamento do gateway poderiam cair direto na bronze, sem arquivos intermediários.

### [lakebase-cicd-blueprint](https://github.com/databricks-solutions/lakebase-cicd-blueprint) · Lakebase (Postgres) · ★0 · Free Edition: A confirmar

- **Finalidade:** CI/CD de Lakebase: tabela sincronizada, roles, grants, índices e view de consumo, por bundle ou Terraform + Liquibase.
- **Como usar:** Seguir o caminho com bundles e o passo de roles e tabelas de origem.
- **Casos de uso:** Esteira de deploy de banco operacional.
- **Benefício para o pos_venda:** Só se o pos_venda ganhar um banco operacional próprio.

### [lakebase-cookbook](https://github.com/databricks-solutions/lakebase-cookbook) · Lakebase (Postgres) · ★1 · Free Edition: A confirmar

- **Finalidade:** Receitas e guias de Lakebase (agentes, apps, dados, experiência de desenvolvimento).
- **Como usar:** Navegar no site lakebase-cookbook.com e implantar o exemplo pelo bundle dele.
- **Casos de uso:** Padrões de app com Postgres gerenciado.
- **Benefício para o pos_venda:** Consulta útil para manter o Lakebase do DQX Studio e para uma futura app operacional.

### [lakebase-fastapi-app](https://github.com/databricks-solutions/lakebase-fastapi-app) · Lakebase (Postgres) · ★44 · Free Edition: A confirmar

- **Finalidade:** API FastAPI que serve dados de uma tabela sincronizada no Lakebase, com OAuth e pool de conexões.
- **Como usar:** Configurar as variáveis do bundle e implantar como App.
- **Casos de uso:** API de consulta para canais digitais, URA ou parceiros.
- **Benefício para o pos_venda:** Base para uma API de consulta de pendência por apólice (corretor, portal do cliente).

### [lakebase-for-ai-developers](https://github.com/databricks-solutions/lakebase-for-ai-developers) · Lakebase (Postgres) · ★0 · Free Edition: A confirmar

- **Finalidade:** Copiloto multiagente de planejamento de supply chain com estado no Lakebase, pgvector e aprovação humana.
- **Como usar:** Configurar com Claude Code e implantar como App.
- **Casos de uso:** Agentes com memória durável e aprovação humana.
- **Benefício para o pos_venda:** Referência se for criar um agente de tratativa de pendências com aprovação.

### [lakebase-online-ml](https://github.com/databricks-solutions/lakebase-online-ml) · Lakebase (Postgres) · ★1 · Free Edition: A confirmar

- **Finalidade:** App de varejo que usa Lakebase como feature store online para servir modelos com baixa latência.
- **Como usar:** Rodar com apx em modo dev e implantar.
- **Casos de uso:** Scoring online com features em Postgres.
- **Benefício para o pos_venda:** Padrão para servir um futuro score de propensão de pagamento em tempo real.

### [lakebase-poc-accelerator](https://github.com/databricks-solutions/lakebase-poc-accelerator) · Lakebase (Postgres) · ★3 · Free Edition: A confirmar

- **Finalidade:** App para POC de OLTP/reverse ETL no Lakebase: dimensionamento, testes de concorrência (pgbench) e otimização de índices.
- **Como usar:** Implantar a App e seguir Deploy, Test e Optimize.
- **Casos de uso:** Provar desempenho de Lakebase para uma carga transacional.
- **Benefício para o pos_venda:** Não necessário hoje.

### [lakebase-solutions](https://github.com/databricks-solutions/lakebase-solutions) · Lakebase (Postgres) · ★0 · Free Edition: A confirmar

- **Finalidade:** Sobe um workshop completo de Lakebase com módulos opcionais numa única execução, e derruba depois.
- **Como usar:** Rodar pelo notebook ou com um coding agent.
- **Casos de uso:** Demonstração de Lakebase integrado à plataforma.
- **Benefício para o pos_venda:** Aprendizado.

### [lakebase-workshop](https://github.com/databricks-solutions/lakebase-workshop) · Lakebase (Postgres) · ★3 · Free Edition: A confirmar

- **Finalidade:** Workshop prático de Lakebase com labs por perfil e console de laboratório.
- **Como usar:** Clonar, rodar o setup e escolher um lab.
- **Casos de uso:** Aprender Lakebase.
- **Benefício para o pos_venda:** Aprendizado; o projeto usa Lakebase apenas pelo DQX Studio.

### [databricks-migrator-with-llm](https://github.com/databricks-solutions/databricks-migrator-with-llm) · Migração · ★2 · Free Edition: A confirmar

- **Finalidade:** App que converte SQL de outros dialetos (Oracle, Teradata, T-SQL...) para Databricks SQL com LLM e valida.
- **Como usar:** Clonar como Git folder e implantar a App.
- **Casos de uso:** Migração de consultas legadas.
- **Benefício para o pos_venda:** Útil se as regras atuais de cobrança estiverem em SQL legado do data warehouse da seguradora.

### [databricks-replicator](https://github.com/databricks-solutions/databricks-replicator) · Migração · ★12 · Free Edition: A confirmar

- **Finalidade:** Replica dados e metadados do UC entre ambientes (Delta Sharing, deep clone, Auto Loader), com reconciliação.
- **Como usar:** Configurar as operações de backup, replicação e reconciliação.
- **Casos de uso:** DR, migração, data mesh multinuvem.
- **Benefício para o pos_venda:** Mesmo cenário de saída do Free Edition.

### [lakebridge-workshop](https://github.com/databricks-solutions/lakebridge-workshop) · Migração · ★0 · Free Edition: A confirmar

- **Finalidade:** Workshop do Lakebridge (Analyzer, Transpile, Reconcile) para migrar DW e ETL.
- **Como usar:** Seguir os cenários Synapse, Reconcile e DataStage.
- **Casos de uso:** Avaliar e converter um DW legado.
- **Benefício para o pos_venda:** Mesmo cenário de migração de legado.

### [powerbi-on-databricks-migration-accelerator](https://github.com/databricks-solutions/powerbi-on-databricks-migration-accelerator) · Migração · ★4 · Free Edition: A confirmar

- **Finalidade:** Reaponta modelos semânticos do Power BI de Snowflake, Redshift, SQL Server etc. para Databricks SQL em massa.
- **Como usar:** Rodar a CLI PowerShell com o arquivo de configuração.
- **Casos de uso:** Migração de relatórios Power BI sem refazer.
- **Benefício para o pos_venda:** Só se a seguradora tiver relatórios Power BI de cobrança em outra fonte.

### [workspace-migration](https://github.com/databricks-solutions/workspace-migration) · Migração · ★0 · Free Edition: A confirmar

- **Finalidade:** Bundle que migra objetos do Unity Catalog e do Hive Metastore entre workspaces (catálogos, schemas, grants, tabelas, views).
- **Como usar:** Preencher config.yaml e seguir o fluxo de deploy e operação.
- **Casos de uso:** Consolidação de contas, troca de região.
- **Benefício para o pos_venda:** Útil no dia em que o pos_venda sair do Free Edition para um workspace corporativo.

### [dais-2024-dw-workshop](https://github.com/databricks-solutions/dais-2024-dw-workshop) · Pipelines e engenharia de dados · ★0 · Free Edition: A confirmar

- **Finalidade:** Implementações do benchmark TPC-DI (integração de dados) em Databricks.
- **Como usar:** Gerar dados e workflows com o setup e executar uma das variantes.
- **Casos de uso:** Referência de cargas com SCD e integração de dados em larga escala.
- **Benefício para o pos_venda:** Referência de modelagem e SCD; não traz ganho direto.

### [livevalidator](https://github.com/databricks-solutions/livevalidator) · Pipelines e engenharia de dados · ★4 · Free Edition: A confirmar

- **Finalidade:** Plataforma que compara tabelas entre bancos diferentes: schema, contagem e diferenças linha a linha.
- **Como usar:** Seguir o Quick Start, cadastrar origem e destino e agendar validações.
- **Casos de uso:** Reconciliação em migrações, conferência origem x lakehouse.
- **Benefício para o pos_venda:** Em produção, conciliaria o sistema de cobrança com a bronze; com dados sintéticos não há origem para comparar.

### [monitoring-declarative-pipeline-refresh-behavior](https://github.com/databricks-solutions/monitoring-declarative-pipeline-refresh-behavior) · Pipelines e engenharia de dados · ★2 · Free Edition: A confirmar

- **Finalidade:** Kit de observabilidade do refresh de materialized views em Declarative Pipelines (incremental ou recompute, custo).
- **Como usar:** Implantar o bundle, rodar o job e abrir o painel SQL.
- **Casos de uso:** Entender por que uma MV recomputa tudo, custo por refresh.
- **Benefício para o pos_venda:** Só útil se o pos_venda migrar para SDP com materialized views.

### [sdp-explorer](https://github.com/databricks-solutions/sdp-explorer) · Pipelines e engenharia de dados · ★3 · Free Edition: A confirmar

- **Finalidade:** App didática com cartões animados de cada recurso do Spark Declarative Pipelines.
- **Como usar:** Implantar a App ou abrir a versão em arquivo único.
- **Casos de uso:** Aprender SDP visualmente, ensinar o time.
- **Benefício para o pos_venda:** Material de estudo se for adotar SDP.

### [sdp-rewind-replay](https://github.com/databricks-solutions/sdp-rewind-replay) · Pipelines e engenharia de dados · ★1 · Free Edition: A confirmar

- **Finalidade:** Demonstra a API Rewind (time travel de streaming) para corrigir um pipeline com bug sem full refresh.
- **Como usar:** Implantar o bundle e seguir o cenário de pagamentos inflados em 10x.
- **Casos de uso:** Recuperação de incidentes em pipelines de streaming.
- **Benefício para o pos_venda:** Padrão interessante para os incidentes simulados no projeto, caso a carga vire SDP em streaming.

### [databricks-waf](https://github.com/databricks-solutions/databricks-waf) · Plataforma, infraestrutura e custos · ★4 · Free Edition: A confirmar

- **Finalidade:** App que avalia workspace ou conta contra os 7 pilares do Well-Architected Framework e gera planos de melhoria com evidências.
- **Como usar:** Clonar o release, vincular recursos, instalar e rodar a primeira avaliação.
- **Casos de uso:** Revisão de arquitetura com evidências.
- **Benefício para o pos_venda:** Checklist de prontidão para levar o pós-venda à produção.
- **Situação no projeto:** adiado. App com Lakebase; serve para preparar a ida para produção.

### [platform-deployment-kit](https://github.com/databricks-solutions/platform-deployment-kit) · Plataforma, infraestrutura e custos · ★4 · Free Edition: Não

- **Finalidade:** Gerador web de projetos Terraform para workspaces em AWS, Azure e GCP.
- **Como usar:** Escolher a nuvem, preencher, baixar o ZIP e aplicar.
- **Casos de uso:** Provisionar workspaces.
- **Benefício para o pos_venda:** Só quando o projeto for para um workspace pago.

### [waf-assessment-tool](https://github.com/databricks-solutions/waf-assessment-tool) · Plataforma, infraestrutura e custos · ★0 · Free Edition: Sim

- **Finalidade:** PWA para conduzir avaliações do Well-Architected Framework com clientes.
- **Como usar:** Abrir o app e preencher a avaliação.
- **Casos de uso:** Workshop de arquitetura.
- **Benefício para o pos_venda:** Mesmo benefício, em versão questionário.

### [cybersec-workspace-detection-app](https://github.com/databricks-solutions/cybersec-workspace-detection-app) · Qualidade, governança e segurança · ★13 · Free Edition: A confirmar

- **Finalidade:** 35 detecções de segurança sobre os logs de auditoria (eventos e comportamento), com espaço Genie para investigar.
- **Como usar:** Rodar os notebooks de detecção ou perguntar à Genie de auditoria.
- **Casos de uso:** Monitoramento de acesso suspeito, investigação de incidentes, threat hunting.
- **Benefício para o pos_venda:** Útil em produção para vigiar quem acessa dados de clientes; no Free Edition pessoal o ganho é pequeno.
- **Nota Free Edition:** Depende de system.access.audit.

### [adtech-solutions](https://github.com/databricks-solutions/adtech-solutions) · Workshops, demos e coleções · ★3 · Free Edition: A confirmar

- **Finalidade:** Workshops e arquiteturas de referência para AdTech (data collaboration, AI/BI, agentes, apps e Lakebase).
- **Como usar:** Escolher a série e a sessão.
- **Casos de uso:** Mídia e publicidade.
- **Benefício para o pos_venda:** Pouco aplicável.

### [databricks-blogposts](https://github.com/databricks-solutions/databricks-blogposts) · Workshops, demos e coleções · ★48 · Free Edition: A confirmar

- **Finalidade:** Código dos posts do blog da Databricks, uma pasta por post.
- **Como usar:** Abrir a pasta do post desejado.
- **Casos de uso:** Stored procedures em SQL, gitflow com bundles, framework orientado a configuração, debug de streaming.
- **Benefício para o pos_venda:** Posts de SQL scripting e stored procedures podem simplificar a lógica da carga diária.

### [databricks-workshops](https://github.com/databricks-solutions/databricks-workshops) · Workshops, demos e coleções · ★4 · Free Edition: A confirmar

- **Finalidade:** Workshops com botão Open in Databricks que se instalam no workspace.
- **Como usar:** Clicar em Open in Databricks no README do workshop.
- **Casos de uso:** Workshop de DBSQL e outros.
- **Benefício para o pos_venda:** O dbsql_workshop ajuda a treinar analistas no SQL da gold.

### [databricks_demos_br](https://github.com/databricks-solutions/databricks_demos_br) · Workshops, demos e coleções · ★5 · Free Edition: A confirmar

- **Finalidade:** Demos em português do Data + AI World Tour São Paulo 2025.
- **Como usar:** Abrir a pasta daiwt_sp_2025.
- **Casos de uso:** Material de demonstração em português.
- **Benefício para o pos_venda:** Material pronto em português para apresentações junto com o ROTEIRO do pos_venda.

### [devrel-examples](https://github.com/databricks-solutions/devrel-examples) · Workshops, demos e coleções · ★16 · Free Edition: A confirmar

- **Finalidade:** Notebooks e demos do time de Developer Relations (Foundation Model APIs, Vector Search, MLflow).
- **Como usar:** Importar o notebook desejado.
- **Casos de uso:** Aprender recursos de IA.
- **Benefício para o pos_venda:** Aprendizado.

### [specialist-offerings](https://github.com/databricks-solutions/specialist-offerings) · Workshops, demos e coleções · ★4 · Free Edition: A confirmar

- **Finalidade:** Conteúdo oficial dos Specialist SAs: blueprints de design do UC, DW, engenharia, GenAI e cibersegurança.
- **Como usar:** Navegar pelas pastas por especialidade.
- **Casos de uso:** Métodos e templates de engajamento.
- **Benefício para o pos_venda:** O uc-design-blueprint ajuda a revisar a organização de catálogos e schemas.

### [starter-journey](https://github.com/databricks-solutions/starter-journey) · Workshops, demos e coleções · ★5 · Free Edition: A confirmar

- **Finalidade:** Guia passo a passo para começar no Databricks, da configuração à produção.
- **Como usar:** Ler o site ou rodar localmente.
- **Casos de uso:** Onboarding de equipes.
- **Benefício para o pos_venda:** Aprendizado básico.

## Relevância Nenhuma (51)

### [mason](https://github.com/databricks-solutions/mason) · Agentes e IA generativa · ★4 · Free Edition: A confirmar

- **Finalidade:** App desktop para conversar com modelos via Unity AI Gateway e montar fluxos multimodelo.
- **Como usar:** Instalar no macOS, Windows ou Linux.
- **Casos de uso:** Fluxos agênticos em canvas.
- **Benefício para o pos_venda:** Não se aplica.

### [otel-on-databricks](https://github.com/databricks-solutions/otel-on-databricks) · Agentes e IA generativa · ★0 · Free Edition: A confirmar

- **Finalidade:** Modelos de telecom (Open Telco) e agente de troubleshooting de RAN.
- **Como usar:** Seguir os capítulos em notebooks.
- **Casos de uso:** Operações de telecom.
- **Benefício para o pos_venda:** Não se aplica.

### [realtime-rag-agents-databricks-youcom](https://github.com/databricks-solutions/realtime-rag-agents-databricks-youcom) · Agentes e IA generativa · ★0 · Free Edition: A confirmar

- **Finalidade:** RAG com dados da web em tempo real pela API da You.com.
- **Como usar:** Implantar o bundle e configurar a chave.
- **Casos de uso:** Respostas com notícias e web atual.
- **Benefício para o pos_venda:** Não se aplica.

### [databricks-quest](https://github.com/databricks-solutions/databricks-quest) · Apps e ferramentas de app · ★8 · Free Edition: A confirmar

- **Finalidade:** Gamificação da adoção da plataforma (pontos, missões e ranking a partir das system tables).
- **Como usar:** Rodar python deploy.py.
- **Casos de uso:** Engajar usuários na adoção do Databricks.
- **Benefício para o pos_venda:** Não se aplica.

### [databricks-vision](https://github.com/databricks-solutions/databricks-vision) · Apps e ferramentas de app · ★5 · Free Edition: A confirmar

- **Finalidade:** App de geração, edição, avaliação e busca de imagens.
- **Como usar:** Implantar a App e escolher o modelo de imagem.
- **Casos de uso:** Conteúdo visual gerado por IA.
- **Benefício para o pos_venda:** Não se aplica.

### [youtube-video-intelligence](https://github.com/databricks-solutions/youtube-video-intelligence) · Apps e ferramentas de app · ★3 · Free Edition: A confirmar

- **Finalidade:** Análise de vídeos do YouTube com Gemini, histórico em Lakebase.
- **Como usar:** Escolher prefixo, implantar e abrir a App.
- **Casos de uso:** Análise de mídia.
- **Benefício para o pos_venda:** Não se aplica.

### [ai-runtime-cookbook](https://github.com/databricks-solutions/ai-runtime-cookbook) · Avaliação, MLOps e modelos · ★20 · Free Edition: Não

- **Finalidade:** Receitas de ML em escala no Databricks AI Runtime (Ray, serving).
- **Como usar:** Escolher a receita, o perfil e submeter.
- **Casos de uso:** Treino distribuído.
- **Benefício para o pos_venda:** Não se aplica.
- **Nota Free Edition:** Exige GPU e AI Runtime.

### [ai-runtime-rft-cookbook](https://github.com/databricks-solutions/ai-runtime-rft-cookbook) · Avaliação, MLOps e modelos · ★1 · Free Edition: Não

- **Finalidade:** Treino de agentes por reforço (GRPO) no AI Runtime.
- **Como usar:** Seguir o quickstart de matemática.
- **Casos de uso:** Fine-tuning de agentes.
- **Benefício para o pos_venda:** Não se aplica.
- **Nota Free Edition:** Exige GPUs H100.

### [cspray](https://github.com/databricks-solutions/cspray) · Avaliação, MLOps e modelos · ★4 · Free Edition: A confirmar

- **Finalidade:** Análise distribuída de single-cell RNA com PySpark.
- **Como usar:** Instalar via pip.
- **Casos de uso:** Biologia.
- **Benefício para o pos_venda:** Não se aplica.

### [multi-region-model-serving](https://github.com/databricks-solutions/multi-region-model-serving) · Avaliação, MLOps e modelos · ★0 · Free Edition: Não

- **Finalidade:** Serving de modelo de fraude em várias regiões com Delta Sharing.
- **Como usar:** Seguir o passo a passo do blog.
- **Casos de uso:** Inferência de baixa latência multirregião.
- **Benefício para o pos_venda:** Não se aplica.

### [proteinsearch](https://github.com/databricks-solutions/proteinsearch) · Avaliação, MLOps e modelos · ★3 · Free Edition: Não

- **Finalidade:** Embeddings e busca de sequências de proteínas em escala.
- **Como usar:** Configurar e rodar as etapas do pipeline.
- **Casos de uso:** Bioinformática.
- **Benefício para o pos_venda:** Não se aplica.

### [grafana-lakehouse-rt-quickstart](https://github.com/databricks-solutions/grafana-lakehouse-rt-quickstart) · BI externo (Power BI, Grafana) · ★0 · Free Edition: A confirmar

- **Finalidade:** Grafana consultando warehouses SQL, incluindo Lakehouse//RT.
- **Como usar:** Subir com Docker Compose e configurar o token.
- **Casos de uso:** Painéis operacionais em Grafana.
- **Benefício para o pos_venda:** Não se aplica.

### [partner-ai-dev-kit](https://github.com/databricks-solutions/partner-ai-dev-kit) · Ferramentas para coding agents · ★5 · Free Edition: A confirmar

- **Finalidade:** Skills para parceiros ISV criarem conectores conforme o Partner Well-Architected Framework.
- **Como usar:** Instalar as skills no assistente.
- **Casos de uso:** Conectores de parceiros.
- **Benefício para o pos_venda:** Não se aplica.

### [genie-geo-chat](https://github.com/databricks-solutions/genie-geo-chat) · Genie e camada semântica · ★4 · Free Edition: A confirmar

- **Finalidade:** App com globo 3D e mapa 2D integrados à Genie para perguntar sobre regiões desenhadas no mapa.
- **Como usar:** Importar o repo, rodar o notebook de setup e implantar a App.
- **Casos de uso:** Análise de ativos geográficos (torres, lojas, sites).
- **Benefício para o pos_venda:** Pouco aplicável; só faria sentido para visualizar pontos de venda por região.

### [lakeflow-connect-terraform](https://github.com/databricks-solutions/lakeflow-connect-terraform) · Ingestão e streaming · ★6 · Free Edition: Não

- **Finalidade:** Terraform guiado por YAML para implantar conectores de banco do Lakeflow Connect em escala.
- **Como usar:** Preencher o YAML de configuração e aplicar o Terraform.
- **Casos de uso:** Dezenas de conectores CDC padronizados.
- **Benefício para o pos_venda:** Não se aplica ao Free Edition.

### [lakeflow-tapworks](https://github.com/databricks-solutions/lakeflow-tapworks) · Ingestão e streaming · ★1 · Free Edition: Não

- **Finalidade:** Gera bundles e balanceia carga de tabelas entre pipelines de conectores gerenciados do Lakeflow Connect.
- **Como usar:** Descrever tabelas e grupos, rodar a CLI ou o notebook.
- **Casos de uso:** Milhares de tabelas em conectores gerenciados.
- **Benefício para o pos_venda:** Não se aplica.

### [latency-benchmarks](https://github.com/databricks-solutions/latency-benchmarks) · Ingestão e streaming · ★2 · Free Edition: Não

- **Finalidade:** Benchmarks de latência entre Spark Real-Time Mode e Apache Flink lendo e escrevendo Kafka.
- **Como usar:** Configurar Kafka e gerador, rodar as consultas A, B e C.
- **Casos de uso:** Escolha de motor de streaming de baixa latência.
- **Benefício para o pos_venda:** Não se aplica.

### [streaming-binary-ingest-patterns](https://github.com/databricks-solutions/streaming-binary-ingest-patterns) · Ingestão e streaming · ★0 · Free Edition: A confirmar

- **Finalidade:** Padrão para ingerir arquivos binários grandes (ex.: MDF4) em Delta sem estourar memória.
- **Como usar:** Abrir o notebook de exemplo e trocar o parser.
- **Casos de uso:** Telemetria automotiva, tick data, logs de sensores.
- **Benefício para o pos_venda:** Não se aplica.

### [zerobus-otel-collector-demo](https://github.com/databricks-solutions/zerobus-otel-collector-demo) · Ingestão e streaming · ★0 · Free Edition: A confirmar

- **Finalidade:** Databricks como backend de observabilidade de Kubernetes (OpenTelemetry via Zerobus, SDP e App com Genie).
- **Como usar:** Provisionar a ingestão e implantar pipelines e App.
- **Casos de uso:** Logs, métricas e traces de clusters Kubernetes.
- **Benefício para o pos_venda:** Não se aplica.

### [fastpgcache](https://github.com/databricks-solutions/fastpgcache) · Lakebase (Postgres) · ★1 · Free Edition: A confirmar

- **Finalidade:** Biblioteca de cache estilo Redis sobre tabelas UNLOGGED do Postgres.
- **Como usar:** Instalar e usar a API set/get com TTL.
- **Casos de uso:** Cache de aplicação sem Redis.
- **Benefício para o pos_venda:** Não se aplica.

### [lakebase-express](https://github.com/databricks-solutions/lakebase-express) · Lakebase (Postgres) · ★10 · Free Edition: A confirmar

- **Finalidade:** App que migra bancos SQL Server e Azure SQL para o Lakebase.
- **Como usar:** Implantar e seguir o catálogo de conectores.
- **Casos de uso:** Migração de banco transacional.
- **Benefício para o pos_venda:** Não se aplica.

### [lakebase-scm-extension](https://github.com/databricks-solutions/lakebase-scm-extension) · Lakebase (Postgres) · ★6 · Free Edition: A confirmar

- **Finalidade:** Extensão VS Code que pareia branches git com branches do Lakebase.
- **Como usar:** Instalar o VSIX e adotar no projeto.
- **Casos de uso:** Desenvolvimento de app com banco versionado.
- **Benefício para o pos_venda:** Não se aplica.

### [lakebase-scm-utils](https://github.com/databricks-solutions/lakebase-scm-utils) · Lakebase (Postgres) · ★0 · Free Edition: A confirmar

- **Finalidade:** CLI e skills do fluxo git + Lakebase (migrações, diff de schema, PR e CI).
- **Como usar:** Instalar a CLI e seguir o fluxo de feature branch.
- **Casos de uso:** Mesmo da extensão SCM.
- **Benefício para o pos_venda:** Não se aplica.

### [lakets](https://github.com/databricks-solutions/lakets) · Lakebase (Postgres) · ★8 · Free Edition: A confirmar

- **Finalidade:** Toolkit de séries temporais em PL/pgSQL para Lakebase (particionamento, rollups, tiering, sync com UC).
- **Como usar:** Instalar as funções SQL e criar ChronoTables.
- **Casos de uso:** IoT, métricas de alta frequência.
- **Benefício para o pos_venda:** Não se aplica.

### [alteryx-to-databricks-converter](https://github.com/databricks-solutions/alteryx-to-databricks-converter) · Migração · ★3 · Free Edition: A confirmar

- **Finalidade:** Converte workflows do Alteryx em PySpark, SDP, SQL e Lakeflow Designer.
- **Como usar:** Enviar o .yxmd pela linha de comando ou app.
- **Casos de uso:** Sair do Alteryx.
- **Benefício para o pos_venda:** Só se houver fluxos em Alteryx.

### [flowx](https://github.com/databricks-solutions/flowx) · Migração · ★6 · Free Edition: A confirmar

- **Finalidade:** Converte pipelines do Azure Data Factory e Airflow em Lakeflow Jobs empacotados em bundles.
- **Como usar:** Usar as skills no Genie Code ou Claude Code: descobrir, converter, empacotar.
- **Casos de uso:** Migração de orquestradores.
- **Benefício para o pos_venda:** Só se houver ADF ou Airflow legado.

### [managed-table-migration-accelerator](https://github.com/databricks-solutions/managed-table-migration-accelerator) · Migração · ★0 · Free Edition: A confirmar

- **Finalidade:** Converte tabelas EXTERNAL do UC para MANAGED em ondas, com rollback de 14 dias.
- **Como usar:** Instalar o bundle e conduzir pela App ou Genie Code.
- **Casos de uso:** Habilitar otimização preditiva em tabelas externas.
- **Benefício para o pos_venda:** As tabelas do projeto já são gerenciadas.

### [.github](https://github.com/databricks-solutions/.github) · Modelo vazio ou arquivado · ★0 · Free Edition: A confirmar

- **Finalidade:** Configuração e modelo de README da organização.
- **Como usar:** Nada a usar.
- **Casos de uso:** Nenhum.
- **Benefício para o pos_venda:** Não se aplica.

### [alert-test-repo-02-pleasedelete](https://github.com/databricks-solutions/alert-test-repo-02-pleasedelete) · Modelo vazio ou arquivado · ★0 · Free Edition: A confirmar

- **Finalidade:** Repositório de teste com README de modelo.
- **Como usar:** Nada a usar.
- **Casos de uso:** Nenhum.
- **Benefício para o pos_venda:** Não se aplica.

### [lakebridge-migration-self-service-demo](https://github.com/databricks-solutions/lakebridge-migration-self-service-demo) · Modelo vazio ou arquivado · ★0 · Free Edition: A confirmar

- **Finalidade:** README ainda é o modelo padrão, sem conteúdo descrito.
- **Como usar:** Nada a usar ainda.
- **Casos de uso:** Nenhum.
- **Benefício para o pos_venda:** Não se aplica.

### [maxgenie](https://github.com/databricks-solutions/maxgenie) · Modelo vazio ou arquivado · ★2 · Free Edition: A confirmar

- **Finalidade:** Otimizador de espaços Genie, arquivado e descontinuado.
- **Como usar:** Não usar; o próprio README indica o Genie Workbench.
- **Casos de uso:** Histórico.
- **Benefício para o pos_venda:** Use o databricks-genie-workbench.

### [multimodal_blog](https://github.com/databricks-solutions/multimodal_blog) · Modelo vazio ou arquivado · ★1 · Free Edition: A confirmar

- **Finalidade:** Código de um post sobre multimodal, sem descrição no README.
- **Como usar:** Abrir os notebooks diretamente.
- **Casos de uso:** Não descrito.
- **Benefício para o pos_venda:** Não se aplica.

### [streaming-real-time-mode-examples](https://github.com/databricks-solutions/streaming-real-time-mode-examples) · Modelo vazio ou arquivado · ★0 · Free Edition: A confirmar

- **Finalidade:** README ainda é o modelo padrão, sem conteúdo descrito.
- **Como usar:** Nada a usar ainda.
- **Casos de uso:** Nenhum.
- **Benefício para o pos_venda:** Não se aplica.

### [zerobus_station](https://github.com/databricks-solutions/zerobus_station) · Modelo vazio ou arquivado · ★6 · Free Edition: A confirmar

- **Finalidade:** Serviço FastAPI de ingestão via Zerobus, arquivado.
- **Como usar:** Não usar.
- **Casos de uso:** Histórico.
- **Benefício para o pos_venda:** Não se aplica.

### [databricks-dbt-training-labs](https://github.com/databricks-solutions/databricks-dbt-training-labs) · Pipelines e engenharia de dados · ★1 · Free Edition: A confirmar

- **Finalidade:** Laboratórios do curso de dbt no Databricks, até produção com bundles.
- **Como usar:** Clonar, preencher os valores do workspace e seguir os labs.
- **Casos de uso:** Aprender dbt no Unity Catalog.
- **Benefício para o pos_venda:** Só se o time decidir modelar a gold em dbt.

### [dbt-query-tags](https://github.com/databricks-solutions/dbt-query-tags) · Pipelines e engenharia de dados · ★0 · Free Edition: A confirmar

- **Finalidade:** Projeto dbt em bundle que usa query tags e system tables, com painel.
- **Como usar:** Ajustar profiles.yml e databricks.yml, rodar dbt e o bundle.
- **Casos de uso:** Atribuir custo de queries dbt por equipe.
- **Benefício para o pos_venda:** O projeto não usa dbt.

### [ai-platform-kit](https://github.com/databricks-solutions/ai-platform-kit) · Plataforma, infraestrutura e custos · ★22 · Free Edition: Não

- **Finalidade:** Engenharia de plataforma por linguagem natural: workspaces, Unity Catalog, identidade e redes em Azure, AWS e GCP.
- **Como usar:** Instalar as skills no agente de código e pedir o provisionamento.
- **Casos de uso:** Montar a plataforma corporativa.
- **Benefício para o pos_venda:** Não se aplica ao Free Edition.
- **Nota Free Edition:** Exige administração de conta e nuvem.

### [cloud-infra-costs](https://github.com/databricks-solutions/cloud-infra-costs) · Plataforma, infraestrutura e custos · ★53 · Free Edition: Não

- **Finalidade:** Une relatórios de custo da nuvem com system tables para o custo total da computação clássica, em painéis FOCUS.
- **Como usar:** Configurar a exportação de custos e rodar as consultas.
- **Casos de uso:** TCO de clusters clássicos.
- **Benefício para o pos_venda:** O Free Edition é serverless e gratuito.
- **Nota Free Edition:** Mira computação clássica e faturas de nuvem.

### [dais-2024-faster-library-loads](https://github.com/databricks-solutions/dais-2024-faster-library-loads) · Plataforma, infraestrutura e custos · ★4 · Free Edition: Não

- **Finalidade:** Truque para acelerar a instalação de bibliotecas em clusters interativos.
- **Como usar:** Seguir os notebooks.
- **Casos de uso:** Reduzir espera de cluster.
- **Benefício para o pos_venda:** O projeto usa serverless.

### [dbx-proxy](https://github.com/databricks-solutions/dbx-proxy) · Plataforma, infraestrutura e custos · ★2 · Free Edition: Não

- **Finalidade:** Proxy HAProxy para conectividade privada do serverless até redes do cliente.
- **Como usar:** Implantar com Terraform.
- **Casos de uso:** Acessar bancos em VPC a partir do serverless.
- **Benefício para o pos_venda:** Não se aplica.

### [network-doctor](https://github.com/databricks-solutions/network-doctor) · Plataforma, infraestrutura e custos · ★5 · Free Edition: Não

- **Finalidade:** Skill do Genie Code que diagnostica falhas de rede do Azure Databricks.
- **Como usar:** Registrar o Git folder no Genie Code e descrever o problema.
- **Casos de uso:** Troubleshooting de rede.
- **Benefício para o pos_venda:** Não se aplica.

### [aim-divergence-fix](https://github.com/databricks-solutions/aim-divergence-fix) · Qualidade, governança e segurança · ★0 · Free Edition: Não

- **Finalidade:** Encontra e corrige divergências de identidade que bloqueiam a migração de SCIM para Automatic Identity Management (Entra ID).
- **Como usar:** Rodar as ferramentas de diagnóstico e seguir a correção por categoria.
- **Casos de uso:** Migração de provisionamento de identidades no Azure.
- **Benefício para o pos_venda:** Não se aplica ao projeto.
- **Nota Free Edition:** Exige Microsoft Entra ID e administração de conta.

### [data-intelligence-for-smarter-community](https://github.com/databricks-solutions/data-intelligence-for-smarter-community) · Soluções de indústria · ★4 · Free Edition: A confirmar

- **Finalidade:** Acelerador de telecom para comunidades inteligentes (sinais de torres e IoT).
- **Como usar:** Seguir os labs em 3 passos.
- **Casos de uso:** Trânsito, congestionamento e segurança urbana.
- **Benefício para o pos_venda:** Não se aplica.

### [geogenie-esri](https://github.com/databricks-solutions/geogenie-esri) · Soluções de indústria · ★0 · Free Edition: A confirmar

- **Finalidade:** Mapa de rede de telecom com ROI de expansão e Genie, alternativa ao ArcGIS.
- **Como usar:** Implantar a App.
- **Casos de uso:** Planejamento de rede.
- **Benefício para o pos_venda:** Não se aplica.

### [lakeflow-deliveries](https://github.com/databricks-solutions/lakeflow-deliveries) · Soluções de indústria · ★1 · Free Edition: A confirmar

- **Finalidade:** Simulação de entregas com SDP em streaming e funções espaciais, App de mapa.
- **Como usar:** Implantar o bundle.
- **Casos de uso:** Logística em tempo real.
- **Benefício para o pos_venda:** Não se aplica.

### [network-intelligence-accelerator](https://github.com/databricks-solutions/network-intelligence-accelerator) · Soluções de indústria · ★0 · Free Edition: Não

- **Finalidade:** Gêmeo digital de RF para planejamento celular com ray tracing em GPU.
- **Como usar:** Implantar o bundle com jobs de GPU.
- **Casos de uso:** Telecom 5G.
- **Benefício para o pos_venda:** Não se aplica.

### [supply-chain-control-tower-bricks](https://github.com/databricks-solutions/supply-chain-control-tower-bricks) · Soluções de indústria · ★1 · Free Edition: A confirmar

- **Finalidade:** Visibilidade de supply chain com fluxo agêntico de atendimento de pedidos.
- **Como usar:** Configurar o repo no workspace.
- **Casos de uso:** Cadeia de suprimentos.
- **Benefício para o pos_venda:** Não se aplica.

### [dais-2024-dab-mod-orch-template](https://github.com/databricks-solutions/dais-2024-dab-mod-orch-template) · Workshops, demos e coleções · ★0 · Free Edition: A confirmar

- **Finalidade:** Template simples de bundle com três jobs (DAIS 2024).
- **Como usar:** Inicializar a partir do template.
- **Casos de uso:** Primeiro bundle.
- **Benefício para o pos_venda:** Superado pelos bundles do projeto.

### [dais-2024-llm4good](https://github.com/databricks-solutions/dais-2024-llm4good) · Workshops, demos e coleções · ★3 · Free Edition: A confirmar

- **Finalidade:** Alinhamento de LLMs a preferências de negócio usando outro LLM como avaliador (DAIS 2024).
- **Como usar:** Usar a branch V2.
- **Casos de uso:** Alinhamento de modelos.
- **Benefício para o pos_venda:** Não se aplica.

### [dais-2025-genai-hackathon](https://github.com/databricks-solutions/dais-2025-genai-hackathon) · Workshops, demos e coleções · ★7 · Free Edition: A confirmar

- **Finalidade:** Guia de início do hackathon de GenAI do Data + AI Summit 2025.
- **Como usar:** Seguir o README.
- **Casos de uso:** Hackathon.
- **Benefício para o pos_venda:** Não se aplica.

### [databricks-japan-bootcamp](https://github.com/databricks-solutions/databricks-japan-bootcamp) · Workshops, demos e coleções · ★7 · Free Edition: A confirmar

- **Finalidade:** Workshops em japonês (Unity Gateway, governança de IA, coding agents).
- **Como usar:** Abrir a sessão desejada.
- **Casos de uso:** Treinamento no Japão.
- **Benefício para o pos_venda:** Não se aplica.
