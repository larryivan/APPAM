import csv
import math
import re
from pathlib import Path


MISSING_TOKENS = {"", "na", "n/a", "none", "nan", "null"}
FASTA_SUFFIXES = {".fa", ".fasta", ".fna"}


def ensure_parent(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def _fallback_delimiter_from_fieldnames(fieldnames):
    if not fieldnames or len(fieldnames) != 1:
        return None
    header = fieldnames[0]
    if "," in header:
        return ","
    if "\t" in header:
        return "\t"
    return None


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
        fallback_delimiter = _fallback_delimiter_from_fieldnames(reader.fieldnames)
        if fallback_delimiter is not None:
            handle.seek(0)
            reader = csv.DictReader(handle, delimiter=fallback_delimiter)
        rows = list(reader)
        return rows, reader.fieldnames


def write_tsv_rows(path, rows, fieldnames):
    path = Path(path)
    ensure_parent(path)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def validate_required_columns(path, fieldnames, required_columns):
    missing = [column for column in required_columns if column not in fieldnames]
    if missing:
        raise ValueError(
            f"{path} is missing required columns: {', '.join(missing)}. "
            f"Available columns: {', '.join(fieldnames)}"
        )


def detect_domain_from_filename(filename):
    name = Path(filename).name.lower()
    if re.search(r"(^|[._-])bac\d*", name) or "bacteria" in name:
        return "Bacteria"
    if re.search(r"(^|[._-])(ar|arc)\d*", name) or "archaea" in name:
        return "Archaea"
    return None


def infer_domain_from_record(summary_file, row):
    domain = detect_domain_from_filename(Path(summary_file).name)
    if domain:
        return domain

    classification = str(row.get("classification", ""))
    if classification.startswith("d__Bacteria"):
        return "Bacteria"
    if classification.startswith("d__Archaea"):
        return "Archaea"
    return "Unknown"


def read_identifier_list(path, column_name=None):
    path = Path(path)
    with path.open("r", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters="\t,")
        except csv.Error:
            dialect = csv.excel_tab
        reader = csv.reader(handle, dialect=dialect)
        rows = [row for row in reader if any(cell.strip() for cell in row)]
        if len(rows) == 1 and rows[0]:
            header = rows[0][0]
            delimiter = "," if "," in header else "\t" if "\t" in header else None
            if delimiter is not None:
                handle.seek(0)
                reader = csv.reader(handle, delimiter=delimiter)
                rows = [row for row in reader if any(cell.strip() for cell in row)]

    if not rows:
        return []

    header = [cell.strip() for cell in rows[0]]
    if column_name and column_name in header:
        index = header.index(column_name)
        values = rows[1:]
    else:
        index = 0
        values = rows

    seen = []
    for row in values:
        if index >= len(row):
            continue
        value = row[index].strip()
        if value:
            seen.append(value)
    return seen


def normalize_group_value(value):
    text = str(value).strip()
    upper = text.upper()
    if upper.startswith("MIS"):
        return upper[3:]
    return upper


def matches_group_value(value, expected):
    return str(value).strip() == str(expected).strip() or (
        normalize_group_value(value) == normalize_group_value(expected)
    )


def extract_phylum(classification):
    return extract_taxon(classification, "p__")


def extract_taxon(classification, prefix, default="Unclassified"):
    if not classification:
        return default
    for field in str(classification).split(";"):
        if field.startswith(prefix):
            label = field[len(prefix):].strip()
            return label or default
    return default


def extract_genus(classification):
    return extract_taxon(classification, "g__")


def extract_species(classification):
    return extract_taxon(classification, "s__")


def extract_gtdb_ani(row):
    missing_tokens = {"", "na", "n/a", "none", "nan"}
    for column in ("closest_genome_ani", "fastani_ani", "closest_placement_ani"):
        value = str(row.get(column, "")).strip()
        if value and value.lower() not in missing_tokens:
            return value
    return ""


def normalize_gtdb_record(row, domain, sample):
    classification = row.get("classification")
    return {
        "sample": sample,
        "accession_MAGbin": row.get("user_genome", ""),
        "domain": domain,
        "phylum": extract_phylum(classification),
        "genus": extract_genus(classification),
        "species": extract_species(classification),
        "classification": classification or "",
        "closest_genome_ani": extract_gtdb_ani(row),
    }


def normalize_bin_id(value):
    text = Path(str(value).strip()).name.rstrip(".")
    lower_text = text.lower()
    for suffix in sorted(FASTA_SUFFIXES, key=len, reverse=True):
        if lower_text.endswith(suffix):
            text = text[: -len(suffix)]
            break
    return text.rstrip(".")


def _first_non_missing(normalized, keys, default=""):
    for key in keys:
        lookup_key = re.sub(r"[^a-z0-9]+", "_", str(key).strip().lower()).strip("_")
        value = normalized.get(lookup_key, "")
        if value is None:
            continue
        text = str(value).strip()
        if text.lower() not in MISSING_TOKENS:
            return text
    return default


def filter_rows_by_sample(rows, sample):
    filtered = []
    saw_sample_column = False
    for row in rows:
        normalized = _normalize_row_lookup(row)
        row_sample = _first_non_missing(normalized, ["Sample_ID", "sample", "sample_id"])
        if not row_sample:
            filtered.append(row)
            continue
        saw_sample_column = True
        if str(row_sample) == str(sample):
            filtered.append(row)
    return filtered if saw_sample_column else list(rows)


def normalize_mag_summary_record(row, sample):
    normalized = _normalize_row_lookup(row)
    row_sample = _first_non_missing(normalized, ["Sample_ID", "sample", "sample_id"], sample)
    bin_id = _first_non_missing(normalized, ["Bin_ID", "Bin Id", "binid", "Name", "Genome"])
    classification = _first_non_missing(normalized, ["Classification", "classification"], "")
    return {
        "sample": row_sample,
        "accession_MAGbin": normalize_bin_id(bin_id),
        "domain": _first_non_missing(normalized, ["Domain"], extract_taxon(classification, "d__", "Unknown")),
        "phylum": _first_non_missing(normalized, ["Phylum"], extract_phylum(classification)),
        "genus": _first_non_missing(normalized, ["Genus"], extract_genus(classification)),
        "species": _first_non_missing(normalized, ["Species"], extract_species(classification)),
        "classification": classification,
        "closest_genome_ani": _first_non_missing(
            normalized,
            ["Closest_Genome_ANI", "closest_genome_ani", "fastani_ani", "closest_placement_ani"],
        ),
    }


def load_mag_summary_records(summary_path, sample):
    rows, _ = read_tabular_rows(summary_path)
    records = []
    for row in rows:
        record = normalize_mag_summary_record(row, sample)
        if record["sample"] and str(record["sample"]) != str(sample):
            continue
        records.append(record)
    return records


def load_sample_gtdb_records(summary_files, sample):
    required_columns = ["user_genome", "classification"]
    records = []
    for summary_file in sorted(Path(path) for path in summary_files):
        rows, fieldnames = read_tabular_rows(summary_file)
        validate_required_columns(summary_file, fieldnames, required_columns)
        for row in rows:
            records.append(
                normalize_gtdb_record(
                    row,
                    domain=infer_domain_from_record(summary_file, row),
                    sample=sample,
                )
            )
    return records


def count_taxa(records, rank):
    counts = {}
    for record in records:
        label = str(record.get(rank, "")).strip() or "Unclassified"
        counts[label] = counts.get(label, 0) + 1
    return counts


def shannon_index_from_counts(counts):
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    shannon = 0.0
    for count in counts.values():
        if count <= 0:
            continue
        proportion = count / total
        shannon -= proportion * math.log(proportion)
    return shannon


def summarize_alpha_diversity(records, ranks):
    rows = []
    for rank in ranks:
        counts = count_taxa(records, rank)
        rows.append(
            {
                "rank": rank,
                "shannon_index": shannon_index_from_counts(counts),
                "observed_taxa": len(counts),
                "total_bins": sum(counts.values()),
            }
        )
    return rows


def top_n_categories(rows, top_n, other_label="Others"):
    kept = []
    other_count = 0
    total = sum(count for _, count in rows)
    for index, (label, count) in enumerate(rows):
        if index < top_n:
            kept.append(
                {
                    "label": label,
                    "count": count,
                    "fraction": count / total if total else 0,
                }
            )
        else:
            other_count += count
    if other_count:
        kept.append(
            {
                "label": other_label,
                "count": other_count,
                "fraction": other_count / total if total else 0,
            }
        )
    return kept


def build_length_bins(lengths, bin_size):
    length_count_map = {}
    for length in lengths:
        int_length = int(length)
        length_count_map[int_length] = length_count_map.get(int_length, 0) + 1
    return build_length_bins_from_count_map(length_count_map, bin_size)


def build_length_bins_from_count_map(length_count_map, bin_size):
    counts = {}
    for length, count in length_count_map.items():
        start = (int(length) // bin_size) * bin_size
        end = start + bin_size
        counts[(start, end)] = counts.get((start, end), 0) + int(count)
    rows = []
    for start, end in sorted(counts):
        rows.append(
            {
                "start": start,
                "end": end,
                "label": f"[{start}-{end})",
                "count": counts[(start, end)],
            }
        )
    return rows


def collapse_small_categories(rows, min_fraction, other_label="Others"):
    total = sum(count for _, count in rows)
    kept = []
    other_count = 0
    for label, count in rows:
        fraction = count / total if total else 0
        if fraction > min_fraction:
            kept.append({"label": label, "count": count, "fraction": fraction})
        else:
            other_count += count
    if other_count:
        kept.append(
            {
                "label": other_label,
                "count": other_count,
                "fraction": other_count / total if total else 0,
            }
        )
    return kept


def bin_ani_records(rows, start=95, end=100, step=1):
    counts = {}
    edges = list(range(start, end, step))
    for row in rows:
        try:
            ani = float(row.get("closest_genome_ani", ""))
        except (TypeError, ValueError):
            continue
        domain = row.get("domain", "") or "Unknown"
        for lower in edges:
            upper = lower + step
            is_last = upper >= end
            if (lower <= ani < upper) or (is_last and lower <= ani <= end):
                label = f"[{lower},{end}]" if is_last else f"[{lower},{upper})"
                counts[(label, domain)] = counts.get((label, domain), 0) + 1
                break
    result = []
    for label, domain in sorted(counts):
        result.append({"ani_bin": label, "domain": domain, "count": counts[(label, domain)]})
    return result


def summarize_contig_validation(rows, accuracy_min=0.5, qvalue_max=0.05):
    counts = {}
    totals = {}
    for row in rows:
        try:
            accuracy = float(row.get("predicted_accuracy", ""))
            qvalue = float(row.get("qvalue", ""))
        except (TypeError, ValueError):
            continue
        group = (
            f"Accuracy >= {accuracy_min:g}"
            if accuracy >= accuracy_min
            else f"Accuracy < {accuracy_min:g}"
        )
        sig = (
            f"q-value <= {qvalue_max:g}"
            if qvalue <= qvalue_max
            else f"q-value > {qvalue_max:g}"
        )
        counts[(group, sig)] = counts.get((group, sig), 0) + 1
        totals[group] = totals.get(group, 0) + 1

    group_order = [f"Accuracy >= {accuracy_min:g}", f"Accuracy < {accuracy_min:g}"]
    sig_order = [f"q-value <= {qvalue_max:g}", f"q-value > {qvalue_max:g}"]
    result = []
    for group in group_order:
        for sig in sig_order:
            count = counts.get((group, sig), 0)
            if count == 0:
                continue
            result.append(
                {
                    "group": group,
                    "sig": sig,
                    "count": count,
                    "proportion": count / totals[group],
                }
            )
    return result


def _normalize_row_lookup(row):
    return {
        re.sub(r"[^a-z0-9]+", "_", str(key).strip().lower()).strip("_"): value
        for key, value in row.items()
        if key is not None
    }


def classify_mag_quality(completeness, contamination):
    if completeness >= 90 and contamination <= 5:
        return "HQ"
    if completeness >= 50 and contamination <= 10:
        return "MQ"
    return "LQ"


def normalize_summary_quality(value):
    text = str(value).strip().lower()
    if text in {"hq", "high", "high-quality", "high_quality"}:
        return "HQ"
    if text in {"mq", "medium", "medium-quality", "medium_quality"}:
        return "MQ"
    if text in {"lq", "low", "low-quality", "low_quality"}:
        return "LQ"
    return ""


def summarize_gunc_css_by_quality(rows):
    result = []
    for row in rows:
        normalized = _normalize_row_lookup(row)
        quality = normalize_summary_quality(normalized.get("quality", ""))
        if quality not in {"HQ", "MQ"}:
            continue

        try:
            css = float(normalized.get("gunc_clade_separation_score", ""))
        except (TypeError, ValueError):
            continue

        bin_id = (
            normalized.get("bin_id")
            or normalized.get("binid")
            or normalized.get("name")
            or "unknown"
        )
        result.append(
            {
                "bin_id": str(bin_id).strip(),
                "quality": quality,
                "gunc_clade_separation_score": css,
            }
        )
    return result


def parse_checkm_rows(path, sample=None):
    rows, fieldnames = read_tabular_rows(path)
    if sample is not None:
        rows = filter_rows_by_sample(rows, sample)
    parsed_rows = []
    for row in rows:
        normalized = _normalize_row_lookup(row)
        bin_id = (
            normalized.get("bin_id")
            or normalized.get("binid")
            or normalized.get("name")
            or normalized.get("marker_lineage")
            or "unknown"
        )
        try:
            completeness = float(normalized.get("completeness", ""))
            contamination = float(normalized.get("contamination", ""))
        except (TypeError, ValueError):
            continue
        quality = normalize_summary_quality(normalized.get("quality", "")) or classify_mag_quality(
            completeness,
            contamination,
        )
        parsed_rows.append(
            {
                "bin_id": normalize_bin_id(bin_id),
                "completeness": completeness,
                "contamination": contamination,
                "quality": quality,
            }
        )
    return parsed_rows, fieldnames


def summarize_gunc_css_from_gunc_rows(gunc_rows, quality_rows):
    quality_by_bin = {
        normalize_bin_id(row.get("bin_id", "")): row.get("quality", "")
        for row in quality_rows
        if row.get("bin_id")
    }
    result = []
    for row in gunc_rows:
        normalized = _normalize_row_lookup(row)
        bin_id = normalize_bin_id(
            _first_non_missing(normalized, ["genome", "Bin_ID", "Name", "user_genome"])
        )
        quality = quality_by_bin.get(bin_id, "")
        if quality not in {"HQ", "MQ"}:
            continue
        try:
            css = float(
                _first_non_missing(
                    normalized,
                    [
                        "clade_separation_score",
                        "GUNC_Clade_Separation_Score",
                        "css",
                        "maxcss",
                        "max_css",
                    ],
                )
            )
        except (TypeError, ValueError):
            continue
        result.append(
            {
                "bin_id": bin_id,
                "quality": quality,
                "gunc_clade_separation_score": css,
            }
        )
    return result


def summarize_pydamage_by_sample(rows, accuracy_min, qvalue_max):
    counts = {}
    totals = {}
    for row in rows:
        sample = str(row.get("sample", "")).strip()
        if not sample:
            continue
        try:
            accuracy = float(row.get("predicted_accuracy", ""))
            qvalue = float(row.get("qvalue", ""))
        except (TypeError, ValueError):
            continue
        status = "Ancient-like" if accuracy >= accuracy_min and qvalue <= qvalue_max else "Other contigs"
        counts[(sample, status)] = counts.get((sample, status), 0) + 1
        totals[sample] = totals.get(sample, 0) + 1

    result = []
    for sample in sorted(totals):
        for status in ["Ancient-like", "Other contigs"]:
            count = counts.get((sample, status), 0)
            if count == 0:
                continue
            result.append(
                {
                    "sample": sample,
                    "status": status,
                    "count": count,
                    "proportion": count / totals[sample],
                }
            )
    return result
