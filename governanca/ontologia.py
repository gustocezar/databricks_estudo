"""Ontologia do domínio Pós-venda (seguro de vida): fonte única do conhecimento de negócio.

Daqui saem (scripts nesta pasta):
  - aplicar_semantica.py : domínio e subdomínios do Discover, Pages (conceitos), Wikis (tabelas), tags e certificação
  - ontologia.sql / metric views / Genie (próximas etapas): entidades, relações, glossário e perguntas de avaliação

Regras de redação (boas práticas da documentação de Unity Catalog semantics):
  - uma Page por conceito ("atômica"): definição, uso no negócio, exemplos, o que pode e o que não pode, como validar;
  - uma Wiki por tabela: para que serve, grão, atualização, regras de qualidade, uso permitido e exemplo;
  - NENHUM dado pessoal (nome, CPF, contato) em Pages e Wikis. Os exemplos usam só identificadores técnicos.
Os dados do pos_venda são SINTÉTICOS (gerados para demonstração).
"""

CAT = "pos_venda"
DOMINIO = {
    "tag_key": "Pós-venda",
    "subtitle": "Cobrança de parcelas de seguro de vida, carteira de clientes e apólices, e qualidade dos dados",
    "description": (
        "Domínio de negócio do pós-venda de seguro de vida: parcelas que não foram pagas no vencimento (pendências), "
        "o ciclo de cobrança até a baixa, a carteira de clientes, apólices, produtos, corretores e pontos de venda, e a "
        "qualidade dos dados que chegam todo dia do sistema de origem. Dados sintéticos para demonstração."),
    "icon": {"name": "BANK", "color": "#2F6B9A"},
}
SUB = {  # chave curta -> definição do subdomínio (tag "Pós-venda/<nome>")
    "cobranca": {"nome": "Cobrança e inadimplência",
                 "subtitle": "Pendências, aging, status de cobrança, baixas e recuperação",
                 "description": "Parcelas em atraso desde a entrada (1 dia após o vencimento) até a baixa: valores com multa e "
                                "juros, faixas de atraso, fases da cobrança, motivos, pagamentos e a foto diária da carteira."},
    "carteira": {"nome": "Clientes e apólices",
                 "subtitle": "Cadastro de clientes, apólices, produtos, coberturas, corretores e canais",
                 "description": "Quem é o segurado pagador, qual apólice e produto ele tem, por qual canal, corretor e ponto de "
                                "venda a apólice foi vendida e como o prêmio é pago (forma e periodicidade)."},
    "qualidade": {"nome": "Qualidade de dados",
                  "subtitle": "Barreira de qualidade, quarentena, métricas e janelas do DQX Studio",
                  "description": "Regras que decidem se um evento pode entrar na silver, os eventos barrados (não aptos), as "
                                 "métricas diárias de qualidade e as janelas que o DQX Studio avalia."},
}

FATO = f"{CAT}.gold.fact_pagamento_pendente_snapshot"

