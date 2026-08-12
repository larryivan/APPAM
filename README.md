# APPAM

APPAM is a small-laboratory research platform for reproducible ancient metagenomics workflows, with an optional paleoproteomics workflow and Web interface. The Web application is an execution and provenance layer; scientific conclusions remain the responsibility of the underlying workflows and study design.

## Research status

APPAM is under active pre-publication validation. The repository does not currently claim that damage-aware contig filtering improves MAG recovery, or that an optimized PyDamage implementation is faster than upstream PyDamage. Those claims require the benchmark protocol under `benchmark/` and public raw results.

The conservative metagenomics default bins all assembled contigs. PyDamage-only binning is retained as an explicit experimental ablation.

## Components

- `APPAM-SMK-main/`: ancient metagenomics Snakemake workflow.
- `appam-paleoproteomics-main/`: RAW/.d conversion, MaxQuant search, and descriptive QC.
- `backend/`: Flask API, authentication, queue, provenance, reports, and project storage.
- `frontend/`: Vue Web interface.
- `benchmark/`: publication benchmark schema, validation, and statistical summaries.
- `docker/`: reproducible container and deployment assets.

## One-time server setup

Create a deployment `.env` beside `docker-compose.yml`; generate the secret value with `openssl rand -hex 32`:

```bash
FLASK_SECRET_KEY=replace-with-output-of-openssl-rand-hex-32
APPAM_ALLOWED_ORIGINS=http://SERVER_NAME_OR_IP:25078
APPAM_HOST_DB_ROOT=/home/adna/db
APPAM_HOST_MAXQUANT_ROOT=/home/adna/MaxQuant_v2.8.1.0
APPAM_SMK_GTDBTK_DB=/databases/gtdbtk_r226
```

Self-registration is disabled by default. Additional users can be created by an administrator through `POST /api/admin/users`; open registration can be enabled explicitly with `APPAM_ALLOW_REGISTRATION=true`. The first self-registered user is never promoted automatically in production.

Start the service on a custom host port:

```bash
APPAM_WEB_PORT=25078 docker compose up -d --build
docker compose exec tools micromamba run -n backend \
  python /opt/appam/backend/manage.py create-admin --username labadmin
```

The administrator command prompts for the password without retaining it in shell history. Automated deployments may instead use `APPAM_BOOTSTRAP_ADMINS_JSON`.

After the first administrator is created, run the same readiness audit shown in the Web Admin Center:

```bash
docker compose exec tools micromamba run -n backend \
  python /opt/appam/backend/manage.py doctor
```

The command reports core runtime readiness separately from publication readiness. A missing optional paleoproteomics runtime does not block metagenomics, while an incomplete database manifest keeps the publication status incomplete. `doctor` exits non-zero on a core blocker; add `--require-publication` to also fail on a publication blocker, and `--json` to archive the report. The JSON report carries `schema_version`, the checkout commit, and the blocker identifiers, so an archived copy stays auditable.

For native Mamba deployment, use the scripts under `deploy/native/`; Docker is not required by either workflow.

The complete native installation, systemd, nginx, database, and port procedure is in `deploy/native/README.md`.

## Guided Web workflow

For routine laboratory use, create a project and select **Ancient metagenomics** or **Paleoproteomics**. Upload input files directly on the analysis page, review the automatically detected samples, and select **Start analysis**. APPAM generates the sample table, validates inputs, runs preflight checks, and submits the job to the shared queue without requiring users to edit TSV or YAML files.

Each project has four stable destinations: **Overview**, **Analysis**, **Files**, and **Tools**. The **Options** dialog exposes versioned presets and scientific settings only when a study needs to depart from the recommended defaults. The searchable Tools page provides individual programs without mixing them into the routine workflow. Runtime paths, database setup, and worker diagnostics remain in the Admin Center. Project terminals, live system monitoring, and OpenCode are loaded as administrator-only floating tools and are never rendered for regular users.

## Workflow inputs

Metagenomics manifests use explicit paths:

```tsv
sample_id	forward_reads	reverse_reads
sample1	raw/sample1_R1.fastq.gz	raw/sample1_R2.fastq.gz
```

APPAM snapshots this table with resolved absolute paths for every run. Preprocessing retains paired, collapsed/singleton, and all-read streams. Assembly and damage mapping use paired reads when present.

Paleoproteomics tables use:

```tsv
sample_id	input_path	experiment	fraction
sample1	raw_ms/sample1.RAW	projectA	1
```

Every Web run writes a complete effective configuration, resolved input table, workflow Git revision, runtime environment fingerprints, and optional SHA-256 input hashes. Use the `Publication run` preset to enable full input hashes.
For metagenomics, that preset also requires a versioned database manifest and keeps specialized annotation modules disabled until the study explicitly selects them.

Each run also snapshots the parsed database manifest it used, and records the SHA-256 of the resolved sample table it wrote. Provenance bundles are built from those archived records rather than from current server state.

Every run is audited for archival completeness against a fixed schema. The verdict ships inside the downloadable provenance bundle as `publication-audit.json` and can be recomputed from the checkout:

```bash
python backend/manage.py audit-run PROJECT_DIR/workflow_runs/appam-smk/RUN_ID --json
```

Run from disk, the audit re-hashes the archived resolved sample table, so a table edited after the run becomes a blocker. It reports evidence completeness only — exact software, configuration, input, runtime, and database identity. It never assesses data quality or whether a result supports a claim.

## Databases

Expected database directories are CheckM2, GUNC, eggNOG, GTDB-Tk, and KrakenUniq when read-level taxonomy is used. CheckM1 is required only when MetaWRAP bin refinement or the standalone CheckM1 report is enabled. Record versions and download dates in `appam-db-manifest.json`; begin with `docker/database-manifest.example.json`. The example declares `"template": true` and its versions are illustrative, so publication checks reject it until that field is deleted and every version is replaced with the release actually installed.

## Validation

```bash
python -m unittest discover -s backend/tests
python -m unittest discover -s appam-paleoproteomics-main/.test/unit
python -m unittest discover -s appam-paleoproteomics-main/.test/integration
python -m unittest discover -s tests
cd frontend && pnpm install --frozen-lockfile && pnpm test && pnpm build
```

Scientific benchmark instructions and acceptance criteria are in `benchmark/README.md`. Example observations are synthetic and must never be reported as APPAM performance.

The manuscript claim audit, minimum study design, evidence package, and release gates are in `docs/PUBLICATION_READINESS.md`.

## Security scope

APPAM is intended for a trusted laboratory deployment behind HTTPS. OpenCode and shell access are optional administrator-only features, have no default tool permissions, and are not part of the scientific claims. Remote downloads reject local/private network targets and FTP is disabled by default.

See `SECURITY.md` for the supported trust boundary and deployment requirements.

Remote download tasks are stored in SQLite and survive backend restarts. Interrupted transfers return as paused instead of restarting automatically. Finished download history is retained for `APPAM_DOWNLOAD_HISTORY_DAYS` days (30 by default) and can also be cleared from the Download Manager.

## License and citation

APPAM is available under the MIT License. See `CITATION.cff` for the current software citation placeholder.
