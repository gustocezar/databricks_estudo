# Mapeamento · <nome da base>

> Preenchido nas tarefas T2.1 a T2.3 (contrato: [SPEC](../aplicar-base-bruta/SPEC.md)). Cada conceito precisa de uma
> coluna, uma derivação ou "não se aplica".

## Conceitos

| Conceito | Coluna no pos_venda | Coluna nesta base | Derivação ou decisão | Prática |
|---|---|---|---|---|
| chave da pendência | `pendencia_id` | | | P05 |
| data do evento ou da foto | `data_extracao` | | | P06 |
| tipo do evento | `tipo_evento` | | | P06 |
| status | `status_cobranca` | | | P09 |
| número da apólice e da parcela | `numero_apolice`, `numero_parcela` | | | P05 |
| vencimento | `data_vencimento` | | | P09 |
| valor da parcela | `valor_parcela` | | | P20 |
| multa, juros e total | `valor_multa`, `valor_juros`, `valor_total_pendente` | | | P20 |
| atraso | `dias_atraso` | | | P20 |
| baixa | `data_baixa`, `valor_pago` | | | P09 |
| forma de pagamento | `forma_pagamento` | | | P05 |
| periodicidade | `periodicidade_pagamento` | | | P05 |
| motivo da pendência | `motivo_pendencia` | | | P05 |
| canal de venda | `canal_venda` | | | P05 |
| produto | `produto_codigo`, `produto_nome` | | | P05 |
| cliente | `cliente_id` | | | P05, P17 |
| dado pessoal | `cliente_cpf`, `cliente_nome`, contatos, `cliente_uf`, nascimento | | | P15, P17 |
| corretor e ponto de venda | `corretor_id`, `ponto_venda_codigo` | | | P05 |

## De-para de domínios

| Domínio | Valor na base | Valor canônico |
|---|---|---|
| status | | |
| tipo do evento | | |

## Regras (erro e aviso)

Nome estável: ele vira o motivo na quarentena e a linha do painel. Ponto de partida:
`dqx_codigo/checks_pendencias.yml`.

| Nome | Criticidade | Coluna | Expressão (TRUE = dado bom) | Origem (barreira, candidata do DQX, negócio) | Aceita? |
|---|---|---|---|---|---|
| pendencia_id_nulo | erro | | | barreira | |
| tipo_evento_invalido | erro | | | barreira | |
| status_cobranca_invalido | erro | | | barreira | |
| valor_parcela_nao_positivo | erro | | | barreira | |
| valor_total_inconsistente | erro | | | barreira | |
| vencimento_nao_anterior_ao_evento | erro | | | barreira | |
| atraso_nao_confere_com_as_datas | erro | | | barreira | |
| valores_fora_da_regra | erro | | | barreira | |
| baixa_sem_data_ou_valor_pago | erro | | | barreira | |
| uf_invalida | erro | | | barreira | |
| cliente_menor_de_idade | erro | | | barreira | |
