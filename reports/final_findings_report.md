# UrbanPulse NYC final findings

Report date: 6 November 2026. Dataset: 100,000 NYC 311 requests created between 14 October 2026 at 11:19:47 and 23 October 2026 at 02:46:57, NYC local time. No filters were applied.

## Main findings

Illegal Parking is the largest category, with 16,398 requests. The top ten categories account for 58.57% of the snapshot. NYPD, HPD and DSNY together receive 76.95% of requests; Brooklyn has the largest borough count, at 32,779.

Valid closed cases have a median duration of 2.64 hours and a mean of 16.32 hours. The long right tail makes the mean much higher than the median. Service categories also differ substantially, so the overall median should not be used to rank agencies.

## Dashboard KPIs

| KPI | Value | Denominator |
|---|---:|---|
| Distinct requests | 100,000 | Unique request IDs |
| Recorded closure | 69.38% | 69,382 / 100,000 rows |
| Open requests | 30,618 | Rows without a closure timestamp |
| Median resolution | 2.64 hours | 69,263 valid durations |
| Over 72 hours | 6.4% | 4,402 / 69,263 valid durations |

Closure means a recorded closed timestamp. The 119 closures dated before creation count as recorded closures but are excluded from duration calculations. The 72-hour threshold is a project choice, not an official SLA.

## Demand patterns

| Category | Requests |
|---|---:|
| Illegal Parking | 16,398 |
| HEAT/HOT WATER | 11,692 |
| Noise - Residential | 8,971 |

Brooklyn contributes 32.78% of requests, Queens 22.30%, Manhattan 21.83%, the Bronx 19.60% and Staten Island 3.38%. Another 108 requests have an unspecified borough. These are counts, not population-adjusted rates.

Thursday has the largest pooled weekday count (22,084), and 11:00-11:59 is the busiest pooled hour (6,113 requests). Some weekdays occur more often in this short window, and boundary days are partial. Complete comparable days are needed before recommending staffing changes. One partial month cannot establish seasonal trends.

[Complaint chart](analysis/02_top_complaints.png) | [Weekday/hour results](analysis/06_weekday_hour.csv)

## Duration and outliers

| Statistic | Hours |
|---|---:|
| Mean / median | 16.32 / 2.64 |
| First / third quartile | 0.74 / 18.05 |
| IQR | 17.31 |
| Sample standard deviation | 29.63 |
| Minimum / maximum | 0.00 / 199.47 |

Sample skewness is 2.727. The IQR fences are -25.23 and 44.02 hours; 9,250 durations (13.35%) exceed the upper fence. These cases remain in the analysis because long durations may be legitimate. Open cases do not contribute final durations, so recent-case follow-up affects these statistics.

[Distribution chart](analysis/12_duration_distribution.png) | [Full statistics](analysis/08_resolution_statistics.csv)

## Categories for further review

Thirty-six categories meet the exploratory cut-offs of at least 100 requests and 24 median hours. The five highest-volume candidates are:

| Category | Requests | Valid durations | Median hours |
|---|---:|---:|---:|
| HEAT/HOT WATER | 11,692 | 7,054 | 32.71 |
| UNSANITARY CONDITION | 4,249 | 637 | 70.31 |
| PLUMBING | 2,186 | 573 | 46.87 |
| Noise | 2,019 | 1,286 | 42.02 |
| PAINT/PLASTER | 2,002 | 489 | 50.94 |

Use these as investigation candidates, not a performance ranking. Valid-duration coverage varies sharply. OTI's 119.83-hour agency median, for example, is based on just one valid case. Agency responsibilities and recording practices also differ.

## Closure and geography

Queens has the highest recorded closure rate among named boroughs (73.79%), followed by Staten Island (71.79%) and Brooklyn (70.10%). Rates for the Bronx and Manhattan are 66.48% and 66.17%. These comparisons are not adjusted for request age or service mix and do not measure satisfaction.

There are 98,415 coordinate-usable records (98.42%). The busiest rounded 0.01-degree cell, at 40.65, -73.96, contains 865 requests. Cells are approximate groupings, not neighbourhoods. Reporting density, repeated complaints and incomplete location provenance limit spatial conclusions.

[Closure results](analysis/14_closure_rate.csv) | [Geographic chart](analysis/13_geographic_concentration.png)

## Recommended actions

1. Review high-volume, longer-duration categories using case age and valid sample counts.
2. Investigate negative and zero-duration records and status/closure disagreements.
3. Report medians, sample sizes and tail measures together; retain legitimate outliers.
4. Collect complete comparable periods before making seasonal or staffing claims.
5. Recover genuine extraction metadata or document a successful new API run.

## Verification and limits

Preparation, statistics, the 100,000-row MySQL load, full read-back validation and all 15 SQL/Python comparisons passed. Streamlit's five views passed using CSV and MySQL. See [execution evidence](execution/20261106_163637/summary.md) and [all 15 investigations](analyst_findings.md).

The initial report used the earlier cleaned snapshot; its headline figures agree with the newly prepared canonical data and executed SQL. Source hashes are in [report provenance](analysis_provenance.json) and the execution manifests. Original API download time and parameters remain unknown; the live extraction attempt stalled. This short snapshot describes reported requests, not all urban problems or causal service performance.

To regenerate the supporting Python findings from the included canonical CSV:

```powershell
python scripts/05_write_analyst_findings.py
```

Review this narrative after changing data; it is not automatically rewritten by the script.
