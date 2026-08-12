import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
COMMON_SCRIPT = REPO_ROOT / 'deploy' / 'native' / 'common.sh'


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


if __name__ == '__main__':
    unittest.main()
