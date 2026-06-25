from __future__ import annotations

import os
from pathlib import Path

from ..paths import DATABASES_ROOT
from .workflow_results import resource_fingerprint


TRUE_VALUES = {'1', 'true', 'yes', 'on'}
FALSE_VALUES = {'0', 'false', 'no', 'off'}


def _first_value(*values):
    for value in values:
        if value not in (None, ''):
            return value
    return None


def _env_value(*names):
    for name in names:
        value = os.getenv(name, '').strip()
        if value:
            return value
    return None


def _bool_setting(params: dict, name: str, default: bool) -> bool:
    value = params.get(name)
    if value in (None, ''):
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return default


def _database_path(value: str | Path) -> str:
    path = Path(os.path.expanduser(str(value)))
    if not path.is_absolute():
        path = DATABASES_ROOT / path
    return str(path.resolve())


def _database_setting(params: dict, param_names: tuple[str, ...], env_names: tuple[str, ...], default_name: str) -> str:
    param_values = [params.get(name) for name in param_names]
    value = _first_value(*param_values, _env_value(*env_names), DATABASES_ROOT / default_name)
    return _database_path(value)


def _setting(params: dict, param_names: tuple[str, ...], env_names: tuple[str, ...], default: str | None = None) -> str | None:
    param_values = [params.get(name) for name in param_names]
    value = _first_value(*param_values, _env_value(*env_names), default)
    return str(value) if value not in (None, '') else None


def get_appam_smk_runtime_settings(params: dict | None = None) -> dict:
    params = params or {}
    return {
        'databases_root': str(DATABASES_ROOT),
        'tools': {
            'metawrap_env': _setting(params, ('metawrap_env',), ('APPAM_SMK_METAWRAP_ENV',), '/opt/conda/envs/metawrap'),
            'pydamage_env': _setting(params, ('pydamage_env',), ('APPAM_SMK_PYDAMAGE_ENV',), '/opt/conda/envs/ancient_dna'),
            'checkm2_env': _setting(params, ('checkm2_env',), ('APPAM_SMK_CHECKM2_ENV',), '/opt/conda/envs/checkm2'),
            'gunc_env': _setting(params, ('gunc_env',), ('APPAM_SMK_GUNC_ENV',), '/opt/conda/envs/binning'),
            'prokka_env': _setting(params, ('prokka_env',), ('APPAM_SMK_PROKKA_ENV',), '/opt/conda/envs/prokka'),
            'eggnog_env': _setting(params, ('eggnog_env',), ('APPAM_SMK_EGGNOG_ENV',), '/opt/conda/envs/eggnog_py310'),
            'abricate_env': _setting(params, ('abricate_env',), ('APPAM_SMK_ABRICATE_ENV',), '/opt/conda/envs/abricate'),
            'rgi_env': _setting(params, ('rgi_env',), ('APPAM_SMK_RGI_ENV',), '/opt/conda/envs/rgi'),
            'antismash_env': _setting(params, ('antismash_env',), ('APPAM_SMK_ANTISMASH_ENV',), '/opt/conda/envs/antismash'),
        },
        'databases': {
            'checkm1_db': _database_setting(
                params,
                ('checkm1_db', 'checkm_db'),
                ('APPAM_SMK_CHECKM1_DB', 'APPAM_SMK_CHECKM_DB'),
                'checkm',
            ),
            'checkm2_db': _database_setting(params, ('checkm2_db',), ('APPAM_SMK_CHECKM2_DB',), 'checkm2'),
            'gunc_db': _database_setting(params, ('gunc_db',), ('APPAM_SMK_GUNC_DB',), 'gunc'),
            'eggnog_db': _database_setting(params, ('eggnog_db',), ('APPAM_SMK_EGGNOG_DB',), 'eggnog'),
            'abricate_db': _setting(params, ('abricate_db',), ('APPAM_SMK_ABRICATE_DB',), 'builtin'),
            'rgi_db_mode': _setting(params, ('rgi_db_mode',), ('APPAM_SMK_RGI_DB_MODE',), 'online'),
            'rgi_db': _setting(params, ('rgi_db',), ('APPAM_SMK_RGI_DB',), None),
            'antismash_db': _setting(params, ('antismash_db',), ('APPAM_SMK_ANTISMASH_DB',), 'builtin'),
            'prokka_db': _setting(params, ('prokka_db',), ('APPAM_SMK_PROKKA_DB',), 'builtin'),
        },
        'modules': {
            'enable_checkm2': _bool_setting(params, 'enable_checkm2', True),
            'enable_gunc': _bool_setting(params, 'enable_gunc', True),
            'enable_prokka': _bool_setting(params, 'enable_prokka', True),
            'enable_eggnog': _bool_setting(params, 'enable_eggnog', True),
            'enable_abricate': _bool_setting(params, 'enable_abricate', True),
            'enable_rgi': _bool_setting(params, 'enable_rgi', False),
            'enable_antismash': _bool_setting(params, 'enable_antismash', True),
        },
    }


def _path_check(name: str, value: str | None, label: str, *, required: bool = True, kind: str = 'dir') -> dict:
    if not value:
        status = 'error' if required else 'warn'
        return {'name': name, 'status': status, 'required': required, 'message': f'{label} is not configured'}
    path = Path(str(value))
    if kind == 'file_or_dir':
        ok = path.exists()
        expected = 'file or directory'
    elif kind == 'file':
        ok = path.is_file()
        expected = 'file'
    else:
        ok = path.is_dir()
        expected = 'directory'
    if ok:
        return {'name': name, 'status': 'ok', 'required': required, 'message': f'{label}: {path}'}
    status = 'error' if required else 'warn'
    return {'name': name, 'status': status, 'required': required, 'message': f'{label} {expected} not found: {path}'}


