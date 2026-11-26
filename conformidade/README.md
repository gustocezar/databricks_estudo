# Conformidade dos dados e do workspace

> Schema `pos_venda.conformidade`, gerado por [`gerar_conformidade.py`](gerar_conformidade.py). Números de
> 26/11/2026. Práticas P35 a P37 do [framework](../docs/04_FRAMEWORK.md).

Responde a duas perguntas:

1. **Os dados seguem as regras do projeto?** Mede descrições, tags governadas, dado pessoal (LGPD), chaves,
   certificação, atualização e uso, otimização, jobs, warehouses e alertas.
2. **O que fazer com a observabilidade que já roda no workspace?** A resposta está em
   [AVALIACAO_OBSERVABILIDADE.md](AVALIACAO_OBSERVABILIDADE.md) e na visão `acoes_observabilidade`.

A conformidade só lê o `information_schema` do Unity Catalog, as tabelas de sistema e duas APIs (tag policies e
alertas SQL). Ela grava apenas no próprio schema.

## Visões

| Visão | Para quem | O que mostra |
|---|---|---|
| `boas_praticas_dados` | todos | uma linha por regra: verificados, conformes, falhas, %, meta, situação, origem e como corrigir |
| `pendencias` | quem corrige | só o que não atende, com severidade e como corrigir |
| `squad_por_schema` | squad | conformidade de cada schema do `pos_venda` por dimensão |
| `plataforma_por_catalogo` | plataforma | conformidade de cada catálogo do workspace e dos recursos (jobs, warehouses, alertas) |
| `acoes_observabilidade` | plataforma | as 8 ações de observabilidade, com veredito, execuções, custo em 30 dias e a última sonda |
| `achados` | análise | uma linha por verificação (objeto × regra); base de todas as outras |
| `ativos` | análise | inventário de tabelas e views do workspace: descrição, tags, dado pessoal, PK, dono, lineage e Predictive Optimization |
| `colunas` | análise | colunas do `pos_venda`: descrição, `dado_pessoal`, classes automáticas (`class.*`) e se o nome indica dado pessoal |
| `recursos` | análise | jobs, warehouses e alertas SQL com tags, descrição, timeout, auto-stop e disparos por dia |
| `config_regras`, `config_camadas`, `config_tags_governadas` | quem mantém | o catálogo de regras, o papel de cada schema e os valores permitidos das tags governadas |
| `mv_conformidade` | Genie e painéis | metric view sobre `achados`: Verificações, Conformes, Pendências e Conformidade (%) |
| `sonda_views` (tabela) | plataforma | cada view do workspace testada com `DESCRIBE QUERY`, por dia |
| `historico` (tabela) | todos | a situação de cada regra, por dia |

Todas as colunas têm descrição. O papel de cada schema define quais regras valem para ele:

| Papel | Schemas |
|---|---|
| principal (fluxo diário) | landing, fonte, bronze, silver, gold, dq, ontologia, regras, bi |
| legado (primeira versão; só tags de dado pessoal, por decisão) | `*_sql`, `*_ldp` |
| apoio (monitoramento) | finops, conformidade, dqx_codigo (DQX como código), sustentacao (tempo de execução e SLA) |
| interno (fica fora das regras) | `__materialization_*`, `event_log_*`, que o Lakeflow cria sozinho (L80) |

## Regras e resultado

28 regras em 7 dimensões. Uma regra está em **atende** quando bate a meta; em **crítico**, quando tem severidade alta
e está abaixo da meta; em **atenção**, quando está abaixo da meta com severidade média ou baixa; e em **sem dados**,
quando não verificou nenhum objeto.

