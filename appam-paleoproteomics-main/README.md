# appam-paleoproteomics

Snakemake workflow for converting Thermo `.RAW` files and Bruker `.d` folders to mzML, then running MaxQuant on the full batch.

## Inputs

`config/samples.tsv` is the sample manifest. Required columns:

```tsv
sample_id	input_path	experiment	fraction
```

`sample_id` must be unique. `experiment` groups related files. `fraction` is required and must be an integer.

The checked-in sample table points to fixture inputs under `.test/data/example_inputs` so repository-level dry-runs work without editing paths first.

`config/README.md` documents the required sample table schema, the `config.yaml` keys, and how the tracked `workflow/templates/mqpar.template.xml` is turned into the runtime `results/maxquant/mqpar/all_samples.mqpar.xml`.

## Configuration

Use `config/config.yaml` for workflow and MaxQuant settings. The important keys are:

- `sample_table`
- `mqpar_template`
- `results_dir`
- `maxquant_output_dir`
- `threads`
- `fasta_path`
- `match_between_runs`
- `enzymes`
- `enzyme_mode`
- `fixed_modifications`
- `variable_modifications`
- `peptide_fdr`
- `protein_fdr`
- `site_fdr`
- `include_contaminants`
- `min_peptide_length`
- `first_search_tol`
- `main_search_tol`
- `dotnet_bin`
- `maxquant_cmd_dll`
- `thermo_raw_file_parser`
- `timsconvert_bin`
- `openms_fileconverter`

The default paths are:

- `sample_table: config/samples.tsv`
- `mqpar_template: workflow/templates/mqpar.template.xml`
- `dotnet_bin: dotnet`
- `maxquant_cmd_dll: /opt/tools/MaxQuant_v2.7.5.0/bin/MaxQuantCmd.dll`
- `thermo_raw_file_parser: ThermoRawFileParser`
- `timsconvert_bin: timsconvert`
- `openms_fileconverter: FileConverter`

For machine-specific overrides, keep a local file such as `config/config.local.yaml` and run Snakemake with `--configfile config/config.local.yaml`. Files matching `*.local.yaml` are ignored by Git, so local paths and private settings will not be committed.

The workflow passes Snakemake's loaded `config` object into the mqpar renderer, so no separate YAML parser dependency is required. Run all commands from the repository root.

## Run

Dry-run the workflow:

```bash
snakemake -n --cores 1
```

Snakemake will automatically discover `workflow/Snakefile` from the repository root.

Show the rendered shell commands:

```bash
snakemake -n -p --cores 1 results/maxquant/combined/txt/proteinGroups.txt
```

Run the full pipeline:

```bash
snakemake --cores 1
```

Run with a local override config:

```bash
snakemake --configfile config/config.local.yaml --cores 4
```

## Docker

The repository tracks the Docker build assets under:

- `docker/Dockerfile`
- `docker/environment.yml`
- `docker/requirements-pypi.txt`
- `docker/entrypoint.sh`

When preparing the actual image build context, place `Dockerfile`, `environment.yml`, `requirements-pypi.txt`, and `entrypoint.sh` at the root of the Docker packaging directory rather than under a nested `docker/` subdirectory.

Published image:

- `xreal1ty/appam-paleoproteomics`
- <https://hub.docker.com/repository/docker/xreal1ty/appam-paleoproteomics/>

The current published version is `xreal1ty/appam-paleoproteomics:v0.1.3`.

Pull the published image:

```bash
docker pull xreal1ty/appam-paleoproteomics:latest
```

The Docker image contains the runtime dependencies for APPAM paleoproteomics, while the Snakemake workflow is mounted at runtime rather than baked into the image. This allows independent workflow updates without rebuilding the container.

The recommended deployment is to run `snakemake` inside a Docker image that already includes:

- `snakemake`
- `ThermoRawFileParser`
- `timsconvert`
- `FileConverter`
- `dotnet`
- `entrypoint.sh`

`entrypoint.sh` should activate the `paleoproteomics` conda environment and export these runtime paths:

