# SPEC · Aplicar o framework do pos_venda a uma base bruta de pendências

> Versão 1 · 24/11/2026. Este é o **contrato** que um agente de código (o Copilot no VS Code, ou outro) executa.
> Para entender o porquê de cada passo, leia o [guia 06](../../docs/06_GUIA_BASE_BRUTA.md). Para executar, siga
> [TAREFAS.md](modelos/TAREFAS.md) na pasta da sua base.

## Como começar

1. Crie a pasta da base copiando os modelos:
   `mkdir -p specs/<nome> && cp specs/aplicar-base-bruta/modelos/*.md specs/<nome>/`. Os links dos modelos valem a partir
   dessa pasta.
2. Siga `specs/<nome>/TAREFAS.md` de cima para baixo. Cada tarefa tem verificação e saída, e as marcadas com **G** param
   para aprovação.
3. No VS Code, o prompt `/aplicar-base-bruta` faz isso por você. Para retomar, rode o prompt de novo: o agente continua
   da primeira tarefa sem `[x]`.

## 1 · Objetivo

Levar para uma base bruta de pendências de pagamento que já está no Databricks tudo o que o pos_venda tem:
- medalhão com histórico;
- barreira de qualidade e DQX;
- governança;
- camada semântica;
- Genie e painéis;
- custo e conformidade.

Cada passo tem critério de pronto conferível e aprovação humana nos pontos que mudam o workspace.

## 2 · Escopo

**Dentro:**
- as etapas 0 a 8 do guia 06;
- a qualidade por uma de duas trilhas: **A**, DQX como código, ou **B**, DQX Studio como app;
- os registros da base: ficha, mapeamento, decisões e tarefas.

**Fora:**
- mudar a base bruta ou o schema dela;
- conceder privilégio a terceiros;
- abrir a Genie a usuários sem a decisão sobre dado pessoal (G7);
- alterar objetos de outros times;
- ligar agendas sem aprovação.

## 3 · Entradas

| Entrada | Exemplo | Quem fornece |
|---|---|---|
| tabela da base bruta | `financeiro.raw.pendencias` | você |
| perfil do Databricks CLI | `meu-workspace` | você |
| nome curto da base | `pendencias_vida` | você |
| catálogo e prefixo de destino | `analytics` + `pend_` | decidido em T0.3 (G1) |
| pasta do código novo | `dominios/<nome>/` (padrão) ou outro repositório | decidido em T0.3 (G1) |

## 4 · Saídas

| Saída | Onde |
|---|---|
| ficha, mapeamento, decisões e progresso | `specs/<nome>/` (cópia de [modelos/](modelos/)) |
| código da base (geradores, notebooks, bundles, checagens) | a pasta do código novo |
| objetos no Databricks | só no catálogo e nos schemas de destino |
| CHANGELOG e lições novas | `specs/<nome>/DECISOES.md` (e o CHANGELOG do projeto novo, se houver) |

## 5 · Restrições (valem em todas as tarefas)

- **R1.** Nunca escreva na base bruta nem no schema dela. Sobre ela, só `SELECT`, `DESCRIBE` e `SHOW`.
- **R2.** Pare e peça aprovação em todo ponto marcado **G** (seção 7). Aprovação vale para aquela tarefa, não para as
  seguintes.
- **R3.** Não marque uma tarefa como feita sem rodar a verificação dela e anotar o resultado em `TAREFAS.md`.
- **R4.** Cite a origem de cada decisão: prática `P##`, módulo `M#`, lição `L##` ou arquivo. Se o repositório não
  responde, diga isso e registre em `DECISOES.md`; não invente.
- **R5.** Não edite os módulos do pos_venda: copie para a pasta do código novo e troque os parâmetros (catálogo, tabelas,
  colunas, domínios).
- **R6.** Repositório público: nunca grave token, senha, e-mail ou caminho local. Varra antes de cada commit (L70).
- **R7.** Agendas nascem pausadas (P02). Ligar é a aprovação G9.
- **R8.** Se a cota ou a permissão acabar, pare e registre; não tente contornar (L01).

## 6 · Critérios de aceite por etapa

