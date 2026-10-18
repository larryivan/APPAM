from __future__ import annotations

import copy
import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

import yaml

from .execution_backends import build_backend_command_spec, resolve_backend_name
from .runtime_resources import (
    collect_appam_smk_runtime_metadata,
    get_appam_smk_runtime_checks,
    get_appam_smk_runtime_settings,
    validate_appam_smk_runtime,
)
from .provenance import conda_environment_fingerprint, fingerprint_path, repository_state, sha256_bytes
from .sample_validator import (
    validate_appam_smk_manifest,
    validate_paleoproteomics_table,
    write_resolved_appam_smk_manifest,
    write_resolved_paleoproteomics_table,
)
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
    if not os.path.isabs(raw_value):
        return resolve_project_path(project_id, raw_value)

    candidate = Path(raw_value).expanduser().resolve()
    project_root = get_project_dir(project_id).resolve()
    shared_root = Path(os.getenv('APPAM_DATABASES_ROOT', '/databases')).expanduser().resolve()
    allowed_roots = (project_root, shared_root)
    if not any(candidate == root or root in candidate.parents for root in allowed_roots):
        raise ValueError('Absolute paths must be inside the project or APPAM_DATABASES_ROOT')
    return candidate


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _load_yaml_mapping(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(payload, dict):
        raise ValueError(f'Configuration must be a mapping: {path}')
    return payload


def _deep_merge(base: dict, overrides: dict) -> dict:
    merged = copy.deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _materialize_config(default_path: Path, overrides: dict) -> dict:
    return _deep_merge(_load_yaml_mapping(default_path), overrides)


def _list_parameter(params: dict, name: str, default: list[str]) -> list[str]:
    value = params.get(name)
    if value in (None, ''):
        return list(default)
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split(',') if item.strip()]


def command_to_string(argv: list[str]) -> str:
    return ' '.join(shlex.quote(str(part)) for part in argv)


def get_snakemake_bin() -> str:
    configured = os.getenv('APPAM_SNAKEMAKE_BIN', 'snakemake')
    expanded = os.path.expanduser(configured)
    if os.path.isabs(expanded):
        path = Path(expanded).resolve()
        if not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError(f'Snakemake binary not found: {configured}')
        return str(path)
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
    expanded = os.path.expanduser(configured)
    if os.path.isabs(expanded):
        path = Path(expanded).resolve()
        if not path.is_file():
            raise ValueError(f'{label} not found: {configured}')
        if not os.access(path, os.X_OK):
            raise ValueError(f'{label} is not executable: {path}')
        return str(path)
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


def _project_scoped_path(project_id: str, value: str | Path, label: str) -> Path:
    """Resolve a persisted path while keeping workflow state inside its project."""
    raw_value = str(value or '').strip()
    if not raw_value:
        raise ValueError(f'{label} is required')
    raw_path = Path(raw_value)
    candidate = raw_path.resolve() if raw_path.is_absolute() else resolve_project_path(project_id, str(raw_path))
    project_dir = get_project_dir(project_id).resolve()
    if candidate != project_dir and project_dir not in candidate.parents:
        raise ValueError(f'{label} escapes project workspace: {candidate}')
    return candidate


def _project_relative_value(project_id: str, path: Path) -> str:
    project_dir = get_project_dir(project_id).resolve()
    resolved = path.resolve()
    if resolved == project_dir:
        return '.'
    if project_dir not in resolved.parents:
        raise ValueError(f'Path escapes project workspace: {resolved}')
    return str(resolved.relative_to(project_dir))


def _load_frozen_source_config(project_id: str, source_run: dict, default_path: Path) -> tuple[Path, dict]:
    config_path = _project_scoped_path(project_id, source_run.get('config_path', ''), 'Source workflow config')
    require_existing_file(config_path, 'Source workflow config')
    return config_path, _materialize_config(default_path, _load_yaml_mapping(config_path))


def _runtime_settings_from_appam_config(config_data: dict) -> dict:
    runtime_params = {}
    runtime_params.update(config_data.get('databases') or {})
    runtime_params.update(config_data.get('tools') or {})
    workflow_params = config_data.get('params') or {}
    for name in (
        'enable_bin_refinement',
        'enable_checkm1',
        'enable_checkm2',
        'enable_gunc',
        'enable_gtdbtk',
        'enable_prokka',
        'enable_eggnog',
        'enable_abricate',
        'enable_rgi',
        'enable_antismash',
        'enable_variants',
    ):
        if name in workflow_params:
            runtime_params[name] = workflow_params[name]
    visualization = config_data.get('visualization') or {}
    if 'enabled' in visualization:
        runtime_params['enable_visualization'] = visualization['enabled']
    return get_appam_smk_runtime_settings(runtime_params)


def _verify_source_inputs(project_id: str, source_run: dict | None, current_inputs: list[dict]) -> dict:
    if not source_run:
        return {'checked': False, 'matched': None, 'reason': 'not a resumed or retried run'}
    manifest_value = source_run.get('manifest_path')
    if not manifest_value:
        return {'checked': False, 'matched': None, 'reason': 'source run has no manifest'}
    manifest_path = _project_scoped_path(project_id, manifest_value, 'Source workflow manifest')
    require_existing_file(manifest_path, 'Source workflow manifest')
    try:
        source_manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f'Could not read source workflow manifest: {exc}') from exc
    source_inputs = source_manifest.get('inputs') or []
    if not source_inputs:
        return {'checked': False, 'matched': None, 'reason': 'source manifest predates input fingerprints'}

    def key(item: dict) -> tuple[str, str, str]:
        return (
            str(item.get('sample_id') or ''),
            str(item.get('input_role') or ''),
            str(Path(str(item.get('path') or '')).resolve()),
        )

    current_by_key = {key(item): item for item in current_inputs}
    mismatches = []
    for source in source_inputs:
        current = current_by_key.get(key(source))
        if current is None:
            mismatches.append(f'missing input: {source.get("path")}')
            continue
        if source.get('sha256'):
            fields = ('exists', 'type', 'size_bytes', 'sha256')
        elif source.get('type') == 'directory':
            fields = ('exists', 'type', 'file_count', 'size_bytes', 'fingerprint')
        else:
            fields = ('exists', 'type', 'size_bytes', 'mtime_ns')
        changed = [field for field in fields if source.get(field) != current.get(field)]
        if changed:
            mismatches.append(f'{source.get("path")}: changed {", ".join(changed)}')
    if mismatches:
        raise ValueError(
            'Frozen workflow inputs changed after the source run. Submit a new run instead of retry/resume: '
            + '; '.join(mismatches[:10])
        )
    return {'checked': True, 'matched': True, 'input_count': len(source_inputs)}


def _runtime_value_with_source_shape(current, source):
    if isinstance(source, dict):
        current_mapping = current if isinstance(current, dict) else {}
        return {
            key: _runtime_value_with_source_shape(current_mapping.get(key), value)
            for key, value in source.items()
            if key != 'path'
        }
    if isinstance(source, list):
        current_values = current if isinstance(current, list) else []
        if not source:
            return list(current_values)
        return [
            _runtime_value_with_source_shape(value, source[min(index, len(source) - 1)])
            for index, value in enumerate(current_values)
        ]
    return current


