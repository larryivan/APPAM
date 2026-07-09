from __future__ import annotations

import hashlib
import csv
import json
import os
import html
from pathlib import Path


INTERESTING_SUFFIXES = {
    '.csv',
    '.fa',
    '.faa',
    '.fasta',
    '.fna',
    '.html',
    '.json',
    '.mzml',
    '.tsv',
    '.txt',
    '.xml',
    '.yaml',
    '.yml',
}


APPAM_SMK_PATTERNS = (
    ('PyDamage results', 'pydamage/*/pydamage_results.csv', 'damage'),
    ('Ancient contigs', 'pydamage/*/ancient.contigs.fa', 'fasta'),
    ('CheckM report', 'checkm/*/bins_qa.txt', 'quality'),
    ('CheckM2 report', 'checkm2/*/quality_report.tsv', 'quality'),
    ('GUNC report', 'gunc/*/GUNC.progenomes_2.1.maxCSS_level.tsv', 'quality'),
    ('GTDB-Tk summary', 'gtdbtk/*/*.summary.tsv', 'taxonomy'),
    ('Prokka annotations', 'annotation/prokka/*/*/*.gff', 'annotation'),
    ('eggNOG annotations', 'annotation/eggnog/*/*.annotations', 'annotation'),
    ('ABRicate combined report', 'annotation/abricate/*/abricate.tsv', 'annotation'),
    ('RGI reports', 'annotation/rgi/*/*.txt', 'annotation'),
    ('antiSMASH index', 'annotation/antismash/*/*/index.html', 'annotation'),
)

PALEO_PATTERNS = (
    ('mqpar', '**/*.mqpar.xml', 'config'),
    ('mzML', '**/*.mzML', 'spectra'),
    ('proteinGroups', '**/proteinGroups.txt', 'maxquant'),
    ('peptides', '**/peptides.txt', 'maxquant'),
    ('Paleoproteomics QC', '**/paleoproteomics-qc.json', 'quality'),
    ('Paleoproteomics QC report', '**/paleoproteomics-qc.html', 'report'),
)


def _sha256(path: Path, max_bytes: int | None = None) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        remaining = max_bytes
        while True:
            if remaining is not None and remaining <= 0:
                break
            chunk_size = 1024 * 1024 if remaining is None else min(1024 * 1024, remaining)
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
            if remaining is not None:
                remaining -= len(chunk)
    return digest.hexdigest()


def _artifact(label: str, path: Path, kind: str) -> dict:
    return {
        'label': label,
        'path': str(path.resolve()),
        'kind': kind,
        'size_bytes': path.stat().st_size,
        'sha256': _sha256(path, max_bytes=64 * 1024 * 1024),
    }


