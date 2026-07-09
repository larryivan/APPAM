from __future__ import annotations

import csv
import re
from pathlib import Path

from ..paths import get_project_dir, resolve_project_path


FASTQ_EXTENSIONS = ('.fastq.gz', '.fq.gz', '.fastq', '.fq')
THERMO_RAW_EXTENSIONS = ('.raw',)
SAMPLE_ID_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$')


def _project_relative(project_id: str, path: Path) -> str:
    project_dir = get_project_dir(project_id).resolve()
    resolved = path.resolve()
    if resolved == project_dir:
        return '.'
    if project_dir in resolved.parents:
        return str(resolved.relative_to(project_dir))
    return str(resolved)


def _read_tsv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle, delimiter='\t')
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    return fieldnames, rows


def _check(status: str, name: str, message: str, **extra) -> dict:
    payload = {'name': name, 'status': status, 'message': message}
    payload.update(extra)
    return payload


def _sample_id(value) -> str:
    return str(value or '').strip()


def _safe_project_candidate(project_id: str, base: Path, value: str) -> Path:
    project_dir = get_project_dir(project_id).resolve()
    candidate = (base / value).resolve()
    if candidate != project_dir and project_dir not in candidate.parents:
        raise ValueError(f'Path escapes project workspace: {value}')
    return candidate


def _resolve_manifest_path(project_id: str, manifest_path: Path, value: str) -> Path:
    project_candidate = resolve_project_path(project_id, value)
    manifest_candidate = _safe_project_candidate(project_id, manifest_path.parent, value)
    for candidate in (project_candidate, manifest_candidate):
        if candidate.exists():
            return candidate
    return manifest_candidate


