# Genie Space IQ Scan - `01f1e4772cf610a8baf0c236595c284b`

**Score:** 8 / 12  |  **Maturity:** Not Ready

## Checks

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Data sources exist | PASS | 2 table(s), 4 metric view(s) configured |
| 2 | Table descriptions | PASS | 2/2 tables have descriptions (100%) |
| 3 | Column descriptions | FAIL | 0/32 configured columns have descriptions (0%) - 50%+ required - advisory: no column synonyms defined |
| 4 | Text instructions | WARN | 2086 chars of instructions - consider trimming below 2000 |
| 5 | Join specifications | FAIL | 0 join spec(s) for 6 data sources - define at least one join |
| 6 | Data source count 1-12 | PASS | 6 data source(s) |
| 7 | 8+ example SQLs | WARN | 8 example SQL(s) - 10-15 is the sweet spot - advisory: 8/8 lack usage_guidance |
| 8 | SQL snippets | WARN | 0 filter(s), 0 measure(s), 0 expression(s), 4 function(s) - consider adding filters and measures |
| 9 | Entity/format matching | PASS | 32 column(s) with entity/format matching enabled (RLS-tainted tables not evaluated offline) |
| 10 | 10+ benchmark questions | PASS | 14 benchmark question(s) |
| 11 | Optimization workflow completed | FAIL | No optimization_run found - run an optimization workflow |
| 12 | Optimization accuracy >= 85% | FAIL | No optimization accuracy available |

## Findings (7)

- [FAIL] Check 3 - Column descriptions: 0/32 configured columns have descriptions (0%) - 50%+ required - advisory: no column synonyms defined
- [FAIL] Check 5 - Join specifications: 0 join spec(s) for 6 data sources - define at least one join
- [FAIL] Check 11 - Optimization workflow completed: No optimization_run found - run an optimization workflow
- [FAIL] Check 12 - Optimization accuracy >= 85%: No optimization accuracy available
- [WARN] Check 4 - Text instructions: 2086 chars of instructions - consider trimming below 2000
- [WARN] Check 7 - 8+ example SQLs: 8 example SQL(s) - 10-15 is the sweet spot - advisory: 8/8 lack usage_guidance
- [WARN] Check 8 - SQL snippets: 0 filter(s), 0 measure(s), 0 expression(s), 4 function(s) - consider adding filters and measures

## Ranked next steps

1. Check 3 - Column descriptions: Add column descriptions and synonyms (Lever 1: Tables & Columns).
2. Check 5 - Join specifications: Add join specifications between related tables (Lever 4: Joins).
3. Check 11 - Optimization workflow completed [manual]: Run an optimization workflow. Not a config lever.
4. Check 12 - Optimization accuracy >= 85% [manual]: Raise optimization accuracy to >=85% by iterating. Not a config lever.
5. Check 4 - Text instructions: Add or expand text instructions (Lever 5: Instructions).
6. Check 7 - 8+ example SQLs: Add curated example question/SQL pairs (Lever 6: SQL Expressions).
7. Check 8 - SQL snippets: Add reusable SQL snippets: filters, measures, expressions (Lever 6).

