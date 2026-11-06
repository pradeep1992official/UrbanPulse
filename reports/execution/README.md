# Fresh execution evidence

Each dated folder contains the environment versions, executed notebook copies, a manifest with timestamps and SHA-256 hashes, and automated-check logs. Successful runs also update the corresponding notebooks in `notebooks/` with their actual execution counts and outputs. Failed executed copies are retained in the dated folder without replacing the main notebook.

Read the [latest processing summary](20261106_153641/summary.md). Its raw input was explicitly imported from an existing snapshot after the live API attempt stalled. To repeat this mode, use `python scripts/06_execute_evidence.py --local-source data/raw/nyc_311_100k.csv`; the import record is labelled as an import, and notebook 01 is marked unexecuted for that run.

The manifest distinguishes passed, failed and unexecuted stages. A notebook's saved historical outputs alone do not establish that the current code or current database was rerun.

```powershell
python scripts/06_execute_evidence.py
```

This executes live extraction (100,000-row target), preparation, statistics and the automated tests. The API may exhaust available results or fail; inspect actual counts and status in the metadata and manifest.

To execute the database notebook against the canonical prepared snapshot, configure the MySQL environment variables and CA certificate, then run:

```powershell
python scripts/06_execute_evidence.py --mysql --only-mysql
```

Notebook 04 writes to its configured MySQL database: it creates a staging table, loads and validates data, and publishes it while retaining an old-table backup. Use the project's intended service and avoid concurrent loaders. Do not include credentials in logs or Git. The process running the command must inherit the configured environment variables; values set in a different terminal are not automatically inherited by an already-running process.

For a complete run with MySQL enabled, use `python scripts/06_execute_evidence.py --mysql`. Keep record-level raw and cleaned data locally under ignored `data/`; their hashes in the manifest identify the files used. Dictionary, extraction metadata and cleaning log copies provide small, reviewable provenance artifacts.
