from __future__ import annotations

import os
import shutil
from pathlib import Path

from ..database import DATABASE_FILE
from ..paths import (
    APPAM_PALEOPROTEOMICS_ROOT,
    APPAM_SMK_ROOT,
    DATABASES_ROOT,
    PROJECTS_ROOT,
    REPO_ROOT,
)
from .auth_service import count_active_admins
from .database_manifest import load_database_manifest, validate_database_manifest
from .local_executor import embedded_worker_running
from .runtime_resources import get_appam_smk_runtime_checks, get_appam_smk_runtime_settings


PUBLICATION_DATABASES = ('checkm2_db', 'gunc_db', 'gtdbtk_db', 'prokka_db')


def _check(
    check_id: str,
    label: str,
    status: str,
    detail: str,
    *,
    required: bool = False,
    publication_required: bool = False,
    capability: str | None = None,
    capability_required: bool = False,
    path: str | Path | None = None,
    action: str | None = None,
) -> dict:
    payload = {
        'id': check_id,
        'label': label,
        'status': status,
        'detail': detail,
        'required': required,
        'publication_required': publication_required,
        'capability': capability,
        'capability_required': capability_required,
    }
    if path is not None:
        payload['path'] = str(path)
    if action:
        payload['action'] = action
    return payload


def _path_check(
    check_id: str,
    label: str,
    path: str | Path | None,
    *,
    kind: str = 'directory',
    writable: bool = False,
    required: bool = True,
    capability: str | None = None,
    capability_required: bool = False,
) -> dict:
    raw_path = str(path or '').strip()
    if not raw_path:
        return _check(
            check_id,
            label,
            'error' if required or capability_required else 'warn',
            f'{kind.title()} is not configured.',
            required=required,
            capability=capability,
            capability_required=capability_required,
        )
    path = Path(raw_path).expanduser()
    exists = path.is_file() if kind == 'file' else path.is_dir()
    if not exists:
        return _check(
            check_id,
            label,
            'error' if required or capability_required else 'warn',
            f'{kind.title()} not found.',
            required=required,
            capability=capability,
            capability_required=capability_required,
            path=path,
        )
    if writable and not os.access(path, os.W_OK):
        return _check(
            check_id,
            label,
            'error' if required else 'warn',
            'Path exists but is not writable by the APPAM service account.',
            required=required,
            capability=capability,
            capability_required=capability_required,
            path=path,
        )
    return _check(
        check_id,
        label,
        'ok',
        'Ready.',
        required=required,
        capability=capability,
        capability_required=capability_required,
        path=path,
    )


def _command_check(
    check_id: str,
    label: str,
    value: str | None,
    *,
    required: bool,
    capability: str | None = None,
    capability_required: bool = False,
) -> dict:
    configured = str(value or '').strip()
    resolved = None
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_absolute() or '/' in configured:
            resolved = str(candidate) if candidate.is_file() and os.access(candidate, os.X_OK) else None
        else:
            resolved = shutil.which(configured)
    if resolved:
        return _check(
            check_id,
            label,
            'ok',
            'Executable resolved.',
            required=required,
            capability=capability,
            capability_required=capability_required,
            path=resolved,
        )
    return _check(
        check_id,
        label,
        'error' if required or capability_required else 'warn',
        f'Executable not found: {configured or "not configured"}',
        required=required,
        capability=capability,
        capability_required=capability_required,
    )


def _database_file_check() -> dict:
    path = Path(DATABASE_FILE).expanduser().resolve()
    target = path if path.exists() else path.parent
    ready = target.exists() and os.access(target, os.W_OK)
    return _check(
        'application_database',
        'Application database',
        'ok' if ready else 'error',
        'SQLite storage is writable.' if ready else 'SQLite file or its parent directory is not writable.',
        required=True,
        path=path,
    )


def _platform_checks() -> list[dict]:
    admin_count = count_active_admins()
    queue_backend = os.getenv('APPAM_QUEUE_BACKEND', 'local-db').strip().lower()
    worker_disabled = os.getenv('APPAM_DISABLE_EMBEDDED_WORKER', 'false').strip().lower() == 'true'
    if queue_backend == 'local-db':
        worker_ready = embedded_worker_running() or not worker_disabled
        worker_detail = 'Embedded worker is running.' if embedded_worker_running() else (
            'Embedded worker starts with the production server.' if not worker_disabled
            else 'Embedded worker is disabled; start an external worker before submitting jobs.'
        )
    else:
        worker_ready = bool(os.getenv('APPAM_REDIS_URL', '').strip())
        worker_detail = 'External RQ queue is configured.' if worker_ready else 'APPAM_REDIS_URL is not configured.'

    checks = [
        _check(
            'active_admin',
            'Administrator account',
            'ok' if admin_count else 'error',
            f'{admin_count} active administrator account(s).' if admin_count else 'Create at least one administrator account.',
            required=True,
            action='python backend/manage.py create-admin --username labadmin' if not admin_count else None,
        ),
        _path_check('repository_root', 'Application checkout', REPO_ROOT, required=True),
        _path_check('projects_root', 'Project storage', PROJECTS_ROOT, writable=True, required=True),
        _database_file_check(),
        _check(
            'queue_worker',
            'Workflow queue',
            'ok' if worker_ready else 'error',
            worker_detail,
            required=True,
        ),
    ]
    return checks


