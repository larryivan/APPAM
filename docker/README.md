# APPAM Docker deployment

Compose builds a tools/backend image and a separate nginx/Vue image. The public Web port defaults to `25078` and can be set with `APPAM_WEB_PORT`. The backend API defaults to host loopback port `25079`; nginx proxies `/api/` and `/socket.io/` over the Compose network.

## First start

Create `.env` beside `docker-compose.yml`:

```dotenv
FLASK_SECRET_KEY=replace-with-output-of-openssl-rand-hex-32
APPAM_WEB_PORT=25078
APPAM_ALLOWED_ORIGINS=http://SERVER_NAME_OR_IP:25078
APPAM_HOST_DB_ROOT=/home/adna/db
APPAM_HOST_MAXQUANT_ROOT=/home/adna/MaxQuant_v2.8.1.0
```

Then run:

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 tools website
```

Open `http://SERVER_NAME_OR_IP:25078`. Port `19455` is not published; OpenCode is optional, loopback-only inside the tools container, and starts only if its executable is supplied.

Create the first administrator with a hidden password prompt:

```bash
docker compose exec tools micromamba run -n backend \
  python /opt/appam/backend/manage.py create-admin --username labadmin
```

For unattended provisioning, `APPAM_BOOTSTRAP_ADMINS_JSON` is still supported.

## Persistent data

- `appam-data` volume: SQLite application database.
- `docker-data/projects`: project files, run snapshots, outputs, and provenance.
- `APPAM_HOST_DB_ROOT`: read-only database mount at `/databases`.
- `APPAM_HOST_MAXQUANT_ROOT`: read-only MaxQuant release mounted at `/opt/tools/maxquant-current`.
- `docker-data/runtime-logs`: backend logs.

Back up the application volume and project directory together.

The container entrypoint uses root only to prepare mounted directories and then drops to `mambauser` before starting APPAM or any analysis process. When upgrading a deployment that previously wrote project files as root, start once with `APPAM_FIX_PROJECT_OWNERSHIP=true`; this recursively changes ownership and can take time on large projects, so remove the setting after the migration.

## Database mount

Expected defaults under the host database root are:

```text
checkm2/
gunc/
eggnog/
gtdbtk_r226/
krakenuniq_refseq_bav/
```

`checkm/` is optional unless CheckM1 or MetaWRAP refinement is enabled; KrakenUniq is optional when that advanced tool is unused. Copy `docker/database-manifest.example.json` to `appam-db-manifest.json` under the database root, record exact versions/download dates, and delete the `"template": true` field. Publication checks reject the unmodified example.

RGI command-line runs always require CARD reference data. Keep `APPAM_SMK_RGI_DB_MODE=global` only when CARD has been loaded into the RGI environment; for a directory prepared with `rgi load --local`, set mode `local`, configure `APPAM_SMK_RGI_DB`, and record the CARD release.

## MaxQuant

Point `APPAM_HOST_MAXQUANT_ROOT` at the release directory that directly contains `bin/MaxQuantCmd.dll`, for example:

```text
/home/adna/MaxQuant_v2.8.1.0/bin/MaxQuantCmd.dll
```

Compose mounts that directory read-only at `/opt/tools/maxquant-current`; MaxQuant itself is not copied into the Git repository or Docker image.

## Queue modes

The default `local-db` queue is intended for one small-laboratory server and one backend process. For Redis/RQ:

```bash
APPAM_QUEUE_BACKEND=rq docker compose --profile rq up -d
```

Keep project, database, and environment mounts identical between the API and worker.
Queued jobs, including dry runs, are capped by `APPAM_MAX_GLOBAL_QUEUED`,
`APPAM_MAX_PROJECT_QUEUED`, and `APPAM_MAX_USER_QUEUED`. Worker count controls execution
concurrency; the default deployment runs one worker so laboratory jobs execute serially.

## Diagnostics

```bash
FLASK_SECRET_KEY=test docker compose config --quiet
docker compose ps
docker compose logs -f tools
curl -fsS http://127.0.0.1:25079/api/health
```

The direct API host port can be changed with `APPAM_API_PORT`, but remains bound to `127.0.0.1`.

For an LXC host that denies nested container sysctls/mounts, use `deploy/native/README.md` instead of weakening the host runtime.
