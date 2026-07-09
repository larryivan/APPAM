import importlib.util
from pathlib import Path
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / 'benchmark' / 'scripts'


def load_module(name):
    path = SCRIPTS / f'{name}.py'
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BenchmarkTests(unittest.TestCase):
    def test_example_design_and_paired_analysis(self):
        validator = load_module('validate_observations')
        import sys
        sys.modules['validate_observations'] = validator
        analyzer = load_module('analyze_observations')
        rows = validator.validate(REPO_ROOT / 'benchmark' / 'data' / 'observations.example.tsv')
        summaries, differences = analyzer.analyze(rows, 'appam-all-contigs', 200, 7)
        self.assertEqual(len(summaries), 2)
        self.assertEqual(len(differences), 3)
        self.assertAlmostEqual(
            next(row['mean'] for row in summaries if row['method'] == 'appam-all-contigs'),
            0.71,
        )

    def test_duplicate_observation_is_rejected(self):
        validator = load_module('validate_observations')
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'observations.tsv'
            header = 'dataset_id\tscenario_id\tmethod\treplicate\tmetric\tvalue\tunit\n'
            row = 'D\tS\tM\t1\trecall\t0.5\tfraction\n'
            path.write_text(header + row + row, encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                validator.validate(path)

    def test_snakemake_runtime_metrics_are_collectable(self):
        collector = load_module('collect_runtime_metrics')
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'rule.tsv'
            path.write_text(
                's\th:m:s\tmax_rss\tmax_vms\tmax_uss\tmax_pss\tio_in\tio_out\tmean_load\tcpu_time\n'
                '12.5\t00:00:12\t256.0\t512.0\t200.0\t220.0\t1.0\t2.0\t80.0\t10.0\n',
                encoding='utf-8',
            )
            row = collector.read_benchmark(path)
            self.assertEqual(row['s'], '12.5')
            self.assertEqual(row['max_rss'], '256.0')


if __name__ == '__main__':
    unittest.main()