| Regra | O que exige | Verificados | % | Situação |
|---|---|---|---|---|
| DOC01 | Ativo com descrição (workspace inteiro) | 246 | 70,7 | crítico |
| DOC02 | Descrição do ativo com ao menos 30 caracteres | 155 | 98,7 | atenção |
| DOC03 | Coluna com descrição | 3.582 | 100,0 | atende |
| DOC04 | Descrição da coluna com ao menos 15 caracteres | 3.582 | 98,9 | atenção |
| DOC05 | Schema com descrição | 19 | 100,0 | atende |
| TAG01 | Ativo principal com `domain`, `data_owner` e `subject_area` | 71 | 100,0 | atende |
| TAG02 | Ativo principal com a tag `atualizacao` | 71 | 100,0 | atende |
| TAG03 | Valor de tag governada dentro da política | 898 | 100,0 | atende |
| TAG04 | Schema principal com `domain` e `camada` | 9 | 100,0 | atende |
| LGPD01 | Coluna com nome de dado pessoal tem `dado_pessoal` | 381 | 100,0 | atende |
| LGPD02 | Classificação automática revisada com `dado_pessoal` | 532 | 100,0 | atende |
| LGPD03 | Ativo com coluna pessoal marcado `contem_dado_pessoal` | 26 | 100,0 | atende |
| LGPD04 | `contem_dado_pessoal` sem coluna marcada (tag órfã) | 28 | 100,0 | atende |
| LGPD05 | Ativo com coluna sensível marcado `contem_dado_sensivel` | 21 | 100,0 | atende |
| EST01 | Dimensão, fato e ponte da gold com chave primária | 14 | 100,0 | atende |
| EST02 | Gold e ontologia certificadas | 34 | 100,0 | atende |
| EST03 | Ativo legado marcado como deprecated | 32 | 0,0 | atenção |
| EST04 | Dono do ativo é grupo ou service principal | 155 | 0,0 | atenção |
| USO01 | `atualizacao=diaria` escrito nos últimos 2 dias | 23 | 100,0 | atende |
| USO02 | Ativo principal lido nos últimos 30 dias | 71 | 88,7 | atenção |
| USO03 | View responde (sonda diária) | 170 | 87,1 | crítico |
| OTM01 | Predictive Optimization nos últimos 30 dias, fora as tabelas `sob_demanda` (meta 90%) | 42 | 95,2 | atende |
| PLT01 | Job com as tags `project` e `team` | 13 | 92,3 | atenção |
| PLT02 | Job com descrição | 13 | 92,3 | atenção |
| PLT03 | Job com timeout | 13 | 53,8 | atenção |
| PLT04 | Warehouse com auto-stop de até 30 minutos | 1 | 100,0 | atende |
| PLT05 | Warehouse com as tags `project` e `team` | 1 | 0,0 | atenção |
| PLT06 | Alerta SQL com até 4 disparos por dia | 6 | 83,3 | atenção |

A origem, o link da fonte e como corrigir cada regra estão em `config_regras`. As fontes são a documentação
Databricks (comentários, governed tags, data classification, constraints, boas práticas do Unity Catalog, lineage,
Predictive Optimization, jobs, warehouses e alertas), o Well-Architected, a LGPD, o bundle `observabilidade-framework`
e as práticas do projeto.

## O que a conformidade encontrou

**Em ordem:**
- **Dado pessoal e descrições de coluna.** As 5 regras de LGPD, as colunas descritas (3.582 de 3.582) e os 898
  valores de tag governada estão em 100%.
- **Chaves.** As 14 dimensões, fatos e pontes da gold têm chave primária.

**Pendências reais (26/11/2026):** são 10.209 verificações e 344 pendências.
- **Descrição fora do `pos_venda` (DOC01, crítica).** São 72 ativos sem descrição em `finops.observability`, `main`,
  `workspace` e nas tabelas internas do Lakeview. No `pos_venda`, nenhum.
- **Views quebradas (USO03, crítica).** São 22 de 170, todas fora do domínio e pela mesma
  causa (L76): 19 em `finops.observability` e 3 cópias `vw_billing_*` em `workspace.default`.
- **Jobs.**
  - Timeout (PLT03): faltam 6, todos do bundle de observabilidade, que só se lê.
  - Tags `project` e `team` (PLT01): falta só o job do DQX Studio, que o app gerencia (1).
- **Alertas (PLT06).** O alerta de queries lentas dispara 24 vezes por dia (L79).
- **Ativos sem leitura (USO02).** 8 ativos da ontologia não foram lidos em 30 dias. A Genie usa as metric
  views.
- **Descrições curtas.** DOC02 tem 2 pendências e DOC04, 41: descrições abaixo do mínimo, a maioria
  no schema `finops` e nas dimensões de data.

