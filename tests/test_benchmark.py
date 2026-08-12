import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / 'benchmark' / 'scripts'

CHECKSUM = 'a' * 64

# A minimal design that really is pre-registered: no placeholders, every row
# frozen, and inapplicable fields declared explicitly.
FROZEN_DESIGN = {
    'datasets.tsv': (
        'dataset_id\tkind\tsource_url\taccession\tsha256\tlicense\tpreservation_context\t'
        'blank_included\tpartition\tstatus\tnotes\n'
        f'sim-low-damage\tsimulated\thttps://example.org/sim\tnot-applicable\t{CHECKSUM}\tCC0\t'
        'in_silico\tfalse\tdevelopment\tfrozen\tgargammel 1.1.4 seed 7\n'
        f'empirical-context-a\tempirical\thttps://example.org/ena\tSRR0000001\t{CHECKSUM}\tCC0\t'
        'permafrost\ttrue\ttest\tfrozen\tExtraction blank included\n'
    ),
    'scenarios.tsv': (
        'scenario_id\tdamage_model\tmean_fragment_length_bp\tcoverage_x\tendogenous_fraction\t'
        'modern_contamination_fraction\tcommunity_complexity\treplicates\tpartition\tstatus\n'
        'no-damage\tC0=0.00,G0=0.00\t75\t5\t0.10\t0.10\tmedium\t10\tdevelopment\tfrozen\n'
        'high-damage\tC0=0.20,G0=0.20\t45\t5\t0.10\t0.10\tmedium\t10\ttest\tfrozen\n'
    ),
    'methods.tsv': (
        'method\tworkflow_version\tcontainer_digest\tdatabase_manifest_sha256\tthreads\t'
        'memory_gb\tcache_policy\tstatus\n'
        f'appam-all-contigs\t2026.1\tnot-applicable\t{CHECKSUM}\t16\t64\tcold\tfrozen\n'
        f'appam-damage-filtered\t2026.1\tnot-applicable\t{CHECKSUM}\t16\t64\tcold\tfrozen\n'
    ),
}


