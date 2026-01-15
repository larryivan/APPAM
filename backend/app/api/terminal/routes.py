import json
import os
import pty
import select
import struct
import fcntl
import termios
from collections import deque
from flask import Blueprint, request
from flask_socketio import emit, join_room, leave_room
from app import socketio
import logging

terminal_bp = Blueprint('terminal', __name__)
logger = logging.getLogger(__name__)

# 存储终端会话
terminal_sessions = {}
client_sessions = {}

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DEFAULT_OPENCODE_AGENTS_PATH = os.path.join(BACKEND_DIR, "opencode", "AGENTS.md")
DEFAULT_OPENCODE_SYSTEM_PROMPT_PATH = os.path.join(BACKEND_DIR, "opencode", "system_prompt.txt")

class TerminalSession:
    def __init__(self, session_key, project_path, keep_alive=False, extra_env=None):
        self.session_key = session_key
        self.project_path = project_path
        self.keep_alive = keep_alive
        self.extra_env = extra_env or {}
        self.process = None
        self.fd = None
        self.pid = None
        self.clients = set()
        self.reading = False
        self.output_chunks = deque()
        self.output_size = 0
        try:
            self.buffer_limit = max(0, int(os.getenv("TERMINAL_OUTPUT_BUFFER_SIZE", "2000000")))
        except ValueError:
            self.buffer_limit = 2000000
        
    def start(self):
        """启动终端会话"""
        try:
            # 创建伪终端
            self.pid, self.fd = pty.fork()
            
            if self.pid == 0:  # 子进程
                # 设置环境变量
                env = os.environ.copy()
                env['TERM'] = 'xterm-256color'
                env['PYTHONUNBUFFERED'] = '1'
                if self.extra_env:
                    env.update(self.extra_env)
                
                # 切换到项目目录
                if os.path.exists(self.project_path):
                    os.chdir(self.project_path)
                    logger.info(f"Changed directory to: {self.project_path}")
                else:
                    logger.warning(f"Project path does not exist: {self.project_path}")
                
                # 启动 shell
                shell = os.environ.get('SHELL', '/bin/bash')
                os.execvpe(shell, [shell], env)
            else:  # 父进程
                # 设置非阻塞模式
                fcntl.fcntl(self.fd, fcntl.F_SETFL, os.O_NONBLOCK)
                logger.info(f"Terminal session {self.session_key} started with PID {self.pid}")
                
        except Exception as e:
            logger.error(f"Failed to start terminal session: {e}")
            raise
            
    def resize(self, rows, cols):
        """调整终端大小"""
        if self.fd:
            try:
                winsize = struct.pack('HHHH', rows, cols, 0, 0)
                fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsize)
            except Exception as e:
                logger.error(f"Failed to resize terminal: {e}")
                
    def write(self, data):
        """写入数据到终端"""
        if self.fd:
            try:
                os.write(self.fd, data.encode())
            except Exception as e:
                logger.error(f"Failed to write to terminal: {e}")
                
    def read(self):
        """从终端读取数据"""
        if self.fd:
            try:
                # 检查是否有数据可读
                if self.fd in select.select([self.fd], [], [], 0)[0]:
                    data = os.read(self.fd, 1024)
                    return data.decode('utf-8', errors='replace')
            except Exception as e:
                logger.error(f"Failed to read from terminal: {e}")
        return None

    def append_output(self, data):
        """缓存终端输出以支持会话重连回放"""
        if not data or self.buffer_limit <= 0:
            return
        self.output_chunks.append(data)
        self.output_size += len(data)
        while self.output_chunks and self.output_size > self.buffer_limit:
            chunk = self.output_chunks.popleft()
            self.output_size -= len(chunk)

    def get_output_buffer(self):
        """获取当前缓存的输出内容"""
        if not self.output_chunks:
            return ""
        return "".join(self.output_chunks)
        
    def close(self):
        """关闭终端会话"""
        if self.fd:
            try:
                os.close(self.fd)
            except:
                pass
        if self.pid:
            try:
                os.kill(self.pid, 9)
            except:
                pass
        logger.info(f"Terminal session {self.session_key} closed")

    @property
    def room(self):
        return f"terminal:{self.session_key}"

    def add_client(self, client_id):
        self.clients.add(client_id)

    def remove_client(self, client_id):
        self.clients.discard(client_id)

    def should_close(self):
        return not self.keep_alive and not self.clients


