from flask import Blueprint, jsonify, request

from app.auth import current_user, project_access_required, user_is_admin
from app.services import file_manager as services
from app.services.auth_service import (
    get_user_by_username,
    validate_project_member_role,
)


projects_bp = Blueprint('projects_bp', __name__)


@projects_bp.route('/', methods=['GET'])
def get_projects():
    user = current_user()
    projects = services.get_all_projects(user_id=user['id'], is_admin=user_is_admin(user))
    return jsonify(projects)


@projects_bp.route('/', methods=['POST'])
def create_project():
    user = current_user()
    data = request.get_json() or {}
    creator = data.get('creator') or user.get('display_name') or user.get('username')
    project = services.create_project(
        data['name'],
        data.get('description', ''),
        creator,
        owner_id=user['id']
    )
    return jsonify(project), 201


@projects_bp.route('/<project_id>', methods=['GET'])
@project_access_required
def get_project(project_id):
    user = current_user()
    project = services.get_project_by_id(project_id, user_id=user['id'], is_admin=user_is_admin(user))
    if project:
        return jsonify(project)
    return jsonify({'error': 'Project not found'}), 404


@projects_bp.route('/<project_id>', methods=['PUT'])
@project_access_required(min_role='owner')
def update_project(project_id):
    data = request.get_json() or {}
    updated = services.update_project(
        project_id,
        data.get('name'),
        data.get('description'),
        data.get('creator'),
    )
    if updated:
        user = current_user()
        project = services.get_project_by_id(project_id, user_id=user['id'], is_admin=user_is_admin(user))
        return jsonify(project)
    return jsonify({'error': 'Project not found'}), 404


@projects_bp.route('/<project_id>/access', methods=['POST'])
@project_access_required
def update_project_access(project_id):
    services.update_project_access_time(project_id)
    return '', 204


@projects_bp.route('/<project_id>', methods=['DELETE'])
@project_access_required(min_role='owner')
def delete_project(project_id):
    services.delete_project(project_id)
    return '', 204


@projects_bp.route('/<project_id>/members', methods=['GET'])
@project_access_required
def list_members(project_id):
    members = services.list_project_members(project_id)
    return jsonify({'members': members})


@projects_bp.route('/<project_id>/members', methods=['POST'])
@project_access_required(min_role='owner')
def add_member(project_id):
    data = request.get_json() or {}
    user_id = data.get('user_id')
    username = data.get('username')
    try:
        role = validate_project_member_role(data.get('role', 'viewer'))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    if not user_id:
        user = get_user_by_username(username)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        user_id = user['id']

    try:
        services.add_or_update_project_member(
            project_id,
            user_id,
            role,
            created_by=current_user()['id']
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    members = services.list_project_members(project_id)
    return jsonify({'members': members}), 201


@projects_bp.route('/<project_id>/members/<user_id>', methods=['PUT'])
@project_access_required(min_role='owner')
def update_member_role(project_id, user_id):
    data = request.get_json() or {}
    try:
        role = validate_project_member_role(data.get('role', 'viewer'))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    try:
        services.add_or_update_project_member(
            project_id,
            user_id,
            role,
            created_by=current_user()['id']
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    members = services.list_project_members(project_id)
    return jsonify({'members': members})


@projects_bp.route('/<project_id>/members/<user_id>', methods=['DELETE'])
@project_access_required(min_role='owner')
def remove_member(project_id, user_id):
    try:
        services.remove_project_member(project_id, user_id)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    members = services.list_project_members(project_id)
    return jsonify({'members': members})
