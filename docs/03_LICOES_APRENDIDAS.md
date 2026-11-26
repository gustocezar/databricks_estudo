# Lições aprendidas · pos_venda

> Documento incremental. Cada lição tem um código (`L##`) que não muda, para ser citada no playbook, no CHANGELOG e em
> revisões. Lição nova entra no fim do tema dela, com o próximo número livre. Última atualização: **24/11/2026**.

Formato: **o que aconteceu → regra que fica**. Entre parênteses, onde a regra está aplicada.

## Plataforma e Free Edition

- **L01** A cota diária de computação acaba e o warehouse recusa consultas até a meia-noite UTC → todo script que usa o
  warehouse detecta a cota e para com mensagem clara; não rode cargas no dia de uma demonstração. (`governanca/sql_util.py`)
- **L02** Só existe um SQL warehouse → bundles oficiais que criam warehouse precisam de patch para usar o existente. (`dqx_studio/README.md`)
- **L03** Até 3 apps e 1 projeto Lakebase → planeje quais apps cabem antes de instalar aceleradores que são apps.
- **L04** O Model Serving do Free Edition não tem Claude; o `qwen35-122b` falhou na saída estruturada grande e o
  `llama-4-maverick` aceita no máximo 8.192 tokens de saída → teste a saída estruturada do modelo antes de rodar uma
  ferramenta de IA longa. (`governanca/genie/avaliacao_boas_praticas/rodar.py`)
- **L05** Sem cluster clássico, ferramentas que exigem Spark local não rodam → prefira modo offline com extrator próprio
  (API + warehouse). (`governanca/genie/avaliacao_boas_praticas/extrair.py`)
- **L06** Agendas ligadas por engano gastam cota → toda agenda nasce `PAUSED` e liga por variável do bundle.
- **L49** Com 1 projeto Lakebase, um segundo app que precisa de Postgres ganha uma **database própria** no projeto que já
  existe (mesmo branch e compute) → isola os dados sem custo extra; o dono da database precisa ser informado
  (`spec.role`). (`governanca/ontologia_readiness/implantar_app.py`)
- **L50** O Python instalado pelo python.org no macOS não traz os certificados raiz (`CERTIFICATE_VERIFY_FAILED` em
  `urllib`) → em scripts locais chame HTTPS pelo `curl`, com o token pela entrada padrão (`-K -`), fora da linha de comando.
- **L58** Com espera síncrona de 50 s, a Statement Execution API estourou o timeout de leitura do SDK (60 s) num cenário
  → espere 20 s, consulte o estado e repita só erros de transporte. (`regras/uc.py`)
- **L70** O projeto morava numa pasta temporária da sessão, e o repositório de destino era público → antes do primeiro
  envio, varra tokens (`dapi`, `gho_`, chaves privadas), e-mails e caminhos locais; mostre ao dono onde cada achado está e
  deixe a decisão explícita; no `.gitignore`, só o que se recria (`.venv`, caches, `.databricks/`, esquemas baixados).
  (`.gitignore`, fase 21)
- **L74** O `databricks bundle deploy` segue o `.gitignore` da raiz do repositório: depois do primeiro `.gitignore`,
  o deploy da carga apagou do workspace 2 arquivos `.pyc` ("2 deleted") → leia a linha de arquivos do deploy e
  confira que só sumiu o que devia; nunca ponha no `.gitignore` algo que o bundle precisa enviar.
- **L81** No Free Edition, 7 das 10 consultas da materialização diária de observabilidade voltam vazias (clusters
  clássicos, spot, policies), e o rightsizing de clusters falha em toda execução → checagem sem objeto para verificar
  não é conformidade: mostre "sem dados", nunca "atende", e tire do Free Edition o que só faz sentido com clusters
  clássicos. (`acoes_observabilidade`; `conferir` reprova regra sem dados)
- **L85** O job liga o app `dqx-studio` e ele aparece como RUNNING, mas ainda reinstala os pacotes por cerca de um
  minuto. Nesse intervalo, todas as 18 submissões do replay voltaram HTTP 502, e o script terminou como se tivesse
  rodado → antes de submeter, espere "Application startup complete" em `databricks apps logs dqx-studio` e confira
  no log do replay que nenhuma linha diz "erro submeter". (`rodar_ciclos.py`)
