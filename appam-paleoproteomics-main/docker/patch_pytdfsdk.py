from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path


OLD_BLOCK = """        list_of_scans = tims_read_scans_v2(tdf_data.api, tdf_data.handle, frame, scan_begin, scan_end)
        frame_mz_arrays = []
        frame_intensity_arrays = []
        for scan_num in range(scan_begin, scan_end):
"""

NEW_BLOCK = """        list_of_scans = tims_read_scans_v2(tdf_data.api, tdf_data.handle, frame, scan_begin, scan_end)
        frame_mz_arrays = []
        frame_intensity_arrays = []
        if scan_begin != 0:
            scan_end = scan_end - scan_begin
            scan_begin = 0
        for scan_num in range(scan_begin, scan_end):
"""


def patch_source(source: str) -> tuple[str, bool]:
    if NEW_BLOCK in source:
        return source, False
    if OLD_BLOCK not in source:
        raise RuntimeError("Could not find the expected pyTDFSDK raw scan block")
    return source.replace(OLD_BLOCK, NEW_BLOCK, 1), True


def main() -> None:
    module_spec = find_spec("pyTDFSDK.tims")
    if module_spec is None or module_spec.origin is None:
        raise RuntimeError("Could not locate pyTDFSDK.tims")

    module_path = Path(module_spec.origin)
    patched, changed = patch_source(module_path.read_text(encoding="utf-8"))
    if changed:
        module_path.write_text(patched, encoding="utf-8")
        print(f"Patched {module_path}")
    else:
        print(f"Already patched: {module_path}")


if __name__ == "__main__":
    main()
