import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[2] / "docker" / "patch_pytdfsdk.py"
SPEC = importlib.util.spec_from_file_location("patch_pytdfsdk", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class PatchPyTDFSDKTests(unittest.TestCase):
    def test_patch_is_idempotent(self):
        source = f"before\n{MODULE.OLD_BLOCK}after\n"
        patched, changed = MODULE.patch_source(source)
        self.assertTrue(changed)
        self.assertIn("if scan_begin != 0:", patched)

        unchanged, changed_again = MODULE.patch_source(patched)
        self.assertFalse(changed_again)
        self.assertEqual(unchanged, patched)

    def test_patch_rejects_an_unknown_upstream_layout(self):
        with self.assertRaisesRegex(RuntimeError, "expected pyTDFSDK raw scan block"):
            MODULE.patch_source("unexpected source")


if __name__ == "__main__":
    unittest.main()
