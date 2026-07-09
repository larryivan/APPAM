import os
import logging
import requests
import shutil
import threading
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse, unquote
from concurrent.futures import ThreadPoolExecutor
import ftplib
from ..paths import resolve_project_path as resolve_project_workspace_path
from .url_security import max_remote_download_bytes, safe_request, validate_remote_url
from .download_store import (
    delete_download_task,
    delete_terminal_download_tasks,
    get_download_task,
    list_download_tasks,
    prune_download_history,
    upsert_download_task,
)


logger = logging.getLogger(__name__)

# 全局下载任务存储
download_tasks = {}
download_threads = {}
download_tasks_lock = threading.RLock()


def _configured_limit(name, default, minimum=1):
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except ValueError:
        return default

class DownloadTask:
    def __init__(self, task_id, url, filename, project_id, path, concurrent=True, submitted_by=None):
        self.task_id = task_id
        self.url = url
        self.filename = filename
        self.project_id = project_id
        self.path = path
        self.concurrent = concurrent
        self.submitted_by = submitted_by
        self.status = 'preparing'
        self.progress = 0
        self.downloaded_size = 0
        self.total_size = 0
        self.speed = 0
        self.time_remaining = None
        self.start_time = time.time()
        self.last_update_time = time.time()
        self.last_downloaded_size = 0
        self.error = None
        self.paused = False
        self.cancelled = False
        self.file_path = None
        self.destination_path = None
        self.resume_headers = {}
        self.created_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        self.finished_at = None
        self._last_persist_time = 0.0
        self._deleted = False
        
    def to_dict(self):
        return {
            'task_id': self.task_id,
            'url': self.url,
            'filename': self.filename,
            'status': self.status,
            'progress': self.progress,
            'downloaded_size': self.downloaded_size,
            'total_size': self.total_size,
            'speed': self.speed,
            'time_remaining': self.time_remaining,
            'error': self.error,
            'path': self.path,
            'concurrent': self.concurrent,
            'created_at': self.created_at,
            'finished_at': self.finished_at,
        }

    def to_record(self):
        return {
            'id': self.task_id,
            'project_id': self.project_id,
            'submitted_by': self.submitted_by,
            'url': self.url,
            'filename': self.filename,
            'relative_path': self.path,
            'concurrent': self.concurrent,
            'status': self.status,
            'progress': self.progress,
            'downloaded_size': self.downloaded_size,
            'total_size': self.total_size,
            'speed': self.speed,
            'time_remaining': self.time_remaining,
            'error': self.error,
            'file_path': self.file_path,
            'destination_path': self.destination_path,
            'created_at': self.created_at,
            'finished_at': self.finished_at,
        }

    @classmethod
    def from_record(cls, record):
        task = cls(
            record['id'],
            record['url'],
            record['filename'],
            record['project_id'],
            record.get('relative_path') or '',
            bool(record.get('concurrent')),
            record.get('submitted_by'),
        )
        task.status = record.get('status') or 'error'
        task.progress = float(record.get('progress') or 0)
        task.downloaded_size = int(record.get('downloaded_size') or 0)
        task.total_size = int(record.get('total_size') or 0)
        task.speed = float(record.get('speed') or 0)
        task.time_remaining = record.get('time_remaining')
        task.error = record.get('error')
        task.file_path = record.get('file_path')
        task.destination_path = record.get('destination_path')
        task.created_at = record.get('created_at') or task.created_at
        task.finished_at = record.get('finished_at')
        return task


def _persist_task(task, *, force=False, strict=False):
    if task._deleted:
        return
    now = time.monotonic()
    if not force and now - task._last_persist_time < 1.0:
        return
    if task.status in {'completed', 'error', 'cancelled'} and not task.finished_at:
        task.finished_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    try:
        upsert_download_task(task.to_record())
        task._last_persist_time = now
    except Exception as exc:
        if strict:
            raise
        logger.warning('Could not persist download task %s: %s', task.task_id, exc)


def _remove_partial_file(path_value):
    if not path_value:
        return
    try:
        path = os.path.abspath(path_value)
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        logger.warning('Could not remove stale partial download file: %s', path_value)


def _history_retention_days():
    return _configured_limit('APPAM_DOWNLOAD_HISTORY_DAYS', 30)


def _prune_history():
    try:
        records = prune_download_history(_history_retention_days())
    except Exception as exc:
        logger.warning('Could not prune download history: %s', exc)
        return
    for record in records:
        _remove_partial_file(record.get('file_path'))


