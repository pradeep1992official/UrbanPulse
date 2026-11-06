
import pandas as pd
from pathlib import Path

# STEP 1: Load raw data
df = pd.read_csv("data/raw/nyc_311_100k.csv")

print("Original shape:", df.shape)

# STEP 2: Check missing values
print("\nMissing values:")
print(df.isnull().sum().sort_values(ascending=False))

# STEP 3: Check duplicate complaint IDs
if "unique_key" in df.columns:
    print("\nDuplicate IDs:", df["unique_key"].duplicated().sum())
    df = df.drop_duplicates(subset=["unique_key"])

# STEP 4: Convert dates to datetime
date_columns = ["created_date", "closed_date", "due_date"]

for col in date_columns:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")

# STEP 5: Clean text fields
text_columns = ["agency", "complaint_type", "borough", "status"]

for col in text_columns:
    if col in df.columns:
        df[col] = df[col].astype("string").str.strip()

# STEP 6: Convert geographic columns
for col in ["latitude", "longitude"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# STEP 7: Calculate resolution duration
if {"created_date", "closed_date"}.issubset(df.columns):
    df["resolution_hours"] = (
        df["closed_date"] - df["created_date"]
    ).dt.total_seconds() / 3600

    # Flag invalid negative durations
    df.loc[df["resolution_hours"] < 0, "resolution_hours"] = float("nan")

    df["is_closed"] = df["closed_date"].notna()
else:
    df["resolution_hours"] = float("nan")
    df["is_closed"] = False

# STEP 8: Create time-related features
if "created_date" in df.columns:
    df["created_year"] = df["created_date"].dt.year
    df["created_month"] = df["created_date"].dt.month
    df["created_weekday"] = df["created_date"].dt.day_name()
    df["created_hour"] = df["created_date"].dt.hour

# STEP 9: Save cleaned data
Path("data/cleaned").mkdir(parents=True, exist_ok=True)

df.to_csv("data/cleaned/nyc_311_cleaned.csv", index=False)

print("\nCleaned shape:", df.shape)
print("Cleaning completed successfully!")
