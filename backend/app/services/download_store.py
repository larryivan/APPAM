from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..database import get_db_connection


TERMINAL_STATUSES = ('completed', 'error', 'cancelled')


def upsert_download_task(task: dict) -> None:
    conn = get_db_connection()
    try:
        conn.execute(
            '''
            INSERT INTO download_tasks (
                id, project_id, submitted_by, url, filename, relative_path,
                concurrent, status, progress, downloaded_size, total_size,
                speed, time_remaining, error, file_path, destination_path,
                created_at, updated_at, finished_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      COALESCE(?, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP, ?)
            ON CONFLICT(id) DO UPDATE SET
                project_id = excluded.project_id,
                submitted_by = COALESCE(download_tasks.submitted_by, excluded.submitted_by),
                url = excluded.url,
                filename = excluded.filename,
                relative_path = excluded.relative_path,
                concurrent = excluded.concurrent,
                status = excluded.status,
                progress = excluded.progress,
                downloaded_size = excluded.downloaded_size,
                total_size = excluded.total_size,
                speed = excluded.speed,
                time_remaining = excluded.time_remaining,
                error = excluded.error,
                file_path = excluded.file_path,
                destination_path = excluded.destination_path,
                updated_at = CURRENT_TIMESTAMP,
                finished_at = excluded.finished_at
            ''',
            (
                task['id'],
                task['project_id'],
                task.get('submitted_by'),
                task['url'],
                task['filename'],
                task.get('relative_path') or '',
                int(bool(task.get('concurrent'))),
                task['status'],
                float(task.get('progress') or 0),
                int(task.get('downloaded_size') or 0),
                int(task.get('total_size') or 0),
                float(task.get('speed') or 0),
                task.get('time_remaining'),
                task.get('error'),
                task.get('file_path'),
                task.get('destination_path'),
                task.get('created_at'),
                task.get('finished_at'),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_download_task(task_id: str, project_id: str | None = None) -> dict | None:
    conn = get_db_connection()
    try:
        if project_id:
            row = conn.execute(
                'SELECT * FROM download_tasks WHERE id = ? AND project_id = ?',
                (task_id, project_id),
            ).fetchone()
        else:
            row = conn.execute('SELECT * FROM download_tasks WHERE id = ?', (task_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_download_tasks(project_id: str | None = None, limit: int = 1000) -> list[dict]:
    limit = min(max(int(limit), 1), 5000)
    conn = get_db_connection()
    try:
        if project_id:
            rows = conn.execute(
                '''
                SELECT * FROM download_tasks
                WHERE project_id = ?
                ORDER BY updated_at DESC, created_at DESC
                LIMIT ?
                ''',
                (project_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                '''
                SELECT * FROM download_tasks
                ORDER BY updated_at DESC, created_at DESC
                LIMIT ?
                ''',
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_download_task(task_id: str, project_id: str | None = None) -> bool:
    conn = get_db_connection()
    try:
        if project_id:
            result = conn.execute(
                'DELETE FROM download_tasks WHERE id = ? AND project_id = ?',
                (task_id, project_id),
            )
        else:
            result = conn.execute('DELETE FROM download_tasks WHERE id = ?', (task_id,))
        conn.commit()
        return result.rowcount > 0
    finally:
        conn.close()


def delete_terminal_download_tasks(project_id: str | None = None) -> list[dict]:
    conn = get_db_connection()
    try:
        placeholders = ','.join('?' for _ in TERMINAL_STATUSES)
        params: list[object] = list(TERMINAL_STATUSES)
        where = f'status IN ({placeholders})'
        if project_id:
            where += ' AND project_id = ?'
            params.append(project_id)
        rows = conn.execute(f'SELECT * FROM download_tasks WHERE {where}', params).fetchall()
        conn.execute(f'DELETE FROM download_tasks WHERE {where}', params)
        conn.commit()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def prune_download_history(retention_days: int) -> list[dict]:
    retention_days = max(1, int(retention_days))
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    cutoff_text = cutoff.strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    try:
        placeholders = ','.join('?' for _ in TERMINAL_STATUSES)
        params: list[object] = [*TERMINAL_STATUSES, cutoff_text]
        where = f'status IN ({placeholders}) AND updated_at < ?'
        rows = conn.execute(f'SELECT * FROM download_tasks WHERE {where}', params).fetchall()
        conn.execute(f'DELETE FROM download_tasks WHERE {where}', params)
        conn.commit()
        return [dict(row) for row in rows]
    finally:
        conn.close()
