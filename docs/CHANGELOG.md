# CHANGELOG · pos_venda

Registro incremental de mudanças, do mais recente para o mais antigo. Toda mudança no projeto ganha uma entrada aqui.

**Como registrar** (copie o modelo para o topo da seção do dia):

```markdown
### <assunto curto>
- **O que mudou:** ...
- **Por quê:** ...
- **Onde:** arquivos e objetos do workspace
- **Conferência:** comando e resultado
- **Docs atualizadas:** trilha (fase N) · playbook (módulo M#) · lições (L##) · nenhuma
```

---

## 23/11/2026

### Catálogo de exemplos de qualidade: semanas 6 e 7 pelo fluxo normal
- **O que mudou:**
  - **Gerador de eventos** (`carga_diaria/gerar_carga.py`):
    - 19 incidentes novos (I16 a I34) e duas semanas;
    - semana 6 (26/12 a 01/01): erros de origem e avisos;
    - semana 7 (02/01 a 08/01): vazamentos para as dimensões e a fato — cadastro de cliente e apólice com defeito,
      produto, ponto de venda e corretor novos (`VIDA_QA_*`, `PV_QA_*`, `COR_QA_*`), chave digitada errado e
      corrigida depois, motivo e periodicidade fora do catálogo, canal de contato inválido, vencimento nulo;
    - os incidentes antigos voltam com taxa baixa;
    - a guarda de idempotência agora ignora data nula (L82).
  - **Carga:** 14 dias pelo job `pos_venda_carga_diaria` (26/12/2026 a 08/01/2027).
  - **DQX Studio:** replay das semanas 6 e 7 e das 8 tabelas inteiras (`rodar_ciclos.py`, ciclos 6 e 7 alinhados à
    grade do painel).
  - **Painel de qualidade:** texto e anotações das semanas 6 e 7; as checagens de `aplicar_e_testar.py` deixaram de
    usar números fixos (25 execuções, 3.049 na quarentena) e passaram a comparar com o pipeline.
- **Por quê:** pedido do usuário: dados para dar exemplo a todos os indicadores do DQX Studio, das fatos e das regras,
  com o mínimo de dado e pelo fluxo normal. Também atualizar a documentação, o framework e as apresentações, verificar
  os apps e enviar ao Git.
- **Onde:** `carga_diaria/` (gerador e notebooks gerados), `dqx_studio/regras/rodar_ciclos.py`, `dqx_studio/painel/`,
  `dqx_studio/demo/ROTEIRO.md`. No workspace: bronze, silver, gold, `main.dqx_studio` e os painéis.
- **Conferência:**
  - **Job:** SUCCESS em 16 minutos; portão 36/36; 102.612 eventos no intervalo; 3.613.748 linhas novas na fato
    (14 fotos).
  - **Quarentena:** os 11 motivos, com 3.596 eventos nas semanas novas.
  - **Fato:** em 08/01/2027, todas as faixas (menos "Vence hoje", por desenho) e todos os status em aberto. Chaves
    órfãs em cliente (59), apólice (24), produto (5), corretor (27), ponto de venda (31), periodicidade (632), forma
    de pagamento (3.806) e motivo (2.380).
  - **Studio:** 19 execuções com todas as linhas, todas SUCCESS (a primeira tentativa deu HTTP 502, L85). 133 das 224
    regras com exemplo; das 91 em zero, 86 são garantias da arquitetura (L84) e 5 pedem mais um dia.
  - **Painel de qualidade:** 6/6 conjuntos de dados e 5/5 checagens; 35 execuções (7 semanas); implantado.
  - **Painéis financeiros:** foto de 08/01/2027, saldo em aberto R$ 33.079.336,07.
  - **Apps:**
    - `dqx-studio` RUNNING, com as execuções novas no histórico;
    - `genie-ontology-readiness` RUNNING, com a avaliação 4 gravada no Lakebase: 94,5 (era 92,7), com métricas de 76
      para 84 e metadados de 93,5 para 94,5.
- **Docs atualizadas:** trilha (fase 25) · playbook (passo 6 do roteiro e 1 linha na matriz) · lições (L82–L85) ·
  framework (P10, P11, P29) · `docs/README.md` · `README.md` · `AGENTS.md` · README da carga · roteiro da demo ·
  inventário

### Revisão total do projeto
- **O que mudou (correções):**
  - **Fases.** A trilha tem 25 fases (0 a 24), não 24. Corrigido no documento e na apresentação, que nas entradas
    anteriores deste dia diziam "24 fases". A prova da P29 (estava "22 fases, 74 lições") foi corrigida no framework
    e no documento.
  - **Datas.** Corrigidas a "Última atualização" da trilha e do playbook e o título "Situação em 23/11/2026".
  - **Guia de opções para LLM.** O contexto dizia "29 práticas em 8 camadas" e a regra 1 não citava Custo e uso nem
    Conformidade. `gerar_opcoes.py` foi corrigido, e `OPCOES_PARA_LLM.md` e `opcoes.json` foram gerados de novo.
  - **Espaços Genie.** `analista.json` e `diretor.json` estavam atrás do `genie.py`: ainda fixavam a data
    24/12/2026. Foram gerados de novo. Os espaços publicados já tinham o texto novo.
  - **Sonda.** `gerar_conformidade.py registrar` agora para com uma mensagem quando não há view para sondar; antes,
    o INSERT saía vazio.
- **Por quê:** pedido do usuário: revisão total.
- **Onde:** `docs/` (framework, trilha, playbook, README), `referencias/databricks_solutions/` (guia de opções),
  `governanca/genie/*.json`, `conformidade/gerar_conformidade.py`. O documento e a apresentação estão no claude.ai.
- **Conferência:**
  - **Geradores.** Os 12 que rodam sem warehouse foram rodados: 11 sem diferença e 1 (Genie) com o JSON atrasado,
    agora corrigido.
  - **Links e código.**
    - links internos dos `.md`: 0 quebrados;
    - links externos da documentação: 61 de 61 responderam 200;
    - `py_compile` em todos os `.py`: ok;
    - imports e funções sem uso nos geradores de FinOps e conformidade: 0.
  - **Varredura.** 0 token. O e-mail do autor e um caminho local aparecem em 4 arquivos, já publicados por decisão do
    dono (fase 21, L70).
  - **Workspace.**
    - conformidade: 9/9 checagens, 8.992 verificações, 338 pendências;
    - FinOps: 7/7, com US$ 1.228,43 = billing;
    - sonda: 0 view quebrada no `pos_venda`; as 22 quebradas estão fora dele e têm a mesma causa (L76);
    - jobs do pós-venda: última execução com sucesso;
    - apps `dqx-studio` e `genie-ontology-readiness`: parados, o esperado no Free Edition.
  - **Não refeito**, porque gasta cota e não mudou desde a última conferência registrada: cenários BDD, validação e
    avaliação da Genie, paridade do Power BI.
