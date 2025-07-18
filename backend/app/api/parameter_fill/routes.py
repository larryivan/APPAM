"""
Parameter fill API routes for intelligent parameter suggestion.
"""

import json
from flask import Blueprint, request, jsonify, session
from flask_cors import cross_origin
from app.tools import tool_registry

parameter_fill_bp = Blueprint('parameter_fill', __name__)

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
        
        # Execute parameter fill tool
        tool_result = tool_registry.execute_tool(
            'fill_parameters',
            json.dumps({
                'tool_name': tool_name,
                'tool_parameters': tool_parameters,
                'project_id': project_id,
                'user_context': user_context
            })
        )
        
        if not tool_result.is_success:
            return jsonify({
                'success': False,
                'error': tool_result.content
            }), 500
        
        # Return successful result
        return jsonify({
            'success': True,
            'suggestions': tool_result.metadata.get('suggestions', {}),
            'summary': tool_result.metadata.get('summary', ''),
            'warnings': tool_result.metadata.get('warnings', []),
            'missing_info': tool_result.metadata.get('missing_info', []),
            'tool_name': tool_name
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@parameter_fill_bp.route('/conversation', methods=['POST'])
@cross_origin()
def conversational_parameter_fill():
    """Handle conversational parameter configuration."""
    try:
        data = request.json
        
        # Extract request data
        tool_name = data.get('tool_name')
        tool_parameters = data.get('tool_parameters', {})
        current_values = data.get('current_values', {})
        user_message = data.get('user_message', '')
        conversation_history = data.get('conversation_history', [])
        project_id = data.get('project_id')
        
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
        
        if not user_message:
            return jsonify({
                'success': False,
                'error': 'user_message is required'
            }), 400
        
        # Execute conversational parameter fill tool
        tool_result = tool_registry.execute_tool(
            'conversational_parameter_fill',
            json.dumps({
                'tool_name': tool_name,
                'tool_parameters': tool_parameters,
                'current_values': current_values,
                'user_message': user_message,
                'conversation_history': conversation_history,
                'project_id': project_id
            })
        )
        
        if not tool_result.is_success:
            return jsonify({
                'success': False,
                'error': tool_result.content
            }), 500
        
        # Return successful result
        return jsonify({
            'success': True,
            'message': tool_result.metadata.get('message', ''),
            'parameter_suggestions': tool_result.metadata.get('parameter_suggestions', {}),
            'questions': tool_result.metadata.get('questions', []),
            'next_steps': tool_result.metadata.get('next_steps', []),
            'ready_to_apply': tool_result.metadata.get('ready_to_apply', False),
            'tool_name': tool_name
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@parameter_fill_bp.route('/apply', methods=['POST'])
@cross_origin()
def apply_parameter_suggestions():
    """Apply parameter suggestions to the tool form."""
    try:
        data = request.json
        
        tool_name = data.get('tool_name')
        parameter_suggestions = data.get('parameter_suggestions', {})
        
        if not tool_name:
            return jsonify({
                'success': False,
                'error': 'tool_name is required'
            }), 400
        
        # Process parameter suggestions into a format suitable for form filling
        applied_parameters = {}
        for param_name, suggestion in parameter_suggestions.items():
            if isinstance(suggestion, dict) and 'value' in suggestion:
                applied_parameters[param_name] = suggestion['value']
            else:
                applied_parameters[param_name] = suggestion
        
        return jsonify({
            'success': True,
            'applied_parameters': applied_parameters,
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