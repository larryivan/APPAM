import uuid
import os
import shutil
import requests
import mimetypes
import time
import yaml
import json
import xml.etree.ElementTree as ET
import hashlib
import secrets
from ..database import get_db_connection

PROJECTS_DIR = './projects'

# Password utilities
def hash_password(password):
    """Hash a password using a secure method."""
    # Generate a random salt
    salt = secrets.token_hex(32)
    # Hash the password with salt
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    # Return salt and hash combined
    return salt + password_hash.hex()

def verify_password(password, stored_hash):
    """Verify a password against a stored hash."""
    try:
        if not stored_hash or len(stored_hash) < 64:
            return False
            
        # Extract salt from stored hash (first 64 characters)
        salt = stored_hash[:64]
        # Extract the hash (remaining characters)
        stored_password_hash = stored_hash[64:]
        
        # Hash the provided password with the same salt
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        computed_hash = password_hash.hex()
        
        # Compare the hashes
        result = computed_hash == stored_password_hash
        return result
    except Exception as e:
        return False

# File extension mappings - centralized configuration
BIO_EXTENSIONS = {
    'fasta': ['.fasta', '.fa', '.fas', '.fna', '.faa', '.ffn'],
    'fastq': ['.fastq', '.fq'],
    'vcf': ['.vcf'],
    'gff': ['.gff', '.gff3', '.gtf'],
    'bed': ['.bed'],
    'sam': ['.sam', '.bam']
}

TEXT_EXTENSIONS = {
    '.txt', '.md', '.markdown', '.log', '.conf', '.cfg', '.ini',
    '.py', '.js', '.html', '.css', '.scss', '.sass', '.less',
    '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.php', '.rb',
    '.go', '.rs', '.swift', '.kt', '.scala', '.sh', '.bash',
    '.zsh', '.fish', '.ps1', '.bat', '.cmd', '.r', '.R',
    '.sql', '.dockerfile', '.dockerignore', '.gitignore',
    '.env', '.example', '.sample', '.template'
}

LANG_MAP = {
    '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
    '.jsx': 'javascript', '.tsx': 'typescript', '.html': 'html',
    '.css': 'css', '.scss': 'scss', '.sass': 'sass', '.less': 'less',
    '.java': 'java', '.cpp': 'cpp', '.c': 'c', '.h': 'c',
    '.hpp': 'cpp', '.cs': 'csharp', '.php': 'php', '.rb': 'ruby',
    '.go': 'go', '.rs': 'rust', '.swift': 'swift', '.kt': 'kotlin',
    '.scala': 'scala', '.sh': 'bash', '.bash': 'bash', '.zsh': 'zsh',
    '.fish': 'fish', '.ps1': 'powershell', '.bat': 'batch',
    '.cmd': 'batch', '.r': 'r', '.R': 'r', '.sql': 'sql',
    '.dockerfile': 'dockerfile', '.md': 'markdown', '.markdown': 'markdown',
    '.yaml': 'yaml', '.yml': 'yaml', '.json': 'json', '.xml': 'xml',
    '.toml': 'toml', '.ini': 'ini', '.cfg': 'ini', '.conf': 'apache'
}

# Utility functions
def get_project_path(project_id, path=''):
    """Safely constructs a path within a project directory."""
    base_path = os.path.abspath(os.path.join(os.getcwd(), PROJECTS_DIR, project_id))
    target_path = os.path.abspath(os.path.join(base_path, path.lstrip('/')))
    
    if not target_path.startswith(base_path):
        raise ValueError("Attempted to access path outside of project directory.")
    return target_path

def get_file_format(file_ext):
    """Determine file format from extension."""
    file_ext = file_ext.lower()
    for format_type, extensions in BIO_EXTENSIONS.items():
        if file_ext in extensions:
            return format_type
    return None

def detect_language(file_ext, filename):
    """Detect programming language from file extension and filename."""
    # Check filename patterns first
    if filename.lower() in ['dockerfile', 'makefile', 'rakefile', 'gemfile']:
        return filename.lower()
    
    return LANG_MAP.get(file_ext, 'text')

