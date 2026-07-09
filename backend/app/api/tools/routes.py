from flask import Blueprint, jsonify
from app.auth import current_user
from app.services.tool_library import get_tool_catalog

tools_bp = Blueprint('tools', __name__)


def _visible_tool_catalog():
    tools, tools_by_key, sections = get_tool_catalog()
    if (current_user() or {}).get('role') != 'admin':
        visible_ids = {tool['id'] for tool in tools if not tool.get('admin_only')}
        tools = [tool for tool in tools if tool['id'] in visible_ids]
        tools_by_key = {key: tool for key, tool in tools_by_key.items() if tool['id'] in visible_ids}
        for section in sections:
            section['tools'] = [tool for tool in section.get('tools') or [] if tool['id'] in visible_ids]
        sections = [section for section in sections if section['tools']]
        for tool in tools:
            tool['parameters'] = [
                parameter for parameter in tool.get('parameters') or []
                if not parameter.get('admin_only')
            ]
    for tool in tools:
        execution = tool.get('execution') or {}
        tool['execution'] = {
            key: execution[key]
            for key in ('mode', 'workflow_id')
            if key in execution
        }
    return tools, tools_by_key, sections

@tools_bp.route('/tools', methods=['GET'])
def get_tools():
    """获取所有工具列表"""
    try:
        tools, tools_by_key, sections = _visible_tool_catalog()
        return jsonify({
            'success': True,
            'tools': tools,
            'tools_by_key': tools_by_key,
            'sections': sections,
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
        _, tools_by_key, _ = _visible_tool_catalog()
        tool = tools_by_key.get(tool_name.lower())
        
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