**Resolvido em 24 e 26/11:**
- área de negócio (TAG01) em 100%;
- timeout nos jobs do pós-venda;
- tags de custo nos 4 jobs do pós-venda;
- as 3 tabelas `dq_*` certificadas (EST02);
- frescor das tabelas sob demanda (USO01, L96);
- a sonda diária, que virou job às 06:45.

**Esperado no Free Edition ou decisão do dono:**
- **EST04, dono em grupo.** Todo ativo tem uma pessoa como dona, porque é um workspace de uma pessoa só.
- **EST03, legado como deprecated.** Os 32 ativos legados não estão marcados. Marcar ou apagar é decisão do dono.

**Triagem da primeira rodada:** ela acusou 382 colunas sem descrição e 129 colunas de dado pessoal sem tag. Eram 126
colunas de tabelas internas do Lakeflow (L80) e 3 nomes de métrica da ontologia ("CPF inválido", "CEP malformado",
"Taxa de CPF inválido"). As duas causas foram corrigidas no gerador, não com exceção à mão.

## Como rodar

```bash
python3 conformidade/gerar_conformidade.py politicas   # valores das tags governadas -> politicas_tags.json
python3 conformidade/gerar_conformidade.py alertas     # alertas SQL e disparos por dia -> alertas.json
python3 conformidade/gerar_conformidade.py aplicar     # schema, tabelas e visões (só recria o que mudou)
python3 conformidade/gerar_conformidade.py registrar   # sonda das views + histórico do dia
python3 conformidade/gerar_conformidade.py conferir    # checagens -> conferencia.json
```

**`registrar`** testa cada view, metric view e materialized view do workspace (140 hoje) com `DESCRIBE QUERY`. O
comando analisa a view sem executá-la. Depois, grava a situação de cada regra em `historico`.

**Job diário da sonda (desde 26/11/2026).** O mesmo `registrar` roda todo dia às 06:45 no job
`pos_venda_conformidade_sonda`, depois da carga das 05:00 e do Studio das 06:30. O job é o bundle desta pasta
([databricks.yml](databricks.yml)), e o notebook é [src/sonda_diaria.py](src/sonda_diaria.py). O notebook usa
`spark.sql` porque o CLI não existe dentro do job. Se mudar a sonda, mude `cmd_registrar` também. As visões continuam
sendo criadas pelo `aplicar` local.

```bash
cd conformidade && databricks bundle deploy -t dev --profile <perfil>              # cria ou atualiza o job
databricks bundle run sonda_conformidade -t dev --profile <perfil>                 # roda agora
databricks bundle deploy -t dev --var="sonda_status=PAUSED" --profile <perfil>     # pausa a agenda
```

**`conferir`** verifica:
- que cada visão responde;
- que o inventário tem todo ativo do `information_schema`;
- que as regras de descrição verificam todo ativo e toda coluna que não sejam internos;
- que a soma por regra é igual às linhas de `achados`;
- que pendências = não conformes = a metric view;
- que nenhuma regra ficou "sem dados";
- que o histórico do dia tem uma linha por regra.

Em 26/11/2026, as 9 checagens passaram (10.209 verificações, 268 ativos).

**Para reaplicar em outro case:**
1. troque `DOMINIO` e `CAMADAS`;
2. ajuste `TAGS_ATIVO` e `TAGS_SCHEMA` às suas tags governadas;
3. revise as regras em `REGRAS`;
4. ajuste os padrões de nome de dado pessoal (`PII` e `NAO_PII`).

## Limites

- **`alterado_em`** é a última alteração no `information_schema`: definição, dados ou metadados. Por isso o frescor
  (USO01) usa primeiro a última escrita registrada pelo lineage.
- **O lineage conta toda leitura** (USO02), inclusive as feitas por consultas de teste. A sonda usa `DESCRIBE QUERY`,
  que não executa a view.
- **A sonda pega a view que não resolve** (tabela, coluna ou tipo que mudou). Ela não pega um erro que só aparece ao
  executar.
- **Valores das tags e alertas vêm de fotos.** As tabelas de sistema não trazem os valores permitidos das tags nem
  os alertas SQL. Por isso eles vêm de `politicas_tags.json` e `alertas.json`, que se atualizam com `politicas` e
  `alertas`.