def restore_download_tasks():
    """Restore persisted tasks without automatically resuming network transfers."""
    _prune_history()
    try:
        records = list_download_tasks(limit=5000)
    except Exception as exc:
        logger.warning('Could not restore download tasks: %s', exc)
        return 0

    restored = 0
    with download_tasks_lock:
        inactive_ids = [
            task_id for task_id in download_tasks
            if not download_threads.get(task_id) or not download_threads[task_id].is_alive()
        ]
        for task_id in inactive_ids:
            download_tasks.pop(task_id, None)
            download_threads.pop(task_id, None)

        for record in records:
            if record['id'] in download_tasks:
                continue
            task = DownloadTask.from_record(record)
            destination_exists = bool(task.destination_path and os.path.isfile(task.destination_path))
            if destination_exists:
                task.status = 'completed'
                task.progress = 100
                task.downloaded_size = os.path.getsize(task.destination_path)
                task.total_size = task.total_size or task.downloaded_size
                task.error = None
            elif task.status == 'completed':
                task.status = 'error'
                task.error = 'Completed download file is no longer present.'
            elif task.status in {'preparing', 'downloading'}:
                task.status = 'paused'
                task.speed = 0
                task.time_remaining = None
                if task.file_path and os.path.isfile(task.file_path):
                    task.downloaded_size = os.path.getsize(task.file_path)
                    if task.total_size:
                        task.progress = min(100, task.downloaded_size / task.total_size * 100)
                elif task.concurrent:
                    task.downloaded_size = 0
                    task.progress = 0
            download_tasks[task.task_id] = task
            _persist_task(task, force=True)
            restored += 1
    return restored

def get_project_path(project_id, path=''):
    """Get absolute path for project files"""
    return str(resolve_project_workspace_path(project_id, path))

def extract_filename_from_url(url):
    """从URL中提取文件名"""
    try:
        parsed = urlparse(url)
        filename = unquote(os.path.basename(parsed.path))
        if not filename or '.' not in filename:
            # 如果没有找到合适的文件名，生成一个
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"download_{timestamp}"
        return filename
    except:
        return f"download_{int(time.time())}"

def get_ftp_file_info(url):
    """获取FTP文件信息"""
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or 21
        path = parsed.path
        username = parsed.username or 'anonymous'
        password = parsed.password or 'anonymous@'
        
        ftp = ftplib.FTP()
        ftp.connect(host, port, timeout=30)
        ftp.login(username, password)
        
        # 获取文件大小
        file_size = ftp.size(path)
        
        # 获取文件名
        filename = os.path.basename(path)
        
        ftp.quit()
        
        return {
            'supports_resume': True,  # FTP支持断点续传
            'content_length': file_size or 0,
            'content_type': '',
            'filename': filename
        }
    except Exception as e:
        print(f"Error getting FTP info: {e}")
        return {'supports_resume': False, 'content_length': 0, 'content_type': '', 'filename': None}

def get_content_info(url):
    """获取远程文件信息"""
    try:
        parsed = urlparse(url)
        if parsed.scheme.lower() == 'ftp':
            return get_ftp_file_info(url)
        
        # HTTP/HTTPS处理
        with safe_request('HEAD', url, timeout=30) as response:
            response.raise_for_status()
            info = {
                'supports_resume': response.headers.get('accept-ranges', '').lower() == 'bytes',
                'content_length': int(response.headers.get('content-length', 0)),
                'content_type': response.headers.get('content-type', ''),
                'filename': None
            }

            # 尝试从Content-Disposition获取文件名
            content_disposition = response.headers.get('content-disposition', '')
            if 'filename=' in content_disposition:
                filename = content_disposition.split('filename=', 1)[1].strip('"\'')
                info['filename'] = unquote(filename)

            return info
    except Exception as e:
        print(f"Error getting content info: {e}")
        return {'supports_resume': False, 'content_length': 0, 'content_type': '', 'filename': None}

