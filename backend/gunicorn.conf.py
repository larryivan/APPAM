import os


def _integer_setting(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return min(max(value, minimum), maximum)


bind = f"{os.getenv('FLASK_HOST', '127.0.0.1')}:{_integer_setting('FLASK_PORT', 25079, 1, 65535)}"
workers = 1
worker_class = 'gthread'
threads = _integer_setting('APPAM_GUNICORN_THREADS', 32, 4, 100)
timeout = _integer_setting('APPAM_GUNICORN_TIMEOUT', 120, 30, 3600)
graceful_timeout = _integer_setting('APPAM_GUNICORN_GRACEFUL_TIMEOUT', 30, 10, 300)
keepalive = 5
preload_app = False
accesslog = '-'
errorlog = '-'
capture_output = True


def post_worker_init(worker):
    from app.services.job_queue import start_embedded_worker

    queue_thread = start_embedded_worker()
    if queue_thread is not None:
        worker.log.info('APPAM local queue worker initialized')
    else:
        worker.log.info('APPAM embedded queue worker disabled or using RQ')


def worker_exit(server, worker):
    from app.services.job_queue import stop_embedded_worker

    stop_embedded_worker(timeout=min(20, graceful_timeout))
