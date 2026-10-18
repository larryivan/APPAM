"""Execute APPAM-SMK `script:` rules through real Snakemake.

Dry runs and linting build the DAG but never run a script, and the reporting
tests import modules directly, bypassing the preamble Snakemake injects. A
`from __future__` import once broke megahit and bowtie2_align on every real
run while all of those checks passed. This test runs the rules for real, with
small stand-ins for the external tools, so the scripts' Snakemake glue (input,
params, output and log access, subprocess pipelines, cleanup) is exercised.

The stand-ins enforce the behaviour the scripts rely on: MEGAHIT refuses an
existing output directory, Bowtie2 needs a built index, and samtools calmd
needs its reference.
"""

import gzip
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = REPO_ROOT / 'APPAM-SMK-main'
ENVIRONMENTS = REPO_ROOT / 'docker' / 'tools' / 'environments'

STUBS = {
    'megahit': '''
        args = sys.argv[1:]
        out = Path(args[args.index('-o') + 1])
        if out.exists():
            sys.exit(f'MEGAHIT: output directory {out} already exists')
        if '-1' not in args and '-r' not in args:
            sys.exit('MEGAHIT: no reads given')
        out.mkdir(parents=True)
        (out / 'intermediate_contigs').mkdir()
        (out / 'final.contigs.fa').write_text('>k141_1\\n' + 'ACGT' * 150 + '\\n>k141_2\\n' + 'GGCC' * 150 + '\\n')
    ''',
    'bowtie2-build': '''
        prefix = sys.argv[-1]
        for suffix in ('1', '2', '3', '4', 'rev.1', 'rev.2'):
            Path(f'{prefix}.{suffix}.bt2').write_text('index')
    ''',
    'bowtie2': '''
        args = sys.argv[1:]
        prefix = args[args.index('-x') + 1]
        if not Path(f'{prefix}.1.bt2').is_file():
            sys.exit(f'bowtie2: index {prefix} not found')
        sys.stdout.write('@HD\\tVN:1.6\\n@SQ\\tSN:k141_1\\tLN:600\\nr1\\t0\\tk141_1\\t1\\t42\\t4M\\t*\\t0\\t0\\tACGT\\tFFFF\\n')
    ''',
    'samtools': '''
        args = sys.argv[1:]
        command = args[0]
        if command in ('view', 'calmd'):
            if command == 'calmd' and not Path(args[-1]).is_file():
                sys.exit('samtools calmd: reference missing')
            shutil.copyfileobj(sys.stdin.buffer, sys.stdout.buffer)
        elif command == 'sort':
            Path(args[args.index('-o') + 1]).write_bytes(sys.stdin.buffer.read() or b'empty')
        elif command == 'index':
            bam = [a for a in args[1:] if not a.startswith('-') and not a.isdigit()][-1]
            Path(bam + '.bai').write_text('bai')
        else:
            sys.exit(f'samtools stub: unsupported {command}')
    ''',
    'seqkit': '''
        args = sys.argv[1:]
        invert = '-v' in args
        wanted = set(Path(args[args.index('-f') + 1]).read_text().split())
        source = [a for a in args if a.endswith('.fa') and a != args[args.index('-o') + 1]][0]
        records, keep = [], False
        for line in Path(source).read_text().splitlines():
            if line.startswith('>'):
                keep = (line[1:].split()[0] in wanted) != invert
            if keep:
                records.append(line)
        Path(args[args.index('-o') + 1]).write_text('\\n'.join(records) + ('\\n' if records else ''))
    ''',
}

RULES = [
    'megahit', 'bowtie2_index', 'bowtie2_align', 'index_bam',
    'count_read_lengths', 'split_contigs_by_pydamage',
    'mag_summary_per_sample', 'mag_summary',
]


def write_fastq(path: Path, sequences) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, 'wt') as handle:
        for index, sequence in enumerate(sequences):
            handle.write(f'@r{index}\n{sequence}\n+\n{"F" * len(sequence)}\n')


