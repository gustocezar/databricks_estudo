# Pós-venda · Analista financeiro (cobrança e recuperação)
Evaluated: 2026-11-20 23:34 UTC · Best practices reference: 2026-05-30

> [!NOTE]
> Disclaimer:
> 1. This report is AI-generated and may contain errors — verify findings against your actual environment before making changes.
> 2. Data quality assessments are based on Unity Catalog metadata and a limited sample of row values; column-level statistics (min, max, distinct count) are only available when pre-computed in UC, so some data insights may be incomplete or imprecise.

## Executive Summary
The Pós-venda · Analista financeiro (cobrança e recuperação) Genie Space is generally well-configured, with a solid foundation for Genie's operations. The evaluation identified several areas for improvement to enhance accuracy, compliance, and overall configuration. The space achieved a benchmark accuracy of N/A (not provided). The evaluation findings are categorized into 7 issues across 3 severity levels: 🔴 Critical (1), 🟡 Recommended (6), 🟢 Optional (0).

## 🔴 Critical Issues
### Potential PII data detected in cleartext
* **Details:** The column 'cliente_id' in 'pos_venda.ontologia.pendencia' contains potential PII data. Although it is excluded from Genie's results, it is still stored in cleartext without masking.
* **Affected Objects:** `pos_venda.ontologia.pendencia.cliente_id`
* **Recommendation:** Apply a UC column mask or tokenization to 'cliente_id' to protect sensitive client information.

## 🟡 Recommended Improvements
### Table count is within the upper recommended range
* **Details:** The space contains 6 tables, which is within the recommended range of 6-10 tables for mature spaces. Consider reviewing the table structure for potential consolidation opportunities.
* **Affected Objects:** `pos_venda.gold.dq_barrados_por_motivo_dia`, `pos_venda.ontologia.mv_carteira_em_aberto`, `pos_venda.ontologia.mv_qualidade_dados`, `pos_venda.ontologia.mv_recuperacao`, `pos_venda.ontologia.mv_safra_recuperacao`, `pos_venda.ontologia.pendencia`
* **Recommendation:** Review the tables for potential consolidation or pre-joining related tables into views or metric views to improve Genie's focus and accuracy.

### No explicit join specifications defined
* **Details:** The space does not have explicit join specifications defined in the configuration, relying on Genie's inference from column names and metadata.
* **Affected Objects:** `instructions.join_specs`
* **Recommendation:** Consider adding join specifications to ensure correctness and avoid ambiguous or incorrect joins, especially if more tables are added in the future.

### Column 'cliente_id' is excluded but has entity matching disabled
* **Details:** The column 'cliente_id' in table 'pos_venda.ontologia.pendencia' is excluded from Genie's results but has entity matching disabled. While this does not directly cause an issue, it's worth reviewing to ensure it aligns with the intended use of the column.
* **Affected Objects:** `pos_venda.ontologia.pendencia.cliente_id`
* **Recommendation:** Review the configuration for 'cliente_id' to ensure it is correctly excluded and consider adding a description or other relevant configurations if necessary.

### Column names are not consistently in snake_case
* **Details:** The column names in the tables are not consistently in snake_case. For example, 'Canal de venda' and 'produto_nome' use different casing conventions.
* **Affected Objects:** `pos_venda.ontologia.mv_carteira_em_aberto.Canal de venda`, `pos_venda.ontologia.pendencia.produto_nome`
* **Recommendation:** Ensure that column names follow a consistent naming convention, preferably snake_case, to improve readability and compatibility with Genie.

### Benchmark questions are provided but could be expanded
* **Details:** The space includes 13 benchmark questions, which is a good start. However, consider expanding this set to cover more scenarios and edge cases.
* **Affected Objects:** `benchmarks.questions`
* **Recommendation:** Add more benchmark questions to systematically test Genie's accuracy across a broader range of user queries.

### Text instructions are clear but could be more specific
* **Details:** The general text instructions are clear and provide useful guidance. However, some parts could be more specific to avoid potential misinterpretation.
* **Affected Objects:** `instructions.text_instructions`
* **Recommendation:** Review the text instructions to ensure they are as clear and specific as possible, and consider breaking down complex instructions into simpler, more actionable guidance.

## 🟢 Optional Enhancements
No issues found.