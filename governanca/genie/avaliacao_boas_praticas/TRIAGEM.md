# Avaliação dos espaços Genie com o genie-best-practices-agent (20/11/2026)

Ferramenta: [databricks-solutions/genie-best-practices-agent](https://github.com/databricks-solutions/genie-best-practices-agent)
(commit 061a909). Relatórios originais, gerados por IA: `analista_relatorio_original.md` e `diretor_relatorio_original.md`.

## Como foi rodado (adaptações ao Free Edition)

- **Sem Spark local:** a extração "ao vivo" da ferramenta exige cluster. Usei o modo offline. `extrair.py` gera os mesmos
  JSONs (configuração do espaço + metadados do UC) pela API e pelo warehouse, incluindo as metric views, que a
  extração original ignora quando estão em `data_sources.metric_views`.
- **Modelo:** o Free Edition não tem os endpoints Claude Opus validados pela ferramenta. O `qwen35-122b` falhou na saída
  estruturada (400). Usei o `databricks-llama-4-maverick`, que exige limitar a saída a 8.192 tokens (ajuste feito em
  `rodar.py` em tempo de execução, sem alterar o repositório).
- **Benchmarks** pela API oficial de avaliação da Genie (Genie Eval), não pelo comparador do `genie.py`.
- Sem busca da documentação na internet (`skip_fetch_best_practices`): vale a referência embutida de 30/05/2026.

## Benchmarks oficiais (Genie Eval)

| Espaço | Resultado | Observação |
|---|---|---|
| Analista | 13 de 13 | — |
| Diretor | 12 de 14 → **14 de 14** | As 2 reprovadas tinham gabarito antigo (fim de mês e variação entre fins de mês). A Genie já usava `Saldo de fechamento` e `Variação mensal do saldo`. Gabaritos atualizados no `genie.py` e as 2 perguntas reavaliadas: GOOD. |

## Triagem dos achados

| Achado | Espaço | Veredito | Ação |
|---|---|---|---|
| 63 de 87 campos das metric views sem descrição (carteira 24/38, qualidade 15/15, recuperação 12/20, safra 12/14) | Diretor | **Procede** (o relatório disse que `mv_qualidade_dados` não tem descrição; a view tem, os campos é que não) | **Aplicado em 20/11**: `DESCR` em `gerar_ontologia_sql.py`; 87 de 87 campos descritos no UC; schema `ontologia` 225/225 |
| "CPF inválido" seria dado pessoal | Diretor | **Falso positivo**: é uma contagem de eventos com CPF inválido, sem CPF | **Aplicado**: a descrição diz "É uma contagem: não contém CPF" |
| Meses como `timestamp` e dias como `date` | Diretor | **Procede**, impacto baixo | **Aplicado**: `CAST(DATE_TRUNC(...) AS DATE)` em 5 dimensões; medidas de janela iguais antes e depois. Efeito colateral: a Genie passou a filtrar "semanas de dezembro" por `Semana` e perdia a semana de 30/11. Corrigido com a descrição de `Semana` e o exemplo `qualidade_semanal` filtrando por `Dia`; avaliação final 27 de 27 |
| `cliente_id` em texto claro na view `pendencia` | Analista | **Procede em parte**: é chave pseudônima (não é CPF) e já está excluída na Genie, mas a camada de ontologia promete "sem identificadores pessoais" | **Aplicado em 21/11/2026**: `cliente_id` saiu de `ontologia.pendencia` e também de `ontologia.pagamento` (mesma exposição); views recriadas com `views_preservadas.garantir_view(..., ddl=...)`, com as 5 tags, as descrições e a Wiki iguais às de antes; exclusão da coluna tirada do `genie.py`; Page "Cliente" ajustada. Depois, por decisão do usuário, `cliente_id` saiu também de `ontologia.cliente` (relação Cliente–Apólice por `cliente_sk`) |
| Colunas fora de snake_case | ambos | **Não procede**: as dimensões das metric views usam nomes de negócio de propósito (a Genie casa melhor com a pergunta); a regra vem do `org_conventions.md` de exemplo da ferramenta | Nenhuma |
| Quantidade de tabelas, ausência de join_specs, entity matching em coluna excluída | ambos | **Não procede**: 4 a 6 objetos, metric views sem join entre si | Nenhuma |
| Ampliar benchmarks e deixar instruções mais específicas | Analista | Genérico | Opcional |