def _runtime_digest(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return sha256_bytes(payload)


def _resolved_input_record(path: Path | None, role: str) -> dict | None:
    """Deterministic identity of the resolved input table archived for this run."""
    if path is None or not Path(path).is_file():
        return None
    path = Path(path)
    payload = path.read_bytes()
    lines = [line for line in payload.decode('utf-8', errors='replace').splitlines() if line.strip()]
    return {
        'role': role,
        'path': str(path),
        'sha256': sha256_bytes(payload),
        'size_bytes': len(payload),
        'row_count': max(0, len(lines) - 1),
    }


def _database_manifest_snapshot(database_manifest: dict, errors: list[str], required_resources: list[str]) -> dict:
    """Freeze the parsed database manifest as it was when this run was prepared.

    A run bundle must never be re-assembled from the current manifest on disk, so
    the exact parsed content is stored here together with a path-independent
    canonical digest.
    """
    found = bool(database_manifest.get('found'))
    source_path = Path(str(database_manifest.get('path') or '')).expanduser()
    canonical = {
        'schema_version': database_manifest.get('schema_version'),
        'template': bool(database_manifest.get('template')),
        'resources': database_manifest.get('resources') or {},
    }
    return {
        'found': found,
        # 'path' is excluded from retry drift comparison by _runtime_value_with_source_shape.
        'path': str(source_path) if found else None,
        'sha256': fingerprint_path(source_path, 'sha256').get('sha256') if found else None,
        'canonical_sha256': _runtime_digest(canonical),
        'schema_version': canonical['schema_version'],
        'template': canonical['template'],
        'required_resources': sorted(required_resources),
        'resources': canonical['resources'],
        'validation_errors': list(errors),
    }


def _verify_source_runtime(project_id: str, source_run: dict | None, current_runtime: dict) -> dict:
    if not source_run:
        return {'checked': False, 'matched': None, 'reason': 'not a resumed or retried run'}
    manifest_value = source_run.get('manifest_path')
    if not manifest_value:
        return {'checked': False, 'matched': None, 'reason': 'source run has no manifest'}
    manifest_path = _project_scoped_path(project_id, manifest_value, 'Source workflow manifest')
    require_existing_file(manifest_path, 'Source workflow manifest')
    try:
        source_manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f'Could not read source workflow manifest: {exc}') from exc
    source_runtime = source_manifest.get('runtime_metadata')
    if not source_runtime:
        return {'checked': False, 'matched': None, 'reason': 'source manifest predates runtime fingerprints'}

    normalized_source = _runtime_value_with_source_shape(source_runtime, source_runtime)
    normalized_current = _runtime_value_with_source_shape(current_runtime, source_runtime)
    source_digest = _runtime_digest(normalized_source)
    current_digest = _runtime_digest(normalized_current)
    matched = source_digest == current_digest
    if not matched and os.getenv('APPAM_ALLOW_RUNTIME_DRIFT_ON_RETRY', 'false').strip().lower() not in {'1', 'true', 'yes', 'on'}:
        raise ValueError(
            'Workflow runtime or database resources changed after the source run. '
            'Submit a new run, or explicitly set APPAM_ALLOW_RUNTIME_DRIFT_ON_RETRY=true and document the deviation.'
        )
    return {
        'checked': True,
        'matched': matched,
        'source_digest': source_digest,
        'current_digest': current_digest,
        'override_used': not matched,
    }


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
        'preflight_id': context.get('preflight_id') or params.get('_preflight_id'),
        'backend': context['backend'],
        'dry_run': bool(params.get('dry_run')),
        'params': params,
        'runtime': context.get('runtime_settings'),
        'runtime_checks': context.get('runtime_checks'),
        'runtime_metadata': context.get('runtime_metadata'),
        'workflow_revision': context.get('workflow_revision'),
        'effective_config': context.get('config_data'),
        'effective_config_sha256': context.get('config_sha256'),
        'inputs': context.get('input_provenance'),
        'resolved_input_table': context.get('resolved_input_record'),
        'source_input_verification': context.get('source_input_verification'),
        'source_runtime_verification': context.get('source_runtime_verification'),
        'input_validation': context.get('input_validation'),
        'paths': {
            'config_path': str(context['config_path']),
            'log_path': str(context['log_path']),
            'run_dir': str(context['run_paths']['run_dir']),
            'work_dir': str(context['run_paths']['work_dir']),
            'results_dir': str(context['run_paths']['results_dir']),
            'reports_dir': str(context['run_paths']['reports_dir']),
            'resolved_sample_manifest': str(context['resolved_sample_manifest']) if context.get('resolved_sample_manifest') else None,
            'resolved_sample_table': str(context['resolved_sample_table']) if context.get('resolved_sample_table') else None,
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


def _has_parameter_value(value) -> bool:
    return value not in (None, '', [])


def validate_parameter_values(tool_info: dict, params: dict) -> list[str]:
    errors = []
    parameters = tool_info.get('parameters') or []
    known_names = {parameter['name'] for parameter in parameters}
    unknown_names = sorted(name for name in params if name not in known_names and not str(name).startswith('_'))
    if unknown_names:
        errors.append(f'Unknown parameter(s): {", ".join(unknown_names)}')

    for parameter in parameters:
        name = parameter['name']
        value = params.get(name)
        if parameter.get('required') and not _has_parameter_value(value):
            errors.append(f"Required parameter '{name}' is missing")
            continue
        if not _has_parameter_value(value):
            continue

        values = value if isinstance(value, list) else [value]
        if not parameter.get('multiple') and isinstance(value, list) and len(value) > 1:
            errors.append(f"Parameter '{name}' accepts only one value")
        minimum_items = parameter.get('minimum_items')
        maximum_items = parameter.get('maximum_items')
        if minimum_items is not None and len(values) < int(minimum_items):
            errors.append(f"Parameter '{name}' requires at least {minimum_items} value(s)")
        if maximum_items is not None and len(values) > int(maximum_items):
            errors.append(f"Parameter '{name}' accepts at most {maximum_items} value(s)")

        options = parameter.get('options') or []
        for item in values:
            if options and item not in options:
                errors.append(f"Parameter '{name}' value '{item}' is not allowed")
                continue

            converted = item
            try:
                if parameter.get('type') == 'integer':
                    if isinstance(item, bool):
                        raise ValueError
                    converted = int(item)
                elif parameter.get('type') == 'float':
                    if isinstance(item, bool):
                        raise ValueError
                    converted = float(item)
                elif parameter.get('type') == 'flag' and not isinstance(item, bool):
                    raise ValueError
            except (TypeError, ValueError):
                errors.append(f"Parameter '{name}' must be a valid {parameter.get('type')}")
                continue

            minimum = parameter.get('minimum')
            maximum = parameter.get('maximum')
            if minimum is not None and converted < minimum:
                errors.append(f"Parameter '{name}' must be at least {minimum}")
            if maximum is not None and converted > maximum:
                errors.append(f"Parameter '{name}' must be at most {maximum}")
            pattern = parameter.get('pattern')
            if pattern and not re.fullmatch(str(pattern), str(item)):
                errors.append(f"Parameter '{name}' has an invalid format")

    required_any = tool_info.get('required_any') or []
    if required_any and not any(_has_parameter_value(params.get(name)) for name in required_any):
        errors.append(f'At least one input parameter is required: {", ".join(required_any)}')
    for group in tool_info.get('paired_parameters') or []:
        present = [_has_parameter_value(params.get(name)) for name in group]
        if any(present) and not all(present):
            errors.append(f'Parameters must be provided together: {", ".join(group)}')
    for requirement in tool_info.get('conditional_requirements') or []:
        if not _has_parameter_value(params.get(requirement.get('when'))):
            continue
        dependent_name = requirement.get('parameter')
        dependent_value = params.get(dependent_name)
        dependent_values = dependent_value if isinstance(dependent_value, list) else [dependent_value]
        dependent_count = len([item for item in dependent_values if _has_parameter_value(item)])
        minimum_items = requirement.get('minimum_items')
        maximum_items = requirement.get('maximum_items')
        if minimum_items is not None and dependent_count < int(minimum_items):
            errors.append(f"Parameter '{dependent_name}' requires at least {minimum_items} value(s) when '{requirement.get('when')}' is enabled")
        if maximum_items is not None and dependent_count > int(maximum_items):
            errors.append(f"Parameter '{dependent_name}' accepts at most {maximum_items} value(s) when '{requirement.get('when')}' is enabled")
    return errors


def _parameter_path_role(param: dict) -> str | None:
    explicit = param.get('path_role')
    if explicit:
        return str(explicit)
    if param.get('type') in {'file', 'directory'}:
        return 'input'
    return None


def _rejects_option_like_values(param: dict) -> bool:
    """Whether a free-form value for this parameter may start with '-'.

    Commands run with shell=False, so a value can never start a second process,
    but a value such as '--outdir' is still consumed by the tool as an option of
    its own and would escape the project workspace. Values constrained by
    `options`, `pattern`, or a resolved path role are already safe, and numeric
    types are rejected earlier by their own conversion.
    """
    if param.get('type') != 'string':
        return False
    if param.get('options') or param.get('pattern'):
        return False
    if _parameter_path_role(param):
        return False
    return not param.get('allow_option_like', False)


def _resolve_shared_path(value: str) -> Path:
    root = Path(os.getenv('APPAM_DATABASES_ROOT', '/databases')).expanduser().resolve()
    raw_value = str(value).strip()
    candidate = Path(raw_value).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f'Path escapes the shared database root: {value}')
    return candidate


