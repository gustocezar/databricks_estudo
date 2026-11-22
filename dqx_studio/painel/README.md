# pos_venda · Painel de qualidade de dados (AI/BI)

Painel publicado: **pos_venda · Qualidade de dados**
https://dbc-15c48c79-7aa2.cloud.databricks.com/dashboardsv3/01f1e410f7f419f19ad6d416805a9bb2/published

| Página | O que mostra |
|---|---|
| **Visão geral** | recebidos, barrados, % barrados e pico de órfãs na fato (com tendência diária); barrados por dia com marcos dos incidentes; barrados por motivo; avisos que passam (% de e-mail ausente, CPF inválido, duplicatas, CEP); órfãs da fato por dia; mapa de calor motivo × semana |
| **DQX Studio · evolução** | linhas avaliadas, em erro e com aviso; reconciliação da quarentena (100% reprovada no Studio); erros e avisos por semana e camada; mapa de calor das regras violadas por semana; tabela das execuções completas |
| **Dados não aptos** | eventos na quarentena, valor retido (R$) e apólices afetadas; os eventos barrados com o motivo e o cadastro do cliente; as linhas que o Studio reprovou, com a regra e a mensagem |
| **Filtros** (globais) | dia, motivo da rejeição, camada do Studio |

## Arquivos

| Arquivo | Para quê |
|---|---|
| `views_painel.sql` | 6 views em `pos_venda.dq` (`v_painel_*`) que juntam as métricas do pipeline e as tabelas do Studio (`main.dqx_studio`) |
| `gerar_painel.py` | gera `src/pos_venda_qualidade.lvdash.json` e confere a estrutura (campos × encodings, versões, grade de 12 colunas) |
| `aplicar_e_testar.py` | cria as views e testa cada consulta do painel como o AI/BI executa (catalog `pos_venda`, schema `dq`), com checagens dos números da demonstração |
| `databricks.yml`, `resources/` | bundle do painel (`dataset_catalog: pos_venda`, `dataset_schema: dq`) |

## Como atualizar

```bash
cd pos_venda/dqx_studio/painel
python3 aplicar_e_testar.py                         # views + testes (precisa do warehouse ligado)
python3 gerar_painel.py                             # só se mudar o layout
databricks bundle deploy -t dev --profile dbx-workshop   # publica (mesmo link)
```

## Observações

- O painel lê as views; sem elas, os widgets mostram erro. As views foram escritas mas **ainda não criadas**: na hora
  da publicação o Free Edition tinha batido a cota diária de computação. Rode `aplicar_e_testar.py` quando a cota renovar.
- A página do Studio usa as execuções **com todas as linhas** do replay (uma por semana e camada). Ficam de fora as
  execuções com amostra, o teste inicial e as 2 marcadas como falso positivo. Execuções agendadas futuras não entram,
  porque a numeração de semana do replay não vale para elas.
