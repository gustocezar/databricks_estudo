# Framework · práticas aplicadas no pos_venda, de onde vieram e por quê

> Documento incremental. Última atualização: **26/11/2026**. Cada prática tem um código (`P##`) que não muda.
> Fontes conferidas em 22 e 23/11/2026 (todos os links responderam).

Este framework reúne as **41 práticas** aplicadas no domínio pós-venda de seguro de vida (fases 0 a 29 da
[trilha](01_TRILHA_DE_APRENDIZAGEM.md)), cada uma com:

- **Origem:** de onde veio. Pode ser documentação oficial, acelerador da Databricks, Databricks Labs, Microsoft,
  legislação ou uma lição do próprio projeto (`L##`).
- **Como aplicamos:** o que foi feito e onde está no repositório.
- **Por quê:** o problema que a prática resolve.
- **Reaplique quando:** o sinal, num case parecido, de que a prática vale.
- **Prova:** o número ou a checagem que mostra que funcionou.

Os outros documentos complementam este:

| Documento | O que dá |
|---|---|
| [Playbook](02_PLAYBOOK.md) | o **passo a passo**: perfil da base, módulos M1 a M13 com critério de saída, matriz de resiliência, roteiro de reconstrução |
| [Lições aprendidas](03_LICOES_APRENDIDAS.md) | as **armadilhas**, com o código `L##` |
| Este framework | o **porquê de cada escolha** e a fonte de cada uma |
| [Skills e ganhos](05_SKILLS_E_GANHOS.md) | a **linhagem**: que skill foi consultada em cada prática e o ganho medido |
| [Guia para outra base](06_GUIA_BASE_BRUTA.md) | o **caminho para reaplicar** numa base bruta, com um agente de código e as duas trilhas do DQX |
| [Manual de sustentação](07_SUSTENTACAO.md) | o **dia a dia em produção**: o que roda, SLAs, onde olhar, rotina, runbooks, reprocessamento, deploy, RACI e indicadores |

```
 Fundação ─► Dados ─► Qualidade ─► Governança ─► Semântica ─► Consumo ─► Avaliação
 (P01–P03)  (P04–P08) (P09–P12)    (P13–P16)     (P17–P20)    (P21–P23)  (P24–P27)
                                Operação contínua (P28–P29)
                    Custo e uso · FinOps (P30–P34), sobre o workspace inteiro
              Conformidade e observabilidade (P35–P37), sobre o workspace inteiro
         Reaplicação em outra base (P38–P39): DQX em duas trilhas e guia para agente
       Sustentação em produção (P40): tempo de execução, linha de base, desvio, SLA e volume
```

---

## Como usar num case parecido

