import os
from pathlib import Path


def _resolve_path(env_name: str, default: Path) -> Path:
    raw = os.getenv(env_name, "").strip()
    return Path(raw).resolve() if raw else default.resolve()


REPO_ROOT = _resolve_path(
    "APPAM_REPO_ROOT",
    Path(__file__).resolve().parents[2],
)

BACKEND_ROOT = _resolve_path(
    "APPAM_BACKEND_ROOT",
    REPO_ROOT / "backend",
)

PROJECTS_ROOT = _resolve_path(
    "APPAM_PROJECTS_ROOT",
    BACKEND_ROOT / "projects",
)

DATABASES_ROOT = _resolve_path(
    "APPAM_DATABASES_ROOT",
    REPO_ROOT / "databases",
)

APPAM_SMK_ROOT = _resolve_path(
    "APPAM_SMK_ROOT",
    REPO_ROOT / "APPAM-SMK-main",
)

APPAM_PALEOPROTEOMICS_ROOT = _resolve_path(
    "APPAM_PALEOPROTEOMICS_ROOT",
    REPO_ROOT / "appam-paleoproteomics-main",
)

OPENCODE_ASSETS_ROOT = _resolve_path(
    "APPAM_OPENCODE_ROOT",
    BACKEND_ROOT / "opencode",
)


def ensure_projects_root() -> Path:
    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    return PROJECTS_ROOT


def get_project_dir(project_id: str) -> Path:
    return ensure_projects_root() / str(project_id)


def resolve_project_path(project_id: str, relative_path: str = "") -> Path:
    project_dir = get_project_dir(project_id).resolve()
    candidate = (project_dir / str(relative_path or "").lstrip("/")).resolve()
    if candidate != project_dir and project_dir not in candidate.parents:
        raise ValueError(f"Path escapes project workspace: {relative_path}")
    return candidate
