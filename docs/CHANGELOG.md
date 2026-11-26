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

## 26/11/2026

### Regras com vigência, questionário do negócio e triagem (P41)
- **O que mudou:**
  - **Catálogo** (`regras/catalogo/catalogo_regras.yml`).
    - As 14 regras de qualidade (11 da barreira e 3 avisos) têm versão e vigência pela data do dado, com dono, limite
      de taxa aceita, motivo, origem e aprovação. Todas estão na versão 1, "desde sempre".
    - O YAML do DQX como código passou a ser **gerado** do catálogo. Cada versão vira uma checagem com `filter` pela
      data e a versão no `user_metadata`.
  - **DQX como código.** O notebook ganhou o modo `ensaio`, que não grava nada e devolve as contagens por regra e
    versão, e a coluna `versao` em `dq_metricas_regras`, gravada com `mergeSchema`.
  - **`pos_venda.regras`:**
    - as tabelas `catalogo_regras` e `triagem_regras`, esta com `CHECK` nas 4 classificações;
    - a função `versao_vigente(regra, dia)`;
    - as visões `v_falhas_regras`, `v_triagem_pendente`, `v_mudancas_regras` e `v_retroalimentacao`.
  - **Questionário do negócio** (`regras/questionario/QUESTIONARIO_NEGOCIO.md`).
    - Tem 5 blocos, e cada pergunta aponta o campo do catálogo que preenche.
    - Inclui o rito (semanal, mensal e trimestral) e 7 perguntas em aberto para o dono, tiradas do dado real.
  - **Ensaio fictício** (`regras/catalogo/ensaio/`): `QUINZENAL` aceita a partir de 05/01/2027.
  - **Garantias.** O gerador tem 17 testes sem rede e 11 checagens no `conferir`, e há 8 cenários BDD do catálogo
    fora do portão da carga. O CI roda `testar` e `validar` em todo push e, com segredos, o BDD do catálogo.
  - **Tags.** `atualizacao=sob_demanda` nas tabelas de catálogo da ontologia e nas tabelas do catálogo de regras
    (L96); `subject_area=qualidade` no schema `regras`.
  - **Documentação:** framework P41, lições L95 e L96, fase 29 da trilha, guia 06, spec (E2, T2.3, T4.8 e T4.9),
    AGENTS.md (decisão e "fonte × gerado"), README do DQX como código e das regras, e doc 05 (plano de ação com
    ciclo).
- **Por quê:** pedido do dono. Ele queria questionários para o negócio criar regras de avaliação de qualidade, métricas
  e observabilidade, e uma retroalimentação que verifique sempre o que dá errado, lembrando que uma regra pode valer só
  por um período.
- **Onde:** `regras/catalogo/`, `regras/questionario/`, `dqx_codigo/aplicar_dqx.py`, `dqx_codigo/checks_pendencias.yml`
  (gerado), `dqx_codigo/ensaio/`, `governanca/ontologia.py`, `governanca/aplicar_semantica.py`,
  `conformidade/gerar_conformidade.py` (texto da tag `atualizacao`), `.github/workflows/ci.yml` e os objetos de
  `pos_venda.regras`.
