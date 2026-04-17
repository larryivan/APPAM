# APPAM Docker Layout

This deployment uses two images:

- `appam-tools`
  - Flask API
  - local DB-backed worker
  - terminal / OpenCode integration
  - OpenCode HTTP API
  - APPAM-SMK workflow runtime
  - paleoproteomics runtime dependencies
- `appam-website`
  - built Vue frontend
  - nginx reverse proxy to `tools:19454`

## Start

```bash
docker compose up --build
```

Then open:

- Website: `http://localhost:19453`
- Direct tools API: `http://localhost:19454`
- Direct OpenCode API: `http://localhost:19455`

## Build with a persistent log

For server-side troubleshooting, prefer the build wrapper. It forces plain Docker
progress output and writes the complete build transcript to a timestamped file on
the host:

```bash
./docker/build-tools.sh tools
```

Logs are written under:

- `docker-data/build-logs/`

You can also build multiple services and keep one combined log:

```bash
./docker/build-tools.sh tools website
```

## Persistent host directories

The compose file uses host-mounted directories under `docker-data/` for project files and reference databases:

- `docker-data/projects`
- `docker-data/databases`
- `docker-data/build-logs` (created automatically by the build wrapper)
- `docker-data/runtime-logs`

These map to container paths:

- `/workspaces/projects`
- `/databases`
- `/runtime-logs`

## Runtime crash logs

The tools container writes backend and OpenCode runtime logs to the host at:

- `docker-data/runtime-logs/backend.latest.log`
- `docker-data/runtime-logs/opencode.latest.log`

Each container start also creates timestamped log files in the same directory.
If the backend exits and Docker restarts the container, the last 120 lines of the
backend log are echoed back into `docker compose logs tools` as well.

The application database is stored in a dedicated Docker volume:

- `appam-data` -> `/data`

This keeps deployments clean by default and avoids shipping a pre-populated SQLite file with the repository.

## Important runtime notes

### APPAM-SMK databases

Set these before starting if you want the metagenomics workflow to run immediately:

- `APPAM_SMK_CHECKM_DB`
- `APPAM_SMK_GUNC_DB`

Defaults point inside `/databases`.

### Paleoproteomics MaxQuant

`ThermoRawFileParser`, `timsconvert`, `dotnet`, and `FileConverter` are installed into the tools image.

Bundle the downloaded MaxQuant release in the repository at:

- `vendor/maxquant/MaxQuant_v2.7.5.0/...`

The tools image copies that directory into:

- `/opt/tools/MaxQuant_v2.7.5.0`

and uses this fixed DLL path:

- `/opt/tools/MaxQuant_v2.7.5.0/bin/MaxQuantCmd.dll`

## Fixed in-container paths

These paths are intentionally fixed for container deployment:

- `/opt/appam/backend`
- `/opt/appam/APPAM-SMK-main`
- `/opt/appam/appam-paleoproteomics-main`
- `/opt/tools/MaxQuant_v2.7.5.0`
- `/opt/tools/MaxQuant_v2.7.5.0/bin/MaxQuantCmd.dll`
- `/workspaces/projects`
- `/databases`
- `/data/app_database.db`

## Reset to an empty database

To start with a clean APPAM database on a server:

```bash
docker compose down
docker volume rm appam_appam-data
docker compose up -d --build
```

If you only want to recreate the tools container against a fresh database:

```bash
docker compose rm -sf tools
docker volume rm appam_appam-data
docker compose up -d --build tools
```
