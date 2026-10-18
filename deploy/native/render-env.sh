#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
# shellcheck source=deploy/native/common.sh
source "${SCRIPT_DIR}/common.sh"
OUTPUT="${SCRIPT_DIR}/appam.env"
DB_ROOT="${HOME}/db"
PROJECTS_ROOT="${HOME}/appam-data/projects"
WEB_ORIGIN="http://127.0.0.1:25078"
PUBLIC_BASE_PATH=""
MAXQUANT_ROOT="${HOME}/MaxQuant_v2.8.1.0"
ENV_RUNNER="${APPAM_ENV_RUNNER:-mamba}"

usage() {
  cat <<'EOF'
Usage: render-env.sh [options]
  --output FILE          Output environment file
  --db-root DIR          Database root (default: ~/db)
  --projects-root DIR    Project data root
  --web-origin URL       Public Web origin (comma-separate several)
  --public-base-path P   URL prefix the UI is served under, e.g. a gateway path
  --maxquant-root DIR    MaxQuant release directory
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) OUTPUT="$2"; shift ;;
    --db-root) DB_ROOT="$2"; shift ;;
    --projects-root) PROJECTS_ROOT="$2"; shift ;;
    --web-origin) WEB_ORIGIN="$2"; shift ;;
    --public-base-path) PUBLIC_BASE_PATH="$2"; shift ;;
    --maxquant-root) MAXQUANT_ROOT="$2"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if ! ENV_RUNNER_BIN="$(command -v "${ENV_RUNNER}")"; then
  printf 'Environment runner not found: %s\n' "${ENV_RUNNER}" >&2
  exit 1
fi
CONDA_BASE="$(resolve_environment_base "${ENV_RUNNER_BIN}")"
ENV_ROOT="${CONDA_BASE}/envs"
GTDBTK_DB="${DB_ROOT}/gtdbtk_r226"
if [[ -d "${GTDBTK_DB}/release226" ]]; then
  GTDBTK_DB="${GTDBTK_DB}/release226"
fi
SECRET="$(openssl rand -hex 32)"
mkdir -p "$(dirname "${OUTPUT}")" "${PROJECTS_ROOT}" "${HOME}/appam-data"

