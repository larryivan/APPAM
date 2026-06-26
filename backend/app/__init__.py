import os
from flask import Flask, jsonify, request
from flask_socketio import SocketIO
from flask_cors import CORS

# Initialize extensions
socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode=os.getenv('SOCKETIO_ASYNC_MODE', 'threading')
)
cors = CORS()

def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'appam-local-dev-secret')
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'

    # Initialize extensions with the app
    socketio.init_app(app)
    cors.init_app(app)

    from .database import init_db
    from .auth import load_current_user, current_user
    from .services.auth_service import bootstrap_admin_users_from_env

    # Initialize the database
    init_db()
    bootstrap_admin_users_from_env()

    @app.before_request
    def enforce_authentication():
        load_current_user()
        if request.method == 'OPTIONS':
            return None

        public_api_prefixes = (
            '/api/auth/login',
            '/api/auth/register',
            '/api/auth/me',
        )
        if request.path.startswith('/api/') and not any(request.path.startswith(prefix) for prefix in public_api_prefixes):
            if not current_user():
                return jsonify({'error': 'Authentication required'}), 401

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
