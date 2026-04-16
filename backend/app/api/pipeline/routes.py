import os
import uuid

from flask import Blueprint, g, jsonify, request

from app.auth import current_user, get_project_for_user, project_role_at_least
from app.services.pipeline_execution import (
    build_job_request,
    build_job_request_from_workflow_run,
    generate_workflow_template,
    preflight_job_request,
    runtime_health_for_workflow,
)
from app.services.job_queue import enqueue_pipeline_job
from app.services.job_store import (
    build_workflow_run_provenance,
    compare_workflow_runs,
    count_jobs,
    get_active_job,
    get_active_workflow_run,
    get_latest_job,
    get_workflow_run,
    list_jobs,
    list_process_history,
    list_workflow_runs,
)
from app.services.tool_library import get_tool_definition


pipeline_bp = Blueprint('pipeline_bp', __name__)

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))


@pipeline_bp.url_value_preprocessor
def pull_project_id(endpoint, values):
    g.pipeline_project_id = values.get('project_id') if values else None


@pipeline_bp.before_request
def ensure_project_access():
    project_id = getattr(g, 'pipeline_project_id', None)
    if not project_id:
        return None
    project = get_project_for_user(project_id, min_role='viewer')
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    g.current_project = project
    return None


def require_project_editor():
    project = getattr(g, 'current_project', None)
    if not project or not project_role_at_least(project.get('access_role'), 'editor'):
        return jsonify({'error': 'Project write access required'}), 403
    return None


def _queue_job_from_request(project_id: str, display_tool_name: str, job_request: dict, job_id: str):
    enqueue_pipeline_job(
        project_id,
        display_tool_name,
        job_request['display_command'],
        job_request['log_path'],
        job_id=job_id,
        submitted_by=current_user()['id'],
        command_spec=job_request['command_spec'],
        output_path=job_request.get('output_path'),
        work_dir=job_request.get('work_dir'),
        execution_mode=job_request.get('execution_mode', 'command'),
        workflow_id=job_request.get('workflow_id'),
        workflow_run_id=job_request.get('workflow_run_id'),
        is_dry_run=bool(job_request.get('is_dry_run')),
        workflow_run_spec=job_request.get('workflow_run_spec'),
    )


def validate_tool_params(tool_info: dict, params: dict) -> list[str]:
    validation_errors = []
    for p in tool_info['parameters']:
        param_name = p['name']
        param_value = params.get(param_name)

        if p.get('required', False) and not param_value:
            validation_errors.append(f"Required parameter '{param_name}' is missing")

        if param_value and p.get('options'):
            if isinstance(param_value, list):
                for value in param_value:
                    if value not in p['options']:
                        validation_errors.append(f"Parameter '{param_name}' value '{value}' is not in allowed options: {p['options']}")
            elif param_value not in p['options']:
                validation_errors.append(f"Parameter '{param_name}' value '{param_value}' is not in allowed options: {p['options']}")

        if param_value and p.get('type') == 'integer':
            try:
                int(param_value)
            except (ValueError, TypeError):
                validation_errors.append(f"Parameter '{param_name}' must be an integer")

        if param_value and p.get('type') == 'float':
            try:
                float(param_value)
            except (ValueError, TypeError):
                validation_errors.append(f"Parameter '{param_name}' must be a float")
    return validation_errors


def _get_limit(env_name: str, default: int) -> int:
    raw = os.getenv(env_name, str(default)).strip()
    try:
        return int(raw)
    except Exception:
        return default


def _enforce_queue_limits(project_id: str, submitted_by: str, is_dry_run: bool):
    if is_dry_run:
        return None

    max_project_running = _get_limit('APPAM_MAX_PROJECT_RUNNING', 1)
    max_project_queued = _get_limit('APPAM_MAX_PROJECT_QUEUED', 10)
    max_user_running = _get_limit('APPAM_MAX_USER_RUNNING', 1)
    max_user_queued = _get_limit('APPAM_MAX_USER_QUEUED', 10)

    project_running = count_jobs(project_id=project_id, statuses=('starting', 'running'))
    project_queued = count_jobs(project_id=project_id, statuses=('queued',))
    user_running = count_jobs(submitted_by=submitted_by, statuses=('starting', 'running'))
    user_queued = count_jobs(submitted_by=submitted_by, statuses=('queued',))

    if max_project_running >= 0 and project_running >= max_project_running:
        return jsonify({'error': f'Project running limit reached ({max_project_running}).'}), 409
    if max_project_queued >= 0 and project_queued >= max_project_queued:
        return jsonify({'error': f'Project queued limit reached ({max_project_queued}). Cancel queued jobs or wait.'}), 409
    if max_user_running >= 0 and user_running >= max_user_running:
        return jsonify({'error': f'User running limit reached ({max_user_running}).'}), 409
    if max_user_queued >= 0 and user_queued >= max_user_queued:
        return jsonify({'error': f'User queued limit reached ({max_user_queued}). Cancel queued jobs or wait.'}), 409
    return None