# ===================================================================================================== PAGES (conceitos)
PAGES = [
    # ---------------------------------------------------------------------------------------------- cobrança
    {"sub": "cobranca", "titulo": "Pendência de pagamento",
     "sinonimos": ["pendência", "parcela em atraso", "parcela vencida não paga", "inadimplência", "débito em aberto",
                   "delinquency", "pending payment"],
     "descricao": "Parcela do prêmio de uma apólice de vida que não foi paga até o vencimento. Existe do dia seguinte ao "
                  "vencimento até a baixa (pagamento).",
     "corpo": f"""## Definição
Uma **pendência** é uma parcela do prêmio que não foi paga no vencimento. Ela **entra** na carteira no dia seguinte ao
vencimento (1 dia de atraso) e **sai** quando há a baixa (pagamento). Parcelas pagas em dia nunca viram pendência.

## Regra de negócio
- Identificador: `pendencia_id` = `PD` + número da apólice (sem o prefixo) + número da parcela com 3 dígitos.
  Ex.: `PD000289125037` é a parcela 37 da apólice `VID000289125`.
- Uma pendência tem eventos ao longo do tempo: `NOVA` (entrada), `ATUALIZACAO` (mudança de fase) e `BAIXA` (pagamento).
- Nem toda pendência é paga: parte segue em aberto e pode ir para cobrança externa.
- Chance de atraso depende do perfil pagador da apólice (bom, regular, crônico).

## Onde está nos dados
- Estado atual (1 linha por pendência): `{CAT}.silver.pendencia_atual`
- Histórico de versões (SCD2): `{CAT}.silver.pendencia_hist`
- Foto diária das pendências em aberto: `{FATO}` (grão pendência × dia)
- Eventos recebidos: `{CAT}.silver.pendencia_evento`

## Pode
- Contar pendências, somar valores e acompanhar o tempo até a baixa.
- Cruzar com produto, canal, corretor, ponto de venda, forma de pagamento e motivo.

## Não pode
- Somar a mesma pendência em vários dias da foto diária como se fossem pendências diferentes (ver **Saldo em aberto da carteira**).
- Usar eventos da quarentena como pendências reais (ver **Quarentena (dado não apto)**).

## Como validar
- "Quantas pendências estavam em aberto em 24/12/2026?" → `count(*)` na fato com `data_referencia_sk = 20261224`.
- "Quantas pendências novas entraram em dezembro?" → eventos `NOVA` em `silver.pendencia_evento` com `data_extracao` em dez/2026.
"""},
    {"sub": "cobranca", "titulo": "Status de cobrança",
     "sinonimos": ["status da pendência", "fase de cobrança", "situação da cobrança", "collection status"],
     "descricao": "Situação da pendência no ciclo de cobrança: PENDENTE, EM_COBRANCA, PROMESSA_PAGAMENTO, NEGOCIADO, "
                  "COBRANCA_EXTERNA ou PAGA.",
     "corpo": f"""## Definição
O status mostra em que ponto da cobrança a pendência está. Ele avança com os eventos `ATUALIZACAO` e termina em `PAGA`.

| Status | Fase | Em aberto | Quando acontece |
|---|---|---|---|
| PENDENTE | INICIAL | sim | primeiros dias de atraso, antes da primeira ação de cobrança |
| EM_COBRANCA | INTERNA | sim | cobrança ativa pela seguradora (SMS, e-mail, WhatsApp, telefone, carta) |
| PROMESSA_PAGAMENTO | NEGOCIACAO | sim | cliente prometeu pagar |
| NEGOCIADO | NEGOCIACAO | sim | acordo fechado com o cliente |
| COBRANCA_EXTERNA | EXTERNA | sim | atraso longo (cerca de 61 a 90 dias): enviado a empresa de cobrança |
| PAGA | ENCERRADA | não | houve a baixa |

## Onde está nos dados
`{CAT}.gold.dim_status_cobranca` (colunas `fase_cobranca`, `ordem_fase`, `em_aberto`) e `status_cobranca` na silver.

## Pode
- Agrupar a carteira em aberto por fase; medir quantas pendências chegam à cobrança externa.

## Não pode
- Tratar valores fora da lista (ex.: `PAGO`, `EM COBRANCA`) como válidos: eles são barrados pela regra `status_cobranca_invalido`.
- Esperar `PAGA` na foto diária da fato: ela só tem pendências em aberto.

## Como validar
- "Qual o valor em aberto em cobrança externa em 24/12/2026?" → fato do dia 20261224 com status `COBRANCA_EXTERNA`.
"""},
    {"sub": "cobranca", "titulo": "Dias de atraso e faixa de atraso (aging)",
     "sinonimos": ["aging", "atraso", "faixa de atraso", "bucket de atraso", "envelhecimento da carteira", "days past due", "DPD"],
     "descricao": "Dias entre o vencimento e a data de referência, agrupados em 7 faixas de 00_VENCE_HOJE a 06_ACIMA_120.",
     "corpo": f"""## Definição
**Dias de atraso** = data de referência − data de vencimento. Na foto diária o atraso é **recalculado a cada dia**.

| Faixa | Dias |
|---|---|
| 00_VENCE_HOJE | 0 |
| 01_1_A_15 | 1 a 15 |
| 02_16_A_30 | 16 a 30 |
| 03_31_A_60 | 31 a 60 |
| 04_61_A_90 | 61 a 90 |
| 05_91_A_120 | 91 a 120 |
| 06_ACIMA_120 | mais de 120 |

## Onde está nos dados
`dias_atraso` e `faixa_atraso_sk` em `{FATO}`; catálogo das faixas em `{CAT}.gold.dim_faixa_atraso` (use `ordem_faixa`
para ordenar). Na silver: `dias_atraso` e `faixa_atraso` (atraso no dia do evento).

## Pode
- Montar o aging da carteira em uma data (valor e quantidade por faixa).

## Não pode
- Ordenar faixas pelo nome sem `ordem_faixa` quando o rótulo mudar; usar o atraso da silver como atraso de hoje (é o do dia do evento).
- Aceitar `dias_atraso` diferente de `data_extracao − data_vencimento`: é barrado (`atraso_nao_confere_com_as_datas`).

## Como validar
- "Qual o aging da carteira em 24/12/2026?" → fato do dia 20261224 agrupada por `dim_faixa_atraso.faixa_atraso`, ordenada por `ordem_faixa`.
"""},
    {"sub": "cobranca", "titulo": "Valor total pendente",
     "sinonimos": ["valor atualizado da parcela", "saldo devedor da parcela", "valor com encargos", "parcela + multa + juros"],
     "descricao": "Valor da parcela mais multa de 2% e juros de 1% ao mês pro rata dia, no dia de referência.",
     "corpo": f"""## Definição
`valor_total_pendente = valor_parcela + valor_multa + valor_juros`, em reais (R$), no dia de referência.

## Regra de negócio
- `valor_parcela` = prêmio periódico da apólice (mensal, trimestral, semestral ou anual).
- `valor_multa` = 2% da parcela, arredondado a 2 casas (fixa).
- `valor_juros` = 1% ao mês **pro rata dia**: parcela × 0,01 × dias de atraso / 30, arredondado a 2 casas.
- A soma precisa fechar com diferença menor que R$ 0,01; se não fechar, o evento é barrado (`valor_total_inconsistente`).
- A conta oficial é a função `pos_venda.regras.valor_total_pendente` (com `valor_multa` e `valor_juros`), testada por
  cenários em português; a gold usa essas funções e a barreira barra o evento cujos valores fogem delas
  (`valores_fora_da_regra`).
- Exemplo numérico: parcela R$ 100,00 com 15 dias de atraso → multa R$ 2,00 + juros R$ 0,50 = **R$ 102,50**.

## Onde está nos dados
`{FATO}` (recalculado a cada dia da foto) e a silver (valor no dia do evento).

## Pode
- Somar o valor total das pendências de **um mesmo dia** de referência.

## Não pode
- Somar o valor de vários dias da foto (ver **Saldo em aberto da carteira**).
- Considerar parcela zero ou negativa: é barrada (`valor_parcela_nao_positivo`).

## Como validar
- "Qual o valor total pendente em 24/12/2026?" → `sum(valor_total_pendente)` na fato com `data_referencia_sk = 20261224`.
"""},
    {"sub": "cobranca", "titulo": "Saldo em aberto da carteira",
     "sinonimos": ["carteira em atraso", "estoque de pendências", "exposição", "saldo pendente", "valor em aberto",
                   "outstanding balance", "receivables in arrears"],
     "descricao": "Soma do valor total pendente de todas as pendências em aberto em UMA data de referência. Métrica "
                  "semiaditiva: não se soma ao longo do tempo.",
     "corpo": f"""## Definição
O **saldo em aberto** é a foto da carteira em uma data: soma de `valor_total_pendente` das pendências abertas naquele dia.

## Regra de negócio (a mais importante)
A fato `{FATO}` guarda **uma linha por pendência por dia** enquanto ela está aberta. A mesma pendência aparece em
vários dias. Por isso o saldo é **semiaditivo**:
- soma entre pendências e categorias **no mesmo dia**: correto;
- soma entre **dias**: **errado** (conta a mesma dívida várias vezes).
Para um período, use o saldo do **último dia** do período ou a **média dos saldos diários**.

## Onde está nos dados
`{FATO}`: filtre `data_referencia_sk` em um único dia (ex.: `20261224`) ou agrupe por `data_referencia_sk` para a evolução.

## Pode
- Comparar o saldo de fim de mês entre meses; ver a evolução diária do saldo.

## Não pode
- `sum(valor_total_pendente)` sem filtrar ou agrupar por `data_referencia_sk`.
- Chamar de "valor recuperado" (isso vem das baixas: ver **Valor recuperado e taxa de recuperação**).

## Como validar
- "Qual o saldo em aberto no fim de novembro de 2026?" → fato com `data_referencia_sk = 20261130`.
- "Como evoluiu o saldo em dezembro?" → fato agrupada por `data_referencia_sk` entre 20261201 e 20261224.
"""},
    {"sub": "cobranca", "titulo": "Baixa (pagamento da pendência)",
     "sinonimos": ["baixa", "pagamento", "quitação", "liquidação", "pendência paga", "settlement"],
     "descricao": "Evento que encerra a pendência quando o cliente paga; registra data da baixa e valor pago.",
     "corpo": f"""## Definição
A **baixa** é o pagamento da pendência. Gera um evento `BAIXA`, muda o status para `PAGA` e tira a pendência da foto diária.

## Regra de negócio
- `data_baixa` = dia do pagamento; `valor_pago` = valor total pendente naquele dia (parcela + multa + juros).
- Todo evento `BAIXA` precisa de `data_baixa` e `valor_pago`; sem isso é barrado (`baixa_sem_data_ou_valor_pago`).
- As baixas acontecem entre cerca de 2 e 60 dias de atraso.

## Onde está nos dados
`{CAT}.silver.pendencia_evento` com `tipo_evento = 'BAIXA'` (colunas `data_baixa`, `valor_pago`);
`{CAT}.silver.pendencia_atual` com `status_cobranca = 'PAGA'`. A fato **não** tem baixas (só pendências em aberto).

## Pode
- Somar `valor_pago` por dia, mês, produto, canal ou forma de pagamento.

## Não pode
- Procurar baixas na fato `{FATO}`.
- Somar `valor_pago` de eventos duplicados: deduplicar por `pendencia_id` + `data_extracao` + `tipo_evento`.

## Como validar
- "Quanto foi recebido em baixas em dezembro de 2026?" → `sum(valor_pago)` de eventos `BAIXA` deduplicados com `data_baixa` em dez/2026.
"""},
    {"sub": "cobranca", "titulo": "Valor recuperado e taxa de recuperação",
     "sinonimos": ["recuperação", "valor recebido", "taxa de recuperação", "recovery rate", "cobrança efetiva"],
     "descricao": "Valor recuperado = soma dos valores pagos nas baixas. Taxa de recuperação = pendências pagas / "
                  "pendências que entraram (por safra de entrada).",
     "corpo": f"""## Definição
- **Valor recuperado** no período = soma de `valor_pago` das baixas com `data_baixa` no período.
- **Taxa de recuperação (por safra)** = pendências da safra que já foram pagas / pendências que entraram na safra.
  A safra é o mês de entrada da pendência (mês do evento `NOVA`).

## Regra de negócio
- Safras recentes têm taxa menor só porque tiveram menos tempo para pagar: compare safras com a mesma idade.
- Use `{CAT}.silver.pendencia_atual` (status `PAGA` = recuperada) com a data de entrada vinda dos eventos `NOVA`.

## Pode
- Comparar a recuperação por produto, canal, forma de pagamento e motivo.

## Não pode
- Calcular recuperação com a fato (ela não tem pagamentos).
- Misturar safras de idades diferentes sem avisar.

## Como validar
- "Qual a taxa de recuperação das pendências que entraram em outubro de 2026?" → pendências com `NOVA` em out/2026
  e status atual `PAGA`, divididas pelo total que entrou em out/2026.
"""},
    {"sub": "cobranca", "titulo": "Motivo da pendência",
     "sinonimos": ["motivo do não pagamento", "causa da inadimplência", "motivo de recusa"],
     "descricao": "Por que a parcela não foi paga; depende da forma de pagamento e se agrupa em FINANCEIRO, CADASTRAL, "
                  "AUTORIZACAO e OPERACIONAL.",
     "corpo": f"""## Definição
| Motivo | Grupo | Forma de pagamento típica |
|---|---|---|
| SALDO_INSUFICIENTE | FINANCEIRO | débito em conta, Pix automático |
| LIMITE_INSUFICIENTE, CARTAO_RECUSADO | FINANCEIRO | cartão de crédito |
| BOLETO_NAO_PAGO | FINANCEIRO | boleto |
| DADOS_BANCARIOS_INVALIDOS, CONTA_ENCERRADA | CADASTRAL | débito em conta |
| CARTAO_EXPIRADO | CADASTRAL | cartão de crédito |
| AUTORIZACAO_DEBITO_CANCELADA | AUTORIZACAO | débito em conta |
| AUTORIZACAO_PIX_REVOGADA | AUTORIZACAO | Pix automático |
| BOLETO_NAO_RECEBIDO | OPERACIONAL | boleto |

## Onde está nos dados
`{CAT}.gold.dim_motivo_pendencia` (`grupo_motivo`) e `motivo_pendencia` na silver.

## Pode
- Priorizar ações: motivos **cadastrais** pedem atualização de dados; **financeiros** pedem negociação.

## Não pode
- Usar motivo fora do catálogo: a regra `motivo_pendencia_cadastrado` do DQX Studio reprova.

## Como validar
- "Qual grupo de motivo concentra o maior valor em aberto em 24/12/2026?" → fato do dia por `dim_motivo_pendencia.grupo_motivo`.
"""},
    {"sub": "cobranca", "titulo": "Foto diária da carteira (snapshot)",
     "sinonimos": ["snapshot diário", "fato histórica", "posição diária", "fotografia da carteira"],
     "descricao": "Fato com uma linha por pendência em aberto por dia (grão pendência × dia), com valores e atraso "
                  "recalculados no dia da foto.",
     "corpo": f"""## Definição
`{FATO}` guarda, para cada dia, todas as pendências **em aberto** naquele dia. Chave primária:
(`data_referencia_sk`, `pendencia_id`). `data_referencia_sk` é o dia da foto no formato `yyyyMMdd`.

## Regra de negócio
- Entram as versões da silver histórica cujo status não é `PAGA` e que estavam vigentes no dia.
- Atraso, faixa, juros e valor total são **recalculados** para o dia da foto.
- `qtd_pendencias` vale 1 em toda linha (grão).
- Chaves para as dimensões: `*_sk` (cliente, apólice, produto, corretor, ponto de venda, periodicidade, forma de pagamento,
  status, motivo, faixa de atraso) e datas `*_sk` para `dim_data`.

## Pode
- Saldo, quantidade e aging em uma data; evolução diária; comparação entre datas.

## Não pode
- Somar entre dias (ver **Saldo em aberto da carteira**); procurar baixas ou eventos barrados aqui.

## Como validar
- "Quantas linhas tem a foto de 24/12/2026?" → `count(*)` com `data_referencia_sk = 20261224` (cada linha = 1 pendência aberta).
"""},
    {"sub": "cobranca", "titulo": "Tentativas e canal de contato da cobrança",
     "sinonimos": ["tentativas de cobrança", "canal de contato", "régua de cobrança", "contato com o cliente"],
     "descricao": "Quantas tentativas de cobrança já foram feitas (1 a 10) e por qual canal foi o último contato.",
     "corpo": f"""## Definição
- `tentativas_cobranca`: 1 tentativa inicial + 1 a cada 10 dias de atraso + 1 se já saiu de `PENDENTE`, limitado a 10.
- `canal_ultimo_contato`: SMS, EMAIL, WHATSAPP, TELEFONE, CARTA ou NENHUM.

## Onde está nos dados
`{FATO}` e silver (`tentativas_cobranca`, `canal_ultimo_contato`, `data_ultima_tentativa`).

## Pode
- Medir o esforço de cobrança por faixa de atraso e a efetividade por canal (com as baixas).

## Não pode
- Usar tentativas fora de 1 a 10 ou canal fora da lista: as regras do Studio reprovam.

## Como validar
- "Qual o canal de último contato mais comum nas pendências em aberto em 24/12/2026?" → fato do dia por `canal_ultimo_contato`.
"""},
    # ---------------------------------------------------------------------------------------------- carteira
    {"sub": "carteira", "titulo": "Cliente (segurado pagador)",
     "sinonimos": ["cliente", "segurado", "pagador", "titular da apólice", "policyholder"],
     "descricao": "Pessoa física titular da apólice e responsável pelo pagamento do prêmio. Dados pessoais protegidos pela LGPD.",
     "corpo": f"""## Definição
O **cliente** é o titular da apólice de vida e pagador do prêmio. Identificador técnico: `cliente_id`; na gold, `cliente_sk`.

## Regra de negócio
- Cliente precisa ter **18 anos ou mais** na data do evento; menor de idade é barrado (`cliente_menor_de_idade`).
- CPF com dígito verificador inválido é **aviso**: o evento entra, sinalizado (`dq_cpf_invalido`).
- UF precisa ser uma das 27 siglas; fora disso é barrado (`uf_invalida`).

## Onde está nos dados
`{CAT}.gold.dim_cliente` (cadastro padronizado) e colunas `cliente_*` na silver.

## Dados pessoais (LGPD)
Nome, CPF, RG, e-mail, celular, telefone, endereço completo, CEP, data de nascimento, sexo, estado civil, profissão,
faixa de renda e fumante são **dados pessoais**. Essas colunas têm tags de classificação `class.*` no Unity Catalog.

## Pode
- Análises **agregadas** por faixa etária, UF, cidade, sexo ou faixa de renda.
- Usar `cliente_sk` (na posição da carteira e na `dim_cliente`) para ligar pendências ao mesmo cliente. As entidades
  `pendencia` e `pagamento` da camada de ontologia não trazem identificador do cliente.

## Não pode
- Listar nome, CPF, RG, e-mail, telefone ou endereço em respostas, relatórios ou exportações sem finalidade legítima.
- Usar faixa de renda, fumante ou sexo para decidir cobrança de forma discriminatória.

## Como validar
- "Quantos clientes distintos têm pendência em aberto em 24/12/2026?" → `count(DISTINCT cliente_sk)` na fato do dia.
"""},
    {"sub": "carteira", "titulo": "Apólice de seguro de vida",
     "sinonimos": ["apólice", "contrato de seguro", "policy"],
     "descricao": "Contrato de seguro de vida do cliente: produto, vigência, capital segurado, prêmio periódico, "
                  "coberturas, endossos e beneficiários.",
     "corpo": f"""## Definição
A **apólice** (`numero_apolice`, ex.: `VID000289125`) é o contrato. Gera uma parcela por período de pagamento.

## Regra de negócio
- Status da apólice: ATIVA, SUSPENSA, REDUZIDA ou CANCELADA_INADIMPLENCIA.
- `valor_premio_periodico` = valor de cada parcela; `dia_vencimento` = dia do mês em que a parcela vence.
- Capital segurado principal e total; indicadores de coberturas adicionais (IPTA, IFPD, doenças graves, DIT, assistência funeral).
- Endossos alteram a apólice (capital, coberturas, beneficiário, periodicidade, dados cadastrais, reajuste anual);
  `parcela_afetada_por_endosso` marca parcelas que vencem depois do último endosso.

## Onde está nos dados
`{CAT}.gold.dim_apolice`, `{CAT}.gold.bridge_apolice_cobertura` (coberturas da apólice) e `{CAT}.fonte.apolices`.

## Pode
- Relacionar pendências ao status e à idade da apólice; medir risco de cancelamento por inadimplência.

## Não pode
- Contar apólices somando linhas da fato (uma apólice tem várias parcelas e vários dias): use `count(DISTINCT apolice_sk)`.

## Como validar
- "Quantas apólices têm pendência em aberto em 24/12/2026?" → `count(DISTINCT apolice_sk)` na fato do dia.
"""},
    {"sub": "carteira", "titulo": "Produto e coberturas de vida",
     "sinonimos": ["produto", "plano", "cobertura", "garantia", "ramo vida"],
     "descricao": "Oito produtos de vida (Essencial, Completo, Inteira, Família, Renda Protegida, Doenças Graves, Premium, "
                  "Resgatável) e suas coberturas principal e adicionais.",
     "corpo": f"""## Definição
| Código | Produto | Categoria | Cobertura principal |
|---|---|---|---|
| VID-ESS | Vida Essencial | TEMPORARIO | Morte (natural ou acidental) |
| VID-COM | Vida Completo | TEMPORARIO | Morte (natural ou acidental) |
| VID-INT | Vida Inteira | VITALICIO | Morte (natural ou acidental) |
| VID-FAM | Vida Familia | FAMILIAR | Morte (natural ou acidental) |
| VID-REN | Vida Renda Protegida | RENDA | Diária por Incapacidade Temporária (DIT) |
| VID-DGR | Vida Doencas Graves | DOENCAS_GRAVES | Doenças Graves |
| VID-PRE | Vida Premium | PREMIUM | Morte (natural ou acidental) |
| VID-RES | Vida Resgatavel | RESGATAVEL | Morte (natural ou acidental) |

Coberturas adicionais: IPTA, IFPD, doenças graves, DIT e assistência funeral. A cobertura principal não aparece como adicional.

## Onde está nos dados
`{CAT}.gold.dim_produto`, `{CAT}.gold.dim_cobertura` e `{CAT}.gold.bridge_apolice_cobertura` (papel PRINCIPAL ou ADICIONAL).

## Pode
- Comparar inadimplência e recuperação por produto ou categoria.

## Não pode
- Somar capital segurado pela ponte apólice × cobertura sem considerar o papel (dupla contagem da principal).

## Como validar
- "Qual produto tem o maior valor em aberto em 24/12/2026?" → fato do dia por `dim_produto.produto_nome`.
"""},
    {"sub": "carteira", "titulo": "Canal de venda, corretor e ponto de venda",
     "sinonimos": ["canal", "corretor", "corretora", "ponto de venda", "PDV", "bancassurance", "distribuição"],
     "descricao": "Por onde a apólice foi vendida: CORRETOR, BANCASSURANCE, DIGITAL ou TELEVENDAS, com o corretor "
                  "(registro SUSEP, comissão) e o ponto de venda.",
     "corpo": f"""## Definição
- **Canal de venda**: CORRETOR, BANCASSURANCE, DIGITAL ou TELEVENDAS.
- **Corretor**: pessoa física ou jurídica com registro SUSEP, regional, % de comissão e status.
  Vendas DIGITAL e TELEVENDAS não têm corretor: na gold aparecem como o membro `NAO_INFORMADO`.
- **Ponto de venda**: escritório do corretor (canal CORRETOR), agência bancária (BANCASSURANCE), plataforma digital
  ou central de televendas, com cidade, UF e regional.

## Regra de negócio
- Venda pelo canal CORRETOR **precisa** ter corretor; sem corretor é **aviso** (`canal_corretor_tem_corretor`).

## Onde está nos dados
`{CAT}.gold.dim_corretor`, `{CAT}.gold.dim_ponto_venda` (inclui `canal_venda`) e colunas `corretor_*` / `ponto_venda_*` na silver.

## Pode
- Ranking de inadimplência por corretor, canal ou regional; acompanhar carteira por ponto de venda.

## Não pode
- Expor o documento do corretor (CPF/CNPJ) em relatórios: é dado classificado.

## Como validar
- "Qual canal de venda tem mais pendências em aberto em 24/12/2026?" → fato do dia por `dim_ponto_venda.canal_venda`.
"""},
    {"sub": "carteira", "titulo": "Forma de pagamento e periodicidade",
     "sinonimos": ["forma de pagamento", "meio de pagamento", "periodicidade", "frequência de pagamento"],
     "descricao": "Como o prêmio é pago (DEBITO_CONTA, BOLETO, CARTAO_CREDITO, PIX_AUTOMATICO) e com que frequência "
                  "(MENSAL, TRIMESTRAL, SEMESTRAL, ANUAL).",
     "corpo": f"""## Definição
| Forma | Grupo |
|---|---|
| DEBITO_CONTA | AUTOMATICO |
| PIX_AUTOMATICO | AUTOMATICO |
| CARTAO_CREDITO | CARTAO |
| BOLETO | BOLETO |

Periodicidades: MENSAL (12 parcelas/ano), TRIMESTRAL (4), SEMESTRAL (2), ANUAL (1). Pagamentos menos frequentes têm desconto.

## Regra de negócio
- Só as 4 formas acima são válidas. Formas novas (ex.: `CRIPTOMOEDA`, `VALE_REFEICAO`, `TRANSFERENCIA_INTERNACIONAL`, vistas
  em dez/2026) **não** têm dimensão: viram chave órfã na fato. O DQX Studio reprova (`forma_pagamento_cadastrada`).

## Onde está nos dados
`{CAT}.gold.dim_forma_pagamento` e `{CAT}.gold.dim_periodicidade`.

## Pode
- Comparar inadimplência entre pagamento automático e boleto.

## Não pode
- Usar `INNER JOIN` com `dim_forma_pagamento` para totais de carteira sem checar órfãs: as linhas sem dimensão somem do total.

## Como validar
- "Qual forma de pagamento tem o maior valor em aberto em 24/12/2026?" → fato do dia com `LEFT JOIN dim_forma_pagamento`.
"""},
    # ---------------------------------------------------------------------------------------------- qualidade
    {"sub": "qualidade", "titulo": "Quarentena (dado não apto)",
     "sinonimos": ["quarentena", "dado não apto", "evento barrado", "rejeitado", "quarantine"],
     "descricao": "Eventos do bronze que violaram uma regra de erro e foram barrados antes da silver; guardam a linha "
                  "original e o motivo da rejeição.",
     "corpo": f"""## Definição
A **quarentena** (`{CAT}.silver.pendencia_evento_quarentena`) guarda os eventos que a barreira de qualidade não deixou
entrar na silver, com `motivo_rejeicao` = a **primeira** regra violada.

## Regra de negócio (as 11 regras de erro da barreira, na ordem)
1. `pendencia_id_nulo` 2. `tipo_evento_invalido` 3. `status_cobranca_invalido` 4. `valor_parcela_nao_positivo`
5. `valor_total_inconsistente` 6. `vencimento_nao_anterior_ao_evento` 7. `atraso_nao_confere_com_as_datas`
8. `valores_fora_da_regra` (multa, juros ou total diferentes das funções `pos_venda.regras.*`) 9. `baixa_sem_data_ou_valor_pago`
10. `uf_invalida` 11. `cliente_menor_de_idade`

## Onde está nos dados
Quarentena na silver; resumo por dia e motivo em `{CAT}.gold.dq_barrados_por_motivo_dia`.

## Pode
- Medir volume e valor barrados; devolver os casos para correção na origem.

## Não pode
- Usar a quarentena em indicadores financeiros (saldo, recuperação): esses eventos **não** são verdade de negócio.

## Como validar
- "Quantos eventos foram barrados em dezembro de 2026 e por qual motivo?" → `dq_barrados_por_motivo_dia` por `motivo_rejeicao`.
"""},
    {"sub": "qualidade", "titulo": "Regra de erro e regra de aviso",
     "sinonimos": ["criticidade", "error", "warn", "aviso de qualidade", "regra DQX"],
     "descricao": "Erro barra a linha (não entra na silver); aviso deixa entrar sinalizada. As regras ficam no DQX Studio.",
     "corpo": f"""## Definição
- **Erro**: o dado é impróprio para uso (ex.: valor negativo, status inexistente). A linha é barrada.
- **Aviso**: o dado tem ressalva, mas serve para o negócio (ex.: CPF com dígito errado, e-mail ausente, duplicata,
  CEP malformado, canal CORRETOR sem corretor). A linha entra e fica sinalizada (`dq_*` na silver).

## Onde está nos dados
254 regras aprovadas no DQX Studio (215 de erro e 39 de aviso); métricas diárias em `{CAT}.gold.dq_qualidade_diaria`.

## Pode
- Filtrar avisos em análises sensíveis (ex.: contato por e-mail só com `dq_email_ausente = false`).

## Não pode
- Ignorar avisos que crescem de repente: indicam incidente na origem (ex.: e-mail ausente subiu de 2% para 17% em 30/11/2026).

## Como validar
- "Qual foi o pico de e-mail ausente na semana de 27/11 a 03/12/2026?" → `max(pct_email_ausente)` em `dq_qualidade_diaria`.
"""},
    {"sub": "qualidade", "titulo": "Janela de avaliação do DQX Studio",
     "sinonimos": ["janela", "janela de 7 dias", "avaliação semanal", "dry run"],
     "descricao": "Intervalo de dias que as views pos_venda.dq.v_*_janela expõem para o DQX Studio avaliar com todas as linhas.",
     "corpo": f"""## Definição
`{CAT}.dq.janela_avaliacao` guarda `data_inicio` e `data_fim`. As views `{CAT}.dq.v_*_janela` (bronze, quarentena,
silver de eventos aptos, silver histórica e fato) mostram só esse intervalo. O job diário aponta para os **últimos 7 dias**.

## Regra de negócio
- O DQX Studio deve avaliar as janelas com **todas as linhas**, porque a amostra do dry run lê as primeiras N linhas e
  não é aleatória.

## Pode
- Reapontar a janela para uma semana do passado e reavaliar (replay).

## Não pode
- Comparar execuções feitas com amostra e sem amostra como se fossem equivalentes.

## Como validar
- "Qual janela o Studio está avaliando?" → `SELECT * FROM {CAT}.dq.janela_avaliacao`.
"""},
]

