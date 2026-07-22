"""Start uvicorn with isolated test DB and dropzone (Playwright / manual E2E)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
TEST_ROOT = Path(tempfile.mkdtemp(prefix="omr_playwright_"))
DB_PATH = TEST_ROOT / "test.db"
DROPZONE = TEST_ROOT / "dropzone"
DROPZONE.mkdir(parents=True, exist_ok=True)

os.environ["OMR_TEST_MODE"] = "1"
os.environ["OMR_DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["OMR_DROPZONE_PATH"] = str(DROPZONE) + os.sep

import sys

sys.path.insert(0, str(BACKEND))

from app.config import get_config  # noqa: E402
from app.db.session import init_db, reset_engine  # noqa: E402

reset_engine()
init_db()

if __name__ == "__main__":
    import uvicorn

    cfg = get_config()
    port = int(os.environ.get("OMR_TEST_PORT", "18080"))
    uvicorn.run(
        "app.main:app",
        host=cfg.server.host,
        port=port,
        reload=False,
        log_level="warning",
    )