def _env_check(name: str, value: str | None, label: str, *, required: bool = True) -> dict:
    if not value:
        status = 'error' if required else 'warn'
        return {'name': name, 'status': status, 'required': required, 'message': f'{label} environment is not configured'}
    path = Path(str(value))
    if path.is_absolute():
        if path.exists():
            return {'name': name, 'status': 'ok', 'required': required, 'message': f'{label} environment: {path}'}
        status = 'error' if required else 'warn'
        return {'name': name, 'status': status, 'required': required, 'message': f'{label} environment not found: {path}'}
    return {'name': name, 'status': 'ok', 'required': required, 'message': f'{label} environment setting: {value}'}


def get_appam_smk_runtime_checks(settings: dict | None = None) -> list[dict]:
    settings = settings or get_appam_smk_runtime_settings()
    tools = settings['tools']
    databases = settings['databases']
    modules = settings['modules']

    checks = [
        _path_check('databases_root', settings['databases_root'], 'Database mount root', required=False, kind='dir'),
        _env_check('metawrap_env', tools.get('metawrap_env'), 'MetaWRAP'),
        _env_check('pydamage_env', tools.get('pydamage_env'), 'PyDamage'),
        _path_check('checkm1_db', databases.get('checkm1_db'), 'CheckM1 database', kind='dir'),
    ]

    if modules.get('enable_checkm2'):
        checks.append(_env_check('checkm2_env', tools.get('checkm2_env'), 'CheckM2'))
        checks.append(_path_check('checkm2_db', databases.get('checkm2_db'), 'CheckM2 database', kind='dir'))
    if modules.get('enable_gunc'):
        checks.append(_env_check('gunc_env', tools.get('gunc_env'), 'GUNC'))
        checks.append(_path_check('gunc_db', databases.get('gunc_db'), 'GUNC database', kind='file_or_dir'))
    if modules.get('enable_prokka'):
        checks.append(_env_check('prokka_env', tools.get('prokka_env'), 'Prokka'))
        checks.append({'name': 'prokka_db', 'status': 'ok', 'required': False, 'message': f"Prokka database: {databases.get('prokka_db')}"})
    if modules.get('enable_eggnog'):
        if not modules.get('enable_prokka'):
            checks.append({'name': 'eggnog_requires_prokka', 'status': 'error', 'required': True, 'message': 'eggNOG-mapper annotation requires Prokka protein FASTA output; enable Prokka or disable eggNOG.'})
        checks.append(_env_check('eggnog_env', tools.get('eggnog_env'), 'eggNOG-mapper'))
        checks.append(_path_check('eggnog_db', databases.get('eggnog_db'), 'eggNOG database', kind='dir'))
    if modules.get('enable_abricate'):
        checks.append(_env_check('abricate_env', tools.get('abricate_env'), 'ABRicate'))
        checks.append({'name': 'abricate_db', 'status': 'ok', 'required': False, 'message': f"ABRicate database: {databases.get('abricate_db')}"})
    if modules.get('enable_rgi'):
        checks.append(_env_check('rgi_env', tools.get('rgi_env'), 'RGI'))
        rgi_mode = str(databases.get('rgi_db_mode') or 'online').lower()
        if rgi_mode == 'local':
            checks.append(_path_check('rgi_db', databases.get('rgi_db'), 'RGI database', kind='dir'))
        else:
            checks.append({'name': 'rgi_db_mode', 'status': 'warn', 'required': False, 'message': 'RGI is configured for online/non-local database mode; record this in provenance.'})
    if modules.get('enable_antismash'):
        checks.append(_env_check('antismash_env', tools.get('antismash_env'), 'antiSMASH'))
        checks.append({'name': 'antismash_db', 'status': 'ok', 'required': False, 'message': f"antiSMASH database: {databases.get('antismash_db')}"})
        checks.append({'name': 'antismash_resources', 'status': 'warn', 'required': False, 'message': 'antiSMASH can be CPU and memory intensive; consider disabling it for quick validation runs.'})

    return checks


def validate_appam_smk_runtime(settings: dict | None = None) -> list[dict]:
    checks = get_appam_smk_runtime_checks(settings)
    errors = [check for check in checks if check.get('required') and check.get('status') == 'error']
    if errors:
        details = '; '.join(check['message'] for check in errors)
        raise ValueError(f'Missing APPAM-SMK runtime resources: {details}')
    return checks


def collect_appam_smk_runtime_metadata(settings: dict | None = None) -> dict:
    settings = settings or get_appam_smk_runtime_settings()
    databases = settings.get('databases', {})
    return {
        'container': {
            'image': os.getenv('APPAM_CONTAINER_IMAGE', os.getenv('APPAM_WORKFLOW_RUNNER_IMAGE', 'local')),
            'image_digest': os.getenv('APPAM_CONTAINER_IMAGE_DIGEST', ''),
        },
        'databases': {
            'checkm1_db': resource_fingerprint(databases.get('checkm1_db')),
            'checkm2_db': resource_fingerprint(databases.get('checkm2_db')),
            'gunc_db': resource_fingerprint(databases.get('gunc_db')),
            'eggnog_db': resource_fingerprint(databases.get('eggnog_db')),
            'abricate_db': databases.get('abricate_db'),
            'rgi_db_mode': databases.get('rgi_db_mode'),
            'rgi_db': resource_fingerprint(databases.get('rgi_db')) if databases.get('rgi_db') else {'path': None, 'exists': False},
            'antismash_db': databases.get('antismash_db'),
            'prokka_db': databases.get('prokka_db'),
        },
        'tools': settings.get('tools', {}),
        'modules': settings.get('modules', {}),
    }
