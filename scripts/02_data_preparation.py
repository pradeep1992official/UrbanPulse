"""Run the matching UrbanPulse notebook as a script from the repository root."""
from IPython.display import display

import pandas as pd
from pathlib import Path

from pathlib import Path
import os

project = Path(os.environ.get("URBANPULSE_ROOT", Path.cwd())).resolve()
if not (project / "data").is_dir() and (project.parent / "data").is_dir():
    project = project.parent
if not (project / "data").is_dir():
    raise FileNotFoundError("Run from the repository root or set URBANPULSE_ROOT.")

data_path = project / "data"
(data_path / "cleaned").mkdir(parents=True, exist_ok=True)

df = pd.read_csv(data_path / "raw" / "nyc_100k_raw.csv", low_memory=False, dtype={"unique_key": "string", "incident_zip": "string"})

# ── Helpers used several times below ──
log = []   # cleaning & validation log, saved at the end
def log_step(stage, item, value):
    log.append({"Stage": stage, "Item": item, "Value": value})
log_step("Cleaning", "Source (raw) rows loaded", len(df))

def invalid_coords(d):
    """True where a coordinate exists but is outside the valid lat/lon range."""
    return ((d["latitude"].notna()  & ~d["latitude"].between(-90, 90)) |
            (d["longitude"].notna() & ~d["longitude"].between(-180, 180)))



print("Shape:", df.shape)
print("\nColumns:", df.columns.tolist())
display(df.head())
print("\nMissing values:")
print(df.isnull().sum().sort_values(ascending=False))

if df["unique_key"].isna().any():
    raise ValueError("Missing request identifiers; inspect the raw snapshot.")
dup = df["unique_key"].duplicated()
print("Duplicate IDs:", dup.sum())

rejected = df[dup].assign(rejection_reason="Duplicate unique_key")
rejected.to_csv(data_path / "rejected_records.csv", index=False)
df = df[~dup].copy()
log_step("Cleaning", "Duplicate unique_key rows rejected (saved to rejected_records.csv)", int(dup.sum()))

# Dates → datetime, with a parse-error flag per column
date_cols = ["created_date", "closed_date", "due_date"]
for col in date_cols:
    parsed = pd.to_datetime(df[col], errors="coerce")
    df[f"{col}_parse_error"] = df[col].notna() & parsed.isna()
    df[col] = parsed

df["closure_before_creation"] = df["closed_date"] < df["created_date"]   # False if either is missing
df["invalid_date_flag"] = (df[[f"{c}_parse_error" for c in date_cols]].any(axis=1)
                           | df["closure_before_creation"])
log_step("Cleaning", "Date parse errors (flagged, set to NaT)",
         int(df[[f"{c}_parse_error" for c in date_cols]].sum().sum()))
log_step("Cleaning", "Closure earlier than creation (flagged, not corrected)",
         int(df["closure_before_creation"].sum()))

# Text → trimmed, single-spaced, upper-case
text_cols = ["agency", "complaint_type", "borough", "status", "agency_name",
             "descriptor", "location_type", "city"]
before = df[text_cols].astype("string")
for col in text_cols:
    df[col] = (df[col].astype("string").str.strip()
               .str.replace(r"\s+", " ", regex=True).str.upper())
log_step("Cleaning", "Text cells changed by normalisation", int((before != df[text_cols]).sum().sum()))

