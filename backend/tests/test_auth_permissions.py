import json
import os
import shutil
import sys
import tempfile
import unittest
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

    def test_admin_worker_status_endpoint_reports_local_executor(self):
        self.register(self.client, 'workeradmin', display_name='Worker Admin')
        response = self.client.get('/api/system/worker')
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['data']['mode'], 'local-db')
        self.assertIn('worker', payload['data'])
        self.assertIn('counts', payload['data'])

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
        pydamage_env = Path(TEST_TEMP_DIR) / 'envs' / 'pydamage'
        checkm2_env = Path(TEST_TEMP_DIR) / 'envs' / 'checkm2'
        gunc_env = Path(TEST_TEMP_DIR) / 'envs' / 'gunc'
        prokka_env = Path(TEST_TEMP_DIR) / 'envs' / 'prokka'
        eggnog_env = Path(TEST_TEMP_DIR) / 'envs' / 'eggnog_py310'
        abricate_env = Path(TEST_TEMP_DIR) / 'envs' / 'abricate'
        antismash_env = Path(TEST_TEMP_DIR) / 'envs' / 'antismash'
        checkm_db = Path(TEST_TEMP_DIR) / 'db' / 'checkm'
        checkm2_db = Path(TEST_TEMP_DIR) / 'db' / 'checkm2'
        gunc_db = Path(TEST_TEMP_DIR) / 'db' / 'gunc'
        eggnog_db = Path(TEST_TEMP_DIR) / 'db' / 'eggnog'
        maxquant_cmd = Path(TEST_TEMP_DIR) / 'maxquant' / 'MaxQuantCmd.dll'
        fasta_path = Path(TEST_TEMP_DIR) / 'references' / 'db.fasta'

        for directory in (
            metawrap_env,
            pydamage_env,
            checkm2_env,
            gunc_env,
            prokka_env,
            eggnog_env,
            abricate_env,
            antismash_env,
            checkm_db,
            checkm2_db,
            gunc_db,
            eggnog_db,
            maxquant_cmd.parent,
            fasta_path.parent,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        maxquant_cmd.write_text('maxquant', encoding='utf-8')
        fasta_path.write_text('>seq\nAAAA\n', encoding='utf-8')

        runtime_env = {
            'APPAM_SNAKEMAKE_BIN': '/bin/echo',
            'APPAM_SMK_METAWRAP_ENV': str(metawrap_env),
            'APPAM_SMK_PYDAMAGE_ENV': str(pydamage_env),
            'APPAM_SMK_CHECKM1_DB': str(checkm_db),
            'APPAM_SMK_CHECKM_DB': str(checkm_db),
            'APPAM_SMK_CHECKM2_ENV': str(checkm2_env),
            'APPAM_SMK_CHECKM2_DB': str(checkm2_db),
            'APPAM_SMK_GUNC_ENV': str(gunc_env),
            'APPAM_SMK_GUNC_DB': str(gunc_db),
            'APPAM_SMK_PROKKA_ENV': str(prokka_env),
            'APPAM_SMK_EGGNOG_ENV': str(eggnog_env),
            'APPAM_SMK_EGGNOG_DB': str(eggnog_db),
            'APPAM_SMK_ABRICATE_ENV': str(abricate_env),
            'APPAM_SMK_ANTISMASH_ENV': str(antismash_env),
            'APPAM_PALEO_MAXQUANT_CMD': str(maxquant_cmd),
            'APPAM_PALEO_DOTNET_BIN': '/bin/echo',
            'APPAM_PALEO_THERMO_RAW_FILE_PARSER': '/bin/echo',
            'APPAM_PALEO_TIMSCONVERT_BIN': '/bin/echo',
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
