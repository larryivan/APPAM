import json
import os
from flask import Blueprint, jsonify, request
from flask_socketio import emit
from app import socketio

tools_bp = Blueprint('tools', __name__)

def load_tool_library():
    """加载工具库"""
    try:
        tool_library_path = os.path.join(os.path.dirname(__file__), '../../../tool_library.json')
        with open(tool_library_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading tool library: {e}")
        return []

@tools_bp.route('/tools', methods=['GET'])
def get_tools():
    """获取所有工具列表"""
    try:
        tools = load_tool_library()
        return jsonify({
            'success': True,
            'tools': tools,
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
        tools = load_tool_library()
        tool = next((t for t in tools if t['tool_name'].lower() == tool_name.lower()), None)
        
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
        
        # 导入ai_service来获取工具建议
        from app.services.ai_service import ai_service
        suggestion = ai_service.get_tool_suggestion(query)
        
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
        query = data.get('query', '')
        
        if not query:
            emit('tool_suggestion_response', {
                'success': False,
                'error': 'Query is required'
            })
            return
        
        # 导入ai_service来获取工具建议
        from app.services.ai_service import ai_service
        suggestion = ai_service.get_tool_suggestion(query)
        
        emit('tool_suggestion_response', {
            'success': True,
            'suggestion': suggestion
        })
    except Exception as e:
        emit('tool_suggestion_response', {
            'success': False,
            'error': str(e)
        })