- **Conferência:**
  - **Gerador sem rede.** `gerar_catalogo.py testar`: 17 de 17. `validar`: catálogo válido, YAML em dia, ensaio válido.
    O YAML de produção tem as mesmas 14 checagens de antes, só com o `user_metadata` a mais.
  - **`gerar_catalogo.py aplicar`:** 10 comandos SUCCEEDED.
  - **`conferir`:** 11 de 11.
    - A tabela é igual ao YAML (14 versões).
    - Há uma versão por regra em cada um dos 236 dias.
    - Os motivos da quarentena estão todos no catálogo.
    - As falhas da barreira na visão são as linhas da quarentena (6.712).
    - As linhas do DQX são válidos mais quarentena (49.972).
    - `versao_vigente` responde.
    - As 5 visões e a tabela respondem.
  - **BDD do catálogo:** `behave catalogo/features` deu 8 de 8 cenários (17 passos). A triagem de teste com
    classificação inválida foi recusada pelo `CHECK`, e `triagem_regras` continua com 0 linhas.
  - **Ensaio no DQX:** `bundle run dqx_codigo` com `modo=ensaio`, na janela de 27/12/2026 a 09/01/2027 (101.636
    eventos). `gerar_catalogo.py ensaio 59410578624066` deu DQX = SQL nas 15 checagens.
    - Os eventos com erro foram 3.388, igual à quarentena da barreira na janela.
    - A periodicidade v1 reprovou 105 (`QUINZENAL` 52 + `BIMESTRAL` 53, até 04/01) e a v2 reprovou 68 (só
      `BIMESTRAL`, de 05/01); as 84 `QUINZENAL` de 05/01 em diante passaram.
  - **Tags:** `auditar_metadados.py` e depois `aplicar_semantica.py --so-tags`, com 30 tags criadas. Os 6 objetos de
    `regras` ficaram com `subject_area=qualidade`; as 3 tabelas da ontologia e as 2 do catálogo ficaram com
    `atualizacao=sob_demanda`.
  - **Triagem:** `v_triagem_pendente` mostra 69 semanas × regra acima do limite (semanas de 30/11/2026 a 04/01/2027 no
    dado), em 11 regras da barreira e 12 do DQX. Ainda não há triagem registrada.
  - **Repositório:** varredura sem achado, 0 link quebrado, `compileall` ok e todos os YAML legíveis.
- **Docs atualizadas:** framework (P41) · lições (L95, L96) · trilha (fase 29) · guia 06 · spec · AGENTS.md · doc 05
  · `docs/README.md` · READMEs de `dqx_codigo/`, `regras/` e `regras/catalogo/` · as duas apresentações · o doc do
  framework

### Rodada de conformidade e primeiros dias da operação ligada
- **O que mudou:**
  - **Tags de custo.** Os 4 jobs do pós-venda ganharam as tags `project=pos_venda` e `team=squad-pos-venda` (PLT01,
    P31).
  - **Certificação.** As 3 tabelas `dq_*` da gold foram certificadas depois da conferência (EST02).
  - **Sonda diária.** O job `pos_venda_conformidade_sonda` (bundle novo em `conformidade/`, notebook
    `src/sonda_diaria.py`, timeout de 20 min) faz o `registrar` às 06:45 com `spark.sql`.
  - **`registrar` local.** Agora aborta sem gravar quando uma chamada falha por rede ou token (L94). A foto falsa das
    09:50 (170 linhas, com 11 views boas dadas como quebradas) foi apagada de `sonda_views`.
  - **CI.** Passa a validar 7 bundles.
- **Por quê:** pedido do dono, depois da pergunta "qual o próximo passo?".
- **Onde:** `carga_diaria/resources/*.job.yml`, `medalhao/resources/*.job.yml`, `governanca/ontologia.py`
  (`CERTIFICADAS`), `conformidade/databricks.yml`, `conformidade/src/sonda_diaria.py`,
  `conformidade/gerar_conformidade.py`, `.github/workflows/ci.yml`, AGENTS.md, `docs/07_SUSTENTACAO.md`,
  `docs/04_FRAMEWORK.md` (P37), lição L94 e a fase 28 da trilha.
- **Conferência:**
  - **Primeiros dias da operação.**
    - Carga: 25/11 em 14,9 min e 26/11 em 16,7 min, as duas SUCCESS e dentro do SLA (terminaram às 05:15 e às 05:17).
    - Studio: 24 de 24 execuções SUCCESS.
    - Alerta de sustentação: OK. O Lakebase está ACTIVE e o app, RUNNING.
  - **Jobs.** `databricks jobs list` mostra os 5 jobs do pós-venda com `project` e `team`. O que falta em PLT01 é o
    job do DQX Studio, que é gerido pelo app.
  - **Certificação.** Antes de certificar, conferimos as tabelas `dq_*`:
    - recebidos = bronze (1.718.895);
    - aptos = silver (1.712.183);
    - barrados = quarentena = soma por motivo (6.712);
    - linhas e órfãs da fato na janela = fato (12.280.092 e 8.479).
  - **Job da sonda.** A primeira execução deu SUCCESS em 7,6 min: 170 views, 148 respondem e 22 quebradas (as mesmas,
    fora do domínio). O histórico do dia tem 28 regras.
  - **`conferir` da conformidade, depois das mudanças:** as 9 checagens passaram.
    - São 10.209 verificações em 268 ativos: **16 regras atendem**, 10 estão em atenção e 2 críticas, ambas fora do
      domínio (antes eram 15, 11 e 2).
    - EST02 e USO01 passaram a atender; OTM01 está em 95,2%.
    - PLT01 tem 1 falha, o job do DQX Studio.
    - Os ativos sob demanda saíram da OTM01 (L96), e a descrição curta da coluna `tipo` nas 3 visões de regras foi
      completada (DOC04).

