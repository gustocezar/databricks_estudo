# pos_venda · Roteiro da demonstração de qualidade de dados (DQX Studio)

**Mensagem central:** o dado de pagamentos pendentes chega todo dia. As regras de qualidade **barram** o que não pode
entrar na silver e **avisam** o que entra com ressalva. O DQX Studio mostra, semana a semana, os problemas aparecendo,
o pico e a recuperação, e deixa ver **linha por linha** o que foi reprovado e por qual regra.

| Recurso | Onde |
|---|---|
| DQX Studio (app) | https://dqx-studio-7474645927052439.aws.databricksapps.com (menu do usuário, canto superior direito → Idioma → Português) |
| Job de carga diária | Jobs → `pos_venda_carga_diaria` (id 288828593679314) |
| Pipeline da silver | Pipelines → `pos_venda_carga_silver_lakeflow` |
| Painel do Studio | Dashboards → `[release] DQX Quality Overview` |
| Consultas da demonstração | [consultas_demo.sql](consultas_demo.sql) (SQL Editor, warehouse *Serverless Starter Warehouse*) |
| Painel financeiro · Diretoria | https://dbc-15c48c79-7aa2.cloud.databricks.com/dashboardsv3/01f1e47bee241a5da58e8c357f99d8f5/published |
| Painel financeiro · Analista | https://dbc-15c48c79-7aa2.cloud.databricks.com/dashboardsv3/01f1e47bee3a1c5ebd180bfff03034a7/published |

---

## A história (8 semanas simuladas)

| Ciclo | Semana | O que acontece | Onde aparece |
|---|---|---|---|
| 1 | 20–26/11 | semana limpa: linha de base | só avisos de sempre (RG, e-mail, UF minúscula) |
| 2 | 27/11–03/12 | pico de CPF inválido, duplicatas e e-mail ausente | **avisos**: entram na silver, o Studio sinaliza |
| 3 | 04–10/12 | valor ≤ 0, status inválido, total ≠ parcela + multa + juros, pendência sem id | **erros**: barrados na quarentena |
| 4 | 11–17/12 | vencimento futuro, menor de idade, UF inválida, baixa sem data, atraso errado | **erros**: barrados |
|   |  | forma de pagamento nova, CEP malformado, canal CORRETOR sem corretor | **entram na silver**: a forma de pagamento é **erro que vazou** (não está na barreira); CEP e CORRETOR são **avisos** |
| 5 | 18–24/12 | recuperação: os incidentes caem até zerar (22/12) | barrados e vazados caem; as **órfãs da fato continuam** enquanto as pendências seguem abertas |
| 6 | 25–31/12 | **catálogo de erros e avisos**. O dia 25/12 é limpo; de 26/12 em diante voltam os incidentes I01 a I15. Entram também: tipo de evento nulo ou `ESTORNO`, multa fora da regra (com total coerente), faixa fora do domínio, tentativas fora de 1 a 10, cadastro do cliente com defeito e UF minúscula | **erros** barrados (os 11 motivos da quarentena) e **avisos** na silver |
| 7 | 01–07/01/2027 | **catálogo de vazamentos**. Passam pela barreira: cliente, apólice ou parcela sem número; vencimento nulo; `PAGA` sem baixa; canal de contato e motivo fora do domínio; periodicidade nova; cadastro de apólice ruim; produto, ponto de venda e corretor novos e incompletos (`VIDA_QA_*`, `PV_QA_*`, `COR_QA_*`); chave digitada errado e corrigida no evento seguinte | **dimensões** com cadastro ruim e **fato** com chaves órfãs |
| 8 | 08–09/01/2027 | 08/01 ainda tem os vazamentos da semana 7; **09/01 fecha o catálogo** com atraso zerado (barrado), cliente sem data de nascimento e produto e ponto de venda sem código (`PRODUTO SEM CODIGO`, `PONTO SEM CODIGO`) | bronze e quarentena (atraso), `dim_cliente`, `dim_produto` e `dim_ponto_venda`; semana parcial (2 dias) |


