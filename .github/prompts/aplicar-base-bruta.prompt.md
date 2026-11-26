---
description: Aplicar o framework do pos_venda a uma base bruta de pendências de pagamento no Databricks, seguindo o spec
---

Você vai aplicar o framework deste repositório a uma base bruta de pendências de pagamento que já está no Databricks,
seguindo o contrato [specs/aplicar-base-bruta/SPEC.md](../../specs/aplicar-base-bruta/SPEC.md).

1. Leia o [AGENTS.md](../../AGENTS.md), o [SPEC](../../specs/aplicar-base-bruta/SPEC.md) e, para o porquê de cada passo, o
   [guia 06](../../docs/06_GUIA_BASE_BRUTA.md).
2. Pergunte o que faltar destes dados:
   - a tabela da base bruta (`catalogo.schema.tabela`);
   - o perfil do Databricks CLI;
   - o nome curto da base.
3. Se `specs/<nome>/` ainda não existe, crie a pasta copiando `specs/aplicar-base-bruta/modelos/*.md`. Se já existe,
   retome da primeira tarefa sem `[x]` em `specs/<nome>/TAREFAS.md`.
4. Para saber qual comando rodar em cada tarefa e o que esperar, use o
   [passo a passo](../../specs/aplicar-base-bruta/PASSO_A_PASSO.md). Não invente comando: se o passo a passo não traz
   um comando para a tarefa, diga isso.
5. Execute **uma tarefa por vez**:
   - rode a verificação dela;
   - anote o resultado na linha "Resultado";
   - só então marque `[x]`.
6. Numa tarefa com **G#**, pare antes de executar. Mostre o que vai fazer e o que já foi decidido, e espere a aprovação.
7. Ao fim de cada etapa (E0 a E8), mostre o critério de aceite do SPEC § 6 e diga se passou.

Regras do SPEC § 5, sempre:
- não escreva na base bruta (R1);
- pare nos gates (R2);
- não marque tarefa sem verificação (R3);
- cite a origem `P##`, `M#` ou `L##` de cada decisão (R4);
- copie os módulos em vez de editá-los (R5);
- varra o que for commitar (R6);
- agendas nascem pausadas (R7);
- pare se a cota ou a permissão acabar (R8).
