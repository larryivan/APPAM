from __future__ import annotations

import json
import socket
import uuid
import hashlib
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from ..database import get_db_connection
from .execution_insights import classify_failure


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


def create_job(
    job_id: str,
    project_id: str,
    tool_name: str,
    command: str,
    log_path: str,
    command_spec: Optional[dict] = None,
    output_path: Optional[str] = None,
    status: str = 'queued',
    submitted_by: Optional[str] = None,
    execution_mode: str = 'command',
    workflow_id: Optional[str] = None,
    workflow_run_id: Optional[str] = None,
    work_dir: Optional[str] = None,
    is_dry_run: bool = False,
    workflow_run_spec: Optional[dict] = None,
    backend: Optional[str] = None,
) -> None:
    conn = get_db_connection()
    try:
        conn.execute(
            '''
            INSERT INTO jobs
            (
                id,
                project_id,
                tool_name,
                command,
                command_spec_json,
                status,
                log_path,
                output_path,
                work_dir,
                cancel_requested,
                submitted_by,
                execution_mode,
                backend,
                workflow_id,
                workflow_run_id,
                is_dry_run
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)
            ''',
            (
                job_id,
                project_id,
                tool_name,
                command,
                json.dumps(command_spec) if command_spec is not None else None,
                status,
                log_path,
                output_path,
                work_dir,
                submitted_by,
                execution_mode,
                backend or 'local',
                workflow_id,
                workflow_run_id,
                1 if is_dry_run else 0,
            )
        )
        conn.execute(
            '''
            INSERT INTO process_history
            (job_id, project_id, tool_name, command, status, submitted_by)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (job_id, project_id, tool_name, command, status, submitted_by)
        )

        if workflow_run_spec:
            _insert_workflow_run(conn, workflow_run_spec)

        conn.commit()
    finally:
        conn.close()


def _insert_workflow_run(conn, workflow_run_spec: dict) -> None:
    conn.execute(
        '''
        INSERT INTO workflow_runs
        (
            id,
            job_id,
            project_id,
            workflow_id,
            tool_name,
            status,
            dry_run,
            backend,
            submitted_by,
            parent_run_id,
            preflight_id,
            params_json,
            config_path,
            manifest_path,
            run_dir,
            work_dir,
            results_dir,
            output_root,
            log_path,
            current_stage_id,
            current_stage_title,
            current_rule
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            workflow_run_spec['id'],
            workflow_run_spec.get('job_id'),
            workflow_run_spec['project_id'],
            workflow_run_spec['workflow_id'],
            workflow_run_spec['tool_name'],
            workflow_run_spec.get('status', 'queued'),
            1 if workflow_run_spec.get('dry_run') else 0,
            workflow_run_spec.get('backend'),
            workflow_run_spec.get('submitted_by'),
            workflow_run_spec.get('parent_run_id'),
            workflow_run_spec.get('preflight_id'),
            json.dumps(workflow_run_spec.get('params')) if workflow_run_spec.get('params') is not None else None,
            workflow_run_spec.get('config_path'),
            workflow_run_spec.get('manifest_path'),
            workflow_run_spec.get('run_dir'),
            workflow_run_spec.get('work_dir'),
            workflow_run_spec.get('results_dir'),
            workflow_run_spec.get('output_root'),
            workflow_run_spec.get('log_path'),
            workflow_run_spec.get('current_stage_id'),
            workflow_run_spec.get('current_stage_title'),
            workflow_run_spec.get('current_rule'),
        )
    )

    for stage in workflow_run_spec.get('stages', []):
        conn.execute(
            '''
            INSERT INTO workflow_stage_states
            (
                run_id,
                stage_id,
                stage_title,
                stage_order,
                status,
                optional,
                current_rule,
                started_at,
                finished_at,
                completed_rules,
                total_rules
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                workflow_run_spec['id'],
                stage['id'],
                stage['title'],
                stage.get('order', 0),
                stage.get('status', 'pending'),
                1 if stage.get('optional') else 0,
                stage.get('current_rule'),
                stage.get('started_at'),
                stage.get('finished_at'),
                stage.get('completed_rules', 0),
                stage.get('total_rules', 0),
            )
        )

    for artifact in workflow_run_spec.get('artifacts', []):
        conn.execute(
            '''
            INSERT INTO workflow_artifacts
            (run_id, label, path, kind, size_bytes)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                workflow_run_spec['id'],
                artifact['label'],
                artifact['path'],
                artifact['kind'],
                artifact.get('size_bytes'),
            )
        )

    for event in workflow_run_spec.get('events', []):
        conn.execute(
            '''
            INSERT INTO workflow_run_events
            (run_id, event_type, stage_id, rule_name, message, payload)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (
                workflow_run_spec['id'],
                event.get('event_type'),
                event.get('stage_id'),
                event.get('rule_name'),
                event.get('message'),
                json.dumps(event.get('payload')) if event.get('payload') is not None else None,
            )
        )


def update_job(job_id: str, **fields) -> None:
    if not fields:
        return
    keys = []
    values = []
    for key, value in fields.items():
        keys.append(f"{key} = ?")
        values.append(value)
    values.append(job_id)
    conn = get_db_connection()
    try:
        conn.execute(f"UPDATE jobs SET {', '.join(keys)} WHERE id = ?", values)
        conn.commit()
    finally:
        conn.close()


def update_process_history(job_id: str, **fields) -> None:
    if not fields:
        return
    keys = []
    values = []
    for key, value in fields.items():
        keys.append(f"{key} = ?")
        values.append(value)
    values.append(job_id)
    conn = get_db_connection()
    try:
        conn.execute(f"UPDATE process_history SET {', '.join(keys)} WHERE job_id = ?", values)
        conn.commit()
    finally:
        conn.close()


def update_workflow_run(run_id: str, **fields) -> None:
    if not run_id or not fields:
        return
    keys = []
    values = []
    for key, value in fields.items():
        keys.append(f"{key} = ?")
        values.append(value)
    values.append(run_id)
    conn = get_db_connection()
    try:
        conn.execute(f"UPDATE workflow_runs SET {', '.join(keys)} WHERE id = ?", values)
        conn.commit()
    finally:
        conn.close()


def update_workflow_stage(run_id: str, stage_id: str, **fields) -> None:
    if not run_id or not stage_id or not fields:
        return
    keys = []
    values = []
    for key, value in fields.items():
        keys.append(f"{key} = ?")
        values.append(value)
    values.extend([run_id, stage_id])
    conn = get_db_connection()
    try:
        conn.execute(
            f"UPDATE workflow_stage_states SET {', '.join(keys)} WHERE run_id = ? AND stage_id = ?",
            values,
        )
        conn.commit()
    finally:
        conn.close()


def append_workflow_run_event(
    run_id: str,
    event_type: str,
    stage_id: Optional[str] = None,
    rule_name: Optional[str] = None,
    message: Optional[str] = None,
    payload: Optional[dict] = None,
) -> None:
    if not run_id or not event_type:
        return
    conn = get_db_connection()
    try:
        conn.execute(
            '''
            INSERT INTO workflow_run_events
            (run_id, event_type, stage_id, rule_name, message, payload)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (
                run_id,
                event_type,
                stage_id,
                rule_name,
                message,
                json.dumps(payload) if payload is not None else None,
            )
        )
        conn.commit()
    finally:
        conn.close()


