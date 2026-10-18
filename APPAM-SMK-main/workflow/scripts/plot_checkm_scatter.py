import argparse
import random
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from visualization_utils import ensure_parent, parse_checkm_rows, write_tsv_rows


def save_plot(rows, output_png, output_pdf, sample):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
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

    colors = {
        "HQ": "#009E73",
        "MQ": "#E69F00",
        "LQ": "#999999",
    }
    quality_order = ["HQ", "MQ", "LQ"]

    rng = random.Random(42)
    plot_rows = [
        {
            **row,
            "completeness_jitter": row["completeness"] + rng.uniform(-0.8, 0.8),
            "contamination_jitter": row["contamination"] + rng.uniform(-0.15, 0.15),
        }
        for row in rows
    ]
    plot_df = pd.DataFrame(plot_rows)

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    sns.scatterplot(
        data=plot_df,
        x="completeness_jitter",
        y="contamination_jitter",
        hue="quality",
        hue_order=quality_order,
        palette=colors,
        s=80,
        edgecolor="black",
        linewidth=0.6,
        alpha=0.85,
        ax=ax,
    )

    ax.axhline(y=5, color="#777777", linestyle="--", linewidth=1, alpha=0.7)
    ax.axvline(x=90, color="#777777", linestyle="--", linewidth=1, alpha=0.7)
    ax.axhline(y=10, color="#BDBDBD", linestyle=":", linewidth=1, alpha=0.7)
    ax.axvline(x=50, color="#BDBDBD", linestyle=":", linewidth=1, alpha=0.7)

    ax.set_xlabel("Completeness (%)")
    ax.set_ylabel("Contamination (%)")
    ax.set_xlim(48, 102)
    ax.set_ylim(-1, 11)
    ax.set_title(f"CheckM2 Completeness/Contamination: {sample}")
    ax.grid(True, color="#E6E6E6", linewidth=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    sns.despine(ax=ax)
    ax.legend(title="Proxy class", frameon=False)
    fig.tight_layout()
    fig.savefig(output_png, dpi=300)
    fig.savefig(output_pdf)
    plt.close(fig)


def save_placeholder_plot(output_png, output_pdf, sample):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    ax.text(0.5, 0.5, "No valid CheckM2 rows", ha="center", va="center", transform=ax.transAxes)
    ax.set_title(f"CheckM2 Completeness/Contamination: {sample}")
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(output_png, dpi=300)
    fig.savefig(output_pdf)
    plt.close(fig)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Plot MAG completeness/contamination proxy classes from MAG summary or CheckM2 output."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--mag-summary", help="Input per-sample or merged MAG summary TSV.")
    input_group.add_argument("--quality-report", help="Input CheckM2 quality report.")
    parser.add_argument("--output-png", required=True, help="Output PNG path.")
    parser.add_argument("--output-pdf", required=True, help="Output PDF path.")
    parser.add_argument("--output-table", required=True, help="Output parsed TSV path.")
    parser.add_argument("--sample", required=True, help="Sample identifier for plot title/log.")
    parser.add_argument("--log", required=True, help="Output log path.")
    return parser.parse_args(argv)


def run(args):
    input_table = Path(args.mag_summary or args.quality_report)
    input_source = "mag_summary" if args.mag_summary else "checkm2"
    output_png = Path(args.output_png)
    output_pdf = Path(args.output_pdf)
    output_table = Path(args.output_table)
    log_path = Path(args.log)

    ensure_parent(output_png)
    ensure_parent(output_pdf)
    ensure_parent(output_table)
    ensure_parent(log_path)

    rows, _ = parse_checkm_rows(
        input_table,
        sample=args.sample if args.mag_summary else None,
    )
    write_tsv_rows(output_table, rows, ["bin_id", "completeness", "contamination", "quality"])
    if rows:
        save_plot(rows, output_png, output_pdf, args.sample)
    else:
        save_placeholder_plot(output_png, output_pdf, args.sample)

    with log_path.open("w") as log_handle:
        log_handle.write(f"sample={args.sample}\n")
        log_handle.write(f"input_source={input_source}\n")
        log_handle.write(f"rows={len(rows)}\n")


def main(argv=None):
    run(parse_args(argv))


if __name__ == "__main__":
    main()
