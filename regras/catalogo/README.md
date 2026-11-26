# Catálogo de regras com vigência e retroalimentação

> Prática P41 do [framework](../../docs/04_FRAMEWORK.md). Criado em 26/11/2026. O negócio responde pelo
> [questionário](../questionario/QUESTIONARIO_NEGOCIO.md).

## Para que serve

As regras de qualidade mudam com o tempo: um produto novo passa a aceitar outra periodicidade, um tipo de evento
passa a ser válido, um limite fica mais rígido. Se a regra nova julgar o dado antigo, o passado começa a "falhar" e
ninguém consegue explicar o salto no painel. O catálogo resolve isso em três partes:

1. **Cada regra tem versões com vigência pela data do dado.** O evento de outubro é julgado pela versão de outubro,
   mesmo que o job rode em dezembro.
2. **Cada versão nasce de uma resposta do negócio** (questionário), com motivo, origem e aprovação.
3. **Cada falha é triada.** A triagem decide se o problema é o dado ou a regra, e isso volta para o questionário.

```
questionário do negócio ──► catalogo_regras.yml (versão, vigência, dono, limite)
        ▲                          │ gerar_catalogo.py gerar
        │                          ▼
        │              YAML do DQX (filter pela data + user_metadata.versao)
        │              pos_venda.regras.catalogo_regras + versao_vigente()
        │                          │
        │                          ▼
        │              barreira diária e DQX ──► v_falhas_regras (dia × regra × versão)
        │                                              │
 regra_errada ◄── triagem_regras ◄── v_triagem_pendente (semanas acima do limite, sem triagem)
 (versão nova)        │
                      └── dado_ruim ──► plano de ação (origem corrige)
```

## Arquivos

| Arquivo | O que é |
|---|---|
| [catalogo_regras.yml](catalogo_regras.yml) | **a fonte**: 14 regras (11 erros da barreira e 3 avisos), cada uma com versões |
| [gerar_catalogo.py](gerar_catalogo.py) | valida, testa, gera o YAML do DQX e o SQL, aplica, confere e compara o ensaio |
| [catalogo_regras.sql](catalogo_regras.sql) | gerado: tabelas, função e visões em `pos_venda.regras` |
| [ensaio/vigencia_periodicidade.yml](ensaio/vigencia_periodicidade.yml) | ensaio **fictício**: `QUINZENAL` aceita a partir de 05/01/2027 |
| [features/](features/catalogo_regras.feature) | 8 cenários BDD do catálogo, fora do portão da carga |
| `../../dqx_codigo/checks_pendencias.yml` | gerado: o YAML do DQX como código (não edite à mão) |

## Objetos em `pos_venda.regras`

| Objeto | O que mostra |
|---|---|
| `catalogo_regras` (tabela) | uma linha por regra e versão: título de negócio, tipo, dono, vigência, limite, expressão, motivo, origem e aprovação |
| `triagem_regras` (tabela) | as triagens do negócio; a tabela só aceita as 4 classificações (`CHECK`) |
| `versao_vigente(regra, dia)` (função) | a versão aprovada que vale para o dado daquele dia |
| `v_falhas_regras` | falhas por dia, fonte (barreira ou DQX), regra e versão, com zero quando a regra passou (L84) |
| `v_triagem_pendente` | semanas acima do limite que ninguém triou ainda: a pauta do rito semanal |
| `v_mudancas_regras` | as datas em que alguma regra mudou, para marcar nos painéis |
| `v_retroalimentacao` | por regra: falhas, semanas pendentes, o que a triagem concluiu e a taxa de falso positivo |

## Como mudar uma regra

1. O negócio responde aos blocos A e D do questionário. Exemplo: "a partir de 05/01/2027, `QUINZENAL` é válida".
2. No catálogo, acrescente a versão nova com `status: proposta`, `vigente_de`, `motivo` e `origem`. Não mexa na
   versão anterior ainda.
