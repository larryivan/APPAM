import csv
from pathlib import Path


def ensure_parent(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def merge_summary_files(input_paths, output_path):
    output_path = Path(output_path)
    ensure_parent(output_path)

    wrote_header = False
    row_count = 0
    with output_path.open("w", newline="") as output_handle:
        writer = None
        for input_path in input_paths:
            with Path(input_path).open("r", newline="") as input_handle:
                reader = csv.DictReader(input_handle, delimiter="\t")
                if reader.fieldnames is None:
                    continue
                if writer is None:
                    writer = csv.DictWriter(
                        output_handle,
                        fieldnames=reader.fieldnames,
                        delimiter="\t",
                    )
                if not wrote_header:
                    writer.writeheader()
                    wrote_header = True
                for row in reader:
                    writer.writerow(row)
                    row_count += 1
    return row_count


def main_from_snakemake(smk):
    row_count = merge_summary_files(smk.input, smk.output.table)
    log_path = Path(smk.log[0])
    ensure_parent(log_path)
    with log_path.open("w") as log_handle:
        log_handle.write(f"samples={len(smk.input)}\n")
        log_handle.write(f"rows={row_count}\n")
        log_handle.write(f"output={smk.output.table}\n")


if "snakemake" in globals():
    main_from_snakemake(snakemake)
