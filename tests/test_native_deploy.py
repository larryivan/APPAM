import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
COMMON_SCRIPT = REPO_ROOT / 'deploy' / 'native' / 'common.sh'
RENDER_SCRIPT = REPO_ROOT / 'deploy' / 'native' / 'render-env.sh'
INSTALL_SCRIPT = REPO_ROOT / 'deploy' / 'native' / 'install-environments.sh'
TOOL_WRAPPER = REPO_ROOT / 'docker' / 'tools' / 'tool-wrapper.sh'
TOOLS_DOCKERFILE = REPO_ROOT / 'docker' / 'tools' / 'Dockerfile'


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
                    '--web-origin',
                    'https://gateway.example',
                    '--public-base-path',
                    '/proxy/relative/10.0.0.5/25078',
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
            self.assertIn(
                f'APPAM_PALEO_DOTNET_BIN={root / "conda" / "envs" / "paleoproteomics" / "lib" / "dotnet" / "dotnet"}',
                rendered,
            )
            self.assertIn(f'APPAM_PALEO_TIMSCONVERT_BIN={root / ".local" / "bin" / "appam-timsconvert"}', rendered)
            self.assertIn(f'APPAM_PALEO_TIMSCONVERT_ENV={root / "conda" / "envs" / "timsconvert"}', rendered)
            self.assertIn(f'APPAM_PALEO_THERMO_RAW_FILE_PARSER={root / ".local" / "bin" / "ThermoRawFileParser"}', rendered)
            self.assertIn(f'APPAM_KRAKENUNIQ_KDB={database_root / "krakenuniq_refseq_bav" / "database.kdb"}', rendered)
            self.assertIn(f'APPAM_SMK_REPORTING_ENV={root / "conda" / "envs" / "reporting"}', rendered)
            self.assertIn('APPAM_ALLOWED_ORIGINS=https://gateway.example', rendered)
            self.assertIn('APPAM_PUBLIC_BASE_PATH=/proxy/relative/10.0.0.5/25078', rendered)

    def test_checkm_contract_uses_compatible_runtime(self):
        spec = (REPO_ROOT / 'docker' / 'tools' / 'environments' / 'checkm.yml').read_text(encoding='utf-8')
        rules = (REPO_ROOT / 'APPAM-SMK-main' / 'workflow' / 'rules' / 'binning.smk').read_text(encoding='utf-8')

        self.assertIn('setuptools<81', spec)
        self.assertIn('checkm data setRoot ', rules)
        self.assertNotIn('setRootPath', rules)
        self.assertIn("-name 'uniref100.KO.1.dmnd'", rules)
        self.assertIn('--database_path "$db_file"', rules)

    def test_native_installer_exposes_metawrap_configuration(self):
        installer = INSTALL_SCRIPT.read_text(encoding='utf-8')

        self.assertIn('SOFT=${METAWRAP_ROOT}/bin/metawrap-scripts', installer)
        self.assertIn('PIPES=${METAWRAP_ROOT}/bin/metawrap-modules', installer)
        self.assertIn('chmod 0755 "${METAWRAP_ROOT}/bin/config-metawrap"', installer)
        self.assertIn('${HOME}/.local/bin/config-metawrap', installer)

    def test_native_installer_isolates_timsconvert_qt_runtime(self):
        installer = INSTALL_SCRIPT.read_text(encoding='utf-8')

        self.assertIn('environment_exists timsconvert', installer)
        self.assertIn('run -n timsconvert python', installer)
        self.assertIn('patch_pytdfsdk.py', installer)
        self.assertIn('appam-timsconvert', installer)
        # libEGL ships with the environment, which is the only library path.
        self.assertIn('create -y -n timsconvert -c conda-forge python=3.11 pip libegl', installer)
        self.assertIn('export LD_LIBRARY_PATH="${TIMSCONVERT_PREFIX}/lib"', installer)
        self.assertNotIn('paleoproteomics/lib', installer)
        self.assertIn('unset QT_PLUGIN_PATH', installer)
        self.assertIn('ln -sfn appam-timsconvert', installer)

    def test_tools_image_isolates_timsconvert_from_openms(self):
        dockerfile = TOOLS_DOCKERFILE.read_text(encoding='utf-8')

        self.assertIn('micromamba create -y -n timsconvert python=3.11 pip', dockerfile)
        self.assertIn('micromamba run -n timsconvert python /opt/appam/appam-paleoproteomics-main/docker/patch_pytdfsdk.py', dockerfile)
        self.assertIn('exec /opt/conda/envs/timsconvert/bin/timsconvert "$@"', dockerfile)
        self.assertIn('unset LD_LIBRARY_PATH', dockerfile)
        self.assertNotIn('micromamba run -n paleoproteomics pip install -r', dockerfile)

    def test_pmdtools_aliases_target_the_environment_binary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wrapper = root / 'appam-tool'
            runner = root / 'runner'
            capture = root / 'capture.txt'
            shutil.copy2(TOOL_WRAPPER, wrapper)
            wrapper.chmod(0o755)
            runner.write_text(
                '#!/usr/bin/env bash\n'
                'printf "%s\\n" "$@" > "$APPAM_CAPTURE"\n',
                encoding='utf-8',
            )
            runner.chmod(0o755)

            for alias_name in ('pmdtools', 'pmdtools.py'):
                alias = root / alias_name
                alias.symlink_to(wrapper.name)
                result = subprocess.run(
                    [str(alias), '--help'],
                    check=False,
                    capture_output=True,
                    text=True,
                    env={
                        **os.environ,
                        'APPAM_CAPTURE': str(capture),
                        'APPAM_ENV_RUNNER': str(runner),
                    },
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    capture.read_text(encoding='utf-8').splitlines(),
                    ['run', '-n', 'ancient_dna', 'pmdtools', '--help'],
                )


if __name__ == '__main__':
    unittest.main()
