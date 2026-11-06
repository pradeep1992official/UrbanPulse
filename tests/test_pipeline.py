import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import nbformat
import pandas as pd

root = Path(__file__).resolve().parents[1]
for path in (root / 'notebooks').glob('*.ipynb'):
    nb = nbformat.read(path, as_version=4)
    nbformat.validate(nb)
    script = root / 'scripts' / (path.stem + '.py')
    ast.parse(script.read_text(encoding='utf-8'))
    assert '\n\n'.join(c.source for c in nb.cells if c.cell_type == 'code') in script.read_text(encoding='utf-8')

with tempfile.TemporaryDirectory(prefix='urbanpulse_check_') as tmp:
    work = Path(tmp)
    (work / 'data/raw').mkdir(parents=True)
    fields = ['unique_key', 'created_date', 'closed_date', 'due_date', 'agency', 'complaint_type',
              'borough', 'status', 'latitude', 'longitude', 'agency_name', 'descriptor',
              'location_type', 'incident_zip', 'city', 'resolution_description']
    rows = []
    for i in range(6):
        row = {key: None for key in fields}
        row.update(unique_key=str(i+1), created_date='2026-01-01T00:00:00',
                   closed_date=f'2026-01-01T0{i+1}:00:00', agency=' dot ', complaint_type='street',
                   borough='brooklyn', status='in progress', latitude=40.7, longitude=-73.9)
        rows.append(row)
    rows[1]['closed_date'] = '2025-12-31T00:00:00'
    rows[2]['latitude'] = None
    rows[3]['created_date'] = 'bad-date'
    rows[4]['latitude'] = 120
    rows.append(rows[0].copy())
    raw = pd.DataFrame(rows, columns=fields)
    source = work / 'data/raw/nyc_100k_raw.csv'
    raw.to_csv(source, index=False)
    env = dict(os.environ, URBANPULSE_ROOT=tmp, MPLBACKEND='Agg', PYTHONIOENCODING='utf-8')
    for name in ['02_data_preparation', '03_statistics']:
        proc = subprocess.run([sys.executable, str(root / 'scripts' / (name + '.py'))], env=env,
                              cwd=root, capture_output=True, text=True, encoding='utf-8')
        if proc.returncode:
            raise RuntimeError(proc.stdout + proc.stderr)
    cleaned = pd.read_csv(work / 'data/cleaned/nyc_cleaned.csv')
    assert len(cleaned) == 6 and len(cleaned.columns) == 41
    assert cleaned.status.eq('IN PROGRESS').all()
    assert cleaned.incident_zip.isna().all() and cleaned.city.isna().all()
    assert cleaned.loc[2, 'latitude'] != cleaned.loc[2, 'latitude']
    assert cleaned.loc[1, 'closure_before_creation']
    assert cleaned.loc[1, 'resolution_hours'] != cleaned.loc[1, 'resolution_hours']
    assert cleaned.loc[3, 'created_date_parse_error']
    assert cleaned.loc[4, 'coordinate_quality_flag']
    assert (work / 'data/statistics/resolution_distribution.png').is_file()
    # Execute the real MySQL schema validation without connecting to a service.
    nb = nbformat.read(root / 'notebooks/04_mysql_sql_analytics.ipynb', as_version=4)
    scope = {}
    previous = os.environ.get('URBANPULSE_ROOT')
    os.environ['URBANPULSE_ROOT'] = tmp
    try:
        exec(nb.cells[2].source, scope)
        exec(nb.cells[4].source, scope)
    finally:
        if previous is None:
            del os.environ['URBANPULSE_ROOT']
        else:
            os.environ['URBANPULSE_ROOT'] = previous
    # Export actual query definitions without running the load or SQL.
    definition = nb.cells[10].source.split('results = {}')[0]
    sql_scope = {}
    exec(definition, sql_scope)
    assert len(sql_scope['Q']) == 15
    for name, (question, query) in sql_scope['Q'].items():
        (root / 'sql' / (name + '.sql')).write_text(
            '-- ' + question + '\n-- Bind %s parameters via mysql.connector.\n' + sql_scope['prefix'] + query + ';\n', encoding='utf-8')
    # Missing identifiers must fail before writing a new cleaned file.
    raw.loc[0, 'unique_key'] = None
    raw.to_csv(source, index=False)
    proc = subprocess.run([sys.executable, str(root / 'scripts/02_data_preparation.py')], env=env,
                          cwd=root, capture_output=True, text=True, encoding='utf-8')
    assert proc.returncode != 0 and 'Missing request identifiers' in proc.stderr

print('PASS: 4 notebook schemas and script parity; cleaning edge cases; statistics artifacts; 41-column MySQL validation; 15 SQL exports; missing-ID failure.')
