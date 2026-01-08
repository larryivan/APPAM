from flask import Blueprint, request, jsonify
from app.services import file_manager as services
import functools

projects_bp = Blueprint('projects_bp', __name__)

def require_project_access(f):
    """Decorator: Verify project exists"""
    @functools.wraps(f)
    def decorated_function(project_id, *args, **kwargs):
        # Check if project exists
        project = services.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        return f(project_id, *args, **kwargs)

    return decorated_function

@projects_bp.route('/', methods=['GET'])
def get_projects():
    projects = services.get_all_projects()
    return jsonify(projects)

@projects_bp.route('/', methods=['POST'])
def create_project():
    data = request.get_json()
    project = services.create_project(
        data['name'], 
        data.get('description', ''), 
        data.get('creator', '')
    )
    return jsonify(project), 201

@projects_bp.route('/<project_id>', methods=['GET'])
@require_project_access
def get_project(project_id):
    project = services.get_project_by_id(project_id)
    if project:
        return jsonify(project)
    return jsonify({'error': 'Project not found'}), 404

@projects_bp.route('/<project_id>', methods=['PUT'])
@require_project_access
def update_project(project_id):
    data = request.get_json()

    project = services.update_project(
        project_id, 
        data.get('name'), 
        data.get('description'),
        data.get('creator')
    )
    if project:
        return jsonify(project)
    return jsonify({'error': 'Project not found'}), 404

@projects_bp.route('/<project_id>/access', methods=['POST'])
@require_project_access
def update_project_access(project_id):
    services.update_project_access_time(project_id)
    return '', 204

@projects_bp.route('/<project_id>', methods=['DELETE'])
@require_project_access
def delete_project(project_id):
    services.delete_project(project_id)
    return '', 204
