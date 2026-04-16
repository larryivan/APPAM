import json
import re
import secrets
import uuid

from werkzeug.security import check_password_hash, generate_password_hash

from ..database import get_db_connection


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
MAX_DISPLAY_NAME_LENGTH = 80
USER_ROLES = {'user', 'admin'}
USER_STATUSES = {'active', 'disabled'}
PROJECT_MEMBER_ROLES = {'viewer', 'editor', 'owner'}
LOGIN_RATE_LIMIT_WINDOW_MINUTES = 15
LOGIN_RATE_LIMIT_MAX_BY_USERNAME = 5
LOGIN_RATE_LIMIT_MAX_BY_IP = 20


class AuthRateLimitError(ValueError):
    pass


class AuthDisabledError(ValueError):
    pass


def _sanitize_user(row):
    if not row:
        return None
    user = dict(row)
    user.pop('password_hash', None)
    return user


def _validate_role(role: str) -> str:
    role = (role or '').strip().lower()
    if role not in USER_ROLES:
        raise ValueError(f"Role must be one of: {', '.join(sorted(USER_ROLES))}.")
    return role


def _validate_status(status: str) -> str:
    status = (status or '').strip().lower()
    if status not in USER_STATUSES:
        raise ValueError(f"Status must be one of: {', '.join(sorted(USER_STATUSES))}.")
    return status


def validate_project_member_role(role: str) -> str:
    role = (role or '').strip().lower()
    if role not in PROJECT_MEMBER_ROLES:
        raise ValueError(f"Project role must be one of: {', '.join(sorted(PROJECT_MEMBER_ROLES))}.")
    return role


def validate_username(username: str) -> str:
    username = (username or '').strip()
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError('Username must be 3-32 characters and use only letters, numbers, dot, underscore, or hyphen.')
    return username


def validate_password(password: str) -> str:
    password = password or ''
    if len(password) < 8:
        raise ValueError('Password must be at least 8 characters long.')
    return password


def validate_display_name(display_name: str) -> str:
    display_name = (display_name or '').strip()
    if len(display_name) > MAX_DISPLAY_NAME_LENGTH:
        raise ValueError(f'Display name must be at most {MAX_DISPLAY_NAME_LENGTH} characters long.')
    return display_name


def count_users(active_only: bool = False) -> int:
    conn = get_db_connection()
    try:
        if active_only:
            row = conn.execute("SELECT COUNT(*) AS count FROM users WHERE status = 'active'").fetchone()
        else:
            row = conn.execute('SELECT COUNT(*) AS count FROM users').fetchone()
        return int(row['count']) if row else 0
    finally:
        conn.close()


def count_active_admins() -> int:
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM users WHERE role = 'admin' AND status = 'active'"
        ).fetchone()
        return int(row['count']) if row else 0
    finally:
        conn.close()


def get_user_by_id(user_id: str, active_only: bool = False):
    if not user_id:
        return None

    conn = get_db_connection()
    try:
        if active_only:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ? AND status = 'active'",
                (user_id,)
            ).fetchone()
        else:
            row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        return _sanitize_user(row)
    finally:
        conn.close()


def get_user_by_username(username: str, active_only: bool = False):
    username = (username or '').strip()
    if not username:
        return None

    conn = get_db_connection()
    try:
        if active_only:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ? AND status = 'active'",
                (username,)
            ).fetchone()
        else:
            row = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        return _sanitize_user(row)
    finally:
        conn.close()


