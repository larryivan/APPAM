import importlib.util
from pathlib import Path


def _load_render_mqpar_module():
    module_path = Path(__file__).resolve().with_name("render_mqpar.py")
    spec = importlib.util.spec_from_file_location("render_mqpar_module", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MZML_INPUTS = [Path(path) for path in snakemake.input.mzmls]
MZML_DIR = MZML_INPUTS[0].parent
MZML_PATHS = {path.stem: path.resolve() for path in MZML_INPUTS}

render_mqpar_module = _load_render_mqpar_module()
render_mqpar_module.render_mqpar(
    samples_path=Path(snakemake.input.samples),
    config_path=None,
    template_path=Path(snakemake.input.template),
    mzml_dir=MZML_DIR,
    output_path=Path(snakemake.output.mqpar),
    config_data=snakemake.config,
    mzml_paths=MZML_PATHS,
    config_base_dir=Path.cwd(),
)

Path(snakemake.log[0]).write_text(f"Rendered {snakemake.output.mqpar}\n", encoding="utf-8")
