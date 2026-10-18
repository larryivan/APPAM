import os
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault('FLASK_SECRET_KEY', 'appam-results-test-secret')
os.environ.setdefault('APPAM_DISABLE_EMBEDDED_WORKER', 'true')
sys.path.insert(0, str(REPO_ROOT / 'backend'))

from app.services.workflow_results import build_appam_smk_metrics  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


class MagMetricIdentityTests(unittest.TestCase):
    """Binners restart numbering in every sample, so bin.1 exists in each one."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix='appam-results-')
        self.results = Path(self.temp_dir.name)
        for sample, completeness in (('DC01', '94.2'), ('DC02', '61.0')):
            write(self.results / 'checkm2' / sample / 'quality_report.tsv',
                  f'Name\tCompleteness\tContamination\nbin.1\t{completeness}\t1.5\n')
            write(self.results / 'gunc' / sample / 'GUNC.progenomes_2.1.maxCSS_level.tsv',
                  'genome\tpass.GUNC\tclade_separation_score\nbin.1.\tTrue\t0.02\n')
            write(self.results / 'gtdbtk' / sample / 'gtdbtk.bac120.summary.tsv',
                  'user_genome\tclassification\nbin.1\td__Bacteria;g__Tannerella\n')

    def tearDown(self):
        self.temp_dir.cleanup()

    def metrics(self, group, name):
        return [
            metric for metric in build_appam_smk_metrics(self.results, summary={})
            if metric['group'] == group and metric['name'] == name
        ]

    def test_same_bin_name_in_two_samples_stays_distinguishable(self):
        completeness = {m['sample_id']: m['value'] for m in self.metrics('checkm2', 'completeness')}
        self.assertEqual(completeness, {'DC01/bin.1': 94.2, 'DC02/bin.1': 61.0})

    def test_overview_reports_mags_and_quality_from_the_summary_table(self):
        write(self.results / 'summaries' / 'MAG_summary.tsv',
              'Sample_ID\tBin_ID\tCompleteness\tContamination\tQuality\tGenus\n'
              'DC01\tbin.1\t94.2\t1.5\tHigh-quality\tTannerella\n'
              'DC01\tbin.2\t70.0\t4.0\tMedium-quality\tTreponema_B\n'
              'DC02\tbin.1\t61.0\t9.0\tMedium-quality\tTannerella\n')
        overview = {m['name']: m['value'] for m in build_appam_smk_metrics(self.results, summary={})
                    if m['group'] == 'overview'}
        self.assertEqual(overview['samples'], 2)
        self.assertEqual(overview['mags_recovered'], 3)
        self.assertEqual(overview['high_quality_mags'], 1)
        self.assertEqual(overview['medium_quality_mags'], 2)
        self.assertEqual(overview['median_completeness'], 70.0)
        self.assertEqual(overview['genera'], 2)

    def test_damage_support_uses_the_run_thresholds_or_is_omitted(self):
        write(self.results / 'pydamage' / 'DC01' / 'pydamage_results.csv',
              'reference,qvalue,predicted_accuracy\nc1,0.01,0.9\nc2,0.04,0.4\nc3,0.20,0.9\nc4,0.001,0.7\n')

        def damage():
            return [m for m in build_appam_smk_metrics(self.results, summary={})
                    if m['name'] == 'damage_supported_contigs']

        # No recorded thresholds: no number rather than a number built on a guess.
        self.assertEqual(damage(), [])

        write(self.results / 'visualization' / 'report-data.json',
              '{"settings": {"PyDamage maximum q-value": 0.05, "PyDamage minimum predicted accuracy": 0.5}}')
        [metric] = damage()
        self.assertEqual(metric['value'], 50.0)  # c1 and c4 pass; c2 fails accuracy, c3 fails q
        self.assertEqual(metric['payload']['supported'], 2)
        self.assertEqual(metric['payload']['total'], 4)

    def test_every_mag_metric_names_its_sample(self):
        for group, name in (('gunc', 'clade_separation_score'), ('gtdbtk', 'classification')):
            identifiers = sorted(m['sample_id'] for m in self.metrics(group, name))
            self.assertEqual(identifiers, ['DC01/bin.1', 'DC02/bin.1'], group)


if __name__ == '__main__':
    unittest.main()