@unittest.skipUnless(shutil.which('snakemake'), 'snakemake is not installed')
class AppamSmkScriptExecutionTests(unittest.TestCase):
    def test_script_rules_execute_under_snakemake(self):
        with tempfile.TemporaryDirectory(prefix='appam-script-exec-') as tmpdir:
            root = Path(tmpdir)
            results = root / 'results'

            bin_dir = root / 'bin'
            bin_dir.mkdir()
            trace = root / 'trace.log'
            for name, body in STUBS.items():
                stub = bin_dir / name
                stub.write_text(
                    f'#!{sys.executable}\n'
                    'import shutil, sys\nfrom pathlib import Path\n'
                    f'with open({str(trace)!r}, "a") as t: t.write({name!r} + " " + " ".join(sys.argv[1:]) + "\\n")\n'
                    + textwrap.dedent(body)
                )
                stub.chmod(stub.stat().st_mode | stat.S_IEXEC)

            raw = root / 'raw'
            write_fastq(raw / 'S1_R1.fastq.gz', ['ACGTACGT'])
            write_fastq(raw / 'S1_R2.fastq.gz', ['TGCATGCA'])
            samples = root / 'samples.tsv'
            samples.write_text(
                'sample_id\tforward_reads\treverse_reads\n'
                f'S1\t{raw / "S1_R1.fastq.gz"}\t{raw / "S1_R2.fastq.gz"}\n'
            )

            # Outputs of rules this test does not run (preprocessing, PyDamage, binning).
            preprocess = results / 'preprocess'
            write_fastq(preprocess / 'S1.paired_R1.fastq.gz', ['ACGTACGTAC', 'GGCCGGCC'])
            write_fastq(preprocess / 'S1.paired_R2.fastq.gz', ['GTACGTACGT', 'GGCCGGCC'])
            write_fastq(preprocess / 'S1.single.fastq.gz', ['ACGTAC'])
            write_fastq(preprocess / 'S1.all.single.fastq.gz', ['ACGTACGTAC', 'ACGTAC', 'ACGTACGTACGTACG'])
            damage = results / 'pydamage' / 'S1' / 'pydamage_results.csv'
            damage.parent.mkdir(parents=True)
            damage.write_text('reference,qvalue,predicted_accuracy\nk141_1,0.001,0.93\nk141_2,0.6,0.12\n')
            bins = results / 'metawrap' / 'binning' / 'S1' / 'metabat2_bins'
            bins.mkdir(parents=True)
            (bins / 'bin.1.fa').write_text('>k141_1\n' + 'ACGT' * 150 + '\n')

            config = yaml.safe_load((WORKFLOW_ROOT / 'config' / 'config.yaml').read_text(encoding='utf-8'))
            config['samples_file'] = str(samples)
            config['paths'] = {
                'raw_data_dir': str(raw),
                'results_dir': str(results),
                'logs_dir': str(root / 'logs'),
                'benchmark_dir': str(root / 'benchmarks'),
            }
            for tool in config['tools']:
                config['tools'][tool] = str(ENVIRONMENTS / 'reporting.yml')
            for module in ('enable_checkm2', 'enable_gunc', 'enable_gtdbtk', 'enable_prokka'):
                config['params'][module] = False
            config_path = root / 'config.yaml'
            config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding='utf-8')

            targets = [
                results / 'megahit' / 'S1' / 'done',
                results / 'bowtie2' / 'S1' / 'S1.sorted.bam.bai',
                results / 'visualization' / 'S1' / 'reads_length' / 'length_counts.tsv',
                results / 'pydamage' / 'S1' / 'ancient.contigs.fa',
                results / 'summaries' / 'MAG_summary.tsv',
            ]
            env = {'PATH': f'{bin_dir}:{Path(sys.executable).parent}:/usr/bin:/bin', 'HOME': str(root)}
            result = subprocess.run(
                [
                    shutil.which('snakemake'), *map(str, targets),
                    '--snakefile', 'workflow/Snakefile',
                    '--configfile', str(config_path),
                    '--cores', '2', '--latency-wait', '1',
                    '--allowed-rules', *RULES,
                ],
                cwd=WORKFLOW_ROOT, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout[-4000:])
            calls = trace.read_text().splitlines()

            # megahit: both read streams passed, intermediates cleaned, completion marked
            [megahit_call] = [line for line in calls if line.startswith('megahit ')]
            self.assertIn('-1 ', megahit_call)
            self.assertIn('-r ', megahit_call)
            self.assertIn('--min-contig-len 500', megahit_call)
            assembly = results / 'megahit' / 'S1'
            self.assertGreater((assembly / 'final.contigs.fa').stat().st_size, 0)
            self.assertFalse((assembly / 'intermediate_contigs').exists())

            # bowtie2_align: the four-stage pipe ran and wrote a non-empty BAM
            self.assertTrue(any(line.startswith('bowtie2 ') and '--very-sensitive' in line for line in calls))
            for stage in ('samtools view', 'samtools calmd', 'samtools sort'):
                self.assertTrue(any(line.startswith(stage) for line in calls), stage)
            self.assertGreater((results / 'bowtie2' / 'S1' / 'S1.sorted.bam').stat().st_size, 0)

            # count_read_lengths: every read counted
            counts = (results / 'visualization' / 'S1' / 'reads_length' / 'length_counts.tsv').read_text()
            self.assertIn('10', counts)
            self.assertIn('15', counts)

            # split_contigs_by_pydamage: only the damage-supported contig is kept
            ancient = (results / 'pydamage' / 'S1' / 'ancient.contigs.fa').read_text()
            self.assertIn('>k141_1', ancient)
            self.assertNotIn('>k141_2', ancient)

            # mag_summary: one row per bin, sample-qualified
            summary = (results / 'summaries' / 'MAG_summary.tsv').read_text().splitlines()
            self.assertEqual(len(summary), 2)
            self.assertTrue(summary[1].startswith('S1\tbin.1'))


if __name__ == '__main__':
    unittest.main()
