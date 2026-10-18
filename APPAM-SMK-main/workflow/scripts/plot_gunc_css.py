import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from visualization_utils import (
    ensure_parent,
    filter_rows_by_sample,
    normalize_summary_quality,
    parse_checkm_rows,
    read_tabular_rows,
    summarize_gunc_css_from_gunc_rows,
    summarize_gunc_css_by_quality,
    write_tsv_rows,
)


def save_plot(rows, output_png, output_pdf, sample):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    try:
        import seaborn as sns
    except ModuleNotFoundError:
        sns = None

    if sns is not None:
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
    else:
        plt.rcParams.update({
            "font.family": "sans-serif",
            "axes.grid": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
        })

    quality_order = ["HQ", "MQ"]
    colors = {
        "HQ": "#009E73",
        "MQ": "#E69F00",
    }
    plot_df = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(5.8, 4.8))
    if sns is not None:
        sns.boxplot(
            data=plot_df,
            x="quality",
            y="gunc_clade_separation_score",
            order=quality_order,
            hue="quality",
            hue_order=quality_order,
            palette=colors,
            width=0.5,
            showfliers=False,
            linewidth=1.0,
            legend=False,
            ax=ax,
        )
        sns.stripplot(
            data=plot_df,
            x="quality",
            y="gunc_clade_separation_score",
            order=quality_order,
            hue="quality",
            hue_order=quality_order,
            palette=colors,
            jitter=0.12,
            size=5.5,
            edgecolor="black",
            linewidth=0.6,
            alpha=0.85,
            legend=False,
            ax=ax,
        )
    else:
        for index, quality in enumerate(quality_order):
            values = list(
                plot_df.loc[
                    plot_df["quality"] == quality,
                    "gunc_clade_separation_score",
                ]
            )
            if not values:
                continue
            ax.boxplot(
                [values],
                positions=[index],
                widths=0.5,
                patch_artist=True,
                showfliers=False,
                boxprops={
                    "facecolor": colors[quality],
                    "edgecolor": "#555555",
                    "alpha": 0.35,
                },
                medianprops={"color": "#222222", "linewidth": 1.2},
                whiskerprops={"color": "#555555"},
                capprops={"color": "#555555"},
            )
            if len(values) == 1:
                offsets = [0.0]
            else:
                offsets = [
                    -0.09 + 0.18 * point_index / (len(values) - 1)
                    for point_index in range(len(values))
                ]
            ax.scatter(
                [index + offset for offset in offsets],
                values,
                s=32,
                color=colors[quality],
                edgecolors="black",
                linewidths=0.6,
                alpha=0.85,
            )
        ax.set_xticks(range(len(quality_order)))
        ax.set_xticklabels(quality_order)

    ax.set_ylim(bottom=-0.03)
    ax.set_xlabel("Completeness/contamination proxy class")
    ax.set_ylabel("GUNC-CSS")
    ax.set_title(f"GUNC CSS by MAG Quality: {sample}")
    ax.grid(axis="y", color="#E6E6E6", linewidth=0.7)
    ax.set_axisbelow(True)
    if sns is not None:
        sns.despine(ax=ax)
    else:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(output_png, dpi=300)
    fig.savefig(output_pdf)
    plt.close(fig)


def save_placeholder_plot(output_png, output_pdf, sample, message):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    try:
        import seaborn as sns
    except ModuleNotFoundError:
        sns = None

    if sns is not None:
        sns.set_theme(style="ticks", context="paper", font_scale=1.1)

    fig, ax = plt.subplots(figsize=(5.8, 4.8))
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=12, wrap=True)
    ax.set_title(f"GUNC CSS by MAG Quality: {sample}")
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(output_png, dpi=300)
    fig.savefig(output_pdf)
    plt.close(fig)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Plot GUNC clade separation scores by completeness/contamination proxy class."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--mag-summary", help="Input per-sample or merged MAG summary TSV.")
    input_group.add_argument("--gunc-report", help="Input GUNC maxCSS TSV.")
    parser.add_argument(
        "--quality-report",
        help="Input CheckM2 quality report. Required with --gunc-report.",
    )
    parser.add_argument("--output-png", required=True, help="Output PNG path.")
    parser.add_argument("--output-pdf", required=True, help="Output PDF path.")
    parser.add_argument("--output-table", required=True, help="Output plotted value TSV path.")
    parser.add_argument("--sample", required=True, help="Sample identifier for plot title/log.")
    parser.add_argument("--log", required=True, help="Output log path.")
    return parser.parse_args(argv)


def load_plot_rows(args):
    if args.mag_summary:
        summary_rows, _ = read_tabular_rows(args.mag_summary)
        summary_rows = filter_rows_by_sample(summary_rows, args.sample)
        return summary_rows, summarize_gunc_css_by_quality(summary_rows), "mag_summary"

    if not args.quality_report:
        raise ValueError("--quality-report is required when using --gunc-report.")
    gunc_rows, _ = read_tabular_rows(args.gunc_report)
    quality_rows, _ = parse_checkm_rows(args.quality_report)
    return (
        gunc_rows,
        summarize_gunc_css_from_gunc_rows(gunc_rows, quality_rows),
        "gunc_report",
    )


def count_missing_gunc_css_records(rows):
    missing = 0
    for row in rows:
        normalized = {
            str(key).strip().lower().replace(" ", "_"): value
            for key, value in row.items()
            if key is not None
        }
        quality = normalize_summary_quality(normalized.get("quality", ""))
        if quality not in {"HQ", "MQ"}:
            continue
        try:
            float(
                normalized.get("gunc_clade_separation_score", "")
                or normalized.get("clade_separation_score", "")
            )
        except (TypeError, ValueError):
            missing += 1
    return missing


def run(args):
    output_png = Path(args.output_png)
    output_pdf = Path(args.output_pdf)
    output_table = Path(args.output_table)
    log_path = Path(args.log)

    ensure_parent(output_png)
    ensure_parent(output_pdf)
    ensure_parent(output_table)
    ensure_parent(log_path)

    input_rows, plot_rows, input_source = load_plot_rows(args)
    missing_gunc_css_records = count_missing_gunc_css_records(input_rows)
    if not plot_rows:
        write_tsv_rows(
            output_table,
            [],
            ["bin_id", "quality", "gunc_clade_separation_score"],
        )
        save_placeholder_plot(
            output_png,
            output_pdf,
            args.sample,
            "No valid HQ/MQ GUNC-CSS values were available for this sample.",
        )
        with log_path.open("w") as log_handle:
            log_handle.write(f"sample={args.sample}\n")
            log_handle.write(f"input_source={input_source}\n")
            log_handle.write("status=no_valid_gunc_css\n")
            log_handle.write(f"records={len(input_rows)}\n")
            log_handle.write(f"missing_gunc_css_records={missing_gunc_css_records}\n")
            log_handle.write("plotted_records=0\n")
        return

    write_tsv_rows(
        output_table,
        plot_rows,
        ["bin_id", "quality", "gunc_clade_separation_score"],
    )
    save_plot(plot_rows, output_png, output_pdf, args.sample)

    with log_path.open("w") as log_handle:
        log_handle.write(f"sample={args.sample}\n")
        log_handle.write(f"input_source={input_source}\n")
        log_handle.write(f"records={len(input_rows)}\n")
        log_handle.write(f"missing_gunc_css_records={missing_gunc_css_records}\n")
        log_handle.write(f"plotted_records={len(plot_rows)}\n")


def main(argv=None):
    run(parse_args(argv))


if __name__ == "__main__":
    main()
