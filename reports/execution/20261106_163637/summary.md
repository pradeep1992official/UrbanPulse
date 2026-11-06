# Fresh MySQL execution results

Notebook 04 completed successfully on 6 November 2026 against **MySQL 8.4.11**, with certificate and hostname verification enabled and an encrypted connection confirmed. All seven code cells executed without errors. The input was the current canonical `data/cleaned/nyc_cleaned.csv`, identified by SHA-256 `80502bf0307c77c3f2ece33ea97ec6a126d34b7b82d6ed1a129c06293dd8a7be`.

## Load validation

| Check | Result |
|---|---:|
| Raw rows | 100,000 |
| Rejected duplicate rows | 0 |
| Cleaned rows | 100,000 |
| Staged rows | 100,000 |
| Published rows | 100,000 |
| Full row-by-row and field-by-field read-back comparison | Passed |
| Publication after validation | Passed |
| Flagged invalid-date rows | 119 |
| Coordinate-quality issue rows | 1,585 |

See the [successful load report](mysql/load_validation_20261106_110646_0b34c517.json), [executed notebook](04_mysql_sql_analytics.ipynb) and [exported schema](mysql/schema.sql). The previous published table was retained as `service_requests_backup_20261106_110646_0b34c517`; it was not deleted.

## SQL and Python agreement

All **15 SQL investigations executed successfully**. Each exported result was compared with an independent pandas calculation from the canonical CSV. All comparisons passed, including distinct volume, grouped counts, temporal demand, resolution statistics, category/agency medians, interpolated IQR quartiles and outlier counts, duration rows, geographic cells, closure rates and high-volume/long-duration categories.

Counts and identifiers agree. Floating-point comparisons use relative tolerance `1e-9` and absolute tolerance `1e-7`; percentage comparisons allow `5.1e-6` percentage points because MySQL decimal division exports them to five decimal places. This is rounding precision, not a difference in KPI definitions.

See the [comparison report](sql_python_comparison.json), [15 completed evidence rows](mysql/analyst_evidence.csv), exported SQL, aggregate/result CSVs and charts in `mysql/`. The completed written observations were taken from the canonical-data Python findings after confirming numerical agreement. They are not placeholders.

The [execution manifest](manifest.json) records code and artifact hashes, notebook timestamps and the successful pipeline and dashboard regression tests. Package versions are in [environment.txt](environment.txt). Credentials and the CA certificate remain outside Git.

## Streamlit database integration

The app was switched to its live MySQL source and all five views loaded successfully. The five displayed KPI values matched the canonical CSV source. See [the MySQL dashboard validation](mysql_dashboard_validation.json).

## Remaining limitation

This closes the outstanding current MySQL load and SQL-verification work. It does not establish successful fresh API extraction or recover the original snapshot's missing download metadata. The canonical snapshot's metadata explicitly records its import from the preserved raw extract. The [earlier processing summary](../20261106_153641/summary.md) documents preparation, statistics and canonical CSV dashboard checks.
