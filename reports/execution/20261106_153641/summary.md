# Preparation and statistics run

6 November 2026. Source: the preserved 100,000-row raw snapshot, covering 14-23 October 2026.

| Stage | Result | Evidence |
|---|---|---|
| Raw import | 100,000 rows, 16 selected fields | [Metadata](extraction_metadata.json) |
| Notebook 02 | Passed, all 10 code cells | [Notebook](../../../notebooks/02_data_preparation.ipynb) |
| Notebook 03 | Passed, all 7 code cells | [Notebook](../../../notebooks/03_statistics.ipynb) |
| Pipeline checks | Passed | [Result](manifest.json) |
| Dashboard checks | Passed | [Result](manifest.json) |
| CSV dashboard | All five views passed | [Result](dashboard_validation.json) |
| Fifteen Python investigations | Completed | [Findings](../../analyst_findings.md) |

The cleaned output has 100,000 unique requests, 69,382 recorded closures and 69,263 valid durations. The median duration is 2.64 hours.

See the [dictionary](data_dictionary.csv), [cleaning log](cleaning_validation_log.csv), [manifest](manifest.json) and [package versions](environment.txt).

The live API attempt stalled; original download metadata remains unknown. MySQL was not part of this run and [passed in the later run](../20261106_163637/summary.md).
