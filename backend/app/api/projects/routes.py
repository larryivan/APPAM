from flask import Blueprint, request, jsonify, session
from app.services import file_manager as services
import functools

projects_bp = Blueprint('projects_bp', __name__)

def require_project_access(f):
    """Decorator: Verify project access permissions"""
    @functools.wraps(f)
    def decorated_function(project_id, *args, **kwargs):
        # Check if project exists
        project = services.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # If project has no password protection, allow access directly
        if not project.get('has_password'):
            return f(project_id, *args, **kwargs)
        
        # Check if password has been verified in session
        session_key = f'project_access_{project_id}'
        if session.get(session_key):
            return f(project_id, *args, **kwargs)
        
        # Password verification required
        return jsonify({'error': 'Password required', 'has_password': True}), 401
    
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
        data.get('creator', ''),
        data.get('password', '')
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
    
    # If project has password protection, verify current password
    project = services.get_project_by_id(project_id)
    if project and project.get('has_password'):
        current_password = data.get('current_password', '')
        if not services.verify_project_password(project_id, current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401
    
    project = services.update_project(
        project_id, 
        data.get('name'), 
        data.get('description'),
        data.get('creator'),
        data.get('password')
    )
    if project:
        return jsonify(project)
    return jsonify({'error': 'Project not found'}), 404

@projects_bp.route('/<project_id>/verify-password', methods=['POST'])
def verify_project_password(project_id):
    """Verify project password."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        password = data.get('password', '')
        
        if services.verify_project_password(project_id, password):
            # Record verification in session
            session[f'project_access_{project_id}'] = True
            # Update access time on successful verification
            services.update_project_access_time(project_id)
            return jsonify({'success': True, 'message': 'Password verified'}), 200
        else:
            return jsonify({'success': False, 'message': 'Invalid password'}), 401
    except Exception as e:
        return jsonify({'success': False, 'message': 'Verification failed'}), 500

@projects_bp.route('/<project_id>/access', methods=['POST'])
@require_project_access
def update_project_access(project_id):
    services.update_project_access_time(project_id)
    return '', 204

@projects_bp.route('/<project_id>', methods=['DELETE'])
@require_project_access
def delete_project(project_id):
    project = services.get_project_by_id(project_id)
    if project and project.get('has_password'):
        data = request.get_json(silent=True) or {}
        current_password = data.get('current_password', '')
        if not services.verify_project_password(project_id, current_password):
            return jsonify({'error': 'Current password is incorrect, cannot delete project'}), 401
    services.delete_project(project_id)
    return '', 204
