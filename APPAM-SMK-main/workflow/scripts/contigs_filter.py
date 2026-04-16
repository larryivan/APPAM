import csv
import subprocess
import tempfile
from pathlib import Path


def _is_ancient(row, columns, thresholds):
    qvalue_raw = row.get(columns["qvalue"], "")
    accuracy_raw = row.get(columns["predicted_accuracy"], "")
    try:
        qvalue = float(qvalue_raw)
        accuracy = float(accuracy_raw)
    except (TypeError, ValueError):
        return False
    return qvalue <= thresholds["qvalue_max"] and accuracy >= thresholds["predicted_accuracy_min"]


def _validate_columns(fieldnames, columns):
    required = {columns["contig"], columns["qvalue"], columns["predicted_accuracy"]}
    missing = [col for col in required if col not in fieldnames]
    if missing:
        raise ValueError(
            "Missing columns in pydamage_results.csv: "
            + ", ".join(missing)
            + f". Available columns: {', '.join(fieldnames)}"
        )


contigs_path = Path(snakemake.input.contigs)
pydamage_path = Path(snakemake.input.pydamage)
ancient_path = Path(snakemake.output.ancient)
modern_path = Path(snakemake.output.modern)
log_path = Path(snakemake.log[0])

ancient_path.parent.mkdir(parents=True, exist_ok=True)
log_path.parent.mkdir(parents=True, exist_ok=True)

columns = {
    "contig": snakemake.params.contig_column,
    "qvalue": snakemake.params.qvalue_column,
    "predicted_accuracy": snakemake.params.predicted_accuracy_column,
}
thresholds = {
    "qvalue_max": float(snakemake.params.qvalue_max),
    "predicted_accuracy_min": float(snakemake.params.predicted_accuracy_min),
}

ancient_ids = set()
with pydamage_path.open("r", newline="") as handle:
    reader = csv.DictReader(handle)
    if reader.fieldnames is None:
        raise ValueError("pydamage_results.csv is missing a header row.")
    _validate_columns(reader.fieldnames, columns)
    for row in reader:
        contig_id = row.get(columns["contig"], "")
        if not contig_id:
            continue
        if _is_ancient(row, columns, thresholds):
            ancient_ids.add(contig_id)

with log_path.open("w") as log_handle, tempfile.TemporaryDirectory() as tmpdir:
    ids_path = Path(tmpdir) / "ancient_ids.txt"
    if ancient_ids:
        ids_path.write_text("\n".join(sorted(ancient_ids)) + "\n")
    else:
        ids_path.write_text("")

    log_handle.write(f"qvalue_max={thresholds['qvalue_max']}\n")
    log_handle.write(f"predicted_accuracy_min={thresholds['predicted_accuracy_min']}\n")
    log_handle.write(f"ancient_id_count={len(ancient_ids)}\n")
    log_handle.flush()

    subprocess.run(
        [
            "seqkit",
            "grep",
            "-f",
            str(ids_path),
            str(contigs_path),
            "-o",
            str(ancient_path),
        ],
        check=True,
        stderr=log_handle,
    )
    subprocess.run(
        [
            "seqkit",
            "grep",
            "-v",
            "-f",
            str(ids_path),
            str(contigs_path),
            "-o",
            str(modern_path),
        ],
        check=True,
        stderr=log_handle,
    )