## 24/11/2026

### Operação ligada: agendas, timeouts, área de negócio, CI e ensaio do spec
- **O que mudou:**
  - **Timeouts (PLT03, P40):**
    - carga diária com 33 min, o valor sugerido pela sustentação (2 × p95);
    - setup e medalhão SQL com 30 min, e medalhão Lakeflow com 60 min, porque têm pouco histórico.
  - **Área de negócio (TAG01):** os 17 ativos sem `subject_area` (`bi.*`, `dq.v_painel_*` e metadados da ontologia)
    ganharam a tag. A regra fica em `SUB_SEM_WIKI` (`governanca/ontologia.py`), aplicada por `aplicar_semantica.py`.
  - **Agendas ligadas, a pedido do dono:**
    - carga às 05:00, Studio às 06:30 (12 tabelas) e alerta de sustentação às 06:20;
    - o padrão da carga e do alerta nos bundles passou a ser `UNPAUSED`;
    - o medalhão da primeira versão continua pausado;
    - para ligar o Studio, o endpoint do Lakebase foi reabilitado e o app reiniciado (L19).
  - **CI:** `.github/workflows/ci.yml` roda a varredura (L70), a compilação, os YAML e os links. Com os segredos
    `DATABRICKS_HOST` e `DATABRICKS_TOKEN`, valida os 6 bundles e roda os 36 cenários BDD. O deploy é manual
    (`workflow_dispatch`, ambiente `dev`).
  - **Ensaio do spec:** as etapas 0 a 2, só com leitura, sobre a bronze tratada como base nova
    (`specs/ensaio_pos_venda_bronze/`). O spec ganhou a consulta do dono, as consultas do perfil na ficha, as variantes
    no de-para e a sugestão de aviso de chave repetida. Lição L93.
  - **AGENTS.md:** a decisão "agendas pausadas" virou "agendas ligadas desde 24/11", com o comando de CI.
- **Por quê:** pedido do usuário: executar os próximos passos do time (timeouts e área de negócio, ligar agenda e
  alerta, CI/CD dos bundles, ensaio do spec).
- **Onde:** `carga_diaria/databricks.yml` e `resources/*.job.yml`, `medalhao/resources/*.job.yml`,
  `sustentacao/databricks.yml`, `governanca/ontologia.py`, `governanca/aplicar_semantica.py`,
  `.github/workflows/ci.yml`, `specs/ensaio_pos_venda_bronze/`, os modelos do spec, `docs/06`, `docs/07`, `docs/01`,
  `docs/03`, `docs/04`, `docs/README.md`, AGENTS.md e os gerados da conformidade.
- **Conferência:**
  - **Jobs:** `databricks jobs list` mostra `pos_venda_carga_diaria` com timeout de 1.980 s e agenda `UNPAUSED`; o
    setup e o medalhão SQL com 1.800 s; o medalhão Lakeflow com 3.600 s; os medalhões continuam `PAUSED`.
  - **Studio:** `registro_studio.py ligar` deu "12 tabelas agendadas", com `pausado=False`. O app está RUNNING depois
    de reabilitar o Lakebase.
  - **Conformidade:** `aplicar`, `registrar` e `conferir` ok, com 10.013 verificações. Antes eram 13, 12 e 3; agora:
    - 15 regras atendem, 11 em atenção e 2 críticas;
    - TAG01 em 100%;
    - PLT03 com 6 falhas, todas do bundle de observabilidade.
  - **CI:** a varredura, `compileall`, os YAML e os links rodaram localmente sem achado. Os bundles da carga e da
    sustentação passam em `bundle validate`.
  - **Ensaio:** 10 tarefas de E0 a E2 marcadas com resultado (1.718.895 linhas, 236 dias, 10.277 chaves repetidas).
- **Docs atualizadas:** framework (provas de P02 e P03) · lições (L93) · trilha (fase 28) · guia 06 · spec (modelos)
  · manual de sustentação · `docs/README.md` · AGENTS.md

