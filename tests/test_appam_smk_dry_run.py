import gzip
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = REPO_ROOT / 'APPAM-SMK-main'


class AppamSmkDryRunTests(unittest.TestCase):
    def test_empty_bin_and_annotation_outputs_are_guarded(self):
        binning = (WORKFLOW_ROOT / 'workflow' / 'rules' / 'binning.smk').read_text(encoding='utf-8')
        annotation = (WORKFLOW_ROOT / 'workflow' / 'rules' / 'annotation.smk').read_text(encoding='utf-8')
        self.assertIn('Selected binner produced no FASTA bins', binning)
        self.assertGreaterEqual(annotation.count('No MAG FASTA files found'), 4)
        self.assertIn('No Prokka protein FASTA files found', annotation)

    def test_script_directives_have_no_future_imports(self):
        # Snakemake prepends a preamble to every `script:` file before running
        # it, so a `from __future__` import is no longer the first statement and
        # the script dies with a SyntaxError. Dry runs never execute scripts, so
        # only this check catches it; it once broke megahit and bowtie2_align on
        # every real run.
        import re

        rules_dir = WORKFLOW_ROOT / 'workflow' / 'rules'
        offenders = []
        for rule_file in sorted(rules_dir.glob('*.smk')):
            for script in re.findall(r'script:\s*\n?\s*"([^"]+)"', rule_file.read_text(encoding='utf-8')):
                path = (rules_dir / script).resolve()
                if re.search(r'^\s*from __future__ import', path.read_text(encoding='utf-8'), re.M):
                    offenders.append(f'{rule_file.name} -> {path.name}')
        self.assertEqual(offenders, [], 'script: files must not use __future__ imports')

    @unittest.skipUnless(shutil.which('snakemake'), 'snakemake is not installed')
    def test_core_and_experimental_dags(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw = root / 'raw'
            raw.mkdir()
            for mate, sequence in ((1, 'ACGTACGT'), (2, 'TGCATGCA')):
                with gzip.open(raw / f'ancient_sample_R{mate}.fastq.gz', 'wt') as handle:
                    handle.write(f'@read/{mate}\n{sequence}\n+\nFFFFFFFF\n')
            samples = root / 'samples.tsv'
            samples.write_text(
                'sample_id\tforward_reads\treverse_reads\n'
                f'ancient_sample\t{raw / "ancient_sample_R1.fastq.gz"}\t{raw / "ancient_sample_R2.fastq.gz"}\n',
                encoding='utf-8',
            )

            base = yaml.safe_load((WORKFLOW_ROOT / 'config' / 'config.yaml').read_text(encoding='utf-8'))
            environment_root = REPO_ROOT / 'docker' / 'tools' / 'environments'
            base['samples_file'] = str(samples)
            base['paths'] = {
                'raw_data_dir': str(raw),
                'results_dir': str(root / 'results'),
                'logs_dir': str(root / 'logs'),
                'benchmark_dir': str(root / 'benchmarks'),
            }
            base['tools'].update({
                'preprocessing_env': str(environment_root / 'preprocessing.yml'),
                'mapping_env': str(environment_root / 'mapping_dna.yml'),
                'assembly_env': str(environment_root / 'assembly.yml'),
                'metawrap_env': str(environment_root / 'metawrap.yml'),
                'pydamage_env': str(environment_root / 'ancient_dna.yml'),
                'checkm1_env': str(environment_root / 'checkm.yml'),
                'checkm2_env': str(environment_root / 'checkm2.yml'),
                'gunc_env': str(environment_root / 'binning.yml'),
                'gtdbtk_env': str(environment_root / 'gtdbtk.yml'),
                'prokka_env': str(environment_root / 'prokka.yml'),
                'freebayes_env': str(environment_root / 'freebayes.yml'),
                'bcftools_env': str(environment_root / 'bcftools.yml'),
                'reporting_env': str(environment_root / 'reporting.yml'),
            })
            base['params'].update({
                'enable_checkm2': False,
                'enable_gunc': False,
                'enable_gtdbtk': False,
                'enable_prokka': False,
                'enable_eggnog': False,
                'enable_abricate': False,
                'enable_rgi': False,
                'enable_antismash': False,
            })

            scenarios = [
                ('fastp', False, False, False),
                ('adapter_removal', True, True, True),
            ]
            for method, ancient_only, refinement, checkm1 in scenarios:
                with self.subTest(method=method, ancient_only=ancient_only, refinement=refinement):
                    config = dict(base)
                    config['params'] = dict(base['params'])
                    config['params'].update({
                        'preprocess_method': method,
                        'use_ancient_contigs': ancient_only,
                        'enable_bin_refinement': refinement,
                        'enable_checkm1': checkm1,
                    })
                    config_path = root / f'{method}.yaml'
                    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding='utf-8')
                    result = subprocess.run(
                        [
                            'snakemake',
                            '--snakefile',
                            'workflow/Snakefile',
                            '--configfile',
                            str(config_path),
                            '--cores',
                            '1',
                            '--dry-run',
                        ],
                        cwd=WORKFLOW_ROOT,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stdout)
                    self.assertIn('megahit', result.stdout)
                    self.assertIn('bowtie2_align', result.stdout)
                    self.assertIn('metawrap_binning', result.stdout)
                    self.assertIn('mag_summary', result.stdout)
                    self.assertIn('visualization_report', result.stdout)
                    if ancient_only:
                        self.assertIn('split_contigs_by_pydamage', result.stdout)
                    if refinement:
                        self.assertIn('metawrap_bin_refinement', result.stdout)

            def dry_run(config, filename):
                config_path = root / filename
                config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding='utf-8')
                return subprocess.run(
                    [
                        'snakemake',
                        '--snakefile',
                        'workflow/Snakefile',
                        '--configfile',
                        str(config_path),
                        '--cores',
                        '1',
                        '--dry-run',
                    ],
                    cwd=WORKFLOW_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )

            # The modules that config/config.yaml ships as enabled. Without this
            # scenario the DAG every user actually runs is never built, because
            # the scenarios above disable CheckM2, GUNC and GTDB-Tk.
            shipped_defaults = yaml.safe_load(
                (WORKFLOW_ROOT / 'config' / 'config.yaml').read_text(encoding='utf-8')
            )['params']
            default_modules = {
                key: value for key, value in shipped_defaults.items() if key.startswith('enable_')
            }
            self.assertTrue(
                default_modules['enable_checkm2']
                and default_modules['enable_gunc']
                and default_modules['enable_gtdbtk']
                and default_modules['enable_prokka'],
                'shipped defaults changed; update this scenario to match config/config.yaml',
            )

            defaults_config = dict(base)
            defaults_config['params'] = {**base['params'], **default_modules}
            defaults_result = dry_run(defaults_config, 'shipped-defaults.yaml')
            self.assertEqual(defaults_result.returncode, 0, defaults_result.stdout)
            for rule_name in (
                'checkm2',
                'gunc',
                'gtdbtk_classify',
                'prokka_annotation',
                'mag_summary_per_sample',
                'plot_checkm2_quality',
                'plot_gunc_quality',
                'plot_gtdb_ani',
                'plot_taxonomy_rose',
                'compute_taxonomy_alpha_diversity',
                'visualization_report',
            ):
                self.assertIn(rule_name, defaults_result.stdout)

            annotation_config = dict(base)
            annotation_config['params'] = dict(base['params'])
            annotation_config['params'].update({
                **default_modules,
                'enable_prokka': True,
                'enable_eggnog': True,
                'enable_abricate': True,
                'enable_rgi': True,
                'enable_antismash': True,
                'enable_variants': True,
            })
            annotation_result = dry_run(annotation_config, 'full-annotation.yaml')
            self.assertEqual(annotation_result.returncode, 0, annotation_result.stdout)
            self.assertIn('eggnog_annotation', annotation_result.stdout)
            self.assertIn('abricate_annotation', annotation_result.stdout)
            self.assertIn('rgi_annotation', annotation_result.stdout)
            self.assertIn('antismash_annotation', annotation_result.stdout)
            self.assertIn('freebayes_variants', annotation_result.stdout)
            self.assertIn('filter_variants_and_consensus', annotation_result.stdout)


if __name__ == '__main__':
    unittest.main()
