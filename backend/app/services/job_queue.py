import uuid

from ..database import get_db_connection
from .job_store import create_job, get_job
from .local_executor import notify_new_job, start_embedded_worker, stop_embedded_worker


def get_queue():
    return {'mode': 'local-db'}


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
    )
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