# ===================================================================================================== WIKIS (tabelas)
# tabela -> (subdomínio, descrição curta, seções). Seções: proposito, grao, atualizacao, qualidade, pode, nao_pode, exemplo, pages
W = {}


def wiki(tabela, sub, descricao, proposito, grao, atualizacao, qualidade, pode, nao_pode, exemplo, pages, tipo, entidade=None):
    W[f"{CAT}.{tabela}"] = dict(sub=sub, descricao=descricao, proposito=proposito, grao=grao, atualizacao=atualizacao,
                                qualidade=qualidade, pode=pode, nao_pode=nao_pode, exemplo=exemplo, pages=pages,
                                tipo=tipo, entidade=entidade)


wiki("landing.pagamentos_pendentes_one_table", "cobranca",
     "Extração one-table original do core de vida (500 mil linhas, 6 meses): ponto de partida da simulação.",
     "Base histórica única (uma tabela larga) com pendência, apólice, cliente, corretor e ponto de venda.",
     "1 linha por pendência por dia de extração (com defeitos propositais: duplicatas, CPF inválido, nulos).",
     "Carga única (dbldatagen). Não é atualizada pelo job diário.",
     "Contém defeitos de propósito para treinar regras. Não passou pela barreira.",
     "Estudar o formato da origem; testar regras novas.", "Usar em indicadores: use a gold.",
     "SELECT status_cobranca, count(*) FROM pos_venda.landing.pagamentos_pendentes_one_table GROUP BY 1",
     ["Pendência de pagamento"], "one_table", "pendencia")