def replace_workflow_artifacts(run_id: str, artifacts: list[dict]) -> None:
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM workflow_artifacts WHERE run_id = ?', (run_id,))
        for artifact in artifacts or []:
            conn.execute(
                '''
                INSERT INTO workflow_artifacts
                (run_id, label, path, kind, size_bytes)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (
                    run_id,
                    artifact['label'],
                    artifact['path'],
                    artifact['kind'],
                    artifact.get('size_bytes'),
                )
            )
        conn.commit()
    finally:
        conn.close()


def replace_workflow_metrics(run_id: str, metrics: list[dict]) -> None:
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM workflow_metrics WHERE run_id = ?', (run_id,))
        for metric in metrics or []:
            payload = metric.get('payload')
            conn.execute(
                '''
                INSERT INTO workflow_metrics
                (run_id, metric_group, metric_name, metric_value, metric_text, unit, sample_id, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    run_id,
                    metric.get('group') or metric.get('metric_group') or 'general',
                    metric.get('name') or metric.get('metric_name') or 'metric',
                    metric.get('value') if metric.get('value') is not None else metric.get('metric_value'),
                    metric.get('text') if metric.get('text') is not None else metric.get('metric_text'),
                    metric.get('unit'),
                    metric.get('sample_id'),
                    json.dumps(payload, ensure_ascii=False) if payload is not None else None,
                )
            )
        conn.commit()
    finally:
        conn.close()


