# Opções databricks-solutions para o pos_venda · guia para LLM

> Gerado por `gerar_opcoes.py` em 2026-11-23, a partir de `catalogo.py`. Não edite à mão. Versão estruturada: [`opcoes.json`](opcoes.json).

Este guia lista os **147 repositórios públicos** da organização [databricks-solutions](https://github.com/databricks-solutions) como opções para o projeto. Cada opção diz o que é, como ajudaria no pos_venda, quando escolher, se cabe no Free Edition, a camada e as práticas do [framework](../../docs/04_FRAMEWORK.md) que ela reforça, e a recomendação para o projeto hoje.

**Para uma LLM:** leia o contexto e as regras, depois use o ranking e os blocos. Pergunta de exemplo: *"Quero medir quanto a Genie e os painéis são usados. Qual opção databricks-solutions usar no pos_venda?"* A resposta esperada aplica as regras: a camada é Avaliação; `dbx-adoption-monitor` está em *Aplicar a seguir*, cabe no Free Edition e não ocupa vaga de app; o `databricks-genie-workbench` fica de fora porque gastaria a última vaga de app.

## Contexto do projeto

| Item | Situação |
|---|---|
| Dominio | Pós-venda de seguro de vida: parcelas pendentes de pagamento (carteira em aberto, recuperação, safras) |
| Plataforma | Databricks Free Edition: 1 SQL warehouse 2X-Small, cota diária de computação, só serverless |
| Apps | 2 de 3 vagas em uso (dqx-studio e genie-ontology-readiness); resta 1 |
| Lakebase | 1 projeto, já em uso (dqx-studio-db); um app novo que precise de Postgres usa uma database nesse projeto |
| Modelos | Sem modelos Claude no Model Serving; llama-4-maverick testado para saída estruturada (até 8.192 tokens) |
| Dados | Sintéticos (dbldatagen); dado pessoal marcado por tag e sem máscara, por decisão (a validação usa os valores) |
| Consumo | 2 espaços Genie (analista e diretor), painéis AI/BI, opção Power BI por importação (schema bi) |
| Versionamento | Git no GitHub (gustocezar/databricks_estudo); ainda sem CI/CD |
| Framework | docs/04_FRAMEWORK.md: 37 práticas (P01 a P37) em 10 camadas |

## Regras de escolha

1. Identifique a necessidade e a camada do framework que ela toca (Fundação, Dados, Qualidade, Governança, Semântica, Consumo, Avaliação, Custo e uso, Operação, Conformidade).
2. Filtre as opções pela camada e pelas práticas (campos `camada` e `praticas`); confira o campo `escolha_quando`.
3. Se uma opção `Já aplicado` cobre a necessidade, estenda-a antes de adotar outra (ela já está integrada e testada).
4. Enquanto o projeto estiver no Free Edition, descarte `Não roda no Free Edition`; em `Com ressalvas`, leia a `nota_free_edition` e diga a ressalva.
5. Prefira `Aplicar a seguir`, depois `Candidato`, em ordem de relevância (Alta antes de Média); o campo `prioridade` já ordena assim.
6. Desempate: sem app novo (resta 1 vaga), sem modelo Claude, sem projeto Lakebase novo, menor esforço.
7. `Adiado` só volta se o motivo do adiamento (campo `motivo_situacao`) deixou de valer.
8. `Só se a necessidade mudar` e `Fora do escopo` não são recomendações para o pos_venda atual; cite-as só quando a necessidade nova bater com `escolha_quando`.
9. Responda com: a opção escolhida, por quê (citando os campos), o que ela exige no Free Edition, a prática do framework que ela reforça e a alternativa descartada, com o motivo.

## Recomendações, em números

| Recomendação | Opções | O que significa |
|---|---|---|
| Aplicar a seguir | 2 | proposta da revisão de 22/11 ainda não aplicada |
| Candidato | 5 | relevância alta ou média, cabe no Free Edition, sem decisão ainda |
| Já aplicado | 7 | em uso no projeto; estenda antes de adotar outra |
| Adiado | 10 | avaliado e adiado, com o motivo; volta se o motivo deixar de valer |
| Só se a necessidade mudar | 69 | relevância baixa para o pos_venda atual |
| Fora do escopo | 37 | sem relação com o pos_venda atual |
| Não roda no Free Edition | 17 | exige recurso que o Free Edition não tem |

## Ranking das opções que importam para o pos_venda

Aplicar a seguir, candidatos, já aplicados e adiados, nessa ordem e por relevância.

| # | Opção | Recomendação | Camada · práticas | Relevância | Free Edition | Como ajudaria |
|---|---|---|---|---|---|---|
| 1 | [regulatory_data_governance](https://github.com/databricks-solutions/regulatory_data_governance) | Aplicar a seguir | Qualidade e Governança · P11, P14 | Alta | Com ressalvas | Arquitetura mais próxima do pos_venda (medallion, DQX Studio, AI/BI, Genie, em português), mas para a Resolução BACEN nº 18; o pós-venda segue a SUSEP. Não… |
| 2 | [dbx-adoption-monitor](https://github.com/databricks-solutions/dbx-adoption-monitor) | Aplicar a seguir | Avaliação · P26 | Média | Sim | Copiar só as metric views de adoção de painéis e Genie para medir o uso na avaliação Databricks × Power BI; separar os eventos das avaliações automáticas da… |
| 3 | [ai-dev-kit](https://github.com/databricks-solutions/ai-dev-kit) | Candidato | Fundação · P02 | Média | Sim | É a origem das skills Databricks usadas neste projeto; manter atualizado traz correções de APIs (Genie, metric views, painéis). |
| 4 | [aibi-dashboard-wanderbricks](https://github.com/databricks-solutions/aibi-dashboard-wanderbricks) | Candidato | Consumo · P22 | Média | Sim | Modelo visual para refinar os três painéis do projeto (Qualidade, Diretoria e Analista): KPIs no topo, páginas, tema e filtros. |
| 5 | [caspers](https://github.com/databricks-solutions/caspers) | Candidato | Dados e Qualidade · P04, P10 | Média | Com ressalvas | Referência de narrativa de demo e de simulação em streaming para tornar o gerador do pós-venda mais realista. |
| 6 | [databricks-aibi-design-first-accelerator](https://github.com/databricks-solutions/databricks-aibi-design-first-accelerator) | Candidato | Semântica · P18 | Média | Com ressalvas | Permite regenerar ou comparar a camada semântica do pos_venda a partir de um kpi_spec.md escrito pelo negócio, útil para evoluir os KPIs da gold sem refazer… |
| 7 | [databricks-forge](https://github.com/databricks-solutions/databricks-forge) | Candidato | Governança e Semântica · P14, P18 | Média | Com ressalvas | Com os metadados ricos que já temos (descrições em 92% das colunas, tags e domínio), sugere os próximos casos de uso do pós-venda com estimativa de valor. |
| 8 | [powerbi-analyzer](https://github.com/databricks-solutions/powerbi-analyzer) | Já aplicado | Consumo e Avaliação · P08, P26 | Alta | Sim | Audita o projeto Power BI do pos_venda e o lado Databricks contra as 42 regras da cheat sheet; cobre parte do que hoje só o Power BI Desktop verificaria e… |
| 9 | [uc-semantics-patterns](https://github.com/databricks-solutions/uc-semantics-patterns) | Já aplicado | Semântica · P19 | Alta | Sim | Resolve com padrão oficial o saldo em aberto semiaditivo que hoje tratamos com três medidas (foto mais recente, fim de mês, média diária); acrescenta… |
| 10 | [genie-best-practices-agent](https://github.com/databricks-solutions/genie-best-practices-agent) | Já aplicado | Avaliação · P24 | Alta | Com ressalvas | Segunda opinião independente sobre os espaços do CFO e do analista: instruções de texto, exemplos SQL, descrições e sinônimos. |
| 11 | [genie-ontology-readiness](https://github.com/databricks-solutions/genie-ontology-readiness) | Já aplicado | Avaliação · P25 | Alta | Com ressalvas | Mede a camada de ontologia que acabamos de montar (domínio Pós-venda, 18 Pages, 51 wikis, tags, metric views, 2 espaços Genie) e aponta lacunas como chaves… |
| 12 | [technical-services-solutions](https://github.com/databricks-solutions/technical-services-solutions) | Já aplicado | Avaliação · P26 | Alta | Com ressalvas | genie/genie-agent-scanner aplica a régua de 12 itens do Genie Workbench sem app, Lakebase ou LLM aos dois espaços Genie. data-warehousing/pbi-aibi-converter… |
| 13 | [agentic-bdd-uc-functions](https://github.com/databricks-solutions/agentic-bdd-uc-functions) | Já aplicado | Semântica · P20 | Média | Sim | Transforma regras do pós-venda (valor total = parcela + multa + juros, faixas de atraso) em funções testadas por cenários legíveis pelo negócio. |
| 14 | [power-bi-on-databricks-quickstarts](https://github.com/databricks-solutions/power-bi-on-databricks-quickstarts) | Já aplicado | Consumo · P23 | Média | Sim | Referência das regras que o powerbi-analyzer verifica. Com importação (942 mil linhas na maior tabela) valem parâmetros de conexão (já usados), chaves com… |
| 15 | [databricks-dab-examples](https://github.com/databricks-solutions/databricks-dab-examples) | Adiado | Fundação · P02, P03 | Média | Sim | Modelo para amadurecer os bundles carga_diaria, painel e paineis_financeiros com targets dev/prod, testes e pipeline de CI. |
| 16 | [advance-document-processing](https://github.com/databricks-solutions/advance-document-processing) | Adiado | Consumo (agentes e IA generativa) · — (capacidade nova: leitura de documentos) | Média | Com ressalvas | Próximo passo natural do pós-venda: ler comprovantes de pagamento, boletos e cartas de cobrança e conciliar com as pendências. |
| 17 | [data-classification-review-app](https://github.com/databricks-solutions/data-classification-review-app) | Adiado | Governança · P15 | Média | Com ressalvas | Formaliza a revisão das tags class.br_cpf, class.br_rg e class.name que aplicamos na dim_cliente, com o dono do dado aprovando. |
| 18 | [databricks-genie-workbench](https://github.com/databricks-solutions/databricks-genie-workbench) | Adiado | Consumo e Avaliação · P21, P26 | Média | Com ressalvas | Dá nota e plano de melhoria para os dois espaços (Analista financeiro e Diretoria) e automatiza o ciclo de benchmark que fizemos à mão no genie.py (24/24). |
| 19 | [genierails](https://github.com/databricks-solutions/genierails) | Adiado | Governança · P15 | Média | Com ressalvas | Caminho seguro para abrir os espaços do pós-venda a mais pessoas: nenhuma coluna com CPF ou RG fica sem máscara. |
| 20 | [ingestion-workbench](https://github.com/databricks-solutions/ingestion-workbench) | Adiado | Dados · P06 | Média | Com ressalvas | Caminho de produção para trocar o gerador sintético pelo banco real do sistema de cobrança e apólices. |
| 21 | [lakeflow_framework](https://github.com/databricks-solutions/lakeflow_framework) | Adiado | Dados e Qualidade · P06, P09 | Média | Com ressalvas | Alternativa para trocar os notebooks escritos à mão do carga_diaria por pipelines declarados, com expectations nativas ao lado do DQX. |
| 22 | [mlops-quickstart](https://github.com/databricks-solutions/mlops-quickstart) | Adiado | Avaliação e modelos · — (capacidade nova: modelo de propensão) | Média | Com ressalvas | Esqueleto para um modelo de propensão de regularização das pendências, que priorizaria a cobrança. |
| 23 | [uc-declarative-abac](https://github.com/databricks-solutions/uc-declarative-abac) | Adiado | Governança · P15 | Média | Com ressalvas | Usa as tags de classificação já aplicadas para mascarar CPF e RG para o analista e liberar ao time de cobrança, sem escrever política tabela a tabela. |
| 24 | [databricks-waf](https://github.com/databricks-solutions/databricks-waf) | Adiado | Fundação e Operação · P01, P28 | Baixa | Com ressalvas | Checklist de prontidão para levar o pós-venda à produção. |

## Todas as opções, em ordem de prioridade

### Aplicar a seguir (2)

#### 1. regulatory_data_governance

- **Recomendação:** Aplicar a seguir. Só os padrões, sem instalar o acelerador: propostas 4 (dimensão de qualidade nas regras) e 7 (linhagem externa com Power BI) da revisão de 22/11.
- **Relevância para o pos_venda:** Alta · **Free Edition:** Com ressalvas (Exige DQX Studio e Lakebase no mesmo workspace, que o projeto já tem; o deploy cria vários recursos e consome cota.)
- **Camada do framework:** Qualidade e Governança · **Práticas:** P11, P14 · **Categoria:** Qualidade, governança e segurança
- **O que é:** Starter kit em português para a Resolução Conjunta BACEN nº 18: app de monitoramento de qualidade com motor de regras ligado ao DQX Studio, pipelines medallion dos CADOCs 3040/3050, painéis AI/BI e sala Genie.
- **Como ajudaria no pos_venda:** Arquitetura mais próxima do pos_venda (medallion, DQX Studio, AI/BI, Genie, em português), mas para a Resolução BACEN nº 18; o pós-venda segue a SUSEP. Não instalar: reaproveitar a dimensão de qualidade em user_metadata de cada regra e a linhagem externa no Unity Catalog.
- **Escolha quando:** Governança de dados regulatórios, críticas de qualidade com aprovação, linhagem externa, evidências para auditoria.
- **Como usar:** Copiar target.yml.example, preencher perfil e URL do DQX Studio, rodar databricks bundle deploy e os jobs rc18_end_to_end e r18_compliance_app.
- **Repositório:** [regulatory_data_governance](https://github.com/databricks-solutions/regulatory_data_governance) · último commit 2026-11-19

#### 2. dbx-adoption-monitor

- **Recomendação:** Aplicar a seguir. Proposta 6 da revisão de 22/11.
- **Relevância para o pos_venda:** Média · **Free Edition:** Sim (system.access.audit é legível neste workspace (7 dias: 71 eventos de painéis, 1.421 da Genie, 21 de apps).)
- **Camada do framework:** Avaliação · **Práticas:** P26 · **Categoria:** Qualidade, governança e segurança
- **O que é:** Bundle que inventaria e mede adoção de painéis AI/BI, Genie, Apps, model serving e vector search, com modelo dimensional, metric views e painel.
- **Como ajudaria no pos_venda:** Copiar só as metric views de adoção de painéis e Genie para medir o uso na avaliação Databricks × Power BI; separar os eventos das avaliações automáticas da Genie, que são a maioria.
- **Escolha quando:** Medir uso de painéis e Genie por usuário, apps acessadas, retorno do investimento em BI.
- **Como usar:** Fazer bundle deploy e rodar o workflow; abrir o painel publicado.
- **Repositório:** [dbx-adoption-monitor](https://github.com/databricks-solutions/dbx-adoption-monitor) · último commit 2026-09-29

### Candidato (5)

#### 3. ai-dev-kit

- **Recomendação:** Candidato
- **Relevância para o pos_venda:** Média · **Free Edition:** Sim
- **Camada do framework:** Fundação · **Práticas:** P02 · **Categoria:** Ferramentas para coding agents
- **O que é:** Toolkit de skills para agentes de código no Databricks; as skills agora são as Databricks AI Tools, instaladas por databricks aitools install.
- **Como ajudaria no pos_venda:** É a origem das skills Databricks usadas neste projeto; manter atualizado traz correções de APIs (Genie, metric views, painéis).
- **Escolha quando:** Construir pipelines, painéis, Genie, apps com assistentes de código.
- **Como usar:** Rodar o instalador ou databricks aitools install e manter atualizado.
- **Repositório:** [ai-dev-kit](https://github.com/databricks-solutions/ai-dev-kit) · último commit 2026-11-09

#### 4. aibi-dashboard-wanderbricks

- **Recomendação:** Candidato
- **Relevância para o pos_venda:** Média · **Free Edition:** Sim (Usa o dataset samples.wanderbricks e importação de painel.)
- **Camada do framework:** Consumo · **Práticas:** P22 · **Categoria:** Genie e camada semântica
- **O que é:** Painel de referência do blog 'Design Beautiful Dashboards in AI/BI', pronto para importar.
- **Como ajudaria no pos_venda:** Modelo visual para refinar os três painéis do projeto (Qualidade, Diretoria e Analista): KPIs no topo, páginas, tema e filtros.
- **Escolha quando:** Referência de layout, hierarquia visual, filtros e tema para painéis AI/BI.
- **Como usar:** Baixar o .lvdash.json e importar em Dashboards > Importar arquivo.
- **Repositório:** [aibi-dashboard-wanderbricks](https://github.com/databricks-solutions/aibi-dashboard-wanderbricks) · último commit 2026-06-22

#### 5. caspers

- **Recomendação:** Candidato
- **Relevância para o pos_venda:** Média · **Free Edition:** Com ressalvas (Cria catálogos, streams, agentes e apps; consome bastante cota.)
- **Camada do framework:** Dados e Qualidade · **Práticas:** P04, P10 · **Categoria:** Workshops, demos e coleções
- **O que é:** Empresa simulada completa (ghost kitchen) com streaming, AI/BI, Genie, Agent Bricks, Apps e Lakebase; uma skill gera a mesma demo para outros domínios.
- **Como ajudaria no pos_venda:** Referência de narrativa de demo e de simulação em streaming para tornar o gerador do pós-venda mais realista.
- **Escolha quando:** Demo de plataforma de ponta a ponta.
- **Como usar:** Autenticar o CLI e implantar; usar a branch skill para gerar outro domínio.
- **Repositório:** [caspers](https://github.com/databricks-solutions/caspers) · último commit 2026-09-29

#### 6. databricks-aibi-design-first-accelerator

- **Recomendação:** Candidato
- **Relevância para o pos_venda:** Média · **Free Edition:** Com ressalvas (Usa Genie Code ou uma App em Flask; gera tabelas, metric views e painéis.)
- **Camada do framework:** Semântica · **Práticas:** P18 · **Categoria:** Genie e camada semântica
- **O que é:** Do catálogo de KPIs (e ERD ou schema existente) para tabelas, metric views, painéis AI/BI e espaço Genie, por uma sequência de prompts.
- **Como ajudaria no pos_venda:** Permite regenerar ou comparar a camada semântica do pos_venda a partir de um kpi_spec.md escrito pelo negócio, útil para evoluir os KPIs da gold sem refazer tudo à mão.
- **Escolha quando:** POC de BI governado em horas, padronizar a camada semântica a partir de uma especificação de KPIs.
- **Como usar:** Preencher accelerator.yaml e kpi_spec.md, fazer bundle deploy e rodar o prompt mestre no Genie Code ou na App (modo brownfield usa o schema atual).
- **Repositório:** [databricks-aibi-design-first-accelerator](https://github.com/databricks-solutions/databricks-aibi-design-first-accelerator) · último commit 2026-10-08

#### 7. databricks-forge

- **Recomendação:** Candidato
- **Relevância para o pos_venda:** Média · **Free Edition:** Com ressalvas (App em Next.js com Lakebase e warehouse serverless; lê metadados do UC.)
- **Camada do framework:** Governança e Semântica · **Práticas:** P14, P18 · **Categoria:** Genie e camada semântica
- **O que é:** Transforma metadados do Unity Catalog numa lista priorizada e com valor financeiro de casos de uso de dados e IA, e ativa como Genie, painéis, metric views e documentação.
- **Como ajudaria no pos_venda:** Com os metadados ricos que já temos (descrições em 92% das colunas, tags e domínio), sugere os próximos casos de uso do pós-venda com estimativa de valor.
- **Escolha quando:** Descobrir próximos casos de uso, gerar backlog para a diretoria, documentar o catálogo.
- **Como usar:** Implantar como App, apontar para catálogos e rodar a descoberta; escolher recomendações e ativar.
- **Repositório:** [databricks-forge](https://github.com/databricks-solutions/databricks-forge) · último commit 2026-11-02

### Já aplicado (7)

#### 8. powerbi-analyzer

- **Recomendação:** Já aplicado. Proposta 1, aplicada em 22/11 (paineis_financeiros/powerbi/auditoria/): modelo 80/100, Databricks 75/100. O leitor de PBIP só aceita model.bim (o gerador ganhou a saída bim) e as regras de preparo de dados passam sem avaliar enquanto o Power BI não consultar o warehouse.
- **Relevância para o pos_venda:** Alta · **Free Edition:** Sim (`pba pbix` lê .pbip sem credencial (roda no Mac); `pba databricks` lê system.query.history, legível neste workspace.)
- **Camada do framework:** Consumo e Avaliação · **Práticas:** P08, P26 · **Categoria:** BI externo (Power BI, Grafana)
- **O que é:** CLI que audita uma instalação de Power BI sobre Databricks com 42 regras da cheat sheet.
- **Como ajudaria no pos_venda:** Audita o projeto Power BI do pos_venda e o lado Databricks contra as 42 regras da cheat sheet; cobre parte do que hoje só o Power BI Desktop verificaria e dá um relatório de boas práticas para a avaliação das duas ferramentas.
- **Escolha quando:** Auditoria de boas práticas.
- **Como usar:** Instalar com uv e rodar pba sobre .pbix, workspace ou config.
- **Repositório:** [powerbi-analyzer](https://github.com/databricks-solutions/powerbi-analyzer) · último commit 2026-07-24

#### 9. uc-semantics-patterns

- **Recomendação:** Já aplicado. Fase 12: saldo de fechamento, mês anterior e variação, acumulados no mês e no ano, ranking. Ainda não usados: médias móveis e curva ABC (proposta 5 da revisão).
- **Relevância para o pos_venda:** Alta · **Free Edition:** Sim
- **Camada do framework:** Semântica · **Práticas:** P19 · **Categoria:** Genie e camada semântica
- **O que é:** Coleção de padrões prontos de metric views (UC Business Semantics) para cálculos que não são óbvios em YAML.
- **Como ajudaria no pos_venda:** Resolve com padrão oficial o saldo em aberto semiaditivo que hoje tratamos com três medidas (foto mais recente, fim de mês, média diária); acrescenta MoM/YoY e ranking de corretores e produtos nas metric views que a Genie e os painéis já usam.
- **Escolha quando:** Comparação de períodos (MoM, YoY), acumulado no período (MTD, YTD), saldos semiaditivos (abertura e fechamento), ranking, segmentação estática e dinâmica, calendários, curva ABC, conversão de moeda.
- **Como usar:** Abrir a pasta do padrão, copiar o YAML e a consulta de exemplo, trocar tabelas e colunas pelas suas.
- **Repositório:** [uc-semantics-patterns](https://github.com/databricks-solutions/uc-semantics-patterns) · último commit 2026-11-06

#### 10. genie-best-practices-agent

- **Recomendação:** Já aplicado. Fase 13: triagem em governanca/genie/avaliacao_boas_praticas/.
- **Relevância para o pos_venda:** Alta · **Free Edition:** Com ressalvas (Roda localmente com LangGraph; precisa de um endpoint de LLM no workspace.)
- **Camada do framework:** Avaliação · **Práticas:** P24 · **Categoria:** Genie e camada semântica
- **O que é:** Agente que avalia a configuração de um espaço Genie e os metadados do UC contra as boas práticas, com benchmarks opcionais.
- **Como ajudaria no pos_venda:** Segunda opinião independente sobre os espaços do CFO e do analista: instruções de texto, exemplos SQL, descrições e sinônimos.
- **Escolha quando:** Revisão de espaço Genie antes de liberar para o negócio; auditoria de instruções, exemplos SQL e descrições de colunas.
- **Como usar:** Configurar o ID do espaço e o perfil do CLI, rodar o pipeline LangGraph e ler o relatório por trilha de avaliação.
- **Repositório:** [genie-best-practices-agent](https://github.com/databricks-solutions/genie-best-practices-agent) · último commit 2026-08-03

#### 11. genie-ontology-readiness

- **Recomendação:** Já aplicado. Fase 18: app v1.5.0 (a versão mais recente em 22/11), nota 92,7, histórico no Lakebase.
- **Relevância para o pos_venda:** Alta · **Free Edition:** Com ressalvas (App com chamada à Foundation Model API do workspace; avaliação somente leitura.)
- **Camada do framework:** Avaliação · **Práticas:** P25 · **Categoria:** Genie e camada semântica
- **O que é:** App que avalia a prontidão do workspace para a Genie Ontology em 7 pilares (UC, metadados, relações, metric views, Genie, domínios, adoção) e gera um plano.
- **Como ajudaria no pos_venda:** Mede a camada de ontologia que acabamos de montar (domínio Pós-venda, 18 Pages, 51 wikis, tags, metric views, 2 espaços Genie) e aponta lacunas como chaves PK/FK declaradas e adoção.
- **Escolha quando:** Diagnóstico de maturidade semântica, roteiro de capacitação, explicação técnica e de negócio de cada recurso.
- **Como usar:** Implantar pela UI de Apps a partir do Git, rodar a aba Assess, depois Plan e Learn.
- **Repositório:** [genie-ontology-readiness](https://github.com/databricks-solutions/genie-ontology-readiness) · último commit 2026-11-20

#### 12. technical-services-solutions

- **Recomendação:** Já aplicado. Proposta 2, aplicada em 22/11 (governanca/genie/scanner/): 8/12 nos dois espaços; teto de 10/12 sem o Workbench; itens 4, 7 e 8 ficam como ajuste proposto.
- **Relevância para o pos_venda:** Alta · **Free Edition:** Com ressalvas
- **Camada do framework:** Avaliação · **Práticas:** P26 · **Categoria:** Workshops, demos e coleções
- **O que é:** Coleção do time de Technical Services: governança (ABAC), business semantics, Genie (otimização e scanner de agentes), migrações, prontidão para produção.
- **Como ajudaria no pos_venda:** genie/genie-agent-scanner aplica a régua de 12 itens do Genie Workbench sem app, Lakebase ou LLM aos dois espaços Genie. data-warehousing/pbi-aibi-converter e aibi-migration convertem .pbip em painel AI/BI com LLM (Claude, ausente no Free Edition); servem só de referência, porque os dois painéis já saem do mesmo gerador.
- **Escolha quando:** Aceleradores pontuais por tema.
- **Como usar:** Entrar na pasta do tema e seguir o README de cada projeto.
- **Repositório:** [technical-services-solutions](https://github.com/databricks-solutions/technical-services-solutions) · último commit 2026-11-20

#### 13. agentic-bdd-uc-functions

- **Recomendação:** Já aplicado. Fase 19: regras de negócio como funções do Unity Catalog testadas por cenários (regras/).
- **Relevância para o pos_venda:** Média · **Free Edition:** Sim (Usa a Statement Execution API e funções do UC, que funcionam no Free Edition.)
- **Camada do framework:** Semântica · **Práticas:** P20 · **Categoria:** Qualidade, governança e segurança
- **O que é:** Testes BDD (Behave, Gherkin) de funções do Unity Catalog pela Statement Execution API, rodando em CI sem Spark.
- **Como ajudaria no pos_venda:** Transforma regras do pós-venda (valor total = parcela + multa + juros, faixas de atraso) em funções testadas por cenários legíveis pelo negócio.
- **Escolha quando:** Testar regras de negócio escritas como funções SQL, documentação viva das regras.
- **Como usar:** Escrever cenários .feature, implementar os passos, rodar localmente ou no GitHub Actions.
- **Repositório:** [agentic-bdd-uc-functions](https://github.com/databricks-solutions/agentic-bdd-uc-functions) · último commit 2026-05-04

#### 14. power-bi-on-databricks-quickstarts

- **Recomendação:** Já aplicado. Proposta 3, aplicada em 22/11 (governanca/aplicar_rely.py): RELY nas 14 PKs da gold, FKs sem RELY; saldo por dia na metric view passou de 9 junções para 0, com o mesmo resultado.
- **Relevância para o pos_venda:** Média · **Free Edition:** Sim
- **Camada do framework:** Consumo · **Práticas:** P23 · **Categoria:** BI externo (Power BI, Grafana)
- **O que é:** Referências e boas práticas de Power BI sobre Databricks SQL.
- **Como ajudaria no pos_venda:** Referência das regras que o powerbi-analyzer verifica. Com importação (942 mil linhas na maior tabela) valem parâmetros de conexão (já usados), chaves com RELY (07), integridade referencial (16) e OAuth M2M (13) para atualizar no serviço; os de DirectQuery e agregações valem se a carteira for consultada ao vivo.
- **Escolha quando:** Desempenho de Power BI em DBSQL.
- **Como usar:** Abrir o quickstart do tema e a cheat sheet.
- **Repositório:** [power-bi-on-databricks-quickstarts](https://github.com/databricks-solutions/power-bi-on-databricks-quickstarts) · último commit 2026-11-02

### Adiado (10)

#### 15. databricks-dab-examples

- **Recomendação:** Adiado. O pré-requisito (projeto num repositório Git) foi cumprido em 22/11; falta decidir a esteira de CI/CD.
- **Relevância para o pos_venda:** Média · **Free Edition:** Sim
- **Camada do framework:** Fundação · **Práticas:** P02, P03 · **Categoria:** Pipelines e engenharia de dados
- **O que é:** Projetos de exemplo de Declarative Automation Bundles com boas práticas de desenvolvimento, testes e CI/CD.
- **Como ajudaria no pos_venda:** Modelo para amadurecer os bundles carga_diaria, painel e paineis_financeiros com targets dev/prod, testes e pipeline de CI.
- **Escolha quando:** Ambientes dev e prod, testes unitários de bibliotecas, CI/CD de jobs e pipelines.
- **Como usar:** Começar por flights/flights-simple; copiar a estrutura de targets, testes e workflows.
- **Repositório:** [databricks-dab-examples](https://github.com/databricks-solutions/databricks-dab-examples) · último commit 2026-11-09

#### 16. advance-document-processing

- **Recomendação:** Adiado. Fora do escopo atual (revisão de 22/11): não há documentos para ler. Retomar se comprovantes, boletos ou cartas de cobrança entrarem no projeto.
- **Relevância para o pos_venda:** Média · **Free Edition:** Com ressalvas (Usa ai_parse_document e AI Functions; confira disponibilidade e cota.)
- **Camada do framework:** Consumo (agentes e IA generativa) · **Práticas:** — (capacidade nova: leitura de documentos) · **Categoria:** Agentes e IA generativa
- **O que é:** Pipelines de referência para documentos com ai_parse_document, ai_classify, ai_extract, LLMs de visão e Auto Loader, em notebooks e bundles.
- **Como ajudaria no pos_venda:** Próximo passo natural do pós-venda: ler comprovantes de pagamento, boletos e cartas de cobrança e conciliar com as pendências.
- **Escolha quando:** Extrair campos de PDFs, classificar páginas, montar base de conhecimento.
- **Como usar:** Escolher o pipeline (classificação e extração de páginas, citações, base de conhecimento) e implantar o bundle.
- **Repositório:** [advance-document-processing](https://github.com/databricks-solutions/advance-document-processing) · último commit 2026-11-03

#### 17. data-classification-review-app

- **Recomendação:** Adiado. Decisão do usuário: não mascarar dado pessoal, usado na validação. Retomar se a Genie abrir a mais pessoas.
- **Relevância para o pos_venda:** Média · **Free Edition:** Com ressalvas (Depende do recurso Data Classification do Unity Catalog.)
- **Camada do framework:** Governança · **Práticas:** P15 · **Categoria:** Qualidade, governança e segurança
- **O que é:** App que distribui a revisão da classificação automática de dados sensíveis (PII) entre os donos dos dados.
- **Como ajudaria no pos_venda:** Formaliza a revisão das tags class.br_cpf, class.br_rg e class.name que aplicamos na dim_cliente, com o dono do dado aprovando.
- **Escolha quando:** Confirmar ou rejeitar colunas marcadas como PII, trilha de revisão por domínio.
- **Como usar:** Implantar a partir dos artefatos prontos, dar permissões e enviar as colunas para revisão dos stewards.
- **Repositório:** [data-classification-review-app](https://github.com/databricks-solutions/data-classification-review-app) · último commit 2026-10-07

#### 18. databricks-genie-workbench

- **Recomendação:** Adiado. O genie-agent-scanner aplica a mesma régua sem instalar; voltar se o scan pedir o Auto-Optimize.
- **Relevância para o pos_venda:** Média · **Free Edition:** Com ressalvas (Ocuparia a última vaga de app (2 de 3 em uso) e depende do Unity AI Gateway, não confirmado no Free Edition.)
- **Camada do framework:** Consumo e Avaliação · **Práticas:** P21, P26 · **Categoria:** Genie e camada semântica
- **O que é:** App para criar, pontuar (IQ scan por regras) e otimizar Genie Agents com benchmarks (Genie Space Optimizer). Substitui o MaxGenie.
- **Como ajudaria no pos_venda:** Dá nota e plano de melhoria para os dois espaços (Analista financeiro e Diretoria) e automatiza o ciclo de benchmark que fizemos à mão no genie.py (24/24).
- **Escolha quando:** Avaliar a qualidade de um espaço Genie, achar instruções e exemplos faltantes, otimizar com base nas perguntas de benchmark, guardar histórico.
- **Como usar:** Clonar como Git folder no workspace e rodar o notebook instalador; apontar para o espaço Genie e rodar o scan e o Auto-Optimize.
- **Repositório:** [databricks-genie-workbench](https://github.com/databricks-solutions/databricks-genie-workbench) · último commit 2026-11-20

#### 19. genierails

- **Recomendação:** Adiado. Decisão do usuário: não mascarar dado pessoal, usado na validação. Retomar se a Genie abrir a mais pessoas.
- **Relevância para o pos_venda:** Média · **Free Edition:** Com ressalvas (Usa Terraform, Data Classification e ABAC; mais indicado para workspace pago.)
- **Camada do framework:** Governança · **Práticas:** P15 · **Categoria:** Qualidade, governança e segurança
- **O que é:** Leva espaços Genie para produção como código: máscaras para cada coluna sensível, testes em dev e liberação de acesso só quando a cobertura é total.
- **Como ajudaria no pos_venda:** Caminho seguro para abrir os espaços do pós-venda a mais pessoas: nenhuma coluna com CPF ou RG fica sem máscara.
- **Escolha quando:** Abrir a Genie a usuários de negócio sem expor dados sensíveis.
- **Como usar:** Seguir o Get started; a ferramenta gera as políticas e um gate de cobertura bloqueia a liberação.
- **Repositório:** [genierails](https://github.com/databricks-solutions/genierails) · último commit 2026-11-17

#### 20. ingestion-workbench

- **Recomendação:** Adiado. Fora do escopo atual (revisão de 22/11): os dados são sintéticos e não há sistema de origem real. Retomar quando o banco de cobrança e apólices for ligado.
- **Relevância para o pos_venda:** Média · **Free Edition:** Com ressalvas (Usa Lakehouse Federation para bancos externos; no Free Edition não há origem real nem rede privada.)
- **Camada do framework:** Dados · **Práticas:** P06 · **Categoria:** Ingestão e streaming
- **O que é:** Copia tabelas de SQL Server, Oracle, PostgreSQL e MySQL para Delta via Lakehouse Federation, de forma incremental e guiada por metadados, com app de operação.
- **Como ajudaria no pos_venda:** Caminho de produção para trocar o gerador sintético pelo banco real do sistema de cobrança e apólices.
- **Escolha quando:** Ingestão em massa de bancos transacionais, estates com milhares de tabelas.
- **Como usar:** Implantar, descrever tabelas como linhas de metadados e acompanhar os jobs na app.
- **Repositório:** [ingestion-workbench](https://github.com/databricks-solutions/ingestion-workbench) · último commit 2026-11-20

#### 21. lakeflow_framework

- **Recomendação:** Adiado. Fora do escopo atual (revisão de 22/11): a carga diária já funciona, com paridade linha a linha. Retomar ao construir um segundo domínio com o mesmo padrão.
- **Relevância para o pos_venda:** Média · **Free Edition:** Com ressalvas (Usa Spark Declarative Pipelines serverless; confira consumo da cota diária.)
- **Camada do framework:** Dados e Qualidade · **Práticas:** P06, P09 · **Categoria:** Pipelines e engenharia de dados
- **O que é:** Framework guiado por metadados para Spark Declarative Pipelines (SDP) em batch e streaming, cobrindo bronze, silver e gold, implantado por bundles.
- **Como ajudaria no pos_venda:** Alternativa para trocar os notebooks escritos à mão do carga_diaria por pipelines declarados, com expectations nativas ao lado do DQX.
- **Escolha quando:** Padronizar dezenas de tabelas medallion, SCD, data vault, modelo dimensional.
- **Como usar:** Descrever fluxos em arquivos de configuração e padrões, implantar com bundle; a documentação traz quick start.
- **Repositório:** [lakeflow_framework](https://github.com/databricks-solutions/lakeflow_framework) · último commit 2026-11-20

#### 22. mlops-quickstart

- **Recomendação:** Adiado. Fora do escopo atual (revisão de 22/11): o projeto não tem modelo de propensão. Retomar se a cobrança pedir priorização por modelo.
- **Relevância para o pos_venda:** Média · **Free Edition:** Com ressalvas (Treino leve em serverless; serving pode não estar disponível.)
- **Camada do framework:** Avaliação e modelos · **Práticas:** — (capacidade nova: modelo de propensão) · **Categoria:** Avaliação, MLOps e modelos
- **O que é:** Exemplo de MLOps de ponta a ponta (feature table, treino, registro no UC, inferência, CI/CD) com o dataset Iris.
- **Como ajudaria no pos_venda:** Esqueleto para um modelo de propensão de regularização das pendências, que priorizaria a cobrança.
- **Escolha quando:** Primeiro modelo em produção com esteira.
- **Como usar:** Seguir o vídeo e adaptar com o Genie Code para seus dados.
- **Repositório:** [mlops-quickstart](https://github.com/databricks-solutions/mlops-quickstart) · último commit 2026-07-22

#### 23. uc-declarative-abac

- **Recomendação:** Adiado. Decisão do usuário: não mascarar dado pessoal, usado na validação. Retomar se a Genie abrir a mais pessoas.
- **Relevância para o pos_venda:** Média · **Free Edition:** Com ressalvas (Depende de ABAC (políticas por tag) disponível no workspace.)
- **Camada do framework:** Governança · **Práticas:** P15 · **Categoria:** Qualidade, governança e segurança
- **O que é:** Define o modelo de controle de acesso por atributos (ABAC) em YAML versionado: máscaras de coluna, filtros de linha e grants por tag.
- **Como ajudaria no pos_venda:** Usa as tags de classificação já aplicadas para mascarar CPF e RG para o analista e liberar ao time de cobrança, sem escrever política tabela a tabela.
- **Escolha quando:** Mascarar PII por tag, filtros por região ou carteira, governança como código.
- **Como usar:** Escrever os YAML, rodar a CLI uc-abac (ou GitHub Action) que compara com o estado atual e aplica só a diferença.
- **Repositório:** [uc-declarative-abac](https://github.com/databricks-solutions/uc-declarative-abac) · último commit 2026-11-14

#### 24. databricks-waf

- **Recomendação:** Adiado. App com Lakebase; serve para preparar a ida para produção.
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Fundação e Operação · **Práticas:** P01, P28 · **Categoria:** Plataforma, infraestrutura e custos
- **O que é:** App que avalia workspace ou conta contra os 7 pilares do Well-Architected Framework e gera planos de melhoria com evidências.
- **Como ajudaria no pos_venda:** Checklist de prontidão para levar o pós-venda à produção.
- **Escolha quando:** Revisão de arquitetura com evidências.
- **Como usar:** Clonar o release, vincular recursos, instalar e rodar a primeira avaliação.
- **Repositório:** [databricks-waf](https://github.com/databricks-solutions/databricks-waf) · último commit 2026-11-20

### Só se a necessidade mudar (69)

#### 25. databricks-api-explorer

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Sim (Roda localmente com o perfil do CLI.)
- **Camada do framework:** Consumo (apps) · **Práticas:** P22 · **Categoria:** Apps e ferramentas de app
- **O que é:** Navegador interativo das APIs REST do Databricks (workspace e conta), com formulários e execução de SQL.
- **Como ajudaria no pos_venda:** Ajuda a explorar APIs pouco documentadas que usamos (domínios, knowledge pages, tag policies).
- **Escolha quando:** Explorar endpoints antes de automatizar.
- **Como usar:** Rodar localmente com o perfil do CLI ou implantar como App.
- **Repositório:** [databricks-api-explorer](https://github.com/databricks-solutions/databricks-api-explorer) · último commit 2026-08-03

#### 26. vibe-coding-workshop-app

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Sim (O README afirma que roda no Free Edition.)
- **Camada do framework:** Fundação (ferramentas) · **Práticas:** P02 · **Categoria:** Ferramentas para coding agents
- **O que é:** App de workshop de vibe coding que roda no Free Edition.
- **Como ajudaria no pos_venda:** Aprendizado.
- **Escolha quando:** Treinar o time em desenvolvimento assistido.
- **Como usar:** Instalar e seguir os comandos do README.
- **Repositório:** [vibe-coding-workshop-app](https://github.com/databricks-solutions/vibe-coding-workshop-app) · último commit 2026-11-17

#### 27. waf-assessment-tool

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Sim
- **Camada do framework:** Fundação e Operação · **Práticas:** P01, P28 · **Categoria:** Plataforma, infraestrutura e custos
- **O que é:** PWA para conduzir avaliações do Well-Architected Framework com clientes.
- **Como ajudaria no pos_venda:** Mesmo benefício, em versão questionário.
- **Escolha quando:** Workshop de arquitetura.
- **Como usar:** Abrir o app e preencher a avaliação.
- **Repositório:** [waf-assessment-tool](https://github.com/databricks-solutions/waf-assessment-tool) · último commit 2025-12-12

#### 28. adtech-solutions

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Referência (workshops e demos) · **Práticas:** — · **Categoria:** Workshops, demos e coleções
- **O que é:** Workshops e arquiteturas de referência para AdTech (data collaboration, AI/BI, agentes, apps e Lakebase).
- **Como ajudaria no pos_venda:** Pouco aplicável.
- **Escolha quando:** Mídia e publicidade.
- **Como usar:** Escolher a série e a sessão.
- **Repositório:** [adtech-solutions](https://github.com/databricks-solutions/adtech-solutions) · último commit 2026-06-12

#### 29. agent-control-plane

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (agentes e IA generativa) · **Práticas:** — · **Categoria:** Agentes e IA generativa
- **O que é:** App de governança e observabilidade de agentes, endpoints e uso do Unity Gateway entre workspaces.
- **Como ajudaria no pos_venda:** Não se aplica sem agentes em produção.
- **Escolha quando:** Inventário e custo de agentes em produção.
- **Como usar:** Seguir o Quick Start e os pré-requisitos.
- **Repositório:** [agent-control-plane](https://github.com/databricks-solutions/agent-control-plane) · último commit 2026-11-18

#### 30. agent-monitoring-demo-app

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (agentes e IA generativa) · **Práticas:** — · **Categoria:** Agentes e IA generativa
- **O que é:** Template de agente com chat em Databricks Apps e monitoramento por MLflow 3.
- **Como ajudaria no pos_venda:** Base para um agente do pós-venda com observabilidade.
- **Escolha quando:** Começar um agente com tracing desde o início.
- **Como usar:** Seguir o Quick Start e implantar.
- **Repositório:** [agent-monitoring-demo-app](https://github.com/databricks-solutions/agent-monitoring-demo-app) · último commit 2025-07-02

#### 31. agentbricks-utilities

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (agentes e IA generativa) · **Práticas:** — · **Categoria:** Agentes e IA generativa
- **O que é:** Utilitários que estendem Agent Bricks e AI Functions para cobrir lacunas do produto.
- **Como ajudaria no pos_venda:** Pontual.
- **Escolha quando:** Melhorias de Agent Bricks em POCs.
- **Como usar:** Instalar e usar o utilitário desejado.
- **Repositório:** [agentbricks-utilities](https://github.com/databricks-solutions/agentbricks-utilities) · último commit 2026-01-13

#### 32. agentic-customer-support

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (agentes e IA generativa) · **Práticas:** — · **Categoria:** Agentes e IA generativa
- **O que é:** Sistema multiagente de atendimento (telecom) com supervisor, vector search, ferramentas e monitoramento.
- **Como ajudaria no pos_venda:** Modelo para um copiloto de atendimento de pós-venda que consulta pendências e políticas.
- **Escolha quando:** Copiloto de atendente, respostas com dados estruturados e documentos.
- **Como usar:** Configurar o ambiente e seguir geração de dados e deploy.
- **Repositório:** [agentic-customer-support](https://github.com/databricks-solutions/agentic-customer-support) · último commit 2026-01-27

#### 33. agentic-starter-journey

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Fundação (ferramentas) · **Práticas:** P02 · **Categoria:** Ferramentas para coding agents
- **O que é:** Runbooks para agentes de código, da conta vazia ao projeto implantado.
- **Como ajudaria no pos_venda:** Pouco ganho; o projeto já está implantado.
- **Escolha quando:** Onboarding automatizado.
- **Como usar:** Apontar o agente para a página do runbook.
- **Repositório:** [agentic-starter-journey](https://github.com/databricks-solutions/agentic-starter-journey) · último commit 2026-09-19

#### 34. agentops-stacks

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (agentes e IA generativa) · **Práticas:** — · **Categoria:** Agentes e IA generativa
- **O que é:** Template de bundle e plugin para projetos multiagente LangGraph em produção (dev, staging, prod, CI/CD, avaliação).
- **Como ajudaria no pos_venda:** Só se o pós-venda ganhar agentes próprios.
- **Escolha quando:** Padronizar projetos de agentes.
- **Como usar:** Gerar o projeto pela CLI ou pelo assistente de código.
- **Repositório:** [agentops-stacks](https://github.com/databricks-solutions/agentops-stacks) · último commit 2026-11-19

#### 35. agents-with-mcp-on-databricks-apps

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (agentes e IA generativa) · **Práticas:** — · **Categoria:** Agentes e IA generativa
- **O que é:** Laboratório de agentes com LangGraph, funções do UC, MCP, Unity AI Gateway e memória gerenciada.
- **Como ajudaria no pos_venda:** Aprendizado para uma eventual camada de agentes sobre o pós-venda.
- **Escolha quando:** Aprender a construir agentes governados.
- **Como usar:** Clonar no workspace e seguir os labs 1 a 4.
- **Repositório:** [agents-with-mcp-on-databricks-apps](https://github.com/databricks-solutions/agents-with-mcp-on-databricks-apps) · último commit 2026-07-09

#### 36. ai-governance

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (agentes e IA generativa) · **Práticas:** — · **Categoria:** Agentes e IA generativa
- **O que é:** Workshop do Unity AI Gateway (escolha, custo e controle de modelos, ferramentas e agentes) como App.
- **Como ajudaria no pos_venda:** Não se aplica agora.
- **Escolha quando:** Governança de IA corporativa.
- **Como usar:** Implantar o bundle e conduzir o workshop.
- **Repositório:** [ai-governance](https://github.com/databricks-solutions/ai-governance) · último commit 2026-11-16

#### 37. aibi-dashboards-external-embedding

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas (Embedding externo depende de configuração do workspace.)
- **Camada do framework:** Consumo (apps) · **Práticas:** P22 · **Categoria:** Apps e ferramentas de app
- **O que é:** Template para embutir painéis AI/BI em aplicação externa com login e segurança por linha.
- **Como ajudaria no pos_venda:** Permitiria mostrar a cada corretor só as pendências dele num portal externo.
- **Escolha quando:** Painéis para corretores ou parceiros dentro do portal deles.
- **Como usar:** Configurar o .env, o backend Flask (gera token) e o frontend React.
- **Repositório:** [aibi-dashboards-external-embedding](https://github.com/databricks-solutions/aibi-dashboards-external-embedding) · último commit 2025-11-11

#### 38. aibi-genie-enablement-lab

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Semântica e Consumo · **Práticas:** P18, P19, P21 · **Categoria:** Genie e camada semântica
- **O que é:** Laboratório para público não técnico que mostra por que definir métricas uma vez (metric views) evita números divergentes.
- **Como ajudaria no pos_venda:** Roteiro pronto para treinar a equipe financeira que vai usar a Genie e os painéis do pós-venda.
- **Escolha quando:** Treinamento de analistas de negócio em AI/BI e Genie, narrativa de 'uma métrica, uma verdade'.
- **Como usar:** Instrutor clona o repo, roda setup/00_instructor_setup; cada aluno segue os notebooks em sua pasta.
- **Repositório:** [aibi-genie-enablement-lab](https://github.com/databricks-solutions/aibi-genie-enablement-lab) · último commit 2026-09-01

#### 39. apx

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps) · **Práticas:** P22 · **Categoria:** Apps e ferramentas de app
- **O que é:** Toolkit (CLI em Rust) para criar, desenvolver e implantar Databricks Apps com FastAPI e React.
- **Como ajudaria no pos_venda:** Opção para uma app própria do pós-venda.
- **Escolha quando:** Apps full-stack com tipagem e recarga rápida.
- **Como usar:** Seguir o quickstart do apx para gerar e rodar o projeto.
- **Repositório:** [apx](https://github.com/databricks-solutions/apx) · último commit 2026-04-07

#### 40. brickhouse-brands-demo

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps) · **Práticas:** P22 · **Categoria:** Apps e ferramentas de app
- **O que é:** Demo de gestão de estoque com React, FastAPI e Lakebase.
- **Como ajudaria no pos_venda:** Referência de app operacional, sem ganho direto.
- **Escolha quando:** Exemplo de app operacional completa.
- **Como usar:** Autenticar o CLI, configurar e implantar.
- **Repositório:** [brickhouse-brands-demo](https://github.com/databricks-solutions/brickhouse-brands-demo) · último commit 2025-06-20

#### 41. claude-databricks-app-template

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps) · **Práticas:** P22 · **Categoria:** Apps e ferramentas de app
- **O que é:** Template de App FastAPI + React com fluxo /dba no Claude Code, da ideia ao deploy.
- **Como ajudaria no pos_venda:** Opção para criar rapidamente uma app do pós-venda.
- **Escolha quando:** Criar apps com assistente de código.
- **Como usar:** Usar como template no GitHub e rodar /dba.
- **Repositório:** [claude-databricks-app-template](https://github.com/databricks-solutions/claude-databricks-app-template) · último commit 2025-08-27

#### 42. consort

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Fundação (ferramentas) · **Práticas:** P02 · **Categoria:** Ferramentas para coding agents
- **O que é:** Conjunto de agentes por papel, orientado a especificação e testes, com branches reais de Lakebase.
- **Como ajudaria no pos_venda:** Não necessário.
- **Escolha quando:** Disciplina de engenharia em código gerado por IA.
- **Como usar:** Seguir o quick start e instalar o kit.
- **Repositório:** [consort](https://github.com/databricks-solutions/consort) · último commit 2026-11-22

#### 43. custom-mcp-databricks-app

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (agentes e IA generativa) · **Práticas:** — · **Categoria:** Agentes e IA generativa
- **O que é:** Servidor MCP próprio hospedado em Databricks Apps, com prompts e ferramentas.
- **Como ajudaria no pos_venda:** Poderia expor ferramentas do pós-venda (consultar pendência, rodar a carga) para assistentes.
- **Escolha quando:** Dar a assistentes de código acesso governado ao workspace.
- **Como usar:** Adicionar prompts em markdown e ferramentas em Python; implantar e registrar no Claude.
- **Repositório:** [custom-mcp-databricks-app](https://github.com/databricks-solutions/custom-mcp-databricks-app) · último commit 2025-10-10

#### 44. custom-mlflow-review-app

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Avaliação e modelos · **Práticas:** P24 · **Categoria:** Avaliação, MLOps e modelos
- **O que é:** Template de app de revisão do MLflow customizada para especialistas rotularem traces.
- **Como ajudaria no pos_venda:** Só com agentes no projeto.
- **Escolha quando:** Coleta de rótulos de especialistas.
- **Como usar:** Usar o comando /review-app no Claude Code ou seguir o guia.
- **Repositório:** [custom-mlflow-review-app](https://github.com/databricks-solutions/custom-mlflow-review-app) · último commit 2025-11-03

#### 45. cybersec-workspace-detection-app

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas (Depende de system.access.audit.)
- **Camada do framework:** Qualidade e Governança · **Práticas:** P09 a P16 · **Categoria:** Qualidade, governança e segurança
- **O que é:** 35 detecções de segurança sobre os logs de auditoria (eventos e comportamento), com espaço Genie para investigar.
- **Como ajudaria no pos_venda:** Útil em produção para vigiar quem acessa dados de clientes; no Free Edition pessoal o ganho é pequeno.
- **Escolha quando:** Monitoramento de acesso suspeito, investigação de incidentes, threat hunting.
- **Como usar:** Rodar os notebooks de detecção ou perguntar à Genie de auditoria.
- **Repositório:** [cybersec-workspace-detection-app](https://github.com/databricks-solutions/cybersec-workspace-detection-app) · último commit 2026-11-22

#### 46. dais-2024-dw-workshop

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Fundação e Dados · **Práticas:** P02, P05 a P08 · **Categoria:** Pipelines e engenharia de dados
- **O que é:** Implementações do benchmark TPC-DI (integração de dados) em Databricks.
- **Como ajudaria no pos_venda:** Referência de modelagem e SCD; não traz ganho direto.
- **Escolha quando:** Referência de cargas com SCD e integração de dados em larga escala.
- **Como usar:** Gerar dados e workflows com o setup e executar uma das variantes.
- **Repositório:** [dais-2024-dw-workshop](https://github.com/databricks-solutions/dais-2024-dw-workshop) · último commit 2024-06-12

#### 47. databricks-ab-testing

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Avaliação e modelos · **Práticas:** P24 · **Categoria:** Avaliação, MLOps e modelos
- **O que é:** Framework de testes A/B com atribuição determinística e avaliação estatística para modelos, agentes e apps.
- **Como ajudaria no pos_venda:** Poderia testar réguas de cobrança alternativas, se virarem um serviço.
- **Escolha quando:** Comparar versões de modelo ou de agente.
- **Como usar:** Seguir o guia de deploy e a documentação de arquitetura.
- **Repositório:** [databricks-ab-testing](https://github.com/databricks-solutions/databricks-ab-testing) · último commit 2026-06-01

#### 48. databricks-agent-foundry

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (agentes e IA generativa) · **Práticas:** — · **Categoria:** Agentes e IA generativa
- **O que é:** Blocos e contrato para equipes construírem apps e agentes iguais entre dev, staging e prod.
- **Como ajudaria no pos_venda:** Não se aplica ao escopo atual.
- **Escolha quando:** Governança de vários times de agentes.
- **Como usar:** O time de plataforma faz fork; os times de aplicação geram repos com agent-foundry init.
- **Repositório:** [databricks-agent-foundry](https://github.com/databricks-solutions/databricks-agent-foundry) · último commit 2026-11-17

#### 49. databricks-apps-cookbook

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps) · **Práticas:** P22 · **Categoria:** Apps e ferramentas de app
- **O que é:** Receitas prontas para apps Dash, Streamlit, Reflex e FastAPI no Databricks Apps (ler e gravar tabelas, chamar modelos, disparar jobs).
- **Como ajudaria no pos_venda:** Atalho se o pós-venda precisar de uma tela operacional (ex.: registrar tratativa de pendência).
- **Escolha quando:** App de tratativa com gravação, formulários, gatilho de workflow.
- **Como usar:** Ver a receita no site apps-cookbook.dev e copiar o trecho para a sua app.
- **Repositório:** [databricks-apps-cookbook](https://github.com/databricks-solutions/databricks-apps-cookbook) · último commit 2026-10-21

#### 50. databricks-apps-examples

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps) · **Práticas:** P22 · **Categoria:** Apps e ferramentas de app
- **O que é:** Exemplos de apps feitos pelo campo (shell, write-back, autenticação, vector search).
- **Como ajudaria no pos_venda:** Mesmo benefício do cookbook, com exemplos de write-back.
- **Escolha quando:** Inspiração para apps com gravação e autenticação.
- **Como usar:** Escolher a pasta do exemplo e seguir o README.
- **Repositório:** [databricks-apps-examples](https://github.com/databricks-solutions/databricks-apps-examples) · último commit 2026-01-19

#### 51. databricks-blogposts

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Referência (workshops e demos) · **Práticas:** — · **Categoria:** Workshops, demos e coleções
- **O que é:** Código dos posts do blog da Databricks, uma pasta por post.
- **Como ajudaria no pos_venda:** Posts de SQL scripting e stored procedures podem simplificar a lógica da carga diária.
- **Escolha quando:** Stored procedures em SQL, gitflow com bundles, framework orientado a configuração, debug de streaming.
- **Como usar:** Abrir a pasta do post desejado.
- **Repositório:** [databricks-blogposts](https://github.com/databricks-solutions/databricks-blogposts) · último commit 2026-11-13

#### 52. databricks-bot-service

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (agentes e IA generativa) · **Práticas:** — · **Categoria:** Agentes e IA generativa
- **O que é:** Exemplo de bot do Microsoft Teams ligado a um endpoint de agente.
- **Como ajudaria no pos_venda:** Permitiria ao CFO perguntar pelo Teams, se houver um agente sobre a Genie.
- **Escolha quando:** Levar agentes para o Teams.
- **Como usar:** Configurar o bot e o endpoint.
- **Repositório:** [databricks-bot-service](https://github.com/databricks-solutions/databricks-bot-service) · último commit 2025-11-10

#### 53. databricks-genai-app-template

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (agentes e IA generativa) · **Práticas:** — · **Categoria:** Agentes e IA generativa
- **O que é:** Template de app de chat (React + FastAPI) para agentes, com histórico opcional em Lakebase.
- **Como ajudaria no pos_venda:** Front-end se um agente do pós-venda for criado.
- **Escolha quando:** Front-end de agente pronto.
- **Como usar:** Configurar config/app.json com o endpoint do agente e implantar.
- **Repositório:** [databricks-genai-app-template](https://github.com/databricks-solutions/databricks-genai-app-template) · último commit 2025-12-30

#### 54. databricks-migrator-with-llm

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Dados (migração) · **Práticas:** — · **Categoria:** Migração
- **O que é:** App que converte SQL de outros dialetos (Oracle, Teradata, T-SQL...) para Databricks SQL com LLM e valida.
- **Como ajudaria no pos_venda:** Útil se as regras atuais de cobrança estiverem em SQL legado do data warehouse da seguradora.
- **Escolha quando:** Migração de consultas legadas.
- **Como usar:** Clonar como Git folder e implantar a App.
- **Repositório:** [databricks-migrator-with-llm](https://github.com/databricks-solutions/databricks-migrator-with-llm) · último commit 2025-11-03

#### 55. databricks-replicator

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Dados (migração) · **Práticas:** — · **Categoria:** Migração
- **O que é:** Replica dados e metadados do UC entre ambientes (Delta Sharing, deep clone, Auto Loader), com reconciliação.
- **Como ajudaria no pos_venda:** Mesmo cenário de saída do Free Edition.
- **Escolha quando:** DR, migração, data mesh multinuvem.
- **Como usar:** Configurar as operações de backup, replicação e reconciliação.
- **Repositório:** [databricks-replicator](https://github.com/databricks-solutions/databricks-replicator) · último commit 2026-11-22

#### 56. databricks-workshops

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Referência (workshops e demos) · **Práticas:** — · **Categoria:** Workshops, demos e coleções
- **O que é:** Workshops com botão Open in Databricks que se instalam no workspace.
- **Como ajudaria no pos_venda:** O dbsql_workshop ajuda a treinar analistas no SQL da gold.
- **Escolha quando:** Workshop de DBSQL e outros.
- **Como usar:** Clicar em Open in Databricks no README do workshop.
- **Repositório:** [databricks-workshops](https://github.com/databricks-solutions/databricks-workshops) · último commit 2026-11-20

#### 57. databricks_demos_br

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Referência (workshops e demos) · **Práticas:** — · **Categoria:** Workshops, demos e coleções
- **O que é:** Demos em português do Data + AI World Tour São Paulo 2025.
- **Como ajudaria no pos_venda:** Material pronto em português para apresentações junto com o ROTEIRO do pos_venda.
- **Escolha quando:** Material de demonstração em português.
- **Como usar:** Abrir a pasta daiwt_sp_2025.
- **Repositório:** [databricks_demos_br](https://github.com/databricks-solutions/databricks_demos_br) · último commit 2025-09-29

#### 58. dbx-unifiedchat

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Semântica e Consumo · **Práticas:** P18, P19, P21 · **Categoria:** Genie e camada semântica
- **O que é:** Sistema multiagente (LangGraph, Genie, Lakebase) que responde perguntas que cruzam vários domínios e espaços Genie.
- **Como ajudaria no pos_venda:** Poderia unir os espaços Analista e Diretoria e a qualidade de dados num chat único; vale mais quando houver outros domínios além do pós-venda.
- **Escolha quando:** Uma única conversa sobre dados de várias áreas, síntese de respostas de vários espaços.
- **Como usar:** Seguir o Quick Start, registrar os espaços Genie e implantar a App de chat.
- **Repositório:** [dbx-unifiedchat](https://github.com/databricks-solutions/dbx-unifiedchat) · último commit 2026-06-13

#### 59. devrel-examples

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Referência (workshops e demos) · **Práticas:** — · **Categoria:** Workshops, demos e coleções
- **O que é:** Notebooks e demos do time de Developer Relations (Foundation Model APIs, Vector Search, MLflow).
- **Como ajudaria no pos_venda:** Aprendizado.
- **Escolha quando:** Aprender recursos de IA.
- **Como usar:** Importar o notebook desejado.
- **Repositório:** [devrel-examples](https://github.com/databricks-solutions/devrel-examples) · último commit 2026-11-13

#### 60. genie-a2a-agent

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Semântica e Consumo · **Práticas:** P18, P19, P21 · **Categoria:** Genie e camada semântica
- **O que é:** Servidor do protocolo A2A (agente para agente) que expõe um espaço Genie como agente.
- **Como ajudaria no pos_venda:** Permitiria que um agente corporativo externo consultasse o espaço do pós-venda; hoje não há esse cenário.
- **Escolha quando:** Integrar a Genie em ecossistemas multiagente de outros fornecedores.
- **Como usar:** Configurar o ID do espaço, rodar deploy.sh e descobrir o agente pelo Agent Card.
- **Repositório:** [genie-a2a-agent](https://github.com/databricks-solutions/genie-a2a-agent) · último commit 2026-03-18

#### 61. genie-api-cache-queue

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Semântica e Consumo · **Práticas:** P18, P19, P21 · **Categoria:** Genie e camada semântica
- **O que é:** Camada de cache semântico, fila com retentativa e roteamento na frente da API da Genie, implantada como App.
- **Como ajudaria no pos_venda:** Só ajuda se a Genie do pós-venda for embutida numa app com muitos usuários; no uso atual (CFO e analista) não é necessário.
- **Escolha quando:** Apps com muitos usuários perguntando à Genie, picos de uso, roteamento entre vários espaços.
- **Como usar:** Deploy com o bundle, criar um gateway por espaço Genie e trocar a URL base dos clientes.
- **Repositório:** [genie-api-cache-queue](https://github.com/databricks-solutions/genie-api-cache-queue) · último commit 2026-05-13

#### 62. genie-code-skills-demo

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Fundação (ferramentas) · **Práticas:** P02 · **Categoria:** Ferramentas para coding agents
- **O que é:** Skills, instruções e MCP do Genie Code para impor padrões de engenharia de dados.
- **Como ajudaria no pos_venda:** Permitiria codificar os padrões do pos_venda (nomes, DQX, tags) para o Genie Code seguir.
- **Escolha quando:** Padronizar código gerado por IA no workspace.
- **Como usar:** Instalar as skills, configurar MCP opcional e instruções.
- **Repositório:** [genie-code-skills-demo](https://github.com/databricks-solutions/genie-code-skills-demo) · último commit 2026-09-15

#### 63. genie-visualization-interface

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Semântica e Consumo · **Práticas:** P18, P19, P21 · **Categoria:** Genie e camada semântica
- **O que é:** Interface de conversa com a Genie (Angular + Node) que recomenda gráficos e mapas.
- **Como ajudaria no pos_venda:** Opcional: a interface nativa da Genie já atende o CFO e o analista.
- **Escolha quando:** Front-end próprio para a Genie com gráficos automáticos.
- **Como usar:** Configurar app.yaml com o espaço Genie e implantar como App.
- **Repositório:** [genie-visualization-interface](https://github.com/databricks-solutions/genie-visualization-interface) · último commit 2026-03-19

#### 64. hospital-control-tower-agentic-nba

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (agentes e IA generativa) · **Práticas:** — · **Categoria:** Agentes e IA generativa
- **O que é:** Apesar do nome, o README descreve uma plataforma de inteligência de investimentos: agente conversacional para gestores de portfólio que consulta dados e políticas.
- **Como ajudaria no pos_venda:** Inspiração para um assistente do CFO que junte a Genie com documentos de política de cobrança.
- **Escolha quando:** Copiloto para executivos de finanças com dados e documentos.
- **Como usar:** Setup com um comando ou via Git folder.
- **Repositório:** [hospital-control-tower-agentic-nba](https://github.com/databricks-solutions/hospital-control-tower-agentic-nba) · último commit 2026-07-23

#### 65. judge-builder

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Avaliação e modelos · **Práticas:** P24 · **Categoria:** Avaliação, MLOps e modelos
- **O que é:** Plataforma para criar e alinhar juízes LLM com feedback humano.
- **Como ajudaria no pos_venda:** Só com agentes no projeto.
- **Escolha quando:** Avaliação automática alinhada ao negócio.
- **Como usar:** Criar o juiz, convidar especialistas e otimizar.
- **Repositório:** [judge-builder](https://github.com/databricks-solutions/judge-builder) · último commit 2026-02-11

#### 66. lakebase-cicd-blueprint

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps com Postgres) · **Práticas:** — · **Categoria:** Lakebase (Postgres)
- **O que é:** CI/CD de Lakebase: tabela sincronizada, roles, grants, índices e view de consumo, por bundle ou Terraform + Liquibase.
- **Como ajudaria no pos_venda:** Só se o pos_venda ganhar um banco operacional próprio.
- **Escolha quando:** Esteira de deploy de banco operacional.
- **Como usar:** Seguir o caminho com bundles e o passo de roles e tabelas de origem.
- **Repositório:** [lakebase-cicd-blueprint](https://github.com/databricks-solutions/lakebase-cicd-blueprint) · último commit 2026-10-30

#### 67. lakebase-cookbook

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps com Postgres) · **Práticas:** — · **Categoria:** Lakebase (Postgres)
- **O que é:** Receitas e guias de Lakebase (agentes, apps, dados, experiência de desenvolvimento).
- **Como ajudaria no pos_venda:** Consulta útil para manter o Lakebase do DQX Studio e para uma futura app operacional.
- **Escolha quando:** Padrões de app com Postgres gerenciado.
- **Como usar:** Navegar no site lakebase-cookbook.com e implantar o exemplo pelo bundle dele.
- **Repositório:** [lakebase-cookbook](https://github.com/databricks-solutions/lakebase-cookbook) · último commit 2026-11-11

#### 68. lakebase-fastapi-app

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps com Postgres) · **Práticas:** — · **Categoria:** Lakebase (Postgres)
- **O que é:** API FastAPI que serve dados de uma tabela sincronizada no Lakebase, com OAuth e pool de conexões.
- **Como ajudaria no pos_venda:** Base para uma API de consulta de pendência por apólice (corretor, portal do cliente).
- **Escolha quando:** API de consulta para canais digitais, URA ou parceiros.
- **Como usar:** Configurar as variáveis do bundle e implantar como App.
- **Repositório:** [lakebase-fastapi-app](https://github.com/databricks-solutions/lakebase-fastapi-app) · último commit 2026-06-10

#### 69. lakebase-for-ai-developers

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps com Postgres) · **Práticas:** — · **Categoria:** Lakebase (Postgres)
- **O que é:** Copiloto multiagente de planejamento de supply chain com estado no Lakebase, pgvector e aprovação humana.
- **Como ajudaria no pos_venda:** Referência se for criar um agente de tratativa de pendências com aprovação.
- **Escolha quando:** Agentes com memória durável e aprovação humana.
- **Como usar:** Configurar com Claude Code e implantar como App.
- **Repositório:** [lakebase-for-ai-developers](https://github.com/databricks-solutions/lakebase-for-ai-developers) · último commit 2026-10-01

#### 70. lakebase-online-ml

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps com Postgres) · **Práticas:** — · **Categoria:** Lakebase (Postgres)
- **O que é:** App de varejo que usa Lakebase como feature store online para servir modelos com baixa latência.
- **Como ajudaria no pos_venda:** Padrão para servir um futuro score de propensão de pagamento em tempo real.
- **Escolha quando:** Scoring online com features em Postgres.
- **Como usar:** Rodar com apx em modo dev e implantar.
- **Repositório:** [lakebase-online-ml](https://github.com/databricks-solutions/lakebase-online-ml) · último commit 2026-05-19

#### 71. lakebase-poc-accelerator

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps com Postgres) · **Práticas:** — · **Categoria:** Lakebase (Postgres)
- **O que é:** App para POC de OLTP/reverse ETL no Lakebase: dimensionamento, testes de concorrência (pgbench) e otimização de índices.
- **Como ajudaria no pos_venda:** Não necessário hoje.
- **Escolha quando:** Provar desempenho de Lakebase para uma carga transacional.
- **Como usar:** Implantar a App e seguir Deploy, Test e Optimize.
- **Repositório:** [lakebase-poc-accelerator](https://github.com/databricks-solutions/lakebase-poc-accelerator) · último commit 2026-07-27

#### 72. lakebase-solutions

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps com Postgres) · **Práticas:** — · **Categoria:** Lakebase (Postgres)
- **O que é:** Sobe um workshop completo de Lakebase com módulos opcionais numa única execução, e derruba depois.
- **Como ajudaria no pos_venda:** Aprendizado.
- **Escolha quando:** Demonstração de Lakebase integrado à plataforma.
- **Como usar:** Rodar pelo notebook ou com um coding agent.
- **Repositório:** [lakebase-solutions](https://github.com/databricks-solutions/lakebase-solutions) · último commit 2026-11-06

#### 73. lakebase-workshop

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps com Postgres) · **Práticas:** — · **Categoria:** Lakebase (Postgres)
- **O que é:** Workshop prático de Lakebase com labs por perfil e console de laboratório.
- **Como ajudaria no pos_venda:** Aprendizado; o projeto usa Lakebase apenas pelo DQX Studio.
- **Escolha quando:** Aprender Lakebase.
- **Como usar:** Clonar, rodar o setup e escolher um lab.
- **Repositório:** [lakebase-workshop](https://github.com/databricks-solutions/lakebase-workshop) · último commit 2026-08-20

#### 74. lakebridge-workshop

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Dados (migração) · **Práticas:** — · **Categoria:** Migração
- **O que é:** Workshop do Lakebridge (Analyzer, Transpile, Reconcile) para migrar DW e ETL.
- **Como ajudaria no pos_venda:** Mesmo cenário de migração de legado.
- **Escolha quando:** Avaliar e converter um DW legado.
- **Como usar:** Seguir os cenários Synapse, Reconcile e DataStage.
- **Repositório:** [lakebridge-workshop](https://github.com/databricks-solutions/lakebridge-workshop) · último commit 2026-06-10

#### 75. livevalidator

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Fundação e Dados · **Práticas:** P02, P05 a P08 · **Categoria:** Pipelines e engenharia de dados
- **O que é:** Plataforma que compara tabelas entre bancos diferentes: schema, contagem e diferenças linha a linha.
- **Como ajudaria no pos_venda:** Em produção, conciliaria o sistema de cobrança com a bronze; com dados sintéticos não há origem para comparar.
- **Escolha quando:** Reconciliação em migrações, conferência origem x lakehouse.
- **Como usar:** Seguir o Quick Start, cadastrar origem e destino e agendar validações.
- **Repositório:** [livevalidator](https://github.com/databricks-solutions/livevalidator) · último commit 2026-08-26

#### 76. mcp-workshop

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (agentes e IA generativa) · **Práticas:** — · **Categoria:** Agentes e IA generativa
- **O que é:** Workshop de MCP: servidores gerenciados, externos, próprios e integração com IDE.
- **Como ajudaria no pos_venda:** Aprendizado.
- **Escolha quando:** Aprender MCP no Databricks.
- **Como usar:** Rodar o setup interativo que cria o ambiente do participante.
- **Repositório:** [mcp-workshop](https://github.com/databricks-solutions/mcp-workshop) · último commit 2025-12-09

#### 77. microbricks

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps) · **Práticas:** P22 · **Categoria:** Apps e ferramentas de app
- **O que é:** Blueprint de microsserviços em Databricks Apps com Lakebase por serviço, OBO e CI/CD.
- **Como ajudaria no pos_venda:** Excesso para o escopo atual.
- **Escolha quando:** Arquitetura de microsserviços na plataforma.
- **Como usar:** Seguir o quickstart e os workflows de GitHub Actions.
- **Repositório:** [microbricks](https://github.com/databricks-solutions/microbricks) · último commit 2026-07-29

#### 78. mlflow-demo

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Avaliação e modelos · **Práticas:** P24 · **Categoria:** Avaliação, MLOps e modelos
- **O que é:** Demo dos recursos GenAI do MLflow 3 (avaliação, monitoramento, melhoria de qualidade).
- **Como ajudaria no pos_venda:** Aprendizado.
- **Escolha quando:** Aprender avaliação de apps de IA.
- **Como usar:** Instalação automatizada como App com notebooks guiados.
- **Repositório:** [mlflow-demo](https://github.com/databricks-solutions/mlflow-demo) · último commit 2025-08-28

#### 79. model-landscape

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Avaliação e modelos · **Práticas:** P24 · **Categoria:** Avaliação, MLOps e modelos
- **O que é:** Observabilidade de modelos nativa (SDK mlflow-lens e App de drift sobre tabelas de inferência).
- **Como ajudaria no pos_venda:** Útil depois que existir um modelo de propensão.
- **Escolha quando:** Drift e degradação de modelos em produção.
- **Como usar:** Seguir o deploy rápido da documentação.
- **Repositório:** [model-landscape](https://github.com/databricks-solutions/model-landscape) · último commit 2026-06-09

#### 80. monitoring-declarative-pipeline-refresh-behavior

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Fundação e Dados · **Práticas:** P02, P05 a P08 · **Categoria:** Pipelines e engenharia de dados
- **O que é:** Kit de observabilidade do refresh de materialized views em Declarative Pipelines (incremental ou recompute, custo).
- **Como ajudaria no pos_venda:** Só útil se o pos_venda migrar para SDP com materialized views.
- **Escolha quando:** Entender por que uma MV recomputa tudo, custo por refresh.
- **Como usar:** Implantar o bundle, rodar o job e abrir o painel SQL.
- **Repositório:** [monitoring-declarative-pipeline-refresh-behavior](https://github.com/databricks-solutions/monitoring-declarative-pipeline-refresh-behavior) · último commit 2025-08-05

#### 81. powerbi-on-databricks-migration-accelerator

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Dados (migração) · **Práticas:** — · **Categoria:** Migração
- **O que é:** Reaponta modelos semânticos do Power BI de Snowflake, Redshift, SQL Server etc. para Databricks SQL em massa.
- **Como ajudaria no pos_venda:** Só se a seguradora tiver relatórios Power BI de cobrança em outra fonte.
- **Escolha quando:** Migração de relatórios Power BI sem refazer.
- **Como usar:** Rodar a CLI PowerShell com o arquivo de configuração.
- **Repositório:** [powerbi-on-databricks-migration-accelerator](https://github.com/databricks-solutions/powerbi-on-databricks-migration-accelerator) · último commit 2026-07-23

#### 82. prompt-playground

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (agentes e IA generativa) · **Práticas:** — · **Categoria:** Agentes e IA generativa
- **O que é:** App sem código para testar prompts do Prompt Registry contra endpoints de modelo.
- **Como ajudaria no pos_venda:** Não se aplica agora.
- **Escolha quando:** Iterar prompts com o negócio.
- **Como usar:** Implantar com o bundle e dar permissões ao service principal.
- **Repositório:** [prompt-playground](https://github.com/databricks-solutions/prompt-playground) · último commit 2026-06-11

#### 83. salesforce-zerobus

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Dados · **Práticas:** P06 · **Categoria:** Ingestão e streaming
- **O que é:** Conector de CDC do Salesforce para Delta via Pub/Sub API e Zerobus (Python e Go).
- **Como ajudaria no pos_venda:** Só se o CRM do pós-venda for Salesforce.
- **Escolha quando:** Trazer alterações do CRM quase em tempo real.
- **Como usar:** Entrar em python/ ou go_salesforce_zerobus/, configurar e fazer bundle deploy.
- **Repositório:** [salesforce-zerobus](https://github.com/databricks-solutions/salesforce-zerobus) · último commit 2026-10-07

#### 84. sdp-explorer

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Fundação e Dados · **Práticas:** P02, P05 a P08 · **Categoria:** Pipelines e engenharia de dados
- **O que é:** App didática com cartões animados de cada recurso do Spark Declarative Pipelines.
- **Como ajudaria no pos_venda:** Material de estudo se for adotar SDP.
- **Escolha quando:** Aprender SDP visualmente, ensinar o time.
- **Como usar:** Implantar a App ou abrir a versão em arquivo único.
- **Repositório:** [sdp-explorer](https://github.com/databricks-solutions/sdp-explorer) · último commit 2026-10-14

#### 85. sdp-rewind-replay

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Fundação e Dados · **Práticas:** P02, P05 a P08 · **Categoria:** Pipelines e engenharia de dados
- **O que é:** Demonstra a API Rewind (time travel de streaming) para corrigir um pipeline com bug sem full refresh.
- **Como ajudaria no pos_venda:** Padrão interessante para os incidentes simulados no projeto, caso a carga vire SDP em streaming.
- **Escolha quando:** Recuperação de incidentes em pipelines de streaming.
- **Como usar:** Implantar o bundle e seguir o cenário de pagamentos inflados em 10x.
- **Repositório:** [sdp-rewind-replay](https://github.com/databricks-solutions/sdp-rewind-replay) · último commit 2026-08-10

#### 86. solution-builder

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Fundação (ferramentas) · **Práticas:** P02 · **Categoria:** Ferramentas para coding agents
- **O que é:** App e CLI em que um agente constrói soluções a partir de blueprints validados (inclui serviços financeiros).
- **Como ajudaria no pos_venda:** Alternativa para gerar demos de outros casos de seguros.
- **Escolha quando:** Demos e POCs rápidos.
- **Como usar:** Rodar a app completa ou a skill de CLI.
- **Repositório:** [solution-builder](https://github.com/databricks-solutions/solution-builder) · último commit 2026-11-16

#### 87. spark-jdbc-ingestor

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Dados · **Práticas:** P06 · **Categoria:** Ingestão e streaming
- **O que é:** Biblioteca para ingestão JDBC simples e eficiente, com filtros e ingestão parcial.
- **Como ajudaria no pos_venda:** Alternativa simples para ingerir o banco de origem quando houver um.
- **Escolha quando:** Ingestão de bancos SQL sem conector gerenciado.
- **Como usar:** Instalar via pip, instanciar JdbcIngestor com URL, usuário e driver.
- **Repositório:** [spark-jdbc-ingestor](https://github.com/databricks-solutions/spark-jdbc-ingestor) · último commit 2025-11-30

#### 88. specialist-offerings

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Referência (workshops e demos) · **Práticas:** — · **Categoria:** Workshops, demos e coleções
- **O que é:** Conteúdo oficial dos Specialist SAs: blueprints de design do UC, DW, engenharia, GenAI e cibersegurança.
- **Como ajudaria no pos_venda:** O uc-design-blueprint ajuda a revisar a organização de catálogos e schemas.
- **Escolha quando:** Métodos e templates de engajamento.
- **Como usar:** Navegar pelas pastas por especialidade.
- **Repositório:** [specialist-offerings](https://github.com/databricks-solutions/specialist-offerings) · último commit 2026-11-12

#### 89. starter-journey

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Referência (workshops e demos) · **Práticas:** — · **Categoria:** Workshops, demos e coleções
- **O que é:** Guia passo a passo para começar no Databricks, da configuração à produção.
- **Como ajudaria no pos_venda:** Aprendizado básico.
- **Escolha quando:** Onboarding de equipes.
- **Como usar:** Ler o site ou rodar localmente.
- **Repositório:** [starter-journey](https://github.com/databricks-solutions/starter-journey) · último commit 2026-11-12

#### 90. vibe-coding-workshop-template

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Fundação (ferramentas) · **Práticas:** P02 · **Categoria:** Ferramentas para coding agents
- **O que é:** Template de produto de dados com 77 skills: medallion, camada semântica, Genie, ML e agentes, com Lakebase e AppKit.
- **Como ajudaria no pos_venda:** Boas práticas parecidas com o que já fizemos; útil para comparar.
- **Escolha quando:** Construir produtos de dados com assistente.
- **Como usar:** Clonar o template e escolher o ponto de partida.
- **Repositório:** [vibe-coding-workshop-template](https://github.com/databricks-solutions/vibe-coding-workshop-template) · último commit 2026-11-17

#### 91. vibescaler

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Avaliação e modelos · **Práticas:** P24 · **Categoria:** Avaliação, MLOps e modelos
- **O que é:** App em que especialistas definem o que é boa resposta e o sistema vira um avaliador automático.
- **Como ajudaria no pos_venda:** Só com agentes no projeto.
- **Escolha quando:** Qualidade de agentes por especialistas.
- **Como usar:** Implantar como App e conduzir a sessão com os especialistas.
- **Repositório:** [vibescaler](https://github.com/databricks-solutions/vibescaler) · último commit 2026-07-17

#### 92. workspace-migration

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Dados (migração) · **Práticas:** — · **Categoria:** Migração
- **O que é:** Bundle que migra objetos do Unity Catalog e do Hive Metastore entre workspaces (catálogos, schemas, grants, tabelas, views).
- **Como ajudaria no pos_venda:** Útil no dia em que o pos_venda sair do Free Edition para um workspace corporativo.
- **Escolha quando:** Consolidação de contas, troca de região.
- **Como usar:** Preencher config.yaml e seguir o fluxo de deploy e operação.
- **Repositório:** [workspace-migration](https://github.com/databricks-solutions/workspace-migration) · último commit 2026-10-05

#### 93. zerobus-ingest-examples

- **Recomendação:** Só se a necessidade mudar
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Com ressalvas
- **Camada do framework:** Dados · **Práticas:** P06 · **Categoria:** Ingestão e streaming
- **O que é:** Exemplos e demos do Zerobus Ingest, API de ingestão por push direto para tabelas Delta.
- **Como ajudaria no pos_venda:** Em produção, eventos de pagamento do gateway poderiam cair direto na bronze, sem arquivos intermediários.
- **Escolha quando:** Eventos em tempo real de sistemas externos, telemetria, logs.
- **Como usar:** Escolher uma demo (REST ou gRPC) e seguir o README dela.
- **Repositório:** [zerobus-ingest-examples](https://github.com/databricks-solutions/zerobus-ingest-examples) · último commit 2026-11-17

### Fora do escopo (37)

#### 94. .github

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Nenhuma · **Práticas:** — · **Categoria:** Modelo vazio ou arquivado
- **O que é:** Configuração e modelo de README da organização.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Nenhum.
- **Como usar:** Nada a usar.
- **Repositório:** [.github](https://github.com/databricks-solutions/.github) · último commit 2025-08-04

#### 95. alert-test-repo-02-pleasedelete

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Nenhuma · **Práticas:** — · **Categoria:** Modelo vazio ou arquivado
- **O que é:** Repositório de teste com README de modelo.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Nenhum.
- **Como usar:** Nada a usar.
- **Repositório:** [alert-test-repo-02-pleasedelete](https://github.com/databricks-solutions/alert-test-repo-02-pleasedelete) · último commit 2025-07-08

#### 96. alteryx-to-databricks-converter

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Dados (migração) · **Práticas:** — · **Categoria:** Migração
- **O que é:** Converte workflows do Alteryx em PySpark, SDP, SQL e Lakeflow Designer.
- **Como ajudaria no pos_venda:** Só se houver fluxos em Alteryx.
- **Escolha quando:** Sair do Alteryx.
- **Como usar:** Enviar o .yxmd pela linha de comando ou app.
- **Repositório:** [alteryx-to-databricks-converter](https://github.com/databricks-solutions/alteryx-to-databricks-converter) · último commit 2026-11-16

#### 97. cspray

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Avaliação e modelos · **Práticas:** P24 · **Categoria:** Avaliação, MLOps e modelos
- **O que é:** Análise distribuída de single-cell RNA com PySpark.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Biologia.
- **Como usar:** Instalar via pip.
- **Repositório:** [cspray](https://github.com/databricks-solutions/cspray) · último commit 2026-11-20

#### 98. dais-2024-dab-mod-orch-template

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Referência (workshops e demos) · **Práticas:** — · **Categoria:** Workshops, demos e coleções
- **O que é:** Template simples de bundle com três jobs (DAIS 2024).
- **Como ajudaria no pos_venda:** Superado pelos bundles do projeto.
- **Escolha quando:** Primeiro bundle.
- **Como usar:** Inicializar a partir do template.
- **Repositório:** [dais-2024-dab-mod-orch-template](https://github.com/databricks-solutions/dais-2024-dab-mod-orch-template) · último commit 2024-06-06

#### 99. dais-2024-llm4good

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Referência (workshops e demos) · **Práticas:** — · **Categoria:** Workshops, demos e coleções
- **O que é:** Alinhamento de LLMs a preferências de negócio usando outro LLM como avaliador (DAIS 2024).
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Alinhamento de modelos.
- **Como usar:** Usar a branch V2.
- **Repositório:** [dais-2024-llm4good](https://github.com/databricks-solutions/dais-2024-llm4good) · último commit 2024-06-13

#### 100. dais-2025-genai-hackathon

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Referência (workshops e demos) · **Práticas:** — · **Categoria:** Workshops, demos e coleções
- **O que é:** Guia de início do hackathon de GenAI do Data + AI Summit 2025.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Hackathon.
- **Como usar:** Seguir o README.
- **Repositório:** [dais-2025-genai-hackathon](https://github.com/databricks-solutions/dais-2025-genai-hackathon) · último commit 2025-06-06

#### 101. data-intelligence-for-smarter-community

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Referência (soluções de indústria) · **Práticas:** — · **Categoria:** Soluções de indústria
- **O que é:** Acelerador de telecom para comunidades inteligentes (sinais de torres e IoT).
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Trânsito, congestionamento e segurança urbana.
- **Como usar:** Seguir os labs em 3 passos.
- **Repositório:** [data-intelligence-for-smarter-community](https://github.com/databricks-solutions/data-intelligence-for-smarter-community) · último commit 2026-11-06

#### 102. databricks-dbt-training-labs

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Fundação e Dados · **Práticas:** P02, P05 a P08 · **Categoria:** Pipelines e engenharia de dados
- **O que é:** Laboratórios do curso de dbt no Databricks, até produção com bundles.
- **Como ajudaria no pos_venda:** Só se o time decidir modelar a gold em dbt.
- **Escolha quando:** Aprender dbt no Unity Catalog.
- **Como usar:** Clonar, preencher os valores do workspace e seguir os labs.
- **Repositório:** [databricks-dbt-training-labs](https://github.com/databricks-solutions/databricks-dbt-training-labs) · último commit 2026-11-13

#### 103. databricks-japan-bootcamp

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Referência (workshops e demos) · **Práticas:** — · **Categoria:** Workshops, demos e coleções
- **O que é:** Workshops em japonês (Unity Gateway, governança de IA, coding agents).
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Treinamento no Japão.
- **Como usar:** Abrir a sessão desejada.
- **Repositório:** [databricks-japan-bootcamp](https://github.com/databricks-solutions/databricks-japan-bootcamp) · último commit 2026-11-21

#### 104. databricks-quest

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps) · **Práticas:** P22 · **Categoria:** Apps e ferramentas de app
- **O que é:** Gamificação da adoção da plataforma (pontos, missões e ranking a partir das system tables).
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Engajar usuários na adoção do Databricks.
- **Como usar:** Rodar python deploy.py.
- **Repositório:** [databricks-quest](https://github.com/databricks-solutions/databricks-quest) · último commit 2026-11-13

#### 105. databricks-vision

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps) · **Práticas:** P22 · **Categoria:** Apps e ferramentas de app
- **O que é:** App de geração, edição, avaliação e busca de imagens.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Conteúdo visual gerado por IA.
- **Como usar:** Implantar a App e escolher o modelo de imagem.
- **Repositório:** [databricks-vision](https://github.com/databricks-solutions/databricks-vision) · último commit 2026-11-20

#### 106. dbt-query-tags

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Fundação e Dados · **Práticas:** P02, P05 a P08 · **Categoria:** Pipelines e engenharia de dados
- **O que é:** Projeto dbt em bundle que usa query tags e system tables, com painel.
- **Como ajudaria no pos_venda:** O projeto não usa dbt.
- **Escolha quando:** Atribuir custo de queries dbt por equipe.
- **Como usar:** Ajustar profiles.yml e databricks.yml, rodar dbt e o bundle.
- **Repositório:** [dbt-query-tags](https://github.com/databricks-solutions/dbt-query-tags) · último commit 2026-06-26

#### 107. fastpgcache

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps com Postgres) · **Práticas:** — · **Categoria:** Lakebase (Postgres)
- **O que é:** Biblioteca de cache estilo Redis sobre tabelas UNLOGGED do Postgres.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Cache de aplicação sem Redis.
- **Como usar:** Instalar e usar a API set/get com TTL.
- **Repositório:** [fastpgcache](https://github.com/databricks-solutions/fastpgcache) · último commit 2025-10-28

#### 108. flowx

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Dados (migração) · **Práticas:** — · **Categoria:** Migração
- **O que é:** Converte pipelines do Azure Data Factory e Airflow em Lakeflow Jobs empacotados em bundles.
- **Como ajudaria no pos_venda:** Só se houver ADF ou Airflow legado.
- **Escolha quando:** Migração de orquestradores.
- **Como usar:** Usar as skills no Genie Code ou Claude Code: descobrir, converter, empacotar.
- **Repositório:** [flowx](https://github.com/databricks-solutions/flowx) · último commit 2026-11-21

#### 109. genie-geo-chat

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Semântica e Consumo · **Práticas:** P18, P19, P21 · **Categoria:** Genie e camada semântica
- **O que é:** App com globo 3D e mapa 2D integrados à Genie para perguntar sobre regiões desenhadas no mapa.
- **Como ajudaria no pos_venda:** Pouco aplicável; só faria sentido para visualizar pontos de venda por região.
- **Escolha quando:** Análise de ativos geográficos (torres, lojas, sites).
- **Como usar:** Importar o repo, rodar o notebook de setup e implantar a App.
- **Repositório:** [genie-geo-chat](https://github.com/databricks-solutions/genie-geo-chat) · último commit 2026-04-22

#### 110. geogenie-esri

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Referência (soluções de indústria) · **Práticas:** — · **Categoria:** Soluções de indústria
- **O que é:** Mapa de rede de telecom com ROI de expansão e Genie, alternativa ao ArcGIS.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Planejamento de rede.
- **Como usar:** Implantar a App.
- **Repositório:** [geogenie-esri](https://github.com/databricks-solutions/geogenie-esri) · último commit 2026-09-04

#### 111. grafana-lakehouse-rt-quickstart

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (BI externo) · **Práticas:** P23 · **Categoria:** BI externo (Power BI, Grafana)
- **O que é:** Grafana consultando warehouses SQL, incluindo Lakehouse//RT.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Painéis operacionais em Grafana.
- **Como usar:** Subir com Docker Compose e configurar o token.
- **Repositório:** [grafana-lakehouse-rt-quickstart](https://github.com/databricks-solutions/grafana-lakehouse-rt-quickstart) · último commit 2026-11-06

#### 112. lakebase-express

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps com Postgres) · **Práticas:** — · **Categoria:** Lakebase (Postgres)
- **O que é:** App que migra bancos SQL Server e Azure SQL para o Lakebase.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Migração de banco transacional.
- **Como usar:** Implantar e seguir o catálogo de conectores.
- **Repositório:** [lakebase-express](https://github.com/databricks-solutions/lakebase-express) · último commit 2026-11-05

#### 113. lakebase-scm-extension

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps com Postgres) · **Práticas:** — · **Categoria:** Lakebase (Postgres)
- **O que é:** Extensão VS Code que pareia branches git com branches do Lakebase.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Desenvolvimento de app com banco versionado.
- **Como usar:** Instalar o VSIX e adotar no projeto.
- **Repositório:** [lakebase-scm-extension](https://github.com/databricks-solutions/lakebase-scm-extension) · último commit 2026-11-10

#### 114. lakebase-scm-utils

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps com Postgres) · **Práticas:** — · **Categoria:** Lakebase (Postgres)
- **O que é:** CLI e skills do fluxo git + Lakebase (migrações, diff de schema, PR e CI).
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Mesmo da extensão SCM.
- **Como usar:** Instalar a CLI e seguir o fluxo de feature branch.
- **Repositório:** [lakebase-scm-utils](https://github.com/databricks-solutions/lakebase-scm-utils) · último commit 2026-11-12

#### 115. lakebridge-migration-self-service-demo

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Nenhuma · **Práticas:** — · **Categoria:** Modelo vazio ou arquivado
- **O que é:** README ainda é o modelo padrão, sem conteúdo descrito.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Nenhum.
- **Como usar:** Nada a usar ainda.
- **Repositório:** [lakebridge-migration-self-service-demo](https://github.com/databricks-solutions/lakebridge-migration-self-service-demo) · último commit 2026-05-12

#### 116. lakeflow-deliveries

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Referência (soluções de indústria) · **Práticas:** — · **Categoria:** Soluções de indústria
- **O que é:** Simulação de entregas com SDP em streaming e funções espaciais, App de mapa.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Logística em tempo real.
- **Como usar:** Implantar o bundle.
- **Repositório:** [lakeflow-deliveries](https://github.com/databricks-solutions/lakeflow-deliveries) · último commit 2026-03-26

#### 117. lakets

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps com Postgres) · **Práticas:** — · **Categoria:** Lakebase (Postgres)
- **O que é:** Toolkit de séries temporais em PL/pgSQL para Lakebase (particionamento, rollups, tiering, sync com UC).
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** IoT, métricas de alta frequência.
- **Como usar:** Instalar as funções SQL e criar ChronoTables.
- **Repositório:** [lakets](https://github.com/databricks-solutions/lakets) · último commit 2026-11-16

#### 118. managed-table-migration-accelerator

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Dados (migração) · **Práticas:** — · **Categoria:** Migração
- **O que é:** Converte tabelas EXTERNAL do UC para MANAGED em ondas, com rollback de 14 dias.
- **Como ajudaria no pos_venda:** As tabelas do projeto já são gerenciadas.
- **Escolha quando:** Habilitar otimização preditiva em tabelas externas.
- **Como usar:** Instalar o bundle e conduzir pela App ou Genie Code.
- **Repositório:** [managed-table-migration-accelerator](https://github.com/databricks-solutions/managed-table-migration-accelerator) · último commit 2026-11-17

#### 119. mason

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (agentes e IA generativa) · **Práticas:** — · **Categoria:** Agentes e IA generativa
- **O que é:** App desktop para conversar com modelos via Unity AI Gateway e montar fluxos multimodelo.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Fluxos agênticos em canvas.
- **Como usar:** Instalar no macOS, Windows ou Linux.
- **Repositório:** [mason](https://github.com/databricks-solutions/mason) · último commit 2026-09-23

#### 120. maxgenie

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Nenhuma · **Práticas:** — · **Categoria:** Modelo vazio ou arquivado
- **O que é:** Otimizador de espaços Genie, arquivado e descontinuado.
- **Como ajudaria no pos_venda:** Use o databricks-genie-workbench.
- **Escolha quando:** Histórico.
- **Como usar:** Não usar; o próprio README indica o Genie Workbench.
- **Repositório:** [maxgenie](https://github.com/databricks-solutions/maxgenie) · último commit 2026-08-13 · **arquivado**

#### 121. multimodal_blog

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Nenhuma · **Práticas:** — · **Categoria:** Modelo vazio ou arquivado
- **O que é:** Código de um post sobre multimodal, sem descrição no README.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Não descrito.
- **Como usar:** Abrir os notebooks diretamente.
- **Repositório:** [multimodal_blog](https://github.com/databricks-solutions/multimodal_blog) · último commit 2025-08-26

#### 122. otel-on-databricks

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (agentes e IA generativa) · **Práticas:** — · **Categoria:** Agentes e IA generativa
- **O que é:** Modelos de telecom (Open Telco) e agente de troubleshooting de RAN.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Operações de telecom.
- **Como usar:** Seguir os capítulos em notebooks.
- **Repositório:** [otel-on-databricks](https://github.com/databricks-solutions/otel-on-databricks) · último commit 2026-08-25

#### 123. partner-ai-dev-kit

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Fundação (ferramentas) · **Práticas:** P02 · **Categoria:** Ferramentas para coding agents
- **O que é:** Skills para parceiros ISV criarem conectores conforme o Partner Well-Architected Framework.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Conectores de parceiros.
- **Como usar:** Instalar as skills no assistente.
- **Repositório:** [partner-ai-dev-kit](https://github.com/databricks-solutions/partner-ai-dev-kit) · último commit 2026-04-29

#### 124. realtime-rag-agents-databricks-youcom

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (agentes e IA generativa) · **Práticas:** — · **Categoria:** Agentes e IA generativa
- **O que é:** RAG com dados da web em tempo real pela API da You.com.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Respostas com notícias e web atual.
- **Como usar:** Implantar o bundle e configurar a chave.
- **Repositório:** [realtime-rag-agents-databricks-youcom](https://github.com/databricks-solutions/realtime-rag-agents-databricks-youcom) · último commit 2025-10-29

#### 125. streaming-binary-ingest-patterns

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Dados · **Práticas:** P06 · **Categoria:** Ingestão e streaming
- **O que é:** Padrão para ingerir arquivos binários grandes (ex.: MDF4) em Delta sem estourar memória.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Telemetria automotiva, tick data, logs de sensores.
- **Como usar:** Abrir o notebook de exemplo e trocar o parser.
- **Repositório:** [streaming-binary-ingest-patterns](https://github.com/databricks-solutions/streaming-binary-ingest-patterns) · último commit 2026-06-01

#### 126. streaming-real-time-mode-examples

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Nenhuma · **Práticas:** — · **Categoria:** Modelo vazio ou arquivado
- **O que é:** README ainda é o modelo padrão, sem conteúdo descrito.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Nenhum.
- **Como usar:** Nada a usar ainda.
- **Repositório:** [streaming-real-time-mode-examples](https://github.com/databricks-solutions/streaming-real-time-mode-examples) · último commit 2025-11-19

#### 127. supply-chain-control-tower-bricks

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Referência (soluções de indústria) · **Práticas:** — · **Categoria:** Soluções de indústria
- **O que é:** Visibilidade de supply chain com fluxo agêntico de atendimento de pedidos.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Cadeia de suprimentos.
- **Como usar:** Configurar o repo no workspace.
- **Repositório:** [supply-chain-control-tower-bricks](https://github.com/databricks-solutions/supply-chain-control-tower-bricks) · último commit 2026-03-11

#### 128. youtube-video-intelligence

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Consumo (apps) · **Práticas:** P22 · **Categoria:** Apps e ferramentas de app
- **O que é:** Análise de vídeos do YouTube com Gemini, histórico em Lakebase.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Análise de mídia.
- **Como usar:** Escolher prefixo, implantar e abrir a App.
- **Repositório:** [youtube-video-intelligence](https://github.com/databricks-solutions/youtube-video-intelligence) · último commit 2026-10-19

#### 129. zerobus-otel-collector-demo

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Dados · **Práticas:** P06 · **Categoria:** Ingestão e streaming
- **O que é:** Databricks como backend de observabilidade de Kubernetes (OpenTelemetry via Zerobus, SDP e App com Genie).
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Logs, métricas e traces de clusters Kubernetes.
- **Como usar:** Provisionar a ingestão e implantar pipelines e App.
- **Repositório:** [zerobus-otel-collector-demo](https://github.com/databricks-solutions/zerobus-otel-collector-demo) · último commit 2026-11-18

#### 130. zerobus_station

- **Recomendação:** Fora do escopo
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Com ressalvas
- **Camada do framework:** Nenhuma · **Práticas:** — · **Categoria:** Modelo vazio ou arquivado
- **O que é:** Serviço FastAPI de ingestão via Zerobus, arquivado.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Histórico.
- **Como usar:** Não usar.
- **Repositório:** [zerobus_station](https://github.com/databricks-solutions/zerobus_station) · último commit 2025-10-14 · **arquivado**

### Não roda no Free Edition (17)

#### 131. databricks-exec-code-mcp

- **Recomendação:** Não roda no Free Edition
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Não (Usa a Command Execution API em clusters clássicos.)
- **Camada do framework:** Fundação (ferramentas) · **Práticas:** P02 · **Categoria:** Ferramentas para coding agents
- **O que é:** Servidor MCP que roda código em clusters e cria bundles a partir de prompts.
- **Como ajudaria no pos_venda:** O Free Edition não tem clusters clássicos.
- **Escolha quando:** Testar código no cluster pelo assistente.
- **Como usar:** Configurar o MCP no assistente.
- **Repositório:** [databricks-exec-code-mcp](https://github.com/databricks-solutions/databricks-exec-code-mcp) · último commit 2026-02-03

#### 132. platform-deployment-kit

- **Recomendação:** Não roda no Free Edition
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Não
- **Camada do framework:** Fundação e Operação · **Práticas:** P01, P28 · **Categoria:** Plataforma, infraestrutura e custos
- **O que é:** Gerador web de projetos Terraform para workspaces em AWS, Azure e GCP.
- **Como ajudaria no pos_venda:** Só quando o projeto for para um workspace pago.
- **Escolha quando:** Provisionar workspaces.
- **Como usar:** Escolher a nuvem, preencher, baixar o ZIP e aplicar.
- **Repositório:** [platform-deployment-kit](https://github.com/databricks-solutions/platform-deployment-kit) · último commit 2026-11-18

#### 133. realtime-apps-feature-demo

- **Recomendação:** Não roda no Free Edition
- **Relevância para o pos_venda:** Baixa · **Free Edition:** Não (Usa computação clássica para o Real-Time Mode.)
- **Camada do framework:** Dados · **Práticas:** P06 · **Categoria:** Ingestão e streaming
- **O que é:** Telemetria de rede elétrica com Structured Streaming Real-Time Mode, sink nativo para Lakebase e App com latência abaixo de 500 ms.
- **Como ajudaria no pos_venda:** Padrão para uma visão de pagamentos em tempo real, fora do alcance do Free Edition.
- **Escolha quando:** Painéis operacionais em tempo real.
- **Como usar:** Configurar perfil, catálogo e segredos; fazer deploy e rodar.
- **Repositório:** [realtime-apps-feature-demo](https://github.com/databricks-solutions/realtime-apps-feature-demo) · último commit 2026-11-01

#### 134. ai-platform-kit

- **Recomendação:** Não roda no Free Edition
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Não (Exige administração de conta e nuvem.)
- **Camada do framework:** Fundação e Operação · **Práticas:** P01, P28 · **Categoria:** Plataforma, infraestrutura e custos
- **O que é:** Engenharia de plataforma por linguagem natural: workspaces, Unity Catalog, identidade e redes em Azure, AWS e GCP.
- **Como ajudaria no pos_venda:** Não se aplica ao Free Edition.
- **Escolha quando:** Montar a plataforma corporativa.
- **Como usar:** Instalar as skills no agente de código e pedir o provisionamento.
- **Repositório:** [ai-platform-kit](https://github.com/databricks-solutions/ai-platform-kit) · último commit 2026-10-13

#### 135. ai-runtime-cookbook

- **Recomendação:** Não roda no Free Edition
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Não (Exige GPU e AI Runtime.)
- **Camada do framework:** Avaliação e modelos · **Práticas:** P24 · **Categoria:** Avaliação, MLOps e modelos
- **O que é:** Receitas de ML em escala no Databricks AI Runtime (Ray, serving).
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Treino distribuído.
- **Como usar:** Escolher a receita, o perfil e submeter.
- **Repositório:** [ai-runtime-cookbook](https://github.com/databricks-solutions/ai-runtime-cookbook) · último commit 2026-11-22

#### 136. ai-runtime-rft-cookbook

- **Recomendação:** Não roda no Free Edition
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Não (Exige GPUs H100.)
- **Camada do framework:** Avaliação e modelos · **Práticas:** P24 · **Categoria:** Avaliação, MLOps e modelos
- **O que é:** Treino de agentes por reforço (GRPO) no AI Runtime.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Fine-tuning de agentes.
- **Como usar:** Seguir o quickstart de matemática.
- **Repositório:** [ai-runtime-rft-cookbook](https://github.com/databricks-solutions/ai-runtime-rft-cookbook) · último commit 2026-11-06

#### 137. aim-divergence-fix

- **Recomendação:** Não roda no Free Edition
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Não (Exige Microsoft Entra ID e administração de conta.)
- **Camada do framework:** Qualidade e Governança · **Práticas:** P09 a P16 · **Categoria:** Qualidade, governança e segurança
- **O que é:** Encontra e corrige divergências de identidade que bloqueiam a migração de SCIM para Automatic Identity Management (Entra ID).
- **Como ajudaria no pos_venda:** Não se aplica ao projeto.
- **Escolha quando:** Migração de provisionamento de identidades no Azure.
- **Como usar:** Rodar as ferramentas de diagnóstico e seguir a correção por categoria.
- **Repositório:** [aim-divergence-fix](https://github.com/databricks-solutions/aim-divergence-fix) · último commit 2026-09-09

#### 138. cloud-infra-costs

- **Recomendação:** Não roda no Free Edition
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Não (Mira computação clássica e faturas de nuvem.)
- **Camada do framework:** Fundação e Operação · **Práticas:** P01, P28 · **Categoria:** Plataforma, infraestrutura e custos
- **O que é:** Une relatórios de custo da nuvem com system tables para o custo total da computação clássica, em painéis FOCUS.
- **Como ajudaria no pos_venda:** O Free Edition é serverless e gratuito.
- **Escolha quando:** TCO de clusters clássicos.
- **Como usar:** Configurar a exportação de custos e rodar as consultas.
- **Repositório:** [cloud-infra-costs](https://github.com/databricks-solutions/cloud-infra-costs) · último commit 2026-11-16

#### 139. dais-2024-faster-library-loads

- **Recomendação:** Não roda no Free Edition
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Não
- **Camada do framework:** Fundação e Operação · **Práticas:** P01, P28 · **Categoria:** Plataforma, infraestrutura e custos
- **O que é:** Truque para acelerar a instalação de bibliotecas em clusters interativos.
- **Como ajudaria no pos_venda:** O projeto usa serverless.
- **Escolha quando:** Reduzir espera de cluster.
- **Como usar:** Seguir os notebooks.
- **Repositório:** [dais-2024-faster-library-loads](https://github.com/databricks-solutions/dais-2024-faster-library-loads) · último commit 2025-08-13

#### 140. dbx-proxy

- **Recomendação:** Não roda no Free Edition
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Não
- **Camada do framework:** Fundação e Operação · **Práticas:** P01, P28 · **Categoria:** Plataforma, infraestrutura e custos
- **O que é:** Proxy HAProxy para conectividade privada do serverless até redes do cliente.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Acessar bancos em VPC a partir do serverless.
- **Como usar:** Implantar com Terraform.
- **Repositório:** [dbx-proxy](https://github.com/databricks-solutions/dbx-proxy) · último commit 2026-11-16

#### 141. lakeflow-connect-terraform

- **Recomendação:** Não roda no Free Edition
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Não
- **Camada do framework:** Dados · **Práticas:** P06 · **Categoria:** Ingestão e streaming
- **O que é:** Terraform guiado por YAML para implantar conectores de banco do Lakeflow Connect em escala.
- **Como ajudaria no pos_venda:** Não se aplica ao Free Edition.
- **Escolha quando:** Dezenas de conectores CDC padronizados.
- **Como usar:** Preencher o YAML de configuração e aplicar o Terraform.
- **Repositório:** [lakeflow-connect-terraform](https://github.com/databricks-solutions/lakeflow-connect-terraform) · último commit 2026-05-31

#### 142. lakeflow-tapworks

- **Recomendação:** Não roda no Free Edition
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Não
- **Camada do framework:** Dados · **Práticas:** P06 · **Categoria:** Ingestão e streaming
- **O que é:** Gera bundles e balanceia carga de tabelas entre pipelines de conectores gerenciados do Lakeflow Connect.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Milhares de tabelas em conectores gerenciados.
- **Como usar:** Descrever tabelas e grupos, rodar a CLI ou o notebook.
- **Repositório:** [lakeflow-tapworks](https://github.com/databricks-solutions/lakeflow-tapworks) · último commit 2026-10-16

#### 143. latency-benchmarks

- **Recomendação:** Não roda no Free Edition
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Não
- **Camada do framework:** Dados · **Práticas:** P06 · **Categoria:** Ingestão e streaming
- **O que é:** Benchmarks de latência entre Spark Real-Time Mode e Apache Flink lendo e escrevendo Kafka.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Escolha de motor de streaming de baixa latência.
- **Como usar:** Configurar Kafka e gerador, rodar as consultas A, B e C.
- **Repositório:** [latency-benchmarks](https://github.com/databricks-solutions/latency-benchmarks) · último commit 2026-03-13

#### 144. multi-region-model-serving

- **Recomendação:** Não roda no Free Edition
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Não
- **Camada do framework:** Avaliação e modelos · **Práticas:** P24 · **Categoria:** Avaliação, MLOps e modelos
- **O que é:** Serving de modelo de fraude em várias regiões com Delta Sharing.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Inferência de baixa latência multirregião.
- **Como usar:** Seguir o passo a passo do blog.
- **Repositório:** [multi-region-model-serving](https://github.com/databricks-solutions/multi-region-model-serving) · último commit 2026-09-09

#### 145. network-doctor

- **Recomendação:** Não roda no Free Edition
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Não
- **Camada do framework:** Fundação e Operação · **Práticas:** P01, P28 · **Categoria:** Plataforma, infraestrutura e custos
- **O que é:** Skill do Genie Code que diagnostica falhas de rede do Azure Databricks.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Troubleshooting de rede.
- **Como usar:** Registrar o Git folder no Genie Code e descrever o problema.
- **Repositório:** [network-doctor](https://github.com/databricks-solutions/network-doctor) · último commit 2026-11-10

#### 146. network-intelligence-accelerator

- **Recomendação:** Não roda no Free Edition
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Não
- **Camada do framework:** Referência (soluções de indústria) · **Práticas:** — · **Categoria:** Soluções de indústria
- **O que é:** Gêmeo digital de RF para planejamento celular com ray tracing em GPU.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Telecom 5G.
- **Como usar:** Implantar o bundle com jobs de GPU.
- **Repositório:** [network-intelligence-accelerator](https://github.com/databricks-solutions/network-intelligence-accelerator) · último commit 2026-08-05

#### 147. proteinsearch

- **Recomendação:** Não roda no Free Edition
- **Relevância para o pos_venda:** Nenhuma · **Free Edition:** Não
- **Camada do framework:** Avaliação e modelos · **Práticas:** P24 · **Categoria:** Avaliação, MLOps e modelos
- **O que é:** Embeddings e busca de sequências de proteínas em escala.
- **Como ajudaria no pos_venda:** Não se aplica.
- **Escolha quando:** Bioinformática.
- **Como usar:** Configurar e rodar as etapas do pipeline.
- **Repositório:** [proteinsearch](https://github.com/databricks-solutions/proteinsearch) · último commit 2026-01-29
