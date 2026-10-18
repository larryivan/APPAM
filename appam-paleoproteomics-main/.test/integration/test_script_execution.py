"""Execute the workflow's `script:` rules through real Snakemake.

Dry runs never execute scripts, and the unit tests import the QC modules
directly, which skips the preamble Snakemake injects into every `script:`
file. A `from __future__` import in a script therefore passed every check
while failing the QC stage of every real run. This test runs those rules for
real on synthetic MaxQuant output; conversion and the MaxQuant search itself
are excluded because they need licensed vendor software.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


SNAKEFILE = Path("workflow/Snakefile")
RULES_DIR = Path("workflow/rules")


class ScriptDirectiveTests(unittest.TestCase):
    def test_script_directives_have_no_future_imports(self):
        offenders = []
        for rule_file in sorted(RULES_DIR.glob("*.smk")):
            for script in re.findall(r'script:\s*\n?\s*"([^"]+)"', rule_file.read_text(encoding="utf-8")):
                path = (RULES_DIR / script).resolve()
                if re.search(r"^\s*from __future__ import", path.read_text(encoding="utf-8"), re.M):
                    offenders.append(f"{rule_file.name} -> {path.name}")
        self.assertEqual(offenders, [], "script: files must not use __future__ imports")


@unittest.skipUnless(shutil.which("snakemake"), "snakemake is not installed")
class ScriptExecutionTests(unittest.TestCase):
    def test_mqpar_rendering_and_qc_rules_execute(self):
        with tempfile.TemporaryDirectory(prefix="paleo-script-exec-") as tmpdir:
            root = Path(tmpdir)
            results = root / "results"
            maxquant = root / "maxquant"

            raw = root / "raw" / "S1.RAW"
            raw.parent.mkdir()
            raw.write_bytes(b"thermo raw placeholder")
            fasta = root / "reference.fasta"
            fasta.write_text(">sp|P02452|CO1A1_HUMAN Collagen alpha-1(I) chain\nMFSFVDLRLLLLLAATALLTHG\n")
            samples = root / "samples.tsv"
            samples.write_text(f"sample_id\tinput_path\texperiment\tfraction\nS1\t{raw}\tbone\t1\n")

            # Outputs of the stages this test does not run (conversion, MaxQuant).
            mzml = results / "mzml" / "S1.mzML"
            mzml.parent.mkdir(parents=True)
            mzml.write_text("<mzML/>\n")
            txt = maxquant / "batch" / "combined" / "txt"
            txt.mkdir(parents=True)
            (txt / "proteinGroups.txt").write_text(
                "Protein IDs\tPotential contaminant\tReverse\n"
                "P02452\t\t\nCON__P00761\t+\t\nREV__P02452\t\t+\n"
            )
            (txt / "peptides.txt").write_text(
                "Sequence\tPotential contaminant\tReverse\nGPPGPQGAR\t\t\nGEAGPQGPR\t\t\n"
            )
            # MaxQuant always fills `Modifications` with the full name.
            (txt / "evidence.txt").write_text(
                "Sequence\tModifications\tModified sequence\tRaw file\n"
                "GPPGPQGAR\tDeamidation (NQ)\t_GPPGPQ(Deamidation (NQ))GAR_\tS1\n"
                "GEAGPQGPR\tUnmodified\t_GEAGPQGPR_\tS1\n"
            )

            config = root / "config.yaml"
            config.write_text(
                "\n".join([
                    f"sample_table: {samples}",
                    "mqpar_template: workflow/templates/mqpar.template.xml",
                    f"results_dir: {results}",
                    f"maxquant_output_dir: {maxquant}",
                    "maxquant_mode: batch",
                    "threads: 1",
                    f"fasta_path: {fasta}",
                    f"runtime_env: {Path('docker/environment.yml').resolve()}",
                    "dotnet_bin: dotnet",
                    "maxquant_cmd_dll: /path/to/MaxQuantCmd.dll",
                    "thermo_raw_file_parser: ThermoRawFileParser",
                    "timsconvert_bin: timsconvert",
                    "openms_fileconverter: FileConverter",
                ]) + "\n"
            )

            env = os.environ.copy()
            env.update({"HOME": str(root), "XDG_CACHE_HOME": str(root / "cache"), "TMPDIR": str(root)})
            qc_report = results / "reports" / "paleoproteomics-qc.json"
            mqpar = maxquant / "batch" / "mqpar.xml"

            def snakemake(target, rules):
                return subprocess.run(
                    [
                        shutil.which("snakemake"), str(target),
                        "--snakefile", str(SNAKEFILE),
                        "--configfile", str(config),
                        "--cores", "1", "--latency-wait", "1",
                        "--allowed-rules", *rules,
                    ],
                    env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False,
                )

            # Same order as a real run: render the parameter file, MaxQuant then
            # writes its tables (simulated by refreshing their timestamps), then QC.
            rendered_run = snakemake(mqpar, ["render_mqpar_batch"])
            self.assertEqual(rendered_run.returncode, 0, rendered_run.stdout[-4000:])
            for table in txt.iterdir():
                table.touch()
            qc_run = snakemake(qc_report, ["paleoproteomics_qc_batch", "paleoproteomics_qc_report"])
            self.assertEqual(qc_run.returncode, 0, qc_run.stdout[-4000:])

            rendered = mqpar.read_text(encoding="utf-8")
            self.assertIn(str(mzml.resolve()), rendered)
            self.assertIn(str(fasta), rendered)

            report = json.loads(qc_report.read_text(encoding="utf-8"))
            self.assertEqual(report["maxquant_mode"], "batch")
            self.assertEqual(report["analysis_ids"], ["batch"])
            self.assertEqual(report["counts"]["protein_groups"], 3)
            self.assertEqual(report["counts"]["protein_contaminants"], 1)
            self.assertEqual(report["counts"]["protein_reverse"], 1)
            self.assertEqual(report["counts"]["deamidated_evidence"], 1)
            self.assertEqual(report["evidence_by_raw_file"], {"S1": 2})


if __name__ == "__main__":
    unittest.main()