- **L89** A carga diária levou 14,5 min no backfill de 184 dias (1,3 milhão de eventos, 21,5 milhões de linhas na
  fato) e cerca de 14 min com 1 dia (8 mil eventos). O tempo é quase todo fixo:
  - 2,5 a 3 min de setup da computação serverless na primeira tarefa de notebook, e de novo na `gold_dimensoes`,
    depois do pipeline;
  - cerca de 1,5 min até o update do pipeline começar.

  → Meça setup e execução separados (`setup_duration_seconds`, `execution_duration_seconds`) e o volume de cada
  execução. Antes de chamar de lentidão, confira se o que subiu foi a espera por computação ou o volume.
  (`sustentacao/`: `linha_base`, `volume_execucao`, `desvios.provavel_causa`)
- **L90** Nas tabelas `system.lakeflow.*_timeline`, uma execução que passa da virada da hora vem em mais de uma linha,
  e só a última traz o resultado. No task runner do DQX Studio, 197 linhas eram 174 execuções → junte por `run_id`,
  com o menor início, o maior fim e o resultado e as durações da última fatia (`max_by(..., period_end_time)`). Tire
  da linha de base as tarefas `SKIPPED`, que têm duração 0. (`sustentacao/gerar_sustentacao.py`)
- **L91** Com a agenda pausada, toda execução da carga é manual (`ONETIME`), em qualquer hora: medir nela o SLA das
  06:15 daria "atraso" de 14 horas numa execução das 20:41 → o SLA só vale para a execução da agenda (`CRON`). Para
  saber se a meta cabe antes de ligar a agenda, use a folga projetada: meta − hora da agenda − p95.
  (`sustentacao`: `sla_diario`, `ultima_execucao`)
- **L92** Na primeira conferência, o alerta de sustentação teria disparado 3 vezes por ruído. Os três casos:
  - a silver passou do p95 por 0,1 s;
  - o job inteiro passou por 15 s;
  - o `dq_metricas` passou por 6,6 s, numa execução de 14 dias.

  Com poucas execuções, o p95 fica no máximo, e qualquer segundo a mais vira desvio → o desvio continua com a
  definição (acima do p95 ou de 1,5 vez a mediana) e aparece no painel. O alerta só avisa o que passou do limite por
  60 s ou mais e não é explicado por volume. Teste o alerta com 30 dias de histórico antes de ligar.
  (`MIN_EXCESSO_ALERTA_S` em `sustentacao/gerar_sustentacao.py`)

- **L93** No ensaio do spec (24/11), `SHOW GRANTS ON CATALOG` mostrou só os 3 service principals com acesso e não
  mostrou que o perfil era o **dono** do catálogo e do schema, que pode conceder qualquer privilégio. Pela lista, a
  escolha da trilha do DQX teria saído errada → antes de decidir se dá para conceder privilégio a um app, consulte o
  dono em `system.information_schema` (`catalog_owner`, `schema_owner`) e compare com `current_user()`.
  (`specs/aplicar-base-bruta/modelos/FICHA.md`, etapa 0 do guia 06)

- **L94** Em 26/11, o `registrar` rodou na máquina durante uma queda de rede. Cada `DESCRIBE QUERY` que não chegou ao
  workspace (DNS, renovação do token OAuth) foi gravado como view que "não responde": 33 views quebradas em vez de 22,
  e uma foto falsa no histórico da sonda → falha de transporte não é resultado da sonda. O `registrar` agora aborta
  sem gravar quando alguma chamada falha por rede ou token. A sonda diária roda no job, com `spark.sql`, sem passar
  pelo CLI. (`cmd_registrar` em `conformidade/gerar_conformidade.py`; `conformidade/src/sonda_diaria.py`)

## Custo e FinOps

- **L76** O framework FinOps que já existia (`finops.observability`) quebrou em 19 de 28 visões: a base
  `v_focus_cost_usage` guardou o struct `system.billing.usage.usage_metadata` inteiro, e o struct ganhou campos (de 50
  para 58) → numa visão sobre tabela de sistema, escolha os campos do struct um a um (`usage_metadata.job_id AS job_id`),
  nunca o struct inteiro; o Databricks acrescenta campos sem aviso. (`finops/gerar_finops.py`)
