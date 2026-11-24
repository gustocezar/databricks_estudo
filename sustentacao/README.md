# Sustentação · tempo de execução dos jobs e pipelines diários

> Schema `pos_venda.sustentacao`, gerado por [`gerar_sustentacao.py`](gerar_sustentacao.py). Prática P40 do
> [framework](../docs/04_FRAMEWORK.md). Números de 24/11/2026.

Responde a quem sustenta a carga diária em produção:

1. **Quanto tempo levou** cada execução, cada tarefa e cada atualização do pipeline Lakeflow? A resposta traz início,
   fim, duração, setup, resultado e tentativas.
2. **Qual é o normal?** A linha de base é a mediana e o p95 das últimas 20 execuções com sucesso.
3. **O que passou do normal, quanto passou e por quê?** O desvio separa espera por computação, volume maior e
   lentidão com o mesmo volume.
4. **A carga terminou até a meta (06:15)?** Se não terminou, quanto atrasou. Com a agenda pausada, a página mostra a
   folga projetada.
5. **O que fazer em cada tarefa?** A matriz de resiliência por tarefa (P28) traz o sintoma e a ação.

```
system.lakeflow.job_run_timeline ─────► execucoes_job ──┐
system.lakeflow.job_task_run_timeline ► execucoes_tarefa ├─► linha_base ─► desvios ─┐
system.lakeflow.pipeline_update_timeline ► atualizacoes_pipeline ┘                   ├─► alerta_sustentacao ─► alerta SQL (06:20, pausado)
bronze (_ingestao_ts) e fato (_carga_ts) ─► volume_diario, volume_execucao ──────────┤
jobs_monitorados + config_sla ─► sla_diario, ultima_execucao ────────────────────────┘
TAREFAS (gerador) ─► matriz_tarefas                       painel "pos_venda · Sustentação" (página Sustentação)
```

**Reaproveita, não duplica:**
- **Atribuição.** Quais jobs e pipelines são do projeto vem de `pos_venda.finops.config_atribuicao`, as mesmas regras
  da FinOps.
- **Custo.** A duração média por dia, as falhas e o custo por execução continuam em `pos_venda.finops.uso_jobs_diario`.
- **Regras.** O frescor das tabelas (USO01) e o timeout dos jobs (PLT03) continuam em `pos_venda.conformidade`. Aqui
  entra o timeout sugerido a partir do p95.
- **Só leitura.** O bundle `observabilidade-framework` e o `finops.observability` só são lidos. O alerta de jobs com
  falha do bundle continua com o dono dele.

## As visões

| Visão | Responde |
|---|---|
| `execucoes_job` | uma linha por execução de job do projeto: início e fim (UTC e horário de Brasília), duração, fila, setup, resultado, gatilho (agenda ou manual) e o intervalo carregado (`data_inicio`, `data_fim`) |
| `execucoes_tarefa` | uma linha por execução de tarefa: duração, setup, execução, limpeza, resultado e o número da tentativa |
| `atualizacoes_pipeline` | uma linha por update dos pipelines Lakeflow do projeto: duração, espera entre a tarefa do job e o início do update, full refresh |
| `volume_diario` | eventos do bronze por `data_extracao` e linhas da fato por foto |
| `volume_execucao` | o que cada execução da carga gravou: dias do intervalo, eventos no bronze, linhas e fotos na fato, segundos por dia |
| `linha_base` | por job, tarefa e pipeline: mediana, p95, mínimo e máximo das últimas 20 execuções com sucesso; setup e execução medianos; limite de desvio; timeout sugerido |
| `desvios` | execução com sucesso acima do p95 ou de 1,5 vez a mediana das 20 anteriores (mínimo de 5), com o excesso e a causa provável |
| `sla_diario` | os últimos 30 dias de cada job com hora meta: execuções da agenda e manuais, fim, atraso e situação |
| `ultima_execucao` | a última execução de cada job, comparada com a base, com o atraso na meta, a folga projetada e o timeout sugerido |
| `matriz_tarefas` | por tarefa da carga: o que faz, sintoma e ação na falha e na lentidão, referência na matriz do playbook, base e última execução |
| `alerta_sustentacao` | o que o alerta avisa: SLA estourado hoje e desvios das últimas 24 h da carga diária (vazia = nada a fazer) |
| `jobs_monitorados`, `config_sla`, `config_sustentacao` | os jobs do projeto com agenda e timeout, a hora meta e os parâmetros |

