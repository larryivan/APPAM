import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = Path(__file__).resolve().parent / "data"


def load_render_mqpar_module():
    module_path = REPO_ROOT / "workflow" / "scripts" / "render_mqpar.py"
    spec = importlib.util.spec_from_file_location("render_mqpar", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RenderMqparTests(unittest.TestCase):
    def write_samples_tsv(self, directory: Path, rows: list[tuple[str, str, str, str]]) -> Path:
        samples_path = directory / "samples.tsv"
        header = "sample_id\tinput_path\texperiment\tfraction\n"
        lines = ["\t".join(row) for row in rows]
        samples_path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
        return samples_path

    def base_config_data(self) -> dict[str, object]:
        return {
            "fasta_path": "/data/reference/proteins.fasta",
            "match_between_runs": True,
            "enzymes": ["Trypsin/P", "LysC"],
            "enzyme_mode": 4,
            "fixed_modifications": ["Carbamidomethyl (C)"],
            "variable_modifications": [
                "Oxidation (M)",
                "Acetyl (Protein N-term)",
            ],
            "peptide_fdr": 0.02,
            "protein_fdr": 0.01,
            "site_fdr": 0.005,
            "include_contaminants": False,
            "min_peptide_length": 8,
            "first_search_tol": 25,
            "main_search_tol": 4.0,
            "threads": 6,
        }

    def duplicate_parameter_group_template(self, source_template: Path, destination_template: Path) -> Path:
        root = ET.parse(source_template).getroot()
        parameter_groups = root.findall(".//parameterGroups/parameterGroup")
        self.assertGreaterEqual(len(parameter_groups), 1)
        root.find(".//parameterGroups").append(ET.fromstring(ET.tostring(parameter_groups[0])))
        ET.ElementTree(root).write(destination_template, encoding="utf-8", xml_declaration=True)
        return destination_template

    def test_render_mqpar_rewrites_run_metadata(self):
        module = load_render_mqpar_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            first_input = tmp_path / "S1_F1.RAW"
            second_input = tmp_path / "S1_F2.RAW"
            first_input.write_text("raw1", encoding="utf-8")
            second_input.write_text("raw2", encoding="utf-8")
            samples_path = self.write_samples_tsv(
                tmp_path,
                [
                    ("S1_F1", str(first_input), "S1", "1"),
                    ("S1_F2", str(second_input), "S1", "2"),
                ],
            )
            output_xml = tmp_path / "all_samples.mqpar.xml"
            module.render_mqpar(
                samples_path=samples_path,
                config_path=FIXTURE_DIR / "test_config.yaml",
                template_path=FIXTURE_DIR / "test_mqpar.template.xml",
                mzml_dir=Path("results/mzml"),
                output_path=output_xml,
            )
            text = output_xml.read_text(encoding="utf-8")
            self.assertIn("results/mzml/S1_F1.mzML", text)
            self.assertIn("results/mzml/S1_F2.mzML", text)
            self.assertIn("<string>S1</string>", text)
            self.assertIn("<short>1</short>", text)
            self.assertIn("<short>2</short>", text)
            self.assertEqual(text.count("<int>0</int>"), 2)

    def test_render_mqpar_uses_explicit_mzml_paths_when_provided(self):
        module = load_render_mqpar_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_path = tmp_path / "S1_F1.RAW"
            input_path.write_text("raw1", encoding="utf-8")
            explicit_mzml = (tmp_path / "mzml" / "S1_F1.mzML").resolve()
            explicit_mzml.parent.mkdir(parents=True, exist_ok=True)
            explicit_mzml.write_text("mzml", encoding="utf-8")
            samples_path = self.write_samples_tsv(
                tmp_path,
                [("S1_F1", str(input_path), "S1", "1")],
            )
            output_xml = tmp_path / "all_samples.mqpar.xml"

            module.render_mqpar(
                samples_path=samples_path,
                config_path=FIXTURE_DIR / "test_config.yaml",
                template_path=FIXTURE_DIR / "test_mqpar.template.xml",
                mzml_dir=Path("results/mzml"),
                output_path=output_xml,
                mzml_paths={"S1_F1": explicit_mzml},
            )

            root = ET.parse(output_xml).getroot()
            self.assertEqual(root.findtext(".//filePaths/string"), str(explicit_mzml))

    def test_render_mqpar_accepts_config_data_without_config_path(self):
        module = load_render_mqpar_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_path = tmp_path / "S1_F1.RAW"
            input_path.write_text("raw1", encoding="utf-8")
            samples_path = self.write_samples_tsv(
                tmp_path,
                [("S1_F1", str(input_path), "S1", "1")],
            )
            output_xml = tmp_path / "all_samples.mqpar.xml"

            module.render_mqpar(
                samples_path=samples_path,
                config_path=None,
                template_path=FIXTURE_DIR / "test_mqpar.template.xml",
                mzml_dir=Path("results/mzml"),
                output_path=output_xml,
                config_data=self.base_config_data(),
            )

            self.assertTrue(output_xml.exists())

    def test_render_mqpar_resolves_relative_fasta_path_against_config_base_dir(self):
        module = load_render_mqpar_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_path = tmp_path / "S1_F1.RAW"
            input_path.write_text("raw1", encoding="utf-8")
            fasta_path = tmp_path / "db" / "proteins.fasta"
            fasta_path.parent.mkdir(parents=True, exist_ok=True)
            fasta_path.write_text(">sp|P1|TEST\nPEPTIDE\n", encoding="utf-8")
            samples_path = self.write_samples_tsv(
                tmp_path,
                [("S1_F1", str(input_path), "S1", "1")],
            )
            output_xml = tmp_path / "all_samples.mqpar.xml"

            config_data = self.base_config_data()
            config_data["fasta_path"] = "db/proteins.fasta"

            module.render_mqpar(
                samples_path=samples_path,
                config_path=None,
                template_path=FIXTURE_DIR / "test_mqpar.template.xml",
                mzml_dir=Path("results/mzml"),
                output_path=output_xml,
                config_data=config_data,
                config_base_dir=tmp_path,
            )

            root = ET.parse(output_xml).getroot()
            self.assertEqual(root.findtext(".//fastaFiles/FastaFileInfo/fastaFilePath"), str(fasta_path.resolve()))

    def test_render_mqpar_sets_maxquant_folder_paths_from_output_directory(self):
        module = load_render_mqpar_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_path = tmp_path / "S1_F1.RAW"
            input_path.write_text("raw1", encoding="utf-8")
            samples_path = self.write_samples_tsv(
                tmp_path,
                [("S1_F1", str(input_path), "S1", "1")],
            )
            output_xml = tmp_path / "results" / "maxquant" / "mqpar" / "all_samples.mqpar.xml"

            module.render_mqpar(
                samples_path=samples_path,
                config_path=FIXTURE_DIR / "test_config.yaml",
                template_path=FIXTURE_DIR / "test_mqpar.template.xml",
                mzml_dir=Path("results/mzml"),
                output_path=output_xml,
            )

            root = ET.parse(output_xml).getroot()
            self.assertEqual(
                root.findtext(".//fixedSearchFolder"),
                str((tmp_path / "results" / "maxquant" / "search").resolve()),
            )
            self.assertEqual(
                root.findtext(".//fixedCombinedFolder"),
                str((tmp_path / "results" / "maxquant" / "combined").resolve()),
            )
            self.assertEqual(
                root.findtext(".//tempFolder"),
                str((tmp_path / "results" / "maxquant" / "tmp").resolve()),
            )

    def test_render_mqpar_preserves_scalar_types_from_template(self):
        module = load_render_mqpar_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_path = tmp_path / "S1_F1.RAW"
            input_path.write_text("raw1", encoding="utf-8")
            samples_path = self.write_samples_tsv(
                tmp_path,
                [("S1_F1", str(input_path), "S1", "1")],
            )
            output_xml = tmp_path / "all_samples.mqpar.xml"

            module.render_mqpar(
                samples_path=samples_path,
                config_path=FIXTURE_DIR / "test_config.yaml",
                template_path=REPO_ROOT / "workflow" / "templates" / "mqpar.template.xml",
                mzml_dir=Path("results/mzml"),
                output_path=output_xml,
            )

            root = ET.parse(output_xml).getroot()
            self.assertEqual(root.findtext(".//lfqMode"), "0")
            self.assertEqual(root.findtext(".//razorProteinFdr"), "True")

    def test_render_mqpar_writes_all_parameter_group_indices_as_zero(self):
        module = load_render_mqpar_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            first_input = tmp_path / "S2_F1.RAW"
            second_input = tmp_path / "S2_F2.RAW"
            first_input.write_text("raw1", encoding="utf-8")
            second_input.write_text("raw2", encoding="utf-8")
            samples_path = self.write_samples_tsv(
                tmp_path,
                [
                    ("S2_F1", str(first_input), "S2", "1"),
                    ("S2_F2", str(second_input), "S2", "2"),
                ],
            )
            output_xml = tmp_path / "all_samples.mqpar.xml"

            module.render_mqpar(
                samples_path=samples_path,
                config_path=FIXTURE_DIR / "test_config.yaml",
                template_path=FIXTURE_DIR / "test_mqpar.template.xml",
                mzml_dir=Path("results/mzml"),
                output_path=output_xml,
            )

            root = ET.parse(output_xml).getroot()
            self.assertEqual([node.text for node in root.findall(".//paramGroupIndices/int")], ["0", "0"])

    def test_render_mqpar_rejects_missing_fraction(self):
        module = load_render_mqpar_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_path = tmp_path / "S2_MISSING.RAW"
            input_path.write_text("raw", encoding="utf-8")
            samples_path = tmp_path / "samples.tsv"
            samples_path.write_text(
                "\n".join(
                    [
                        "sample_id\tinput_path\texperiment\tfraction",
                        f"S2_MISSING\t{input_path}\tS2_MISSING",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "empty fraction for sample S2_MISSING"):
                module.render_mqpar(
                    samples_path=samples_path,
                    config_path=FIXTURE_DIR / "test_config.yaml",
                    template_path=FIXTURE_DIR / "test_mqpar.template.xml",
                    mzml_dir=Path("results/mzml"),
                    output_path=tmp_path / "all_samples.mqpar.xml",
                )

    def test_render_mqpar_rejects_missing_required_column(self):
        module = load_render_mqpar_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_path = tmp_path / "S2_HEADER.RAW"
            input_path.write_text("raw", encoding="utf-8")
            samples_path = tmp_path / "samples.tsv"
            samples_path.write_text(
                "\n".join(
                    [
                        "sample_id\tinput_path\texperiment",
                        f"S2_HEADER\t{input_path}\tS2_HEADER",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "samples.tsv must contain columns"):
                module.render_mqpar(
                    samples_path=samples_path,
                    config_path=FIXTURE_DIR / "test_config.yaml",
                    template_path=FIXTURE_DIR / "test_mqpar.template.xml",
                    mzml_dir=Path("results/mzml"),
                    output_path=tmp_path / "all_samples.mqpar.xml",
                )

    def test_render_mqpar_rejects_duplicate_sample_ids(self):
        module = load_render_mqpar_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            first_input = tmp_path / "dup1.RAW"
            second_input = tmp_path / "dup2.RAW"
            first_input.write_text("raw1", encoding="utf-8")
            second_input.write_text("raw2", encoding="utf-8")
            samples_path = self.write_samples_tsv(
                tmp_path,
                [
                    ("DUP", str(first_input), "S1", "1"),
                    ("DUP", str(second_input), "S1", "2"),
                ],
            )

            with self.assertRaisesRegex(ValueError, "duplicate sample_id"):
                module.render_mqpar(
                    samples_path=samples_path,
                    config_path=FIXTURE_DIR / "test_config.yaml",
                    template_path=FIXTURE_DIR / "test_mqpar.template.xml",
                    mzml_dir=Path("results/mzml"),
                    output_path=tmp_path / "all_samples.mqpar.xml",
                )

    def test_render_mqpar_rejects_empty_sample_id(self):
        module = load_render_mqpar_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_path = tmp_path / "S5.RAW"
            input_path.write_text("raw5", encoding="utf-8")
            samples_path = self.write_samples_tsv(
                tmp_path,
                [("", str(input_path), "S5", "1")],
            )

            with self.assertRaisesRegex(ValueError, "empty sample_id"):
                module.render_mqpar(
                    samples_path=samples_path,
                    config_path=FIXTURE_DIR / "test_config.yaml",
                    template_path=FIXTURE_DIR / "test_mqpar.template.xml",
                    mzml_dir=Path("results/mzml"),
                    output_path=tmp_path / "all_samples.mqpar.xml",
                )

    def test_render_mqpar_rejects_empty_experiment(self):
        module = load_render_mqpar_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_path = tmp_path / "S6.RAW"
            input_path.write_text("raw6", encoding="utf-8")
            samples_path = self.write_samples_tsv(
                tmp_path,
                [("S6", str(input_path), "", "1")],
            )

            with self.assertRaisesRegex(ValueError, "empty experiment for sample S6"):
                module.render_mqpar(
                    samples_path=samples_path,
                    config_path=FIXTURE_DIR / "test_config.yaml",
                    template_path=FIXTURE_DIR / "test_mqpar.template.xml",
                    mzml_dir=Path("results/mzml"),
                    output_path=tmp_path / "all_samples.mqpar.xml",
                )

    def test_render_mqpar_rejects_invalid_fraction(self):
        module = load_render_mqpar_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_path = tmp_path / "S7.RAW"
            input_path.write_text("raw7", encoding="utf-8")
            samples_path = self.write_samples_tsv(
                tmp_path,
                [("S7", str(input_path), "S7", "abc")],
            )

            with self.assertRaisesRegex(ValueError, "invalid fraction for sample S7"):
                module.render_mqpar(
                    samples_path=samples_path,
                    config_path=FIXTURE_DIR / "test_config.yaml",
                    template_path=FIXTURE_DIR / "test_mqpar.template.xml",
                    mzml_dir=Path("results/mzml"),
                    output_path=tmp_path / "all_samples.mqpar.xml",
                )

    def test_render_mqpar_rejects_missing_input_path(self):
        module = load_render_mqpar_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            samples_path = self.write_samples_tsv(
                tmp_path,
                [("S3", str(tmp_path / "missing.RAW"), "S3", "1")],
            )

            with self.assertRaisesRegex(ValueError, "missing input_path"):
                module.render_mqpar(
                    samples_path=samples_path,
                    config_path=FIXTURE_DIR / "test_config.yaml",
                    template_path=FIXTURE_DIR / "test_mqpar.template.xml",
                    mzml_dir=Path("results/mzml"),
                    output_path=tmp_path / "all_samples.mqpar.xml",
                )

    def test_render_mqpar_rejects_unsupported_input_type(self):
        module = load_render_mqpar_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_path = tmp_path / "bad.txt"
            input_path.write_text("bad", encoding="utf-8")
            samples_path = self.write_samples_tsv(
                tmp_path,
                [("S4", str(input_path), "S4", "1")],
            )

            with self.assertRaisesRegex(ValueError, "unsupported input type"):
                module.render_mqpar(
                    samples_path=samples_path,
                    config_path=FIXTURE_DIR / "test_config.yaml",
                    template_path=FIXTURE_DIR / "test_mqpar.template.xml",
                    mzml_dir=Path("results/mzml"),
                    output_path=tmp_path / "all_samples.mqpar.xml",
                )

    def test_render_mqpar_overrides_key_configuration_and_arrays(self):
        module = load_render_mqpar_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            first_input = tmp_path / "S9_F1.RAW"
            second_input = tmp_path / "S9_F2.RAW"
            first_input.write_text("raw9a", encoding="utf-8")
            second_input.write_text("raw9b", encoding="utf-8")
            samples_path = self.write_samples_tsv(
                tmp_path,
                [
                    ("S9_F1", str(first_input), "S9", "1"),
                    ("S9_F2", str(second_input), "S9", "2"),
                ],
            )
            output_xml = tmp_path / "all_samples.mqpar.xml"

            module.render_mqpar(
                samples_path=samples_path,
                config_path=FIXTURE_DIR / "test_config.yaml",
                config_data=self.base_config_data(),
                template_path=FIXTURE_DIR / "test_mqpar.template.xml",
                mzml_dir=Path("results/mzml"),
                output_path=output_xml,
            )

            root = ET.parse(output_xml).getroot()
            self.assertEqual(root.findtext(".//fastaFiles/FastaFileInfo/fastaFilePath"), "/data/reference/proteins.fasta")
            self.assertEqual(root.findtext(".//matchBetweenRuns"), "True")
            self.assertEqual(root.findtext(".//parameterGroups/parameterGroup/enzymeMode"), "4")
            self.assertEqual(
                [element.text for element in root.findall(".//parameterGroups/parameterGroup/enzymes/string")],
                ["Trypsin/P", "LysC"],
            )
            self.assertEqual(
                [element.text for element in root.findall(".//parameterGroups/parameterGroup/fixedModifications/string")],
                ["Carbamidomethyl (C)"],
            )
            self.assertEqual(
                [element.text for element in root.findall(".//parameterGroups/parameterGroup/variableModifications/string")],
                [
                    "Oxidation (M)",
                    "Acetyl (Protein N-term)",
                ],
            )
            self.assertEqual(root.findtext(".//peptideFdr"), "0.02")
            self.assertEqual(root.findtext(".//proteinFdr"), "0.01")
            self.assertEqual(root.findtext(".//siteFdr"), "0.005")
            self.assertEqual(root.findtext(".//includeContaminants"), "False")
            self.assertEqual(root.findtext(".//minPeptideLength"), "8")
            self.assertEqual(root.findtext(".//parameterGroups/parameterGroup/firstSearchTol"), "25")
            self.assertEqual(root.findtext(".//parameterGroups/parameterGroup/mainSearchTol"), "4.0")
            self.assertEqual(root.findtext(".//numThreads"), "6")
            self.assertEqual(len(root.findall(".//ptms/boolean")), 2)
            self.assertEqual([element.text for element in root.findall(".//ptms/boolean")], ["False", "False"])
            self.assertEqual(len(root.findall(".//referenceChannel/string")), 2)
            self.assertEqual([element.text or "" for element in root.findall(".//referenceChannel/string")], ["", ""])

    def test_render_mqpar_updates_all_parameter_groups(self):
        module = load_render_mqpar_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            first_input = tmp_path / "S10_F1.RAW"
            second_input = tmp_path / "S10_F2.RAW"
            first_input.write_text("raw10a", encoding="utf-8")
            second_input.write_text("raw10b", encoding="utf-8")
            samples_path = self.write_samples_tsv(
                tmp_path,
                [
                    ("S10_F1", str(first_input), "S10", "1"),
                    ("S10_F2", str(second_input), "S10", "2"),
                ],
            )
            template_path = self.duplicate_parameter_group_template(
                FIXTURE_DIR / "test_mqpar.template.xml",
                tmp_path / "two_groups.template.xml",
            )
            output_xml = tmp_path / "all_samples.mqpar.xml"

            module.render_mqpar(
                samples_path=samples_path,
                config_path=FIXTURE_DIR / "test_config.yaml",
                config_data=self.base_config_data(),
                template_path=template_path,
                mzml_dir=Path("results/mzml"),
                output_path=output_xml,
            )

            root = ET.parse(output_xml).getroot()
            groups = root.findall(".//parameterGroups/parameterGroup")
            self.assertEqual(len(groups), 2)
            for group in groups:
                self.assertEqual(group.findtext("./enzymeMode"), "4")
                self.assertEqual(
                    [element.text for element in group.findall("./enzymes/string")],
                    ["Trypsin/P", "LysC"],
                )
                self.assertEqual(
                    [element.text for element in group.findall("./fixedModifications/string")],
                    ["Carbamidomethyl (C)"],
                )
                self.assertEqual(
                    [element.text for element in group.findall("./variableModifications/string")],
                    [
                        "Oxidation (M)",
                        "Acetyl (Protein N-term)",
                    ],
                )
                self.assertEqual(group.findtext("./firstSearchTol"), "25")
                self.assertEqual(group.findtext("./mainSearchTol"), "4.0")

if __name__ == "__main__":
    unittest.main()
