import os

from flask import Blueprint, jsonify, request

from app.auth import get_project_for_user, project_role_at_least
from app.services.job_queue import cancel_enqueued_job
from app.services.job_store import (
    get_job,
    list_jobs,
    mark_job_finished,
    request_cancel,
)


jobs_bp = Blueprint('jobs_bp', __name__)


def _project_for_job_access(project_id: str, min_role: str = 'viewer'):
    project = get_project_for_user(project_id, min_role=min_role)
    if not project:
        return None
    return project


@jobs_bp.route('/jobs', methods=['GET'])
def list_jobs_endpoint():
    project_id = request.args.get('project_id')
    if not project_id:
        return jsonify({'error': 'project_id is required'}), 400
    if not _project_for_job_access(project_id, min_role='viewer'):
        return jsonify({'error': 'Project not found'}), 404
    limit = request.args.get('limit', 20, type=int)
    status = request.args.get('status')
    jobs = list_jobs(project_id, limit=limit, status=status)
    return jsonify({'jobs': jobs})


@jobs_bp.route('/jobs/<job_id>', methods=['GET'])
def get_job_endpoint(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    if not _project_for_job_access(job.get('project_id'), min_role='viewer'):
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job)


@jobs_bp.route('/jobs/<job_id>/logs', methods=['GET'])
def get_job_logs(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    if not _project_for_job_access(job.get('project_id'), min_role='viewer'):
        return jsonify({'error': 'Job not found'}), 404

    offset = request.args.get('offset', 0, type=int)
    limit = request.args.get('limit', 65536, type=int)
    log_path = job.get('log_path')
    if not log_path or not os.path.exists(log_path):
        return jsonify({
            'job_id': job_id,
            'offset': offset,
            'content': '',
            'status': job.get('status')
        })

    with open(log_path, 'rb') as log_file:
        log_file.seek(offset)
        data = log_file.read(limit)
        new_offset = log_file.tell()

    content = data.decode('utf-8', errors='replace')
    return jsonify({
        'job_id': job_id,
        'offset': new_offset,
        'content': content,
        'status': job.get('status')
    })


@jobs_bp.route('/jobs/<job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    project = _project_for_job_access(job.get('project_id'), min_role='viewer')
    if not project:
        return jsonify({'error': 'Job not found'}), 404
    if not project_role_at_least(project.get('access_role'), 'editor'):
        return jsonify({'error': 'Project write access required'}), 403
    if job.get('status') not in ('queued', 'starting', 'running'):
        return jsonify({'error': 'Job is not running'}), 400
    if job.get('status') == 'queued':
        request_cancel(job_id)
        canceled = cancel_enqueued_job(job_id)
        mark_job_finished(job_id, 'canceled', None, 'Canceled before execution', 0)
        return jsonify({
            'message': 'Queued job canceled' if canceled else 'Queued job marked as canceled. Queue cleanup will be retried by the worker.',
            'job_id': job_id,
            'mode': 'queued',
            'queue_removed': bool(canceled),
        })
    request_cancel(job_id)
    return jsonify({'message': 'Interrupt requested', 'job_id': job_id, 'mode': 'running'})


@jobs_bp.route('/jobs/<job_id>/interrupt', methods=['POST'])
def interrupt_job(job_id):
    return cancel_job(job_id)
