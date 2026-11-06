"""UrbanPulse interactive analyst dashboard. Run: streamlit run streamlit_app.py."""
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.data import ROOT, counts, filter_data, kpis, medians, read_csv, read_mysql, usable_coordinates

st.set_page_config(page_title='UrbanPulse NYC', page_icon='🏙️', layout='wide')
st.title('UrbanPulse NYC')
st.caption('Citizen requests · Service demand · Recorded closure')


@st.cache_data(ttl=300, show_spinner=False)
def load_csv(path, modified):
    return read_csv(path)


@st.cache_data(ttl=60, show_spinner=False)
def load_database():
    return read_mysql()


def chart(fig):
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, width='stretch')


def bars(table, category, metric='Requests', limit=15):
    if table.empty:
        st.info('No matching results for this investigation.')
        return
    chart(px.bar(table.head(limit), x=metric, y=category, orientation='h',
                 color_discrete_sequence=['#13a89e']).update_yaxes(autorange='reversed'))
    st.dataframe(table, hide_index=True, width='stretch')


with st.sidebar:
    st.header('Explore requests')
    source = st.selectbox('Data source', ['Cleaned CSV', 'MySQL'], key='source')
    if st.button('Refresh data'):
        st.cache_data.clear()
    page = st.radio('View', ['Overview', 'Demand & workload', 'Resolution & outliers',
                             'Geography & closure', 'Records & quality'])

try:
    with st.spinner('Loading requests…'):
        if source == 'MySQL':
            df = load_database()
            label = 'Published MySQL service_requests'
        else:
            canonical = ROOT / 'data/cleaned/nyc_cleaned.csv'
            legacy = ROOT / 'data/cleaned/nyc_311_cleaned.csv'
            default = os.environ.get('URBANPULSE_DATA', 'data/cleaned/nyc_cleaned.csv' if canonical.is_file() or not legacy.is_file() else 'data/cleaned/nyc_311_cleaned.csv')
            path_text = st.sidebar.text_input('Cleaned CSV path', default)
            path = Path(path_text).expanduser()
            if not path.is_absolute():
                path = ROOT / path
            if not path.is_file():
                st.info('No cleaned dataset found. Run notebooks 01 and 02, or select your cleaned CSV path in the sidebar.')
                st.code('python scripts/01_data_retrieval.py\npython scripts/02_data_preparation.py')
                st.stop()
            df = load_csv(str(path), path.stat().st_mtime_ns)
            label = path.name
except (ValueError, OSError, pd.errors.ParserError) as error:
    st.error(str(error) if isinstance(error, ValueError) else 'Could not read the dataset. Check the file path, access and CSV format.')
    st.stop()

if df.empty:
    st.info('The selected source contains no requests. Load a populated extract first.')
    st.stop()

if source == 'Cleaned CSV' and path.name == 'nyc_311_cleaned.csv':
    st.warning('Using the earlier local extract for exploration. For submission, select nyc_cleaned.csv from the reviewed preparation notebook and retain its matching extraction metadata.')

with st.sidebar:
    st.divider()
    dated = df.created_date.dropna()
    use_dates = st.checkbox('Filter by creation date', value=False, disabled=dated.empty)
    dates = None
    if use_dates:
        selected = st.date_input('Creation dates (inclusive)',
                                 value=(dated.min().date(), dated.max().date()))
        if len(selected) != 2:
            st.info('Select a start and end date.')
            st.stop()
        dates = selected
    boroughs = st.multiselect('Boroughs', sorted(df.borough.unique()), default=sorted(df.borough.unique()))
    complaints = st.multiselect('Complaint types', sorted(df.complaint_type.unique()),
                                default=sorted(df.complaint_type.unique()))
    st.caption('Clearing a category filter selects no records. Dates refer to NYC local time.')

filtered = filter_data(df, dates, boroughs, complaints)
st.caption(f'{label} · {len(filtered):,} of {len(df):,} requests · source coverage: '
           f'{df.created_date.min()} to {df.created_date.max()}')
if filtered.empty:
    st.info('No requests match these filters. Widen the date range or select more categories.')
    st.stop()