def calculate_gc_content(sequence):
    """Calculate GC content of a sequence."""
    if not sequence:
        return 0.0
    sequence = sequence.upper()
    gc_count = sequence.count('G') + sequence.count('C')
    total_count = len([base for base in sequence if base in 'ATGC'])
    
    if total_count > 0:
        return (gc_count / total_count) * 100
    return 0.0

def calculate_avg_quality(quality_string):
    """Calculate average quality score from FASTQ quality string."""
    if not quality_string:
        return 0.0
    
    # Convert ASCII to quality scores (Phred+33)
    quality_scores = [ord(char) - 33 for char in quality_string]
    return sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

def process_sequence_info(header, sequence, quality=None):
    """Process individual sequence and return standardized info."""
    info = {
        'header': header,
        'length': len(sequence),
        'gc_content': calculate_gc_content(sequence)
    }
    if quality:
        info['avg_quality'] = calculate_avg_quality(quality)
    return info

# File management functions
def list_files(project_id, path):
    abs_path = get_project_path(project_id, path)
    if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
        raise FileNotFoundError("Directory not found")

    items = []
    for item_name in os.listdir(abs_path):
        item_path = os.path.join(abs_path, item_name)
        if item_name.startswith('.tmp_'):
            continue
        try:
            stat_info = os.stat(item_path)
            is_dir = os.path.isdir(item_path)
            
            # Get file extension and type
            file_ext = os.path.splitext(item_name)[1].lower() if not is_dir else ''
            file_type = 'folder' if is_dir else get_file_format(file_ext) or 'file'
            
            items.append({
                'name': item_name,
                'is_dir': is_dir,
                'size': stat_info.st_size,
                'mtime': stat_info.st_mtime,          # 修改时间
                'ctime': stat_info.st_ctime,          # 创建时间 (Windows) / 状态改变时间 (Unix)
                'atime': stat_info.st_atime,          # 访问时间
                'mode': stat_info.st_mode,            # 文件权限模式
                'type': file_type,                    # 文件类型
                'extension': file_ext,                # 文件扩展名
                'permissions': {                      # 权限信息
                    'readable': os.access(item_path, os.R_OK),
                    'writable': os.access(item_path, os.W_OK),
                    'executable': os.access(item_path, os.X_OK)
                }
            })
        except (FileNotFoundError, PermissionError, OSError):
            continue
    return items

def upload_chunk(project_id, file, path, filename, chunk_number, total_chunks):
    temp_dir = get_project_path(project_id, os.path.join(path, f'.tmp_{filename}'))
    os.makedirs(temp_dir, exist_ok=True)
    file.save(os.path.join(temp_dir, str(chunk_number)))

    if len(os.listdir(temp_dir)) == total_chunks:
        final_path = get_project_path(project_id, os.path.join(path, filename))
        with open(final_path, 'wb') as outfile:
            for i in range(1, total_chunks + 1):
                chunk_path = os.path.join(temp_dir, str(i))
                with open(chunk_path, 'rb') as infile:
                    outfile.write(infile.read())
                os.remove(chunk_path)
        os.rmdir(temp_dir)

def make_directory(project_id, path):
    os.makedirs(get_project_path(project_id, path), exist_ok=True)

def rename_item(project_id, old_path, new_path):
    os.rename(get_project_path(project_id, old_path), get_project_path(project_id, new_path))

def delete_items(project_id, items):
    for item_rel_path in items:
        abs_path = get_project_path(project_id, item_rel_path)
        if os.path.isdir(abs_path):
            shutil.rmtree(abs_path)
        else:
            os.remove(abs_path)

