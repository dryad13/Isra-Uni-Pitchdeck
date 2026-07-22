"""Central, frozen-aware filesystem paths.

Resolves resource and writable locations consistently whether the app runs
from source (dev) or from a PyInstaller one-folder bundle (.exe).

Layout assumptions
------------------
Dev (running from source):
    <repo>/config.yaml
    <repo>/samples/
    <repo>/frontend/dist/
    <repo>/backend/omr_engine/
    <repo>/data/                      (writable)

Frozen one-folder bundle (PyInstaller 6.x):
    dist/OMR/OMR.exe
    dist/OMR/_internal/...            -> sys._MEIPASS (read-only resources)
        _internal/config.yaml         (bundled default)
        _internal/samples/
        _internal/frontend/dist/
        _internal/omr_engine/
    dist/OMR/config.yaml             (optional operator override, next to exe)
    dist/OMR/data/                   (writable, created at runtime, next to exe)
"""

import sys
from pathlib import Path

FROZEN: bool = bool(getattr(sys, "frozen", False))

if FROZEN:
    # Bundled, read-only resources are extracted/placed under _MEIPASS.
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS"))
    # Writable data lives next to the executable so it survives re-extraction.
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    # backend/app/paths.py -> repo root is parents[2]
    RESOURCE_DIR = Path(__file__).resolve().parents[2]
    BASE_DIR = RESOURCE_DIR

# --- Read-only resources (bundled) ---------------------------------------
SAMPLES_ROOT = RESOURCE_DIR / "samples"
FRONTEND_DIST = RESOURCE_DIR / "frontend" / "dist"
ENGINE_ROOT = (
    RESOURCE_DIR / "omr_engine" if FROZEN else RESOURCE_DIR / "backend" / "omr_engine"
)

# --- Writable locations (next to exe in frozen mode) ---------------------
DATA_DIR = BASE_DIR / "data"
CROPS_DIR = DATA_DIR / "crops"
PDF_PAGES_DIR = DATA_DIR / "pdf_pages"
BACKUPS_DIR = DATA_DIR / "backups"

# --- Config: prefer an operator-editable file next to the exe ------------
_external_config = BASE_DIR / "config.yaml"
CONFIG_PATH = _external_config if _external_config.exists() else (RESOURCE_DIR / "config.yaml")


def ensure_writable_dirs() -> None:
    """Create writable directories if missing (safe to call repeatedly)."""
    for d in (DATA_DIR, CROPS_DIR, PDF_PAGES_DIR, BACKUPS_DIR):
        d.mkdir(parents=True, exist_ok=True)
