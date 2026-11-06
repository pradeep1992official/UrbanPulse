"""Compare all 15 executed MySQL result files with independent pandas calculations."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.data import read_csv, usable_coordinates


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    data=ROOT/'data/mysql'
    df=read_csv(ROOT/'data/cleaned/nyc_cleaned.csv')
    valid=df.loc[df.resolution_hours.notna()].copy()
    v=valid.resolution_hours
    q1,q3=v.quantile([.25,.75]);lo=q1-1.5*(q3-q1);hi=q3+1.5*(q3-q1)
    def count(col):
        return df.groupby(col,dropna=False).size().rename('request_count').reset_index()
    def median(col):
        return valid.groupby(col,dropna=False).agg(valid_n=('resolution_hours','size'),
                mean_hours=('resolution_hours','mean'),median_hours=('resolution_hours','median')).reset_index()
    geo=usable_coordinates(df).copy()
    # MySQL ROUND uses half-away-from-zero for exact decimals; DOUBLE cells here
    # are compared against the actual rounded grid after checking all counts.
    geo['latitude_cell']=geo.latitude.round(2);geo['longitude_cell']=geo.longitude.round(2)
    geographic=geo.groupby(['latitude_cell','longitude_cell']).size().rename('request_count').reset_index()
    geographic['imputed_n']=0
    agencies=count('agency');agencies['share_pct']=agencies.request_count/len(df)*100
    monthly=df.groupby([df.created_date.dt.year.rename('year'),df.created_date.dt.month.rename('month')]).size().rename('request_count').reset_index()
    demand=df.groupby([df.created_date.dt.day_of_week.rename('weekday_mon0'),df.created_date.dt.hour.rename('hour')]).size().rename('request_count').reset_index()
    closure=df.groupby('borough',dropna=False).agg(request_count=('unique_key','size'),recorded_closed=('is_closed','sum')).reset_index()
    closure['closure_pct']=100*closure.recorded_closed/closure.request_count
    slow=count('complaint_type').merge(median('complaint_type'),on='complaint_type')
    slow=slow.loc[slow.request_count.ge(100)&slow.median_hours.ge(24),['complaint_type','request_count','valid_n','median_hours']]
    expected=[
        pd.DataFrame({'total_requests':[df.unique_key.nunique()]}),
        count('complaint_type').sort_values(['request_count','complaint_type'],ascending=[False,True]).head(10),
        agencies,count('borough'),monthly,demand,count('status'),
        pd.DataFrame([dict(valid_n=len(v),min_hours=v.min(),max_hours=v.max(),mean_hours=v.mean(),
                          sample_std=v.std(),sample_variance=v.var(),median_hours=v.median())]),
        median('complaint_type'),median('agency'),
        pd.DataFrame([dict(valid_n=len(v),q1_hours=q1,q3_hours=q3,lower_fence=lo,upper_fence=hi,
                          outlier_n=int((v.lt(lo)|v.gt(hi)).sum()))]),
        valid[['unique_key','resolution_hours']],geographic,closure,slow]
    keys=[[],['complaint_type'],['agency'],['borough'],['year','month'],['weekday_mon0','hour'],
          ['status'],[],['complaint_type'],['agency'],[],['unique_key'],['latitude_cell','longitude_cell'],
          ['borough'],['complaint_type']]
    checks=[]
    files=sorted(data.glob('[0-9][0-9]_*.csv'))
    if len(files)!=15:
        raise ValueError('Expected exactly 15 SQL result CSVs from a completed run')
    for path,want,key in zip(files,expected,keys):
        got=pd.read_csv(path,dtype={'unique_key':'string'})
        want=want[got.columns].copy()
        if key:
            got=got.sort_values(key).reset_index(drop=True)
            want=want.sort_values(key).reset_index(drop=True)
        if len(got)!=len(want):
            raise AssertionError(f'{path.stem}: row count differs ({len(got)} vs {len(want)})')
        error=0.
        for col in got.columns:
            if pd.api.types.is_numeric_dtype(want[col]):
                actual=pd.to_numeric(got[col],errors='raise').to_numpy(dtype=float)
                reference=want[col].to_numpy(dtype=float)
                # MySQL decimal division exports these percentages to 5 places.
                tolerance=5.1e-6 if col in ['closure_pct','share_pct'] else 1e-7
                if not np.allclose(actual,reference,rtol=1e-9,atol=tolerance,equal_nan=True):
                    raise AssertionError(f'{path.stem}: {col} differs')
                if len(actual):
                    error=max(error,float(np.nanmax(np.abs(actual-reference))))
            elif got[col].astype('string').fillna('(missing)').tolist()!=want[col].astype('string').fillna('(missing)').tolist():
                raise AssertionError(f'{path.stem}: {col} differs')
        checks.append(dict(task=path.stem,status='passed',result_rows=len(got),max_absolute_numeric_difference=error,
                           sql_result_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    report=dict(checked_at=datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),status='passed',
                source='data/cleaned/nyc_cleaned.csv',source_sha256=hashlib.sha256((ROOT/'data/cleaned/nyc_cleaned.csv').read_bytes()).hexdigest(),
                filtered_rows=len(df),valid_durations=len(valid),rtol=1e-9,atol=1e-7,
                percentage_atol=5.1e-6,percentage_note='SQL decimal division exports percentages to five decimal places',investigations=checks)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('PASS: all 15 MySQL results agree with independently calculated pandas results')


if __name__=='__main__':
    main()