- **L77** Na primeira versão das visões FinOps, 80% do custo ficou sem dono. A causa eram 2.122 consultas de cinco jobs
  que não existem mais em `system.lakeflow.jobs` e não têm nome no billing → atribua em camadas: tag, nome da origem
  (job, espaço Genie, painel) e, quando a origem não tem nome, o texto da consulta (catálogo citado). Confira sempre quanto
  sobrou sem dono antes de mostrar o custo por time. (`custo_sql_por_consulta`) *Correção de 23/11/2026: os cinco
  "jobs" eram os jobs ocultos dos 5 alertas SQL do bundle de observabilidade (L79).*
- **L78** As 249 perguntas de novembro aos espaços Genie do pós-venda vieram todas pela API (as avaliações
  automáticas); o uso por pessoas foi zero → meça a adoção pelo canal UI e pelo painel publicado; contar todos os
  eventos mede os testes, não as pessoas. (`uso_genie_diario`, `uso_paineis_diario`)
- **L79** Os 5 alertas SQL do bundle de observabilidade (API `alerts-v2`) rodam como jobs ocultos: não aparecem em
  `databricks jobs list`, `jobs get` responde "does not exist" e a API antiga (`databricks alerts list`) volta vazia.
  Eram eles as consultas "sem dono" da L77: US$ 816,20 desde julho. Só o alerta de hora em hora custou US$ 29,73 em 7
  dias, porque cada disparo acorda o warehouse, que fica ligado até o auto-stop → procure alertas com
  `databricks alerts-v2 list-alerts`; ligue consulta a alerta por `system.query.history.query_source.alert_id`; limite
  a agenda a poucos disparos por dia. (`conformidade/gerar_conformidade.py alertas`, regra PLT06)

## Dados e pipeline

- **L07** Defeitos injetados de propósito tornam a demonstração de qualidade convincente → planeje os incidentes por semana
  (linha de base, avisos, erros barrados, erro que vaza, recuperação).
- **L08** Regra fora da barreira vaza e reaparece como chave órfã na fato → toda condição que torna o dado inutilizável é regra de erro na silver.
- **L09** Chave substituta sequencial quebraria a fato histórica → use `xxhash64(chave de negócio)`.
- **L10** Saldo de carteira é semiaditivo (uma linha por dia) → nunca some dias; use fechamento, média diária ou uma data.
- **L11** A simulação não baixa pendências por perda, então a carteira só cresce → diga isso na demonstração; não confunda com tendência real.
- **L82** A guarda de idempotência do gerador de eventos usava `data_evento NOT IN (SELECT DISTINCT data_extracao FROM
  bronze)`. Bastaria uma linha com `data_extracao` nula na bronze para o `NOT IN` virar NULL e nenhuma carga futura
  inserir nada, sem erro → em `NOT IN` com subconsulta, filtre os nulos (`WHERE data_extracao IS NOT NULL`) ou use
  `NOT EXISTS`. (`carga_diaria/gerar_carga.py`)

## Qualidade e DQX Studio

- **L12** O dry run com amostra lê as primeiras N linhas, não uma amostra aleatória → avalie janelas com todas as linhas.
- **L13** Uma view de janela por camada, apontada por tabela de controle, dá um destino estável e um histórico semana a
  semana no Studio. (`carga_diaria/janela_avaliacao.py`)
- **L14** Regra mapeada na tabela errada gera falso positivo (pk única em view de eventos) → mapeie regras pelo grão real e
  marque as execuções afetadas.
- **L15** Regras de tabela única (API antiga) não aparecem no menu do Studio → use o Registro de Regras e tabelas monitoradas.
- **L16** `skip_duplicates` funde modelos de severidades diferentes, e regras antigas na mesma tabela travam o Registro →
  crie sem deduplicação e remova as antigas com backup. (`dqx_studio/regras/registro_studio.py`)
