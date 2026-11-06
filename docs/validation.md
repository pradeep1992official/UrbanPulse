# Validation performed

The portable versions were checked locally on 6 November 2026 using Python 3.13. Notebook structure, Python syntax and notebook/script calculation parity passed for all four notebooks.

`python tests/test_pipeline.py` runs the real preparation and statistics scripts on an isolated six-request fixture plus a duplicate. It checks duplicate rejection, preservation of missing geography and recorded status, date parse flags, negative-duration exclusion, coordinate quality flags, statistics chart creation, the exact 41-column MySQL input contract and missing-ID failure handling. It also exports and counts all 15 SQL definitions. These fixtures are synthetic and do not support civic findings.

No new live extraction or MySQL load was executed. The SQL queries were inspected and exported, not independently executed against MySQL. Successful database evidence described in the requirements review comes from the original supplied notebook outputs. All changed notebooks need fresh execution with matching genuine data and metadata before submission.
