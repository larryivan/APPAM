# Config Guide

This directory contains the user-edited inputs for the workflow:

- `config.yaml`
- `samples.tsv`

`config.yaml` is the tracked default configuration. For machine-specific overrides, create `config/config.local.yaml` and invoke Snakemake with `--configfile config/config.local.yaml`. The repository ignores `*.local.yaml`, so local paths and private settings stay out of version control.

## `samples.tsv`

`samples.tsv` must contain exactly these four tab-separated columns, in this order:

```tsv
sample_id	input_path	experiment	fraction
```

Column meanings:

- `sample_id`: unique identifier for one raw acquisition. It becomes `results/mzml/{sample_id}.mzML`.
- `input_path`: path to the source data. Thermo inputs must be a single `.RAW` file. Bruker inputs must be a `.d` directory.
- `experiment`: MaxQuant experiment name. Multiple fraction files from the same sample should share the same `experiment`.
- `fraction`: MaxQuant fraction number for that input file. This value is required and must be an integer. Use `32767` for non-fractionated single-shot runs if that is the convention you want to keep.

Example:

```tsv
sample_id	input_path	experiment	fraction
S1_F1	/data/project/S1_F1.RAW	S1	1
S1_F2	/data/project/S1_F2.RAW	S1	2
S2	/data/project/S2.d	S2	32767
```

## Container Path Convention

Recommended Docker mounts:

- mount the repository to `/workspace`
- mount raw data to `/data`

With that convention:

- `config/samples.tsv` should use container paths under `/data`
- workflow outputs will be written under `/workspace/results`
- the default `maxquant_output_dir` resolves to `/workspace/results/maxquant` inside the container

Example `docker run`:

```bash
docker run --rm -it \
  -v "$PWD":/workspace \
  -v /path/to/raw_data:/data \
  -w /workspace \
  your-image:tag \
  snakemake --cores 4
```

Example `samples.tsv` rows for container execution:

```tsv
sample_id	input_path	experiment	fraction
S1_F1	/data/project/S1_F1.RAW	S1	1
S1_F2	/data/project/S1_F2.RAW	S1	2
S2	/data/project/S2.d	S2	32767
```

Do not write host-only paths such as `/Users/...` or `D:\\...` in `samples.tsv` when running inside Docker. Use the paths that exist inside the container after mounting.

## `config.yaml`

Important keys:

- `sample_table`: path to `samples.tsv`
- `mqpar_template`: path to the version-controlled MaxQuant template XML
- `results_dir`: root directory for converted mzML files and logs
- `maxquant_output_dir`: MaxQuant result directory
- `maxquant_mode`: `batch` or `per_sample_id`
- `threads`: threads passed to tools and written into the generated MaxQuant parameters
- `runtime_env`: existing Conda/Mamba environment prefix activated for every rule
- `fasta_path`: FASTA database path written into the generated mqpar XML
- `match_between_runs`
- `enzymes`
- `enzyme_mode`
- `max_missed_cleavages` and `max_missed_cleavages_dia`
- `identifier_parse_rule` and `description_parse_rule`
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

The workflow declares one existing Conda/Mamba runtime prefix for every rule. Run Snakemake with `--sdm conda`; the prefix is activated without recreating it.

In the Docker image, `entrypoint.sh` activates the `paleoproteomics` conda environment and exports:

- `/opt/tools/ThermoRawFileParser` to `PATH`
- `/opt/tools/maxquant-current` to `PATH`
- `/opt/tools/openms-development/bin` to `PATH`
- `/opt/tools/openms-development/lib` to `LD_LIBRARY_PATH`

That is why the default config uses command names for most tools:

- `dotnet_bin: dotnet`
- `thermo_raw_file_parser: ThermoRawFileParser`
- `timsconvert_bin: timsconvert`
- `openms_fileconverter: FileConverter`

MaxQuant is the exception. The workflow needs the DLL path passed to `dotnet`, so the default is:

- `maxquant_cmd_dll: /opt/tools/maxquant-current/bin/MaxQuantCmd.dll`

If you run the workflow outside the image, replace these values with paths that match your host environment.

For host deployment, `timsconvert` is recommended to be installed via `conda` so it matches the environment used in `docs/plans/environment.yml`. A typical install command is:

```bash
conda install -c bioconda -c conda-forge timsconvert
```

Output locations in the container:

- Thermo intermediate mzML: `/workspace/results/thermo`
- Bruker intermediate mzML: `/workspace/results/bruker`
- final mzML: `/workspace/results/mzml`
- batch mqpar: `/workspace/results/maxquant/batch/mqpar.xml`
- batch MaxQuant tables: `/workspace/results/maxquant/batch/combined/txt`
- per-sample searches: `/workspace/results/maxquant/samples/{sample}`
- consolidated QC: `/workspace/results/reports/paleoproteomics-qc.html`

## `mqpar.template.xml` and Generated `mqpar.xml`

`workflow/templates/mqpar.template.xml` is the tracked template for MaxQuant. It should contain placeholder paths instead of real sample-specific paths.

In `batch` mode, the workflow renders:

- `results/maxquant/batch/mqpar.xml`

In `per_sample_id` mode, it renders one file per acquisition:

- `results/maxquant/samples/{sample}/mqpar.xml`

The rendered file is the one passed to MaxQuant. The template is not used directly for execution.

The workflow rewrites these parts of the template on each run:

- `filePaths`
- `experiments`
- `fractions`
- `paramGroupIndices`
- `ptms`
- `referenceChannel`
- `fastaFiles/FastaFileInfo/fastaFilePath`
- `fastaFiles/FastaFileInfo/identifierParseRule` and `descriptionParseRule`
- `matchBetweenRuns`
- `includeContaminants`
- `minPeptideLength`
- `peptideFdr`
- `proteinFdr`
- `siteFdr`
- `numThreads`
- `maxQuantVersion`, search/combined/temp folders, and thread count
- each `parameterGroup` block's enzyme mode, missed-cleavage limits, enzymes, modifications, and mass tolerances

All samples currently use the same MaxQuant search parameter group. The workflow therefore writes every `paramGroupIndices` entry as `0`, and the template must contain at least one `<parameterGroup>`.

Other XML nodes are inherited from the template unchanged. When you export a new template from MaxQuant, sanitize real paths before replacing `workflow/templates/mqpar.template.xml`.
