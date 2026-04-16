import os
import json
import shlex
import shutil
from pathlib import Path

import yaml

from .execution_backends import build_backend_command_spec, resolve_backend_name
from .workflow_runtime import get_workflow_stage_definitions
from ..paths import (
    APPAM_PALEOPROTEOMICS_ROOT,
    APPAM_SMK_ROOT,
    REPO_ROOT,
    get_project_dir,
)


def resolve_project_path(project_id: str, relative_path: str) -> Path:
    if not relative_path:
        raise ValueError('Path is required')
    project_dir = get_project_dir(project_id).resolve()
    candidate = (project_dir / str(relative_path).lstrip('/')).resolve()
    if candidate != project_dir and project_dir not in candidate.parents:
        raise ValueError(f'Path escapes project workspace: {relative_path}')
    return candidate


def resolve_project_or_absolute_path(project_id: str, path_value: str) -> Path:
    raw_value = str(path_value).strip()
    if not raw_value:
        raise ValueError('Path is required')
    if os.path.isabs(raw_value):
        return Path(raw_value).resolve()
    return resolve_project_path(project_id, raw_value)


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def command_to_string(argv: list[str]) -> str:
    return ' '.join(shlex.quote(str(part)) for part in argv)


def get_snakemake_bin() -> str:
    configured = os.getenv('APPAM_SNAKEMAKE_BIN', 'snakemake')
    if os.path.isabs(configured):
        if not Path(configured).exists():
            raise ValueError(f'Snakemake binary not found: {configured}')
        return configured
    resolved = shutil.which(configured)
    if not resolved:
        raise ValueError(
            f'Snakemake executable "{configured}" was not found on PATH. '
            'Set APPAM_SNAKEMAKE_BIN or install Snakemake.'
        )
    return resolved


def resolve_executable(value: str, label: str) -> str:
    configured = str(value or '').strip()
    if not configured:
        raise ValueError(f'{label} is required')
    if os.path.isabs(configured):
        if not Path(configured).exists():
            raise ValueError(f'{label} not found: {configured}')
        return str(Path(configured).resolve())
    resolved = shutil.which(configured)
    if not resolved:
        raise ValueError(f'{label} executable "{configured}" was not found on PATH')
    return resolved


def require_existing_file(path: Path, label: str) -> Path:
    if not path.exists():
        raise ValueError(f'{label} not found: {path}')
    if not path.is_file():
        raise ValueError(f'{label} must be a file: {path}')
    return path


def require_existing_directory(path: Path, label: str) -> Path:
    if not path.exists():
        raise ValueError(f'{label} not found: {path}')
    if not path.is_dir():
        raise ValueError(f'{label} must be a directory: {path}')
    return path


def _required_config_value(params: dict, param_name: str, env_name: str | None = None):
    value = params.get(param_name)
    if value not in (None, ''):
        return value
    if env_name:
        env_value = os.getenv(env_name)
        if env_value:
            return env_value
    return None


def _initial_stage_rows(workflow_id: str, queued: bool = False) -> list[dict]:
    stages = []
    for index, stage in enumerate(get_workflow_stage_definitions(workflow_id)):
        stage_status = 'queued' if queued and index == 0 else ('optional' if stage['optional'] else 'pending')
        stages.append({
            'id': stage['id'],
            'title': stage['title'],
            'order': stage['order'],
            'optional': stage['optional'],
            'status': stage_status,
            'completed_rules': 0,
            'total_rules': len(stage.get('rules', [])),
        })
    return stages


def _workflow_run_root(project_id: str, workflow_id: str, run_id: str) -> dict[str, Path]:
    base_root = get_project_dir(project_id) / 'workflow_runs' / workflow_id / run_id
    return {
        'run_dir': base_root,
        'config_dir': base_root / 'config',
        'logs_dir': base_root / 'logs',
        'metadata_dir': base_root / 'metadata',
        'results_dir': base_root / 'results',
        'reports_dir': base_root / 'reports',
        'work_dir': base_root / 'work',
    }


def _manifest_path(run_paths: dict[str, Path], run_id: str) -> Path:
    return run_paths['metadata_dir'] / f'manifest.{run_id}.json'


def _write_workflow_manifest(run_paths: dict[str, Path], manifest: dict) -> Path:
    manifest_path = _manifest_path(run_paths, manifest['run_id'])
    ensure_directory(manifest_path.parent)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    return manifest_path