- **L17** A nota da tabela só aparece após `refresh-scores` → chame o recálculo no fim de toda execução pela API.
- **L18** Token expira no meio de processos longos → o cliente da API renova em 401 e repete. (`dqx_studio/regras/carregar_regras.py`)
- **L19** O Lakebase do Studio desliga com a cota → `spec.disabled=false` no endpoint e reinício do app.
- **L20** Execuções extras (Registro) apareceram como "semana 6" no painel → identifique a origem das execuções
  (`registry_rule_id`) e mantenha checagens de consistência no script de teste do painel.
- **L43** O agendador do DQX Studio roda dentro do app; no Free Edition o app para sozinho após 24 h e o agendamento não
  dispara → o job diário termina ligando o app (`40_ligar_dqx_studio`). Teste o agendamento com um disparo real
  (cron para daqui a 3 minutos), não só a configuração.
- **L44** Agendar uma tabela monitorada já concede SELECT aos service principals do agendador (que leem sem o token do
  usuário); confira antes com `schedule-grants/preflight`. Execuções agendadas aparecem com `run_type = 'scheduled'`
  e `requesting_user = 'scheduler'`.
- **L83** As dimensões pegam o evento mais recente de cada entidade. Um defeito injetado num produto, ponto de venda ou
  corretor que já existe estragaria a dimensão inteira dessa entidade, e com ela os painéis → nos incidentes de
  demonstração, o defeito de entidade compartilhada vai num código novo (`VIDA_QA_*`, `PV_QA_*`, `COR_QA_*`); só
  clientes e apólices, que são individuais, recebem o defeito no próprio cadastro. (`gerar_carga.py`, I31 a I33)
- **L84** Cerca de 40 regras do DQX Studio ficam em zero mesmo com os incidentes, porque são garantias da arquitetura:
  a barreira tira os erros antes da silver e a fato recalcula faixa, multa, juros, total e tentativas pelas funções de
  regra. Exemplos: chave única, chave substituta não nula, `dim_data` e a faixa "Vence hoje" → zero nessas regras é
  prova de que a barreira e o recálculo funcionam, não falta de dado. Os exemplos delas ficam na quarentena e na
  bronze. (`dqx_studio/demo/ROTEIRO.md`)
- **L88** No DQX 0.17.2, a checagem `is_in_list` com valores de texto em `allowed` (`MENSAL`, `TRIMESTRAL`…) falhou com
  `UNRESOLVED_COLUMN`: a biblioteca leu cada valor como nome de coluna, e o job do DQX como código parou na primeira
  execução → domínio fechado de texto vai em `sql_expression` com `IN`, com o `coalesce` que define o nulo; e rode o
  modelo numa janela conhecida antes de ligá-lo na carga. (`dqx_codigo/checks_pendencias.yml`)

- **L95** No ensaio de vigência (26/11), o DQX 0.17.2 aceitou duas checagens com o **mesmo nome** e `filter`
  complementares pela data do dado, e o resultado de cada linha trouxe o `user_metadata` da versão que a julgou. A
  versão 1 reprovou 105 eventos e a versão 2, 68; as 15 checagens bateram com a mesma conta em SQL → para versionar
  uma regra no tempo, não troque o nome (ele é o motivo estável, P09): use `filter` pela data do dado e a versão no
  `user_metadata`. Antes de confiar, rode o modo `ensaio`, que não grava nada, e compare com SQL.
  (`regras/catalogo/gerar_catalogo.py ensaio`, `dqx_codigo/aplicar_dqx.py`)

## Governança e metadados

- **L21** `CREATE OR REPLACE TABLE ... AS SELECT` mantém descrições e tags; `CREATE OR REPLACE VIEW` apaga tags, tags de
  coluna e Wiki (descrições de `SELECT *` sobrevivem por herança) → views recriadas por job passam por
  `garantir_view`, que só recria se a definição mudou e devolve a governança. (`carga_diaria/views_preservadas.py`)
- **L22** Tags de coluna de view não podem ser gravadas por SQL → use a API de entity tag assignments.
- **L23** Views com colunas calculadas não herdam descrição → descreva por código depois de criar. (`dqx_studio/painel/descricoes_painel.py`)
- **L24** Tags com acento funcionam, mas SQL exige o nome exato e a API pede `%2F` para a barra do subdomínio.
- **L25** Pages atômicas com seção "Como validar" geram as perguntas de avaliação da Genie.
- **L26** Camada de negócio deve cumprir o que promete (sem identificadores pessoais) → audite PII também nas views de
  ontologia. (aplicado em 21/11: `cliente_id` fora de `pendencia` e `pagamento`)
