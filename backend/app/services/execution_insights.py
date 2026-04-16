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
        return {'category': None, 'label': None}
    if 'canceled by user' in text or 'cancellation requested' in text:
        return {'category': 'canceled', 'label': 'Canceled'}
    if 'authentication required' in text or 'permission denied' in text:
        return {'category': 'permissions', 'label': 'Permission / access error'}
    if 'path is required' in text or 'required parameter' in text or 'parameter validation failed' in text:
        return {'category': 'input_validation', 'label': 'Input validation'}
    if 'not found' in text or 'was not found on path' in text or 'missing' in text:
        return {'category': 'runtime_missing', 'label': 'Missing runtime or file'}
    if 'snakemake' in text and ('unlock' in text or 'directory cannot be locked' in text or 'lock exception' in text):
        return {'category': 'workflow_lock', 'label': 'Workflow lock / stale state'}
    if 'exception occurred' in text:
        return {'category': 'platform_exception', 'label': 'Platform exception'}
    if exit_code not in (None, 0):
        return {'category': 'tool_exit_nonzero', 'label': 'Tool exited non-zero'}
    return {'category': 'unknown', 'label': 'Unknown failure'}

