# Regras de negócio testadas (BDD) · pos_venda

As regras de cálculo do pós-venda viram **funções SQL do Unity Catalog** (`pos_venda.regras`), a fonte única da regra.
O contrato de cada regra são **cenários em português** (Gherkin, `features/*.feature`), executados pelo
[behave](https://behave.readthedocs.io/) contra as funções reais pela Statement Execution API: um `SELECT` por cenário,
sem Spark e sem cluster. Padrão do [agentic-bdd-uc-functions](https://github.com/databricks-solutions/agentic-bdd-uc-functions),
usado como modelo (não como dependência).

```
pos_venda.regras.*  (funcoes.py)
   ├── cenários BDD em português (features/)  → o contrato, legível pelo negócio
   ├── paridade com a gold e a silver (paridade.py)  → prova que a função = o que já está gravado
   ├── portão do job diário (05_portao_regras)  → os mesmos cenários rodam antes da carga; se falhar, nada roda
   ├── silver (cpf_valido), barreira (valores_fora_da_regra) e gold (faixa, multa, juros, total)
   └── Genie (instructions.sql_functions)  → simulações de multa, juros, total e faixa
```

## Onde cada função é usada (etapa 2, 22/11/2026)

| Função | Silver | Barreira | Gold (fato diária) | DQX Studio | Genie |
|---|---|---|---|---|---|
| `faixa_atraso` | | | `faixa_atraso_sk` | | sim |
| `valor_multa` | | `valores_fora_da_regra` | `valor_multa` | `valores_seguem_regras_de_calculo` | sim |
| `valor_juros` | | `valores_fora_da_regra` | `valor_juros` | `valores_seguem_regras_de_calculo` | sim |
| `valor_total_pendente` | | `valores_fora_da_regra` | `valor_total_pendente` | `valores_seguem_regras_de_calculo` | sim |
| `cpf_valido` | `dq_cpf_invalido` | | | | não (espaços sem dado pessoal) |

No DQX Studio a regra `valores_seguem_regras_de_calculo` está nas janelas de bronze, silver e fato. Quem executa o Studio
(o service principal do app e o executor dos agendamentos) tem `USE SCHEMA` e `EXECUTE` em `pos_venda.regras`.

A barreira mantém `valor_total_inconsistente` (o total bate com a soma das partes **informadas**) e ganhou
`valores_fora_da_regra` **depois** de `atraso_nao_confere_com_as_datas`: trocar a regra antiga no mesmo lugar faria 319
eventos do incidente I14 (dias adulterados) aparecerem como total errado, escondendo a causa. O simulador da origem
continua com a conta própria, de propósito (imita o sistema externo e seus erros).

## Funções

| Função | Regra | Decisão explícita (difere do pipeline só em entrada inválida) |
|---|---|---|
| `faixa_atraso(dias_atraso)` | 0 → `00_VENCE_HOJE`; até 15, 30, 60, 90, 120; acima → `06_ACIMA_120` | dias negativos → nulo (pipeline dava `01_1_A_15`) |
| `valor_multa(valor_parcela)` | 2% da parcela, fixa, arredondada em centavos | — |
| `valor_juros(valor_parcela, dias_atraso)` | 1% ao mês pró-rata (30 dias), arredondado | dias negativos → nulo (pipeline dava juros negativos) |
| `valor_total_pendente(valor_parcela, dias_atraso)` | parcela + multa + juros (cada parte arredondada) | dias negativos → nulo |
| `cpf_valido(cpf)` | 11 dígitos, 2 dígitos verificadores (módulo 11) | dígitos todos iguais → inválido (pipeline aceitava) |

Impacto das decisões nos dados de hoje: **0 linha** (medido por `paridade.py`).

## Como usar

```bash
cd pos_venda/regras
uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r requirements.txt   # uma vez
.venv/bin/python funcoes.py          # cria o schema e (re)cria as funções (descrições ficam no DDL)
.venv/bin/behave                     # 36 cenários; relatório JUnit em resultados/
.venv/bin/python paridade.py         # função x gold/silver/quarentena; sai com 1 se divergir
```

Variáveis opcionais: `DATABRICKS_PROFILE` (padrão `dbx-workshop`), `DATABRICKS_WAREHOUSE_ID`, `REGRAS_CATALOGO`,
`REGRAS_SCHEMA` (para rodar contra outro catálogo, por exemplo um de teste).

## Resultados (21 e 22/11/2026)

| Verificação | Resultado |
|---|---|
| Cenários BDD | **36/36** em ~30 s (3 funcionalidades, 9 regras, 123 passos) |
| Gold · fato diária | 29.893.555 linhas, **0** divergência em faixa, multa, juros e total |
| Silver · eventos aceitos | 1.596.919 linhas, **0** divergência em faixa, multa, juros, total e CPF |
| Quarentena · total inconsistente | a função também reprova os **517** totais barrados |
| Job com as funções (22/11) | portão 36/36 no Databricks; silver sem mudança (1.596.919 e 3.049); gold de 18 a 24/12 recalculada: 1.743.052 linhas, **0** diferença com a cópia anterior |
| Genie | 29/29 perguntas de avaliação (2 simulações novas respondidas chamando as funções) |
| Painéis | 13/13 datasets respondem |
| DQX Studio (22/11) | regra espelhada nas 3 janelas; execução manual e **agendada** (executor `scheduler`): bronze 60 violações (todas do I03, já barradas), silver 0, fato 0 |
| Dia novo 25/12 (22/11) | job completo: portão 36/36; 8.559 eventos, 0 na quarentena; silver e gold do dia com **0** divergência das funções; CPF inválido 139 = 139; Studio na janela 19–25/12: bronze 44 (I03 de 19–20/12), silver 0, fato 0 |

## Regras de qualidade com vigência e triagem (P41)

As regras de cálculo ficam aqui, como funções e cenários. As **regras de qualidade** (o que barra ou avisa) ficam no
[catálogo de regras](catalogo/README.md). Lá cada regra tem versões com vigência pela data do dado, dono, limite
aceito e triagem. O negócio responde pelo [questionário](questionario/QUESTIONARIO_NEGOCIO.md).

Os cenários do catálogo ficam fora do portão da carga, de propósito: `.venv/bin/behave catalogo/features`.

Uma regra de **cálculo** também pode mudar com o tempo; o cenário "A parcela que vence hoje já tem multa (regra atual)"
é o candidato. Quando mudar:
1. a função ganha um parâmetro de data, por exemplo `valor_multa(valor_parcela, data_referencia)`;
2. a função escolhe a conta pela vigência;
3. o `.feature` ganha um cenário por versão ("Dado a data de referência 2027-02-01…");
4. a paridade roda antes da troca (L56).

## Adicionar uma regra

1. Escreva a função em `FUNCOES` (`funcoes.py`), com descrição da função e de cada parâmetro, e rode `funcoes.py`.
2. Escreva os cenários em `features/<regra>.feature` (`# language: pt`), primeiro os exemplos do negócio, depois os limites.
3. Acrescente os passos em `features/steps/regras_steps.py` (finos: frase → chamada da função → conferência).
4. Acrescente a checagem de paridade em `paridade.py` contra a tabela que já calcula a regra.
5. Só depois de 100% de paridade troque o cálculo no pipeline pela chamada da função (na barreira, acrescente; não substitua).
6. Rode `python3 gerar_carga.py` em `carga_diaria/` para atualizar a cópia da suíte usada pelo portão do job e implante o bundle.