- **Docs atualizadas:** framework (prova da P29) · trilha · playbook · `docs/README.md` · guia de opções

### Origem "Alerta SQL" na FinOps; documento e apresentação com a conformidade
- **O que mudou:**
  - **FinOps.**
    - `ativos.json` traz os nomes dos 5 alertas SQL, sem o prefixo de usuário do bundle.
    - `custo_sql_por_consulta` ganhou a origem "Alerta SQL" (por `query_source.alert_id`) e o tipo de recurso `alerta`.
    - A regra 25 atribui os alertas `[Observabilidade]` ao projeto `observabilidade-framework` pelo nome.
  - **Documento do framework:**
    - 37 práticas e 24 fases;
    - a seção "Conformidade e observabilidade" (P35 a P37);
    - 3 gatilhos e 7 fontes novas;
    - a faixa de Conformidade no diagrama das camadas.
  - **Apresentação:**
    - slide novo de conformidade (19 slides) e 10 camadas;
    - 37 práticas, 24 fases, 81 lições e 56 fontes;
    - 2 pendências novas.
- **Por quê:** pedido do usuário: fazer os próximos passos da entrega de conformidade.
- **Onde:** `finops/` (`gerar_finops.py`, `ativos.json`, `finops.sql`, `README.md`). O documento e a apresentação são
  artefatos privados no claude.ai.
- **Conferência:**
  - FinOps (`python3 finops/gerar_finops.py conferir`): 19/19 visões e a metric view respondem, e as 7 checagens
    passam (27.757 linhas e US$ 1.228,43 = billing; SQL rateado = SQL da base, US$ 949,20);
  - as 2.129 consultas dos alertas têm a origem "Alerta SQL" e o projeto `observabilidade-framework` (US$ 817,22);
  - diagrama do documento conferido pela captura da página;
  - slides alterados renderizados em 1920×1080, sem estouro.
- **Docs atualizadas:** `finops/README.md` (correção do achado da L77)

### Conformidade dos dados e avaliação da observabilidade do workspace
- **O que mudou:**
  - **Avaliação.** Foram avaliadas as 8 ações de observabilidade que já rodam no workspace: os 6 jobs e os 5 alertas
    SQL do bundle `observabilidade-framework`, as visões de `main.observabilidade_dev` e `finops.observability`. Cada
    ação recebeu um veredito: 3 internalizadas, 2 mantidas, 1 a consertar (alertas), 1 a aposentar (rightsizing) e 1
    só leitura. Nada do bundle foi alterado; as recomendações ficam com o dono.
  - **Schema novo `pos_venda.conformidade`.** Gerado por `conformidade/gerar_conformidade.py`, tem:
    - 28 regras em 7 dimensões, com meta, severidade, origem, link e como corrigir;
    - 12 visões, a metric view `mv_conformidade` e as tabelas `sonda_views` e `historico`.

    As regras de warehouse, tags e policies do bundle viraram PLT01 a PLT06.
  - **Alertas.** Os 5 alertas SQL rodam como jobs ocultos e eram as consultas "sem dono" da L77: US$ 816,20 desde
    julho. A L77 recebeu uma nota de correção, e a trilha e o playbook trocaram "job removido" por "job oculto de
    alerta SQL".
- **Por quê:** pedido do usuário: avaliar se as ações de observabilidade do workspace entram no framework e monitorar
  se os dados estão em conformidade, com tags, descrições e boas práticas.
- **Onde:** `conformidade/` (`gerar_conformidade.py`, `README.md`, `AVALIACAO_OBSERVABILIDADE.md`, `conformidade.sql`,
  `politicas_tags.json`, `alertas.json`, `conferencia.json`). No workspace, o schema `pos_venda.conformidade`.
- **Conferência** (`python3 conformidade/gerar_conformidade.py conferir`): 15 de 15 objetos respondem e as 9 checagens
  passam.
  - inventário = `information_schema`: 229 ativos e 3.885 colunas;
  - DOC01 verifica 207 ativos e DOC03 verifica 3.093 colunas, todos os que não são internos;
  - soma por regra = 8.992 achados;
  - pendências = não conformes = metric view = 337;
  - 0 regra sem dados;
  - histórico do dia com 28 linhas;
  - sonda de 140 views: 118 respondem.

  **Triagem.** A primeira rodada acusou 382 colunas sem descrição e 129 colunas de dado pessoal sem tag. Eram
  tabelas internas do Lakeflow (L80) e 3 nomes de métrica da ontologia. Corrigido no gerador. Os links das fontes
  novas responderam 200.
- **Docs atualizadas:** trilha (fase 24) · playbook (M12 e 2 linhas na matriz de resiliência) · lições (L79–L81 e
  correção da L77) · framework (P35–P37) · `AGENTS.md` · `docs/README.md` · `README.md` · inventário

### Documento e apresentação do framework com a camada FinOps
- **O que mudou:**
  - O documento compartilhável e a apresentação (ambos no claude.ai, privados) ganharam a camada Custo e uso
    (FinOps, P30 a P34).
  - **Documento:**
    - abertura com 34 práticas e 23 fases;
    - diagrama com a caixa "Custo e uso" e legenda "9 camadas · 34 práticas";
    - 4 linhas novas no mapa de gatilhos;
    - seção "Custo e uso (FinOps)" com a tabela P30–P34;
    - fontes FinOps;
    - módulos M1 a M11.
  - **Apresentação:**
    - slide novo "Custo e uso: todo custo com dono", agora com 18 slides;
    - camadas "de 9";
    - números atualizados (34 práticas, 23 fases, 78 lições, 49 fontes);
    - linha nova no mapa de gatilhos;
    - pendência de tags e budget policies;
    - fontes FinOps.
- **Por quê:** pedido do usuário: atualizar o documento e a apresentação com a camada FinOps.
- **Onde:** artefatos do claude.ai (fora do repositório). No repositório, só esta entrada.
- **Conferência:**
  - captura do diagrama sem texto cortado;
  - busca no documento sem "29 práticas" restante;
  - na apresentação, 18 slides na ordem, todos com arquivo, e nenhum número antigo;
  - altura do slide do mapa de gatilhos (12 linhas) estimada em ~761 px dos 792 úteis.
  
  A apresentação não foi pré-visualizada, porque o Playwright não está instalado.
