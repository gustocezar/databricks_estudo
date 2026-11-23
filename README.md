# pos_venda · estudo de Databricks

Domínio **pós-venda de seguro de vida** (parcelas pendentes de pagamento) construído de ponta a ponta no **Databricks
Free Edition**: dados sintéticos, medalhão, carga diária com histórico, qualidade (pipeline + DQX Studio), governança no
Unity Catalog, ontologia com metric views, Genie para o financeiro, painéis AI/BI e uma opção Power BI para comparação.

Os dados de clientes são **sintéticos**, gerados com o [dbldatagen](https://github.com/databrickslabs/dbldatagen)
(semente fixa em `01_gerar_one_table.py`).

## Por onde começar

| Documento | Responde |
|---|---|
| [docs/README.md](docs/README.md) | mapa da documentação e situação de cada bloco |
| [Trilha de aprendizagem](docs/01_TRILHA_DE_APRENDIZAGEM.md) | o que foi feito, em que ordem e por quê (fases 0 a 22) |
| [Playbook](docs/02_PLAYBOOK.md) | como recriar a estrutura ou aplicá-la a outra base |
| [Lições aprendidas](docs/03_LICOES_APRENDIDAS.md) | armadilhas reais e a regra que ficou (`L##`) |
| [Framework](docs/04_FRAMEWORK.md) | as 29 práticas aplicadas: de onde vieram, como aplicamos, por quê e quando reaplicar |
| [CHANGELOG](docs/CHANGELOG.md) | o que mudou, quando e como foi conferido |
| [Inventário](docs/INVENTARIO.md) | retrato atual de scripts, bundles, objetos, painéis e jobs (gerado) |

## Pastas

| Pasta | Conteúdo |
|---|---|
| `01_gerar_one_table.py` | gerador dos dados sintéticos (one-table) |
| [`medalhao/`](medalhao/README.md) | bronze, silver e gold (star schema) |
| [`carga_diaria/`](carga_diaria/README.md) | job diário com histórico e portão de regras |
| [`dqx_studio/`](dqx_studio/README.md) | regras de qualidade, DQX Studio e painel de qualidade |
| [`governanca/`](governanca/README.md) | descrições, tags, ontologia, metric views e espaços Genie |
| [`regras/`](regras/README.md) | regras de negócio como funções do Unity Catalog testadas por cenários (BDD) |
| [`paineis_financeiros/`](paineis_financeiros/README.md) | painéis AI/BI e projeto Power BI (PBIP) |
| `referencias/` | catálogo comentado dos repositórios databricks-solutions |

## Para rodar no seu workspace

Os arquivos apontam para o workspace e o warehouse do autor (`host` nos `databricks.yml`, parâmetros `Host` e `HttpPath`
do Power BI). Troque pelos seus e siga o [roteiro de reconstrução](docs/02_PLAYBOOK.md#roteiro-de-reconstrução-do-pos_venda).
Nenhum token ou senha fica no repositório: a autenticação é a do Databricks CLI (`~/.databrickscfg`).
