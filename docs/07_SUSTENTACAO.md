# Manual de sustentação · pos_venda

> Documento incremental. Última atualização: **24/11/2026**. É o manual de quem mantém o domínio funcionando no dia a
> dia: o que roda, as metas, onde olhar, a rotina, o que fazer quando algo falha e como mudar sem quebrar.
> A prática é a [P40](04_FRAMEWORK.md#p40--tempo-de-execução-com-linha-de-base-desvio-sla-e-volume-a-partir-das-tabelas-de-sistema),
> o módulo é o [M13](02_PLAYBOOK.md#m13--sustentação-tempo-de-execução-linha-de-base-e-sla) e os números vêm de
> `pos_venda.sustentacao` ([README](../sustentacao/README.md)).

**Agendas ligadas em 24/11/2026** (carga 05:00, Studio 06:30, alerta 06:20). **Provisório:** até a linha de base
acumular execuções da agenda, ela vem de 13 execuções manuais da carga, de 19 a
23/11, com intervalos de 1 a 184 dias. Toda meta marcada com **(provisório)** vale como ponto de partida. Revise
depois de 20 execuções da agenda.

---

## 1 · Catálogo do que roda

**Cadeia diária** (horário de Brasília; agendas ligadas desde 24/11, a sonda desde 26/11):

```
05:00 pos_venda_carga_diaria ─► portao_regras ─► gerar_eventos ─► silver_lakeflow (pipeline) ─► gold_dimensoes
                                ─► gold_fato_snapshot ─► dq_metricas ─► ligar_dqx_studio
06:15 meta: carga terminada (SLA)
06:20 alerta de sustentação (SLA estourado ou desvio)
06:30 DQX Studio avalia 12 tabelas (agendamentos do Studio)
06:45 sonda da conformidade (views do workspace e histórico do dia)
depois painéis AI/BI, Genie e Power BI leem a gold, a ontologia, as metric views e o schema bi
```

| O que | Tipo | Agenda | Dono | Depende de | Se falhar |
|---|---|---|---|---|---|
| `pos_venda_carga_diaria` | job (7 tarefas) | 05:00, **ligada** desde 24/11 | squad pós-venda | funções `pos_venda.regras`, landing e cadastro em `fonte` | sem foto do dia: painéis, Genie e Studio mostram o dia anterior |
| `pos_venda_carga_silver_lakeflow` | pipeline Lakeflow (serverless) | pela tarefa `silver_lakeflow` | squad pós-venda | bronze | silver parada; dimensões e fato não andam |
| `dqx-studio` | app (Lakebase `dqx-studio-db`) | ligado pela tarefa `ligar_dqx_studio`; para sozinho após 24 h | squad pós-venda | Lakebase ligado, warehouse | sem avaliação de qualidade do dia |
| agendamentos do DQX Studio | 12 tabelas no Studio | 06:30, **ligados** desde 24/11 | squad pós-venda | app ligado, foto do dia | sem histórico de qualidade do dia |
| `dqx-studio-task-runner` | job gerido pelo app | sob demanda (cada execução do Studio) | app `dqx-studio` | warehouse | execução do Studio falha |
| `pos_venda_dqx_codigo` | job (trilha A, P38) | sob demanda; timeout de 1 h | squad pós-venda | bronze, YAML das checagens | sem métricas por regra da trilha A |
| `pos_venda_carga_setup` | job | uma vez (cria schemas e cadastro) | squad pós-venda | — | só na reconstrução |
| `pos_venda_medalhao_sql`, `pos_venda_medalhao_lakeflow_job` | jobs legados | sob demanda | squad pós-venda | one-table | nada no fluxo diário (schemas `*_sql`, `*_ldp`) |
| `genie-ontology-readiness` | app | sob demanda | squad pós-venda | espaços Genie, Lakebase | sem nota de prontidão |
| "pos_venda · Qualidade de dados" | painel AI/BI | lê na abertura | squad pós-venda | `pos_venda.dq`, Studio | painel desatualizado |
| "pos_venda · KPIs financeiros" (Diretoria e Analista) | painéis AI/BI | lê na abertura | squad pós-venda | metric views | números do dia anterior |
| "pos_venda · Sustentação" | painel AI/BI | lê na abertura | squad pós-venda | `pos_venda.sustentacao` | sem visão de tempo e SLA |
| Pós-venda · Analista financeiro e Diretor financeiro | espaços Genie | sob demanda | squad pós-venda | metric views e ontologia | respostas com o dia anterior |
| "pos_venda · Sustentação: SLA ou desvio da carga" | alerta SQL | 06:20, 1 vez por dia, **ligado** desde 24/11 | squad pós-venda | `alerta_sustentacao` | ninguém é avisado do atraso |
| `pos_venda_conformidade_sonda` | job (notebook serverless) | 06:45, **ligada** desde 26/11; timeout de 20 min | squad pós-venda | visões de `pos_venda.conformidade` (criadas pelo `aplicar` local) | sem histórico do dia; USO03 fica com a sonda anterior |
| 5 alertas `[Observabilidade]` | alertas SQL (jobs ocultos, L79) | de hora em hora a 1 vez por dia | dono do bundle `observabilidade-framework` | tabelas de sistema | só leitura para o pós-venda |

O inventário vivo dos jobs do projeto é `pos_venda.sustentacao.jobs_monitorados`. A lista completa de objetos fica no
[inventário](INVENTARIO.md).

## 2 · SLAs e metas

| Meta | Valor | Como medir | Situação |
|---|---|---|---|
| Carga terminada | até **06:15** (antes do Studio às 06:30) | `sustentacao.sla_diario` (só a execução da agenda conta, L91) | no prazo em 25 e 26/11: a agenda terminou às 05:15 e às 05:17 |
| Duração da carga | mediana de 14,53 min; p95 de 16,05 min **(provisório)** | `sustentacao.linha_base` (tipo job) | 12 execuções com sucesso |
| Duração por tarefa | ver a tabela abaixo **(provisório)** | `sustentacao.linha_base` (tipo tarefa) | desvio = acima do p95 ou de 1,5 vez a mediana |
| Frescor | tabela com `atualizacao=diaria` escrita nos últimos 2 dias | regra USO01 em `conformidade.boas_praticas_dados` | atende desde que a agenda foi ligada: USO01 sem pendência em 26/11 |
| Disponibilidade do Studio | app `RUNNING` e "Application startup complete" antes das 06:30 | `databricks apps get dqx-studio`; tarefa `ligar_dqx_studio` | o app para após 24 h no Free Edition |
| Timeout do job | 2 vezes o p95 (33 min) **(provisório)** | `sustentacao.ultima_execucao.timeout_sugerido_min`; regra PLT03 | 33 min no job desde 24/11 |

| Tarefa | Mediana (min) | p95 (min) | Setup normal |
|---|---|---|---|
| `portao_regras` | 3,59 | 3,73 | cerca de 3 min (primeira tarefa) |
| `gerar_eventos` | 3,05 | 4,37 | poucos segundos depois do portão |
| `silver_lakeflow` | 6,81 | 7,39 | cerca de 1,5 min até o update |
| `gold_dimensoes` | 3,65 | 4,17 | cerca de 2,5 min (depois do pipeline) |
| `gold_fato_snapshot` | 0,40 | 2,09 | segundos |
| `dq_metricas` | 0,39 | 0,65 | segundos |
| `ligar_dqx_studio` | 0,11 | 2,11 | 2,3 min quando o app estava parado |

Valores medidos em `system.lakeflow.job_task_run_timeline` em 24/11/2026, todos **(provisório)**. A duração não
acompanha o volume: 184 dias levaram 14,5 min, e 1 dia, cerca de 14 (L89).

## 3 · Onde olhar

| Pergunta | Onde | Quem recebe aviso |
|---|---|---|
| A carga rodou? Quanto demorou? Algo passou do normal? | painel "pos_venda · Sustentação"; `sustentacao.execucoes_tarefa`, `desvios`, `sla_diario`, `ultima_execucao` | alerta de sustentação: quem implantou o bundle (`workspace.current_user`), quando ligado |
| Por que demorou? | `sustentacao.volume_execucao`, `atualizacoes_pipeline` (espera e update), `execucoes_tarefa` (setup × execução) | — |
| O que fazer nesta tarefa? | `sustentacao.matriz_tarefas` e a [matriz de resiliência](02_PLAYBOOK.md#matriz-de-resiliência) | — |
| Quanto custou? Quantas falhas? | `finops.uso_jobs_diario` (execuções, falhas, custo e custo das falhas) | — |
| O dado está em dia e governado? | `conformidade.pendencias` (USO01, TAG, DOC, LGPD, PLT) | — |
| A qualidade do dia está boa? | painel "pos_venda · Qualidade de dados"; `gold.dq_qualidade_diaria`, `gold.dq_barrados_por_motivo_dia`, `gold.dq_fato_orfas_diarias`; DQX Studio | — |
| Jobs com falha no workspace, custo alto, recursos sem tag | os 5 alertas `[Observabilidade]` | o dono do bundle `observabilidade-framework` |

## 4 · Rotina

**Diária (5 min, depois das 06:30):**
1. Abrir a página Sustentação. `Ocorrências para o alerta` deve estar em 0 e o SLA do dia em "no prazo".
2. Na linha da carga em "Última execução", conferir que o resultado é `SUCCEEDED` e que a duração está perto da
   mediana.
3. No painel de qualidade, conferir que a foto do dia apareceu e que os barrados por motivo estão no padrão.
4. Conferir que o DQX Studio avaliou as 12 tabelas, ou que o app está `RUNNING`.
5. Se algo estiver fora, ir ao runbook da seção 5 e registrar no CHANGELOG.

**Semanal:**
- Rodar `python3 conformidade/gerar_conformidade.py registrar` e `conferir`, e ler `pendencias`.
- Rodar `python3 sustentacao/gerar_sustentacao.py conferir`. Revisar `desvios` e a linha de base: com 20 execuções da
  agenda, tirar o **(provisório)** das metas.
- Abrir `finops.uso_jobs_diario`: falhas e custo das falhas na semana.
- Conferir os disparos dos alertas (PLT06) e o custo da origem "Alerta SQL" em `finops.uso_consultas_diario`.

**Mensal:**
- Reconferir a Genie: `python3 governanca/genie.py avaliar` (meta 29/29; gasta cota).
- Reconferir o Power BI: `gerar_powerbi.py referencia` (meta 21/21) e a paridade dos painéis.
- Rodar a auditoria de metadados (`governanca/auditar_metadados.py`): 100% descrito e 0 dado pessoal sem tag.
- Rever o custo do mês (`finops.squad_custo_mensal`) e o crescimento da fato (seção 9).
- Rever esta seção e a matriz por tarefa. Toda lição nova vira linha de runbook.

## 5 · Runbooks

Formato de cada runbook: **sintoma → onde ver → diagnóstico → ação → como confirmar**.

### 5.1 Portão BDD falhou
- **Sintoma:** a tarefa `portao_regras` termina `FAILED`, e as outras não rodam (sem foto do dia).
- **Onde ver:** `sustentacao.execucoes_tarefa` (resultado e `codigo_termino`); log da tarefa no job.
- **Diagnóstico:** qual cenário falhou. Mudou a função em `pos_venda.regras`? O cenário ficou velho porque a regra de
  negócio mudou? Ou foi o timeout da Statement Execution API (L58)?
- **Ação:** corrigir a função (`regras/funcoes.py`) ou o cenário (`regras/features/`). Depois, rodar os cenários e a
  paridade localmente ([regras/README.md](../regras/README.md)) e rodar o job de novo.
- **Como confirmar:** o portão volta a `SUCCEEDED` com 36/36 cenários, e a carga do dia termina.

### 5.2 Cota esgotada (L01)
- **Sintoma:** "free daily limit" ou "The request could not be processed by the warehouse"; o warehouse fica
  `STOPPED`, e os scripts param com `CotaEsgotada`.
- **Onde ver:** `databricks warehouses get 5f010b8396e591fb`; o consumo do dia em `finops.uso_consultas_diario`.
- **Diagnóstico:** o que gastou a cota. Os suspeitos são o alerta horário do bundle de observabilidade (L79), as
  avaliações da Genie e as cargas grandes.
- **Ação:** esperar a renovação à meia-noite UTC (21:00 em Brasília). Não forçar e não rodar cargas no dia de uma
  demonstração. Aconteceu em 24/11, depois do `testar` da sustentação.
- **Como confirmar:** `SELECT 1` responde pela Statement Execution API.

### 5.3 Carga não rodou (frescor)
- **Sintoma:** USO01 cai, `sla_diario` mostra "sem execução da agenda" ou "falhou", e os painéis mostram a foto do dia
  anterior.
- **Onde ver:** `sustentacao.sla_diario`, `ultima_execucao`; `conformidade.pendencias` (USO01).
- **Diagnóstico:** a agenda está pausada? O job falhou (veja 5.1 e 5.4)? A cota acabou (5.2)?
- **Ação:** rodar o dia que faltou:
  `databricks bundle run carga_diaria -t dev --profile dbx-workshop --params data_inicio=AAAA-MM-DD,data_fim=AAAA-MM-DD`
  (seção 6).
- **Como confirmar:** a execução fica `SUCCEEDED` em `execucoes_job`, `volume_execucao` mostra eventos gravados e USO01
  volta a atender.

### 5.4 Execução lenta (acima do p95)
- **Sintoma:** uma linha em `sustentacao.desvios`, ou o alerta de sustentação dispara. O alerta só avisa o desvio de
  60 s ou mais acima do limite que o volume não explica (L92).
- **Onde ver:** `desvios.provavel_causa`; `execucoes_tarefa` (`setup_s` × `execucao_s`); `atualizacoes_pipeline`
  (`espera_s`); `volume_execucao`.
- **Diagnóstico:** separe volume de lentidão (L89).
  - **Espera por computação:** o setup subiu e a execução não. É a fila do serverless, não o código.
  - **Volume maior:** o intervalo tem mais dias que a base, como num backfill.
  - **Lentidão com o mesmo volume:** a execução subiu com o mesmo volume. Ler o log da tarefa ou o event log do update.
- **Ação:**
  - espera por computação: nada a corrigir; acompanhar se repete;
  - volume maior: esperado, sem ação;
  - lentidão: corrigir a consulta ou a tabela. Se a carga corre risco de passar das 06:15, avisar quem usa a foto.
- **Como confirmar:** a próxima execução fica abaixo de `limite_desvio_s` em `linha_base`.

### 5.5 Quarentena acima do normal
- **Sintoma:** `gold.dq_barrados_por_motivo_dia` sobe, e o painel de qualidade mostra mais não aptos.
- **Onde ver:** `silver.pendencia_evento_quarentena` (linha original e motivo); `gold.dq_qualidade_diaria`; o DQX
  Studio.
- **Diagnóstico:** qual motivo subiu e desde quando. É dado novo na origem, código novo ou um incidente programado
  (`JANELAS` em `carga_diaria/gerar_carga.py`)?
- **Ação:** corrigir na origem; a barreira está certa em barrar (P09). Depois da correção, reprocessar conforme a
  seção 6.
- **Como confirmar:** os barrados voltam ao padrão do motivo, e aptos + quarentena = bronze no dia.

### 5.6 Órfãs na fato
- **Sintoma:** `gold.dq_fato_orfas_diarias` mostra linhas além das esperadas. A forma de pagamento `NAO_CADASTRADA` é
  órfã de propósito.
- **Onde ver:** `gold.dq_fato_orfas_diarias`; o painel de qualidade; a consulta 8 do
  [roteiro](../dqx_studio/demo/ROTEIRO.md).
- **Diagnóstico:** é um código novo sem cadastro (L83) ou uma chave digitada errado?
- **Ação:** cadastrar na origem ou na dimensão. Na ontologia, a chave órfã tem o membro "não identificado", para não
  sumir dinheiro na Genie (L87).
- **Como confirmar:** as órfãs zeram, ou ficam só as explicadas, e o total da fato bate com o painel.

### 5.7 DQX Studio parado ou com HTTP 502 (L85)
- **Sintoma:** o app está `STOPPED`, as submissões voltam HTTP 502 ou aparece `lakebase_connection_unavailable`.
- **Onde ver:** `databricks apps get dqx-studio`; `databricks apps logs dqx-studio`; a tarefa `ligar_dqx_studio`.
- **Diagnóstico:** o app parou após 24 h, ainda está subindo (reinstala os pacotes por cerca de 1 min) ou o Lakebase
  está desligado.
- **Ação:** `databricks apps start dqx-studio --profile dbx-workshop`. Se o Lakebase estiver desligado,
  `databricks postgres update-endpoint ... spec.disabled=false` e reiniciar o app. Esperar "Application startup
  complete" antes de submeter.
- **Como confirmar:** o replay ou o agendamento roda sem nenhuma linha "erro submeter".

### 5.8 View recriada sem tags e Wiki (L31)
- **Sintoma:** TAG01 e TAG02 caem em `conformidade.pendencias`, e a Genie perde contexto da view.
- **Onde ver:** `conformidade.pendencias` filtrada pela view; a sonda `conformidade.sonda_views`.
- **Diagnóstico:** a view foi recriada com `CREATE OR REPLACE` fora de `garantir_view`.
- **Ação:** rodar `python3 governanca/aplicar_semantica.py` e republicar as Wikis. Em código novo, usar `garantir_view`
  (`carga_diaria/views_preservadas.py`).
- **Como confirmar:** as pendências de TAG somem no próximo `conformidade conferir`, e a auditoria fica em 100%.

### 5.9 Painel diferente do Power BI (L86)
- **Sintoma:** a paridade fica abaixo de 21/21 em `paineis_financeiros/powerbi/gerar_powerbi.py referencia`.
- **Onde ver:** `paineis_financeiros/powerbi/VALORES_DE_REFERENCIA.md`.
- **Diagnóstico:** uma medida semiaditiva (início ou fechamento) foi somada por grupo, e há grupos novos no meio do
  mês.
- **Ação:** calcular no total, com zero para o grupo que não existia, em `paineis_financeiros/gerar_paineis.py`. Depois,
  gerar e publicar no mesmo link.
- **Como confirmar:** 21/21 na referência.

### 5.10 Genie deixando dinheiro de fora (L87)
- **Sintoma:** a avaliação fica abaixo de 29/29, ou uma resposta traz um total menor que o do painel.
- **Onde ver:** `governanca/genie/avaliacao.json`; a SQL gerada pela Genie.
- **Diagnóstico:** um filtro de nulo numa chave órfã (produto, canal) tirou linhas.
- **Ação:** membro "não identificado" nas metric views (`governanca/gerar_ontologia_sql.py`); atualizar o gabarito e
  rodar `python3 governanca/genie.py avaliar` (gasta cota).
- **Como confirmar:** 29/29.

### 5.11 Checagem do DQX como código quebrando (L88)
- **Sintoma:** o job `pos_venda_dqx_codigo` falha ao validar as checagens.
- **Onde ver:** o log do job; `dqx_codigo/checks_pendencias.yml`.
- **Diagnóstico:** função de checagem com tipo que a versão do DQX não aceita. No DQX 0.17.2, `is_in_list` com texto
  falhou.
- **Ação:** usar `sql_expression` com `IN` para o domínio de texto. Validar o YAML e rodar o job
  ([dqx_codigo/README.md](../dqx_codigo/README.md)).
- **Como confirmar:** o job fica `SUCCESS`, e toda regra aparece nas métricas, mesmo com zero.

### 5.12 Alerta caro: mais de 4 disparos por dia (PLT06)
- **Sintoma:** PLT06 em "atenção", e o custo SQL da origem "Alerta SQL" sobe.
- **Onde ver:** `conformidade.recursos` e `conformidade/alertas.json`; `finops.uso_consultas_diario`.
- **Diagnóstico:** cada disparo acorda o warehouse por até 10 minutos (auto-stop), e o alerta horário custou
  US$ 29,73 em 7 dias (L79).
- **Ação:**
  - alerta do pós-venda: espaçar a agenda para até 4 por dia, ou pausar;
  - alertas `[Observabilidade]`: recomendar ao dono do bundle, que é só leitura para nós.
- **Como confirmar:** PLT06 atende depois de `gerar_conformidade.py alertas` e `aplicar`.

## 6 · Reprocessamento

- **Intervalo:** o job recebe `data_inicio` e `data_fim`. Sem parâmetros, usa o dia da execução. Para refazer um dia ou
  uma janela:
  `databricks bundle run carga_diaria -t dev --profile dbx-workshop --params data_inicio=AAAA-MM-DD,data_fim=AAAA-MM-DD`.
- **Idempotência por tarefa:**
  - `gerar_eventos` pula o dia que já está no bronze. A guarda filtra os nulos da subconsulta (L82).
  - O bronze só acrescenta (P06).
  - A silver anda pelo Auto CDC, com `SEQUENCE BY data_extracao`.
  - As dimensões são recriadas a partir da silver atual.
  - A fato apaga e regrava as fotos do intervalo (`DELETE ... BETWEEN` + `INSERT`), então rodar de novo não duplica.
- **Depois de corrigir na origem:** o evento corrigido chega numa extração seguinte e passa pela barreira. A linha que
  ficou na quarentena é evidência e não se apaga. Full refresh do pipeline só com decisão do dono, porque refaz a
  silver histórica a partir do bronze.
- **Reparar em vez de rodar tudo:** reparar a execução do job a partir da tarefa que falhou mantém as tarefas que já
  terminaram.
- **Replay do Studio:** com o app ligado e pronto (L85),
  `cd dqx_studio/regras && python3 -u rodar_ciclos.py <semanas> --replay`, que avalia todas as linhas. Para os
  agendamentos, `python3 registro_studio.py executar`.
- **Conferir depois:**
  - `sustentacao conferir`, com o volume por execução igual às tabelas;
  - `dqx_studio/painel/aplicar_e_testar.py`;
  - a paridade dos painéis.

## 7 · Mudança e deploy

1. Mudar a **fonte** (o gerador), nunca o arquivo gerado (AGENTS.md, fonte × gerado).
2. `gerar` e, onde houver, `testar` (só leitura).
3. `databricks bundle validate -t dev --profile dbx-workshop`.
4. Com aprovação (G6): `databricks bundle deploy -t dev --profile dbx-workshop`. Leia a linha de arquivos apagados do
   deploy (L74).
5. `aplicar` e `conferir` do módulo. Registrar no [CHANGELOG](CHANGELOG.md) com a conferência.
6. Commit e push com aprovação, depois da varredura de token, e-mail e caminho local (L70).

**Ligar as agendas** (decisão do dono, G9):
- carga: `cd carga_diaria && databricks bundle deploy -t dev --var="carga_schedule_status=UNPAUSED"`;
- Studio: `cd dqx_studio/regras && python3 registro_studio.py ligar`;
- alerta de sustentação: `cd sustentacao && databricks bundle deploy -t dev --var="alerta_status=UNPAUSED"`.

Ligue os três juntos: o alerta sem a agenda acusa "agenda pausada" como normal, e a agenda sem o alerta deixa o atraso
sem aviso.

**Rollback:**
- **Código e recursos:** `git revert` do commit, `gerar` e `bundle deploy` de novo. O bundle é declarativo e volta ao
  estado do commit.
- **Visões:** `aplicar` no commit anterior. Só recria o que mudou, e `garantir_view` devolve as tags (L31).
- **Dados:** rodar o intervalo afetado (seção 6). A fato regrava as fotos.
- **Agenda:** fazer o deploy com `PAUSED`.

## 8 · Escalonamento (RACI)

R = executa, A = responde, C = consultado, I = informado. No Free Edition todos os papéis são a mesma pessoa. A tabela
diz quem seria em produção.

| Situação | Origem (sistema de cobrança) | Dono do catálogo `pos_venda` | Squad pós-venda | Plataforma (engenharia de dados) | Dono do bundle de observabilidade |
|---|---|---|---|---|---|
| Carga falhou ou atrasou | I | I | R/A | C (warehouse, serverless) | — |
| Quarentena ou órfãs acima do normal | R (corrige o dado) | I | A (diagnóstico e reprocessamento) | — | — |
| Regra de negócio mudou (portão) | C | C | R/A | — | — |
| Cota ou warehouse | — | I | C | R/A | C (alertas que consomem) |
| Tags, descrição e dado pessoal | — | A | R | C | — |
| App do Studio ou Lakebase parado | — | — | R/A | C | — |
| Alerta caro ou quebrado do bundle | — | — | I | C | R/A |
| Ligar agendas, deploy em produção | — | A | R | C | — |

## 9 · Capacidade e custo

- **Warehouse:**
  - 1 SQL warehouse (`5f010b8396e591fb`), com cota diária de computação e auto-stop;
  - é o recurso escasso: painéis, Genie, alertas, conformidade, FinOps e sustentação disputam a mesma cota (L01);
  - o pipeline e os notebooks da carga usam computação serverless de job, não o warehouse.
- **Volume (24/11/2026):**
  - a fato tem **34,0 milhões de linhas** em 10 cargas (cerca de 250 mil linhas por foto);
  - o bronze tem **1,72 milhão de eventos** (cerca de 8,5 mil por dia).
  - Na agenda diária, a fato cresce cerca de 7,5 milhões de linhas por mês **(estimativa)**.
- **Tempo:** a duração é quase toda fixa: setup da computação e subida do pipeline (L89). O volume diário não é o
  gargalo hoje.
- **Custo:** a preço de lista, em `pos_venda.finops`.
  - US$ 0,09 por execução de job do pós-venda em novembro ([FinOps](../finops/README.md)).
  - O custo das execuções com falha fica em `finops.uso_jobs_diario.custo_falhas_usd`.
  - Cada disparo de alerta acorda o warehouse (L79).

## 10 · Indicadores da sustentação

| Indicador | Definição | Fonte | Hoje |
|---|---|---|---|
| % de dias no SLA | dias "no prazo" ÷ dias com execução da agenda | `sustentacao.sla_diario` | sem dado (agenda pausada) |
| Falhas | execuções com falha por semana | `finops.uso_jobs_diario` | 1 cancelada (pelo usuário) em 13 execuções da carga |
| Tempo para resolver | fim da execução com falha → fim da próxima com sucesso | `sustentacao.execucoes_job` | sem incidente real ainda |
| Custo das falhas | custo a preço de lista das execuções com falha | `finops.uso_jobs_diario` | ver a visão |
| Frescor | % das tabelas diárias escritas em 2 dias (USO01) | `conformidade.boas_praticas_dados` | depende da agenda |
| Desvios | execuções acima do limite por semana, por causa provável | `sustentacao.desvios` | 10 da carga e 40 do task runner do Studio desde 19/11; o alerta só avisa os de 60 s ou mais sem ser volume (L92) |

## 11 · Incidentes

**Modelo sem culpa:** o registro descreve o sistema, não a pessoa. Copie para o CHANGELOG do dia:

```markdown
### Incidente: <o que o usuário viu>
- **Início e fim:** <horário de Brasília> · **Impacto:** <quem ficou sem o quê e por quanto tempo>
- **Linha do tempo:** detecção (alerta, painel, pessoa) → diagnóstico → ação → confirmação
- **Causa:** <a causa técnica, com a evidência (visão, log, consulta)>
- **O que funcionou e o que não funcionou:** <runbook, alerta, painel>
- **Ações:** <correção feita> · <prevenção, com dono e data>
- **Conferência:** <comando e resultado que provam a volta ao normal>
```

**Do incidente à lição:** se a causa pode voltar em outro lugar, ela vira o próximo `L##` em
[03_LICOES_APRENDIDAS.md](03_LICOES_APRENDIDAS.md), no formato "o que aconteceu → regra que fica". A lição entra
também como linha da [matriz de resiliência](02_PLAYBOOK.md#matriz-de-resiliência) e como runbook na seção 5. Se a
regra virou código (uma checagem, um `conferir`), diga onde.

## 12 · Em produção

O que muda quando o domínio sair do Free Edition:

- **Agendas ligadas** (carga, Studio e alerta juntos, seção 7). Depois de 20 execuções da agenda, tire o
  **(provisório)** das metas e revise a hora meta.
- **Grupos como donos** de jobs, tabelas, painéis e alertas (regra EST04), e o job rodando como service principal
  (`run_as`).
- **Alertas para um destino do time:** e-mail de grupo ou Slack, por destino de notificação (`destination_id` em vez de
  `user_email`). Tags `project` e `team` também nos alertas.
- **Timeout e regra de saúde no job:** `timeout_seconds` de 2 vezes o p95 (PLT03) e uma regra `RUN_DURATION_SECONDS`
  no p95. Assim o próprio Jobs avisa da lentidão.
- **Dev e prod:** targets separados nos bundles (`mode: production` em prod), catálogo de produção e deploy só pelo
  pipeline de CI.
- **CI/CD:** a cada pull request, `gerar` + `bundle validate` + `testar`. No merge, `bundle deploy` em prod com service
  principal e `conferir` dos módulos. A varredura de segredos (L70) roda no CI.
- **Warehouse sem cota diária:** dimensionar pelo pico das 06:00 às 07:00, quando rodam carga, Studio, painéis e
  alerta.