- **Docs atualizadas:** nenhuma além desta entrada

### Visões de custo e uso no padrão FOCUS (FinOps)
- **O que mudou:**
  - Schema novo `pos_venda.finops`, com 19 visões e a metric view `mv_finops_custo`, gerados por
    `finops/gerar_finops.py`:
    - base FOCUS 1.4 (`focus_custo_uso`, 65 colunas da especificação + colunas `x_`);
    - custo por funcionalidade do Databricks, custo SQL rateado por consulta e custo por projeto;
    - uso de painéis, Genie (UI × API), consultas e jobs;
    - visões do time de plataforma (custo diário e anomalias, cobertura de atribuição, top recursos, warehouses);
    - visões do time de squad (custo mensal, custo unitário, uso);
    - 15 boas práticas de custo com meta.
  - Todas as colunas são descritas. As regras de atribuição ficam em `REGRAS`, e os nomes dos ativos em `ativos.json`.
  - `finops.observability` não foi alterado.
- **Por quê:** pedido do usuário: visões de uso e de custo, com o framework FOCUS do FinOps, boas práticas dos
  aceleradores da Databricks, custo por funcionalidade e visões do time de plataforma e do time de squad.
- **Onde:** `finops/` (`gerar_finops.py`, `README.md`, `finops.sql`, `ativos.json`, `conferencia.json`). No workspace,
  o schema `pos_venda.finops`.
- **Conferência** (`python3 finops/gerar_finops.py conferir`):
  - 19/19 visões e a metric view respondem;
  - 27.613 linhas na base = billing;
  - US$ 1.217,11 = uso × preço de lista;
  - custo por funcionalidade e por projeto = base;
  - SQL rateado = SQL da base (US$ 938,40);
  - 0 linha com `ServiceCategory` fora da FOCUS e 0 com coluna obrigatória nula.
  
  A primeira versão deixou 80% do custo sem dono. Corrigido para 10,3%, classificando pelo texto da consulta quando a
  origem não tem nome (L77). Os links das fontes foram conferidos e responderam 200.
- **Docs atualizadas:** trilha (fase 23) · playbook (M11) · lições (L76–L78) · framework (P30–P34) · `AGENTS.md` ·
  `docs/README.md` · `README.md` · inventário

### Orientação para LLMs e agentes: AGENTS.md, CLAUDE.md e README
- **O que mudou:**
  - Novo `AGENTS.md` na raiz, com:
    - a ordem de leitura;
    - onde está cada resposta (tabela por tipo de pergunta);
    - as decisões já tomadas (Free Edition, sem máscara, ontologia sem identificador, saldo semiaditivo, `RELY` só nas
      PKs, agendas pausadas, acesso do app de prontidão, escolha de aceleradores);
    - a tabela fonte × gerado (12 linhas);
    - como trabalhar, o que registrar a cada mudança, segurança e limites.
  - Novo `CLAUDE.md`, que importa o `AGENTS.md` (`@AGENTS.md`).
  - O README ganhou a seção "Para LLMs e agentes", com os atalhos.
  - `docs/README.md` passou a citar o `AGENTS.md` em "O que ler" e no passo 7 de "Como manter".
- **Por quê:** o usuário perguntou se o README orienta uma LLM que lê o repositório. Só orientava pessoas: faltavam a
  ordem de leitura, as regras de escolha, as decisões fixas e a lista do que é gerado.
- **Onde:** `AGENTS.md`, `CLAUDE.md`, `README.md`, `docs/README.md`.
- **Conferência:**
  - Os links e caminhos citados nos três arquivos existem: 0 falhas na checagem por script.
  - Os geradores da tabela fonte × gerado foram conferidos no código (`write_text`).
  - As lições citadas (L01, L31, L41, L56, L70, L71, L74) existem e tratam do que o texto diz.
- **Docs atualizadas:** `docs/README.md` (O que ler, Como manter) · `README.md` · inventário

### Guia de opções databricks-solutions para LLM
- **O que mudou:**
  - `referencias/databricks_solutions/gerar_opcoes.py` gera `OPCOES_PARA_LLM.md` e `opcoes.json` a partir do
    catálogo: os 147 repositórios como opções para o pos_venda.
  - Cada opção traz o que é, como ajudaria no projeto, quando escolher, como usar, relevância, Free Edition (com a
    ressalva), camada e práticas do framework, situação com motivo, recomendação e prioridade.
  - O guia abre com o contexto do projeto (vagas de app, Lakebase, modelos) e 9 regras de escolha.
  - O framework, o documento e a apresentação ganharam a seção de opções; a apresentação passou a ter 17 slides.
  - `catalogo.py` registrou como **adiados** os 4 repositórios que a revisão de 22/11 pôs em "não agora" e que o dado
    ainda mostrava sem decisão: `lakeflow_framework`, `ingestion-workbench`, `mlops-quickstart` e
    `advance-document-processing`.
  - Em `regulatory_data_governance`, a situação diz "só os padrões, sem instalar".
- **Por quê:** pedido do usuário: todas as opções da databricks-solutions, com como ajudariam no projeto, de forma que
  uma LLM entenda qual é a melhor opção.
- **Onde:** `referencias/databricks_solutions/` (`gerar_opcoes.py` novo, `OPCOES_PARA_LLM.md`, `opcoes.json`,
  `catalogo.py` e os gerados); `docs/04_FRAMEWORK.md` (seção nova e P27).
- **Conferência:**
  - 147 opções com 147 nomes únicos, e `opcoes.json` válido.
  - Recomendações: aplicar a seguir 2, candidato 5, já aplicado 7, adiado 10, só se a necessidade mudar 69, fora do
    escopo 37, não roda no Free Edition 17.
  - A primeira geração recomendou como candidatos 4 repositórios já adiados; a causa foi corrigida no catálogo (L75).
  - O exemplo do guia (medir o uso da Genie) leva ao `dbx-adoption-monitor`, que está em *Aplicar a seguir*.
- **Docs atualizadas:** framework (seção de opções, P27) · revisão de 22/11 · trilha (fase 12) · lições (L75) ·
  `README.md` · inventário

## 22/11/2026

