from __future__ import annotations

import ast
import csv
from collections.abc import Mapping
from pathlib import Path
import xml.etree.ElementTree as ET


REQUIRED_SAMPLE_COLUMNS = ["sample_id", "input_path", "experiment", "fraction"]


def _parse_scalar(value: str) -> object:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none", "~"}:
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value[1:-1]
    return value


def _load_simple_config(config_path: Path) -> dict[str, object]:
    config: dict[str, object] = {}
    current_key: str | None = None
    current_list: list[object] | None = None

    with config_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("- "):
                if current_list is None or current_key is None:
                    raise ValueError(f"unexpected list item in config: {line}")
                current_list.append(_parse_scalar(line[2:].strip()))
                continue
            if ":" not in line:
                raise ValueError(f"invalid config entry: {line}")

            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            current_key = key
            if value:
                config[key] = _parse_scalar(value)
                current_list = None
            else:
                current_list = []
                config[key] = current_list

    return config


def _read_samples(samples_path: Path) -> list[dict[str, str]]:
    with samples_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != REQUIRED_SAMPLE_COLUMNS:
            columns = ", ".join(REQUIRED_SAMPLE_COLUMNS)
            raise ValueError(f"samples.tsv must contain columns: {columns}")

        samples = []
        for row in reader:
            normalized_row = {key: (value or "").strip() for key, value in row.items()}
            if not any(normalized_row.values()):
                continue
            samples.append(normalized_row)
    return samples


def _validate_input_path(input_path: Path) -> None:
    if not input_path.exists():
        raise ValueError(f"missing input_path: {input_path}")

    if input_path.is_dir() and input_path.name.lower().endswith(".d"):
        return

    if input_path.is_file() and input_path.suffix.lower() == ".raw":
        return

    raise ValueError(f"unsupported input type: {input_path}")


def _replace_list(parent: ET.Element, tag: str, child_tag: str, values: list[object]) -> None:
    node = parent.find(tag)
    if node is None:
        raise ValueError(f"missing XML node: {tag}")
    node.clear()
    for value in values:
        child = ET.SubElement(node, child_tag)
        child.text = "" if value == "" else _xml_text(value)


def _replace_text(root: ET.Element, xpath: str, value: object) -> None:
    node = root.find(xpath)
    if node is None:
        raise ValueError(f"missing XML node: {xpath}")
    node.text = _xml_text(value)


def _xml_text(value: object) -> str:
    if isinstance(value, bool):
        return "True" if value else "False"
    if value is None:
        return ""
    return str(value)


