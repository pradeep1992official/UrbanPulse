# UrbanPulse NYC

Analyze 100,000 NYC 311 service requests using Python, MySQL and Streamlit. Explore complaint categories, agency workloads, geographic patterns and recorded closure times through 15 investigations and an interactive dashboard.

## Quick start

Install Python 3.11 or newer. Download and extract this repository, then open a terminal in the folder containing this README.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Open the URL shown in the terminal, usually http://localhost:8501. Choose **Cleaned CSV** to explore the included data without MySQL.

## Included data

All paths are relative to the project folder:

- Raw data: `data/raw/nyc_100k_raw.csv`
- Cleaned data: `data/cleaned/nyc_cleaned.csv`
- Field definitions: `data/data_dictionary.csv`

The snapshot covers 14-23 October 2026. Original API download metadata is unavailable; `data/extraction_metadata.json` records its local import. The dictionary and validation log are included in `data/`. From inside `notebooks/`, data paths begin with `../data/`.

## Run the analysis

```powershell
python scripts/02_data_preparation.py
python scripts/03_statistics.py
python scripts/05_write_analyst_findings.py
```

You can also run the numbered notebooks in `notebooks/`. Notebook 01 downloads replacement data from the live API and is optional when using the included snapshot.

## MySQL setup (optional)

Use a hosted MySQL 8+ service. Copy `.env.example` to `.env`, enter your connection settings, and save the service CA certificate as `certs/ca.pem`.

```powershell
python scripts/04_mysql_sql_analytics.py
```

This loads the data, validates it and runs all 15 SQL investigations. It refreshes the published table and keeps the previous table as a backup. Afterward, choose **MySQL** in the dashboard. Keep `.env` and certificates out of Git.

## Project folders

| Folder | Contents |
|---|---|
| `data/` | CSV snapshots, dictionary and validation log |
| `notebooks/` | Four analysis notebooks |
| `scripts/` | Extraction, processing, SQL and findings scripts |
| `dashboard/` | Dashboard data access and calculations |
| `sql/` | Fifteen SQL investigations |
| `reports/` | Findings, charts and execution evidence |
| `tests/` | Pipeline and dashboard checks |

## Findings and checks

- [Final findings report](reports/final_findings_report.md)
- [All 15 investigations](reports/analyst_findings.md)
- [Successful MySQL execution and SQL/Python comparison](reports/execution/20261106_163637/summary.md)

```powershell
python tests/test_pipeline.py
python tests/test_dashboard.py
```

Recorded closure does not prove citizen satisfaction. The dashboard's 72-hour threshold is a project choice, not an official SLA. The short snapshot does not establish seasonal trends.

Data source: NYC Open Data, dataset `erm2-nwe9`.
