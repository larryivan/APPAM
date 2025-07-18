from flask import Blueprint, jsonify, request
from app.services.system_info import system_info_service
import traceback

system_bp = Blueprint('system', __name__)

@system_bp.route('/info', methods=['GET'])
def get_system_info():
    """获取系统信息"""
    try:
        info_type = request.args.get('type', 'full')
        
        if info_type == 'cpu':
            data = system_info_service.get_cpu_info()
        elif info_type == 'memory':
            data = system_info_service.get_memory_info()
        elif info_type == 'disk':
            data = system_info_service.get_disk_info()
        elif info_type == 'load':
            data = system_info_service.get_system_load()
        elif info_type == 'network':
            data = system_info_service.get_network_info()
        elif info_type == 'processes':
            limit = request.args.get('limit', 10, type=int)
            data = system_info_service.get_process_info(limit=limit)
        elif info_type == 'gpu':
            data = system_info_service.get_gpu_info()
        elif info_type == 'recommendations':
            data = system_info_service.get_bioinformatics_recommendations()
        else:  # full
            data = system_info_service.get_full_system_info()
        
        return jsonify({
            'success': True,
            'data': data
        })
    
    except Exception as e:
        print(f"Error getting system info: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@system_bp.route('/recommendations', methods=['GET'])
def get_bioinformatics_recommendations():
    """获取生物信息学分析建议"""
    try:
        recommendations = system_info_service.get_bioinformatics_recommendations()
        
        return jsonify({
            'success': True,
            'data': recommendations
        })
    
    except Exception as e:
        print(f"Error getting recommendations: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@system_bp.route('/status', methods=['GET'])
def get_system_status():
    """获取系统状态摘要"""
    try:
        cpu_info = system_info_service.get_cpu_info()
        memory_info = system_info_service.get_memory_info()
        load_info = system_info_service.get_system_load()
        disk_info = system_info_service.get_disk_info()
        
        # 计算总磁盘使用率
        total_disk_space = sum(d['total'] for d in disk_info)
        used_disk_space = sum(d['used'] for d in disk_info)
        disk_usage_percent = (used_disk_space / total_disk_space * 100) if total_disk_space > 0 else 0
        
        status = {
            'cpu_usage': cpu_info['usage_percent'],
            'memory_usage': memory_info['usage_percent'],
            'disk_usage': disk_usage_percent,
            'system_load': load_info.get('load_1min'),
            'status': 'healthy'
        }
        
        # 判断系统状态
        if (cpu_info['usage_percent'] > 90 or 
            memory_info['usage_percent'] > 90 or 
            disk_usage_percent > 95):
            status['status'] = 'critical'
        elif (cpu_info['usage_percent'] > 70 or 
              memory_info['usage_percent'] > 70 or 
              disk_usage_percent > 80):
            status['status'] = 'warning'
        
        return jsonify({
            'success': True,
            'data': status
        })
    
    except Exception as e:
        print(f"Error getting system status: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 