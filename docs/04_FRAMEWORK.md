# Framework · práticas aplicadas no pos_venda, de onde vieram e por quê

> Documento incremental. Última atualização: **22/11/2026**. Cada prática tem um código (`P##`) que não muda.
> Fontes conferidas em 22/11/2026 (todos os links responderam).

Este framework reúne as **29 práticas** aplicadas no domínio pós-venda de seguro de vida (fases 0 a 22 da
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
| [Playbook](02_PLAYBOOK.md) | o **passo a passo**: perfil da base, módulos M1 a M10 com critério de saída, matriz de resiliência, roteiro de reconstrução |
| [Lições aprendidas](03_LICOES_APRENDIDAS.md) | as **armadilhas**, com o código `L##` |
| Este framework | o **porquê de cada escolha** e a fonte de cada uma |

```
 Fundação ─► Dados ─► Qualidade ─► Governança ─► Semântica ─► Consumo ─► Avaliação
 (P01–P03)  (P04–P08) (P09–P12)    (P13–P16)     (P17–P20)    (P21–P23)  (P24–P27)
                                Operação contínua (P28–P29)
```

---

## Como usar num case parecido

1. **Perfil da base.** Responda às 9 perguntas do [Passo 0 do playbook](02_PLAYBOOK.md#passo-0--perfil-da-base): como
   os dados chegam, o que muda no tempo, a natureza das medidas, dado pessoal, quem consome, regulação e onde roda.
2. **Escolha as práticas** pelo [mapa de gatilhos](#mapa-de-gatilhos) abaixo. Cada resposta do perfil aponta para as
   práticas que valem.
3. **Construa na ordem das camadas**, usando os módulos do playbook (M1 a M10). Não avance sem o critério de saída do
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
- **Prova:** nenhum token nos arquivos enviados; o GitHub tem os mesmos arquivos que o commit local.

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
- **Prova:** paridade 21/21 entre o painel do Databricks e as medidas DAX, que repetem a regra semiaditiva.

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
- **Como aplicamos:** 5 ciclos semanais com roteiro, nesta ordem:
  1. semana limpa;
  2. pico de avisos;
  3. erros barrados;
  4. erros que vazam;
  5. recuperação.
- **Por quê:** um dia sem incidente prova que a regra não reprova evento bom, não que ela pega erro.
- **Reaplique quando:** a qualidade precisa ser demonstrada ou homologada.
- **Prova:** roteiro em [dqx_studio/demo/ROTEIRO.md](../dqx_studio/demo/ROTEIRO.md).

### P11 · Monitoramento contínuo com DQX Studio, em janelas com todas as linhas
- **Origem:** [DQX](https://github.com/databrickslabs/dqx) ([documentação](https://databrickslabs.github.io/dqx/))
  (Databricks Labs).
- **Como aplicamos:**
  - Studio instalado como app, com estado no Lakebase.
  - Registro de Regras com 69 modelos, 12 tabelas monitoradas e 194 checagens aprovadas.
  - Views de janela (`dq.v_*_janela`) e replay das 5 semanas.
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
- **Prova:** painéis 14/14, Genie 29/29 e paridade Power BI 21/21, com os mesmos números.

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
- **Prova:** 29/29 perguntas de avaliação certas.

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
- **Prova:** 102 arquivos válidos nos esquemas e paridade 21/21. **Não verificado:** abrir no Power BI Desktop.

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
- **Por quê:** o catálogo envelhece pelo lado do projeto. A opção Power BI levou o `powerbi-analyzer` de relevância baixa
  para alta.
- **Reaplique quando:** a cada fase nova do projeto.
- **Prova:** catálogo com 7 aplicados, 2 propostos e 6 adiados.

---

## Operação contínua

### P28 · Matriz de resiliência
- **Origem:** prática do projeto (princípio 7 do playbook).
- **Como aplicamos:** a [matriz de resiliência](02_PLAYBOOK.md#matriz-de-resiliência) tem 15 falhas, cada uma com o
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
- **Prova:** 22 fases, 74 lições, inventário regenerado a cada mudança.

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

**Do próprio projeto:** [trilha](01_TRILHA_DE_APRENDIZAGEM.md), [playbook](02_PLAYBOOK.md),
[lições](03_LICOES_APRENDIDAS.md), [CHANGELOG](CHANGELOG.md) e
[catálogo databricks-solutions](../referencias/databricks_solutions/CATALOGO.md).