wiki("fonte.apolices", "carteira",
     "Cadastro das apólices que alimenta o gerador de eventos diários (sistema de origem simulado).",
     "Fonte das apólices, clientes, produtos e corretores usados para gerar as pendências do dia.",
     "1 linha por apólice (260.482 apólices).", "Criada pelo job de setup; estável.",
     "Inclui o perfil pagador (bom, regular, crônico) que define a chance de atraso.",
     "Entender a carteira de origem.", "Expor dados pessoais; usar como verdade de cobrança.",
     "SELECT produto_nome, count(*) FROM pos_venda.fonte.apolices GROUP BY 1",
     ["Apólice de seguro de vida", "Cliente (segurado pagador)"], "cadastro_fonte", "apolice")
wiki("bronze.pagamentos_pendentes_eventos", "cobranca",
     "Bronze: todos os eventos de pendência recebidos do sistema de origem, como chegaram (append-only).",
     "Registro fiel do que a origem enviou a cada dia: NOVA, ATUALIZACAO e BAIXA, inclusive dados com defeito.",
     "1 linha por evento recebido (pode ter duplicatas).", "Diária, 05:00 (job pos_venda_carga_diaria), por data_extracao.",
     "Ainda não validado. As regras de erro são aplicadas na passagem para a silver.",
     "Auditoria e reprocessamento; investigar incidentes na origem.",
     "Indicadores financeiros (use silver e gold); contar eventos sem deduplicar.",
     "SELECT data_extracao, tipo_evento, count(*) FROM pos_venda.bronze.pagamentos_pendentes_eventos GROUP BY ALL ORDER BY 1",
     ["Pendência de pagamento", "Quarentena (dado não apto)"], "evento", "evento_cobranca")