def list_users(search: str = ''):
    search = (search or '').strip().lower()
    conn = get_db_connection()
    try:
        if search:
            like_value = f'%{search}%'
            rows = conn.execute(
                '''
                SELECT
                    u.*,
                    (
                        SELECT COUNT(*)
                        FROM projects p
                        WHERE p.owner_id = u.id
                    ) AS owned_projects_count,
                    (
                        SELECT COUNT(*)
                        FROM project_members pm
                        JOIN projects p ON p.id = pm.project_id
                        WHERE pm.user_id = u.id
                          AND p.owner_id != u.id
                    ) AS member_projects_count
                FROM users u
                WHERE lower(u.username) LIKE ? OR lower(COALESCE(u.display_name, '')) LIKE ?
                ORDER BY u.created_at DESC, u.username ASC
                ''',
                (like_value, like_value)
            ).fetchall()
        else:
            rows = conn.execute(
                '''
                SELECT
                    u.*,
                    (
                        SELECT COUNT(*)
                        FROM projects p
                        WHERE p.owner_id = u.id
                    ) AS owned_projects_count,
                    (
                        SELECT COUNT(*)
                        FROM project_members pm
                        JOIN projects p ON p.id = pm.project_id
                        WHERE pm.user_id = u.id
                          AND p.owner_id != u.id
                    ) AS member_projects_count
                FROM users u
                ORDER BY u.created_at DESC, u.username ASC
                '''
            ).fetchall()
        return [_sanitize_user(row) for row in rows]
    finally:
        conn.close()


