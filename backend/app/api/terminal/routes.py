import os
import pty
import select
import subprocess
import struct
import fcntl
import termios
import json
import asyncio
from flask import Blueprint, request
from flask_socketio import emit, disconnect
from app import socketio
import logging

terminal_bp = Blueprint('terminal', __name__)
logger = logging.getLogger(__name__)

# 存储终端会话
terminal_sessions = {}

class TerminalSession:
    def __init__(self, session_id, project_path):
        self.session_id = session_id
        self.project_path = project_path
        self.process = None
        self.fd = None
        self.pid = None
        
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
                logger.info(f"Terminal session {self.session_id} started with PID {self.pid}")
                
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
        logger.info(f"Terminal session {self.session_id} closed")


@socketio.on('terminal_connect')
def handle_terminal_connect(data):
    """处理终端连接请求"""
    session_id = request.sid
    project_id = data.get('project_id')
    
    if not project_id:
        emit('terminal_error', {'error': 'Project ID is required'})
        return
        
    # 获取项目路径 - 修复路径计算
    # routes.py -> terminal -> api -> app -> backend
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    project_path = os.path.join(backend_dir, 'projects', project_id)
    
    logger.info(f"Calculated backend_dir: {backend_dir}")
    logger.info(f"Calculated project_path: {project_path}")
    
    # 确保项目目录存在
    if not os.path.exists(project_path):
        logger.warning(f"Project directory does not exist: {project_path}")
        # 如果项目目录不存在，使用backend目录作为默认
        project_path = backend_dir
    
    try:
        # 创建终端会话
        session = TerminalSession(session_id, project_path)
        session.start()
        terminal_sessions[session_id] = session
        
        emit('terminal_connected', {
            'session_id': session_id, 
            'project_path': project_path,
            'project_id': project_id
        })
        logger.info(f"Terminal connected for session {session_id}, project path: {project_path}")
        
        # 启动读取循环
        socketio.start_background_task(read_terminal_output, session_id)
        
    except Exception as e:
        logger.error(f"Failed to connect terminal: {e}")
        emit('terminal_error', {'error': str(e)})


@socketio.on('terminal_input')
def handle_terminal_input(data):
    """处理终端输入"""
    session_id = request.sid
    session = terminal_sessions.get(session_id)
    
    if session:
        command = data.get('input', '')
        session.write(command)
    else:
        emit('terminal_error', {'error': 'Terminal session not found'})


@socketio.on('terminal_resize')
def handle_terminal_resize(data):
    """处理终端大小调整"""
    session_id = request.sid
    session = terminal_sessions.get(session_id)
    
    if session:
        rows = data.get('rows', 24)
        cols = data.get('cols', 80)
        session.resize(rows, cols)


@socketio.on('terminal_disconnect')
def handle_terminal_disconnect():
    """处理终端断开连接"""
    session_id = request.sid
    session = terminal_sessions.pop(session_id, None)
    
    if session:
        session.close()
        logger.info(f"Terminal disconnected for session {session_id}")


@socketio.on('disconnect')
def handle_disconnect():
    """处理客户端断开连接"""
    session_id = request.sid
    session = terminal_sessions.pop(session_id, None)
    
    if session:
        session.close()
        logger.info(f"Client disconnected, terminal session {session_id} closed")


def read_terminal_output(session_id):
    """读取终端输出的后台任务"""
    session = terminal_sessions.get(session_id)
    
    while session and session_id in terminal_sessions:
        try:
            output = session.read()
            if output:
                socketio.emit('terminal_output', {'output': output}, room=session_id)
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