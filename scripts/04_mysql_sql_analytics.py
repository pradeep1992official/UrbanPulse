"""Run the matching UrbanPulse notebook as a script from the repository root."""
from IPython.display import display

# Install dependencies from requirements.txt before running this notebook.

import os, json, time, uuid
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import mysql.connector
from IPython.display import display, Markdown

from pathlib import Path
import os

project = Path(os.environ.get("URBANPULSE_ROOT", Path.cwd())).resolve()
if not (project / "data").is_dir() and (project.parent / "data").is_dir():
    project = project.parent
if not (project / "data").is_dir():
    raise FileNotFoundError("Run from the repository root or set URBANPULSE_ROOT.")

from dotenv import load_dotenv
load_dotenv(project / '.env', override=False)

data = project / 'data'
out = data / 'mysql'
out.mkdir(parents=True, exist_ok=True)
source_file = data / 'cleaned' / 'nyc_cleaned.csv'
DB, TABLE, BATCH = 'urban_pulse_db', 'service_requests', 1000

dates  = ['created_date', 'closed_date', 'due_date']
floats = ['latitude', 'longitude', 'latitude_original', 'longitude_original', 'resolution_hours']
ints   = ['unique_key', 'created_year', 'created_month', 'created_hour']
texts  = ['agency', 'complaint_type', 'borough', 'status', 'agency_name', 'descriptor', 'location_type',
          'incident_zip', 'city', 'resolution_description', 'created_weekday']
flags  = ['created_date_parse_error', 'closed_date_parse_error', 'due_date_parse_error', 'closure_before_creation',
          'invalid_date_flag', 'invalid_coordinates_original', 'city_borough_imputed', 'zipcode_city_imputed',
          'location_type_imputed', 'latitude_imputed', 'longitude_imputed', 'status_updated', 'invalid_coordinates',
          'missing_coordinates', 'outside_nyc_bounds', 'coordinate_quality_flag', 'long_resolution_flag', 'is_closed']
FLAG_MAP = {'True': 1, 'False': 0, '1': 1, '0': 0}

def must(ok, message):
    if not ok:
        raise ValueError(message)

df = pd.read_csv(source_file, dtype='string', keep_default_na=False).replace('', pd.NA)
must(set(df.columns) == set(dates + floats + ints + texts + flags) and len(df.columns) == 41 and not df.empty,
     'Empty data or changed schema; review notebook 02 output.')

for c in dates:
    df[c] = pd.to_datetime(df[c], errors='raise')
    must(df[c].dt.tz is None, 'Expected timezone-naive timestamps: ' + c)
for c in floats:
    df[c] = pd.to_numeric(df[c], errors='raise').astype('float64')
    must(not np.isinf(df[c]).any(), 'Infinite value: ' + c)
for c in ints:
    v = pd.to_numeric(df[c], errors='raise')
    must((v.dropna() % 1 == 0).all(), 'Non-integer: ' + c)
    df[c] = v.astype('Int64')
for c in flags:
    must(df[c].isin(list(FLAG_MAP)).all(), 'Invalid flag: ' + c)
    df[c] = df[c].map(FLAG_MAP).astype('int64')

must(df.unique_key.notna().all() and df.unique_key.is_unique and (df.unique_key >= 0).all(),
     'Missing, negative or duplicate request ID')
must(df.is_closed.eq(df.closed_date.notna().astype(int)).all(), 'Closure flag mismatch')

valid = df.created_date.notna() & df.closed_date.notna() & (df.closed_date >= df.created_date)
hours = (df.closed_date - df.created_date).dt.total_seconds() / 3600
must(df.resolution_hours.notna().eq(valid).all()
     and np.allclose(df.loc[valid, 'resolution_hours'], hours[valid], atol=1e-8, rtol=1e-10),
     'Invalid derived duration')

