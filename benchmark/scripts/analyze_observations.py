from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

from validate_observations import validate


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def bootstrap_ci(values: list[float], iterations: int, rng: random.Random) -> tuple[float, float]:
    if len(values) == 1:
        return values[0], values[0]
    means = [statistics.fmean(rng.choices(values, k=len(values))) for _ in range(iterations)]
    return percentile(means, 0.025), percentile(means, 0.975)


def analyze(rows: list[dict[str, str]], baseline: str, iterations: int, seed: int):
    grouped = defaultdict(list)
    units = {}
    paired_values = {}
    for row in rows:
        group_key = (row['dataset_id'], row['scenario_id'], row['method'], row['metric'])
        value = float(row['value'])
        grouped[group_key].append(value)
        units[row['metric']] = row['unit']
        paired_values[(row['dataset_id'], row['scenario_id'], int(row['replicate']), row['metric'], row['method'])] = value

    rng = random.Random(seed)
    summaries = []
    for (dataset_id, scenario_id, method, metric), values in sorted(grouped.items()):
        ci_low, ci_high = bootstrap_ci(values, iterations, rng)
        summaries.append({
            'dataset_id': dataset_id,
            'scenario_id': scenario_id,
            'method': method,
            'metric': metric,
            'unit': units[metric],
            'n': len(values),
            'mean': statistics.fmean(values),
            'sd': statistics.stdev(values) if len(values) > 1 else 0.0,
            'median': statistics.median(values),
            'ci95_low': ci_low,
            'ci95_high': ci_high,
        })

    differences = []
    for key, method_value in sorted(paired_values.items()):
        dataset_id, scenario_id, replicate, metric, method = key
        if method == baseline:
            continue
        baseline_key = (dataset_id, scenario_id, replicate, metric, baseline)
        if baseline_key not in paired_values:
            continue
        baseline_value = paired_values[baseline_key]
        differences.append({
            'dataset_id': dataset_id,
            'scenario_id': scenario_id,
            'method': method,
            'baseline': baseline,
            'replicate': replicate,
            'metric': metric,
            'unit': units[metric],
            'method_value': method_value,
            'baseline_value': baseline_value,
            'difference': method_value - baseline_value,
        })
    return summaries, differences


def write_tsv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('observations', type=Path)
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--iterations', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=20260710)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--paired', type=Path, required=True)
    parser.add_argument('--json', dest='json_path', type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.iterations < 100:
        raise ValueError('bootstrap iterations must be at least 100')
    rows = validate(args.observations)
    methods = {row['method'] for row in rows}
    if args.baseline not in methods:
        raise ValueError(f'baseline method is absent: {args.baseline}')
    summaries, differences = analyze(rows, args.baseline, args.iterations, args.seed)
    summary_columns = ['dataset_id', 'scenario_id', 'method', 'metric', 'unit', 'n', 'mean', 'sd', 'median', 'ci95_low', 'ci95_high']
    paired_columns = ['dataset_id', 'scenario_id', 'method', 'baseline', 'replicate', 'metric', 'unit', 'method_value', 'baseline_value', 'difference']
    write_tsv(args.summary, summaries, summary_columns)
    write_tsv(args.paired, differences, paired_columns)
    args.json_path.parent.mkdir(parents=True, exist_ok=True)
    args.json_path.write_text(json.dumps({
        'schema_version': 1,
        'baseline': args.baseline,
        'bootstrap_iterations': args.iterations,
        'seed': args.seed,
        'summaries': summaries,
        'paired_differences': differences,
    }, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
