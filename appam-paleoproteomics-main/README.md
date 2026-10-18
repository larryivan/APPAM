# APPAM paleoproteomics

This Snakemake workflow converts Thermo `.RAW` files and Bruker `.d` directories to mzML, renders MaxQuant parameters, runs either a joint or per-sample MaxQuant search, and generates descriptive paleoproteomics QC.

It is an optional APPAM workflow. Deamidation and identification counts are reported descriptively; they are not, by themselves, evidence of peptide antiquity or authenticity.

## Input table

`config/samples.tsv` requires:

```tsv
sample_id	input_path	experiment	fraction
S1	raw_ms/S1.RAW	projectA	1
S2	raw_ms/S2.d	projectA	2
```

Sample IDs must be unique. `experiment` must be non-empty and `fraction` must be an integer. Standalone Snakemake runs may use absolute paths or paths relative to the table. Web runs require sample inputs inside the project workspace and permit the reference FASTA inside either the project or `APPAM_DATABASES_ROOT`; every run snapshots resolved paths for resume/retry and provenance export.

## Frozen search parameters

`config/config.yaml` records:

- the existing rule runtime environment prefix;
- FASTA and mqpar template paths;
- enzymes and enzyme mode;
- fixed and variable modifications;
- peptide, protein, and site FDR;
- minimum peptide length and mass tolerances;
- match-between-runs and contaminant settings;
- exact converter, .NET, and MaxQuant executable paths.
- `maxquant_mode`: `batch` for one joint search or `per_sample_id` for one isolated search per acquisition.
- the MaxQuant version, FASTA parsing rules, and DDA/DIA missed-cleavage limits written into every generated XML file.

For local changes, use an ignored `config/config.local.yaml` rather than editing tracked defaults.
The tracked MaxQuant template is `workflow/templates/mqpar.template.xml`.

## Run

```bash
snakemake --configfile config/config.local.yaml --cores 4 --sdm conda --dry-run
snakemake --configfile config/config.local.yaml --cores 4 --sdm conda
```

Snakemake discovers `workflow/Snakefile` from the repository root.

## Outputs

- `results/thermo/` and `results/bruker/`: converter intermediates.
- `results/mzml/`: normalized mzML inputs.
- `results/maxquant/batch/mqpar.xml`: rendered joint-search config in `batch` mode.
- `results/maxquant/batch/combined/txt/`: batch proteinGroups, peptides, and evidence tables.
- `results/maxquant/samples/{sample}/`: isolated mqpar and result tables in `per_sample_id` mode.
- `results/reports/maxquant/`: per-search QC JSON and HTML files.
- `results/reports/paleoproteomics-qc.{json,html}`: combined QC summary for either mode.

The QC report counts identified groups/peptides/evidence, reverse and contaminant records, raw-file coverage, and available deamidation fields. Authentication, taxonomic interpretation, and contamination assessment still require study-specific controls and expert review.

## Runtime

Required software:

- Snakemake and Python
- ThermoRawFileParser
- timsconvert
- OpenMS `FileConverter`
- .NET runtime
- MaxQuant `MaxQuantCmd.dll`

APPAM uses the stable convention `/opt/tools/maxquant-current/bin/MaxQuantCmd.dll` in containers. Native installations may point `APPAM_PALEO_MAXQUANT_CMD` directly to any staged MaxQuant release, such as `$HOME/MaxQuant_v2.8.1.0/bin/MaxQuantCmd.dll`.

MaxQuant and vendor conversion components are not stored in this repository. Confirm their licenses before redistribution.

## Docker

Standalone packaging assets are `docker/Dockerfile`, `docker/environment.yml`, and `docker/entrypoint.sh`.

Root Compose deployments mount `APPAM_HOST_MAXQUANT_ROOT` read-only at `/opt/tools/maxquant-current`; the release is not copied into the image. The standalone Docker assets in this directory expect the build context to provide `tools/MaxQuant` and install it at the same generic location.

Example root deployment:

```bash
FLASK_SECRET_KEY=... docker compose up -d --build
```

For hosts where Docker cannot start containers, follow `../deploy/native/README.md` and install the optional paleoproteomics environment.

## Tests

```bash
python -m unittest discover -s .test/unit -p 'test_*.py' -v
python -m unittest discover -s .test/integration -p 'test_*.py' -v
```

Integration tests validate layout, input errors, command quoting, and Snakemake DAGs without executing vendor software. A real release still requires fixture RAW/.d conversion and MaxQuant result comparison on a licensed test system.
