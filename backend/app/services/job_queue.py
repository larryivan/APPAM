from __future__ import annotations

import os
import socket
import uuid

from ..database import get_db_connection
from .job_store import create_job, get_job, mark_job_claimed
from .local_executor import (
    notify_new_job,
    start_embedded_worker as _start_embedded_worker,
    stop_embedded_worker as _stop_embedded_worker,
)


def _queue_backend() -> str:
    return os.getenv('APPAM_QUEUE_BACKEND', 'local-db').strip().lower() or 'local-db'


def _rq_queue():
    try:
        from redis import Redis
        from rq import Queue
    except Exception as exc:
        raise RuntimeError('RQ backend requires redis and rq Python packages') from exc

    redis_url = os.getenv('APPAM_REDIS_URL', 'redis://redis:6379/0')
    queue_name = os.getenv('APPAM_RQ_QUEUE', 'appam-workflows')
    return Queue(queue_name, connection=Redis.from_url(redis_url))


def run_queued_rq_job(job_id: str) -> dict:
    from .job_runner import run_pipeline_job

    job = get_job(job_id)
    if not job:
        raise ValueError(f'Job not found: {job_id}')
    if job.get('status') != 'queued':
        return {'status': job.get('status'), 'skipped': True}

    worker_id = os.getenv('APPAM_RQ_WORKER_NAME') or f'rq:{socket.gethostname()}'
    if not mark_job_claimed(job_id, worker_id, host=socket.gethostname(), backend='rq'):
        job = get_job(job_id)
        return {'status': job.get('status') if job else 'missing', 'skipped': True}
    job = get_job(job_id)
    if not job:
        raise ValueError(f'Job disappeared after claim: {job_id}')
    return run_pipeline_job(
        job['id'],
        job['project_id'],
        job['tool_name'],
        job['command'],
        job['log_path'],
        command_spec=job.get('command_spec'),
    )


def get_queue():
    if _queue_backend() == 'rq':
        queue = _rq_queue()
        return {
            'mode': 'rq',
            'name': queue.name,
            'redis_url': os.getenv('APPAM_REDIS_URL', 'redis://redis:6379/0'),
            'queued_count': len(queue),
        }
    return {'mode': 'local-db'}


def start_embedded_worker():
    if _queue_backend() == 'rq':
        return None
    return _start_embedded_worker()


def stop_embedded_worker(timeout: float = 5.0) -> None:
    if _queue_backend() == 'rq':
        return
    _stop_embedded_worker(timeout=timeout)


def get_queue_position(job_id: str) -> int | None:
    conn = get_db_connection()
    try:
        row = conn.execute(
            '''
            SELECT created_at, id, status
            FROM jobs
            WHERE id = ?
            ''',
            (job_id,),
        ).fetchone()
        if not row or row['status'] != 'queued':
            return None
        count_row = conn.execute(
            '''
            SELECT COUNT(*) AS count
            FROM jobs
            WHERE status = 'queued'
              AND (
                created_at < ?
                OR (created_at = ? AND id <= ?)
              )
            ''',
            (row['created_at'], row['created_at'], row['id']),
        ).fetchone()
        return int(count_row['count']) if count_row else None
    finally:
        conn.close()


def cancel_enqueued_job(job_id: str) -> bool:
    job = get_job(job_id)
    if job and job.get('status') == 'queued' and _queue_backend() == 'rq':
        try:
            rq_job = _rq_queue().fetch_job(job_id)
            if rq_job:
                rq_job.cancel()
        except Exception:
            pass
    return bool(job and job.get('status') == 'queued')


def enqueue_pipeline_job(
    project_id: str,
    tool_name: str,
    command: str,
    log_path: str,
    job_id: str | None = None,
    submitted_by: str | None = None,
    command_spec: dict | None = None,
    output_path: str | None = None,
    work_dir: str | None = None,
    execution_mode: str = 'command',
    workflow_id: str | None = None,
    workflow_run_id: str | None = None,
    is_dry_run: bool = False,
    workflow_run_spec: dict | None = None,
) -> str:
    job_id = job_id or uuid.uuid4().hex
    create_job(
        job_id,
        project_id,
        tool_name,
        command,
        log_path,
        command_spec=command_spec,
        output_path=output_path,
        status='queued',
        submitted_by=submitted_by,
        execution_mode=execution_mode,
        workflow_id=workflow_id,
        workflow_run_id=workflow_run_id,
        work_dir=work_dir,
        is_dry_run=is_dry_run,
        workflow_run_spec=workflow_run_spec,
        backend='rq' if _queue_backend() == 'rq' else 'local',
    )
    if _queue_backend() == 'rq':
        _rq_queue().enqueue(run_queued_rq_job, job_id, job_id=job_id)
    else:
        start_embedded_worker()
        notify_new_job()
    return job_id


__all__ = [
    'cancel_enqueued_job',
    'enqueue_pipeline_job',
    'get_queue',
    'get_queue_position',
    'notify_new_job',
    'start_embedded_worker',
    'stop_embedded_worker',
]
