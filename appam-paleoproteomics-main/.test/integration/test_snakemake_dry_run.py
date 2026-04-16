import os
from pathlib import Path
from shlex import quote as shell_quote
import subprocess
import tempfile
import unittest


SNAKEFILE = Path("workflow/Snakefile")


class SnakemakeDryRunTests(unittest.TestCase):
    def _write_sample_table(self, directory: Path, rows: list[tuple[str, str, str, str]]) -> Path:
        samples_path = directory / "samples.tsv"
        header = "sample_id\tinput_path\texperiment\tfraction\n"
        lines = ["\t".join(row) for row in rows]
        samples_path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
        return samples_path

    def _write_config(self, directory: Path, sample_table: Path) -> Path:
        config_path = directory / "config.yaml"
        config_path.write_text(
            "\n".join(
                [
                    f"sample_table: {sample_table}",
                    "mqpar_template: workflow/templates/mqpar.template.xml",
                    f"results_dir: {directory / 'results'}",
                    "maxquant_output_dir: results/maxquant",
                    "threads: 4",
                    "dotnet_bin: dotnet",
                    "maxquant_cmd_dll: /path/to/MaxQuantCmd.dll",
                    "thermo_raw_file_parser: ThermoRawFileParser",
                    "timsconvert_bin: timsconvert",
                    "openms_fileconverter: FileConverter",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return config_path

    def _write_tool_override_config(self, directory: Path) -> Path:
        config_path = directory / "tool override config.yaml"
        tool_root = directory / "tool paths with spaces"
        config_path.write_text(
            "\n".join(
                [
                    "sample_table: config/samples.tsv",
                    "mqpar_template: workflow/templates/mqpar.template.xml",
                    "results_dir: results",
                    f"maxquant_output_dir: {tool_root / 'MaxQuant Output'}",
                    "threads: 4",
                    f"dotnet_bin: {tool_root / 'dot net' / 'dotnet'}",
                    f"maxquant_cmd_dll: {tool_root / 'MaxQuant Cmd' / 'MaxQuantCmd.dll'}",
                    f"thermo_raw_file_parser: {tool_root / 'Thermo RawFileParser' / 'ThermoRawFileParser'}",
                    f"timsconvert_bin: {tool_root / 'timsconvert bin' / 'timsconvert'}",
                    f"openms_fileconverter: {tool_root / 'OpenMS Tools' / 'FileConverter'}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return config_path

    def _run_snakemake(self, args: list[str], tmpdir: str) -> subprocess.CompletedProcess[str]:
        tmp_path = Path(tmpdir)
        cache_home = tmp_path / "cache"
        temp_home = tmp_path / "home"
        cache_home.mkdir()
        temp_home.mkdir()
        env = os.environ.copy()
        env["XDG_CACHE_HOME"] = str(cache_home)
        env["TMPDIR"] = str(tmp_path)
        env["HOME"] = str(temp_home)
        return subprocess.run(
            ["snakemake", "-s", str(SNAKEFILE), *args],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

    def test_dry_run_lists_final_targets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self._run_snakemake(["-n", "--cores", "1"], tmpdir)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("results/mzml/S1_RAW.mzML", result.stdout)
        self.assertIn("results/mzml/S2_D.mzML", result.stdout)
        self.assertIn("results/maxquant/combined/txt/proteinGroups.txt", result.stdout)
        self.assertIn("results/maxquant/mqpar/all_samples.mqpar.xml", result.stdout)
        self.assertIn("finalize_raw_mzml", result.stdout)
        self.assertIn("finalize_bruker_mzml", result.stdout)

    def test_dry_run_shows_raw_conversion_commands(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self._run_snakemake(["-n", "-p", "--cores", "1", "results/mzml/S1_RAW.mzML"], tmpdir)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ThermoRawFileParser", result.stdout)
        self.assertIn("-b=results/thermo/S1_RAW.mzML", result.stdout)
        self.assertNotIn("results/mzml/raw/S1_RAW/S1_RAW.mzML", result.stdout)
        self.assertNotIn("if [ ! -f", result.stdout)
        self.assertNotIn("mkdir -p", result.stdout)

    def test_dry_run_shows_d_to_conversion_commands(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self._run_snakemake(["-n", "-p", "--cores", "1", "results/mzml/S2_D.mzML"], tmpdir)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("timsconvert", result.stdout)
        self.assertIn("output: results/bruker/S2_D.mzML", result.stdout)
        self.assertIn("--outdir results/bruker/S2_D", result.stdout)
        self.assertNotIn("results/mzml/bruker/S2_D", result.stdout)
        self.assertNotIn("if [ ! -f", result.stdout)
        self.assertNotIn("mkdir -p", result.stdout)

    def test_dry_run_shows_maxquant_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self._run_snakemake(
                ["-n", "-p", "--cores", "1", "results/maxquant/combined/txt/proteinGroups.txt"],
                tmpdir,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dotnet", result.stdout)
        self.assertIn("/opt/tools/MaxQuant_v2.7.5.0/bin/MaxQuantCmd.dll", result.stdout)
        self.assertIn("all_samples.mqpar.xml", result.stdout)
        self.assertIn("proteinGroups.txt", result.stdout)
        self.assertIn("cd results/maxquant", result.stdout)
        self.assertIn("results/logs/run_maxquant.log", result.stdout)
        self.assertNotIn("./results/logs/run_maxquant.log", result.stdout)
        self.assertNotIn("if [ ! -f", result.stdout)

    def test_dry_run_quotes_tool_paths_from_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config_path = self._write_tool_override_config(tmp_path)
            result = self._run_snakemake(
                ["-n", "-p", "--cores", "1", "--configfile", str(config_path)],
                tmpdir,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            shell_quote(
                str(tmp_path / "tool paths with spaces" / "Thermo RawFileParser" / "ThermoRawFileParser")
            ),
            result.stdout,
        )
        self.assertIn(
            shell_quote(str(tmp_path / "tool paths with spaces" / "OpenMS Tools" / "FileConverter")),
            result.stdout,
        )
        self.assertIn(
            shell_quote(str(tmp_path / "tool paths with spaces" / "timsconvert bin" / "timsconvert")),
            result.stdout,
        )
        self.assertIn(
            shell_quote(str(tmp_path / "tool paths with spaces" / "dot net" / "dotnet")),
            result.stdout,
        )
        self.assertIn(
            shell_quote(str(tmp_path / "tool paths with spaces" / "MaxQuant Cmd" / "MaxQuantCmd.dll")),
            result.stdout,
        )
        self.assertIn(
            f"cd {shell_quote(str(tmp_path / 'tool paths with spaces' / 'MaxQuant Output'))}",
            result.stdout,
        )

    def test_dry_run_rejects_duplicate_sample_ids(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            first_input = tmp_path / "dup1.RAW"
            second_input = tmp_path / "dup2.RAW"
            first_input.write_text("raw1", encoding="utf-8")
            second_input.write_text("raw2", encoding="utf-8")
            sample_table = self._write_sample_table(
                tmp_path,
                [
                    ("DUP", str(first_input), "DUP", "1"),
                    ("DUP", str(second_input), "DUP", "2"),
                ],
            )
            config_path = self._write_config(tmp_path, sample_table)
            result = self._run_snakemake(
                ["-n", "--cores", "1", "--configfile", str(config_path)],
                tmpdir,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate sample_id", result.stdout + result.stderr)

    def test_dry_run_rejects_missing_fraction_column(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_path = tmp_path / "missing_fraction.RAW"
            input_path.write_text("raw", encoding="utf-8")
            sample_table = tmp_path / "samples.tsv"
            sample_table.write_text(
                "\n".join(
                    [
                        "sample_id\tinput_path\texperiment",
                        f"S1\t{input_path}\tS1",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            config_path = self._write_config(tmp_path, sample_table)
            result = self._run_snakemake(
                ["-n", "--cores", "1", "--configfile", str(config_path)],
                tmpdir,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("samples.tsv must contain columns", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
