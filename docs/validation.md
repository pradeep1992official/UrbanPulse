# Validation performed

## Fresh processing run

See the [6 November execution summary](../reports/execution/20261106_153641/summary.md) for actual notebook outputs, timestamps, hashes and check logs. Notebook 02 and notebook 03 passed on a preserved 100,000-row raw snapshot imported with explicit provenance. All five dashboard views passed against the newly prepared canonical data, and the 15 Python investigations were regenerated. The live API extraction attempt was terminated after stalling and diagnostic timeouts; no successful fresh download is claimed. MySQL remains unexecuted pending connection settings. The historical validation scope below remains relevant to the earlier report.

The portable versions were checked locally on 6 November 2026 using Python 3.13. Notebook structure, Python syntax and notebook/script calculation parity passed for all four notebooks.

`python tests/test_pipeline.py` runs the real preparation and statistics scripts on an isolated six-request fixture plus a duplicate. It checks duplicate rejection, preservation of missing geography and recorded status, date parse flags, negative-duration exclusion, coordinate quality flags, statistics chart creation, the exact 41-column MySQL input contract and missing-ID failure handling. It also exports and counts all 15 SQL definitions. These fixtures are synthetic and do not support civic findings.

No new live extraction or MySQL load was executed. The SQL queries were inspected and exported, not independently executed against MySQL. Successful database evidence described in the requirements review comes from the original supplied notebook outputs. All changed notebooks need fresh execution with matching genuine data and metadata before submission.

The Streamlit dashboard is covered by `python tests/test_dashboard.py`. Tests use Streamlit AppTest to exercise all five views and all investigation selectors, shared filters, missing-file states and missing database configuration. Separate assertions check exact KPI denominators, the strict greater-than-72-hours boundary, negative-duration exclusion, source-status preservation and exclusion of flagged imputed coordinates. No live MySQL service is required by these tests.
