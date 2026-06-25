from __future__ import annotations

from functools import wraps

from flask import g, jsonify, session

from .database import get_db_connection
from .services.auth_service import get_user_by_id


PROJECT_ROLE_LEVELS = {
    'viewer': 1,
    'editor': 2,
    'owner': 3,
    'admin': 4,
}

ACTION_MIN_ROLES = {
    'view_project': 'viewer',
    'view_files': 'viewer',
    'view_results': 'viewer',
    'view_provenance': 'viewer',
    'upload_files': 'editor',
    'edit_files': 'editor',
    'create_manifest': 'editor',
    'run_workflow': 'editor',
    'cancel_own_job': 'editor',
    'manage_project': 'owner',
    'manage_members': 'owner',
    'delete_project': 'owner',
    'open_terminal': 'admin',
    'open_opencode': 'admin',
    'view_worker': 'admin',
    'manage_runtime': 'admin',
}


def load_current_user():
    user_id = session.get('user_id')
    user = get_user_by_id(user_id, active_only=True) if user_id else None
    if user_id and not user:
        session.clear()
    g.current_user = user
    return user


def session_user(active_only: bool = True):
    user_id = session.get('user_id')
    return get_user_by_id(user_id, active_only=active_only) if user_id else None


def resolved_current_user(active_only: bool = True):
    if active_only:
        return getattr(g, 'current_user', None) or session_user(active_only=True)
    return getattr(g, 'current_user', None) or session_user(active_only=False)


def current_user():
    return getattr(g, 'current_user', None)


def login_user(user: dict):
    session.clear()
    session['user_id'] = user['id']


def logout_user():
    session.clear()


def user_is_admin(user: dict | None = None) -> bool:
    user = user or resolved_current_user()
    return bool(user and user.get('role') == 'admin' and user.get('status') == 'active')


def project_role_at_least(role: str | None, required_role: str) -> bool:
    return PROJECT_ROLE_LEVELS.get(role or '', 0) >= PROJECT_ROLE_LEVELS.get(required_role, 0)


def can(user: dict | None, action: str, project: dict | None = None) -> bool:
    if not user or user.get('status') != 'active':
        return False
    if user_is_admin(user):
        return True
    required_role = ACTION_MIN_ROLES.get(action)
    if not required_role:
        return False
    if required_role == 'admin':
        return False
    role = project.get('access_role') if project else None
    return project_role_at_least(role, required_role)


def get_project_for_user(project_id: str, user: dict | None = None, min_role: str = 'viewer'):
    user = user or resolved_current_user()
    if not user:
        return None

    conn = get_db_connection()
    try:
        if user_is_admin(user):
            row = conn.execute(
                '''
                SELECT p.*, 'admin' AS access_role
                FROM projects p
                WHERE p.id = ?
                ''',
                (project_id,)
            ).fetchone()
        else:
            row = conn.execute(
                '''
                SELECT
                    p.*,
                    CASE
                        WHEN p.owner_id = ? THEN 'owner'
                        ELSE pm.role
                    END AS access_role
                FROM projects p
                LEFT JOIN project_members pm
                    ON pm.project_id = p.id
                   AND pm.user_id = ?
                WHERE p.id = ?
                  AND (p.owner_id = ? OR pm.user_id = ?)
                LIMIT 1
                ''',
                (user['id'], user['id'], project_id, user['id'], user['id'])
            ).fetchone()

        project = dict(row) if row else None
        if not project:
            return None
        if not project_role_at_least(project.get('access_role'), min_role):
            return None
        return project
    finally:
        conn.close()


def current_project():
    return getattr(g, 'current_project', None)


def current_project_role():
    project = current_project()
    return project.get('access_role') if project else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not resolved_current_user():
            return jsonify({'error': 'Authentication required'}), 401
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not resolved_current_user():
            return jsonify({'error': 'Authentication required'}), 401
        if not user_is_admin():
            return jsonify({'error': 'Admin access required'}), 403
        return view(*args, **kwargs)

    return wrapped


def project_access_required(view=None, *, min_role: str = 'viewer'):
    def decorator(func):
        @wraps(func)
        def wrapped(project_id, *args, **kwargs):
            project = get_project_for_user(project_id, min_role=min_role)
            if not project:
                return jsonify({'error': 'Project not found or access denied'}), 404
            g.current_project = project
            return func(project_id, *args, **kwargs)

        return wrapped

    if callable(view):
        return decorator(view)
    return decorator