def download_chunk(url, start, end, chunk_file, headers=None, max_retries=3, task=None):
    """下载文件片段 - 增强错误处理和重试机制"""
    if headers is None:
        headers = {}
    
    headers = dict(headers)
    headers['Range'] = f'bytes={start}-{end}'
    headers['User-Agent'] = 'APPAM/1.0'
    expected_size = end - start + 1
    
    for attempt in range(max_retries):
        try:
            with safe_request(
                'GET',
                url,
                headers=headers,
                stream=True,
                timeout=(15, 60),
            ) as response:
                if response.status_code != 206:
                    print(f"Expected HTTP 206 for chunk {start}-{end}, got {response.status_code}")
                    continue
                content_range = response.headers.get('content-range', '')
                if content_range and not content_range.lower().startswith(f'bytes {start}-'):
                    print(f"Invalid Content-Range for chunk {start}-{end}: {content_range}")
                    continue
                downloaded = 0
                with open(chunk_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=32768):
                        if task is not None and (task.cancelled or task.paused):
                            return False
                        if chunk:
                            downloaded += len(chunk)
                            if downloaded > expected_size:
                                raise ValueError(f'Remote server exceeded requested byte range {start}-{end}')
                            f.write(chunk)
                if downloaded != expected_size:
                    print(f"Incomplete chunk {start}-{end}: received {downloaded} of {expected_size} bytes")
                    continue
                return True
                
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed for chunk {start}-{end}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                print(f"Final failure downloading chunk {start}-{end}: {e}")
        except Exception as e:
            print(f"Unexpected error downloading chunk {start}-{end}: {e}")
            break
    
    return False

def merge_chunks(chunk_files, output_file):
    """合并文件片段"""
    merge_path = f'{output_file}.merging-{uuid.uuid4().hex}'
    try:
        with open(merge_path, 'wb') as outfile:
            for chunk_file in chunk_files:
                if not os.path.exists(chunk_file):
                    raise FileNotFoundError(f'Missing download chunk: {chunk_file}')
                with open(chunk_file, 'rb') as infile:
                    shutil.copyfileobj(infile, outfile, length=1024 * 1024)
            outfile.flush()
            os.fsync(outfile.fileno())
        os.replace(merge_path, output_file)
        for chunk_file in chunk_files:
            os.remove(chunk_file)
        return True
    except Exception as e:
        print(f"Error merging chunks: {e}")
        return False
    finally:
        if os.path.exists(merge_path):
            os.remove(merge_path)

def single_thread_download(task):
    """单线程下载"""
    try:
        headers = task.resume_headers.copy()
        
        # 检查是否支持断点续传
        if task.downloaded_size > 0:
            headers['Range'] = f'bytes={task.downloaded_size}-'
        
        with safe_request('GET', task.url, headers=headers, stream=True, timeout=(15, 60)) as response:
            if response.status_code not in [200, 206]:
                task.status = 'error'
                task.error = f"HTTP error: {response.status_code}"
                return

            if task.downloaded_size > 0 and response.status_code == 206:
                content_range = response.headers.get('content-range', '').lower()
                if not content_range.startswith(f'bytes {task.downloaded_size}-'):
                    raise ValueError('Remote server returned an invalid resume range')

            # 获取总大小
            if task.total_size == 0:
                content_length = response.headers.get('content-length')
                if content_length:
                    if response.status_code == 206:
                        task.total_size = task.downloaded_size + int(content_length)
                    else:
                        task.total_size = int(content_length)
            limit = max_remote_download_bytes()
            if task.total_size > limit or task.downloaded_size > limit:
                raise ValueError(f'Remote file exceeds configured size limit ({limit} bytes)')

            # 打开文件进行写入
            mode = 'ab' if task.downloaded_size > 0 and response.status_code == 206 else 'wb'
            if mode == 'wb':
                task.downloaded_size = 0
            with open(task.file_path, mode) as f:
                chunk_size = 8192
                last_update = time.time()

                for chunk in response.iter_content(chunk_size=chunk_size):
                    if task.cancelled:
                        task.status = 'cancelled'
                        return

                    if task.paused:
                        task.status = 'paused'
                        return

                    if chunk:
                        task.downloaded_size += len(chunk)
                        if task.downloaded_size > limit:
                            raise ValueError(f'Remote file exceeds configured size limit ({limit} bytes)')
                        f.write(chunk)

                        current_time = time.time()
                        if current_time - last_update >= 1.0:
                            elapsed = current_time - task.last_update_time
                            if elapsed > 0:
                                bytes_per_second = (task.downloaded_size - task.last_downloaded_size) / elapsed
                                task.speed = bytes_per_second

                                if task.total_size > 0 and bytes_per_second > 0:
                                    remaining_bytes = task.total_size - task.downloaded_size
                                    task.time_remaining = remaining_bytes / bytes_per_second

                            if task.total_size > 0:
                                task.progress = (task.downloaded_size / task.total_size) * 100

                            task.last_update_time = current_time
                            task.last_downloaded_size = task.downloaded_size
                            last_update = current_time
                            _persist_task(task)
                f.flush()
                os.fsync(f.fileno())
        
        task.status = 'completed'
        task.progress = 100
        
    except Exception as e:
        task.status = 'error'
        task.error = str(e)

