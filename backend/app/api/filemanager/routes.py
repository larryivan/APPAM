from flask import Blueprint, request, jsonify, send_from_directory, Response
from app.services import file_manager as services
from app.services import download_manager
import os
import shutil
from urllib.parse import quote

filemanager_bp = Blueprint('filemanager_bp', __name__)

@filemanager_bp.route('/<project_id>/list', methods=['GET'])
def list_files(project_id):
    try:
        path = request.args.get('path', '.')
        items = services.list_files(project_id, path)
        return jsonify({'items': items})
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@filemanager_bp.route('/<project_id>/upload-chunk', methods=['POST'])
def upload_chunk(project_id):
    try:
        file = request.files['file']
        target_path = request.form['path']
        filename = request.form['filename']
        chunk_number = int(request.form['chunkNumber'])
        total_chunks = int(request.form['totalChunks'])
        services.upload_chunk(project_id, file, target_path, filename, chunk_number, total_chunks)
        return jsonify({'message': 'Chunk uploaded'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@filemanager_bp.route('/<project_id>/mkdir', methods=['POST'])
def make_directory(project_id):
    try:
        path = request.json['path']
        services.make_directory(project_id, path)
        return jsonify({'message': 'Directory created'})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@filemanager_bp.route('/<project_id>/rename', methods=['POST'])
def rename_item(project_id):
    try:
        data = request.json
        services.rename_item(project_id, data['old_path'], data['new_path'])
        return jsonify({'message': 'Renamed successfully'})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@filemanager_bp.route('/<project_id>/download-zip', methods=['POST'])
def download_zip(project_id):
    try:
        items = request.json['items']
        zip_path, temp_dir = services.download_zip(project_id, items)
        
        response = send_from_directory(
            os.path.dirname(zip_path),
            os.path.basename(zip_path),
            as_attachment=True
        )
        
        @response.call_on_close
        def cleanup():
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            if os.path.exists(zip_path):
                os.remove(zip_path)
        
        return response
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@filemanager_bp.route('/<project_id>/delete', methods=['POST'])
def delete_items(project_id):
    try:
        items = request.json['items']
        services.delete_items(project_id, items)
        return jsonify({'message': 'Items deleted'})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@filemanager_bp.route('/<project_id>/fetch-url', methods=['POST'])
def fetch_from_url(project_id):
    try:
        url = request.json['url']
        path = request.json.get('path', '.')
        message = services.fetch_from_url(project_id, url, path)
        return jsonify({'message': message})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@filemanager_bp.route('/<project_id>/preview', methods=['GET'])
def preview_file(project_id):
    try:
        path = request.args.get('path')
        result = services.preview_file(project_id, path)
        if result['type'] == 'image':
            # Return JSON with image URL instead of raw image
            encoded_path = quote(path or '', safe='')
            result['url'] = f"/api/filemanager/{project_id}/image?path={encoded_path}"
            return jsonify(result)
        else:
            return jsonify(result)
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@filemanager_bp.route('/<project_id>/image', methods=['GET'])
def serve_image(project_id):
    try:
        path = request.args.get('path')
        result = services.preview_file(project_id, path)
        if result['type'] == 'image':
            return send_from_directory(os.path.dirname(result['path']), os.path.basename(result['path']))
        else:
            return jsonify({'error': 'Not an image file'}), 400
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@filemanager_bp.route('/<project_id>/download', methods=['GET'])
def download_file(project_id):
    try:
        path = request.args.get('path')
        if not path:
            return jsonify({'error': 'Missing path'}), 400

        abs_path = services.get_project_path(project_id, path)
        if not os.path.exists(abs_path) or os.path.isdir(abs_path):
            return jsonify({'error': 'File not found'}), 404

        return send_from_directory(
            os.path.dirname(abs_path),
            os.path.basename(abs_path),
            as_attachment=True
        )
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@filemanager_bp.route('/<project_id>/save', methods=['POST'])
def save_file(project_id):
    try:
        data = request.get_json()
        if not data or 'path' not in data or 'content' not in data:
            return jsonify({'error': 'Missing path or content'}), 400
        
        result = services.save_file(project_id, data['path'], data['content'])
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@filemanager_bp.route('/<project_id>/copy', methods=['POST'])
def copy_items(project_id):
    try:
        data = request.json
        items = data['items']
        destination = data['destination']
        result = services.copy_items(project_id, items, destination)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@filemanager_bp.route('/<project_id>/cut', methods=['POST'])
def cut_items(project_id):
    try:
        data = request.json
        items = data['items']
        destination = data['destination']
        result = services.cut_items(project_id, items, destination)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@filemanager_bp.route('/<project_id>/thumbnail', methods=['GET'])
def get_thumbnail(project_id):
    try:
        path = request.args.get('path')
        size = request.args.get('size', '128')
        result = services.generate_thumbnail(project_id, path, int(size))
        if result['success']:
            return send_from_directory(
                os.path.dirname(result['path']),
                os.path.basename(result['path']),
                mimetype='image/jpeg'
            )
        else:
            return jsonify({'error': result['error']}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@filemanager_bp.route('/<project_id>/preview-head', methods=['GET'])
def preview_file_head(project_id):
    """Preview first N lines of a file"""
    try:
        path = request.args.get('path')
        lines = int(request.args.get('lines', 1000))
        result = services.preview_file_head(project_id, path, lines)
        return jsonify(result)
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@filemanager_bp.route('/<project_id>/preview-sample', methods=['GET'])
def preview_file_sample(project_id):
    """Preview sample lines from a file"""
    try:
        path = request.args.get('path')
        samples = int(request.args.get('samples', 100))
        result = services.preview_file_sample(project_id, path, samples)
        return jsonify(result)
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 下载管理器API端点
@filemanager_bp.route('/<project_id>/download-url', methods=['POST'])
def start_url_download(project_id):
    """开始URL下载任务"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'Missing download URL'}), 400
        
        url = data['url']
        filename = data.get('filename', '')
        path = data.get('path', '/')
        concurrent = data.get('concurrent', True)
        task_id = data.get('task_id')
        
        # Validate URL format
        if not url.startswith(('http://', 'https://', 'ftp://')):
            return jsonify({'error': 'Unsupported URL protocol, please use HTTP/HTTPS/FTP'}), 400
        
        task_id = download_manager.start_download(
            project_id=project_id,
            url=url,
            filename=filename,
            path=path,
            concurrent=concurrent,
            task_id=task_id
        )
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Download task started'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@filemanager_bp.route('/<project_id>/download-progress/<task_id>', methods=['GET'])
def get_download_progress(project_id, task_id):
    """获取下载进度"""
    try:
        progress = download_manager.get_download_progress(task_id)
        if progress is None:
            return jsonify({'error': 'Download task not found'}), 404
        
        return jsonify(progress)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@filemanager_bp.route('/<project_id>/download-pause/<task_id>', methods=['POST'])
def pause_download(project_id, task_id):
    """暂停下载任务"""
    try:
        success = download_manager.pause_download(task_id)
        if success:
            return jsonify({'success': True, 'message': 'Download paused'})
        else:
            return jsonify({'error': 'Failed to pause download task'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@filemanager_bp.route('/<project_id>/download-resume/<task_id>', methods=['POST'])
def resume_download(project_id, task_id):
    """继续下载任务"""
    try:
        success = download_manager.resume_download(task_id)
        if success:
            return jsonify({'success': True, 'message': 'Download resumed'})
        else:
            return jsonify({'error': 'Failed to resume download task'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@filemanager_bp.route('/<project_id>/download-cancel/<task_id>', methods=['POST'])
def cancel_download(project_id, task_id):
    """取消下载任务"""
    try:
        success = download_manager.cancel_download(task_id)
        if success:
            return jsonify({'success': True, 'message': 'Download cancelled'})
        else:
            return jsonify({'error': 'Failed to cancel download task'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@filemanager_bp.route('/<project_id>/downloads', methods=['GET'])
def list_downloads(project_id):
    """获取所有下载任务"""
    try:
        downloads = download_manager.get_all_downloads(project_id)
        return jsonify({'downloads': downloads})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@filemanager_bp.route('/<project_id>/download-cleanup', methods=['POST'])
def cleanup_downloads(project_id):
    """清理已完成的下载任务"""
    try:
        count = download_manager.cleanup_completed_downloads()
        return jsonify({
            'success': True, 
            'message': f'Cleaned up {count} completed download tasks'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
