import os
from flask import Flask, jsonify, request
from flask_socketio import SocketIO
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix


def _allowed_origins():
    configured = os.getenv('APPAM_ALLOWED_ORIGINS', '').strip()
    if configured:
        return [origin.strip().rstrip('/') for origin in configured.split(',') if origin.strip()]
    return []


def _secret_key() -> str:
    configured = os.getenv('FLASK_SECRET_KEY', '').strip()
    if configured:
        return configured
    if os.getenv('FLASK_DEBUG', 'false').strip().lower() in {'1', 'true', 'yes', 'on'}:
        return 'appam-local-dev-secret'
    raise RuntimeError('FLASK_SECRET_KEY is required when FLASK_DEBUG is disabled.')


def _max_request_bytes() -> int:
    try:
        max_chunk = max(1, int(os.getenv('APPAM_MAX_UPLOAD_CHUNK_BYTES', str(16 * 1024 * 1024))))
    except ValueError:
        max_chunk = 16 * 1024 * 1024
    try:
        return max(1024 * 1024, int(os.getenv('APPAM_MAX_REQUEST_BYTES', str(max_chunk + 1024 * 1024))))
    except ValueError:
        return max_chunk + 1024 * 1024


# Initialize extensions
socketio = SocketIO(
    cors_allowed_origins=_allowed_origins() or None,
    async_mode=os.getenv('SOCKETIO_ASYNC_MODE', 'threading')
)
cors = CORS()

def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)
    if os.getenv('APPAM_TRUST_PROXY_HEADERS', 'false').strip().lower() in {'1', 'true', 'yes', 'on'}:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.config['SECRET_KEY'] = _secret_key()
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    app.config['MAX_CONTENT_LENGTH'] = _max_request_bytes()

    # Initialize extensions with the app
    socketio.init_app(app)
    allowed_origins = _allowed_origins()
    if allowed_origins:
        cors.init_app(app, origins=allowed_origins, supports_credentials=True)

    from .database import init_db
    from .auth import load_current_user, current_user
    from .services.auth_service import bootstrap_admin_users_from_env
    from .services.download_manager import restore_download_tasks

    # Initialize the database
    init_db()
    bootstrap_admin_users_from_env()
    restore_download_tasks()

    @app.before_request
    def enforce_authentication():
        load_current_user()
        if request.method == 'OPTIONS':
            return None

        public_api_paths = {
            '/api/health',
            '/api/auth/login',
            '/api/auth/register',
            '/api/auth/me',
        }
        if request.path.startswith('/api/') and request.path not in public_api_paths:
            if not current_user():
                return jsonify({'error': 'Authentication required'}), 401

        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            if request.headers.get('Sec-Fetch-Site', '').lower() == 'cross-site':
                return jsonify({'error': 'Cross-site request rejected'}), 403
            origin = request.headers.get('Origin', '').rstrip('/')
            same_origin = origin and origin == f'{request.scheme}://{request.host}'.rstrip('/')
            if origin and not same_origin and origin not in _allowed_origins():
                return jsonify({'error': 'Origin not allowed'}), 403

    @app.get('/api/health')
    def health_check():
        return jsonify({'status': 'ok', 'service': 'appam-backend'})

    @app.errorhandler(413)
    def request_too_large(_error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Request body is too large'}), 413
        return 'Request body is too large', 413

    # --- Register Blueprints ---
    from .api.filemanager.routes import filemanager_bp
    from .api.projects.routes import projects_bp
    from .api.system.routes import system_bp
    from .api.pipeline.routes import pipeline_bp
    from .api.terminal.routes import register_terminal_routes
    from .api.auth.routes import auth_bp
    from .api.tools.routes import tools_bp
    from .api.parameter_fill.routes import parameter_fill_bp
    from .api.jobs.routes import jobs_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(filemanager_bp, url_prefix='/api/filemanager')
    app.register_blueprint(projects_bp, url_prefix='/api/projects')
    app.register_blueprint(system_bp, url_prefix='/api/system')
    app.register_blueprint(pipeline_bp, url_prefix='/api/pipeline')
    app.register_blueprint(tools_bp, url_prefix='/api')
    app.register_blueprint(parameter_fill_bp, url_prefix='/api/parameter-fill')
    app.register_blueprint(jobs_bp, url_prefix='/api')
    
    # Register terminal routes
    register_terminal_routes(app)
    
    return app