def search_active_users(query: str = '', exclude_user_id: str | None = None, limit: int = 50):
    query = (query or '').strip().lower()
    conn = get_db_connection()
    try:
        params: list = []
        conditions = ["status = 'active'"]
        if exclude_user_id:
            conditions.append('id != ?')
            params.append(exclude_user_id)
        if query:
            conditions.append("(lower(username) LIKE ? OR lower(COALESCE(display_name, '')) LIKE ?)")
            like_value = f'%{query}%'
            params.extend([like_value, like_value])
        params.append(limit)
        rows = conn.execute(
            f'''
            SELECT id, username, display_name, role, status
            FROM users
            WHERE {' AND '.join(conditions)}
            ORDER BY username ASC
            LIMIT ?
            ''',
            tuple(params)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def create_user(username: str, password: str, display_name: str = ''):
    username = validate_username(username)
    password = validate_password(password)
    display_name = validate_display_name(display_name)

    conn = get_db_connection()
    try:
        existing = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if existing:
            raise ValueError('Username already exists.')

        user_count_row = conn.execute('SELECT COUNT(*) AS count FROM users').fetchone()
        role = 'admin' if int(user_count_row['count']) == 0 else 'user'
        user_id = str(uuid.uuid4())
        conn.execute(
            '''
            INSERT INTO users (id, username, display_name, password_hash, role, status)
            VALUES (?, ?, ?, ?, ?, 'active')
            ''',
            (user_id, username, display_name, generate_password_hash(password), role)
        )
        conn.commit()
        row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        return _sanitize_user(row)
    finally:
        conn.close()


def update_display_name(user_id: str, display_name: str):
    display_name = validate_display_name(display_name)
    conn = get_db_connection()
    try:
        conn.execute(
            'UPDATE users SET display_name = ? WHERE id = ?',
            (display_name, user_id)
        )
        conn.commit()
        row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        return _sanitize_user(row)
    finally:
        conn.close()


def change_password(user_id: str, current_password: str, new_password: str):
    new_password = validate_password(new_password)
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if not row:
            raise ValueError('User not found.')
        if not check_password_hash(row['password_hash'], current_password or ''):
            raise ValueError('Current password is incorrect.')

        conn.execute(
            'UPDATE users SET password_hash = ? WHERE id = ?',
            (generate_password_hash(new_password), user_id)
        )
        conn.commit()
    finally:
        conn.close()


def _ensure_admin_guard(conn, target_user_id: str, next_role: str | None = None, next_status: str | None = None):
    row = conn.execute('SELECT id, role, status FROM users WHERE id = ?', (target_user_id,)).fetchone()
    if not row:
        raise ValueError('User not found.')

    current_role = row['role']
    current_status = row['status']
    role_after = next_role or current_role
    status_after = next_status or current_status

    if current_role == 'admin' and current_status == 'active' and (role_after != 'admin' or status_after != 'active'):
        admin_count = conn.execute(
            "SELECT COUNT(*) AS count FROM users WHERE role = 'admin' AND status = 'active'"
        ).fetchone()
        if int(admin_count['count']) <= 1:
            raise ValueError('APPAM must keep at least one active admin.')


def admin_update_user(user_id: str, role: str | None = None, status: str | None = None, display_name: str | None = None):
    updates = {}
    if role is not None:
        updates['role'] = _validate_role(role)
    if status is not None:
        updates['status'] = _validate_status(status)
    if display_name is not None:
        updates['display_name'] = validate_display_name(display_name)

    if not updates:
        raise ValueError('No updates were provided.')

    conn = get_db_connection()
    try:
        _ensure_admin_guard(conn, user_id, next_role=updates.get('role'), next_status=updates.get('status'))

        sets = ', '.join(f"{column} = ?" for column in updates)
        values = list(updates.values()) + [user_id]
        conn.execute(f'UPDATE users SET {sets} WHERE id = ?', values)
        conn.commit()
        row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if not row:
            raise ValueError('User not found.')
        return _sanitize_user(row)
    finally:
        conn.close()


def generate_temporary_password(length: int = 18) -> str:
    while True:
        candidate = secrets.token_urlsafe(length)
        if len(candidate) >= 12:
            return candidate[: max(12, length)]


def admin_reset_password(user_id: str, new_password: str | None = None):
    password = validate_password(new_password) if new_password is not None else generate_temporary_password()
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if not row:
            raise ValueError('User not found.')

        conn.execute(
            'UPDATE users SET password_hash = ? WHERE id = ?',
            (generate_password_hash(password), user_id)
        )
        conn.commit()
        refreshed = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        return _sanitize_user(refreshed), password
    finally:
        conn.close()


def get_user_admin_impact(user_id: str):
    conn = get_db_connection()
    try:
        row = conn.execute(
            '''
            SELECT
                u.*,
                (
                    SELECT COUNT(*)
                    FROM projects p
                    WHERE p.owner_id = u.id
                ) AS owned_projects_count,
                (
                    SELECT COUNT(*)
                    FROM project_members pm
                    JOIN projects p ON p.id = pm.project_id
                    WHERE pm.user_id = u.id
                      AND p.owner_id != u.id
                ) AS member_projects_count,
                (
                    SELECT COUNT(*)
                    FROM jobs j
                    WHERE j.submitted_by = u.id
                      AND j.status IN ('queued', 'running')
                ) AS active_jobs_count
            FROM users u
            WHERE u.id = ?
            ''',
            (user_id,)
        ).fetchone()
        if not row:
            return None

        owned_projects = conn.execute(
            '''
            SELECT id, name, last_accessed, created_at
            FROM projects
            WHERE owner_id = ?
            ORDER BY last_accessed DESC, name ASC
            ''',
            (user_id,)
        ).fetchall()
        member_projects = conn.execute(
            '''
            SELECT
                p.id,
                p.name,
                p.last_accessed,
                p.created_at,
                pm.role AS project_role
            FROM project_members pm
            JOIN projects p ON p.id = pm.project_id
            WHERE pm.user_id = ?
              AND p.owner_id != ?
            ORDER BY p.last_accessed DESC, p.name ASC
            ''',
            (user_id, user_id)
        ).fetchall()
        active_jobs = conn.execute(
            '''
            SELECT id, project_id, tool_name, status, created_at
            FROM jobs
            WHERE submitted_by = ?
              AND status IN ('queued', 'running')
            ORDER BY created_at DESC
            ''',
            (user_id,)
        ).fetchall()

        user = _sanitize_user(row)
        impact = {
            'owned_projects_count': int(row['owned_projects_count'] or 0),
            'member_projects_count': int(row['member_projects_count'] or 0),
            'active_jobs_count': int(row['active_jobs_count'] or 0),
            'owned_projects': [dict(project) for project in owned_projects],
            'member_projects': [dict(project) for project in member_projects],
            'active_jobs': [dict(job) for job in active_jobs],
        }
        warnings = []
        if impact['owned_projects_count']:
            warnings.append(
                f"Disabling or deleting this user affects {impact['owned_projects_count']} owned project(s)."
            )
        if impact['member_projects_count']:
            warnings.append(
                f"This user still participates in {impact['member_projects_count']} shared project(s)."
            )
        if impact['active_jobs_count']:
            warnings.append(
                f"This user has {impact['active_jobs_count']} active job(s) in queue or running."
            )
        impact['warnings'] = warnings
        impact['can_delete'] = impact['owned_projects_count'] == 0
        return {
            'user': user,
            'impact': impact,
        }
    finally:
        conn.close()


def admin_delete_user(target_user_id: str, acting_user_id: str | None = None):
    conn = get_db_connection()
    try:
        if acting_user_id and acting_user_id == target_user_id:
            raise ValueError('You cannot delete your own account from the admin panel.')

        row = conn.execute('SELECT * FROM users WHERE id = ?', (target_user_id,)).fetchone()
        if not row:
            raise ValueError('User not found.')

        _ensure_admin_guard(conn, target_user_id, next_status='disabled')

        owned_projects_row = conn.execute(
            'SELECT COUNT(*) AS count FROM projects WHERE owner_id = ?',
            (target_user_id,)
        ).fetchone()
        owned_projects_count = int(owned_projects_row['count']) if owned_projects_row else 0
        if owned_projects_count:
            raise ValueError('Transfer or remove owned projects before deleting this user.')

        sanitized = _sanitize_user(row)
        conn.execute('DELETE FROM users WHERE id = ?', (target_user_id,))
        conn.commit()
        return sanitized
    finally:
        conn.close()


def record_auth_event(
    *,
    username: str | None,
    event_type: str,
    success: bool,
    user_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    details: dict | str | None = None,
) -> None:
    if isinstance(details, dict):
        details_value = json.dumps(details, ensure_ascii=False)
    elif details is None:
        details_value = None
    else:
        details_value = str(details)

    conn = get_db_connection()
    try:
        conn.execute(
            '''
            INSERT INTO auth_audit_log
            (user_id, username, event_type, success, ip_address, user_agent, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                user_id,
                (username or '').strip() or None,
                event_type,
                1 if success else 0,
                ip_address,
                user_agent,
                details_value,
            )
        )
        conn.commit()
    finally:
        conn.close()


def _count_recent_failed_attempts(conn, *, username: str | None = None, ip_address: str | None = None) -> int:
    conditions = ["success = 0", "event_type IN ('login_failed', 'login_rate_limited', 'login_disabled')"]
    params: list = []
    if username:
        conditions.append('username = ?')
        params.append(username)
    if ip_address:
        conditions.append('ip_address = ?')
        params.append(ip_address)
    conditions.append(f"created_at >= datetime('now', '-{LOGIN_RATE_LIMIT_WINDOW_MINUTES} minutes')")

    row = conn.execute(
        f'''
        SELECT COUNT(*) AS count
        FROM auth_audit_log
        WHERE {' AND '.join(conditions)}
        ''',
        tuple(params)
    ).fetchone()
    return int(row['count']) if row else 0


def assert_login_allowed(username: str, ip_address: str | None = None):
    username = (username or '').strip()
    conn = get_db_connection()
    try:
        username_attempts = _count_recent_failed_attempts(conn, username=username) if username else 0
        ip_attempts = _count_recent_failed_attempts(conn, ip_address=ip_address) if ip_address else 0
    finally:
        conn.close()

    if username_attempts >= LOGIN_RATE_LIMIT_MAX_BY_USERNAME or ip_attempts >= LOGIN_RATE_LIMIT_MAX_BY_IP:
        raise AuthRateLimitError('Too many failed login attempts. Please wait a few minutes and try again.')


def authenticate_user(username: str, password: str, ip_address: str | None = None, user_agent: str | None = None):
    username = (username or '').strip()
    password = password or ''

    assert_login_allowed(username, ip_address)

    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if not row or not check_password_hash(row['password_hash'], password):
            return None
        if row['status'] != 'active':
            raise AuthDisabledError('This account has been disabled.')

        conn.execute(
            'UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?',
            (row['id'],)
        )
        conn.commit()
        refreshed = conn.execute('SELECT * FROM users WHERE id = ?', (row['id'],)).fetchone()
        return _sanitize_user(refreshed)
    finally:
        conn.close()