wiki("silver.pendencia_evento", "cobranca",
     "Silver: eventos aptos (passaram nas 10 regras de erro), padronizados e com flags de aviso dq_*.",
     "Base confiável de eventos para pagamentos (BAIXA), entradas (NOVA) e mudanças de fase.",
     "1 linha por evento apto (duplicatas da origem ainda presentes: deduplicar por pendencia_id + data_extracao + tipo_evento).",
     "Diária, pelo pipeline Lakeflow pos_venda_carga_silver_lakeflow (streaming).",
     "Barreira com 10 regras de erro; avisos marcados em dq_cpf_invalido, dq_email_ausente, dq_email_invalido, dq_rg_ausente, dq_celular_ausente.",
     "Valor recuperado (baixas), entradas por safra, tempo até a baixa.", "Somar eventos duplicados.",
     "SELECT date_trunc('MONTH', data_baixa) mes, sum(valor_pago) FROM pos_venda.silver.pendencia_evento WHERE tipo_evento = 'BAIXA' GROUP BY 1",
     ["Baixa (pagamento da pendência)", "Valor recuperado e taxa de recuperação"], "evento", "evento_cobranca")
wiki("silver.pendencia_evento_quarentena", "qualidade",
     "Quarentena: eventos NÃO aptos barrados antes da silver, com a linha original e o motivo da rejeição.",
     "Separar o que não pode virar verdade de negócio e devolver para correção na origem.",
     "1 linha por evento barrado; motivo_rejeicao = primeira regra de erro violada.", "Diária, pelo mesmo pipeline Lakeflow.",
     "100% das linhas reprovam em pelo menos uma regra de erro do DQX Studio (reconciliado).",
     "Medir volume e valor barrados; listar casos para correção.", "Usar em indicadores financeiros.",
     "SELECT motivo_rejeicao, count(*) FROM pos_venda.silver.pendencia_evento_quarentena GROUP BY 1 ORDER BY 2 DESC",
     ["Quarentena (dado não apto)", "Regra de erro e regra de aviso"], "quarentena", "evento_cobranca")