### Manual de sustentação (docs/07) e etapa E8 do spec
- **O que mudou:**
  - **Manual novo:** [`07_SUSTENTACAO.md`](07_SUSTENTACAO.md) tem 12 partes:
    - o catálogo do que roda, com a cadeia carga 05:00 → Studio 06:30 → painéis e Genie;
    - SLAs e metas, onde olhar e a rotina diária, semanal e mensal;
    - 12 runbooks (sintoma → onde ver → diagnóstico → ação → como confirmar);
    - reprocessamento, mudança e deploy com rollback, e o RACI;
    - capacidade e custo, indicadores e o modelo de incidente sem culpa;
    - o que muda em produção.

    As metas da base curta estão marcadas como provisórias.
  - **Ligações:** a P40 e o M13 apontam para o manual.
  - **Spec:** ganhou a etapa E8 (sustentação, antes de ligar as agendas), com o critério de aceite e as tarefas T8.1 a
    T8.4. São 41 tarefas no total.
  - **Guia 06:** ganhou a etapa 8.
  - **Prompt do Copilot:** passou a ir até a E8.
  - **Onde está cada resposta:** o AGENTS.md ganhou "Algo falhou ou está lento → docs/07_SUSTENTACAO.md".
  - **READMEs:** o `docs/README.md` e o README citam o manual.
- **Por quê:** pedido do usuário. As visões de sustentação dizem o que aconteceu; o manual diz o que fazer, quem faz e
  como confirmar.
- **Onde:** `docs/07_SUSTENTACAO.md`, `docs/04_FRAMEWORK.md`, `docs/02_PLAYBOOK.md`, `docs/06_GUIA_BASE_BRUTA.md`,
  `specs/aplicar-base-bruta/SPEC.md`, `specs/aplicar-base-bruta/modelos/TAREFAS.md`,
  `.github/prompts/aplicar-base-bruta.prompt.md`, `AGENTS.md`, `docs/README.md`, `README.md`.
- **Conferência:**
  - os links relativos e as âncoras dos documentos alterados resolvem (script de conferência, 12 arquivos);
  - o modelo tem 41 tarefas;
  - os números do manual vêm das tabelas de sistema e das visões de 24/11. Os da linha de base estão marcados como
    provisórios.
- **Docs atualizadas:** framework (P40, P39) · playbook (M13) · guia 06 (etapa 8) · spec (E8) · `docs/README.md` ·
  README · AGENTS.md

### Sustentação: tempo de execução dos jobs e do pipeline diários (P40)
- **O que mudou:**
  - **Gerador novo:** `sustentacao/gerar_sustentacao.py` gera o schema `pos_venda.sustentacao`, com 14 visões:
    - execuções por job, tarefa e update do pipeline (`system.lakeflow.*_timeline`);
    - volume por dia e por execução (bronze e fato);
    - linha de base: mediana e p95 das últimas 20 execuções com sucesso, com mínimo de 5;
    - desvios: acima do p95 ou de 1,5 vez a mediana, com o excesso e a causa provável;
    - SLA com meta às 06:15, a última execução de cada job, a matriz de resiliência por tarefa e o que o alerta avisa.
  - **Bundle `sustentacao/`:** o painel AI/BI "pos_venda · Sustentação", com a página "Sustentação", e o alerta SQL
    diário das 06:20, pausado, com 1 disparo por dia (PLT06).
  - **Conformidade:** o schema `sustentacao` entrou em `CAMADAS` como "apoio".
  - **Reaproveitado, sem duplicar:** a atribuição de jobs e pipelines (`finops.config_atribuicao`), o custo
    (`finops.uso_jobs_diario`), o frescor (USO01) e o timeout (PLT03).
- **Por quê:** pedido do usuário. Para a sustentação em produção faltavam a visão por tarefa e por pipeline, a linha
  de base, os desvios, o SLA, o volume, o alerta e o painel.
- **Onde:** `sustentacao/` (gerador, SQL, painel, bundle e README), `conformidade/gerar_conformidade.py` e
  `conformidade.sql`, `conformidade/README.md`, `docs/` (trilha, playbook, lições, framework e README),
  `README.md`, `AGENTS.md`.