| Etapa | Pronto quando | Prática |
|---|---|---|
| **E0 · Acesso** | perfil e usuário confirmados; grants da base e do destino anotados na ficha; destino e trilha do DQX decididos (G1, G2) | P01, P02, P38 |
| **E1 · Ficha** | as perguntas da ficha respondidas com números do perfil (contagens, nulos, duplicatas, domínios); perfil pronto (A a E) escolhido (G3) | Passo 0 |
| **E2 · Mapeamento** | todo conceito do modelo com coluna, derivação ou "não se aplica"; regras de erro e aviso com nome estável (G4) | P05, P09 |
| **E3 · Medalhão** | cenários de regra 100%; aptos + quarentena = bronze na janela; fato = silver na foto do dia; job SUCCESS com agenda pausada (G5, G6) | P05 a P10, P20 |
| **E4A · DQX código** | job SUCCESS numa janela conhecida; erros do DQX = quarentena da barreira na mesma janela; toda regra em `dq_metricas_regras`, mesmo com zero | P11, P12, P38 |
| **E4B · DQX Studio** | pré-requisitos confirmados (G8); `registro_studio.py executar` SUCCESS com nota; reprovados = quarentena da barreira | P11, P12 |
| **E4 · Plano de ação** | cada regra com reprovação tem dono, ação e critério de pronto | 05 · plano de ação |
| **E5 · Governança e semântica** | 100% das colunas descritas e com tags; `dado_pessoal` marcado; ontologia sem identificadores e com membro explícito para chave órfã (L87); metric views com início e fechamento no total (L86) | P13 a P19 |
| **E6 · Consumo** | Genie com perguntas de avaliação e gabarito em SQL, acerto igual ou acima da meta (G7); painel e BI batendo indicador a indicador | P21 a P26 |
| **E7 · Operação** | matriz de resiliência preenchida; custo com tag de projeto e time; conformidade rodando com histórico; CHANGELOG com as conferências | P28 a P37 |
| **E8 · Sustentação** (antes de ligar as agendas, T7.4) | execuções por job, tarefa e pipeline batem com as tabelas de sistema; linha de base com mínimo de execuções ou metas marcadas como provisórias; SLA com hora meta e consumidor; alerta pausado com até 4 disparos por dia; manual com runbook por tarefa | P28, P40 |

## 7 · Pontos de aprovação humana (gates)

| Gate | Antes de |
|---|---|
| **G1** | definir catálogo, schemas e pasta do código novo |
| **G2** | escolher a trilha do DQX (A ou B) |
| **G3** | aceitar a ficha e o perfil pronto |
| **G4** | aceitar o mapeamento e a lista de regras de erro e aviso |
| **G5** | criar o primeiro objeto no Databricks (schema, tabela, função, pipeline) |
| **G6** | qualquer `databricks bundle deploy`, `bundle run` ou execução de job |
| **G7** | criar ou abrir espaço Genie (e decidir máscara para dado pessoal real) |
| **G8** | instalar app, criar service principal ou projeto Lakebase (trilha B) |
| **G9** | ligar agendas ou fazer commit e push |

## 8 · Regra de escolha da trilha do DQX (G2)

- **Trilha B:** só se você puder conceder ao service principal do app `USE CATALOG` e `CREATE SCHEMA` no catálogo
  (dono ou `MANAGE`), e houver vaga de app, Lakebase e service principal.
- **Trilha A:** em qualquer outro caso.
- **Em comum:** as regras têm os mesmos nomes da barreira nas duas, e a migração de A para B pode vir depois.

## 9 · Riscos conhecidos

| Risco | Lição |
|---|---|
| cota esgotada no meio da tarefa | L01 |
| recriar view apaga tags e Wiki | L31 |
| mudar regra de cálculo sem paridade | L56 |
| deploy de bundle ignora arquivos do `.gitignore` | L74 |
| regra em zero confundida com falta de dado | L84 |
| soma de início ou fechamento por grupo | L86 |
| filtro de nulo esconde chave órfã na Genie | L87 |
| `is_in_list` do DQX lê valores de texto como colunas | L88 |