def multi_thread_download(task, num_threads=8):
    """多线程下载 - 优化大文件下载"""
    try:
        # 获取文件信息
        info = get_content_info(task.url)
        if not info['supports_resume'] or info['content_length'] == 0:
            # 不支持断点续传，使用单线程
            return single_thread_download(task)
        
        task.total_size = info['content_length']
        limit = max_remote_download_bytes()
        if task.total_size > limit:
            raise ValueError(f'Remote file exceeds configured size limit ({limit} bytes)')

        # 为大文件动态调整线程数
        max_download_threads = _configured_limit('APPAM_MAX_DOWNLOAD_THREADS', 8)
        num_threads = min(num_threads, max_download_threads)

        minimum_chunk_size = 1024 * 1024
        num_threads = max(1, min(num_threads, (task.total_size + minimum_chunk_size - 1) // minimum_chunk_size))
        chunk_size = (task.total_size + num_threads - 1) // num_threads
        
        # 创建临时目录
        temp_dir = os.path.join(
            os.path.dirname(task.file_path),
            f'.tmp_{task.task_id}_{uuid.uuid4().hex}',
        )
        os.makedirs(temp_dir, exist_ok=True)
        
        # 创建下载任务
        chunk_files = []
        download_futures = []
        
        # 限制并发数以避免过度消耗资源
        max_workers = min(num_threads, (os.cpu_count() or 1) * 2)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for i in range(num_threads):
                start = i * chunk_size
                end = start + chunk_size - 1 if i < num_threads - 1 else task.total_size - 1
                
                chunk_file = os.path.join(temp_dir, f'chunk_{i}')
                chunk_files.append(chunk_file)
                
                future = executor.submit(download_chunk, task.url, start, end, chunk_file, None, 3, task)
                download_futures.append(future)
            
            # 监控下载进度
            while not all(future.done() for future in download_futures):
                if task.cancelled:
                    # 取消所有下载
                    for future in download_futures:
                        future.cancel()
                    task.status = 'cancelled'
                    return
                
                if task.paused:
                    task.status = 'paused'
                    return
                
                # 计算总下载大小
                total_downloaded = 0
                for chunk_file in chunk_files:
                    if os.path.exists(chunk_file):
                        total_downloaded += os.path.getsize(chunk_file)
                
                task.downloaded_size = total_downloaded
                if task.total_size > 0:
                    task.progress = (task.downloaded_size / task.total_size) * 100
                
                # 计算速度
                current_time = time.time()
                elapsed = current_time - task.last_update_time
                if elapsed >= 1.0:
                    bytes_per_second = (task.downloaded_size - task.last_downloaded_size) / elapsed
                    task.speed = bytes_per_second
                    
                    if task.total_size > 0 and bytes_per_second > 0:
                        remaining_bytes = task.total_size - task.downloaded_size
                        task.time_remaining = remaining_bytes / bytes_per_second
                    
                    task.last_update_time = current_time
                    task.last_downloaded_size = task.downloaded_size
                    _persist_task(task)
                
                time.sleep(0.5)
            
            if task.cancelled:
                task.status = 'cancelled'
            elif task.paused:
                task.status = 'paused'
            elif all(future.result() for future in download_futures):
                # 合并文件片段
                if merge_chunks(chunk_files, task.file_path):
                    task.status = 'completed'
                    task.progress = 100
                else:
                    task.status = 'error'
                    task.error = 'Failed to merge file chunks'
            else:
                task.status = 'error'
                task.error = 'Some file chunks failed to download'
        
    except Exception as e:
        task.status = 'error'
        task.error = str(e)
    finally:
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)

def download_worker(task):
    """下载工作线程"""
    try:
        task.status = 'downloading'
        task.finished_at = None
        _persist_task(task, force=True)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(task.file_path), exist_ok=True)
        
        # 检查协议类型
        parsed = urlparse(task.url)
        if parsed.scheme.lower() == 'ftp':
            # FTP下载（目前只支持单线程）
            single_thread_ftp_download(task)
        else:
            # HTTP/HTTPS下载
            if task.concurrent:
                multi_thread_download(task)
            else:
                single_thread_download(task)

        if task.status == 'completed':
            if task.cancelled:
                task.status = 'cancelled'
            elif not task.file_path or not os.path.isfile(task.file_path):
                raise FileNotFoundError('Downloaded temporary file is missing')
            else:
                actual_size = os.path.getsize(task.file_path)
                if task.total_size and actual_size != task.total_size:
                    raise ValueError(
                        f'Downloaded file size mismatch: expected {task.total_size}, received {actual_size}'
                    )
                os.replace(task.file_path, task.destination_path)
            
    except Exception as e:
        task.status = 'error'
        task.error = str(e)
    finally:
        _persist_task(task, force=True)
        # 清理下载线程记录
        with download_tasks_lock:
            download_threads.pop(task.task_id, None)

