import os
import socket
import threading
import time
from typing import Optional

from ..database import get_db_connection
from .job_runner import run_pipeline_job
from .job_store import (
    claim_next_job,
    get_job,
    list_stale_jobs,
    mark_job_finished,
)


_WORKER_LOCK = threading.Lock()
_WORKER_THREAD: threading.Thread | None = None
_WORKER_STOP = threading.Event()
_WORKER_WAKE = threading.Event()
_WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"
_WORKER_STATE = {
    'worker_id': _WORKER_ID,
    'host': socket.gethostname(),
    'started_at': None,
    'last_heartbeat_at': None,
    'last_claimed_at': None,
    'last_idle_at': None,
    'last_error': None,
    'current_job_id': None,
    'recovered_jobs': 0,
}


def _poll_interval() -> float:
    try:
        return max(0.2, float(os.getenv('APPAM_WORKER_POLL_INTERVAL', '1.0')))
    except Exception:
        return 1.0


def _stale_timeout() -> int:
    try:
        return max(30, int(os.getenv('APPAM_WORKER_STALE_TIMEOUT', '900')))
    except Exception:
        return 900


def notify_new_job() -> None:
    _WORKER_WAKE.set()


def _timestamp() -> str:
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())


def _process_is_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _recover_stale_jobs() -> None:
    for job in list_stale_jobs(timeout_seconds=_stale_timeout()):
        if job.get('status') not in ('starting', 'running'):
            continue
        if _process_is_alive(job.get('pid')):
            from .job_store import update_job_heartbeat

            update_job_heartbeat(job['id'])
            continue
        mark_job_finished(
            job['id'],
            'failed',
            None,
            'Worker heartbeat timed out before the task completed.',
            job.get('duration'),
        )
        _WORKER_STATE['recovered_jobs'] += 1


def run_worker_once(worker_id: str | None = None) -> bool:
    worker_id = worker_id or _WORKER_ID
    job = claim_next_job(worker_id, host=socket.gethostname())
    if not job:
        _WORKER_STATE['current_job_id'] = None
        _WORKER_STATE['last_idle_at'] = _timestamp()
        return False

    _WORKER_STATE['current_job_id'] = job['id']
    _WORKER_STATE['last_claimed_at'] = _timestamp()
    command_spec = job.get('command_spec')
    try:
        run_pipeline_job(
            job['id'],
            job['project_id'],
            job['tool_name'],
            job['command'],
            job['log_path'],
            command_spec=command_spec,
        )
    except Exception as exc:
        _WORKER_STATE['last_error'] = str(exc)
        raise
    finally:
        _WORKER_STATE['current_job_id'] = None
    return True


def run_worker_forever(stop_event: Optional[threading.Event] = None) -> None:
    stop_event = stop_event or _WORKER_STOP
    _WORKER_STATE['started_at'] = _timestamp()
    _recover_stale_jobs()
    while not stop_event.is_set():
        _WORKER_STATE['last_heartbeat_at'] = _timestamp()
        claimed = run_worker_once(_WORKER_ID)
        if claimed:
            continue
        _WORKER_WAKE.wait(timeout=_poll_interval())
        _WORKER_WAKE.clear()


def start_embedded_worker() -> threading.Thread | None:
    if os.getenv('APPAM_DISABLE_EMBEDDED_WORKER', 'false').lower() == 'true':
        return None

    global _WORKER_THREAD
    with _WORKER_LOCK:
        if _WORKER_THREAD and _WORKER_THREAD.is_alive():
            return _WORKER_THREAD

        _WORKER_STOP.clear()
        _WORKER_THREAD = threading.Thread(
            target=run_worker_forever,
            name='appam-local-worker',
            daemon=True,
        )
        _WORKER_THREAD.start()
        return _WORKER_THREAD


def stop_embedded_worker(timeout: float = 5.0) -> None:
    global _WORKER_THREAD
    with _WORKER_LOCK:
        if not _WORKER_THREAD:
            return
        _WORKER_STOP.set()
        _WORKER_WAKE.set()
        _WORKER_THREAD.join(timeout=timeout)
        _WORKER_THREAD = None


def embedded_worker_running() -> bool:
    return bool(_WORKER_THREAD and _WORKER_THREAD.is_alive())


def get_worker_status() -> dict:
    conn = get_db_connection()
    try:
        counts = conn.execute(
            '''
            SELECT status, COUNT(*) AS count
            FROM jobs
            WHERE status IN ('queued', 'starting', 'running', 'failed', 'completed', 'canceled')
            GROUP BY status
            '''
        ).fetchall()
        recent_active = conn.execute(
            '''
            SELECT id, project_id, tool_name, status, created_at, started_at, heartbeat_at, pid, claimed_by
            FROM jobs
            WHERE status IN ('queued', 'starting', 'running')
            ORDER BY created_at DESC
            LIMIT 12
            '''
        ).fetchall()
    finally:
        conn.close()

    count_map = {row['status']: int(row['count']) for row in counts}
    stale_jobs = list_stale_jobs(timeout_seconds=_stale_timeout())
    return {
        'mode': 'local-db',
        'embedded_worker_running': embedded_worker_running(),
        'poll_interval_seconds': _poll_interval(),
        'stale_timeout_seconds': _stale_timeout(),
        'worker': dict(_WORKER_STATE),
        'counts': {
            'queued': count_map.get('queued', 0),
            'starting': count_map.get('starting', 0),
            'running': count_map.get('running', 0),
            'failed': count_map.get('failed', 0),
            'completed': count_map.get('completed', 0),
            'canceled': count_map.get('canceled', 0),
        },
        'stale_jobs': stale_jobs,
        'active_jobs': [dict(row) for row in recent_active],
    }
