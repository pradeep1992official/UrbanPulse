# Submission evidence

Fresh notebook outputs, canonical-data dashboard checks and regenerated investigations are available in the [dated execution summary](execution/20261106_153641/summary.md). It distinguishes the successful processing stages from the unsuccessful API attempt and pending MySQL stage.

Start with the [final findings report](final_findings_report.md) for the executive findings, five KPIs, demand and resolution comparisons, recommended next actions, limitations and reproduction instructions. It describes the identified earlier local snapshot; final canonical-data and MySQL reconciliation remain outstanding.

Read [the written findings for all 15 investigations](analyst_findings.md) or open [the completed evidence table](analyst_evidence.csv). Aggregate CSVs and charts are stored in `analysis/`; the source hash, coverage and calculation scope are recorded in [provenance](analysis_provenance.json).

These findings were calculated from the available earlier local extract (14–23 October 2026), not the later sample in the saved Colab/MySQL notebook. They use the dashboard's timestamp-derived duration and closure definitions. SQL reference files are included, but no new MySQL execution is claimed.

Reproduce or update this report with:

```powershell
python scripts/05_write_analyst_findings.py --source data/cleaned/nyc_311_cleaned.csv
```

Use `--source data/cleaned/nyc_cleaned.csv` when the canonical extract is available. This command overwrites generated findings, evidence, charts and provenance, so preserve manual edits separately. Review interpretations against any new extraction window before submission.

The final report is maintained separately from the evidence generator. If a new source is analysed, update the narrative after checking the regenerated tables and charts; running the generator does not refresh the final report automatically.

Original notebook 04 contains saved evidence of a successful prior MySQL load. The edited portable notebooks intentionally have cleared outputs because the code and preparation policy changed. They must be rerun before submission; original Downloads files remain unchanged.