def mysql_type(c):
    if c in dates:  return 'DATETIME(6) NULL'
    if c in floats: return 'DOUBLE NULL'
    if c == 'unique_key': return 'BIGINT UNSIGNED NOT NULL PRIMARY KEY'
    if c in ints:   return 'SMALLINT NULL'
    if c in flags:  return 'TINYINT NOT NULL'
    if c == 'resolution_description': return 'LONGTEXT NULL'
    size = max(32, int(df[c].str.len().max()) if df[c].notna().any() else 32)
    return f'VARCHAR({size}) NULL' if size <= 1000 else 'TEXT NULL'

schema = {c: mysql_type(c) for c in df.columns}
display(pd.DataFrame(list(schema.items()), columns=['column', 'MySQL type']))
print('Verified shape:', df.shape, '| created_date:', df.created_date.min(), 'to', df.created_date.max())

def secret(name, default=None):
    value = os.environ.get(name)
    if value is None:
        try:
            from google.colab import userdata
            value = userdata.get(name)
        except Exception:
            value = None
    return value if value else default

config = {k: secret('MYSQL_' + k.upper()) for k in ['host', 'port', 'user', 'password']}
missing = ['MYSQL_' + k.upper() for k, v in config.items() if not v]
if missing:
    raise ValueError('Set these environment variables: ' + ', '.join(missing))

config['host'] = config['host'].strip()
if '/' in config['host'] or config['host'].lower() in {'localhost', '127.0.0.1', '::1'}:
    raise ValueError('MYSQL_HOST must be the Aiven host name only (no URI, not localhost).')
config['port'] = int(config['port'])

PEM = '-----BEGIN CERTIFICATE-----'
ca_value = secret('MYSQL_SSL_CA', str(project / 'certs' / 'ca.pem'))
if PEM in ca_value:                      # the secret holds the certificate text itself
    ca_path = project / 'certs' / 'ca.pem'
    ca_path.parent.mkdir(parents=True, exist_ok=True)
    ca_path.write_text(ca_value.replace('\r\n', '\n').strip() + '\n')
else:                                    # the secret (or default) is a file path
    ca_path = Path(ca_value).expanduser()
    if not ca_path.is_absolute():
        ca_path = project / ca_path
    if not ca_path.is_file():
        raise FileNotFoundError("Set MYSQL_SSL_CA to your CA certificate path.")
must(b'-----BEGIN CERTIFICATE-----' in ca_path.read_bytes(), 'MYSQL_SSL_CA must be a PEM CA certificate.')

config.update(charset='utf8mb4', connection_timeout=20, autocommit=False, ssl_disabled=False,
              ssl_ca=str(ca_path), ssl_verify_cert=True, ssl_verify_identity=True)

def connect(database=True):
    cn = mysql.connector.connect(**config, **({'database': DB} if database else {}))
    with cn.cursor() as cur:
        cur.execute("SET SESSION sql_mode='STRICT_ALL_TABLES,NO_ENGINE_SUBSTITUTION'")
    return cn

try:
    with connect(False) as cn, cn.cursor() as cur:
        cur.execute('SELECT VERSION()')
        version = cur.fetchone()[0]
        must('mariadb' not in version.lower() and int(version.split('.')[0]) >= 8, 'Requires MySQL 8.0+.')
        cur.execute("SHOW SESSION STATUS LIKE 'Ssl_cipher'")
        tls = cur.fetchone()
        must(bool(tls and tls[1]), 'No encrypted connection detected; stopping.')
        cur.execute('SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name=%s', (DB,))
        if not cur.fetchone()[0]:
            cur.execute(f'CREATE DATABASE `{DB}` CHARACTER SET utf8mb4')
    print('Connection passed: verified TLS, MySQL', version, '| database', DB)
except mysql.connector.Error as error:
    # Do not print the raw exception: it can contain connection settings.
    raise RuntimeError(f'MySQL connection/setup failed (error {error.errno}). Check status, Secrets, '
                       'host/port, CA certificate and network access.') from None

run = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:8]
stage, backup = f'{TABLE}_stage_{run}', f'{TABLE}_backup_{run}'
cols = list(df.columns)
quoted = ', '.join(f'`{c}`' for c in cols)
create = (f'CREATE TABLE `{stage}` (' + ', '.join(f'`{c}` {t}' for c, t in schema.items())
          + ', INDEX idx_created(created_date)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4')
(out / 'schema.sql').write_text(create.replace(stage, TABLE) + ';', encoding='utf-8')
insert = (f'INSERT INTO `{stage}` ({quoted}) VALUES (' + ','.join(['%s'] * len(cols))
          + ') ON DUPLICATE KEY UPDATE unique_key=unique_key')

TRANSIENT = {1205, 1213, 2002, 2003, 2006, 2013, 2055}   # lock timeout, deadlock, lost connection
def native(v):
    if pd.isna(v): return None
    if isinstance(v, pd.Timestamp): return v.to_pydatetime()
    return v.item() if isinstance(v, np.generic) else v

def insert_batch(rows):
    for attempt in range(3):
        try:
            with connect() as cn:
                with cn.cursor() as cur:
                    cur.executemany(insert, rows)
                cn.commit()
            return
        except mysql.connector.Error as e:
            if e.errno not in TRANSIENT or attempt == 2:
                raise
            time.sleep(2 ** attempt)

report = {'run_id': run, 'stage': stage, 'cleaned_rows': len(df), 'published': False}
try:
    with connect() as cn, cn.cursor() as cur:
        cur.execute(create)

    for start in range(0, len(df), BATCH):
        chunk = df.iloc[start:start + BATCH]
        insert_batch([tuple(native(v) for v in row) for row in chunk.itertuples(index=False, name=None)])
        if start % 10000 == 0:
            print('Loaded:', min(start + BATCH, len(df)))

    # Full read-back comparison
    with connect() as cn, cn.cursor() as cur:
        cur.execute(f'SELECT {quoted} FROM `{stage}` ORDER BY unique_key')
        loaded = pd.DataFrame(cur.fetchall(), columns=cols)
    for c in dates:
        loaded[c] = pd.to_datetime(loaded[c])
    # Normalize connector nulls and nullable extension dtypes before comparison.
    for c in texts:
        loaded[c] = loaded[c].astype('string')
    for c in ints:
        loaded[c] = pd.to_numeric(loaded[c]).astype('Int64')
    pd.testing.assert_frame_equal(df.sort_values('unique_key').reset_index(drop=True), loaded,
                                  check_dtype=False, check_exact=False, atol=1e-8, rtol=1e-10)

    # Source -> rejected -> cleaned -> staged reconciliation
    log = pd.read_csv(data / 'cleaning_validation_log.csv').set_index('Item')['Value']
    raw = int(log['Source (raw) rows loaded'])
    rejected = int(log['Duplicate unique_key rows rejected (saved to rejected_records.csv)'])
    extracted = int(json.loads((data / 'extraction_metadata.json').read_text(encoding='utf-8'))['actual_records'])
    must(extracted == raw and raw - rejected == len(loaded), 'Row reconciliation failed')
    report.update(raw_rows=raw, rejected_rows=rejected, staged_rows=len(loaded), full_roundtrip_passed=True,
                  invalid_date_rows=int(df.invalid_date_flag.sum()),
                  coordinate_issue_rows=int(df.coordinate_quality_flag.sum()))

    # Publish
    with connect() as cn, cn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s AND table_name=%s',
                    (DB, TABLE))
        exists = bool(cur.fetchone()[0])
        cur.execute(f'RENAME TABLE `{TABLE}` TO `{backup}`, `{stage}` TO `{TABLE}`' if exists
                    else f'RENAME TABLE `{stage}` TO `{TABLE}`')
        cur.execute(f'SELECT COUNT(*) FROM `{TABLE}`')
        report.update(published=True, backup_table=backup if exists else None, published_rows=cur.fetchone()[0])
    display(pd.DataFrame([report]))
    display(loaded.head())          # sample records after loading
except Exception as e:
    report['failure_type'] = type(e).__name__
    print('Stopped. Inspect the staging table and load report. Published:', report['published'])
    raise
