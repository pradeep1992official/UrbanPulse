
import requests
import pandas as pd
from pathlib import Path
import time

# NYC 311 API URL
url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"

# Settings
target_records = 100000
batch_size = 1000
all_records = []

session = requests.Session()

print("Starting NYC 311 data extraction...")

for offset in range(0, target_records, batch_size):

    params = {
        "$limit": batch_size,
        "$offset": offset,
        "$order": "created_date DESC, unique_key DESC"
    }

    try:
        response = session.get(
            url,
            params=params,
            timeout=60
        )

        response.raise_for_status()
        batch = response.json()

        if not batch:
            print("No more records available.")
            break

        all_records.extend(batch)

        print(f"Downloaded {len(all_records)} records")

        time.sleep(0.2)

    except requests.exceptions.RequestException as error:
        print(f"Error at offset {offset}: {error}")
        print("Extraction stopped. Retry this batch later.")
        break

# Convert data into a DataFrame
df = pd.DataFrame(all_records)

# Create folder
output_dir = Path("data/raw")
output_dir.mkdir(parents=True, exist_ok=True)

# Save downloaded data
df.to_csv(
    output_dir / "nyc_311_100k.csv",
    index=False
)

print("\nExtraction finished!")
print("Total records downloaded:", len(df))
print("Unique requests:", df["unique_key"].nunique()
      if "unique_key" in df.columns else "Unknown")
print("CSV file saved successfully!")
