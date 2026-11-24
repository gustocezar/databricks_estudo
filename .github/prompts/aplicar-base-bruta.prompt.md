---
description: Aplicar o framework do pos_venda a uma base bruta de pendências de pagamento no Databricks
---

Você vai aplicar o framework deste repositório a uma base bruta de pendências de pagamento que já está no Databricks.

Antes de tudo, leia [AGENTS.md](../../AGENTS.md) e [docs/06_GUIA_BASE_BRUTA.md](../../docs/06_GUIA_BASE_BRUTA.md).
Depois, pergunte o que faltar destes dados:

- a tabela da base bruta (`catalogo.schema.tabela`);
- o perfil do Databricks CLI;
- o catálogo e o prefixo dos schemas de destino.

Siga as etapas 0 a 7 do guia, **uma por vez**:

1. **Etapa 0 (permissões):** rode só comandos de leitura (`current-user me`, `SHOW GRANTS`). Diga o que pode e o que
   não pode ser feito e recomende a trilha de qualidade: **A** (DQX como código, `dqx_codigo/`) ou **B** (DQX Studio
   como app, `dqx_studio/`). Se não houver permissão para conceder `USE CATALOG` e `CREATE SCHEMA` ao service
   principal de um app, a trilha é A.
2. **Etapa 1 (ficha):** perfile a base com SQL de leitura e preencha a ficha do guia. Pare e mostre.
3. **Etapa 2 (mapeamento):** proponha o de-para de cada conceito e a decisão para o que falta. Pare e mostre.
4. **Etapas 3 a 7:** gere ou adapte o código a partir dos modelos do repositório. Mostre o critério de saída de cada
   etapa antes de passar para a próxima.

Regras:
- Nunca escreva na base bruta nem no schema dela.
- Peça aprovação antes de criar objeto, rodar job, fazer deploy, ligar agenda, instalar app, commit ou push.
- Cite a prática (`P##`), o módulo (`M#`) ou a lição (`L##`) em cada decisão.
- Se o repositório não responde, diga isso.
