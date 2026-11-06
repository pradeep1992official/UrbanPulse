# Execution results on 6 November 2026

The changed preparation and statistics notebooks were executed successfully against the existing 100,000-row raw snapshot. The dashboard and all 15 Python investigations were then rerun against the newly prepared canonical CSV. This is fresh processing evidence; it is not evidence of a successful new API extraction or a current MySQL load.

| Stage | Result | Evidence |
|---|---|---|
| Live API extraction | Unsuccessful; long-running attempt explicitly terminated after diagnostic request timeouts | [Attempt manifest](../20261106_152719/manifest.json) |
| Preserved raw snapshot import | Passed; 100,000 rows projected to the selected 16 source fields | [Import provenance](extraction_metadata.json) |
| Notebook 02 preparation | Passed; all 10 code cells executed, 100,000 cleaned rows | [Executed notebook](02_data_preparation.ipynb), [validation log](cleaning_validation_log.csv), [dictionary](data_dictionary.csv) |
| Notebook 03 statistics | Passed; all 7 code cells executed with tables and chart outputs | [Executed notebook](03_statistics.ipynb) |
| Notebook 04 MySQL | Not executed; connection settings unavailable in the execution environment | [Manifest](manifest.json) |
| Pipeline regression checks | Passed | [Check log](test_pipeline.py.log) |
| Dashboard automated checks | Passed | [Check log](test_dashboard.py.log) |
| Dashboard on canonical data | Passed; all five views loaded on 100,000 newly prepared rows | [Dashboard evidence](dashboard_validation.json) |
| Fifteen Python investigations | Rerun against canonical preparation output, with aggregate tables and charts | [Fresh findings](findings/analyst_findings.md), [completed evidence](findings/analyst_evidence.csv) |

The canonical-data KPIs agree with the earlier findings: 100,000 distinct requests; 69,382 recorded closures; 30,618 requests without recorded closure; 69,263 valid durations; median 2.6408 hours; and 6.3555% of valid durations over 72 hours. This agreement does not establish SQL equivalence, which still requires executing notebook 04.

The canonical raw file was imported from `data/raw/nyc_311_100k.csv`. Its original download metadata remains unknown. `extraction_metadata.json` explicitly records `source_kind=local_raw_snapshot_import`, the source hash and import time. It does not invent an extraction time or claim an API success.

The successful outputs are also saved in the main notebooks under `notebooks/`. Package versions, timestamps, code hashes and artifact hashes are recorded in [the manifest](manifest.json) and [environment](environment.txt).

After configuring MySQL in the terminal that will launch the command, run:

```powershell
python scripts/06_execute_evidence.py --mysql --only-mysql
```

That creates separate dated database evidence while preserving this local-processing run.