- **L45** Governed tag criada sem lista de valores recusa qualquer valor ("Allowed values: []") → defina os valores
  permitidos na política da tag antes de aplicar (`garantir_valores_tag` em `aplicar_semantica.py`).
- **L42** Views criadas com lista de colunas e `COMMENT` perdem essas descrições se recriadas só com `AS consulta` →
  recrie com o DDL completo: `garantir_view(..., ddl=...)`. (`carga_diaria/views_preservadas.py`)
- **L47** Valor recém-incluído na lista de uma governed tag leva alguns segundos para valer: a primeira gravação falhou com
  "not an allowed value" → depois de mudar os valores da política, espere e repita (`aplicar_tag` tenta 4 vezes).
- **L53** A auditoria lia ~3.500 tags uma a uma pela API, levava 15 min e, quando a API recusava por limite, contava a
  coluna como "sem tag" (147 falsos "dado pessoal sem tag") → leia em lote pelo `information_schema` e trate falha de
  leitura como "não lida", nunca como ausência. (`auditar_metadados.py`)
- **L54** `COMMENT ON COLUMN` funciona em materialized view de pipeline, mas comandos simultâneos no mesmo objeto falham
  com `CONCURRENT_UPDATE` → paralelize entre colunas com nova tentativa para esse erro (`aplicar_descricoes.py`).
- **L55** Marcar dado pessoal só nas camadas "oficiais" deixou CPF, RG e endereço sem tag em 6 schemas antigos que
  continuavam consultáveis → a marcação segue o dado, não a camada: todo schema no catálogo entra no plano de tags de dado
  pessoal (`tags_dado_pessoal` em `aplicar_semantica.py`). A nota de prontidão não muda com isso.
- **L80** As tabelas internas que o Lakeflow cria (`__materialization_*` e `event_log_*`) aparecem no `information_schema`
  como tabelas `MANAGED`, sem descrição nem tags. Na primeira rodada da conformidade, elas renderam 382 colunas "sem
  descrição" e 126 colunas "de dado pessoal sem tag". Todos eram falsos positivos → separe as tabelas internas (papel
  `interno`) antes de contar, porque são do pipeline, não do domínio. Pelo mesmo motivo, confira se a regra por nome
  de coluna não pega nome de métrica ("CPF inválido"). (`conformidade/gerar_conformidade.py`, `INTERNO` e `NAO_PII`)

- **L96** Em 26/11, a regra de frescor (USO01) passou a acusar as 3 tabelas de catálogo da ontologia (`entidades`,
  `glossario`, `relacoes`), que estavam com `atualizacao=diaria` mas só mudam quando a ontologia muda. Em 24/11 a regra
  passava só porque elas tinham sido reescritas 2 dias antes, e concluímos cedo demais que não havia o que corrigir →
  declare `sob_demanda` em toda tabela que não é escrita pela carga, e confira o frescor de novo depois de 2 dias, não
  no mesmo dia da mudança. Vale também para a otimização (OTM01): o Predictive Optimization não age em tabela sem
  escrita, e as 2 tabelas novas do catálogo de regras derrubaram a regra para 87,2%. Desde 26/11, a OTM01 não conta as
  tabelas `sob_demanda`. (`ATUALIZACAO_TABELA` em `governanca/ontologia.py`; OTM01 em `conformidade/gerar_conformidade.py`)

## Camada semântica (metric views)

- **L27** O semiaditivo `last` usa o último dia **de cada fatia**: fatias que somem antes do fim do período ficam com o último
  saldo → valide a soma das fatias contra o total no grão do consumo (produto × canal bateu; com forma de pagamento sobrou R$ 240,33).
