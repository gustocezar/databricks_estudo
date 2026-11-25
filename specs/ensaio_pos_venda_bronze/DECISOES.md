# Decisões e lições · ensaio com a bronze do pos_venda

> Decisões **de ensaio**: registram o que o agente proporia em cada gate. Nada foi criado.

## Decisões

| Id | Data | Gate | Decisão (ensaio) | Alternativa descartada | Origem | Aprovado por |
|---|---|---|---|---|---|---|
| D-001 | 24/11/2026 | G1 | destino `pos_venda_ensaio` com schemas `bronze`, `silver`, `gold`, `ontologia`, `dq`; código em `dominios/ensaio/` | escrever em `pos_venda.*` (proibido por R1) | P01, R1 | não se aplica (ensaio) |
| D-002 | 24/11/2026 | G2 | trilha B possível, porque o perfil é dono do catálogo; a A também serve e não depende de app | — | P38, SPEC § 8, L93 | não se aplica (ensaio) |
| D-003 | 24/11/2026 | — | chegada por eventos (append-only), com `ESTORNO` tratado como tipo fora do domínio | foto completa com Auto CDC de snapshot | P06 | — |
| D-004 | 24/11/2026 | G4 | as 11 regras de erro da barreira, mais um aviso de chave repetida (10.277 combinações no perfil) | tratar repetição como erro | P09 | não se aplica (ensaio) |

## Bloqueios e lições novas

| Data | O que aconteceu | Regra que fica | Tarefa |
|---|---|---|---|
| 24/11/2026 | `SHOW GRANTS` mostrou só os 3 service principals; não mostrou que o perfil é **dono** do catálogo e do schema, e por isso pode conceder | consultar o dono em `system.information_schema` (`catalog_owner`, `schema_owner`) e comparar com `current_user()` antes de decidir a trilha (L93) | T0.2, T0.4 |
| 24/11/2026 | a T1.2 pedia "números com a consulta usada", mas o spec não trazia as consultas | o modelo da ficha passou a ter as consultas do perfil prontas | T1.2 |
| 24/11/2026 | o perfil achou variantes de grafia (`pendente`, `EM COBRANCA`, `PAGO`) que o de-para precisa cobrir | o de-para de domínios ganhou a coluna "variantes vistas no perfil" | T2.1 |
| 24/11/2026 | 10.277 combinações de chave repetida, que as 11 regras de erro não cobrem | sugerir um aviso de duplicata na T2.3 | T2.3 |
