# Régua de 12 itens do Genie Workbench (`genie-agent-scanner`) · 22/11/2026

O [genie-agent-scanner](https://github.com/databricks-solutions/technical-services-solutions/tree/main/genie/genie-agent-scanner)
(commit `69230dd`) aplica aos espaços Genie a mesma régua de 12 itens do Genie Workbench, sem instalar o app. O cálculo
não usa IA e só lê: um `GET` no espaço e outro nos metadados do Unity Catalog de cada fonte. O `optimize.py`, que grava
no espaço, não foi usado.

Relatórios: [`scan_analista.md`](scan_analista.md) e [`scan_diretor.md`](scan_diretor.md), com os JSON ao lado.

## Nota

| Espaço | Fontes | Nota | Maturidade |
|---|---|---|---|
| Analista financeiro | 2 tabelas + 4 metric views | **8/12** | Not Ready |
| Diretor financeiro | 4 metric views | **8/12** | Not Ready |

O teto sem o Workbench é **10/12**: os itens 11 e 12 exigem uma rodada de otimização do próprio Workbench. Para chegar a
*Ready to Optimize*, faltam dois itens.

## Triagem por item

| Item | Resultado | Veredito |
|---|---|---|
| 1 Fontes de dados · 2 Descrição das tabelas · 6 De 1 a 12 fontes · 9 Correspondência de valores · 10 Dez ou mais perguntas de avaliação | PASS | Confirmado (14 e 15 perguntas de avaliação; 29/29 certas na última avaliação) |
| 3 Descrição das colunas | FAIL: 0/32 e 0/26 | **Falso positivo para este projeto.** A régua só conta descrições gravadas no próprio espaço (`column_configs`). As colunas têm descrição no Unity Catalog (100%) e nas metric views (`comment` de cada dimensão e medida), que é o que a Genie lê. Copiar as descrições para o espaço faria passar, mas duplicaria a fonte da verdade |
| 5 Especificação de junções | FAIL: 0 junções | **Não se aplica na prática.** As metric views já trazem as junções dentro. As 2 tabelas do analista (`ontologia.pendencia` e `gold.dq_barrados_por_motivo_dia`) não se relacionam: uma é a pendência, a outra conta eventos barrados por motivo de qualidade |
| 11 Rodada de otimização · 12 Acerto de 85% ou mais | FAIL | **Fora do alcance sem o Workbench**, que ocuparia a última vaga de app do Free Edition. A avaliação própria do projeto (29/29) cobre a intenção |
| 4 Instruções em texto | WARN: 2.086 e 2.090 caracteres | **Real e fácil.** Passam um pouco do limite recomendado de 2.000 |
| 7 Oito ou mais exemplos de SQL | WARN: 8 e 9 exemplos, nenhum com `usage_guidance` | **Real.** Acrescentar a orientação de uso a cada exemplo e chegar a 10 |
| 8 Trechos de SQL | WARN: 4 funções, nenhum filtro, medida ou expressão | **Real, de pouco ganho.** As medidas vêm das metric views. Um filtro "foto mais recente" seria o candidato |

**O que fazer:** nada foi mudado nos espaços. Os itens 4, 7 e 8 são ajustes em `governanca/genie.py`, mas cada mudança
nas instruções precisa ser seguida da avaliação (29 perguntas), para não perder acertos. Fica como proposta.

## Como rodar

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/databricks-solutions/technical-services-solutions tss
git -C tss sparse-checkout set genie/genie-agent-scanner
python3 -m venv .venv-scan && .venv-scan/bin/pip install "databricks-sdk>=0.20"
.venv-scan/bin/python tss/genie/genie-agent-scanner/scripts/scan.py --space-id <id> --profile dbx-workshop \
  --json-out scan_<espaco>.json --md-out scan_<espaco>.md
```

Os ids dos espaços estão em [`../espacos.json`](../espacos.json).