- **L28** O `offset` do mês anterior só enxerga fora do filtro quando o filtro é na dimensão de mês da janela.
- **L29** Acumulado ordenado por dia respeita o filtro de mês; ordenado por mês, não → YTD por mês resiste ao filtro.
- **L30** Ranking (`RANK() OVER`) não pode ir na mesma consulta que medidas de janela (`SCALAR_SUBQUERY_TOO_MANY_ROWS`).
- **L31** Recriar metric view apaga tags e Wiki → rode `aplicar_semantica.py` e republique as Wikis depois.
- **L32** Campo sem descrição confunde a IA ("CPF inválido" lido como dado pessoal) → descreva todo campo de metric view. (`DESCR` em `gerar_ontologia_sql.py`)
- **L72** A visão por trás da metric view da carteira junta 9 dimensões, e sem `RELY` o plano lê todas, mesmo numa
  pergunta só sobre o saldo por dia → declare `RELY` nas chaves primárias depois de provar unicidade e ausência de nulos
  (o Databricks não valida); deixe as estrangeiras sem `RELY` quando houver órfãs. Não existe `ALTER CONSTRAINT`: remova a
  PK e declare de novo; o `CASCADE` apaga as FKs que apontam para ela, então recrie-as no mesmo script. Resultado: 9 → 0
  junções, resultado idêntico. (`governanca/aplicar_rely.py`)

## Genie

- **L33** Instruções curtas e específicas (desambiguação, período, semiaditivo, privacidade) com menos de 2.000 caracteres funcionam melhor.
- **L34** Valide todo SQL de exemplo e de avaliação no warehouse antes de publicar o espaço.
- **L35** Compare o resultado inteiro, não só o primeiro número, para não ter falso negativo.
- **L36** Ao mudar a semântica, atualize os gabaritos: a avaliação oficial reprovou respostas certas com gabarito antigo.
- **L37** Mudar o tipo de uma dimensão (`timestamp` → `date`) mudou o comportamento da Genie (filtro pela semana truncada) →
  rode a avaliação completa após qualquer mudança de tipo e corrija com descrição do campo e exemplo de SQL.
- **L38** Mês incompleto distorce variação de fluxo → compare só meses completos (o painel usa `ultimo_mes_completo`).
- **L73** A régua de 12 itens do Genie Workbench (genie-agent-scanner) só conta as descrições de coluna gravadas no
  próprio espaço e ignora as do Unity Catalog, que a Genie usa; os itens 11 e 12 exigem uma rodada de otimização do
  Workbench → sem o app o teto é 10/12; trate o item 3 como falso positivo quando o catálogo está descrito, e não
  duplique descrições só para a régua. (`governanca/genie/scanner/TRIAGEM.md`)
- **L87** Na reconferência de 24/11, com os dados até 09/01/2027, a Genie acertou 28 de 29. A que errou foi "saldo em
  cobrança externa por produto hoje": a Genie filtrou `Produto IS NOT NULL` e deixou de fora R$ 779,34 de linhas da
  fato com produto órfão (vazamento da semana 7). O gabarito, sem o filtro, mostra esse saldo numa linha sem produto →
  dê às chaves órfãs um membro explícito na ontologia (por exemplo, "Produto não identificado"), para que nenhum
  filtro de nulo esconda dinheiro, e reavalie a Genie depois de toda carga que traga chave órfã. Corrigido em 24/11:
  produto, categoria, canal, regional e UF ganharam o membro "não identificado" nas metric views (a gold não mudou, e o
  DQX Studio continua vendo as órfãs); a Genie voltou a 29/29.
  (`governanca/gerar_ontologia_sql.py`, `governanca/genie.py avaliar`, `governanca/genie/avaliacao.json`)

## Regras de negócio (BDD)

- **L56** A mesma conta (faixa, multa, juros, total) estava escrita como texto SQL na origem, na gold e na barreira → uma
  função do Unity Catalog por regra, com cenários em português; troque o pipeline só depois de 100% de paridade linha a
  linha (29,9 mi de linhas, 0 divergência). (`regras/`)
- **L57** Cenário escrito pelo negócio revela regra implícita: multa já no dia do vencimento, faixa e juros para dias
  negativos, CPF repetido aceito → registre a decisão na descrição da função e meça o impacto nos dados antes de mudar
  (0 linha afetada no pos_venda).

- **L59** Trocar a regra da barreira pela função no mesmo lugar faria 319 eventos do I14 (dias adulterados) virarem
  "total inconsistente": a causa sumiria do painel → acrescente a regra nova depois das que apontam a causa e meça a
  reclassificação na quarentena antes (`valores_fora_da_regra`, 0 evento hoje).