def single_thread_ftp_download(task):
    """单线程FTP下载"""
    try:
        parsed = urlparse(task.url)
        host = parsed.hostname
        port = parsed.port or 21
        path = parsed.path
        username = parsed.username or 'anonymous'
        password = parsed.password or 'anonymous@'
        
        ftp = ftplib.FTP()
        ftp.connect(host, port, timeout=60)
        ftp.login(username, password)
        ftp.set_pasv(True)
        
        # 获取文件大小
        if task.total_size == 0:
            try:
                task.total_size = ftp.size(path)
            except:
                pass
        limit = max_remote_download_bytes()
        if task.total_size and task.total_size > limit:
            raise ValueError(f'Remote file exceeds configured size limit ({limit} bytes)')
        
        # 打开文件进行写入
        mode = 'ab' if task.downloaded_size > 0 else 'wb'
        
        with open(task.file_path, mode) as f:
            last_update = time.time()
            
            def callback(data):
                nonlocal last_update
                
                if task.cancelled:
                    raise Exception("Download cancelled")
                if task.paused:
                    raise Exception("Download paused")
                
                f.write(data)
                task.downloaded_size += len(data)
                if task.downloaded_size > limit:
                    raise ValueError(f'Remote file exceeds configured size limit ({limit} bytes)')
                
                # 更新进度
                current_time = time.time()
                if current_time - last_update >= 1.0:
                    elapsed = current_time - task.last_update_time
                    if elapsed > 0:
                        bytes_per_second = (task.downloaded_size - task.last_downloaded_size) / elapsed
                        task.speed = bytes_per_second
                        
                        if task.total_size > 0 and bytes_per_second > 0:
                            remaining_bytes = task.total_size - task.downloaded_size
                            task.time_remaining = remaining_bytes / bytes_per_second
                    
                    if task.total_size > 0:
                        task.progress = (task.downloaded_size / task.total_size) * 100
                    
                    task.last_update_time = current_time
                    task.last_downloaded_size = task.downloaded_size
                    last_update = current_time
                    _persist_task(task)
            
            # ftplib must pass the REST offset to RETR; sending REST separately can
            # cause some servers to restart from byte zero and corrupt an append.
            rest = task.downloaded_size if task.downloaded_size > 0 else None
            try:
                ftp.retrbinary(f'RETR {path}', callback, rest=rest)
            except ftplib.error_perm:
                if rest is None:
                    raise
                task.downloaded_size = 0
                f.seek(0)
                f.truncate()
                ftp.retrbinary(f'RETR {path}', callback)

            f.flush()
            os.fsync(f.fileno())
        
        ftp.quit()
        task.status = 'completed'
        task.progress = 100
        
    except Exception as e:
        if "cancelled" in str(e):
            task.status = 'cancelled'
        elif "paused" in str(e):
            task.status = 'paused'
        else:
            task.status = 'error'
            task.error = str(e)
        
        # 确保关闭FTP连接
        try:
            ftp.quit()
        except:
            pass

