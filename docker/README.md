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

## Persistent host directories

The compose file uses host-mounted directories under `docker-data/`:

- `docker-data/projects`
- `docker-data/databases`
- `docker-data/app`

These map to container paths:

- `/workspaces/projects`
- `/databases`
- `/data`

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
