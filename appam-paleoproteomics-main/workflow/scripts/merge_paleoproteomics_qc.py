import importlib.util
import json
from collections import Counter
from pathlib import Path


def _load_qc_module():
    module_path = Path(__file__).resolve().with_name("paleoproteomics_qc.py")
    spec = importlib.util.spec_from_file_location("paleoproteomics_qc_module", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def merge_payloads(payloads: list[dict], mode: str) -> dict:
    count_keys = (
        "protein_groups",
        "peptides",
        "evidence_rows",
        "protein_contaminants",
        "protein_reverse",
        "peptide_contaminants",
        "peptide_reverse",
        "deamidated_evidence",
    )
    counts = {key: sum(int(payload.get("counts", {}).get(key, 0)) for payload in payloads) for key in count_keys}
    evidence_by_raw_file: Counter[str] = Counter()
    for payload in payloads:
        evidence_by_raw_file.update(payload.get("evidence_by_raw_file", {}))

    qc_module = _load_qc_module()
    return {
        "schema_version": 1,
        "maxquant_mode": mode,
        "analysis_count": len(payloads),
        "analysis_ids": [str(payload.get("analysis_id") or "unknown") for payload in payloads],
        "interpretation_note": (
            "Deamidation is reported as a descriptive quality-control signal and is not, by itself, "
            "evidence of ancient origin."
        ),
        "counts": counts,
        "rates": {
            "protein_contaminant_fraction": qc_module.ratio(counts["protein_contaminants"], counts["protein_groups"]),
            "protein_reverse_fraction": qc_module.ratio(counts["protein_reverse"], counts["protein_groups"]),
            "peptide_contaminant_fraction": qc_module.ratio(counts["peptide_contaminants"], counts["peptides"]),
            "peptide_reverse_fraction": qc_module.ratio(counts["peptide_reverse"], counts["peptides"]),
            "deamidated_evidence_fraction": qc_module.ratio(counts["deamidated_evidence"], counts["evidence_rows"]),
        },
        "evidence_by_raw_file": dict(sorted(evidence_by_raw_file.items())),
        "analyses": payloads,
    }


def run(smk) -> None:
    log_path = Path(smk.log[0])
    json_path = Path(smk.output.json)
    html_path = Path(smk.output.html)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    payloads = [json.loads(Path(path).read_text(encoding="utf-8")) for path in smk.input]
    payload = merge_payloads(payloads, str(smk.params.mode))
    qc_module = _load_qc_module()
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    html_path.write_text(qc_module.render_html(payload), encoding="utf-8")
    log_path.write_text(
        f"mode={smk.params.mode}\nanalyses={len(payloads)}\n",
        encoding="utf-8",
    )


if "snakemake" in globals():
    run(snakemake)
