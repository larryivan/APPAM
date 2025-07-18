
from app import create_app
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = create_app()

if __name__ == '__main__':
    # 从环境变量读取debug模式设置，默认为False（生产环境）
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 'yes']
    # 使用端口5001匹配防火墙配置
    port = int(os.getenv('FLASK_PORT', 5001))
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
