
from app import create_app
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = create_app()

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 'yes']
    port = int(os.getenv('FLASK_PORT', 8666))
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