def write_frozen_design(design_dir: Path) -> Path:
    design_dir.mkdir(parents=True, exist_ok=True)
    for name, content in FROZEN_DESIGN.items():
        (design_dir / name).write_text(content, encoding='utf-8')
    return design_dir


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

    def test_repository_design_is_template_only_until_pre_registered(self):
        validator = load_module('validate_observations')
        design = validator.load_design(REPO_ROOT / 'benchmark' / 'design')
        self.assertFalse(design['frozen'])
        self.assertEqual(validator.design_record(design), {'frozen': False, 'reason': design['reason']})

    def test_copying_the_shipped_templates_is_not_pre_registration(self):
        validator = load_module('validate_observations')
        design_source = REPO_ROOT / 'benchmark' / 'design'
        with tempfile.TemporaryDirectory() as tmpdir:
            design_dir = Path(tmpdir) / 'design'
            design_dir.mkdir()
            for name in ('datasets', 'scenarios', 'methods'):
                (design_dir / f'{name}.tsv').write_text(
                    (design_source / f'{name}.template.tsv').read_text(encoding='utf-8'),
                    encoding='utf-8',
                )
            with self.assertRaisesRegex(ValueError, 'status'):
                validator.load_design(design_dir)

    def test_frozen_design_rejects_duplicates_and_unresolved_fields(self):
        validator = load_module('validate_observations')
        with tempfile.TemporaryDirectory() as tmpdir:
            design_dir = write_frozen_design(Path(tmpdir) / 'design')
            self.assertTrue(validator.load_design(design_dir)['frozen'])

            duplicated = design_dir / 'methods.tsv'
            duplicated.write_text(
                duplicated.read_text(encoding='utf-8')
                + 'appam-all-contigs\t2026.1\tnot-applicable\t' + ('a' * 64) + '\t16\t64\tcold\tfrozen\n',
                encoding='utf-8',
            )
            with self.assertRaisesRegex(ValueError, 'duplicate method: appam-all-contigs'):
                validator.load_design(design_dir)

            write_frozen_design(design_dir)
            unresolved = design_dir / 'datasets.tsv'
            unresolved.write_text(
                unresolved.read_text(encoding='utf-8').replace('SRR0000001', 'TBD'),
                encoding='utf-8',
            )
            with self.assertRaisesRegex(ValueError, 'unresolved field'):
                validator.load_design(design_dir)

    def test_frozen_design_identifies_itself_by_file_digest(self):
        validator = load_module('validate_observations')
        with tempfile.TemporaryDirectory() as tmpdir:
            design_dir = write_frozen_design(Path(tmpdir) / 'design')
            record = validator.design_record(validator.load_design(design_dir))
            self.assertEqual(
                record['declared_counts'],
                {'dataset_id': 2, 'method': 2, 'scenario_id': 2},
            )
            self.assertEqual(
                sorted(record['files']),
                ['datasets.tsv', 'methods.tsv', 'scenarios.tsv'],
            )
            for name, entry in record['files'].items():
                self.assertEqual(
                    entry['sha256'],
                    hashlib.sha256((design_dir / name).read_bytes()).hexdigest(),
                )
            # The digest is stable across reloads and changes when a table changes.
            self.assertEqual(record, validator.design_record(validator.load_design(design_dir)))
            edited = design_dir / 'scenarios.tsv'
            edited.write_text(edited.read_text(encoding='utf-8').replace('\t5\t', '\t6\t', 1), encoding='utf-8')
            self.assertNotEqual(
                validator.design_record(validator.load_design(design_dir))['files']['scenarios.tsv']['sha256'],
                record['files']['scenarios.tsv']['sha256'],
            )

    def test_frozen_design_rejects_undeclared_identifiers(self):
        validator = load_module('validate_observations')
        with tempfile.TemporaryDirectory() as tmpdir:
            design = validator.load_design(write_frozen_design(Path(tmpdir) / 'design'))
            observations = Path(tmpdir) / 'observations.tsv'
            header = 'dataset_id\tscenario_id\tmethod\treplicate\tmetric\tvalue\tunit\n'
            observations.write_text(
                header + 'sim-low-damage\tno-damage\tappam-all-contigs\t1\tmag_recall\t0.5\tfraction\n',
                encoding='utf-8',
            )
            self.assertEqual(len(validator.validate(observations, design=design)), 1)

            observations.write_text(
                header + 'undeclared-dataset\tno-damage\tappam-all-contigs\t1\tmag_recall\t0.5\tfraction\n',
                encoding='utf-8',
            )
            with self.assertRaisesRegex(ValueError, 'not pre-registered in datasets.tsv'):
                validator.validate(observations, design=design)

    def test_analysis_records_the_exact_pre_registration_it_used(self):
        validator = load_module('validate_observations')
        import sys
        sys.modules['validate_observations'] = validator
        analyzer = load_module('analyze_observations')
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            design_dir = write_frozen_design(tmp / 'design')
            observations = tmp / 'observations.tsv'
            observations.write_text(
                'dataset_id\tscenario_id\tmethod\treplicate\tmetric\tvalue\tunit\n'
                'sim-low-damage\tno-damage\tappam-all-contigs\t1\tmag_recall\t0.50\tfraction\n'
                'sim-low-damage\tno-damage\tappam-damage-filtered\t1\tmag_recall\t0.48\tfraction\n',
                encoding='utf-8',
            )
            summary_json = tmp / 'summary.json'
            argv = [
                'analyze_observations.py', str(observations),
                '--baseline', 'appam-all-contigs',
                '--iterations', '100', '--seed', '7',
                '--design-dir', str(design_dir), '--require-design',
                '--summary', str(tmp / 'summary.tsv'),
                '--paired', str(tmp / 'paired.tsv'),
                '--json', str(summary_json),
            ]
            with mock.patch.object(sys, 'argv', argv):
                analyzer.main()

            payload = json.loads(summary_json.read_text(encoding='utf-8'))
            self.assertTrue(payload['design']['frozen'])
            self.assertEqual(payload['observations']['row_count'], 2)
            self.assertEqual(
                payload['observations']['sha256'],
                hashlib.sha256(observations.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                {name: entry['sha256'] for name, entry in payload['design']['files'].items()},
                {
                    name: hashlib.sha256((design_dir / name).read_bytes()).hexdigest()
                    for name in FROZEN_DESIGN
                },
            )

    def test_require_design_blocks_unregistered_analysis(self):
        validator = load_module('validate_observations')
        reported = io.StringIO()
        with contextlib.redirect_stderr(reported):
            exit_code = validator.main([
                'validate_observations.py',
                str(REPO_ROOT / 'benchmark' / 'data' / 'observations.example.tsv'),
                '--design-dir',
                str(REPO_ROOT / 'benchmark' / 'design'),
                '--require-design',
            ])
        self.assertEqual(exit_code, 1)
        self.assertIn('design is not pre-registered', reported.getvalue())

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