## Cobertura das regras (semanas 6 a 8)

Medida nas 32 execuções do Studio de 23/11/2026: replay das semanas 6, 7 e 8 nas 5 camadas e as 8 tabelas inteiras,
duas vezes. São 224 regras nas 13 tabelas, e **138 têm exemplo**. Antes das semanas novas, eram cerca de 32.

| Tabela | Regras | Com exemplo |
|---|---|---|
| bronze (`v_bronze_eventos_janela`) | 26 | 25 |
| quarentena (`v_quarentena_janela`) | 26 | 22 |
| silver, eventos aptos (`v_silver_eventos_aptos_janela`) | 29 | 19 |
| silver atual (`pendencia_atual`) | 29 | 18 |
| silver histórica (`v_silver_hist_janela`) | 10 | 1 |
| fato (`v_fato_snapshot_janela`) | 36 | 11 |
| `dim_cliente` | 20 | 15 |
| `dim_apolice` | 16 | 13 |
| `dim_produto` | 7 | 4 |
| `dim_ponto_venda` | 8 | 5 |
| `dim_corretor` | 7 | 3 |
| `bridge_apolice_cobertura` | 7 | 2 |
| `dim_data` | 3 | 0 |

**As 86 regras que ficam em zero são todas garantias da arquitetura (L84).** O exemplo delas, quando existe, está numa
camada anterior:
- **Chave substituta não nula**, na fato, nas dimensões e na ponte: a chave é `xxhash64` do código, que nunca é nula.
- **Chave única**, nas dimensões, na fato, na silver atual e na histórica: a dimensão pega uma linha por código, e o
  Auto CDC guarda uma versão por pendência e vigência.
- **Valores recalculados na fato:** multa de 2%, total igual a parcela + multa + juros, valores conforme as funções
  de regra, tentativas de 1 a 10, uma pendência por linha, entrada depois do vencimento e foto depois da entrada. As
  funções `pos_venda.regras.*` recalculam esses valores no dia da foto.
- **O que a barreira tira da silver:** pendência sem id, status nulo ou fora do domínio, valor nulo ou não positivo,
  total inconsistente, valores fora da regra, vencimento depois do evento, menor de idade e UF inválida. O exemplo
  fica na quarentena.
- **Data da extração nula:** a origem sempre carimba a data, e a guarda da carga ignora linha sem data (L82).
- **Na quarentena:** vencimento, apólice e parcela nulos passam pela barreira, então nunca estão na quarentena.
- **`dim_data`:** é um calendário gerado. A faixa "Vence hoje" também não chega à fato, porque a pendência entra um dia
  depois do vencimento.

O dia 09/01/2027 fechou as 5 regras que ainda faltavam:
- atraso zerado: 77 na bronze e na quarentena;
- nascimento nulo: 46 na `dim_cliente`;
- produto e ponto de venda sem código: 1 linha em cada dimensão.

Como o dado é avaliado:

```
fonte (sistema de cobrança) ──► bronze.pagamentos_pendentes_eventos   (tudo que chegou)
                                   │
                    barreira de qualidade (10 regras de erro, no pipeline Lakeflow)
                     ├── não apto ──► silver.pendencia_evento_quarentena  (linha original + motivo)
                     └── apto ─────► silver.pendencia_evento ─► pendencia_hist (SCD2) / pendencia_atual (SCD1)
                                                                   └─► gold: dimensões + fato histórica (foto diária)
DQX Studio ──► avalia as janelas semanais (pos_venda.dq.v_*_janela) com TODAS as linhas
               e guarda execuções, métricas e linhas reprovadas em main.dqx_studio
```

---

## Ato 1 · O dado chegando todo dia (3 min)

1. **Jobs → `pos_venda_carga_diaria`**: mostre as 5 tarefas (gerar eventos → silver Lakeflow → dimensões → fato → métricas).
   Execuções recentes: uma por semana simulada, com `data_inicio`/`data_fim`.
2. **Pipelines → `pos_venda_carga_silver_lakeflow`**: o grafo mostra o bronze se dividindo em **quarentena** e **eventos aptos**,
   e depois a histórica (SCD2) e a atual.
