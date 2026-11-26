# Base regras · modelo de entidade e relacionamento

> Gerado por `governanca/modelo_dados.py` a partir do Unity Catalog. Não edite: rode `python3 governanca/modelo_dados.py gerar`.
> Schemas: `pos_venda.regras` · papel: **principal**.

Funções de cálculo, catálogo de regras de qualidade com vigência, triagem e retroalimentação (P20, P41).

## Diagrama

Chave: `PK` (declarada no Unity Catalog ou lógica, ver a tabela abaixo) e `FK` (coluna que aponta para outra entidade).
Relacionamentos com outras bases aparecem com o nome completo da entidade (`schema__tabela`).

```mermaid
erDiagram
  regras__catalogo_regras {
    string regra_id PK
    int versao PK
    string titulo
    string tipo
    string area
    string dono
    string mais_11_colunas "veja a Wiki"
  }
  regras__triagem_regras {
    string triagem_id PK
    string regra_id FK
    int versao
    date periodo_de
    date periodo_ate
    string classificacao
    string mais_4_colunas "veja a Wiki"
  }
  regras__v_falhas_regras {
    date dia PK
    string fonte PK
    string regra_id PK,FK
    int versao FK
    string titulo
    string tipo
    string mais_6_colunas "veja a Wiki"
  }
  regras__v_mudancas_regras {
    string regra_id PK,FK
    int versao PK,FK
    date mudou_em
    string titulo
    string motivo
    string origem
    string mais_2_colunas "veja a Wiki"
  }
  regras__v_retroalimentacao {
    string regra_id PK,FK
    string titulo
    string tipo
    string dono
    long versoes
    int versao_atual
    string mais_10_colunas "veja a Wiki"
  }
  regras__v_triagem_pendente {
    date semana PK
    string fonte PK
    string regra_id PK,FK
    int versao PK,FK
    string titulo
    string tipo
    string mais_6_colunas "veja a Wiki"
  }
  gold__dq_barrados_por_motivo_dia }o--|| regras__catalogo_regras : "motivo_rejeicao"
  regras__triagem_regras }o--|| regras__catalogo_regras : "regra_id"
  regras__v_falhas_regras }o--|| regras__catalogo_regras : "regra_id+versao"
  regras__v_triagem_pendente }o--|| regras__catalogo_regras : "regra_id+versao"
  regras__v_mudancas_regras ||--|| regras__catalogo_regras : "regra_id+versao"
  regras__v_retroalimentacao ||--o{ regras__catalogo_regras : "regra_id"
  silver__pendencia_evento_quarentena }o--|| regras__catalogo_regras : "motivo_rejeicao"
  dqx_codigo__dq_metricas_regras }o--|| regras__catalogo_regras : "regra"
  dq__v_painel_barrados }o--|| regras__catalogo_regras : "motivo_rejeicao"
```

## Entidades

| Entidade | Tipo | Chave | Colunas | Descrição |
|---|---|---|---|---|
| `regras.catalogo_regras` | managed | `regra_id`, `versao` (PK no Unity Catalog) | 17 | Catálogo das regras de qualidade do pos_venda, com versão e vigência pela data do dado (P41). Gerado por regras/catalogo/gerar_catalogo.py a partir de catalogo_ |
| `regras.triagem_regras` | managed | `triagem_id` (lógica) | 10 | Triagem das falhas de regra: cada semana com falha recebe uma classificação e uma ação. Fecha o ciclo de retroalimentação (P41): regra errada vira versão nova;  |
| `regras.v_falhas_regras` | view | `dia`, `fonte`, `regra_id` (lógica) | 12 | Falhas por dia, fonte, regra e versão vigente (P41). Na barreira, cada evento barrado conta só no primeiro motivo; no DQX, em todas as regras que violou. Base d |
| `regras.v_mudancas_regras` | view | `regra_id`, `versao` (lógica) | 8 | Mudanças de regra no tempo (P41): uma linha por versão com início de vigência. Os painéis marcam essas datas para explicar saltos na taxa de reprovação. |
| `regras.v_retroalimentacao` | view | `regra_id` (lógica) | 16 | Indicadores da retroalimentação por regra (P41): quanto falha, quanto falta triar, o que a triagem concluiu e a taxa de falso positivo. Uma regra com falso posi |
| `regras.v_triagem_pendente` | view | `semana`, `fonte`, `regra_id`, `versao` (lógica) | 12 | O que falta triar (P41): semanas em que a regra passou do limite aceito e nenhuma triagem cobre o período. Cada linha pede uma classificação em triagem_regras. |

## Relacionamentos

| De | Para | Colunas | Cardinalidade | Tipo | O que significa |
|---|---|---|---|---|---|
| `gold.dq_barrados_por_motivo_dia` | `regras.catalogo_regras` | motivo_rejeicao → regra_id | N:1 | lógico | barrados por uma regra de erro do catálogo |
| `regras.triagem_regras` | `regras.catalogo_regras` | regra_id → regra_id | N:1 | lógico | a triagem classifica as falhas de uma regra (e versão) |
| `regras.v_falhas_regras` | `regras.catalogo_regras` | regra_id, versao → regra_id, versao | N:1 | lógico | falhas do dia pela versão vigente |
| `regras.v_triagem_pendente` | `regras.catalogo_regras` | regra_id, versao → regra_id, versao | N:1 | lógico | semana a triar de uma versão |
| `regras.v_mudancas_regras` | `regras.catalogo_regras` | regra_id, versao → regra_id, versao | 1:1 | lógico | versão que começou a valer |
| `regras.v_retroalimentacao` | `regras.catalogo_regras` | regra_id → regra_id | 1:N | lógico | indicadores da regra em todas as versões |
| `silver.pendencia_evento_quarentena` | `regras.catalogo_regras` | motivo_rejeicao → regra_id | N:1 | lógico | o motivo de rejeição é uma regra de erro do catálogo |
| `dqx_codigo.dq_metricas_regras` | `regras.catalogo_regras` | regra → regra_id | N:1 | lógico | métrica de uma regra do catálogo |
| `dq.v_painel_barrados` | `regras.catalogo_regras` | motivo_rejeicao → regra_id | N:1 | lógico | barrados por uma regra de erro |

## Linhagem (Unity Catalog, últimos 90 dias)

| Entidade | Vem de | Alimenta |
|---|---|---|
| `regras.catalogo_regras` | — | `regras.v_falhas_regras`, `regras.v_mudancas_regras`, `regras.v_retroalimentacao` |
| `regras.triagem_regras` | — | `regras.v_retroalimentacao` |
| `regras.v_falhas_regras` | `bronze.pagamentos_pendentes_eventos`, `dqx_codigo.eventos_quarentena`, `dqx_codigo.eventos_validos`, `regras.catalogo_regras`, `silver.pendencia_evento_quarentena` | `regras.v_retroalimentacao`, `regras.v_triagem_pendente` |
| `regras.v_mudancas_regras` | `regras.catalogo_regras` | — |
| `regras.v_retroalimentacao` | `regras.catalogo_regras`, `regras.triagem_regras`, `regras.v_falhas_regras`, `regras.v_triagem_pendente` | — |
| `regras.v_triagem_pendente` | `regras.v_falhas_regras` | `regras.v_retroalimentacao` |
