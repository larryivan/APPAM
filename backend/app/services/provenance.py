from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint_path(path_value: str | Path, hash_mode: str = 'metadata') -> dict:
    path = Path(path_value).expanduser().resolve()
    if not path.exists():
        return {'path': str(path), 'exists': False}

    normalized_mode = str(hash_mode or 'metadata').strip().lower()
    include_content = normalized_mode == 'sha256'
    if path.is_file():
        stat = path.stat()
        payload = {
            'path': str(path),
            'exists': True,
            'type': 'file',
            'size_bytes': stat.st_size,
            'mtime_ns': stat.st_mtime_ns,
        }
        if include_content:
            payload['sha256'] = sha256_file(path)
        return payload

    files = sorted(item for item in path.rglob('*') if item.is_file())
    digest = hashlib.sha256()
    total_size = 0
    for item in files:
        stat = item.stat()
        relative = item.relative_to(path).as_posix()
        total_size += stat.st_size
        digest.update(relative.encode('utf-8'))
        digest.update(b'\0')
        digest.update(str(stat.st_size).encode('ascii'))
        digest.update(b'\0')
        if include_content:
            digest.update(sha256_file(item).encode('ascii'))
        else:
            digest.update(str(stat.st_mtime_ns).encode('ascii'))
        digest.update(b'\n')
    return {
        'path': str(path),
        'exists': True,
        'type': 'directory',
        'file_count': len(files),
        'size_bytes': total_size,
        'fingerprint_mode': 'sha256' if include_content else 'metadata',
        'fingerprint': digest.hexdigest(),
    }


def repository_state(repo_root: Path) -> dict:
    def run_git(*args):
        result = subprocess.run(
            ['git', '-C', str(repo_root), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else None

    commit = run_git('rev-parse', 'HEAD')
    status = run_git('status', '--porcelain')
    return {
        'repository': str(repo_root.resolve()),
        'commit': commit,
        'dirty': bool(status) if status is not None else None,
        'status': status.splitlines()[:100] if status else [],
    }


def conda_environment_fingerprint(path_value: str | None) -> dict:
    if not path_value:
        return {'path': None, 'exists': False}
    path = Path(os.path.expanduser(str(path_value)))
    if not path.is_absolute():
        return {'name': str(path_value), 'type': 'named_environment', 'exists': None}
    path = path.resolve()
    conda_meta = path / 'conda-meta'
    if not conda_meta.is_dir():
        return {'path': str(path), 'exists': path.exists(), 'type': 'environment_path'}

    packages = []
    for record_path in sorted(conda_meta.glob('*.json')):
        try:
            record = json.loads(record_path.read_text(encoding='utf-8'))
        except Exception:
            continue
        packages.append({
            'name': record.get('name'),
            'version': record.get('version'),
            'build': record.get('build'),
            'channel': record.get('channel'),
        })
    serialized = json.dumps(packages, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return {
        'path': str(path),
        'exists': True,
        'type': 'conda_environment',
        'package_count': len(packages),
        'packages_sha256': sha256_bytes(serialized),
        'packages': packages,
    }
