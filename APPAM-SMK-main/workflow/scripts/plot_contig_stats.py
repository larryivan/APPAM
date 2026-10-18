import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from visualization_utils import (
    ensure_parent,
    read_tabular_rows,
    summarize_contig_validation,
    validate_required_columns,
    write_tsv_rows,
)


def _threshold_label(name, operator, value):
    return f"{name} {operator} {value:g}"


def save_plot(rows, output_png, output_pdf, accuracy_min=0.5, qvalue_max=0.05):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    from matplotlib.ticker import PercentFormatter

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

    group_order = [
        _threshold_label("Accuracy", ">=", accuracy_min),
        _threshold_label("Accuracy", "<", accuracy_min),
    ]
    status_order = [
        _threshold_label("q-value", "<=", qvalue_max),
        _threshold_label("q-value", ">", qvalue_max),
    ]
    colors = {
        status_order[0]: "#00BFC4",
        status_order[1]: "#F8766D",
    }
    lookup = {(row["group"], row["sig"]): row["proportion"] for row in rows}

    fig, ax = plt.subplots(figsize=(6.5, 4.8))
    bottom = [0] * len(group_order)
    for status in status_order:
        values = [lookup.get((group, status), 0) for group in group_order]
        bars = ax.bar(
            group_order,
            values,
            bottom=bottom,
            label=status,
            color=colors[status],
            edgecolor="black",
            linewidth=0.35,
        )
        for bar, value, base in zip(bars, values, bottom):
            if value >= 0.08:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    base + value / 2,
                    f"{value:.0%}",
                    ha="center",
                    va="center",
                    color="white",
                    fontsize=8,
                )
        bottom = [current + value for current, value in zip(bottom, values)]

    ax.set_ylim(0, 1)
    ax.set_xlabel("")
    ax.set_ylabel("Proportion")
    ax.set_title("")
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0))
    ax.grid(axis="y", color="#D9D9D9", linestyle="-", linewidth=0.7)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color("black")
        spine.set_linewidth(0.8)
    ax.legend(
        title="q-value",
        frameon=False,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.16),
        ncol=2,
    )
    fig.subplots_adjust(bottom=0.24)
    fig.savefig(output_png, dpi=300)
    fig.savefig(output_pdf)
    plt.close(fig)


def save_placeholder_plot(output_png, output_pdf, message):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.5, 4.8))
    ax.text(0.5, 0.5, message, ha="center", va="center", transform=ax.transAxes)
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(output_png, dpi=300)
    fig.savefig(output_pdf)
    plt.close(fig)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Plot PyDamage contig validation proportions."
    )
    parser.add_argument("--pydamage", required=True, help="Input PyDamage result table.")
    parser.add_argument("--output-png", required=True, help="Output PNG path.")
    parser.add_argument("--output-pdf", required=True, help="Output PDF path.")
    parser.add_argument("--output-table", required=True, help="Output summary TSV path.")
    parser.add_argument("--sample", required=True, help="Sample identifier for log.")
    parser.add_argument("--qvalue-column", default="qvalue", help="PyDamage q-value column.")
    parser.add_argument("--qvalue-max", default=0.05, type=float, help="Maximum significant q-value.")
    parser.add_argument(
        "--accuracy-column",
        default="predicted_accuracy",
        help="PyDamage predicted accuracy column.",
    )
    parser.add_argument("--accuracy-min", default=0.5, type=float, help="Minimum predicted accuracy.")
    parser.add_argument("--log", required=True, help="Output log path.")
    return parser.parse_args(argv)


def run(args):
    output_png = Path(args.output_png)
    output_pdf = Path(args.output_pdf)
    output_table = Path(args.output_table)
    log_path = Path(args.log)

    ensure_parent(output_png)
    ensure_parent(output_pdf)
    ensure_parent(output_table)
    ensure_parent(log_path)

    pydamage_path = Path(args.pydamage)
    rows, fieldnames = read_tabular_rows(pydamage_path)
    validate_required_columns(pydamage_path, fieldnames, [args.qvalue_column, args.accuracy_column])
    all_rows = [
        {
            "predicted_accuracy": row.get(args.accuracy_column, ""),
            "qvalue": row.get(args.qvalue_column, ""),
        }
        for row in rows
    ]

    summary_rows = summarize_contig_validation(
        all_rows,
        accuracy_min=args.accuracy_min,
        qvalue_max=args.qvalue_max,
    )
    write_tsv_rows(output_table, summary_rows, ["group", "sig", "count", "proportion"])
    if summary_rows:
        save_plot(
            summary_rows,
            output_png,
            output_pdf,
            accuracy_min=args.accuracy_min,
            qvalue_max=args.qvalue_max,
        )
    else:
        save_placeholder_plot(output_png, output_pdf, "No valid PyDamage rows")

    with log_path.open("w") as log_handle:
        log_handle.write(f"sample={args.sample}\n")
        log_handle.write(f"records={len(all_rows)}\n")
        log_handle.write(f"groups={len(summary_rows)}\n")
        log_handle.write(f"accuracy_min={args.accuracy_min}\n")
        log_handle.write(f"qvalue_max={args.qvalue_max}\n")


def main(argv=None):
    run(parse_args(argv))


if __name__ == "__main__":
    main()
