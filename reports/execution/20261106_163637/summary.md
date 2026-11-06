# MySQL execution results

6 November 2026. Notebook 04 passed all seven code cells on MySQL 8.4.11 with verified TLS.

| Check | Result |
|---|---|
| Raw / cleaned / staged / published rows | 100,000 each |
| Rejected duplicates | 0 |
| Full row and field read-back comparison | Passed |
| Publication after validation | Passed |
| Fifteen SQL/Python comparisons | All passed |
| Live MySQL dashboard | All five views passed; KPIs match CSV |
| Pipeline and dashboard tests | Passed |

There are 119 flagged invalid-date rows and 1,585 coordinate-quality issues. The previous published table was retained as a backup; its name is recorded in the load report.

## Evidence

- [Executed notebook](../../../notebooks/04_mysql_sql_analytics.ipynb)
- [Load validation](mysql/load_validation_20261106_110646_0b34c517.json)
- [Schema](mysql/schema.sql)
- [SQL/Python comparison](sql_python_comparison.json)
- [All 15 completed interpretations](mysql/analyst_evidence.csv)
- [MySQL dashboard check](mysql_dashboard_validation.json)
- [Pipeline and dashboard test results](manifest.json)
- [Manifest and hashes](manifest.json) and [package versions](environment.txt)

SQL, result CSVs and charts are in `mysql/`. Counts and identifiers agree. Numeric tolerances are `rtol=1e-9`, `atol=1e-7`; percentages allow `5.1e-6` percentage points for MySQL's five-decimal rounding.

This verifies current database processing. Original API extraction metadata is still unavailable. [Earlier preparation run](../20261106_153641/summary.md).