def _build_manifest_payload(project_id: str, tool_info: dict, params: dict, context: dict, *, run_id: str, job_id: str, submitted_by: str | None, parent_run_id: str | None = None, mode: str = 'run') -> dict:
    return {
        'run_id': run_id,
        'job_id': job_id,
        'project_id': project_id,
        'workflow_id': context['workflow_id'],
        'tool_name': tool_info['tool_name'],
        'mode': mode,
        'submitted_by': submitted_by,
        'parent_run_id': parent_run_id,
        'backend': context['backend'],
        'dry_run': bool(params.get('dry_run')),
        'params': params,
        'paths': {
            'config_path': str(context['config_path']),
            'log_path': str(context['log_path']),
            'run_dir': str(context['run_paths']['run_dir']),
            'work_dir': str(context['run_paths']['work_dir']),
            'results_dir': str(context['run_paths']['results_dir']),
            'reports_dir': str(context['run_paths']['reports_dir']),
        },
        'command': context['argv'],
        'cleanup_commands': context.get('unlock_argv') and [context['unlock_argv']] or [],
    }


def build_job_request(
    project_id: str,
    job_id: str,
    tool_info: dict,
    params: dict,
    *,
    run_id: str | None = None,
    submitted_by: str | None = None,
    source_run: dict | None = None,
    mode: str = 'run',
) -> dict:
    execution = tool_info.get('execution') or {}
    if execution.get('mode') == 'snakemake':
        workflow_id = execution.get('workflow_id')
        if workflow_id == 'appam-smk':
            return _build_appam_smk_job(project_id, job_id, tool_info, params, run_id=run_id, submitted_by=submitted_by, source_run=source_run, mode=mode)
        if workflow_id == 'appam-paleoproteomics':
            return _build_paleoproteomics_job(project_id, job_id, tool_info, params, run_id=run_id, submitted_by=submitted_by, source_run=source_run, mode=mode)
        raise ValueError(f'Unsupported workflow: {workflow_id}')
    return _build_command_job(project_id, job_id, tool_info, params)


def preflight_job_request(project_id: str, tool_info: dict, params: dict) -> dict:
    execution = tool_info.get('execution') or {}
    if execution.get('mode') == 'snakemake':
        workflow_id = execution.get('workflow_id')
        if workflow_id == 'appam-smk':
            return _preflight_appam_smk(project_id, tool_info, params)
        if workflow_id == 'appam-paleoproteomics':
            return _preflight_paleoproteomics(project_id, tool_info, params)
        raise ValueError(f'Unsupported workflow: {workflow_id}')
    return _preflight_command_job(project_id, tool_info, params)


def _append_parameter_value(argv: list[str], param: dict, value, project_id: str) -> None:
    if value in (None, '', []):
        return

    positional = param.get('position') is not None or param.get('positional', False)
    param_type = param.get('type')

    values = value if isinstance(value, list) else [value]
    rendered_values = []

    for item in values:
        if param_type in {'file', 'directory'}:
            rendered_values.append(str(resolve_project_path(project_id, item)))
        else:
            rendered_values.append(str(item))

    if param_type == 'flag':
        if value:
            argv.append(param['name'])
        return

    if positional:
        argv.extend(rendered_values)
        return

    argv.append(param['name'])
    argv.extend(rendered_values)


def _build_command_job(project_id: str, job_id: str, tool_info: dict, params: dict) -> dict:
    execution = tool_info.get('execution') or {}
    command = execution.get('command')
    if not command:
        raise ValueError(f'No executable configured for {tool_info["tool_name"]}')

    executable = resolve_executable(command, tool_info['tool_name'])
    argv = [executable]
    output_dirs = []

    positional_params = sorted(
        [param for param in tool_info.get('parameters', []) if param.get('position') is not None],
        key=lambda item: item.get('position', 0),
    )
    named_params = [param for param in tool_info.get('parameters', []) if param.get('position') is None]

    for param in positional_params + named_params:
        param_name = param['name']
        if param_name not in params:
            continue
        value = params.get(param_name)
        _append_parameter_value(argv, param, value, project_id)

        if param.get('type') == 'directory' and value and ('out' in param_name.lower() or 'output' in param_name.lower()):
            if isinstance(value, list):
                output_dirs.extend(resolve_project_path(project_id, item) for item in value)
            else:
                output_dirs.append(resolve_project_path(project_id, value))

    for directory in output_dirs:
        ensure_directory(directory)

    project_dir = get_project_dir(project_id)
    log_dir = project_dir / 'logs'
    ensure_directory(log_dir)

    return {
        'display_command': command_to_string(argv),
        'log_path': str(log_dir / f'{job_id}.log'),
        'output_path': str(output_dirs[0]) if output_dirs else None,
        'work_dir': str(project_dir),
        'execution_mode': 'command',
        'is_dry_run': False,
        'command_spec': {
            'argv': argv,
            'cwd': str(project_dir),
        },
    }


