# Mapeamento · ensaio com a bronze do pos_venda

> T2.1 a T2.3 do ensaio. Como a base é a própria bronze do pos_venda, todo conceito tem a coluna de mesmo nome; o
> valor do ensaio está nos domínios e nas regras.

## Conceitos

Todos os 18 conceitos do modelo existem com o mesmo nome (`pendencia_id`, `data_extracao`, `tipo_evento`,
`status_cobranca`, `numero_apolice`, `numero_parcela`, `data_vencimento`, `valor_parcela`, `valor_multa`, `valor_juros`,
`valor_total_pendente`, `dias_atraso`, `data_baixa`, `valor_pago`, `forma_pagamento`, `periodicidade_pagamento`,
`motivo_pendencia`, `canal_venda`, cadastro e dado pessoal). Nenhuma derivação necessária.

## De-para de domínios

| Domínio | Valor na base | Variantes vistas no perfil | Valor canônico ou decisão |
|---|---|---|---|
| status | `PENDENTE`, `EM_COBRANCA`, `PAGA`, `NEGOCIADO`, `PROMESSA_PAGAMENTO`, `COBRANCA_EXTERNA` | `pendente` (154), `EM COBRANCA` (180), `PAGO` (159), `CANCELADO` (173) | sem de-para: as variantes vão para a quarentena (`status_cobranca_invalido`), como na barreira; numa base real, decidir com o dono da origem |
| tipo do evento | `NOVA`, `ATUALIZACAO`, `BAIXA` | `ESTORNO` (114), nulo (118) | erro `tipo_evento_invalido` |
| forma de pagamento | 4 do catálogo | `VALE_REFEICAO`, `TRANSFERENCIA_INTERNACIONAL`, `CRIPTOMOEDA` | entram e ficam órfãs na dimensão; o dono do catálogo decide (plano de ação) |
| periodicidade | 4 do domínio | `QUINZENAL` (136), `BIMESTRAL` (121) | aviso `periodicidade_fora_do_dominio` |

## Regras (erro e aviso)

As 11 regras de erro de `dqx_codigo/checks_pendencias.yml` valem sem troca de coluna. Somam-se 3 avisos (e-mail,
forma e periodicidade) e a sugestão do ensaio: um aviso para chave repetida (`pendencia_id` + `data_extracao` +
`tipo_evento`), com 10.277 combinações no perfil.