### Framework das práticas aplicadas, documento e apresentação
- **O que mudou:** `docs/04_FRAMEWORK.md` reúne as 29 práticas (P01 a P29) em 8 camadas. Cada prática traz a origem
  (documentação, acelerador, Databricks Labs, Microsoft, Kimball, LGPD ou lição `L##`), como aplicamos, por quê, quando
  reaplicar e a prova. O documento traz ainda os 5 passos para reaplicar, o mapa de gatilhos e as 39 fontes. Do mesmo
  conteúdo saíram um documento compartilhável e uma apresentação de 16 slides, ambos no claude.ai e privados.
- **Por quê:** pedido do usuário: um framework, um documento e uma apresentação com tudo o que foi aplicado e por quê,
  para reaplicar em cases parecidos, com as fontes e a origem.
- **Onde:** `docs/04_FRAMEWORK.md`; `docs/README.md` e `README.md` (link na tabela "O que ler").
- **Conferência:**
  - As 41 URLs candidatas responderam HTTP 200 em 22/11/2026, e 39 fontes entraram no framework.
  - Cada linha "Prova" foi conferida contra a trilha e o CHANGELOG, e quatro foram reescritas para não dizer mais do que
    o projeto verificou.
  - O diagrama das camadas foi conferido por captura de tela no documento.
  - A apresentação não foi pré-visualizada: o Playwright não está instalado nesta máquina. A altura de cada slide foi
    estimada; a mais cheia, Camadas, dá cerca de 764 px dos 824 px úteis.
- **Docs atualizadas:** framework (novo) · `docs/README.md` · `README.md` · inventário

### Propostas 1 a 3 da revisão: auditoria Power BI, régua da Genie e RELY nas chaves
- **O que mudou:**
  - (1) **Auditoria do Power BI com o `powerbi-analyzer` (`pba`):** o modelo tirou 80/100 e o lado Databricks, 75/100.
    `gerar_powerbi.py` ganhou a ação `bim` (model.bim só para o `pba`, fora de `projeto/`), e `auditoria/pba_oauth.py`
    deixa o `pba` usar o perfil OAuth.
  - (2) **Régua de 12 itens do Genie Workbench com o `genie-agent-scanner`:** os dois espaços tiraram 8/12. Nada foi
    alterado nos espaços.
  - (3) **`RELY` nas 14 chaves primárias da gold** (`governanca/aplicar_rely.py`): as 15 estrangeiras foram recriadas sem
    `RELY`, e `gerar_carga.py` passou a criar as chaves já com `RELY` (notebooks regenerados, bundle da carga implantado,
    job ainda pausado). O catálogo marca os três repositórios como aplicados.
- **Por quê:** pedido do usuário: aplicar as três propostas pequenas da revisão do catálogo.
- **Onde:** `paineis_financeiros/powerbi/auditoria/` (relatórios e triagem), `paineis_financeiros/powerbi/gerar_powerbi.py`,
  `governanca/genie/scanner/` (relatórios e `TRIAGEM.md`), `governanca/aplicar_rely.py` e `governanca/rely/` (medições e
  cópia das definições antes), `carga_diaria/gerar_carga.py` e `src/notebooks/20_gold_dims.py` e `30_fato_snapshot.py`,
  `referencias/databricks_solutions/` (revisão e catálogo), `.gitignore` (`auditoria/modelo_bim/`).
- **Conferência:**
  - `projeto/` regenerado **sem diferença**; `model.bim` com 8 tabelas, 47 medidas e 12 relações.
  - Unicidade: 14/14 chaves únicas e sem nulo, inclusive os 30.147.469 registros da fato.
  - `aplicar_rely.py conferir`: 14/14 PK com `RELY`, 15/15 FK, 0 FK com `RELY`.
  - Medição: junções no plano otimizado de 9 para 0 (saldo por dia), de 9 para 1 (saldo por produto) e de 9 para 6
    (`bi.carteira_diaria`). Linhas e assinatura do resultado iguais; tempo igual (~1,5 s).
  - O deploy apagou 2 `.pyc` do workspace (efeito do `.gitignore`), e os 7 notebooks continuam lá.
  - **Não avaliado de fato:** as regras do `pba` que dependem de visuais (RD-001, RD-010) e as de preparo de dados (o
    Power BI ainda não consultou o warehouse). IN-008 e o item 3 da régua da Genie são falsos positivos (ver as triagens).
- **Docs atualizadas:** trilha (fase 22) · playbook (M4, M9) · lições (L71–L74) · `docs/README.md` (situação) · READMEs de
  `powerbi/` e `governanca/` · revisão de 22/11

### Projeto no GitHub
- **O que mudou:** o projeto inteiro foi para o repositório público `gustocezar/databricks_estudo` (branch `main`). A raiz
  ganhou `.gitignore` (fora: `.venv` de `regras/` com 29 MB, caches Python, `.databricks/` dos bundles, esquemas do Power
  BI baixados, arquivos locais do Desktop) e `README.md` com o mapa do projeto. A tabela de fases da trilha ganhou as
  linhas 19 e 20, que faltavam. Com o Git, o pré-requisito do `databricks-dab-examples` foi cumprido (catálogo e revisão
  atualizados).
- **Por quê:** pedido do usuário: salvar todo o projeto no GitHub. Até aqui ele só existia na pasta que o app criou para
  a sessão.
- **Onde:** `.gitignore`, `README.md`; `referencias/databricks_solutions/` (`catalogo.py`, `REVISAO_2026-11-22.md` e
  arquivos gerados); docs.
- **Conferência:** varredura antes do envio: 0 tokens (`dapi`, `gho_`, `sk-`, `AKIA`, chave privada) e 0 senhas nos 325
  arquivos. Achados mostrados ao usuário, que decidiu publicar tudo: o e-mail do autor (1 linha do README do DQX Studio e
  390 vezes em 2 JSON de backup das regras), amostras de clientes sintéticos (dbldatagen) em 3 JSON de resultados do DQX,
  um caminho local num log e o endereço do workspace em 11 arquivos de configuração. Depois do envio: commit `6c3d766`
  no `main` remoto, 321 arquivos no GitHub (= 321 no commit local), nenhum caminho de `.venv`, cache, `.databricks/` ou
  esquema baixado, `git status` limpo. Autor dos commits com o e-mail `noreply` do GitHub (o Git desta máquina não tinha
  identidade global; a configuração ficou só neste repositório).
- **Docs atualizadas:** trilha (fase 21) · playbook (M1) · lições (L70) · README da raiz (novo) · situação no
  `docs/README.md`