def _preflight_command_job(project_id: str, tool_info: dict, params: dict) -> dict:
    executable = resolve_executable((tool_info.get('execution') or {}).get('command'), tool_info['tool_name'])
    checks = [
        {'name': 'tool', 'status': 'ok', 'message': f'Executable resolved: {executable}'},
    ]
    for param in tool_info.get('parameters', []):
        if param.get('type') == 'file' and params.get(param['name']):
            path = require_existing_file(resolve_project_path(project_id, params[param['name']]), param['name'])
            checks.append({'name': param['name'], 'status': 'ok', 'message': f'Input file found: {path}'})
        elif param.get('type') == 'directory' and params.get(param['name']):
            path = require_existing_directory(resolve_project_path(project_id, params[param['name']]), param['name'])
            checks.append({'name': param['name'], 'status': 'ok', 'message': f'Input directory found: {path}'})
    return {'ok': True, 'mode': 'command', 'checks': checks}


def _appam_smk_context(project_id: str, job_id: str, params: dict, run_id: str, write_files: bool, *, source_run: dict | None = None, mode: str = 'run') -> dict:
    workflow_id = 'appam-smk'
    workflow_root = APPAM_SMK_ROOT
    snakefile = require_existing_file(workflow_root / 'workflow' / 'Snakefile', 'APPAM-SMK Snakefile')

    sample_manifest = require_existing_file(resolve_project_path(project_id, params.get('sample_manifest', '')), 'APPAM-SMK sample manifest')
    raw_data_dir = require_existing_directory(resolve_project_path(project_id, params.get('raw_data_dir', '')), 'APPAM-SMK raw data directory')

    metawrap_env = _required_config_value(params, 'metawrap_env', 'APPAM_SMK_METAWRAP_ENV')
    pydamage_env = _required_config_value(params, 'pydamage_env', 'APPAM_SMK_PYDAMAGE_ENV')
    checkm_db = _required_config_value(params, 'checkm_db', 'APPAM_SMK_CHECKM_DB')
    gunc_db = _required_config_value(params, 'gunc_db', 'APPAM_SMK_GUNC_DB')

    missing = []
    if not metawrap_env:
        missing.append('metawrap_env / APPAM_SMK_METAWRAP_ENV')
    if not pydamage_env:
        missing.append('pydamage_env / APPAM_SMK_PYDAMAGE_ENV')
    if not checkm_db:
        missing.append('checkm_db / APPAM_SMK_CHECKM_DB')
    if not gunc_db:
        missing.append('gunc_db / APPAM_SMK_GUNC_DB')
    if missing:
        raise ValueError('Missing APPAM-SMK runtime settings: ' + ', '.join(missing))

    profile = str(params.get('profile', 'local')).strip() or 'local'
    profile_dir = require_existing_directory(workflow_root / 'profiles' / profile, f'APPAM-SMK profile "{profile}"')
    snakemake_bin = get_snakemake_bin()
    cores = int(params.get('cores', 4))
    backend = resolve_backend_name(params.get('execution_backend') or os.getenv('APPAM_SMK_EXECUTION_BACKEND'), profile=profile)

    if Path(str(checkm_db)).is_absolute():
        require_existing_directory(Path(str(checkm_db)).resolve(), 'CheckM database')
    if Path(str(gunc_db)).is_absolute():
        require_existing_directory(Path(str(gunc_db)).resolve(), 'GUNC database')
    if Path(str(metawrap_env)).is_absolute() and not Path(str(metawrap_env)).exists():
        raise ValueError(f'MetaWRAP environment path not found: {metawrap_env}')
    if Path(str(pydamage_env)).is_absolute() and not Path(str(pydamage_env)).exists():
        raise ValueError(f'PyDamage environment path not found: {pydamage_env}')

    if mode == 'resume' and source_run:
        run_paths = {
            'run_dir': Path(source_run['run_dir']),
            'config_dir': Path(source_run['run_dir']) / 'config',
            'logs_dir': Path(source_run['run_dir']) / 'logs',
            'metadata_dir': Path(source_run['run_dir']) / 'metadata',
            'results_dir': Path(source_run['results_dir']),
            'reports_dir': Path(source_run['run_dir']) / 'reports',
            'work_dir': Path(source_run['work_dir']),
        }
        generated_config = Path(source_run['config_path'])
    else:
        run_paths = _workflow_run_root(project_id, workflow_id, run_id)
        generated_config = run_paths['config_dir'] / f'config.{job_id}.yaml'
    temp_dir = run_paths['work_dir'] / 'temp'
    benchmark_dir = run_paths['metadata_dir'] / 'benchmarks'
    log_path = run_paths['logs_dir'] / f'{job_id}.log'

    config_data = {
        'samples_file': str(sample_manifest),
        'paths': {
            'raw_data_dir': str(raw_data_dir),
            'temp_dir': str(temp_dir),
            'results_dir': str(run_paths['results_dir']),
            'logs_dir': str(run_paths['logs_dir']),
            'benchmark_dir': str(benchmark_dir),
        },
        'params': {
            'preprocess_method': params.get('preprocess_method', 'fastp'),
            'min_contig_len': int(params.get('min_contig_len', 500)),
            'use_ancient_contigs': bool(params.get('use_ancient_contigs', True)),
        },
        'databases': {
            'checkm_db': str(checkm_db),
            'gunc_db': str(gunc_db),
        },
        'tools': {
            'metawrap_env': str(metawrap_env),
            'pydamage_env': str(pydamage_env),
        },
    }

    if write_files:
        for directory in (
            run_paths['run_dir'],
            run_paths['config_dir'],
            run_paths['logs_dir'],
            run_paths['metadata_dir'],
            run_paths['results_dir'],
            run_paths['reports_dir'],
            run_paths['work_dir'],
            temp_dir,
            benchmark_dir,
        ):
            ensure_directory(directory)
        if mode != 'resume' or not generated_config.exists():
            generated_config.write_text(yaml.safe_dump(config_data, sort_keys=False), encoding='utf-8')

    argv = [
        snakemake_bin,
        '--snakefile',
        str(snakefile),
        '--configfile',
        str(generated_config),
        '--profile',
        str(profile_dir),
        '--printshellcmds',
    ]
    if profile == 'local':
        argv.extend(['--cores', str(cores)])
    else:
        argv.extend(['--jobs', str(cores)])

    if params.get('dry_run'):
        argv.append('-n')
    if mode == 'resume':
        argv.append('--rerun-incomplete')

    target_rule = str(params.get('target_rule', '')).strip()
    if target_rule:
        argv.append(target_rule)

    unlock_argv = [
        snakemake_bin,
        '--snakefile',
        str(snakefile),
        '--configfile',
        str(generated_config),
        '--profile',
        str(profile_dir),
        '--unlock',
    ]

    return {
        'workflow_id': workflow_id,
        'workflow_root': workflow_root,
        'snakefile': snakefile,
        'profile': profile,
        'cores': cores,
        'sample_manifest': sample_manifest,
        'raw_data_dir': raw_data_dir,
        'metawrap_env': str(metawrap_env),
        'pydamage_env': str(pydamage_env),
        'checkm_db': str(checkm_db),
        'gunc_db': str(gunc_db),
        'config_path': generated_config,
        'log_path': log_path,
        'run_paths': run_paths,
        'config_data': config_data,
        'argv': argv,
        'unlock_argv': unlock_argv,
        'backend': backend,
    }