- **Conferência:**
  - **`testar`:** antes de criar, rodou sem criar nada as 14 visões e os 10 conjuntos do painel.
  - **`aplicar`:** criou as 14 visões. Rodado de novo depois do piso do alerta, recriou só as 2 que mudaram.
  - **`conferir`:** passou nas 13 checagens:
    - 186 execuções de job, 249 de tarefa e 13 updates, iguais às tabelas de sistema;
    - bronze de 1.718.895 eventos e fato de 34.026.469 linhas, iguais por dia, por execução e nas tabelas;
    - as 7 medianas por tarefa iguais ao cálculo direto;
    - 7 de 7 tarefas na matriz;
    - 0 colunas sem descrição;
    - os 10 conjuntos do painel respondem com o catálogo e o schema do bundle.
  - **Linha de base:** carga com mediana de 14,53 min e p95 de 16,05 min; folga projetada de 59,0 min até 06:15;
    timeout sugerido de 33 min (provisórios, 12 execuções manuais).
  - **Desvios:** 50, dos quais 40 do task runner do DQX Studio e 10 da carga.
  - **Alerta:** na primeira conferência, avisaria 3 vezes por ruído, com segundos acima de um p95 de base curta. Com o
    piso de 60 s e sem desvio explicado por volume (L92), avisa 0 agora e 2 em 30 dias:
    - o job inteiro 67 s acima do limite, com o mesmo volume;
    - a fato em 22/11, 166 s acima, por espera de computação.
  - **Deploy:** `databricks bundle deploy` criou o painel e o alerta (2 criados, 0 apagados). O painel está publicado e
    o alerta está `PAUSED`, às 06:20, America/Sao_Paulo, 1 disparo por dia. O painel não foi aberto no navegador: o
    workspace pediu login. Os conjuntos foram conferidos pela API.
  - **Conformidade:**
    - `alertas` leu 6 alertas e `aplicar` recriou `config_camadas` e `recursos`;
    - as pendências por regra ficaram iguais antes e depois (nenhuma nova);
    - `sustentacao` entrou como "apoio", e as 14 visões só aparecem em EST04 (dono pessoa, como todo ativo do Free
      Edition);
    - `conferir` passou nas 9 checagens, com 9.966 verificações e 370 pendências.
- **Docs atualizadas:** trilha (fase 27) · playbook (módulo M13, 2 linhas na matriz, passo 20 do roteiro) · lições
  (L89 a L92) · framework (P40) · `docs/README.md` · README · AGENTS.md · README da conformidade

### Pendências executadas: DQX como código, correções L86 e L87, Genie 29/29 e Power BI 21/21
- **O que mudou:**
  - **DQX como código (trilha A):** rodou no workspace. O job passou a se chamar `pos_venda_dqx_codigo`, com tags
    `project` e `team` e timeout de 1 hora.
    - O notebook passou a aplicar, a cada execução, as descrições da tabela de entrada e a tag `dado_pessoal` das
      colunas, além das tags de domínio e LGPD da tabela.
    - A periodicidade virou `sql_expression` com `IN` (L88).
    - O schema `pos_venda.dqx_codigo` entrou como "apoio" em `CAMADAS` da conformidade.
  - **L86 (painel):** `ds_carteira_mes` lê início, fechamento e mês anterior de cada produto × canal nas datas da carteira
    inteira, com zero para o grupo que não existia. Os dois painéis foram publicados no mesmo link.
  - **L87 (ontologia):** produto, categoria, canal, regional e UF ganharam o membro "não identificado" nas metric views.
    A gold não mudou, e o DQX Studio continua vendo as órfãs. A semântica foi reaplicada depois (L31).
- **Por quê:** pedido do usuário: executar as pendências sem sobrescrever nada do DQX Studio.
- **Onde:** `dqx_codigo/` (`aplicar_dqx.py`, `checks_pendencias.yml`, `databricks.yml`, `README.md`),
  `paineis_financeiros/gerar_paineis.py` e `src/*.lvdash.json`, `governanca/gerar_ontologia_sql.py`, `ontologia.sql`,
  `ontologia_sql.json`, `conformidade/gerar_conformidade.py` e os gerados, `governanca/genie/avaliacao.json`,
  `governanca/genie/avaliacao_2411b.log`, `paineis_financeiros/powerbi/VALORES_DE_REFERENCIA.md`.