wiki("silver.pendencia_hist", "cobranca",
     "Silver histórica (SCD2): uma linha por versão da pendência; nova versão quando muda o status ou há a baixa.",
     "Reconstruir o estado de qualquer pendência em qualquer dia; base da foto diária da fato.",
     "1 linha por versão de pendencia_id; vigência [__START_AT, __END_AT).", "Diária, AUTO CDC SCD Tipo 2 no Lakeflow.",
     "Só eventos aptos. Histórico rastreado em status_cobranca e data_baixa.",
     "Tempo em cada fase; quando a pendência mudou de status.", "Somar valores de versões diferentes da mesma pendência.",
     "SELECT status_cobranca, count(*) FROM pos_venda.silver.pendencia_hist WHERE __END_AT IS NULL GROUP BY 1",
     ["Status de cobrança", "Foto diária da carteira (snapshot)"], "historico", "pendencia")
wiki("silver.pendencia_atual", "cobranca",
     "Silver estado atual (SCD1): 1 linha por pendência com o último estado conhecido.",
     "Situação de hoje de cada pendência (inclusive pagas) e base das dimensões da gold.",
     "1 linha por pendencia_id.", "Diária, AUTO CDC SCD Tipo 1 no Lakeflow.",
     "Só eventos aptos; avisos em dq_*.",
     "Taxa de recuperação por safra; status atual da carteira; cadastro mais recente.",
     "Saldo histórico (use a fato); expor dados pessoais.",
     "SELECT status_cobranca, count(*), sum(valor_total_pendente) FROM pos_venda.silver.pendencia_atual GROUP BY 1",
     ["Pendência de pagamento", "Valor recuperado e taxa de recuperação"], "estado_atual", "pendencia")
wiki("gold.fact_pagamento_pendente_snapshot", "cobranca",
     "Fato histórica (snapshot diário) das pendências em aberto: grão pendência × dia, PK (data_referencia_sk, pendencia_id).",
     "Saldo em aberto, quantidade e aging da carteira em qualquer data, e a evolução diária.",
     "1 linha por pendência em aberto por dia de referência (data_referencia_sk = yyyyMMdd).",
     "Diária, notebook 30_fato_snapshot (DELETE + INSERT por intervalo, idempotente).",
     "35 regras no DQX Studio (chaves, 12 FKs, valores). Formas de pagamento novas viram FK órfã.",
     "Saldo de um dia; evolução do saldo; aging; ranking por produto, canal, corretor e motivo.",
     "Somar valores entre dias (semiaditivo); procurar baixas aqui; INNER JOIN com dim_forma_pagamento sem checar órfãs.",
     "SELECT data_referencia_sk, sum(valor_total_pendente) saldo FROM pos_venda.gold.fact_pagamento_pendente_snapshot GROUP BY 1 ORDER BY 1",
     ["Saldo em aberto da carteira", "Foto diária da carteira (snapshot)", "Dias de atraso e faixa de atraso (aging)"],
     "fato", "pendencia")
for dim, sub, desc, ent, pages in [
    ("dim_cliente", "carteira", "Dimensão cliente (cadastro padronizado, último estado). Contém dados pessoais classificados.", "cliente",
     ["Cliente (segurado pagador)"]),
    ("dim_apolice", "carteira", "Dimensão apólice de vida: status, vigência, capital, prêmio, coberturas, endossos e beneficiários.", "apolice",
     ["Apólice de seguro de vida"]),
    ("dim_produto", "carteira", "Dimensão produto: 8 produtos de vida, categoria e cobertura principal.", "produto",
     ["Produto e coberturas de vida"]),
    ("dim_cobertura", "carteira", "Dimensão cobertura: catálogo fixo das coberturas de vida.", "cobertura", ["Produto e coberturas de vida"]),
    ("bridge_apolice_cobertura", "carteira", "Ponte N:N apólice × cobertura com papel (PRINCIPAL/ADICIONAL) e capital.", "cobertura",
     ["Produto e coberturas de vida"]),
    ("dim_corretor", "carteira", "Dimensão corretor (SUSEP, regional, comissão); membro NAO_INFORMADO para vendas sem corretor.", "corretor",
     ["Canal de venda, corretor e ponto de venda"]),
    ("dim_ponto_venda", "carteira", "Dimensão ponto de venda e canal de venda (escritório, agência, digital, televendas).", "ponto_venda",
     ["Canal de venda, corretor e ponto de venda"]),
    ("dim_periodicidade", "carteira", "Dimensão periodicidade do prêmio: MENSAL, TRIMESTRAL, SEMESTRAL, ANUAL.", "periodicidade",
     ["Forma de pagamento e periodicidade"]),
    ("dim_forma_pagamento", "carteira", "Dimensão forma de pagamento: 4 formas válidas e grupo.", "forma_pagamento",
     ["Forma de pagamento e periodicidade"]),
    ("dim_status_cobranca", "cobranca", "Dimensão status de cobrança: fase, ordem e se está em aberto.", "status_cobranca",
     ["Status de cobrança"]),
    ("dim_motivo_pendencia", "cobranca", "Dimensão motivo da pendência e grupo do motivo.", "motivo_pendencia",
     ["Motivo da pendência"]),
    ("dim_faixa_atraso", "cobranca", "Dimensão faixa de atraso (aging): 7 faixas ordenadas.", "faixa_atraso",
     ["Dias de atraso e faixa de atraso (aging)"]),
    ("dim_data", "cobranca", "Dimensão data (calendário 2015–2030) usada nos papéis de data da fato.", "data",
     ["Foto diária da carteira (snapshot)"]),
]:
    pk = {"bridge_apolice_cobertura": "(apolice_sk, cobertura_sk)", "dim_data": "data_sk (yyyyMMdd)"}.get(dim, f"{dim.replace('dim_', '')}_sk")
    wiki(f"gold.{dim}", sub, desc, desc, f"1 linha por membro; chave {pk}.",
         "Diária, notebook 20_gold_dims (reescrita completa, com PK).",
         "Regras do DQX Studio para chaves, nulos e domínios de valores.",
         "Filtrar e agrupar a fato pelos atributos.",
         "Expor colunas classificadas como dado pessoal." if dim == "dim_cliente" else "Somar atributos numéricos da dimensão por linha da fato.",
         f"SELECT * FROM pos_venda.gold.{dim} LIMIT 10", pages,
         "ponte" if dim.startswith("bridge") else "dimensao", ent)
for t, desc, prop, grao, ex in [
    ("gold.dq_qualidade_diaria", "Qualidade diária do fluxo bronze > silver: recebidos, aptos, barrados e métricas de aviso.",
     "Acompanhar a saúde dos dados que chegam por dia.", "1 linha por dia de extração.",
     "SELECT dia, pct_barrados, pct_email_ausente FROM pos_venda.gold.dq_qualidade_diaria ORDER BY dia"),
    ("gold.dq_barrados_por_motivo_dia", "Eventos barrados por dia, motivo da rejeição e tipo de evento.",
     "Ver quais regras seguraram quais incidentes.", "1 linha por dia × motivo × tipo de evento.",
     "SELECT motivo_rejeicao, sum(eventos) FROM pos_venda.gold.dq_barrados_por_motivo_dia GROUP BY 1"),
    ("gold.dq_fato_orfas_diarias", "Linhas da fato por foto diária e quantas ficaram sem dimensão de forma de pagamento.",
     "Detectar dado não cadastrado que vazou para a gold.", "1 linha por dia de foto.",
     "SELECT dia, fk_forma_pagamento_orfa FROM pos_venda.gold.dq_fato_orfas_diarias ORDER BY dia"),
    ("dq.janela_avaliacao", "Controle da janela de avaliação do DQX Studio (data_inicio, data_fim).",
     "Definir o intervalo que as views v_*_janela expõem.", "1 linha.", "SELECT * FROM pos_venda.dq.janela_avaliacao"),
]:
    wiki(t, "qualidade", desc, prop, grao, "Diária, notebook 25_dq_metricas.", "Métrica derivada; recalculada a cada carga.",
         "Monitorar a qualidade e explicar incidentes.", "Usar como indicador financeiro.", ex,
         ["Regra de erro e regra de aviso", "Quarentena (dado não apto)"] if t.startswith("gold") else ["Janela de avaliação do DQX Studio"],
         "metrica_qualidade" if t.startswith("gold") else "controle")