def _paleoproteomics_context(project_id: str, job_id: str, params: dict, run_id: str, write_files: bool, *, source_run: dict | None = None, mode: str = 'run') -> dict:
    workflow_id = 'appam-paleoproteomics'
    workflow_root = APPAM_PALEOPROTEOMICS_ROOT
    snakefile = require_existing_file(workflow_root / 'workflow' / 'Snakefile', 'APPAM paleoproteomics Snakefile')

    sample_table = require_existing_file(resolve_project_path(project_id, params.get('sample_table', '')), 'Paleoproteomics sample table')
    fasta_path = require_existing_file(resolve_project_or_absolute_path(project_id, params.get('fasta_path', '')), 'Reference FASTA')

    dotnet_bin = resolve_executable(_required_config_value(params, 'dotnet_bin', 'APPAM_PALEO_DOTNET_BIN') or 'dotnet', 'dotnet')
    maxquant_cmd_dll = _required_config_value(params, 'maxquant_cmd_dll', 'APPAM_PALEO_MAXQUANT_CMD')
    thermo_raw_file_parser = resolve_executable(
        _required_config_value(params, 'thermo_raw_file_parser', 'APPAM_PALEO_THERMO_RAW_FILE_PARSER') or 'ThermoRawFileParser',
        'ThermoRawFileParser',
    )
    timsconvert_bin = resolve_executable(
        _required_config_value(params, 'timsconvert_bin', 'APPAM_PALEO_TIMSCONVERT_BIN') or 'timsconvert',
        'timsconvert',
    )
    openms_fileconverter = resolve_executable(
        _required_config_value(params, 'openms_fileconverter', 'APPAM_PALEO_OPENMS_FILECONVERTER') or 'FileConverter',
        'OpenMS FileConverter',
    )

    if not maxquant_cmd_dll:
        raise ValueError('Missing paleoproteomics runtime settings: maxquant_cmd_dll / APPAM_PALEO_MAXQUANT_CMD')
    maxquant_cmd_dll = require_existing_file(Path(str(maxquant_cmd_dll)).resolve(), 'MaxQuantCmd.dll')

    backend = resolve_backend_name(params.get('execution_backend') or os.getenv('APPAM_PALEO_EXECUTION_BACKEND'), profile='local')
    if mode == 'resume' and source_run:
        run_paths = {
            'run_dir': Path(source_run['run_dir']),
            'config_dir': Path(source_run['run_dir']) / 'config',
            'logs_dir': Path(source_run['run_dir']) / 'logs',
            'metadata_dir': Path(source_run['run_dir']) / 'metadata',
            'results_dir': Path(source_run['results_dir']),
            'reports_dir': Path(source_run['run_dir']) / 'reports',
            'work_dir': Path(source_run['work_dir']),
        }
        generated_config = Path(source_run['config_path'])
    else:
        run_paths = _workflow_run_root(project_id, workflow_id, run_id)
        generated_config = run_paths['config_dir'] / f'config.{job_id}.yaml'
    log_path = run_paths['logs_dir'] / f'{job_id}.log'
    maxquant_output_dir = run_paths['results_dir'] / 'maxquant'

    config_data = {
        'sample_table': str(sample_table),
        'mqpar_template': str(workflow_root / 'workflow' / 'templates' / 'mqpar.template.xml'),
        'results_dir': str(run_paths['results_dir']),
        'maxquant_output_dir': str(maxquant_output_dir),
        'threads': int(params.get('cores', 4)),
        'fasta_path': str(fasta_path),
        'match_between_runs': bool(params.get('match_between_runs', False)),
        'include_contaminants': bool(params.get('include_contaminants', True)),
        'min_peptide_length': int(params.get('min_peptide_length', 7)),
        'first_search_tol': float(params.get('first_search_tol', 20)),
        'main_search_tol': float(params.get('main_search_tol', 4.5)),
        'dotnet_bin': str(dotnet_bin),
        'maxquant_cmd_dll': str(maxquant_cmd_dll),
        'thermo_raw_file_parser': str(thermo_raw_file_parser),
        'timsconvert_bin': str(timsconvert_bin),
        'openms_fileconverter': str(openms_fileconverter),
    }

    if write_files:
        for directory in (
            run_paths['run_dir'],
            run_paths['config_dir'],
            run_paths['logs_dir'],
            run_paths['metadata_dir'],
            run_paths['results_dir'],
            run_paths['reports_dir'],
            run_paths['work_dir'],
            maxquant_output_dir,
        ):
            ensure_directory(directory)
        if mode != 'resume' or not generated_config.exists():
            generated_config.write_text(yaml.safe_dump(config_data, sort_keys=False), encoding='utf-8')

    snakemake_bin = get_snakemake_bin()
    cores = int(params.get('cores', 4))
    argv = [
        snakemake_bin,
        '-s',
        str(snakefile),
        '--configfile',
        str(generated_config),
        '--cores',
        str(cores),
        '--printshellcmds',
    ]
    if params.get('dry_run'):
        argv.append('-n')
    if mode == 'resume':
        argv.append('--rerun-incomplete')

    target_rule = str(params.get('target_rule', '')).strip()
    if target_rule:
        argv.append(target_rule)

    unlock_argv = [
        snakemake_bin,
        '-s',
        str(snakefile),
        '--configfile',
        str(generated_config),
        '--cores',
        str(cores),
        '--unlock',
    ]

    return {
        'workflow_id': workflow_id,
        'workflow_root': workflow_root,
        'snakefile': snakefile,
        'sample_table': sample_table,
        'fasta_path': fasta_path,
        'config_path': generated_config,
        'log_path': log_path,
        'run_paths': run_paths,
        'config_data': config_data,
        'argv': argv,
        'unlock_argv': unlock_argv,
        'backend': backend,
    }


