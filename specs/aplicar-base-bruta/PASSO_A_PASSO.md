# Passo a passo de implementação · comandos em ordem

> Versão 2 · 26/11/2026. Complemento do [SPEC](SPEC.md): o SPEC diz **o que** precisa estar pronto, as
> [TAREFAS](modelos/TAREFAS.md) dizem **como conferir**, e este arquivo diz **qual comando rodar, em que ordem e o que
> esperar**. O porquê de cada passo está no [guia 06](../../docs/06_GUIA_BASE_BRUTA.md).

## Como ler

- **Ordem.** Execute os passos de cima para baixo. Cada passo começa pela tarefa que ele cumpre (`T3.4`).
- **Aprovação.** Passo com **⛔ G#** para antes de rodar e pede aprovação (R2).
- **Variáveis de exemplo:**
  - `<perfil>`: perfil do Databricks CLI;
  - `<base>`: tabela bruta;
  - `<cat>`: catálogo de destino;
  - `<pasta>`: pasta do código novo, onde ficam as cópias dos módulos do pos_venda (R5).
- **Esperado.** Os números do pos_venda aparecem como referência: na sua base, o que precisa bater são as igualdades,
  não os valores.
- **Depois de cada passo:** anote o resultado em `specs/<nome>/TAREFAS.md` e só então marque `[x]` (R3).

## 0 · Uma vez, antes de tudo

```bash
databricks --version                                   # CLI v0.29x ou mais novo
databricks auth login --profile <perfil>               # se o perfil não estiver válido
databricks auth profiles                               # o perfil precisa aparecer como "Valid: YES"
cd <pasta>/regras && uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r requirements.txt
```

Esperado: perfil válido; `.venv` com `databricks-sdk` e `behave`. Os scripts que importam o SDK (por exemplo,
`gerar_powerbi.py visoes`) rodam com `<pasta>/regras/.venv/bin/python`.

## E0 · Acesso e permissões

| Passo | Comando | Esperado |
|---|---|---|
| T0.1 | `databricks current-user me --profile <perfil>` | o seu usuário |
| T0.2 | `SHOW GRANTS ON CATALOG <cat>` e `SHOW GRANTS ON SCHEMA <schema>`, mais a consulta do dono (FICHA § Consultas do perfil) | grants anotados; `sou_dono_catalogo` e `sou_dono_schema` (L93) |
| T0.3 ⛔ G1 | — (decisão) | D-001: catálogo, schemas e pasta |
| T0.4 ⛔ G2 | — (decisão, SPEC § 8) | D-002: trilha A ou B |

## E1 · Ficha da base

| Passo | Comando | Esperado |
|---|---|---|
| T1.1 | `databricks experimental aitools tools discover-schema <base> --profile <perfil>` | colunas e tipos na ficha |
| T1.2 | as consultas da FICHA § Consultas do perfil, só `SELECT` (R1) | linhas por dia, nulos, chaves repetidas, domínios, faixas |
| T1.3 ⛔ G3 | — | ficha sem pergunta em branco e perfil (A a E) escolhido |

## E2 · Mapeamento e regras do negócio

| Passo | Comando | Esperado |
|---|---|---|
| T2.1 | — (MAPEAMENTO) | todo conceito com coluna, derivação ou "não se aplica" |
| T2.2 | — (decisão) | D-003: eventos ou foto completa |
| T2.3 ⛔ G4 | a área dona responde ao [questionário](../../regras/questionario/QUESTIONARIO_NEGOCIO.md); depois `cp -r regras/catalogo <pasta>/regras/`, edite `catalogo_regras.yml` e rode `python3 <pasta>/regras/catalogo/gerar_catalogo.py validar` | "catálogo válido"; versão e vigência pela data do dado (P41) |

## E3 · Medalhão, barreira e regras de cálculo

```bash
# T3.1: copie os módulos e troque catálogo, tabela de origem e colunas (R5)
cp -r carga_diaria medalhao regras <pasta>/
grep -rn "pos_venda" <pasta>/carga_diaria <pasta>/medalhao <pasta>/regras   # só comentários, ou nada

# T3.2: funções de regra, cenários e paridade (P20, L56)
cd <pasta>/regras && .venv/bin/python funcoes.py && .venv/bin/behave && .venv/bin/python paridade.py
```