- **Conferência:**
  - **DQX como código:**
    - a primeira execução falhou com `UNRESOLVED_COLUMN` `MENSAL` (L88), e a segunda terminou SUCCESS em cerca de
      7 min;
    - na janela de 26/12 a 01/01 (49.972 eventos da bronze), deu 3.229 em quarentena, o mesmo número da barreira, e
      46.743 válidas;
    - as 14 regras estão em `dq_metricas_regras`;
    - as 3 tabelas têm 0 coluna sem descrição e 25 colunas com `dado_pessoal`.
  - **Power BI:** `gerar_powerbi.py referencia` deu "PARIDADE: 100%". O crescimento de janeiro é R$ 1.405.736,27 nos
    dois lados, e a variação 3,91%.
  - **Genie:** `genie.py avaliar` deu "RESULTADO: 29/29". A pergunta por produto agora traz "Produto não identificado",
    R$ 779,34.
  - **Ontologia:** `aplicar_sql.py ontologia_sql.json` deu 21/21. `aplicar_semantica.py` publicou 51/51 Wikis.
  - **Conformidade:**
    - `aplicar`, `registrar` e `conferir` ok, com 9.494 verificações;
    - situação igual (13 atendem, 12 em atenção, 3 críticas) e nenhuma pendência nova;
    - o job novo atende PLT01 e PLT03.
  - **DQX Studio:** nada mudou no app, no Lakebase `dqx-studio-db` nem em `main.dqx_studio`.
- **Docs atualizadas:** framework (P07, P18, P21, P23, P29, P38) · lições (L86 e L87 corrigidas, L88) · trilha (fase
  26) · guia 06 · spec · skills e ganhos · `docs/README.md` · READMEs do DQX como código e dos painéis

### E-mail do autor fora do repositório (README e evidências do DQX Studio)
- **O que mudou:** o e-mail do autor virou `<seu-usuario>` em `dqx_studio/README.md` (caminho do bundle) e nos 2
  arquivos de evidência do Studio em `dqx_studio/regras/resultados/`.
- **Por quê:** pedido do usuário. O repositório é público, e o e-mail não precisa aparecer na documentação (L70).
- **Onde:** `dqx_studio/README.md`, `dqx_studio/regras/resultados/backup_regras_tabela_unica_12_tabelas.json`,
  `dqx_studio/regras/resultados/agendamento_antigo_pos_venda_janela_diaria.json`.
- **Conferência:**
  - `git grep` confirma que o e-mail saiu da documentação.
  - Nos 2 arquivos de evidência de `dqx_studio/regras/resultados/` (390 ocorrências nos campos `created_by` e
    `updated_by`), a troca foi feita com autorização do usuário, como exceção à regra do AGENTS.md. Nenhum script lê
    esses arquivos, e os dois continuam JSON válido.
  - Ele continua também no histórico do Git.
- **Docs atualizadas:** nenhuma além do README do DQX Studio

### Spec executável para aplicar o framework a outra base
- **O que mudou:**
  - [`specs/aplicar-base-bruta/SPEC.md`](../specs/aplicar-base-bruta/SPEC.md) é o contrato que o agente executa. Traz
    objetivo, escopo e fora de escopo, entradas e saídas, as restrições R1 a R8, os critérios de aceite por etapa
    (E0 a E7, com E4A e E4B separados), os gates G1 a G9, a regra de escolha da trilha do DQX e os riscos conhecidos.
  - Os modelos em `specs/aplicar-base-bruta/modelos/` são copiados para `specs/<nome-da-base>/`:
    - `TAREFAS.md`: 37 tarefas com verificação, saída e linha de resultado;
    - `FICHA.md`, `MAPEAMENTO.md` e `DECISOES.md`, com o plano de ação.
  - O prompt `/aplicar-base-bruta` passou a seguir o spec tarefa por tarefa e a retomar da primeira sem `[x]`.
  - O guia 06, as instruções do Copilot, o framework (P39), o README, o AGENTS.md e `docs/README.md` apontam para o
    spec.
- **Por quê:** pedido do usuário. Além do guia, que explica, o Copilot no VS Code precisa de um contrato verificável:
  cada tarefa com um comando que prova que terminou, pontos de aprovação explícitos e progresso salvo no repositório
  para retomar.