def _params_hash(params: dict | None) -> str:
    serialized = json.dumps(params or {}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def create_workflow_preflight(
    project_id: str,
    tool_name: str,
    result: dict,
    params: dict | None = None,
    submitted_by: str | None = None,
    preflight_id: str | None = None,
) -> dict:
    preflight_id = preflight_id or uuid.uuid4().hex
    conn = get_db_connection()
    try:
        conn.execute(
            '''
            INSERT INTO workflow_preflights
            (id, project_id, workflow_id, tool_name, ok, params_hash, checks_json, preview_json, submitted_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                preflight_id,
                project_id,
                result.get('workflow_id'),
                tool_name,
                1 if result.get('ok') else 0,
                _params_hash(params),
                json.dumps(result.get('checks') or [], ensure_ascii=False),
                json.dumps(result.get('preview') or {}, ensure_ascii=False),
                submitted_by,
            )
        )
        conn.commit()
    finally:
        conn.close()
    record = get_workflow_preflight(preflight_id)
    return record or {'id': preflight_id}


def get_workflow_preflight(preflight_id: str) -> Optional[Dict]:
    conn = get_db_connection()
    try:
        row = conn.execute(
            '''
            SELECT *
            FROM workflow_preflights
            WHERE id = ?
            ''',
            (preflight_id,),
        ).fetchone()
        if not row:
            return None
        record = dict(row)
        record['ok'] = bool(record.get('ok'))
        record['checks'] = _decode_json(record.get('checks_json')) or []
        record['preview'] = _decode_json(record.get('preview_json')) or {}
        return record
    finally:
        conn.close()


def list_workflow_preflights(project_id: str, workflow_id: str | None = None, limit: int = 10) -> List[Dict]:
    conn = get_db_connection()
    try:
        if workflow_id:
            rows = conn.execute(
                '''
                SELECT *
                FROM workflow_preflights
                WHERE project_id = ? AND workflow_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                ''',
                (project_id, workflow_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                '''
                SELECT *
                FROM workflow_preflights
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                ''',
                (project_id, limit),
            ).fetchall()
        records = []
        for row in rows:
            record = dict(row)
            record['ok'] = bool(record.get('ok'))
            record['checks'] = _decode_json(record.get('checks_json')) or []
            record['preview'] = _decode_json(record.get('preview_json')) or {}
            records.append(record)
        return records
    finally:
        conn.close()


def set_job_status(job_id: str, status: str) -> None:
    update_job(job_id, status=status)
    update_process_history(job_id, status=status)


def mark_job_started(job_id: str) -> None:
    timestamp = _now_str()
    update_job(job_id, status='running', started_at=timestamp)
    update_process_history(job_id, status='running', start_time=timestamp)

    job = get_job(job_id)
    run_id = job.get('workflow_run_id') if job else None
    if run_id:
        update_workflow_run(run_id, status='running', started_at=timestamp)
        append_workflow_run_event(run_id, 'run_started', message='Workflow execution started')


def mark_job_claimed(job_id: str, worker_id: str, host: str | None = None, backend: str = 'local') -> bool:
    host = host or socket.gethostname()
    claimed_at = _now_str()
    conn = get_db_connection()
    try:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute(
            '''
            SELECT id, workflow_run_id, status
            FROM jobs
            WHERE id = ?
            ''',
            (job_id,),
        ).fetchone()
        if not row or row['status'] != 'queued':
            conn.rollback()
            return False
        conn.execute(
            '''
            UPDATE jobs
            SET status = 'starting',
                claimed_at = ?,
                claimed_by = ?,
                heartbeat_at = ?,
                host = ?,
                backend = ?
            WHERE id = ?
              AND status = 'queued'
            ''',
            (claimed_at, worker_id, claimed_at, host, backend, job_id),
        )
        conn.execute(
            '''
            UPDATE process_history
            SET status = 'starting'
            WHERE job_id = ?
            ''',
            (job_id,),
        )
        if row['workflow_run_id']:
            conn.execute(
                '''
                UPDATE workflow_runs
                SET status = 'starting'
                WHERE id = ?
                ''',
                (row['workflow_run_id'],),
            )
        conn.commit()
        return True
    finally:
        conn.close()


def mark_job_finished(job_id: str, status: str, exit_code: Optional[int], error_message: Optional[str], duration: Optional[float]) -> None:
    finished_at = _now_str()
    update_job(
        job_id,
        status=status,
        finished_at=finished_at,
        exit_code=exit_code,
        error_message=error_message,
        duration=duration
    )
    update_process_history(
        job_id,
        status=status,
        end_time=finished_at,
        exit_code=exit_code,
        error_message=error_message,
        duration=duration
    )

    job = get_job(job_id)
    run_id = job.get('workflow_run_id') if job else None
    if run_id:
        update_workflow_run(
            run_id,
            status=status,
            finished_at=finished_at,
            exit_code=exit_code,
            error_message=error_message,
            duration=duration,
        )
        append_workflow_run_event(
            run_id,
            'run_finished',
            message=f'Workflow finished with status {status}',
            payload={'status': status, 'exit_code': exit_code, 'error_message': error_message},
        )


def request_cancel(job_id: str) -> None:
    update_job(job_id, cancel_requested=1)


def clear_cancel(job_id: str) -> None:
    update_job(job_id, cancel_requested=0)


def is_cancel_requested(job_id: str) -> bool:
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT cancel_requested FROM jobs WHERE id = ?",
            (job_id,)
        ).fetchone()
        return bool(row and row['cancel_requested'])
    finally:
        conn.close()


def _job_select_sql() -> str:
    return '''
        SELECT
            jobs.*,
            submitter.username AS submitted_by_username,
            submitter.display_name AS submitted_by_display_name
        FROM jobs
        LEFT JOIN users AS submitter ON submitter.id = jobs.submitted_by
    '''


def _history_select_sql() -> str:
    return '''
        SELECT
            process_history.*,
            submitter.username AS submitted_by_username,
            submitter.display_name AS submitted_by_display_name
        FROM process_history
        LEFT JOIN users AS submitter ON submitter.id = process_history.submitted_by
    '''


def _workflow_run_select_sql() -> str:
    return '''
        SELECT
            workflow_runs.*,
            submitter.username AS submitted_by_username,
            submitter.display_name AS submitted_by_display_name
        FROM workflow_runs
        LEFT JOIN users AS submitter ON submitter.id = workflow_runs.submitted_by
    '''


def _decode_payload(value):
    if not value:
        return None
    try:
        return json.loads(value)
    except Exception:
        return value


def _decode_json(value):
    if not value:
        return None
    try:
        return json.loads(value)
    except Exception:
        return value


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _enrich_job_record(record: Dict) -> Dict:
    if not record:
        return record
    record['command_spec'] = _decode_json(record.get('command_spec_json'))
    failure = classify_failure(record.get('error_message'), record.get('exit_code'), record.get('log_path'))
    record['failure_category'] = failure['category']
    record['failure_label'] = failure['label']
    record['failure_suggestion'] = failure.get('suggestion')
    record['queue_position'] = _get_queue_position_safe(record.get('id')) if record.get('status') == 'queued' else None
    return record


def _enrich_workflow_run_record(record: Dict) -> Dict:
    if not record:
        return record
    failure = classify_failure(record.get('error_message'), record.get('exit_code'), record.get('log_path'))
    record['failure_category'] = failure['category']
    record['failure_label'] = failure['label']
    record['failure_suggestion'] = failure.get('suggestion')
    record['queue_position'] = _get_queue_position_safe(record.get('job_id')) if record.get('status') == 'queued' and record.get('job_id') else None
    return record


def _get_queue_position_safe(job_id: str | None):
    if not job_id:
        return None
    try:
        from .job_queue import get_queue_position

        return get_queue_position(job_id)
    except Exception:
        return None


def get_job(job_id: str) -> Optional[Dict]:
    conn = get_db_connection()
    try:
        row = conn.execute(
            f"{_job_select_sql()} WHERE jobs.id = ?",
            (job_id,)
        ).fetchone()
        return _enrich_job_record(dict(row)) if row else None
    finally:
        conn.close()


def list_jobs(project_id: str, limit: int = 20, status: Optional[str] = None) -> List[Dict]:
    conn = get_db_connection()
    try:
        if status:
            rows = conn.execute(
                f'''
                {_job_select_sql()}
                WHERE jobs.project_id = ? AND jobs.status = ?
                ORDER BY jobs.created_at DESC
                LIMIT ?
                ''',
                (project_id, status, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                f'''
                {_job_select_sql()}
                WHERE jobs.project_id = ?
                ORDER BY jobs.created_at DESC
                LIMIT ?
                ''',
                (project_id, limit)
            ).fetchall()
        return [_enrich_job_record(dict(row)) for row in rows]
    finally:
        conn.close()


def list_process_history(project_id: str, limit: int = 20) -> List[Dict]:
    conn = get_db_connection()
    try:
        rows = conn.execute(
            f'''
            {_history_select_sql()}
            WHERE process_history.project_id = ?
            ORDER BY process_history.start_time DESC
            LIMIT ?
            ''',
            (project_id, limit)
        ).fetchall()
        history = [dict(row) for row in rows]
        for item in history:
            failure = classify_failure(item.get('error_message'), item.get('exit_code'))
            item['failure_category'] = failure['category']
            item['failure_label'] = failure['label']
            item['failure_suggestion'] = failure.get('suggestion')
        return history
    finally:
        conn.close()


def get_latest_job(project_id: str) -> Optional[Dict]:
    conn = get_db_connection()
    try:
        row = conn.execute(
            f'''
            {_job_select_sql()}
            WHERE jobs.project_id = ?
            ORDER BY jobs.created_at DESC
            LIMIT 1
            ''',
            (project_id,)
        ).fetchone()
        return _enrich_job_record(dict(row)) if row else None
    finally:
        conn.close()


def get_active_job(project_id: str) -> Optional[Dict]:
    conn = get_db_connection()
    try:
        row = conn.execute(
            f'''
            {_job_select_sql()}
            WHERE jobs.project_id = ? AND jobs.status IN ('queued', 'starting', 'running')
            ORDER BY jobs.created_at DESC
            LIMIT 1
            ''',
            (project_id,)
        ).fetchone()
        return _enrich_job_record(dict(row)) if row else None
    finally:
        conn.close()


def count_jobs(
    *,
    project_id: str | None = None,
    submitted_by: str | None = None,
    statuses: tuple[str, ...] = ('queued', 'running'),
) -> int:
    conditions = []
    params: list = []
    if project_id:
        conditions.append('project_id = ?')
        params.append(project_id)
    if submitted_by:
        conditions.append('submitted_by = ?')
        params.append(submitted_by)
    if statuses:
        placeholders = ','.join('?' for _ in statuses)
        conditions.append(f"status IN ({placeholders})")
        params.extend(statuses)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ''
    conn = get_db_connection()
    try:
        row = conn.execute(
            f'''
            SELECT COUNT(*) AS count
            FROM jobs
            {where_clause}
            ''',
            tuple(params),
        ).fetchone()
        return int(row['count']) if row else 0
    finally:
        conn.close()


def get_workflow_run(run_id: str) -> Optional[Dict]:
    conn = get_db_connection()
    try:
        row = conn.execute(
            f'''
            {_workflow_run_select_sql()}
            WHERE workflow_runs.id = ?
            ''',
            (run_id,)
        ).fetchone()
        if not row:
            return None
        data = _enrich_workflow_run_record(dict(row))
        data['params'] = _decode_json(data.get('params_json'))
        data['stage_states'] = list_workflow_stage_states(run_id, conn=conn)
        data['events'] = list_workflow_run_events(run_id, limit=200, conn=conn)
        data['artifacts'] = list_workflow_artifacts(run_id, conn=conn)
        data['metrics'] = list_workflow_metrics(run_id, conn=conn)
        return data
    finally:
        conn.close()


def get_workflow_run_by_job(job_id: str) -> Optional[Dict]:
    conn = get_db_connection()
    try:
        row = conn.execute(
            f'''
            {_workflow_run_select_sql()}
            WHERE workflow_runs.job_id = ?
            ''',
            (job_id,)
        ).fetchone()
        if not row:
            return None
        data = _enrich_workflow_run_record(dict(row))
        data['params'] = _decode_json(data.get('params_json'))
        data['stage_states'] = list_workflow_stage_states(data['id'], conn=conn)
        data['events'] = list_workflow_run_events(data['id'], limit=200, conn=conn)
        data['artifacts'] = list_workflow_artifacts(data['id'], conn=conn)
        data['metrics'] = list_workflow_metrics(data['id'], conn=conn)
        return data
    finally:
        conn.close()


def list_workflow_stage_states(run_id: str, conn=None) -> List[Dict]:
    owns_connection = conn is None
    connection = conn or get_db_connection()
    try:
        rows = connection.execute(
            '''
            SELECT *
            FROM workflow_stage_states
            WHERE run_id = ?
            ORDER BY stage_order ASC
            ''',
            (run_id,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        if owns_connection:
            connection.close()


def list_workflow_run_events(run_id: str, limit: int = 100, conn=None) -> List[Dict]:
    owns_connection = conn is None
    connection = conn or get_db_connection()
    try:
        rows = connection.execute(
            '''
            SELECT *
            FROM workflow_run_events
            WHERE run_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            ''',
            (run_id, limit)
        ).fetchall()
        events = [dict(row) for row in rows]
        for event in events:
            event['payload'] = _decode_payload(event.get('payload'))
        return events
    finally:
        if owns_connection:
            connection.close()


def list_workflow_artifacts(run_id: str, limit: int = 200, conn=None) -> List[Dict]:
    owns_connection = conn is None
    connection = conn or get_db_connection()
    try:
        rows = connection.execute(
            '''
            SELECT *
            FROM workflow_artifacts
            WHERE run_id = ?
            ORDER BY created_at ASC, id ASC
            LIMIT ?
            ''',
            (run_id, limit)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        if owns_connection:
            connection.close()


def list_workflow_metrics(run_id: str, limit: int = 500, conn=None) -> List[Dict]:
    owns_connection = conn is None
    connection = conn or get_db_connection()
    try:
        rows = connection.execute(
            '''
            SELECT *
            FROM workflow_metrics
            WHERE run_id = ?
            ORDER BY metric_group ASC, sample_id ASC, metric_name ASC, id ASC
            LIMIT ?
            ''',
            (run_id, limit)
        ).fetchall()
        metrics = [dict(row) for row in rows]
        for metric in metrics:
            metric['payload'] = _decode_payload(metric.get('payload'))
        return metrics
    finally:
        if owns_connection:
            connection.close()


def list_workflow_runs(project_id: str, workflow_id: Optional[str] = None, limit: int = 20) -> List[Dict]:
    conn = get_db_connection()
    try:
        if workflow_id:
            rows = conn.execute(
                f'''
                {_workflow_run_select_sql()}
                WHERE workflow_runs.project_id = ? AND workflow_runs.workflow_id = ?
                ORDER BY workflow_runs.created_at DESC
                LIMIT ?
                ''',
                (project_id, workflow_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                f'''
                {_workflow_run_select_sql()}
                WHERE workflow_runs.project_id = ?
                ORDER BY workflow_runs.created_at DESC
                LIMIT ?
                ''',
                (project_id, limit)
            ).fetchall()

        runs = [_enrich_workflow_run_record(dict(row)) for row in rows]
        for run in runs:
            run['params'] = _decode_json(run.get('params_json'))
            run['stage_states'] = list_workflow_stage_states(run['id'], conn=conn)
            run['artifacts'] = list_workflow_artifacts(run['id'], conn=conn)
            run['metrics'] = list_workflow_metrics(run['id'], conn=conn)
        return runs
    finally:
        conn.close()


def get_latest_workflow_run(project_id: str, workflow_id: Optional[str] = None) -> Optional[Dict]:
    runs = list_workflow_runs(project_id, workflow_id=workflow_id, limit=1)
    return runs[0] if runs else None


def get_active_workflow_run(project_id: str, workflow_id: Optional[str] = None) -> Optional[Dict]:
    conn = get_db_connection()
    try:
        params = [project_id]
        workflow_filter = ''
        if workflow_id:
            workflow_filter = ' AND workflow_runs.workflow_id = ?'
            params.append(workflow_id)
        params.append(1)
        row = conn.execute(
            f'''
            {_workflow_run_select_sql()}
            WHERE workflow_runs.project_id = ?
              {workflow_filter}
              AND workflow_runs.status IN ('queued', 'starting', 'running')
            ORDER BY workflow_runs.created_at DESC
            LIMIT ?
            ''',
            tuple(params)
        ).fetchone()
        if not row:
            return None
        run = _enrich_workflow_run_record(dict(row))
        run['params'] = _decode_json(run.get('params_json'))
        run['stage_states'] = list_workflow_stage_states(run['id'], conn=conn)
        run['artifacts'] = list_workflow_artifacts(run['id'], conn=conn)
        run['metrics'] = list_workflow_metrics(run['id'], conn=conn)
        return run
    finally:
        conn.close()


def load_workflow_manifest(run_id: str) -> Optional[Dict]:
    run = get_workflow_run(run_id)
    if not run:
        return None
    manifest_path = run.get('manifest_path')
    if not manifest_path:
        return None
    try:
        return json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    except Exception:
        return None


def build_workflow_run_provenance(run_id: str) -> Optional[Dict]:
    run = get_workflow_run(run_id)
    if not run:
        return None
    preflight = get_workflow_preflight(run.get('preflight_id')) if run.get('preflight_id') else None
    return {
        'run': {k: v for k, v in run.items() if k not in {'events', 'stage_states', 'artifacts', 'metrics'}},
        'stage_states': run.get('stage_states', []),
        'artifacts': run.get('artifacts', []),
        'metrics': run.get('metrics', []),
        'events': run.get('events', []),
        'manifest': load_workflow_manifest(run_id),
        'preflight': preflight,
        'exported_at': _now_str(),
    }


def compare_workflow_runs(left_run_id: str, right_run_id: str) -> Optional[Dict]:
    left = get_workflow_run(left_run_id)
    right = get_workflow_run(right_run_id)
    if not left or not right:
        return None

    left_stages = {stage['stage_id']: stage for stage in left.get('stage_states', [])}
    right_stages = {stage['stage_id']: stage for stage in right.get('stage_states', [])}
    stage_ids = sorted(set(left_stages) | set(right_stages))

    stage_diffs = []
    for stage_id in stage_ids:
        left_stage = left_stages.get(stage_id)
        right_stage = right_stages.get(stage_id)
        stage_diffs.append({
            'stage_id': stage_id,
            'left_status': left_stage.get('status') if left_stage else None,
            'right_status': right_stage.get('status') if right_stage else None,
            'left_completed_rules': left_stage.get('completed_rules') if left_stage else None,
            'right_completed_rules': right_stage.get('completed_rules') if right_stage else None,
        })

    return {
        'left': left,
        'right': right,
        'summary': {
            'same_workflow': left.get('workflow_id') == right.get('workflow_id'),
            'same_status': left.get('status') == right.get('status'),
            'duration_delta': (left.get('duration') or 0) - (right.get('duration') or 0),
        },
        'stage_diffs': stage_diffs,
    }


def claim_next_job(worker_id: str, host: str | None = None) -> Optional[Dict]:
    host = host or socket.gethostname()
    claimed_at = _now_str()
    conn = get_db_connection()
    try:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute(
            '''
            SELECT id, workflow_run_id
            FROM jobs
            WHERE status = 'queued'
            ORDER BY created_at ASC, id ASC
            LIMIT 1
            '''
        ).fetchone()
        if not row:
            conn.rollback()
            return None
        updated = conn.execute(
            '''
            UPDATE jobs
            SET status = 'starting',
                claimed_at = ?,
                claimed_by = ?,
                heartbeat_at = ?,
                host = ?,
                backend = 'local'
            WHERE id = ?
              AND status = 'queued'
            ''',
            (claimed_at, worker_id, claimed_at, host, row['id']),
        )
        if updated.rowcount != 1:
            conn.rollback()
            return None
        conn.execute(
            '''
            UPDATE process_history
            SET status = 'starting'
            WHERE job_id = ?
            ''',
            (row['id'],)
        )
        if row['workflow_run_id']:
            conn.execute(
                '''
                UPDATE workflow_runs
                SET status = 'starting'
                WHERE id = ?
                ''',
                (row['workflow_run_id'],)
            )
        conn.commit()
    finally:
        conn.close()
    return get_job(row['id'])


def update_job_heartbeat(job_id: str) -> None:
    timestamp = _now_str()
    update_job(job_id, heartbeat_at=timestamp)


def attach_process_info(job_id: str, *, pid: int | None = None, pgid: int | None = None, host: str | None = None) -> None:
    update_fields = {}
    if pid is not None:
        update_fields['pid'] = pid
    if pgid is not None:
        update_fields['pgid'] = pgid
    if host is not None:
        update_fields['host'] = host
    if update_fields:
        update_job(job_id, **update_fields)


def list_stale_jobs(timeout_seconds: int = 600) -> List[Dict]:
    threshold = (datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)).strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    try:
        rows = conn.execute(
            f'''
            {_job_select_sql()}
            WHERE jobs.status IN ('starting', 'running')
              AND jobs.heartbeat_at IS NOT NULL
              AND jobs.heartbeat_at < ?
            ORDER BY jobs.created_at ASC
            ''',
            (threshold,),
        ).fetchall()
        return [_enrich_job_record(dict(row)) for row in rows]
    finally:
        conn.close()
