
import json
import time
import os
from flask import Blueprint, request, jsonify, Response
from app.services.process_manager import run_process, log_stream, get_task_status, get_process_history, RUNNING_PROCESSES, TASK_STATUSES

pipeline_bp = Blueprint('pipeline_bp', __name__)

with open('tool_library.json', 'r') as f:
    tool_library = {tool['tool_name'].lower(): tool for tool in json.load(f)}

def get_project_absolute_path(project_id, relative_path=''):
    """Get absolute path for a file/directory within the project."""
    # Get the current working directory (should be the backend directory)
    backend_dir = os.getcwd()
    # Build absolute path to project directory
    project_dir = os.path.join(backend_dir, 'projects', project_id)
    
    if relative_path:
        # Remove leading slash if present and join with project directory
        clean_path = relative_path.lstrip('/')
        return os.path.join(project_dir, clean_path)
    else:
        return project_dir

@pipeline_bp.route('/<project_id>/run/<tool_name>', methods=['POST'])
def run_tool_endpoint(project_id, tool_name):
    # Check if a task is already running for this project
    if get_task_status(project_id)['status'] == 'running':
        return jsonify({'error': 'A task is already running for this project. Please wait for it to complete.'}), 409

    tool_name_lower = tool_name.lower()
    if tool_name_lower not in tool_library:
        return jsonify({'error': f'Tool "{tool_name}" not found in library.'}), 404

    tool_info = tool_library[tool_name_lower]
    params = request.get_json() or {}
    
    # 验证参数
    validation_errors = []
    for p in tool_info['parameters']:
        param_name = p['name']
        param_value = params.get(param_name)
        
        # 验证required参数
        if p.get('required', False) and not param_value:
            validation_errors.append(f"Required parameter '{param_name}' is missing")
        
        # 验证options参数
        if param_value and p.get('options'):
            if isinstance(param_value, list):
                # 多选参数
                for value in param_value:
                    if value not in p['options']:
                        validation_errors.append(f"Parameter '{param_name}' value '{value}' is not in allowed options: {p['options']}")
            else:
                # 单选参数
                if param_value not in p['options']:
                    validation_errors.append(f"Parameter '{param_name}' value '{param_value}' is not in allowed options: {p['options']}")
        
        # 验证数值类型
        if param_value and p.get('type') == 'integer':
            try:
                int(param_value)
            except (ValueError, TypeError):
                validation_errors.append(f"Parameter '{param_name}' must be an integer")
        
        if param_value and p.get('type') == 'float':
            try:
                float(param_value)
            except (ValueError, TypeError):
                validation_errors.append(f"Parameter '{param_name}' must be a float")
    
    if validation_errors:
        return jsonify({
            'error': 'Parameter validation failed',
            'details': validation_errors
        }), 400
    
    # 构建命令
    command_parts = [tool_name_lower]
    
    # Keep track of directories to create
    directories_to_create = []
    
    # Process file parameters first (they should come before other parameters)
    file_params = []
    for p in tool_info['parameters']:
        if p.get('type') == 'file' and p['name'] in params:
            files = params[p['name']]
            if isinstance(files, list):
                # Multiple files
                for file_path in files:
                    # Convert to absolute path
                    abs_file_path = get_project_absolute_path(project_id, file_path)
                    file_params.append(abs_file_path)
            elif files:
                # Single file
                abs_file_path = get_project_absolute_path(project_id, files)
                file_params.append(abs_file_path)
    
    # Add file parameters to command
    command_parts.extend(file_params)
    
    # Process other parameters (including directory type)
    for p in tool_info['parameters']:
        if p.get('type') not in ['file'] and p['name'] in params:
            if p.get('type') == 'flag' and params[p['name']]:
                command_parts.append(p['name'])
            elif p.get('type') == 'directory' and params[p['name']]:
                # Handle directory type parameters
                dir_path = params[p['name']]
                if isinstance(dir_path, list):
                    # Multiple directories
                    for directory in dir_path:
                        command_parts.append(p['name'])
                        # Convert to absolute path
                        abs_dir_path = get_project_absolute_path(project_id, directory)
                        command_parts.append(abs_dir_path)
                        # Check if this looks like an output directory and should be created
                        if 'out' in p['name'].lower() or 'output' in p['name'].lower():
                            directories_to_create.append(abs_dir_path)
                else:
                    # Single directory
                    command_parts.append(p['name'])
                    # Convert to absolute path
                    abs_dir_path = get_project_absolute_path(project_id, dir_path)
                    command_parts.append(abs_dir_path)
                    # Check if this looks like an output directory and should be created
                    if 'out' in p['name'].lower() or 'output' in p['name'].lower():
                        directories_to_create.append(abs_dir_path)
            elif p.get('type') not in ['flag', 'directory'] and params[p['name']]:
                # Handle other parameter types (string, integer, etc.)
                command_parts.append(p['name'])
                command_parts.append(str(params[p['name']]))

    # Create output directories if they don't exist
    for dir_path in directories_to_create:
        try:
            os.makedirs(dir_path, exist_ok=True)
            print(f"Created directory: {dir_path}")
        except Exception as e:
            print(f"Failed to create directory {dir_path}: {e}")
            return jsonify({'error': f'Failed to create output directory: {dir_path}'}), 500

    command_str = ' '.join(command_parts)
    
    # Log the final command for debugging
    print(f"Executing command: {command_str}")
    
    run_process(command_str, project_id, tool_name)

    return jsonify({'message': f'Tool "{tool_name}" started successfully.', 'command': command_str})

@pipeline_bp.route('/<project_id>/stream-logs')
def stream_logs(project_id):
    def generate():
        # 首先检查任务状态，避免不必要的流建立
        task_status = get_task_status(project_id)
        current_status = task_status.get('status', 'not_found')
        
        if current_status == 'running':
            # 有正在运行的任务，正常流式传输日志
            for log_entry in log_stream(project_id):
                yield f"data: {log_entry}\n\n"
        else:
            # 没有正在运行的任务，发送状态信息后保持连接一段时间
            if current_status == 'not_found':
                yield f"data: [SYSTEM] Ready to receive new tasks.\n\n"
            else:
                tool_name = task_status.get('tool', 'unknown')
                yield f"data: [SYSTEM] Last task: {tool_name} ({current_status})\n\n"
            
            # 保持连接60秒，期间每20秒发送一个静默心跳（减少噪音）
            for i in range(3):
                time.sleep(20)
                # 只发送静默心跳，不产生日志噪音
                yield f"data: [HEARTBEAT_SILENT]\n\n"
            
            yield f"data: [SYSTEM] Connection closed - no active tasks.\n\n"
    
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

@pipeline_bp.route('/<project_id>/task-status')
def task_status(project_id):
    status = TASK_STATUSES.get(project_id, {'status': 'not_found'})
    return jsonify(status)

@pipeline_bp.route('/<project_id>/history')
def process_history(project_id):
    """Get process execution history for a project."""
    limit = request.args.get('limit', 20, type=int)
    history = get_process_history(project_id, limit)
    return jsonify(history)