Todas as colunas têm descrição no Unity Catalog. As colunas `*_local` estão no horário de Brasília
(`convert_timezone`, que não depende do fuso da sessão).

## Regras de cálculo

- **Execução.** Uma execução que passa da virada da hora vem em várias linhas ("fatias") nas tabelas `*_timeline`, e
  só a última traz o resultado. As visões juntam as fatias por `run_id`: o início é o menor, o fim é o maior, e o
  resultado e as durações vêm da última fatia (L90).
- **Linha de base.** Só entram execuções com sucesso. Uma tarefa desativada aparece como `SKIPPED`, com duração 0, e
  puxaria a mediana para baixo. Com menos de 5 execuções a base "não vale", e nenhum desvio é apontado.
- **Desvio.** A execução é comparada com as 20 execuções com sucesso **anteriores** a ela (base móvel), não com a base
  de hoje. A causa provável é:
  - **espera por computação**, quando o setup explica metade ou mais do que passou da mediana;
  - **volume maior**, quando o intervalo tem mais de 1,5 vez os dias da base;
  - **lentidão com o mesmo volume**, nos outros casos.
- **SLA.** Só a execução da agenda (gatilho `CRON`) conta. Execução manual roda em qualquer hora, e medir o SLA nela
  daria um "atraso" de horas sem sentido (L91). Com a agenda pausada, a situação é "agenda pausada". A folga
  projetada é a meta menos a hora da agenda menos o p95: diz se a meta cabe quando a agenda for ligada.

## Painel e alerta

O bundle desta pasta implanta:

- **o painel "pos_venda · Sustentação"**, com a página "Sustentação". Ela tem os indicadores da carga, a duração por
  tarefa em cada execução, a linha de base, volume × duração, os desvios, o SLA dia a dia, a espera e o update do
  pipeline, a matriz por tarefa, a última execução de cada job e o que o alerta avisaria agora;
- **o alerta SQL "pos_venda · Sustentação: SLA ou desvio da carga"**:
  - lê `count(*)` de `alerta_sustentacao` e dispara quando o resultado passa de 0;
  - avisa o SLA estourado hoje e os desvios da carga nas últimas 24 h que passaram do limite por 60 s ou mais e que
    não são explicados por volume;
  - roda às 06:20 (horário de Brasília), 1 vez por dia: a regra PLT06 permite até 4;
  - nasce **pausado** (variável `alerta_status`) e liga junto com a agenda da carga (P02).

## Rodar

```bash
cd pos_venda
python3 sustentacao/gerar_sustentacao.py gerar      # sustentacao.sql, o JSON do painel e resources/sustentacao.yml
python3 sustentacao/gerar_sustentacao.py testar     # roda cada visão e cada conjunto do painel sem criar nada
python3 sustentacao/gerar_sustentacao.py aplicar    # cria o schema e as visões (só recria a que mudou)
python3 sustentacao/gerar_sustentacao.py conferir   # checagens -> conferencia.json
cd sustentacao && databricks bundle deploy -t dev --profile dbx-workshop    # painel + alerta pausado
```

Para ligar o alerta junto com a agenda da carga:

```bash
databricks bundle deploy -t dev --var="alerta_status=UNPAUSED" --profile dbx-workshop
```

**`conferir` verifica:**
- que cada visão responde;
- que as execuções de job e de tarefa e os updates do pipeline batem com os `run_id` e `update_id` das tabelas de
  sistema;
- que o volume do bronze e da fato, somado por dia e por execução, é igual às tabelas;
- que a mediana de cada tarefa é igual ao cálculo direto na tabela de sistema;
- que todo desvio tem base suficiente e passou do limite;
- que toda tarefa da carga está na matriz;
- que o SLA tem um dia por linha;
- que toda coluna tem descrição;
- que a consulta do alerta responde e que, com 30 dias em vez de 24 h, ela acharia ocorrências.

## O que os números mostram (24/11/2026)

**Histórico curto.** As agendas estão pausadas, então as 13 execuções da carga (12 com sucesso e 1 cancelada) foram
manuais, entre 19 e 23/11, em horários variados e com intervalos de 1 a 184 dias. A linha de base é indicativa,
não um padrão de produção.

| Tarefa | Execuções com sucesso | Mediana (min) | p95 (min) |
|---|---|---|---|
| `portao_regras` | 4 | 3,59 | 3,73 |
| `gerar_eventos` | 12 | 3,05 | 4,37 |
| `silver_lakeflow` | 12 | 6,81 | 7,39 |
| `gold_dimensoes` | 11 | 3,65 | 4,17 |
| `gold_fato_snapshot` | 12 | 0,40 | 2,09 |
| `dq_metricas` | 8 | 0,39 | 0,65 |
| `ligar_dqx_studio` | 3 | 0,11 | 2,11 |

