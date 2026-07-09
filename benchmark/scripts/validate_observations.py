from __future__ import annotations

import csv
import math
import sys
from pathlib import Path


REQUIRED_COLUMNS = ['dataset_id', 'scenario_id', 'method', 'replicate', 'metric', 'value', 'unit']


def validate(path: Path) -> list[dict[str, str]]:
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
    return rows


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f'usage: {argv[0]} OBSERVATIONS.tsv', file=sys.stderr)
        return 2
    try:
        rows = validate(Path(argv[1]))
    except (OSError, ValueError) as exc:
        print(f'observation validation failed: {exc}', file=sys.stderr)
        return 1
    print(f'validated {len(rows)} observations')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