for v, desc in [
    ("dq.v_bronze_eventos_janela", "Bronze: todos os eventos recebidos na janela de avaliação."),
    ("dq.v_quarentena_janela", "Quarentena: eventos não aptos da janela de avaliação."),
    ("dq.v_silver_eventos_aptos_janela", "Silver: eventos aptos da janela de avaliação."),
    ("dq.v_silver_hist_janela", "Silver histórica: versões iniciadas na janela de avaliação."),
    ("dq.v_fato_snapshot_janela", "Gold: fotos diárias da fato na janela de avaliação."),
    ("dq.v_bronze_eventos_7d", "Antiga janela de 7 dias do bronze (substituída por v_bronze_eventos_janela)."),
    ("dq.v_silver_pendencia_atual_7d", "Antiga janela de 7 dias da silver atual (substituída por v_silver_eventos_aptos_janela)."),
    ("dq.v_silver_pendencia_hist_7d", "Antiga janela de 7 dias da silver histórica (substituída por v_silver_hist_janela)."),
    ("dq.v_fato_snapshot_7d", "Antiga janela de 7 dias da fato (substituída por v_fato_snapshot_janela)."),
]:
    antiga = v.endswith("_7d")
    wiki(v, "qualidade", desc, "Destino estável para o DQX Studio avaliar uma camada com todas as linhas.",
         "Mesmo grão da tabela de origem, filtrado pela janela.", "Lê a tabela de origem; janela atualizada pelo job diário.",
         "Avaliada pelas regras da camada de origem no DQX Studio.",
         "Execuções do DQX Studio e investigação de uma semana." if not antiga else "Consultar o histórico antigo do Studio.",
         "Indicadores financeiros." + (" Novas execuções: use a view _janela." if antiga else ""),
         f"SELECT count(*) FROM pos_venda.{v}", ["Janela de avaliação do DQX Studio"], "janela")

# ---- camada de ontologia (pos_venda.ontologia): entidades, catálogos e metric views
_ONT = [  # objeto, subdomínio (None = domínio todo), descrição, tipo, entidade, pages, exemplo
    ("cliente", "carteira", "Entidade Cliente sem identificadores pessoais (faixa etária, UF, CPF válido, cadastro).", "entidade", "cliente",
     ["Cliente (segurado pagador)"], "SELECT faixa_etaria, count(*) FROM pos_venda.ontologia.cliente GROUP BY 1"),
    ("apolice", "carteira", "Entidade Apólice: status, vigência, capital, prêmio, coberturas e endossos.", "entidade", "apolice",
     ["Apólice de seguro de vida"], "SELECT status_apolice, count(*) FROM pos_venda.ontologia.apolice GROUP BY 1"),
    ("produto", "carteira", "Entidade Produto: 8 produtos de vida e cobertura principal.", "entidade", "produto",
     ["Produto e coberturas de vida"], "SELECT * FROM pos_venda.ontologia.produto"),
    ("apolice_cobertura", "carteira", "Relação Apólice tem Cobertura (N:N) com papel e capital.", "entidade", "cobertura",
     ["Produto e coberturas de vida"], "SELECT cobertura_nome, count(*) FROM pos_venda.ontologia.apolice_cobertura GROUP BY 1"),
    ("corretor", "carteira", "Entidade Corretor sem nome e documento: SUSEP, regional, comissão.", "entidade", "corretor",
     ["Canal de venda, corretor e ponto de venda"], "SELECT corretor_regional, count(*) FROM pos_venda.ontologia.corretor GROUP BY 1"),
    ("ponto_venda", "carteira", "Entidade Ponto de venda e canal.", "entidade", "ponto_venda",
     ["Canal de venda, corretor e ponto de venda"], "SELECT canal_venda, count(*) FROM pos_venda.ontologia.ponto_venda GROUP BY 1"),
    ("pendencia", "cobranca", "Entidade Pendência (estado atual): entrada, safra, status, baixa e valor pago.", "entidade", "pendencia",
     ["Pendência de pagamento", "Valor recuperado e taxa de recuperação"],
     "SELECT safra_entrada, avg(CAST(paga AS INT)) taxa FROM pos_venda.ontologia.pendencia GROUP BY 1 ORDER BY 1"),
    ("pagamento", "cobranca", "Entidade Pagamento: 1 linha por pendência paga (baixa deduplicada).", "entidade", "pagamento",
     ["Baixa (pagamento da pendência)"], "SELECT date_trunc('MONTH', data_baixa) mes, sum(valor_pago) FROM pos_venda.ontologia.pagamento GROUP BY 1"),
    ("evento_cobranca", "cobranca", "Entidade Evento de cobrança deduplicado (NOVA, ATUALIZACAO, BAIXA).", "entidade", "evento_cobranca",
     ["Pendência de pagamento", "Status de cobrança"], "SELECT tipo_evento, count(*) FROM pos_venda.ontologia.evento_cobranca GROUP BY 1"),
    ("posicao_carteira", "cobranca", "Posição diária da carteira com rótulos legíveis (base da metric view de carteira). Saldo semiaditivo.",
     "entidade", "pendencia", ["Saldo em aberto da carteira", "Foto diária da carteira (snapshot)"],
     "SELECT faixa_atraso, sum(valor_total_pendente) FROM pos_venda.ontologia.posicao_carteira WHERE foto_mais_recente GROUP BY 1"),
    ("entidades", None, "Catálogo das entidades da ontologia do Pós-venda.", "catalogo_ontologia", None,
     ["Pendência de pagamento", "Cliente (segurado pagador)"], "SELECT * FROM pos_venda.ontologia.entidades"),
    ("relacoes", None, "Relações entre as entidades (triplas sujeito-predicado-objeto, cardinalidade e chave).", "catalogo_ontologia", None,
     ["Pendência de pagamento", "Apólice de seguro de vida"], "SELECT * FROM pos_venda.ontologia.relacoes"),
    ("glossario", None, "Glossário do Pós-venda: termos, definições e sinônimos (mesmo conteúdo das Pages).", "catalogo_ontologia", None,
     ["Pendência de pagamento"], "SELECT termo, sinonimos FROM pos_venda.ontologia.glossario"),
    ("mv_carteira_em_aberto", "cobranca", "Metric view da carteira em aberto: saldo (semiaditivo), saldo de fechamento e de início do "
     "período, variação mensal (MoM), ranking, aging, risco acima de 60 dias e cobrança externa.",
     "metrica", "pendencia", ["Saldo em aberto da carteira", "Dias de atraso e faixa de atraso (aging)"],
     "SELECT `Mês de referência`, MEASURE(`Saldo de fechamento`), MEASURE(`Variação mensal do saldo`) "
     "FROM pos_venda.ontologia.mv_carteira_em_aberto GROUP BY ALL ORDER BY ALL"),
    ("mv_recuperacao", "cobranca", "Metric view de recuperação: valor recuperado nas baixas, variação mensal (MoM), acumulado no mês e "
     "no ano, ranking, pendências pagas, ticket e prazo.", "metrica", "pagamento",
     ["Valor recuperado e taxa de recuperação", "Baixa (pagamento da pendência)"],
     "SELECT `Mês da baixa`, MEASURE(`Valor recuperado`), MEASURE(`Variação mensal do valor recuperado`), "
     "MEASURE(`Valor recuperado acumulado no ano`) FROM pos_venda.ontologia.mv_recuperacao GROUP BY ALL ORDER BY ALL"),
    ("mv_safra_recuperacao", "cobranca", "Metric view de safras: pendências que entraram, pagas e taxa de recuperação por safra.", "metrica",
     "pendencia", ["Valor recuperado e taxa de recuperação"],
     "SELECT `Safra de entrada`, MEASURE(`Taxa de recuperação`) FROM pos_venda.ontologia.mv_safra_recuperacao GROUP BY ALL ORDER BY ALL"),
    ("mv_qualidade_dados", "qualidade", "Metric view da qualidade diária: recebidos, barrados, taxa de barrados e avisos.", "metrica", None,
     ["Regra de erro e regra de aviso", "Quarentena (dado não apto)"],
     "SELECT `Semana`, MEASURE(`Taxa de barrados`) FROM pos_venda.ontologia.mv_qualidade_dados GROUP BY ALL ORDER BY ALL"),
]
for _n, _sub, _desc, _tipo, _ent, _pages, _ex in _ONT:
    _mv = _n.startswith("mv_")
    wiki(f"ontologia.{_n}", _sub, _desc,
         ("Métrica governada: a definição vive aqui e é reusada por Genie, painéis e SQL." if _mv else
          "Visão de negócio da ontologia do Pós-venda, com descrição em cada coluna e sem identificadores pessoais."),
         "Medidas agregadas pelas dimensões escolhidas (consulte com MEASURE())." if _mv else "Ver a descrição das colunas.",
         "Lê as tabelas da silver e da gold no momento da consulta (sempre atualizada).",
         "Herda a qualidade das camadas de origem (barreira de qualidade e regras do DQX Studio).",
         "Responder perguntas de negócio, alimentar a Genie e os painéis.",
         "Somar o saldo de datas diferentes." if _n in ("mv_carteira_em_aberto", "posicao_carteira") else "Expor dados pessoais.",
         _ex, _pages, _tipo, _ent)