metrics = kpis(filtered)
columns = st.columns(5)
for col, title, value, help_text in zip(columns,
    ['Total requests', 'Recorded closure', 'Open requests', 'Median resolution', 'Over 72 hours'],
    [f"{metrics['total']:,}", f"{metrics['closure']:.1f}%", f"{metrics['open']:,}",
     'N/A' if metrics['median'] is None else f"{metrics['median']:.2f} h",
     'N/A' if metrics['over72'] is None else f"{metrics['over72']:.1f}%"],
    ['Distinct request identifiers.', 'Rows with a recorded closed timestamp / filtered rows.',
     'Rows without a recorded closed timestamp.', 'Median among valid non-negative durations.',
     'Valid durations strictly greater than 72 hours / all valid durations.']):
    col.metric(title, value, help=help_text)
st.caption(f"Resolution denominator: {metrics['valid_n']:,} valid durations. Closure is not satisfaction; "
           '72 hours is an illustrative project threshold, not an official SLA.')

if page == 'Overview':
    st.subheader('Demand at a glance')
    a, b = st.columns(2)
    with a:
        st.markdown('**Top 10 complaint categories**')
        bars(counts(filtered, 'complaint_type'), 'complaint_type', limit=10)
    with b:
        st.markdown('**Daily incoming requests**')
        daily = filtered.groupby(filtered.created_date.dt.date).size().rename('Requests').reset_index()
        chart(px.line(daily, x='created_date', y='Requests', markers=True))
    st.info('311 reflects reported requests. Recent cases have incomplete follow-up, and short extracts cannot establish seasonal trends.')

elif page == 'Demand & workload':
    task = st.selectbox('Investigation', ['Top complaints', 'Agency workload', 'Borough volume',
                                         'Monthly trend', 'Weekday and hour', 'Recorded statuses'], key='demand_task')
    if task in ['Top complaints', 'Agency workload', 'Borough volume', 'Recorded statuses']:
        field = {'Top complaints': 'complaint_type', 'Agency workload': 'agency',
                 'Borough volume': 'borough', 'Recorded statuses': 'status'}[task]
        table = counts(filtered, field)
        table['Share_pct'] = table.Requests / len(filtered) * 100
        bars(table, field, limit=10 if task == 'Top complaints' else 20)
    elif task == 'Monthly trend':
        table = filtered.groupby(filtered.created_date.dt.to_period('M').astype('string')).size().rename('Requests').reset_index()
        table = table.loc[table.created_date.notna()]
        chart(px.line(table, x='created_date', y='Requests', markers=True))
        st.dataframe(table, hide_index=True)
        st.caption('First and last months may be partial; missing creation dates are excluded.')
    else:
        table = filtered.groupby([filtered.created_date.dt.day_of_week.rename('Weekday'),
                                  filtered.created_date.dt.hour.rename('Hour')]).size().unstack(fill_value=0)
        table = table.reindex(index=range(7), columns=range(24), fill_value=0)
        chart(px.imshow(table, labels={'x': 'Hour', 'y': 'Weekday (Monday=0)', 'color': 'Requests'}, aspect='auto'))
        st.dataframe(table)
    st.caption(f'Dated sample: {filtered.created_date.notna().sum():,}; total filtered sample: {len(filtered):,}.')

