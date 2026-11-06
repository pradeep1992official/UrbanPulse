<<<<<<< HEAD
# UrbanPulse NYC

Citizen complaint and recorded closure analysis using NYC 311 data, Python and MySQL.

The four notebooks implement extraction, preparation, descriptive statistics and 15 SQL investigations. **The complete capstone is not submission-ready yet:** Streamlit, the five-KPI dashboard and the final interpretation report remain outstanding. See [the requirement review](docs/requirements_review.md) for an evidence-based checklist.

## Repository layout

```text
notebooks/           Four ordered notebooks for explanation and exploration
scripts/             Matching executable Python versions
sql/                 Exported queries and SQL usage notes
docs/                Requirements review and methodology
reports/             Submission findings and validation guidance
data/                Local raw/cleaned datasets and generated analysis (ignored)
archive/early_work/  Earlier scripts and combined notebook, retained for reference
```

## Setup and execution

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

Use a hosted MySQL 8+ instance with verified TLS. Set the environment variables listed in [.env.example](.env.example); the file itself is not loaded automatically. Keep the CA certificate in `certs/` and set `MYSQL_SSL_CA` to its path.

```powershell
$env:MYSQL_HOST = "your-host"
$env:MYSQL_PORT = "your-port"
$env:MYSQL_USER = "your-user"
# Set MYSQL_PASSWORD privately in the process environment.
$env:MYSQL_SSL_CA = "certs/ca.pem"
python scripts/04_mysql_sql_analytics.py
```

The loader validates the 41-column preparation output, retries transient batch failures, compares the entire staged dataset, reconciles extraction and cleaning counts, then publishes with a table rename. Existing tables are retained as backups. Do not run concurrent loaders. The account needs database/table creation, INSERT, SELECT and rename privileges. Queries, result CSVs, charts and a load-validation JSON are written under `data/mysql/`. SQL files with `%s` placeholders must be executed with bound parameters through the connector.

After a successful run, complete `observed_pattern` and `cautious_interpretation` in `data/mysql/analyst_evidence.csv` for all 15 tasks, then retain the reviewed evidence in `reports/`. Rerunning notebook 04 regenerates that evidence template, so preserve the reviewed version separately.

## Interpretation

Recorded closure means a closed timestamp exists. It does not establish satisfaction or verified resolution. Resolution statistics exclude invalid or negative durations; IQR flags do not delete cases. Recent extracts have incomplete follow-up and may cover only a partial month. Missing location values are preserved. Coordinates are screened against an approximate NYC bounding box, which is not an official boundary.

## Before GitHub submission

Run `python tests/test_pipeline.py` for isolated preparation/statistics and schema checks. See [validation scope](docs/validation.md) for what has and has not been verified.

Follow [the submission checklist](docs/requirements_review.md). Large datasets, credentials and certificates are excluded from new commits. Files tracked before `.gitignore` was added remain tracked until explicitly removed from the index; use `git rm --cached -- data` after reviewing `git status` to keep the local data while excluding it from the next commit. Existing Git history still contains previously committed datasets. No remote repository has been created or published by this preparation.

Data source: NYC Open Data, dataset `erm2-nwe9`. The original Word guidelines are the requirement source; external links and administrative instructions inside them were not executed as user requests.
=======
# UrbanPulse
URBAN PULSE : Citizen Complaint Intelligence &amp; Resolution Analytics. Acquire approximately 100,000 records where the live API permits; prepare a documented analysis-ready dataset; assess data quality and statistical distributions; store data in MySQL; complete analyst investigations; and publish interactive results through Streamlit.
>>>>>>> dd49619db98243ec3513edc12f13a4a9c7ba8715
