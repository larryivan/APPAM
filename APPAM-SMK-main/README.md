# APPAM-SMK

APPAM-SMK is the Snakemake workflow component of APPAM, providing automated and reproducible processing for ancient metaproteomics and metagenomics data.

## Features
- Reproducible, user-friendly, efficient, and actively maintained workflow
- End-to-end processing from raw reads to bins, taxonomy, MAG quality assessment, and genome annotation
- Built-in QC, assembly, damage assessment, variant calling, binning, CheckM/CheckM2/GUNC assessment, classification, and annotation
- Optional preprocessing backend: `fastqc + AdapterRemoval` or `fastp`
- Ready-to-use local and SLURM execution profiles

## Requirements

## Installation
```bash
git clone git@github.com:XREAL1TY/APPAM-SMK.git
cd APPAM-SMK
```

Snakemake will create environments from `workflow/envs/` when you run with `--use-conda` (enabled in profiles).  
MetaWRAP and PyDamage environments are external and must be created separately, then referenced by path in `config/config.yaml`.

## Input Data
- Raw paired-end reads: `{sample}_R1.fastq.gz` and `{sample}_R2.fastq.gz` under `paths.raw_data_dir` in `config/config.yaml`
- Sample manifest: `config/samples.tsv` with a `sample_id` column

Example `config/samples.tsv`:
```tsv
sample_id
sample1
```

## Configuration
Main config file: `config/config.yaml`

Key sections:
- `paths`: input/output/log/benchmark directories
- `params`: tool parameters (e.g., `min_contig_len`, `pydamage_window`)
- `tools`: external environment paths (e.g., `metawrap_env`, `pydamage_env`)
- `databases`: external database paths (e.g., `checkm1_db`, `checkm2_db`, `gunc_db`, `eggnog_db`)
- `tools`: external environment paths for Docker/Conda-backed runtime modules

Optional preprocessing mode:
- `preprocess_method`: `adapter_removal` (default) or `fastp`
- `fastp_detect_adapter_for_pe`: enable `--detect_adapter_for_pe` when using `fastp` (default `true`)

Optional ancient-only binning (based on PyDamage results):
- `use_ancient_contigs`: enable/disable filtering before binning
- `pydamage_qvalue_max`: q-value threshold (default `0.05`)
- `pydamage_predicted_accuracy_min`: minimum `predicted_accuracy` (default `0.5`)
- `pydamage_contig_column`, `pydamage_qvalue_column`, `pydamage_predicted_accuracy_column`: column names in `pydamage_results.csv`

## Quick Start
Dry run:
```bash
snakemake --profile profiles/local -n
```

Run locally:
```bash
snakemake --profile profiles/local
```

Run on SLURM:
```bash
snakemake --profile profiles/slurm
```

Visualize the DAG:
```bash
snakemake --profile profiles/local --dag | dot -Tsvg > dag.svg
```

Rerun a specific rule:
```bash
snakemake --profile profiles/local --forcerun <rule_name>
```

## Workflow Overview
Default targets in `rule all` include:
- Read QC and adapter trimming/collapsing
- Assembly
- Mapping and damage assessment
- Binning and refinement
- Bin quality assessment with CheckM1 and optional CheckM2
- Contamination/chimerism assessment with optional GUNC
- Taxonomic classification
- Optional genome annotation with Prokka, eggNOG-mapper, ABRicate, RGI, and antiSMASH

Additional rules exist but are not in the default targets:
- Variant calling
- Contig filtering by damage (ancient vs modern)

## Outputs
Primary outputs are under `paths.results_dir` in `config/config.yaml`. Examples (relative to `paths.results_dir`):
- `preprocess/` (both modes write preprocessing outputs here)
- `megahit/`
- `bowtie2/`
- `pydamage/`
- `metawrap/`
- `checkm/`
- `checkm2/`
- `gunc/`
- `gtdbtk/`
- `annotation/prokka/`
- `annotation/eggnog/`
- `annotation/abricate/`
- `annotation/rgi/`
- `annotation/antismash/`

Logs and benchmarks are written to `paths.logs_dir` and `paths.benchmark_dir`.  
Runtime directories like `work/` and `.snakemake/` are gitignored.

When ancient-only binning is enabled, filtered contigs are written to:
- `pydamage/{sample}/ancient.contigs.fa`
- `pydamage/{sample}/modern.contigs.fa`

## Project Structure
- `workflow/Snakefile`: workflow entry point
- `workflow/rules/`: pipeline stages (`preprocess.smk`, `assembly.smk`, `damage.smk`, `contigs_filter.smk`, `variants.smk`, `binning.smk`, `classify.smk`)
- `workflow/envs/`: Conda environment specs
- `profiles/`: execution profiles (`local`, `slurm`)
- `config/`: configuration and sample manifest

## Contributing
Issues and pull requests are welcome. Please keep changes focused and describe the workflow impact, commands run, and any config or environment updates.

## License
MIT. See `LICENSE`.

## Citation
See `CITATION.md`.
