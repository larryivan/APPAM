import json
import uuid
from flask import Blueprint, jsonify, request, session
from flask_socketio import emit
from app import socketio
from app.services.opencode_service import opencode_service
from app.services.tool_library import get_tool_definition, get_tool_library, get_tool_library_map, get_tool_sections

tools_bp = Blueprint('tools', __name__)

def _build_tool_suggestion_prompt(query: str, tools: list) -> str:
    tool_summaries = [
        {
            "name": tool.get("tool_name"),
            "description": tool.get("description", "")
        }
        for tool in tools
    ]
    return (
        "You are a bioinformatics assistant. Return ONLY valid JSON:\n"
        "{\n"
        '  "has_recommendation": true/false,\n'
        '  "recommended_tool": "tool_name",\n'
        '  "confidence": 0.0,\n'
        '  "reasoning": "...",\n'
        '  "alternative_tools": ["tool1", "tool2"]\n'
        "}\n"
        "Only recommend a tool if the user explicitly asks for tool suggestions.\n"
        "Do not include Markdown or extra text.\n\n"
        f"User query: {query}\n"
        f"Tools: {json.dumps(tool_summaries, ensure_ascii=False)}\n"
    )

def _map_tool_recommendation(result: dict, tools: list) -> dict:
    if not result.get("has_recommendation"):
        return {
            "recommendation": None,
            "query": result.get("query")
        }

    recommended_name = result.get("recommended_tool")
    tool = next((t for t in tools if t.get("tool_name", "").lower() == str(recommended_name).lower()), None)

    return {
        "tool": tool,
        "confidence": result.get("confidence", 0.0),
        "reasoning": result.get("reasoning", ""),
        "alternative_tools": result.get("alternative_tools", []),
    }

@tools_bp.route('/tools', methods=['GET'])
def get_tools():
    """获取所有工具列表"""
    try:
        tools = get_tool_library()
        return jsonify({
            'success': True,
            'tools': tools,
            'tools_by_key': get_tool_library_map(),
            'sections': get_tool_sections(),
            'count': len(tools)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tools_bp.route('/tools/<tool_name>', methods=['GET'])
def get_tool(tool_name):
    """获取特定工具信息"""
    try:
        tool = get_tool_definition(tool_name)
        
        if tool:
            return jsonify({
                'success': True,
                'tool': tool
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Tool not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tools_bp.route('/tools/suggest', methods=['POST'])
def suggest_tool():
    """基于查询建议工具"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query is required'
            }), 400
        
        tools = get_tool_library()
        prompt = _build_tool_suggestion_prompt(query, tools)
        result = opencode_service.request_json(
            message=prompt,
            project_id=None,
            app_session_id=f"tool_suggest_{uuid.uuid4().hex}",
        )
        suggestion = _map_tool_recommendation(result, tools)
        
        return jsonify({
            'success': True,
            'suggestion': suggestion
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@socketio.on('request_tool_suggestion', namespace='/chat')
def handle_tool_suggestion_request(data):
    """处理工具建议请求"""
    try:
        if not session.get('user_id'):
            emit('tool_suggestion_response', {
                'success': False,
                'error': 'Authentication required'
            })
            return
        query = data.get('query', '')
        
        if not query:
            emit('tool_suggestion_response', {
                'success': False,
                'error': 'Query is required'
            })
            return
        
        tools = get_tool_library()
        prompt = _build_tool_suggestion_prompt(query, tools)
        result = opencode_service.request_json(
            message=prompt,
            project_id=None,
            app_session_id=f"tool_suggest_{uuid.uuid4().hex}",
        )
        suggestion = _map_tool_recommendation(result, tools)
        
        emit('tool_suggestion_response', {
            'success': True,
            'suggestion': suggestion
        })
    except Exception as e:
        emit('tool_suggestion_response', {
            'success': False,
            'error': str(e)
        })
