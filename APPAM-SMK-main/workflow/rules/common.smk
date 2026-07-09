from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


SAMPLE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
FASTQ_SUFFIXES = (".fastq.gz", ".fq.gz", ".fastq", ".fq")


def _resolve_read_path(value, default_name, samples_file, raw_data_dir):
    raw_value = str(value or "").strip()
    if not raw_value:
        path = Path(raw_data_dir) / default_name
        return path.expanduser().resolve()

    path = Path(raw_value).expanduser()
    if path.is_absolute():
        return path.resolve()

    manifest_dir = Path(samples_file).expanduser().resolve().parent
    raw_dir = Path(raw_data_dir).expanduser().resolve()
    candidates = [
        manifest_dir / path,
        raw_dir / path,
        raw_dir / path.name,
        Path.cwd() / path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def load_samples(samples_file, raw_data_dir):
    samples_path = Path(samples_file).expanduser().resolve()
    df = pd.read_csv(samples_path, sep="\t", dtype=str).fillna("")
    if "sample_id" not in df.columns:
        raise ValueError("samples_file must include a 'sample_id' column")

    rows = {}
    for row_number, row in enumerate(df.to_dict(orient="records"), start=2):
        sample_id = str(row.get("sample_id", "")).strip()
        if not sample_id:
            raise ValueError(f"empty sample_id at row {row_number}")
        if not SAMPLE_ID_PATTERN.fullmatch(sample_id):
            raise ValueError(
                f"invalid sample_id at row {row_number}: {sample_id!r}; "
                "use letters, numbers, dots, underscores, and hyphens"
            )
        if sample_id in rows:
            raise ValueError(f"duplicate sample_id: {sample_id}")

        r1_value = row.get("forward_reads") or row.get("r1") or row.get("R1")
        r2_value = row.get("reverse_reads") or row.get("r2") or row.get("R2")
        r1 = _resolve_read_path(r1_value, f"{sample_id}_R1.fastq.gz", samples_path, raw_data_dir)
        r2 = _resolve_read_path(r2_value, f"{sample_id}_R2.fastq.gz", samples_path, raw_data_dir)
        for label, path in (("forward_reads", r1), ("reverse_reads", r2)):
            if not path.is_file():
                raise ValueError(f"{label} for {sample_id} not found: {path}")
            if not str(path).lower().endswith(FASTQ_SUFFIXES):
                raise ValueError(f"{label} for {sample_id} is not FASTQ: {path}")

        rows[sample_id] = {
            "sample_id": sample_id,
            "forward_reads": str(r1),
            "reverse_reads": str(r2),
        }

    if not rows:
        raise ValueError("samples_file has no sample rows")
    return rows


def sample_r1(wildcards):
    return SAMPLE_ROWS[wildcards.sample]["forward_reads"]


def sample_r2(wildcards):
    return SAMPLE_ROWS[wildcards.sample]["reverse_reads"]