def _resolve_terminal_command(preset, initial_command):
    if initial_command:
        return initial_command
    if preset == "opencode":
        return os.getenv("OPENCODE_CLI_COMMAND", "opencode")
    return ""


def _resolve_opencode_path(value, fallback):
    candidate = value or fallback
    if not candidate:
        return ""
    if os.path.isabs(candidate):
        return candidate
    return os.path.join(BACKEND_DIR, candidate)


def _load_text(path):
    if not path or not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError as exc:
        logger.warning(f"Failed to read OpenCode file {path}: {exc}")
    return ""


def _parse_opencode_config():
    raw = os.getenv("OPENCODE_CONFIG_CONTENT", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        logger.warning("OPENCODE_CONFIG_CONTENT is not valid JSON; ignoring.")
        return {}


def _build_opencode_config():
    config = _parse_opencode_config()

    instructions = list(config.get("instructions") or [])
    agents_path = _resolve_opencode_path(
        os.getenv("OPENCODE_CLI_AGENTS_PATH"),
        DEFAULT_OPENCODE_AGENTS_PATH,
    )
    if agents_path and os.path.exists(agents_path) and agents_path not in instructions:
        instructions.append(agents_path)
    if instructions:
        config["instructions"] = instructions

    system_prompt_path = _resolve_opencode_path(
        os.getenv("OPENCODE_CLI_SYSTEM_PROMPT_PATH"),
        DEFAULT_OPENCODE_SYSTEM_PROMPT_PATH,
    )
    system_prompt = _load_text(system_prompt_path)
    if system_prompt:
        agent_name = os.getenv("OPENCODE_CLI_AGENT") or os.getenv("OPENCODE_AGENT") or "build"
        agent_block = config.get("agent") if isinstance(config.get("agent"), dict) else {}
        if agent_name not in agent_block or not agent_block.get(agent_name, {}).get("prompt"):
            agent_block[agent_name] = {**agent_block.get(agent_name, {}), "prompt": system_prompt}
        if "general" not in agent_block:
            agent_block["general"] = {"prompt": system_prompt}
        config["agent"] = agent_block

    provider_id = os.getenv("OPENCODE_LLM_PROVIDER_ID") or os.getenv("OPENCODE_PROVIDER_ID")
    api_key = os.getenv("OPENCODE_LLM_API_KEY")
    base_url = os.getenv("OPENCODE_LLM_BASE_URL")
    if provider_id and (api_key or base_url):
        provider_block = config.get("provider") if isinstance(config.get("provider"), dict) else {}
        provider_config = provider_block.get(provider_id, {})
        options = provider_config.get("options", {})
        if api_key and not options.get("apiKey"):
            options["apiKey"] = api_key
        if base_url and not options.get("baseURL"):
            options["baseURL"] = base_url
        provider_config["options"] = options
        provider_block[provider_id] = provider_config
        config["provider"] = provider_block

    model = os.getenv("OPENCODE_LLM_MODEL") or os.getenv("OPENCODE_MODEL_ID")
    if model and not config.get("model"):
        if provider_id and "/" not in model:
            config["model"] = f"{provider_id}/{model}"
        else:
            config["model"] = model

    return config


def _build_opencode_env():
    config = _build_opencode_config()
    if not config:
        return {}
    return {"OPENCODE_CONFIG_CONTENT": json.dumps(config)}


def _detach_client(session_id, session_key=None):
    resolved_key = session_key or client_sessions.get(session_id) or session_id
    client_sessions.pop(session_id, None)
    session = terminal_sessions.get(resolved_key)
    if not session:
        return
    session.remove_client(session_id)
    if session.should_close():
        session.close()
        terminal_sessions.pop(resolved_key, None)


@socketio.on('terminal_connect')
def handle_terminal_connect(data):
    """处理终端连接请求"""
    session_id = request.sid
    project_id = data.get('project_id')
    session_key = data.get('session_key') or session_id
    keep_alive = bool(data.get('keep_alive', False))
    preset = data.get('preset')
    initial_command = _resolve_terminal_command(preset, data.get('initial_command'))
    
    if not project_id:
        emit('terminal_error', {'error': 'Project ID is required'})
        return
        
    # 获取项目路径 - 修复路径计算
    # routes.py -> terminal -> api -> app -> backend
    project_path = os.path.join(BACKEND_DIR, 'projects', project_id)
    
    logger.info(f"Calculated backend_dir: {BACKEND_DIR}")
    logger.info(f"Calculated project_path: {project_path}")
    
    # 确保项目目录存在
    if not os.path.exists(project_path):
        logger.warning(f"Project directory does not exist: {project_path}")
        # 如果项目目录不存在，使用backend目录作为默认
        project_path = BACKEND_DIR
    
    try:
        # 创建或复用终端会话
        session = terminal_sessions.get(session_key)
        is_new = False
        if not session:
            extra_env = _build_opencode_env() if preset == "opencode" else {}
            session = TerminalSession(session_key, project_path, keep_alive=keep_alive, extra_env=extra_env)
            session.start()
            terminal_sessions[session_key] = session
            is_new = True
        else:
            session.keep_alive = session.keep_alive or keep_alive
            if session.project_path != project_path:
                logger.warning(
                    f"Terminal session {session_key} reused with different path: "
                    f"{session.project_path} -> {project_path}"
                )
                session.project_path = project_path

        session.add_client(session_id)
        client_sessions[session_id] = session_key
        join_room(session.room)

        emit('terminal_connected', {
            'session_id': session_id,
            'session_key': session_key,
            'project_path': project_path,
            'project_id': project_id,
            'reused': not is_new
        })
        logger.info(f"Terminal connected for session {session_key}, project path: {project_path}")

        buffered_output = session.get_output_buffer()
        if buffered_output:
            emit('terminal_output', {'output': buffered_output})

        if is_new and initial_command:
            session.write(initial_command + "\n")

        if not session.reading:
            session.reading = True
            socketio.start_background_task(read_terminal_output, session_key)

    except Exception as e:
        logger.error(f"Failed to connect terminal: {e}")
        emit('terminal_error', {'error': str(e)})


@socketio.on('terminal_input')
def handle_terminal_input(data):
    """处理终端输入"""
    session_id = request.sid
    session_key = data.get('session_key') or client_sessions.get(session_id) or session_id
    session = terminal_sessions.get(session_key)
    
    if session:
        command = data.get('input', '')
        session.write(command)
    else:
        emit('terminal_error', {'error': 'Terminal session not found'})


@socketio.on('terminal_resize')
def handle_terminal_resize(data):
    """处理终端大小调整"""
    session_id = request.sid
    session_key = data.get('session_key') or client_sessions.get(session_id) or session_id
    session = terminal_sessions.get(session_key)
    
    if session:
        rows = data.get('rows', 24)
        cols = data.get('cols', 80)
        session.resize(rows, cols)


@socketio.on('terminal_disconnect')
def handle_terminal_disconnect(data=None):
    """处理终端断开连接"""
    session_id = request.sid
    session_key = None
    if isinstance(data, dict):
        session_key = data.get('session_key')
    try:
        if session_key:
            leave_room(f"terminal:{session_key}")
    except Exception:
        pass
    _detach_client(session_id, session_key=session_key)
    logger.info(f"Terminal disconnected for session {session_key or session_id}")


@socketio.on('disconnect')
def handle_disconnect():
    """处理客户端断开连接"""
    session_id = request.sid
    _detach_client(session_id)
    logger.info(f"Client disconnected, terminal session {session_id} detached")


def read_terminal_output(session_id):
    """读取终端输出的后台任务"""
    session = terminal_sessions.get(session_id)

    while session and session_id in terminal_sessions:
        try:
            output = session.read()
            if output:
                session.append_output(output)
                socketio.emit('terminal_output', {'output': output}, room=session.room)
            else:
                # 短暂休眠避免CPU占用过高
                socketio.sleep(0.01)
        except Exception as e:
            logger.error(f"Error reading terminal output: {e}")
            break
            
    logger.info(f"Terminal output reader stopped for session {session_id}")


# 注册蓝图
def register_terminal_routes(app):
    app.register_blueprint(terminal_bp, url_prefix='/api/terminal') 
