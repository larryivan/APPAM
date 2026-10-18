import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / 'backend'

TEST_TEMP_DIR = tempfile.mkdtemp(prefix='appam-socket-origin-tests-')
os.environ.setdefault('APPAM_DB_PATH', str(Path(TEST_TEMP_DIR) / 'app_database.db'))
os.environ.setdefault('FLASK_SECRET_KEY', 'appam-test-secret')
os.environ.setdefault('SOCKETIO_ASYNC_MODE', 'threading')
os.environ.setdefault('APPAM_DISABLE_EMBEDDED_WORKER', 'true')

sys.path.insert(0, str(BACKEND_DIR))

from app import create_app  # noqa: E402

HANDSHAKE = '/socket.io/?EIO=4&transport=polling'


class SocketOriginTests(unittest.TestCase):
    """Terminal websockets follow the same origin rule as the HTTP API."""

    def setUp(self):
        self.client = create_app().test_client()

    def handshake(self, origin, host='127.0.0.1:25079', **headers):
        return self.client.get(HANDSHAKE, headers={'Origin': origin, 'Host': host, **headers})

    def test_same_origin_is_accepted_even_when_other_origins_are_listed(self):
        with mock.patch.dict(os.environ, {'APPAM_ALLOWED_ORIGINS': 'https://appam.example'}):
            response = self.handshake('http://127.0.0.1:25079')
        self.assertEqual(response.status_code, 200)

    def test_listed_origin_is_accepted(self):
        with mock.patch.dict(os.environ, {'APPAM_ALLOWED_ORIGINS': 'http://localhost:25078'}):
            response = self.handshake('http://localhost:25078')
        self.assertEqual(response.status_code, 200)

    def test_foreign_origin_and_websocket_scheme_origin_are_rejected(self):
        # A dev proxy that rewrites Origin to its ws:// target is not same-origin.
        with mock.patch.dict(os.environ, {'APPAM_ALLOWED_ORIGINS': ''}):
            self.assertEqual(self.handshake('https://untrusted.example').status_code, 400)
            self.assertEqual(self.handshake('ws://127.0.0.1:25079').status_code, 400)

    def test_forwarded_host_counts_only_behind_a_trusted_proxy(self):
        forwarded = {'X-Forwarded-Proto': 'https', 'X-Forwarded-Host': 'appam.example'}
        with mock.patch.dict(os.environ, {'APPAM_ALLOWED_ORIGINS': '', 'APPAM_TRUST_PROXY_HEADERS': 'false'}):
            self.assertEqual(self.handshake('https://appam.example', **forwarded).status_code, 400)
        with mock.patch.dict(os.environ, {'APPAM_ALLOWED_ORIGINS': '', 'APPAM_TRUST_PROXY_HEADERS': 'true'}):
            self.assertEqual(self.handshake('https://appam.example', **forwarded).status_code, 200)


if __name__ == '__main__':
    unittest.main()
