# pos_venda · Governança, ontologia e camada semântica

Fonte única do conhecimento de negócio: [ontologia.py](ontologia.py) (domínio, subdomínios, Pages, Wikis e tags) e
[descricoes_colunas.py](descricoes_colunas.py) (descrição de cada coluna). Dados sintéticos.

## O que já está no workspace (APIs de metadados, sem warehouse)

| Item | Onde ver | Situação |
|---|---|---|
| Domínio **Pós-venda** + 3 subdomínios (Cobrança e inadimplência, Clientes e apólices, Qualidade de dados) | Discover → Domínios | criado (governed tags `Pós-venda` e `Pós-venda/<subdomínio>`) |
| 18 **Pages** (conceitos de negócio: definição, regra, onde está, pode / não pode, como validar) | Discover → Pós-venda → Pages | publicadas |
| 34 **Wikis** (uma por tabela das camadas principais: grão, atualização, qualidade, pode / não pode, exemplo) | Catalog Explorer → tabela → Overview | publicadas |
| Tags: domínio e `camada` nos 6 schemas; subdomínio, `tipo_ativo`, `entidade`, `atualizacao` nas 34 tabelas | Catalog Explorer → tags | 497 aplicadas, 0 erros |
| Certificação (`system.certification_status = certified`) no star schema e na silver | Catalog Explorer | 17 tabelas |
| Classificação LGPD (`class.br_cpf`, `class.br_rg`, `class.name`, `class.email_address`, `class.phone_number`, `class.street_address`, `class.location`, `class.date_of_birth`, `class.age`, `class.gender`...) | colunas | 345 colunas |

## O que depende do warehouse (cota diária do Free Edition)

| Passo | Script | O que faz |
|---|---|---|
| 1 | `python3 aplicar_sql.py ontologia_sql.json` | cria `pos_venda.ontologia`: 10 entidades (views sem identificadores pessoais), `entidades`, `relacoes`, `glossario` e 4 metric views (`mv_carteira_em_aberto`, `mv_recuperacao`, `mv_safra_recuperacao`, `mv_qualidade_dados`) |
| 2 | `python3 aplicar_descricoes.py` | grava a descrição das 1.619 colunas das camadas principais |
| 3 | `python3 auditar_metadados.py` | mede de novo a cobertura de descrições e tags |

`aguardar_cota_ontologia.sh` (na pasta temporária da sessão) roda os três passos assim que a cota renovar.

> **Atenção:** recriar uma metric view (`CREATE OR REPLACE`) apaga as tags e a Wiki dela. Depois do passo 1, rode
> `python3 aplicar_semantica.py` (completo) para devolver tags, certificação e Wikis.

## Views do schema dq: governança preservada na recriação

Teste de 20/11/2026: `CREATE OR REPLACE TABLE ... AS SELECT` mantém descrições, tags e tags de coluna;
`CREATE OR REPLACE VIEW` apaga as tags da view, as tags das colunas e a Wiki. O job diário recriava 9 views
(`v_*_7d` e `v_*_janela`) a cada execução. Agora tudo passa por `carga_diaria/views_preservadas.garantir_view`:

- definição igual → não faz nada (o caso de todo dia; testado nas 9 views: "igual");
- view nova → cria (depois rode `aplicar_semantica.py` para tags e Wiki);
- definição mudou → guarda descrições, tags, tags de coluna e Wiki, recria e devolve tudo (testado em
  `v_painel_studio_execucoes`: 13 descrições e 1 tag devolvidas).

Usam a rotina: o notebook 25 do job (embutida por `gerar_carga.py`), o replay (`rodar_ciclos.py`) e as views do painel
de qualidade (`dqx_studio/painel/aplicar_e_testar.py`, que também grava as 89 descrições de `descricoes_painel.py`).
Cobertura depois disso: 1.933 de 1.933 colunas descritas nas camadas principais.

## Padrões de metric view (uc-semantics-patterns)

