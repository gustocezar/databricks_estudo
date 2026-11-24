# Tarefas · <nome da base>

> Copiado de `specs/aplicar-base-bruta/modelos/TAREFAS.md`. Contrato: [SPEC](../aplicar-base-bruta/SPEC.md).
> Marque `[x]` só depois de rodar a **verificação** e anotar o resultado na linha "Resultado". Tarefa com **G#** para e
> pede aprovação antes de executar (R2).

**Base:** `<catalogo.schema.tabela>` · **Perfil:** `<perfil>` · **Destino:** `<catalogo>.<prefixo>_*` ·
**Código:** `<pasta>` · **Trilha DQX:** A / B

## E0 · Acesso e permissões

- [ ] **T0.1** Confirmar perfil e usuário.
  - Verificação: `databricks current-user me --profile <perfil>` retorna o seu usuário.
  - Saída: FICHA § Ambiente. Resultado:
- [ ] **T0.2** Anotar os grants da base e do destino.
  - Verificação: `SHOW GRANTS ON CATALOG …` e `SHOW GRANTS ON SCHEMA …` gravados na ficha.
  - Saída: FICHA § Permissões. Resultado:
- [ ] **T0.3 · G1** Decidir catálogo, schemas de destino e pasta do código; nunca o schema da base (R1).
  - Verificação: decisão D-001 registrada.
  - Saída: DECISOES. Resultado:
- [ ] **T0.4 · G2** Decidir a trilha do DQX pela regra do SPEC § 8.
  - Verificação: decisão D-002 com os grants que a justificam.
  - Saída: DECISOES. Resultado:

## E1 · Ficha da base

- [ ] **T1.1** Ler a estrutura da base.
  - Verificação: `databricks experimental aitools tools discover-schema <tabela> --profile <perfil>` com colunas e
    tipos copiados para a ficha.
  - Saída: FICHA § Colunas. Resultado:
- [ ] **T1.2** Perfilar a base, só com `SELECT` (R1):
  - linhas por dia de extração;
  - nulos por coluna;
  - chaves duplicadas;
  - domínios de status, forma de pagamento e periodicidade;
  - faixas de datas e valores.
  - Verificação: os números estão na ficha, com a consulta usada.
  - Saída: FICHA § Perfil. Resultado:
- [ ] **T1.3 · G3** Responder às perguntas da ficha e escolher o perfil pronto (A a E do playbook).
  - Verificação: nenhuma pergunta em branco.
  - Saída: FICHA. Resultado:

## E2 · Mapeamento

- [ ] **T2.1** Fazer o de-para de cada conceito do modelo (P05).
  - Verificação: toda linha do MAPEAMENTO tem coluna, derivação ou "não se aplica".
  - Saída: MAPEAMENTO. Resultado:
- [ ] **T2.2** Definir a chegada dos dados: eventos ou foto completa. Se for foto, usar Auto CDC a partir de snapshot.
  - Verificação: decisão D-003.
  - Saída: DECISOES. Resultado:
- [ ] **T2.3 · G4** Listar as regras de erro e de aviso, com nome estável (P09). Usar como base as 11 de
  `dqx_codigo/checks_pendencias.yml`.
  - Verificação: lista no MAPEAMENTO § Regras, cada uma com coluna e expressão.
  - Saída: MAPEAMENTO. Resultado:

## E3 · Medalhão, barreira e regras de negócio

- [ ] **T3.1** Copiar os modelos para a pasta do código (R5) e parametrizar catálogo, tabela de origem e colunas:
  `carga_diaria/`, `medalhao/` e `regras/`.
  - Verificação: `grep -r "pos_venda" <pasta>` só acha comentários ou nada.
  - Saída: código. Resultado:
- [ ] **T3.2** Escrever as funções de regra e os cenários BDD (M10, P20).
  - Verificação: os cenários passam localmente; a paridade com o cálculo atual dá 100% (L56).
  - Saída: código. Resultado:
- [ ] **T3.3 · G5** Criar os schemas e a bronze append-only (P06).
  - Verificação: linhas da bronze = linhas da base na janela de teste.
  - Saída: objetos. Resultado:
- [ ] **T3.4** Silver com a barreira (motivo de rejeição) e a quarentena (P09).
  - Verificação: aptos + quarentena = bronze na janela.
  - Saída: objetos. Resultado:
- [ ] **T3.5** Gold com star schema e fato snapshot diária (P05, P07). Chave órfã ganha membro explícito (L87).
  - Verificação: fato = silver na foto do dia; saldo nunca somado entre dias.
  - Saída: objetos. Resultado:
- [ ] **T3.6 · G6** Fazer o deploy do bundle do job diário (portão → bronze → silver → gold), com a agenda pausada (R7).
  - Verificação: run SUCCESS e portão com 100% dos cenários.
  - Saída: job. Resultado:

## E4 · Qualidade: siga só a trilha escolhida em T0.4

### Trilha A · DQX como código

- [ ] **T4A.1** Gerar regras candidatas com `DQProfiler` e `DQGenerator` numa amostra e revisar
  ([dqx_codigo/README.md](../../dqx_codigo/README.md)).
  - Verificação: candidatas aceitas ou recusadas no MAPEAMENTO § Regras.
  - Resultado:
- [ ] **T4A.2** Copiar `dqx_codigo/` e adaptar o YAML: colunas, domínios, catálogo das funções; mesmos nomes da barreira.
  - Verificação: `python3 -c "import yaml; yaml.safe_load(open('checks_<nome>.yml'))"` e
    `databricks bundle validate`.
  - Resultado:
