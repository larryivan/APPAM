import json
import os
from pathlib import Path

from ..paths import DATABASES_ROOT
from .runtime_resources import get_appam_smk_runtime_settings
from .workflow_results import resource_fingerprint


MANIFEST_NAMES = ('appam-db-manifest.json', 'db-manifest.json', 'database-manifest.json')
PLACEHOLDER_VERSION_MARKERS = (
    'placeholder',
    'record-',
    'container-configured',
    'downloaded-with',
    'unknown',
    'latest',
    'global-or-local',
    'online-or-local',
)


def _candidate_paths() -> list[Path]:
    configured = os.getenv('APPAM_DB_MANIFEST', '').strip()
    candidates = [Path(configured)] if configured else []
    candidates.extend(DATABASES_ROOT / name for name in MANIFEST_NAMES)
    return candidates


def load_database_manifest() -> dict:
    for path in _candidate_paths():
        if not path:
            continue
        expanded = Path(os.path.expanduser(str(path)))
        if not expanded.is_file():
            continue
        try:
            payload = json.loads(expanded.read_text(encoding='utf-8'))
        except Exception as exc:
            return {
                'found': False,
                'path': str(expanded),
                'error': f'Could not parse database manifest: {exc}',
                'resources': infer_database_resources(),
            }
        if not isinstance(payload, dict):
            return {
                'found': False,
                'path': str(expanded),
                'error': 'Database manifest must contain a JSON object.',
                'resources': infer_database_resources(),
            }
        payload.setdefault('resources', {})
        payload['found'] = True
        payload['path'] = str(expanded)
        return payload

    return {
        'found': False,
        'path': str(DATABASES_ROOT / MANIFEST_NAMES[0]),
        'resources': infer_database_resources(),
    }


def infer_database_resources() -> dict:
    settings = get_appam_smk_runtime_settings({})
    databases = settings.get('databases', {})
    inferred = {}
    for name in ('checkm1_db', 'checkm2_db', 'gunc_db', 'gtdbtk_db', 'eggnog_db', 'rgi_db'):
        inferred[name] = resource_fingerprint(databases.get(name))
    inferred['krakenuniq_db'] = resource_fingerprint(os.getenv('APPAM_KRAKENUNIQ_DB', ''))
    inferred['abricate_db'] = {'name': databases.get('abricate_db'), 'builtin': True}
    inferred['prokka_db'] = {'name': databases.get('prokka_db'), 'builtin': True}
    inferred['antismash_db'] = {'name': databases.get('antismash_db'), 'builtin': True}
    inferred['rgi_db_mode'] = databases.get('rgi_db_mode')
    return inferred


def validate_database_manifest(manifest: dict, required_resources: list[str]) -> list[str]:
    errors = []
    if not manifest.get('found'):
        return ['database manifest was not found'] if required_resources else []
    if manifest.get('schema_version') != 1:
        errors.append('schema_version must be 1')
    resources = manifest.get('resources')
    if not isinstance(resources, dict):
        return [*errors, 'resources must be an object']

    for name in required_resources:
        resource = resources.get(name)
        if not isinstance(resource, dict):
            errors.append(f'missing resource entry: {name}')
            continue
        version = str(resource.get('version') or '').strip()
        normalized = version.lower()
        if not version or any(marker in normalized for marker in PLACEHOLDER_VERSION_MARKERS):
            errors.append(f'{name} requires an exact non-placeholder version')
    return errors
