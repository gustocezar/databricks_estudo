# Painéis financeiros do Pós-venda

Dois públicos, quatro fatos, duas ferramentas. A regra de negócio fica nas metric views de `pos_venda.ontologia`; os
painéis só leem.

| Fato | Metric view | Pergunta que responde |
|---|---|---|
| Carteira em aberto | `mv_carteira_em_aberto` | Quanto está em atraso hoje, com que risco (acima de 60 dias) e como fechou cada mês |
| Recuperação | `mv_recuperacao` | Quanto foi pago (baixas) por mês, forma e faixa de atraso; acumulado no ano |
| Safras | `mv_safra_recuperacao` | Que parte de cada safra de entrada já foi paga |
| Qualidade dos dados | `mv_qualidade_dados` | Quanto do que chega da origem entra nos números (barrados e avisos) |

## Databricks (AI/BI) · publicado

| Painel | Público | Páginas | Link |
|---|---|---|---|
| `pos_venda · KPIs financeiros · Diretoria` | diretor | Visão executiva + uma por fato | [publicado](https://dbc-15c48c79-7aa2.cloud.databricks.com/dashboardsv3/01f1e47bee241a5da58e8c357f99d8f5/published) |
| `pos_venda · KPIs financeiros · Analista` | time de negócio | uma por fato + Filtros (produto, canal, forma) | [publicado](https://dbc-15c48c79-7aa2.cloud.databricks.com/dashboardsv3/01f1e47bee3a1c5ebd180bfff03034a7/published) |

Cada painel tem o botão **Ask Genie** ligado ao espaço Genie do mesmo público.

```bash
cd pos_venda/paineis_financeiros
python3 gerar_paineis.py                                   # gera src/*.lvdash.json + conferência (versões, grade, campos, nomes únicos)
databricks bundle deploy -t dev --profile dbx-workshop    # atualiza e publica os dois painéis (mesmo link)
```

## Power BI · para avaliação

O mesmo conteúdo (mesmas páginas, títulos e números) em um projeto do Power BI Desktop: [powerbi/README.md](powerbi/README.md).
Os números foram conferidos contra o painel do Databricks: 21 de 21 indicadores iguais na foto de 25/12/2026 e de novo 21 de 21
na foto de 09/01/2027, depois da correção de 24/11 (`powerbi/VALORES_DE_REFERENCIA.md`). A reconferência tinha dado 20
de 21; a causa e a correção estão na lição L86.
