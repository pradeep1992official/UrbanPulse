"""Run the matching UrbanPulse notebook as a script from the repository root."""
from IPython.display import display

import json, time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ── Settings ──
from pathlib import Path
import os

project = Path(os.environ.get("URBANPULSE_ROOT", Path.cwd())).resolve()
if not (project / "data").is_dir() and (project.parent / "data").is_dir():
    project = project.parent
if not (project / "data").is_dir():
    raise FileNotFoundError("Run from the repository root or set URBANPULSE_ROOT.")

base_path = project / "data"
raw_path = base_path / "raw"
raw_path.mkdir(parents=True, exist_ok=True)

url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
target_records = int(os.environ.get("URBANPULSE_TARGET", "100000"))
batch_size = 1000
if target_records <= 0:
    raise ValueError("URBANPULSE_TARGET must be positive")
fields = ["unique_key", "created_date", "closed_date", "due_date", "agency",
          "complaint_type", "borough", "status", "latitude", "longitude",
          "agency_name", "descriptor", "location_type", "incident_zip",
          "city", "resolution_description"]
order_by = "created_date DESC, unique_key DESC"
ist = ZoneInfo("Asia/Kolkata")

retry = Retry(total=5, backoff_factor=1, allowed_methods=["GET"],
              status_forcelist=[429, 500, 502, 503, 504])
records, errors, status = [], [], "completed"
start = datetime.now(ist)

with requests.Session() as session:
    session.mount("https://", HTTPAdapter(max_retries=retry))
    for offset in range(0, target_records, batch_size):
        limit = min(batch_size, target_records - offset)
        params = {"$select": ",".join(fields), "$limit": limit,
                  "$offset": offset, "$order": order_by}
        try:
            r = session.get(url, params=params, timeout=(15, 60))
            r.raise_for_status()
            batch = r.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            errors.append(str(e)); status = "partial_failed"; break

        if not isinstance(batch, list) or not all(isinstance(row, dict) for row in batch):
            errors.append("Unexpected API response shape"); status = "partial_failed"; break
        records.extend(batch)
        print(f"Extracted {len(records)} records so far...")
        if len(batch) < limit:          # empty or short page = no more data
            status = "source_exhausted"; break
        time.sleep(0.2)

if not records:
    raise RuntimeError("No records downloaded; existing snapshot was preserved.")
df = pd.DataFrame(records, columns=fields)
raw_file = raw_path / "nyc_100k_raw.csv"
df.to_csv(raw_file, index=False, encoding="utf-8")

metadata = {
    "dataset": "NYC 311 Service Requests",
    "api_url": url,
    "extraction_start_ist": start.isoformat(),
    "extraction_end_ist": datetime.now(ist).isoformat(),
    "timezone": "Asia/Kolkata (UTC+05:30)",
    "target_records": target_records,
    "actual_records": len(df),
    "unique_requests": int(df["unique_key"].nunique()),
    "duplicate_records": int(df["unique_key"].duplicated().sum()),
    "data_coverage_start": df["created_date"].min() if not df.empty else None,
    "data_coverage_end": df["created_date"].max() if not df.empty else None,
    "batch_size": batch_size,
    "selected_fields": fields,
    "ordering": order_by,
    "status": status,
    "api_limitations": [
        "API rate limits may apply",
        "Source data can change during extraction",
        "Offset pagination may cause duplicates or omissions",
        "Only selected fields were extracted",
    ],
    "errors": errors,
}
metadata_file = base_path / "extraction_metadata.json"
metadata_file.write_text(json.dumps(metadata, indent=4), encoding="utf-8")

# Summary (reuses the metadata dict — nothing is recomputed)
skip = {"selected_fields", "api_limitations", "api_url", "ordering"}
print("========== EXTRACTION SUMMARY ==========")
for k, v in metadata.items():
    if k not in skip:
        print(f"{k}: {v}")
print(f"raw_csv: {raw_file}\nmetadata_json: {metadata_file}")
display(df.head())
if status == "partial_failed":
    raise RuntimeError("Partial extraction saved with failure metadata; inspect before continuing.")

