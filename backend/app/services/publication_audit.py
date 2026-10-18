"""Deterministic completeness audit for an archived workflow run.

The audit answers one question only: does this run record enough identity to be
re-created and checked by a reader who has nothing but the archived bundle? It
never judges scientific validity, data quality, or whether a result supports a
claim.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import yaml

from .database_manifest import validate_database_manifest


AUDIT_SCHEMA_VERSION = 2
AUDIT_SCOPE = (
    'Evidence completeness only. Scientific validity, data quality, and claim support are not assessed.'
)

_SHA256 = re.compile(r'^[0-9a-f]{64}$')
_GIT_COMMIT = re.compile(r'^[0-9a-f]{40,64}$')
_CONTAINER_DIGEST = re.compile(r'^sha256:[0-9a-f]{64}$')
_FROZEN_MODES = {'retry', 'resume'}

# Environments APPAM-SMK always executes, plus the ones each optional module adds.
# Mirrors get_appam_smk_runtime_checks so only enabled tools gate the audit.
_APPAM_SMK_CORE_TOOLS = (
    'preprocessing_env',
    'mapping_env',
    'assembly_env',
    'metawrap_env',
    'pydamage_env',
    'reporting_env',
)
_APPAM_SMK_MODULE_TOOLS = {
    'enable_bin_refinement': ('checkm1_env',),
    'enable_checkm1': ('checkm1_env',),
    'enable_checkm2': ('checkm2_env',),
    'enable_gunc': ('gunc_env',),
    'enable_gtdbtk': ('gtdbtk_env',),
    'enable_prokka': ('prokka_env',),
    'enable_eggnog': ('eggnog_env',),
    'enable_abricate': ('abricate_env',),
    'enable_rgi': ('rgi_env',),
    'enable_antismash': ('antismash_env',),
    'enable_variants': ('freebayes_env', 'bcftools_env'),
}


def _is_sha256(value) -> bool:
    return bool(_SHA256.fullmatch(str(value or '').strip().lower()))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_sha256(value) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False,
    ).encode('utf-8')
    return _sha256_bytes(payload)


def _check(check_id: str, label: str, status: str, detail: str, *, severity: str = 'blocker') -> dict:
    return {
        'id': check_id,
        'label': label,
        'status': status,
        'severity': severity,
        'detail': detail,
    }


def _mapping(value) -> dict:
    return value if isinstance(value, dict) else {}


def _run_mode_check(manifest: dict) -> dict:
    if manifest.get('dry_run'):
        return _check(
            'run_mode',
            'Executed run',
            'error',
            'This was a dry run. Dry runs verify software behaviour and are not result evidence.',
        )
    return _check('run_mode', 'Executed run', 'ok', 'The workflow was executed rather than dry-run.')


def _software_revision_check(manifest: dict) -> dict:
    revision = _mapping(manifest.get('workflow_revision'))
    commit = str(revision.get('commit') or '').strip().lower()
    if not _GIT_COMMIT.fullmatch(commit):
        return _check(
            'software_revision',
            'Software revision',
            'error',
            'No valid full Git commit was recorded for this run.',
        )
    dirty = revision.get('dirty')
    if dirty is None:
        return _check(
            'software_revision',
            'Software revision',
            'error',
            f'Commit {commit} was recorded but the checkout state could not be determined.',
        )
    if dirty:
        return _check(
            'software_revision',
            'Software revision',
            'error',
            f'Commit {commit} was recorded from a checkout with uncommitted changes.',
        )
    return _check('software_revision', 'Software revision', 'ok', f'Clean checkout at commit {commit}.')


def _effective_config_check(manifest: dict) -> dict:
    config = _mapping(manifest.get('effective_config'))
    digest = str(manifest.get('effective_config_sha256') or '').strip().lower()
    if not config:
        return _check('effective_config', 'Effective configuration', 'error', 'No resolved configuration was archived.')
    if not _SHA256.fullmatch(digest):
        return _check(
            'effective_config',
            'Effective configuration',
            'error',
            'The archived configuration has no SHA-256 digest.',
        )
    actual = _sha256_bytes(yaml.safe_dump(config, sort_keys=False).encode('utf-8'))
    if actual != digest:
        return _check(
            'effective_config',
            'Effective configuration',
            'error',
            'The archived effective configuration no longer matches its recorded SHA-256.',
        )
    return _check('effective_config', 'Effective configuration', 'ok', f'Configuration digest {digest[:12]}.')


def _resolved_inputs_check(manifest: dict, *, verify_files: bool = False) -> dict:
    validation = _mapping(manifest.get('input_validation'))
    if validation and not validation.get('ok'):
        return _check(
            'resolved_inputs',
            'Resolved input table',
            'error',
            'The archived input validation did not pass.',
        )

    record = _mapping(manifest.get('resolved_input_table'))
    paths = _mapping(manifest.get('paths'))
    legacy_path = paths.get('resolved_sample_manifest') or paths.get('resolved_sample_table')
    if not record:
        if legacy_path:
            return _check(
                'resolved_inputs',
                'Resolved input table',
                'error',
                'This manifest records only a path to the resolved sample table, with no digest. '
                'A path is not archived evidence; re-run to record a SHA-256.',
            )
        return _check(
            'resolved_inputs',
            'Resolved input table',
            'error',
            'No resolved sample table with absolute paths was archived.',
        )

    digest = str(record.get('sha256') or '').strip().lower()
    if not _is_sha256(digest):
        return _check(
            'resolved_inputs',
            'Resolved input table',
            'error',
            'The resolved sample table was recorded without a valid SHA-256 digest.',
        )

    row_count = record.get('row_count')
    summary = f'{row_count} sample row(s), digest {digest[:12]}' if row_count is not None else f'digest {digest[:12]}'
    if not verify_files:
        return _check('resolved_inputs', 'Resolved input table', 'ok', f'Resolved table recorded with {summary}.')

    recorded_path = str(record.get('path') or '').strip()
    if not recorded_path:
        return _check(
            'resolved_inputs',
            'Resolved input table',
            'error',
            'The resolved sample table digest was recorded without a path, so it cannot be verified.',
        )
    path = Path(recorded_path).expanduser()
    if not path.is_file():
        return _check(
            'resolved_inputs',
            'Resolved input table',
            'error',
            f'The recorded resolved sample table is missing: {path}',
        )
    try:
        actual = _sha256_file(path)
    except OSError as exc:
        return _check(
            'resolved_inputs',
            'Resolved input table',
            'error',
            f'The recorded resolved sample table could not be read: {exc}',
        )
    if actual != digest:
        return _check(
            'resolved_inputs',
            'Resolved input table',
            'error',
            'The resolved sample table on disk no longer matches its recorded SHA-256. '
            'The archived input table was modified after the run.',
        )
    return _check('resolved_inputs', 'Resolved input table', 'ok', f'Resolved table verified against {summary}.')


def _input_identity_check(manifest: dict) -> dict:
    inputs = manifest.get('inputs')
    if not isinstance(inputs, list) or not inputs:
        return _check('input_identity', 'Input identity', 'error', 'No input fingerprints were recorded.')

    missing = []
    metadata_only = []
    for item in inputs:
        entry = _mapping(item)
        path = str(entry.get('path') or 'unknown input')
        if not entry.get('exists'):
            missing.append(path)
            continue
        if entry.get('type') == 'directory':
            if entry.get('fingerprint_mode') != 'sha256':
                metadata_only.append(path)
        elif not _SHA256.fullmatch(str(entry.get('sha256') or '').lower()):
            metadata_only.append(path)

    if missing:
        return _check(
            'input_identity',
            'Input identity',
            'error',
            f'{len(missing)} input(s) were missing when the run was prepared: {", ".join(missing[:3])}',
        )
    if metadata_only:
        return _check(
            'input_identity',
            'Input identity',
            'error',
            f'{len(metadata_only)} of {len(inputs)} input(s) recorded size/mtime only. '
            'Re-run with the Publication run preset to record SHA-256 input hashes.',
        )
    return _check('input_identity', 'Input identity', 'ok', f'{len(inputs)} input(s) recorded with SHA-256 hashes.')


def _container_identity(runtime_metadata: dict) -> tuple[bool, str | None, str]:
    """Return (container claimed, digest, image name) for the run.

    ``image`` is literally ``local`` for a native Mamba deployment, where package
    fingerprints rather than an image digest carry the runtime identity.
    """
    container = _mapping(runtime_metadata.get('container'))
    image = str(container.get('image') or '').strip()
    digest = str(container.get('image_digest') or '').strip() or None
    claimed = bool(image) and image.lower() not in {'local', 'none'}
    return claimed, digest, image


def _appam_smk_runtime_identity(runtime_metadata: dict) -> dict:
    claimed, digest, image = _container_identity(runtime_metadata)
    if claimed:
        if not digest or not _CONTAINER_DIGEST.fullmatch(digest.lower()):
            return _check(
                'runtime_identity',
                'Runtime identity',
                'error',
                f'Container image "{image}" was claimed without a valid immutable sha256 digest. '
                'Record APPAM_CONTAINER_IMAGE_DIGEST so the runtime can be re-pulled exactly.',
            )
        return _check('runtime_identity', 'Runtime identity', 'ok', f'Container image {image} pinned to {digest}.')

    modules = _mapping(runtime_metadata.get('modules'))
    required = list(_APPAM_SMK_CORE_TOOLS)
    for module, tools in _APPAM_SMK_MODULE_TOOLS.items():
        if modules.get(module):
            required.extend(tools)

    tools = _mapping(runtime_metadata.get('tools'))
    if not tools:
        return _check(
            'runtime_identity',
            'Runtime identity',
            'error',
            'No container digest and no environment fingerprints were recorded.',
        )

    unidentified = []
    for name in dict.fromkeys(required):
        fingerprint = _mapping(tools.get(name))
        if not _is_sha256(fingerprint.get('packages_sha256')):
            unidentified.append(name)
    if unidentified:
        return _check(
            'runtime_identity',
            'Runtime identity',
            'error',
            f'{len(unidentified)} enabled environment(s) have no package fingerprint: '
            f'{", ".join(sorted(unidentified)[:4])}. A local run must record installed package identity.',
        )
    return _check(
        'runtime_identity',
        'Runtime identity',
        'ok',
        f'{len(set(required))} enabled environment(s) fingerprinted by installed packages.',
    )


def _paleoproteomics_runtime_identity(runtime_metadata: dict) -> dict:
    runtime_env = _mapping(runtime_metadata.get('runtime_env'))
    maxquant = _mapping(runtime_metadata.get('maxquant_cmd_dll'))
    missing = []
    if not _is_sha256(runtime_env.get('packages_sha256')):
        missing.append('conversion environment packages')
    if not (maxquant.get('exists') and _is_sha256(maxquant.get('sha256'))):
        missing.append('MaxQuantCmd.dll content hash')
    if missing:
        return _check(
            'runtime_identity',
            'Runtime identity',
            'error',
            f'Paleoproteomics runtime identity is incomplete: {", ".join(missing)}.',
        )
    return _check(
        'runtime_identity',
        'Runtime identity',
        'ok',
        'Conversion environment packages and MaxQuant binary are both fingerprinted.',
    )


def _runtime_identity_check(manifest: dict) -> dict:
    runtime_metadata = _mapping(manifest.get('runtime_metadata'))
    if not runtime_metadata:
        return _check(
            'runtime_identity',
            'Runtime identity',
            'error',
            'No environment or binary fingerprints were recorded.',
        )

    workflow_id = str(manifest.get('workflow_id') or '').strip()
    if workflow_id == 'appam-smk':
        return _appam_smk_runtime_identity(runtime_metadata)
    if workflow_id == 'appam-paleoproteomics':
        return _paleoproteomics_runtime_identity(runtime_metadata)
    return _check(
        'runtime_identity',
        'Runtime identity',
        'warn',
        f'Runtime fingerprints are present but this audit has no depth rule for workflow "{workflow_id or "unknown"}". '
        'Verify the runtime record manually.',
        severity='advisory',
    )


def _database_manifest_check(manifest: dict) -> dict:
    runtime_metadata = _mapping(manifest.get('runtime_metadata'))
    if 'database_manifest' not in runtime_metadata:
        return _check(
            'database_manifest',
            'Database version manifest',
            'skipped',
            'This workflow does not consume manifest-described reference databases.',
        )
    snapshot = _mapping(runtime_metadata.get('database_manifest'))
    if not snapshot.get('found'):
        return _check(
            'database_manifest',
            'Database version manifest',
            'error',
            'No database version manifest was present when the run was prepared.',
        )
    errors = snapshot.get('validation_errors') or []
    if errors:
        detail = '; '.join(str(error) for error in errors[:3])
        if len(errors) > 3:
            detail += f'; {len(errors) - 3} more issue(s)'
        return _check('database_manifest', 'Database version manifest', 'error', f'Manifest incomplete: {detail}')
    if not _mapping(snapshot.get('resources')):
        return _check(
            'database_manifest',
            'Database version manifest',
            'error',
            'The run recorded no parsed database resources, so the manifest content is not archived.',
        )
    canonical = str(snapshot.get('canonical_sha256') or '').strip().lower()
    if not _is_sha256(canonical):
        return _check(
            'database_manifest',
            'Database version manifest',
            'error',
            'This manifest predates run-time database snapshots and carries no canonical digest, '
            'so the recorded database versions cannot be tied to this run.',
        )
    canonical_payload = {
        'schema_version': snapshot.get('schema_version'),
        'template': bool(snapshot.get('template')),
        'resources': snapshot.get('resources') or {},
    }
    if _canonical_sha256(canonical_payload) != canonical:
        return _check(
            'database_manifest',
            'Database version manifest',
            'error',
            'The archived database snapshot no longer matches its canonical SHA-256.',
        )
    required_resources = snapshot.get('required_resources')
    if not isinstance(required_resources, list):
        return _check(
            'database_manifest',
            'Database version manifest',
            'error',
            'The run did not record which database resources its enabled modules required.',
        )
    recomputed_errors = validate_database_manifest(snapshot, [str(name) for name in required_resources])
    if recomputed_errors:
        detail = '; '.join(recomputed_errors[:3])
        if len(recomputed_errors) > 3:
            detail += f'; {len(recomputed_errors) - 3} more issue(s)'
        return _check(
            'database_manifest',
            'Database version manifest',
            'error',
            f'Archived manifest fails current validation: {detail}',
        )
    if not _is_sha256(snapshot.get('sha256')):
        return _check(
            'database_manifest',
            'Database version manifest',
            'warn',
            f'Database snapshot {canonical[:12]} is archived, but the source file digest was not recorded.',
            severity='advisory',
        )
    return _check(
        'database_manifest',
        'Database version manifest',
        'ok',
        f'Run-time snapshot {canonical[:12]} covers '
        f'{len(_mapping(snapshot.get("resources")))} database resource(s).',
    )


def _command_check(manifest: dict) -> dict:
    command = manifest.get('command')
    if not isinstance(command, list) or not command:
        return _check('command_recorded', 'Command line', 'error', 'No command line was recorded for this run.')
    return _check('command_recorded', 'Command line', 'ok', f'{len(command)} argument(s) recorded verbatim.')


def _continuity_check(manifest: dict) -> dict:
    mode = str(manifest.get('mode') or 'run').strip().lower()
    runtime_verification = _mapping(manifest.get('source_runtime_verification'))
    if runtime_verification.get('override_used'):
        return _check(
            'provenance_continuity',
            'Retry/resume continuity',
            'error',
            'Runtime drift was accepted through APPAM_ALLOW_RUNTIME_DRIFT_ON_RETRY. '
            'Report this run as a deviation or re-run it on the recorded runtime.',
        )
    if mode not in _FROZEN_MODES:
        return _check(
            'provenance_continuity',
            'Retry/resume continuity',
            'ok',
            'This run was submitted directly rather than retried or resumed.',
        )
    input_verification = _mapping(manifest.get('source_input_verification'))
    if not input_verification.get('checked') or not runtime_verification.get('checked'):
        return _check(
            'provenance_continuity',
            'Retry/resume continuity',
            'warn',
            f'The source run of this {mode} could not be fully re-verified: '
            f'{input_verification.get("reason") or runtime_verification.get("reason") or "no reason recorded"}.',
            severity='advisory',
        )
    return _check(
        'provenance_continuity',
        'Retry/resume continuity',
        'ok',
        f'Inputs and runtime matched the source run of this {mode}.',
    )


def _preflight_check(manifest: dict) -> dict:
    if not manifest.get('preflight_id'):
        return _check(
            'preflight_recorded',
            'Preflight record',
            'warn',
            'No preflight record is linked to this run.',
            severity='advisory',
        )
    return _check(
        'preflight_recorded',
        'Preflight record',
        'ok',
        f'Linked to preflight {manifest["preflight_id"]}.',
        severity='advisory',
    )


# _resolved_inputs_check is run separately because it can touch the filesystem.
_CHECKS = (
    _run_mode_check,
    _software_revision_check,
    _effective_config_check,
    _input_identity_check,
    _runtime_identity_check,
    _database_manifest_check,
    _command_check,
    _continuity_check,
    _preflight_check,
)

_CHECK_ORDER = [
    'run_mode',
    'software_revision',
    'effective_config',
    'resolved_inputs',
    'input_identity',
    'runtime_identity',
    'database_manifest',
    'command_recorded',
    'provenance_continuity',
    'preflight_recorded',
]


def audit_run_manifest(manifest: dict | None, *, verify_files: bool = False) -> dict:
    """Audit one workflow run manifest for archival completeness.

    ``verify_files`` re-hashes the recorded resolved input table on disk. Callers
    with filesystem access to the run should enable it; pure manifest consumers
    should not.
    """
    if not isinstance(manifest, dict) or not manifest:
        return {
            'schema_version': AUDIT_SCHEMA_VERSION,
            'scope': AUDIT_SCOPE,
            'ok': False,
            'run_id': None,
            'workflow_id': None,
            'mode': None,
            'summary': {'ok': 0, 'warnings': 0, 'blockers': 1, 'skipped': 0},
            'blockers': ['manifest_present'],
            'warnings': [],
            'checks': [
                _check('manifest_present', 'Run manifest', 'error', 'No run manifest was available for this run.')
            ],
        }

    checks = [_resolved_inputs_check(manifest, verify_files=verify_files)]
    checks.extend(check(manifest) for check in _CHECKS)
    checks.sort(key=lambda check: _CHECK_ORDER.index(check['id']))
    blockers = [check['id'] for check in checks if check['severity'] == 'blocker' and check['status'] == 'error']
    warnings = [check['id'] for check in checks if check['status'] == 'warn']
    return {
        'schema_version': AUDIT_SCHEMA_VERSION,
        'scope': AUDIT_SCOPE,
        'ok': not blockers,
        'run_id': manifest.get('run_id'),
        'workflow_id': manifest.get('workflow_id'),
        'mode': manifest.get('mode'),
        'summary': {
            'ok': sum(check['status'] == 'ok' for check in checks),
            'warnings': len(warnings),
            'blockers': len(blockers),
            'skipped': sum(check['status'] == 'skipped' for check in checks),
        },
        'blockers': blockers,
        'warnings': warnings,
        'checks': checks,
    }


def find_run_manifest(target: str | Path) -> Path:
    """Resolve a manifest file from a manifest path or a workflow run directory."""
    path = Path(target).expanduser()
    if path.is_file():
        return path
    if path.is_dir():
        candidates = sorted(path.glob('metadata/manifest.*.json')) or sorted(path.glob('manifest.*.json'))
        if candidates:
            return candidates[0]
        raise ValueError(f'No run manifest found under {path}')
    raise ValueError(f'Run manifest or run directory not found: {path}')


def audit_run_path(target: str | Path) -> dict:
    """Audit a run from disk, re-hashing the archived files it points at."""
    manifest_path = find_run_manifest(target)
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f'Could not read run manifest {manifest_path}: {exc}') from exc
    if not isinstance(manifest, dict):
        raise ValueError(f'Run manifest must contain a JSON object: {manifest_path}')
    report = audit_run_manifest(manifest, verify_files=True)
    report['manifest_path'] = str(manifest_path.resolve())
    return report
