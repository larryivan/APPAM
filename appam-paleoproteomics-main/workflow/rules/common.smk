from __future__ import annotations

import csv
import re
from pathlib import Path

from snakemake.exceptions import WorkflowError


REQUIRED_SAMPLE_COLUMNS = ["sample_id", "input_path", "experiment", "fraction"]
SAMPLE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


def _load_samples() -> list[dict[str, str]]:
    with Path(config["sample_table"]).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != REQUIRED_SAMPLE_COLUMNS:
            columns = ", ".join(REQUIRED_SAMPLE_COLUMNS)
            raise WorkflowError(f"samples.tsv must contain columns: {columns}")

        rows = []
        seen_sample_ids: set[str] = set()
        for row in reader:
            if not any((value or "").strip() for value in row.values()):
                continue

            sample_id = (row.get("sample_id") or "").strip()
            if not sample_id:
                raise WorkflowError("empty sample_id in samples.tsv")
            if not SAMPLE_ID_PATTERN.fullmatch(sample_id):
                raise WorkflowError(
                    f"invalid sample_id in samples.tsv: {sample_id!r}; "
                    "use 1-100 letters, numbers, dots, underscores, or hyphens"
                )
            if sample_id in seen_sample_ids:
                raise WorkflowError(f"duplicate sample_id in samples.tsv: {sample_id}")
            seen_sample_ids.add(sample_id)
            rows.append({key: (value or "").strip() for key, value in row.items()})

        if not rows:
            raise WorkflowError("samples.tsv has no sample rows")
        return rows


SAMPLES = _load_samples()
SAMPLE_IDS = [row["sample_id"] for row in SAMPLES]
SAMPLES_BY_ID = {row["sample_id"]: row for row in SAMPLES}
SAMPLE_ID_REGEX = "|".join(re.escape(sample_id) for sample_id in SAMPLE_IDS) or "(?!)"
RAW_SAMPLE_ID_REGEX = "|".join(
    re.escape(row["sample_id"])
    for row in SAMPLES
    if Path(row["input_path"]).suffix.lower() == ".raw"
) or "(?!)"
D_SAMPLE_ID_REGEX = "|".join(
    re.escape(row["sample_id"])
    for row in SAMPLES
    if Path(row["input_path"]).name.lower().endswith(".d") and Path(row["input_path"]).is_dir()
) or "(?!)"
MAXQUANT_MODE = str(config.get("maxquant_mode", "batch")).strip().lower()
if MAXQUANT_MODE not in {"batch", "per_sample_id"}:
    raise WorkflowError(
        f"maxquant_mode must be batch or per_sample_id; got {MAXQUANT_MODE!r}"
    )

MZML_TARGETS = expand("<results>/mzml/{sample}.mzML", sample=SAMPLE_IDS)
if MAXQUANT_MODE == "batch":
    MQPAR_TARGETS = ["<maxquant>/batch/mqpar.xml"]
    MAXQUANT_TARGETS = [
        "<maxquant>/batch/combined/txt/proteinGroups.txt",
        "<maxquant>/batch/combined/txt/peptides.txt",
        "<maxquant>/batch/combined/txt/evidence.txt",
    ]
    QC_INPUT_TARGETS = ["<results>/reports/maxquant/batch.qc.json"]
else:
    MQPAR_TARGETS = expand("<maxquant>/samples/{sample}/mqpar.xml", sample=SAMPLE_IDS)
    MAXQUANT_TARGETS = [
        *expand("<maxquant>/samples/{sample}/combined/txt/proteinGroups.txt", sample=SAMPLE_IDS),
        *expand("<maxquant>/samples/{sample}/combined/txt/peptides.txt", sample=SAMPLE_IDS),
        *expand("<maxquant>/samples/{sample}/combined/txt/evidence.txt", sample=SAMPLE_IDS),
    ]
    QC_INPUT_TARGETS = expand("<results>/reports/maxquant/samples/{sample}.qc.json", sample=SAMPLE_IDS)


def _sample_input_path(sample: str) -> Path:
    try:
        return Path(SAMPLES_BY_ID[sample]["input_path"])
    except KeyError as exc:
        raise WorkflowError(f"unknown sample_id: {sample}") from exc


def _raw_input(wildcards) -> str:
    input_path = _sample_input_path(wildcards.sample)
    if input_path.is_file() and input_path.suffix.lower() == ".raw":
        return str(input_path)
    raise WorkflowError(f"sample {wildcards.sample} is not a RAW input: {input_path}")


def _d_input(wildcards) -> str:
    input_path = _sample_input_path(wildcards.sample)
    if input_path.is_dir() and input_path.name.lower().endswith(".d"):
        return str(input_path)
    raise WorkflowError(f"sample {wildcards.sample} is not a .d input: {input_path}")
