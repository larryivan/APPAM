import tempfile
import unittest
import hashlib
from pathlib import Path
from unittest import mock

from app import paths
from app.services import file_manager


class PlotTableTests(unittest.TestCase):
    def setUp(self):
        self.projects_dir = tempfile.TemporaryDirectory()
        self.projects_patch = mock.patch.object(paths, 'PROJECTS_ROOT', Path(self.projects_dir.name))
        self.projects_patch.start()
        self.project_dir = Path(self.projects_dir.name) / 'plot-project'
        self.project_dir.mkdir(parents=True)

    def tearDown(self):
        self.projects_patch.stop()
        self.projects_dir.cleanup()

    def test_reads_complete_utf8_table(self):
        table = self.project_dir / 'summary.tsv'
        table.write_text('sample\tvalue\nA\t1\nB\t2\n', encoding='utf-8')

        result = file_manager.read_plot_table('plot-project', 'summary.tsv')

        self.assertTrue(result['complete'])
        self.assertEqual(result['content'], 'sample\tvalue\nA\t1\nB\t2\n')
        self.assertEqual(result['line_count'], 3)
        self.assertEqual(
            result['sha256'],
            hashlib.sha256(table.read_bytes()).hexdigest(),
        )

    def test_rejects_oversized_table_instead_of_truncating(self):
        table = self.project_dir / 'summary.csv'
        table.write_text('sample,value\nA,123456\n', encoding='utf-8')

        with mock.patch.dict('os.environ', {'APPAM_MAX_PLOT_TABLE_BYTES': '12'}):
            with self.assertRaises(file_manager.PlotTableTooLargeError):
                file_manager.read_plot_table('plot-project', 'summary.csv')

    def test_rejects_non_table_file(self):
        figure = self.project_dir / 'figure.png'
        figure.write_bytes(b'not really a png')

        with self.assertRaisesRegex(ValueError, 'CSV or tab-separated'):
            file_manager.read_plot_table('plot-project', 'figure.png')


if __name__ == '__main__':
    unittest.main()
