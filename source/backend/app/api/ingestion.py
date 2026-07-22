"""M07 — Dropzone ingestion control API."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_config
from app.db.session import get_db
from app.services import batch_recovery, program_service
from app.watcher.dropzone import controller

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


class IngestionStart(BaseModel):
    session_id: int
    expected_count: int | None = None


@router.post("/start")
def start(payload: IngestionStart, db: Session = Depends(get_db)):
    try:
        program_service.get_session(db, payload.session_id)
    except program_service.ProgramError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = controller.start(payload.session_id, expected_count=payload.expected_count)
    batch_recovery.save_ingestion_state(
        db,
        active_session_id=payload.session_id,
        expected_count=payload.expected_count,
        watching=True,
    )
    return result


@router.post("/stop")
def stop(db: Session = Depends(get_db)):
    session_id = controller._active_session_id
    expected = controller.expected_count
    controller.stop()
    batch_recovery.save_ingestion_state(
        db,
        active_session_id=session_id,
        expected_count=expected,
        watching=False,
    )
    return controller.status()


@router.get("/status")
def status():
    return controller.status()


@router.post("/flush")
def flush():
    return controller.flush()


@router.post("/upload")
async def upload_scan(file: UploadFile = File(...)):
    """Save a scan into the dropzone folder and ingest it (watching must be active)."""
    if controller._active_session_id is None:
        raise HTTPException(
            status_code=400,
            detail="Start scanning for a session first, then upload or copy files.",
        )

    cfg = get_config()
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in cfg.dropzone.accepted_extensions:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported file type {suffix!r}. "
                f"Use {', '.join(cfg.dropzone.accepted_extensions)}."
            ),
        )

    dropzone = Path(cfg.dropzone.path)
    dropzone.mkdir(parents=True, exist_ok=True)
    safe_stem = Path(file.filename or "scan").stem.replace(" ", "_")[:80]
    dest = dropzone / f"{safe_stem}_{uuid.uuid4().hex[:8]}{suffix}"
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Empty file.")
    dest.write_bytes(data)

    result = controller.handle_file(str(dest))
    if result.get("skipped") == "duplicate":
        raise HTTPException(
            status_code=409,
            detail="This scan was already ingested (duplicate content).",
        )
    if result.get("skipped"):
        raise HTTPException(
            status_code=422,
            detail=f"Scan not ingested: {result.get('skipped')}",
        )
    return {**controller.status(), "file": dest.name, "result": result}
