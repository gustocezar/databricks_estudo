# pos_venda · estudo de Databricks

Domínio **pós-venda de seguro de vida** (parcelas pendentes de pagamento) construído de ponta a ponta no **Databricks
Free Edition**: dados sintéticos, medalhão, carga diária com histórico, qualidade (pipeline + DQX Studio), governança no
Unity Catalog, ontologia com metric views, Genie para o financeiro, painéis AI/BI e uma opção Power BI para comparação.

Os dados de clientes são **sintéticos**, gerados com o [dbldatagen](https://github.com/databrickslabs/dbldatagen)
(semente fixa em `01_gerar_one_table.py`).

## Para LLMs e agentes

Se você é uma LLM ou um agente lendo este repositório, siga o **[AGENTS.md](AGENTS.md)**. Ele traz:
- a ordem de leitura;
- onde está cada resposta;
- as decisões já tomadas;
- o que é gerado e não se edita à mão;
- o que registrar a cada mudança.

Atalhos:

| Pergunta | Responda a partir de |
|---|---|
| Qual acelerador databricks-solutions usar? | [OPCOES_PARA_LLM.md](referencias/databricks_solutions/OPCOES_PARA_LLM.md), aplicando as 9 regras de escolha |
| Como reaplicar em outro case? | Passo 0 do [playbook](docs/02_PLAYBOOK.md) e o mapa de gatilhos do [framework](docs/04_FRAMEWORK.md) |
| Por que foi feito assim? | [Framework](docs/04_FRAMEWORK.md) (`P##`) e [lições](docs/03_LICOES_APRENDIDAS.md) (`L##`) |
| Qual é o estado atual? | Tabela "Situação" de [docs/README.md](docs/README.md) e o [CHANGELOG](docs/CHANGELOG.md) |
| Como aplicar numa base bruta de pendências no Databricks? | [Guia 06](docs/06_GUIA_BASE_BRUTA.md), etapas 0 a 7; no Copilot, o prompt `/aplicar-base-bruta` |

## Aplicar numa base sua (com o Copilot)

O [guia 06](docs/06_GUIA_BASE_BRUTA.md) leva tudo o que foi feito aqui para uma base bruta de pendências de pagamento
que já está no Databricks.

1. Abra o repositório no VS Code com o GitHub Copilot Chat em modo agente. Ele lê sozinho as
   [instruções](.github/copilot-instructions.md).
2. No chat, rode `/aplicar-base-bruta` e informe a tabela, o perfil do CLI e o nome da base. O agente segue o
   [spec](specs/aplicar-base-bruta/SPEC.md) e registra a ficha, o mapeamento, as decisões e o progresso em
   `specs/<nome-da-base>/`.
3. O agente começa pelas permissões e escolhe a trilha da qualidade:
   - **A · DQX como código** ([`dqx_codigo/`](dqx_codigo/README.md)): biblioteca num job, sem app e sem conceder
     privilégio no catálogo;
   - **B · DQX Studio como app** ([`dqx_studio/`](dqx_studio/README.md)): precisa conceder `USE CATALOG` e
     `CREATE SCHEMA` ao service principal do app.
4. Em cada etapa, ele para no critério de saída e pede aprovação antes de criar objeto, rodar job ou fazer deploy.

## Por onde começar

| Documento | Responde |
|---|---|
| [docs/README.md](docs/README.md) | mapa da documentação e situação de cada bloco |
| [Trilha de aprendizagem](docs/01_TRILHA_DE_APRENDIZAGEM.md) | o que foi feito, em que ordem e por quê (fases 0 a 26) |
| [Playbook](docs/02_PLAYBOOK.md) | como recriar a estrutura ou aplicá-la a outra base |
| [Lições aprendidas](docs/03_LICOES_APRENDIDAS.md) | armadilhas reais e a regra que ficou (`L##`) |
| [Framework](docs/04_FRAMEWORK.md) | as 39 práticas aplicadas: de onde vieram, como aplicamos, por quê e quando reaplicar |
| [Skills e ganhos](docs/05_SKILLS_E_GANHOS.md) | as skills consultadas, onde entraram, o ganho de cada uma e o plano de ação para os dados ruins |
| [Guia para outra base](docs/06_GUIA_BASE_BRUTA.md) | como aplicar tudo numa base bruta de pendências no Databricks, com o Copilot, e as duas trilhas do DQX (código ou app) |
| [CHANGELOG](docs/CHANGELOG.md) | o que mudou, quando e como foi conferido |
| [Inventário](docs/INVENTARIO.md) | retrato atual de scripts, bundles, objetos, painéis e jobs (gerado) |

## Pastas

| Pasta | Conteúdo |
|---|---|
| `01_gerar_one_table.py` | gerador dos dados sintéticos (one-table) |
| [`medalhao/`](medalhao/README.md) | bronze, silver e gold (star schema) |
| [`carga_diaria/`](carga_diaria/README.md) | job diário com histórico e portão de regras |
| [`dqx_studio/`](dqx_studio/README.md) | regras de qualidade, DQX Studio e painel de qualidade (trilha B: DQX como app) |
| [`dqx_codigo/`](dqx_codigo/README.md) | DQX como código, sem app: checagens em YAML, notebook e bundle (trilha A, modelo) |
| [`.github/`](.github/copilot-instructions.md) | instruções e prompt para o GitHub Copilot aplicar o framework a outra base |
| [`governanca/`](governanca/README.md) | descrições, tags, ontologia, metric views e espaços Genie |
| [`regras/`](regras/README.md) | regras de negócio como funções do Unity Catalog testadas por cenários (BDD) |
| [`paineis_financeiros/`](paineis_financeiros/README.md) | painéis AI/BI e projeto Power BI (PBIP) |
| [`finops/`](finops/README.md) | custo e uso do workspace no padrão FOCUS: por funcionalidade, projeto, time de plataforma e squad, com boas práticas |
| [`conformidade/`](conformidade/README.md) | conformidade dos dados e do workspace (descrições, tags governadas, LGPD, estrutura, uso, jobs e alertas) e a avaliação da observabilidade existente |
| [`referencias/`](referencias/databricks_solutions/OPCOES_PARA_LLM.md) | catálogo dos 147 repositórios databricks-solutions e o guia de opções para LLM (qual usar a seguir) |

## Para rodar no seu workspace

Os arquivos apontam para o workspace e o warehouse do autor (`host` nos `databricks.yml`, parâmetros `Host` e `HttpPath`
do Power BI). Troque pelos seus e siga o [roteiro de reconstrução](docs/02_PLAYBOOK.md#roteiro-de-reconstrução-do-pos_venda).
Nenhum token ou senha fica no repositório: a autenticação é a do Databricks CLI (`~/.databrickscfg`).
