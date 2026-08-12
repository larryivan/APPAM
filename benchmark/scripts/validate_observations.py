from __future__ import annotations

import argparse
import csv
import hashlib
import math
import sys
from pathlib import Path


REQUIRED_COLUMNS = ['dataset_id', 'scenario_id', 'method', 'replicate', 'metric', 'value', 'unit']

# A frozen design uses the non-template file names. Templates stay unfrozen on purpose.
DESIGN_TABLES = {
    'dataset_id': ('datasets.tsv', 'dataset_id'),
    'scenario_id': ('scenarios.tsv', 'scenario_id'),
    'method': ('methods.tsv', 'method'),
}

# Every row of a frozen table must declare this status.
FROZEN_STATUS = 'frozen'
# A field that legitimately does not apply must say so explicitly rather than
# being left blank or carrying a shipped-template placeholder.
NOT_APPLICABLE = 'not-applicable'
PLACEHOLDER_VALUES = {
    'tbd',
    'todo',
    'planned',
    'draft',
    'template',
    'placeholder',
    'unknown',
    'fixme',
    'replace-me',
    'xxx',
    'n/a',
    'na',
    '-',
    '?',
}


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return True
    if normalized == NOT_APPLICABLE:
        return False
    return normalized in PLACEHOLDER_VALUES


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _read_design_table(path: Path, column: str) -> tuple[set[str], int]:
    """Read one frozen design table, rejecting anything still unresolved.

    Copying a shipped template is not pre-registration: template rows carry TBD
    values and status=planned, both of which are rejected here.
    """
    with path.open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle, delimiter='\t')
        fieldnames = reader.fieldnames or []
        for required in (column, 'status'):
            if required not in fieldnames:
                raise ValueError(f'{path.name} is missing the {required} column')
        rows = [dict(row) for row in reader]

    if not rows:
        raise ValueError(f'{path.name} declares no rows')

    identifiers = set()
    for line_number, row in enumerate(rows, start=2):
        identifier = str(row.get(column) or '').strip()
        if not identifier:
            raise ValueError(f'{path.name} line {line_number} has an empty {column}')
        if identifier in identifiers:
            raise ValueError(f'{path.name} declares duplicate {column}: {identifier}')
        identifiers.add(identifier)

        status = str(row.get('status') or '').strip().lower()
        if status != FROZEN_STATUS:
            raise ValueError(
                f'{path.name} line {line_number} has status {status or "(empty)"!r}; '
                f'a pre-registered row must declare status={FROZEN_STATUS}'
            )
        unresolved = sorted(
            field for field, value in row.items()
            if field is not None and _is_placeholder(str(value or ''))
        )
        if unresolved:
            raise ValueError(
                f'{path.name} line {line_number} still has unresolved field(s): {", ".join(unresolved[:5])}. '
                f'Fill each one or set it to {NOT_APPLICABLE}.'
            )
    return identifiers, len(rows)


def load_design(design_dir: Path | None) -> dict:
    """Load the frozen pre-registration tables, if they have been frozen.

    A directory that holds the non-template file names is treated as a freeze
    attempt: the tables must then validate, or loading fails outright.
    """
    if design_dir is None:
        return {'frozen': False, 'reason': 'no design directory was provided', 'declared': {}}
    missing = [name for name, _ in DESIGN_TABLES.values() if not (design_dir / name).is_file()]
    if missing:
        return {
            'frozen': False,
            'reason': f'{design_dir} has no frozen {", ".join(sorted(missing))}',
            'declared': {},
        }

    declared = {}
    files = {}
    for field, (name, column) in DESIGN_TABLES.items():
        path = design_dir / name
        identifiers, row_count = _read_design_table(path, column)
        declared[field] = identifiers
        files[name] = {'sha256': sha256_file(path), 'row_count': row_count}
    return {
        'frozen': True,
        'design_dir': str(design_dir),
        'declared': declared,
        'files': files,
    }


def design_record(design: dict) -> dict:
    """JSON-safe identity of the design an analysis was run against."""
    record = {'frozen': bool(design.get('frozen'))}
    if design.get('frozen'):
        record['design_dir'] = design.get('design_dir')
        record['declared_counts'] = {
            field: len(values) for field, values in sorted((design.get('declared') or {}).items())
        }
        record['files'] = dict(sorted((design.get('files') or {}).items()))
    else:
        record['reason'] = design.get('reason')
    return record


def _check_against_design(rows: list[dict[str, str]], design: dict) -> None:
    declared = design.get('declared') or {}
    for field, allowed in declared.items():
        observed = {str(row.get(field) or '').strip() for row in rows}
        undeclared = sorted(value for value in observed if value not in allowed)
        if undeclared:
            table = DESIGN_TABLES[field][0]
            raise ValueError(
                f'{field} value(s) not pre-registered in {table}: {", ".join(undeclared[:5])}'
            )


def validate(path: Path, design: dict | None = None) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle, delimiter='\t')
        missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f'missing observation columns: {", ".join(missing)}')
        rows = [dict(row) for row in reader]

    if not rows:
        raise ValueError('observation table is empty')
    seen = set()
    for line_number, row in enumerate(rows, start=2):
        for column in REQUIRED_COLUMNS:
            if not str(row.get(column) or '').strip():
                raise ValueError(f'empty {column} at line {line_number}')
        try:
            replicate = int(row['replicate'])
        except ValueError as exc:
            raise ValueError(f'invalid replicate at line {line_number}: {row["replicate"]!r}') from exc
        if replicate < 1:
            raise ValueError(f'replicate must be >= 1 at line {line_number}')
        try:
            value = float(row['value'])
        except ValueError as exc:
            raise ValueError(f'invalid numeric value at line {line_number}: {row["value"]!r}') from exc
        if not math.isfinite(value):
            raise ValueError(f'non-finite value at line {line_number}')

        key = tuple(row[column].strip() for column in ('dataset_id', 'scenario_id', 'method', 'replicate', 'metric'))
        if key in seen:
            raise ValueError(f'duplicate run-level observation at line {line_number}: {key}')
        seen.add(key)

    units = {}
    for row in rows:
        metric = row['metric'].strip()
        unit = row['unit'].strip()
        previous = units.setdefault(metric, unit)
        if previous != unit:
            raise ValueError(f'inconsistent units for metric {metric}: {previous!r} and {unit!r}')

    if design and design.get('frozen'):
        _check_against_design(rows, design)
    return rows


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Validate raw benchmark observations')
    parser.add_argument('observations', type=Path)
    parser.add_argument(
        '--design-dir',
        type=Path,
        default=None,
        help='Directory holding the frozen datasets.tsv, scenarios.tsv, and methods.tsv',
    )
    parser.add_argument(
        '--require-design',
        action='store_true',
        help='Fail when the design tables have not been frozen (publication gate)',
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv[1:])
    try:
        design = load_design(args.design_dir)
        if args.require_design and not design['frozen']:
            raise ValueError(f'benchmark design is not pre-registered: {design["reason"]}')
        rows = validate(args.observations, design=design)
    except (OSError, ValueError) as exc:
        print(f'observation validation failed: {exc}', file=sys.stderr)
        return 1
    if design['frozen']:
        print(f'validated {len(rows)} observations against the frozen design in {design["design_dir"]}')
    else:
        print(f'validated {len(rows)} observations; design not pre-registered ({design["reason"]})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