- **L60** Validar mudança de pipeline sem alterar a demonstração: `jobs run-now` com `only` (portão, silver sem dado
  novo, gold de um intervalo) e cópia antes/depois comparada com `EXCEPT ALL` nos dois sentidos (1,74 mi de linhas, 0
  diferença). Gerar um dia novo mudaria os saldos que a Genie e os painéis conferem.
- **L61** Funções do Unity Catalog entram na Genie em `instructions.sql_functions` (`id` + `identifier`), campo ausente da
  referência local → teste no próprio espaço (a API recusa campo desconhecido sem alterar nada); com a descrição da
  função e um exemplo, a Genie chamou a função nas simulações (29/29).

- **L62** A regra "total = soma das partes" não pegava o I03: a parcela vinha zerada ou negativa, mas multa e juros da
  parcela original, e a soma fechava → compare os valores com a **regra de cálculo** (funções), não só entre si; no Studio
  a regra nova acusou 60 eventos que só eram barrados por outra causa.
- **L63** Regra do DQX Studio que chama função do Unity Catalog precisa de `USE SCHEMA` + `EXECUTE` para o service
  principal do app e para o executor dos agendamentos; o preflight de agendamento só confere SELECT em tabelas → conceda
  e prove com execução manual **e** disparo agendado real. Para não republicar as 12 tabelas, `registro_studio.py aplicar`
  aceita só as tabelas afetadas e mescla o arquivo de ids.
- **L64** Um dia novo sem incidente (25/12: 8.559 eventos, 0 barrados) prova que as funções no caminho não reprovam evento
  bom e que a silver marca o CPF pela função (139 = 139), mas **não** prova a captura: nenhuma janela de incidente cobria o
  dia → a captura vem dos cenários e do Studio na janela com incidente (44 do I03); para provar no pipeline, injete o
  incidente num dia novo.
- **L65** Carregar um dia novo envelhece o que cita data fixa: instrução da Genie ("foto mais recente: 24/12"), roteiro,
  teste que contava 35 dias e a semana do painel de qualidade (abriu a "Semana 6") → escreva "foto mais recente", faça a
  checagem relativa à data (`count = dias desde o início`) e procure `24/12` no projeto depois de cada carga.

## Painéis

- **L39** Gerar o JSON do painel por código e conferir versões, grade de 12 colunas e campos × encodings evita painel quebrado.
- **L40** Teste cada dataset como o AI/BI executa (catálogo e schema do bundle, nomes simples nas consultas).
- **L66** Painel por público com **uma página por fato** (carteira, recuperação, safras, qualidade) responde "cada fato para
  cada público" sem multiplicar painéis e sem trocar o link; a diretoria abre numa visão executiva que resume os quatro.
- **L67** Segunda ferramenta de BI sem duplicar regra: visões `bi` agregadas **a partir das metric views** (942 mil linhas em
  vez de 29,9 milhões) e medidas DAX só para o que é do motor (saldo semiaditivo pelo último dia do contexto, mês anterior,
  acumulado no ano) → prove com paridade: a lógica das medidas calculada em SQL deu 21/21 iguais ao painel do Databricks.
- **L68** Projeto do Power BI gerado por código sem Power BI na máquina: valide os JSON contra os esquemas oficiais da
  Microsoft (versões de meados de 2025, que qualquer Desktop recente abre) e faça um teste negativo para provar que a
  validação pega erro; o que só o Desktop prova (TMDL e DAX executando) fica declarado como não verificado.
- **L86** Na reconferência de 24/11, com a foto de 09/01/2027, o cartão "Crescimento da carteira no mês" deu
  R$ 1.403.002,55 no painel e R$ 1.405.736,27 na lógica do Power BI (20 de 21 iguais). O painel agrupa por produto e
  canal e soma o "Saldo no início do período" de cada grupo. Em janeiro, 17 grupos só apareceram depois do dia 1º
  (vazamentos da semana 7), e cada um entrou com o saldo do seu primeiro dia. O total certo é o do Power BI: saldo da
  foto menos o saldo do primeiro dia do mês → medida semiaditiva de início ou fechamento se calcula no total, nunca
  somando os grupos; e reconfira painel e BI depois de toda carga que traga grupos novos.
  Corrigido em 24/11: o conjunto de dados lê início, fechamento e mês anterior de cada grupo nas datas da carteira
  inteira, com zero para o grupo que não existia, e a paridade voltou a 21/21.
  (`paineis_financeiros/gerar_paineis.py` `ds_carteira_mes`, `powerbi/gerar_powerbi.py referencia`)

