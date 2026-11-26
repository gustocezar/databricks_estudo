# Questionário do negócio · regras de qualidade, métricas e vigência

> **Para quem responde:** a área dona do dado (no pós-venda, o financeiro), com o time de dados ao lado.
> **Quando:**
> - na implantação de uma base nova (etapa E2 do [spec](../../specs/aplicar-base-bruta/SPEC.md));
> - sempre que a triagem classificar uma falha como `regra_errada`;
> - numa revisão a cada trimestre.
>
> **O que acontece com as respostas:** cada uma vira uma linha do [catálogo de regras](../catalogo/catalogo_regras.yml),
> uma meta de painel ou uma pergunta de avaliação da Genie. O ciclo está em [catalogo/README.md](../catalogo/README.md)
> e a prática é a P41 do [framework](../../docs/04_FRAMEWORK.md).

## Como usar

1. Escolha o assunto: um campo, um evento ou um indicador. Responda cada bloco em linguagem de negócio, sempre com um
   exemplo de dado certo e um de dado errado.
2. O time de dados transforma a resposta em um destes três:
   - regra do catálogo, com `status: proposta`;
   - cenário BDD, se for regra de cálculo ([regras/features](../features/));
   - pergunta de avaliação da Genie, se for indicador.
3. O dono aprova a versão: `status: aprovada`, mais `aprovado_por` (o papel, nunca o e-mail) e `aprovado_em`. Só então
   ela entra no DQX e na triagem.
4. Não apague resposta antiga. Se a regra mudou, a resposta nova vira **versão nova**, com data de início. O dado
   antigo continua sendo julgado pela resposta antiga.

## Bloco A · O que é dado certo

| # | Pergunta | Vira no catálogo | Exemplo do pós-venda |
|---|---|---|---|
| A1 | Que informação é obrigatória para o registro fazer sentido? | regra `is_not_null`, tipo `erro` | "Toda pendência tem identificador" (`pendencia_id_nulo`) |
| A2 | Quais valores são aceitos? A lista é fechada? | `sql_expression` com `IN` | status de cobrança: os 6 valores aceitos (`status_cobranca_invalido`) |
| A3 | Que contas precisam bater? Com que arredondamento? | expressão ou função de regra (`pos_venda.regras`) | total = parcela + multa + juros, em centavos (`valor_total_inconsistente`, `valores_fora_da_regra`) |
| A4 | Que datas precisam estar em ordem? | `sql_expression` com datas | vencimento antes da data do evento (`vencimento_nao_anterior_ao_evento`) |
| A5 | Que combinações não podem existir? | `sql_expression` com `NOT (… AND …)` | baixa sem data ou sem valor pago (`baixa_sem_data_ou_valor_pago`) |
| A6 | Dado faltando ou estranho barra o registro ou só avisa? | `tipo: erro` (barra) ou `aviso` (entra marcado) | e-mail ausente só avisa (`email_ausente`) |
| A7 | Se o campo vier vazio, o registro passa ou é barrado? | o `coalesce(…, true/false)` da expressão | UF vazia passa; parcela vazia é barrada |

## Bloco B · Quanto erro é aceitável (métricas e observabilidade)

| # | Pergunta | Vira | Exemplo do pós-venda |
|---|---|---|---|
| B1 | Qual é a taxa de falha normal desta regra num dia comum? | linha de base em `pos_venda.regras.v_falhas_regras` | barreira: mediana de 0% por regra e por dia; falha em 150 de 2.596 dias × regra; pico de 2,09% (`valor_total_inconsistente`, 08/12/2026) |
| B2 | A partir de que taxa alguém precisa agir? | `limite_taxa` da versão | regras de erro: 0 (qualquer falha pede triagem) |
| B3 | Para os avisos, que taxa é aceitável sem abrir ação? | `limite_taxa` (nulo = ainda não definido, e a triagem cobra) | e-mail ausente: **em aberto** (pergunta 6) |
| B4 | Quem precisa saber, e em quanto tempo? | dono da regra; alerta e SLA ([07](../../docs/07_SUSTENTACAO.md)) | carga até 06:15; alerta às 06:20 |
| B5 | Que indicador de negócio esta falha distorce? | ligação com o painel e com a metric view | parcela ≤ 0 reduz o saldo em aberto |

## Bloco C · Perguntas que o negócio faz aos números (avaliação)

| # | Pergunta | Vira | Exemplo do pós-venda |
|---|---|---|---|
| C1 | Que pergunta você faz aos dados toda semana? | pergunta de avaliação da Genie (P21, P24) | "Qual o saldo em aberto por produto no fim do mês?" |
| C2 | Qual é a resposta certa hoje, e como você confere? | gabarito em SQL da pergunta | SQL de referência sobre a metric view |
| C3 | Que número tem que bater entre painel, Genie e Power BI? | paridade indicador a indicador (P23) | 21 de 21 indicadores do BI iguais ao painel |

## Bloco D · Vigência: quando a regra muda

