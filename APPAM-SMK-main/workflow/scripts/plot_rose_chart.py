import argparse
import math
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from visualization_utils import (
    collapse_small_categories,
    count_taxa,
    ensure_parent,
    load_mag_summary_records,
    load_sample_gtdb_records,
    top_n_categories,
    write_tsv_rows,
)


def format_taxon_label(label, max_length=28):
    label = str(label)
    if len(label) <= max_length:
        return label
    return f"{label[:max_length - 3]}..."


def save_plot(rows, output_png, output_pdf, sample, rank_label):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    sns.set_theme(
        style="ticks",
        context="paper",
        font_scale=1.0,
        rc={
            "font.family": "sans-serif",
            "axes.grid": False,
        },
    )

    labels = [row["taxon"] for row in rows]
    counts = [row["count"] for row in rows]
    total = len(labels)
    angles = [2 * math.pi * index / total for index in range(total)]
    width = 2 * math.pi / max(total, 1)
    palette = sns.husl_palette(n_colors=max(total, 1), s=0.68, l=0.62).as_hex()
    colors = {
        "Others": "#BDBDBD",
    }

    fig, ax = plt.subplots(figsize=(8.5, 8.5), subplot_kw={"projection": "polar"})
    bars = ax.bar(
        angles,
        counts,
        width=width,
        bottom=0,
        align="edge",
        edgecolor="#F8F8F8",
        linewidth=1.1,
    )
    for index, bar in enumerate(bars):
        bar.set_color(colors.get(labels[index], palette[index % len(palette)]))

    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks([angle + width / 2 for angle in angles])
    ax.set_xticklabels([format_taxon_label(label) for label in labels])
    ax.set_yticklabels([])
    ax.tick_params(axis="x", pad=8, labelsize=8)
    ax.grid(color="#E6E6E6", linewidth=0.7)
    ax.spines["polar"].set_color("#D0D0D0")
    ax.set_title(f"{rank_label} Nightingale Rose Chart: {sample}", va="bottom")
    fig.tight_layout()
    fig.savefig(output_png, dpi=300)
    fig.savefig(output_pdf)
    plt.close(fig)


def format_count_rows(category_rows):
    return [
        {
            "taxon": row["label"],
            "count": row["count"],
            "fraction": row["fraction"],
        }
        for row in category_rows
    ]


def build_fraction_rows(counts, min_fraction):
    return collapse_small_categories(
        sorted(counts.items(), key=lambda item: item[1], reverse=True),
        min_fraction=min_fraction,
        other_label="Others",
    )


def build_species_rows(counts, top_n):
    return top_n_categories(
        sorted(counts.items(), key=lambda item: item[1], reverse=True),
        top_n=top_n,
        other_label="Others",
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Plot taxonomic rose charts from MAG summary or GTDB-Tk summary files."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--mag-summary", help="Input per-sample or merged MAG summary TSV.")
    input_group.add_argument("--gtdbtk-dir", help="Directory containing GTDB-Tk *.summary.tsv files.")
    parser.add_argument("--sample", required=True, help="Sample identifier for plot title/log.")
    parser.add_argument("--phylum-png", required=True, help="Output phylum PNG path.")
    parser.add_argument("--phylum-pdf", required=True, help="Output phylum PDF path.")
    parser.add_argument("--phylum-table", required=True, help="Output phylum count TSV path.")
    parser.add_argument("--genus-png", required=True, help="Output genus PNG path.")
    parser.add_argument("--genus-pdf", required=True, help="Output genus PDF path.")
    parser.add_argument("--genus-table", required=True, help="Output genus count TSV path.")
    parser.add_argument("--species-png", required=True, help="Output species PNG path.")
    parser.add_argument("--species-pdf", required=True, help="Output species PDF path.")
    parser.add_argument("--species-table", required=True, help="Output species count TSV path.")
    parser.add_argument("--min-fraction", type=float, default=0.01, help="Minimum fraction before grouping as Others.")
    parser.add_argument("--species-top-n", type=int, default=10, help="Number of species categories to keep.")
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
    log_path = Path(args.log)
    output_paths = {
        "phylum": {
            "png": Path(args.phylum_png),
            "pdf": Path(args.phylum_pdf),
            "table": Path(args.phylum_table),
        },
        "genus": {
            "png": Path(args.genus_png),
            "pdf": Path(args.genus_pdf),
            "table": Path(args.genus_table),
        },
        "species": {
            "png": Path(args.species_png),
            "pdf": Path(args.species_pdf),
            "table": Path(args.species_table),
        },
    }

    for rank_outputs in output_paths.values():
        ensure_parent(rank_outputs["png"])
        ensure_parent(rank_outputs["pdf"])
        ensure_parent(rank_outputs["table"])
    ensure_parent(log_path)

    records, input_source = load_records(args)
    if not records:
        raise ValueError("No taxonomy rows were available for rose chart plotting.")

    rank_rows = {
        "phylum": format_count_rows(build_fraction_rows(count_taxa(records, "phylum"), args.min_fraction)),
        "genus": format_count_rows(build_fraction_rows(count_taxa(records, "genus"), args.min_fraction)),
        "species": format_count_rows(build_species_rows(count_taxa(records, "species"), args.species_top_n)),
    }

    for rank, rows in rank_rows.items():
        if not rows:
            raise ValueError(f"No {rank} rows were available for rose chart plotting.")
        outputs = output_paths[rank]
        write_tsv_rows(outputs["table"], rows, ["taxon", "count", "fraction"])
        save_plot(rows, outputs["png"], outputs["pdf"], args.sample, rank.title())

    with log_path.open("w") as log_handle:
        log_handle.write(f"sample={args.sample}\n")
        log_handle.write(f"input_source={input_source}\n")
        log_handle.write(f"records={len(records)}\n")
        for rank, rows in rank_rows.items():
            log_handle.write(f"{rank}_taxa={len(rows)}\n")


def main(argv=None):
    run(parse_args(argv))


if __name__ == "__main__":
    main()