3. SQL **consulta 1**: a evolução diária. O % de barrados é 0 nas semanas 1–2, sobe até ~4,7% em 08/12 e 13/12 e volta a 0.

## Ato 2 · As regras no Studio (5 min)

1. **Regras** (Registro de Regras): os **modelos reutilizáveis** do Pós-venda, todos aprovados. Exemplo: "Campo obrigatório
   preenchido" é **um** modelo aplicado a 63 colunas; "Chave existe em dim_cliente" é a chave estrangeira; regras de negócio
   como `valor_total_igual_parcela_multa_juros` são modelos SQL. Cada um tem dimensão (Completeness, Validity, Uniqueness,
   Consistency) e severidade: **High** = erro (reprova a linha), **Medium** = aviso (sinaliza e deixa passar).
2. **Tabelas** (Tabelas Monitoradas): as 12 tabelas mapeadas (as 3 janelas de 7 dias de bronze, silver de eventos e fato,
   a silver atual e histórica, e as dimensões da gold). Abra uma: aba de regras aplicadas (modelo → coluna), versão
   aprovada e a **nota de qualidade** (score) depois da execução.
3. **Resultados**: visão consolidada das tabelas monitoradas por dimensão e severidade, com as checagens que falharam.
4. **Revisar e Aprovar**: o ciclo de vida é rascunho → pendente de aprovação → aprovada, para modelos e para tabelas.
5. **IA (em Regras → novo modelo → descrever em texto)**. Exemplo para colar:
   > O CEP do cliente deve ter exatamente 8 dígitos; quando o canal de venda for CORRETOR o corretor_id deve estar
   > preenchido; o valor_total_pendente deve ser maior ou igual ao valor_parcela; a forma_pagamento deve ser
   > DEBITO_CONTA, BOLETO, CARTAO_CREDITO ou PIX_AUTOMATICO.

   A IA (modelo `qwen3-next-80b`) devolve 4 regras em segundos, **mas** inventa um filtro (`tipo_evento = 'PAGAMENTO_PENDENTE'`)
   e esquece as aspas da lista. Ponto da demonstração: **a IA sugere, a pessoa revisa e aprova**.

## Ato 3 · A evolução semana a semana (7 min)

**Histórico de Execuções** → filtro de tabela ("Buscar tabelas…") → digite `janela`. Cada destino tem 5 execuções com
**todas as linhas** (amostra = 0), uma por semana, em ordem:

| Ciclo | Semana | Bronze: linhas · erro · aviso | Quarentena: linhas = erro | Silver aptos: erro · aviso | Fato: linhas · erro |
|---|---|---|---|---|---|
| 1 | 20–26/11 | 59.756 · **0** (0,00%) · 2.558 | 0 = 0 | **0** · 5.710 | 1.535.030 · **0** |
| 2 | 27/11–03/12 | 52.374 · **0** (0,00%) · 7.963 | 0 = 0 | **0** · 12.167 | 1.574.102 · **0** |
| 3 | 04–10/12 | 55.616 · **1.349** (2,43%) · 2.362 | 1.349 = 1.349 | **0** · 5.221 | 1.616.408 · **0** |
| 4 | 11–17/12 | 59.053 · **2.275** (3,85%) · 3.460 | 1.556 = 1.556 | **719** · 8.801 | 1.678.586 · **1.439** |
| 5 | 18–24/12 | 59.828 · **292** (0,49%) · 2.630 | 144 = 144 | **148** · 6.054 | 1.743.052 · **2.603** |

Regras com mais linhas por semana (erro/aviso):

