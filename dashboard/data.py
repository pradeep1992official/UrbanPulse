"""Read-only sources and consistent analytical definitions."""
import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env', override=False)
REQUIRED = {'unique_key', 'created_date', 'closed_date', 'agency', 'complaint_type', 'borough', 'status'}


def prepare(frame):
    """Validate IDs, preserve recorded categories and derive durations from dates."""
    missing = REQUIRED - set(frame.columns)
    if missing:
        raise ValueError('Missing required columns: ' + ', '.join(sorted(missing)))
    df = frame.copy()
    df['unique_key'] = df.unique_key.astype('string').str.strip().replace('', pd.NA)
    if df.unique_key.isna().any() or df.unique_key.duplicated().any():
        raise ValueError('Request identifiers must be present and unique. Run data preparation first.')
    for col in ['created_date', 'closed_date']:
        df[col] = pd.to_datetime(df[col], errors='coerce', format='mixed')
        if df[col].dt.tz is not None:
            df[col] = df[col].dt.tz_convert('America/New_York').dt.tz_localize(None)
    for col in ['agency', 'complaint_type', 'borough', 'status']:
        df[col] = df[col].astype('string').str.strip().replace('', pd.NA).fillna('(missing)')
    df['is_closed'] = df.closed_date.notna()
    hours = (df.closed_date - df.created_date).dt.total_seconds() / 3600
    df['resolution_hours'] = hours.where(np.isfinite(hours) & hours.ge(0))
    for col in ['latitude', 'longitude']:
        df[col] = pd.to_numeric(df[col], errors='coerce') if col in df else np.nan
    return df


def read_csv(path):
    return prepare(pd.read_csv(path, dtype={'unique_key': 'string', 'incident_zip': 'string'}, low_memory=False))


def read_mysql():
    """Read only the published table; never expose connection exceptions to users."""
    import mysql.connector

    names = ['MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_SSL_CA']
    if any(not os.environ.get(name) for name in names):
        raise ValueError('Set MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD and MYSQL_SSL_CA before connecting.')
    ca = Path(os.environ['MYSQL_SSL_CA']).expanduser()
    if not ca.is_absolute():
        ca = ROOT / ca
    if not ca.is_file():
        raise ValueError('MYSQL_SSL_CA must point to an existing CA certificate file.')
    try:
        with mysql.connector.connect(
            host=os.environ['MYSQL_HOST'], port=int(os.environ.get('MYSQL_PORT', '3306')),
            user=os.environ['MYSQL_USER'], password=os.environ['MYSQL_PASSWORD'],
            database='urban_pulse_db', connection_timeout=15, ssl_ca=str(ca),
            ssl_verify_cert=True, ssl_verify_identity=True,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT * FROM service_requests')
                frame = pd.DataFrame(cursor.fetchall(), columns=[c[0] for c in cursor.description])
    except (mysql.connector.Error, ValueError, OSError):
        raise ValueError('Could not read MySQL. Check service availability, environment settings, certificate and SELECT permissions.') from None
    return prepare(frame)


def filter_data(df, dates=None, boroughs=None, complaints=None):
    mask = pd.Series(True, index=df.index)
    if dates is not None:
        start, end = dates
        mask &= df.created_date.ge(pd.Timestamp(start)) & df.created_date.lt(pd.Timestamp(end) + pd.Timedelta(days=1))
    if boroughs is not None:
        mask &= df.borough.isin(boroughs)
    if complaints is not None:
        mask &= df.complaint_type.isin(complaints)
    return df.loc[mask].copy()


def kpis(df):
    valid = df.resolution_hours.dropna()
    return dict(total=int(df.unique_key.nunique()),
                closure=float(df.is_closed.mean() * 100) if len(df) else None,
                open=int((~df.is_closed).sum()),
                median=float(valid.median()) if len(valid) else None,
                over72=float(valid.gt(72).mean() * 100) if len(valid) else None,
                valid_n=len(valid))


def counts(df, col):
    return df.groupby(col, dropna=False).size().rename('Requests').sort_values(ascending=False).reset_index()


def medians(df, col):
    return df.groupby(col, dropna=False).agg(
        Requests=('unique_key', 'size'), Valid_durations=('resolution_hours', 'count'),
        Median_hours=('resolution_hours', 'median'), Mean_hours=('resolution_hours', 'mean')
    ).sort_values('Median_hours', ascending=False).reset_index()


def usable_coordinates(df):
    mask = df.latitude.between(40.4, 41.0) & df.longitude.between(-74.3, -73.7)
    # Exclude imputed coordinates when provenance flags are available.
    for col in ['latitude_imputed', 'longitude_imputed', 'coordinate_quality_flag']:
        if col in df:
            flag = df[col].astype('string').str.lower()
            mask &= flag.isin(['false', '0', '0.0'])
    return df.loc[mask]