def _build_workflow_request(project_id: str, job_id: str, run_id: str, tool_info: dict, params: dict, context: dict, submitted_by: str | None, *, source_run: dict | None = None, mode: str = 'run') -> dict:
    workflow_id = context['workflow_id']
    dry_run = bool(params.get('dry_run'))
    stage_rows = _initial_stage_rows(workflow_id, queued=True)
    output_root = str(context['run_paths']['results_dir'])
    manifest = _build_manifest_payload(
        project_id,
        tool_info,
        params,
        context,
        run_id=run_id,
        job_id=job_id,
        submitted_by=submitted_by,
        parent_run_id=source_run.get('id') if source_run else None,
        mode=mode,
    )
    manifest_path = _write_workflow_manifest(context['run_paths'], manifest)
    command_spec = build_backend_command_spec(
        backend=context['backend'],
        argv=context['argv'],
        cwd=str(context['workflow_root']),
        cleanup_commands=[
            {
                'argv': context['unlock_argv'],
                'cwd': str(context['workflow_root']),
            }
        ] if not dry_run else [],
        workflow_context={
            'run_id': run_id,
            'workflow_id': workflow_id,
            'stages': get_workflow_stage_definitions(workflow_id),
            'manifest_path': str(manifest_path),
            'results_dir': str(context['run_paths']['results_dir']),
            'reports_dir': str(context['run_paths']['reports_dir']),
        },
    )

    return {
        'display_command': command_spec.get('backend_display_command') or command_to_string(context['argv']),
        'log_path': str(context['log_path']),
        'output_path': output_root,
        'work_dir': str(context['run_paths']['work_dir']),
        'execution_mode': 'snakemake',
        'workflow_id': workflow_id,
        'workflow_run_id': run_id,
        'is_dry_run': dry_run,
        'workflow_run_spec': {
            'id': run_id,
            'job_id': job_id,
            'project_id': project_id,
            'workflow_id': workflow_id,
            'tool_name': tool_info['tool_name'],
            'status': 'queued',
            'dry_run': dry_run,
            'backend': context['backend'],
            'submitted_by': submitted_by,
            'parent_run_id': source_run.get('id') if source_run else None,
            'params': params,
            'config_path': str(context['config_path']),
            'manifest_path': str(manifest_path),
            'run_dir': str(context['run_paths']['run_dir']),
            'work_dir': str(context['run_paths']['work_dir']),
            'results_dir': str(context['run_paths']['results_dir']),
            'output_root': output_root,
            'log_path': str(context['log_path']),
            'current_stage_id': stage_rows[0]['id'] if stage_rows else None,
            'current_stage_title': stage_rows[0]['title'] if stage_rows else None,
            'current_rule': None,
            'stages': stage_rows,
            'events': [
                {
                    'event_type': 'run_queued',
                    'message': 'Workflow queued',
                    'payload': {'dry_run': dry_run, 'workflow_id': workflow_id, 'mode': mode},
                }
            ],
            'artifacts': [],
        },
        'command_spec': command_spec,
    }


