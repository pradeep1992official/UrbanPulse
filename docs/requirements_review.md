# Review against the supplied Word guidelines

Reviewed 6 November 2026. Source: `URBANPULSE_NYC..docx` and the four explicitly supplied `simplified_0*.ipynb` files. Saved outputs establish prior runs, not a new independent execution. The unrelated duplicate filenames in Downloads were not substituted for the supplied files.

## Overall verdict

The four notebooks provide a strong implementation of the first four stages, but **neither all four notebooks nor the entire project are complete for submission**. Notebook 04 contains saved successful MySQL-load evidence, whereas notebooks 01 and 03 contain no execution counts or outputs. The required interpretation fields for the 15 investigations are generated blank. The Word document also requires Streamlit and final reporting beyond these four notebooks.

| Guideline | Supplied evidence | Status / remaining work |
|---|---|---|
| API pagination, selected fields, retries, metadata, raw separation | Notebook 01 implements these with 16 selected fields | Code present; no saved execution evidence. The approximate 25-field guideline permits the final selected list to be authoritative; justify the 16-field selection. |
| Approximately 100,000 rows | Notebook 02 and 04 saved outputs show 100,000 rows | Supported by saved outputs; retain genuine extraction metadata and raw snapshot. |
| Load inspection and missingness | Notebook 02 prints dimensions, columns, sample and missing counts | Present. |
| Duplicate IDs and rejected rows | Notebook 02 writes rejected duplicates; saved output reports zero | Present; missing IDs need explicit failure handling (added in repository version). |
| Date parsing and invalid chronology | Parse flags, negative chronology flags, valid-duration derivation | Present; saved output reports 91 negative chronology records. |
| Preserve meaningful nulls | City/ZIP/location modes and ZIP-mean coordinates were used | Needs correction: imputation can fabricate geography. Repository version preserves nulls and retains compatibility flags as false. |
| Recorded status distribution | Original notebook overwrites status where a closed date exists | Needs correction: keep normalized source status; derive closure separately. Fixed in repository version. |
| Data dictionary and cleaning log | Notebook 02 creates both | Implemented; generated artifacts from the original Colab run were not supplied as files. |
| Mean, median, mode, spread, skewness | Notebook 03 calculates requested metrics | Implemented; no saved execution evidence in supplied notebook. |
| IQR histogram and boxplot | Notebook 03 flags and retains outliers | Implemented; execute and review saved charts. |
| MySQL staging, retries, validation and publication | Notebook 04 saved report shows 100,000 published and full roundtrip passed | Supported by original saved output; rerun after cleaning changes, retain new JSON report. |
| Fifteen SQL investigations | All 15 questions and calculations in notebook 04 | Implemented with saved result/chart outputs; interpretation remains incomplete. |
| Question, query, n, chart, observed pattern, cautious interpretation per task | Evidence CSV generated with blank final two columns | Incomplete: review results and fill all 15 rows. |
| Navigable Streamlit analyst pages and filters | No application supplied | Missing. |
| Five KPIs and filtered preview | No application supplied | Missing. |
| Empty-state / connection-error handling | No application supplied | Missing. |
| Final findings and limitations | Scattered caveats; no final report supplied | Incomplete. |
| GitHub code organization and reproducibility | Hard-coded personal Colab paths, no dependency file | Repository now has portable notebooks/scripts, README, requirements and ignore rules. |

## Important technical findings

1. The original preparation output filled 5,719 cities, 873 ZIPs, 1,198 location types and 1,578 coordinate pairs, and replaced 2,350 statuses. Although flagged, these changes can bias status and geographic investigations. The repository keeps missing values and normalized recorded statuses instead. Existing database results will therefore need regeneration.
2. The original saved sample spans 19–28 October 2026 (about nine days). A monthly chart for this extract cannot establish monthly seasonality. Recent requests have incomplete closure follow-up.
3. Original notebook 04 contains successful prior execution: 100,000 source, cleaned, staged and published rows; `published=True`, `full_roundtrip_passed=True`. This is real saved notebook evidence, but not an independently verified current database state.
4. Original notebook 03 has a fixed right-tail conclusion before execution. The repository version asks the reader to inspect the actual distribution and keeps the calculated skewness interpretation.
5. The original extraction warns correctly that changing-source offset pagination can omit or duplicate records. Retain that limitation; it is not a stable historical census.
6. The original repository's older raw/cleaned CSV filenames and schema differ from the supplied notebooks. Do not mix them into notebook 04 or fabricate provenance to satisfy reconciliation.

## Submission checklist

- [ ] Run the portable extraction notebook and preserve its actual metadata (or use the matching genuine original snapshot and metadata).
- [ ] Run preparation and statistics; review dictionary, validation log, invalid records, distribution and outlier outputs.
- [ ] Rerun MySQL load and all queries against the new preparation policy; retain the successful load JSON.
- [ ] Fill observed pattern and cautious interpretation for all 15 investigations with denominators and reviewed visualizations.
- [ ] Build Streamlit date, borough and complaint filters, analyst navigation, preview, empty states and connection-error handling.
- [ ] Add the five KPIs: distinct requests; recorded-closure share; rows without recorded closure; median valid resolution hours; share of valid durations over 72 hours.
- [ ] Explain that 72 hours is an illustrative threshold, not a verified official SLA.
- [ ] Write a final findings report using actual outputs, coverage dates, sample sizes and limitations.
- [ ] Review Git tracking, credentials, large files and the final repository diff before committing and publishing.

This review does not claim a grade or treat the Word document's proposed weights as an official program rubric.
