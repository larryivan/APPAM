import os
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / 'backend'
os.environ.setdefault('FLASK_SECRET_KEY', 'appam-command-test-secret')
os.environ.setdefault('APPAM_DISABLE_EMBEDDED_WORKER', 'true')
sys.path.insert(0, str(BACKEND_DIR))

from app.services.pipeline_execution import (  # noqa: E402
    _verify_source_runtime,
    build_job_request,
    preflight_job_request,
    resolve_project_or_absolute_path,
    validate_parameter_values,
)
from app.services.job_runner import run_pipeline_job  # noqa: E402
from app.services.database_manifest import validate_database_manifest  # noqa: E402
from app.services.tool_library import get_tool_definition, get_tool_library  # noqa: E402


class CommandExecutionContractTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix='appam-command-tests-')
        self.project_dir = Path(self.temp_dir.name) / 'project'
        self.project_dir.mkdir()
        self.project_dir = self.project_dir.resolve()
        (self.project_dir / 'inputs').mkdir()
        self.fastq = self.project_dir / 'inputs' / 'sample.fastq.gz'
        self.fastq.write_bytes(b'not-a-real-fastq\n')
        self.reference = self.project_dir / 'inputs' / 'reference.fa'
        self.reference.write_text('>ref\nACGT\n', encoding='utf-8')

        self.project_patch = mock.patch(
            'app.services.pipeline_execution.get_project_dir',
            return_value=self.project_dir,
        )
        self.executable_patch = mock.patch(
            'app.services.pipeline_execution.resolve_executable',
            return_value='/usr/bin/appam-test-tool',
        )
        self.project_patch.start()
        self.executable_patch.start()

    def tearDown(self):
        self.executable_patch.stop()
        self.project_patch.stop()
        self.temp_dir.cleanup()

    def test_fastqc_named_options_precede_positional_inputs(self):
        request = build_job_request(
            'project-1',
            'job-1',
            get_tool_definition('fastqc'),
            {
                'input_files': ['inputs/sample.fastq.gz'],
                '-o': 'results/fastqc',
                '-t': 4,
            },
        )

        self.assertEqual(
            request['command_spec']['argv'],
            [
                '/usr/bin/appam-test-tool',
                '-o',
                str(self.project_dir / 'results' / 'fastqc'),
                '-t',
                '4',
                str(self.fastq),
            ],
        )
        self.assertTrue((self.project_dir / 'results' / 'fastqc').is_dir())

    def test_bwa_subcommand_and_positional_order_are_stable(self):
        request = build_job_request(
            'project-1',
            'job-2',
            get_tool_definition('bwa'),
            {
                'command': 'mem',
                'reference_genome': 'inputs/reference.fa',
                'input_reads': ['inputs/sample.fastq.gz'],
                '-t': 2,
                '-o': 'results/bwa/output.sam',
            },
        )

        self.assertEqual(request['command_spec']['argv'][1], 'mem')
        self.assertEqual(request['command_spec']['argv'][-2:], [str(self.reference), str(self.fastq)])
        self.assertEqual(request['output_path'], str(self.project_dir / 'results' / 'bwa' / 'output.sam'))

    def test_stream_parameters_do_not_enable_a_shell(self):
        input_sam = self.project_dir / 'inputs' / 'alignments.sam'
        input_sam.write_text('@HD\tVN:1.6\n', encoding='utf-8')
        request = build_job_request(
            'project-1',
            'job-3',
            get_tool_definition('pmdtools'),
            {
                '--threshold': 3,
                'input_sam': 'inputs/alignments.sam',
                'output_sam': 'results/pmdtools/filtered.sam',
            },
        )

        self.assertEqual(request['command_spec']['argv'], ['/usr/bin/appam-test-tool', '--threshold', '3'])
        self.assertEqual(request['command_spec']['stdin_path'], str(input_sam))
        self.assertEqual(
            request['command_spec']['stdout_path'],
            str(self.project_dir / 'results' / 'pmdtools' / 'filtered.sam'),
        )
        self.assertIn(' < ', request['display_command'])
        self.assertIn(' > ', request['display_command'])

    def test_project_output_cannot_escape_workspace(self):
        with self.assertRaisesRegex(ValueError, 'escapes project workspace'):
            build_job_request(
                'project-1',
                'job-4',
                get_tool_definition('fastqc'),
                {
                    'input_files': ['inputs/sample.fastq.gz'],
                    '-o': '../outside',
                },
            )

    def test_absolute_reference_path_is_limited_to_project_or_shared_root(self):
        shared_root = Path(self.temp_dir.name) / 'databases'
        shared_root.mkdir()
        shared_reference = shared_root / 'reference.fasta'
        shared_reference.write_text('>protein\nMPEPTIDE\n', encoding='utf-8')
        with mock.patch.dict(os.environ, {'APPAM_DATABASES_ROOT': str(shared_root)}, clear=False):
            self.assertEqual(
                resolve_project_or_absolute_path('project-1', str(shared_reference)),
                shared_reference.resolve(),
            )
            with self.assertRaisesRegex(ValueError, 'project or APPAM_DATABASES_ROOT'):
                resolve_project_or_absolute_path('project-1', '/etc/hosts')

    def test_preflight_does_not_require_output_directory_to_exist(self):
        result = preflight_job_request(
            'project-1',
            get_tool_definition('fastqc'),
            {
                'input_files': ['inputs/sample.fastq.gz'],
                '-o': 'results/not-created-by-preflight',
            },
        )

        self.assertTrue(result['ok'])
        self.assertFalse((self.project_dir / 'results' / 'not-created-by-preflight').exists())

    def test_runner_streams_files_without_shell_redirection(self):
        input_path = self.project_dir / 'inputs' / 'stream.txt'
        output_path = self.project_dir / 'results' / 'stream-copy.txt'
        log_path = self.project_dir / 'logs' / 'stream.log'
        input_path.write_text('APPAM stream test\n', encoding='utf-8')

        with mock.patch('app.services.job_runner._backend_dir', return_value=str(self.project_dir)), \
             mock.patch('app.services.job_runner.get_job', return_value=None), \
             mock.patch('app.services.job_runner.is_cancel_requested', return_value=False), \
             mock.patch('app.services.job_runner.mark_job_started'), \
             mock.patch('app.services.job_runner.update_job_heartbeat'), \
             mock.patch('app.services.job_runner.attach_process_info'), \
             mock.patch('app.services.job_runner.mark_job_finished'):
            result = run_pipeline_job(
                'stream-job',
                'project-1',
                'stream-test',
                'cat input > output',
                str(log_path),
                command_spec={
                    'argv': [shutil.which('cat') or '/bin/cat'],
                    'cwd': str(self.project_dir),
                    'stdin_path': str(input_path),
                    'stdout_path': str(output_path),
                },
            )

        self.assertEqual(result['status'], 'completed')
        self.assertEqual(output_path.read_text(encoding='utf-8'), 'APPAM stream test\n')

    def test_catalog_has_explicit_contracts_for_plain_parameter_names(self):
        for tool in get_tool_library():
            if tool['kind'] != 'tool':
                continue
            for parameter in tool['parameters']:
                if parameter['name'].startswith('-'):
                    continue
                self.assertTrue(
                    parameter.get('position') is not None
                    or parameter.get('positional')
                    or parameter.get('stream'),
                    f'{tool["tool_name"]}.{parameter["name"]} has no CLI placement contract',
                )

    def test_parameter_validation_rejects_unknown_and_excessive_resources(self):
        tool = get_tool_definition('fastqc')
        thread_parameter = next(parameter for parameter in tool['parameters'] if parameter['name'] == '-t')
        errors = validate_parameter_values(
            tool,
            {
                'input_files': ['inputs/sample.fastq.gz'],
                '-t': thread_parameter['maximum'] + 1,
                '--not-a-real-option': True,
            },
        )
        self.assertTrue(any('Unknown parameter' in error for error in errors))
        self.assertTrue(any('must be at most' in error for error in errors))

    def test_kraken_paired_mode_requires_exactly_two_inputs(self):
        errors = validate_parameter_values(
            get_tool_definition('krakenuniq'),
            {
                'input_files': ['inputs/sample.fastq.gz'],
                '--db': 'krakenuniq_refseq_bav',
                '--paired': True,
            },
        )
        self.assertTrue(any('requires at least 2' in error for error in errors))

    def test_retry_runtime_verification_ignores_paths_but_rejects_package_drift(self):
        manifest_path = self.project_dir / 'source-manifest.json'
        manifest_path.write_text(json.dumps({
            'runtime_metadata': {
                'tools': {
                    'mapping': {
                        'path': '/old/environment/path',
                        'packages_sha256': 'stable-packages',
                    },
                },
            },
        }), encoding='utf-8')
        source_run = {'manifest_path': str(manifest_path)}

        matched = _verify_source_runtime('project-1', source_run, {
            'tools': {
                'mapping': {
                    'path': '/new/environment/path',
                    'packages_sha256': 'stable-packages',
                },
            },
        })
        self.assertTrue(matched['matched'])

        with self.assertRaisesRegex(ValueError, 'runtime or database resources changed'):
            _verify_source_runtime('project-1', source_run, {
                'tools': {
                    'mapping': {
                        'path': '/new/environment/path',
                        'packages_sha256': 'changed-packages',
                    },
                },
            })

    def test_publication_manifest_rejects_placeholder_versions(self):
        manifest = {
            'found': True,
            'schema_version': 1,
            'resources': {
                'checkm2_db': {'version': 'downloaded-with-checkm2'},
                'gunc_db': {'version': 'progenomes_2.1'},
            },
        }
        errors = validate_database_manifest(manifest, ['checkm2_db', 'gunc_db'])
        self.assertEqual(errors, ['checkm2_db requires an exact non-placeholder version'])
        manifest['resources']['checkm2_db']['version'] = 'CheckM2 database 1.1.0 / 2026-01-20'
        self.assertEqual(validate_database_manifest(manifest, ['checkm2_db', 'gunc_db']), [])


if __name__ == '__main__':
    unittest.main()
