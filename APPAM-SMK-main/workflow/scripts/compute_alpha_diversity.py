import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from visualization_utils import (
    ensure_parent,
    load_mag_summary_records,
    load_sample_gtdb_records,
    summarize_alpha_diversity,
    write_tsv_rows,
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Compute alpha diversity from MAG summary or GTDB-Tk summary files."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--mag-summary", help="Input per-sample or merged MAG summary TSV.")
    input_group.add_argument("--gtdbtk-dir", help="Directory containing GTDB-Tk *.summary.tsv files.")
    parser.add_argument("--output-table", required=True, help="Output alpha diversity TSV path.")
    parser.add_argument("--sample", required=True, help="Sample identifier for output/log.")
    parser.add_argument(
        "--rank",
        action="append",
        dest="ranks",
        default=None,
        help="Taxonomic rank to summarize. Can be provided multiple times.",
    )
    parser.add_argument("--log", required=True, help="Output log path.")
    return parser.parse_args(argv)


def load_records(args):
    if args.mag_summary:
        return load_mag_summary_records(args.mag_summary, args.sample), "mag_summary"

    gtdbtk_dir = Path(args.gtdbtk_dir)
    summary_files = sorted(gtdbtk_dir.glob("*.summary.tsv"))
    if not summary_files:
        raise FileNotFoundError(f"No GTDB summary files found in {gtdbtk_dir}")
    return load_sample_gtdb_records(summary_files, args.sample), "gtdbtk"


def run(args):
    output_table = Path(args.output_table)
    log_path = Path(args.log)
    ranks = args.ranks or ["phylum", "genus", "species"]

    ensure_parent(output_table)
    ensure_parent(log_path)

    records, input_source = load_records(args)
    if not records:
        raise ValueError("No taxonomy rows were available for alpha diversity calculation.")

    rows = summarize_alpha_diversity(records, ranks=ranks)
    for row in rows:
        row["sample"] = args.sample

    write_tsv_rows(output_table, rows, ["sample", "rank", "shannon_index", "observed_taxa", "total_bins"])

    with log_path.open("w") as log_handle:
        log_handle.write(f"sample={args.sample}\n")
        log_handle.write(f"input_source={input_source}\n")
        log_handle.write(f"records={len(records)}\n")
        log_handle.write(f"ranks={','.join(ranks)}\n")


def main(argv=None):
    run(parse_args(argv))


if __name__ == "__main__":
    main()
