from __future__ import annotations

import argparse
import csv
from pathlib import Path


METRICS = {
    's': ('runtime_seconds', 'seconds'),
    'max_rss': ('peak_rss_mb', 'MB'),
    'cpu_time': ('cpu_time_seconds', 'seconds'),
}


def read_benchmark(path: Path) -> dict[str, str]:
    with path.open('r', encoding='utf-8', newline='') as handle:
        rows = list(csv.DictReader(handle, delimiter='\t'))
    if len(rows) != 1:
        raise ValueError(f'expected one Snakemake benchmark row in {path}, found {len(rows)}')
    return rows[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('benchmark', type=Path)
    parser.add_argument('--dataset', required=True)
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--method', required=True)
    parser.add_argument('--replicate', required=True, type=int)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.replicate < 1:
        raise ValueError('replicate must be >= 1')

    source = read_benchmark(args.benchmark)
    rows = []
    for source_column, (metric, unit) in METRICS.items():
        value = str(source.get(source_column) or '').strip()
        if value:
            float(value)
            rows.append({
                'dataset_id': args.dataset,
                'scenario_id': args.scenario,
                'method': args.method,
                'replicate': args.replicate,
                'metric': metric,
                'value': value,
                'unit': unit,
            })
    if not rows:
        raise ValueError(f'no supported runtime columns found in {args.benchmark}')

    args.output.parent.mkdir(parents=True, exist_ok=True)
    columns = ['dataset_id', 'scenario_id', 'method', 'replicate', 'metric', 'value', 'unit']
    with args.output.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    main()
