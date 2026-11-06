# Findings for all 15 investigations

100,000 requests; creation coverage 2026-10-14 11:19:47 to 2026-10-23 02:46:57 (NYC local time). No filters. Valid durations: 69,263.

Closure means a recorded closed timestamp. Negative durations are excluded from duration analysis; outliers are retained. Original API download metadata is unavailable.

[Full evidence](analyst_evidence.csv) | [Source details](analysis_provenance.json) | [Calculation script](../scripts/05_write_analyst_findings.py)

## 01 distinct volume

What is the total distinct request volume?

**Sample:** 100,000.

**Observed:** The extract contains 100,000 rows and 100,000 distinct request IDs. Creation timestamps span 2026-10-14 11:19:47 to 2026-10-23 02:46:57; 100,000 rows have usable creation dates.

**Interpretation:** Requests are reports, not unique incidents or all problems in NYC.

[Results](analysis/01_distinct_volume.csv) | [Chart](analysis/01_distinct_volume.png) | [SQL reference](../sql/01_distinct_volume.sql)

## 02 top complaints

Which 10 complaint categories are most frequent?

**Sample:** 100,000.

**Observed:** The leading categories are Illegal Parking (16,398); HEAT/HOT WATER (11,692); Noise - Residential (8,971). The top ten account for 58,573 requests (58.57%); Illegal Parking alone accounts for 16.40%.

**Interpretation:** Repeat reports and reporting access affect counts; volume does not establish severity.

[Results](analysis/02_top_complaints.csv) | [Chart](analysis/02_top_complaints.png) | [SQL reference](../sql/02_top_complaints.sql)

## 03 agency workload

How is workload distributed across agencies?

**Sample:** 100,000.

**Observed:** The largest recorded agency workloads are NYPD (41,731); HPD (27,979); DSNY (7,237). These three agencies receive 76.95% of the sample.

**Interpretation:** Agency counts do not measure staff effort or performance; case types differ.

[Results](analysis/03_agency_workload.csv) | [Chart](analysis/03_agency_workload.png) | [SQL reference](../sql/03_agency_workload.sql)

## 04 borough volume

How does request volume vary by borough?

**Sample:** 100,000.

**Observed:** The largest borough counts are BROOKLYN (32,779); QUEENS (22,303); MANHATTAN (21,831). BROOKLYN represents 32.78% of all requests.

**Interpretation:** Borough counts are not population-adjusted rates or performance rankings.

[Results](analysis/04_borough_volume.csv) | [Chart](analysis/04_borough_volume.png) | [SQL reference](../sql/04_borough_volume.sql)

## 05 monthly trend

How does request volume change by month?

**Sample:** 100,000.

**Observed:** The extract covers 1 calendar month(s), with 100,000 dated requests. Coverage begins 2026-10-14 11:19:47 and ends 2026-10-23 02:46:57; the monthly series does not contain a full set of comparable months.

**Interpretation:** Partial-month coverage cannot establish monthly growth or seasonality.

[Results](analysis/05_monthly_trend.csv) | [Chart](analysis/05_monthly_trend.png) | [SQL reference](../sql/05_monthly_trend.sql)

## 06 weekday hour

When (weekday and hour) is demand highest?

**Sample:** 100,000.

**Observed:** Thursday has the largest pooled weekday count (22,084); the busiest pooled hour is 11:00–11:59 (6,113 requests, 6.11% of dated records). The weekday/hour table contains the full cross-tabulation.

**Interpretation:** Weekday exposure is unequal and boundary days are partial; reporting time may differ from incident time.

[Results](analysis/06_weekday_hour.csv) | [Chart](analysis/06_weekday_hour.png) | [SQL reference](../sql/06_weekday_hour.sql)

## 07 status distribution

How are recorded statuses distributed?

**Sample:** 100,000.

**Observed:** The most frequent recorded statuses are Closed (66,944); Open (21,119); In Progress (11,639). Separately, 69,382 rows (69.38%) have a closure timestamp; source status labels have been preserved.

**Interpretation:** Keep source status separate from timestamp-based closure; neither verifies satisfaction.

[Results](analysis/07_status_distribution.csv) | [Chart](analysis/07_status_distribution.png) | [SQL reference](../sql/07_status_distribution.sql)

## 08 resolution statistics