Esperado: cenários 100% (no pos_venda, 36 de 36); paridade sem divergência.

| Passo | Comando | Esperado |
|---|---|---|
| T3.3 ⛔ G5 | `cd <pasta>/carga_diaria && python3 gerar_carga.py && databricks bundle deploy -t dev --profile <perfil>` e depois `databricks bundle run carga_setup -t dev --profile <perfil>` | schemas e bronze criados; agenda **pausada** (R7) |
| T3.4 a T3.6 ⛔ G6 | `databricks bundle run carga_diaria -t dev --profile <perfil> --params data_inicio=<d1>,data_fim=<d2>` | run SUCCESS; portão 100%; aptos + quarentena = bronze; fato = silver na foto |
| T3.7 | `python3 <pasta>/governanca/aplicar_rely.py verificar` e, se der 100%, `aplicar` e `conferir` | toda PK única e sem nulo; "PK com RELY: N/N" (L100) |

## E4 · Qualidade: siga só a trilha escolhida em T0.4

### Trilha A · DQX como código

```bash
cp -r dqx_codigo <pasta>/
python3 <pasta>/regras/catalogo/gerar_catalogo.py gerar          # escreve o YAML do DQX a partir do catálogo
cd <pasta>/dqx_codigo && databricks bundle validate -t dev --profile <perfil>
```

| Passo | Comando | Esperado |
|---|---|---|
| T4A.3 ⛔ G6 | `databricks bundle deploy -t dev --profile <perfil>` e `databricks bundle run dqx_codigo -t dev --profile <perfil> --notebook-params "modo=ensaio,filtro=<janela>"`; depois `python3 <pasta>/regras/catalogo/gerar_catalogo.py ensaio <run_id>` | "ensaio ok": DQX = SQL em todas as checagens; erros = quarentena da barreira (L95) |
| T4A.3 ⛔ G6 | o mesmo `bundle run`, sem `modo=ensaio` | run SUCCESS; toda regra em `dq_metricas_regras`, mesmo com zero (L84) |
| T4A.4 | `python3 <pasta>/dqx_studio/painel/gerar_painel.py` (adaptado) e `bundle deploy` do painel | todas as consultas testadas antes do deploy (P12) |

### Trilha B · DQX Studio como app

| Passo | Comando | Esperado |
|---|---|---|
| T4B.1 e T4B.2 ⛔ G8 | os passos de [dqx_studio/README.md](../../dqx_studio/README.md) | app RUNNING e "Application startup complete" (L85) |
| T4B.3 | `python3 registro_studio.py planejar` e depois `aplicar` | tabelas no menu do Studio |
| T4B.4 ⛔ G6 | `python3 registro_studio.py executar` | todas as execuções SUCCESS; reprovados = quarentena |

### Comum às duas trilhas

| Passo | Comando | Esperado |
|---|---|---|
| T4.8 ⛔ G5 | `python3 <pasta>/regras/catalogo/gerar_catalogo.py aplicar`, depois `conferir`, depois `cd <pasta>/regras && .venv/bin/behave catalogo/features` | `conferir` sem falha; falhas da barreira na visão = quarentena; cenários do catálogo 100% |
| T4.9 | — (rito com o dono) | dono e dia da triagem semanal em DECISOES |

## E5 · Governança, semântica e modelo de dados

```bash
cd <pasta>/governanca
python3 auditar_metadados.py                     # T5.1: retrato das descrições e tags
python3 aplicar_descricoes.py                    # T5.1: descrições por nome de coluna (descricoes_colunas.py)
python3 auditar_metadados.py && python3 aplicar_semantica.py   # T5.2: tags, domínio, Pages e Wikis
python3 gerar_ontologia_sql.py && python3 aplicar_sql.py ontologia_sql.json   # T5.3 e T5.4: ontologia e metric views
```

| Passo | Comando | Esperado |
|---|---|---|
| T5.1 | `python3 auditar_metadados.py` | 100% das colunas das camadas principais descritas |
| T5.2 | `python3 aplicar_semantica.py` | tags aplicadas e "Wikis publicadas: N/N" |
| T5.5 | `python3 modelo_dados.py gerar` e depois `conferir` (P42) | `docs/modelo_dados/` com um diagrama por base; toda tabela numa base; toda FK no modelo; chave única nos dados; linhagem de entrada em toda tabela do fluxo |
| T5.6 | `python3 auditar_metadados.py && python3 aplicar_semantica.py` (de novo, depois do modelo) | "Wikis publicadas: N/N" em **todo** ativo, cada Wiki com chave, relacionamentos e linhagem |

