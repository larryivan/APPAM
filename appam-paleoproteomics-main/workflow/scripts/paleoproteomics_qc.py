import csv
import html
import json
from collections import Counter
from pathlib import Path


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8-sig', newline='') as handle:
        return [dict(row) for row in csv.DictReader(handle, delimiter='\t')]


def marked(row: dict[str, str], column: str) -> bool:
    return str(row.get(column) or '').strip() == '+'


def deamidated(row: dict[str, str]) -> bool:
    text = ' '.join(
        str(row.get(column) or '')
        for column in ('Modifications', 'Modified sequence', 'Modification names')
    ).lower()
    return 'deamid' in text


def ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def build_qc(protein_groups_path: Path, peptides_path: Path, evidence_path: Path) -> dict:
    protein_groups = read_tsv(protein_groups_path)
    peptides = read_tsv(peptides_path)
    evidence = read_tsv(evidence_path)

    protein_contaminants = sum(marked(row, 'Potential contaminant') for row in protein_groups)
    protein_reverse = sum(marked(row, 'Reverse') for row in protein_groups)
    peptide_contaminants = sum(marked(row, 'Potential contaminant') for row in peptides)
    peptide_reverse = sum(marked(row, 'Reverse') for row in peptides)
    deamidated_evidence = sum(deamidated(row) for row in evidence)
    raw_file_counts = Counter(
        str(row.get('Raw file') or 'unknown').strip() or 'unknown'
        for row in evidence
    )

    return {
        'schema_version': 1,
        'interpretation_note': (
            'Deamidation is reported as a descriptive quality-control signal and is not, by itself, '
            'evidence of ancient origin.'
        ),
        'counts': {
            'protein_groups': len(protein_groups),
            'peptides': len(peptides),
            'evidence_rows': len(evidence),
            'protein_contaminants': protein_contaminants,
            'protein_reverse': protein_reverse,
            'peptide_contaminants': peptide_contaminants,
            'peptide_reverse': peptide_reverse,
            'deamidated_evidence': deamidated_evidence,
        },
        'rates': {
            'protein_contaminant_fraction': ratio(protein_contaminants, len(protein_groups)),
            'protein_reverse_fraction': ratio(protein_reverse, len(protein_groups)),
            'peptide_contaminant_fraction': ratio(peptide_contaminants, len(peptides)),
            'peptide_reverse_fraction': ratio(peptide_reverse, len(peptides)),
            'deamidated_evidence_fraction': ratio(deamidated_evidence, len(evidence)),
        },
        'evidence_by_raw_file': dict(sorted(raw_file_counts.items())),
    }


def render_html(payload: dict) -> str:
    count_rows = ''.join(
        f'<tr><th>{html.escape(name.replace("_", " ").title())}</th><td>{value}</td></tr>'
        for name, value in payload['counts'].items()
    )
    rate_rows = ''.join(
        f'<tr><th>{html.escape(name.replace("_", " ").title())}</th><td>{"NA" if value is None else f"{value:.4f}"}</td></tr>'
        for name, value in payload['rates'].items()
    )
    sample_rows = ''.join(
        f'<tr><th>{html.escape(name)}</th><td>{value}</td></tr>'
        for name, value in payload['evidence_by_raw_file'].items()
    )
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>APPAM paleoproteomics QC</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;max-width:960px;margin:32px auto;padding:0 20px;color:#182230}}h1{{font-size:26px}}h2{{font-size:18px;margin-top:28px}}table{{border-collapse:collapse;width:100%}}th,td{{padding:8px 10px;border-bottom:1px solid #dce3ea;text-align:left}}th{{width:68%;font-weight:600}}.note{{padding:12px 14px;background:#f4f7fa;border-left:3px solid #60758a}}</style>
</head><body><h1>APPAM paleoproteomics QC</h1><p class="note">{html.escape(payload['interpretation_note'])}</p>
<h2>Identification counts</h2><table>{count_rows}</table><h2>QC fractions</h2><table>{rate_rows}</table>
<h2>Evidence by raw file</h2><table>{sample_rows}</table></body></html>'''


def run(snakemake_object) -> None:
    log_path = Path(snakemake_object.log[0])
    json_path = Path(snakemake_object.output.json)
    html_path = Path(snakemake_object.output.html)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_qc(
        Path(snakemake_object.input.protein_groups),
        Path(snakemake_object.input.peptides),
        Path(snakemake_object.input.evidence),
    )
    json_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    html_path.write_text(render_html(payload), encoding='utf-8')
    log_path.write_text('Paleoproteomics QC report generated.\n', encoding='utf-8')


if 'snakemake' in globals():
    run(snakemake)