cat >"${OUTPUT}" <<EOF
FLASK_DEBUG=false
FLASK_HOST=127.0.0.1
FLASK_PORT=25079
FLASK_SECRET_KEY=${SECRET}
APPAM_ALLOWED_ORIGINS=${WEB_ORIGIN}
APPAM_PUBLIC_BASE_PATH=${PUBLIC_BASE_PATH}
APPAM_TRUST_PROXY_HEADERS=true
APPAM_ALLOW_REGISTRATION=false
APPAM_ALLOW_FIRST_USER_ADMIN=false
APPAM_BOOTSTRAP_ADMINS_JSON=
APPAM_REPO_ROOT=${REPO_ROOT}
APPAM_BACKEND_ROOT=${REPO_ROOT}/backend
APPAM_PROJECTS_ROOT=${PROJECTS_ROOT}
APPAM_DATABASES_ROOT=${DB_ROOT}
APPAM_DB_MANIFEST=${DB_ROOT}/appam-db-manifest.json
APPAM_DB_PATH=${HOME}/appam-data/app_database.db
APPAM_QUEUE_BACKEND=local-db
APPAM_DISABLE_EMBEDDED_WORKER=false
APPAM_MAX_GLOBAL_QUEUED=100
APPAM_MAX_PROJECT_QUEUED=10
APPAM_MAX_USER_QUEUED=10
APPAM_ALLOW_RUNTIME_DRIFT_ON_RETRY=false
SOCKETIO_ASYNC_MODE=threading
APPAM_GUNICORN_THREADS=32
APPAM_GUNICORN_TIMEOUT=120
APPAM_GUNICORN_GRACEFUL_TIMEOUT=30
APPAM_SNAKEMAKE_BIN=${ENV_ROOT}/appam-backend/bin/snakemake
APPAM_SMK_ROOT=${REPO_ROOT}/APPAM-SMK-main
APPAM_PALEOPROTEOMICS_ROOT=${REPO_ROOT}/appam-paleoproteomics-main
APPAM_PALEO_ENV=${ENV_ROOT}/paleoproteomics
APPAM_PALEO_TIMSCONVERT_ENV=${ENV_ROOT}/timsconvert
APPAM_ENV_RUNNER=${ENV_RUNNER_BIN}
APPAM_METAWRAP_ROOT=${HOME}/.local/share/appam/metaWRAP
APPAM_SMK_PREPROCESSING_ENV=${ENV_ROOT}/preprocessing
APPAM_SMK_MAPPING_ENV=${ENV_ROOT}/mapping_dna
APPAM_SMK_ASSEMBLY_ENV=${ENV_ROOT}/assembly
APPAM_SMK_METAWRAP_ENV=${ENV_ROOT}/metawrap
APPAM_SMK_PYDAMAGE_ENV=${ENV_ROOT}/ancient_dna
APPAM_SMK_CHECKM1_ENV=${ENV_ROOT}/checkm
APPAM_SMK_CHECKM2_ENV=${ENV_ROOT}/checkm2
APPAM_SMK_GUNC_ENV=${ENV_ROOT}/binning
APPAM_SMK_GTDBTK_ENV=${ENV_ROOT}/gtdbtk
APPAM_SMK_PROKKA_ENV=${ENV_ROOT}/prokka
APPAM_SMK_EGGNOG_ENV=${ENV_ROOT}/eggnog_py310
APPAM_SMK_ABRICATE_ENV=${ENV_ROOT}/abricate
APPAM_SMK_RGI_ENV=${ENV_ROOT}/rgi
APPAM_SMK_ANTISMASH_ENV=${ENV_ROOT}/antismash
APPAM_SMK_FREEBAYES_ENV=${ENV_ROOT}/freebayes
APPAM_SMK_BCFTOOLS_ENV=${ENV_ROOT}/bcftools
APPAM_SMK_REPORTING_ENV=${ENV_ROOT}/reporting
APPAM_SMK_CHECKM1_DB=${DB_ROOT}/checkm
APPAM_SMK_CHECKM2_DB=${DB_ROOT}/checkm2
APPAM_SMK_GUNC_DB=${DB_ROOT}/gunc
APPAM_SMK_GTDBTK_DB=${GTDBTK_DB}
APPAM_SMK_EGGNOG_DB=${DB_ROOT}/eggnog
APPAM_KRAKENUNIQ_DB=${DB_ROOT}/krakenuniq_refseq_bav
APPAM_KRAKENUNIQ_KDB=${DB_ROOT}/krakenuniq_refseq_bav/database.kdb
APPAM_KRAKENUNIQ_IDX=${DB_ROOT}/krakenuniq_refseq_bav/database.idx
APPAM_KRAKENUNIQ_TAXDB=${DB_ROOT}/krakenuniq_refseq_bav/taxDB
APPAM_SMK_RGI_DB_MODE=global
APPAM_PALEO_DOTNET_BIN=${ENV_ROOT}/paleoproteomics/lib/dotnet/dotnet
APPAM_PALEO_MAXQUANT_CMD=${MAXQUANT_ROOT}/bin/MaxQuantCmd.dll
APPAM_PALEO_MAXQUANT_VERSION=2.8.1.0
APPAM_PALEO_THERMO_RAW_FILE_PARSER=${HOME}/.local/bin/ThermoRawFileParser
APPAM_PALEO_TIMSCONVERT_BIN=${HOME}/.local/bin/appam-timsconvert
APPAM_PALEO_OPENMS_FILECONVERTER=${ENV_ROOT}/paleoproteomics/bin/FileConverter
APPAM_ALLOW_FTP_DOWNLOADS=false
APPAM_REMOTE_DOWNLOAD_HOSTS=
APPAM_MAX_REMOTE_DOWNLOAD_BYTES=107374182400
APPAM_MAX_GLOBAL_DOWNLOADS=8
APPAM_MAX_PROJECT_DOWNLOADS=2
APPAM_MAX_DOWNLOAD_THREADS=8
APPAM_DOWNLOAD_HISTORY_DAYS=30
APPAM_MAX_UPLOAD_CHUNK_BYTES=16777216
APPAM_MAX_UPLOAD_CHUNKS=20000
APPAM_MAX_PLOT_TABLE_BYTES=8388608
APPAM_MAX_PLOT_TABLE_ROWS=50000
APPAM_MAX_REQUEST_BYTES=17825792
EOF

chmod 0600 "${OUTPUT}"
printf 'Wrote %s\n' "${OUTPUT}"
printf 'Next: %s/manage.sh create-admin --username labadmin\n' "${SCRIPT_DIR}"