What are the descriptive statistics of valid resolution durations?

**Sample:** 69,263.

**Observed:** Among 69,263 valid durations, mean resolution is 16.32 h and median is 2.64 h. Q1=0.74 h, Q3=18.05 h, sample SD=29.63 h, and range=0.00–199.47 h. 119 negative chronological durations are excluded.

**Interpretation:** Only valid closed cases contribute durations; open cases create incomplete-follow-up bias.

[Results](analysis/08_resolution_statistics.csv) | [Chart](analysis/08_resolution_statistics.png) | [SQL reference](../sql/08_resolution_statistics.sql)

## 09 category median

What is the median resolution duration by complaint category?

**Sample:** 69,263.

**Observed:** The largest observed category median is Curb Condition: 146.55 h, based on 16 valid durations from 260 requests. The accompanying table reports both counts for every category with a valid duration.

**Interpretation:** Compare valid sample sizes and case mix before interpreting category medians.

[Results](analysis/09_category_median.csv) | [Chart](analysis/09_category_median.png) | [SQL reference](../sql/09_category_median.sql)

## 10 agency median

What is the median resolution duration by agency?

**Sample:** 69,263.

**Observed:** The largest observed agency median is OTI: 119.83 h from 1 valid durations (8 requests). The table retains valid-duration denominators for each agency.

**Interpretation:** Small samples and different responsibilities prevent a simple agency performance ranking.

[Results](analysis/10_agency_median.csv) | [Chart](analysis/10_agency_median.png) | [SQL reference](../sql/10_agency_median.sql)

## 11 iqr outliers

Which durations fall outside the 1.5 × IQR fences?

**Sample:** 69,263.

**Observed:** Tukey fences are -25.23 h and 44.02 h (IQR=17.31 h). 9,250 of 69,263 valid durations (13.35%) lie outside the fences. No cases are deleted by this screening.

**Interpretation:** Flags prompt review, not deletion or a finding of SLA failure.

[Results](analysis/11_iqr_outliers.csv) | [Chart](analysis/11_iqr_outliers.png) | [SQL reference](../sql/11_iqr_outliers.sql)

## 12 duration distribution

What is the shape of the duration distribution?

**Sample:** 69,263.

**Observed:** Sample skewness is 2.727; mean=16.32 h versus median=2.64 h. The histogram contains all 69,263 valid durations, including its long-duration tail.

**Interpretation:** Report the median and tail alongside the mean; open cases are excluded.

[Results](analysis/12_duration_distribution.csv) | [Chart](analysis/12_duration_distribution.png) | [SQL reference](../sql/12_duration_distribution.sql)

## 13 geographic concentration

Where are complaints geographically concentrated using usable coordinates?

**Sample:** 98,415.

**Observed:** 98,415 of 100,000 requests (98.42%) have usable coordinates inside the approximate NYC bounds. The busiest rounded 0.01-degree cell is latitude 40.65, longitude -73.96, with 865.0 requests.

**Interpretation:** Rounded cells are not neighbourhoods; repeated reports, missing data and location provenance affect concentration.

[Results](analysis/13_geographic_concentration.csv) | [Chart](analysis/13_geographic_concentration.png) | [SQL reference](../sql/13_geographic_concentration.sql)

## 14 closure rate

How do recorded closure rates compare across boroughs?

**Sample:** 100,000.

**Observed:** Overall recorded closure is 69,382/100,000 (69.38%). Borough-specific numerators, denominators and percentages are in the result table.

**Interpretation:** Request age and service mix affect closure rates; recorded closure does not establish service quality.

[Results](analysis/14_closure_rate.csv) | [Chart](analysis/14_closure_rate.png) | [SQL reference](../sql/14_closure_rate.sql)

## 15 high volume slow categories

Which categories have both high volume and long median duration?

**Sample:** 69,263.

**Observed:** 36 categories meet at least 100 requests and median duration of at least 24 h. The highest-volume qualifying category is HEAT/HOT WATER: 11,692 requests, 7,054 valid durations and median 32.71 h.

**Interpretation:** Thresholds are project choices; high request volume may still have few valid durations.

[Results](analysis/15_high_volume_slow_categories.csv) | [Chart](analysis/15_high_volume_slow_categories.png) | [SQL reference](../sql/15_high_volume_slow_categories.sql)