def _metagenomics_checks() -> list[dict]:
    checks = [
        _path_check('appam_smk_root', 'Metagenomics workflow', APPAM_SMK_ROOT / 'workflow' / 'Snakefile', kind='file'),
        _command_check('snakemake', 'Snakemake', os.getenv('APPAM_SNAKEMAKE_BIN', 'snakemake'), required=True),
    ]
    labels = {
        'databases_root': 'Database root',
        'preprocessing_env': 'Preprocessing environment',
        'mapping_env': 'Read mapping environment',
        'assembly_env': 'Assembly environment',
        'metawrap_env': 'Binning environment',
        'pydamage_env': 'Damage analysis environment',
        'checkm2_env': 'CheckM2 environment',
        'checkm2_db': 'CheckM2 database',
        'gunc_env': 'GUNC environment',
        'gunc_db': 'GUNC database',
        'gtdbtk_env': 'GTDB-Tk environment',
        'gtdbtk_db': 'GTDB-Tk database',
        'prokka_env': 'Prokka environment',
        'prokka_db': 'Prokka database',
    }
    settings = get_appam_smk_runtime_settings()
    for item in get_appam_smk_runtime_checks(settings):
        required = bool(item.get('required'))
        checks.append(_check(
            item['name'],
            labels.get(item['name'], item['name'].replace('_', ' ').title()),
            item.get('status', 'warn'),
            item.get('message', ''),
            required=required,
            capability='metagenomics',
            capability_required=required,
        ))
    return checks


def _paleoproteomics_checks() -> list[dict]:
    capability = 'paleoproteomics'
    runtime_env = os.path.expanduser(os.getenv('APPAM_PALEO_ENV', ''))
    maxquant = os.path.expanduser(os.getenv('APPAM_PALEO_MAXQUANT_CMD', ''))
    return [
        _path_check(
            'paleo_workflow_root',
            'Paleoproteomics workflow',
            APPAM_PALEOPROTEOMICS_ROOT / 'workflow' / 'Snakefile',
            kind='file',
            required=False,
            capability=capability,
            capability_required=True,
        ),
        _path_check(
            'paleo_runtime_env',
            'Paleoproteomics environment',
            runtime_env,
            required=False,
            capability=capability,
            capability_required=True,
        ),
        _command_check(
            'paleo_dotnet',
            '.NET runtime',
            os.getenv('APPAM_PALEO_DOTNET_BIN', 'dotnet'),
            required=False,
            capability=capability,
            capability_required=True,
        ),
        _path_check(
            'maxquant',
            'MaxQuant',
            maxquant,
            kind='file',
            required=False,
            capability=capability,
            capability_required=True,
        ),
        _command_check(
            'openms_fileconverter',
            'OpenMS FileConverter',
            os.getenv('APPAM_PALEO_OPENMS_FILECONVERTER', 'FileConverter'),
            required=False,
            capability=capability,
            capability_required=True,
        ),
        _command_check(
            'thermo_parser',
            'Thermo RAW converter',
            os.getenv('APPAM_PALEO_THERMO_RAW_FILE_PARSER', 'ThermoRawFileParser'),
            required=False,
            capability=capability,
        ),
        _command_check(
            'timsconvert',
            'Bruker converter',
            os.getenv('APPAM_PALEO_TIMSCONVERT_BIN', 'timsconvert'),
            required=False,
            capability=capability,
        ),
    ]


def _publication_checks() -> list[dict]:
    manifest = load_database_manifest()
    errors = validate_database_manifest(manifest, list(PUBLICATION_DATABASES))
    if errors:
        detail = '; '.join(errors[:4])
        if len(errors) > 4:
            detail += f'; {len(errors) - 4} more issue(s)'
        status = 'error'
    else:
        detail = 'Exact database releases are recorded for the publication preset.'
        status = 'ok'
    return [
        _check(
            'database_manifest',
            'Database version manifest',
            status,
            detail,
            publication_required=True,
            path=manifest.get('path'),
            action='Copy docker/database-manifest.example.json and replace every placeholder version.' if errors else None,
        ),
        _check(
            'database_root',
            'Mounted database root',
            'ok' if DATABASES_ROOT.is_dir() else 'error',
            'Database root is available.' if DATABASES_ROOT.is_dir() else 'Database root is missing.',
            publication_required=True,
            path=DATABASES_ROOT,
        ),
    ]


def collect_system_readiness() -> dict:
    groups = [
        {'id': 'platform', 'label': 'Platform', 'checks': _platform_checks()},
        {'id': 'metagenomics', 'label': 'Metagenomics', 'checks': _metagenomics_checks()},
        {'id': 'paleoproteomics', 'label': 'Paleoproteomics', 'optional': True, 'checks': _paleoproteomics_checks()},
        {'id': 'publication', 'label': 'Publication record', 'checks': _publication_checks()},
    ]
    checks = [check for group in groups for check in group['checks']]
    core_blockers = [check for check in checks if check.get('required') and check['status'] == 'error']
    publication_blockers = [
        check for check in checks
        if (check.get('required') or check.get('publication_required')) and check['status'] == 'error'
    ]
    capabilities = {}
    for capability in ('metagenomics', 'paleoproteomics'):
        capability_checks = [
            check for check in checks
            if check.get('capability') == capability and check.get('capability_required')
        ]
        capabilities[capability] = {
            'ready': bool(capability_checks) and not any(check['status'] == 'error' for check in capability_checks),
            'blockers': [check['id'] for check in capability_checks if check['status'] == 'error'],
        }
    capabilities['metagenomics']['ready'] = capabilities['metagenomics']['ready'] and not any(
        check['id'] in {'appam_smk_root', 'snakemake'} and check['status'] == 'error' for check in checks
    )

    return {
        'ready': not core_blockers,
        'publication_ready': not publication_blockers,
        'summary': {
            'ok': sum(check['status'] == 'ok' for check in checks),
            'warnings': sum(check['status'] == 'warn' for check in checks),
            'errors': sum(check['status'] == 'error' for check in checks),
            'core_blockers': len(core_blockers),
            'publication_blockers': len(publication_blockers),
        },
        'capabilities': capabilities,
        'groups': groups,
    }
