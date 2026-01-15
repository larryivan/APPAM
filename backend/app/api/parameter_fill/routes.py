"""
Parameter fill API routes powered by OpenCode.
"""

import json
import uuid
import requests
from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from app.services.opencode_service import opencode_service

parameter_fill_bp = Blueprint('parameter_fill', __name__)

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
@cross_origin()
def suggest_parameters():
    """Generate parameter suggestions for a tool."""
    try:
        data = request.json
        
        # Extract request data
        tool_name = data.get('tool_name')
        tool_parameters = data.get('tool_parameters', {})
        project_id = data.get('project_id')
        user_context = data.get('user_context', '')
        
        if not tool_name:
            return jsonify({
                'success': False,
                'error': 'tool_name is required'
            }), 400
        
        if not tool_parameters:
            return jsonify({
                'success': False,
                'error': 'tool_parameters is required'
            }), 400
        
        prompt = _build_suggestion_prompt(tool_name, tool_parameters, user_context)
        try:
            result = opencode_service.request_json(
                message=prompt,
                project_id=project_id,
                app_session_id=f"parameter_fill_{uuid.uuid4().hex}",
            )
        except requests.RequestException as exc:
            return jsonify({
                'success': False,
                'error': f'OpenCode request failed: {str(exc)}'
            }), 502
        except ValueError as exc:
            return jsonify({
                'success': False,
                'error': f'OpenCode response invalid: {str(exc)}'
            }), 502

        return jsonify({
            'success': True,
            'suggestions': result.get('suggestions', {}),
            'summary': result.get('summary', ''),
            'warnings': result.get('warnings', []),
            'missing_info': result.get('missing_info', []),
            'tool_name': tool_name
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@parameter_fill_bp.route('/health', methods=['GET'])
@cross_origin()
def parameter_fill_health():
    """Health check for parameter fill service."""
    return jsonify({
        'status': 'healthy',
        'service': 'parameter_fill'
    }) 