- **L97** Em 26/11, ao juntar as cores numa fonte única, rodamos o validador de paleta da skill `dataviz`. A paleta
  dos painéis e do Power BI, escolhida no olho em 20/11, reprovou: o roxo `#7A5195` e o azul `#2F6B9A` vizinhos
  tinham ΔE 1,2 para daltônicos (mínimo 8), e havia cor fora da faixa de luminosidade. A da sustentação também
  reprovou. Eram 5 paletas em 6 lugares, cada uma com o seu "vermelho de erro" → cor de série se valida com script
  (`validate_palette.js`, no fundo claro e no escuro) antes de usar, e fica num lugar só (`docs/marca/marca.json`).
  Cor de estado (bom, alerta, crítico) é separada das séries e sempre vai com rótulo. (`docs/marca/`)

## Avaliação por IA

- **L46** Ferramentas de avaliação contam pilar sem dados como zero, e um app só enxerga o que o service principal dele
  pode ler → ligue a autorização do usuário (escopo `sql`) e compartilhe os objetos (ex.: espaços Genie) antes de ler a
  nota; no pos_venda ela foi de 61,1 para 81,3 sem mudar nada no projeto.

- **L48** Ferramentas de prontidão leem domínio e responsável só por chaves padrão (`domain`, `subject_area`,
  `data_owner`) e cobram certificação dos objetos mais acessados → use as chaves padrão ao lado das tags próprias, mas não
  certifique bronze bruto nem views técnicas de qualidade só para subir a nota; registre como lacuna aceita.
  (pos_venda: 81,3 → 90,5)
- **L51** Para o histórico de uma ferramenta de avaliação ser comparável, fixe a versão: o `main` do
  genie-ontology-readiness resolvia o Lakebase Autoscaling, mas mudava o cálculo da nota → ficamos na v1.5.0 com as
  variáveis no `app.yaml`. Confira também qual rota grava: só `POST /api/assess/runs` salva no histórico.
- **L52** Ferramentas de prontidão contam as tabelas internas dos pipelines (`__materialization_mat_*`, `event_log_*`)
  na cobertura de descrições → descreva o que é publicado e registre o resto como lacuna aceita; não edite objetos que o
  pipeline administra. (pos_venda: 382 colunas, metadados parou em 93,5)

- **L41** Relatórios gerados por IA trazem achados genéricos e falsos positivos → triagem com veredito por achado, conferido nos metadados.
- **L69** O catálogo de aceleradores envelhece pelo lado do projeto, não pelo da organização: em dois dias a
  databricks-solutions não ganhou repositório, mas a opção Power BI levou `powerbi-analyzer` de baixa para alta → reveja o
  catálogo a cada fase nova do projeto e guarde a situação de cada um (aplicado, proposto, adiado, com o motivo).
  (`referencias/databricks_solutions/REVISAO_2026-11-22.md`)
- **L71** Auditoria que não tem o dado de entrada aprova em branco: o `pba` aprovou as 10 regras de preparo de dados
  com "No Power BI history" e as regras de desenho que dependem de visuais (RD-001, RD-010) sem ler um visual (o
  leitor de PBIP não extrai visuais) → leia o resumo
  de cada aprovação; "sem histórico" ou "nada encontrado" é "não avaliado", e vai para a triagem como lacuna.
  (`paineis_financeiros/powerbi/auditoria/README.md`)
- **L75** A revisão de 22/11 pôs quatro repositórios em "não agora" só no texto, e o guia de opções gerado do
  catálogo os recomendou como candidatos → toda decisão sobre um acelerador vai para o dado de onde as ferramentas
  leem (`s` e `sn` em `catalogo.py`), não só para o documento da revisão. (`referencias/databricks_solutions/gerar_opcoes.py`)
