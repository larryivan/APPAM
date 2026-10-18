import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from visualization_utils import (
    build_length_bins_from_count_map,
    ensure_parent,
    read_tabular_rows,
    validate_required_columns,
    write_tsv_rows,
)


def save_plot(rows, output_png, output_pdf, sample):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    sns.set_theme(
        style="ticks",
        context="paper",
        font_scale=1.1,
        rc={
            "font.family": "sans-serif",
            "axes.grid": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
        },
    )

    fig, ax = plt.subplots(figsize=(9, 4.8))

    if rows:
        labels = [row["label"] for row in rows]
        counts = [row["count"] for row in rows]
        positions = list(range(len(labels)))
        palette = sns.color_palette("flare", n_colors=max(len(labels), 1)).as_hex()
        ax.bar(positions, counts, color=palette, edgecolor="#5A3A2E", linewidth=0.45)
        tick_step = max(1, len(labels) // 18)
        tick_positions = positions[::tick_step]
        ax.set_xticks(tick_positions)
        ax.set_xticklabels([labels[index] for index in tick_positions], rotation=45, ha="right")
    else:
        ax.text(0.5, 0.5, "No reads available", ha="center", va="center", transform=ax.transAxes)

    ax.set_xlabel("Read length range")
    ax.set_ylabel("Read count")
    ax.set_title(f"Read Length Distribution: {sample}")
    ax.grid(axis="y", color="#E6E6E6", linestyle="-", linewidth=0.7)
    ax.set_axisbelow(True)
    sns.despine(ax=ax)
    fig.tight_layout()
    fig.savefig(output_png, dpi=300)
    fig.savefig(output_pdf)
    plt.close(fig)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Plot read length distribution from a length count table."
    )
    parser.add_argument("--counts", required=True, help="Input TSV with length/count columns.")
    parser.add_argument("--output-png", required=True, help="Output PNG path.")
    parser.add_argument("--output-pdf", required=True, help="Output PDF path.")
    parser.add_argument("--output-table", required=True, help="Output binned TSV path.")
    parser.add_argument("--sample", required=True, help="Sample identifier for plot title/log.")
    parser.add_argument("--bin-size", type=int, default=10, help="Read length bin size.")
    parser.add_argument("--log", required=True, help="Output log path.")
    return parser.parse_args(argv)


def run(args):
    input_counts = Path(args.counts)
    output_png = Path(args.output_png)
    output_pdf = Path(args.output_pdf)
    output_table = Path(args.output_table)
    log_path = Path(args.log)

    ensure_parent(output_png)
    ensure_parent(output_pdf)
    ensure_parent(output_table)
    ensure_parent(log_path)

    count_rows, fieldnames = read_tabular_rows(input_counts)
    validate_required_columns(input_counts, fieldnames, ["length", "count"])
    length_count_map = {
        int(row["length"]): int(row["count"])
        for row in count_rows
    }
    rows = build_length_bins_from_count_map(length_count_map, bin_size=args.bin_size)
    total_reads = sum(length_count_map.values())
    write_tsv_rows(output_table, rows, ["start", "end", "label", "count"])
    save_plot(rows, output_png, output_pdf, args.sample)

    with log_path.open("w") as log_handle:
        log_handle.write(f"sample={args.sample}\n")
        log_handle.write(f"reads={total_reads}\n")
        log_handle.write(f"bin_size={args.bin_size}\n")


def main(argv=None):
    run(parse_args(argv))


if __name__ == "__main__":
    main()
