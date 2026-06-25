import os

from dotenv import load_dotenv

load_dotenv()
os.environ['APPAM_DISABLE_EMBEDDED_WORKER'] = 'true'

from redis import Redis
from rq import Queue, Worker

from app.database import init_db


def main() -> None:
    init_db()
    redis_url = os.getenv('APPAM_REDIS_URL', 'redis://redis:6379/0')
    queue_name = os.getenv('APPAM_RQ_QUEUE', 'appam-workflows')
    worker_name = os.getenv('APPAM_RQ_WORKER_NAME') or None
    connection = Redis.from_url(redis_url)
    queue = Queue(queue_name, connection=connection)
    worker = Worker([queue], connection=connection, name=worker_name)
    worker.work()


if __name__ == '__main__':
    main()
