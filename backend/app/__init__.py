import json
from flask import Flask, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS

# Initialize extensions
socketio = SocketIO(cors_allowed_origins="*")
cors = CORS()

def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'a_very_secret_key'

    # Initialize extensions with the app
    socketio.init_app(app)
    cors.init_app(app)

    from .database import init_db

    # Initialize the database
    init_db()

    # --- Register Main API Endpoints ---
    @app.route('/api/tools')
    def get_tool_library():
        """Endpoint to provide the entire tool library to the frontend."""
        with open('tool_library.json', 'r') as f:
            tool_data = json.load(f)
            tool_library = {tool['tool_name'].lower(): tool for tool in tool_data}
        return jsonify(tool_library)

    # --- Register Blueprints ---
    from .api.chatbot.routes import chatbot_bp
    from .api.filemanager.routes import filemanager_bp
    from .api.projects.routes import projects_bp
    from .api.system.routes import system_bp
    from .api.pipeline.routes import pipeline_bp
    from .api.terminal.routes import register_terminal_routes
    from .api.tools.routes import tools_bp
    from .api.parameter_fill.routes import parameter_fill_bp
    
    app.register_blueprint(chatbot_bp, url_prefix='/api/chatbot')
    app.register_blueprint(filemanager_bp, url_prefix='/api/filemanager')
    app.register_blueprint(projects_bp, url_prefix='/api/projects')
    app.register_blueprint(system_bp, url_prefix='/api/system')
    app.register_blueprint(pipeline_bp, url_prefix='/api/pipeline')
    app.register_blueprint(tools_bp, url_prefix='/api')
    app.register_blueprint(parameter_fill_bp, url_prefix='/api/parameter-fill')
    
    # Register terminal routes
    register_terminal_routes(app)
    
    return app