- `/opt/tools/ThermoRawFileParser`
- `/opt/tools/MaxQuant_v2.7.5.0`
- `/opt/tools/openms-development/bin`
- `/opt/tools/openms-development/lib`

With that entrypoint, the defaults in `config/config.yaml` match the container directly. Only `maxquant_cmd_dll` stays absolute because Snakemake passes it to `dotnet` as a DLL path:

- `/opt/tools/MaxQuant_v2.7.5.0/bin/MaxQuantCmd.dll`

The Docker build context should also provide vendor tool directories under `tools/`. Those binaries are not stored in this repository.

Example:

```bash
docker run --rm -it \
  -v "$PWD":/workspace \
  -v /path/to/raw_data:/data \
  -w /workspace \
  xreal1ty/appam-paleoproteomics:latest \
  snakemake --cores 4
```

Run with a local override config:

```bash
docker run --rm -it \
  -v "$PWD":/workspace \
  -v /path/to/raw_data:/data \
  -w /workspace \
  xreal1ty/appam-paleoproteomics:latest \
  snakemake --configfile config/config.local.yaml --cores 4
```

Dry-run:

```bash
docker run --rm -it \
  -v "$PWD":/workspace \
  -v /path/to/raw_data:/data \
  -w /workspace \
  xreal1ty/appam-paleoproteomics:latest \
  snakemake -n --cores 1
```

Open a shell in the prepared runtime:

```bash
docker run --rm -it \
  -v "$PWD":/workspace \
  -v /path/to/raw_data:/data \
  -w /workspace \
  xreal1ty/appam-paleoproteomics:latest \
  bash
```

Mount convention:

- Mount the workflow repository to `/workspace`
- Mount raw vendor files to `/data`
- Write `config/samples.tsv` with container-visible paths such as `/data/project/S1_F1.RAW` or `/data/project/S2.d`

Input and output handling:

- Input raw data stay in the mounted `/data` directory and are read in place
- Workflow code, `config/`, and templates are read from `/workspace`
- Thermo intermediate mzML files are written under `/workspace/results/thermo`
- Bruker intermediate mzML files are written under `/workspace/results/bruker`
- Converted mzML files are written under `/workspace/results/mzml`
- Rendered MaxQuant parameters are written under `/workspace/results/maxquant/mqpar`
- MaxQuant output tables are written under `/workspace/results/maxquant`

This means users normally only need to back up two things:

- the repository directory mounted at `/workspace`
- the raw data directory mounted at `/data`

This repository no longer expects Snakemake to launch another container from inside the workflow. The image is the execution environment; the workflow runs directly inside it, while the workflow code remains mounted from the host repository.

## Run Without Docker

You can also run the workflow directly on the host, but then you need to install the runtime yourself.

Required external software:

- `ThermoRawFileParser`
- `timsconvert`
- `OpenMS` with `FileConverter`
- `MaxQuant`
- `dotnet`

For host installs, `timsconvert` is recommended to be installed via `conda`, consistent with the Docker environment definition. For example:

```bash
conda install -c bioconda -c conda-forge timsconvert
```

Recommended `conda` environment:

- `snakemake`
- Python runtime used by Snakemake
- any Python packages you want for local testing

When running without Docker, make sure these commands are available on `PATH`:

- `snakemake`
- `ThermoRawFileParser`
- `timsconvert`
- `FileConverter`
- `dotnet`

Then update `config/config.yaml` to match your local installation, especially:

- `maxquant_cmd_dll`
- `thermo_raw_file_parser`
- `timsconvert_bin`
- `openms_fileconverter`

Local execution example:

```bash
snakemake --cores 4
```

With a local override config:

```bash
snakemake --configfile config/config.local.yaml --cores 4
```

## Tests

Unit tests cover `workflow/scripts/render_mqpar.py`:

```bash
python3 -m unittest discover -s .test/unit -p 'test_*.py' -v
```

Integration tests cover repository layout and Snakemake dry-runs:

```bash
python3 -m unittest discover -s .test/integration -p 'test_*.py' -v
```

The repository's tests and `snakemake -n` dry-runs work without those tools being installed, but real conversion and MaxQuant execution require either your prepared Docker image or a host environment with the required tools on `PATH`.
