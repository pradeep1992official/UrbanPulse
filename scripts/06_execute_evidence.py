"""Execute current notebooks with saved outputs and a dated, hashed run manifest.

Run from the repository root. MySQL is run only with --mysql, after configuring
its environment variables. The source notebooks are updated with actual outputs.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from zoneinfo import ZoneInfo

import nbformat
from nbclient import NotebookClient
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env', override=False)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mysql', action='store_true', help='Execute notebook 04 against the configured service')
    parser.add_argument('--skip-extraction', action='store_true', help='Use an already preserved canonical snapshot')
    parser.add_argument('--only-mysql', action='store_true', help='Execute only notebook 04; requires --mysql')
    parser.add_argument('--local-source', type=Path, help='Project an existing raw snapshot into the 16-field contract; records import provenance, not API success')
    args = parser.parse_args()
    if args.only_mysql and not args.mysql:
        parser.error('--only-mysql requires --mysql')
    now = lambda: datetime.now(ZoneInfo('Asia/Kolkata')).isoformat()
    run = datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%Y%m%d_%H%M%S')
    out = ROOT / 'reports/execution' / run
    out.mkdir(parents=True)
    manifest = dict(started_at=now(), python=platform.python_version(), platform=platform.platform(),
                    mysql_requested=args.mysql, notebooks=[], checks=[], artifacts=[])
    if args.local_source:
        import pandas as pd
        source=args.local_source.resolve()
        raw=pd.read_csv(source,dtype='string',low_memory=False)
        fields=['unique_key','created_date','closed_date','due_date','agency','complaint_type','borough','status',
                'latitude','longitude','agency_name','descriptor','location_type','incident_zip','city','resolution_description']
        absent=set(fields)-set(raw.columns)
        if absent:
            raise ValueError('Local source missing columns: '+', '.join(sorted(absent)))
        destination=ROOT/'data/raw/nyc_100k_raw.csv'
        destination.parent.mkdir(parents=True,exist_ok=True)
        raw[fields].to_csv(destination,index=False)
        metadata=dict(source_kind='local_raw_snapshot_import',source_file=source.relative_to(ROOT).as_posix() if source.is_relative_to(ROOT) else str(source),
                      source_sha256=digest(source),imported_at=now(),actual_records=len(raw),selected_fields=fields,
                      status='local_import_completed',original_extraction_time=None,original_api_parameters=None,
                      data_coverage_start=raw.created_date.min(),data_coverage_end=raw.created_date.max(),
                      limitations=['Existing raw snapshot; import is not a successful fresh API extraction.'])
        (ROOT/'data/extraction_metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
        manifest['local_import']=metadata
        args.skip_extraction=True
    freeze = subprocess.run([sys.executable, '-m', 'pip', 'freeze'], capture_output=True, text=True)
    (out/'environment.txt').write_text(freeze.stdout, encoding='utf-8')
    os.environ['URBANPULSE_ROOT'] = str(ROOT)
    os.environ['MPLBACKEND'] = 'Agg'
    # Ensure the kernel uses this same interpreter, without registering a global kernel.
    from jupyter_client.kernelspec import KernelSpecManager
    import tempfile
    with tempfile.TemporaryDirectory(prefix='urbanpulse_kernel_') as tmp:
        spec = Path(tmp)/'urbanpulse'
        spec.mkdir()
        (spec/'kernel.json').write_text(json.dumps(dict(argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],
                                                       display_name='UrbanPulse verification',language='python')),encoding='utf-8')
        manager = KernelSpecManager(kernel_dirs=[tmp])
        pipeline_ok = True
        for path in sorted((ROOT/'notebooks').glob('*.ipynb')):
            if args.only_mysql and not path.name.startswith('04'):
                continue
            entry = dict(notebook=path.relative_to(ROOT).as_posix(), started_at=now(),
                         source_code_sha256=hashlib.sha256('\n\n'.join(c.source for c in nbformat.read(path,4).cells if c.cell_type=='code').encode()).hexdigest())
            if path.name.startswith('04') and not args.mysql:
                entry.update(status='not_executed',reason='MySQL not requested; requires configured environment and CA certificate')
            elif path.name.startswith('01') and args.skip_extraction:
                entry.update(status='not_executed',reason='Existing canonical snapshot explicitly selected')
            elif not pipeline_ok:
                entry.update(status='not_executed',reason='Upstream notebook failed; downstream execution withheld')
            else:
                print('Executing',path.name,flush=True)
                nb = nbformat.read(path,4)
                nb.metadata.pop('widgets',None)
                for cell in nb.cells:
                    if cell.cell_type=='code':
                        cell.outputs=[];cell.execution_count=None
                from jupyter_client import KernelManager
                class LocalKernelManager(KernelManager):
                    def __init__(self, **kwargs):
                        kwargs['kernel_spec_manager']=manager
                        super().__init__(**kwargs)
                client=NotebookClient(nb,timeout=900,kernel_name='urbanpulse',resources={'metadata':{'path':str(ROOT)}},
                                      kernel_manager_class=LocalKernelManager,
                                      on_cell_executed=lambda cell_index, **kwargs: print('Completed cell',cell_index,flush=True))
                try:
                    client.execute()
                    entry['status']='passed'
                except Exception as error:
                    entry.update(status='failed',error_type=type(error).__name__)
                    pipeline_ok=False
                finally:
                    if client.km is not None and client.km.has_kernel:
                        client.km.shutdown_kernel(now=True)
                    executed=out/path.name
                    nbformat.write(nb,executed)
                    if entry['status']=='passed':
                        nbformat.write(nb,path)
                    entry.update(executed_file=executed.relative_to(ROOT).as_posix(),ended_at=now(),sha256=digest(executed),
                                 executed_cells=sum(c.get('execution_count') is not None for c in nb.cells if c.cell_type=='code'))
            manifest['notebooks'].append(entry)
            (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
            print(path.name,entry['status'],flush=True)
    for name in ['test_pipeline.py','test_dashboard.py']:
        proc=subprocess.run([sys.executable,str(ROOT/'tests'/name)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',env=dict(os.environ,PYTHONIOENCODING='utf-8'))
        (out/(name+'.log')).write_text(proc.stdout+'\n'+proc.stderr,encoding='utf-8')
        manifest['checks'].append(dict(test=name,status='passed' if proc.returncode==0 else 'failed',exit_code=proc.returncode))
    for name in ['data/extraction_metadata.json','data/data_dictionary.csv','data/cleaning_validation_log.csv','data/cleaned/nyc_cleaned.csv']:
        path=ROOT/name
        if path.is_file():
            manifest['artifacts'].append(dict(path=name,bytes=path.stat().st_size,sha256=digest(path)))
            if path.suffix=='.json' or name.endswith(('data_dictionary.csv','cleaning_validation_log.csv')):
                (out/path.name).write_bytes(path.read_bytes())
    manifest['ended_at']=now()
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Evidence directory:',out,flush=True)
    if any(item['status']=='failed' for item in manifest['notebooks']+manifest['checks']):
        raise SystemExit(1)


if __name__=='__main__':
    main()
