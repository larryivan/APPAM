# Publication readiness

APPAM should be presented as a reproducible execution and provenance platform with two scientific workflows. The Web UI is an enabling interface, not the scientific novelty by itself.

## Defensible claims now

| Claim | Current evidence | Manuscript treatment |
| --- | --- | --- |
| One-click, role-controlled workflow execution | API/UI implementation and permission tests | Software capability |
| Explicit paired-read handling | DAG tests and frozen sample contract | Methods/implementation |
| Complete per-run config and input snapshots | Manifest/config generation and resume tests | Reproducibility capability |
| Retry/resume runtime drift rejection | Environment/database fingerprint comparison tests | Reproducibility capability |
| Conditional database/runtime preflight | Backend checks and database manifest | Software capability |
| Paleoproteomics batch conversion/search/QC | Unit and dry-run integration tests | Workflow capability, pending real vendor-file validation |

## Claims that are not yet supported

| Candidate claim | Evidence still required |
| --- | --- |
| Damage-filtered binning improves ancient MAG recovery | Locked simulations, held-out empirical data, blanks, external baseline, uncertainty intervals |
| APPAM outperforms nf-core or another workflow | Matched versions/resources/databases and raw run-level results |
| Optimized PyDamage is equivalent and faster | Numerical equivalence tolerances plus cold-cache runtime/memory repetitions |
| Deamidation authenticates ancient peptides | Independent authentication evidence and controls; APPAM QC alone is descriptive |
| Production security for untrusted multi-tenant Internet use | Dedicated security review, hardened process isolation, external identity provider, and penetration testing |

## Manuscript-to-repository audit

The planning manuscript must be revised against the frozen release branch before submission. The following are not wording details; they change the scientific claim.

| Draft concept or claim | Repository reality | Required manuscript action |
| --- | --- | --- |
| APPAM is a free public platform that removes the need for HPC | APPAM is currently self-hosted software for a trusted laboratory. Large GTDB-Tk, binning, and MaxQuant runs still need adequate CPU, RAM, storage, and licensed/vendor components. | Describe local deployment and reduced operational friction. Do not promise a public service or hardware independence until such a service is operated and measured. |
| An optimized PyDamage implementation provides large speed and memory gains | The shipped environment installs upstream `pydamage==1.0`; no optimized implementation or equivalence suite is present. | Remove every optimization number from the main text and abstract, or archive the optimized source and pass the equivalence/performance benchmark first. |
| PyDamage-positive contig filtering improves ancient MAG recovery | Conservative defaults bin all contigs. Filtering is an opt-in ablation because it may discard low-coverage authentic sequence and alter completeness/contamination. | Report a preregistered paired ablation across simulations, empirical samples, and blanks with uncertainty intervals. Do not select thresholds on the test set. |
| The workflow always consists of FastQC, AdapterRemoval, QUAST, refinement, CheckM1, and all annotation tools | The default path uses fastp, keeps refinement and CheckM1 optional, uses CheckM2/GUNC, and enables only GTDB-Tk and Prokka among downstream annotations. QUAST is an advanced tool rather than a core DAG target. | Make the methods table match the exact publication preset and archive its resolved config. Label every optional module explicitly. |
| APPAM performs integrated ancient multi-omics inference | Metagenomics and paleoproteomics are two separately executable workflows with shared execution/provenance infrastructure; there is no joint statistical model. | Use “multi-workflow” or “supports metagenomics and paleoproteomics,” not “integrative multi-omics analysis,” unless a validated integration layer is added. |
| Paleoproteomics is validated across vendor formats | The DAG, mqpar rendering, and QC are covered by unit/dry-run tests, but real licensed Thermo RAW and Bruker `.d` fixtures have not been archived and compared. | Keep paleoproteomics secondary or supplementary until both vendor paths and expected MaxQuant outputs pass real-data acceptance tests. |
| MaxQuant and every reference database are contained in the application image | MaxQuant is mounted from an administrator-provided installation; large databases are mounted and described by a manifest. Native Mamba deployment is also supported. | Describe external licensed tools and mounted databases accurately, including exact versions, dates, and checksums. |
| AI parameter filling is a scientific contribution | The routine Web workflow uses deterministic presets and schemas. OpenCode remains an optional administrator capability and is not exposed as a scientific workflow feature. | Exclude AI parameter filling from the scientific claims. Reproducibility relies on frozen resolved parameters. |
| APPAM is already faster or more accurate than competing workflows | The repository contains a benchmark protocol and synthetic example observations, not publishable comparative results. | Run matched datasets with identical databases, versions, resources, repetitions, failure accounting, and raw observation release before making comparative claims. |

## Evidence package required for submission

Each reported run must be traceable to one immutable release and include:

1. Raw input accession or archived checksum, resolved sample table, complete effective configuration, and command line.
2. Git commit, package/environment export, binary versions, database manifest, database checksums, and host resource description.
3. Per-rule wall time and peak memory, failure/timeout records, seeds where applicable, and all excluded-run reasons.
4. Raw benchmark observations before aggregation, paired dataset/method identifiers, analysis code, and machine-readable summary tables.
5. Negative controls and blanks for ancient metagenomics; target-decoy/FDR settings and independent authentication evidence for paleoproteomics.
6. A provenance bundle generated by APPAM for every figure-producing workflow run.

