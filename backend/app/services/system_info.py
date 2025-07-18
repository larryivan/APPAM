import psutil
import platform
import shutil
import subprocess
import json
import os
from datetime import datetime
import threading
import time


class SystemInfoService:
    """系统信息服务"""
    
    def __init__(self):
        self._cache = {}
        self._cache_timeout = 5  # 5秒缓存
        self._last_update = {}
    
    def _get_cached_or_update(self, key, update_func):
        """获取缓存数据或更新缓存"""
        now = time.time()
        if key not in self._cache or now - self._last_update.get(key, 0) > self._cache_timeout:
            try:
                self._cache[key] = update_func()
                self._last_update[key] = now
            except Exception as e:
                print(f"Error updating {key}: {e}")
                if key not in self._cache:
                    self._cache[key] = None
        return self._cache[key]
    
    def get_cpu_info(self):
        """获取CPU信息"""
        def _get_cpu_info():
            cpu_count = psutil.cpu_count()
            cpu_count_logical = psutil.cpu_count(logical=True)
            cpu_percent = psutil.cpu_percent(interval=1, percpu=False)
            cpu_freq = psutil.cpu_freq()
            
            # 获取CPU温度（如果可用）
            cpu_temp = None
            try:
                if hasattr(psutil, "sensors_temperatures"):
                    temps = psutil.sensors_temperatures()
                    if temps:
                        for name, entries in temps.items():
                            if 'cpu' in name.lower() or 'core' in name.lower():
                                cpu_temp = entries[0].current if entries else None
                                break
            except:
                pass
            
            return {
                'physical_cores': cpu_count,
                'logical_cores': cpu_count_logical,
                'usage_percent': cpu_percent,
                'frequency': {
                    'current': cpu_freq.current if cpu_freq else None,
                    'min': cpu_freq.min if cpu_freq else None,
                    'max': cpu_freq.max if cpu_freq else None
                },
                'temperature': cpu_temp,
                'architecture': platform.machine(),
                'processor': platform.processor()
            }
        
        return self._get_cached_or_update('cpu', _get_cpu_info)
    
    def get_memory_info(self):
        """获取内存信息"""
        def _get_memory_info():
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                'total': memory.total,
                'available': memory.available,
                'used': memory.used,
                'free': memory.free,
                'usage_percent': memory.percent,
                'swap': {
                    'total': swap.total,
                    'used': swap.used,
                    'free': swap.free,
                    'usage_percent': swap.percent
                }
            }
        
        return self._get_cached_or_update('memory', _get_memory_info)
    
    def get_disk_info(self):
        """获取磁盘信息"""
        def _get_disk_info():
            disks = []
            for partition in psutil.disk_partitions():
                try:
                    partition_usage = psutil.disk_usage(partition.mountpoint)
                    disks.append({
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'file_system': partition.fstype,
                        'total': partition_usage.total,
                        'used': partition_usage.used,
                        'free': partition_usage.free,
                        'usage_percent': (partition_usage.used / partition_usage.total) * 100 if partition_usage.total > 0 else 0
                    })
                except PermissionError:
                    continue
            
            return disks
        
        return self._get_cached_or_update('disk', _get_disk_info)
    
    def get_system_load(self):
        """获取系统负载"""
        def _get_system_load():
            try:
                # Unix/Linux系统
                load_avg = os.getloadavg()
                return {
                    'load_1min': load_avg[0],
                    'load_5min': load_avg[1],
                    'load_15min': load_avg[2],
                    'cpu_count': psutil.cpu_count()
                }
            except (OSError, AttributeError):
                # Windows系统使用CPU使用率代替
                return {
                    'load_1min': psutil.cpu_percent(interval=1),
                    'load_5min': None,
                    'load_15min': None,
                    'cpu_count': psutil.cpu_count()
                }
        
        return self._get_cached_or_update('load', _get_system_load)
    
    def get_network_info(self):
        """获取网络信息"""
        def _get_network_info():
            network_io = psutil.net_io_counters()
            network_connections = len(psutil.net_connections())
            
            return {
                'bytes_sent': network_io.bytes_sent,
                'bytes_received': network_io.bytes_recv,
                'packets_sent': network_io.packets_sent,
                'packets_received': network_io.packets_recv,
                'active_connections': network_connections
            }
        
        return self._get_cached_or_update('network', _get_network_info)
    
    def get_process_info(self, limit=10):
        """获取进程信息"""
        def _get_process_info():
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info']):
                try:
                    pinfo = proc.info
                    if pinfo['cpu_percent'] is not None and pinfo['cpu_percent'] > 0.1:  # 只显示有CPU使用的进程
                        processes.append({
                            'pid': pinfo['pid'],
                            'name': pinfo['name'],
                            'cpu_percent': pinfo['cpu_percent'],
                            'memory_percent': pinfo['memory_percent'],
                            'memory_mb': pinfo['memory_info'].rss / 1024 / 1024 if pinfo['memory_info'] else 0
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # 按CPU使用率排序
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            return processes[:limit]
        
        return self._get_cached_or_update('processes', _get_process_info)
    
    def get_gpu_info(self):
        """获取GPU信息"""
        def _get_gpu_info():
            gpu_info = []
            try:
                # 尝试使用nvidia-smi获取NVIDIA GPU信息
                result = subprocess.run(['nvidia-smi', '--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu', '--format=csv,noheader,nounits'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if line.strip():
                            parts = [p.strip() for p in line.split(',')]
                            if len(parts) >= 7:
                                gpu_info.append({
                                    'index': int(parts[0]),
                                    'name': parts[1],
                                    'memory_total_mb': int(parts[2]),
                                    'memory_used_mb': int(parts[3]),
                                    'memory_free_mb': int(parts[4]),
                                    'utilization_percent': int(parts[5]),
                                    'temperature': int(parts[6]) if parts[6] != '[Not Supported]' else None
                                })
            except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
                pass
            
            return gpu_info
        
        return self._get_cached_or_update('gpu', _get_gpu_info)
    
    def get_bioinformatics_recommendations(self):
        """获取生物信息学分析建议"""
        cpu_info = self.get_cpu_info()
        memory_info = self.get_memory_info()
        disk_info = self.get_disk_info()
        load_info = self.get_system_load()
        
        recommendations = {
            'threading': {
                'max_threads': cpu_info['logical_cores'],
                'recommended_threads': max(1, int(cpu_info['logical_cores'] * 0.8)),  # 使用80%的核心
                'current_load': cpu_info['usage_percent']
            },
            'memory': {
                'total_gb': round(memory_info['total'] / (1024**3), 2),
                'available_gb': round(memory_info['available'] / (1024**3), 2),
                'recommended_max_memory_gb': round(memory_info['available'] * 0.8 / (1024**3), 2),  # 使用80%的可用内存
                'usage_percent': memory_info['usage_percent']
            },
            'storage': {
                'available_space_gb': round(sum(d['free'] for d in disk_info) / (1024**3), 2),
                'recommended_temp_space_gb': round(sum(d['free'] for d in disk_info) * 0.5 / (1024**3), 2)  # 为临时文件预留50%空间
            },
            'system_status': {
                'cpu_load': load_info.get('load_1min'),
                'memory_pressure': 'high' if memory_info['usage_percent'] > 80 else 'medium' if memory_info['usage_percent'] > 60 else 'low',
                'disk_pressure': 'high' if any(d['usage_percent'] > 90 for d in disk_info) else 'medium' if any(d['usage_percent'] > 70 for d in disk_info) else 'low'
            }
        }
        
        return recommendations
    
    def get_full_system_info(self):
        """获取完整的系统信息"""
        return {
            'timestamp': datetime.now().isoformat(),
            'platform': {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor()
            },
            'cpu': self.get_cpu_info(),
            'memory': self.get_memory_info(),
            'disk': self.get_disk_info(),
            'load': self.get_system_load(),
            'network': self.get_network_info(),
            'processes': self.get_process_info(),
            'gpu': self.get_gpu_info(),
            'bioinformatics_recommendations': self.get_bioinformatics_recommendations()
        }


# 创建全局实例
system_info_service = SystemInfoService() 