def _resolve_parameter_path(project_id: str, param: dict, value: str) -> Path:
    scope = param.get('path_scope', 'project')
    if scope == 'shared':
        path = _resolve_shared_path(value)
    elif scope == 'project':
        path = resolve_project_path(project_id, value)
    else:
        raise ValueError(f'Unsupported path scope for {param["name"]}: {scope}')

    selector = param.get('path_select')
    if selector and path.is_dir():
        matches = sorted(candidate for candidate in path.rglob(str(selector)) if candidate.is_file())
        if not matches:
            raise ValueError(f'No file matching {selector} found under {path}')
        path = matches[0]
    return path


def _validate_input_path(path: Path, param: dict) -> None:
    if param.get('path_exists', True) is False:
        return

    path_kind = param.get('path_kind') or param.get('type')
    if path_kind == 'file':
        require_existing_file(path, param['name'])
    elif path_kind == 'directory':
        require_existing_directory(path, param['name'])
    elif path_kind == 'prefix':
        if not path.parent.is_dir() or not any(path.parent.glob(f'{path.name}*')):
            raise ValueError(f'{param["name"]} prefix not found: {path}')
    elif path_kind == 'any':
        if not path.exists():
            raise ValueError(f'{param["name"]} not found: {path}')
    else:
        raise ValueError(f'Unsupported path kind for {param["name"]}: {path_kind}')


def _prepare_output_path(path: Path, param: dict) -> None:
    path_kind = param.get('path_kind') or param.get('type')
    if path_kind == 'directory' and param.get('create_output_directory'):
        ensure_directory(path)
    else:
        ensure_directory(path.parent)


def _render_parameter_values(
    project_id: str,
    param: dict,
    value,
    *,
    prepare_outputs: bool,
) -> tuple[list[str], list[Path]]:
    values = value if isinstance(value, list) else [value]
    rendered_values = []
    output_paths = []
    path_role = _parameter_path_role(param)
    reject_option_like = _rejects_option_like_values(param)

    for item in values:
        if path_role:
            path = _resolve_parameter_path(project_id, param, str(item))
            if path_role == 'input':
                _validate_input_path(path, param)
            elif path_role == 'output':
                output_paths.append(path)
                if prepare_outputs:
                    _prepare_output_path(path, param)
            else:
                raise ValueError(f'Unsupported path role for {param["name"]}: {path_role}')
            rendered_values.append(str(path))
        else:
            rendered = str(item)
            if reject_option_like and rendered.startswith('-'):
                raise ValueError(
                    f'{param["name"]} value must not start with "-": {rendered}'
                )
            rendered_values.append(rendered)

    join_with = param.get('join')
    if join_with is not None and rendered_values:
        rendered_values = [str(join_with).join(rendered_values)]
    return rendered_values, output_paths


def _append_parameter_value(
    argv: list[str],
    param: dict,
    value,
    project_id: str,
    *,
    prepare_outputs: bool = True,
) -> tuple[list[Path], str | None, str | None]:
    if not _has_parameter_value(value):
        return [], None, None

    if param.get('type') == 'flag':
        if value:
            argv.append(param['name'])
        return [], None, None

    rendered_values, output_paths = _render_parameter_values(
        project_id,
        param,
        value,
        prepare_outputs=prepare_outputs,
    )
    stream = param.get('stream')
    if stream:
        if len(rendered_values) != 1:
            raise ValueError(f'{param["name"]} must contain exactly one path')
        if stream == 'stdin':
            return output_paths, rendered_values[0], None
        if stream == 'stdout':
            return output_paths, None, rendered_values[0]
        raise ValueError(f'Unsupported stream for {param["name"]}: {stream}')

    positional = param.get('position') is not None or param.get('positional', False)
    if positional:
        argv.extend(rendered_values)
        return output_paths, None, None

    if param.get('repeat'):
        for rendered in rendered_values:
            argv.extend([param['name'], rendered])
        return output_paths, None, None

    separator = param.get('separator')
    if separator is not None:
        argv.extend(f'{param["name"]}{separator}{rendered}' for rendered in rendered_values)
        return output_paths, None, None

    argv.append(param['name'])
    argv.extend(rendered_values)
    return output_paths, None, None


def _validate_parameter_groups(tool_info: dict, params: dict) -> None:
    errors = validate_parameter_values(tool_info, params)
    if errors:
        raise ValueError('; '.join(errors))


