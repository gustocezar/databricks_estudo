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

## 22/11/2026

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