Valores calculados direto em `system.lakeflow.job_task_run_timeline`.

- **A duração não acompanha o volume (L89).** Execuções comparadas:

  | Intervalo | Eventos no bronze | Linhas na fato | Duração |
  |---|---|---|---|
  | backfill de 184 dias | 1.304.869 | 21,5 milhões | 14,5 min |
  | 1 dia | 8.472 | 214 mil | cerca de 14 min |

  A maior parte do tempo é fixa:
  - a primeira tarefa de notebook espera a computação serverless, com cerca de 2,5 a 3 min de setup;
  - a `gold_dimensoes` espera de novo, depois do pipeline;
  - o update do pipeline começa cerca de 1,5 min depois da tarefa `silver_lakeflow` e dura de 2,4 a 5,8 min.
- **Por que a `gerar_eventos` tem mediana alta (3,05 min).** Nas primeiras execuções ela era a primeira tarefa, porque
  o portão ainda não existia, e carregava o setup. Separar setup e execução mostra isso.
- **`ligar_dqx_studio`** leva segundos com o app ligado e 2,3 min com o app parado (23/11, 20:16).
- **SLA.** A agenda da carga está pausada, então todos os dias aparecem como "agenda pausada".

- **Carga inteira:**
  - a mediana é de 14,53 min e o p95, de 16,05 min (12 execuções com sucesso);
  - a folga projetada até 06:15 é de 59,0 min, para a agenda das 05:00;
  - o timeout sugerido é de 33 min, e hoje o job não tem timeout (PLT03).
- **Pipeline da silver:** o update tem mediana de 5,21 min e p95 de 5,75 min.
- **Desvios:** 50 no total, dos quais 40 vêm do task runner do DQX Studio, que roda sob demanda. Os 10 da carga são, em
  geral, poucos segundos acima de um p95 que, com poucas execuções, fica no máximo. O caso real é de 22/11, às 11:40:
  - a `gold_fato_snapshot` levou 201 s contra 24 s de mediana;
  - a `gold_dimensoes` tinha sido pulada, e a fato carregou os 165 s de setup;
  - a causa provável ficou certa: espera por computação.
- **Alerta:** na primeira conferência, ele avisaria 3 vezes por ruído. Por isso passou a exigir 60 s ou mais acima do
  limite e a ignorar o desvio explicado por volume (L92). Agora avisa 0 e, em 30 dias, avisaria 2 casos reais. O
  painel continua mostrando todos.

## Conferência (24/11/2026)

`conferir` passou nas 13 checagens:
- **Visões e painel:** as 14 visões e os 10 conjuntos do painel respondem, com o catálogo e o schema do bundle.
- **Execuções:** 186 de job, 249 de tarefa e 13 updates de pipeline, iguais às tabelas de sistema.
- **Volume:** bronze de 1.718.895 eventos e fato de 34.026.469 linhas, iguais por dia, por execução e nas tabelas.
- **Medianas:** as 7 medianas por tarefa são iguais ao cálculo direto.
- **Matriz e SLA:** 7 de 7 tarefas na matriz, e 30 dias no SLA.
- **Descrições:** 0 colunas sem descrição.

O deploy criou o painel, publicado, e o alerta, pausado: `PAUSED`, às 06:20, America/Sao_Paulo. Na conformidade, o
schema entrou como "apoio" sem pendência nova. As 14 visões só aparecem em EST04 (dono pessoa), como todo ativo do
Free Edition.

## Limites

- **A agenda é a de hoje.** `system.lakeflow.jobs` guarda a configuração mais recente. Um dia antigo sem execução
  aparece com a situação de agenda de hoje.
- **O volume vem do momento da gravação.** As colunas `_ingestao_ts` e `_carga_ts` ligam as linhas às execuções.
  Uma execução que não grava o bronze, porque o dia já existe, tem 0 eventos.
- **Execução em andamento não vira desvio.** Ela aparece no SLA como "atrasada (em andamento)" depois da meta.
- **No nível do job, o setup fica perto de zero.** O setup de computação é das tarefas. A causa "espera por
  computação" aparece nas linhas de tarefa.
- **O p95 fica perto do máximo** enquanto houver menos de 20 execuções.
