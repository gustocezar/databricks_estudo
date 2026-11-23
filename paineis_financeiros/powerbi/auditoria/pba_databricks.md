# Power BI on Databricks Audit — warehouse 5f010b8396e591fb

Generated 2026-11-22 23:38 UTC by pba 0.1.0

Modes run: databricks

## Summary

| Phase | Score | Pass | Warn | Error | Info | N/A |
|---|---|---|---|---|---|---|
| Data Preparation | 100/100 | 10 | 0 | 0 | 0 | 0 |
| SQL Serving | 50/100 | 6 | 2 | 0 | 2 | 0 |
| Power BI Integration | — | — | — | — | — | — |
| Power BI Report Design | — | — | — | — | — | — |
| **Overall** | **75/100** | | | | | |

### Top 5 highest-impact issues

1. **[SS-005] Configure SQL warehouse scaling** (warn) — max_clusters=1 and 121 query(ies) queued > 1s.
2. **[SS-006] Increase min clusters for concurrent traffic** (warn) — 5 query(ies) waited >5s with min_clusters=1.
3. **[SS-009] Reasonable starting warehouse size** (info) — 2X-Small warehouse with queueing/spills.
4. **[SS-010] Monitor via system tables** (info) — 214 scaling event(s) but min/max not tuned.

## Data Preparation