def copy_items(project_id, items, destination):
    """Copy items to destination directory."""
    try:
        copied_items = []
        for item_rel_path in items:
            source_path = get_project_path(project_id, item_rel_path)
            item_name = os.path.basename(item_rel_path)
            dest_path = get_project_path(project_id, os.path.join(destination, item_name))
            
            # Handle name conflicts
            if os.path.exists(dest_path):
                base_name, ext = os.path.splitext(item_name)
                counter = 1
                while os.path.exists(dest_path):
                    new_name = f"{base_name}_copy_{counter}{ext}"
                    dest_path = get_project_path(project_id, os.path.join(destination, new_name))
                    counter += 1
            
            if os.path.isdir(source_path):
                shutil.copytree(source_path, dest_path)
            else:
                shutil.copy2(source_path, dest_path)
            
            copied_items.append(os.path.basename(dest_path))
        
        return {'success': True, 'copied_items': copied_items}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def cut_items(project_id, items, destination):
    """Cut (move) items to destination directory."""
    try:
        moved_items = []
        for item_rel_path in items:
            source_path = get_project_path(project_id, item_rel_path)
            item_name = os.path.basename(item_rel_path)
            dest_path = get_project_path(project_id, os.path.join(destination, item_name))
            
            # Handle name conflicts
            if os.path.exists(dest_path):
                base_name, ext = os.path.splitext(item_name)
                counter = 1
                while os.path.exists(dest_path):
                    new_name = f"{base_name}_moved_{counter}{ext}"
                    dest_path = get_project_path(project_id, os.path.join(destination, new_name))
                    counter += 1
            
            shutil.move(source_path, dest_path)
            moved_items.append(os.path.basename(dest_path))
        
        return {'success': True, 'moved_items': moved_items}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def download_zip(project_id, items):
    if not items:
        raise ValueError("No items selected for download.")

    temp_zip_dir_name = f".tmp_zip_{int(time.time())}_{os.getpid()}"
    temp_zip_dir_path = get_project_path(project_id, temp_zip_dir_name)
    os.makedirs(temp_zip_dir_path)

    project_abs_path = get_project_path(project_id)

    for item_rel_path in items:
        full_item_path = get_project_path(project_id, item_rel_path)
        if not full_item_path.startswith(project_abs_path):
            raise ValueError(f"Attempted to download item outside project: {item_rel_path}")

        dest_path = os.path.join(temp_zip_dir_path, os.path.basename(full_item_path))
        
        if os.path.isdir(full_item_path):
            shutil.copytree(full_item_path, dest_path)
        else:
            shutil.copy(full_item_path, dest_path)

    zip_base_name = f"selected_files_{int(time.time())}"
    zip_output_path = os.path.join(get_project_path(project_id), zip_base_name)
    shutil.make_archive(zip_output_path, 'zip', temp_zip_dir_path)
    
    return f'{zip_output_path}.zip', temp_zip_dir_path

