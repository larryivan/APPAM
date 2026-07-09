from __future__ import annotations

import gzip
import shutil
import subprocess
from pathlib import Path


def has_reads(path_value: str) -> bool:
    path = Path(path_value)
    opener = gzip.open if path.name.lower().endswith(".gz") else open
    with opener(path, "rb") as handle:
        return bool(handle.read(1))


r1 = str(snakemake.input.r1)
r2 = str(snakemake.input.r2)
se = str(snakemake.input.se)
outdir = Path(snakemake.params.outdir)
log_path = Path(snakemake.log[0])

r1_has_reads = has_reads(r1)
r2_has_reads = has_reads(r2)
se_has_reads = has_reads(se)
if r1_has_reads != r2_has_reads:
    raise ValueError("paired FASTQ outputs are inconsistent: only one mate contains reads")
if not r1_has_reads and not se_has_reads:
    raise ValueError("preprocessing produced no reads for assembly")

if outdir.exists():
    shutil.rmtree(outdir)
outdir.parent.mkdir(parents=True, exist_ok=True)
log_path.parent.mkdir(parents=True, exist_ok=True)

command = [
    "megahit",
    "-o",
    str(outdir),
    "--min-contig-len",
    str(snakemake.params.min_contig_len),
    "-t",
    str(snakemake.threads),
]
if r1_has_reads:
    command.extend(["-1", r1, "-2", r2])
if se_has_reads:
    command.extend(["-r", se])

with log_path.open("w", encoding="utf-8") as log_handle:
    log_handle.write("command=" + subprocess.list2cmdline(command) + "\n")
    log_handle.flush()
    subprocess.run(command, stdout=log_handle, stderr=subprocess.STDOUT, check=True)

contigs = Path(snakemake.output.contigs)
if not contigs.is_file() or contigs.stat().st_size == 0:
    raise RuntimeError(f"MEGAHIT did not produce contigs: {contigs}")
Path(snakemake.output.done).touch()
shutil.rmtree(outdir / "intermediate_contigs", ignore_errors=True)
shutil.rmtree(outdir / "intermediate_files", ignore_errors=True)