- **Onde:** `specs/aplicar-base-bruta/`, `.github/prompts/aplicar-base-bruta.prompt.md`,
  `.github/copilot-instructions.md`, `docs/06_GUIA_BASE_BRUTA.md`, `docs/04_FRAMEWORK.md`, `README.md`, `AGENTS.md`,
  `docs/README.md`.
- **Conferência:**
  - **Tarefas e gates:** 37 tarefas no modelo e 9 gates no spec.
  - **Links:** os links do spec e dos documentos alterados resolvem. Os dos modelos resolvem a partir de
    `specs/<nome-da-base>/`, conferidos numa cópia de teste.
  - **Uso real:** o spec ainda não foi executado pelo Copilot numa base real.
- **Docs atualizadas:** framework (P39) · guia 06 · `docs/README.md` · README · AGENTS.md

### Reconferência da Genie e do Power BI; guia para outra base com o Copilot; DQX em duas trilhas
- **O que mudou:**
  - **Reconferência com os dados até 09/01/2027:**
    - a Genie deu 28/29 (era 29/29 em 21/11);
    - a paridade do Power BI deu 20/21 (era 21/21 na foto de 25/12);
    - as duas diferenças vêm dos vazamentos da semana 7 e viraram as lições L86 e L87.
  - **Guia novo:** [`06_GUIA_BASE_BRUTA.md`](06_GUIA_BASE_BRUTA.md) aplica o framework a uma base bruta de pendências
    no Databricks, com as etapas 0 a 7, a ficha da base, o mapeamento, o que muda por cenário e o prompt para o
    Copilot.
  - **Copilot:** `.github/copilot-instructions.md` e o prompt `.github/prompts/aplicar-base-bruta.prompt.md`.
  - **Trilha A do DQX (como código):** `dqx_codigo/` com as 11 regras de erro da barreira em YAML e 3 avisos, um
    notebook que separa válidos e quarentena e grava as métricas por regra, e um bundle sob demanda.
  - **Framework:** P38 (DQX em duas trilhas) e P39 (guia executável por agente); as provas de P07, P18, P21 e P23
    ganharam a reconferência.
  - **Outros documentos:**
    - playbook: M5 com as duas trilhas e o Passo 0 com a pergunta sobre conceder privilégio a um app;
    - trilha: fase 26;
    - skills: o plano de ação ganhou dois itens.
- **Por quê:** pedido do usuário:
  - reconferir a Genie e o Power BI com os dados novos;
  - deixar o framework capaz de conduzir o Copilot na aplicação a uma base bruta;
  - separar o DQX como código do DQX como app, porque o app pede privilégio no catálogo que nem todo time pode
    conceder.
- **Onde:** `docs/06_GUIA_BASE_BRUTA.md`, `dqx_codigo/`, `.github/`, `docs/01` a `05`, `README.md`, `AGENTS.md`,
  `paineis_financeiros/README.md`, `paineis_financeiros/powerbi/README.md`, `governanca/genie/avaliacao.json` (gerado),
  `governanca/genie/avaliacao_2411.log`, `paineis_financeiros/powerbi/VALORES_DE_REFERENCIA.md` (gerado).
- **Conferência:**
  - **Genie:** `genie.py avaliar` → "RESULTADO: 28/29". A que errou ("saldo em cobrança externa por produto hoje")
    filtrou `Produto IS NOT NULL` e deixou de fora R$ 779,34 numa linha sem produto (L87).
  - **Power BI:** `gerar_powerbi.py referencia` → 20/21. "Crescimento da carteira no mês" deu R$ 1.403.002,55 no
    painel e R$ 1.405.736,27 na lógica DAX. Uma consulta em `pos_venda.bi.carteira_diaria` mostrou 17 grupos produto ×
    canal que começam depois de 01/01, somando R$ 3.070,71 no primeiro dia (L86).
  - **DQX como código:** `databricks bundle validate` em `dqx_codigo/` → "Validation OK!". O YAML tem 14 checagens (11
    erros). O aviso de periodicidade pega os valores novos da bronze (`QUINZENAL`, 136; `BIMESTRAL`, 121). O job **não
    foi executado**.
  - **Links:** os links relativos dos documentos novos e alterados resolvem. As fontes novas responderam 200 (DQX,
    PyPI, GitHub Copilot, VS Code).