def _normalize_field(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip()


def _require_nonempty(value: str | None, field_name: str, sample_label: str | None = None) -> str:
    cleaned = _normalize_field(value)
    if not cleaned:
        if sample_label:
            raise ValueError(f"empty {field_name} for sample {sample_label}")
        raise ValueError(f"empty {field_name}")
    return cleaned


def _parse_int_field(
    value: str | None,
    field_name: str,
    sample_label: str,
) -> str:
    cleaned = _require_nonempty(value, field_name, sample_label)
    try:
        return str(int(cleaned))
    except ValueError as exc:
        raise ValueError(f"invalid {field_name} for sample {sample_label}: {cleaned}") from exc


def _config_value(config: Mapping[str, object], key: str, default: object | None = None) -> object | None:
    if key in config:
        return config[key]
    return default


def _config_list(config: Mapping[str, object], key: str) -> list[object]:
    value = _config_value(config, key, [])
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _resolve_config_path(value: object | None, config_base_dir: Path | None) -> object | None:
    if value in (None, ""):
        return value
    if not isinstance(value, str):
        return value
    path = Path(value)
    if path.is_absolute() or config_base_dir is None:
        return str(path)
    return str((config_base_dir / path).resolve())


def _parameter_group_nodes(root: ET.Element) -> list[ET.Element]:
    nodes = root.findall(".//parameterGroups/parameterGroup")
    if not nodes:
        raise ValueError("missing XML node: .//parameterGroups/parameterGroup")
    return nodes


def render_mqpar(
    *,
    samples_path: Path,
    config_path: Path | None,
    template_path: Path,
    mzml_dir: Path,
    output_path: Path,
    config_data: Mapping[str, object] | None = None,
    mzml_paths: Mapping[str, Path] | None = None,
    config_base_dir: Path | None = None,
) -> Path:
    if config_data is None:
        if config_path is None:
            raise ValueError("config_path is required when config_data is not provided")
        config = _load_simple_config(config_path)
        resolved_config_base_dir = config_path.parent
    else:
        config = dict(config_data)
        resolved_config_base_dir = config_base_dir

    tree = ET.parse(template_path)
    root = tree.getroot()

    samples = _read_samples(samples_path)
    file_paths = []
    experiments = []
    fractions = []
    ptms = []
    reference_channels = []
    seen_sample_ids: set[str] = set()
    resolved_mzml_paths = {} if mzml_paths is None else {sample_id: Path(path) for sample_id, path in mzml_paths.items()}

    for sample in samples:
        sample_id = _require_nonempty(sample["sample_id"], "sample_id")
        if sample_id in seen_sample_ids:
            raise ValueError(f"duplicate sample_id: {sample_id}")
        seen_sample_ids.add(sample_id)

        input_path = Path(_require_nonempty(sample.get("input_path"), "input_path", sample_id))
        _validate_input_path(input_path)

        experiment = _require_nonempty(sample["experiment"], "experiment", sample_id)
        fraction = _parse_int_field(sample.get("fraction"), "fraction", sample_id)

        mzml_path = resolved_mzml_paths.get(sample_id, mzml_dir / f"{sample_id}.mzML")
        file_paths.append(str(mzml_path))
        experiments.append(experiment)
        fractions.append(fraction)
        ptms.append(False)
        reference_channels.append("")

    parameter_group_nodes = _parameter_group_nodes(root)
    parameter_group_indices = ["0"] * len(file_paths)

    _replace_list(root, "filePaths", "string", file_paths)
    _replace_list(root, "experiments", "string", experiments)
    _replace_list(root, "fractions", "short", fractions)
    _replace_list(root, "paramGroupIndices", "int", parameter_group_indices)
    _replace_list(root, "ptms", "boolean", ptms)
    _replace_list(root, "referenceChannel", "string", reference_channels)

    maxquant_output_dir = _resolve_config_path(
        _config_value(config, "maxquant_output_dir", str(output_path.parent.parent.resolve())),
        resolved_config_base_dir,
    )
    fixed_search_folder = str(Path(maxquant_output_dir) / "search")
    fixed_combined_folder = str(Path(maxquant_output_dir) / "combined")
    temp_folder = str(Path(maxquant_output_dir) / "tmp")
    _replace_text(root, ".//fixedSearchFolder", fixed_search_folder)
    _replace_text(root, ".//fixedCombinedFolder", fixed_combined_folder)
    _replace_text(root, ".//tempFolder", temp_folder)
    _replace_text(
        root,
        ".//fastaFiles/FastaFileInfo/fastaFilePath",
        _resolve_config_path(_config_value(config, "fasta_path", ""), resolved_config_base_dir),
    )
    _replace_text(root, ".//matchBetweenRuns", _config_value(config, "match_between_runs", False))
    _replace_text(root, ".//includeContaminants", _config_value(config, "include_contaminants", True))
    _replace_text(root, ".//minPeptideLength", _config_value(config, "min_peptide_length", 7))
    _replace_text(root, ".//peptideFdr", _config_value(config, "peptide_fdr", 0.01))
    _replace_text(root, ".//proteinFdr", _config_value(config, "protein_fdr", 0.01))
    _replace_text(root, ".//siteFdr", _config_value(config, "site_fdr", 0.01))
    _replace_text(root, ".//numThreads", _config_value(config, "threads", 1))

    for parameter_group in parameter_group_nodes:
        _replace_text(parameter_group, "./enzymeMode", _config_value(config, "enzyme_mode", 4))
        _replace_list(parameter_group, "fixedModifications", "string", _config_list(config, "fixed_modifications"))
        _replace_list(parameter_group, "enzymes", "string", _config_list(config, "enzymes"))
        _replace_list(
            parameter_group,
            "variableModifications",
            "string",
            _config_list(config, "variable_modifications"),
        )
        _replace_text(parameter_group, "./firstSearchTol", _config_value(config, "first_search_tol", 20))
        _replace_text(parameter_group, "./mainSearchTol", _config_value(config, "main_search_tol", 4.5))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(tree, space="   ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    return output_path
