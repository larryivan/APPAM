import gzip
from collections import Counter
from pathlib import Path


def _open_text(path: Path):
    if path.name.lower().endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def count_fastq_lengths(path: Path) -> Counter[int]:
    counts: Counter[int] = Counter()
    with _open_text(path) as handle:
        while True:
            header = handle.readline()
            if not header:
                break
            sequence = handle.readline().rstrip("\r\n")
            plus = handle.readline()
            quality = handle.readline().rstrip("\r\n")
            if not sequence or not plus or not quality:
                raise ValueError(f"truncated FASTQ record in {path}")
            if not header.startswith("@") or not plus.startswith("+"):
                raise ValueError(f"invalid FASTQ record in {path}")
            if len(sequence) != len(quality):
                raise ValueError(f"sequence/quality length mismatch in {path}")
            counts[len(sequence)] += 1
    return counts


def run(smk) -> None:
    input_path = Path(smk.input.fastq)
    output_path = Path(smk.output.counts)
    log_path = Path(smk.log[0])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    counts = count_fastq_lengths(input_path)
    with output_path.open("w", encoding="utf-8") as handle:
        handle.write("length\tcount\n")
        for length, count in sorted(counts.items()):
            handle.write(f"{length}\t{count}\n")
    log_path.write_text(
        f"input={input_path}\nreads={sum(counts.values())}\nlengths={len(counts)}\n",
        encoding="utf-8",
    )


if "snakemake" in globals():
    run(snakemake)
