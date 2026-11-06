# UrbanPulse NYC

Citizen complaint and recorded closure analysis using NYC 311 data, Python and MySQL.

The four notebooks implement extraction, preparation, descriptive statistics and 15 SQL investigations. The Streamlit application adds interactive analyst views and the five-KPI dashboard. Read the [final findings report](reports/final_findings_report.md) for the results and recommendations, supported by [evidence for all 15 investigations](reports/analyst_findings.md) from the earlier local extract. **Current MySQL execution and all 15 SQL/Python comparisons have passed; original API extraction provenance remains incomplete.** See [the requirement review](docs/requirements_review.md) for an evidence-based checklist.

## Repository layout

```text
notebooks/           Four ordered notebooks for explanation and exploration
streamlit_app.py     Interactive dashboard entry point
dashboard/           Read-only data access, filters and KPI calculations
scripts/             Matching executable Python versions
sql/                 Exported queries and SQL usage notes
docs/                Requirements review and methodology
reports/             Submission findings and validation guidance
data/                Included raw/cleaned CSV snapshots, dictionary and provenance
```

## Setup and execution

The CSV snapshot is included at `data/raw/nyc_100k_raw.csv` and `data/cleaned/nyc_cleaned.csv`. After downloading and extracting the repository, processing can start at notebook 02 without an API call. See [data paths and usage](data/README.md). Notebook 01 optionally refreshes the source using the live API.

Use Python 3.11 or newer. Run commands from the repository root.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/01_data_retrieval.py
python scripts/02_data_preparation.py
python scripts/03_statistics.py
```

Alternatively, select this virtual environment as the notebook kernel and run notebooks in numeric order. The notebooks support launching from either the root or `notebooks/`; for other launch locations set `URBANPULSE_ROOT` to the repository path. Colab users can mount Drive separately and set that variable to a copy of this repository.

Notebook and script versions contain the same calculations. Keep both updated when making changes. Scripts display tables in the terminal; notebooks provide the richer presentation.

The extraction writes `data/raw/nyc_100k_raw.csv` and `data/extraction_metadata.json`. Preparation writes `data/cleaned/nyc_cleaned.csv`, a field-level dictionary, rejected duplicates and a cleaning/validation log. Statistics writes tables and a distribution chart under `data/statistics/`. API extraction uses a changing source; actual rows and coverage must be reported for each run. A failed partial extraction raises an error after writing its failure metadata; inspect it before continuing.

## MySQL

Use a hosted MySQL 8+ instance with verified TLS. Set the environment variables listed in [.env.example](.env.example), or copy the placeholders into an ignored `.env` file and enter your settings there. Notebook 04, the execution runner and dashboard load the repository's `.env` without overriding existing environment variables. Keep the CA certificate in `certs/` and set `MYSQL_SSL_CA` to its relative path. The template `.env.example` is never loaded as credentials.

```powershell
$env:MYSQL_HOST = "your-host"
$env:MYSQL_PORT = "your-port"
$env:MYSQL_USER = "your-user"
# Set MYSQL_PASSWORD privately in the process environment.
$env:MYSQL_SSL_CA = "certs/ca.pem"
python scripts/04_mysql_sql_analytics.py
```

The loader validates the 41-column preparation output, retries transient batch failures, compares the entire staged dataset, reconciles extraction and cleaning counts, then publishes with a table rename. Existing tables are retained as backups. Do not run concurrent loaders. The account needs database/table creation, INSERT, SELECT and rename privileges. Queries, result CSVs, charts and a load-validation JSON are written under `data/mysql/`. SQL files with `%s` placeholders must be executed with bound parameters through the connector.

After a successful run, complete `observed_pattern` and `cautious_interpretation` in `data/mysql/analyst_evidence.csv` for all 15 tasks, then retain the reviewed evidence in `reports/`. The current [completed evidence](reports/analyst_evidence.csv) describes the earlier local extract; do not transplant those numbers into a different MySQL snapshot. Rerunning notebook 04 regenerates its evidence template, so preserve reviewed versions separately. Reproduce the local written findings with `python scripts/05_write_analyst_findings.py`; see [reports](reports/README.md) for source selection.

## Streamlit dashboard

```powershell
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Open the local URL printed in the terminal (normally `http://localhost:8501`). The default source is `data/cleaned/nyc_cleaned.csv`. If only the earlier `nyc_311_cleaned.csv` exists, the app opens it with a provenance warning. Change the CSV path in the sidebar or set `URBANPULSE_DATA` before launch. Missing files show preparation instructions instead of an exception.

Select MySQL to read `urban_pulse_db.service_requests` using the same environment settings as notebook 04. This app accepts a CA file path in `MYSQL_SSL_CA`; it requires verified TLS and only reads the published table. It does not create or load a database. Data is cached for 60 seconds for MySQL and five minutes for CSV (file modification time also invalidates the CSV cache); **Refresh data** clears the cache.

The sidebar provides five views: Overview; Demand & workload; Resolution & outliers; Geography & closure; Records & quality. Creation-date, borough and complaint filters apply to every chart, table, KPI and export. Date endpoints are inclusive. Missing creation dates remain included until a date filter is enabled; clearing a category selection yields an empty result.

The five KPIs are distinct requests, recorded-closure percentage, requests without a recorded closure, median valid resolution hours, and the percentage of valid durations strictly exceeding 72 hours. Durations and closure are recalculated from timestamps; invalid/negative durations are excluded from duration denominators. Missing-duration KPIs display N/A. The geographic view excludes imputed coordinates when flags exist. Records can be previewed (500 rows) and downloaded (all filtered rows, selected columns).

Run `python tests/test_dashboard.py` to check KPI arithmetic, filters, all investigation views, missing data, and connection configuration errors without live services. Full MySQL integration still needs a configured service.

## Interpretation

Recorded closure means a closed timestamp exists. It does not establish satisfaction or verified resolution. Resolution statistics exclude invalid or negative durations; IQR flags do not delete cases. Recent extracts have incomplete follow-up and may cover only a partial month. Missing location values are preserved. Coordinates are screened against an approximate NYC bounding box, which is not an official boundary.

## Before GitHub submission

Run `python tests/test_pipeline.py` for isolated preparation/statistics and schema checks. See [validation scope](docs/validation.md) for what has and has not been verified.

Run `python scripts/06_execute_evidence.py` for fresh execution of notebooks 01–03 with saved outputs and dated evidence. Once MySQL is configured, `python scripts/06_execute_evidence.py --mysql --only-mysql` records notebook 04 separately. See [execution evidence](reports/execution/README.md) for run artifacts and scope.

The [latest recorded processing run](reports/execution/20261106_153641/summary.md) passed preparation, statistics, dashboard checks and the Python investigations using the preserved raw snapshot. The live API attempt stalled; the [subsequent MySQL execution](reports/execution/20261106_163637/summary.md) passed the 100,000-row load and all 15 SQL/Python comparisons. To rerun processing on the bundled canonical snapshot, use `python scripts/06_execute_evidence.py --skip-extraction`.

Follow [the submission checklist](docs/requirements_review.md). The canonical raw/cleaned CSVs, dictionary, import metadata and validation log are included for offline processing. Older duplicate datasets, regenerated statistics, credentials and certificates remain excluded from new commits.

Data source: NYC Open Data, dataset `erm2-nwe9`. The original Word guidelines are the requirement source; external links and administrative instructions inside them were not executed as user requests.

Verify newly exported SQL results with `python scripts/07_verify_sql_results.py --output reports/sql_python_comparison.json`. The successful recorded MySQL run is documented in [the dated summary](reports/execution/20261106_163637/summary.md).