Recriou uma view? Rode `aplicar_semantica.py` de novo: `CREATE OR REPLACE VIEW` apaga tags e Wiki (L31).

## E6 · Consumo

| Passo | Comando | Esperado |
|---|---|---|
| T6.0 | ler `docs/marca/` da **sua** empresa (ou criar a pasta com o modelo de [docs/marca/README.md](../../docs/marca/README.md)) | cores vindas de `marca.json`; paleta nova validada (L97) |
| T6.1 ⛔ G7 | `python3 genie.py gerar`, depois `validar`, depois `criar` | todo SQL de exemplo e de avaliação SUCCEEDED |
| T6.2 | `python3 genie.py avaliar` | acerto ≥ meta (no pos_venda, 29 de 29) |
| T6.3 ⛔ G6 | `python3 <pasta>/paineis_financeiros/gerar_paineis.py` e `bundle deploy`; se houver Power BI: `gerar_powerbi.py visoes`, depois `gerar_powerbi.py`, depois `gerar_powerbi.py referencia` | "conferência: ok"; PARIDADE 100%; dimensões do BI com chave única (L101) |

## E7 · Operação, custo e conformidade

| Passo | Comando | Esperado |
|---|---|---|
| T7.1 | — (matriz de resiliência do playbook) | cada falha conhecida com sinal e ação |
| T7.2 | tags `project` e `team` nos `resources/*.yml` e `bundle deploy` | PLT01 sem falha nos jobs da base |
| T7.2 | `python3 finops/gerar_finops.py gerar`, depois `aplicar`, depois `conferir` | nenhum custo da base sem dono |
| T7.3 | `python3 conformidade/gerar_conformidade.py politicas`, `alertas`, `aplicar`, `registrar` e `conferir`, nessa ordem | "conferência: ok"; histórico do dia com uma linha por regra |
| T7.5 ⛔ G6 | `python3 governanca/modelo_dados.py aplicar`; depois `cd conformidade && databricks bundle deploy -t dev --profile <perfil>` e `bundle run sonda_conformidade` | job SUCCESS com as tarefas `sonda` e `chaves`; `chaves_unicas` com todas as chaves únicas (L100) |

## E8 · Sustentação (antes de ligar as agendas)

| Passo | Comando | Esperado |
|---|---|---|
| T8.1 | `python3 sustentacao/gerar_sustentacao.py testar` | passa sem criar objeto |
| T8.2 ⛔ G5 | `python3 sustentacao/gerar_sustentacao.py aplicar` e depois `conferir` | execuções = tabelas de sistema; toda coluna descrita |
| T8.3 ⛔ G6 | `cd sustentacao && databricks bundle deploy -t dev --profile <perfil>` | painel publicado; alerta **pausado**; até 4 disparos por dia |
| T8.4 | — (manual a partir de `docs/07_SUSTENTACAO.md`) | runbook por tarefa |

## Fechamento · agendas, commit e push (T7.4 ⛔ G9)

```bash
# ligar as agendas: só com aprovação (R7)
cd <pasta>/carga_diaria && databricks bundle deploy -t dev --var="carga_schedule_status=UNPAUSED" --profile <perfil>

# antes de cada commit (R6): varredura, testes sem rede e documentação
git grep -nIE 'dapi[0-9a-f]{20,}|ghp_[A-Za-z0-9]{20,}|/Users/[A-Za-z]|[A-Za-z0-9._%+-]+@gmail\.com' || echo "sem achados"
python3 regras/catalogo/gerar_catalogo.py testar && python3 regras/catalogo/gerar_catalogo.py validar
python3 docs/validar_docs.py && python3 docs/gerar_inventario.py
```

Esperado:
- a varredura sem achados;
- "todos os testes passaram" e "catálogo válido";
- "documentação ok";
- o CHANGELOG com a conferência de cada passo.

O CI (`.github/workflows/ci.yml`) roda as mesmas checagens em todo push.
