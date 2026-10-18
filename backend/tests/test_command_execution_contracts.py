import os
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml


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
from app.services.publication_audit import audit_run_manifest, audit_run_path  # noqa: E402
from app.services.tool_library import get_tool_definition, get_tool_library  # noqa: E402


DIGEST = 'a' * 64

# Environments an all-defaults APPAM-SMK run consumes: the always-on ones plus
# the tools of the modules enabled by default.
DEFAULT_SMK_TOOLS = (
    'preprocessing_env',
    'mapping_env',
    'assembly_env',
    'metawrap_env',
    'pydamage_env',
    'reporting_env',
    'checkm2_env',
    'gunc_env',
    'gtdbtk_env',
    'prokka_env',
)

DEFAULT_SMK_MODULES = {
    'enable_bin_refinement': False,
    'enable_checkm1': False,
    'enable_checkm2': True,
    'enable_gunc': True,
    'enable_gtdbtk': True,
    'enable_prokka': True,
    'enable_eggnog': False,
    'enable_abricate': False,
    'enable_rgi': False,
    'enable_antismash': False,
    'enable_variants': False,
    'enable_visualization': True,
}


def complete_evidence_manifest() -> dict:
    """A run manifest that records everything an archived run must carry."""
    effective_config = {'params': {'min_contig_len': 500}}
    resources = {
        'checkm2_db': {'version': '1.1.0 / 2026-01-20'},
        'gunc_db': {'version': '2.1 / 2025-09-01'},
    }
    canonical_database = {
        'schema_version': 1,
        'template': False,
        'resources': resources,
    }
    return {
        'run_id': 'run-1',
        'workflow_id': 'appam-smk',
        'mode': 'run',
        'dry_run': False,
        'preflight_id': 'preflight-1',
        'workflow_revision': {'commit': 'b' * 40, 'dirty': False},
        'effective_config': effective_config,
        'effective_config_sha256': hashlib.sha256(
            yaml.safe_dump(effective_config, sort_keys=False).encode('utf-8')
        ).hexdigest(),
        'paths': {'resolved_sample_manifest': '/projects/p1/config/samples.resolved.tsv'},
        'resolved_input_table': {
            'role': 'appam_smk_sample_manifest',
            'path': '/projects/p1/config/samples.resolved.tsv',
            'sha256': DIGEST,
            'size_bytes': 120,
            'row_count': 1,
        },
        'input_validation': {'ok': True},
        'inputs': [
            {'path': '/projects/p1/raw/s1_R1.fastq.gz', 'exists': True, 'type': 'file', 'sha256': DIGEST},
            {'path': '/projects/p1/raw/s1_R2.fastq.gz', 'exists': True, 'type': 'file', 'sha256': DIGEST},
        ],
        'runtime_metadata': {
            'container': {'image': 'local', 'image_digest': ''},
            'modules': dict(DEFAULT_SMK_MODULES),
            'tools': {name: {'packages_sha256': DIGEST} for name in DEFAULT_SMK_TOOLS},
            'database_manifest': {
                'found': True,
                'sha256': DIGEST,
                'canonical_sha256': hashlib.sha256(json.dumps(
                    canonical_database,
                    sort_keys=True,
                    separators=(',', ':'),
                ).encode('utf-8')).hexdigest(),
                'schema_version': 1,
                'template': False,
                'required_resources': ['checkm2_db', 'gunc_db'],
                'resources': resources,
                'validation_errors': [],
            },
        },
        'source_input_verification': {'checked': False},
        'source_runtime_verification': {'checked': False},
        'command': ['snakemake', '--snakefile', 'workflow/Snakefile'],
    }