| # | Pergunta | Vira no catálogo | Exemplo |
|---|---|---|---|
| D1 | Desde quando esta regra vale? Ela já foi diferente antes? | `vigente_de` da versão; versões antigas registradas | todas as 14 regras do pós-venda estão na versão 1, "desde sempre" |
| D2 | A mudança vale só para o dado novo, ou também para o passado? | `vigente_de` pela **data do dado**; reprocessar ou não é decisão registrada | padrão: só o dado com data a partir de `vigente_de` |
| D3 | O que exatamente mudou: valor aceito, conta ou limite? | versão nova, com `motivo` | ensaio: `QUINZENAL` aceita a partir de 05/01/2027 (fictício) |
| D4 | Existe data de fim (campanha, produto descontinuado)? | `vigente_ate` (exclusive) | versão 1 da periodicidade no ensaio: até 05/01/2027 |
| D5 | Quem aprovou, e onde a decisão está registrada? | `aprovado_por` (papel), `aprovado_em`, `origem` (ata, normativo, triagem) | "diretoria financeira, ata de 02/01/2027" |
| D6 | Dado antigo reprocessado hoje usa qual regra? | sempre a da data do dado; exceção vira decisão registrada | evento de 03/01 reprocessado em 10/01 → versão 1 |

**Regra de ouro da vigência:** o evento é julgado pela regra que valia na **data dele** (`data_extracao`), não na data
em que o job rodou. Sem isso, toda mudança de regra faz o passado "falhar", e o gráfico de qualidade dá um salto que
ninguém explica. Os painéis marcam a mudança com `pos_venda.regras.v_mudancas_regras`.

## Bloco E · Retroalimentação: o que fazer com cada falha

| # | Pergunta | Vira | Onde |
|---|---|---|---|
| E1 | Quem tria as falhas desta regra, e com que frequência? | dono da regra e rito semanal | `pos_venda.regras.v_triagem_pendente` |
| E2 | Quando a falha é dado ruim, quem corrige na origem, e em quanto tempo? | ação do plano de ação | `triagem_regras.acao`; [05](../../docs/05_SKILLS_E_GANHOS.md) |
| E3 | Quando a falha é regra errada, quem reescreve a regra? | volta aos blocos A e D: versão nova | catálogo, `status: proposta` |
| E4 | Que falha é conhecida e aceita, e por quanto tempo? | classificação `esperado`, com período | `triagem_regras` |
| E5 | Quantas acusações erradas a regra pode ter antes de ser revista? | limite da `taxa_falso_positivo` | `pos_venda.regras.v_retroalimentacao` |

**As quatro classificações da triagem** (a tabela recusa qualquer outra):

| Classificação | Quer dizer | O que acontece |
|---|---|---|
| `dado_ruim` | a regra está certa e o dado está errado | ação na origem (plano de ação) |
| `regra_errada` | o dado está certo e a regra acusou sem razão | pergunta nova no bloco A ou D, e versão nova |
| `fora_da_vigencia` | a versão aplicada não era a do período do dado | corrigir a vigência no catálogo |
| `esperado` | falha conhecida e aceita (incidente explicado, teste) | nada, no período registrado |

## Rito

| Quando | Quem | O quê | Saída |
|---|---|---|---|
| Toda semana, 30 min | dono da regra e time de dados | percorrer `v_triagem_pendente` e classificar cada linha | linhas em `triagem_regras` |
| Todo mês | dono das regras | olhar `v_retroalimentacao`: falso positivo alto, semanas pendentes, avisos sem limite | perguntas dos blocos A, B e D |
| Todo trimestre | área de negócio | responder o questionário inteiro de novo para os assuntos que mudaram | versões novas no catálogo |

Para registrar uma triagem (exemplo ilustrativo; o plano de ação #7 não existe):

```sql
INSERT INTO pos_venda.regras.triagem_regras VALUES
  ('T-2026-12-14-01', 'valor_parcela_nao_positivo', 1, DATE'2026-12-07', DATE'2026-12-13',
   'dado_ruim', 'parcela negativa vem de estorno lançado como pendência na origem',
   'origem separa estorno de pendência (plano de ação #7)', 'financeiro_pos_venda', current_timestamp());
```

## Perguntas em aberto para o dono (26/11/2026)

Elas saíram do ensaio do spec na bronze (24/11, [FICHA](../../specs/ensaio_pos_venda_bronze/FICHA.md)) e da primeira
leitura de `v_triagem_pendente` (26/11). Cada uma pede uma resposta antes de virar versão nova.

| # | O que apareceu no dado | Pergunta | Blocos |
|---|---|---|---|
| 1 | periodicidades `QUINZENAL` (136) e `BIMESTRAL` (121), só de 02 a 08/01/2027 | é produto novo (versão nova com início) ou erro da origem? Hoje só avisam. | A2, D1, D3 |
| 2 | tipo de evento `ESTORNO` (114), barrado como `tipo_evento_invalido` | o estorno passa a ser evento válido? A partir de quando? | A2, D1 |
| 3 | status com outra grafia (`EM COBRANCA` 180, `pendente` 154) e status novos (`CANCELADO` 173, `PAGO` 159) | normalizar, aceitar ou barrar? `PAGO` é o mesmo que `PAGA`? | A2, A7 |
| 4 | parcela ≤ 0: 1.033 no perfil; 1.025 barradas pela barreira, de 05/12/2026 a 08/01/2027 no dado | é estorno ou crédito (regra errada) ou erro de lançamento (dado ruim)? | A3, E2 |
| 5 | no dia do vencimento (0 dias de atraso), a parcela já tem multa de 2% | confirma a regra atual? O cenário BDD a marca como "regra atual". | A3, D1 |
| 6 | `email_ausente`: 2.995 avisos em 2 semanas, sem limite definido | que taxa de e-mail ausente é aceitável? | B3 |
| 7 | 69 pares semana × regra acima do limite, nas semanas de 30/11/2026 a 04/01/2027 no dado, nenhum triado | quem tria, e quando começa o rito semanal? | E1 |
