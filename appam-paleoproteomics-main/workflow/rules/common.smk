from __future__ import annotations

import csv
import re
from pathlib import Path

from snakemake.exceptions import WorkflowError


REQUIRED_SAMPLE_COLUMNS = ["sample_id", "input_path", "experiment", "fraction"]


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
            if sample_id in seen_sample_ids:
                raise WorkflowError(f"duplicate sample_id in samples.tsv: {sample_id}")
            seen_sample_ids.add(sample_id)
            rows.append({key: (value or "").strip() for key, value in row.items()})

        return rows


SAMPLES = _load_samples()
SAMPLE_IDS = [row["sample_id"] for row in SAMPLES]
SAMPLES_BY_ID = {row["sample_id"]: row for row in SAMPLES}
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
