import importlib.util
from pathlib import Path
import unittest


def load_module():
    path = Path("workflow/scripts/merge_paleoproteomics_qc.py")
    spec = importlib.util.spec_from_file_location("merge_paleoproteomics_qc", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MergePaleoproteomicsQcTests(unittest.TestCase):
    def test_merge_payloads_recomputes_rates_from_aggregate_counts(self):
        module = load_module()
        payload = module.merge_payloads(
            [
                {
                    "analysis_id": "S1",
                    "counts": {
                        "protein_groups": 10,
                        "peptides": 20,
                        "evidence_rows": 30,
                        "protein_contaminants": 1,
                        "protein_reverse": 1,
                        "peptide_contaminants": 2,
                        "peptide_reverse": 0,
                        "deamidated_evidence": 3,
                    },
                    "evidence_by_raw_file": {"S1": 30},
                },
                {
                    "analysis_id": "S2",
                    "counts": {
                        "protein_groups": 30,
                        "peptides": 60,
                        "evidence_rows": 70,
                        "protein_contaminants": 3,
                        "protein_reverse": 1,
                        "peptide_contaminants": 4,
                        "peptide_reverse": 2,
                        "deamidated_evidence": 7,
                    },
                    "evidence_by_raw_file": {"S2": 70},
                },
            ],
            "per_sample_id",
        )

        self.assertEqual(payload["analysis_ids"], ["S1", "S2"])
        self.assertEqual(payload["counts"]["protein_groups"], 40)
        self.assertEqual(payload["counts"]["evidence_rows"], 100)
        self.assertEqual(payload["rates"]["protein_contaminant_fraction"], 0.1)
        self.assertEqual(payload["rates"]["deamidated_evidence_fraction"], 0.1)
        self.assertEqual(payload["evidence_by_raw_file"], {"S1": 30, "S2": 70})


if __name__ == "__main__":
    unittest.main()