def start_download(project_id, url, filename, path, concurrent=True, submitted_by=None):
    """开始下载任务"""
    url = validate_remote_url(url)
    info = get_content_info(url)
    content_length = int(info.get('content_length') or 0)
    limit = max_remote_download_bytes()
    if content_length > limit:
        raise ValueError(f'Remote file exceeds configured size limit ({limit} bytes)')

    # 如果没有提供文件名，从URL提取
    if not filename:
        filename = info.get('filename') or extract_filename_from_url(url)
    raw_filename = str(filename or '').strip()
    filename = os.path.basename(raw_filename)
    if (
        not filename
        or filename in {'.', '..'}
        or filename != raw_filename
        or '\\' in filename
        or '\x00' in filename
        or len(filename.encode('utf-8')) > 255
    ):
        raise ValueError('A valid output filename is required')
    
    # 构建文件保存路径
    save_dir = get_project_path(project_id, path)
    destination_path = os.path.join(save_dir, filename)
    
    # 创建下载任务
    with download_tasks_lock:
        active_tasks = [
            task for task in download_tasks.values()
            if task.status not in {'completed', 'error', 'cancelled'}
        ]
        max_global = _configured_limit('APPAM_MAX_GLOBAL_DOWNLOADS', 8)
        max_project = _configured_limit('APPAM_MAX_PROJECT_DOWNLOADS', 2)
        if len(active_tasks) >= max_global:
            raise ValueError(f'Global active download limit reached ({max_global})')
        if sum(task.project_id == project_id for task in active_tasks) >= max_project:
            raise ValueError(f'Project active download limit reached ({max_project})')
        if any(task.destination_path == destination_path for task in active_tasks):
            raise ValueError('A download to this destination is already active')
        if os.path.exists(destination_path):
            raise ValueError('The destination file already exists')

        task_id = str(uuid.uuid4())
        task = DownloadTask(task_id, url, filename, project_id, path, concurrent, submitted_by=submitted_by)
        task.destination_path = destination_path
        task.file_path = f'{destination_path}.appam-part-{task_id}'
        task.total_size = content_length
        _persist_task(task, force=True, strict=True)
        download_tasks[task_id] = task

        thread = threading.Thread(target=download_worker, args=(task,), daemon=True)
        download_threads[task_id] = thread
        thread.start()
    
    return task_id

def pause_download(task_id, project_id=None):
    """暂停下载"""
    with download_tasks_lock:
        task = download_tasks.get(task_id)
        if task and (not project_id or task.project_id == project_id):
            task.paused = True
            task.status = 'paused'
            task.speed = 0
            task.time_remaining = None
            _persist_task(task, force=True)
            return True
    return False

def resume_download(task_id, project_id=None):
    """继续下载"""
    with download_tasks_lock:
        task = download_tasks.get(task_id)
        if (
            task
            and (not project_id or task.project_id == project_id)
            and task.status == 'paused'
        ):
            existing_thread = download_threads.get(task_id)
            if existing_thread and existing_thread.is_alive():
                return False
            task.paused = False
            task.status = 'preparing'
            task.error = None
            task.finished_at = None
            _persist_task(task, force=True)
            thread = threading.Thread(target=download_worker, args=(task,), daemon=True)
            download_threads[task_id] = thread
            thread.start()
            return True
    return False

def cancel_download(task_id, project_id=None):
    """取消下载"""
    with download_tasks_lock:
        task = download_tasks.get(task_id)
        if not task or (project_id and task.project_id != project_id):
            return False
        task.cancelled = True
        task.status = 'cancelled'
        task._deleted = True
        
        # 删除部分下载的文件
        if task.file_path and os.path.exists(task.file_path):
            try:
                os.remove(task.file_path)
            except:
                pass
        
        # 清理任务记录
        download_tasks.pop(task_id, None)
        download_threads.pop(task_id, None)
        delete_download_task(task_id, project_id=task.project_id)
        
        return True

def get_download_progress(task_id, project_id=None):
    """获取下载进度"""
    with download_tasks_lock:
        task = download_tasks.get(task_id)
        if task and (not project_id or task.project_id == project_id):
            return task.to_dict()
    record = get_download_task(task_id, project_id=project_id)
    return DownloadTask.from_record(record).to_dict() if record else None

def get_all_downloads(project_id=None):
    """获取所有下载任务"""
    _prune_history()
    with download_tasks_lock:
        if project_id:
            return [task.to_dict() for task in download_tasks.values() if task.project_id == project_id]
        return [task.to_dict() for task in download_tasks.values()]

def cleanup_completed_downloads(project_id=None):
    """清理已完成的下载任务"""
    persisted = delete_terminal_download_tasks(project_id=project_id)
    persisted_ids = {record['id'] for record in persisted}
    for record in persisted:
        _remove_partial_file(record.get('file_path'))
    with download_tasks_lock:
        completed_tasks = [task_id for task_id, task in download_tasks.items()
                          if task.status in ['completed', 'error', 'cancelled']
                          and (not project_id or task.project_id == project_id)]

        for task_id in completed_tasks:
            task = download_tasks.get(task_id)
            if task and task.file_path and os.path.exists(task.file_path):
                try:
                    os.remove(task.file_path)
                except OSError:
                    pass
            download_tasks.pop(task_id, None)
            download_threads.pop(task_id, None)

        return len(persisted_ids | set(completed_tasks))
