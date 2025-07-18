import os
import requests
import threading
import time
import uuid
from datetime import datetime
from urllib.parse import urlparse, unquote
from concurrent.futures import ThreadPoolExecutor
import json
import ftplib
import socket
from ..database import get_db_connection

# 全局下载任务存储
download_tasks = {}
download_threads = {}

class DownloadTask:
    def __init__(self, task_id, url, filename, project_id, path, concurrent=True):
        self.task_id = task_id
        self.url = url
        self.filename = filename
        self.project_id = project_id
        self.path = path
        self.concurrent = concurrent
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
        self.resume_headers = {}
        
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
            'error': self.error
        }

def get_project_path(project_id, path=''):
    """Get absolute path for project files"""
    base_path = os.path.join('./projects', project_id)
    if path and path != '/':
        return os.path.join(base_path, path.lstrip('/'))
    return base_path

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
        response = requests.head(url, allow_redirects=True, timeout=30)
        
        info = {
            'supports_resume': 'accept-ranges' in response.headers and response.headers.get('accept-ranges') == 'bytes',
            'content_length': int(response.headers.get('content-length', 0)),
            'content_type': response.headers.get('content-type', ''),
            'filename': None
        }
        
        # 尝试从Content-Disposition获取文件名
        content_disposition = response.headers.get('content-disposition', '')
        if 'filename=' in content_disposition:
            filename = content_disposition.split('filename=')[1].strip('"\'')
            info['filename'] = unquote(filename)
        
        return info
    except Exception as e:
        print(f"Error getting content info: {e}")
        return {'supports_resume': False, 'content_length': 0, 'content_type': '', 'filename': None}

def download_chunk(url, start, end, chunk_file, headers=None, max_retries=3):
    """下载文件片段 - 增强错误处理和重试机制"""
    if headers is None:
        headers = {}
    
    headers['Range'] = f'bytes={start}-{end}'
    headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    headers['Connection'] = 'keep-alive'
    
    for attempt in range(max_retries):
        try:
            response = requests.get(
                url, 
                headers=headers, 
                stream=True, 
                timeout=60,  # 增加超时时间
                allow_redirects=True
            )
            
            if response.status_code in [206, 200]:  # 206 Partial Content, 200 OK
                with open(chunk_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=32768):  # 增大块大小
                        if chunk:
                            f.write(chunk)
                return True
            else:
                print(f"HTTP {response.status_code} for chunk {start}-{end}")
                
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
    try:
        with open(output_file, 'wb') as outfile:
            for chunk_file in chunk_files:
                if os.path.exists(chunk_file):
                    with open(chunk_file, 'rb') as infile:
                        outfile.write(infile.read())
                    os.remove(chunk_file)  # 删除临时片段文件
        return True
    except Exception as e:
        print(f"Error merging chunks: {e}")
        return False

