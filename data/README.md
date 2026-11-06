# Included data

The repository includes the processing snapshot as CSV files. Paths are relative to the repository root and work after cloning or downloading and extracting the repository.

| Relative path | Purpose |
|---|---|
| `data/raw/nyc_100k_raw.csv` | 100,000 raw records with the 16 selected source fields |
| `data/cleaned/nyc_cleaned.csv` | 100,000 prepared records with 41 final columns |
| `data/extraction_metadata.json` | Local-import provenance; original API download metadata is unavailable |
| `data/data_dictionary.csv` | Field meanings, types, missingness and transformations |
| `data/cleaning_validation_log.csv` | Cleaning steps and validation |
| `data/rejected_records.csv` | Rejected duplicates; currently header-only because no duplicates were rejected |

No Excel workbook is required. To process the included snapshot, run from the repository root:

```powershell
python scripts/02_data_preparation.py
python scripts/03_statistics.py
python scripts/05_write_analyst_findings.py
python -m streamlit run streamlit_app.py
```

In a notebook launched from the repository root:

```python
from pathlib import Path
import pandas as pd

data_dir = Path('data')
raw = pd.read_csv(data_dir / 'raw' / 'nyc_100k_raw.csv', dtype={'unique_key': 'string', 'incident_zip': 'string'})
cleaned = pd.read_csv(data_dir / 'cleaned' / 'nyc_cleaned.csv', dtype={'unique_key': 'string', 'incident_zip': 'string'})
```

For a notebook launched inside `notebooks/`, use `Path('../data')`. The supplied notebooks detect both launch locations automatically. The app resolves its relative source path against the repository root.

Notebook 01 is optional for the bundled snapshot: running it downloads a replacement from the live API. The bundled files derive from the preserved October snapshot, not a verified fresh download. Older duplicate extracts and regenerated statistics remain ignored.
