"""Run with python tests/test_dashboard.py; no live services required."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dashboard.data import filter_data, kpis, prepare, usable_coordinates
from streamlit.testing.v1 import AppTest


def fixture():
    return pd.DataFrame({
        'unique_key': ['1', '2', '3', '4', '5'],
        'created_date': ['2026-01-01', '2026-01-01', '2026-01-01', '2026-01-02', None],
        'closed_date': ['2026-01-04', '2026-01-05', None, '2026-01-01', None],
        'agency': ['DOT']*5, 'complaint_type': ['Street', 'Noise', 'Street', 'Noise', 'Street'],
        'borough': ['BROOKLYN', 'QUEENS', 'BROOKLYN', 'QUEENS', 'BROOKLYN'],
        'status': ['OPEN']*5, 'latitude': [40.7]*5, 'longitude': [-73.9]*5,
        'latitude_imputed': [False, True, False, False, False],
    })


class DashboardTests(unittest.TestCase):
    def test_kpis_and_filters(self):
        df = prepare(fixture())
        values = kpis(df)
        self.assertEqual(values, dict(total=5, closure=60., open=2, median=84., over72=50., valid_n=2))
        self.assertTrue(df.status.eq('OPEN').all())
        self.assertEqual(len(usable_coordinates(df)), 4)
        subset = filter_data(df, ('2026-01-01', '2026-01-01'), ['BROOKLYN'], ['Street'])
        self.assertEqual(list(subset.unique_key), ['1', '3'])
        self.assertEqual(len(filter_data(df, boroughs=[])), 0)
        self.assertIsNone(kpis(df.iloc[0:0])['median'])
        self.assertIsNone(kpis(df.iloc[0:0])['closure'])
        self.assertEqual(kpis(df.iloc[[2]])['open'], 1)
        self.assertIsNone(kpis(df.iloc[[2]])['over72'])

    def test_duplicate_rejection(self):
        frame = fixture()
        frame.loc[1, 'unique_key'] = '1'
        with self.assertRaises(ValueError):
            prepare(frame)

    def test_app_views_filters_and_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'cleaned.csv'
            fixture().to_csv(path, index=False)
            old = os.environ.get('URBANPULSE_DATA')
            os.environ['URBANPULSE_DATA'] = str(path)
            try:
                app = AppTest.from_file(str(ROOT / 'streamlit_app.py'), default_timeout=30).run()
                self.assertFalse(app.exception)
                self.assertEqual([m.value for m in app.metric], ['5', '60.0%', '2', '84.00 h', '50.0%'])
                for page, tasks in {
                    'Demand & workload': ['Top complaints', 'Agency workload', 'Borough volume', 'Monthly trend', 'Weekday and hour', 'Recorded statuses'],
                    'Resolution & outliers': ['Descriptive statistics', 'Median by category', 'Median by agency', 'IQR outliers', 'Distribution and skewness', 'High volume and slow categories'],
                    'Geography & closure': [], 'Records & quality': [],
                }.items():
                    app.radio[0].set_value(page).run()
                    self.assertFalse(app.exception, page)
                    for task in tasks:
                        app.selectbox(key='demand_task' if page == 'Demand & workload' else 'resolution_task').set_value(task).run()
                        self.assertFalse(app.exception, task)
                app.multiselect[0].set_value([]).run()
                self.assertFalse(app.exception)
                self.assertTrue(any('No requests match' in item.value for item in app.info))
                app.multiselect[0].set_value(['BROOKLYN']).run()
                app.checkbox[0].check().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.metric[0].value, '2')
                app.text_input[0].set_value(str(Path(tmp) / 'missing.csv')).run()
                self.assertFalse(app.exception)
                self.assertTrue(app.info)
                # A failed database source must render an error, never a traceback or credentials.
                host = os.environ.pop('MYSQL_HOST', None)
                try:
                    app.selectbox(key='source').set_value('MySQL').run()
                    self.assertFalse(app.exception)
                    self.assertTrue(app.error)
                finally:
                    if host is not None:
                        os.environ['MYSQL_HOST'] = host
            finally:
                if old is None:
                    del os.environ['URBANPULSE_DATA']
                else:
                    os.environ['URBANPULSE_DATA'] = old


if __name__ == '__main__':
    unittest.main()