def single_thread_download(task):
    """单线程下载"""
    try:
        headers = task.resume_headers.copy()
        
        # 检查是否支持断点续传
        if task.downloaded_size > 0:
            headers['Range'] = f'bytes={task.downloaded_size}-'
        
        response = requests.get(task.url, headers=headers, stream=True, timeout=30)
        
        if response.status_code not in [200, 206]:
            task.status = 'error'
            task.error = f"HTTP error: {response.status_code}"
            return
        
        # 获取总大小
        if task.total_size == 0:
            content_length = response.headers.get('content-length')
            if content_length:
                if response.status_code == 206:
                    # 部分内容响应
                    task.total_size = task.downloaded_size + int(content_length)
                else:
                    task.total_size = int(content_length)
        
        # 打开文件进行写入
        mode = 'ab' if task.downloaded_size > 0 else 'wb'
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
                    f.write(chunk)
                    task.downloaded_size += len(chunk)
                    
                    # 更新进度和速度
                    current_time = time.time()
                    if current_time - last_update >= 1.0:  # 每秒更新一次
                        elapsed = current_time - task.last_update_time
                        if elapsed > 0:
                            bytes_per_second = (task.downloaded_size - task.last_downloaded_size) / elapsed
                            task.speed = bytes_per_second
                            
                            # 计算剩余时间
                            if task.total_size > 0 and bytes_per_second > 0:
                                remaining_bytes = task.total_size - task.downloaded_size
                                task.time_remaining = remaining_bytes / bytes_per_second
                        
                        # 计算进度
                        if task.total_size > 0:
                            task.progress = (task.downloaded_size / task.total_size) * 100
                        
                        task.last_update_time = current_time
                        task.last_downloaded_size = task.downloaded_size
                        last_update = current_time
        
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
        
        # 为大文件动态调整线程数
        if task.total_size > 100 * 1024 * 1024:  # 100MB+
            num_threads = min(16, num_threads * 2)
        elif task.total_size > 1024 * 1024 * 1024:  # 1GB+
            num_threads = min(32, num_threads * 4)
        
        chunk_size = max(1024 * 1024, task.total_size // num_threads)  # 最小1MB块
        
        # 创建临时目录
        temp_dir = os.path.join(os.path.dirname(task.file_path), f'.tmp_{task.task_id}')
        os.makedirs(temp_dir, exist_ok=True)
        
        # 创建下载任务
        chunk_files = []
        download_futures = []
        
        # 限制并发数以避免过度消耗资源
        max_workers = min(num_threads, os.cpu_count() * 2)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for i in range(num_threads):
                start = i * chunk_size
                end = start + chunk_size - 1 if i < num_threads - 1 else task.total_size - 1
                
                chunk_file = os.path.join(temp_dir, f'chunk_{i}')
                chunk_files.append(chunk_file)
                
                future = executor.submit(download_chunk, task.url, start, end, chunk_file)
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
                
                time.sleep(0.5)
            
            # 检查所有下载是否成功
            if all(future.result() for future in download_futures):
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
        
        # 清理临时目录
        try:
            os.rmdir(temp_dir)
        except:
            pass
            
    except Exception as e:
        task.status = 'error'
        task.error = str(e)

def download_worker(task):
    """下载工作线程"""
    try:
        task.status = 'downloading'
        
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
            
    except Exception as e:
        task.status = 'error'
        task.error = str(e)
    finally:
        # 清理下载线程记录
        if task.task_id in download_threads:
            del download_threads[task.task_id]

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
            
            # 支持断点续传
            if task.downloaded_size > 0:
                try:
                    ftp.voidcmd(f'REST {task.downloaded_size}')
                except:
                    # 如果不支持断点续传，重新开始
                    task.downloaded_size = 0
                    f.seek(0)
                    f.truncate()
            
            ftp.retrbinary(f'RETR {path}', callback)
        
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

def start_download(project_id, url, filename, path, concurrent=True, task_id=None):
    """开始下载任务"""
    if not task_id:
        task_id = str(uuid.uuid4())
    
    # 如果没有提供文件名，从URL提取
    if not filename:
        info = get_content_info(url)
        filename = info.get('filename') or extract_filename_from_url(url)
    
    # 构建文件保存路径
    save_dir = get_project_path(project_id, path)
    file_path = os.path.join(save_dir, filename)
    
    # 创建下载任务
    task = DownloadTask(task_id, url, filename, project_id, path, concurrent)
    task.file_path = file_path
    
    # 检查文件是否已存在，如果存在则支持断点续传
    if os.path.exists(file_path):
        task.downloaded_size = os.path.getsize(file_path)
    
    download_tasks[task_id] = task
    
    # 启动下载线程
    thread = threading.Thread(target=download_worker, args=(task,))
    thread.daemon = True
    thread.start()
    
    download_threads[task_id] = thread
    
    return task_id

def pause_download(task_id):
    """暂停下载"""
    if task_id in download_tasks:
        task = download_tasks[task_id]
        task.paused = True
        return True
    return False

def resume_download(task_id):
    """继续下载"""
    if task_id in download_tasks:
        task = download_tasks[task_id]
        if task.status == 'paused':
            task.paused = False
            
            # 重新启动下载线程
            thread = threading.Thread(target=download_worker, args=(task,))
            thread.daemon = True
            thread.start()
            
            download_threads[task_id] = thread
            return True
    return False

def cancel_download(task_id):
    """取消下载"""
    if task_id in download_tasks:
        task = download_tasks[task_id]
        task.cancelled = True
        task.status = 'cancelled'
        
        # 删除部分下载的文件
        if task.file_path and os.path.exists(task.file_path):
            try:
                os.remove(task.file_path)
            except:
                pass
        
        # 清理任务记录
        del download_tasks[task_id]
        if task_id in download_threads:
            del download_threads[task_id]
        
        return True
    return False

def get_download_progress(task_id):
    """获取下载进度"""
    if task_id in download_tasks:
        return download_tasks[task_id].to_dict()
    return None

def get_all_downloads(project_id=None):
    """获取所有下载任务"""
    if project_id:
        return [task.to_dict() for task in download_tasks.values() if task.project_id == project_id]
    return [task.to_dict() for task in download_tasks.values()]

def cleanup_completed_downloads():
    """清理已完成的下载任务"""
    completed_tasks = [task_id for task_id, task in download_tasks.items() 
                      if task.status in ['completed', 'error', 'cancelled']]
    
    for task_id in completed_tasks:
        if task_id in download_tasks:
            del download_tasks[task_id]
        if task_id in download_threads:
            del download_threads[task_id]
    
    return len(completed_tasks) 