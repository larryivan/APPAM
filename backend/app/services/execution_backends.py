import os
import shlex
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def resolve_backend_name(requested: str | None, profile: str | None = None) -> str:
    name = str(requested or '').strip().lower()
    if name in {'local', 'slurm', 'docker'}:
        return name
    profile_name = str(profile or '').strip().lower()
    if profile_name == 'slurm':
        return 'slurm'
    return 'local'


def resolve_docker_bin() -> str:
    configured = os.getenv('APPAM_DOCKER_BIN', 'docker')
    if os.path.isabs(configured):
        if not Path(configured).exists():
            raise ValueError(f'Docker executable not found: {configured}')
        return configured
    resolved = shutil.which(configured)
    if not resolved:
        raise ValueError(
            f'Docker executable "{configured}" was not found on PATH. '
            'Set APPAM_DOCKER_BIN or install Docker.'
        )
    return resolved


def build_backend_command_spec(
    *,
    backend: str,
    argv: list[str],
    cwd: str,
    env: dict | None = None,
    cleanup_commands: list[dict] | None = None,
    workflow_context: dict | None = None,
) -> dict:
    normalized = resolve_backend_name(backend)
    if normalized != 'docker':
        return {
            'argv': argv,
            'cwd': cwd,
            'env': env or {},
            'cleanup_commands': cleanup_commands or [],
            'workflow_context': workflow_context or {},
            'backend': normalized,
        }

    docker_bin = resolve_docker_bin()
    image = os.getenv('APPAM_WORKFLOW_RUNNER_IMAGE')
    if not image:
        raise ValueError('APPAM_WORKFLOW_RUNNER_IMAGE is required for docker execution backend')

    mounted_cwd = str(Path(cwd).resolve())
    repo_root = str(REPO_ROOT.resolve())
    docker_argv = [
        docker_bin,
        'run',
        '--rm',
        '-v',
        f'{repo_root}:{repo_root}',
        '-w',
        mounted_cwd,
    ]
    docker_argv.extend(['-v', f'{mounted_cwd}:{mounted_cwd}'])
    if env:
        for key, value in env.items():
            docker_argv.extend(['-e', f'{key}={value}'])
    docker_argv.append(image)
    docker_argv.extend(argv)

    docker_cleanup = []
    for cleanup in cleanup_commands or []:
        cleanup_cwd = str(Path(cleanup.get('cwd', cwd)).resolve())
        cleanup_argv = [
            docker_bin,
            'run',
            '--rm',
            '-v',
            f'{repo_root}:{repo_root}',
            '-w',
            cleanup_cwd,
        ]
        cleanup_argv.extend(['-v', f'{cleanup_cwd}:{cleanup_cwd}'])
        if env:
            for key, value in env.items():
                cleanup_argv.extend(['-e', f'{key}={value}'])
        cleanup_argv.append(image)
        cleanup_argv.extend(cleanup.get('argv') or [])
        docker_cleanup.append({
            'argv': cleanup_argv,
            'cwd': cwd,
        })

    return {
        'argv': docker_argv,
        'cwd': cwd,
        'env': {},
        'cleanup_commands': docker_cleanup,
        'workflow_context': workflow_context or {},
        'backend': 'docker',
        'backend_display_command': ' '.join(shlex.quote(part) for part in docker_argv),
    }
