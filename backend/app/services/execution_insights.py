from __future__ import annotations

from pathlib import Path


def _read_log_tail(log_path: str | None, limit_bytes: int = 16384) -> str:
    if not log_path:
        return ''
    path = Path(str(log_path))
    if not path.exists() or not path.is_file():
        return ''
    with path.open('rb') as handle:
        handle.seek(0, 2)
        size = handle.tell()
        handle.seek(max(0, size - limit_bytes))
        return handle.read().decode('utf-8', errors='replace')


def classify_failure(error_message: str | None = None, exit_code: int | None = None, log_path: str | None = None):
    text = ' '.join(filter(None, [str(error_message or '').strip(), _read_log_tail(log_path)])).lower()

    if not text and exit_code in (None, 0):
        return {'category': None, 'label': None, 'suggestion': None}
    if 'canceled by user' in text or 'cancellation requested' in text:
        return {'category': 'canceled', 'label': 'Canceled', 'suggestion': 'The run was intentionally stopped; retry or resume when ready.'}
    if 'authentication required' in text or 'permission denied' in text:
        return {'category': 'permissions', 'label': 'Permission / access error', 'suggestion': 'Check project role, file permissions, and mounted volume ownership.'}
    if 'path is required' in text or 'required parameter' in text or 'parameter validation failed' in text:
        return {'category': 'input_validation', 'label': 'Input validation', 'suggestion': 'Re-run manifest validation and confirm required workflow parameters.'}
    if 'out of memory' in text or 'oom' in text or 'killed' in text:
        return {'category': 'resource_limit', 'label': 'Resource limit', 'suggestion': 'Reduce threads, disable heavy annotation modules, or run on a larger machine.'}
    if 'database' in text and ('not found' in text or 'missing' in text or 'cannot open' in text):
        return {'category': 'database_missing', 'label': 'Missing database', 'suggestion': 'Check APPAM_HOST_DB_ROOT, /databases mount, and appam-db-manifest.json.'}
    if 'not found' in text or 'was not found on path' in text or 'missing' in text:
        return {'category': 'runtime_missing', 'label': 'Missing runtime or file', 'suggestion': 'Confirm the container image includes this tool and the referenced input exists.'}
    if 'snakemake' in text and ('unlock' in text or 'directory cannot be locked' in text or 'lock exception' in text):
        return {'category': 'workflow_lock', 'label': 'Workflow lock / stale state', 'suggestion': 'Use the resume path or unlock the previous Snakemake work directory.'}
    if 'snakemake' in text and ('missinginputexception' in text or 'missing input files' in text):
        return {'category': 'workflow_missing_input', 'label': 'Workflow missing input', 'suggestion': 'Inspect the preflight dry-run output and manifest paths.'}
    if 'exception occurred' in text:
        return {'category': 'platform_exception', 'label': 'Platform exception', 'suggestion': 'Inspect backend logs and provenance bundle for the failing command.'}
    if exit_code not in (None, 0):
        return {'category': 'tool_exit_nonzero', 'label': 'Tool exited non-zero', 'suggestion': 'Open logs, check the last tool command, and verify runtime resources.'}
    return {'category': 'unknown', 'label': 'Unknown failure', 'suggestion': 'Review the run log tail and compare against the last successful preflight.'}