def generate_thumbnail(project_id, path, size=128):
    """Generate thumbnail for image files."""
    try:
        from PIL import Image
        
        abs_path = get_project_path(project_id, path)
        if not os.path.exists(abs_path):
            return {'success': False, 'error': 'File not found'}
        
        # Check if it's an image file
        try:
            with Image.open(abs_path) as img:
                # Create thumbnail
                img.thumbnail((size, size), Image.LANCZOS)
                
                # Save thumbnail
                thumb_dir = get_project_path(project_id, '.thumbnails')
                os.makedirs(thumb_dir, exist_ok=True)
                
                thumb_filename = f"{os.path.basename(path)}_{size}.jpg"
                thumb_path = os.path.join(thumb_dir, thumb_filename)
                
                # Convert to RGB if necessary (for PNG with transparency)
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                img.save(thumb_path, 'JPEG', quality=85)
                
                return {'success': True, 'path': thumb_path}
        except Exception as e:
            return {'success': False, 'error': f'Cannot create thumbnail: {str(e)}'}
    except ImportError:
        return {'success': False, 'error': 'PIL/Pillow not installed'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def fetch_from_url(project_id, url, path):
    filename = url.split('/')[-1] or 'downloaded_file'
    save_path = get_project_path(project_id, os.path.join(path, filename))
    
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return f'Downloaded {filename} from URL.'

def save_file(project_id, path, content):
    """Save content to a file."""
    abs_path = get_project_path(project_id, path)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    
    try:
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {'success': True, 'message': 'File saved successfully'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Preview functions
def preview_file_head(project_id, path, lines=1000):
    """Preview first N lines of a file"""
    abs_path = get_project_path(project_id, path)
    
    if not os.path.exists(abs_path) or os.path.isdir(abs_path):
        raise FileNotFoundError("File not found or is a directory")
    
    try:
        content_lines = []
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if i >= lines:
                    break
                content_lines.append(line.rstrip())
        
        return {
            'content': '\n'.join(content_lines),
            'lines_count': len(content_lines),
            'preview_type': 'head'
        }
    except Exception as e:
        return {
            'content': f'Error reading file: {str(e)}',
            'lines_count': 0,
            'preview_type': 'error'
        }

def preview_file_sample(project_id, path, samples=100):
    """Preview sample lines from a file"""
    abs_path = get_project_path(project_id, path)
    
    if not os.path.exists(abs_path) or os.path.isdir(abs_path):
        raise FileNotFoundError("File not found or is a directory")
    
    try:
        # First, count total lines
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            total_lines = sum(1 for _ in f)
        
        if total_lines <= samples:
            # If file is small enough, return all lines
            with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return {
                'content': content,
                'lines_count': total_lines,
                'preview_type': 'full'
            }
        
        # Sample lines evenly throughout the file
        sample_interval = max(1, total_lines // samples)
        content_lines = []
        
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if i % sample_interval == 0:
                    content_lines.append(f"Line {i+1}: {line.rstrip()}")
                if len(content_lines) >= samples:
                    break
        
        return {
            'content': '\n'.join(content_lines),
            'lines_count': len(content_lines),
            'preview_type': 'sample',
            'total_lines': total_lines
        }
    except Exception as e:
        return {
            'content': f'Error reading file: {str(e)}',
            'lines_count': 0,
            'preview_type': 'error'
        }

# Project management functions
def get_all_projects():
    """Get all projects from the database."""
    conn = get_db_connection()
    projects = conn.execute('SELECT * FROM projects').fetchall()
    conn.close()
    
    # Remove password_hash from returned data for security
    result = []
    for project in projects:
        project_dict = dict(project)
        # Remove password_hash from the returned data
        if 'password_hash' in project_dict:
            del project_dict['password_hash']
        result.append(project_dict)
    
    return result

def get_project_by_id(project_id):
    """Get a specific project by ID."""
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    conn.close()
    
    if not project:
        return None
    
    project_dict = dict(project)
    # Remove password_hash from the returned data
    if 'password_hash' in project_dict:
        del project_dict['password_hash']
    
    return project_dict

def create_project(name, description='', creator='', password=''):
    """Create a new project."""
    project_id = str(uuid.uuid4())
    
    # Create project directory
    project_dir = get_project_path(project_id)
    os.makedirs(project_dir, exist_ok=True)
    
    # Handle password
    password_hash = None
    has_password = False
    if password:
        password_hash = hash_password(password)
        has_password = True
    
    # Insert into database
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO projects (id, name, description, creator, password_hash, has_password) VALUES (?, ?, ?, ?, ?, ?)',
        (project_id, name, description, creator, password_hash, has_password)
    )
    conn.commit()
    
    # Get the created project with all fields
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    conn.close()
    
    project_dict = dict(project)
    # Remove password_hash from the returned data
    if 'password_hash' in project_dict:
        del project_dict['password_hash']

    return project_dict

def update_project(project_id, name=None, description=None, creator=None, password=None):
    """Update an existing project."""
    conn = get_db_connection()
    
    # Check if project exists
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        conn.close()
        return None
    
    # Update fields
    if name is not None:
        conn.execute('UPDATE projects SET name = ? WHERE id = ?', (name, project_id))
    if description is not None:
        conn.execute('UPDATE projects SET description = ? WHERE id = ?', (description, project_id))
    if creator is not None:
        conn.execute('UPDATE projects SET creator = ? WHERE id = ?', (creator, project_id))
    
    # Handle password update
    if password is not None:
        if password:  # Set new password
            password_hash = hash_password(password)
            conn.execute('UPDATE projects SET password_hash = ?, has_password = ? WHERE id = ?', 
                        (password_hash, True, project_id))
        else:  # Remove password
            conn.execute('UPDATE projects SET password_hash = NULL, has_password = FALSE WHERE id = ?', 
                        (project_id,))
    
    conn.commit()
    
    # Get updated project
    updated_project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    conn.close()
    
    project_dict = dict(updated_project)
    # Remove password_hash from the returned data
    if 'password_hash' in project_dict:
        del project_dict['password_hash']
    
    return project_dict

def verify_project_password(project_id, password):
    """Verify a project password."""
    
    conn = get_db_connection()
    project = conn.execute('SELECT password_hash, has_password FROM projects WHERE id = ?', (project_id,)).fetchone()
    conn.close()
    
    if not project:
        return False
    
    has_password = project['has_password']
    password_hash = project['password_hash']
    
    # If project has no password, allow access
    if not has_password or not password_hash:
        return True
    
    # Verify password
    result = verify_password(password, password_hash)
    return result

def update_project_access_time(project_id):
    """Update the last accessed time for a project."""
    conn = get_db_connection()
    conn.execute('UPDATE projects SET last_accessed = CURRENT_TIMESTAMP WHERE id = ?', (project_id,))
    conn.commit()
    conn.close()

def delete_project(project_id):
    """Delete a project and its associated files."""
    # Delete project directory
    project_dir = get_project_path(project_id)
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)
    
    # Delete from database
    conn = get_db_connection()
    conn.execute('DELETE FROM projects WHERE id = ?', (project_id,))
    conn.commit()
    conn.close()

# Analysis functions
def analyze_bio_file(abs_path, file_ext, file_size):
    """Analyze bioinformatics files and return structured data"""
    try:
        # Quick analysis for bio files
        filename = os.path.basename(abs_path)
        file_format = file_ext.lstrip('.')
        
        # Basic file info
        result = {
            'type': 'bioinformatics',
            'file_format': file_format,
            'file_size': file_size,
            'bio_analysis': {
                'sequence_count': 0,
                'total_length': 0,
                'gc_content': 0,
                'sequence_type': file_format.upper()
            }
        }
        
        # For smaller files, do actual analysis
        if file_size < 5 * 1024 * 1024:  # 5MB limit for analysis
            if file_format in ['fasta', 'fa', 'fas']:
                result['bio_analysis'] = analyze_fasta_file(abs_path)
            elif file_format in ['fastq', 'fq']:
                result['bio_analysis'] = analyze_fastq_file(abs_path)
            elif file_format == 'vcf':
                result['bio_analysis'] = analyze_vcf_file(abs_path)
        
        # Read small sample of content for display
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            content_lines = []
            for i, line in enumerate(f):
                if i >= 50:  # Only read first 50 lines
                    break
                content_lines.append(line.rstrip())
            result['content'] = '\n'.join(content_lines)
        
        return result
        
    except Exception as e:
        return {
            'type': 'bioinformatics',
            'file_format': file_ext.lstrip('.'),
            'content': f'Error analyzing file: {str(e)}',
            'bio_analysis': None
        }

def analyze_fasta_file(abs_path):
    """Analyze FASTA file and return statistics"""
    sequence_count = 0
    total_length = 0
    gc_count = 0
    
    try:
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            current_seq = ''
            for line in f:
                line = line.strip()
                if line.startswith('>'):
                    if current_seq:
                        total_length += len(current_seq)
                        gc_count += current_seq.upper().count('G') + current_seq.upper().count('C')
                    sequence_count += 1
                    current_seq = ''
                else:
                    current_seq += line
            
            # Process last sequence
            if current_seq:
                total_length += len(current_seq)
                gc_count += current_seq.upper().count('G') + current_seq.upper().count('C')
        
        gc_content = (gc_count / total_length * 100) if total_length > 0 else 0
        
        return {
            'sequence_count': sequence_count,
            'total_length': total_length,
            'gc_content': gc_content,
            'sequence_type': 'FASTA'
        }
    except Exception:
        return {
            'sequence_count': 0,
            'total_length': 0,
            'gc_content': 0,
            'sequence_type': 'FASTA'
        }

def analyze_fastq_file(abs_path):
    """Analyze FASTQ file and return statistics"""
    sequence_count = 0
    total_length = 0
    gc_count = 0
    
    try:
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
            # FASTQ format: 4 lines per sequence
            for i in range(0, len(lines), 4):
                if i + 3 < len(lines):
                    sequence_count += 1
                    seq_line = lines[i + 1].strip()
                    total_length += len(seq_line)
                    gc_count += seq_line.upper().count('G') + seq_line.upper().count('C')
        
        gc_content = (gc_count / total_length * 100) if total_length > 0 else 0
        
        return {
            'sequence_count': sequence_count,
            'total_length': total_length,
            'gc_content': gc_content,
            'sequence_type': 'FASTQ'
        }
    except Exception:
        return {
            'sequence_count': 0,
            'total_length': 0,
            'gc_content': 0,
            'sequence_type': 'FASTQ'
        }

def analyze_vcf_file(abs_path):
    """Analyze VCF file and return statistics"""
    variant_count = 0
    
    try:
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if not line.startswith('#') and line.strip():
                    variant_count += 1
        
        return {
            'sequence_count': variant_count,
            'total_length': 0,
            'gc_content': 0,
            'sequence_type': 'VCF'
        }
    except Exception:
        return {
            'sequence_count': 0,
            'total_length': 0,
            'gc_content': 0,
            'sequence_type': 'VCF'
        }

def preview_file(project_id, path):
    """Preview file with support for various formats"""
    abs_path = get_project_path(project_id, path)
    
    if not os.path.exists(abs_path) or os.path.isdir(abs_path):
        raise FileNotFoundError("File not found or is a directory")

    filename = os.path.basename(abs_path)
    file_ext = os.path.splitext(filename)[1].lower()
    mimetype, _ = mimetypes.guess_type(abs_path)
    file_size = os.path.getsize(abs_path)
    
    # Size limits
    MAX_PREVIEW_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_BIO_PREVIEW_SIZE = 50 * 1024 * 1024  # 50MB for bio files
    
    try:
        # Check if it's a bioinformatics file
        bio_format = get_file_format(file_ext)
        is_bio_file = bio_format is not None
        
        # Handle large files
        if file_size > MAX_PREVIEW_SIZE:
            if is_bio_file:
                return {
                    'type': 'bioinformatics',
                    'file_format': file_ext.lstrip('.'),
                    'file_size': file_size,
                    'too_large': True,
                    'error': f'File is too large ({file_size / (1024*1024):.1f}MB) to preview safely. Use preview options below.',
                    'mimetype': mimetype or 'text/plain'
                }
            else:
                return {
                    'type': 'text',
                    'file_size': file_size,
                    'too_large': True,
                    'error': f'File is too large ({file_size / (1024*1024):.1f}MB) to preview safely. Download to view.',
                    'mimetype': mimetype or 'text/plain'
                }
        
        # Handle bioinformatics files
        if is_bio_file:
            return analyze_bio_file(abs_path, file_ext, file_size)
        
        # Handle JSON files
        if file_ext in {'.json', '.jsonl', '.geojson'}:
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Validate and format JSON
                json_data = json.loads(content)
                formatted_content = json.dumps(json_data, indent=2, ensure_ascii=False)
                return {
                    'type': 'json',
                    'content': formatted_content,
                    'mimetype': 'application/json',
                    'language': 'json',
                    'editable': True
                }
            except json.JSONDecodeError as e:
                return {
                    'type': 'json_error',
                    'content': content,
                    'error': str(e),
                    'mimetype': 'application/json'
                }
        
        # Handle YAML files
        if file_ext in {'.yaml', '.yml'}:
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Validate YAML
                yaml.safe_load(content)
                return {
                    'type': 'yaml',
                    'content': content,
                    'mimetype': 'application/x-yaml',
                    'language': 'yaml',
                    'editable': True
                }
            except yaml.YAMLError as e:
                return {
                    'type': 'yaml_error',
                    'content': content,
                    'error': str(e),
                    'mimetype': 'application/x-yaml'
                }
        
        # Handle XML files
        if file_ext in {'.xml', '.xsd', '.xsl', '.xslt', '.svg'}:
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Validate XML
                ET.fromstring(content)
                return {
                    'type': 'xml',
                    'content': content,
                    'mimetype': 'application/xml',
                    'language': 'xml',
                    'editable': True
                }
            except ET.ParseError as e:
                return {
                    'type': 'xml_error',
                    'content': content,
                    'error': str(e),
                    'mimetype': 'application/xml'
                }
        
        # Handle CSV/TSV files
        if file_ext in {'.csv', '.tsv', '.tab'}:
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read(1024 * 50)  # 50KB preview
                return {
                    'type': 'csv',
                    'content': content,
                    'mimetype': 'text/csv',
                    'language': 'csv',
                    'editable': True
                }
            except UnicodeDecodeError:
                return {
                    'type': 'binary',
                    'content': 'CSV file appears to be binary. Cannot preview.'
                }
        
        # Handle HTML files
        if file_ext in {'.html', '.htm'}:
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {
                    'type': 'html',
                    'content': content,
                    'language': 'html',
                    'mimetype': 'text/html',
                    'editable': True
                }
            except UnicodeDecodeError:
                return {
                    'type': 'binary',
                    'content': 'HTML file appears to be binary. Cannot preview.'
                }
        
        # Handle Markdown files
        if file_ext in {'.md', '.markdown'}:
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {
                    'type': 'markdown',
                    'content': content,
                    'language': 'markdown',
                    'mimetype': 'text/markdown',
                    'editable': True
                }
            except UnicodeDecodeError:
                return {
                    'type': 'binary',
                    'content': 'Markdown file appears to be binary. Cannot preview.'
                }
        
        # Handle text/code files
        if file_ext in TEXT_EXTENSIONS or (mimetype and mimetype.startswith('text/')):
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read(1024 * 50)  # 50KB preview
                
                language = detect_language(file_ext, filename)
                
                return {
                    'type': 'code',
                    'content': content,
                    'language': language,
                    'mimetype': mimetype or 'text/plain',
                    'editable': True
                }
            except UnicodeDecodeError:
                return {
                    'type': 'binary',
                    'content': 'File is not UTF-8 encoded text. Cannot preview.'
                }
        
        # Handle image files
        if mimetype and mimetype.startswith('image/'):
            return {
                'type': 'image',
                'path': abs_path,
                'mimetype': mimetype,
                'size': file_size
            }
        
        # Handle PDF files
        if file_ext == '.pdf':
            return {
                'type': 'pdf',
                'content': f'PDF file ({file_size / 1024:.1f}KB). Download to view.',
                'mimetype': 'application/pdf',
                'size': file_size
            }
        
        # Handle archive files
        if file_ext in {'.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar'}:
            return {
                'type': 'archive',
                'content': f'Archive file ({file_ext[1:].upper()}, {file_size / 1024:.1f}KB). Download to extract.',
                'mimetype': f'application/{file_ext[1:]}',
                'size': file_size
            }
        
        # Default: try to read as text
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read(1024 * 50)
                return {
                    'type': 'text',
                    'content': content,
                    'mimetype': mimetype or 'text/plain',
                    'language': 'text'
                }
            except UnicodeDecodeError:
                return {
                    'type': 'binary',
                    'content': f'Cannot preview this file type ({mimetype or "unknown"}). File appears to be binary.',
                    'mimetype': mimetype,
                    'size': file_size
                }
    
    except Exception as e:
        return {'type': 'error', 'content': str(e)}

# End of file_manager.py