elif page == 'Resolution & outliers':
    valid = filtered.resolution_hours.dropna()
    if valid.empty:
        st.info('No valid resolution durations in the current selection. Volume and closure views remain available.')
    else:
        task = st.selectbox('Investigation', ['Descriptive statistics', 'Median by category', 'Median by agency',
                                             'IQR outliers', 'Distribution and skewness', 'High volume and slow categories'], key='resolution_task')
        if task == 'Descriptive statistics':
            summary = valid.describe().to_frame('Hours')
            summary.loc['variance'] = valid.var()
            summary.loc['range'] = valid.max() - valid.min()
            summary.loc['mode'] = valid.mode().iloc[0]
            st.dataframe(summary)
            chart(px.box(filtered, x='resolution_hours'))
        elif task in ['Median by category', 'Median by agency', 'High volume and slow categories']:
            field = 'agency' if task == 'Median by agency' else 'complaint_type'
            table = medians(filtered, field).dropna(subset=['Median_hours'])
            if task == 'High volume and slow categories':
                n = st.number_input('Minimum requests', min_value=1, value=100)
                h = st.number_input('Minimum median hours', min_value=0.0, value=24.0)
                table = table.loc[table.Requests.ge(n) & table.Median_hours.ge(h)]
                st.caption('Thresholds are project choices. Compare valid-duration counts before drawing conclusions.')
            bars(table, field, metric='Median_hours')
        elif task == 'IQR outliers':
            q1, q3 = valid.quantile([.25, .75])
            lower, upper = q1 - 1.5*(q3-q1), q3 + 1.5*(q3-q1)
            outliers = filtered.loc[filtered.resolution_hours.lt(lower) | filtered.resolution_hours.gt(upper)]
            st.write(f'Q1: {q1:.2f} h · Q3: {q3:.2f} h · Fences: {lower:.2f}–{upper:.2f} h · Flagged: {len(outliers):,} / {len(valid):,}')
            chart(px.box(filtered, x='resolution_hours'))
            st.dataframe(outliers[['unique_key', 'complaint_type', 'agency', 'resolution_hours']], hide_index=True)
            st.caption('Outliers are investigation prompts and remain in the analysis.')
        else:
            chart(px.histogram(filtered, x='resolution_hours', nbins=50, labels={'resolution_hours': 'Resolution hours'}))
            st.write(f'Mean: {valid.mean():.2f} h · Median: {valid.median():.2f} h · Sample skewness: {valid.skew():.3f}')
            st.caption('Long cases may be legitimate. Duration comparisons reflect case mix and incomplete follow-up.')

elif page == 'Geography & closure':
    st.subheader('Geographic concentration')
    geo = usable_coordinates(filtered)
    st.caption(f'{len(geo):,} / {len(filtered):,} usable original-coordinate records. Approximate NYC bounds; imputed coordinates excluded when flagged.')
    if geo.empty:
        st.info('No usable coordinates. Borough counts below provide a geographic summary.')
    else:
        cells = geo.assign(latitude=geo.latitude.round(2), longitude=geo.longitude.round(2))
        cells = cells.groupby(['latitude', 'longitude']).size().rename('Requests').reset_index()
        chart(px.scatter(cells, x='longitude', y='latitude', size='Requests', color='Requests',
                         hover_data=['Requests'], labels={'latitude': 'Latitude', 'longitude': 'Longitude'}))
        st.dataframe(cells.sort_values('Requests', ascending=False), hide_index=True)
    bars(counts(filtered, 'borough'), 'borough')
    st.subheader('Recorded closure by borough')
    table = filtered.groupby('borough').agg(Requests=('unique_key', 'size'), Closed=('is_closed', 'sum')).reset_index()
    table['Closure_pct'] = table.Closed / table.Requests * 100
    bars(table.sort_values('Closure_pct', ascending=False), 'borough', 'Closure_pct')
    st.caption('Recorded closure is based on timestamps and does not demonstrate service quality or satisfaction.')

elif page == 'Records & quality':
    st.subheader('Filtered record preview')
    preview = ['unique_key', 'created_date', 'closed_date', 'agency', 'complaint_type', 'borough', 'status', 'is_closed', 'resolution_hours']
    st.dataframe(filtered[preview].head(500), hide_index=True, width='stretch')
    st.caption('Preview capped at 500 rows; download includes all filtered rows and these columns.')
    st.download_button('Download filtered records', filtered[preview].to_csv(index=False).encode('utf-8'),
                       file_name='urbanpulse_filtered.csv', mime='text/csv')
    st.subheader('Data quality and definitions')
    st.write({'Missing creation dates': int(filtered.created_date.isna().sum()),
              'Closure before creation': int(filtered.closed_date.lt(filtered.created_date).sum()),
              'Without valid duration': int(filtered.resolution_hours.isna().sum()),
              'Without usable original coordinates': len(filtered)-len(usable_coordinates(filtered))})
    st.caption('Durations and closure indicators are recalculated from parsed timestamps. Missing creation dates remain in totals unless a date filter is active. Source categories are preserved. Source CSV provenance and cleaning logs should be reviewed before submission.')