- **v_bronze_eventos_janela**
  - semana 1 (20–26/11): email_preenchido 1.458 (aviso); uf_em_maiusculas 606 (aviso); evento_unico_por_dia_pendencia_tipo 540 (aviso)
  - semana 2 (27/11–03/12): email_preenchido 5.465 (aviso); evento_unico_por_dia_pendencia_tipo 2.294 (aviso); uf_em_maiusculas 536 (aviso)
  - semana 3 (04–10/12): valor_total_igual_parcela_multa_juros 520; valor_parcela_positivo 509; status_cobranca_valido 234; pendencia_id_nao_nulo 96
  - semana 4 (11–17/12): forma_pagamento_cadastrada 740; atraso_confere_com_as_datas 611; uf_valida 472; vencimento_ate_data_do_evento 291
  - semana 5 (18–24/12): forma_pagamento_cadastrada 148; uf_valida 67; valor_parcela_positivo 60; status_cobranca_valido 17
- **v_silver_eventos_aptos_janela**
  - semana 1 (20–26/11): rg_preenchido 2.976 (aviso); email_preenchido 1.458 (aviso); cpf_valido 937 (aviso); evento_unico_por_dia_pendencia_tipo 540 (aviso)
  - semana 2 (27/11–03/12): email_preenchido 5.465 (aviso); cpf_valido 3.191 (aviso); rg_preenchido 2.554 (aviso); evento_unico_por_dia_pendencia_tipo 2.294 (aviso)
  - semana 3 (04–10/12): rg_preenchido 2.695 (aviso); email_preenchido 1.312 (aviso); cpf_valido 889 (aviso); evento_unico_por_dia_pendencia_tipo 486 (aviso)
  - semana 4 (11–17/12): forma_pagamento_cadastrada 719; cep_8_digitos 2.955 (aviso); rg_preenchido 2.880 (aviso); email_preenchido 1.481 (aviso)
  - semana 5 (18–24/12): forma_pagamento_cadastrada 148; rg_preenchido 2.981 (aviso); email_preenchido 1.432 (aviso); cpf_valido 1.261 (aviso)
- **v_fato_snapshot_janela**
  - semana 1 (20–26/11): nenhuma violação
  - semana 2 (27/11–03/12): nenhuma violação
  - semana 3 (04–10/12): nenhuma violação
  - semana 4 (11–17/12): fk_forma_pagamento_sk 1.439
  - semana 5 (18–24/12): fk_forma_pagamento_sk 2.603

(gerado por `python3 resumo_evolucao.py` a partir do histórico do Studio)

O que comentar:
- **Bronze**: os erros só aparecem nas semanas 3–5: os incidentes que a barreira segura e, na 4 e na 5, também o que vazou.
- **Bronze, semana 2**: nenhum erro, mas os **avisos** triplicam (e-mail ausente de 1.458 para 5.465, duplicatas de 540 para
  2.294). São problemas que não justificam barrar o pagamento, mas precisam de atenção.
- **Silver (eventos aptos)**: **sem erro** nas semanas 1–3, porque a barreira funcionou. Na semana 4 aparecem **719 erros na
  silver**: a forma de pagamento nova **não estava na barreira** e vazou. CEP malformado (2.955) e canal CORRETOR sem
  corretor são **avisos**: entram de propósito, sinalizados.
- **Bronze = barrados + vazados**: semana 4 com 2.275 erros = 1.556 barrados + 719 vazados; semana 5 com 292 = 144 + 148.
- **Fato**: as linhas com `forma_pagamento_sk` órfã aparecem na semana 4 (**1.439**) e **crescem** na 5 (**2.603**), mesmo com o
  incidente acabando, porque a pendência continua aberta e entra na foto de cada dia. O número bate, dia a dia, com
  `gold.dq_fato_orfas_diarias` (consulta 8).
- **Quarentena**: 100% das linhas reprovam em pelo menos uma regra de erro do Studio (consulta 5). O pipeline e o Studio
  usam a mesma régua.

## Ato 4 · Os dados não aptos (5 min)

1. No Histórico, abra a execução de `v_bronze_eventos_janela` da **semana 3 ou 4** → aba de **linhas reprovadas**:
   cada linha traz a regra violada e a mensagem. Dá para **exportar** em CSV/Excel.