def _resolve_read_path(project_id: str, manifest_path: Path, raw_dir: Path, value: str | None, default_name: str) -> Path:
    if not value:
        return raw_dir / default_name
    raw_value = str(value).strip()
    if not raw_value:
        return raw_dir / default_name
    candidates = [
        _resolve_manifest_path(project_id, manifest_path, raw_value),
        _safe_project_candidate(project_id, raw_dir, raw_value),
        _safe_project_candidate(project_id, raw_dir, Path(raw_value).name),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def validate_appam_smk_manifest(project_id: str, sample_manifest: str, raw_data_dir: str) -> dict:
    manifest_path = resolve_project_path(project_id, sample_manifest)
    raw_dir = resolve_project_path(project_id, raw_data_dir)
    checks = []
    samples = []

    if not manifest_path.is_file():
        return {
            'ok': False,
            'workflow_id': 'appam-smk',
            'checks': [_check('error', 'sample_manifest', f'Sample manifest not found: {manifest_path}')],
            'samples': [],
        }
    if not raw_dir.is_dir():
        return {
            'ok': False,
            'workflow_id': 'appam-smk',
            'checks': [_check('error', 'raw_data_dir', f'Raw data directory not found: {raw_dir}')],
            'samples': [],
        }

    fieldnames, rows = _read_tsv(manifest_path)
    if 'sample_id' not in fieldnames:
        checks.append(_check('error', 'sample_id_column', "samples.tsv must include a 'sample_id' column"))
        return {'ok': False, 'workflow_id': 'appam-smk', 'checks': checks, 'samples': []}

    seen = set()
    for index, row in enumerate(rows, start=2):
        sample_id = _sample_id(row.get('sample_id'))
        if not sample_id:
            checks.append(_check('error', f'row_{index}', f'Missing sample_id at row {index}'))
            continue
        if not SAMPLE_ID_RE.fullmatch(sample_id):
            checks.append(_check('error', sample_id, f'Invalid sample_id: {sample_id}. Use letters, numbers, dots, underscores, and hyphens.'))
            continue
        if sample_id in seen:
            checks.append(_check('error', sample_id, f'Duplicate sample_id: {sample_id}'))
            continue
        seen.add(sample_id)

        forward_value = row.get('forward_reads') or row.get('r1') or row.get('R1')
        reverse_value = row.get('reverse_reads') or row.get('r2') or row.get('R2')
        forward_path = _resolve_read_path(project_id, manifest_path, raw_dir, forward_value, f'{sample_id}_R1.fastq.gz')
        reverse_path = _resolve_read_path(project_id, manifest_path, raw_dir, reverse_value, f'{sample_id}_R2.fastq.gz')
        forward_exists = forward_path.is_file()
        reverse_exists = reverse_path.is_file()
        forward_fastq = str(forward_path).lower().endswith(FASTQ_EXTENSIONS)
        reverse_fastq = str(reverse_path).lower().endswith(FASTQ_EXTENSIONS)

        samples.append({
            'sample_id': sample_id,
            'forward_reads': _project_relative(project_id, forward_path),
            'reverse_reads': _project_relative(project_id, reverse_path),
            'forward_exists': forward_exists,
            'reverse_exists': reverse_exists,
        })
        checks.append(_check('ok' if forward_exists and forward_fastq else 'error', f'{sample_id}_R1', f'R1 found: {forward_path}' if forward_exists and forward_fastq else f'R1 missing or not FASTQ: {forward_path}'))
        checks.append(_check('ok' if reverse_exists and reverse_fastq else 'error', f'{sample_id}_R2', f'R2 found: {reverse_path}' if reverse_exists and reverse_fastq else f'R2 missing or not FASTQ: {reverse_path}'))

    if not rows:
        checks.append(_check('error', 'sample_rows', 'samples.tsv has no sample rows'))

    ok = not any(check['status'] == 'error' for check in checks)
    return {'ok': ok, 'workflow_id': 'appam-smk', 'checks': checks, 'samples': samples}


def validate_paleoproteomics_table(project_id: str, sample_table: str) -> dict:
    table_path = resolve_project_path(project_id, sample_table)
    checks = []
    samples = []
    required = {'sample_id', 'input_path', 'experiment', 'fraction'}

    if not table_path.is_file():
        return {
            'ok': False,
            'workflow_id': 'appam-paleoproteomics',
            'checks': [_check('error', 'sample_table', f'Sample table not found: {table_path}')],
            'samples': [],
        }

    fieldnames, rows = _read_tsv(table_path)
    missing = sorted(required - set(fieldnames))
    if missing:
        checks.append(_check('error', 'sample_table_columns', f'Missing columns: {", ".join(missing)}'))
        return {'ok': False, 'workflow_id': 'appam-paleoproteomics', 'checks': checks, 'samples': []}

    seen = set()
    for index, row in enumerate(rows, start=2):
        sample_id = _sample_id(row.get('sample_id'))
        if not sample_id:
            checks.append(_check('error', f'row_{index}', f'Missing sample_id at row {index}'))
            continue
        if not SAMPLE_ID_RE.fullmatch(sample_id):
            checks.append(_check('error', sample_id, f'Invalid sample_id: {sample_id}. Use letters, numbers, dots, underscores, and hyphens.'))
            continue
        if sample_id in seen:
            checks.append(_check('error', sample_id, f'Duplicate sample_id: {sample_id}'))
            continue
        seen.add(sample_id)

        raw_input_path = str(row.get('input_path') or '').strip()
        if not raw_input_path:
            checks.append(_check('error', sample_id, f'Missing input_path for sample {sample_id}'))
            continue
        input_path = _resolve_manifest_path(project_id, table_path, raw_input_path)
        exists = input_path.exists()
        is_supported = (
            input_path.is_file() and input_path.suffix.lower() in THERMO_RAW_EXTENSIONS
        ) or (
            input_path.is_dir() and input_path.name.lower().endswith('.d')
        )
        experiment = str(row.get('experiment') or '').strip()
        fraction = str(row.get('fraction') or '').strip()
        samples.append({
            'sample_id': sample_id,
            'input_path': _project_relative(project_id, input_path),
            'experiment': experiment,
            'fraction': fraction,
            'exists': exists,
        })
        checks.append(_check('ok' if exists and is_supported else 'error', sample_id, f'Input found: {input_path}' if exists and is_supported else f'Input missing or unsupported (expected .RAW file or .d directory): {input_path}'))
        checks.append(_check('ok' if experiment else 'error', f'{sample_id}_experiment', f'Experiment: {experiment}' if experiment else 'Experiment is required'))
        try:
            fraction_value = int(fraction)
            fraction_valid = -32768 <= fraction_value <= 32767
        except (TypeError, ValueError):
            fraction_valid = False
        checks.append(_check('ok' if fraction_valid else 'error', f'{sample_id}_fraction', f'Fraction: {fraction}' if fraction_valid else f'Fraction must be an integer: {fraction!r}'))

    if not rows:
        checks.append(_check('error', 'sample_rows', 'samples.tsv has no sample rows'))

    ok = not any(check['status'] == 'error' for check in checks)
    return {'ok': ok, 'workflow_id': 'appam-paleoproteomics', 'checks': checks, 'samples': samples}


def _fastq_sample_key(filename: str):
    if not filename.lower().endswith(FASTQ_EXTENSIONS):
        return None
    patterns = [
        r'(.+?)[._-]r?1(?:[._-].*)?\.(?:fastq|fq)(?:\.gz)?$',
        r'(.+?)[._-]r?2(?:[._-].*)?\.(?:fastq|fq)(?:\.gz)?$',
    ]
    for read, pattern in enumerate(patterns, start=1):
        match = re.match(pattern, filename, flags=re.IGNORECASE)
        if match:
            return match.group(1), read
    return None


def scan_project_data(project_id: str, path: str = '.') -> dict:
    root = resolve_project_path(project_id, path or '.')
    if not root.exists():
        raise FileNotFoundError(f'Path not found: {root}')
    if not root.is_dir():
        raise ValueError(f'Path must be a directory: {root}')

    fastq_pairs = {}
    thermo_raw = []
    bruker_dirs = []
    for item in sorted(root.rglob('*')):
        if item.is_file():
            key = _fastq_sample_key(item.name)
            if key:
                sample_key, read = key
                record = fastq_pairs.setdefault(sample_key, {'sample_id': sample_key, 'forward_reads': None, 'reverse_reads': None})
                if read == 1:
                    record['forward_reads'] = _project_relative(project_id, item)
                else:
                    record['reverse_reads'] = _project_relative(project_id, item)
            if item.suffix.lower() in THERMO_RAW_EXTENSIONS:
                thermo_raw.append({'sample_id': item.stem, 'input_path': _project_relative(project_id, item)})
        elif item.is_dir() and item.name.lower().endswith('.d'):
            bruker_dirs.append({'sample_id': item.name[:-2], 'input_path': _project_relative(project_id, item)})

    fastq_samples = sorted(fastq_pairs.values(), key=lambda row: row['sample_id'])
    proteomics_samples = sorted(thermo_raw + bruker_dirs, key=lambda row: row['sample_id'])
    return {
        'root': _project_relative(project_id, root),
        'fastq_samples': fastq_samples,
        'proteomics_samples': proteomics_samples,
        'counts': {
            'fastq_samples': len(fastq_samples),
            'proteomics_samples': len(proteomics_samples),
            'complete_fastq_pairs': sum(1 for sample in fastq_samples if sample.get('forward_reads') and sample.get('reverse_reads')),
        },
    }


def write_appam_smk_manifest(project_id: str, raw_data_dir: str, output_path: str, overwrite: bool = False) -> dict:
    scan = scan_project_data(project_id, raw_data_dir)
    destination = resolve_project_path(project_id, output_path)
    if destination.exists() and not overwrite:
        raise ValueError(f'Manifest already exists: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = [sample for sample in scan['fastq_samples'] if sample.get('forward_reads') and sample.get('reverse_reads')]
    with destination.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['sample_id', 'forward_reads', 'reverse_reads'], delimiter='\t')
        writer.writeheader()
        for row in rows:
            writer.writerow({
                'sample_id': row['sample_id'],
                'forward_reads': row['forward_reads'],
                'reverse_reads': row['reverse_reads'],
            })
    return {'path': _project_relative(project_id, destination), 'samples_written': len(rows), 'scan': scan}


def write_paleoproteomics_manifest(project_id: str, data_dir: str, output_path: str, overwrite: bool = False) -> dict:
    scan = scan_project_data(project_id, data_dir)
    destination = resolve_project_path(project_id, output_path)
    if destination.exists() and not overwrite:
        raise ValueError(f'Manifest already exists: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['sample_id', 'input_path', 'experiment', 'fraction'], delimiter='\t')
        writer.writeheader()
        for row in scan['proteomics_samples']:
            writer.writerow({
                'sample_id': row['sample_id'],
                'input_path': row['input_path'],
                'experiment': 'project',
                'fraction': '1',
            })
    return {'path': _project_relative(project_id, destination), 'samples_written': len(scan['proteomics_samples']), 'scan': scan}


def write_resolved_appam_smk_manifest(project_id: str, validation: dict, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['sample_id', 'forward_reads', 'reverse_reads'], delimiter='\t')
        writer.writeheader()
        for sample in validation.get('samples') or []:
            writer.writerow({
                'sample_id': sample['sample_id'],
                'forward_reads': str(resolve_project_path(project_id, sample['forward_reads'])),
                'reverse_reads': str(resolve_project_path(project_id, sample['reverse_reads'])),
            })
    return destination


def write_resolved_paleoproteomics_table(project_id: str, validation: dict, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['sample_id', 'input_path', 'experiment', 'fraction'], delimiter='\t')
        writer.writeheader()
        for sample in validation.get('samples') or []:
            writer.writerow({
                'sample_id': sample['sample_id'],
                'input_path': str(resolve_project_path(project_id, sample['input_path'])),
                'experiment': sample['experiment'],
                'fraction': sample['fraction'],
            })
    return destination