def _validate_execution_requirements(execution: dict) -> list[dict]:
    checks = []
    for requirement in execution.get('required_paths') or []:
        path = Path(str(requirement.get('path') or '')).expanduser().resolve()
        label = requirement.get('label') or 'Runtime resource'
        kind = requirement.get('kind', 'any')
        if kind == 'file':
            require_existing_file(path, label)
        elif kind == 'directory':
            require_existing_directory(path, label)
        elif kind == 'any':
            if not path.exists():
                raise ValueError(f'{label} not found: {path}')
        else:
            raise ValueError(f'Unsupported runtime path kind for {label}: {kind}')
        checks.append({'name': label, 'status': 'ok', 'message': f'{label} found: {path}'})
    return checks


def _build_command_job(project_id: str, job_id: str, tool_info: dict, params: dict) -> dict:
    execution = tool_info.get('execution') or {}
    command = execution.get('command')
    if not command:
        raise ValueError(f'No executable configured for {tool_info["tool_name"]}')

    executable = resolve_executable(command, tool_info['tool_name'])
    _validate_execution_requirements(execution)
    _validate_parameter_groups(tool_info, params)
    argv = [executable, *[str(item) for item in execution.get('prefix_args', [])]]
    output_paths = []
    stdin_path = None
    stdout_path = None

    indexed_params = list(enumerate(tool_info.get('parameters', [])))
    ordered_params = sorted(
        indexed_params,
        key=lambda item: (
            item[1].get('order', 100 if item[1].get('position') is not None or item[1].get('positional') else 50),
            item[0],
        ),
    )

    for _, param in ordered_params:
        param_name = param['name']
        value = params.get(param_name)
        if param.get('required') and not _has_parameter_value(value):
            raise ValueError(f'Required parameter is missing: {param_name}')
        if not _has_parameter_value(value):
            continue
        rendered_outputs, rendered_stdin, rendered_stdout = _append_parameter_value(
            argv,
            param,
            value,
            project_id,
        )
        output_paths.extend(rendered_outputs)
        if rendered_stdin:
            if stdin_path:
                raise ValueError('Only one stdin parameter is supported')
            stdin_path = rendered_stdin
        if rendered_stdout:
            if stdout_path:
                raise ValueError('Only one stdout parameter is supported')
            stdout_path = rendered_stdout

    project_dir = get_project_dir(project_id)
    log_dir = project_dir / 'logs'
    ensure_directory(log_dir)

    display_command = command_to_string(argv)
    if stdin_path:
        display_command += f' < {shlex.quote(stdin_path)}'
    if stdout_path:
        display_command += f' > {shlex.quote(stdout_path)}'

    command_spec = {
        'argv': argv,
        'cwd': str(project_dir),
    }
    if execution.get('env'):
        command_spec['env'] = {str(name): str(value) for name, value in execution['env'].items()}
    if stdin_path:
        command_spec['stdin_path'] = stdin_path
    if stdout_path:
        command_spec['stdout_path'] = stdout_path

    return {
        'display_command': display_command,
        'log_path': str(log_dir / f'{job_id}.log'),
        'output_path': str(output_paths[0]) if output_paths else None,
        'work_dir': str(project_dir),
        'execution_mode': 'command',
        'is_dry_run': False,
        'command_spec': command_spec,
    }


def _preflight_command_job(project_id: str, tool_info: dict, params: dict) -> dict:
    execution = tool_info.get('execution') or {}
    executable = resolve_executable(execution.get('command'), tool_info['tool_name'])
    _validate_parameter_groups(tool_info, params)
    checks = [
        {'name': 'tool', 'status': 'ok', 'message': f'Executable resolved: {executable}'},
    ]
    checks.extend(_validate_execution_requirements(execution))
    for param in tool_info.get('parameters', []):
        value = params.get(param['name'])
        if param.get('required') and not _has_parameter_value(value):
            raise ValueError(f'Required parameter is missing: {param["name"]}')
        if not _has_parameter_value(value) or not _parameter_path_role(param):
            continue
        rendered, _ = _render_parameter_values(
            project_id,
            param,
            value,
            prepare_outputs=False,
        )
        role = _parameter_path_role(param)
        label = 'Input found' if role == 'input' else 'Output path ready'
        checks.append({'name': param['name'], 'status': 'ok', 'message': f'{label}: {", ".join(rendered)}'})
    return {'ok': True, 'mode': 'command', 'checks': checks}