2. SQL **consulta 3b**: um exemplo de cada um dos 9 motivos de rejeição, com o cadastro do cliente.
3. SQL **consulta 3**: os eventos barrados, com valores, datas e cliente, ou seja, o que o time de cobrança precisa corrigir na origem.
4. SQL **consulta 4**: a mesma visão a partir da quarentena do Studio (`main.dqx_studio.dq_quarantine_records`).

## Ato 5 · O vazamento e a lição (3 min)

1. SQL **consulta 8b**: valores novos de forma de pagamento (`CRIPTOMOEDA`, `VALE_REFEICAO`, `TRANSFERENCIA_INTERNACIONAL`).
2. SQL **consulta 8**: as linhas da fato sem dimensão crescem de 52 (13/12) até ~450 (17/12) e só caem devagar.
   No Studio, a execução da **silver atual inteira** (608.622 pendências, todas as linhas) acusa **486 erros**, todos em
   `forma_pagamento_cadastrada`. São as pendências que ainda carregam o valor ruim, e 284 delas seguem abertas na foto
   de 24/12, exatamente as 284 órfãs da fato nesse dia.
3. **Lição**: a regra `forma_pagamento_cadastrada` já existia no Studio como **erro**, mas não estava na barreira do pipeline.
   O Studio detectou. O próximo passo é **promover a regra para a barreira**.

## Ato 6 · Governança e operação (4 min)

1. **Falso positivo**: no Histórico, as 2 primeiras execuções de `v_silver_eventos_aptos_janela` (semanas 1 e 2) estão
   marcadas como **False positive**, com comentário. Uma regra de chave da silver atual (`pendencia_id` único) foi aplicada por
   engano à silver de **eventos**, que tem vários eventos por pendência. A regra foi corrigida e a semana reavaliada. Mostre
   o status de revisão e o comentário: é o fluxo real de triagem.
2. **Agendamentos**: `pos_venda_janela_diaria` avalia as 3 janelas todo dia às 06:30 (Brasília), depois da carga das 05:00,
   com todas as linhas. Está **pausado** e deve ser ligado junto com o job.
3. **Profiler**: já há uma execução pronta (`68d02252c6b34590`). É o bronze filtrado na **semana limpa** (20–26/11):
   59.756 eventos e 15 colunas, em 91 s. O profiler aprendeu o comportamento normal e **sugeriu 25 regras**, entre elas:
   - `forma_pagamento_other_value`: só os 4 valores conhecidos. É **a regra que teria barrado o vazamento da semana 4**;
   - `cliente_idade_isnt_in_range` (18–74): pega o menor de idade da semana 4;
   - as listas de `status_cobranca`, `tipo_evento` e `canal_venda`, e as faixas de `valor_parcela` e `dias_atraso`.

   Mostre também o que **não** aproveitar: `data_extracao` fixada naquela semana e `dias_atraso` ≤ 55 são rígidas demais.
   Perfil sugere, a pessoa decide.
4. **Dashboards → `[release] DQX Quality Overview`**: visão consolidada das execuções e da quarentena do Studio.

## Ato 7 · O painel de qualidade do pos_venda (4 min)