def _build_appam_smk_job(project_id: str, job_id: str, tool_info: dict, params: dict, *, run_id: str | None, submitted_by: str | None, source_run: dict | None = None, mode: str = 'run') -> dict:
    resolved_run_id = run_id or job_id
    context = _appam_smk_context(project_id, job_id, params, resolved_run_id, write_files=True, source_run=source_run, mode=mode)
    return _build_workflow_request(project_id, job_id, resolved_run_id, tool_info, params, context, submitted_by, source_run=source_run, mode=mode)


def _build_paleoproteomics_job(project_id: str, job_id: str, tool_info: dict, params: dict, *, run_id: str | None, submitted_by: str | None, source_run: dict | None = None, mode: str = 'run') -> dict:
    resolved_run_id = run_id or job_id
    context = _paleoproteomics_context(project_id, job_id, params, resolved_run_id, write_files=True, source_run=source_run, mode=mode)
    return _build_workflow_request(project_id, job_id, resolved_run_id, tool_info, params, context, submitted_by, source_run=source_run, mode=mode)


def _preflight_appam_smk(project_id: str, tool_info: dict, params: dict) -> dict:
    preview_run_id = 'preflight-preview'
    context = _appam_smk_context(project_id, 'preflight', params, preview_run_id, write_files=False)
    return {
        'ok': True,
        'mode': 'snakemake',
        'workflow_id': context['workflow_id'],
        'checks': [
            {'name': 'snakemake', 'status': 'ok', 'message': f'Snakemake resolved: {get_snakemake_bin()}'},
            {'name': 'snakefile', 'status': 'ok', 'message': f'Snakefile found: {context["snakefile"]}'},
            {'name': 'sample_manifest', 'status': 'ok', 'message': f'Sample manifest found: {context["sample_manifest"]}'},
            {'name': 'raw_data_dir', 'status': 'ok', 'message': f'Raw data directory found: {context["raw_data_dir"]}'},
            {'name': 'profile', 'status': 'ok', 'message': f'Profile ready: {context["profile"]}'},
        ],
        'preview': {
            'config_path': str(context['config_path']),
            'run_dir': str(context['run_paths']['run_dir']),
            'work_dir': str(context['run_paths']['work_dir']),
            'results_dir': str(context['run_paths']['results_dir']),
            'log_path': str(context['log_path']),
            'command': command_to_string(context['argv']),
        },
    }