- **Docs atualizadas:** framework (P38, P39, provas) · playbook (Passo 0, M5, como adaptar) · lições (L86, L87) ·
  trilha (fase 26) · `docs/README.md` · README · AGENTS.md · skills e ganhos

### Mapa de skills, plano de ação e qualidade na Genie (documento 05 e apresentação para o diretor)
- **O que mudou:**
  - Documento novo [`05_SKILLS_E_GANHOS.md`](05_SKILLS_E_GANHOS.md):
    - as 11 skills Databricks consultadas, com fase, prática, pasta e ganho medido de cada uma;
    - como ajudam na governança, nas métricas de qualidade, no plano de ação para os dados ruins e na Genie;
    - a ordem das skills para reaplicar em outro domínio e os limites do mapa.
  - Apresentação "Pós-venda: entrega final" para o Diretor de Dados (claude.ai, privada), com 20 slides:
    - os fluxos de dados, de qualidade (DQX) e de observabilidade;
    - o plano de ação, a qualidade na Genie e o slide de skills.
  - `docs/README.md`, `README.md`, `AGENTS.md` e o quadro de documentos do framework apontam para o 05.
- **Por quê:** pedido do usuário: mapear as skills usadas e consultadas para mostrar a linhagem do estudo, a
  aplicação e os ganhos. Explicar também como ajudam na governança, nas métricas de qualidade, no plano de ação
  para os dados ruins e na Genie.
- **Onde:** `docs/05_SKILLS_E_GANHOS.md`, `docs/README.md`, `README.md`, `AGENTS.md`, `docs/04_FRAMEWORK.md`.
- **Conferência:**
  - **Skills:** as chamadas registradas nas conversas do projeto listam 11 skills Databricks. As referências mais lidas
    são as de genie-agents, aibi-dashboards e metric-views.
  - **Conformidade:** consulta em `pos_venda.conformidade.boas_praticas_dados` em 24/11 deu 13 regras que atendem,
    12 em atenção e 3 críticas. Entre as críticas, TAG01 tem 17 ativos sem `subject_area` e USO03 tem 22 views
    quebradas.
  - **Genie:** em `governanca/genie/avaliacao.json`, 3 das 29 perguntas são sobre qualidade, e as 3 acertaram.
  - **Apresentação:** os 20 slides, renderizados no Chrome headless, cabem na área útil. Os links relativos do 05
    resolvem.
- **Docs atualizadas:** framework (quadro de documentos) · `docs/README.md` · README · AGENTS.md · trilha, playbook e
  lições: nenhuma

## 23/11/2026

### Últimos casos do catálogo de qualidade (09/01/2027)
- **O que mudou:**
  - O gerador ganhou 4 incidentes para o dia 09/01/2027:
    - I35: atraso zerado, que a barreira barra;
    - I36: cliente sem data de nascimento;
    - I37: produto sem código, como `PRODUTO SEM CODIGO`;
    - I38: ponto de venda sem código, como `PONTO SEM CODIGO`.
  - O ciclo 8 (08/01 a 14/01) entrou em `rodar_ciclos.py`, e o painel de qualidade fala da semana 8.
- **Por quê:** pedido do usuário: carregar mais um dia para as 5 regras que ainda não tinham exemplo.
- **Onde:** `carga_diaria/gerar_carga.py` (e o notebook gerado), `dqx_studio/regras/rodar_ciclos.py`,
  `dqx_studio/painel/gerar_painel.py`, `dqx_studio/demo/ROTEIRO.md`.
- **Conferência:**
  - **Job:** SUCCESS; portão 36/36; 7.756 eventos em 09/01; 265.252 linhas na fato.
  - **Os 5 casos apareceram:** 77 atrasos zerados na bronze, todos barrados na quarentena; 46 clientes sem nascimento
    na `dim_cliente`; 1 linha sem código na `dim_produto` e 1 na `dim_ponto_venda`.
  - **Studio:** 13 execuções SUCCESS (semana 8 e 8 tabelas inteiras). Cobertura final: 138 das 224 regras com
    exemplo; as 86 em zero são todas garantias da arquitetura (L84).
  - **Painel de qualidade:** 6/6 e 5/5, com 40 execuções (8 semanas); implantado.
- **Docs atualizadas:** framework (P10, P11) · trilha (fase 25) · playbook · `docs/README.md` · roteiro da demo

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
