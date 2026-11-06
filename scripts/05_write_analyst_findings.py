"""Reproduce all 15 observations and evidence from one identified local extract.

Run from the repository root. This writes aggregate CSVs/charts and the findings
report; it does not execute SQL or claim to verify MySQL results.
"""
import argparse
import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.data import counts, medians, read_csv, usable_coordinates


def render_findings(evidence, metadata, relative_script):
    """Keep the reader view short; full interpretations remain in the evidence CSV."""
    cautions = [
        'Requests are reports, not unique incidents or all problems in NYC.',
        'Repeat reports and reporting access affect counts; volume does not establish severity.',
        'Agency counts do not measure staff effort or performance; case types differ.',
        'Borough counts are not population-adjusted rates or performance rankings.',
        'Partial-month coverage cannot establish monthly growth or seasonality.',
        'Weekday exposure is unequal and boundary days are partial; reporting time may differ from incident time.',
        'Keep source status separate from timestamp-based closure; neither verifies satisfaction.',
        'Only valid closed cases contribute durations; open cases create incomplete-follow-up bias.',
        'Compare valid sample sizes and case mix before interpreting category medians.',
        'Small samples and different responsibilities prevent a simple agency performance ranking.',
        'Flags prompt review, not deletion or a finding of SLA failure.',
        'Report the median and tail alongside the mean; open cases are excluded.',
        'Rounded cells are not neighbourhoods; repeated reports, missing data and location provenance affect concentration.',
        'Request age and service mix affect closure rates; recorded closure does not establish service quality.',
        'Thresholds are project choices; high request volume may still have few valid durations.',
    ]
    lines = ['# Findings for all 15 investigations',
             f"{metadata['rows']:,} requests; creation coverage {metadata['creation_start']} to {metadata['creation_end']} (NYC local time). No filters. Valid durations: {metadata['valid_durations']:,}.",
             'Closure means a recorded closed timestamp. Negative durations are excluded from duration analysis; outliers are retained. Original API download metadata is unavailable.',
             f'[Full evidence](analyst_evidence.csv) | [Source details](analysis_provenance.json) | [Calculation script]({relative_script})']
    for i, row in enumerate(evidence):
        sentences=re.split(r'(?<=[.!?])\s+(?=[A-Z])',row['observed_pattern'])
        observation=' '.join(sentences[:2])
        lines.extend([f"## {row['task'].replace('_',' ')}", row['question'],
                      f"**Sample:** {int(row['sample_size']):,}.",
                      '**Observed:** '+observation, '**Interpretation:** '+cautions[i],
                      f"[Results]({row['result_file']}) | [Chart]({row['visualization']}) | [SQL reference]({row['query_file']})"])
    return '\n\n'.join(lines)+'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'data/cleaned/nyc_cleaned.csv')
    parser.add_argument('--output', type=Path, default=ROOT / 'reports')
    args = parser.parse_args()
    source = args.source.resolve()
    out = args.output.resolve()
    evidence_dir = out / 'analysis'
    relative_script = Path(os.path.relpath(Path(__file__).resolve(),out)).as_posix()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    df = read_csv(source)
    v = df.resolution_hours.dropna()
    if df.empty or v.empty:
        raise ValueError('This findings generator requires requests and at least one valid duration.')
    n, nv = len(df), len(v)
    dated = df.created_date.notna().sum()
    start, end = df.created_date.min(), df.created_date.max()
    q1, q3 = v.quantile([.25, .75])
    lower, upper = q1-1.5*(q3-q1), q3+1.5*(q3-q1)
    outlier_n = int((v.lt(lower) | v.gt(upper)).sum())
    cat, agency, borough, status = [counts(df, c) for c in ['complaint_type', 'agency', 'borough', 'status']]
    cm, am = medians(df, 'complaint_type').dropna(subset=['Median_hours']), medians(df, 'agency').dropna(subset=['Median_hours'])
    monthly = df.groupby(df.created_date.dt.to_period('M')).size().rename('Requests').reset_index()
    monthly['created_date'] = monthly.created_date.astype(str)
    weekday_hour = df.groupby([df.created_date.dt.day_of_week.rename('Weekday_Monday0'),
                              df.created_date.dt.hour.rename('Hour')]).size().rename('Requests').reset_index()
    weekday = df.groupby(df.created_date.dt.day_name()).size()
    hour = df.groupby(df.created_date.dt.hour).size()
    geo = usable_coordinates(df)
    geo_cells = geo.assign(Latitude_cell=geo.latitude.round(2), Longitude_cell=geo.longitude.round(2))
    geo_cells = geo_cells.groupby(['Latitude_cell', 'Longitude_cell']).size().rename('Requests').reset_index().sort_values('Requests', ascending=False)
    closure = df.groupby('borough').agg(Requests=('unique_key', 'size'), Recorded_closed=('is_closed', 'sum')).reset_index()
    closure['Closure_pct'] = 100*closure.Recorded_closed/closure.Requests
    closure = closure.sort_values('Closure_pct', ascending=False)
    slow = cm.loc[cm.Requests.ge(100) & cm.Median_hours.ge(24)].sort_values('Requests', ascending=False)
    stats = pd.DataFrame([dict(valid_n=nv, mean_hours=v.mean(), median_hours=v.median(),
                               mode_hours=v.mode().iloc[0], min_hours=v.min(), max_hours=v.max(),
                               range_hours=v.max()-v.min(), q1_hours=q1, q3_hours=q3, iqr_hours=q3-q1,
                               sample_variance=v.var(), sample_std=v.std(), skewness=v.skew())])
    iqr = pd.DataFrame([dict(valid_n=nv, q1_hours=q1, q3_hours=q3, lower_fence=lower,
                             upper_fence=upper, outlier_n=outlier_n, outlier_pct=100*outlier_n/nv)])
    hist_counts, edges = np.histogram(v, bins=50)
    histogram = pd.DataFrame(dict(bin_start_hours=edges[:-1], bin_end_hours=edges[1:], Requests=hist_counts))
    pct = lambda x, den=n: 100*x/den
    def leaders(table, field, metric='Requests', limit=3):
        return '; '.join(f'{r[field]} ({r[metric]:,.0f})' for _, r in table.head(limit).iterrows())
    questions = [
        'What is the total distinct request volume?', 'Which 10 complaint categories are most frequent?',
        'How is workload distributed across agencies?', 'How does request volume vary by borough?',
        'How does request volume change by month?', 'When (weekday and hour) is demand highest?',
        'How are recorded statuses distributed?', 'What are the descriptive statistics of valid resolution durations?',
        'What is the median resolution duration by complaint category?', 'What is the median resolution duration by agency?',
        'Which durations fall outside the 1.5 × IQR fences?', 'What is the shape of the duration distribution?',
        'Where are complaints geographically concentrated using usable coordinates?',
        'How do recorded closure rates compare across boroughs?',
        'Which categories have both high volume and long median duration?',
    ]
    names = ['distinct_volume', 'top_complaints', 'agency_workload', 'borough_volume', 'monthly_trend',
             'weekday_hour', 'status_distribution', 'resolution_statistics', 'category_median',
             'agency_median', 'iqr_outliers', 'duration_distribution', 'geographic_concentration',
             'closure_rate', 'high_volume_slow_categories']
    observations = [
        f'The extract contains {n:,} rows and {df.unique_key.nunique():,} distinct request IDs. Creation timestamps span {start} to {end}; {dated:,} rows have usable creation dates.',
        f'The leading categories are {leaders(cat, "complaint_type")}. The top ten account for {cat.head(10).Requests.sum():,} requests ({pct(cat.head(10).Requests.sum()):.2f}%); {cat.iloc[0].complaint_type} alone accounts for {pct(cat.iloc[0].Requests):.2f}%.',
        f'The largest recorded agency workloads are {leaders(agency, "agency")}. These three agencies receive {pct(agency.head(3).Requests.sum()):.2f}% of the sample.',
        f'The largest borough counts are {leaders(borough, "borough")}. {borough.iloc[0].borough} represents {pct(borough.iloc[0].Requests):.2f}% of all requests.',
        f'The extract covers {len(monthly)} calendar month(s), with {dated:,} dated requests. Coverage begins {start} and ends {end}; the monthly series does not contain a full set of comparable months.',
        f'{weekday.idxmax()} has the largest pooled weekday count ({weekday.max():,}); the busiest pooled hour is {hour.idxmax():02.0f}:00–{hour.idxmax():02.0f}:59 ({hour.max():,} requests, {pct(hour.max(), dated):.2f}% of dated records). The weekday/hour table contains the full cross-tabulation.',
        f'The most frequent recorded statuses are {leaders(status, "status")}. Separately, {df.is_closed.sum():,} rows ({pct(df.is_closed.sum()):.2f}%) have a closure timestamp; source status labels have been preserved.',
        f'Among {nv:,} valid durations, mean resolution is {v.mean():.2f} h and median is {v.median():.2f} h. Q1={q1:.2f} h, Q3={q3:.2f} h, sample SD={v.std():.2f} h, and range={v.min():.2f}–{v.max():.2f} h. {int(df.closed_date.lt(df.created_date).sum()):,} negative chronological durations are excluded.',
        f'The largest observed category median is {cm.iloc[0].complaint_type}: {cm.iloc[0].Median_hours:.2f} h, based on {cm.iloc[0].Valid_durations:,} valid durations from {cm.iloc[0].Requests:,} requests. The accompanying table reports both counts for every category with a valid duration.',
        f'The largest observed agency median is {am.iloc[0].agency}: {am.iloc[0].Median_hours:.2f} h from {am.iloc[0].Valid_durations:,} valid durations ({am.iloc[0].Requests:,} requests). The table retains valid-duration denominators for each agency.',
        f'Tukey fences are {lower:.2f} h and {upper:.2f} h (IQR={q3-q1:.2f} h). {outlier_n:,} of {nv:,} valid durations ({pct(outlier_n,nv):.2f}%) lie outside the fences. No cases are deleted by this screening.',
        f'Sample skewness is {v.skew():.3f}; mean={v.mean():.2f} h versus median={v.median():.2f} h. The histogram contains all {nv:,} valid durations, including its long-duration tail.',
        (f'{len(geo):,} of {n:,} requests ({pct(len(geo)):.2f}%) have usable coordinates inside the approximate NYC bounds. The busiest rounded 0.01-degree cell is latitude {geo_cells.iloc[0].Latitude_cell:.2f}, longitude {geo_cells.iloc[0].Longitude_cell:.2f}, with {geo_cells.iloc[0].Requests:,} requests.' if len(geo) else 'No usable original-coordinate requests remain after screening; use borough counts instead.'),
        f'Overall recorded closure is {df.is_closed.sum():,}/{n:,} ({pct(df.is_closed.sum()):.2f}%). Borough-specific numerators, denominators and percentages are in the result table. The highest displayed group is {closure.iloc[0].borough}: {closure.iloc[0].Recorded_closed:,}/{closure.iloc[0].Requests:,} ({closure.iloc[0].Closure_pct:.2f}%).',
        (f'{len(slow):,} categories meet at least 100 requests and median duration of at least 24 h. The highest-volume qualifying category is {slow.iloc[0].complaint_type}: {slow.iloc[0].Requests:,} requests, {slow.iloc[0].Valid_durations:,} valid durations and median {slow.iloc[0].Median_hours:.2f} h.' if len(slow) else 'No category meets both thresholds: at least 100 requests and at least 24 median hours.'),
    ]
    interpretations = [
        'This is the volume of the supplied snapshot, not all NYC requests or unique incidents. Multiple requests can describe the same problem. The extraction timestamp and API parameters were not supplied for this local file; creation coverage does not establish when it was downloaded.',
        'These categories are candidates for workload review, but reporting frequency, repeated complaints and category definitions affect counts. A high complaint count does not establish the underlying prevalence or severity of a problem.',
        'Counts describe assigned requests rather than staff effort, capacity or performance. Agencies handle different case types and complexity; staffing recommendations would require workload and resource measures beyond request totals.',
        'Raw borough counts are not population-adjusted rates. Population, visitors, reporting access and the mix of services can explain differences; do not conclude that the largest count identifies the worst-performing borough.',
        'No month-to-month or seasonal conclusion is supported by this short, partial-month sample. Obtain complete comparable months before assessing growth, decline or seasonality.',
        'Pooled weekday totals have unequal exposure: some weekdays occur more often in this short window, and boundary days are partial. Hourly counts can reflect reporting behaviour as well as incident timing. Use complete days and per-day exposure before proposing staffing changes.',
        'A recorded status and the existence of a closed timestamp are different fields and may disagree. Neither verifies satisfaction or independently confirmed resolution. Do not overwrite source statuses just to make them match the closure indicator.',
        'These statistics describe observed valid closed cases only. Open cases have no final duration and are excluded, creating incomplete-follow-up bias in a recent extract. Report the median alongside the mean and retain invalid-date counts as a quality limitation.',
        'The largest median is not a reliable performance ranking. Some categories have very few valid closed cases relative to incoming volume, and service complexity differs. Inspect the valid counts and closure coverage, and use minimum-sample rules before comparing categories.',
        'Agency medians reflect different case mixes and closure coverage. A very small valid sample can produce an unstable apparent maximum; do not infer that the agency is intrinsically slower or less effective.',
        'IQR flags are prompts for case review, not proof of errors or SLA breaches. Long cases may be legitimate and should remain in the main analysis. The fences depend on this particular sample and its observed closed cases.',
        'The positive skew and difference between mean and median indicate that long cases pull the average upward in this sample. The median better summarizes its central closed-case duration, while tail behaviour remains operationally relevant; unclosed cases are still absent from the distribution.',
        'Rounded cells are approximate angular grid cells, not neighbourhoods or official boundaries. Repeated reports, reporting density and missing coordinates affect apparent concentration. Imputed coordinates are excluded when flags exist; the earlier local file lacks full imputation provenance, so geographic findings remain exploratory.',
        'Closure-rate differences do not establish service quality. Request age, agency/category mix, inconsistent timestamps and follow-up length can affect comparisons. Rows with impossible closure chronology still count as recorded closure under the stated KPI definition, but never as valid durations.',
        'The 100-request and 24-hour cut-offs are project choices, not official service standards. High total volume does not guarantee a large valid-duration sample; use the valid count and closure coverage when selecting categories for further investigation rather than treating this as a definitive priority ranking.',
    ]
    tables = [pd.DataFrame({'Distinct_requests':[df.unique_key.nunique()]}), cat.head(10), agency, borough,
              monthly, weekday_hour, status, stats, cm, am, iqr, histogram, geo_cells, closure, slow]
    samples = [n,n,n,n,int(dated),int(dated),n,nv,nv,nv,nv,nv,len(geo),n,nv]
    evidence = []
    for i, (name, question, table, observation, interpretation, sample) in enumerate(zip(names, questions, tables, observations, interpretations, samples), 1):
        stem = f'{i:02}_{name}'
        table.to_csv(evidence_dir/f'{stem}.csv', index=False)
        fig, ax = plt.subplots(figsize=(10, 4.5))
        if i in [8,12]:
            ax.hist(v, bins=50, color='#138f89'); ax.set(xlabel='Valid resolution hours', ylabel='Requests')
            ax.axvline(v.median(), color='#c46a14', label='Median'); ax.legend()
        elif i == 11:
            ax.boxplot(v, vert=False); ax.set_xlabel('Valid resolution hours')
        elif i == 6:
            grid = table.pivot(index='Weekday_Monday0', columns='Hour', values='Requests').reindex(index=range(7), columns=range(24)).fillna(0)
            im=ax.imshow(grid, aspect='auto', cmap='viridis');fig.colorbar(im,ax=ax,label='Requests')
            ax.set(xlabel='NYC local hour', ylabel='Weekday (Monday=0)')
        elif i == 13 and not table.empty:
            im=ax.scatter(table.Longitude_cell,table.Latitude_cell,c=table.Requests,s=table.Requests**.5*3)
            fig.colorbar(im,ax=ax,label='Requests'); ax.set(xlabel='Longitude',ylabel='Latitude')
        elif i == 5:
            ax.bar(table.created_date,table.Requests);ax.set_ylabel('Requests (partial months)')
        elif i == 1:
            ax.bar(['Distinct requests'],[n]);ax.set_ylabel('Requests')
        elif table.empty:
            ax.text(.5,.5,'No matching results',ha='center',transform=ax.transAxes)
        else:
            metric = 'Median_hours' if i in [9,10,15] else 'Closure_pct' if i == 14 else 'Requests'
            show=table.head(15)
            labels = show.iloc[:,0].astype(str)
            if i in [9,10,15]:
                labels = labels + ' (valid n=' + show.Valid_durations.astype(str) + ')'
            ax.barh(labels,show[metric],color='#138f89');ax.invert_yaxis();ax.set_xlabel(metric)
        ax.set_title(f'{i:02} {name.replace("_"," ")} · sample n={sample:,}')
        fig.tight_layout();fig.savefig(evidence_dir/f'{stem}.png',dpi=150);plt.close(fig)
        evidence.append(dict(task=stem,question=question,query_file=Path(os.path.relpath(ROOT/'sql'/f'{stem}.sql',out)).as_posix(),
                             calculation='Pandas equivalent; see scripts/05_write_analyst_findings.py (SQL not executed)',
                             sample_size=sample,filtered_n=n,valid_duration_n=nv,
                             result_file=f'analysis/{stem}.csv',visualization=f'analysis/{stem}.png',
                             observed_pattern=observation,cautious_interpretation=interpretation))
    pd.DataFrame(evidence).to_csv(out/'analyst_evidence.csv',index=False)
    metadata = dict(source=str(source.relative_to(ROOT)) if source.is_relative_to(ROOT) else str(source),
                    sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    generated_at=datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),
                    creation_start=str(start),creation_end=str(end),rows=n,valid_durations=nv,
                    recorded_closed=int(df.is_closed.sum()),negative_chronology=int(df.closed_date.lt(df.created_date).sum()),
                    usable_coordinates=len(geo),filters='None; full supplied snapshot',
                    extraction_metadata_available=False,sql_executed=False,
                    minimum_requests=100,minimum_median_hours=24)
    (out/'analysis_provenance.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    (out/'analyst_findings.md').write_text(render_findings(evidence, metadata, relative_script),encoding='utf-8')
    print(f'Wrote {len(evidence)} completed investigations, aggregate tables and charts to {out}')


if __name__ == '__main__':
    main()