3. Com a aprovação do dono:
   - a nova passa a `status: aprovada`, com `aprovado_por` (o papel) e `aprovado_em`;
   - a anterior ganha `vigente_ate` igual ao `vigente_de` da nova.
4. Rode a sequência abaixo e registre a mudança no CHANGELOG.

```bash
python3 regras/catalogo/gerar_catalogo.py validar
python3 regras/catalogo/gerar_catalogo.py aplicar
python3 regras/catalogo/gerar_catalogo.py conferir
cd regras && .venv/bin/behave catalogo/features
```

O `validar` recusa:
- buraco ou sobreposição entre versões;
- versão nova sem motivo;
- versão aprovada sem aprovação;
- regra de erro diferente da barreira.

O `conferir` garante que, em cada dia da base, cada regra tem exatamente uma versão.

## Ensaio de vigência (26/11/2026)

Para provar que o DQX julga cada evento pela versão do dia dele, o ensaio simulou uma mudança fictícia: a
periodicidade `QUINZENAL` aceita a partir de 05/01/2027.

1. O DQX como código rodou em modo `ensaio`, que não grava nada e devolve as contagens. A janela foi de 14 dias (27/12/2026
   a 09/01/2027), com 101.636 eventos.
2. O comando `gerar_catalogo.py ensaio <run_id>` refez a mesma conta em SQL.

| Checagem | DQX | SQL |
|---|---|---|
| eventos com erro (= quarentena da barreira na janela: 3.388) | 3.388 | 3.388 |
| periodicidade v1, até 04/01 (63.518 avaliados): `QUINZENAL` 52 + `BIMESTRAL` 53 | 105 | 105 |
| periodicidade v2, de 05/01 (38.118 avaliados): só `BIMESTRAL`; `QUINZENAL` 84 passa | 68 | 68 |
| as outras 13 regras | iguais | iguais |

As 15 checagens bateram. O DQX 0.17.2 aceita duas checagens com o mesmo nome e `filter` diferentes, e o resultado
traz o `user_metadata` de cada uma (L95).

```bash
cd dqx_codigo && databricks bundle run dqx_codigo -t dev --profile <perfil> \
  --notebook-params "modo=ensaio,arquivo_checks=ensaio/checks_ensaio_vigencia.yml,filtro=data_extracao BETWEEN DATE'2026-12-27' AND DATE'2027-01-09'"
python3 regras/catalogo/gerar_catalogo.py ensaio <run_id>
```

## Primeira leitura da triagem (26/11/2026)

- **Pendências:** `v_triagem_pendente` tem 69 pares semana × regra acima do limite, nas semanas de 30/11/2026 a
  04/01/2027 no dado:
  - 11 regras de erro na barreira;
  - 12 regras na última execução do DQX como código.
- **Avisos sem limite:** `email_ausente` ainda não tem limite aceito.
- **Triagens registradas:** nenhuma; o rito ainda não começou.

As perguntas em aberto para o dono estão no fim do [questionário](../questionario/QUESTIONARIO_NEGOCIO.md).

## Limites

- **A barreira do pipeline ainda não lê a vigência.**
  - Ela tem a versão 1 de cada regra escrita no SQL (`MOTIVO_REJEICAO`), e o `validar` confere que os nomes batem.
  - Quando uma regra de erro ganhar versão 2, a barreira terá de usar a mesma vigência, com paridade antes da troca
    (L56). Isso fica como próximo passo.
- **Contagem diferente nas duas fontes.**
  - Na barreira, o evento barrado conta só no primeiro motivo da ordem.
  - No DQX, ele conta em todas as regras que violou. Por isso `v_falhas_regras` separa as fontes.
- **A fonte `dqx_codigo` é a última execução gravada.** O DQX como código não tem agenda, então essa fonte só cobre a
  janela da última execução.
- **O Studio (trilha B) ainda não usa o catálogo.** As regras dele ficam em `dqx_studio/regras/definir_regras.py`.
