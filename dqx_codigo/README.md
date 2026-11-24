# DQX como código (trilha A)

Modelo para usar o **DQX como biblioteca** (`databricks-labs-dqx`), sem o app DQX Studio. Serve para quem não tem
permissão para dar ao app o acesso que ele pede no catálogo, ou não quer manter um app e um Lakebase.

O app é a [trilha B](../dqx_studio/README.md). O [guia para outra base](../docs/06_GUIA_BASE_BRUTA.md) compara as duas
e diz quando escolher cada uma.

> **Situação (24/11/2026):** executado neste workspace na janela de 26/12 a 01/01 (49.972 eventos da bronze). Deu 3.229
> linhas em quarentena, o mesmo número da barreira do pipeline, e 46.743 válidas. As 14 regras estão em
> `dq_metricas_regras`. O job é `pos_venda_dqx_codigo`, com tags de projeto e time e timeout de 1 hora.

## O que tem aqui

| Arquivo | O que faz |
|---|---|
| `checks_pendencias.yml` | 14 checagens: as 11 regras de erro da barreira do pipeline, com os mesmos nomes, e 3 avisos |
| `aplicar_dqx.py` | notebook: instala `databricks-labs-dqx==0.17.2`, aplica as checagens, separa válidos e quarentena, grava as métricas por regra e aplica descrições e tags (copiadas da tabela de entrada) |
| `databricks.yml` | bundle com o job `dqx_codigo_checagens`, sob demanda e no serverless |

## Permissões necessárias

| Para | Privilégio |
|---|---|
| ler a base | `USE CATALOG` e `USE SCHEMA` no catálogo e no schema da base, `SELECT` na tabela |
| gravar o resultado | `USE CATALOG` e `USE SCHEMA` no catálogo e no schema de destino, `CREATE TABLE` e `MODIFY` no schema (ou um schema seu, já criado) |
| usar as funções de regra | `EXECUTE` nas funções (no pos_venda, `pos_venda.regras`) |
| rodar | permissão para criar e rodar job (ou rodar o notebook à mão) |

**Não precisa de:** app, service principal, Lakebase, `CREATE SCHEMA` no catálogo, `MANAGE` no catálogo nem papel de
administrador.

## Como rodar

```bash
cd dqx_codigo
databricks bundle validate --profile <perfil>
databricks bundle deploy -t dev --profile <perfil> --var="tabela_entrada=<cat.schema.tabela>" --var="schema_destino=<cat.schema>"
databricks bundle run dqx_codigo -t dev --profile <perfil>
```

Sem bundle, importe `aplicar_dqx.py` e `checks_pendencias.yml` para a mesma pasta do workspace, preencha os widgets e
rode.

## O que sai

| Tabela | Conteúdo | Para quê |
|---|---|---|
| `<destino>.<prefixo>_validos` | linhas sem erro; avisos na coluna `_warnings` | entrada da silver |
| `<destino>.<prefixo>_quarentena` | linhas com erro, com o nome e a mensagem de cada regra em `_errors` | devolver à origem com o motivo |
| `<destino>.dq_metricas_regras` | por execução e regra: linhas avaliadas, reprovadas, taxa | painel de qualidade e plano de ação |

Consulta para o plano de ação (regras com reprovação na última execução):

```sql
SELECT regra, criticidade, reprovadas, round(taxa * 100, 2) AS pct
FROM <destino>.dq_metricas_regras
WHERE execucao_id = (SELECT max_by(execucao_id, executado_em) FROM <destino>.dq_metricas_regras)
  AND reprovadas > 0
ORDER BY reprovadas DESC;
```

## Como adaptar para outra base

1. **Gere candidatas.** Rode o perfilador do DQX numa amostra da base bruta e revise as regras sugeridas antes de
   adotar:

   ```python
   from databricks.labs.dqx.profiler.profiler import DQProfiler
   from databricks.labs.dqx.profiler.generator import DQGenerator
   from databricks.sdk import WorkspaceClient

   ws = WorkspaceClient()
   _, perfis = DQProfiler(ws).profile(spark.table("<cat.schema.tabela>"))
   candidatas = DQGenerator(ws).generate_dq_rules(perfis)
   ```

2. **Escreva as regras do negócio.** O que torna o dado inutilizável é `error`; o resto é `warn`. As respostas ao
   [Passo 0 do playbook](../docs/02_PLAYBOOK.md#passo-0--perfil-da-base) dizem quais são.
3. **Troque as colunas e o catálogo das funções** no YAML. Mantenha um nome estável por regra: o nome vira o motivo na
   quarentena e a linha do painel.
4. **Rode numa janela pequena primeiro** (`filtro`, por exemplo `data_extracao >= date_sub(current_date(), 7)`).
   Confira as colunas de resultado (`_errors`, `_warnings`) e os números por regra.
5. **Ponha o job no fim da carga**, como uma tarefa depois da bronze ou da silver.

## Resultado da primeira execução (janela de 26/12 a 01/01)

| Regra | Reprovadas no DQX | Motivo na barreira |
|---|---|---|
| valores_fora_da_regra | 1.358 | 335 |
| atraso_nao_confere_com_as_datas | 721 | 352 |
| vencimento_nao_anterior_ao_evento | 359 | 344 |
| uf_invalida | 341 | 320 |
| valor_parcela_nao_positivo | 331 | 330 |
| valor_total_inconsistente | 329 | 322 |
| cliente_menor_de_idade | 323 | 300 |
| status_cobranca_invalido | 299 | 298 |
| tipo_evento_invalido | 232 | 230 |
| baixa_sem_data_ou_valor_pago | 214 | 204 |
| pendencia_id_nulo | 194 | 194 |
| **linhas em quarentena** | **3.229** | **3.229** |

O total de linhas bate, e as regras diferem porque contam coisas diferentes:
- **DQX:** conta toda regra que a linha violou.
- **Barreira:** guarda só o primeiro motivo, na ordem do `CASE`.

Uma linha com atraso errado, por exemplo, quase sempre tem também multa e juros fora da regra. Dos avisos, o e-mail
ausente marcou 2.995 linhas. Periodicidade e forma de pagamento deram zero nesta janela, porque os valores novos
chegaram na semana 7.

## Cuidados

- **Use todas as linhas da janela, não amostra.** Por amostra de 10 mil linhas, o Studio nunca acusou as órfãs da fato
  (P11).
- **Mesmo nome, mesmas regras nas duas linhas de defesa.** A barreira do pipeline e o DQX usam os mesmos nomes; assim a
  quarentena e o painel batem.
- **Expressão escrita para dar TRUE quando o dado está bom.** O `coalesce` define o que acontece com valor nulo.
- **Domínio de texto em `sql_expression` com `IN`.** Na versão 0.17.2, o `is_in_list` leu cada valor de `allowed` como
  nome de coluna e o job falhou (L88).
- **Versão fixada.** Atualize a versão de propósito e rode de novo numa janela conhecida. O Studio instalado no
  pos_venda usa DQX 0.17.x.
