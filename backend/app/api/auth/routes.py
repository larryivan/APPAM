from flask import Blueprint, jsonify, request

from app.auth import admin_required, current_user, login_required, login_user, logout_user
from app.services.auth_service import (
    AuthDisabledError,
    AuthRateLimitError,
    admin_delete_user,
    admin_reset_password,
    admin_update_user,
    authenticate_user,
    change_password,
    create_user,
    get_user_admin_impact,
    list_users,
    record_auth_event,
    search_active_users,
    update_display_name,
)


auth_bp = Blueprint('auth', __name__)


def _request_ip() -> str | None:
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote_addr


def _request_user_agent() -> str:
    return request.headers.get('User-Agent', '')


@auth_bp.route('/auth/me', methods=['GET'])
def get_current_user_endpoint():
    user = current_user()
    return jsonify({
        'authenticated': bool(user),
        'user': user
    })


@auth_bp.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username', '')
    password = data.get('password', '')
    display_name = data.get('display_name', '')

    try:
        user = create_user(username=username, password=password, display_name=display_name)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    record_auth_event(
        username=user['username'],
        user_id=user['id'],
        event_type='register',
        success=True,
        ip_address=_request_ip(),
        user_agent=_request_user_agent(),
    )
    login_user(user)
    return jsonify({
        'message': 'Registration successful.',
        'user': user
    }), 201


@auth_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username', '')
    password = data.get('password', '')
    ip_address = _request_ip()
    user_agent = _request_user_agent()

    try:
        user = authenticate_user(
            username=username,
            password=password,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except AuthRateLimitError as exc:
        record_auth_event(
            username=username,
            event_type='login_rate_limited',
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return jsonify({'error': str(exc)}), 429
    except AuthDisabledError as exc:
        record_auth_event(
            username=username,
            event_type='login_disabled',
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return jsonify({'error': str(exc)}), 403

    if not user:
        record_auth_event(
            username=username,
            event_type='login_failed',
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return jsonify({'error': 'Invalid username or password.'}), 401

    record_auth_event(
        username=user['username'],
        user_id=user['id'],
        event_type='login_success',
        success=True,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    login_user(user)
    return jsonify({
        'message': 'Login successful.',
        'user': user
    })


@auth_bp.route('/auth/logout', methods=['POST'])
def logout():
    user = current_user()
    if user:
        record_auth_event(
            username=user['username'],
            user_id=user['id'],
            event_type='logout',
            success=True,
            ip_address=_request_ip(),
            user_agent=_request_user_agent(),
        )
    logout_user()
    return jsonify({'message': 'Logout successful.'})


@auth_bp.route('/auth/profile', methods=['PUT'])
@login_required
def update_profile():
    data = request.get_json() or {}
    try:
        user = update_display_name(current_user()['id'], data.get('display_name', ''))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    login_user(user)
    return jsonify({'message': 'Profile updated.', 'user': user})


@auth_bp.route('/auth/password', methods=['POST'])
@login_required
def update_password():
    data = request.get_json() or {}
    try:
        change_password(
            current_user()['id'],
            data.get('current_password', ''),
            data.get('new_password', '')
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    return jsonify({'message': 'Password updated.'})


@auth_bp.route('/auth/users/search', methods=['GET'])
@login_required
def search_users():
    query = request.args.get('query', '')
    users = search_active_users(query=query, exclude_user_id=current_user()['id'])
    return jsonify({'users': users})


@auth_bp.route('/admin/users', methods=['GET'])
@admin_required
def admin_list_users():
    search = request.args.get('search', '')
    return jsonify({'users': list_users(search=search)})


@auth_bp.route('/admin/users/<user_id>', methods=['GET'])
@admin_required
def admin_get_user(user_id):
    payload = get_user_admin_impact(user_id)
    if not payload:
        return jsonify({'error': 'User not found.'}), 404
    return jsonify(payload)


@auth_bp.route('/admin/users/<user_id>', methods=['PATCH'])
@admin_required
def admin_patch_user(user_id):
    data = request.get_json() or {}
    try:
        user = admin_update_user(
            user_id,
            role=data.get('role'),
            status=data.get('status'),
            display_name=data.get('display_name'),
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    if current_user() and current_user()['id'] == user_id:
        login_user(user)

    return jsonify({'message': 'User updated.', 'user': user})


@auth_bp.route('/admin/users/<user_id>/reset-password', methods=['POST'])
@admin_required
def admin_reset_user_password(user_id):
    data = request.get_json() or {}
    try:
        user, temporary_password = admin_reset_password(
            user_id,
            new_password=data.get('new_password'),
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    return jsonify({
        'message': 'Password reset successfully.',
        'user': user,
        'temporary_password': temporary_password,
    })


@auth_bp.route('/admin/users/<user_id>', methods=['DELETE'])
@admin_required
def admin_remove_user(user_id):
    try:
        deleted_user = admin_delete_user(user_id, acting_user_id=current_user()['id'])
    except ValueError as exc:
        impact_payload = get_user_admin_impact(user_id)
        return jsonify({
            'error': str(exc),
            'impact': impact_payload['impact'] if impact_payload else None,
        }), 400

    return jsonify({
        'message': 'User deleted.',
        'user': deleted_user,
    })
