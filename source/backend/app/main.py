from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.accuracy import router as accuracy_router
from app.api.answer_keys import router as answer_keys_router
from app.api.batches import router as batches_router
from app.api.export import router as export_router
from app.api.health import router as health_router
from app.api.ingestion import router as ingestion_router
from app.api.programs import router as programs_router
from app.api.sessions import router as sessions_router
from app.api.sheets import router as sheets_router
from app.api.students import router as students_router
from app.api.templates import router as templates_router
from app.api.test_helpers import router as test_helpers_router
from app.api.verification import router as verification_router
from app.config import get_config
from app.db.session import SessionLocal, init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from app.paths import ensure_writable_dirs

    ensure_writable_dirs()
    init_db()
    from app.services.batch_recovery import recover_batches_on_startup, recover_ingestion_on_startup
    from app.services.template_service import seed_default_layouts

    db = SessionLocal()
    try:
        seed_default_layouts(db)
        recover_batches_on_startup(db)
        recover_ingestion_on_startup(db)
    finally:
        db.close()

    yield


app = FastAPI(title="On-Premises OMR System", lifespan=lifespan)

cfg = get_config()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(templates_router, prefix="/api")
app.include_router(accuracy_router, prefix="/api")
app.include_router(programs_router, prefix="/api")
app.include_router(sessions_router, prefix="/api")
app.include_router(answer_keys_router, prefix="/api")
app.include_router(batches_router, prefix="/api")
app.include_router(ingestion_router, prefix="/api")
app.include_router(verification_router, prefix="/api")
app.include_router(students_router, prefix="/api")
app.include_router(sheets_router, prefix="/api")
app.include_router(export_router, prefix="/api")
app.include_router(test_helpers_router, prefix="/api")


@app.api_route(
    "/api/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def api_not_found(full_path: str):
    """Return JSON 404 for unknown API paths (avoids StaticFiles 405 on POST)."""
    raise HTTPException(status_code=404, detail=f"API route not found: /api/{full_path}")


frontend_dist = cfg.frontend_dist
if frontend_dist.exists():
    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        """Serve built frontend; unknown paths fall back to index.html for client routing."""
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail=f"API route not found: /{full_path}")
        asset = frontend_dist / full_path
        if asset.is_file():
            return FileResponse(asset)
        index = frontend_dist / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="Not found")
else:
    placeholder = Path(__file__).resolve().parents[1] / "static_placeholder"
    placeholder.mkdir(exist_ok=True)
    index_path = placeholder / "index.html"
    if not index_path.exists():
        index_path.write_text(
            "<!DOCTYPE html><html><body><h1>OMR Platform</h1>"
            "<p>Frontend not built. Run <code>npm run build</code> in frontend/.</p>"
            "</body></html>",
            encoding="utf-8",
        )
    app.mount("/", StaticFiles(directory=str(placeholder), html=True), name="placeholder")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=cfg.server.host,
        port=cfg.server.port,
        reload=True,
    )