def complete_paleoproteomics_manifest() -> dict:
    manifest = complete_evidence_manifest()
    manifest['workflow_id'] = 'appam-paleoproteomics'
    manifest['resolved_input_table']['role'] = 'paleoproteomics_sample_table'
    manifest['runtime_metadata'] = {
        'runtime_env': {'type': 'conda_environment', 'packages_sha256': DIGEST},
        'maxquant_cmd_dll': {'exists': True, 'sha256': DIGEST},
    }
    return manifest


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

    def test_single_valued_parameters_reject_lists_even_without_an_explicit_contract(self):
        # Most catalog parameters never declare `multiple`, so the guard has to
        # default to single-valued instead of only rejecting `multiple: false`.
        tool = get_tool_definition('prokka')
        genus = next(parameter for parameter in tool['parameters'] if parameter['name'] == '--genus')
        self.assertNotIn('multiple', genus, 'fixture assumes --genus has no explicit contract')
        errors = validate_parameter_values(
            tool,
            {'contigs_fasta': 'inputs/reference.fa', '--genus': ['Escherichia', '--outdir', '/etc']},
        )
        self.assertTrue(any('accepts only one value' in error for error in errors))

    def test_free_form_values_cannot_smuggle_extra_options_into_argv(self):
        with self.assertRaises(ValueError) as single:
            build_job_request(
                'project-1',
                'job-genus',
                get_tool_definition('prokka'),
                {'contigs_fasta': 'inputs/reference.fa', '--genus': '--outdir'},
            )
        self.assertIn('must not start with', str(single.exception))

        # `-m` does declare multiple: true, so only the render-time guard stops it.
        with self.assertRaises(ValueError) as repeated:
            build_job_request(
                'project-1',
                'job-modules',
                get_tool_definition('multiqc'),
                {'analysis_directories': ['inputs'], '-m': ['fastqc', '--outdir']},
            )
        self.assertIn('must not start with', str(repeated.exception))

    def test_option_guard_leaves_legitimate_free_form_values_alone(self):
        request = build_job_request(
            'project-1',
            'job-modules-ok',
            get_tool_definition('multiqc'),
            {'analysis_directories': ['inputs'], '-m': ['fastqc', 'samtools']},
        )
        argv = request['command_spec']['argv']
        self.assertEqual(argv.count('-m'), 2)
        self.assertIn('fastqc', argv)
        self.assertIn('samtools', argv)

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

    def test_kraken_runtime_requires_all_database_indexes(self):
        runtime_paths = {
            'APPAM_KRAKENUNIQ_KDB': '/db/kraken/database.kdb',
            'APPAM_KRAKENUNIQ_IDX': '/db/kraken/database.idx',
            'APPAM_KRAKENUNIQ_TAXDB': '/db/kraken/taxDB',
        }
        with mock.patch.dict(os.environ, runtime_paths, clear=False):
            get_tool_library.cache_clear()
            tool = get_tool_definition('krakenuniq')
            requirements = tool['execution']['required_paths']
        get_tool_library.cache_clear()

        self.assertEqual(
            {item['path'] for item in requirements},
            set(runtime_paths.values()),
        )
        self.assertTrue(all(item['kind'] == 'file' for item in requirements))

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
        for placeholder in ('TBD', 'planned', 'n/a', 'replace with installed release'):
            with self.subTest(placeholder=placeholder):
                manifest['resources']['checkm2_db']['version'] = placeholder
                self.assertIn(
                    'checkm2_db requires an exact non-placeholder version',
                    validate_database_manifest(manifest, ['checkm2_db']),
                )

    def test_publication_manifest_rejects_the_unmodified_example(self):
        example = json.loads((REPO_ROOT / 'docker' / 'database-manifest.example.json').read_text(encoding='utf-8'))
        example['found'] = True
        errors = validate_database_manifest(example, ['gunc_db', 'gtdbtk_db'])
        self.assertIn(
            'manifest is still the unmodified example; remove "template": true after recording real releases',
            errors,
        )
        example.pop('template')
        self.assertEqual(validate_database_manifest(example, ['gunc_db', 'gtdbtk_db']), [])

    def test_publication_audit_accepts_a_complete_evidence_record(self):
        report = audit_run_manifest(complete_evidence_manifest())
        self.assertTrue(report['ok'], report['blockers'])
        self.assertEqual(report['blockers'], [])
        self.assertEqual(report['warnings'], [])
        self.assertEqual(report['schema_version'], 2)
        self.assertEqual(
            [check['id'] for check in report['checks']][:4],
            ['run_mode', 'software_revision', 'effective_config', 'resolved_inputs'],
        )

    def test_publication_audit_blocks_incomplete_evidence(self):
        cases = {
            'run_mode': {'dry_run': True},
            'software_revision': {'workflow_revision': {'commit': 'c' * 40, 'dirty': True}},
            'effective_config': {'effective_config_sha256': 'not-a-digest'},
            'resolved_inputs': {'resolved_input_table': None},
            'input_identity': {
                'inputs': [{'path': '/projects/p1/raw/s1_R1.fastq.gz', 'exists': True, 'type': 'file'}]
            },
            'runtime_identity': {'runtime_metadata': {}},
            'command_recorded': {'command': []},
        }
        for expected_blocker, override in cases.items():
            with self.subTest(blocker=expected_blocker):
                manifest = {**complete_evidence_manifest(), **override}
                report = audit_run_manifest(manifest)
                self.assertFalse(report['ok'])
                self.assertIn(expected_blocker, report['blockers'])

    def test_publication_audit_recomputes_archived_config_and_database_digests(self):
        manifest = complete_evidence_manifest()
        self.assertTrue(audit_run_manifest(manifest)['ok'])

        manifest['effective_config']['params']['min_contig_len'] = 1000
        report = audit_run_manifest(manifest)
        self.assertIn('effective_config', report['blockers'])
        self.assertIn(
            'no longer matches',
            next(check['detail'] for check in report['checks'] if check['id'] == 'effective_config'),
        )

        manifest = complete_evidence_manifest()
        manifest['runtime_metadata']['database_manifest']['resources']['gunc_db']['version'] = 'tampered'
        report = audit_run_manifest(manifest)
        self.assertIn('database_manifest', report['blockers'])
        self.assertIn(
            'canonical SHA-256',
            next(check['detail'] for check in report['checks'] if check['id'] == 'database_manifest'),
        )

    def test_publication_audit_rejects_a_path_only_resolved_input_record(self):
        manifest = complete_evidence_manifest()
        manifest.pop('resolved_input_table')
        report = audit_run_manifest(manifest)
        self.assertIn('resolved_inputs', report['blockers'])
        detail = next(check['detail'] for check in report['checks'] if check['id'] == 'resolved_inputs')
        self.assertIn('A path is not archived evidence', detail)

        manifest['resolved_input_table'] = {'path': '/projects/p1/config/samples.resolved.tsv'}
        self.assertIn('resolved_inputs', audit_run_manifest(manifest)['blockers'])

    def test_publication_audit_verifies_resolved_input_bytes_on_disk(self):
        table = self.project_dir / 'samples.resolved.tsv'
        table.write_text('sample_id\tforward_reads\treverse_reads\nS1\t/a_R1.fq\t/a_R2.fq\n', encoding='utf-8')
        manifest = complete_evidence_manifest()
        manifest['resolved_input_table'] = {
            'role': 'appam_smk_sample_manifest',
            'path': str(table),
            'sha256': hashlib.sha256(table.read_bytes()).hexdigest(),
            'size_bytes': table.stat().st_size,
            'row_count': 1,
        }
        self.assertTrue(audit_run_manifest(manifest, verify_files=True)['ok'])

        table.write_text('sample_id\tforward_reads\treverse_reads\nS1\t/tampered_R1.fq\t/a_R2.fq\n', encoding='utf-8')
        tampered = audit_run_manifest(manifest, verify_files=True)
        self.assertIn('resolved_inputs', tampered['blockers'])
        self.assertIn(
            'no longer matches its recorded SHA-256',
            next(check['detail'] for check in tampered['checks'] if check['id'] == 'resolved_inputs'),
        )
        # Without the file present the audit must block rather than crash.
        table.unlink()
        missing = audit_run_manifest(manifest, verify_files=True)
        self.assertIn('resolved_inputs', missing['blockers'])
        # The same manifest still passes the digest-only audit used by pure consumers.
        self.assertTrue(audit_run_manifest(manifest)['ok'])

    def test_publication_audit_blocks_incomplete_database_snapshot_and_drift_overrides(self):
        manifest = complete_evidence_manifest()
        manifest['runtime_metadata']['database_manifest'] = {
            'found': True,
            'validation_errors': ['gtdbtk_db requires an exact non-placeholder version'],
        }
        self.assertIn('database_manifest', audit_run_manifest(manifest)['blockers'])

        # A manifest predating run-time snapshots records no parsed content.
        manifest = complete_evidence_manifest()
        manifest['runtime_metadata']['database_manifest'] = {
            'found': True,
            'sha256': DIGEST,
            'validation_errors': [],
        }
        report = audit_run_manifest(manifest)
        self.assertIn('database_manifest', report['blockers'])

        # Parsed resources but no canonical digest is still not tied to the run.
        manifest['runtime_metadata']['database_manifest']['resources'] = {'gunc_db': {'version': '2.1'}}
        self.assertIn('database_manifest', audit_run_manifest(manifest)['blockers'])

    def test_publication_audit_requires_container_digest_when_a_container_is_claimed(self):
        manifest = complete_evidence_manifest()
        manifest['runtime_metadata']['container'] = {'image': 'appam/tools:2026.1', 'image_digest': ''}
        report = audit_run_manifest(manifest)
        self.assertIn('runtime_identity', report['blockers'])
        self.assertIn(
            'without a valid immutable sha256 digest',
            next(check['detail'] for check in report['checks'] if check['id'] == 'runtime_identity'),
        )

        manifest['runtime_metadata']['container']['image_digest'] = 'latest'
        self.assertIn('runtime_identity', audit_run_manifest(manifest)['blockers'])

        manifest['runtime_metadata']['container']['image_digest'] = f'sha256:{DIGEST}'
        # A pinned container carries the runtime identity; per-env packages are then not required.
        manifest['runtime_metadata']['tools'] = {}
        self.assertTrue(audit_run_manifest(manifest)['ok'])

    def test_publication_audit_requires_package_identity_for_enabled_local_tools(self):
        manifest = complete_evidence_manifest()
        manifest['runtime_metadata']['tools'].pop('reporting_env')
        report = audit_run_manifest(manifest)
        self.assertIn('runtime_identity', report['blockers'])
        self.assertIn(
            'reporting_env',
            next(check['detail'] for check in report['checks'] if check['id'] == 'runtime_identity'),
        )

        manifest = complete_evidence_manifest()
        manifest['runtime_metadata']['tools'].pop('gtdbtk_env')
        report = audit_run_manifest(manifest)
        self.assertIn('runtime_identity', report['blockers'])
        self.assertIn(
            'gtdbtk_env',
            next(check['detail'] for check in report['checks'] if check['id'] == 'runtime_identity'),
        )

        # A disabled module must not gate the audit.
        manifest['runtime_metadata']['modules']['enable_gtdbtk'] = False
        self.assertTrue(audit_run_manifest(manifest)['ok'])

        # An enabled optional module must.
        manifest['runtime_metadata']['modules']['enable_antismash'] = True
        self.assertIn('runtime_identity', audit_run_manifest(manifest)['blockers'])

        manifest = complete_evidence_manifest()
        manifest['runtime_metadata']['modules']['enable_variants'] = True
        report = audit_run_manifest(manifest)
        self.assertIn('runtime_identity', report['blockers'])
        detail = next(check['detail'] for check in report['checks'] if check['id'] == 'runtime_identity')
        self.assertIn('freebayes_env', detail)
        self.assertIn('bcftools_env', detail)

    def test_publication_audit_requires_environment_and_maxquant_identity_for_paleoproteomics(self):
        manifest = complete_paleoproteomics_manifest()
        report = audit_run_manifest(manifest)
        self.assertTrue(report['ok'], report['blockers'])
        self.assertEqual(report['summary']['skipped'], 1)

        manifest['runtime_metadata']['maxquant_cmd_dll'] = {'exists': True}
        self.assertIn('runtime_identity', audit_run_manifest(manifest)['blockers'])

        manifest = complete_paleoproteomics_manifest()
        manifest['runtime_metadata']['runtime_env'] = {'type': 'environment_path', 'exists': True}
        self.assertIn('runtime_identity', audit_run_manifest(manifest)['blockers'])

    def test_publication_audit_warns_rather_than_passes_for_an_unknown_workflow(self):
        manifest = complete_evidence_manifest()
        manifest['workflow_id'] = 'future-workflow'
        report = audit_run_manifest(manifest)
        self.assertIn('runtime_identity', report['warnings'])
        self.assertNotIn('runtime_identity', report['blockers'])

        manifest = complete_evidence_manifest()
        manifest['mode'] = 'retry'
        manifest['source_runtime_verification'] = {'checked': True, 'matched': False, 'override_used': True}
        self.assertIn('provenance_continuity', audit_run_manifest(manifest)['blockers'])

    def test_publication_audit_reads_and_verifies_a_run_directory(self):
        run_dir = self.project_dir / 'workflow_runs' / 'appam-smk' / 'run-1'
        (run_dir / 'metadata').mkdir(parents=True)
        (run_dir / 'config').mkdir(parents=True)
        table = run_dir / 'config' / 'samples.resolved.tsv'
        table.write_text('sample_id\tforward_reads\treverse_reads\nS1\t/a_R1.fq\t/a_R2.fq\n', encoding='utf-8')

        manifest = complete_evidence_manifest()
        manifest['resolved_input_table'] = {
            'role': 'appam_smk_sample_manifest',
            'path': str(table),
            'sha256': hashlib.sha256(table.read_bytes()).hexdigest(),
            'size_bytes': table.stat().st_size,
            'row_count': 1,
        }
        manifest_path = run_dir / 'metadata' / 'manifest.run-1.json'
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')

        report = audit_run_path(run_dir)
        self.assertTrue(report['ok'], report['blockers'])
        self.assertTrue(report['manifest_path'].endswith('manifest.run-1.json'))

        table.write_text('sample_id\tforward_reads\treverse_reads\n', encoding='utf-8')
        self.assertIn('resolved_inputs', audit_run_path(run_dir)['blockers'])

        with self.assertRaisesRegex(ValueError, 'not found'):
            audit_run_path(self.project_dir / 'missing-run')


if __name__ == '__main__':
    unittest.main()