def _collect_by_patterns(base: Path, patterns: tuple[tuple[str, str, str], ...]) -> list[dict]:
    artifacts = []
    seen = set()
    for label, pattern, kind in patterns:
        for path in sorted(base.glob(pattern)):
            if not path.is_file():
                continue
            resolved = str(path.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            artifacts.append(_artifact(label, path, kind))
    return artifacts


def _collect_generic(candidate_dirs: list[str | None], limit: int = 200) -> list[dict]:
    artifacts = []
    seen = set()
    for candidate in candidate_dirs:
        if not candidate:
            continue
        base_path = Path(candidate)
        if not base_path.exists():
            continue
        for path in sorted(base_path.rglob('*')):
            if len(artifacts) >= limit:
                break
            if not path.is_file() or path.suffix.lower() not in INTERESTING_SUFFIXES:
                continue
            resolved = str(path.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            artifacts.append(_artifact(path.name, path, path.suffix.lower().lstrip('.') or 'file'))
    return artifacts


def _read_tsv_preview(path: Path, limit: int = 10) -> dict:
    if not path.is_file():
        return {'exists': False, 'rows': []}
    rows = []
    with path.open('r', encoding='utf-8', errors='replace') as handle:
        header = handle.readline().rstrip('\n').split('\t')
        for line in handle:
            if len(rows) >= limit:
                break
            values = line.rstrip('\n').split('\t')
            rows.append(dict(zip(header, values)))
    return {'exists': True, 'columns': header, 'rows': rows}


def _read_tsv_rows(path: Path, limit: int = 500) -> list[dict]:
    if not path.is_file():
        return []
    with path.open('r', encoding='utf-8', errors='replace', newline='') as handle:
        reader = csv.DictReader(handle, delimiter='\t')
        return [dict(row) for _, row in zip(range(limit), reader)]


def _count_tsv_rows(path: Path, limit: int | None = None) -> int:
    if not path.is_file():
        return 0
    count = 0
    with path.open('r', encoding='utf-8', errors='replace', newline='') as handle:
        reader = csv.reader(handle, delimiter='\t')
        next(reader, None)
        for _ in reader:
            count += 1
            if limit is not None and count >= limit:
                break
    return count


def _metric(group: str, name: str, value=None, text=None, sample_id=None, unit=None, payload=None) -> dict:
    return {
        'group': group,
        'name': name,
        'value': value,
        'text': text,
        'sample_id': sample_id,
        'unit': unit,
        'payload': payload,
    }


def _numeric(value):
    try:
        if value in (None, ''):
            return None
        return float(str(value).strip())
    except Exception:
        return None


def _first(row: dict, *names):
    lowered = {str(key).lower(): value for key, value in row.items()}
    for name in names:
        if name in row:
            return row.get(name)
        value = lowered.get(str(name).lower())
        if value not in (None, ''):
            return value
    return None


def _metrics_from_summary(summary: dict) -> list[dict]:
    metrics = []
    for name, value in (summary.get('counts') or {}).items():
        metrics.append(_metric('counts', name, value=_numeric(value), text=str(value)))
    return metrics


def build_appam_smk_metrics(results_dir: Path, summary: dict | None = None) -> list[dict]:
    metrics = _metrics_from_summary(summary or build_appam_smk_summary(results_dir))

    for report in sorted(results_dir.glob('checkm2/*/quality_report.tsv')):
        for row in _read_tsv_rows(report):
            sample_id = _first(row, 'Name', 'name', 'Bin Id', 'bin_id', 'genome')
            for column, metric_name, unit in (
                ('Completeness', 'completeness', '%'),
                ('Contamination', 'contamination', '%'),
                ('Quality', 'quality_score', None),
            ):
                value = _numeric(_first(row, column, metric_name))
                if value is not None:
                    metrics.append(_metric('checkm2', metric_name, value=value, sample_id=sample_id, unit=unit, payload=row))

    for report in sorted(results_dir.glob('gunc/*/GUNC.progenomes_2.1.maxCSS_level.tsv')):
        for row in _read_tsv_rows(report):
            sample_id = _first(row, 'genome', 'genome_name', 'name')
            pass_text = _first(row, 'pass.GUNC', 'pass_gunc', 'clade_separation_score', 'CSS')
            metrics.append(_metric('gunc', 'status', text=str(pass_text), sample_id=sample_id, payload=row))
            css = _numeric(_first(row, 'clade_separation_score', 'CSS'))
            if css is not None:
                metrics.append(_metric('gunc', 'clade_separation_score', value=css, sample_id=sample_id, payload=row))

    for report in sorted(results_dir.glob('gtdbtk/*/*.summary.tsv')):
        for row in _read_tsv_rows(report):
            sample_id = _first(row, 'user_genome', 'genome', 'name')
            classification = _first(row, 'classification', 'fastani_reference')
            if classification:
                metrics.append(_metric('gtdbtk', 'classification', text=str(classification), sample_id=sample_id, payload=row))

    for report in sorted(results_dir.glob('annotation/abricate/*/abricate.tsv')):
        sample_id = report.parent.name
        hit_count = _count_tsv_rows(report)
        metrics.append(_metric('abricate', 'hit_count', value=hit_count, text=str(hit_count), sample_id=sample_id))

    for report in sorted(results_dir.glob('annotation/rgi/*/*.txt')):
        sample_id = report.parent.name
        hit_count = _count_tsv_rows(report)
        metrics.append(_metric('rgi', 'hit_count', value=hit_count, text=str(hit_count), sample_id=sample_id))

    for antismash_dir in sorted(results_dir.glob('annotation/antismash/*')):
        if antismash_dir.is_dir():
            gbk_count = len(list(antismash_dir.rglob('*.gbk')))
            metrics.append(_metric('antismash', 'cluster_file_count', value=gbk_count, text=str(gbk_count), sample_id=antismash_dir.name))

    return metrics


def build_paleoproteomics_metrics(results_dir: Path, summary: dict | None = None) -> list[dict]:
    metrics = _metrics_from_summary(summary or build_paleoproteomics_summary(results_dir))
    for report in sorted(results_dir.rglob('proteinGroups.txt')):
        row_count = _count_tsv_rows(report)
        metrics.append(_metric('maxquant', 'protein_group_count', value=row_count, text=str(row_count), payload={'path': str(report)}))
    for report in sorted(results_dir.rglob('peptides.txt')):
        row_count = _count_tsv_rows(report)
        metrics.append(_metric('maxquant', 'peptide_count', value=row_count, text=str(row_count), payload={'path': str(report)}))
    for report in sorted(results_dir.rglob('paleoproteomics-qc.json')):
        try:
            payload = json.loads(report.read_text(encoding='utf-8'))
        except Exception:
            continue
        for name, value in (payload.get('counts') or {}).items():
            numeric = _numeric(value)
            if numeric is not None:
                metrics.append(_metric('paleoproteomics_qc', name, value=numeric, text=str(value)))
        for name, value in (payload.get('rates') or {}).items():
            numeric = _numeric(value)
            if numeric is not None:
                metrics.append(_metric('paleoproteomics_qc', name, value=numeric, text=str(value)))
    return metrics


def build_result_metrics(workflow_id: str | None, results_dir: str | None, summary: dict | None = None) -> list[dict]:
    if not results_dir:
        return []
    base = Path(results_dir)
    if not base.exists():
        return []
    if workflow_id == 'appam-smk':
        return build_appam_smk_metrics(base, summary=summary)
    if workflow_id == 'appam-paleoproteomics':
        return build_paleoproteomics_metrics(base, summary=summary)
    return _metrics_from_summary(summary or build_result_summary(workflow_id, results_dir))


def build_appam_smk_summary(results_dir: Path) -> dict:
    checkm2_reports = sorted(results_dir.glob('checkm2/*/quality_report.tsv'))
    gunc_reports = sorted(results_dir.glob('gunc/*/GUNC.progenomes_2.1.maxCSS_level.tsv'))
    gtdb_reports = sorted(results_dir.glob('gtdbtk/*/*.summary.tsv'))
    return {
        'workflow_id': 'appam-smk',
        'counts': {
            'pydamage_reports': len(list(results_dir.glob('pydamage/*/pydamage_results.csv'))),
            'refined_mag_dirs': len(list(results_dir.glob('metawrap/bin_refinement/*/metawrap_50_10_bins'))),
            'checkm2_reports': len(checkm2_reports),
            'gunc_reports': len(gunc_reports),
            'gtdbtk_reports': len(gtdb_reports),
            'prokka_done': len(list(results_dir.glob('annotation/prokka/*/prokka.done'))),
            'eggnog_done': len(list(results_dir.glob('annotation/eggnog/*/eggnog.done'))),
            'abricate_done': len(list(results_dir.glob('annotation/abricate/*/abricate.done'))),
            'rgi_done': len(list(results_dir.glob('annotation/rgi/*/rgi.done'))),
            'antismash_done': len(list(results_dir.glob('annotation/antismash/*/antismash.done'))),
        },
        'previews': {
            'checkm2': _read_tsv_preview(checkm2_reports[0]) if checkm2_reports else {'exists': False, 'rows': []},
            'gunc': _read_tsv_preview(gunc_reports[0]) if gunc_reports else {'exists': False, 'rows': []},
            'gtdbtk': _read_tsv_preview(gtdb_reports[0]) if gtdb_reports else {'exists': False, 'rows': []},
        },
    }


def build_paleoproteomics_summary(results_dir: Path) -> dict:
    return {
        'workflow_id': 'appam-paleoproteomics',
        'counts': {
            'mzml_files': len(list(results_dir.rglob('*.mzML'))),
            'mqpar_files': len(list(results_dir.rglob('mqpar.xml'))),
            'protein_groups': len(list(results_dir.rglob('proteinGroups.txt'))),
            'peptides': len(list(results_dir.rglob('peptides.txt'))),
            'qc_reports': len(list(results_dir.rglob('paleoproteomics-qc.json'))),
        },
    }


def build_result_summary(workflow_id: str | None, results_dir: str | None) -> dict:
    if not results_dir:
        return {'workflow_id': workflow_id, 'counts': {}}
    base = Path(results_dir)
    if not base.exists():
        return {'workflow_id': workflow_id, 'counts': {}, 'missing_results_dir': str(base)}
    if workflow_id == 'appam-smk':
        return build_appam_smk_summary(base)
    if workflow_id == 'appam-paleoproteomics':
        return build_paleoproteomics_summary(base)
    return {'workflow_id': workflow_id, 'counts': {'files': sum(1 for path in base.rglob('*') if path.is_file())}}


def render_result_report(summary: dict) -> str:
    workflow_id = str(summary.get('workflow_id') or 'workflow')
    count_rows = ''.join(
        f'<tr><th>{html.escape(str(name).replace("_", " ").title())}</th><td>{html.escape(str(value))}</td></tr>'
        for name, value in (summary.get('counts') or {}).items()
    ) or '<tr><td>No count metrics were produced.</td></tr>'

    metric_rows = []
    for metric in summary.get('metrics') or []:
        value = metric.get('metric_value', metric.get('value'))
        if value in (None, ''):
            value = metric.get('metric_text', metric.get('text'))
        metric_rows.append(
            '<tr>'
            f'<td>{html.escape(str(metric.get("metric_group") or metric.get("group") or ""))}</td>'
            f'<td>{html.escape(str(metric.get("metric_name") or metric.get("name") or ""))}</td>'
            f'<td>{html.escape(str(metric.get("sample_id") or ""))}</td>'
            f'<td>{html.escape(str(value if value is not None else ""))}</td>'
            f'<td>{html.escape(str(metric.get("unit") or ""))}</td>'
            '</tr>'
        )
    metrics_table = ''.join(metric_rows) or '<tr><td colspan="5">No detailed metrics were produced.</td></tr>'

    preview_sections = []
    for name, preview in (summary.get('previews') or {}).items():
        rows = preview.get('rows') if isinstance(preview, dict) else None
        if not rows:
            continue
        columns = list(rows[0])
        header = ''.join(f'<th>{html.escape(str(column))}</th>' for column in columns)
        body = ''.join(
            '<tr>' + ''.join(f'<td>{html.escape(str(row.get(column, "")))}</td>' for column in columns) + '</tr>'
            for row in rows[:20]
        )
        preview_sections.append(
            f'<h2>{html.escape(str(name).replace("_", " ").title())} preview</h2>'
            f'<div class="table-wrap"><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></div>'
        )

    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>APPAM result report</title><style>
body{{font:14px/1.5 system-ui,sans-serif;max-width:1180px;margin:32px auto;padding:0 24px;color:#172235;background:#fff}}
h1{{font-size:26px;margin-bottom:4px}}h2{{font-size:18px;margin-top:30px}}.muted{{color:#607085}}
table{{border-collapse:collapse;width:100%}}th,td{{padding:8px 10px;border-bottom:1px solid #dfe6ed;text-align:left;vertical-align:top}}
thead th{{background:#f3f6f9}}.table-wrap{{overflow:auto}}code{{background:#f3f6f9;padding:2px 5px}}
</style></head><body><h1>APPAM result report</h1><p class="muted">Workflow: <code>{html.escape(workflow_id)}</code></p>
<h2>Output summary</h2><table>{count_rows}</table>
<h2>Detailed metrics</h2><div class="table-wrap"><table><thead><tr><th>Group</th><th>Metric</th><th>Sample</th><th>Value</th><th>Unit</th></tr></thead><tbody>{metrics_table}</tbody></table></div>
{''.join(preview_sections)}</body></html>'''


def collect_workflow_artifacts(workflow_context: dict | None) -> list[dict]:
    workflow_context = workflow_context or {}
    workflow_id = workflow_context.get('workflow_id')
    results_dir = workflow_context.get('results_dir')
    reports_dir = workflow_context.get('reports_dir')
    artifacts = []
    if results_dir and Path(results_dir).exists():
        patterns = APPAM_SMK_PATTERNS if workflow_id == 'appam-smk' else PALEO_PATTERNS if workflow_id == 'appam-paleoproteomics' else ()
        artifacts.extend(_collect_by_patterns(Path(results_dir), patterns))

    generic = _collect_generic([results_dir, reports_dir])
    seen = {artifact['path'] for artifact in artifacts}
    for artifact in generic:
        if artifact['path'] not in seen:
            artifacts.append(artifact)
            seen.add(artifact['path'])
        if len(artifacts) >= 250:
            break

    summary = build_result_summary(workflow_id, results_dir)
    summary['metrics'] = build_result_metrics(workflow_id, results_dir, summary=summary)[:250]
    if reports_dir:
        reports_path = Path(reports_dir)
        reports_path.mkdir(parents=True, exist_ok=True)
        summary_path = reports_path / 'result-summary.json'
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
        report_path = reports_path / 'result-report.html'
        report_path.write_text(render_result_report(summary), encoding='utf-8')
        artifacts.insert(0, _artifact('Result summary', summary_path, 'summary'))
        artifacts.insert(1, _artifact('Result report', report_path, 'report'))
    return artifacts


def resource_fingerprint(path_value: str | None) -> dict:
    if not path_value:
        return {'path': None, 'exists': False}
    path = Path(os.path.expanduser(str(path_value)))
    if not path.exists():
        return {'path': str(path), 'exists': False}
    if path.is_file():
        stat = path.stat()
        return {'path': str(path), 'exists': True, 'type': 'file', 'size_bytes': stat.st_size, 'mtime': stat.st_mtime}
    children = sorted(child.name for child in path.iterdir())[:100]
    return {'path': str(path), 'exists': True, 'type': 'directory', 'entries_preview': children}