def _preflight_paleoproteomics(project_id: str, tool_info: dict, params: dict) -> dict:
    preview_run_id = 'preflight-preview'
    context = _paleoproteomics_context(project_id, 'preflight', params, preview_run_id, write_files=False)
    return {
        'ok': True,
        'mode': 'snakemake',
        'workflow_id': context['workflow_id'],
        'checks': [
            {'name': 'snakemake', 'status': 'ok', 'message': f'Snakemake resolved: {get_snakemake_bin()}'},
            {'name': 'snakefile', 'status': 'ok', 'message': f'Snakefile found: {context["snakefile"]}'},
            {'name': 'sample_table', 'status': 'ok', 'message': f'Sample table found: {context["sample_table"]}'},
            {'name': 'fasta_path', 'status': 'ok', 'message': f'Reference FASTA found: {context["fasta_path"]}'},
        ],
        'preview': {
            'config_path': str(context['config_path']),
            'run_dir': str(context['run_paths']['run_dir']),
            'work_dir': str(context['run_paths']['work_dir']),
            'results_dir': str(context['run_paths']['results_dir']),
            'log_path': str(context['log_path']),
            'command': command_to_string(context['argv']),
        },
    }


def build_job_request_from_workflow_run(
    project_id: str,
    job_id: str,
    tool_info: dict,
    source_run: dict,
    *,
    run_id: str | None = None,
    submitted_by: str | None = None,
    mode: str = 'retry',
) -> dict:
    params = source_run.get('params') or {}
    return build_job_request(
        project_id,
        job_id,
        tool_info,
        params,
        run_id=run_id,
        submitted_by=submitted_by,
        source_run=source_run,
        mode=mode,
    )


def generate_workflow_template(project_id: str, workflow_id: str, overwrite: bool = False) -> dict:
    project_dir = get_project_dir(project_id)
    templates_dir = project_dir / 'workflow_templates' / workflow_id
    ensure_directory(templates_dir)

    if workflow_id == 'appam-smk':
        manifest_path = templates_dir / 'samples.tsv'
        raw_dir = templates_dir / 'raw_fastq'
        ensure_directory(raw_dir)
        if manifest_path.exists() and not overwrite:
            raise ValueError(f'Template already exists: {manifest_path}')
        manifest_path.write_text(
            'sample_id\tforward_reads\treverse_reads\nsample1\traw_fastq/sample1_R1.fastq.gz\traw_fastq/sample1_R2.fastq.gz\n',
            encoding='utf-8',
        )
        notes_path = templates_dir / 'README.txt'
        notes_path.write_text(
            'Place paired-end FASTQ files under raw_fastq/ and update samples.tsv accordingly.\n',
            encoding='utf-8',
        )
        return {
            'workflow_id': workflow_id,
            'created_files': [str(manifest_path), str(notes_path)],
            'created_directories': [str(raw_dir)],
        }

    if workflow_id == 'appam-paleoproteomics':
        sample_table = templates_dir / 'samples.tsv'
        raw_dir = templates_dir / 'raw_ms'
        fasta_path = templates_dir / 'reference.fasta'
        ensure_directory(raw_dir)
        if sample_table.exists() and not overwrite:
            raise ValueError(f'Template already exists: {sample_table}')
        sample_table.write_text(
            'sample_id\traw_path\texperiment\tfraction\nsample1\traw_ms/sample1.RAW\tprojectA\t1\n',
            encoding='utf-8',
        )
        fasta_path.write_text('>protein_1\nMPEPTIDESEQ\n', encoding='utf-8')
        notes_path = templates_dir / 'README.txt'
        notes_path.write_text(
            'Place Thermo RAW files or Bruker .d folders under raw_ms/ and update samples.tsv/reference.fasta.\n',
            encoding='utf-8',
        )
        return {
            'workflow_id': workflow_id,
            'created_files': [str(sample_table), str(fasta_path), str(notes_path)],
            'created_directories': [str(raw_dir)],
        }

    raise ValueError(f'Unsupported workflow template: {workflow_id}')


