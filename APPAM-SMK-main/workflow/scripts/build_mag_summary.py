import csv
import re
from pathlib import Path


SUMMARY_COLUMNS = [
    "Sample_ID",
    "Bin_ID",
    "Completeness",
    "Contamination",
    "Quality",
    "Quality_Basis",
    "Genome_Size",
    "Contig_Count",
    "Contig_N50",
    "GC_Content",
    "Domain",
    "Phylum",
    "Class",
    "Order",
    "Family",
    "Genus",
    "Species",
    "Closest_Genome_ANI",
    "Classification",
    "GUNC_Pass",
    "GUNC_CSS_Level",
    "GUNC_Clade_Separation_Score",
    "GUNC_Contamination_Portion",
]

QUALITY_BASIS = "Completeness/contamination proxy; full MIMAG criteria not evaluated"

FASTA_SUFFIXES = {".fa", ".fasta", ".fna"}
MISSING_TOKENS = {"", "na", "n/a", "none", "nan", "null"}


def ensure_parent(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def normalize_key(key):
    return re.sub(r"[^a-z0-9]+", "_", str(key).strip().lower()).strip("_")


def normalize_row(row):
    return {normalize_key(key): value for key, value in row.items() if key is not None}


def first_value(row, keys, default=""):
    for key in keys:
        value = row.get(normalize_key(key), "")
        if value is None:
            continue
        text = str(value).strip()
        if text.lower() not in MISSING_TOKENS:
            return text
    return default


def strip_fasta_suffix(name):
    text = Path(str(name).strip()).name.rstrip(".")
    lower_text = text.lower()
    for suffix in sorted(FASTA_SUFFIXES, key=len, reverse=True):
        if lower_text.endswith(suffix):
            text = text[: -len(suffix)]
            break
    return text.rstrip(".")


def read_tabular_rows(path):
    path = Path(path)
    with path.open("r", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters="\t,")
        except csv.Error:
            dialect = csv.excel_tab
        reader = csv.DictReader(handle, dialect=dialect)
        if reader.fieldnames is None:
            raise ValueError(f"{path} is missing a header row.")
        return list(reader), reader.fieldnames


def write_tsv_rows(path, rows, fieldnames=SUMMARY_COLUMNS):
    path = Path(path)
    ensure_parent(path)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def parse_gtdb_taxonomy(taxonomy_str):
    ranks = {
        "Domain": "",
        "Phylum": "",
        "Class": "",
        "Order": "",
        "Family": "",
        "Genus": "",
        "Species": "",
    }
    if taxonomy_str is None:
        return ranks

    text = str(taxonomy_str).strip()
    if text.lower() in MISSING_TOKENS or text == "Unclassified":
        return ranks

    prefix_map = {
        "d__": "Domain",
        "p__": "Phylum",
        "c__": "Class",
        "o__": "Order",
        "f__": "Family",
        "g__": "Genus",
        "s__": "Species",
    }
    for part in text.split(";"):
        part = part.strip()
        for prefix, rank in prefix_map.items():
            if part.startswith(prefix):
                ranks[rank] = part.replace(prefix, "", 1)
                break
    return ranks


def assign_quality(completeness, contamination):
    try:
        cpl = float(completeness)
        con = float(contamination)
    except (TypeError, ValueError):
        return "Unknown"

    if cpl >= 90 and con <= 5:
        return "High-quality"
    if cpl >= 50 and con <= 10:
        return "Medium-quality"
    return "Low-quality"


def compute_n50(lengths):
    total = sum(lengths)
    if total <= 0:
        return 0
    cumulative = 0
    for length in sorted(lengths, reverse=True):
        cumulative += length
        if cumulative >= total / 2:
            return length
    return 0


def compute_fasta_metrics(path):
    lengths = []
    current_length = 0
    total_bases = 0
    acgt_bases = 0
    gc_bases = 0

    with Path(path).open("r") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            if text.startswith(">"):
                if current_length:
                    lengths.append(current_length)
                current_length = 0
                continue

            sequence = text.upper()
            current_length += len(sequence)
            total_bases += len(sequence)
            for base in sequence:
                if base in {"A", "C", "G", "T"}:
                    acgt_bases += 1
                    if base in {"G", "C"}:
                        gc_bases += 1

    if current_length:
        lengths.append(current_length)

    gc_content = "" if acgt_bases == 0 else f"{(gc_bases / acgt_bases) * 100:.2f}"
    return {
        "Genome_Size": total_bases,
        "Contig_Count": len(lengths),
        "Contig_N50": compute_n50(lengths),
        "GC_Content": gc_content,
    }


def parse_checkm2_table(path):
    if not path or not Path(path).is_file():
        return {}
    rows, _ = read_tabular_rows(path)
    parsed = {}
    for row in rows:
        normalized = normalize_row(row)
        bin_id = first_value(
            normalized,
            ["Name", "Bin Id", "Bin_ID", "BinID", "Genome", "genome"],
        )
        if not bin_id:
            continue
        bin_id = strip_fasta_suffix(bin_id)
        parsed[bin_id] = {
            "Completeness": first_value(normalized, ["Completeness"]),
            "Contamination": first_value(normalized, ["Contamination"]),
        }
    return parsed


def extract_gtdb_ani(normalized_row):
    return first_value(
        normalized_row,
        ["closest_genome_ani", "fastani_ani", "closest_placement_ani"],
    )


def parse_gtdb_summaries(paths):
    parsed = {}
    for path in sorted(Path(item) for item in paths if item):
        if not path.exists():
            continue
        rows, _ = read_tabular_rows(path)
        for row in rows:
            normalized = normalize_row(row)
            bin_id = first_value(normalized, ["user_genome", "genome", "Name"])
            if not bin_id:
                continue
            bin_id = strip_fasta_suffix(bin_id)
            classification = first_value(normalized, ["classification"], "Unclassified")
            parsed[bin_id] = {
                "Classification": classification,
                "Closest_Genome_ANI": extract_gtdb_ani(normalized),
                **parse_gtdb_taxonomy(classification),
            }
    return parsed


def parse_gunc_table(path):
    if not path:
        return {}
    path = Path(path)
    if not path.exists():
        return {}

    rows, _ = read_tabular_rows(path)
    parsed = {}
    for row in rows:
        normalized = normalize_row(row)
        bin_id = first_value(normalized, ["genome", "bin_id", "Name", "user_genome"])
        if not bin_id:
            continue
        bin_id = strip_fasta_suffix(bin_id)
        parsed[bin_id] = {
            "GUNC_Pass": first_value(normalized, ["pass.GUNC", "pass_gunc", "pass"]),
            "GUNC_CSS_Level": first_value(
                normalized,
                ["taxonomic_level", "css_level", "max_css_level", "level"],
            ),
            "GUNC_Clade_Separation_Score": first_value(
                normalized,
                ["clade_separation_score", "css", "maxcss", "max_css"],
            ),
            "GUNC_Contamination_Portion": first_value(
                normalized,
                ["contamination_portion", "contamination"],
            ),
        }
    return parsed


def load_fasta_metrics(bins_dir):
    metrics = {}
    bins_path = Path(bins_dir)
    if not bins_path.exists():
        return metrics

    for fasta in sorted(path for path in bins_path.iterdir() if path.suffix.lower() in FASTA_SUFFIXES):
        metrics[fasta.stem] = compute_fasta_metrics(fasta)
    return metrics


def bin_sort_key(bin_id):
    text = str(bin_id)
    match = re.search(r"^bin\.(\d+)$", text)
    if match:
        return (0, int(match.group(1)), text)
    return (1, text)


def ordered_bin_ids(*maps):
    seen = set()
    bin_ids = []
    for item in maps:
        for bin_id in item:
            if bin_id in seen:
                continue
            seen.add(bin_id)
            bin_ids.append(bin_id)
    return sorted(bin_ids, key=bin_sort_key)


def build_sample_summary(sample, checkm2_path, gtdb_summary_paths, gunc_path, bins_dir):
    checkm2 = parse_checkm2_table(checkm2_path)
    gtdb = parse_gtdb_summaries(gtdb_summary_paths)
    gunc = parse_gunc_table(gunc_path)
    fasta_metrics = load_fasta_metrics(bins_dir)

    rows = []
    for bin_id in ordered_bin_ids(checkm2, fasta_metrics, gtdb, gunc):
        qc = checkm2.get(bin_id, {})
        classification = gtdb.get(bin_id, {}).get("Classification", "Unclassified")
        taxonomy = parse_gtdb_taxonomy(classification)
        metrics = fasta_metrics.get(bin_id, {})
        gtdb_row = gtdb.get(bin_id, {})
        gunc_row = gunc.get(bin_id, {})
        completeness = qc.get("Completeness", "")
        contamination = qc.get("Contamination", "")

        rows.append(
            {
                "Sample_ID": sample,
                "Bin_ID": bin_id,
                "Completeness": completeness,
                "Contamination": contamination,
                "Quality": assign_quality(completeness, contamination),
                "Quality_Basis": QUALITY_BASIS,
                "Genome_Size": metrics.get("Genome_Size", ""),
                "Contig_Count": metrics.get("Contig_Count", ""),
                "Contig_N50": metrics.get("Contig_N50", ""),
                "GC_Content": metrics.get("GC_Content", ""),
                "Domain": taxonomy["Domain"],
                "Phylum": taxonomy["Phylum"],
                "Class": taxonomy["Class"],
                "Order": taxonomy["Order"],
                "Family": taxonomy["Family"],
                "Genus": taxonomy["Genus"],
                "Species": taxonomy["Species"],
                "Closest_Genome_ANI": gtdb_row.get("Closest_Genome_ANI", ""),
                "Classification": classification,
                "GUNC_Pass": gunc_row.get("GUNC_Pass", ""),
                "GUNC_CSS_Level": gunc_row.get("GUNC_CSS_Level", ""),
                "GUNC_Clade_Separation_Score": gunc_row.get(
                    "GUNC_Clade_Separation_Score", ""
                ),
                "GUNC_Contamination_Portion": gunc_row.get(
                    "GUNC_Contamination_Portion", ""
                ),
            }
        )
    return rows


def find_gtdb_summary_files(done_path):
    if not done_path:
        return []
    done_path = Path(done_path)
    if not done_path.parent.exists():
        return []
    return sorted(done_path.parent.glob("*.summary.tsv"))


def optional_named_input(value):
    values = list(value) if not isinstance(value, (str, Path)) else [value]
    return values[0] if values else None


def main_from_snakemake(smk):
    sample = smk.wildcards.sample
    rows = build_sample_summary(
        sample=sample,
        checkm2_path=optional_named_input(smk.input.checkm2),
        gtdb_summary_paths=find_gtdb_summary_files(optional_named_input(smk.input.gtdb_done)),
        gunc_path=optional_named_input(smk.input.gunc),
        bins_dir=smk.input.bins_dir,
    )
    write_tsv_rows(smk.output.sample_summary, rows)

    log_path = Path(smk.log[0])
    ensure_parent(log_path)
    with log_path.open("w") as log_handle:
        log_handle.write(f"sample={sample}\n")
        log_handle.write(f"rows={len(rows)}\n")
        log_handle.write(f"output={smk.output.sample_summary}\n")


if "snakemake" in globals():
    main_from_snakemake(snakemake)
