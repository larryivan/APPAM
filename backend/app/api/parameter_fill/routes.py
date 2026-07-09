"""
Parameter fill API routes powered by OpenCode.
"""

import json
import uuid
import requests
from flask import Blueprint, current_app, request, jsonify
from app.auth import current_user, get_project_for_user
from app.services.opencode_service import opencode_service
from app.services.tool_library import get_tool_catalog

parameter_fill_bp = Blueprint('parameter_fill', __name__)


def _tool_context(tool_name: str):
    tools, _, _ = get_tool_catalog()
    normalized = tool_name.strip().lower()
    tool = next(
        (
            item for item in tools
            if normalized in {
                str(item.get('id', '')).lower(),
                str(item.get('tool_name', '')).lower(),
            }
        ),
        None,
    )
    if not tool:
        return None
    if tool.get('admin_only') and (current_user() or {}).get('role') != 'admin':
        return None

    parameters = {}
    for parameter in tool.get('parameters') or []:
        if parameter.get('admin_only') and (current_user() or {}).get('role') != 'admin':
            continue
        parameters[parameter['name']] = {
            key: parameter[key]
            for key in ('type', 'description', 'required', 'default', 'extensions', 'multiple', 'options')
            if key in parameter
        }
    return tool, parameters


def _clean_text_list(value, limit=20):
    if not isinstance(value, list):
        return []
    return [str(item)[:500] for item in value[:limit]]

def _build_suggestion_prompt(tool_name: str, tool_parameters: dict, user_context: str) -> str:
    return (
        "You are a bioinformatics assistant. Return ONLY valid JSON with this schema:\n"
        "{\n"
        '  "suggestions": {\n'
        '    "param_name": {"value": "...", "reasoning": "..."}\n'
        "  },\n"
        '  "summary": "...",\n'
        '  "warnings": ["..."],\n'
        '  "missing_info": ["..."]\n'
        "}\n"
        "Do not include Markdown, comments, or extra text.\n\n"
        f"Tool: {tool_name}\n"
        f"Parameters: {json.dumps(tool_parameters, ensure_ascii=False)}\n"
        f"User context: {user_context or 'N/A'}\n"
    )


@parameter_fill_bp.route('/suggest', methods=['POST'])
def suggest_parameters():
    """Generate parameter suggestions for a tool."""
    try:
        if request.content_length and request.content_length > 64 * 1024:
            return jsonify({'success': False, 'error': 'Request is too large'}), 413

        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({'success': False, 'error': 'A JSON object is required'}), 400

        tool_name = data.get('tool_name')
        project_id = data.get('project_id')
        user_context = str(data.get('user_context', ''))[:2000]

        if not isinstance(tool_name, str) or not tool_name.strip() or len(tool_name) > 120:
            return jsonify({
                'success': False,
                'error': 'A valid tool_name is required'
            }), 400

        if project_id is not None:
            if not isinstance(project_id, str) or not project_id.strip() or len(project_id) > 120:
                return jsonify({'success': False, 'error': 'A valid project_id is required'}), 400
            if not get_project_for_user(project_id, user=current_user(), min_role='viewer'):
                return jsonify({'success': False, 'error': 'Project not found or access denied'}), 404

        resolved = _tool_context(tool_name)
        if not resolved:
            return jsonify({
                'success': False,
                'error': 'Tool not found'
            }), 404

        tool, tool_parameters = resolved
        prompt = _build_suggestion_prompt(tool['tool_name'], tool_parameters, user_context)
        try:
            result = opencode_service.request_json(
                message=prompt,
                project_id=project_id,
                app_session_id=f"parameter_fill_{uuid.uuid4().hex}",
            )
            if not isinstance(result, dict):
                raise ValueError('OpenCode response must be a JSON object')
        except requests.RequestException as exc:
            current_app.logger.warning('OpenCode parameter request failed: %s', exc)
            return jsonify({
                'success': False,
                'error': 'Parameter suggestion service is unavailable'
            }), 502
        except ValueError as exc:
            current_app.logger.warning('OpenCode returned an invalid parameter response: %s', exc)
            return jsonify({
                'success': False,
                'error': 'Parameter suggestion service returned an invalid response'
            }), 502

        suggestions = result.get('suggestions', {}) if isinstance(result, dict) else {}
        if not isinstance(suggestions, dict):
            suggestions = {}
        suggestions = {
            name: suggestion
            for name, suggestion in suggestions.items()
            if name in tool_parameters
        }

        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'summary': str(result.get('summary', ''))[:2000],
            'warnings': _clean_text_list(result.get('warnings')),
            'missing_info': _clean_text_list(result.get('missing_info')),
            'tool_name': tool['tool_name']
        })

    except Exception:
        current_app.logger.exception('Unexpected parameter suggestion error')
        return jsonify({
            'success': False,
            'error': 'Parameter suggestion failed'
        }), 500


@parameter_fill_bp.route('/health', methods=['GET'])
def parameter_fill_health():
    """Health check for parameter fill service."""
    health = opencode_service.health()
    return jsonify({
        'status': 'ok' if health['available'] else 'unavailable',
        'service': 'parameter_fill',
        'available': health['available'],
        'version': health['version'],
    })
