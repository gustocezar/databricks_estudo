# Pós-venda · Diretor financeiro (visão executiva)
Evaluated: 2026-11-21 01:03 UTC · Best practices reference: 2026-05-30

> [!NOTE]
> Disclaimer:
> 1. This report is AI-generated and may contain errors — verify findings against your actual environment before making changes.
> 2. Data quality assessments are based on Unity Catalog metadata and a limited sample of row values; column-level statistics (min, max, distinct count) are only available when pre-computed in UC, so some data insights may be incomplete or imprecise.

## Executive Summary
The Pós-venda · Diretor financeiro (visão executiva) Genie Space is generally well-configured but has areas for improvement in naming conventions, Unity Catalog descriptions, and potential PII data exposure. Addressing these issues will enhance Genie's accuracy and user experience. The evaluation identified 1 🔴 Critical, 3 🟡 Recommended, and 1 🟢 Optional findings.

## 🔴 Critical Issues
### Potential PII data exposure
* **Details**: The tables contain columns that might store PII or sensitive information (e.g., 'CPF inválido' in mv_qualidade_dados). Verify if these columns are properly masked or secured.
* **Recommendation**: Review and apply appropriate column masks or security measures for columns potentially containing PII or sensitive data.
* **Affected Objects**:
  | Object Name | Type |
  | --- | --- |
  | pos_venda.ontologia.mv_qualidade_dados | Table/View |
  | CPF inválido | Column |

## 🟡 Recommended Improvements
### Table count approaching upper limit
* **Details**: The space contains 4 tables/views, which is within the recommended range (≤10). However, consider pre-joining related tables into views or metric views if the number of tables grows.
* **Recommendation**: Monitor table count and consider consolidation if it approaches the 30-table limit.
* **Affected Objects**:
  | Object Name |
  | --- |
  | pos_venda.ontologia.mv_carteira_em_aberto |
  | pos_venda.ontologia.mv_qualidade_dados |
  | pos_venda.ontologia.mv_recuperacao |
  | pos_venda.ontologia.mv_safra_recuperacao |

### Column names should follow snake_case convention
* **Details**: Column names in the space configuration are in mixed case (e.g., 'Canal de venda', 'Categoria do produto'). The organization convention prefers snake_case (lowercase with underscores).
* **Recommendation**: Update column names or column_configs to follow snake_case naming convention.
* **Affected Objects**:
  | Object Name |
  | --- |
  | Canal de venda |
  | Categoria do produto |
  | Faixa de atraso |
  | Fase da cobrança |
  | Forma de pagamento |
  | Grupo da forma de pagamento |
  | Grupo do motivo |
  | Motivo da pendência |
  | Periodicidade |
  | Produto |
  | Regional |
  | Status da apólice |
  | Status de cobrança |
  | UF do ponto de venda |

### Missing or inconsistent UC table and column descriptions
* **Details**: Some tables and columns lack descriptions in Unity Catalog. For example, 'mv_carteira_em_aberto' has a description, but many of its columns do not. 'mv_qualidade_dados' lacks a description entirely.
* **Recommendation**: Add or update descriptions for tables and columns in Unity Catalog to improve clarity and Genie's understanding.
* **Affected Objects**:
  | Object Name |
  | --- |
  | pos_venda.ontologia.mv_carteira_em_aberto |
  | pos_venda.ontologia.mv_qualidade_dados |
  | Mês de referência |
  | Foto mais recente |
  | Fim de mês |
  | Status de cobrança |
  | Fase da cobrança |
  | Faixa de atraso |

### Date columns should use consistent naming and types
* **Details**: Date-related columns (e.g., 'Data de referência', 'Mês de referência', 'Dia') have varying data types (date, timestamp). Ensure consistent naming and data types for date columns.
* **Recommendation**: Standardize date column names and data types across tables for better clarity and query accuracy.
* **Affected Objects**:
  | Object Name |
  | --- |
  | Data de referência |
  | Mês de referência |
  | Dia |
  | Mês da baixa |

## 🟢 Optional Enhancements
### Effective mix of instruction types
* **Details**: The space configuration includes a good mix of SQL expressions, example queries, and text instructions, following the recommended priority hierarchy. This should help Genie understand the domain-specific requirements and generate accurate queries.
* **Recommendation**: Continue to maintain and refine the instruction mix as needed to support user queries and business requirements.
* **Affected Objects**:
  | Object Name |
  | --- |
  | text_instructions |
  | example_question_sqls |
  | sql_snippets |