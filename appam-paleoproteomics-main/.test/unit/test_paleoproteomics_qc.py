import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_qc_module():
    module_path = REPO_ROOT / 'workflow' / 'scripts' / 'paleoproteomics_qc.py'
    spec = importlib.util.spec_from_file_location('paleoproteomics_qc', module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PaleoproteomicsQcTests(unittest.TestCase):
    def test_qc_counts_contaminants_reverse_and_deamidation(self):
        module = load_qc_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            proteins = root / 'proteinGroups.txt'
            peptides = root / 'peptides.txt'
            evidence = root / 'evidence.txt'
            proteins.write_text(
                'Protein IDs\tPotential contaminant\tReverse\nP1\t\t\nCON__P2\t+\t\nREV__P3\t\t+\n',
                encoding='utf-8',
            )
            peptides.write_text(
                'Sequence\tPotential contaminant\tReverse\nPEPTIDE\t\t\nBAD\t+\t+\n',
                encoding='utf-8',
            )
            evidence.write_text(
                'Sequence\tModifications\tModified sequence\tRaw file\nAAA\tDeamidation (NQ)\t_AA(de)A_\tS1\nBBB\tUnmodified\t_BBB_\tS1\n',
                encoding='utf-8',
            )

            payload = module.build_qc(proteins, peptides, evidence)
            self.assertEqual(payload['counts']['protein_groups'], 3)
            self.assertEqual(payload['counts']['protein_contaminants'], 1)
            self.assertEqual(payload['counts']['protein_reverse'], 1)
            self.assertEqual(payload['counts']['deamidated_evidence'], 1)
            self.assertEqual(payload['rates']['deamidated_evidence_fraction'], 0.5)
            self.assertEqual(payload['evidence_by_raw_file'], {'S1': 2})
            self.assertIn('not, by itself', payload['interpretation_note'])
            self.assertIn('APPAM paleoproteomics QC', module.render_html(payload))


if __name__ == '__main__':
    unittest.main()
