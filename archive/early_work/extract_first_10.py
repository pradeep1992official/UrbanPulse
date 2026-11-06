import pandas as pd
import requests
from pathlib import Path

url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
params = {
    "$limit": 1000,
    "$order": "created_date DESC"
}

response = requests.get(url, params=params, timeout=30)

records = response.json()

df = pd.DataFrame(records)

print("\nAPI request successful!")
print("Records downloaded:", len(df))
print("Number of columns:", len(df.columns))
print(df.head())

output_dir = Path("data/raw")
output_dir.mkdir(parents=True, exist_ok=True)

df.to_json(
  output_dir / "nyc_311_1000.json",
  orient="records",
  indent=2
)

df.to_csv(
  output_dir / "nyc_311_1000.csv",
  index=False
)

print("\nFiles saved successfully!")