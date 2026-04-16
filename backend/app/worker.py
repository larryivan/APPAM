import os

from .database import init_db
from .services.local_executor import run_worker_forever


def main() -> None:
    os.environ['APPAM_DISABLE_EMBEDDED_WORKER'] = 'true'
    init_db()
    run_worker_forever()


if __name__ == '__main__':
    main()