### Revisão do catálogo databricks-solutions
- **O que mudou:** segunda leitura dos 147 repositórios cruzada com o projeto atual (Power BI, funções de regra, painéis
  por fato). Nenhum repositório novo; 13 com commit novo; seis mudaram de relevância (`powerbi-analyzer` e
  `technical-services-solutions` para alta; `power-bi-on-databricks-quickstarts` para média; `databricks-genie-workbench`
  de alta para média). O catálogo ganhou o campo de situação no projeto: 4 aplicados, 5 propostos, 6 adiados, com o
  motivo. Sete propostas priorizadas, das quais três de esforço pequeno: auditar o Power BI com `pba`, pontuar a Genie com
  o `genie-agent-scanner` e declarar `RELY` nas PKs da gold.
- **Por quê:** pedido do usuário: rever o catálogo e ver o que aplicar no projeto.
- **Onde:** `referencias/databricks_solutions/` (`REVISAO_2026-11-22.md` novo; `catalogo.py` com o bloco `REVISAO`;
  `repos_github.json` atualizado, o de 20/11 guardado em `repos_github_2026-11-20.json`; `CATALOGO.md`, `catalogo.json` e
  a página regenerados).
- **Conferência:** `gh repo list` = 147 repositórios; leitura de `system.access.audit` e `system.query.history` com sucesso;
  `databricks apps list` (2 de 3 apps); restrições da gold sem `RELY`; `node --check` no script da página. A página não
  foi aberta no navegador, e nenhuma das propostas foi aplicada.
- **Docs atualizadas:** trilha (fase 12) · lições (L69)

### Painéis por fato (Databricks) e opção Power BI para avaliação
- **O que mudou:** os painéis `KPIs financeiros · Diretoria` e `· Analista` (time de negócio) ganharam **uma página por
  fato** (carteira em aberto, recuperação, safras, qualidade dos dados); a diretoria abre numa visão executiva; textos sem
  data fixa. Novo schema `pos_venda.bi` com 8 visões agregadas **a partir das metric views** (calendário, produto, canal,
  forma, carteira diária, recuperação, safras, qualidade), descritas e com tags. Novo `paineis_financeiros/powerbi/gerar_powerbi.py`:
  projeto PBIP com modelo TMDL (8 tabelas, 47 medidas DAX, 12 relações) e relatórios PBIR do time de negócio e da diretoria
  com as mesmas páginas; validação contra os esquemas oficiais da Microsoft; paridade de números com o painel.
- **Por quê:** pedido do usuário: painéis de cada fato para o time de negócio e para o diretor, no Databricks e no Power BI,
  para avaliar as duas opções.
- **Onde:** `paineis_financeiros/gerar_paineis.py`, `paineis_financeiros/README.md` (novo), `paineis_financeiros/powerbi/`
  (novo: gerador, `projeto/`, `README.md`, `VALORES_DE_REFERENCIA.md`); `governanca/aplicar_semantica.py`,
  `auditar_metadados.py` e `ontologia.py` (schema `bi` como principal, camada `bi`).
- **Conferência:** 14/14 datasets SUCCEEDED; bundle implantado (2 painéis atualizados no mesmo link, publicados);
  `gerar_powerbi.py`: 102 arquivos válidos nos esquemas oficiais e teste negativo detectado; paridade **21/21** (foto
  25/12); 0 chave órfã nas visões; auditoria: 1.977/1.977 colunas principais descritas, 0 PII sem tag. **Não verificado:**
  abrir o projeto no Power BI Desktop (sem Windows aqui) e ver os painéis no navegador (pedia login; conferidos pela API).
- **Correção no caminho:** recriar as visões `bi` apagou as tags (armadilha já conhecida) → tags reaplicadas e
  `gerar_powerbi.py visoes` passou a recriar só a visão cuja definição mudou; `mes_numero` virou `mes_do_ano` (a heurística
  de PII lia `numero$`).
- **Docs atualizadas:** trilha (fase 20) · playbook (M8, matriz, roteiro 14 e 14b) · lições (L66–L68) · README · ROTEIRO (Ato 10).

### Dia novo (25/12) pelo caminho todo, com as funções de regra
- **O que mudou:** job `pos_venda_carga_diaria` completo para 25/12 (execução 570575487309331, 16 min, 7 tarefas SUCCESS);
  DQX Studio executado nas 3 janelas (agora 19–25/12); textos que fixavam 24/12 como foto mais recente corrigidos
  (instrução da Genie, roteiro); checagem do painel de qualidade relativa à data (antes contava 35 dias).
- **Por quê:** decisão do usuário: provar, com evento novo, o caminho que passou a usar as funções (`cpf_valido` na silver,
  `valores_fora_da_regra` na barreira, funções na gold).
- **Onde:** workspace (job, silver, gold, `dq.janela_avaliacao`, espaços Genie); `governanca/genie.py`,
  `dqx_studio/painel/aplicar_e_testar.py`, `dqx_studio/demo/ROTEIRO.md`.
- **Conferência:** portão 36/36; bronze 8.559 = silver 8.559, quarentena 0; 0 evento fora das funções; silver do dia com
  0 divergência (faixa, valores, CPF) e 139 CPFs inválidos marcados = 139 pela função; gold do dia 253.914 linhas, 0
  divergência; Studio: bronze 44 violações da regra espelhada (I03 de 19–20/12, iguais à regra de valor mínimo), silver 0,
  fato 0; Genie **29/29** com a foto nova; painel de qualidade "tudo certo" (36 dias, "Semana 6" parcial).
- **Limite:** nenhum incidente cobre 25/12: o dia prova que as funções não reprovam evento bom, não que pegam erro (L64).
- **Docs atualizadas:** trilha (fase 19) · playbook (matriz) · lições (L64, L65) · README · regras/README · ROTEIRO.

### DQX Studio espelha a regra de cálculo da barreira
- **O que mudou:** regra `valores_seguem_regras_de_calculo` (erro) em `definir_regras.py` para bronze, silver e fato, herdada
  pelas janelas `dq.v_*_janela`; modelo 70 do Registro, aplicado e aprovado só nas 3 janelas (`registro_studio.py aplicar`
  e `executar` aceitam tabelas e mesclam o arquivo de ids); `USE SCHEMA` e `EXECUTE` em `pos_venda.regras` para o service
  principal do app dqx-studio e o executor dos agendamentos.
- **Por quê:** decisão do usuário; manter a barreira (`valores_fora_da_regra`) e o Studio contando a mesma regra.
- **Onde:** `dqx_studio/regras/definir_regras.py`, `dqx_studio/regras/registro_studio.py`; grants no schema `pos_venda.regras`.
- **Conferência:** expressão testada antes no warehouse (60 / 0 / 0); execuções manuais SUCCESS com bronze 60 violações (todas
  do I03, já barradas por `valor_parcela_nao_positivo`), silver 0 e fato 0; disparo agendado real às 12:10 (`scheduled`,
  `scheduler`, SUCCESS, 60) e agenda devolvida para 06:30 **pausada** nas 12 tabelas; notas recalculadas.
