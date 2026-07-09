# APPAM publication benchmark

This directory defines the evidence package required for an APPAM methods paper. It deliberately contains no claimed performance results.

## Required comparisons

Use identical input reads, references, CPU limits, memory limits, and database releases for:

1. `appam-all-contigs`: conservative APPAM with `use_ancient_contigs=false`.
2. `appam-damage-filtered`: APPAM ablation with `use_ancient_contigs=true`.
3. `nf-core-mag-ancient`: the closest maintained ancient-MAG workflow baseline.
4. Any additional published workflow named in the manuscript.

Compare upstream PyDamage and any optimized implementation separately before attributing workflow-level effects to the damage model.

## Experimental design

- Simulated conditions must vary damage, fragment length, coverage, endogenous fraction, modern near-neighbour contamination, and community complexity.
- Include independent biological datasets from more than one preservation context plus extraction/library blanks.
- Use at least three computational replicates for runtime metrics and enough independent simulated replicates for confidence intervals.
- Freeze input checksums, workflow commits, database versions, threads, memory, and cache state.
- Report contig and taxon precision/recall, recovered MAG counts at declared quality thresholds, completeness, contamination, ANI, runtime, and peak RSS.
- Treat PyDamage thresholds as an ablation. Do not select thresholds on the final test set.

Use `design/datasets.template.tsv`, `design/scenarios.template.tsv`, and `design/methods.template.tsv` as the pre-registration skeleton. `METHODS.md` defines the acceptance gates and required archived evidence.

## Observation format

`data/observations.example.tsv` is synthetic. Replace it with raw run-level observations using these columns:

```text
dataset_id scenario_id method replicate metric value unit
```

Each row must be one independent run-level measurement. Do not average before adding observations.

## Run the analysis

```bash
snakemake -s benchmark/Snakefile --cores 1 \
  --config observations=benchmark/data/observations.example.tsv \
  baseline=appam-all-contigs
```

Outputs are written to `benchmark/results/`:

- `validated.ok`: schema and design validation.
- `summary.tsv`: group means, standard deviations, and deterministic bootstrap 95% intervals.
- `paired-differences.tsv`: paired differences against the declared baseline.
- `summary.json`: machine-readable analysis.

The example output is only a test fixture. Publication tables must be regenerated from archived raw observations.

Convert a one-row Snakemake benchmark file into run-level runtime observations with:

```bash
python benchmark/scripts/collect_runtime_metrics.py path/to/rule.benchmark.tsv \
  --dataset DATASET --scenario SCENARIO --method METHOD --replicate 1 \
  --output benchmark/data/runtime-observations.tsv
```