@pipeline_bp.route('/<project_id>/preflight/<tool_name>', methods=['POST'])
def preflight_tool_endpoint(project_id, tool_name):
    editor_error = require_project_editor()
    if editor_error:
        return editor_error

    tool_info = get_tool_definition(tool_name)
    if not tool_info:
        return jsonify({'error': f'Tool "{tool_name}" not found in library.'}), 404

    params = request.get_json() or {}
    validation_errors = validate_tool_params(tool_info, params)
    if validation_errors:
        return jsonify({'error': 'Parameter validation failed', 'details': validation_errors}), 400

    try:
        result = preflight_job_request(project_id, tool_info, params)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        return jsonify({'error': f'Failed to prepare preflight: {exc}'}), 500

    return jsonify(result)


@pipeline_bp.route('/<project_id>/run/<tool_name>', methods=['POST'])
def run_tool_endpoint(project_id, tool_name):
    editor_error = require_project_editor()
    if editor_error:
        return editor_error

    params = request.get_json() or {}
    limit_error = _enforce_queue_limits(project_id, current_user()['id'], bool(params.get('dry_run')))
    if limit_error:
        return limit_error

    tool_info = get_tool_definition(tool_name)
    if not tool_info:
        return jsonify({'error': f'Tool "{tool_name}" not found in library.'}), 404
    display_tool_name = tool_info.get('tool_name', tool_name)

    validation_errors = validate_tool_params(tool_info, params)
    if validation_errors:
        return jsonify({
            'error': 'Parameter validation failed',
            'details': validation_errors
        }), 400

    job_id = uuid.uuid4().hex
    workflow_run_id = uuid.uuid4().hex if tool_info.get('kind') == 'workflow' else None
    try:
        job_request = build_job_request(
            project_id,
            job_id,
            tool_info,
            params,
            run_id=workflow_run_id,
            submitted_by=current_user()['id'],
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        return jsonify({'error': f'Failed to prepare execution: {exc}'}), 500

    try:
        _queue_job_from_request(project_id, display_tool_name, job_request, job_id)
    except Exception as exc:
        return jsonify({'error': f'Failed to enqueue job: {exc}'}), 502

    return jsonify({
        'message': f'Tool "{display_tool_name}" queued successfully.',
        'command': job_request['display_command'],
        'job_id': job_id,
        'workflow_run_id': job_request.get('workflow_run_id'),
        'status': 'queued'
    })


@pipeline_bp.route('/<project_id>/task-status')
def task_status(project_id):
    job = get_active_job(project_id) or get_latest_job(project_id)
    if not job:
        return jsonify({'status': 'not_found'})
    workflow_run = get_workflow_run(job.get('workflow_run_id')) if job.get('workflow_run_id') else None
    return jsonify({
        'status': job.get('status'),
        'tool': job.get('tool_name'),
        'job_id': job.get('id'),
        'error': job.get('error_message'),
        'code': job.get('exit_code'),
        'submitted_by': job.get('submitted_by'),
        'submitted_by_username': job.get('submitted_by_username'),
        'submitted_by_display_name': job.get('submitted_by_display_name'),
        'claimed_by': job.get('claimed_by'),
        'claimed_at': job.get('claimed_at'),
        'heartbeat_at': job.get('heartbeat_at'),
        'pid': job.get('pid'),
        'pgid': job.get('pgid'),
        'host': job.get('host'),
        'queue_position': job.get('queue_position'),
        'failure_category': job.get('failure_category'),
        'failure_label': job.get('failure_label'),
        'workflow_run_id': job.get('workflow_run_id'),
        'workflow_id': job.get('workflow_id'),
        'current_stage_id': workflow_run.get('current_stage_id') if workflow_run else None,
        'current_stage_title': workflow_run.get('current_stage_title') if workflow_run else None,
        'current_rule': workflow_run.get('current_rule') if workflow_run else None,
        'output_root': workflow_run.get('output_root') if workflow_run else job.get('output_path'),
    })


@pipeline_bp.route('/<project_id>/history')
def process_history(project_id):
    limit = request.args.get('limit', 20, type=int)
    history = list_process_history(project_id, limit=limit)
    return jsonify(history)


@pipeline_bp.route('/<project_id>/jobs')
def job_history(project_id):
    limit = request.args.get('limit', 20, type=int)
    status = request.args.get('status')
    jobs = list_jobs(project_id, limit=limit, status=status)
    return jsonify(jobs)


@pipeline_bp.route('/<project_id>/workflow-runs')
def workflow_runs(project_id):
    workflow_id = request.args.get('workflow_id')
    limit = request.args.get('limit', 20, type=int)
    runs = list_workflow_runs(project_id, workflow_id=workflow_id, limit=limit)
    return jsonify({'workflow_runs': runs})


@pipeline_bp.route('/<project_id>/workflow-runs/<run_id>')
def workflow_run_detail(project_id, run_id):
    run = get_workflow_run(run_id)
    if not run or run.get('project_id') != project_id:
        return jsonify({'error': 'Workflow run not found'}), 404
    return jsonify(run)


@pipeline_bp.route('/<project_id>/workflow-runs/<run_id>/provenance')
def workflow_run_provenance(project_id, run_id):
    provenance = build_workflow_run_provenance(run_id)
    if not provenance or provenance['run'].get('project_id') != project_id:
        return jsonify({'error': 'Workflow run not found'}), 404
    return jsonify(provenance)


@pipeline_bp.route('/<project_id>/workflow-runs/compare')
def workflow_runs_compare(project_id):
    left = request.args.get('left')
    right = request.args.get('right')
    if not left or not right:
        return jsonify({'error': 'left and right workflow run ids are required'}), 400
    payload = compare_workflow_runs(left, right)
    if not payload:
        return jsonify({'error': 'Workflow run not found'}), 404
    if payload['left'].get('project_id') != project_id or payload['right'].get('project_id') != project_id:
        return jsonify({'error': 'Workflow run not found'}), 404
    return jsonify(payload)


@pipeline_bp.route('/<project_id>/runtime-health/<tool_name>')
def workflow_runtime_health(project_id, tool_name):
    tool_info = get_tool_definition(tool_name)
    if not tool_info or tool_info.get('kind') != 'workflow':
        return jsonify({'error': f'Workflow "{tool_name}" not found.'}), 404
    try:
        payload = runtime_health_for_workflow(tool_info['execution']['workflow_id'])
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify(payload)


@pipeline_bp.route('/<project_id>/workflow-templates/<tool_name>', methods=['POST'])
def workflow_template(project_id, tool_name):
    editor_error = require_project_editor()
    if editor_error:
        return editor_error
    tool_info = get_tool_definition(tool_name)
    if not tool_info or tool_info.get('kind') != 'workflow':
        return jsonify({'error': f'Workflow "{tool_name}" not found.'}), 404
    overwrite = bool((request.get_json(silent=True) or {}).get('overwrite'))
    try:
        payload = generate_workflow_template(project_id, tool_info['execution']['workflow_id'], overwrite=overwrite)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify(payload)


def _rerun_workflow(project_id: str, run_id: str, mode: str):
    editor_error = require_project_editor()
    if editor_error:
        return editor_error
    source_run = get_workflow_run(run_id)
    if not source_run or source_run.get('project_id') != project_id:
        return jsonify({'error': 'Workflow run not found'}), 404
    if get_active_workflow_run(project_id, workflow_id=source_run.get('workflow_id')):
        return jsonify({'error': 'A workflow run is already active for this workflow.'}), 409

    tool_info = get_tool_definition(source_run.get('workflow_id'))
    if not tool_info:
        tool_info = next(
            (
                tool
                for tool in [
                    get_tool_definition('workflow-appam-smk'),
                    get_tool_definition('workflow-appam-paleoproteomics'),
                ]
                if tool and tool.get('execution', {}).get('workflow_id') == source_run.get('workflow_id')
            ),
            None,
        )
    if not tool_info:
        return jsonify({'error': 'Workflow definition not found'}), 404

    job_id = uuid.uuid4().hex
    workflow_run_id = uuid.uuid4().hex if mode == 'retry' else uuid.uuid4().hex
    try:
        job_request = build_job_request_from_workflow_run(
            project_id,
            job_id,
            tool_info,
            source_run,
            run_id=workflow_run_id,
            submitted_by=current_user()['id'],
            mode=mode,
        )
        _queue_job_from_request(project_id, tool_info['tool_name'], job_request, job_id)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        return jsonify({'error': f'Failed to {mode} workflow: {exc}'}), 500

    return jsonify({
        'message': f'Workflow {mode} queued successfully.',
        'job_id': job_id,
        'workflow_run_id': job_request.get('workflow_run_id'),
        'status': 'queued',
    })


@pipeline_bp.route('/<project_id>/workflow-runs/<run_id>/retry', methods=['POST'])
def retry_workflow_run(project_id, run_id):
    return _rerun_workflow(project_id, run_id, mode='retry')


@pipeline_bp.route('/<project_id>/workflow-runs/<run_id>/resume', methods=['POST'])
def resume_workflow_run(project_id, run_id):
    return _rerun_workflow(project_id, run_id, mode='resume')
