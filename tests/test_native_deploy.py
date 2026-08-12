import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
COMMON_SCRIPT = REPO_ROOT / 'deploy' / 'native' / 'common.sh'
RENDER_SCRIPT = REPO_ROOT / 'deploy' / 'native' / 'render-env.sh'


class NativeDeploymentTests(unittest.TestCase):
    def _resolve_base(self, payload):
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = Path(temp_dir) / 'runner'
            runner.write_text(
                '#!/usr/bin/env bash\n'
                'test "$1" = info\n'
                'test "$2" = --json\n'
                f"printf '%s\\n' {json.dumps(json.dumps(payload))}\n",
                encoding='utf-8',
            )
            runner.chmod(0o755)
            return subprocess.run(
                [
                    'bash',
                    '-c',
                    'source "$1"; resolve_environment_base "$2"',
                    'bash',
                    str(COMMON_SCRIPT),
                    str(runner),
                ],
                check=False,
                capture_output=True,
                text=True,
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
            )

    def test_resolves_micromamba_base_environment(self):
        result = self._resolve_base({'base environment': '/opt/micromamba root'})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '/opt/micromamba root')

    def test_resolves_conda_root_prefix(self):
        result = self._resolve_base({'root_prefix': '/opt/conda'})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '/opt/conda')

    def test_rejects_missing_base_directory(self):
        result = self._resolve_base({'platform': 'linux-64'})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('did not report its base directory', result.stderr)

    def test_render_env_selects_nested_gtdb_release(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner = root / 'runner'
            runner.write_text(
                '#!/usr/bin/env bash\n'
                'test "$1" = info\n'
                'test "$2" = --json\n'
                f"printf '%s\\n' {json.dumps(json.dumps({'root_prefix': str(root / 'conda')}))}\n",
                encoding='utf-8',
            )
            runner.chmod(0o755)
            database_root = root / 'db'
            release_root = database_root / 'gtdbtk_r226' / 'release226'
            release_root.mkdir(parents=True)
            output = root / 'appam.env'

            result = subprocess.run(
                [
                    'bash',
                    str(RENDER_SCRIPT),
                    '--output',
                    str(output),
                    '--db-root',
                    str(database_root),
                    '--projects-root',
                    str(root / 'projects'),
                ],
                check=False,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    'APPAM_ENV_RUNNER': str(runner),
                    'HOME': str(root),
                    'PYTHONIOENCODING': 'utf-8',
                },
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            rendered = output.read_text(encoding='utf-8')
            self.assertIn(f'APPAM_SMK_GTDBTK_DB={release_root}', rendered)

    def test_checkm_contract_uses_compatible_runtime(self):
        spec = (REPO_ROOT / 'docker' / 'tools' / 'environments' / 'checkm.yml').read_text(encoding='utf-8')
        rules = (REPO_ROOT / 'APPAM-SMK-main' / 'workflow' / 'rules' / 'binning.smk').read_text(encoding='utf-8')

        self.assertIn('setuptools<81', spec)
        self.assertIn('checkm data setRoot ', rules)
        self.assertNotIn('setRootPath', rules)
        self.assertIn("-name 'uniref100.KO.1.dmnd'", rules)
        self.assertIn('--database_path "$db_file"', rules)


if __name__ == '__main__':
    unittest.main()
