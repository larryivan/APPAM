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
                    if ancient_only:
                        self.assertIn('split_contigs_by_pydamage', result.stdout)
                    if refinement:
                        self.assertIn('metawrap_bin_refinement', result.stdout)

            annotation_config = dict(base)
            annotation_config['params'] = dict(base['params'])
            annotation_config['params'].update({
                'enable_prokka': True,
                'enable_eggnog': True,
                'enable_abricate': True,
                'enable_rgi': True,
                'enable_antismash': True,
            })
            annotation_path = root / 'full-annotation.yaml'
            annotation_path.write_text(yaml.safe_dump(annotation_config, sort_keys=False), encoding='utf-8')
            annotation_result = subprocess.run(
                [
                    'snakemake',
                    '--snakefile',
                    'workflow/Snakefile',
                    '--configfile',
                    str(annotation_path),
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
            self.assertEqual(annotation_result.returncode, 0, annotation_result.stdout)
            self.assertIn('rgi_annotation', annotation_result.stdout)
            self.assertIn('antismash_annotation', annotation_result.stdout)


if __name__ == '__main__':
    unittest.main()
