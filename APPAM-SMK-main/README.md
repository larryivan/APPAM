# APPAM-SMK

APPAM-SMK is the ancient-metagenomics workflow used by APPAM. It performs paired-read preprocessing, metagenome assembly, read-to-contig mapping, PyDamage analysis, binning, MAG quality control, taxonomy, and optional annotation.

The conservative default bins all assembled contigs. Restricting binning to PyDamage-positive contigs is an experimental ablation (`use_ancient_contigs: true`), not an established correction method.

## Input contract

`config/samples.tsv` must contain unique sample IDs and explicit paired FASTQ paths:

```tsv
sample_id	forward_reads	reverse_reads
sample1	raw/sample1_R1.fastq.gz	raw/sample1_R2.fastq.gz
```

Standalone Snakemake paths may be absolute or relative to the sample table/raw-data directory. Web runs require reads inside the current project workspace. Supported suffixes are `.fastq`, `.fq`, `.fastq.gz`, and `.fq.gz`. Sample IDs may contain letters, numbers, dots, underscores, and hyphens.

APPAM Web runs copy this table into the run directory with resolved absolute paths. Changing or deleting the original table therefore does not change a retry or resume.

## Read handling

- `fastp` mode keeps surviving read pairs, merged reads, and unpaired reads.
- `adapter_removal` mode keeps surviving read pairs, collapsed reads, truncated collapsed reads, and singletons.
- MEGAHIT receives paired reads and the single-read stream separately.
- Bowtie2 damage mapping receives paired and single reads.
- MetaWRAP receives a combined single-end stream only because its binning interface consumes coverage reads in that form.

## Configuration

Edit a local copy of `config/config.yaml`. Important switches are:

- `preprocess_method`: `fastp` or `adapter_removal`.
- `use_ancient_contigs`: experimental damage-filtered binning; default `false`.
- `enable_bin_refinement`: MetaWRAP refinement; default `false`.
- `unrefined_binner`: output used when refinement is disabled; default `metabat2`.
- `enable_checkm1`: legacy CheckM1 report; default `false`.
- `enable_checkm2`, `enable_gunc`, `enable_gtdbtk`, `enable_prokka`: core result modules.
- `enable_eggnog`, `enable_abricate`, `enable_rgi`, `enable_antismash`: optional expensive/specialized modules.
- `require_database_manifest`: fail before execution when a versioned database manifest is absent; enabled by the Web publication preset.

The `tools` entries may point to existing Conda/Mamba environment prefixes. Snakemake activates those prefixes through the local or Slurm profile. Environment specifications used by APPAM are under `../docker/tools/environments/`.

## Databases

Core publication runs normally require:

- CheckM2 database (`checkm2_db`)
- GUNC database or `.dmnd` file (`gunc_db`)
- GTDB-Tk release directory (`gtdbtk_db`)

eggNOG is needed only when eggNOG annotation is enabled. CheckM1 is needed only for CheckM1 reporting or MetaWRAP refinement. ABRicate, Prokka, and antiSMASH can use their configured software databases; record those releases in the APPAM database manifest. RGI `global` mode uses CARD data loaded into its environment; `local` mode uses a configured directory prepared with `rgi load --local`. Both require an explicit CARD release in the manifest. APPAM records the manifest content and checksum in run provenance.

## Run

From this directory:

```bash
snakemake --snakefile workflow/Snakefile \
  --configfile config/config.local.yaml \
  --profile profiles/local
```

Dry-run:

```bash
snakemake --snakefile workflow/Snakefile \
  --configfile config/config.local.yaml \
  --profile profiles/local --dry-run
```

For Slurm, use `--profile profiles/slurm` after adapting account/partition defaults to the cluster policy. The Slurm executor plugin must be installed in the Snakemake environment.

## Principal outputs

- `fastp/` or `adapterremoval/`: preprocessing products and reports.
- `megahit/{sample}/final.contigs.fa`: assembled contigs.
- `bowtie2/{sample}/`: sorted/indexed contig alignment.
- `pydamage/{sample}/pydamage_results.csv`: upstream PyDamage output.
- `pydamage/{sample}/ancient.contigs.fa`: threshold-selected contigs for the optional ablation.
- `metawrap/binning/{sample}/`: three initial binner outputs.
- `metawrap/bin_refinement/{sample}/`: optional refined bins.
- `checkm2/`, `gunc/`, `gtdbtk/`: MAG quality and taxonomy.
- `prokka/`, `eggnog/`, `abricate/`, `rgi/`, `antismash/`: enabled annotations.
- benchmark and log directories declared in the effective config.

Variant calling outputs are auxiliary and are not interpreted as a general ancient-DNA damage correction.

## Scientific boundaries

- The tracked input contract currently requires paired-end libraries; single-end-only studies need a separate preprocessing contract.
- Host depletion is not performed automatically. Apply and document study-appropriate host screening before APPAM when required.
- The Prokka workflow currently uses bacterial metagenome mode. Archaeal or mixed-domain MAG sets require taxonomy-aware annotation outside this rule.
- Empty selected bin sets and empty annotation inputs are treated as failures rather than successful zero-result runs.
- Negative controls, extraction blanks, damage thresholds, and downstream biological interpretation remain study-design decisions and must be reported separately.

## Validation

Repository dry-run tests exercise both conservative `fastp` and ancient-only AdapterRemoval/refinement DAGs:

```bash
python -m unittest ../tests/test_appam_smk_dry_run.py -v
snakemake --snakefile workflow/Snakefile --configfile tests/config/ci.yaml --lint
```

These checks validate workflow construction, not biological performance. Use the root `benchmark/` protocol before making comparative recovery or speed claims.

## Citation and license

See the repository-root `CITATION.cff` and `LICENSE`.
