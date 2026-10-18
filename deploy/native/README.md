# Native Mamba deployment

This is the recommended path on hosts where Docker is unavailable inside an LXC/container. It keeps the Web application on port `25078` and binds the backend to localhost on `25079`.

## 1. Install environments

Run as the unprivileged service account:

```bash
cd /srv/appam/APPAM
./deploy/native/install-environments.sh
```

Add `--with-paleoproteomics` only when Thermo/Bruker conversion and MaxQuant are needed. MaxQuant itself and ThermoRawFileParser remain separately licensed/vendor-delivered tools and must be placed on the server explicitly.
The installer keeps `timsconvert`/PySide6 in a separate environment from OpenMS so their Qt runtimes cannot conflict.

## 2. Generate the runtime environment

```bash
./deploy/native/render-env.sh \
  --db-root "$HOME/db" \
  --projects-root "$HOME/appam-data/projects" \
  --web-origin "http://SERVER_NAME_OR_IP:25078" \
  --maxquant-root "$HOME/MaxQuant_v2.8.1.0"
```

Keep `deploy/native/appam.env` mode `0600` and never commit it. Create the first administrator with a hidden password prompt:

```bash
./deploy/native/manage.sh create-admin --username labadmin --display-name "Lab administrator"
```

`APPAM_BOOTSTRAP_ADMINS_JSON` remains available for unattended provisioning, but the interactive command avoids retaining a plaintext password in the environment file.

## 3. Build the Web UI

```bash
cd frontend
mamba run -n appam-web pnpm install --frozen-lockfile
mamba run -n appam-web pnpm build
```

### Serving under a URL prefix

A gateway can publish APPAM under a path such as
`https://gateway.example/proxy/relative/10.0.0.5/25078/` and strip that prefix
before forwarding. Render the environment with `--public-base-path` and the
gateway origin, then build the UI with the environment loaded so the prefix is
baked into its URLs:

```bash
./deploy/native/render-env.sh ... \
  --web-origin "https://gateway.example" \
  --public-base-path /proxy/relative/10.0.0.5/25078
set -a; . deploy/native/appam.env; set +a
cd frontend && mamba run -n appam-web pnpm build
```

The session cookie is then scoped to the prefix, which matters on a gateway
host shared with other services. Every service on that host still shares one
browser origin, so prefer a dedicated domain when one is available. Enable the
commented prefix block in `nginx-appam.conf.example` to keep direct access
working.

## 4. Start and verify

Foreground smoke test:

```bash
cd /srv/appam/APPAM
./deploy/native/run-backend.sh
```

The script runs one Gunicorn `gthread` worker with configurable threads. One process is intentional: Socket.IO terminal sessions and the embedded SQLite queue are process-local. Use the Redis/RQ mode before designing a multi-process deployment.

In another shell:

```bash
curl -fsS http://127.0.0.1:25079/api/health
./deploy/native/manage.sh doctor
```

The `doctor` command and the Web Admin Center use the same host-environment checks. Fix core blockers before accepting jobs, then complete the database version manifest before creating publication runs. `./deploy/native/manage.sh doctor --require-publication --json` writes the archivable report and exits non-zero while a host publication blocker remains, including an uncommitted checkout.

For persistence, adapt `appam-backend.service.example` to the actual checkout path and install it as a system or user service. Adapt `nginx-appam.conf.example`, enable it in nginx, and place TLS in front of port `25078` for non-local access.

## 5. Database layout

The generated environment expects:

```text
~/db/checkm2
~/db/gunc
~/db/eggnog
~/db/gtdbtk_r226
~/db/krakenuniq_refseq_bav
```

When a GTDB-Tk archive is extracted as `~/db/gtdbtk_r226/release226`, the
environment renderer automatically records that inner release directory as
`GTDBTK_DATA_PATH`.

`~/db/checkm` is optional and only needed for CheckM1 or MetaWRAP refinement. KrakenUniq is optional when its advanced read-taxonomy tool is not used. Create `~/db/appam-db-manifest.json` from `docker/database-manifest.example.json`, replace placeholders with exact releases and download dates, and delete the `"template": true` field once the versions are real.

RGI command-line analysis requires CARD reference data even without `--local`. Use `global` mode only after loading CARD into the RGI environment; use `local` mode with `APPAM_SMK_RGI_DB` pointing to a directory prepared by `rgi load --local`.

## Operational notes

- The local SQLite queue is suitable for one APPAM backend process on a small laboratory server.
- Use the Redis/RQ deployment when multiple worker processes or multiple hosts are required.
- `APPAM_MAX_GLOBAL_QUEUED`, `APPAM_MAX_PROJECT_QUEUED`, and `APPAM_MAX_USER_QUEUED` cap queued work; dry runs are included.
- `APPAM_MAX_REQUEST_BYTES` must remain larger than `APPAM_MAX_UPLOAD_CHUNK_BYTES` to allow multipart overhead. The defaults are 17 MiB and 16 MiB; the Web UI uploads 5 MiB chunks.
- URL download state is persisted in SQLite. Incomplete transfers are restored as paused after a restart; terminal history is removed after `APPAM_DOWNLOAD_HISTORY_DAYS` (30 by default).
- Project inputs and run snapshots live under `APPAM_PROJECTS_ROOT`; back up that directory together with `APPAM_DB_PATH`.
- The generated Snakemake profiles activate the exact environment prefixes recorded in each run config.
