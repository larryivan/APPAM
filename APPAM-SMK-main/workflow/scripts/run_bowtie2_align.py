from __future__ import annotations

import gzip
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
bam = Path(snakemake.output.bam)
log_path = Path(snakemake.log[0])
threads = str(snakemake.threads)

r1_has_reads = has_reads(r1)
r2_has_reads = has_reads(r2)
se_has_reads = has_reads(se)
if r1_has_reads != r2_has_reads:
    raise ValueError("paired FASTQ outputs are inconsistent: only one mate contains reads")
if not r1_has_reads and not se_has_reads:
    raise ValueError("preprocessing produced no reads for damage mapping")

bowtie_command = [
    "bowtie2",
    "-p",
    threads,
    "--very-sensitive",
    "-N",
    "1",
    "-x",
    str(snakemake.params.index_prefix),
]
if r1_has_reads:
    bowtie_command.extend(["-1", r1, "-2", r2])
if se_has_reads:
    bowtie_command.extend(["-U", se])

bam.parent.mkdir(parents=True, exist_ok=True)
log_path.parent.mkdir(parents=True, exist_ok=True)
commands = [
    bowtie_command,
    ["samtools", "view", "-@", threads, "-h", "-Sb", "-"],
    ["samtools", "calmd", "-@", threads, "-u", "-", str(snakemake.input.contigs)],
    ["samtools", "sort", "-@", threads, "-l", "4", "-o", str(bam), "-"],
]

with log_path.open("wb") as log_handle:
    processes = []
    previous_stdout = None
    for index, command in enumerate(commands):
        process = subprocess.Popen(
            command,
            stdin=previous_stdout,
            stdout=subprocess.PIPE if index < len(commands) - 1 else subprocess.DEVNULL,
            stderr=log_handle,
        )
        if previous_stdout is not None:
            previous_stdout.close()
        previous_stdout = process.stdout
        processes.append(process)

    return_codes = [process.wait() for process in reversed(processes)]
    if any(code != 0 for code in return_codes):
        raise RuntimeError(f"alignment pipeline failed with return codes {list(reversed(return_codes))}")

if not bam.is_file() or bam.stat().st_size == 0:
    raise RuntimeError(f"alignment did not produce a BAM file: {bam}")
