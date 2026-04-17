
import os
from dotenv import load_dotenv

# Load environment variables from .env file before initializing Socket.IO
load_dotenv()

async_mode = os.getenv('SOCKETIO_ASYNC_MODE', 'threading')
if async_mode == 'eventlet':
    try:
        import eventlet
        eventlet.monkey_patch()
    except Exception as exc:
        print(f"Failed to enable eventlet ({exc}). Falling back to default server.")

from app import create_app, socketio
from app.services.job_queue import start_embedded_worker

app = create_app()

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 'yes']
    port = int(os.getenv('FLASK_PORT', 19454))
    allow_unsafe_werkzeug = os.getenv('APPAM_ALLOW_UNSAFE_WERKZEUG', 'false').lower() in ['true', '1', 'yes']
    if not debug_mode or os.getenv('WERKZEUG_RUN_MAIN') == 'true':
        start_embedded_worker()
    socketio.run(
        app,
        debug=debug_mode,
        host='0.0.0.0',
        port=port,
        allow_unsafe_werkzeug=allow_unsafe_werkzeug,
    )
