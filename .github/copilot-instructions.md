# Instruções para o GitHub Copilot

As instruções deste repositório ficam num só lugar, o [AGENTS.md](../AGENTS.md), que vale para qualquer agente. Leia-o
antes de responder ou mudar código. Os pontos que mais importam:

- **Idioma:** português do Brasil em documentos, código, comentários e mensagens de commit.
- **Aplicar o framework a outra base** (por exemplo, uma base bruta de pendências de pagamento no Databricks): siga
  [docs/06_GUIA_BASE_BRUTA.md](../docs/06_GUIA_BASE_BRUTA.md), etapa por etapa, com o critério de saída de cada uma.
  O prompt pronto é `/aplicar-base-bruta` ([prompts/aplicar-base-bruta.prompt.md](prompts/aplicar-base-bruta.prompt.md)).
- **Qualidade com DQX:** há duas trilhas separadas. A trilha A é o DQX como código ([dqx_codigo/](../dqx_codigo/README.md)),
  sem app e sem conceder privilégio no catálogo. A trilha B é o DQX Studio como app ([dqx_studio/](../dqx_studio/README.md)).
  Escolha pela etapa 0 do guia.
- **Peça aprovação antes de** criar ou recriar objetos, rodar job, fazer deploy, ligar agenda, instalar app, commit ou
  push. Nunca escreva na base de origem.
- **Não edite arquivos gerados**: mude o gerador (tabela "Fonte × gerado" do AGENTS.md).
- **Cite a origem** de cada decisão: prática `P##` ([framework](../docs/04_FRAMEWORK.md)), módulo `M#`
  ([playbook](../docs/02_PLAYBOOK.md)) ou lição `L##` ([lições](../docs/03_LICOES_APRENDIDAS.md)). Não invente número,
  prática nem fonte.
- **Repositório público:** nunca envie token, senha, e-mail ou caminho local.
