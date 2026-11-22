# Documentação · pos_venda

Domínio **pós-venda de seguro de vida** (parcelas pendentes de pagamento) no Databricks Free Edition: dados sintéticos,
medalhão, carga diária com histórico, qualidade (pipeline + DQX Studio), governança no Unity Catalog, ontologia com metric
views, Genie para o financeiro e painéis AI/BI.

## O que ler

| Documento | Para quem | Responde |
|---|---|---|
| [01 · Trilha de aprendizagem](01_TRILHA_DE_APRENDIZAGEM.md) | quem quer entender o projeto | o que fizemos, em que ordem, por quê e o que aprendemos em cada fase |
| [02 · Playbook](02_PLAYBOOK.md) | quem vai recriar ou construir outro domínio | perfil da base, módulos com critério de saída, matriz de resiliência, roteiro de reconstrução |
| [03 · Lições aprendidas](03_LICOES_APRENDIDAS.md) | quem vai mexer no código | armadilhas reais e a regra que ficou (códigos `L##`) |
| [CHANGELOG](CHANGELOG.md) | todos | o que mudou, quando e como foi conferido |
| [Inventário](INVENTARIO.md) | todos | retrato atual: scripts, bundles, objetos do catálogo, painéis, Genie, jobs, apps e cobertura de metadados (gerado) |

Documentos de cada bloco continuam nas pastas: [medalhao](../medalhao/README.md), [carga_diaria](../carga_diaria/README.md),
[dqx_studio](../dqx_studio/README.md), [painel de qualidade](../dqx_studio/painel/README.md),
[roteiro da demonstração](../dqx_studio/demo/ROTEIRO.md), [governança](../governanca/README.md),
[triagem da avaliação da Genie](../governanca/genie/avaliacao_boas_praticas/TRIAGEM.md),
[regras de negócio (BDD)](../regras/README.md), [prontidão da ontologia](../governanca/ontologia_readiness/RESULTADO.md),
[painéis financeiros e opção Power BI](../paineis_financeiros/README.md).

## Situação em 22/11/2026

| Bloco | Situação |
|---|---|
| Dados, medalhão e carga diária | pronto; job `pos_venda_carga_diaria` implantado e **pausado**; dados até **25/12/2026** (dia carregado em 22/11 pelo job completo) |
| Qualidade (barreira, DQX Studio, painel) | pronto; o app `dqx-studio` para sozinho após 24 h: `databricks apps start dqx-studio` antes de demonstrar |
| Avaliação contínua do Studio | pronto e **pausado**: 12 tabelas às 06:30; ligar junto com o job (`registro_studio.py ligar`); o job liga o app |
| Governança e metadados | pronto; 1.977 de 1.977 colunas principais (com o schema `bi`) e 682 de 682 legadas descritas; `dado_pessoal` em 380 colunas principais e 152 legadas, 0 sem tag (sem máscara, por decisão: a validação usa os valores reais); auditoria em 28 s |
| Ontologia, metric views, Genie e painéis financeiros | pronto; Genie 29/29 nas perguntas de avaliação (com simulações pelas funções de regra); painéis da diretoria e do time de negócio com **uma página por fato** |
| Opção Power BI (avaliação) | gerada: schema `pos_venda.bi` (8 visões das metric views) + projeto PBIP com os 2 relatórios; 102 arquivos válidos nos esquemas oficiais; paridade 21/21 com o painel; **não aberta no Power BI Desktop** (precisa de Windows) |
| Ontologia sem identificadores pessoais | pronto: nenhum `cliente_id` no schema `ontologia` (ligações por `cliente_sk`) |
| Regras de negócio (BDD) | pronto: 5 funções em `pos_venda.regras`, 36/36 cenários, portão no job diário, silver/barreira/gold/Genie/DQX Studio usando as funções, paridade 100% |
| Prontidão para a Genie Ontology | **92,7 (Optimized)**, com histórico no Lakebase (`avaliar.py`); domínio e responsável por tags padrão; schemas legados descritos (682/682) e com dado pessoal marcado; histórico: ids 1–3 |
| Versionamento | no GitHub: [gustocezar/databricks_estudo](https://github.com/gustocezar/databricks_estudo) (público, branch `main`); depois de cada mudança, `git add -A && git commit && git push` |

## Como manter esta documentação (incremental)

A documentação acompanha o código. A cada mudança no projeto:

1. **CHANGELOG:** acrescente uma entrada no topo do dia, pelo modelo do próprio arquivo (o que, por quê, onde, conferência, docs atualizadas).
2. **Inventário:** rode `python3 docs/gerar_inventario.py` (só leitura; não usa o warehouse). Não edite `INVENTARIO.md` à mão.
3. **Trilha:** se a mudança abriu uma etapa nova, acrescente uma fase no fim; se completou uma fase "em andamento", troque o texto pelo resultado.
4. **Playbook:** se mudou um passo, um comando ou um critério de saída, atualize o módulo (M#) e o roteiro de reconstrução.
5. **Lições:** se apareceu uma armadilha nova, crie o próximo `L##` no tema certo e cite o código no CHANGELOG.
6. **Situação** (tabela acima): atualize a linha do bloco.

Regra de ouro: uma mudança só está pronta quando o critério de saída do módulo passou **e** o CHANGELOG tem a conferência.
