import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from visualization_utils import (
    bin_ani_records,
    ensure_parent,
    load_mag_summary_records,
    load_sample_gtdb_records,
    write_tsv_rows,
)


def build_bin_labels(start, end, step):
    labels = []
    lower = start
    while lower < end:
        upper = lower + step
        if upper >= end:
            labels.append(f"[{lower},{end}]")
        else:
            labels.append(f"[{lower},{upper})")
        lower += step
    return labels


def save_plot(rows, output_png, output_pdf, sample, start, end, step):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
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

    labels = build_bin_labels(start, end, step)
    domain_order = ["Bacteria", "Archaea"]
    colors = {
        "Bacteria": "#B7B7EB",
        "Archaea": "#F09BA0",
    }

    counts = {(row["ani_bin"], row["domain"]): row["count"] for row in rows}
    domains = domain_order + sorted(
        {row["domain"] for row in rows if row["domain"] not in domain_order}
    )
    positions = list(range(len(labels)))

    fig, ax = plt.subplots(figsize=(8, 5))
    bottom = [0] * len(labels)
    for domain in domains:
        values = [counts.get((label, domain), 0) for label in labels]
        if not any(values):
            continue
        ax.bar(
            positions,
            values,
            bottom=bottom,
            label=domain,
            color=colors.get(domain, "#BFBFBF"),
            edgecolor="white",
            linewidth=0.7,
        )
        bottom = [current + value for current, value in zip(bottom, values)]

    ax.set_xlabel("Average Nucleotide Identity (%)")
    ax.set_ylabel("Count (MAGs)")
    ax.set_title(f"ANI to Closest GTDB Reference: {sample}")
    plotted_domains = [
        domain
        for domain in domains
        if any(counts.get((label, domain), 0) for label in labels)
    ]
    ax.legend(
        title="Domain",
        loc="upper center",
        bbox_to_anchor=(0.5, -0.24),
        ncol=max(1, len(plotted_domains)),
        frameon=False,
    )
    ax.set_xticks(positions)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.grid(axis="y", color="#E6E6E6", linestyle="-", linewidth=0.7)
    ax.set_axisbelow(True)
    if sns is not None:
        sns.despine(ax=ax)
    else:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    fig.subplots_adjust(bottom=0.32)
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

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=13, wrap=True)
    ax.set_title(f"ANI to Closest GTDB Reference: {sample}")
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(output_png, dpi=300)
    fig.savefig(output_pdf)
    plt.close(fig)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Plot ANI histogram from MAG summary or GTDB-Tk summary files."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--mag-summary", help="Input per-sample or merged MAG summary TSV.")
    input_group.add_argument("--gtdbtk-dir", help="Directory containing GTDB-Tk *.summary.tsv files.")
    parser.add_argument("--output-png", required=True, help="Output PNG path.")
    parser.add_argument("--output-pdf", required=True, help="Output PDF path.")
    parser.add_argument("--output-table", required=True, help="Output binned TSV path.")
    parser.add_argument("--sample", required=True, help="Sample identifier for plot title/log.")
    parser.add_argument("--start", type=int, default=95, help="ANI bin start.")
    parser.add_argument("--end", type=int, default=100, help="ANI bin end.")
    parser.add_argument("--step", type=int, default=1, help="ANI bin step.")
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


def count_valid_ani_records(records):
    count = 0
    for record in records:
        try:
            float(record.get("closest_genome_ani", ""))
        except (TypeError, ValueError):
            continue
        count += 1
    return count


def count_binned_ani_records(summary_rows):
    return sum(int(row["count"]) for row in summary_rows)


def run(args):
    output_png = Path(args.output_png)
    output_pdf = Path(args.output_pdf)
    output_table = Path(args.output_table)
    log_path = Path(args.log)

    ensure_parent(output_png)
    ensure_parent(output_pdf)
    ensure_parent(output_table)
    ensure_parent(log_path)

    records, input_source = load_records(args)
    valid_ani_records = count_valid_ani_records(records)
    missing_ani_records = len(records) - valid_ani_records
    summary_rows = bin_ani_records(records, start=args.start, end=args.end, step=args.step)
    binned_records = count_binned_ani_records(summary_rows)
    if not summary_rows:
        if valid_ani_records:
            status = "no_binned_ani"
            message = "Valid ANI values were available, but none fell within the configured ANI bin range."
        else:
            status = "no_valid_ani"
            message = "No valid ANI values were available for this sample."
        write_tsv_rows(output_table, [], ["ani_bin", "domain", "count"])
        save_placeholder_plot(
            output_png,
            output_pdf,
            args.sample,
            message,
        )
        with log_path.open("w") as log_handle:
            log_handle.write(f"sample={args.sample}\n")
            log_handle.write(f"input_source={input_source}\n")
            log_handle.write(f"status={status}\n")
            log_handle.write(f"records={len(records)}\n")
            log_handle.write(f"valid_ani_records={valid_ani_records}\n")
            log_handle.write(f"missing_ani_records={missing_ani_records}\n")
            log_handle.write("binned_records=0\n")
        return

    write_tsv_rows(output_table, summary_rows, ["ani_bin", "domain", "count"])
    save_plot(summary_rows, output_png, output_pdf, args.sample, args.start, args.end, args.step)

    with log_path.open("w") as log_handle:
        log_handle.write(f"sample={args.sample}\n")
        log_handle.write(f"input_source={input_source}\n")
        log_handle.write(f"records={len(records)}\n")
        log_handle.write(f"valid_ani_records={valid_ani_records}\n")
        log_handle.write(f"missing_ani_records={missing_ani_records}\n")
        log_handle.write(f"binned_records={binned_records}\n")


def main(argv=None):
    run(parse_args(argv))


if __name__ == "__main__":
    main()