finally:
    (out / f'load_validation_{run}.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

START_DATE = END_DATE = BOROUGH = COMPLAINT_TYPE = None      # optional filters
MIN_REQUESTS, MIN_MEDIAN_HOURS = 100, 24                      # task 15 thresholds

where, params = [], []
for value, predicate in [(START_DATE, 'created_date >= %s'), (END_DATE, 'created_date < %s'),
                         (BOROUGH, 'borough = %s'), (COMPLAINT_TYPE, 'complaint_type = %s')]:
    if value is not None:
        where.append(predicate); params.append(value)
base = 'SELECT * FROM service_requests' + (' WHERE ' + ' AND '.join(where) if where else '')

MEDIAN = 'AVG(CASE WHEN rn IN (FLOOR((n+1)/2),FLOOR((n+2)/2)) THEN resolution_hours END)'

def quantile(q):
    p = f'(n-1)*{q}'
    return (f'SUM(CASE WHEN rn=FLOOR({p})+1 THEN resolution_hours*(1-({p}-FLOOR({p}))) '
            f'WHEN rn=FLOOR({p})+2 THEN resolution_hours*({p}-FLOOR({p})) END)')

def median_by(group):
    ranked = (f'SELECT {group},resolution_hours,ROW_NUMBER() OVER (PARTITION BY {group} ORDER BY resolution_hours) rn,'
              f'COUNT(*) OVER (PARTITION BY {group}) n FROM valid')
    return (f'SELECT {group},COUNT(*) valid_n,AVG(resolution_hours) mean_hours,{MEDIAN} median_hours '
            f'FROM ({ranked}) r GROUP BY {group}')

prefix = ('WITH filtered AS (' + base + '), '
          'valid AS (SELECT * FROM filtered WHERE created_date IS NOT NULL AND closed_date >= created_date AND resolution_hours >= 0), '
          'ranked AS (SELECT resolution_hours,ROW_NUMBER() OVER (ORDER BY resolution_hours) rn,COUNT(*) OVER () n FROM valid), '
          f'fences AS (SELECT {quantile(0.25)} q1,{quantile(0.75)} q3 FROM ranked) ')

# name: (analyst question, SQL)
Q = {
 '01_distinct_volume': ('What is the total distinct request volume?',
    'SELECT COUNT(DISTINCT unique_key) total_requests FROM filtered'),
 '02_top_complaints': ('Which 10 complaint categories are most frequent?',
    'SELECT complaint_type,COUNT(*) request_count FROM filtered GROUP BY complaint_type ORDER BY request_count DESC,complaint_type LIMIT 10'),
 '03_agency_workload': ('How is workload distributed across agencies?',
    'SELECT agency,COUNT(*) request_count,100.0*COUNT(*)/SUM(COUNT(*)) OVER () share_pct FROM filtered GROUP BY agency ORDER BY request_count DESC'),
 '04_borough_volume': ('How does request volume vary by borough?',
    'SELECT borough,COUNT(*) request_count FROM filtered GROUP BY borough ORDER BY request_count DESC'),
 '05_monthly_trend': ('How does request volume change by month?',
    'SELECT YEAR(created_date) year,MONTH(created_date) month,COUNT(*) request_count FROM filtered WHERE created_date IS NOT NULL GROUP BY YEAR(created_date),MONTH(created_date) ORDER BY year,month'),
 '06_weekday_hour': ('When (weekday and hour) is demand highest?',
    'SELECT WEEKDAY(created_date) weekday_mon0,HOUR(created_date) hour,COUNT(*) request_count FROM filtered WHERE created_date IS NOT NULL GROUP BY WEEKDAY(created_date),HOUR(created_date) ORDER BY weekday_mon0,hour'),
 '07_status_distribution': ('How are recorded statuses distributed?',
    'SELECT status,COUNT(*) request_count FROM filtered GROUP BY status ORDER BY request_count DESC'),
 '08_resolution_statistics': ('What are the descriptive statistics of valid resolution durations?',
    f'SELECT COUNT(*) valid_n,MIN(resolution_hours) min_hours,MAX(resolution_hours) max_hours,AVG(resolution_hours) mean_hours,'
    f'STDDEV_SAMP(resolution_hours) sample_std,VAR_SAMP(resolution_hours) sample_variance,{MEDIAN} median_hours FROM ranked'),
 '09_category_median': ('What is the median resolution duration by complaint category?',
    median_by('complaint_type') + ' ORDER BY median_hours DESC'),
 '10_agency_median': ('What is the median resolution duration by agency?',
    median_by('agency') + ' ORDER BY median_hours DESC'),
 '11_iqr_outliers': ('Which durations fall outside the 1.5 x IQR fences?',
    'SELECT COUNT(*) valid_n,MAX(q1) q1_hours,MAX(q3) q3_hours,MAX(q1-1.5*(q3-q1)) lower_fence,MAX(q3+1.5*(q3-q1)) upper_fence,'
    'SUM(resolution_hours<q1-1.5*(q3-q1) OR resolution_hours>q3+1.5*(q3-q1)) outlier_n FROM valid CROSS JOIN fences'),
 '12_duration_distribution': ('What is the shape (skewness) of the duration distribution?',
    'SELECT unique_key,resolution_hours FROM valid ORDER BY unique_key'),
 '13_geographic_concentration': ('Where are complaints geographically concentrated (usable coordinates)?',
    'SELECT ROUND(latitude,2) latitude_cell,ROUND(longitude,2) longitude_cell,COUNT(*) request_count,'
    'SUM(latitude_imputed=1 OR longitude_imputed=1) imputed_n FROM filtered '
    'WHERE coordinate_quality_flag=0 AND latitude IS NOT NULL AND longitude IS NOT NULL '
    'GROUP BY ROUND(latitude,2),ROUND(longitude,2) ORDER BY request_count DESC'),
 '14_closure_rate': ('How do recorded closure rates compare across boroughs?',
    'SELECT borough,COUNT(*) request_count,SUM(is_closed) recorded_closed,100.0*SUM(is_closed)/COUNT(*) closure_pct FROM filtered GROUP BY borough ORDER BY closure_pct DESC'),
 '15_high_volume_slow_categories': ('Which categories have both high volume and long median duration?',
    'SELECT v.complaint_type,v.request_count,m.valid_n,m.median_hours '
    'FROM (SELECT complaint_type,COUNT(*) request_count FROM filtered GROUP BY complaint_type) v '
    f'JOIN ({median_by("complaint_type")}) m ON v.complaint_type <=> m.complaint_type '
    'WHERE v.request_count >= %s AND m.median_hours >= %s ORDER BY v.request_count DESC,m.median_hours DESC'),
}

results = {}
with connect() as cn:
    cn.start_transaction(consistent_snapshot=True, isolation_level='REPEATABLE READ')   # one consistent snapshot
    with cn.cursor() as cur:
        cur.execute(prefix + 'SELECT COUNT(*),SUM(created_date IS NOT NULL) FROM filtered', tuple(params))
        filtered_n, dated_n = (int(x or 0) for x in cur.fetchone())
        for name, (question, sql) in Q.items():
            extra = (MIN_REQUESTS, MIN_MEDIAN_HOURS) if name.startswith('15') else ()
            cur.execute(prefix + sql, tuple(params) + extra)
            results[name] = pd.DataFrame(cur.fetchall(), columns=[c[0] for c in cur.description])
            results[name].to_csv(out / f'{name}.csv', index=False)
            (out / f'{name}.sql').write_text(prefix + sql + ';', encoding='utf-8')
    cn.rollback()

valid_n = int(results['08_resolution_statistics'].valid_n.iloc[0])
print(f'Filtered n: {filtered_n} | dated n: {dated_n} | valid duration n: {valid_n}')
(out / 'analysis_filters.json').write_text(json.dumps(dict(
    start=START_DATE, end_exclusive=END_DATE, borough=BOROUGH, complaint_type=COMPLAINT_TYPE,
    minimum_requests=MIN_REQUESTS, minimum_median_hours=MIN_MEDIAN_HOURS, filtered_n=filtered_n), indent=2),
    encoding='utf-8')

NEEDS_VALID = {'08', '09', '10', '11', '12', '15'}      # tasks based on valid durations
evidence = []
for name, t in results.items():
    kind = name[:2]
    display(Markdown('### ' + name.replace('_', ' '))); display(t.head(20))

    if t.empty or (kind in NEEDS_VALID and valid_n == 0):
        print('No matching records. Widen filters or review thresholds.')
        chart = 'none'
    else:
        fig, ax = plt.subplots(figsize=(10, 4))
        if kind == '12':
            v = t.resolution_hours.astype(float)
            ax.hist(v, bins=50, edgecolor='white')
            ax.axvline(v.mean(), color='red', label='Mean'); ax.axvline(v.median(), color='green', label='Median')
            ax.legend(); ax.set(xlabel='Resolution hours', ylabel='Requests')
            print('Valid sample:', len(v), '| sample skewness:', round(v.skew(), 3))
        elif kind == '11':
            d = results['12_duration_distribution'].resolution_hours.astype(float)
            ax.boxplot(d, vert=False, whis=1.5)
            ax.axvline(float(t.upper_fence.iloc[0]), linestyle='--', label='Upper fence'); ax.legend()
            ax.set(xlabel='Resolution hours')
        elif kind == '08':
            s = t[['mean_hours', 'median_hours', 'sample_std']].iloc[0].astype(float)
            ax.bar(s.index, s.values); ax.set_ylabel('Hours')
        elif kind == '06':
            grid = (t.pivot(index='weekday_mon0', columns='hour', values='request_count')
                      .reindex(index=range(7), columns=range(24)).fillna(0).astype(float))
            im = ax.imshow(grid, aspect='auto'); fig.colorbar(im, ax=ax, label='Requests')
            ax.set(xlabel='Hour', ylabel='Weekday (Monday=0)')
        elif kind == '13':
            n = t.request_count.astype(float)
            im = ax.scatter(t.longitude_cell.astype(float), t.latitude_cell.astype(float), s=np.sqrt(n) * 5, c=n)
            fig.colorbar(im, ax=ax, label='Requests'); ax.set(xlabel='Longitude', ylabel='Latitude')
            print('Usable-coordinate sample:', int(n.sum()), '| imputed-coordinate sample:', int(t.imputed_n.astype(float).sum()))
        elif kind == '05':
            ax.plot(t.year.astype(str) + '-' + t.month.astype(str).str.zfill(2), t.request_count.astype(float), marker='o')
            ax.set_ylabel('Requests'); ax.tick_params(axis='x', rotation=45)
        else:
            metric = next(c for c in ['median_hours', 'closure_pct', 'request_count', 'total_requests'] if c in t)
            top = t.head(15)
            labels = top.iloc[:, 0].fillna('(missing)').astype(str) if top.columns[0] != metric else ['total']
            ax.barh(labels, pd.to_numeric(top[metric]).fillna(0)); ax.invert_yaxis(); ax.set_xlabel(metric)
        ax.set_title(name.replace('_', ' '))
        fig.tight_layout(); fig.savefig(out / f'{name}.png', dpi=160, bbox_inches='tight'); plt.show(); plt.close(fig)
        chart = f'{name}.png'

    sample = (int(t.request_count.astype(float).sum()) if kind == '13' and not t.empty
              else valid_n if kind in NEEDS_VALID else dated_n if kind in {'05', '06'} else filtered_n)
    evidence.append({'task': name, 'question': Q[name][0], 'query_file': f'{name}.sql', 'sample_size': sample,
                     'visualization': chart, 'observed_pattern': '', 'cautious_interpretation': ''})

pd.DataFrame(evidence).to_csv(out / 'analyst_evidence.csv', index=False)
print('Saved SQL, results, charts and the evidence table to', out)
