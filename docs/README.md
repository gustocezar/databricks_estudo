# Documentação · pos_venda

Domínio **pós-venda de seguro de vida** (parcelas pendentes de pagamento) no Databricks Free Edition: dados sintéticos,
medalhão, carga diária com histórico, qualidade (pipeline + DQX Studio), governança no Unity Catalog, ontologia com metric
views, Genie para o financeiro e painéis AI/BI.

## O que ler

| Documento | Para quem | Responde |
|---|---|---|
| [01 · Trilha de aprendizagem](01_TRILHA_DE_APRENDIZAGEM.md) | quem quer entender o projeto | o que fizemos, em que ordem, por quê e o que aprendemos em cada fase |
| [02 · Playbook](02_PLAYBOOK.md) | quem vai recriar ou construir outro domínio | perfil da base, módulos com critério de saída, matriz de resiliência, roteiro de reconstrução |
| [03 · Lições aprendidas](03_LICOES_APRENDIDAS.md) | quem vai mexer no código | armadilhas reais e a regra que ficou (códigos `L##`) |
| [04 · Framework](04_FRAMEWORK.md) | quem vai aplicar em outro case | as 42 práticas (`P##`): origem, como aplicamos, por quê, quando reaplicar e a prova, com as fontes |
| [05 · Skills e ganhos](05_SKILLS_E_GANHOS.md) | quem quer a linhagem do estudo ou vai reaplicar com um agente de código | as 11 skills consultadas, onde entraram (fase, prática, pasta), o ganho de cada uma e como ajudam na governança, nas métricas de qualidade, no plano de ação e na Genie |
| [06 · Guia para outra base](06_GUIA_BASE_BRUTA.md) | quem vai aplicar numa base bruta de pendências, com o Copilot ou outro agente | etapas 0 a 8 com critério de saída, ficha da base, mapeamento, as duas trilhas do DQX (código ou app) e o prompt para o Copilot; o contrato executável é o [spec](../specs/aplicar-base-bruta/SPEC.md) |
| [07 · Manual de sustentação](07_SUSTENTACAO.md) | quem mantém o domínio funcionando | o que roda e quando, SLAs e metas, onde olhar, rotina diária, semanal e mensal, 12 runbooks, reprocessamento, deploy e rollback, RACI, capacidade e indicadores |
| [FinOps](../finops/README.md) | plataforma, squads e quem avalia custo | custo e uso no padrão FOCUS: por funcionalidade, projeto e time, com boas práticas medidas |
| [Conformidade](../conformidade/README.md) | squad, plataforma e quem audita | se os dados seguem as regras (descrições, tags governadas, LGPD, estrutura, uso, jobs e alertas), com meta, histórico e a [avaliação da observabilidade](../conformidade/AVALIACAO_OBSERVABILIDADE.md) |
| [Catálogo de regras](../regras/catalogo/README.md) e [questionário do negócio](../regras/questionario/QUESTIONARIO_NEGOCIO.md) | área de negócio dona do dado e quem tria as falhas | as regras de qualidade com versão e vigência pela data do dado, o que o negócio aceita, a triagem semanal e a taxa de falso positivo (P41) |
| [Sustentação](../sustentacao/README.md) | quem sustenta a carga em produção | tempo de execução por job, tarefa e pipeline, linha de base, desvios, SLA (meta 06:15), volume por execução, matriz por tarefa, painel e alerta |
| [Modelo de dados](modelo_dados/README.md) | quem consulta, modela ou audita os dados | o modelo de entidade e relacionamento de cada base (diagrama, chaves, relacionamentos) e a linhagem do Unity Catalog (P42) |
| [Marca](marca/README.md) | quem cria painel, relatório, apresentação ou usa a logo | onde fica a marca da empresa (paleta, regras, logo) e as paletas do projeto até ela chegar; procure aqui antes de qualquer coisa visual |
| [AGENTS.md](../AGENTS.md) | LLMs e agentes de código | ordem de leitura, onde está cada resposta, decisões já tomadas, fonte × gerado e o que registrar a cada mudança |
| [CHANGELOG](CHANGELOG.md) | todos | o que mudou, quando e como foi conferido |
| [Inventário](INVENTARIO.md) | todos | retrato atual: scripts, bundles, objetos do catálogo, painéis, Genie, jobs, apps e cobertura de metadados (gerado) |

