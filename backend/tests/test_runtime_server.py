import unittest
from unittest import mock

from app.services import local_executor


class _FinishedThread:
    def __init__(self):
        self.joined_with = None
        self.alive = True

    def join(self, timeout=None):
        self.joined_with = timeout
        self.alive = False

    def is_alive(self):
        return self.alive


class RuntimeServerTests(unittest.TestCase):
    def test_worker_shutdown_requests_active_job_cancellation(self):
        original_thread = local_executor._WORKER_THREAD
        original_job_id = local_executor._WORKER_STATE['current_job_id']
        fake_thread = _FinishedThread()
        local_executor._WORKER_THREAD = fake_thread
        local_executor._WORKER_STATE['current_job_id'] = 'active-job'
        try:
            with mock.patch.object(local_executor, 'request_cancel') as request_cancel:
                local_executor.stop_embedded_worker(timeout=7)
            request_cancel.assert_called_once_with('active-job')
            self.assertEqual(fake_thread.joined_with, 7)
            self.assertIsNone(local_executor._WORKER_THREAD)
        finally:
            local_executor._WORKER_THREAD = original_thread
            local_executor._WORKER_STATE['current_job_id'] = original_job_id


if __name__ == '__main__':
    unittest.main()