def runtime_health_for_workflow(workflow_id: str) -> dict:
    checks = []
    snakemake_bin = get_snakemake_bin()
    checks.append({'name': 'snakemake', 'status': 'ok', 'message': f'Snakemake resolved: {snakemake_bin}'})

    if workflow_id == 'appam-smk':
        workflow_root = APPAM_SMK_ROOT
        require_existing_directory(workflow_root, 'APPAM-SMK root')
        require_existing_file(workflow_root / 'workflow' / 'Snakefile', 'APPAM-SMK Snakefile')
        checks.extend([
            {'name': 'workflow_root', 'status': 'ok', 'message': f'Workflow root ready: {workflow_root}'},
            {'name': 'metawrap_env', 'status': 'ok', 'message': f"MetaWRAP setting: {_required_config_value({}, 'metawrap_env', 'APPAM_SMK_METAWRAP_ENV') or 'not set'}"},
            {'name': 'pydamage_env', 'status': 'ok', 'message': f"PyDamage setting: {_required_config_value({}, 'pydamage_env', 'APPAM_SMK_PYDAMAGE_ENV') or 'not set'}"},
            {'name': 'checkm_db', 'status': 'ok', 'message': f"CheckM DB: {_required_config_value({}, 'checkm_db', 'APPAM_SMK_CHECKM_DB') or 'not set'}"},
            {'name': 'gunc_db', 'status': 'ok', 'message': f"GUNC DB: {_required_config_value({}, 'gunc_db', 'APPAM_SMK_GUNC_DB') or 'not set'}"},
        ])
        return {'ok': True, 'workflow_id': workflow_id, 'checks': checks}

    if workflow_id == 'appam-paleoproteomics':
        workflow_root = APPAM_PALEOPROTEOMICS_ROOT
        require_existing_directory(workflow_root, 'APPAM paleoproteomics root')
        require_existing_file(workflow_root / 'workflow' / 'Snakefile', 'APPAM paleoproteomics Snakefile')
        checks.append({'name': 'workflow_root', 'status': 'ok', 'message': f'Workflow root ready: {workflow_root}'})
        checks.append({'name': 'dotnet', 'status': 'ok', 'message': f"dotnet: {resolve_executable(_required_config_value({}, 'dotnet_bin', 'APPAM_PALEO_DOTNET_BIN') or 'dotnet', 'dotnet')}"})
        if _required_config_value({}, 'maxquant_cmd_dll', 'APPAM_PALEO_MAXQUANT_CMD'):
            checks.append({'name': 'maxquant', 'status': 'ok', 'message': f"MaxQuantCmd.dll: {_required_config_value({}, 'maxquant_cmd_dll', 'APPAM_PALEO_MAXQUANT_CMD')}"})
        else:
            raise ValueError('APPAM_PALEO_MAXQUANT_CMD is not configured')
        checks.append({'name': 'ThermoRawFileParser', 'status': 'ok', 'message': f"ThermoRawFileParser: {resolve_executable(_required_config_value({}, 'thermo_raw_file_parser', 'APPAM_PALEO_THERMO_RAW_FILE_PARSER') or 'ThermoRawFileParser', 'ThermoRawFileParser')}"})
        checks.append({'name': 'timsconvert', 'status': 'ok', 'message': f"timsconvert: {resolve_executable(_required_config_value({}, 'timsconvert_bin', 'APPAM_PALEO_TIMSCONVERT_BIN') or 'timsconvert', 'timsconvert')}"})
        checks.append({'name': 'OpenMS FileConverter', 'status': 'ok', 'message': f"FileConverter: {resolve_executable(_required_config_value({}, 'openms_fileconverter', 'APPAM_PALEO_OPENMS_FILECONVERTER') or 'FileConverter', 'OpenMS FileConverter')}"})
        return {'ok': True, 'workflow_id': workflow_id, 'checks': checks}

    raise ValueError(f'Unsupported workflow health check: {workflow_id}')
