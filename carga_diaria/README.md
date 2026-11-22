# pos_venda · carga diária (bronze → silver → gold, com fato histórica)

Simula um sistema de origem que, **todo dia**, envia eventos de pagamentos pendentes de seguro de vida, e processa esses
eventos até o star schema. Dados 100% sintéticos.

```
                   [0] portão das regras ── 36 cenários BDD contra pos_venda.regras.*; se falhar, nada roda
                                                         │
fonte.apolices ──► [1] gerar eventos ──► bronze.pagamentos_pendentes_eventos   (append-only)
 (cadastro)            (notebook)                       │
                                                         ▼
                              [2] pipeline Lakeflow ─► silver.pendencia_evento   todos os eventos, padronizados
                                                      ├► silver.pendencia_hist     HISTÓRICA (SCD2): 1 linha por versão
                                                      └► silver.pendencia_atual    estado atual (SCD1)
                                                         │
                              [3] dimensões (notebook) ─► gold.dim_* + bridge_apolice_cobertura   (PK declarada)
                              [4] fato (notebook) ──────► gold.fact_pagamento_pendente_snapshot   (PK declarada)
```

## O que cada dia traz

- `NOVA`: parcela que venceu ontem e não foi paga entra na carteira de pendentes;
- `ATUALIZACAO`: mudança de status de cobrança (pendente → em cobrança → promessa / negociado / cobrança externa);
- `BAIXA`: pagamento da parcela, a pendência sai da carteira;
- cerca de 0,5% das linhas chegam duplicadas (defeito proposital, tratado na silver).

O gerador é determinístico (hash) e idempotente: dias já carregados no bronze são ignorados.

## Tabelas históricas

| Camada | Tabela | O que guarda |
|---|---|---|
| Silver | `pendencia_evento` | cada evento recebido, padronizado (CPF, RG, telefone, CEP, UF) + flags `dq_*` |
| Silver | `pendencia_hist` (SCD2) | 1 linha por versão da pendência, com `__START_AT` e `__END_AT` (vigência `[início, fim)`). Nova versão quando o status muda ou a parcela é paga |
| Silver | `pendencia_atual` (SCD1) | último estado de cada pendência |
| Gold | `fact_pagamento_pendente_snapshot` | **1 linha por pendência em aberto por dia**. PK = `(data_referencia_sk, pendencia_id)` |

Na fato, dias de atraso, multa, juros, faixa de atraso e tentativas são recalculados **as-of** o dia da foto.
Faixa, multa, juros e total vêm das funções `pos_venda.regras.*` ([regras/README.md](../regras/README.md)); a silver
valida o CPF com `regras.cpf_valido` e a barreira barra eventos cujos valores fogem das funções (`valores_fora_da_regra`).
O simulador da origem (`10_gerar_eventos`) **não** usa as funções: ele imita o sistema externo, com os erros injetados.
Dá para ver a carteira de qualquer data, o aging e a evolução no tempo. Uma pendência paga some da foto a partir do dia da baixa.

## Chaves (PK / FK)

As constraints do Unity Catalog são **informativas** (não são impostas pelo motor, servem de documentação e de dica ao otimizador).

- PK em todas as dimensões, na ponte (`apolice_sk + cobertura_sk`) e na fato (`data_referencia_sk + pendencia_id`);
- 15 FK da fato para as dimensões (`dim_data` em 5 papéis: referência, vencimento, emissão, entrada, última tentativa);
- chaves substitutas = `xxhash64(chave de negócio)`: estáveis entre execuções, então a fato histórica continua válida
  quando as dimensões são reescritas;
- na silver as chaves lógicas são `pendencia_id` (atual) e `pendencia_id + __START_AT` (histórica), definidas no Auto CDC.

## Rodar

```bash
cd pos_venda/carga_diaria
databricks bundle deploy -t dev --profile dbx-workshop            # sempre que mudar algo

# uma vez: schemas e cadastro de apólices
databricks bundle run carga_setup -t dev --profile dbx-workshop

# backfill dos 6 meses (ou qualquer intervalo)
databricks bundle run carga_diaria -t dev --profile dbx-workshop --params data_inicio=2026-05-19,data_fim=2026-11-18

# um dia específico (sob demanda); sem --params usa o dia da execução
databricks bundle run carga_diaria -t dev --profile dbx-workshop --params data_inicio=2026-11-19,data_fim=2026-11-19
```

Repetir o mesmo dia não duplica nada: o bronze ignora dias já carregados, o Auto CDC absorve eventos repetidos e a fato
apaga e regrava só os dias do intervalo.

## Ligar e desligar a agenda diária (05:00, America/Sao_Paulo)

A agenda começa **PAUSED** (desligada): a carga só roda quando você manda.

```bash
databricks bundle deploy -t dev --profile dbx-workshop --var="carga_schedule_status=UNPAUSED"   # liga
databricks bundle deploy -t dev --profile dbx-workshop                                          # desliga (volta ao padrão PAUSED)
```

## Regenerar os notebooks e o SQL

Os notebooks e o SQL do pipeline saem de `gerar_carga.py`:

```bash
python3 gerar_carga.py && databricks bundle deploy -t dev --profile dbx-workshop
```

## Limites e observações

- Free Edition: só serverless, até 5 tarefas de job simultâneas, um pipeline ativo por tipo
  (<https://docs.databricks.com/aws/en/getting-started/free-edition-limitations>).
- A simulação começa vazia em 2026-05-19, então a carteira em aberto cresce no início (efeito da data de partida).
- Dimensões de cliente e apólice só têm quem já teve alguma pendência.
- Não há pendências novas no 1º, 30º e 31º de cada mês (vencimentos vão de 1 a 28 e a pendência entra no dia seguinte).
- O medalhão estático anterior (`pos_venda/medalhao`, schemas `*_sql` e `*_ldp`) continua implantado e não é usado por esta carga.