### ✅ DP-001 Adopt medallion architecture (serve Gold) (pass)
**Target:** Serverless Starter Warehouse
**Status:** pass
**Summary:** All Power BI-referenced tables are in Gold-layer schemas.
**Reference:** [https://docs.databricks.com/lakehouse/medallion.html](https://docs.databricks.com/lakehouse/medallion.html)

### ✅ DP-002 Use star schema (pass)
**Target:** Serverless Starter Warehouse
**Status:** pass
**Summary:** No dim-to-dim relationships detected.
**Reference:** [https://learn.microsoft.com/power-bi/guidance/star-schema](https://learn.microsoft.com/power-bi/guidance/star-schema)

### ✅ DP-003 Use SQL views or persisted tables for repeated aggregations (pass)
**Target:** Serverless Starter Warehouse
**Status:** pass
**Summary:** No Power BI history.
**Reference:** [https://docs.databricks.com/sql/user/queries/index.html](https://docs.databricks.com/sql/user/queries/index.html)

### ✅ DP-004 Declare PK/FK with RELY (pass)
**Target:** Serverless Starter Warehouse
**Status:** pass
**Summary:** All Power BI tables have PK constraints with RELY.
**Reference:** [https://docs.databricks.com/tables/constraints.html](https://docs.databricks.com/tables/constraints.html)

### ✅ DP-005 Avoid wide and high-cardinality types (pass)
**Target:** Serverless Starter Warehouse
**Status:** pass
**Summary:** No wide or high-cardinality column types in Power BI tables.
**Reference:** [https://docs.databricks.com/tables/index.html](https://docs.databricks.com/tables/index.html)

### ✅ DP-006 Use auto-generated (computed) columns (pass)
**Target:** Serverless Starter Warehouse
**Status:** pass
**Summary:** No Power BI history.
**Reference:** [https://docs.databricks.com/sql/language-manual/sql-ref-syntax-ddl-create-table-using.html](https://docs.databricks.com/sql/language-manual/sql-ref-syntax-ddl-create-table-using.html)

### ✅ DP-007 Use Liquid Clustering or Z-order (pass)
**Target:** Serverless Starter Warehouse
**Status:** pass
**Summary:** All large PBI tables have clustering configured.
**Reference:** [https://docs.databricks.com/delta/clustering.html](https://docs.databricks.com/delta/clustering.html)

### ✅ DP-008 Predictive Optimization or recent OPTIMIZE/VACUUM (pass)
**Target:** Serverless Starter Warehouse
**Status:** pass
**Summary:** All PBI tables either use Predictive Optimization or were recently optimized.
**Reference:** [https://docs.databricks.com/optimizations/predictive-optimization.html](https://docs.databricks.com/optimizations/predictive-optimization.html)

### ✅ DP-009 Compute column statistics (pass)
**Target:** Serverless Starter Warehouse
**Status:** pass
**Summary:** All PBI tables have column statistics.
**Reference:** [https://docs.databricks.com/sql/language-manual/sql-ref-syntax-aux-analyze-table.html](https://docs.databricks.com/sql/language-manual/sql-ref-syntax-aux-analyze-table.html)

### ✅ DP-010 Evaluate materialized views (pass)
**Target:** Serverless Starter Warehouse
**Status:** pass
**Summary:** No Power BI history.
**Reference:** [https://docs.databricks.com/sql/user/materialized-views.html](https://docs.databricks.com/sql/user/materialized-views.html)

## SQL Serving

### ⚠️ SS-005 Configure SQL warehouse scaling (warn)
**Target:** Serverless Starter Warehouse
**Status:** fail
**Summary:** max_clusters=1 and 121 query(ies) queued > 1s.
**Why it matters:** With max_clusters=1 the warehouse cannot scale out, so concurrent queries queue.
**How to fix:** Set max_clusters >= 2 (typical: 4) so the warehouse can absorb concurrent BI traffic.
**Reference:** [https://docs.databricks.com/sql/admin/sql-endpoints.html#scaling](https://docs.databricks.com/sql/admin/sql-endpoints.html#scaling)
                <details><summary>Evidence</summary>

                ```json
                {
  "max_clusters": 1,
  "queued_query_count": 121
}
                ```
                </details>

### ⚠️ SS-006 Increase min clusters for concurrent traffic (warn)
**Target:** Serverless Starter Warehouse
**Status:** fail
**Summary:** 5 query(ies) waited >5s with min_clusters=1.
**Why it matters:** When min_clusters=1, the warehouse must scale out from cold each time concurrency rises.
**How to fix:** Raise min_clusters to 2 to keep capacity warm during business hours.
**Reference:** [https://docs.databricks.com/sql/admin/sql-endpoints.html#scaling](https://docs.databricks.com/sql/admin/sql-endpoints.html#scaling)
                <details><summary>Evidence</summary>

                ```json
                {
  "min_clusters": 1,
  "long_wait_count": 5
}
                ```
                </details>

### ℹ️ SS-009 Reasonable starting warehouse size (info)
**Target:** Serverless Starter Warehouse
**Status:** fail
**Summary:** 2X-Small warehouse with queueing/spills.
**Why it matters:** 2X-Small is appropriate for very low-traffic dev only. Production BI will queue or spill.
**How to fix:** Start at Medium for production BI workloads; tune from there based on monitoring.
**Reference:** [https://docs.databricks.com/sql/admin/sql-endpoints.html#sizes](https://docs.databricks.com/sql/admin/sql-endpoints.html#sizes)
                <details><summary>Evidence</summary>

                ```json
                {
  "queued": true,
  "spilled": false
}
                ```
                </details>

### ℹ️ SS-010 Monitor via system tables (info)
**Target:** Serverless Starter Warehouse
**Status:** fail
**Summary:** 214 scaling event(s) but min/max not tuned.
**Why it matters:** warehouse_events shows the warehouse is scaling, but scaling parameters look untuned.
**How to fix:** Inspect system.compute.warehouse_events and adjust min/max clusters to match observed concurrency.
**Reference:** [https://docs.databricks.com/admin/system-tables/index.html](https://docs.databricks.com/admin/system-tables/index.html)
                <details><summary>Evidence</summary>

                ```json
                {
  "scaling_event_count": 214,
  "min_clusters": 1,
  "max_clusters": 1
}
                ```
                </details>

### ✅ SS-001 Use SQL warehouse, not all-purpose cluster (pass)
**Target:** Serverless Starter Warehouse
**Status:** pass
**Summary:** No Power BI queries observed on all-purpose clusters.
**Reference:** [https://docs.databricks.com/sql/admin/sql-endpoints.html](https://docs.databricks.com/sql/admin/sql-endpoints.html)

### ✅ SS-002 Use Serverless SQL warehouse (pass)
**Target:** Serverless Starter Warehouse
**Status:** pass
**Summary:** Warehouse is Serverless.
**Reference:** [https://docs.databricks.com/sql/admin/serverless.html](https://docs.databricks.com/sql/admin/serverless.html)

### ✅ SS-003 Enable SQL warehouse Auto stop (pass)
**Target:** Serverless Starter Warehouse
**Status:** pass
**Summary:** Auto stop set to 10 minutes.
**Reference:** [https://docs.databricks.com/sql/admin/sql-endpoints.html#auto-stop](https://docs.databricks.com/sql/admin/sql-endpoints.html#auto-stop)

### ✅ SS-004 Right-size warehouse for dataset (pass)
**Target:** Serverless Starter Warehouse
**Status:** pass
**Summary:** No Power BI compute samples — cannot evaluate sizing.
**Reference:** [https://docs.databricks.com/sql/admin/sql-endpoints.html#sizes](https://docs.databricks.com/sql/admin/sql-endpoints.html#sizes)

### ✅ SS-007 Same warehouse for same dataset (pass)
**Target:** Serverless Starter Warehouse
**Status:** pass
**Summary:** No table seen across multiple warehouses.
**Reference:** [https://docs.databricks.com/sql/admin/sql-endpoints.html#cache](https://docs.databricks.com/sql/admin/sql-endpoints.html#cache)

### ✅ SS-008 Separate warehouses for different workloads (pass)
**Target:** Serverless Starter Warehouse
**Status:** pass
**Summary:** BI=0 ETL=109; not mixed.
**Reference:** [https://docs.databricks.com/sql/admin/sql-endpoints.html](https://docs.databricks.com/sql/admin/sql-endpoints.html)

## Power BI Integration

### — IN-001 Same region for Power BI and Databricks (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: required input WorkspaceConfig not collected
**Reference:** [https://learn.microsoft.com/power-bi/admin/service-admin-where-is-my-tenant-located](https://learn.microsoft.com/power-bi/admin/service-admin-where-is-my-tenant-located)

### — IN-002 Use DirectQuery on facts and Dual on dimensions (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['pbix', 'pbip', 'workspace'] but active modes are ['databricks']
**Reference:** [https://learn.microsoft.com/power-bi/transform-model/desktop-storage-mode](https://learn.microsoft.com/power-bi/transform-model/desktop-storage-mode)

### — IN-003 Consider composite models (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['pbix', 'pbip', 'workspace'] but active modes are ['databricks']
**Reference:** [https://learn.microsoft.com/power-bi/transform-model/desktop-composite-models](https://learn.microsoft.com/power-bi/transform-model/desktop-composite-models)

### — IN-004 Consider hybrid tables for large facts (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['pbix', 'pbip', 'workspace'] but active modes are ['databricks']
**Reference:** [https://learn.microsoft.com/power-bi/connect-data/desktop-incremental-refresh#hybrid-tables](https://learn.microsoft.com/power-bi/connect-data/desktop-incremental-refresh#hybrid-tables)

### — IN-005 Use incremental refresh for large Import tables (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['pbix', 'pbip', 'workspace'] but active modes are ['databricks']
**Reference:** [https://learn.microsoft.com/power-bi/connect-data/incremental-refresh-overview](https://learn.microsoft.com/power-bi/connect-data/incremental-refresh-overview)

### — IN-006 Tune Power BI query parallelization (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['workspace'] but active modes are ['databricks']
**Reference:** [https://learn.microsoft.com/power-bi/transform-model/desktop-storage-mode](https://learn.microsoft.com/power-bi/transform-model/desktop-storage-mode)

### — IN-007 Enable SSO between Power BI and Databricks (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['workspace'] but active modes are ['databricks']
**Reference:** [https://docs.databricks.com/integrations/configure-power-bi-sso.html](https://docs.databricks.com/integrations/configure-power-bi-sso.html)

### — IN-008 Use parameters for environment switching (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['pbix', 'pbip', 'workspace'] but active modes are ['databricks']
**Reference:** [https://learn.microsoft.com/power-bi/connect-data/desktop-dynamic-m-query-parameters](https://learn.microsoft.com/power-bi/connect-data/desktop-dynamic-m-query-parameters)

### — IN-009 Use clustered gateways (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['workspace'] but active modes are ['databricks']
**Reference:** [https://learn.microsoft.com/data-integration/gateway/service-gateway-high-availability-clusters](https://learn.microsoft.com/data-integration/gateway/service-gateway-high-availability-clusters)

### — IN-010 Use Publish to Power BI Service from Databricks (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: required input WorkspaceConfig not collected
**Reference:** [https://docs.databricks.com/integrations/configure-power-bi-online-service.html](https://docs.databricks.com/integrations/configure-power-bi-online-service.html)

### — IN-011 Use Automatic Publishing from Unity Catalog (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: required input WorkspaceConfig not collected
**Reference:** [https://docs.databricks.com/integrations/configure-power-bi-online-service.html](https://docs.databricks.com/integrations/configure-power-bi-online-service.html)

## Power BI Report Design

### — RD-001 Limit visuals per page (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['pbix', 'pbip', 'workspace'] but active modes are ['databricks']
**Reference:** [https://learn.microsoft.com/power-bi/guidance/power-bi-optimization](https://learn.microsoft.com/power-bi/guidance/power-bi-optimization)

### — RD-002 Limit rows and columns surfaced in DirectQuery (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['pbix', 'pbip', 'workspace'] but active modes are ['databricks']
**Reference:** [https://learn.microsoft.com/power-bi/guidance/power-bi-optimization](https://learn.microsoft.com/power-bi/guidance/power-bi-optimization)

### — RD-003 Use user-defined aggregations on large fact tables (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['pbix', 'pbip', 'workspace'] but active modes are ['databricks']
**Reference:** [https://learn.microsoft.com/power-bi/transform-model/aggregations-advanced](https://learn.microsoft.com/power-bi/transform-model/aggregations-advanced)

### — RD-004 Enable automatic aggregations for DirectQuery (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['pbix', 'pbip', 'workspace'] but active modes are ['databricks']
**Reference:** [https://learn.microsoft.com/power-bi/transform-model/aggregations-auto](https://learn.microsoft.com/power-bi/transform-model/aggregations-auto)

### — RD-005 Avoid many-to-many relationships (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['pbix', 'pbip', 'workspace'] but active modes are ['databricks']
**Reference:** [https://learn.microsoft.com/power-bi/transform-model/desktop-many-to-many-relationships](https://learn.microsoft.com/power-bi/transform-model/desktop-many-to-many-relationships)

### — RD-006 Use Assume Referential Integrity where valid (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['pbix', 'pbip', 'workspace'] but active modes are ['databricks']
**Reference:** [https://learn.microsoft.com/power-bi/transform-model/desktop-relationships-troubleshoot](https://learn.microsoft.com/power-bi/transform-model/desktop-relationships-troubleshoot)

### — RD-007 Configure 'Is nullable' to match source (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: required input SemanticModel not collected
**Reference:** [https://learn.microsoft.com/power-bi/transform-model/desktop-tutorial-create-calculated-columns](https://learn.microsoft.com/power-bi/transform-model/desktop-tutorial-create-calculated-columns)

### — RD-008 Move transformations left (prefer SQL views) (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['pbix', 'pbip', 'workspace'] but active modes are ['databricks']
**Reference:** [https://learn.microsoft.com/power-bi/guidance/power-query-folding](https://learn.microsoft.com/power-bi/guidance/power-query-folding)

### — RD-009 Use efficient DAX patterns (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['pbix', 'pbip', 'workspace'] but active modes are ['databricks']
**Reference:** [https://learn.microsoft.com/dax/best-practices/dax-aggregators](https://learn.microsoft.com/dax/best-practices/dax-aggregators)

### — RD-010 Add Apply All Slicers when many slicers (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['pbix', 'pbip', 'workspace'] but active modes are ['databricks']
**Reference:** [https://learn.microsoft.com/power-bi/create-reports/desktop-query-reduction](https://learn.microsoft.com/power-bi/create-reports/desktop-query-reduction)

### — RD-011 Avoid DAX calculated columns and calculated tables (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['pbix', 'pbip', 'workspace'] but active modes are ['databricks']
**Reference:** [https://learn.microsoft.com/power-bi/guidance/import-modeling-data-reduction](https://learn.microsoft.com/power-bi/guidance/import-modeling-data-reduction)