As medidas abaixo seguem os padrões do repositório
[databricks-solutions/uc-semantics-patterns](https://github.com/databricks-solutions/uc-semantics-patterns)
(pastas *Semi-additive calculations*, *Time Intelligence* e *Ranking*). Foram conferidas contra SQL escrito à mão: fechamento
e mês anterior por produto e mês (64 de 64 combinações iguais), acumulado do mês (24 de 24 dias de dezembro iguais).

| Metric view | Medida | Padrão | Como usar |
|---|---|---|---|
| `mv_carteira_em_aberto` | Saldo de fechamento, Pendências em aberto no fechamento | semiaditivo `last` | por mês: o último dia; sem data: a foto mais recente |
| `mv_carteira_em_aberto` | Saldo no início do período, Variação do saldo no período | semiaditivo `first` | primeiro dia do período e diferença para o fechamento |
| `mv_carteira_em_aberto` | Saldo de fechamento do mês anterior, Variação mensal do saldo | `offset: -1 month` | agrupe ou filtre por `Mês de referência` (não pela data do dia) |
| `mv_carteira_em_aberto` | Posição no ranking do saldo | `RANK() OVER` | ranking pelo saldo médio diário do período |
| `mv_recuperacao` | Valor recuperado no mês, no mês anterior, Variação mensal do valor recuperado | `offset: -1 month` | agrupe ou filtre por `Mês da baixa` |
| `mv_recuperacao` | Valor recuperado acumulado no mês | `range: cumulative` por `Data da baixa` | agrupe por dia; respeita filtros de data |
| `mv_recuperacao` | Valor recuperado acumulado no ano | `range: cumulative` por `Mês da baixa` | por mês; filtrar um mês não corta os meses anteriores |
| `mv_recuperacao` | Posição no ranking de recuperação | `RANK() OVER` | ranking pelo valor recuperado do período |

Limites encontrados nos testes: uma medida de ranking não pode ir na mesma consulta que medidas de janela (erro
`SCALAR_SUBQUERY_TOO_MANY_ROWS`); e o `offset` só enxerga o mês anterior quando o filtro é na dimensão de mês da janela.
O "último dia" do semiaditivo é o último dia **de cada fatia**: uma fatia que some antes do fim do mês fica com o último
saldo em vez de zero. Agrupado por uma dimensão (produto, canal, faixa, status, forma, motivo, regional, UF) e por produto
x canal, o total bate em todos os meses; em produto x canal x forma, dezembro sobra R$ 240,33 (duas fatias
NAO_CADASTRADA quitadas antes de 24/12). Os painéis usam o grão produto x canal.

## Scripts

| Script | Para quê |
|---|---|
| `auditar_metadados.py` | auditoria de descrições e tags (REST, sem warehouse) → `auditoria_metadados.json` |
| `aplicar_semantica.py` | governed tags, domínio, subdomínios, tags, certificação, Pages e Wikis (idempotente) |
| `gerar_ontologia_sql.py` | gera `ontologia.sql` (leitura) e `ontologia_sql.json` (execução) |
| `aplicar_sql.py`, `sql_util.py` | executa SQL no warehouse e detecta a cota esgotada |
| `aplicar_descricoes.py` | COMMENT nas colunas (lote por tabela; por coluna quando o tipo de objeto exige) |

## Regras seguidas

- Pages atômicas (um conceito cada), sem dados pessoais no texto, com dono, sinônimos e seção **Como validar**: as
  perguntas dessa seção viram as perguntas de avaliação (benchmarks) da Genie.
- O saldo em aberto é **semiaditivo** (a fato tem uma linha por pendência por dia): as Pages, a Wiki da fato e a metric
  view dizem para usar uma data, a foto mais recente, o `Saldo de fechamento` ou o saldo médio diário.
- A camada de ontologia não expõe nome, CPF, RG, contato nem endereço (minimização da LGPD).