# ===================================================================================================== TAGS
CAMADA_SCHEMA = {"landing": "landing", "fonte": "fonte", "bronze": "bronze", "silver": "silver", "gold": "gold", "dq": "qualidade",
                 "ontologia": "ontologia", "regras": "regras", "bi": "bi"}
CERTIFICADAS = [f"{CAT}.gold.{t}" for t in [
    "fact_pagamento_pendente_snapshot", "dim_cliente", "dim_apolice", "dim_produto", "dim_cobertura", "bridge_apolice_cobertura",
    "dim_corretor", "dim_ponto_venda", "dim_periodicidade", "dim_forma_pagamento", "dim_status_cobranca", "dim_motivo_pendencia",
    "dim_faixa_atraso", "dim_data"]] + [f"{CAT}.silver.pendencia_atual", f"{CAT}.silver.pendencia_hist", f"{CAT}.silver.pendencia_evento"] + \
    [f"{CAT}.ontologia.{n}" for n, *_ in _ONT]

# coluna -> tags de classificação (governed tags do Databricks); valem em qualquer tabela/view das camadas principais
CLASSIFICACAO = {
    "cliente_nome": ["class.name"], "corretor_nome": ["class.name"],
    "cliente_cpf": ["class.br_cpf"], "cliente_rg": ["class.br_rg"],
    "cliente_rg_data_emissao": ["class.br_rg"], "cliente_rg_orgao_emissor": ["class.br_rg"], "cliente_rg_uf_emissor": ["class.br_rg"],
    "corretor_documento": ["class.br_cpf", "class.br_cnpj"],
    "cliente_email": ["class.email_address"],
    "cliente_celular": ["class.phone_number"], "cliente_telefone_fixo": ["class.phone_number"],
    "cliente_logradouro": ["class.street_address"], "cliente_numero": ["class.street_address"],
    "cliente_complemento": ["class.street_address"], "cliente_endereco_completo": ["class.street_address"],
    "cliente_bairro": ["class.location"], "cliente_cep": ["class.location"], "cliente_cidade": ["class.location"],
    "cliente_data_nascimento": ["class.date_of_birth"], "cliente_idade": ["class.age"], "cliente_faixa_etaria": ["class.age"],
    "cliente_sexo": ["class.gender"], "cliente_estado_civil": ["class.marital_status"],
    "cliente_renda_faixa": ["class.compensation"], "cliente_profissao": ["class.employment_status"],
    "cliente_fumante": ["class.health_data"],
}

# Marcação legível de dado pessoal (LGPD), por cima da classificação técnica acima. Decisão de 21/11/2026: os dados NÃO
# são mascarados, porque as regras de qualidade e a validação precisam dos valores reais; as tags dizem onde estão.
#   coluna:  dado_pessoal = identificacao | contato | endereco | perfil | sensivel
#   tabela:  contem_dado_pessoal = sim   (e contem_dado_sensivel = sim quando há dado de saúde)
TAG_DADO_PESSOAL = {
    "dado_pessoal": "Coluna com dado pessoal (LGPD), por categoria: identificacao, contato, endereco, perfil ou sensivel "
                    "(art. 5º, II: dado de saúde). Não mascarado: usado na validação de qualidade.",
    "contem_dado_pessoal": "A tabela ou view tem pelo menos uma coluna com dado pessoal (LGPD); veja a tag dado_pessoal nas colunas.",
    "contem_dado_sensivel": "A tabela ou view tem dado pessoal sensível (LGPD, art. 5º, II), como dado de saúde.",
}
CATEGORIA_DADO_PESSOAL = {
    "class.name": "identificacao", "class.br_cpf": "identificacao", "class.br_rg": "identificacao", "class.br_cnpj": "identificacao",
    "class.email_address": "contato", "class.phone_number": "contato",
    "class.street_address": "endereco", "class.location": "endereco",
    "class.date_of_birth": "perfil", "class.age": "perfil", "class.gender": "perfil", "class.marital_status": "perfil",
    "class.compensation": "perfil", "class.employment_status": "perfil",
    "class.health_data": "sensivel",
}
ORDEM_CATEGORIA = ["sensivel", "identificacao", "contato", "endereco", "perfil"]   # a mais restritiva vence
VALORES_DADO_PESSOAL = {"dado_pessoal": ORDEM_CATEGORIA, "contem_dado_pessoal": ["sim"], "contem_dado_sensivel": ["sim"]}

# Tags padrão de domínio e responsável (sem acento), ao lado da tag "Pós-venda" do Discover. Ferramentas como o
# genie-ontology-readiness v1.5.0 só reconhecem domínio por chaves padrão (domain, subject_area, data_owner...).
DOMINIO_PADRAO = "pos_venda"
RESPONSAVEL = "financeiro_pos_venda"          # papel responsável pelo domínio (troque aqui e rode aplicar_semantica.py)
TAG_DOMINIO_PADRAO = {
    "domain": "Domínio de negócio do ativo (chave padrão, sem acento). pos_venda = Pós-venda de seguro de vida.",
    "subject_area": "Subdomínio do ativo: cobranca (Cobrança e inadimplência), carteira (Clientes e apólices) ou qualidade (Qualidade de dados).",
    "data_owner": "Responsável (papel) pelo ativo e pelo significado dos dados.",
}
VALORES_DOMINIO_PADRAO = {"domain": [DOMINIO_PADRAO], "subject_area": list(SUB), "data_owner": [RESPONSAVEL]}

# Subdomínio dos ativos da camada principal sem subdomínio na Wiki (ou sem Wiki): visões de apoio do painel de qualidade (dq),
# extratos do Power BI (bi) e metadados da ontologia. Sem isso, a regra TAG01 da conformidade acusa subject_area.
SUB_SEM_WIKI = {"dq": "qualidade", "bi": "cobranca", "ontologia": "cobranca"}
SUB_SEM_WIKI_TABELA = {"bi.qualidade_diaria": "qualidade", "bi.produto": "carteira", "bi.canal_venda": "carteira"}


def categoria_dado_pessoal(coluna):
    """Categoria LGPD da coluna (ou None), pela classificação técnica."""
    cats = {CATEGORIA_DADO_PESSOAL[c] for c in CLASSIFICACAO.get(coluna, []) if c in CATEGORIA_DADO_PESSOAL}
    return next((c for c in ORDEM_CATEGORIA if c in cats), None)
