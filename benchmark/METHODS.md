# Benchmark methods and acceptance gates

## Primary questions

1. Does APPAM reproduce expected assembly, binning, quality-control, and annotation outputs on declared inputs?
2. Does damage-filtered binning improve recovery precision or contamination without unacceptable recall loss relative to all-contig APPAM?
3. What runtime and memory overhead does APPAM add relative to a maintained external workflow under matched resources?
4. Does any optimized damage implementation remain numerically equivalent to upstream PyDamage before speed is compared?

## Locked design

Before running the held-out test partition, copy the three `benchmark/design/*.template.tsv` files to non-template names and freeze:

- dataset accessions, licenses, checksums, and biological context;
- simulation software, version, command, seed, and truth tables;
- workflow commits, container digests, database-manifest digest, threads, memory, and cache policy;
- quality thresholds and the direction of every primary metric;
- exclusion rules, failed-run handling, and statistical tests.

Do not tune PyDamage thresholds, MAG quality thresholds, or method-specific parameters on the test partition.

## Required outputs

- Raw per-run observations, never only group averages.
- Snakemake benchmark files and scheduler accounting for every timed run.
- Input, config, environment, database, and workflow provenance bundles.
- Ground-truth mappings for simulated reads, contigs, taxa, and genomes.
- Failure logs and excluded-run decisions.

## Acceptance gates

- All CI, dry-run, and schema checks pass from a clean checkout.
- At least two independent empirical preservation contexts and appropriate blanks are included.
- Runtime comparisons have at least three independent cold-cache repetitions.
- Accuracy comparisons report uncertainty across independent datasets/replicates, not reads as pseudoreplicates.
- External baselines use documented, defensible parameters and identical resource ceilings.
- Damage-filtering and optimized-PyDamage claims are omitted unless their corresponding tests pass.

The checked-in example observations are synthetic fixtures and are not evidence for any manuscript claim.