- **Docs atualizadas:** trilha (fase 19) · playbook (M10, matriz, roteiro 7) · lições (L62, L63) · README · regras/README · ROTEIRO.

### Regras de negócio em uso: portão, silver, barreira, gold e Genie (etapa 2)
- **O que mudou:** tarefa `portao_regras` (notebook `05_portao_regras`) no início do job diário, rodando os 36 cenários
  copiados de `regras/` por `gerar_carga.py`; silver valida o CPF com `regras.cpf_valido`; barreira com a 11ª regra
  `valores_fora_da_regra` (depois de `atraso_nao_confere_com_as_datas`); gold calcula faixa, multa, juros e total pelas
  funções; Genie com `instructions.sql_functions` (4 funções), 1 SQL de exemplo e 1 pergunta de avaliação por espaço;
  Pages do valor total e da quarentena atualizadas; `uc.py` usa a autenticação do runtime dentro do Databricks.
- **Por quê:** decisão do usuário (etapa 2 do BDD): a regra passa a ser calculada num lugar só e testada antes de cada carga.
- **Decisão:** a barreira **mantém** `valor_total_inconsistente`; substituir no mesmo lugar reclassificaria 319 eventos do
  I14. O simulador da origem continua com a conta própria (imita o sistema externo).
- **Onde:** `carga_diaria/gerar_carga.py`, `carga_diaria/resources/carga_diaria.job.yml`, `carga_diaria/src/portao_regras/`
  (gerado), `regras/uc.py`, `governanca/genie.py`, `governanca/ontologia.py`.
- **Conferência:** bundle validado e implantado; execução 1023717274816452 (só portão, silver e gold de 18 a 24/12):
  portão 36/36, silver sem mudança (1.596.919 eventos, 3.049 na quarentena, 0 `valores_fora_da_regra`), gold 1.743.052
  linhas com 0 diferença (`EXCEPT ALL` nos dois sentidos) e tabela temporária apagada; paridade 100%; Genie 41/41 SQL
  válidos e **29/29** respostas (as simulações chamam as funções); painéis 13/13 datasets; Pages 18 e Wikis 51/51.
- **Em aberto:** espelhar `valores_fora_da_regra` no DQX Studio.
- **Docs atualizadas:** trilha (fase 19) · playbook (M10, matriz, roteiro 18) · lições (L59–L61) · README · carga_diaria/README · regras/README.

## 21/11/2026

### Regras de negócio como funções do Unity Catalog, testadas por BDD (etapa 1)
- **O que mudou:** schema `pos_venda.regras` com `faixa_atraso`, `valor_multa`, `valor_juros`, `valor_total_pendente` e
  `cpf_valido` (descrição na função e nos parâmetros); 36 cenários em português (`behave`, Statement Execution API);
  `paridade.py` contra gold, silver e quarentena; schema na governança (tags `Pós-venda`, `camada = regras`, `domain`).
  Pipeline, barreira e Genie **não** mudaram.
- **Por quê:** decisão do usuário (recomendação do catálogo databricks-solutions: agentic-bdd-uc-functions); as regras
  estavam repetidas como texto SQL e o incidente I07 mostra o custo de um erro de cálculo.
- **Decisões explícitas:** dias negativos → faixa, juros e total nulos; CPF com dígitos todos iguais → inválido; multa já
  no dia do vencimento mantida (regra atual). Impacto nos dados de hoje: 0 linha.
- **Onde:** `regras/` (`funcoes.py`, `uc.py`, `features/`, `paridade.py`, `README.md`); `governanca/aplicar_semantica.py`,
  `auditar_metadados.py`, `ontologia.py` (schema `regras` como principal).
- **Conferência:** `behave` 36/36 (123 passos); paridade 100%: gold 29.893.555 linhas e silver 1.596.919, 0 divergência;
  517/517 totais da quarentena reprovados pela função; auditoria sem pendências.
- **Docs atualizadas:** trilha (fase 19) · playbook (M10, matriz, roteiro 18–19, adaptação) · lições (L56–L58) · README.

### Dado pessoal marcado também nos schemas legados
- **O que mudou:** os schemas `*_sql` e `*_ldp` recebem as tags de dado pessoal (`class.*`, `dado_pessoal`,
  `contem_dado_pessoal`, `contem_dado_sensivel`) pela função `tags_dado_pessoal`, a mesma das camadas principais; nenhuma
  outra tag (domínio, camada, certificação) vai para os legados.
- **Por quê:** decisão do usuário; a auditoria mostrou 108 colunas pessoais sem tag nos legados.
- **Onde:** `governanca/aplicar_semantica.py` (`LEGADO`, `tags_dado_pessoal`, `plano_de_tags`).
- **Conferência:** `aplicar_semantica.py --so-tags` sem erros (310 tags de coluna e 14 de tabela criadas); `information_schema`:
  152 colunas legadas com `dado_pessoal` (identificação 48, endereço 42, perfil 38, contato 18, sensível 6), 8 tabelas com
  `contem_dado_pessoal`, 6 com `contem_dado_sensivel`; auditoria: 0 PII sem tag nos 13 schemas, 0 não lidas; prontidão
  92,7 (id 3, igual à id 2).
- **Docs atualizadas:** trilha (fase 17) · playbook (M6) · lições (L55) · README · RESULTADO.md.

### Schemas legados descritos · prontidão 92,7 · auditoria em lote
- **O que mudou:** 682 colunas dos schemas `*_sql` e `*_ldp` descritas com o mesmo dicionário (6 nomes novos e o mapa
  `LEGADO` em `descricoes_colunas.py`); `aplicar_descricoes.py legado` com caminho coluna a coluna em paralelo e nova
  tentativa em `CONCURRENT_UPDATE`; `auditar_metadados.py` lê as tags em lote pelo `information_schema` e mostra
  "tags não lidas" em vez de contar falha de leitura como "sem tag".
- **Por quê:** decisão do usuário (descrever, não aposentar) para fechar a lacuna de metadados da prontidão; a auditoria
  levava 15 min e acusou 147 falsos "dado pessoal sem tag".