def _appam_smk_context(project_id: str, job_id: str, params: dict, run_id: str, write_files: bool, *, source_run: dict | None = None, mode: str = 'run') -> dict:
    workflow_id = 'appam-smk'
    workflow_root = APPAM_SMK_ROOT
    snakefile = require_existing_file(workflow_root / 'workflow' / 'Snakefile', 'APPAM-SMK Snakefile')

    default_config_path = workflow_root / 'config' / 'config.yaml'
    frozen_source = mode in {'resume', 'retry'} and source_run is not None
    source_config_path = None
    source_config = None
    if frozen_source:
        source_config_path, source_config = _load_frozen_source_config(project_id, source_run, default_config_path)
        sample_manifest = require_existing_file(
            _project_scoped_path(project_id, source_config.get('samples_file', ''), 'Frozen APPAM-SMK sample manifest'),
            'Frozen APPAM-SMK sample manifest',
        )
        raw_data_dir = require_existing_directory(
            _project_scoped_path(project_id, (source_config.get('paths') or {}).get('raw_data_dir', ''), 'Frozen APPAM-SMK raw data directory'),
            'Frozen APPAM-SMK raw data directory',
        )
        runtime_settings = _runtime_settings_from_appam_config(source_config)
    else:
        sample_manifest = require_existing_file(resolve_project_path(project_id, params.get('sample_manifest', '')), 'APPAM-SMK sample manifest')
        raw_data_dir = require_existing_directory(resolve_project_path(project_id, params.get('raw_data_dir', '')), 'APPAM-SMK raw data directory')
        runtime_settings = get_appam_smk_runtime_settings(params)

    runtime_checks = validate_appam_smk_runtime(runtime_settings)
    from .database_manifest import load_database_manifest, validate_database_manifest

    database_manifest = load_database_manifest()
    manifest_found = bool(database_manifest.get('found'))
    module_resources = {
        'enable_checkm2': 'checkm2_db',
        'enable_gunc': 'gunc_db',
        'enable_gtdbtk': 'gtdbtk_db',
        'enable_prokka': 'prokka_db',
        'enable_eggnog': 'eggnog_db',
        'enable_abricate': 'abricate_db',
        'enable_rgi': 'rgi_db',
        'enable_antismash': 'antismash_db',
    }
    required_manifest_resources = [
        resource
        for module, resource in module_resources.items()
        if runtime_settings['modules'].get(module)
    ]
    if runtime_settings['modules'].get('enable_bin_refinement') or runtime_settings['modules'].get('enable_checkm1'):
        required_manifest_resources.append('checkm1_db')
    manifest_errors = validate_database_manifest(database_manifest, required_manifest_resources)
    require_manifest = bool(params.get('require_database_manifest'))
    if require_manifest and manifest_errors:
        raise ValueError('Publication database manifest is incomplete: ' + '; '.join(manifest_errors[:10]))
    if not manifest_found and not required_manifest_resources:
        manifest_status = 'skipped'
        manifest_message = 'Database manifest not required by enabled modules'
    elif manifest_errors:
        manifest_status = 'error' if require_manifest else 'warn'
        manifest_message = 'Database manifest incomplete: ' + '; '.join(manifest_errors[:5])
    else:
        manifest_status = 'ok'
        manifest_message = f'Database manifest validated: {database_manifest.get("path")}'
    runtime_checks.append({
        'name': 'database_manifest',
        'status': manifest_status,
        'required': require_manifest,
        'message': manifest_message,
    })
    runtime_metadata = collect_appam_smk_runtime_metadata(runtime_settings)
    runtime_metadata['database_manifest'] = _database_manifest_snapshot(
        database_manifest,
        manifest_errors,
        required_manifest_resources,
    )
    input_validation = validate_appam_smk_manifest(
        project_id,
        _project_relative_value(project_id, sample_manifest),
        _project_relative_value(project_id, raw_data_dir),
    )
    if not input_validation.get('ok'):
        details = '; '.join(check['message'] for check in input_validation.get('checks', []) if check.get('status') == 'error')
        raise ValueError(f'APPAM-SMK input validation failed: {details}')
    tools = runtime_settings['tools']
    databases = runtime_settings['databases']
    modules = runtime_settings['modules']

    metawrap_env = tools['metawrap_env']
    pydamage_env = tools['pydamage_env']
    checkm1_db = databases['checkm1_db']
    checkm2_db = databases['checkm2_db']
    gunc_db = databases['gunc_db']
    eggnog_db = databases['eggnog_db']

    profile = str(params.get('profile', 'local')).strip() or 'local'
    profile_dir = require_existing_directory(workflow_root / 'profiles' / profile, f'APPAM-SMK profile "{profile}"')
    snakemake_bin = get_snakemake_bin()
    cores = int(params.get('cores', 4))
    backend = (
        str(source_run.get('backend') or 'local')
        if frozen_source
        else resolve_backend_name(params.get('execution_backend') or os.getenv('APPAM_SMK_EXECUTION_BACKEND'), profile=profile)
    )

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
    benchmark_dir = run_paths['metadata_dir'] / 'benchmarks'
    log_path = run_paths['logs_dir'] / f'{job_id}.log'

    if mode == 'resume':
        resolved_sample_manifest = sample_manifest
        config_data = copy.deepcopy(source_config)
    else:
        resolved_sample_manifest = run_paths['config_dir'] / 'samples.resolved.tsv'
        if frozen_source:
            config_data = copy.deepcopy(source_config)
            config_data['samples_file'] = str(resolved_sample_manifest)
            config_data['paths'] = {
                **(config_data.get('paths') or {}),
                'raw_data_dir': str(raw_data_dir),
                'results_dir': str(run_paths['results_dir']),
                'logs_dir': str(run_paths['logs_dir']),
                'benchmark_dir': str(benchmark_dir),
            }
        else:
            config_overrides = {
                'samples_file': str(resolved_sample_manifest),
                'paths': {
                    'raw_data_dir': str(raw_data_dir),
                    'results_dir': str(run_paths['results_dir']),
                    'logs_dir': str(run_paths['logs_dir']),
                    'benchmark_dir': str(benchmark_dir),
                },
                'params': {
                    'preprocess_method': params.get('preprocess_method', 'fastp'),
                    'min_contig_len': int(params.get('min_contig_len', 500)),
                    'use_ancient_contigs': bool(params.get('use_ancient_contigs', False)),
                    'enable_bin_refinement': bool(modules.get('enable_bin_refinement', False)),
                    'unrefined_binner': str(params.get('unrefined_binner', 'metabat2')),
                    'annotation_threads': int(params.get('annotation_threads', 8)),
                    'abricate_db': params.get('abricate_db', 'vfdb'),
                    'abricate_minid': int(params.get('abricate_minid', 80)),
                    'abricate_mincov': int(params.get('abricate_mincov', 80)),
                    'enable_checkm1': bool(modules.get('enable_checkm1', False)),
                    'enable_checkm2': bool(modules.get('enable_checkm2', True)),
                    'enable_gunc': bool(modules.get('enable_gunc', True)),
                    'enable_gtdbtk': bool(modules.get('enable_gtdbtk', True)),
                    'enable_prokka': bool(modules.get('enable_prokka', True)),
                    'enable_eggnog': bool(modules.get('enable_eggnog', False)),
                    'enable_abricate': bool(modules.get('enable_abricate', False)),
                    'enable_rgi': bool(modules.get('enable_rgi', False)),
                    'enable_antismash': bool(modules.get('enable_antismash', False)),
                    'enable_variants': bool(modules.get('enable_variants', False)),
                },
                'databases': {
                    'checkm_db': str(checkm1_db),
                    'checkm1_db': str(checkm1_db),
                    'checkm2_db': str(checkm2_db),
                    'gunc_db': str(gunc_db),
                    'gtdbtk_db': str(databases.get('gtdbtk_db')),
                    'eggnog_db': str(eggnog_db),
                    'abricate_db': str(databases.get('abricate_db')),
                    'rgi_db_mode': str(databases.get('rgi_db_mode')),
                    'rgi_db': str(databases.get('rgi_db') or ''),
                    'antismash_db': str(databases.get('antismash_db')),
                    'prokka_db': str(databases.get('prokka_db')),
                },
                'tools': {
                    'preprocessing_env': str(tools.get('preprocessing_env')),
                    'mapping_env': str(tools.get('mapping_env')),
                    'assembly_env': str(tools.get('assembly_env')),
                    'metawrap_env': str(metawrap_env),
                    'pydamage_env': str(pydamage_env),
                    'checkm1_env': str(tools.get('checkm1_env')),
                    'checkm2_env': str(tools.get('checkm2_env')),
                    'gunc_env': str(tools.get('gunc_env')),
                    'gtdbtk_env': str(tools.get('gtdbtk_env')),
                    'prokka_env': str(tools.get('prokka_env')),
                    'eggnog_env': str(tools.get('eggnog_env')),
                    'abricate_env': str(tools.get('abricate_env')),
                    'rgi_env': str(tools.get('rgi_env')),
                    'antismash_env': str(tools.get('antismash_env')),
                    'freebayes_env': str(tools.get('freebayes_env')),
                    'bcftools_env': str(tools.get('bcftools_env')),
                    'reporting_env': str(tools.get('reporting_env')),
                },
                'variants': {
                    'min_alternate_fraction': float(params.get('min_alternate_fraction', 0.33)),
                    'min_base_quality': int(params.get('min_base_quality', 20)),
                    'min_variant_quality': int(params.get('min_variant_quality', 30)),
                    'rescue_variant_quality': int(params.get('rescue_variant_quality', 20)),
                    'rescue_alternate_observations': int(params.get('rescue_alternate_observations', 2)),
                },
                'visualization': {
                    'enabled': bool(modules.get('enable_visualization', True)),
                    'reads_length_bin_size': int(params.get('reads_length_bin_size', 10)),
                    'ani_bin_start': int(params.get('ani_bin_start', 95)),
                    'ani_bin_end': int(params.get('ani_bin_end', 100)),
                    'ani_bin_step': int(params.get('ani_bin_step', 1)),
                    'rose_chart_min_fraction': float(params.get('rose_chart_min_fraction', 0.01)),
                    'species_top_n': int(params.get('species_top_n', 10)),
                },
            }
            config_data = _materialize_config(default_config_path, config_overrides)
    hash_mode = str(params.get('input_hash_mode', 'metadata')).strip().lower()
    if hash_mode not in {'metadata', 'sha256'}:
        raise ValueError('input_hash_mode must be metadata or sha256')
    input_provenance = []
    for sample in input_validation.get('samples') or []:
        for read_name in ('forward_reads', 'reverse_reads'):
            fingerprint = fingerprint_path(resolve_project_path(project_id, sample[read_name]), hash_mode)
            fingerprint.update({'sample_id': sample['sample_id'], 'input_role': read_name})
            input_provenance.append(fingerprint)
    source_input_verification = _verify_source_inputs(project_id, source_run if frozen_source else None, input_provenance)
    source_runtime_verification = _verify_source_runtime(
        project_id,
        source_run if frozen_source else None,
        runtime_metadata,
    )

    if write_files:
        for directory in (
            run_paths['run_dir'],
            run_paths['config_dir'],
            run_paths['logs_dir'],
            run_paths['metadata_dir'],
            run_paths['results_dir'],
            run_paths['reports_dir'],
            run_paths['work_dir'],
            benchmark_dir,
        ):
            ensure_directory(directory)
        if mode != 'resume':
            write_resolved_appam_smk_manifest(project_id, input_validation, resolved_sample_manifest)
            generated_config.write_text(yaml.safe_dump(config_data, sort_keys=False), encoding='utf-8')

    resolved_input_record = _resolved_input_record(resolved_sample_manifest, 'appam_smk_sample_manifest')

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
        'resolved_sample_manifest': resolved_sample_manifest,
        'resolved_input_record': resolved_input_record,
        'source_config_path': source_config_path,
        'raw_data_dir': raw_data_dir,
        'metawrap_env': str(metawrap_env),
        'pydamage_env': str(pydamage_env),
        'checkm_db': str(checkm1_db),
        'checkm1_db': str(checkm1_db),
        'checkm2_db': str(checkm2_db),
        'gunc_db': str(gunc_db),
        'eggnog_db': str(eggnog_db),
        'runtime_settings': runtime_settings,
        'runtime_checks': runtime_checks,
        'runtime_metadata': runtime_metadata,
        'workflow_revision': repository_state(REPO_ROOT),
        'input_provenance': input_provenance,
        'source_input_verification': source_input_verification,
        'source_runtime_verification': source_runtime_verification,
        'config_sha256': sha256_bytes(yaml.safe_dump(config_data, sort_keys=False).encode('utf-8')),
        'input_validation': input_validation,
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

    default_config_path = workflow_root / 'config' / 'config.yaml'
    frozen_source = mode in {'resume', 'retry'} and source_run is not None
    source_config_path = None
    source_config = None
    if frozen_source:
        source_config_path, source_config = _load_frozen_source_config(project_id, source_run, default_config_path)
        sample_table = require_existing_file(
            _project_scoped_path(project_id, source_config.get('sample_table', ''), 'Frozen paleoproteomics sample table'),
            'Frozen paleoproteomics sample table',
        )
        fasta_path = require_existing_file(
            resolve_project_or_absolute_path(project_id, source_config.get('fasta_path', '')),
            'Frozen reference FASTA',
        )
        runtime_values = source_config
    else:
        sample_table = require_existing_file(resolve_project_path(project_id, params.get('sample_table', '')), 'Paleoproteomics sample table')
        fasta_path = require_existing_file(resolve_project_or_absolute_path(project_id, params.get('fasta_path', '')), 'Reference FASTA')
        runtime_values = params

    input_validation = validate_paleoproteomics_table(project_id, _project_relative_value(project_id, sample_table))
    if not input_validation.get('ok'):
        details = '; '.join(check['message'] for check in input_validation.get('checks', []) if check.get('status') == 'error')
        raise ValueError(f'Paleoproteomics input validation failed: {details}')

    validated_input_paths = [
        resolve_project_path(project_id, sample['input_path'])
        for sample in input_validation.get('samples') or []
    ]
    requires_thermo = any(path.is_file() and path.suffix.lower() == '.raw' for path in validated_input_paths)
    requires_timsconvert = any(path.is_dir() and path.name.lower().endswith('.d') for path in validated_input_paths)

    dotnet_bin = resolve_executable(_required_config_value(runtime_values, 'dotnet_bin', 'APPAM_PALEO_DOTNET_BIN') or 'dotnet', 'dotnet')
    maxquant_cmd_dll = _required_config_value(runtime_values, 'maxquant_cmd_dll', 'APPAM_PALEO_MAXQUANT_CMD')
    thermo_value = _required_config_value(runtime_values, 'thermo_raw_file_parser', 'APPAM_PALEO_THERMO_RAW_FILE_PARSER') or 'ThermoRawFileParser'
    timsconvert_value = _required_config_value(runtime_values, 'timsconvert_bin', 'APPAM_PALEO_TIMSCONVERT_BIN') or 'timsconvert'
    thermo_raw_file_parser = resolve_executable(thermo_value, 'ThermoRawFileParser') if requires_thermo else str(thermo_value)
    timsconvert_bin = resolve_executable(timsconvert_value, 'timsconvert') if requires_timsconvert else str(timsconvert_value)
    openms_fileconverter = resolve_executable(
        _required_config_value(runtime_values, 'openms_fileconverter', 'APPAM_PALEO_OPENMS_FILECONVERTER') or 'FileConverter',
        'OpenMS FileConverter',
    )
    runtime_env_value = _required_config_value(runtime_values, 'runtime_env', 'APPAM_PALEO_ENV')
    if not runtime_env_value:
        raise ValueError('Missing paleoproteomics runtime settings: runtime_env / APPAM_PALEO_ENV')
    runtime_env = require_existing_directory(
        Path(str(runtime_env_value)).expanduser().resolve(),
        'Paleoproteomics Conda environment',
    )

    if not maxquant_cmd_dll:
        raise ValueError('Missing paleoproteomics runtime settings: maxquant_cmd_dll / APPAM_PALEO_MAXQUANT_CMD')
    maxquant_cmd_dll = require_existing_file(Path(str(maxquant_cmd_dll)).expanduser().resolve(), 'MaxQuantCmd.dll')

    backend = (
        str(source_run.get('backend') or 'local')
        if frozen_source
        else resolve_backend_name(params.get('execution_backend') or os.getenv('APPAM_PALEO_EXECUTION_BACKEND'), profile='local')
    )
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
    if mode == 'resume':
        resolved_sample_table = sample_table
        config_data = copy.deepcopy(source_config)
        maxquant_output_dir = _project_scoped_path(
            project_id,
            config_data.get('maxquant_output_dir', run_paths['results_dir'] / 'maxquant'),
            'Frozen MaxQuant output directory',
        )
    else:
        resolved_sample_table = run_paths['config_dir'] / 'samples.resolved.tsv'
        maxquant_output_dir = run_paths['results_dir'] / 'maxquant'
        if frozen_source:
            config_data = copy.deepcopy(source_config)
            config_data.update({
                'sample_table': str(resolved_sample_table),
                'results_dir': str(run_paths['results_dir']),
                'maxquant_output_dir': str(maxquant_output_dir),
            })
        else:
            maxquant_mode = str(params.get('maxquant_mode', 'batch')).strip().lower()
            if maxquant_mode not in {'batch', 'per_sample_id'}:
                raise ValueError('maxquant_mode must be batch or per_sample_id')
            config_overrides = {
                'sample_table': str(resolved_sample_table),
                'mqpar_template': str(workflow_root / 'workflow' / 'templates' / 'mqpar.template.xml'),
                'results_dir': str(run_paths['results_dir']),
                'maxquant_output_dir': str(maxquant_output_dir),
                'threads': int(params.get('cores', 4)),
                'runtime_env': str(runtime_env),
                'maxquant_version': os.getenv('APPAM_PALEO_MAXQUANT_VERSION', '2.8.1.0'),
                'maxquant_mode': maxquant_mode,
                'fasta_path': str(fasta_path),
                'match_between_runs': bool(params.get('match_between_runs', False)),
                'enzymes': _list_parameter(params, 'enzymes', ['Trypsin/P']),
                'enzyme_mode': int(params.get('enzyme_mode', 4)),
                'max_missed_cleavages': int(params.get('max_missed_cleavages', 0)),
                'max_missed_cleavages_dia': int(params.get('max_missed_cleavages_dia', params.get('max_missed_cleavages', 0))),
                'identifier_parse_rule': str(params.get('identifier_parse_rule', r'^>((tr\|)|(sp\|))?(\S+)')),
                'description_parse_rule': str(params.get('description_parse_rule', r'^\S+\s+(.*)$')),
                'fixed_modifications': _list_parameter(params, 'fixed_modifications', ['Carbamidomethyl (C)']),
                'variable_modifications': _list_parameter(
                    params,
                    'variable_modifications',
                    ['Deamidation (NQ)', 'Oxidation (MP)', 'Gln->pyro-Glu', 'Glu->pyro-Glu', 'Phospho (ST)'],
                ),
                'peptide_fdr': float(params.get('peptide_fdr', 0.01)),
                'protein_fdr': float(params.get('protein_fdr', 0.01)),
                'site_fdr': float(params.get('site_fdr', 0.01)),
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
            config_data = _materialize_config(default_config_path, config_overrides)
    hash_mode = str(params.get('input_hash_mode', 'metadata')).strip().lower()
    if hash_mode not in {'metadata', 'sha256'}:
        raise ValueError('input_hash_mode must be metadata or sha256')
    input_provenance = []
    for sample in input_validation.get('samples') or []:
        fingerprint = fingerprint_path(resolve_project_path(project_id, sample['input_path']), hash_mode)
        fingerprint.update({'sample_id': sample['sample_id'], 'input_role': 'mass_spectrometry_raw'})
        input_provenance.append(fingerprint)
    fasta_fingerprint = fingerprint_path(fasta_path, hash_mode)
    fasta_fingerprint['input_role'] = 'reference_fasta'
    input_provenance.append(fasta_fingerprint)
    source_input_verification = _verify_source_inputs(project_id, source_run if frozen_source else None, input_provenance)
    runtime_checks = [
        {'name': 'runtime_env', 'status': 'ok', 'required': True, 'message': f'Paleoproteomics environment: {runtime_env}'},
        {'name': 'dotnet', 'status': 'ok', 'required': True, 'message': f'dotnet: {dotnet_bin}'},
        {'name': 'maxquant', 'status': 'ok', 'required': True, 'message': f'MaxQuantCmd.dll: {maxquant_cmd_dll}'},
        {'name': 'ThermoRawFileParser', 'status': 'ok' if requires_thermo else 'skipped', 'required': requires_thermo, 'message': f'ThermoRawFileParser: {thermo_raw_file_parser}' if requires_thermo else 'ThermoRawFileParser not required by this sample table'},
        {'name': 'timsconvert', 'status': 'ok' if requires_timsconvert else 'skipped', 'required': requires_timsconvert, 'message': f'timsconvert: {timsconvert_bin}' if requires_timsconvert else 'timsconvert not required by this sample table'},
        {'name': 'OpenMS FileConverter', 'status': 'ok', 'required': True, 'message': f'FileConverter: {openms_fileconverter}'},
    ]
    runtime_metadata = {
        'runtime_env': conda_environment_fingerprint(str(runtime_env)),
        'maxquant_cmd_dll': fingerprint_path(maxquant_cmd_dll, 'sha256'),
        'dotnet_bin': fingerprint_path(dotnet_bin, 'metadata'),
        'thermo_raw_file_parser': fingerprint_path(thermo_raw_file_parser, 'metadata'),
        'timsconvert_bin': fingerprint_path(timsconvert_bin, 'metadata'),
        'openms_fileconverter': fingerprint_path(openms_fileconverter, 'metadata'),
    }
    source_runtime_verification = _verify_source_runtime(
        project_id,
        source_run if frozen_source else None,
        runtime_metadata,
    )

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
        if mode != 'resume':
            write_resolved_paleoproteomics_table(project_id, input_validation, resolved_sample_table)
            generated_config.write_text(yaml.safe_dump(config_data, sort_keys=False), encoding='utf-8')

    resolved_input_record = _resolved_input_record(resolved_sample_table, 'paleoproteomics_sample_table')

    snakemake_bin = get_snakemake_bin()
    cores = int(config_data.get('threads', params.get('cores', 4)))
    argv = [
        snakemake_bin,
        '-s',
        str(snakefile),
        '--configfile',
        str(generated_config),
        '--cores',
        str(cores),
        '--software-deployment-method',
        'conda',
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
        '--software-deployment-method',
        'conda',
        '--unlock',
    ]

    return {
        'workflow_id': workflow_id,
        'workflow_root': workflow_root,
        'snakefile': snakefile,
        'sample_table': sample_table,
        'resolved_sample_table': resolved_sample_table,
        'resolved_input_record': resolved_input_record,
        'source_config_path': source_config_path,
        'fasta_path': fasta_path,
        'runtime_env': runtime_env,
        'runtime_settings': {
            'runtime_env': str(runtime_env),
            'dotnet_bin': str(dotnet_bin),
            'maxquant_cmd_dll': str(maxquant_cmd_dll),
            'thermo_raw_file_parser': str(thermo_raw_file_parser),
            'timsconvert_bin': str(timsconvert_bin),
            'openms_fileconverter': str(openms_fileconverter),
        },
        'runtime_checks': runtime_checks,
        'runtime_metadata': runtime_metadata,
        'input_validation': input_validation,
        'workflow_revision': repository_state(REPO_ROOT),
        'input_provenance': input_provenance,
        'source_input_verification': source_input_verification,
        'source_runtime_verification': source_runtime_verification,
        'config_sha256': sha256_bytes(yaml.safe_dump(config_data, sort_keys=False).encode('utf-8')),
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
            'preflight_id': context.get('preflight_id') or params.get('_preflight_id'),
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


def _preflight_dry_run_enabled() -> bool:
    return os.getenv('APPAM_PREFLIGHT_DRY_RUN', 'true').strip().lower() not in {'0', 'false', 'no', 'off'}


def _preflight_dry_run_timeout() -> int:
    try:
        return max(5, int(os.getenv('APPAM_PREFLIGHT_DRY_RUN_TIMEOUT', '120')))
    except Exception:
        return 120


def _snakemake_dry_run_check(context: dict) -> dict:
    if not _preflight_dry_run_enabled():
        return {
            'name': 'snakemake_dry_run',
            'status': 'warn',
            'message': 'Snakemake dry-run check is disabled by APPAM_PREFLIGHT_DRY_RUN.',
        }

    argv = [str(part) for part in context.get('argv') or []]
    if '-n' not in argv and '--dry-run' not in argv:
        argv.append('-n')
    timeout = _preflight_dry_run_timeout()
    try:
        result = subprocess.run(
            argv,
            cwd=str(context['workflow_root']),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            'name': 'snakemake_dry_run',
            'status': 'error',
            'message': f'Snakemake dry-run timed out after {timeout}s.',
        }
    except Exception as exc:
        return {
            'name': 'snakemake_dry_run',
            'status': 'error',
            'message': f'Snakemake dry-run failed to start: {exc}',
        }

    output = (result.stdout or '').strip()
    tail = '\n'.join(output.splitlines()[-12:])
    if result.returncode == 0:
        return {
            'name': 'snakemake_dry_run',
            'status': 'ok',
            'message': 'Snakemake dry-run completed successfully.',
            'details': tail,
        }
    return {
        'name': 'snakemake_dry_run',
        'status': 'error',
        'message': f'Snakemake dry-run failed with exit code {result.returncode}.',
        'details': tail,
    }


def _preflight_appam_smk(project_id: str, tool_info: dict, params: dict) -> dict:
    preview_run_id = 'preflight-preview'
    context = _appam_smk_context(project_id, 'preflight', params, preview_run_id, write_files=True)
    checks = [
        {'name': 'snakemake', 'status': 'ok', 'message': f'Snakemake resolved: {get_snakemake_bin()}'},
        {'name': 'snakefile', 'status': 'ok', 'message': f'Snakefile found: {context["snakefile"]}'},
        {'name': 'sample_manifest', 'status': 'ok', 'message': f'Sample manifest found: {context["sample_manifest"]}'},
        {'name': 'raw_data_dir', 'status': 'ok', 'message': f'Raw data directory found: {context["raw_data_dir"]}'},
        {'name': 'profile', 'status': 'ok', 'message': f'Profile ready: {context["profile"]}'},
    ]
    checks.extend(context.get('input_validation', {}).get('checks') or [])
    checks.extend(context.get('runtime_checks') or [])
    checks.append(_snakemake_dry_run_check(context))
    ok = not any(check.get('status') == 'error' for check in checks)
    return {
        'ok': ok,
        'mode': 'snakemake',
        'workflow_id': context['workflow_id'],
        'checks': checks,
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
    context = _paleoproteomics_context(project_id, 'preflight', params, preview_run_id, write_files=True)
    checks = [
        {'name': 'snakemake', 'status': 'ok', 'message': f'Snakemake resolved: {get_snakemake_bin()}'},
        {'name': 'snakefile', 'status': 'ok', 'message': f'Snakefile found: {context["snakefile"]}'},
        {'name': 'sample_table', 'status': 'ok', 'message': f'Sample table found: {context["sample_table"]}'},
        {'name': 'fasta_path', 'status': 'ok', 'message': f'Reference FASTA found: {context["fasta_path"]}'},
    ]
    checks.extend(context.get('input_validation', {}).get('checks') or [])
    checks.extend(context.get('runtime_checks') or [])
    checks.append(_snakemake_dry_run_check(context))
    ok = not any(check.get('status') == 'error' for check in checks)
    return {
        'ok': ok,
        'mode': 'snakemake',
        'workflow_id': context['workflow_id'],
        'checks': checks,
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
            'sample_id\tinput_path\texperiment\tfraction\nsample1\traw_ms/sample1.RAW\tprojectA\t1\n',
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
        checks.append({'name': 'workflow_root', 'status': 'ok', 'message': f'Workflow root ready: {workflow_root}'})
        checks.extend(get_appam_smk_runtime_checks())
        ok = not any(check.get('required') and check.get('status') == 'error' for check in checks)
        return {'ok': ok, 'workflow_id': workflow_id, 'checks': checks}

    if workflow_id == 'appam-paleoproteomics':
        workflow_root = APPAM_PALEOPROTEOMICS_ROOT
        require_existing_directory(workflow_root, 'APPAM paleoproteomics root')
        require_existing_file(workflow_root / 'workflow' / 'Snakefile', 'APPAM paleoproteomics Snakefile')
        checks.append({'name': 'workflow_root', 'status': 'ok', 'message': f'Workflow root ready: {workflow_root}'})
        runtime_env = _required_config_value({}, 'runtime_env', 'APPAM_PALEO_ENV')
        if not runtime_env:
            raise ValueError('APPAM_PALEO_ENV is not configured')
        resolved_runtime_env = require_existing_directory(
            Path(runtime_env).expanduser().resolve(),
            'Paleoproteomics Conda environment',
        )
        checks.append({'name': 'runtime_env', 'status': 'ok', 'message': f'Paleoproteomics environment: {resolved_runtime_env}'})
        checks.append({'name': 'dotnet', 'status': 'ok', 'message': f"dotnet: {resolve_executable(_required_config_value({}, 'dotnet_bin', 'APPAM_PALEO_DOTNET_BIN') or 'dotnet', 'dotnet')}"})
        maxquant_value = _required_config_value({}, 'maxquant_cmd_dll', 'APPAM_PALEO_MAXQUANT_CMD')
        if not maxquant_value:
            raise ValueError('APPAM_PALEO_MAXQUANT_CMD is not configured')
        maxquant_path = require_existing_file(Path(maxquant_value).expanduser().resolve(), 'MaxQuantCmd.dll')
        checks.append({'name': 'maxquant', 'status': 'ok', 'message': f'MaxQuantCmd.dll: {maxquant_path}'})
        for name, configured in (
            ('ThermoRawFileParser', _required_config_value({}, 'thermo_raw_file_parser', 'APPAM_PALEO_THERMO_RAW_FILE_PARSER') or 'ThermoRawFileParser'),
            ('timsconvert', _required_config_value({}, 'timsconvert_bin', 'APPAM_PALEO_TIMSCONVERT_BIN') or 'timsconvert'),
        ):
            try:
                resolved = resolve_executable(configured, name)
                checks.append({'name': name, 'status': 'ok', 'required': False, 'message': f'{name}: {resolved}'})
            except ValueError as exc:
                checks.append({'name': name, 'status': 'warn', 'required': False, 'message': str(exc)})
        checks.append({'name': 'OpenMS FileConverter', 'status': 'ok', 'message': f"FileConverter: {resolve_executable(_required_config_value({}, 'openms_fileconverter', 'APPAM_PALEO_OPENMS_FILECONVERTER') or 'FileConverter', 'OpenMS FileConverter')}"})
        return {'ok': True, 'workflow_id': workflow_id, 'checks': checks}

    raise ValueError(f'Unsupported workflow health check: {workflow_id}')