**Dashboards → `pos_venda · Qualidade de dados`**
(https://dbc-15c48c79-7aa2.cloud.databricks.com/dashboardsv3/01f1e410f7f419f19ad6d416805a9bb2/published):
1. **Visão geral**: os 4 números do período e o gráfico de barrados por dia, com os marcos "semana 2: só avisos",
   "semana 3: chegam os erros" e "forma de pagamento nova vaza". Ao lado, as órfãs da fato subindo e caindo devagar.
2. **DQX Studio · evolução**: erros e avisos por semana e camada. Silver e fato só têm erro nas semanas 4–5 (o vazamento),
   e o contador de reconciliação mostra a quarentena 100% reprovada no Studio.
3. **Dados não aptos**: filtre um motivo na página Filtros (ex.: `cliente_menor_de_idade`) e mostre as linhas com o cliente.

---

## Ato 8 · Governança e ontologia: o dado com contexto (5 min)

1. **Discover → Domínios → Pós-venda**: 3 subdomínios (Cobrança e inadimplência, Clientes e apólices, Qualidade de dados),
   com os ativos marcados pela governed tag do domínio.
2. **Pages** (conceitos de negócio): abra **Saldo em aberto da carteira**. Mostre a regra "semiaditivo", as seções
   **Pode / Não pode** e **Como validar**. Abra **Cliente (segurado pagador)** para a seção de LGPD.
3. **Catalog Explorer → `pos_venda.gold.fact_pagamento_pendente_snapshot`**: a **Wiki** (grão, atualização, qualidade,
   pode / não pode, exemplo), a descrição das colunas e o selo **certified**.
4. **`pos_venda.gold.dim_cliente`**: as colunas de dado pessoal com tags `class.br_cpf`, `class.name`, `class.email_address`...
5. **`pos_venda.ontologia`**: entidades sem dados pessoais, `relacoes` (Cliente possui Apólice, Apólice gera Pendência...),
   `glossario` e as 4 **metric views** (carteira, recuperação, safra, qualidade).
6. Abra `mv_carteira_em_aberto` e mostre as medidas `Saldo de fechamento`, `Saldo de fechamento do mês anterior` e
   `Variação mensal do saldo`. Elas seguem os padrões semiaditivo e de comparação de períodos do repositório
   [databricks-solutions/uc-semantics-patterns](https://github.com/databricks-solutions/uc-semantics-patterns). A regra "não
   some saldos de dias diferentes" agora está na própria métrica, não só no texto.

## Ato 9 · Genie para o financeiro (5 min)

- **Pós-venda · Analista financeiro (cobrança e recuperação)**: "Qual o saldo em aberto hoje por faixa de atraso?",
  "Quanto recuperamos em dezembro por forma de pagamento e qual o ticket médio?", "Qual a taxa de recuperação das safras
  de setembro a novembro?", "Qual a posição de cada canal de venda no ranking de valor recuperado em novembro de 2026?".
- **Pós-venda · Diretor financeiro (visão executiva)**: "Como evoluiu o saldo de fechamento mês a mês e qual a variação
  mensal?", "Quanto o saldo de fechamento de novembro de 2026 variou em relação ao fechamento de outubro, em percentual?"
  (16,92%), "Quanto recuperamos no acumulado do ano até novembro de 2026?" (R$ 38.682.731,19), "A qualidade dos dados
  afetou os números de dezembro?".
- Ponto da demonstração: a Genie responde com a **regra certa** (saldo de fechamento ou foto mais recente, nunca somando
  dias), diz a data usada e não mostra dados pessoais. Isso vem das metric views, das instruções e das 27 perguntas de
  avaliação (27 de 27 corretas).

## Ato 10 · Os KPIs financeiros nos painéis (4 min)

Os dois painéis têm **uma página por fato** (carteira em aberto, recuperação, safras, qualidade dos dados); o da diretoria
abre numa **Visão executiva** que resume os quatro. Números abaixo com a foto de **25/12/2026** (dia carregado em 22/11).

**Dashboards → `pos_venda · KPIs financeiros · Diretoria`** (link na tabela do início), página **Visão executiva**:
1. **Primeira linha**: a foto mais recente contra 30 dias antes (saldo R$ 31,74 mi, % acima de 60 dias 62,6%, pendências
   253.914) e a taxa de recuperação (58,5%).
2. **Segunda linha**: variação mensal do saldo (+11,62%: 25/12 contra o fechamento de novembro), crescimento da carteira
   no mês (R$ 3,52 mi), recuperado no ano (R$ 44,27 mi) e variação mensal do recuperado no último mês completo
   (novembro: −6,04%). Dezembro não entra nessa comparação porque ainda não fechou.
3. Página **Carteira em aberto** → **Saldo de fechamento por mês** e **Variação mensal do saldo**: pergunte o mesmo à Genie
   e mostre que o número é igual, porque painel e Genie leem a mesma metric view.
4. Seja transparente: a carteira sintética só cresce, porque a simulação não baixa pendências por perda. Por isso a
   variação mensal cai de +198% em junho para +11,6% em dezembro, mas nunca fica negativa.

**`pos_venda · KPIs financeiros · Analista`** (time de negócio): na página **Carteira em aberto**, a tabela **Fechamento
mensal por produto e canal**; na página **Recuperação**, a **Recuperação mês a mês e acumulado no ano** (a coluna *Mês
completo* marca dezembro como incompleto). Os filtros de produto, canal e forma (página Filtros) valem para todas as
páginas, menos Qualidade dos dados.

**Power BI (opcional, para comparar):** o mesmo conteúdo em `paineis_financeiros/powerbi/projeto/*.pbip` (Power BI Desktop
no Windows), com os mesmos números (`VALORES_DE_REFERENCIA.md`). Ver [powerbi/README.md](../../paineis_financeiros/powerbi/README.md).

## Antes da demonstração

- O **Free Edition tem cota diária de computação**. Não rode cargas nem o replay no dia da demonstração. Abra o warehouse
  alguns minutos antes, porque ele desliga sozinho após 10 min sem uso.
- Rode `python3 aplicar_e_testar.py` em `pos_venda/dqx_studio/painel` uma vez: ele cria as views do painel e confere os números.

## Por que "janela" e "todas as linhas"

- O dry run do Studio lê as **primeiras N linhas** da tabela (`limit`), **não** uma amostra aleatória. Com 10 mil linhas
  num bloco de 60 mil a 1,7 milhão, os problemas de alguns dias ficam de fora. As execuções antigas `v_*_7d`, com amostra
  de 10 mil (ainda no Histórico), mostram isso: **nunca** acusaram as órfãs da fato (o completo achou 1.439 e 2.603) e só viram
  duplicatas no ciclo 5 (84, contra 608 no completo). É um bom contraste para mostrar na demonstração.
- A tabela `pos_venda.dq.janela_avaliacao` diz qual intervalo as views `v_*_janela` expõem. O job diário aponta para os
  **últimos 7 dias**, e o replay apontou para cada semana do passado. Cada camada tem um destino estável no Studio, e o
  histórico conta a evolução.

## Ligar em produção

1. Job `pos_venda_carga_diaria`: `databricks bundle deploy -t dev --var carga_schedule_status=UNPAUSED` (pasta `pos_venda/carga_diaria`).
   A última tarefa do job (`ligar_dqx_studio`) liga o app do Studio se ele tiver parado (no Free Edition ele para após 24 h).
2. Agendamentos do Studio (12 tabelas monitoradas, 06:30 de Brasília, só regras, todas as linhas):
   `python3 pos_venda/dqx_studio/regras/registro_studio.py ligar` (e `pausar` para desligar; `agenda` mostra o estado).
   Ligue e desligue junto com a agenda do job. O antigo `pos_venda_janela_diaria` foi removido (configuração em
   `dqx_studio/regras/resultados/agendamento_antigo_pos_venda_janela_diaria.json`).
3. Configurações de IA: o modelo foi trocado para `system.ai.qwen3-next-80b-a3b-instruct`, porque o padrão
   (`claude-sonnet-4-5`) não existe neste workspace.

## Como refazer tudo

```bash
cd pos_venda/dqx_studio/regras
python3 definir_regras.py            # gera checks/*.json e confere as colunas
python3 registro_studio.py aplicar   # Registro de Regras (70 modelos) + 12 Tabelas Monitoradas, aprovadas (o que o menu mostra)
python3 registro_studio.py executar  # executa as 12 tabelas com todas as linhas (Tabelas e Resultados)
# carregar_regras.py cadastrar = regras de tabela única (API antiga, fora do menu); não use nas 12 tabelas monitoradas:
# a trava contra duplicata do Studio deixaria as checagens do Registro presas em rascunho.
python3 -u rodar_ciclos.py 2 3 4 5   # carga semanal com incidentes + Studio (amostra 10 mil)
python3 -u rodar_ciclos.py 1 2 3 4 5 --replay   # histórico no Studio com todas as linhas, semana a semana
python3 -u rodar_ciclos.py --dims    # silver atual e dimensões inteiras
```