- **Onde:** `governanca/descricoes_colunas.py`, `governanca/aplicar_descricoes.py`, `governanca/auditar_metadados.py`.
- **Conferência:** auditoria em 28 s: principais 1.930/1.930 descritas, 380 com `dado_pessoal`, 0 PII sem tag, 0 não lidas;
  legado 682/682. Prontidão **90,5 → 92,7** (metadados 83,5 → 93,5), histórico id 2 (`avaliacao_legado_descrito.json`).
- **Lacuna aceita:** 382 colunas de objetos internos dos pipelines. **Em aberto:** 108 colunas pessoais dos legados sem tag.
- **Docs atualizadas:** trilha (fase 18) · playbook (M6) · lições (L52–L54) · README · RESULTADO.md.

### Histórico da prontidão no Lakebase
- **O que mudou:** database `ontology_readiness` no projeto Lakebase `dqx-studio-db` (branch `dqx`); recurso `lakebase-db`
  no app; app v1.5.0 reimplantado da pasta do workspace com `LAKEBASE_HOST`, `LAKEBASE_ENDPOINT_NAME` e
  `LAKEBASE_DATABASE` no `app.yaml`; scripts `implantar_app.py` (idempotente) e `avaliar.py` (rodar, historico, comparar).
- **Por quê:** pedido do usuário: sem Lakebase cada avaliação valia só para o momento em que rodava.
- **Onde:** `governanca/ontologia_readiness/`.
- **Conferência:** `/api/config` → `history_ready: true`; log "Lakebase pool ready"; avaliação de base gravada (id 1 = 90,5).
- **Docs atualizadas:** playbook (M9) · lições (L49–L51) · RESULTADO.md.

### Tags padrão de domínio e responsável · prontidão 90,5
- **O que mudou:** governed tags `domain` (`pos_venda`), `subject_area` (`cobranca`, `carteira`, `qualidade`) e `data_owner`
  (`financeiro_pos_venda`), ao lado da tag "Pós-venda" do Discover; `aplicar_tag` espera e repete quando o valor da política
  ainda não propagou.
- **Por quê:** a lacuna de domínios (0) do genie-ontology-readiness, que só lê chaves padrão.
- **Onde:** `governanca/ontologia.py` (`DOMINIO_PADRAO`, `RESPONSAVEL`, `TAG_DOMINIO_PADRAO`, `VALORES_DOMINIO_PADRAO`),
  `governanca/aplicar_semantica.py` (plano de tags, políticas e `aplicar_tag`).
- **Conferência:** `information_schema`: `domain` em 7 schemas e 57 tabelas, `data_owner` em 57, `subject_area` em 48
  (17/16/15); segunda execução sem erros. Prontidão **81,3 → 90,5 (Optimized)**, domínios 0 → 92
  (`avaliacao_pos_venda_3.json`).
- **Lacuna aceita:** 3 dos 10 objetos mais acessados sem certificação (bronze bruto e 2 views de janela do DQX), de propósito.
- **Docs atualizadas:** trilha (fase 18) · playbook (M6, M9, adaptação) · lições (L47, L48) · README · RESULTADO.md.

### Prontidão para a Genie Ontology (genie-ontology-readiness v1.5.0)
- **O que mudou:** app `genie-ontology-readiness` instalado direto do Git (sem Lakebase); leitura no catálogo `pos_venda`
  para o app; escopo de usuário `sql` ligado; espaços Genie compartilhados com o app (CAN_READ). Grants em `system` negados
  (Free Edition); `main` e `workspace` não concedidos de propósito.
- **Resultado:** nota 61,1 só com o app e **81,3 (Established)** com a identidade do usuário. Lacunas: domínios e
  responsáveis (0), métricas (76, cresce com a quantidade de metric views) e metadados (83,5, por causa dos schemas legados).
- **Onde:** `governanca/ontologia_readiness/RESULTADO.md` e as respostas JSON.
- **Pendente:** decidir tags de domínio/responsável (resolvido na entrada acima) e o destino dos schemas legados.
- **Docs atualizadas:** trilha (fase 18) · lições (L46).

### Dados pessoais marcados por tag, sem máscara
- **Decisão:** não mascarar CPF, RG, nome, contato e endereço, porque a validação de qualidade precisa dos valores reais;
  marcar onde estão os dados pessoais.
- **O que mudou:** governed tags `dado_pessoal` (identificacao, contato, endereco, perfil, sensivel), `contem_dado_pessoal`
  e `contem_dado_sensivel` (valor `sim`), derivadas da classificação técnica `class.*`.
- **Onde:** `governanca/ontologia.py` (`TAG_DADO_PESSOAL`, `CATEGORIA_DADO_PESSOAL`), `governanca/aplicar_semantica.py`
  (plano de tags e `garantir_valores_tag`).
- **Conferência:** 380 colunas marcadas (identificação 123, endereço 106, perfil 91, contato 45, sensível 15); 18 tabelas com
  `contem_dado_pessoal`, 15 com `contem_dado_sensivel`; nenhuma coluna classificada sem `dado_pessoal`; reaplicação sem erros.
- **Docs atualizadas:** trilha (fase 17) · playbook (M6) · lições (L45).

### DQX Studio agendado junto com a carga diária
- **O que mudou:** 12 tabelas monitoradas agendadas para 06:30 (America/Sao_Paulo), `dq_only`, todas as linhas, **pausadas**;
  comandos `agendar`, `ligar`, `pausar` e `agenda` em `registro_studio.py`; agendamento antigo `pos_venda_janela_diaria`
  removido (configuração em `dqx_studio/regras/resultados/`); tarefa `ligar_dqx_studio` no fim do job; ROTEIRO
  ("Ligar em produção") atualizado.
- **Por quê:** avaliação de qualidade contínua, sem rodar script; o agendador só dispara com o app ligado, e o app para após 24 h.
- **Onde:** `dqx_studio/regras/registro_studio.py`, `carga_diaria/gerar_carga.py`, `carga_diaria/resources/carga_diaria.job.yml`.
- **Conferência:** preflight de permissões sem pendências; disparo real na `dim_data` às 19:58 UTC (`scheduled`, SUCCESS,
  5.844 linhas, 0 erros), depois devolvida para 06:30 e pausada; tarefa do job testada com o app ligado
  (`ACTIVE -> ACTIVE`) e parado (`STOPPED -> ACTIVE`); job implantado com 6 tarefas e agenda PAUSED.
- **Docs atualizadas:** trilha (fase 16) · playbook (M5, matriz, roteiro 16–17) · lições (L43, L44) · ROTEIRO.

