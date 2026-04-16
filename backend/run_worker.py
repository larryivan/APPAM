import os
from dotenv import load_dotenv

load_dotenv()

from app.database import init_db
from app.services.local_executor import run_worker_forever


if __name__ == '__main__':
    os.environ['APPAM_DISABLE_EMBEDDED_WORKER'] = 'true'
    init_db()
    run_worker_forever()
