# Security policy

## Supported deployment

APPAM is designed for a trusted laboratory server behind HTTPS. Keep the backend API on loopback or a private network and expose only the nginx/Web endpoint. Self-registration is disabled by default; create initial administrators with `backend/manage.py create-admin`. Environment bootstrap remains available for automation, but bootstrap passwords should be removed after first start.

## Important boundaries

- Shell and optional OpenCode access are administrator capabilities. Do not grant administrator roles to untrusted users.
- Remote downloads reject credentials, FTP by default, and source hosts that resolve to non-public addresses. Set `APPAM_REMOTE_DOWNLOAD_HOSTS` to an explicit host allowlist for stricter deployments.
- Project paths are confined to their project workspace, but workflow tools process user-provided scientific files and should run under a dedicated unprivileged OS account.
- The Docker entrypoint drops privileges to `mambauser` after preparing mounts; do not bypass that entrypoint when overriding Compose commands.
- Runtime environment/database/binary overrides and direct arbitrary `mqpar.xml` execution are administrator-only; regular users use server-configured resources and the constrained paleoproteomics workflow.
- SQLite/local queue mode supports one trusted server process. Use an external queue and stronger isolation before scaling to multiple hosts.
- Secrets belong in `.env`/service configuration with restrictive permissions, never in Git or provenance bundles.

## Reporting

Report suspected vulnerabilities privately to the maintainers before public disclosure. Include the affected commit, deployment mode, reproduction steps, and impact. Do not include real samples, credentials, or unpublished research data.