# Coordinates → numeric; keep originals for auditing
for col in ["latitude", "longitude"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")
    df[f"{col}_original"] = df[col]
df["invalid_coordinates_original"] = invalid_coords(df)

# ZIP → clean text
df["incident_zip"] = (df["incident_zip"].astype("string").str.strip()
                      .str.replace(r"\.0$", "", regex=True).replace("", pd.NA))

# Preserve meaningful nulls and source status; no geographic imputation.
# Retain compatibility flags so the verified 41-column MySQL contract still applies.
for flag in ["city_borough_imputed", "zipcode_city_imputed", "location_type_imputed",
             "latitude_imputed", "longitude_imputed", "status_updated"]:
    df[flag] = False
log_step("Cleaning", "Imputed values or overwritten statuses", 0)


# The NYC bounding box is approximate, not an official boundary.
df["invalid_coordinates"] = invalid_coords(df)
df["missing_coordinates"] = df["latitude"].isna() | df["longitude"].isna()
df["outside_nyc_bounds"] = (~df["missing_coordinates"]
    & ~(df["latitude"].between(40.4, 41.0) & df["longitude"].between(-74.3, -73.7)))
df["coordinate_quality_flag"] = (df["invalid_coordinates"] | df["outside_nyc_bounds"]
                                 | df["missing_coordinates"])

print("Invalid before filling :", df["invalid_coordinates_original"].sum())
print("Invalid after filling  :", df["invalid_coordinates"].sum())
print("Outside NYC bounds     :", df["outside_nyc_bounds"].sum())
print("Missing coordinates    :", df["missing_coordinates"].sum())
print("Any coordinate issue   :", df["coordinate_quality_flag"].sum())

# Resolution time — only for valid, chronological dates
valid = df["closed_date"].notna() & df["created_date"].notna() & ~df["closure_before_creation"]
df["resolution_hours"] = ((df["closed_date"] - df["created_date"]).dt.total_seconds() / 3600).where(valid)
df["long_resolution_flag"] = (df["resolution_hours"] > 365 * 24).fillna(False)   # > 365 days: review
df["is_closed"] = df["closed_date"].notna()

# Temporal features
created = df["created_date"].dt
df["created_year"], df["created_month"] = created.year, created.month
df["created_weekday"], df["created_hour"] = created.day_name(), created.hour

# field: (source, meaning, transformation, analytical use)
NYC, DER = "NYC 311", "Derived"
field_info = {
    # Source fields
    "unique_key":            (NYC, "Unique service request identifier", "Duplicate identifier check", "Complaint identification"),
    "created_date":          (NYC, "Complaint creation timestamp", "Convert to datetime", "Temporal analysis"),
    "closed_date":           (NYC, "Complaint closure timestamp", "Convert to datetime; preserve missing values", "Closure and resolution analysis"),
    "due_date":              (NYC, "Expected response deadline", "Convert to datetime", "Deadline analysis"),
    "agency":                (NYC, "Responsible agency code", "Normalize whitespace and case", "Agency comparison"),
    "complaint_type":        (NYC, "Complaint category", "Normalize whitespace and case", "Complaint trends"),
    "borough":               (NYC, "NYC borough", "Normalize whitespace and case", "Geographic analysis"),
    "status":                (NYC, "Current complaint status", "Normalize whitespace and case; preserve recorded status", "Status analysis"),
    "latitude":              (NYC, "Geographic latitude", "Numeric; validate range; preserve missing values", "Spatial analysis"),
    "longitude":             (NYC, "Geographic longitude", "Numeric; validate range; preserve missing values", "Spatial analysis"),
    "agency_name":           (NYC, "Responsible agency name", "Normalize whitespace and case", "Agency reporting"),
    "descriptor":            (NYC, "Detailed complaint category", "Normalize whitespace and case", "Complaint classification"),
    "location_type":         (NYC, "Incident location category", "Normalize; preserve missing values", "Location analysis"),
    "incident_zip":          (NYC, "Incident ZIP code", "Keep as text; preserve missing values", "ZIP-level analysis"),
    "city":                  (NYC, "Incident city", "Normalize; preserve missing values", "City-level analysis"),
    "resolution_description":(NYC, "Agency resolution details", "Preserve meaningful nulls", "Resolution assessment"),
    "latitude_original":     (NYC, "Latitude before quality checks", "Preserve numeric original", "Spatial data auditing"),
    "longitude_original":    (NYC, "Longitude before quality checks", "Preserve numeric original", "Spatial data auditing"),
    # Date flags
    "created_date_parse_error": (DER, "Invalid creation timestamp", "Flag failed parsing", "Date quality validation"),
    "closed_date_parse_error":  (DER, "Invalid closure timestamp", "Flag failed parsing", "Date quality validation"),
    "due_date_parse_error":     (DER, "Invalid deadline timestamp", "Flag failed parsing", "Date quality validation"),
    "closure_before_creation":  (DER, "Closure earlier than creation", "Compare closure and creation dates", "Chronological validation"),
    "invalid_date_flag":        (DER, "Any date problem", "Combine parse-error and chronology flags", "Data quality assessment"),
    # Coordinate flags
    "invalid_coordinates_original": (DER, "Invalid coordinates before quality checks", "Check lat/lon ranges", "Original spatial quality"),
    "invalid_coordinates":    (DER, "Invalid coordinates after numeric conversion", "Check lat/lon ranges", "Spatial data quality"),
    "outside_nyc_bounds":     (DER, "Outside approximate NYC bounds", "Check bounding box", "Geographic validation"),
    "missing_coordinates":    (DER, "Missing lat or lon after numeric conversion", "Check nulls", "Spatial completeness"),
    "coordinate_quality_flag":(DER, "Any coordinate problem", "Combine invalid, missing and outside-NYC flags", "Spatial analysis filtering"),
    # Imputation flags
    "city_borough_imputed":  (DER, "City filled from borough", "Flag imputation", "Geographic data quality"),
    "zipcode_city_imputed":  (DER, "ZIP filled from city", "Flag imputation", "Geographic data quality"),
    "latitude_imputed":      (DER, "Latitude filled from ZIP mean", "Flag imputation", "Spatial data quality"),
    "longitude_imputed":     (DER, "Longitude filled from ZIP mean", "Flag imputation", "Spatial data quality"),
    "location_type_imputed": (DER, "Location type filled from descriptor", "Flag imputation", "Data quality assessment"),
    "status_updated":        (DER, "Status changed during cleaning", "Flag status update", "Status quality assessment"),
    # Resolution and time features
    "resolution_hours":      (DER, "Resolution duration in hours", "Closed minus created (valid dates only)", "Resolution performance"),
    "long_resolution_flag":  (DER, "Duration over 365 days", "Flag for review", "Outlier assessment"),
    "is_closed":             (DER, "Closure recorded", "closed_date is present", "Closure analysis"),
    "created_year":          (DER, "Creation year", "Extract from created_date", "Yearly trends"),
    "created_month":         (DER, "Creation month", "Extract from created_date", "Monthly trends"),
    "created_weekday":       (DER, "Creation weekday", "Extract from created_date", "Weekly patterns"),
    "created_hour":          (DER, "Creation hour", "Extract from created_date", "Hourly trends"),
}

data_dictionary = pd.DataFrame([
    {"Field Name": c, "Source Name": field_info[c][0], "Meaning": field_info[c][1],
     "Data Type": str(df[c].dtype), "Missing Count": int(df[c].isna().sum()),
     "Missing Percentage": round(df[c].isna().mean() * 100, 2),
     "Transformation": field_info[c][2], "Analytical Use": field_info[c][3]}
    for c in df.columns if c in field_info
])
display(data_dictionary)
data_dictionary.to_csv(data_path / "data_dictionary.csv", index=False)
print("Undocumented columns:", set(df.columns) - set(field_info))

# Row reconciliation, identifier uniqueness, date ranges, numeric ranges
now = pd.Timestamp.now(tz="America/New_York").tz_localize(None)
source_rows = log[0]["Value"]
rejected_rows = len(rejected)

checks = {
    "Source (raw) rows": source_rows,
    "Rejected rows": rejected_rows,
    "Cleaned rows": len(df),
    "Rows reconcile (source - rejected = cleaned)": source_rows - rejected_rows == len(df),
    "unique_key is unique": df["unique_key"].is_unique,
    "unique_key missing": int(df["unique_key"].isna().sum()),
    "created_date range": f"{df['created_date'].min()}  →  {df['created_date'].max()}",
    "closed_date range": f"{df['closed_date'].min()}  →  {df['closed_date'].max()}",
    "created_date in the future": int((df["created_date"] > now).sum()),
    "closed_date in the future": int((df["closed_date"] > now).sum()),
    "due_date before created_date": int((df["due_date"] < df["created_date"]).sum()),
    "latitude range": f"{df['latitude'].min():.4f}  →  {df['latitude'].max():.4f}",
    "longitude range": f"{df['longitude'].min():.4f}  →  {df['longitude'].max():.4f}",
    "Coordinates with issues": int(df["coordinate_quality_flag"].sum()),
    "Valid resolution durations": int(df["resolution_hours"].notna().sum()),
    "resolution_hours range": f"{df['resolution_hours'].min():.2f}  →  {df['resolution_hours'].max():.2f}",
    "Negative durations (closure < creation)": int(df["closure_before_creation"].sum()),
    "Durations over 365 days (flagged)": int(df["long_resolution_flag"].sum()),
}
for item, value in checks.items():
    log_step("Validation", item, value)
    print(f"{item:<48}: {value}")

display(df[["created_date", "closed_date", "resolution_hours", "closure_before_creation",
            "long_resolution_flag", "created_year", "created_month",
            "created_weekday", "created_hour"]].head())

# Save cleaned data and the cleaning/validation log
df.to_csv(data_path / "cleaned" / "nyc_cleaned.csv", index=False)
cleaning_log = pd.DataFrame(log)
cleaning_log.to_csv(data_path / "cleaning_validation_log.csv", index=False)

display(cleaning_log)
print("Cleaned shape:", df.shape, "— saved. (Add the MySQL row count to this comparison after loading.)")
