from .database_manifest import load_database_manifest
from .job_store import (
    get_active_job,
    get_latest_job,
    list_workflow_preflights,
    list_workflow_runs,
)


def _metric_digest(metrics: list[dict], limit: int = 16) -> list[dict]:
    digest = []
    preferred_groups = {'counts', 'checkm2', 'gunc', 'gtdbtk', 'abricate', 'rgi', 'antismash', 'maxquant'}
    for metric in metrics or []:
        group = metric.get('metric_group') or metric.get('group')
        if group not in preferred_groups:
            continue
        digest.append({
            'group': group,
            'name': metric.get('metric_name') or metric.get('name'),
            'value': metric.get('metric_value') if metric.get('metric_value') is not None else metric.get('value'),
            'text': metric.get('metric_text') or metric.get('text'),
            'sample_id': metric.get('sample_id'),
            'unit': metric.get('unit'),
        })
        if len(digest) >= limit:
            break
    return digest


def _db_resource_count(database_manifest: dict) -> tuple[int, int]:
    resources = database_manifest.get('resources') or {}
    if isinstance(resources, list):
        total = len(resources)
        present = sum(1 for item in resources if item.get('exists', True))
        return present, total
    total = len(resources)
    present = 0
    for value in resources.values():
        if not isinstance(value, dict):
            present += 1
        elif value.get('exists') or value.get('builtin'):
            present += 1
    return present, total


def build_project_dashboard(project_id: str) -> dict:
    active_job = get_active_job(project_id)
    latest_job = get_latest_job(project_id)
    runs = list_workflow_runs(project_id, limit=8)
    preflights = list_workflow_preflights(project_id, limit=6)
    database_manifest = load_database_manifest()
    latest_run = runs[0] if runs else None
    latest_preflight = preflights[0] if preflights else None
    db_present, db_total = _db_resource_count(database_manifest)

    recommendations = []
    if not preflights:
        recommendations.append('Run preflight')
    elif not latest_preflight.get('ok'):
        recommendations.append('Fix preflight')
    if latest_run and latest_run.get('status') == 'failed':
        recommendations.append(f"Review failed run: {latest_run.get('failure_label') or 'logs'}.")
    if not database_manifest.get('found'):
        recommendations.append('Add database manifest')

    return {
        'active_job': active_job,
        'latest_job': latest_job,
        'latest_run': latest_run,
        'recent_runs': runs,
        'latest_preflight': latest_preflight,
        'recent_preflights': preflights,
        'database_manifest': database_manifest,
        'metrics': _metric_digest((latest_run or {}).get('metrics') or []),
        'readiness': {
            'has_passed_preflight': bool(latest_preflight and latest_preflight.get('ok')),
            'has_completed_run': any(run.get('status') == 'completed' for run in runs),
            'has_active_job': bool(active_job),
            'database_manifest_found': bool(database_manifest.get('found')),
            'database_resources_present': db_present,
            'database_resources_total': db_total,
        },
        'recommendations': recommendations,
    }
