# Auditoria Power BI on Databricks (`pba`) · 22/11/2026

O [powerbi-analyzer](https://github.com/databricks-solutions/powerbi-analyzer) (`pba`, commit `f67bebf`) confere o
projeto contra as 42 regras da cheat sheet *Power BI on Databricks best practices*, nos dois lados:

- **`pba pbix`**: o modelo semântico, sem credencial;
- **`pba databricks`**: warehouse, histórico de consultas e catálogo.

Os relatórios completos estão em [`pba_powerbi.md`](pba_powerbi.md) e [`pba_databricks.md`](pba_databricks.md). Abaixo,
a triagem: o que vale e o que o `pba` não conseguiu avaliar.

## Resultado

| Lado | Nota | Achados |
|---|---|---|
| Power BI (modelo) | 80/100 | 2 informativos: IN-003 e IN-008 |
| Databricks | 75/100 | 2 avisos e 2 informativos, todos sobre o warehouse (SS-005, 006, 009, 010) |

## Triagem

| Regra | O que o `pba` disse | Veredito |
|---|---|---|
| IN-003 Modelos compostos | As 8 tabelas usam o mesmo modo (importação) | **Decisão do projeto.** A maior tabela tem 942 mil linhas, e a importação atende. Composto só faria sentido com a carteira consultada ao vivo |
| IN-008 Parâmetros de ambiente | Nenhum parâmetro para trocar a conexão | **Falso positivo.** O modelo tem os parâmetros `Host` e `HttpPath`, mas o leitor de PBIP do `pba` não lê parâmetros (devolve a lista vazia) |
| SS-005, SS-006 Escala do warehouse | `max_clusters=1`; 121 consultas esperaram mais de 1 s, 5 mais de 5 s | **Limite do Free Edition.** O warehouse tem 1 cluster fixo. As filas vêm das consultas do próprio projeto (scripts, painéis, avaliações da Genie); o Power BI ainda não consultou |
| SS-009 Tamanho inicial | 2X-Small com fila | **Limite do Free Edition.** Não dá para escolher o tamanho |
| SS-010 Monitorar por tabelas de sistema | 214 eventos de escala sem ajuste de mínimo e máximo | **Limite do Free Edition.** Não há o que ajustar |
| RD-005, 006, 008, 009, 011 Desenho do modelo | Aprovadas | **Confirmado.** Avaliadas a partir do modelo: sem relação muitos-para-muitos, sem coluna ou tabela calculada, DAX sem padrões ineficientes, Power Query sem transformação a empurrar para SQL. RD-002 a 004 tratam de DirectQuery, que o modelo não usa |
| RD-001, RD-010 Visuais e segmentações por página | Aprovadas | **Não avaliadas de fato.** O leitor de PBIP não extrai visuais. Conferimos à parte: a página com mais visuais é a *Visão executiva* da diretoria, com 13 (12 consultam o modelo e 1 é caixa de texto), no limite de 12 da regra RD-001; nenhuma página tem segmentação |
| DP-001 a DP-010 Preparo de dados | Todas aprovadas | **Não avaliadas de fato.** O `pba` só reconhece as tabelas do Power BI pelo histórico de consultas (`client_application` Power BI), e o Power BI ainda não consultou o warehouse. Além disso, lê `rely` e `key_columns` de `information_schema.table_constraints`, que não tem essas colunas, então a DP-004 nunca veria o `RELY` |

**O que fizemos com isso:** a regra DP-004 (`RELY` nas chaves) foi aplicada à mão, com prova de unicidade e medição antes
e depois: ver [`governanca/aplicar_rely.py`](../../../governanca/aplicar_rely.py) e a revisão de 22/11. Vale rodar o
`pba databricks` de novo depois que o Power BI atualizar o modelo pela primeira vez, porque aí o histórico existirá.

## Como rodar

O `pba` não está no PyPI, e a instalação pelo Git falha com o hatchling atual: o `force-include` dos modelos duplica um
arquivo no wheel. Fixe uma versão anterior do hatchling:

```bash
uv venv --python 3.12 .venv-pba
echo "hatchling<1.27" > /tmp/restricoes.txt
uv pip install --python .venv-pba/bin/python --build-constraint /tmp/restricoes.txt git+https://github.com/databricks-solutions/powerbi-analyzer
```

Lado Power BI. O `pba` só lê o modelo em `model.bim` (TMSL), e o projeto está em TMDL. O gerador escreve um `model.bim`
equivalente, fora de `projeto/`:

```bash
cd pos_venda/paineis_financeiros/powerbi
python3 gerar_powerbi.py bim                                    # auditoria/modelo_bim/model.bim (fora do Git)
.venv-pba/bin/pba pbix auditoria/modelo_bim --out auditoria/pba_powerbi.md
```

Lado Databricks. O `pba` espera um perfil com token fixo, e o perfil `dbx-workshop` usa OAuth. O invólucro
[`pba_oauth.py`](pba_oauth.py) passa o token OAuth ao conector SQL:

```bash
.venv-pba/bin/python auditoria/pba_oauth.py databricks --profile dbx-workshop --warehouse-id 5f010b8396e591fb \
  --catalog pos_venda.gold --catalog pos_venda.bi --out auditoria/pba_databricks.md
```

Só leitura: consulta `system.query.history`, `system.compute.warehouse_events`, `information_schema` e roda
`DESCRIBE` nas tabelas. Levou 60 s.