1. **Perfil da base.** Responda às 9 perguntas do [Passo 0 do playbook](02_PLAYBOOK.md#passo-0--perfil-da-base): como
   os dados chegam, o que muda no tempo, a natureza das medidas, dado pessoal, quem consome, regulação e onde roda.
2. **Escolha as práticas** pelo [mapa de gatilhos](#mapa-de-gatilhos) abaixo. Cada resposta do perfil aponta para as
   práticas que valem.
3. **Construa na ordem das camadas**, usando os módulos do playbook (M1 a M13). Não avance sem o critério de saída do
   módulo.
4. **Avalie com réguas de fora** (P24 a P26) e faça a triagem de cada achado antes de mudar qualquer coisa.
5. **Registre:** CHANGELOG, trilha, lições e a situação de cada acelerador (P27, P29).

## Mapa de gatilhos

| Se o seu case tem... | Comece por |
|---|---|
| Free Edition ou outro plano com limites | P01, P02 |
| Dados que não podem sair do ambiente, ou falta de dado de teste | P04 |
| Eventos diários com mudança de status | P06, P07 |
| Medida de **posição** (saldo, estoque, carteira) | P07, P19 |
| Medida de **fluxo** (pagamentos, vendas) | P19 (MoM, MTD, YTD) |
| Problemas que tornam o dado inutilizável | P09, P10 |
| Necessidade de histórico de qualidade e evidência para auditoria | P11, P12 |
| Dado pessoal (CPF, nome, contato) | P15, P17 |
| Regra de cálculo com impacto financeiro ou regulatório (multa, juros, faixa) | P20 |
| Perguntas em linguagem natural (Genie) | P13, P18, P21, P24 a P26 |
| Mais de uma ferramenta de BI | P18, P23 |
| Star schema consultado por metric views ou BI | P08 |
| Recriações que apagam metadados | P16 |
| Repositório público | P03 |
| Saber quanto custa cada funcionalidade e de quem é o custo | P30, P31 |
| Time de plataforma e squads dividindo o mesmo workspace | P31, P32 |
| Medir a adoção de Genie e painéis | P33 |
| Revisar custo com uma régua conhecida | P34 |
| Regras de governança que precisam continuar valendo depois da primeira aplicação | P35, P37 |
| Observabilidade herdada (jobs, alertas, visões) que ninguém revisou | P36 |
| Views sobre tabelas de sistema ou sobre schemas de outro time | P37 |
| Sem permissão para conceder privilégio no catálogo a um app, ou sem vaga de app | P38 |
| Aplicar o framework a outra base com um agente de código (Copilot, Claude Code, Codex) | P39, P38 |
| Job diário com consumidor em hora marcada, ou "por que a carga demorou hoje?" | P40, P28 |
| Regra de qualidade que muda com o tempo, ou o negócio precisa dizer o que é dado certo e triar as falhas | P41, P09, P20 |

---

## Fundação

### P01 · Conhecer os limites da plataforma antes de desenhar
- **Origem:** [Free Edition limitations](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)
  (Databricks); lições L01 a L06.
- **Como aplicamos:**
  - Um warehouse 2X-Small, cota diária, até 3 apps, 1 projeto Lakebase, sem modelos Claude no Model Serving.
  - Todo script que usa o warehouse detecta a cota esgotada (`governanca/sql_util.py`, `CotaEsgotada`).
  - O bundle do DQX Studio ganhou um patch para usar o warehouse existente.
- **Por quê:** os limites decidiram quais aceleradores cabem. O Genie Workbench ficou de fora para não gastar a última vaga
  de app. Um script que falha sem explicar quando a cota acaba parece defeito.
- **Reaplique quando:** sempre. Em workspace pago, os limites são outros (cotas, custos, permissões), mas a pergunta é a
  mesma.
- **Prova:** decisões de "não agora" registradas com motivo em `referencias/databricks_solutions/REVISAO_2026-11-22.md`.

### P02 · Tudo é código, idempotente, implantado por bundles, com agendas pausadas
- **Origem:** [Declarative Automation Bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/) (Databricks);
  princípios 1 e 3 do playbook; lição L06.
- **Como aplicamos:** bundles `carga_diaria`, `paineis_financeiros` e `dqx_studio/painel`; geradores (`gerar_carga.py`,
  `gerar_ontologia_sql.py`, `gerar_paineis.py`, `gerar_powerbi.py`) seguem o ciclo *gerar → aplicar → conferir*; toda
  agenda nasce `PAUSED` (variável `carga_schedule_status`).
- **Por quê:** rodar de novo não duplica nem quebra; o projeto pode ser reconstruído do zero; uma agenda ligada por engano
  gasta a cota.
- **Reaplique quando:** sempre.
- **Prova:** `databricks bundle validate -t dev` sem erro; o mesmo dia carregado duas vezes não duplica linhas (fase 3).
  As agendas ficaram pausadas até 24/11, quando o dono pediu para ligar: carga às 05:00 com timeout de 33 min (2 × p95,
  P40), Studio às 06:30 e alerta de sustentação às 06:20.

### P03 · Versionar no Git e varrer antes de publicar
- **Origem:** prática do projeto (L70, L74).
- **Como aplicamos:**
  - Repositório `gustocezar/databricks_estudo`.
  - O `.gitignore` deixa fora só o que se recria: `.venv`, caches, `.databricks/` e esquemas baixados.
  - Antes de cada envio, varremos tokens, e-mails e caminhos locais nos arquivos.
- **Por quê:**
  - Um repositório público é uma publicação.
  - O deploy do bundle segue o `.gitignore`: depois que ele entrou, o deploy apagou dois `.pyc` do workspace.
- **Reaplique quando:** sempre. É pré-requisito para CI/CD (`databricks-dab-examples`).
- **Prova:** nenhum token nos arquivos enviados; o GitHub tem os mesmos arquivos que o commit local. Desde 24/11, o
  CI (`.github/workflows/ci.yml`) repete a varredura, compila os scripts, lê os YAML e confere os links em todo push;
  com os segredos do Databricks, valida os 7 bundles e roda os 36 cenários BDD.

---

## Dados

### P04 · Dados sintéticos com defeitos injetados de propósito
- **Origem:** [dbldatagen](https://github.com/databrickslabs/dbldatagen) (Databricks Labs); lição L07.
- **Como aplicamos:**
  - `01_gerar_one_table.py` gera 500.000 parcelas pendentes, com 91 colunas e semente fixa.
  - Com `injetar_defeitos = true`, entram duplicatas, CPF inválido, e-mail e telefone nulos e UF em minúsculas.
- **Por quê:** dá para construir e demonstrar sem dado real. Os defeitos tornam a qualidade visível.
- **Reaplique quando:** o dado real não pode ser usado no ambiente de construção, ou a demonstração precisa de incidentes
  controlados.
- **Prova:** os 5 ciclos da demonstração mostram os incidentes aparecendo, sendo barrados e se recuperando (fases 4 e 6).
- **Cuidado:** CPF sintético com dígito válido pode coincidir com um documento real, e o e-mail usa domínios reais.

### P05 · Medalhão com star schema e chaves substitutas estáveis
- **Origem:** [Medallion architecture](https://docs.databricks.com/aws/en/lakehouse/medallion) (Databricks).
- **Como aplicamos:**
  - Bronze, silver e gold, com fato, 12 dimensões e a ponte `bridge_apolice_cobertura`.
  - Chave substituta = `xxhash64(chave de negócio)`.
  - Membro `NAO_INFORMADO` nas dimensões.
- **Por quê:** a chave por hash é a mesma a cada execução. A fato histórica continua válida quando a dimensão é reescrita,
  coisa que uma chave sequencial quebraria.
- **Reaplique quando:** há dimensões reescritas por carga e uma fato que guarda história.
- **Prova:** 14/14 chaves primárias únicas, inclusive os 30,1 milhões de linhas da fato (`governanca/aplicar_rely.py verificar`).

### P06 · Carga incremental: bronze só acrescenta, Auto CDC monta a história
- **Origem:** [Lakeflow Declarative Pipelines](https://docs.databricks.com/aws/en/ldp/) e
  [AUTO CDC](https://docs.databricks.com/aws/en/ldp/cdc) (Databricks).
- **Como aplicamos:**
  - O job `pos_venda_carga_diaria` gera eventos `NOVA`, `ATUALIZACAO` e `BAIXA` no bronze, que só acrescenta.
  - A silver mantém `pendencia_hist` em SCD2 (a história) e `pendencia_atual` em SCD1 (o estado atual).
- **Por quê:** guarda a história sem reprocessar tudo. Evento repetido é absorvido, e o dia carregado de novo não duplica.
- **Reaplique quando:** a origem manda eventos ou mudanças de status, e o negócio pergunta tanto "como está" quanto "como
  estava em tal dia".
- **Prova:** dia novo pelo caminho todo, com 16 minutos de execução, 8.559 eventos e 0 divergência na silver e na gold
  (fase 19).

### P07 · Fato snapshot diária e saldo semiaditivo
- **Origem:** Kimball,
  [Periodic snapshot fact table](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/periodic-snapshot-fact-table/)
  e [Additive, semi-additive, non-additive facts](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/additive-semi-additive-non-additive-fact/);
  liquid clustering em [Delta clustering](https://docs.databricks.com/aws/en/delta/clustering) (Databricks).
- **Como aplicamos:**
  - `fact_pagamento_pendente_snapshot` guarda uma linha por pendência em aberto por dia, com valores recalculados na data
    da foto.
  - A tabela é agrupada por `data_referencia_sk`.
  - Todas as medidas de saldo pegam o último dia do contexto.
- **Por quê:** saldo é uma posição. Somar dias diferentes infla o número, e essa regra atravessa Pages, metric views, Genie,
  painéis e o DAX.
- **Reaplique quando:** a medida é posição (saldo, estoque, carteira, reserva).
- **Prova:** paridade 21/21 entre o painel do Databricks e as medidas DAX, que repetem a regra semiaditiva (foto de
  25/12). Na reconferência de 24/11 (foto de 09/01/2027), deu 20/21: o painel somava o início do mês de cada grupo, e
  grupos novos no meio do mês distorcem essa soma (L86). Corrigido o painel, voltou a 21/21.

### P08 · Chaves informativas, com `RELY` só nas primárias
- **Origem:** [Constraints](https://docs.databricks.com/aws/en/tables/constraints) e
  [Query optimization with RELY](https://docs.databricks.com/aws/en/sql/user/queries/query-optimization-constraints)
  (Databricks); regra DP-004 do [powerbi-analyzer](https://github.com/databricks-solutions/powerbi-analyzer); lição L72.
- **Como aplicamos:**
  - `governanca/aplicar_rely.py` prova a unicidade das chaves, declara `RELY` nas 14 chaves primárias e recria as 15
    estrangeiras sem `RELY`.
  - A carga diária já cria as chaves com `RELY`.
- **Por quê:** com `RELY`, o otimizador elimina a junção com uma dimensão que a consulta não usa. A chave estrangeira de
  forma de pagamento tem órfãs de propósito: com `RELY`, o LEFT JOIN poderia virar INNER JOIN e mudar os totais.
- **Reaplique quando:** metric views ou ferramentas de BI consultam um star schema por visões que juntam muitas dimensões.
- **Prova:** saldo por dia na metric view passou de 9 junções para 0, e a fonte do Power BI de 9 para 6, com resultado
  idêntico.
- **Cuidado:**
  - O Databricks não valida as chaves: prove a unicidade antes de declarar.
  - Não existe `ALTER CONSTRAINT`. A chave é removida e declarada de novo, e o `CASCADE` apaga as chaves estrangeiras.

---

## Qualidade

### P09 · Barreira no pipeline: erro barra, aviso entra com ressalva
- **Origem:** [Expectations](https://docs.databricks.com/aws/en/ldp/expectations) (Databricks); princípio 5 do
  playbook.
- **Como aplicamos:**
  - 10 regras de erro no pipeline. O que não passa vai para `silver.pendencia_evento_quarentena`, com o motivo.
  - Os avisos entram e são contados.
  - As métricas diárias ficam em `gold.dq_qualidade_diaria`, `dq_barrados_por_motivo_dia` e `dq_fato_orfas_diarias`.
- **Por quê:** o que não é barrado no começo **vaza** e aparece depois como chave órfã na fato. Separar erro de aviso
  evita perder dado bom.
- **Reaplique quando:** existe uma lista de problemas que tornam o dado inutilizável (vira regra de erro); o resto vira
  aviso.
- **Prova:** na semana do vazamento, as formas de pagamento novas aparecem como `NAO_CADASTRADA` e como órfãs na fato
  (fase 4).

### P10 · Incidentes programados para provar a barreira
- **Origem:** prática do projeto (L07, L64).
- **Como aplicamos:** 7 ciclos semanais com roteiro, nesta ordem:
  1. semana limpa;
  2. pico de avisos;
  3. erros barrados;
  4. erros que vazam;
  5. recuperação;
  6. catálogo de erros e avisos: voltam os incidentes e entram os que faltavam para cada regra de origem;
  7. catálogo de vazamentos: cadastro ruim, código novo e chave corrigida depois chegam às dimensões e à fato.

  Os 38 incidentes (I01 a I38) vivem no gerador de eventos (`carga_diaria/gerar_carga.py`) e entram pelo fluxo normal:
  bronze, barreira, silver, dimensões e fato.
- **Por quê:** um dia sem incidente prova que a regra não reprova evento bom, não que ela pega erro.
- **Reaplique quando:** a qualidade precisa ser demonstrada ou homologada.
- **Prova:**
  - roteiro em [dqx_studio/demo/ROTEIRO.md](../dqx_studio/demo/ROTEIRO.md);
  - com as semanas 6 e 7 e o dia 09/01, 138 das 224 regras do DQX Studio (13 tabelas) têm exemplo; antes eram
    cerca de 32;
  - as 86 em zero são todas garantias da arquitetura (L84): chave por hash, chave única, valores recalculados pelas
    funções e o que a barreira já tira.

### P11 · Monitoramento contínuo com DQX Studio, em janelas com todas as linhas
- **Origem:** [DQX](https://github.com/databrickslabs/dqx) ([documentação](https://databrickslabs.github.io/dqx/))
  (Databricks Labs).
- **Como aplicamos:**
  - Studio instalado como app, com estado no Lakebase.
  - Registro de Regras com 69 modelos, 12 tabelas monitoradas e 194 checagens aprovadas.
  - Views de janela (`dq.v_*_janela`) e replay das 8 semanas.
  - Agendamento às 06:30, depois da carga; a tarefa `ligar_dqx_studio` liga o app.
  - A regra de cálculo foi espelhada no Studio (P20).
- **Por quê:**
  - O dry run usa as primeiras N linhas, e com amostra os incidentes de alguns dias somem.
  - O histórico de execuções serve de evidência para auditoria.
- **Reaplique quando:** é preciso histórico de qualidade, aprovação de regras e linhas reprovadas visíveis para o negócio.
- **Prova:** a janela 19–25/12 deu 44 violações da regra espelhada no bronze (incidente I03) e 0 na silver e na fato.

### P12 · Painel de qualidade gerado e testado por código
- **Origem:** [AI/BI dashboards](https://docs.databricks.com/aws/en/dashboards/) (Databricks).
- **Como aplicamos:**
  - 6 views `dq.v_painel_*`.
  - `gerar_painel.py` gera o JSON do painel.
  - `aplicar_e_testar.py` roda cada consulta como o AI/BI executa, mais 5 checagens de consistência.
- **Por quê:** o JSON gerado e conferido evita painel quebrado. As checagens pegam regressões que ninguém veria, como uma
  "semana 6" que não existia.
- **Reaplique quando:** há um painel que precisa sobreviver às mudanças do pipeline.
- **Prova:** `aplicar_e_testar.py` com todas as consultas respondendo e as 5 checagens de consistência passando (fase 6).

---

## Governança

### P13 · Toda coluna descrita, com auditoria
- **Origem:** [Comments](https://docs.databricks.com/aws/en/comments/) (Databricks); lições L32 e L53.
- **Como aplicamos:**
  - `governanca/descricoes_colunas.py` guarda uma descrição por nome de coluna, com exceções por tabela.
  - `aplicar_descricoes.py` grava as descrições.
  - `auditar_metadados.py` mede a cobertura por schema, em 28 s.
- **Por quê:** a Genie e as pessoas leem as descrições. Campo sem descrição confunde a IA: "CPF inválido" foi lido como
  dado pessoal, mas é uma contagem.
- **Reaplique quando:** sempre que houver IA ou autoatendimento sobre os dados.
- **Prova:** 1.977 de 1.977 colunas principais e 682 de 682 legadas descritas.

### P14 · Governed tags, domínio, Pages e Wikis
- **Origem:** [Governed tags](https://docs.databricks.com/aws/en/admin/governed-tags/) e
  [Discover](https://docs.databricks.com/aws/en/discover/) (Databricks).
- **Como aplicamos:**
  - `aplicar_semantica.py`, que é idempotente, grava:
    - o domínio Pós-venda, com 3 subdomínios;
    - as tags por camada, tipo e entidade;
    - a certificação;
    - 18 Pages de conceitos de negócio, cada uma com a seção "Como validar";
    - 51 Wikis de tabela.
  - Também grava as tags padrão `domain`, `subject_area` e `data_owner`.
- **Por quê:**
  - Contexto de negócio para pessoas e IA.
  - As Pages com "Como validar" viraram as perguntas de avaliação da Genie.
  - As tags padrão são as que as ferramentas de prontidão reconhecem.
- **Reaplique quando:** o domínio vai ser descoberto por outras pessoas ou avaliado por ferramentas.
- **Prova:** prontidão da ontologia foi de 81,3 para 90,5 só com as tags de domínio e responsável (fase 18).

### P15 · Dado pessoal marcado por tag (LGPD), sem máscara por decisão
- **Origem:** [Lei 13.709/2018 (LGPD)](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm);
  [Data classification](https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-classification)
  (Databricks); decisão do usuário (fase 17).
- **Como aplicamos:**
  - Na coluna, a tag `dado_pessoal`, com a categoria (identificação, contato, endereço, perfil ou sensível).
  - Na tabela, as tags `contem_dado_pessoal` e `contem_dado_sensivel`.
  - A marcação vale também para os schemas legados.
- **Por quê:**
  - As regras de qualidade (CPF válido, e-mail, CEP) precisam dos valores reais.
  - Marcar é sempre possível; mascarar depende do uso.
  - Quando mais gente tiver acesso, a proteção vem por grants ou por máscara com exceção para quem valida.
- **Reaplique quando:** sempre que houver dado pessoal. Avalie máscara (ABAC) antes de abrir a Genie a mais pessoas.
- **Prova:** 380 colunas principais e 152 legadas marcadas; 0 dado pessoal sem tag nos 13 schemas.

### P16 · Governança que sobrevive à recriação
- **Origem:** prática do projeto (L31, fase 14).
- **Como aplicamos:**
  - `carga_diaria/views_preservadas.py` (`garantir_view`) só recria a view quando a definição mudou.
  - Quando recria, devolve as descrições, as tags, as tags de coluna e a Wiki.
  - Depois de recriar uma metric view, rodamos `aplicar_semantica.py`.
- **Por quê:**
  - `CREATE OR REPLACE VIEW` apaga as tags e a Wiki.
  - Uma carga diária que desfaz a governança anula todo o resto.
- **Reaplique quando:** o job recria views ou metric views.
- **Prova:** `auditar_metadados.py` com 100% das colunas principais descritas (1.977/1.977) e 0 dado pessoal sem tag.

---

## Semântica

### P17 · Ontologia sem identificadores pessoais
- **Origem:** LGPD (P15); prática do projeto (fase 15).
- **Como aplicamos:**
  - O schema `pos_venda.ontologia` tem 10 entidades, as relações em triplas (sujeito, predicado, objeto) e o glossário.
  - As entidades se ligam por `cliente_sk`, nunca por `cliente_id`.
- **Por quê:** um código técnico também é dado pessoal quando leva à pessoa. A camada de negócio é a que mais circula.
- **Reaplique quando:** há uma camada semântica ou uma Genie sobre dado pessoal.
- **Prova:** nenhuma coluna `cliente_id` no schema `ontologia`; Genie 27/27 depois da troca.

### P18 · Metric views como fonte única das métricas
- **Origem:** [Metric views](https://docs.databricks.com/aws/en/metric-views/) (Databricks); princípio 2 do playbook.
- **Como aplicamos:**
  - 4 metric views: carteira em aberto, recuperação, safras e qualidade dos dados, geradas por `gerar_ontologia_sql.py`.
  - Os 87 campos estão descritos.
  - Os painéis, a Genie e o Power BI (pelo schema `bi`) leem as mesmas medidas.
- **Por quê:** a regra vive num lugar só, e o número bate entre as ferramentas.
- **Reaplique quando:** mais de um consumidor (painel, Genie, BI externo) usa a mesma métrica.
- **Prova:** painéis 14/14, Genie 29/29 e paridade Power BI 21/21, com os mesmos números (22/11). Na reconferência
  de 24/11, com os dados até 09/01/2027, a Genie deu 28/29 e a paridade 20/21. As duas diferenças vêm dos vazamentos
  da semana 7 (L86, L87); corrigidas no mesmo dia, voltaram a 29/29 e 21/21.

### P19 · Padrões semânticos: fechamento semiaditivo, mês anterior, acumulados e ranking
- **Origem:** [uc-semantics-patterns](https://github.com/databricks-solutions/uc-semantics-patterns)
  (databricks-solutions); [Window measures](https://docs.databricks.com/aws/en/metric-views/data-modeling/window-measures)
  (Databricks).
- **Como aplicamos:** as medidas de janela "Saldo de fechamento", "mês anterior", "variação mensal", "acumulado no mês e
  no ano" e "ranking" foram levadas aos painéis.
- **Por quê:** é o jeito nativo de fazer MoM, MTD e YTD sem SQL manual em cada consulta.
- **Reaplique quando:** o negócio pede comparação de períodos, ou a medida é semiaditiva.
- **Prova:** o saldo de fechamento no grão produto × canal bate com o total. A diferença de R$ 240,33 em dezembro
  (produto × canal × forma) vem de fatias que somem antes do fim do mês, e está explicada (fase 12).
- **Cuidado:**
  - O "último dia" é por fatia.
  - O ranking não vai na mesma consulta que as medidas de janela.
  - O `offset` exige o filtro na dimensão de mês.

### P20 · Regras de negócio como funções testadas por cenários (BDD)
- **Origem:** [agentic-bdd-uc-functions](https://github.com/databricks-solutions/agentic-bdd-uc-functions)
  (databricks-solutions); [funções do Unity Catalog](https://docs.databricks.com/aws/en/udf/unity-catalog) (Databricks);
  [Gherkin](https://cucumber.io/docs/gherkin/reference/) (Cucumber).
- **Como aplicamos:**
  - Schema `pos_venda.regras`, com 5 funções: faixa de atraso, multa, juros, total pendente e CPF válido.
  - 36 cenários em português e uma paridade linha a linha contra os dados gravados.
  - O portão `05_portao_regras` roda os cenários antes da carga.
  - A silver, a barreira, a gold, a Genie e o DQX Studio usam as mesmas funções.
- **Por quê:**
  - Escrever o cenário obriga a decidir o que o SQL deixava implícito: a parcela que vence hoje já paga multa?
  - A paridade prova que a função calcula igual antes de substituir o SQL antigo.
- **Reaplique quando:** a regra de cálculo tem impacto financeiro ou regulatório, ou aparece em mais de um lugar.
- **Prova:** 36/36 cenários e paridade 100% (29,9 milhões de linhas da gold, 0 divergência).

---

## Consumo

### P21 · Um espaço Genie por público, com instruções curtas, exemplos e benchmarks
- **Origem:** [Genie](https://docs.databricks.com/aws/en/genie/),
  [boas práticas](https://docs.databricks.com/aws/en/genie/best-practices) e
  [benchmarks](https://docs.databricks.com/aws/en/genie/benchmarks) (Databricks).
- **Como aplicamos:**
  - `governanca/genie.py` monta os espaços Analista e Diretor sobre as metric views.
  - Cada espaço tem instruções curtas sobre desambiguação, período e saldo semiaditivo, exemplos de SQL e perguntas de
    avaliação.
  - Antes de publicar, o script valida todo SQL no warehouse.
  - As funções de regra entram como ativos confiáveis.
- **Por quê:** instruções curtas e específicas resolvem mais que instruções longas. Comparar o resultado inteiro evita
  falso negativo.
- **Reaplique quando:** há públicos com perguntas diferentes sobre os mesmos dados.
- **Prova:** 29/29 perguntas de avaliação certas (21/11). Em 24/11, com os dados até 09/01/2027, 28/29: a que errou
  deixou de fora o saldo de produto órfão (L87). Com o membro "não identificado" na ontologia, voltou a 29/29.

### P22 · Painéis AI/BI por público, com uma página por fato
- **Origem:** [AI/BI dashboards](https://docs.databricks.com/aws/en/dashboards/) (Databricks); lição L66.
- **Como aplicamos:** `paineis_financeiros/gerar_paineis.py` gera os painéis Diretoria e Analista, com as páginas
  carteira, recuperação, safras e qualidade dos dados, e um link para a Genie de cada público.
- **Por quê:** uma página por fato atende cada público sem multiplicar painéis nem trocar de link.
- **Reaplique quando:** há mais de um fato e mais de um público.
- **Prova:** 14/14 datasets respondem; os dois painéis estão publicados.

### P23 · Segunda ferramenta de BI lendo extratos das metric views
- **Origem:**
  - [Power BI com Databricks](https://docs.databricks.com/aws/en/partners/bi/power-bi) (Databricks);
  - [projetos PBIP](https://learn.microsoft.com/power-bi/developer/projects/projects-overview) e
    [TMDL](https://learn.microsoft.com/analysis-services/tmdl/tmdl-overview) (Microsoft);
  - [power-bi-on-databricks-quickstarts](https://github.com/databricks-solutions/power-bi-on-databricks-quickstarts)
    (databricks-solutions).
- **Como aplicamos:**
  - O schema `pos_venda.bi` tem 8 visões agregadas a partir das metric views.
  - `gerar_powerbi.py` gera o projeto PBIP: o modelo TMDL, com 47 medidas e 12 relações, e os 2 relatórios PBIR.
  - Os arquivos são conferidos contra os esquemas oficiais.
- **Por quê:**
  - A regra continua no Databricks.
  - O DAX só cuida do que é do motor dele, como o saldo semiaditivo.
  - A comparação entre as ferramentas usa os mesmos números.
- **Reaplique quando:** a empresa tem outra ferramenta de BI, ou está avaliando uma.
- **Prova:** 102 arquivos válidos nos esquemas e paridade 21/21 (foto de 25/12). Na foto de 09/01/2027, deu 20/21 e
  voltou a 21/21 depois da correção do painel (L86).
  **Não verificado:** abrir no Power BI Desktop.

---

## Avaliação

### P24 · Avaliação independente com triagem por achado
- **Origem:** [genie-best-practices-agent](https://github.com/databricks-solutions/genie-best-practices-agent)
  (databricks-solutions); lição L41.
- **Como aplicamos:** rodamos em modo offline, com extrator próprio e `llama-4-maverick`. Cada achado recebeu um veredito
  em `governanca/genie/avaliacao_boas_praticas/TRIAGEM.md`.
- **Por quê:** relatório de IA traz achados genéricos e falsos positivos. Aplicar tudo sem triagem piora o espaço.
- **Reaplique quando:** sempre que usar uma ferramenta de avaliação por IA.
- **Prova:** o que procedia foi aplicado (descrição dos 87 campos, meses como `date`), e os falsos positivos ficaram
  registrados com o motivo.

### P25 · Prontidão da ontologia, com histórico das notas
- **Origem:** [genie-ontology-readiness](https://github.com/databricks-solutions/genie-ontology-readiness)
  (databricks-solutions), versão v1.5.0.
- **Como aplicamos:**
  - App instalado com a identidade do usuário.
  - Cada avaliação fica gravada no Lakebase (`avaliar.py`), para comparar antes e depois.
- **Por quê:** dá uma nota de fora para a camada semântica, por pilar, com as lacunas explicadas.
- **Reaplique quando:** a camada semântica vai servir à Genie.
- **Prova:** a nota foi de 81,3 para **92,7 (Optimized)**.

### P26 · Réguas externas sem instalar app
- **Origem:**
  - [genie-agent-scanner](https://github.com/databricks-solutions/technical-services-solutions/tree/main/genie/genie-agent-scanner),
    a régua de 12 itens do Genie Workbench;
  - [powerbi-analyzer](https://github.com/databricks-solutions/powerbi-analyzer) (`pba`), as 42 regras da cheat sheet
    Power BI on Databricks;
  - lições L71 e L73.
- **Como aplicamos:** as duas ferramentas só leem. A triagem de cada uma está em
  `governanca/genie/scanner/TRIAGEM.md` e `paineis_financeiros/powerbi/auditoria/README.md`.
- **Por quê:**
  - Dão uma nota sem gastar uma vaga de app.
  - Aprovação sem dado de entrada é "não avaliado": as regras do `pba` que dependem de visuais e de histórico do Power BI
    passaram em branco.
- **Reaplique quando:** há Genie ou Power BI sobre Databricks.
- **Prova:**
  - Genie: 8/12; o teto sem o Workbench é 10/12.
  - `pba`: modelo 80/100 e lado Databricks 75/100, com a triagem por regra.

### P27 · Catálogo de aceleradores revisto a cada fase
- **Origem:** organização [databricks-solutions](https://github.com/databricks-solutions); prática do projeto (L69).
- **Como aplicamos:**
  - Os 147 repositórios estão catalogados em `referencias/databricks_solutions/`.
  - Cada um tem a situação no projeto: aplicado, proposto ou adiado, com o motivo.
  - A revisão de 22/11 gerou 7 propostas, das quais 3 já foram aplicadas.
  - Desde 23/11, um guia escrito para LLM transforma o catálogo em opções ranqueadas (seção
    [Opções databricks-solutions](#opções-databricks-solutions-qual-acelerador-usar-a-seguir)).
- **Por quê:** o catálogo envelhece pelo lado do projeto. A opção Power BI levou o `powerbi-analyzer` de relevância baixa
  para alta.
- **Reaplique quando:** a cada fase nova do projeto.
- **Prova:** catálogo com 7 aplicados, 2 propostos e 6 adiados.

---

## Operação contínua

### P28 · Matriz de resiliência
- **Origem:** prática do projeto (princípio 7 do playbook).
- **Como aplicamos:** a [matriz de resiliência](02_PLAYBOOK.md#matriz-de-resiliência) tem 20 falhas, cada uma com o
  sintoma e a resposta. Exemplos: cota esgotada, token expirado, Lakebase desligado, app parado, recriação de view, dia
  novo carregado.
- **Por quê:** no Free Edition, as falhas são rotina. Ter a resposta escrita encurta a recuperação.
- **Reaplique quando:** sempre.
- **Prova:** as respostas foram usadas de verdade ao longo do projeto: cota esgotada, Lakebase desligado, app parado,
  dia novo carregado.

### P29 · Documentação incremental, junto com o código
- **Origem:** prática do projeto (princípio 8 do playbook).
- **Como aplicamos:** a cada mudança atualizamos o CHANGELOG (com a conferência), a trilha, o playbook, as lições, o
  inventário (gerado por script), este framework e o README.
- **Por quê:** quem chega depois entende o porquê de cada escolha. Uma mudança só está pronta quando a conferência está
  registrada.
- **Reaplique quando:** sempre.
- **Prova:** 28 fases (0 a 27), 92 lições, inventário regenerado a cada mudança.

---

## Custo e uso (FinOps)

### P30 · Base de custo no padrão FOCUS, a partir das tabelas de sistema
- **Origem:** [FinOps FOCUS 1.4](https://focus.finops.org/what-is-focus/) ([especificação](https://github.com/FinOps-Open-Cost-and-Usage-Spec/FOCUS_Spec));
  [cloud-infra-costs](https://github.com/databricks-solutions/cloud-infra-costs) (databricks-solutions, `focus_query_1_4.sql`);
  [tabelas de sistema de billing](https://docs.databricks.com/aws/en/admin/system-tables/billing) (Databricks).
- **Como aplicamos:**
  - `pos_venda.finops.focus_custo_uso` tem as 65 colunas da FOCUS 1.4, mais colunas `x_` para projeto, time,
    funcionalidade e custo em BRL.
  - `custo_por_funcionalidade` agrega por mês e funcionalidade do Databricks.
  - Tudo é gerado por `finops/gerar_finops.py`.
- **Por quê:** a FOCUS é uma linguagem comum de custo, comparável entre nuvens e ferramentas. A base escolhe os campos
  um a um, porque o framework anterior quebrou quando a tabela de sistema ganhou campos (L76).
- **Reaplique quando:** alguém precisa saber quanto custa o quê. No Free Edition, a medida é o custo a preço de lista; o
  `BilledCost` é 0, porque não há fatura.
- **Prova:** 27.613 linhas = billing; US$ 1.217,11 = uso × preço de lista; 0 linha com `ServiceCategory` fora da
  especificação.

### P31 · Todo custo com dono: tag, regra, rateio por consulta
- **Origem:**
  - prática CO-03-01 (tags) do pilar de custo do Well-Architected da Databricks
    ([databricks-waf](https://github.com/databricks-solutions/databricks-waf));
  - rateio do warehouse pelo tempo de cada consulta, do
    [dbx-adoption-monitor](https://github.com/databricks-solutions/dbx-adoption-monitor);
  - lição L77.
- **Como aplicamos:**
  - A ordem de atribuição é: tag `project` do recurso, depois as regras pelo nome (`REGRAS` em `gerar_finops.py`).
  - O warehouse é rateado por consulta. Cada consulta vai para o dono da sua origem: espaço Genie, painel, job ou o
    catálogo que cita.
  - Sobra o "não atribuído".
- **Por quê:** sem dono, o custo não entra em nenhum showback. Num workspace compartilhado, o warehouse é o grosso da
  conta.
- **Reaplique quando:** mais de um time usa o mesmo workspace.
- **Prova:** o não atribuído caiu de 80% para 10,3% depois que a consulta sem origem nomeada passou a ser classificada
  pelo texto. O que sobrou são US$ 92 de projetos Lakebase removidos.

### P32 · Uma visão por público: plataforma e squad
- **Origem:** prática CO-03-03 e CO-03-04 do Well-Architected da Databricks (monitorar e gerir custo); prática do projeto.
- **Como aplicamos:**
  - `plataforma_*` para o time de plataforma: custo diário com anomalia, cobertura de atribuição, top recursos e
    warehouses.
  - `squad_*` para o squad: custo mensal, custo unitário e uso.
  - `mv_finops_custo` para a Genie e os painéis.
- **Por quê:** a plataforma pergunta "onde está o desperdício"; o squad pergunta "quanto custa o meu produto por
  unidade entregue".
- **Reaplique quando:** há um time de plataforma e squads produto.
- **Prova:** a plataforma leva 77,1% do custo (jobs de monitoramento); o pós-venda leva 5,3%, a US$ 0,0063 por consulta
  e US$ 0,09 por execução de job em novembro.

### P33 · Uso medido separando pessoas de automação
- **Origem:** [dbx-adoption-monitor](https://github.com/databricks-solutions/dbx-adoption-monitor) (alcance e
  profundidade da Genie, painel publicado × rascunho); [audit logs](https://docs.databricks.com/aws/en/admin/system-tables/audit-logs)
  (Databricks); lição L78.
- **Como aplicamos:**
  - `uso_genie_diario` separa a UI (pessoas) da API (automação e avaliações).
  - `uso_paineis_diario` separa a versão publicada do rascunho.
  - `uso_consultas_diario` mostra a origem de cada consulta.
  - `uso_jobs_diario` mostra o custo das execuções com falha.
- **Por quê:** avaliações automáticas e edição inflam o uso. A adoção real é a UI e o painel publicado.
- **Reaplique quando:** alguém vai medir a adoção de Genie ou de painéis.
- **Prova:** das 249 perguntas de novembro aos espaços do pós-venda, todas vieram da API; a adoção por pessoas foi zero.

### P34 · Boas práticas de custo medidas, com meta
- **Origem:**
  - pilar de custo do Well-Architected da Databricks, práticas CO-01 a CO-04
    ([databricks-waf](https://github.com/databricks-solutions/databricks-waf),
    [boas práticas](https://docs.databricks.com/aws/en/lakehouse-architecture/cost-optimization/best-practices));
  - SS-005 do [powerbi-analyzer](https://github.com/databricks-solutions/powerbi-analyzer);
  - dbx-adoption-monitor;
  - FOCUS.
- **Como aplicamos:** `boas_praticas_custo` mede 15 práticas nos últimos 30 dias, cada uma com métrica, meta, situação,
  leitura e recomendação.
- **Por quê:** a régua vira número que se acompanha, em vez de lista de conselhos.
- **Reaplique quando:** há uma revisão de custo periódica.
- **Prova:** 11 práticas atendem e 4 pedem atenção:
  - tags cobrem 22,4% do custo;
  - nenhum consumo serverless tem budget policy;
  - o armazenamento cresceu 506% em 30 dias;
  - 64,5% das aberturas de painel foram no rascunho.

---

## Conformidade e observabilidade

### P35 · Conformidade medida por regra, com meta, origem e correção
- **Origem:**
  - documentação Databricks: [comentários](https://docs.databricks.com/aws/en/comments/),
    [governed tags](https://docs.databricks.com/aws/en/admin/governed-tags/),
    [data classification](https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-classification),
    [constraints](https://docs.databricks.com/aws/en/tables/constraints),
    [boas práticas do Unity Catalog](https://docs.databricks.com/aws/en/data-governance/unity-catalog/best-practices),
    [lineage](https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-lineage) e
    [Predictive Optimization](https://docs.databricks.com/aws/en/optimizations/predictive-optimization);
  - Well-Architected da Databricks
    ([governança](https://docs.databricks.com/aws/en/lakehouse-architecture/data-governance/best-practices) e custo);
  - LGPD;
  - as checagens do bundle `observabilidade-framework` (`policy_compliance_monitoring`, `materializa_dados_observabilidade`);
  - as práticas P08 e P13 a P16 deste framework.
- **Como aplicamos:** o schema `pos_venda.conformidade`, gerado por `conformidade/gerar_conformidade.py`, tem:
  - 28 regras em 7 dimensões (documentação, tags governadas, LGPD, confiança e estrutura, atualização e uso,
    otimização, plataforma), cada uma com meta, severidade, origem, link e como corrigir (`config_regras`);
  - uma linha por verificação (`achados`), a lista de correções (`pendencias`) e a situação de cada regra
    (`boas_praticas_dados`);
  - uma visão por público (`squad_por_schema`, `plataforma_por_catalogo`) e a metric view `mv_conformidade`.

  As tabelas internas do Lakeflow (`__materialization_*`, `event_log_*`) ficam fora das regras (L80).
- **Por quê:** a governança aplicada uma vez (P13 a P16) se desfaz sem aviso. A view recriada perde as tags, a tabela
  nova chega sem descrição e o job novo sobe sem tag.
- **Reaplique quando:** as regras de governança precisam continuar valendo depois da primeira aplicação, ou mais de
  um time publica no mesmo catálogo.
- **Prova:** 8.992 verificações em 23/11/2026; 13 regras atendem, 12 pedem atenção e 3 são críticas.
  - Dado pessoal (5 regras), colunas descritas e valores de tag governada estão em 100%.
  - Pendências reais:
    - 17 ativos principais sem `subject_area`;
    - 56 ativos sem descrição fora do `pos_venda`;
    - 10 de 11 jobs sem timeout;
    - 5 jobs sem as tags `project` e `team`.

### P36 · Observabilidade herdada avaliada antes de copiar
- **Origem:** o bundle `observabilidade-framework` e o framework FinOps anterior (`finops.observability`), que já
  rodavam no workspace; a revisão de catálogo da P27.
- **Como aplicamos:**
  - inventário de jobs, alertas SQL e visões;
  - para cada ação: o que faz, o que encontramos, execuções e custo em 30 dias e um veredito (internalizar, manter,
    consertar, aposentar ou só leitura).

  Está em `acoes_observabilidade` e em
  [AVALIACAO_OBSERVABILIDADE.md](../conformidade/AVALIACAO_OBSERVABILIDADE.md). Nada do bundle foi alterado: as
  recomendações ficam com o dono.
- **Por quê:**
  - checagem escrita para clusters clássicos volta vazia no Free Edition e parece "tudo certo" (L81);
  - o alerta mais simples de escrever pode ser o mais caro de rodar (L79).
- **Reaplique quando:** o workspace já tem monitoramento de outra pessoa ou de outro projeto.
- **Prova:** 8 ações:
  - 3 internalizadas;
  - 2 mantidas;
  - 1 a consertar: os alertas. Custaram US$ 816,20 desde julho; só o alerta horário, US$ 29,73 em 7 dias;
  - 1 a aposentar: o rightsizing, que falha em toda execução;
  - 1 só leitura.

### P37 · Sonda diária das views e histórico; regra sem dado é "sem dados"
- **Origem:** L71 (auditoria sem dado de entrada aprova em branco), L76 (views quebradas por mudança na tabela de
  sistema) e P28.
- **Como aplicamos:**
  - `gerar_conformidade.py registrar` testa cada view, metric view e materialized view do workspace com
    `DESCRIBE QUERY`, que analisa a view sem executá-la, e grava `sonda_views`;
  - depois, grava em `historico` a situação de cada regra no dia;
  - `conferir` reprova se alguma regra não verificou nenhum objeto, e confere que as contagens fecham (inventário =
    `information_schema`; pendências = não conformes = metric view);
  - desde 26/11, o job `pos_venda_conformidade_sonda` faz o `registrar` todo dia às 06:45, num notebook com
    `spark.sql` (`conformidade/src/sonda_diaria.py`); falha de rede não vira view quebrada (L94).
- **Por quê:** a view quebrada não avisa ninguém, e sem histórico não se vê a conformidade cair.
- **Reaplique quando:** há views sobre tabelas de sistema ou sobre schemas de outro time.
- **Prova:**
  - em 23/11, 140 views sondadas; 22 não respondem, todas pela mesma causa (L76): 19 em `finops.observability` e 3
    cópias em `workspace.default`;
  - em 26/11, a primeira execução do job (SUCCESS, 7,6 min) sondou 170 views, com as mesmas 22 quebradas, e gravou as
    28 regras no histórico.

---

## Reaplicação em outra base

### P38 · DQX em duas trilhas: biblioteca num job ou Studio como app, escolhidas pela permissão
- **Origem:**
  - a [instalação do DQX](https://databrickslabs.github.io/dqx/docs/installation/): a biblioteca dispensa instalação
    no workspace;
  - os requisitos do Studio: um service principal com `USE CATALOG` e `CREATE SCHEMA` no catálogo, Lakebase e
    warehouse;
  - a instalação no pos_venda (`dqx_studio/README.md`, L02);
  - o pedido de reaplicar numa base cujo catálogo não é seu.
- **Como aplicamos:**
  - **Trilha B, o Studio como app:** é a que roda no pos_venda (P11, P12).
  - **Trilha A, o DQX como código:** fica em [`dqx_codigo/`](../dqx_codigo/README.md). Lá estão:
    - as 11 regras de erro da barreira em YAML, com os mesmos nomes, e 3 avisos;
    - um notebook que separa válidos e quarentena e grava as métricas por regra;
    - um bundle com o job sob demanda.
  - **Escolha:** o [guia 06](06_GUIA_BASE_BRUTA.md) escolhe a trilha na etapa 0, pelas permissões.
- **Por quê:** o app pede privilégios no catálogo que nem todo time pode conceder. Sem uma trilha alternativa, a
  segunda linha de defesa da qualidade simplesmente não existe.
- **Reaplique quando:**
  - você não é dono do catálogo nem tem `MANAGE` nele;
  - não há vaga de app;
  - o time quer as regras versionadas em Git.
- **Prova:**
  - `databricks bundle validate` passa;
  - as 11 regras de erro têm o mesmo nome do motivo da barreira;
  - executado em 24/11 na janela de 26/12 a 01/01 (49.972 eventos): 3.229 linhas em quarentena, o mesmo número da
    barreira; 46.743 válidas; as 14 regras em `dq_metricas_regras`, inclusive as que deram zero;
  - as 3 tabelas novas saem com 100% das colunas descritas e a tag `dado_pessoal` copiada da bronze (25 colunas);
  - a primeira execução falhou no `is_in_list` (L88).

---

### P39 · Guia executável por agente de código para aplicar em outra base
- **Origem:**
  - as [instruções de repositório do GitHub Copilot](https://docs.github.com/en/copilot/customizing-copilot/adding-repository-custom-instructions-for-github-copilot);
  - os [arquivos de prompt do VS Code](https://code.visualstudio.com/docs/copilot/customization/prompt-files);
  - a convenção `AGENTS.md`;
  - P29 (documentação junto com o código).
- **Como aplicamos:**
  - **Guia:** [`06_GUIA_BASE_BRUTA.md`](06_GUIA_BASE_BRUTA.md) tem as etapas 0 a 8. Cada etapa tem módulo, práticas,
    skill e critério de saída. O guia traz também a ficha da base, o mapeamento para o modelo e a tabela "o que muda
    quando o cenário é diferente".
  - **Instruções do Copilot:** `.github/copilot-instructions.md` aponta para o AGENTS.md e para o guia.
  - **Spec:** [`specs/aplicar-base-bruta/SPEC.md`](../specs/aplicar-base-bruta/SPEC.md) é o contrato que o agente
    executa. Traz objetivo, escopo, entradas e saídas, as restrições R1 a R8, os critérios de aceite por etapa e os
    gates G1 a G9. Os modelos de tarefas, ficha, mapeamento e decisões são copiados para `specs/<nome-da-base>/`, que
    guarda o progresso e permite retomar.
  - **Prompt:** `.github/prompts/aplicar-base-bruta.prompt.md` segue o spec tarefa por tarefa. Até cada aprovação, só
    roda leitura.
- **Por quê:** o que o projeto aprendeu precisa sair do histórico e virar passos que outro agente siga. Assim ele não
  reinventa o que já foi resolvido e não gasta cota sem pedir. O guia explica, e o spec torna verificável: cada tarefa
  tem um comando que prova que terminou, e o agente não decide sozinho que acabou.
- **Reaplique quando:** o framework vai ser aplicado por outra pessoa ou por um agente, em outra base ou workspace.
- **Prova:**
  - os links do guia resolvem;
  - o guia cobre os 12 módulos e as duas trilhas de qualidade;
  - o spec tem 41 tarefas (com a etapa E8, de sustentação), cada uma com verificação, e 9 gates de aprovação.
  - Ainda não foi testado com o Copilot numa base real (24/11).

---

## Sustentação em produção

### P40 · Tempo de execução com linha de base, desvio, SLA e volume, a partir das tabelas de sistema
- **Origem:**
  - as tabelas de sistema de jobs e pipelines ([jobs](https://docs.databricks.com/aws/en/admin/system-tables/jobs):
    `job_run_timeline`, `job_task_run_timeline`, `pipeline_update_timeline`);
  - os [alertas SQL](https://docs.databricks.com/aws/en/sql/user/alerts/);
  - a pergunta do dono sobre a sustentação em produção. Até então, só havia a duração média por job e dia, as falhas
    e o custo, em `pos_venda.finops.uso_jobs_diario`;
  - P28 (matriz de resiliência), P02 (agendas pausadas) e a regra PLT06 (até 4 disparos por dia).
- **Como aplicamos:** o schema `pos_venda.sustentacao`, gerado por
  [`sustentacao/gerar_sustentacao.py`](../sustentacao/README.md), tem 14 visões:
  - **Execuções.** Por job, por tarefa e por update do pipeline. As fatias de hora em hora são juntadas por `run_id`
    (L90), com o setup separado da execução (L89).
  - **Linha de base.** Mediana e p95 das últimas 20 execuções com sucesso, com o mínimo de 5 para valer.
  - **Desvios.** Execução acima do p95 ou de 1,5 vez a mediana das 20 anteriores, com o excesso e a causa provável:
    espera por computação, volume maior ou lentidão com o mesmo volume.
  - **SLA.** Só a execução da agenda conta, e a meta é 06:15, antes do DQX Studio às 06:30. Com a agenda pausada, a
    página mostra a folga projetada (L91).
  - **Volume.** Eventos do bronze e linhas da fato por execução, ligados pelo momento da gravação.
  - **Matriz por tarefa.** Sintoma e ação na falha e na lentidão, ligados à matriz do playbook (P28).

  Junto vão um painel AI/BI gerado por código (página "Sustentação") e um alerta SQL diário, às 06:20 e pausado. A
  atribuição dos jobs ao projeto vem da FinOps; o custo continua em `uso_jobs_diario`; frescor e timeout continuam na
  conformidade (USO01, PLT03). O [manual de sustentação](07_SUSTENTACAO.md) usa essas visões na rotina diária,
  semanal e mensal, nos runbooks, no RACI e nos indicadores.
- **Por quê:** a média diária esconde a tarefa que ficou lenta e mistura backfill com carga de um dia. Sem linha de
  base, não há como dizer o que é "lento". Sem SLA, ninguém sabe se a foto do dia chega antes de quem a usa.
- **Reaplique quando:** um job diário tem consumidores com hora marcada (avaliação de qualidade, painel, extrato), ou
  quando alguém precisa responder "por que a carga demorou hoje?".
- **Prova:**
  - **`conferir`:** 13 checagens ok. As execuções e os updates batem com as tabelas de sistema (186, 249 e 13); o
    volume por execução soma o bronze (1.718.895) e a fato (34.026.469); as medianas são iguais ao cálculo direto.
  - **Carga:** mediana de 14,53 min, p95 de 16,05 min e folga projetada de 59,0 min até 06:15. São provisórios: 12
    execuções manuais com as agendas pausadas.
  - **Volume:** a duração não acompanha o volume. 184 dias levaram 14,5 min, e 1 dia, cerca de 14 (L89).
  - **Implantação:** o painel está publicado e o alerta está pausado.
  - **Alerta:** com o piso (L92), avisaria 2 casos reais em 30 dias, em vez de ruído.

---

## Regras com vigência e retroalimentação

### P41 · Regra de qualidade com versão e vigência pela data do dado, questionário do negócio e triagem
- **Origem:**
  - o pedido do dono: questionários para o negócio criar regras e uma retroalimentação de qualidade, lembrando que
    regras mudam com o tempo e só valem para certo período;
  - a [definição de checagens do DQX](https://databrickslabs.github.io/dqx/docs/guide/quality_checks_definition/),
    que aceita `filter` e `user_metadata` por checagem;
  - SCD tipo 2, a mesma ideia de vigência da `silver.pendencia_hist`;
  - P09 (nome estável da regra), P20 (regras em BDD) e L84 (zero também aparece).
- **Como aplicamos:**
  - **Catálogo.** [`regras/catalogo/catalogo_regras.yml`](../regras/catalogo/README.md) tem as 14 regras (11 da
    barreira e 3 avisos). Cada regra tem versões com `vigente_de` (inclusive) e `vigente_ate` (exclusive) pela data
    do dado, além de dono, limite de taxa aceita, motivo, origem e aprovação.
  - **DQX.** O YAML do DQX como código passou a ser gerado do catálogo. Cada versão vira uma checagem com o mesmo nome,
    um `filter` pela data do dado e a versão no `user_metadata`. As métricas do DQX ganharam a coluna `versao`.
  - **Objetos em `pos_venda.regras`:**
    - `catalogo_regras` e `triagem_regras`, esta com `CHECK` nas 4 classificações;
    - a função `versao_vigente(regra, dia)`;
    - as visões `v_falhas_regras`, `v_triagem_pendente`, `v_mudancas_regras` e `v_retroalimentacao`.
  - **Questionário.** [`regras/questionario/QUESTIONARIO_NEGOCIO.md`](../regras/questionario/QUESTIONARIO_NEGOCIO.md) tem
    5 blocos: dado certo, quanto erro é aceitável, perguntas aos números, vigência e retroalimentação. Cada pergunta diz
    o campo do catálogo que preenche.
  - **Rito.** Triagem semanal, revisão mensal do falso positivo e questionário a cada trimestre.
  - **Garantias.** O `validar` recusa buraco ou sobreposição de versões, versão nova sem motivo e regra de erro
    diferente da barreira. Os 8 cenários BDD do catálogo rodam fora do portão da carga.
- **Por quê:**
  - Sem vigência, a regra nova julga o dado antigo: o passado "falha" e o painel dá um salto que ninguém explica.
  - Sem triagem, a falha vira número e não volta para a regra. Ninguém separa "dado ruim" de "regra errada", e o
    falso positivo nunca cai.
- **Reaplique quando:** o negócio muda um domínio aceito, um cálculo ou um limite; ou quando as falhas de qualidade
  se acumulam sem dono nem decisão.
- **Prova (26/11/2026):**
  - **Testes do gerador:** os 17 testes sem rede passam. O YAML de produção tem as mesmas 14 checagens de antes, só
    com o `user_metadata` a mais.
  - **`conferir`:** as 11 checagens passam.
    - A tabela é igual ao YAML (14 versões).
    - Cada regra tem uma versão em cada um dos 236 dias da base.
    - As falhas da barreira na visão são as linhas da quarentena (6.712).
    - As linhas do DQX são válidos mais quarentena (49.972).
  - **BDD do catálogo:** 8 de 8 cenários.
  - **Ensaio fictício de vigência:** `QUINZENAL` aceita a partir de 05/01/2027.
    - Na janela de 14 dias, o DQX bateu com o SQL nas 15 checagens.
    - A versão 1 reprovou 105 eventos (`QUINZENAL` + `BIMESTRAL` até 04/01).
    - A versão 2 reprovou 68 (só `BIMESTRAL`, a partir de 05/01).
    - Os eventos com erro foram 3.388, igual à quarentena da barreira (L95).
  - **Triagem:** a primeira leitura achou 69 semanas × regra para triar e 7 perguntas em aberto para o dono.

---

## Opções databricks-solutions: qual acelerador usar a seguir

Os 147 repositórios públicos da organização [databricks-solutions](https://github.com/databricks-solutions) estão
num guia escrito para que uma LLM, ou uma pessoa, escolha a melhor opção para o projeto:
[OPCOES_PARA_LLM.md](../referencias/databricks_solutions/OPCOES_PARA_LLM.md) e a versão estruturada
[opcoes.json](../referencias/databricks_solutions/opcoes.json).

Para cada repositório, o guia diz:
- o que é;
- como ajudaria no pos_venda;
- quando escolher e como usar;
- a relevância para o projeto;
- se cabe no Free Edition, e com qual ressalva;
- a camada e as práticas deste framework que ele reforça;
- a situação no projeto, com o motivo;
- uma recomendação e uma prioridade.

O guia também traz o contexto do projeto (vagas de app, Lakebase, modelos disponíveis) e 9 regras de escolha.
`gerar_opcoes.py` gera os dois arquivos a partir de `catalogo.py`, que segue como a fonte única.

| Recomendação | Opções | Camada |
|---|---|---|
| Aplicar a seguir (2) | `regulatory_data_governance` (só os padrões: dimensão de qualidade nas regras e linhagem externa), `dbx-adoption-monitor` (metric views de uso dos painéis e da Genie) | Qualidade e Governança; Avaliação |
| Candidato (5) | `ai-dev-kit`, `aibi-dashboard-wanderbricks`, `caspers`, `databricks-aibi-design-first-accelerator`, `databricks-forge` | Fundação; Consumo; Dados e Qualidade; Semântica; Governança |
| Já aplicado (7) | `powerbi-analyzer`, `uc-semantics-patterns`, `genie-best-practices-agent`, `genie-ontology-readiness`, `technical-services-solutions` (genie-agent-scanner), `agentic-bdd-uc-functions`, `power-bi-on-databricks-quickstarts` | P08, P19, P20, P23 a P26 |
| Adiado, com motivo (10) | `databricks-dab-examples`, `databricks-genie-workbench`, `uc-declarative-abac`, `genierails`, `data-classification-review-app`, `databricks-waf`, `lakeflow_framework`, `ingestion-workbench`, `mlops-quickstart`, `advance-document-processing` | várias |
| Só se a necessidade mudar (69) · fora do escopo (37) · não roda no Free Edition (17) | listadas no guia, com o motivo | — |

**Como pedir a uma LLM:** entregue o guia e descreva a necessidade, por exemplo: "quero medir o uso da Genie e dos
painéis; qual opção databricks-solutions usar no pos_venda?". As regras levam à resposta. Neste exemplo, a escolha é
`dbx-adoption-monitor`: está em *Aplicar a seguir*, cabe no Free Edition e não ocupa vaga de app. O
`databricks-genie-workbench` fica de fora, porque gastaria a última vaga de app.

---

## Fontes

**Databricks (documentação oficial)**
- [Free Edition limitations](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations) (P01)
- [Declarative Automation Bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/) (P02)
- [Medallion architecture](https://docs.databricks.com/aws/en/lakehouse/medallion) (P05)
- [Lakeflow Declarative Pipelines](https://docs.databricks.com/aws/en/ldp/) (P06)
- [AUTO CDC](https://docs.databricks.com/aws/en/ldp/cdc) (P06)
- [Expectations](https://docs.databricks.com/aws/en/ldp/expectations) (P09)
- [Liquid clustering](https://docs.databricks.com/aws/en/delta/clustering) (P07)
- [Constraints](https://docs.databricks.com/aws/en/tables/constraints) (P08)
- [Query optimization with RELY](https://docs.databricks.com/aws/en/sql/user/queries/query-optimization-constraints) (P08)
- [Comments](https://docs.databricks.com/aws/en/comments/) (P13)
- [Governed tags](https://docs.databricks.com/aws/en/admin/governed-tags/) (P14)
- [Discover](https://docs.databricks.com/aws/en/discover/) (P14)
- [Data classification](https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-classification) (P15)
- [Metric views](https://docs.databricks.com/aws/en/metric-views/) (P18)
- [Window measures](https://docs.databricks.com/aws/en/metric-views/data-modeling/window-measures) (P19)
- [Funções do Unity Catalog](https://docs.databricks.com/aws/en/udf/unity-catalog) (P20)
- [Genie](https://docs.databricks.com/aws/en/genie/) (P21)
- [Genie: boas práticas](https://docs.databricks.com/aws/en/genie/best-practices) (P21)
- [Genie: benchmarks](https://docs.databricks.com/aws/en/genie/benchmarks) (P21)
- [AI/BI dashboards](https://docs.databricks.com/aws/en/dashboards/) (P12, P22)
- [Power BI](https://docs.databricks.com/aws/en/partners/bi/power-bi) (P23)
- [Databricks Apps](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/) (P11, P25)
- [Lakebase](https://docs.databricks.com/aws/en/oltp/) (P11, P25)
- [System tables](https://docs.databricks.com/aws/en/admin/system-tables/) (P25, P26)

**databricks-solutions (aceleradores)**
- [uc-semantics-patterns](https://github.com/databricks-solutions/uc-semantics-patterns) (P19)
- [agentic-bdd-uc-functions](https://github.com/databricks-solutions/agentic-bdd-uc-functions) (P20)
- [genie-best-practices-agent](https://github.com/databricks-solutions/genie-best-practices-agent) (P24)
- [genie-ontology-readiness](https://github.com/databricks-solutions/genie-ontology-readiness) (P25)
- [genie-agent-scanner](https://github.com/databricks-solutions/technical-services-solutions/tree/main/genie/genie-agent-scanner) (P26)
- [powerbi-analyzer](https://github.com/databricks-solutions/powerbi-analyzer) (P08, P26)
- [power-bi-on-databricks-quickstarts](https://github.com/databricks-solutions/power-bi-on-databricks-quickstarts) (P23)

**Databricks Labs**
- [dbldatagen](https://github.com/databrickslabs/dbldatagen) (P04)
- [DQX](https://github.com/databrickslabs/dqx), com a [documentação](https://databrickslabs.github.io/dqx/) (P11)

**Microsoft**
- [Projetos do Power BI Desktop (PBIP)](https://learn.microsoft.com/power-bi/developer/projects/projects-overview) (P23)
- [TMDL](https://learn.microsoft.com/analysis-services/tmdl/tmdl-overview) (P23)

**Modelagem, testes e legislação**
- Kimball: [Periodic snapshot fact table](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/periodic-snapshot-fact-table/) (P07)
- Kimball: [Additive, semi-additive, non-additive facts](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/additive-semi-additive-non-additive-fact/) (P07)
- [Gherkin](https://cucumber.io/docs/gherkin/reference/) (P20)
- [Lei 13.709/2018 (LGPD)](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm) (P15, P17)

**FinOps e custo**
- [FOCUS](https://focus.finops.org/what-is-focus/) e a [especificação FOCUS 1.4](https://github.com/FinOps-Open-Cost-and-Usage-Spec/FOCUS_Spec) (P30)
- [cloud-infra-costs](https://github.com/databricks-solutions/cloud-infra-costs) (P30)
- [dbx-adoption-monitor](https://github.com/databricks-solutions/dbx-adoption-monitor) (P31, P33)
- [databricks-waf](https://github.com/databricks-solutions/databricks-waf) e as [boas práticas de custo](https://docs.databricks.com/aws/en/lakehouse-architecture/cost-optimization/best-practices) (P31, P32, P34)
- [Billing system tables](https://docs.databricks.com/aws/en/admin/system-tables/billing), [query history](https://docs.databricks.com/aws/en/admin/system-tables/query-history), [audit logs](https://docs.databricks.com/aws/en/admin/system-tables/audit-logs) e [budget policies](https://docs.databricks.com/aws/en/admin/usage/budget-policies) (P30 a P34)

**Conformidade e observabilidade**
- [Boas práticas do Unity Catalog](https://docs.databricks.com/aws/en/data-governance/unity-catalog/best-practices) e [boas práticas de governança do Well-Architected](https://docs.databricks.com/aws/en/lakehouse-architecture/data-governance/best-practices) (P35)
- [Data lineage](https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-lineage) e a [tabela de sistema de lineage](https://docs.databricks.com/aws/en/admin/system-tables/lineage) (P35)
- [Predictive Optimization](https://docs.databricks.com/aws/en/optimizations/predictive-optimization) (P35)
- [Configurações de job](https://docs.databricks.com/aws/en/jobs/settings) e a [tabela de sistema de jobs](https://docs.databricks.com/aws/en/admin/system-tables/jobs) (P35)
- [SQL warehouses](https://docs.databricks.com/aws/en/compute/sql-warehouse/create) e [alertas SQL](https://docs.databricks.com/aws/en/sql/user/alerts/) (P35, P36)
- [Query history](https://docs.databricks.com/aws/en/admin/system-tables/query-history) (`query_source.alert_id`) (P36)

**Reaplicação em outra base**
- DQX: [instalação](https://databrickslabs.github.io/dqx/docs/installation/), [definição de checagens](https://databrickslabs.github.io/dqx/docs/guide/quality_checks_definition/), [aplicação](https://databrickslabs.github.io/dqx/docs/guide/quality_checks_apply/) e o [pacote no PyPI](https://pypi.org/project/databricks-labs-dqx/) (P38)
- GitHub Copilot: [instruções de repositório](https://docs.github.com/en/copilot/customizing-copilot/adding-repository-custom-instructions-for-github-copilot) e [arquivos de prompt do VS Code](https://code.visualstudio.com/docs/copilot/customization/prompt-files) (P39)

**Sustentação em produção**
- [Tabelas de sistema de jobs](https://docs.databricks.com/aws/en/admin/system-tables/jobs) (`job_run_timeline`, `job_task_run_timeline`, `pipeline_update_timeline`) e [alertas SQL](https://docs.databricks.com/aws/en/sql/user/alerts/) (P40)

**Do próprio projeto:** [trilha](01_TRILHA_DE_APRENDIZAGEM.md), [playbook](02_PLAYBOOK.md),
[lições](03_LICOES_APRENDIDAS.md), [CHANGELOG](CHANGELOG.md) e
[catálogo databricks-solutions](../referencias/databricks_solutions/CATALOGO.md).