Documentos de cada bloco continuam nas pastas: [medalhao](../medalhao/README.md), [carga_diaria](../carga_diaria/README.md),
[dqx_studio](../dqx_studio/README.md), [painel de qualidade](../dqx_studio/painel/README.md),
[roteiro da demonstração](../dqx_studio/demo/ROTEIRO.md), [governança](../governanca/README.md),
[triagem da avaliação da Genie](../governanca/genie/avaliacao_boas_praticas/TRIAGEM.md),
[regras de negócio (BDD)](../regras/README.md), [prontidão da ontologia](../governanca/ontologia_readiness/RESULTADO.md),
[painéis financeiros e opção Power BI](../paineis_financeiros/README.md),
[auditoria Power BI (pba)](../paineis_financeiros/powerbi/auditoria/README.md), [régua da Genie (scanner)](../governanca/genie/scanner/TRIAGEM.md).

## Situação em 24/11/2026

| Bloco | Situação |
|---|---|
| Dados, medalhão e carga diária | pronto; job `pos_venda_carga_diaria` implantado e **ligado às 05:00** desde 24/11, com timeout de 33 min; em 25 e 26/11 rodou sozinho e terminou às 05:15 e às 05:17, dentro do SLA; dados até **09/01/2027** (semanas 6 a 8 carregadas em 23/11 com o catálogo de incidentes I16 a I38) |
| Qualidade (barreira, DQX Studio, painel) | pronto (trilha B, app; a trilha A, DQX como código, em `dqx_codigo/`, rodou em 24/11 na janela de 26/12 a 01/01 com 3.229 em quarentena, o mesmo da barreira); 8 semanas no histórico do Studio (40 execuções completas); 138 de 224 regras com exemplo, e as 86 em zero (todas garantias da arquitetura) explicadas no roteiro; o app `dqx-studio` para sozinho após 24 h: `databricks apps start dqx-studio` e esperar "Application startup complete" antes de demonstrar |
| Avaliação contínua do Studio | pronto e **ligado** desde 24/11: 12 tabelas às 06:30, depois da carga; o job liga o app; se o Lakebase estiver desabilitado, reabilite o endpoint e reinicie o app (L19) |
| Governança e metadados | pronto; 1.977 de 1.977 colunas principais (com o schema `bi`) e 682 de 682 legadas descritas; `dado_pessoal` em 380 colunas principais e 152 legadas, 0 sem tag (sem máscara, por decisão: a validação usa os valores reais); auditoria em 28 s |
| Ontologia, metric views, Genie e painéis financeiros | pronto; Genie 29/29 nas perguntas de avaliação com os dados até 09/01 (24/11: a reconferência deu 28/29 por causa de produto órfão; corrigido com o membro "não identificado" na ontologia, L87) (com simulações pelas funções de regra); painéis da diretoria e do time de negócio com **uma página por fato** |
| Opção Power BI (avaliação) | gerada: schema `pos_venda.bi` (8 visões das metric views) + projeto PBIP com os 2 relatórios; 102 arquivos válidos nos esquemas oficiais; paridade 21/21 com o painel na foto de 09/01/2027 (24/11: a reconferência deu 20/21 porque o painel somava o início do mês por grupo; corrigido, L86); **não aberta no Power BI Desktop** (precisa de Windows) |
| Ontologia sem identificadores pessoais | pronto: nenhum `cliente_id` no schema `ontologia` (ligações por `cliente_sk`) |
| Regras de negócio (BDD) | pronto: 5 funções em `pos_venda.regras`, 36/36 cenários, portão no job diário, silver/barreira/gold/Genie/DQX Studio usando as funções, paridade 100% |
| Modelo de dados e Wikis (26/11) | [docs/modelo_dados/](modelo_dados/README.md): 157 entidades em 13 bases, 108 relacionamentos e 127 com chave, gerados do Unity Catalog; Wiki em **157 de 157** ativos, com chave, relacionamentos e linhagem; **unicidade das chaves testada todo dia** (job da sonda, tarefa `chaves`: 117 chaves, 15 PKs do UC); `docs/validar_docs.py` no CI |
| Prontidão para a Genie Ontology (26/11) | 94,7 (Optimized), reavaliada no app religado; só os metadados subiram desde 23/11 (94,5 → 95,1); Métricas (84) é o pilar mais baixo |
| Regras com vigência e retroalimentação (26/11) | catálogo com 14 regras (versão 1, desde sempre), triagem, `versao_vigente()` e 4 visões em `pos_venda.regras`; `conferir` 11/11, BDD do catálogo 8/8, 17 testes sem rede; ensaio fictício de vigência: DQX = SQL nas 15 checagens; **69 semanas × regra para triar** e 7 perguntas em aberto para o dono no questionário |
| Prontidão para a Genie Ontology | **94,5 (Optimized)** na avaliação 4 (23/11), com histórico no Lakebase (`avaliar.py`); domínio e responsável por tags padrão; schemas legados descritos (682/682) e com dado pessoal marcado; histórico: ids 1–4 |
| Auditorias externas e RELY (22/11) | `pba`: modelo Power BI 80/100, lado Databricks 75/100 (só limites do warehouse); scanner da Genie 8/12 nos dois espaços (teto 10/12 sem o Workbench; ajustes nos itens 4, 7 e 8 propostos, não feitos); `RELY` em 14/14 PKs da gold, FKs sem `RELY` |
| Custo e uso (FinOps) | `pos_venda.finops`: 19 visões + metric view no padrão FOCUS 1.4; totais = billing (US$ 1.217,11 a preço de lista desde 22/06); plataforma 77,1%, pós-venda 5,3%, não atribuído 10,3%; 11 de 15 boas práticas atendem; `finops.observability` intocado |
| Conformidade e observabilidade (26/11) | `pos_venda.conformidade`: 28 regras, 10.209 verificações em 268 ativos; 16 atendem, 10 em atenção, 2 críticas (descrição fora do `pos_venda` e 22 views quebradas do FinOps antigo); TAG01, EST02 e USO01 em 100%; tags de custo nos jobs do pós-venda (PLT01: falta o job do Studio, gerido pelo app); PLT03: os 6 sem timeout são do bundle de observabilidade; LGPD e colunas descritas em 100%; 8 ações de observabilidade avaliadas; **sonda diária no job `pos_venda_conformidade_sonda` às 06:45** desde 26/11 |
| Sustentação (24/11) | `pos_venda.sustentacao`: 14 visões, `conferir` 13/13 (execuções = tabelas de sistema; volume = bronze e fato); painel "pos_venda · Sustentação" publicado e alerta das 06:20 **ligado** desde 24/11 (avisa só desvio ≥ 60 s sem ser volume, L92; em OK em 26/11); carga com mediana de 14,53 min e p95 de 16,05 min, folga de 59 min até 06:15 (provisórios: 12 execuções manuais); [manual de sustentação](07_SUSTENTACAO.md) com 12 runbooks |
| Versionamento | no GitHub: [gustocezar/databricks_estudo](https://github.com/gustocezar/databricks_estudo) (público, branch `main`); CI no GitHub Actions (`.github/workflows/ci.yml`); depois de cada mudança, `git add -A && git commit && git push` |

## Como manter esta documentação (incremental)

A documentação acompanha o código. A cada mudança no projeto:

1. **CHANGELOG:** acrescente uma entrada no topo do dia, pelo modelo do próprio arquivo (o que, por quê, onde, conferência, docs atualizadas).
2. **Inventário:** rode `python3 docs/gerar_inventario.py` (só leitura; não usa o warehouse). Não edite `INVENTARIO.md` à mão.
3. **Trilha:** se a mudança abriu uma etapa nova, acrescente uma fase no fim; se completou uma fase "em andamento", troque o texto pelo resultado.
4. **Playbook:** se mudou um passo, um comando ou um critério de saída, atualize o módulo (M#) e o roteiro de reconstrução.
5. **Lições:** se apareceu uma armadilha nova, crie o próximo `L##` no tema certo e cite o código no CHANGELOG.
6. **Situação** (tabela acima): atualize a linha do bloco.
7. **AGENTS.md:** se mudou uma decisão já tomada, um gerador (fonte × gerado) ou onde está cada resposta, atualize o
   [AGENTS.md](../AGENTS.md) da raiz, que orienta LLMs e agentes.

Regra de ouro: uma mudança só está pronta quando o critério de saída do módulo passou **e** o CHANGELOG tem a conferência.
