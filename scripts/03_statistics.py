"""Run the matching UrbanPulse notebook as a script from the repository root."""
from IPython.display import display

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

plt.style.use("seaborn-v0_8-whitegrid")
from pathlib import Path
import os

project = Path(os.environ.get("URBANPULSE_ROOT", Path.cwd())).resolve()
if not (project / "data").is_dir() and (project.parent / "data").is_dir():
    project = project.parent
if not (project / "data").is_dir():
    raise FileNotFoundError("Run from the repository root or set URBANPULSE_ROOT.")


data_path = project / "data"
stats_path = data_path / "statistics"
stats_path.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(data_path / "cleaned" / "nyc_cleaned.csv", low_memory=False)
print("Rows:", df.shape[0], "| Columns:", df.shape[1])

# Valid durations only: numeric, finite and non-negative
df["resolution_hours"] = pd.to_numeric(df["resolution_hours"], errors="coerce")
valid_resolution = df.loc[np.isfinite(df["resolution_hours"]) & (df["resolution_hours"] >= 0),
                          "resolution_hours"]
if valid_resolution.empty:
    raise ValueError("No valid resolution records available.")

def describe_numeric(s, with_mode=False):
    s = pd.to_numeric(s, errors="coerce")
    s = s[np.isfinite(s)]
    q1, med, q3 = s.quantile([0.25, 0.50, 0.75])
    out = {"Count": len(s), "Mean": s.mean(), "Median": med}
    if with_mode:
        out["Mode"] = s.mode().iloc[0] if not s.mode().empty else np.nan
    out.update({"Minimum": s.min(), "Maximum": s.max(), "Range": s.max() - s.min(),
                "Q1": q1, "Q3": q3, "IQR": q3 - q1,
                "Variance (sample)": s.var(ddof=1), "Std deviation (sample)": s.std(ddof=1),
                "Skewness": s.skew()})
    return out

v = valid_resolution
res = describe_numeric(v, with_mode=True)
mean, median, q1, q3, iqr, skewness = (res[k] for k in ["Mean", "Median", "Q1", "Q3", "IQR", "Skewness"])

numeric_summary = pd.DataFrame({
    "resolution_hours": res,
    "latitude": describe_numeric(df["latitude"]),
    "longitude": describe_numeric(df["longitude"]),
})
display(numeric_summary.round(2))

if pd.isna(skewness):
    print("Skewness cannot be determined.")
elif skewness > 1:
    print(f"Highly right-skewed (mean {mean:.2f} h > median {median:.2f} h): long cases pull the mean up; report the median alongside it.")
elif skewness < -1:
    print(f"Highly left-skewed (mean {mean:.2f} h, median {median:.2f} h): report the median alongside the mean.")
else:
    print(f"Not highly skewed (±1 threshold; mean {mean:.2f} h, median {median:.2f} h): both are useful.")

def mode_summary(columns):
    rows = []
    for col in columns:
        if col not in df.columns:
            continue
        s = df[col].dropna()
        s = s[s.astype(str).str.strip() != ""]
        if s.empty:
            continue
        counts = s.value_counts()
        rows.append({"Field": col, "Most Frequent Value": counts.index[0],
                     "Frequency": counts.iloc[0],
                     "Percentage": round(counts.iloc[0] / len(s) * 100, 2)})
    return pd.DataFrame(rows)

categorical_summary = mode_summary(["agency", "agency_name", "complaint_type", "descriptor",
                                    "borough", "status", "location_type", "city", "incident_zip"])
temporal_summary = mode_summary(["created_year", "created_month", "created_weekday", "created_hour"])
display(categorical_summary)
display(temporal_summary)

df.loc[~np.isfinite(df["resolution_hours"]) | (df["resolution_hours"] < 0), "resolution_hours"] = np.nan

def group_stats(col, sort_by):
    return (df.groupby(col)["resolution_hours"].agg(Count="count", Mean="mean", Median="median")
              .round(2).sort_values(sort_by, ascending=False))

borough_stats   = group_stats("borough", "Median")
agency_stats    = group_stats("agency", "Median")
complaint_stats = group_stats("complaint_type", "Count")

display(borough_stats)
display(agency_stats)
display(complaint_stats.head(20))

lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
outlier_mask = (v < lower) | (v > upper)
n_out = int(outlier_mask.sum())

outlier_summary = pd.DataFrame({
    "Measure": ["Q1 (hours)", "Q3 (hours)", "IQR (hours)", "Lower fence (hours)",
                "Upper fence (hours)", "Flagged outlier count", "Flagged outlier percentage (%)"],
    "Value": [q1, q3, iqr, lower, upper, n_out, 100 * n_out / len(v)],
})
display(outlier_summary.round(2))

# Flag in the DataFrame (all records kept)
df["resolution_outlier_iqr"] = pd.Series(pd.NA, index=df.index, dtype="boolean")
df.loc[v.index, "resolution_outlier_iqr"] = outlier_mask

preview_cols = [c for c in ["unique_key", "agency", "complaint_type", "borough",
                            "resolution_hours", "resolution_outlier_iqr"] if c in df.columns]
flagged = df.loc[df["resolution_outlier_iqr"].fillna(False), preview_cols]
display(flagged.head(20))
print(f"{n_out:,} of {len(v):,} valid durations ({100 * n_out / len(v):.2f}%) lie outside "
      f"[{lower:.2f}, {upper:.2f}] hours. These are investigation prompts, not deletions.")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))

ax1.hist(v, bins=50, color="skyblue", edgecolor="white")
ax1.axvline(mean, color="red", linestyle="--", label=f"Mean = {mean:.2f} h")
ax1.axvline(median, color="green", label=f"Median = {median:.2f} h")
ax1.set(title="NYC 311 resolution time distribution", xlabel="Resolution hours",
        ylabel="Number of requests")
ax1.legend()

ax2.boxplot(v, vert=False, whis=1.5)
ax2.axvline(upper, linestyle="--", label=f"Upper fence = {upper:.2f} h")
ax2.set(title="Resolution time boxplot", xlabel="Resolution hours")
ax2.legend()

plt.tight_layout()
plt.savefig(stats_path / "resolution_distribution.png", dpi=300, bbox_inches="tight")
plt.show()

print(f"Valid closed-case durations: {len(v):,} | Mean {mean:.2f} h | Median {median:.2f} h | Skewness {skewness:.3f}")
print("Inspect the observed distribution before interpreting it. Flagged durations are retained.")

flat_tables = {"resolution_iqr_outlier_summary": outlier_summary,
               "resolution_iqr_flagged_cases": flagged,
               "categorical_modes": categorical_summary,
               "temporal_modes": temporal_summary}
group_tables = {"numeric_summary": numeric_summary,
                "borough_central_tendency": borough_stats,
                "agency_central_tendency": agency_stats,
                "complaint_central_tendency": complaint_stats}

for name, table in flat_tables.items():
    table.to_csv(stats_path / f"{name}.csv", index=False)
for name, table in group_tables.items():
    table.to_csv(stats_path / f"{name}.csv")          # keep the group label index

print("Saved", len(flat_tables) + len(group_tables) + 1, "files to:", stats_path)