Synthetic fixtures, dry runs, lint results, and UI tests demonstrate software behavior only. They are not biological validation and must not appear as performance evidence.

`python backend/manage.py audit-run RUN_DIR --json` mechanically checks the identity parts of items 1 and 2 and returns a stable report with explicit blocker and warning identifiers. Blockers: a dry run; an unclean or unrecorded workflow commit; a missing or mismatched effective-configuration digest; a resolved input table that has no SHA-256, is missing from disk, or no longer matches its recorded digest; metadata-only or missing input fingerprints; runtime identity that is absent or too shallow; a database manifest that was missing, invalid, or no longer matches its run-time snapshot digest; an unrecorded command line; and an accepted `APPAM_ALLOW_RUNTIME_DRIFT_ON_RETRY` deviation. The same report is written into every downloadable provenance bundle as `publication-audit.json`.

Runtime identity is judged against what the run actually used. A run that claims a container image must record its immutable digest; a native Mamba run must record installed-package fingerprints for every environment its enabled modules consume, and disabled modules do not gate. A paleoproteomics run must fingerprint both the conversion environment and the MaxQuant binary. A workflow the audit has no depth rule for produces a warning, never a silent pass.

Provenance bundles are assembled entirely from the archived run: the database manifest in a bundle is the snapshot taken when the run was prepared, never the manifest currently on the server.

The audit assesses evidence completeness, never scientific validity. Input accessions, per-rule resource accounting and excluded-run reasons (item 3), controls and blanks (item 5), and the mapping from figures to runs (item 6) are not machine-checkable here and stay a manual submission step.

## Minimum publishable study design

The first defensible article should be a software/methods paper, not a new-algorithm paper. A compact but credible study has four layers:

1. **Software verification:** clean-clone CI, permission tests, failure recovery, frozen provenance, database preflight, and one-click task completion.
2. **Metagenomics validation:** simulated mixtures with known truth plus held-out empirical ancient samples and blanks. Compare the conservative APPAM preset against at least one externally maintained workflow under matched resources.
3. **Damage-filter ablation:** all-contig versus PyDamage-positive binning, paired within every dataset. Report MAG recovery, completeness, contamination, strain/taxon precision-recall, runtime, memory, and failures.
4. **Paleoproteomics validation:** at least one Thermo RAW and one Bruker `.d` dataset with expected conversion/search outputs, fixed FDR, reference database provenance, and descriptive modification QC. Keep this layer supplementary if sample size is small.

Recommended main figures are the frozen architecture/provenance model, the exact publication DAG, benchmark accuracy/resource results, and one empirical case study. UI screenshots belong in a compact usability figure or supplement rather than carrying the novelty claim.

## Release gates

1. Freeze the manuscript branch, software version, author list, license, and `CITATION.cff`.
2. Run CI from a clean clone on Linux x86_64.
3. Archive the machine-readable output of `python backend/manage.py doctor --json --require-publication` and resolve every host-environment publication blocker, including a dirty or unidentified Git checkout. The command exits non-zero while any blocker remains; it does not replace real-run or biological validation.
4. Complete a real small FASTQ end-to-end run and archive its provenance bundle. `python backend/manage.py audit-run RUN_DIR` must exit zero for that run.
5. Complete licensed Thermo RAW and Bruker `.d` fixture runs and compare expected mzML/MaxQuant tables.
6. Fill the database manifest with exact releases and checksum it. Delete the `"template": true` field copied from `docker/database-manifest.example.json`; the readiness check and the run audit both reject a manifest that still declares itself a template.
7. Pre-register `benchmark/design/` tables before held-out analysis. Write each `*.tsv` with `status=frozen`, unique identifiers, and no placeholder fields, then analyse with `require_design: true` so every observed dataset, scenario, and method must appear in the frozen tables. `summary.json` then records each table's SHA-256.
8. Publish raw benchmark observations, failure logs, configs, environment exports, and analysis outputs in a DOI-backed archive.
9. Replace all placeholders in citation/release metadata and tag the exact archived commit.

Gates 3, 6, and 7 are verifiable from a checkout today, and gate 4 becomes verifiable as soon as one real run exists. Gates 1, 2, 5, 8, and 9 depend on real data, licensed vendor files, or an external archive.

The current metagenomics workflow requires paired-end input, does not perform automatic host depletion, and runs Prokka in bacterial metagenome mode. A manuscript must either scope its validation data accordingly or add and validate those capabilities before claiming broader coverage.

## Recommended paper shape

The strongest first paper is a methods/software article centered on reproducible ancient multi-omics workflow execution for small laboratories. Lead with architecture, input contracts, environment/database provenance, safe recovery, and usability. Treat damage-filtered binning as an evaluated ablation. Include paleoproteomics as a secondary workflow unless its biological validation is equally mature.

Avoid framing APPAM as a new biological algorithm unless the benchmark demonstrates that claim independently of the platform.