### cliente_id fora também da entidade Cliente
- **O que mudou:** `cliente_id` saiu de `ontologia.cliente`; a relação "Cliente possui Apólice" passou a usar `cliente_sk`.
- **Por quê:** decisão do usuário, pela coerência da camada (sem identificadores pessoais). O `cliente_id` é o código que
  circula fora do Databricks e facilita cruzar bases; dentro da ontologia as ligações usam `cliente_sk`. Nenhuma consulta
  da Genie nem painel usava o campo.
- **Onde:** `governanca/gerar_ontologia_sql.py` (view `cliente` e `RELACOES`).
- **Conferência:** view recriada com `garantir_view(..., ddl=...)`: 5/5 tags e Wiki devolvidas; nenhum `cliente_id` no schema
  `ontologia`; `auditar_metadados.py` 1.930/1.930 e 0 PII sem tag.
- **Docs atualizadas:** trilha (fase 15) · README (situação).

### Ontologia sem identificadores pessoais
- **O que mudou:** `cliente_id` saiu das views `ontologia.pendencia` e `ontologia.pagamento`; `garantir_view` ganhou o
  parâmetro `ddl` (recria com o DDL completo, que traz a descrição das colunas); exclusão da coluna tirada do `genie.py`;
  Page "Cliente" liga pendências pelo `cliente_sk`.
- **Por quê:** a camada de ontologia promete não ter identificadores pessoais (achado da avaliação da Genie).
- **Onde:** `governanca/gerar_ontologia_sql.py`, `governanca/genie.py`, `governanca/ontologia.py`, `carga_diaria/views_preservadas.py`.
- **Conferência:** `cliente_id` só em `ontologia.cliente`; 5 tags e Wiki publicada nas duas views; `genie.py avaliar` 27/27;
  `auditar_metadados.py` 1.931/1.931.
- **Pendente (resolvido na entrada acima):** decidir se `ontologia.cliente` mantém `cliente_id`.
- **Docs atualizadas:** trilha (fase 15) · playbook (M6) · lições (L26, L42).

## 20/11/2026

### Documentação de aprendizagem e playbook
- **O que mudou:** pasta `docs/` com trilha, playbook, lições, este CHANGELOG e inventário gerado por script.
- **Onde:** `pos_venda/docs/`.

### Metadados resilientes e cobertura de 100%
- **O que mudou:** `carga_diaria/views_preservadas.py` (`garantir_view`) usado pelo notebook 25, pelo replay e pelo painel de
  qualidade; 89 descrições nas views `v_painel_*`; filtro das execuções do Registro na view do painel de qualidade.
- **Por quê:** o job recriava 9 views por dia e apagava tags, tags de coluna e Wikis; o painel mostrava uma "semana 6".
- **Conferência:** `auditar_metadados.py` → 1.933/1.933 colunas principais descritas; `aplicar_e_testar.py` → tudo certo;
  9/9 views do job "igual"; job implantado e PAUSED.
- **Docs atualizadas:** trilha (fase 14) · playbook (M6) · lições (L20–L23).

### Avaliação independente da Genie
- **O que mudou:** genie-best-practices-agent em modo offline + avaliação oficial; descrições nos 87 campos das metric views;
  meses, semanas e anos como `date`; gabaritos atualizados; descrição de `Semana` e exemplo filtrando por `Dia`.
- **Conferência:** Genie Eval 13/13 e 14/14; `genie.py avaliar` 27/27.
- **Docs atualizadas:** trilha (fase 13) · lições (L04, L05, L32, L36, L37, L41).

### Painéis financeiros com fechamento, variação mensal e acumulado
- **O que mudou:** datasets `ds_carteira_mes` e `ds_recuperacao_mes`; segunda linha de KPIs da Diretoria; tabelas mensais no
  Analista; Ato 10 no ROTEIRO.
- **Conferência:** 9/9 widgets novos executados; painéis publicados.
- **Docs atualizadas:** trilha (fase 12) · lições (L27, L38).

### Padrões de metric view (uc-semantics-patterns)
- **O que mudou:** saldo de fechamento e de início, mês anterior e variação mensal, acumulado no mês e no ano, ranking.
- **Conferência:** 64/64 combinações produto × mês iguais ao SQL manual; Genie 27/27.
- **Docs atualizadas:** trilha (fase 12) · lições (L27–L31).

### Catálogo databricks-solutions
- **O que mudou:** 147 repositórios avaliados para o projeto; página publicada; `referencias/databricks_solutions/`.

## 19/11/2026

### Registro de Regras e tabelas monitoradas no DQX Studio
- **O que mudou:** 69 modelos, 12 tabelas monitoradas, 194 checagens aprovadas; recálculo das notas.
- **Docs atualizadas:** trilha (fase 7) · lições (L15–L17).

### Painéis de KPIs financeiros (Diretoria e Analista)
- **O que mudou:** bundle `paineis_financeiros` com 2 painéis sobre as metric views e link para a Genie.

### Correção do DQX Studio (Lakebase)
- **O que mudou:** endpoint Lakebase religado (`spec.disabled=false`) e app reiniciado.
- **Docs atualizadas:** lições (L19).

### Genie para o analista e o diretor financeiro
- **O que mudou:** 2 espaços com instruções, exemplos e perguntas de avaliação, validados no warehouse.

### Governança semântica e ontologia
- **O que mudou:** auditoria de metadados; descrições; governed tags; domínio Pós-venda com 3 subdomínios; 18 Pages; 51 Wikis;
  classificação LGPD; certificação; schema `ontologia` com 10 entidades e 4 metric views.

### Painel de qualidade e roteiro de demonstração
- **O que mudou:** 6 views `v_painel_*`, painel "pos_venda · Qualidade de dados", ROTEIRO em atos.

### Ciclos de incidentes, janelas e replay no DQX Studio
- **O que mudou:** regras por código; 5 semanas simuladas com incidentes; views `v_*_janela` e replay com todas as linhas.
- **Docs atualizadas:** lições (L12–L14, L18).

## 18/11/2026

### DQX Studio instalado
- **O que mudou:** app pelo bundle oficial com patch para o warehouse existente; estado no Lakebase.

### Carga diária incremental com histórico
- **O que mudou:** bundle `carga_diaria`: eventos no bronze, silver SCD1/SCD2 com Auto CDC, dimensões e fato snapshot diária com PK/FK.

### Medalhão em duas versões
- **O que mudou:** bundle `medalhao` com notebooks SQL e Lakeflow gerados por `gerar_sql.py` (hoje legado).

### Dados sintéticos
- **O que mudou:** one-table com 500.000 parcelas e defeitos injetados (`01_gerar_one_table.py`).