- [ ] **T4A.3 · G6** Fazer o deploy e rodar numa janela conhecida (`filtro`).
  - Verificação: run SUCCESS; erros do DQX = quarentena da barreira na janela; toda regra em `dq_metricas_regras`.
  - Resultado:
- [ ] **T4A.4** Montar o painel de qualidade sobre `dq_metricas_regras` (P12).
  - Verificação: todas as consultas do painel testadas no warehouse antes do deploy.
  - Resultado:
- [ ] **T4A.5 · G6** Pôr o DQX como tarefa no fim do job diário.
  - Verificação: run do job inteiro SUCCESS.
  - Resultado:

### Trilha B · DQX Studio como app

- [ ] **T4B.1 · G8** Confirmar os pré-requisitos:
  - vaga de app, Lakebase, warehouse e service principal;
  - `USE CATALOG` e `CREATE SCHEMA` concedidos ao service principal do app.
  - Verificação: grants conferidos com `SHOW GRANTS`.
  - Resultado:
- [ ] **T4B.2 · G8** Instalar o Studio conforme [dqx_studio/README.md](../../dqx_studio/README.md).
  - Verificação: o app RUNNING e o log com "Application startup complete" (L85).
  - Resultado:
- [ ] **T4B.3** Criar as views de janela, as regras e o Registro com as tabelas monitoradas (M5, trilha B).
  - Verificação: as tabelas aparecem no menu do Studio.
  - Resultado:
- [ ] **T4B.4 · G6** Rodar o `registro_studio.py executar`.
  - Verificação: todas as execuções SUCCESS com nota; reprovados = quarentena da barreira.
  - Resultado:

### Comum às duas trilhas

- [ ] **T4.9** Montar o plano de ação: cada regra com reprovação ganha dono, ação e critério de pronto
  ([05](../../docs/05_SKILLS_E_GANHOS.md)).
  - Verificação: tabela em DECISOES § Plano de ação.
  - Resultado:

## E5 · Governança e semântica

- [ ] **T5.1** Descrever todas as colunas (P13).
  - Verificação: a auditoria de metadados dá 100%.
  - Resultado:
- [ ] **T5.2** Aplicar as tags de domínio, dono e área de negócio, e a tag `dado_pessoal` (P14, P15).
  - Verificação: 0 coluna pessoal sem tag.
  - Resultado:
- [ ] **T5.3** Montar a ontologia sem identificadores pessoais (P17).
  - Verificação: nenhum CPF, nome ou contato nas entidades.
  - Resultado:
- [ ] **T5.4** Criar as metric views, inclusive a de qualidade (P18, P19). Início e fechamento são calculados no total
  (L86).
  - Verificação: cada métrica bate com um SQL de referência.
  - Resultado:

## E6 · Consumo

- [ ] **T6.1 · G7** Criar os espaços Genie por público, com instruções, exemplos e perguntas de avaliação com gabarito
  (P21). Antes, decidir sobre máscara para dado pessoal real.
  - Verificação: todo SQL validado no warehouse.
  - Resultado:
- [ ] **T6.2** Avaliar a Genie e fazer a triagem (P24).
  - Verificação: acerto ≥ meta (anotar a meta em DECISOES).
  - Resultado:
- [ ] **T6.3 · G6** Fazer o deploy dos painéis por público, com uma página por fato (P22). O Power BI é opcional, com
  paridade (P23).
  - Verificação: painel = BI indicador a indicador.
  - Resultado:

## E7 · Operação, custo e conformidade

- [ ] **T7.1** Preencher a matriz de resiliência (P28).
  - Verificação: cada falha conhecida tem sinal e ação.
  - Resultado:
- [ ] **T7.2** Aplicar as tags de projeto e time em jobs, warehouses e apps (P31).
  - Verificação: nenhum custo da base sem dono.
  - Resultado:
- [ ] **T7.3** Rodar a conformidade com histórico (P35, P37).
  - Verificação: regras com meta e sonda das views gravando histórico.
  - Resultado:
- [ ] **T7.4 · G9** Ligar as agendas e fazer commit e push, com varredura (R6).
  - Verificação: varredura limpa; CHANGELOG com as conferências.
  - Resultado:

## E8 · Sustentação (faça antes do T7.4, que liga as agendas)

- [ ] **T8.1** Adaptar `sustentacao/gerar_sustentacao.py` (job da carga, pipeline, `SLA`, `TAREFAS`, tabelas de volume) e rodar `testar` (P40).
  - Verificação: `testar` passa sem criar objeto.
  - Resultado:
- [ ] **T8.2 · G5** Aplicar as visões de sustentação e rodar `conferir`.
  - Verificação: execuções e updates = tabelas de sistema; volume por execução = tabelas; toda coluna descrita.
  - Resultado:
- [ ] **T8.3 · G6** Implantar o painel e o alerta de sustentação, com o alerta pausado.
  - Verificação: `bundle validate` ok; alerta PAUSED; até 4 disparos por dia (PLT06).
  - Resultado:
- [ ] **T8.4** Escrever o manual de sustentação da base a partir de `docs/07_SUSTENTACAO.md`: catálogo, SLAs, rotina, runbooks, RACI e indicadores.
  - Verificação: cada tarefa do job com runbook; metas da base curta marcadas como provisórias; links resolvem.
  - Resultado:
