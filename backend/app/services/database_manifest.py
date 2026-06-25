import json
import os
from pathlib import Path

from ..paths import DATABASES_ROOT
from .runtime_resources import get_appam_smk_runtime_settings
from .workflow_results import resource_fingerprint


MANIFEST_NAMES = ('appam-db-manifest.json', 'db-manifest.json', 'database-manifest.json')


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
    for name in ('checkm1_db', 'checkm2_db', 'gunc_db', 'eggnog_db', 'rgi_db'):
        inferred[name] = resource_fingerprint(databases.get(name))
    inferred['abricate_db'] = {'name': databases.get('abricate_db'), 'builtin': True}
    inferred['prokka_db'] = {'name': databases.get('prokka_db'), 'builtin': True}
    inferred['antismash_db'] = {'name': databases.get('antismash_db'), 'builtin': True}
    inferred['rgi_db_mode'] = databases.get('rgi_db_mode')
    return inferred
