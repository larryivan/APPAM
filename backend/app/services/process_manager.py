import subprocess
import threading
import queue
import time
from ..database import get_db_connection

# In-memory storage for running processes and task statuses
# In a production app, this would be replaced by a more robust system like Redis or a database.
RUNNING_PROCESSES = {}
TASK_STATUSES = {}

def log_stream(project_id):
    """Continuously yields logs from the queue for a given project_id."""
    # Wait for the log queue to be initialized
    timeout = 10 # seconds
    start_time = time.time()
    log_queue = None
    while log_queue is None and (time.time() - start_time) < timeout:
        log_queue = RUNNING_PROCESSES.get(project_id)
        if log_queue is None:
            time.sleep(0.1) # Wait a bit before retrying

    if not log_queue:
        # 检查是否有历史任务状态，避免重复输出"No running task"消息
        task_status = TASK_STATUSES.get(project_id, {})
        last_status = task_status.get('status', 'not_found')
        
        if last_status == 'not_found':
            yield "[SYSTEM] No task history found for project {}.\n".format(project_id)
        elif last_status in ['completed', 'failed']:
            yield "[SYSTEM] Last task status: {} (Tool: {})\n".format(
                last_status, task_status.get('tool', 'unknown')
            )
        else:
            # 不输出重复的"no running task"消息，直接返回
            pass
        return

    while True:
        try:
            log_entry = log_queue.get(timeout=1) # Wait for 1 second for a log entry
            if log_entry is None: # Sentinel value for end of stream
                break
            yield log_entry
        except queue.Empty:
            # If queue is empty, check if the task is still running
            if TASK_STATUSES.get(project_id, {}).get('status') != 'running':
                break # Task finished, no more logs expected
            time.sleep(0.1) # Small delay before checking again

def get_task_status(project_id):
    """Returns the current status of a task."""
    return TASK_STATUSES.get(project_id, {'status': 'not_found', 'tool': None})

def save_process_history(project_id, tool_name, command, status, start_time, end_time=None, exit_code=None, error_message=None, logs=None):
    """Save process execution history to database."""
    try:
        conn = get_db_connection()
        duration = None
        if start_time and end_time:
            duration = end_time - start_time
        
        conn.execute('''
            INSERT INTO process_history 
            (project_id, tool_name, command, status, start_time, end_time, duration, exit_code, error_message, logs)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            project_id, 
            tool_name, 
            command, 
            status, 
            time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time)) if start_time else None,
            time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time)) if end_time else None,
            duration, 
            exit_code, 
            error_message, 
            logs
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to save process history: {e}")

def get_process_history(project_id, limit=20):
    """Get process execution history for a project."""
    try:
        conn = get_db_connection()
        rows = conn.execute('''
            SELECT * FROM process_history 
            WHERE project_id = ? 
            ORDER BY start_time DESC 
            LIMIT ?
        ''', (project_id, limit)).fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Failed to get process history: {e}")
        return []

def run_process(command, project_id, tool_name):
    """Runs a command in a separate thread and streams its output to a queue."""
    log_queue = queue.Queue()
    RUNNING_PROCESSES[project_id] = log_queue
    start_time = time.time()
    all_logs = []
    
    TASK_STATUSES[project_id] = {'status': 'running', 'tool': tool_name, 'start_time': start_time}

    def target():
        try:
            # 添加开始执行信息
            start_msg = f"[SYSTEM] Starting command: {command}\n"
            log_queue.put(start_msg)
            all_logs.append(start_msg)
            
            # 确保实时输出，禁用缓冲
            import os
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'  # 禁用Python缓冲
            
            # 确保工作目录存在
            work_dir = f'projects/{project_id}'
            if not os.path.exists(work_dir):
                os.makedirs(work_dir, exist_ok=True)
            
            process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,  # 合并stdout和stderr以简化处理
                shell=True, 
                text=True,
                bufsize=1,  # 行缓冲
                universal_newlines=True,
                env=env,
                cwd=work_dir  # 在项目目录执行
            )

            # 实时读取输出，逐行处理
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    log_queue.put(output)
                    all_logs.append(output)
                    # 立即刷新，确保实时性
                    log_queue.task_done() if hasattr(log_queue, 'task_done') else None

            # 等待进程结束
            return_code = process.wait()
            end_time = time.time()

            if return_code == 0:
                TASK_STATUSES[project_id] = {'status': 'completed', 'tool': tool_name}
                completion_msg = f"[SYSTEM] Task '{tool_name}' completed successfully with exit code {return_code}\n"
                log_queue.put(completion_msg)
                all_logs.append(completion_msg)
                
                # Save to history
                save_process_history(
                    project_id, tool_name, command, 'completed', 
                    start_time, end_time, return_code, None, ''.join(all_logs)
                )
            else:
                TASK_STATUSES[project_id] = {'status': 'failed', 'tool': tool_name, 'code': return_code}
                failure_msg = f"[SYSTEM] Task '{tool_name}' failed with exit code {return_code}\n"
                log_queue.put(failure_msg)
                all_logs.append(failure_msg)
                
                # Save to history
                save_process_history(
                    project_id, tool_name, command, 'failed', 
                    start_time, end_time, return_code, None, ''.join(all_logs)
                )

        except Exception as e:
            end_time = time.time()
            error_message = f"[SYSTEM] Exception occurred while running {tool_name}: {str(e)}\n"
            log_queue.put(error_message)
            all_logs.append(error_message)
            TASK_STATUSES[project_id] = {'status': 'failed', 'tool': tool_name, 'error': str(e)}
            
            # Save to history
            save_process_history(
                project_id, tool_name, command, 'failed', 
                start_time, end_time, None, str(e), ''.join(all_logs)
            )
        finally:
            # 关闭管道
            try:
                if hasattr(process, 'stdout') and process.stdout:
                    process.stdout.close()
            except:
                pass
            
            # Signal that the process is finished
            log_queue.put(None)
            if project_id in RUNNING_PROCESSES:
                del RUNNING_PROCESSES[project_id]

    thread = threading.Thread(target=target)
    thread.daemon = True  # 设置为守护线程
    thread.start()