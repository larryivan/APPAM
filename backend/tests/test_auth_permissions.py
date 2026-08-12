import hashlib
import json
from io import BytesIO
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
import yaml
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / 'backend'
os.chdir(BACKEND_DIR)

TEST_TEMP_DIR = tempfile.mkdtemp(prefix='appam-auth-tests-')
os.environ.setdefault('APPAM_DB_PATH', str(Path(TEST_TEMP_DIR) / 'app_database.db'))
os.environ.setdefault('FLASK_SECRET_KEY', 'appam-test-secret')
os.environ.setdefault('SOCKETIO_ASYNC_MODE', 'threading')
os.environ.setdefault('APPAM_DISABLE_EMBEDDED_WORKER', 'true')
os.environ.setdefault('APPAM_ALLOW_REGISTRATION', 'true')
os.environ.setdefault('APPAM_ALLOW_FIRST_USER_ADMIN', 'true')

sys.path.insert(0, str(BACKEND_DIR))

from app import create_app  # noqa: E402
from app.database import DATABASE_FILE, get_db_connection, init_db  # noqa: E402


class AuthPermissionApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.projects_dir = BACKEND_DIR / 'projects'
        cls.projects_dir.mkdir(exist_ok=True)
        cls.initial_project_dirs = {
            path.name for path in cls.projects_dir.iterdir() if path.is_dir()
        }

    def setUp(self):
        for name in (
            'APPAM_BOOTSTRAP_ADMINS',
            'APPAM_BOOTSTRAP_ADMINS_JSON',
            'APPAM_BOOTSTRAP_ADMIN_RESET_PASSWORDS',
        ):
            os.environ.pop(name, None)
        db_path = Path(DATABASE_FILE)
        if db_path.exists():
            db_path.unlink()
        init_db()

        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def tearDown(self):
        for path in self.projects_dir.iterdir():
            if path.is_dir() and path.name not in self.initial_project_dirs:
                shutil.rmtree(path, ignore_errors=True)

    def register(self, client, username, password='password123', display_name=''):
        response = client.post(
            '/api/auth/register',
            json={
                'username': username,
                'password': password,
                'display_name': display_name,
            },
        )
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        return response.get_json()['user']

    def login(self, client, username, password='password123'):
        return client.post(
            '/api/auth/login',
            json={'username': username, 'password': password},
        )

    def logout(self, client):
        return client.post('/api/auth/logout')

    def create_project(self, client, name='Test Project'):
        response = client.post(
            '/api/projects/',
            json={
                'name': name,
                'description': 'Project for tests',
            },
        )
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        return response.get_json()

    def test_health_endpoint_is_public_and_minimal(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': 'ok', 'service': 'appam-backend'})

    def test_parameter_fill_health_is_authenticated_and_reflects_opencode(self):
        unauthenticated = self.client.get('/api/parameter-fill/health')
        self.assertEqual(unauthenticated.status_code, 401)

        self.register(self.client, 'parameteradmin')
        with mock.patch(
            'app.api.parameter_fill.routes.opencode_service.health',
            return_value={'available': False, 'version': ''},
        ):
            response = self.client.get(
                '/api/parameter-fill/health',
                headers={'Origin': 'https://untrusted.example'},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {
            'available': False,
            'service': 'parameter_fill',
            'status': 'unavailable',
            'version': '',
        })
        self.assertIsNone(response.headers.get('Access-Control-Allow-Origin'))

    def test_parameter_fill_rejects_invalid_json(self):
        self.register(self.client, 'parameterjsonadmin')
        response = self.client.post(
            '/api/parameter-fill/suggest',
            data='not-json',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['error'], 'A JSON object is required')

    def test_project_persists_and_validates_analysis_workflow(self):
        self.register(self.client, 'workflow-owner', display_name='Workflow Owner')

        created = self.client.post(
            '/api/projects/',
            json={
                'name': 'Ancient metagenomics study',
                'creator': 'Forged creator',
                'analysis_workflow': 'appam-smk',
            },
        )
        self.assertEqual(created.status_code, 201, created.get_data(as_text=True))
        project = created.get_json()
        self.assertEqual(project['analysis_workflow'], 'appam-smk')
        self.assertEqual(project['creator'], 'Workflow Owner')

        updated = self.client.put(
            f"/api/projects/{project['id']}",
            json={'analysis_workflow': 'appam-paleoproteomics'},
        )
        self.assertEqual(updated.status_code, 200, updated.get_data(as_text=True))
        self.assertEqual(updated.get_json()['analysis_workflow'], 'appam-paleoproteomics')

        cleared = self.client.put(
            f"/api/projects/{project['id']}",
            json={'analysis_workflow': ''},
        )
        self.assertEqual(cleared.status_code, 200, cleared.get_data(as_text=True))
        self.assertIsNone(cleared.get_json()['analysis_workflow'])

        invalid = self.client.post(
            '/api/projects/',
            json={'name': 'Invalid workflow', 'analysis_workflow': 'unknown'},
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.get_json()['error'], 'Unsupported analysis workflow')

    def test_dry_run_cannot_bypass_queue_limits(self):
        self.register(self.client, 'queueadmin')
        project = self.create_project(self.client, name='Queue limits')
        with mock.patch.dict(
            os.environ,
            {
                'APPAM_MAX_GLOBAL_QUEUED': '0',
                'APPAM_MAX_PROJECT_QUEUED': '10',
                'APPAM_MAX_USER_QUEUED': '10',
            },
            clear=False,
        ):
            response = self.client.post(
                f"/api/pipeline/{project['id']}/run/demo",
                json={'dry_run': True},
            )
        self.assertEqual(response.status_code, 409)
        self.assertIn('Global queue limit reached', response.get_json()['error'])

    def test_opencode_api_sessions_deny_tools_by_default(self):
        from app.services.opencode_service import OpenCodeService

        with mock.patch.dict(os.environ, {'OPENCODE_PERMISSIONS': ''}, clear=False):
            service = OpenCodeService()
        self.assertEqual(service.agent, 'plan')
        self.assertEqual(service._permission_rules(), [
            {'permission': '*', 'pattern': '*', 'action': 'deny'},
        ])

    def test_sqlite_uses_wal_for_local_queue_concurrency(self):
        conn = get_db_connection()
        try:
            journal_mode = conn.execute('PRAGMA journal_mode').fetchone()[0]
            busy_timeout = conn.execute('PRAGMA busy_timeout').fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(journal_mode.lower(), 'wal')
        self.assertEqual(busy_timeout, 30000)

    def test_bootstrap_admins_from_environment(self):
        db_path = Path(DATABASE_FILE)
        if db_path.exists():
            db_path.unlink()

        bootstrap_admins = [
            {
                'username': 'labadmin',
                'password': 'labpassword123',
                'display_name': 'Lab Admin',
            },
            {
                'username': 'piadmin',
                'password': 'pipassword123',
                'display_name': 'PI Admin',
            },
        ]
        with mock.patch.dict(
            os.environ,
            {'APPAM_BOOTSTRAP_ADMINS_JSON': json.dumps(bootstrap_admins)},
            clear=False,
        ):
            app = create_app()
            app.config.update(TESTING=True)
            client = app.test_client()

        conn = get_db_connection()
        try:
            rows = conn.execute(
                '''
                SELECT username, display_name, role, status
                FROM users
                ORDER BY username
                '''
            ).fetchall()
        finally:
            conn.close()

        users = {row['username']: dict(row) for row in rows}
        self.assertEqual(users['labadmin']['role'], 'admin')
        self.assertEqual(users['labadmin']['status'], 'active')
        self.assertEqual(users['piadmin']['display_name'], 'PI Admin')

        for username, password in [
            ('labadmin', 'labpassword123'),
            ('piadmin', 'pipassword123'),
        ]:
            response = client.post(
                '/api/auth/login',
                json={'username': username, 'password': password},
            )
            self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
            self.logout(client)

    def test_production_registration_policy_and_admin_user_creation(self):
        with mock.patch.dict(os.environ, {'APPAM_ALLOW_REGISTRATION': 'false'}, clear=False):
            blocked = self.client.post(
                '/api/auth/register',
                json={'username': 'blockeduser', 'password': 'password123'},
            )
        self.assertEqual(blocked.status_code, 403)

        admin = self.register(self.client, 'provisionadmin')
        self.assertEqual(admin['role'], 'admin')
        created = self.client.post(
            '/api/admin/users',
            json={
                'username': 'manageduser',
                'password': 'managedpassword123',
                'display_name': 'Managed User',
                'role': 'user',
            },
        )
        self.assertEqual(created.status_code, 201, created.get_data(as_text=True))
        self.assertEqual(created.get_json()['user']['role'], 'user')

    def test_cross_site_state_changing_request_is_rejected(self):
        self.register(self.client, 'csrfadmin')
        response = self.client.post(
            '/api/projects/',
            json={'name': 'Blocked project'},
            headers={'Sec-Fetch-Site': 'cross-site'},
        )
        self.assertEqual(response.status_code, 403)

    def test_trusted_proxy_preserves_https_same_origin(self):
        with mock.patch.dict(os.environ, {
            'APPAM_TRUST_PROXY_HEADERS': 'true',
            'APPAM_ALLOWED_ORIGINS': '',
        }, clear=False):
            proxy_app = create_app()
            proxy_app.config.update(TESTING=True)
            proxy_client = proxy_app.test_client()
            response = proxy_client.post(
                '/api/auth/register',
                json={'username': 'proxyuser', 'password': 'password123'},
                headers={
                    'Origin': 'https://appam.example:25078',
                    'X-Forwarded-Proto': 'https',
                    'X-Forwarded-Host': 'appam.example:25078',
                },
            )
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))

    def test_remote_download_rejects_private_network_and_ftp(self):
        from app.services.url_security import validate_remote_url

        with self.assertRaisesRegex(ValueError, 'non-public'):
            validate_remote_url('http://127.0.0.1/private')
        with self.assertRaisesRegex(ValueError, 'require'):
            validate_remote_url('ftp://example.com/data.fastq.gz')

    def test_chunk_upload_validates_bounds_and_reassembles_streams(self):
        self.register(self.client, 'uploadadmin')
        project = self.create_project(self.client, name='Chunk upload')
        endpoint = f"/api/filemanager/{project['id']}/upload-chunk"

        invalid = self.client.post(
            endpoint,
            data={
                'file': (BytesIO(b'invalid'), 'chunk'),
                'path': '.',
                'filename': 'reads.fastq.gz',
                'chunkNumber': '0',
                'totalChunks': '2',
            },
            content_type='multipart/form-data',
        )
        self.assertEqual(invalid.status_code, 400)

        for number, content in ((1, b'first-'), (2, b'second')):
            response = self.client.post(
                endpoint,
                data={
                    'file': (BytesIO(content), f'chunk-{number}'),
                    'path': '.',
                    'filename': 'reads.fastq.gz',
                    'chunkNumber': str(number),
                    'totalChunks': '2',
                },
                content_type='multipart/form-data',
            )
            self.assertEqual(response.status_code, 200, response.get_data(as_text=True))

        uploaded = self.projects_dir / project['id'] / 'reads.fastq.gz'
        self.assertEqual(uploaded.read_bytes(), b'first-second')

        with mock.patch.dict(os.environ, {'APPAM_MAX_UPLOAD_CHUNK_BYTES': '4'}, clear=False):
            oversized = self.client.post(
                endpoint,
                data={
                    'file': (BytesIO(b'12345'), 'chunk-large'),
                    'path': '.',
                    'filename': 'too-large.fastq.gz',
                    'chunkNumber': '1',
                    'totalChunks': '1',
                },
                content_type='multipart/form-data',
            )
        self.assertEqual(oversized.status_code, 413)
        self.assertFalse((self.projects_dir / project['id'] / 'too-large.fastq.gz').exists())

    def test_parallel_download_rejects_declared_oversize_file(self):
        from app.services import download_manager

        task = download_manager.DownloadTask('oversize', 'https://example.com/large.fastq.gz', 'large.fastq.gz', 'project', '.', True)
        with mock.patch.dict(os.environ, {'APPAM_MAX_REMOTE_DOWNLOAD_BYTES': '10'}, clear=False), mock.patch.object(
            download_manager,
            'get_content_info',
            return_value={
                'supports_resume': True,
                'content_length': 11,
                'content_type': 'application/gzip',
                'filename': 'large.fastq.gz',
            },
        ):
            download_manager.multi_thread_download(task)
        self.assertEqual(task.status, 'error')
        self.assertIn('size limit', task.error)

    def test_retry_rejects_changed_frozen_input(self):
        from app.services.pipeline_execution import _verify_source_inputs
        from app.services.provenance import fingerprint_path

        self.register(self.client, 'driftadmin')
        project = self.create_project(self.client, name='Input drift project')
        project_dir = self.projects_dir / project['id']
        input_path = project_dir / 'sample_R1.fastq.gz'
        input_path.write_bytes(b'original')
        original = fingerprint_path(input_path, 'metadata')
        original.update({'sample_id': 'S1', 'input_role': 'forward_reads'})
        manifest_path = project_dir / 'source-manifest.json'
        manifest_path.write_text(json.dumps({'inputs': [original]}), encoding='utf-8')

        input_path.write_bytes(b'changed-and-longer')
        current = fingerprint_path(input_path, 'metadata')
        current.update({'sample_id': 'S1', 'input_role': 'forward_reads'})
        with self.assertRaisesRegex(ValueError, 'Frozen workflow inputs changed'):
            _verify_source_inputs(
                project['id'],
                {'manifest_path': str(manifest_path)},
                [current],
            )

    def test_profile_and_password_management(self):
        user = self.register(self.client, 'adminuser', display_name='Admin User')
        self.assertEqual(user['role'], 'admin')

        me_response = self.client.get('/api/auth/me')
        self.assertEqual(me_response.status_code, 200)
        self.assertTrue(me_response.get_json()['authenticated'])

        profile_response = self.client.put('/api/auth/profile', json={'display_name': 'Principal Investigator'})
        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(profile_response.get_json()['user']['display_name'], 'Principal Investigator')

        wrong_password_response = self.client.post(
            '/api/auth/password',
            json={
                'current_password': 'wrong-password',
                'new_password': 'newpassword123',
            },
        )
        self.assertEqual(wrong_password_response.status_code, 400)

        password_response = self.client.post(
            '/api/auth/password',
            json={
                'current_password': 'password123',
                'new_password': 'newpassword123',
            },
        )
        self.assertEqual(password_response.status_code, 200)

        self.logout(self.client)
        old_login_response = self.login(self.client, 'adminuser', 'password123')
        self.assertEqual(old_login_response.status_code, 401)

        new_login_response = self.login(self.client, 'adminuser', 'newpassword123')
        self.assertEqual(new_login_response.status_code, 200)

    def test_login_rate_limit_and_audit_log(self):
        self.register(self.client, 'ratelimit')
        self.logout(self.client)

        for _ in range(5):
            response = self.login(self.client, 'ratelimit', 'wrongpassword')
            self.assertEqual(response.status_code, 401)

        blocked_response = self.login(self.client, 'ratelimit', 'wrongpassword')
        self.assertEqual(blocked_response.status_code, 429)

        conn = get_db_connection()
        try:
            rows = conn.execute(
                '''
                SELECT event_type, COUNT(*) AS count
                FROM auth_audit_log
                WHERE username = ?
                GROUP BY event_type
                ''',
                ('ratelimit',)
            ).fetchall()
        finally:
            conn.close()

        audit_counts = {row['event_type']: row['count'] for row in rows}
        self.assertEqual(audit_counts.get('login_failed'), 5)
        self.assertEqual(audit_counts.get('login_rate_limited'), 1)

    def test_admin_controls_user_status_and_session_invalidation(self):
        admin_client = self.app.test_client()
        user_client = self.app.test_client()

        admin = self.register(admin_client, 'platformadmin')
        self.logout(admin_client)
        target_user = self.register(user_client, 'disableduser', display_name='Disable Me')

        non_admin_access = user_client.get('/api/admin/users')
        self.assertEqual(non_admin_access.status_code, 403)

        login_admin = self.login(admin_client, admin['username'])
        self.assertEqual(login_admin.status_code, 200)

        disable_response = admin_client.patch(
            f"/api/admin/users/{target_user['id']}",
            json={'status': 'disabled'},
        )
        self.assertEqual(disable_response.status_code, 200)
        self.assertEqual(disable_response.get_json()['user']['status'], 'disabled')

        me_response = user_client.get('/api/auth/me')
        self.assertEqual(me_response.status_code, 200)
        self.assertFalse(me_response.get_json()['authenticated'])

        projects_response = user_client.get('/api/projects/')
        self.assertEqual(projects_response.status_code, 401)

        disabled_login = self.login(user_client, target_user['username'])
        self.assertEqual(disabled_login.status_code, 403)

    def test_project_membership_permissions_and_submitted_by_tracking(self):
        admin_client = self.app.test_client()
        owner_client = self.app.test_client()
        viewer_client = self.app.test_client()
        editor_client = self.app.test_client()

        self.register(admin_client, 'rootadmin')
        self.logout(admin_client)
        owner = self.register(owner_client, 'owneruser', display_name='Owner')
        self.logout(owner_client)
        viewer = self.register(viewer_client, 'vieweruser', display_name='Viewer')
        self.logout(viewer_client)
        editor = self.register(editor_client, 'editoruser', display_name='Editor')
        self.logout(editor_client)

        self.login(owner_client, owner['username'])
        project = self.create_project(owner_client, name='Ancient Metaomics')

        add_viewer = owner_client.post(
            f"/api/projects/{project['id']}/members",
            json={'user_id': viewer['id'], 'role': 'viewer'},
        )
        self.assertEqual(add_viewer.status_code, 201, add_viewer.get_data(as_text=True))

        add_editor = owner_client.post(
            f"/api/projects/{project['id']}/members",
            json={'user_id': editor['id'], 'role': 'editor'},
        )
        self.assertEqual(add_editor.status_code, 201, add_editor.get_data(as_text=True))

        self.login(viewer_client, viewer['username'])
        viewer_projects = viewer_client.get('/api/projects/')
        self.assertEqual(viewer_projects.status_code, 200)
        self.assertEqual(viewer_projects.get_json()[0]['access_role'], 'viewer')

        viewer_pipeline = viewer_client.post(f"/api/pipeline/{project['id']}/run/demo", json={})
        self.assertEqual(viewer_pipeline.status_code, 403)

        viewer_edit = viewer_client.put(
            f"/api/projects/{project['id']}",
            json={'name': 'Should Not Work'},
        )
        self.assertEqual(viewer_edit.status_code, 404)

        viewer_download = viewer_client.post(
            f"/api/filemanager/{project['id']}/download-url",
            json={'url': 'https://example.org/sample.fastq.gz'},
        )
        self.assertEqual(viewer_download.status_code, 404)

        self.login(editor_client, editor['username'])
        with mock.patch('app.api.pipeline.routes.get_tool_definition', return_value={
                'id': 'demo',
                'tool_name': 'Demo',
                'parameters': [],
            }), mock.patch('app.api.pipeline.routes.build_job_request', return_value={
                'display_command': 'demo --run',
                'log_path': str(self.projects_dir / project['id'] / 'logs' / 'demo.log'),
                'output_path': None,
                'work_dir': str(self.projects_dir / project['id']),
                'execution_mode': 'command',
                'workflow_id': None,
                'workflow_run_id': None,
                'is_dry_run': False,
                'workflow_run_spec': None,
                'command_spec': {
                    'argv': ['demo', '--run'],
                    'cwd': str(self.projects_dir / project['id']),
                },
            }), mock.patch('app.api.pipeline.routes.get_active_job', return_value=None), mock.patch(
            'app.api.pipeline.routes.enqueue_pipeline_job'
        ) as enqueue_mock:
            run_response = editor_client.post(f"/api/pipeline/{project['id']}/run/demo", json={})
            self.assertEqual(run_response.status_code, 200, run_response.get_data(as_text=True))
            enqueue_mock.assert_called_once()
            _, kwargs = enqueue_mock.call_args
            self.assertEqual(kwargs['submitted_by'], editor['id'])

        editor_job_id = 'job-submit-1'
        from app.services.job_store import create_job, list_process_history

        create_job(
            'owner-job',
            project['id'],
            'Owner Job',
            'owner-job',
            str(self.projects_dir / project['id'] / 'logs' / 'owner-job.log'),
            submitted_by=owner['id'],
        )
        forbidden_cancel = editor_client.post('/api/jobs/owner-job/cancel')
        self.assertEqual(forbidden_cancel.status_code, 403)

        create_job(
            editor_job_id,
            project['id'],
            'Demo',
            'demo',
            str(self.projects_dir / project['id'] / 'logs' / 'job-submit-1.log'),
            submitted_by=editor['id'],
        )
        history = list_process_history(project['id'])
        self.assertEqual(history[0]['submitted_by'], editor['id'])
        self.assertEqual(history[0]['submitted_by_username'], editor['username'])

    def test_admin_password_reset_and_user_impact_workflow(self):
        admin_client = self.app.test_client()
        impact_client = self.app.test_client()
        owner_client = self.app.test_client()
        participant_client = self.app.test_client()

        admin = self.register(admin_client, 'superadmin')
        self.logout(admin_client)
        impact_user = self.register(impact_client, 'impactuser', display_name='Impact User')
        self.logout(impact_client)
        other_owner = self.register(owner_client, 'otherowner', display_name='Other Owner')
        self.logout(owner_client)
        deletable_user = self.register(participant_client, 'deletable', display_name='Delete Me')
        self.logout(participant_client)

        self.login(impact_client, impact_user['username'])
        owned_project = self.create_project(impact_client, name='Owned Project')
        self.logout(impact_client)

        self.login(owner_client, other_owner['username'])
        shared_project = self.create_project(owner_client, name='Shared Project')
        add_impact_user = owner_client.post(
            f"/api/projects/{shared_project['id']}/members",
            json={'user_id': impact_user['id'], 'role': 'editor'},
        )
        self.assertEqual(add_impact_user.status_code, 201)
        add_deletable_user = owner_client.post(
            f"/api/projects/{shared_project['id']}/members",
            json={'user_id': deletable_user['id'], 'role': 'viewer'},
        )
        self.assertEqual(add_deletable_user.status_code, 201)

        self.login(admin_client, admin['username'])

        impact_details = admin_client.get(f"/api/admin/users/{impact_user['id']}")
        self.assertEqual(impact_details.status_code, 200)
        impact_payload = impact_details.get_json()
        self.assertEqual(impact_payload['impact']['owned_projects_count'], 1)
        self.assertEqual(impact_payload['impact']['member_projects_count'], 1)
        self.assertFalse(impact_payload['impact']['can_delete'])
        self.assertTrue(impact_payload['impact']['warnings'])

        reset_response = admin_client.post(f"/api/admin/users/{impact_user['id']}/reset-password", json={})
        self.assertEqual(reset_response.status_code, 200)
        temporary_password = reset_response.get_json()['temporary_password']
        self.assertTrue(temporary_password)

        old_login = self.login(impact_client, impact_user['username'], 'password123')
        self.assertEqual(old_login.status_code, 401)

        temp_login = self.login(impact_client, impact_user['username'], temporary_password)
        self.assertEqual(temp_login.status_code, 200)
        self.logout(impact_client)

        delete_owned_response = admin_client.delete(f"/api/admin/users/{impact_user['id']}")
        self.assertEqual(delete_owned_response.status_code, 400)
        self.assertFalse(delete_owned_response.get_json()['impact']['can_delete'])

        deletable_details = admin_client.get(f"/api/admin/users/{deletable_user['id']}")
        self.assertEqual(deletable_details.status_code, 200)
        deletable_payload = deletable_details.get_json()
        self.assertEqual(deletable_payload['impact']['owned_projects_count'], 0)
        self.assertEqual(deletable_payload['impact']['member_projects_count'], 1)
        self.assertTrue(deletable_payload['impact']['can_delete'])

        delete_response = admin_client.delete(f"/api/admin/users/{deletable_user['id']}")
        self.assertEqual(delete_response.status_code, 200)

        deleted_lookup = admin_client.get(f"/api/admin/users/{deletable_user['id']}")
        self.assertEqual(deleted_lookup.status_code, 404)

        deleted_login = self.login(participant_client, deletable_user['username'], 'password123')
        self.assertEqual(deleted_login.status_code, 401)

    def test_tools_catalog_includes_workflows_and_paleoproteomics(self):
        self.register(self.client, 'catalogadmin', display_name='Catalog Admin')

        response = self.client.get('/api/tools')
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()

        self.assertTrue(payload['success'])
        section_ids = {section['id'] for section in payload['sections']}
        self.assertIn('paleoproteomics', section_ids)
        self.assertIn('workflow-automation', section_ids)

        tools_by_key = payload['tools_by_key']
        self.assertIn('workflow-appam-smk', tools_by_key)
        self.assertIn('workflow-appam-paleoproteomics', tools_by_key)
        self.assertEqual(tools_by_key['workflow-appam-smk']['kind'], 'workflow')
        self.assertEqual(tools_by_key['workflow-appam-paleoproteomics']['section'], 'workflow-automation')

    def test_runtime_path_overrides_are_hidden_and_rejected_for_regular_users(self):
        admin_client = self.app.test_client()
        user_client = self.app.test_client()
        admin = self.register(admin_client, 'runtimeadmin')
        self.logout(admin_client)
        user = self.register(user_client, 'runtimeuser')
        self.logout(user_client)

        self.login(user_client, user['username'])
        project = self.create_project(user_client, name='Runtime Guard')
        user_tools = user_client.get('/api/tools').get_json()['tools_by_key']
        catalog = user_tools['workflow-appam-smk']
        parameter_names = {parameter['name'] for parameter in catalog['parameters']}
        self.assertNotIn('metawrap_env', parameter_names)
        self.assertNotIn('checkm2_db', parameter_names)
        self.assertNotIn('maxquant', user_tools)

        rejected = user_client.post(
            f"/api/pipeline/{project['id']}/run/workflow-appam-smk",
            json={'metawrap_env': '/tmp/user-controlled-environment'},
        )
        self.assertEqual(rejected.status_code, 400)
        self.assertTrue(any('restricted to administrators' in item for item in rejected.get_json()['details']))

        maxquant_rejected = user_client.post(f"/api/pipeline/{project['id']}/run/maxquant", json={})
        self.assertEqual(maxquant_rejected.status_code, 403)

        self.login(admin_client, admin['username'])
        admin_catalog = admin_client.get('/api/tools').get_json()['tools_by_key']['workflow-appam-smk']
        admin_parameter_names = {parameter['name'] for parameter in admin_catalog['parameters']}
        self.assertIn('metawrap_env', admin_parameter_names)
        self.assertIn('maxquant', admin_client.get('/api/tools').get_json()['tools_by_key'])

    def test_admin_worker_status_endpoint_reports_local_executor(self):
        self.register(self.client, 'workeradmin', display_name='Worker Admin')
        response = self.client.get('/api/system/worker')
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['data']['mode'], 'local-db')
        self.assertIn('worker', payload['data'])
        self.assertIn('counts', payload['data'])

    def test_admin_readiness_endpoint_separates_core_and_publication_status(self):
        self.register(self.client, 'readinessadmin', display_name='Readiness Admin')
        response = self.client.get('/api/system/readiness')
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()
        self.assertTrue(payload['success'])
        self.assertIn('ready', payload['data'])
        self.assertIn('publication_ready', payload['data'])
        self.assertEqual(
            [group['id'] for group in payload['data']['groups']],
            ['platform', 'metagenomics', 'paleoproteomics', 'publication'],
        )

    def test_readiness_report_is_self_describing_and_lists_blocker_ids(self):
        self.register(self.client, 'archiveadmin', display_name='Archive Admin')
        report = self.client.get('/api/system/readiness').get_json()['data']
        self.assertEqual(report['schema_version'], 1)
        self.assertEqual(report['scope'], 'host_environment')
        environment = report['environment']
        self.assertTrue(environment['generated_at'].endswith('Z'))
        for field in ('repository', 'commit', 'dirty', 'python_version', 'platform', 'machine'):
            self.assertIn(field, environment)
        # Host-personal locations carry no reproducibility information.
        self.assertNotIn('status', environment)
        self.assertNotIn('python_executable', environment)

        checks_by_id = {
            check['id']: check
            for group in report['groups']
            for check in group['checks']
        }
        self.assertIn('software_checkout', checks_by_id)
        for check_id in report['core_blockers'] + report['publication_blockers']:
            self.assertEqual(checks_by_id[check_id]['status'], 'error')
        self.assertEqual(len(report['core_blockers']), report['summary']['core_blockers'])
        self.assertEqual(len(report['publication_blockers']), report['summary']['publication_blockers'])
        self.assertEqual(report['ready'], not report['core_blockers'])
        self.assertEqual(report['publication_ready'], not report['publication_blockers'])

    def test_job_log_tail_and_result_artifact_project_paths(self):
        from app.services.job_store import create_job

        owner = self.register(self.client, 'resultowner', display_name='Result Owner')
        project = self.create_project(self.client, name='Result project')
        project_dir = self.projects_dir / project['id']
        result_file = project_dir / 'workflow_runs' / 'demo' / 'results' / 'summary.tsv'
        result_file.parent.mkdir(parents=True, exist_ok=True)
        result_file.write_text('name\tvalue\nreads\t12\n', encoding='utf-8')
        outside_file = Path(TEST_TEMP_DIR) / 'outside-result.tsv'
        outside_file.write_text('outside\n', encoding='utf-8')
        log_path = project_dir / 'logs' / 'result-job.log'
        log_path.parent.mkdir(exist_ok=True)
        log_path.write_text('0123456789', encoding='utf-8')

        create_job(
            'result-job',
            project['id'],
            'APPAM-SMK',
            'snakemake',
            str(log_path),
            status='completed',
            submitted_by=owner['id'],
            workflow_id='appam-smk',
            workflow_run_id='result-run',
            workflow_run_spec={
                'id': 'result-run',
                'job_id': 'result-job',
                'project_id': project['id'],
                'workflow_id': 'appam-smk',
                'tool_name': 'APPAM-SMK',
                'status': 'completed',
                'submitted_by': owner['id'],
                'artifacts': [
                    {'label': 'Summary', 'path': str(result_file), 'kind': 'summary', 'size_bytes': result_file.stat().st_size},
                    {'label': 'Outside', 'path': str(outside_file), 'kind': 'summary', 'size_bytes': outside_file.stat().st_size},
                ],
            },
        )

        log_response = self.client.get('/api/jobs/result-job/logs?tail=4&limit=4')
        self.assertEqual(log_response.status_code, 200)
        self.assertEqual(log_response.get_json()['content'], '6789')
        self.assertEqual(log_response.get_json()['offset'], 10)
        self.assertTrue(log_response.get_json()['eof'])
        self.assertTrue(log_response.get_json()['reset'])

        reset_response = self.client.get('/api/jobs/result-job/logs?offset=999&limit=20')
        self.assertEqual(reset_response.get_json()['content'], '0123456789')
        self.assertTrue(reset_response.get_json()['reset'])

        runs_response = self.client.get(
            f"/api/pipeline/{project['id']}/workflow-runs?workflow_id=appam-smk"
        )
        artifacts = runs_response.get_json()['workflow_runs'][0]['artifacts']
        artifacts_by_label = {artifact['label']: artifact for artifact in artifacts}
        self.assertEqual(
            artifacts_by_label['Summary']['project_path'],
            'workflow_runs/demo/results/summary.tsv',
        )
        self.assertIsNone(artifacts_by_label['Outside']['project_path'])

        summary_response = self.client.get(
            f"/api/pipeline/{project['id']}/workflow-runs?workflow_id=appam-smk&include_results=false"
        )
        summary_run = summary_response.get_json()['workflow_runs'][0]
        self.assertNotIn('artifacts', summary_run)
        self.assertNotIn('metrics', summary_run)

    def _open_terminal_session(self, session_key, project_id, owner_id, client_id):
        from app.api.terminal.routes import TerminalSession, client_sessions, terminal_sessions

        session = TerminalSession(
            session_key,
            str(self.projects_dir / project_id),
            owner_user_id=owner_id,
            project_id=project_id,
        )
        session.add_client(client_id)
        terminal_sessions[session_key] = session
        client_sessions[client_id] = session_key
        return session

    def test_terminal_sessions_end_when_admin_privileges_are_revoked(self):
        from flask import request, session as flask_session
        from app.api.terminal import routes as terminal_routes

        admin = self.register(self.client, 'terminalkeeper')
        self.logout(self.client)
        operator_client = self.app.test_client()
        operator = self.register(operator_client, 'terminaloperator')
        self.logout(operator_client)

        self.login(self.client, admin['username'])
        promotion = self.client.patch(f"/api/admin/users/{operator['id']}", json={'role': 'admin'})
        self.assertEqual(promotion.status_code, 200, promotion.get_data(as_text=True))

        self.login(operator_client, operator['username'])
        project = self.create_project(operator_client, name='Terminal Guard')

        def replay(handler, payload):
            """Replay one terminal socket event as the operator.

            Returns (direct emits to this client, broadcasts to the session room).
            """
            with self.app.test_request_context('/socket.io/'):
                flask_session['user_id'] = operator['id']
                request.sid = 'terminal-client'
                with mock.patch.object(terminal_routes, 'emit') as direct:
                    with mock.patch.object(terminal_routes.socketio, 'emit') as room:
                        handler(payload)
                return (
                    [call.args for call in direct.call_args_list],
                    [(call.args, call.kwargs.get('room')) for call in room.call_args_list],
                )

        def send_input():
            return replay(terminal_routes.handle_terminal_input, {'session_key': 'guard-session', 'input': 'whoami\n'})

        try:
            session = self._open_terminal_session(
                'guard-session', project['id'], operator['id'], 'terminal-client'
            )
            with mock.patch.object(session, 'write', return_value=True) as write:
                self.assertEqual(send_input(), ([], []))
            write.assert_called_once_with('whoami\n')

            demotion = self.client.patch(f"/api/admin/users/{operator['id']}", json={'role': 'user'})
            self.assertEqual(demotion.status_code, 200, demotion.get_data(as_text=True))
            self.assertNotIn('guard-session', terminal_routes.terminal_sessions)
            self.assertNotIn('terminal-client', terminal_routes.client_sessions)
            self.assertTrue(session.closed)

            # Even if a session outlives the revocation, every socket event
            # re-checks privileges instead of trusting the connect-time decision.
            for handler, payload in (
                (terminal_routes.handle_terminal_input, {'session_key': 'guard-session', 'input': 'whoami\n'}),
                (terminal_routes.handle_terminal_resize, {'session_key': 'guard-session', 'rows': 40, 'cols': 100}),
            ):
                with self.subTest(handler=handler.__name__):
                    survivor = self._open_terminal_session(
                        'guard-session', project['id'], operator['id'], 'terminal-client'
                    )
                    with mock.patch.object(survivor, 'write', return_value=True) as write:
                        with mock.patch.object(survivor, 'resize') as resize:
                            direct, broadcasts = replay(handler, payload)
                    write.assert_not_called()
                    resize.assert_not_called()

                    # The room is told exactly once, so the panel reports the reason
                    # and stops waiting instead of freezing.
                    self.assertEqual(direct, [])
                    self.assertEqual(
                        broadcasts,
                        [
                            (
                                ('terminal_error', {'error': 'Terminal access requires admin privileges'}),
                                'terminal:guard-session',
                            ),
                            (
                                ('terminal_exit', {'session_key': 'guard-session', 'preset': 'shell'}),
                                'terminal:guard-session',
                            ),
                        ],
                    )
                    self.assertNotIn('guard-session', terminal_routes.terminal_sessions)
                    self.assertNotIn('terminal-client', terminal_routes.client_sessions)
                    self.assertTrue(survivor.closed)

            # A second event for an already-revoked session must not re-notify.
            self.assertEqual(send_input(), ([('terminal_error', {'error': 'Terminal session not found'})], []))
        finally:
            terminal_routes.terminal_sessions.pop('guard-session', None)
            terminal_routes.client_sessions.pop('terminal-client', None)

    def test_system_diagnostics_require_admin(self):
        self.register(self.client, 'diagnosticsadmin')
        self.logout(self.client)
        regular = self.register(self.client, 'diagnosticsuser')
        self.assertEqual(regular['role'], 'user')

        for endpoint in ('/api/system/info', '/api/system/status', '/api/system/recommendations', '/api/system/readiness'):
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 403, endpoint)

    def test_workflow_endpoints_prepare_snakemake_jobs(self):
        owner = self.register(self.client, 'workflowowner', display_name='Workflow Owner')
        project = self.create_project(self.client, name='Workflow Project')

        project_dir = self.projects_dir / project['id']
        project_dir.mkdir(exist_ok=True)
        sample_manifest = project_dir / 'samples.tsv'
        raw_data_dir = project_dir / 'raw'
        sample_manifest.write_text('sample_id\nsample1\n', encoding='utf-8')
        raw_data_dir.mkdir(exist_ok=True)
        (raw_data_dir / 'sample1_R1.fastq.gz').write_text('@sample1/1\nACGT\n+\n!!!!\n', encoding='utf-8')
        (raw_data_dir / 'sample1_R2.fastq.gz').write_text('@sample1/2\nTGCA\n+\n!!!!\n', encoding='utf-8')
        metawrap_env = Path(TEST_TEMP_DIR) / 'envs' / 'metawrap'
        preprocessing_env = Path(TEST_TEMP_DIR) / 'envs' / 'preprocessing'
        mapping_env = Path(TEST_TEMP_DIR) / 'envs' / 'mapping'
        assembly_env = Path(TEST_TEMP_DIR) / 'envs' / 'assembly'
        pydamage_env = Path(TEST_TEMP_DIR) / 'envs' / 'pydamage'
        checkm2_env = Path(TEST_TEMP_DIR) / 'envs' / 'checkm2'
        gunc_env = Path(TEST_TEMP_DIR) / 'envs' / 'gunc'
        gtdbtk_env = Path(TEST_TEMP_DIR) / 'envs' / 'gtdbtk'
        prokka_env = Path(TEST_TEMP_DIR) / 'envs' / 'prokka'
        eggnog_env = Path(TEST_TEMP_DIR) / 'envs' / 'eggnog_py310'
        abricate_env = Path(TEST_TEMP_DIR) / 'envs' / 'abricate'
        antismash_env = Path(TEST_TEMP_DIR) / 'envs' / 'antismash'
        paleoproteomics_env = Path(TEST_TEMP_DIR) / 'envs' / 'paleoproteomics'
        checkm_db = Path(TEST_TEMP_DIR) / 'db' / 'checkm'
        checkm2_db = Path(TEST_TEMP_DIR) / 'db' / 'checkm2'
        gunc_db = Path(TEST_TEMP_DIR) / 'db' / 'gunc'
        gtdbtk_db = Path(TEST_TEMP_DIR) / 'db' / 'gtdbtk_r226'
        eggnog_db = Path(TEST_TEMP_DIR) / 'db' / 'eggnog'
        maxquant_cmd = Path(TEST_TEMP_DIR) / 'maxquant' / 'MaxQuantCmd.dll'
        fasta_path = Path(TEST_TEMP_DIR) / 'references' / 'db.fasta'

        for directory in (
            metawrap_env,
            preprocessing_env,
            mapping_env,
            assembly_env,
            pydamage_env,
            checkm2_env,
            gunc_env,
            gtdbtk_env,
            prokka_env,
            eggnog_env,
            abricate_env,
            antismash_env,
            paleoproteomics_env,
            checkm_db,
            checkm2_db,
            gunc_db,
            gtdbtk_db,
            eggnog_db,
            maxquant_cmd.parent,
            fasta_path.parent,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        maxquant_cmd.write_text('maxquant', encoding='utf-8')
        fasta_path.write_text('>seq\nAAAA\n', encoding='utf-8')

        runtime_env = {
            'APPAM_DATABASES_ROOT': str(fasta_path.parent),
            'APPAM_SNAKEMAKE_BIN': '/bin/echo',
            'APPAM_SMK_METAWRAP_ENV': str(metawrap_env),
            'APPAM_SMK_PREPROCESSING_ENV': str(preprocessing_env),
            'APPAM_SMK_MAPPING_ENV': str(mapping_env),
            'APPAM_SMK_ASSEMBLY_ENV': str(assembly_env),
            'APPAM_SMK_PYDAMAGE_ENV': str(pydamage_env),
            'APPAM_SMK_CHECKM1_DB': str(checkm_db),
            'APPAM_SMK_CHECKM_DB': str(checkm_db),
            'APPAM_SMK_CHECKM2_ENV': str(checkm2_env),
            'APPAM_SMK_CHECKM2_DB': str(checkm2_db),
            'APPAM_SMK_GUNC_ENV': str(gunc_env),
            'APPAM_SMK_GUNC_DB': str(gunc_db),
            'APPAM_SMK_GTDBTK_ENV': str(gtdbtk_env),
            'APPAM_SMK_GTDBTK_DB': str(gtdbtk_db),
            'APPAM_SMK_PROKKA_ENV': str(prokka_env),
            'APPAM_SMK_EGGNOG_ENV': str(eggnog_env),
            'APPAM_SMK_EGGNOG_DB': str(eggnog_db),
            'APPAM_SMK_ABRICATE_ENV': str(abricate_env),
            'APPAM_SMK_ANTISMASH_ENV': str(antismash_env),
            'APPAM_PALEO_MAXQUANT_CMD': str(maxquant_cmd),
            'APPAM_PALEO_ENV': str(paleoproteomics_env),
            'APPAM_PALEO_DOTNET_BIN': '/bin/echo',
            'APPAM_PALEO_THERMO_RAW_FILE_PARSER': '/bin/echo',
            'APPAM_PALEO_TIMSCONVERT_BIN': '/missing/unused-timsconvert',
            'APPAM_PALEO_OPENMS_FILECONVERTER': '/bin/echo',
        }

        mock_queue = mock.Mock()
        with mock.patch.dict(os.environ, runtime_env, clear=False), mock.patch(
            'app.services.job_queue.get_queue', return_value=mock_queue
        ):
            health_response = self.client.get(
                f"/api/pipeline/{project['id']}/runtime-health/workflow-appam-smk"
            )
            self.assertEqual(health_response.status_code, 200, health_response.get_data(as_text=True))
            self.assertTrue(health_response.get_json()['ok'])

            template_response = self.client.post(
                f"/api/pipeline/{project['id']}/workflow-templates/workflow-appam-smk",
                json={},
            )
            self.assertEqual(template_response.status_code, 200, template_response.get_data(as_text=True))
            self.assertTrue(template_response.get_json()['created_files'])

            preflight_response = self.client.post(
                f"/api/pipeline/{project['id']}/preflight/workflow-appam-smk",
                json={
                    'sample_manifest': 'samples.tsv',
                    'raw_data_dir': 'raw',
                    'profile': 'local',
                    'cores': 8,
                    'preprocess_method': 'adapter_removal',
                    'min_contig_len': 1000,
                    'dry_run': True,
                },
            )
            self.assertEqual(preflight_response.status_code, 200, preflight_response.get_data(as_text=True))
            self.assertTrue(preflight_response.get_json()['ok'])

            smk_response = self.client.post(
                f"/api/pipeline/{project['id']}/run/workflow-appam-smk",
                json={
                    'sample_manifest': 'samples.tsv',
                    'raw_data_dir': 'raw',
                    'profile': 'local',
                    'cores': 8,
                    'preprocess_method': 'adapter_removal',
                    'min_contig_len': 1000,
                    'dry_run': True,
                },
            )
            self.assertEqual(smk_response.status_code, 200, smk_response.get_data(as_text=True))
            smk_payload = smk_response.get_json()
            self.assertTrue(smk_payload['workflow_run_id'])

            workflow_runs_response = self.client.get(
                f"/api/pipeline/{project['id']}/workflow-runs?workflow_id=appam-smk"
            )
            self.assertEqual(workflow_runs_response.status_code, 200)
            workflow_runs = workflow_runs_response.get_json()['workflow_runs']
            self.assertEqual(len(workflow_runs), 1)
            self.assertEqual(workflow_runs[0]['workflow_id'], 'appam-smk')
            self.assertEqual(workflow_runs[0]['submitted_by'], owner['id'])
            self.assertTrue(workflow_runs[0]['config_path'].endswith('.yaml'))
            self.assertIn('/workflow_runs/appam-smk/', workflow_runs[0]['run_dir'])
            self.assertTrue(workflow_runs[0]['stage_states'])
            self.assertIn('manifest.', Path(workflow_runs[0]['manifest_path']).name)
            generated_config = Path(workflow_runs[0]['config_path'])
            config_payload = yaml.safe_load(generated_config.read_text(encoding='utf-8'))
            self.assertIn('adapter1', config_payload['params'])
            self.assertFalse(config_payload['params']['use_ancient_contigs'])
            resolved_manifest = Path(config_payload['samples_file'])
            self.assertTrue(resolved_manifest.is_file())
            self.assertIn(str(raw_data_dir.resolve()), resolved_manifest.read_text(encoding='utf-8'))
            provenance_manifest = json.loads(Path(workflow_runs[0]['manifest_path']).read_text(encoding='utf-8'))
            self.assertEqual(len(provenance_manifest['effective_config_sha256']), 64)
            self.assertEqual(len(provenance_manifest['inputs']), 2)
            self.assertEqual(
                Path(provenance_manifest['paths']['resolved_sample_manifest']),
                resolved_manifest,
            )

            resolved_record = provenance_manifest['resolved_input_table']
            self.assertEqual(Path(resolved_record['path']), resolved_manifest)
            self.assertEqual(resolved_record['role'], 'appam_smk_sample_manifest')
            self.assertEqual(resolved_record['row_count'], 1)
            self.assertEqual(
                resolved_record['sha256'],
                hashlib.sha256(resolved_manifest.read_bytes()).hexdigest(),
            )

            database_snapshot = provenance_manifest['runtime_metadata']['database_manifest']
            self.assertEqual(len(database_snapshot['canonical_sha256']), 64)
            self.assertIn('resources', database_snapshot)
            self.assertIn('required_resources', database_snapshot)

            bundle_response = self.client.get(
                f"/api/pipeline/{project['id']}/workflow-runs/{smk_payload['workflow_run_id']}/provenance-bundle"
            )
            self.assertEqual(bundle_response.status_code, 200, bundle_response.status)
            with zipfile.ZipFile(BytesIO(bundle_response.data)) as bundle:
                bundled_table = bundle.read('inputs/samples.resolved.tsv')
                audit = json.loads(bundle.read('publication-audit.json').decode('utf-8'))
                bundled_databases = json.loads(bundle.read('run/database-manifest.json').decode('utf-8'))
                bundled_manifest = json.loads(bundle.read('run/manifest.json').decode('utf-8'))
                bundled_config = bundle.read('run/config.yaml')
                self.assertNotIn('database-manifest.json', bundle.namelist())

            # The bundled table must be the exact bytes the manifest attests to.
            self.assertIn(str(raw_data_dir.resolve()), bundled_table.decode('utf-8'))
            self.assertEqual(
                hashlib.sha256(bundled_table).hexdigest(),
                provenance_manifest['resolved_input_table']['sha256'],
            )
            # The bundle carries the run-time database snapshot, not current server state.
            self.assertEqual(bundled_databases, database_snapshot)
            self.assertEqual(bundled_manifest, provenance_manifest)
            self.assertEqual(
                hashlib.sha256(bundled_config).hexdigest(),
                provenance_manifest['effective_config_sha256'],
            )

            # This run is a dry run over an incomplete database manifest, so the
            # audit must refuse to call it publishable evidence.
            self.assertFalse(audit['ok'])
            self.assertIn('run_mode', audit['blockers'])
            self.assertIn('database_manifest', audit['blockers'])
            self.assertNotIn('resolved_inputs', audit['blockers'])
            provenance = self.client.get(
                f"/api/pipeline/{project['id']}/workflow-runs/{smk_payload['workflow_run_id']}/provenance"
            ).get_json()
            self.assertEqual(provenance['publication_audit']['blockers'], audit['blockers'])

            # Editing the archived resolved table after the run must become a blocker.
            original_resolved = resolved_manifest.read_bytes()
            resolved_manifest.write_text('sample_id\tforward_reads\treverse_reads\n', encoding='utf-8')
            tampered = self.client.get(
                f"/api/pipeline/{project['id']}/workflow-runs/{smk_payload['workflow_run_id']}/provenance"
            ).get_json()
            self.assertIn('resolved_inputs', tampered['publication_audit']['blockers'])
            resolved_manifest.write_bytes(original_resolved)

            original_manifest_path = project_dir / 'samples.tsv'
            original_manifest_contents = original_manifest_path.read_text(encoding='utf-8')
            original_manifest_path.write_text('sample_id\tforward_reads\treverse_reads\n', encoding='utf-8')

            conn = get_db_connection()
            try:
                conn.execute("UPDATE workflow_runs SET status = 'failed' WHERE id = ?", (smk_payload['workflow_run_id'],))
                conn.commit()
            finally:
                conn.close()

            resume_response = self.client.post(
                f"/api/pipeline/{project['id']}/workflow-runs/{smk_payload['workflow_run_id']}/resume"
            )
            self.assertEqual(resume_response.status_code, 200, resume_response.get_data(as_text=True))

            conn = get_db_connection()
            try:
                conn.execute("UPDATE workflow_runs SET status = 'failed' WHERE project_id = ?", (project['id'],))
                conn.commit()
            finally:
                conn.close()

            retry_response = self.client.post(
                f"/api/pipeline/{project['id']}/workflow-runs/{smk_payload['workflow_run_id']}/retry"
            )
            self.assertEqual(retry_response.status_code, 200, retry_response.get_data(as_text=True))
            retry_detail = self.client.get(
                f"/api/pipeline/{project['id']}/workflow-runs/{retry_response.get_json()['workflow_run_id']}"
            ).get_json()
            retry_config = yaml.safe_load(Path(retry_detail['config_path']).read_text(encoding='utf-8'))
            self.assertNotEqual(Path(retry_detail['config_path']), generated_config)
            self.assertTrue(Path(retry_config['samples_file']).is_file())
            self.assertIn(str(raw_data_dir.resolve()), Path(retry_config['samples_file']).read_text(encoding='utf-8'))
            original_manifest_path.write_text(original_manifest_contents, encoding='utf-8')

        paleoproteomics_table = project_dir / 'proteomics_samples.tsv'
        paleoproteomics_table.write_text('sample_id\tinput_path\texperiment\tfraction\nS1\tdata.RAW\tprojectA\t1\n', encoding='utf-8')
        (project_dir / 'data.RAW').write_text('raw data placeholder', encoding='utf-8')

        with mock.patch.dict(os.environ, runtime_env, clear=False), mock.patch(
            'app.services.job_queue.get_queue', return_value=mock_queue
        ):
            paleo_template = self.client.post(
                f"/api/pipeline/{project['id']}/workflow-templates/workflow-appam-paleoproteomics",
                json={},
            )
            self.assertEqual(paleo_template.status_code, 200, paleo_template.get_data(as_text=True))

            paleo_response = self.client.post(
                f"/api/pipeline/{project['id']}/run/workflow-appam-paleoproteomics",
                json={
                    'sample_table': 'proteomics_samples.tsv',
                    'fasta_path': str(fasta_path),
                    'cores': 6,
                    'dry_run': True,
                },
            )
            self.assertEqual(paleo_response.status_code, 200, paleo_response.get_data(as_text=True))

            dry_run_allowed_response = self.client.post(
                f"/api/pipeline/{project['id']}/run/workflow-appam-smk",
                json={
                    'sample_manifest': 'samples.tsv',
                    'raw_data_dir': 'raw',
                    'profile': 'local',
                    'cores': 2,
                    'dry_run': True,
                },
            )
            self.assertEqual(dry_run_allowed_response.status_code, 200, dry_run_allowed_response.get_data(as_text=True))

            detail_response = self.client.get(
                f"/api/pipeline/{project['id']}/workflow-runs/{paleo_response.get_json()['workflow_run_id']}"
            )
            self.assertEqual(detail_response.status_code, 200)
            detail_payload = detail_response.get_json()
            self.assertEqual(detail_payload['workflow_id'], 'appam-paleoproteomics')
            self.assertEqual(detail_payload['job_id'], paleo_response.get_json()['job_id'])
            self.assertTrue(detail_payload['events'])
            self.assertIsInstance(detail_payload['artifacts'], list)

    def test_queued_job_cancel_marks_canceled_immediately(self):
        self.register(self.client, 'queueowner', display_name='Queue Owner')
        project = self.create_project(self.client, name='Queue Project')

        project_dir = self.projects_dir / project['id']
        project_dir.mkdir(exist_ok=True)
        log_dir = project_dir / 'logs'
        log_dir.mkdir(exist_ok=True)

        from app.services.job_store import create_job, get_job

        create_job(
            'queued-job-1',
            project['id'],
            'Demo Workflow',
            'demo',
            str(log_dir / 'queued-job-1.log'),
            status='queued',
        )

        with mock.patch('app.api.jobs.routes.cancel_enqueued_job', return_value=True):
            response = self.client.post('/api/jobs/queued-job-1/cancel')
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()
        self.assertEqual(payload['mode'], 'queued')

        job = get_job('queued-job-1')
        self.assertEqual(job['status'], 'canceled')
        self.assertEqual(job['error_message'], 'Canceled before execution')

    def test_queued_job_cancel_falls_back_to_db_cancel_when_queue_removal_fails(self):
        self.register(self.client, 'queuefallback', display_name='Queue Fallback')
        project = self.create_project(self.client, name='Queue Fallback Project')

        project_dir = self.projects_dir / project['id']
        project_dir.mkdir(exist_ok=True)
        log_dir = project_dir / 'logs'
        log_dir.mkdir(exist_ok=True)

        from app.services.job_store import create_job, get_job

        create_job(
            'queued-job-2',
            project['id'],
            'FastQC',
            'fastqc',
            str(log_dir / 'queued-job-2.log'),
            status='queued',
        )

        with mock.patch('app.api.jobs.routes.cancel_enqueued_job', return_value=False):
            response = self.client.post('/api/jobs/queued-job-2/cancel')
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()
        self.assertEqual(payload['mode'], 'queued')
        self.assertFalse(payload['queue_removed'])

        job = get_job('queued-job-2')
        self.assertEqual(job['status'], 'canceled')
        self.assertEqual(job['error_message'], 'Canceled before execution')

    def test_runner_skips_job_that_was_canceled_before_execution(self):
        self.register(self.client, 'runnercancel', display_name='Runner Cancel')
        project = self.create_project(self.client, name='Runner Cancel Project')

        project_dir = self.projects_dir / project['id']
        project_dir.mkdir(exist_ok=True)
        log_dir = project_dir / 'logs'
        log_dir.mkdir(exist_ok=True)
        log_path = log_dir / 'queued-job-3.log'

        from app.services.job_store import create_job, get_job, mark_job_finished, request_cancel
        from app.services.job_runner import run_pipeline_job

        create_job(
            'queued-job-3',
            project['id'],
            'FastQC',
            'fastqc',
            str(log_path),
            status='queued',
        )
        request_cancel('queued-job-3')
        mark_job_finished('queued-job-3', 'canceled', None, 'Canceled before execution', 0)

        result = run_pipeline_job(
            'queued-job-3',
            project['id'],
            'FastQC',
            'fastqc',
            str(log_path),
            command_spec={
                'argv': ['/bin/echo', 'should-not-run'],
                'cwd': str(project_dir),
            },
        )

        self.assertEqual(result['status'], 'canceled')
        self.assertTrue(result['skipped'])
        self.assertFalse(log_path.exists())

        job = get_job('queued-job-3')
        self.assertEqual(job['status'], 'canceled')
        self.assertEqual(job['error_message'], 'Canceled before execution')


if __name__ == '__main__':
    unittest.main()
