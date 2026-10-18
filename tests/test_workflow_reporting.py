import gzip
import importlib.util
from pathlib import Path
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = REPO_ROOT / 'APPAM-SMK-main' / 'workflow' / 'scripts'


def load_module(name):
    path = SCRIPT_ROOT / f'{name}.py'
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class WorkflowReportingTests(unittest.TestCase):
    def test_fastq_length_counter_supports_gzip(self):
        module = load_module('count_read_lengths')
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'reads.fastq.gz'
            with gzip.open(path, 'wt') as handle:
                handle.write('@r1\nACGT\n+\nFFFF\n@r2\nACGTAA\n+\nFFFFFF\n')
            self.assertEqual(module.count_fastq_lengths(path), {4: 1, 6: 1})

    def test_damage_and_mag_quality_boundaries_match_workflow_thresholds(self):
        module = load_module('visualization_utils')
        rows = module.summarize_contig_validation(
            [
                {'predicted_accuracy': '0.7', 'qvalue': '0.01'},
                {'predicted_accuracy': '0.7', 'qvalue': '0.2'},
                {'predicted_accuracy': '0.6', 'qvalue': '0.1'},
            ],
            accuracy_min=0.7,
            qvalue_max=0.1,
        )
        lookup = {(row['group'], row['sig']): row['count'] for row in rows}
        self.assertEqual(lookup[('Accuracy >= 0.7', 'q-value <= 0.1')], 1)
        self.assertEqual(lookup[('Accuracy < 0.7', 'q-value <= 0.1')], 1)
        self.assertEqual(module.classify_mag_quality(50, 10), 'MQ')

    def test_mag_summary_merges_quality_taxonomy_gunc_and_fasta_metrics(self):
        module = load_module('build_mag_summary')
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bins = root / 'bins'
            bins.mkdir()
            (bins / 'bin.1.fa').write_text('>c1\nACGTACGTNN\n>c2\nGGCC\n', encoding='utf-8')
            checkm2 = root / 'quality.tsv'
            checkm2.write_text(
                'Name\tCompleteness\tContamination\n'
                'bin.1\t95.5\t2.3\n',
                encoding='utf-8',
            )
            gtdb = root / 'gtdbtk.bac120.summary.tsv'
            gtdb.write_text(
                'user_genome\tclassification\tclosest_genome_ani\n'
                'bin.1\td__Bacteria;p__Bacillota;g__Streptococcus;'
                's__Streptococcus suis\t98.7\n',
                encoding='utf-8',
            )
            gunc = root / 'gunc.tsv'
            gunc.write_text(
                'genome\tpass.GUNC\ttaxonomic_level\tclade_separation_score\n'
                'bin.1.\tTrue\tspecies\t0.02\n',
                encoding='utf-8',
            )

            rows = module.build_sample_summary('S1', checkm2, [gtdb], gunc, bins)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['Quality'], 'High-quality')
        self.assertIn('full MIMAG criteria not evaluated', rows[0]['Quality_Basis'])
        self.assertEqual(rows[0]['Genome_Size'], 14)
        self.assertEqual(rows[0]['Contig_N50'], 10)
        self.assertEqual(rows[0]['Phylum'], 'Bacillota')
        self.assertEqual(rows[0]['Closest_Genome_ANI'], '98.7')
        self.assertEqual(rows[0]['GUNC_Clade_Separation_Score'], '0.02')

    def test_mag_summary_remains_structured_when_optional_modules_are_disabled(self):
        module = load_module('build_mag_summary')
        with tempfile.TemporaryDirectory() as tmpdir:
            bins = Path(tmpdir) / 'bins'
            bins.mkdir()
            (bins / 'bin.1.fa').write_text('>c1\nACGT\n', encoding='utf-8')
            rows = module.build_sample_summary('S1', None, [], None, bins)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['Sample_ID'], 'S1')
        self.assertEqual(rows[0]['Bin_ID'], 'bin.1')
        self.assertEqual(rows[0]['Quality'], 'Unknown')
        self.assertEqual(rows[0]['Classification'], 'Unclassified')

    def test_report_contains_only_enabled_run_figures(self):
        module = load_module('build_visualization_report')
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            figure = root / 'S1' / 'reads_length' / 'length_hist.png'
            figure.parent.mkdir(parents=True)
            figure.write_bytes(b'not-a-real-png-but-valid-for-embedding-test')
            output = root / 'report.html'
            html = module.build_report_html(
                root,
                ['S1'],
                output,
                embed_images=True,
                enabled_figure_keys=['reads'],
                summary_rows=[{'Sample_ID': 'S1', 'Quality': 'Medium-quality'}],
                settings={'CheckM2': False},
            )
        self.assertIn('Read length', html)
        self.assertNotIn('ANI histogram', html)
        self.assertNotIn('Missing output', html)
        self.assertIn('1</strong> MAG records', html)
        self.assertIn('CheckM2', html)

    def test_report_exposes_all_taxonomic_plots_and_alpha_diversity(self):
        module = load_module('build_visualization_report')
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for filename in ('phylum_rose.png', 'genus_rose.png', 'species_topn_rose.png'):
                figure = root / 'S1' / 'rose' / filename
                figure.parent.mkdir(parents=True, exist_ok=True)
                figure.write_bytes(b'plot')
            html = module.build_report_html(
                root,
                ['S1'],
                root / 'report.html',
                embed_images=True,
                enabled_figure_keys=['phylum', 'genus', 'species'],
                alpha_rows=[{
                    'sample': 'S1',
                    'rank': 'genus',
                    'shannon_index': '1.25',
                    'observed_taxa': '4',
                    'total_bins': '6',
                }],
            )
        self.assertIn('Phylum rose chart', html)
        self.assertIn('Genus rose chart', html)
        self.assertIn('Top species rose chart', html)
        self.assertIn('Taxonomic alpha diversity', html)
        self.assertIn('1.250', html)

    def test_report_rounds_diversity_for_display_only(self):
        # compute_alpha_diversity writes full float precision; the TSV should
        # keep it, while the report shows a readable three decimals.
        module = load_module('build_visualization_report')
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            html = module.build_report_html(
                root,
                ['S1'],
                root / 'report.html',
                embed_images=True,
                enabled_figure_keys=[],
                alpha_rows=[
                    {'sample': 'S1', 'rank': 'genus', 'shannon_index': '1.7478680974667573',
                     'observed_taxa': '6', 'total_bins': '7'},
                    {'sample': 'S2', 'rank': 'genus', 'shannon_index': 'NA',
                     'observed_taxa': '0', 'total_bins': '0'},
                ],
            )
        self.assertIn('>1.748<', html)
        self.assertNotIn('1.7478680974667573', html)
        self.assertIn('>NA<', html)  # non-numeric values pass through unchanged

    def test_report_rules_do_not_use_static_example_results(self):
        rules = (REPO_ROOT / 'APPAM-SMK-main' / 'workflow' / 'rules' / 'visualization.smk').read_text(encoding='utf-8')
        self.assertNotIn('report_images', rules)
        self.assertNotIn('report_template.md', rules)
        self.assertNotIn('markdown_report', rules)


if __name__ == '__main__':
    unittest.main()
