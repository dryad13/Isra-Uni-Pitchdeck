"""M10 — Verification Workflow API (queue, crop viewer, override)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import verification_service as svc

router = APIRouter(tags=["verification"])


class ResolveRequest(BaseModel):
    action: str  # confirm | skip | flag | exclude
    resolved_value: str | None = None
    resolved_by: str | None = None
    add_to_roster: bool = True
    roster_name: str | None = None
    class_section: str | None = None
    batch_label: str | None = None


@router.get("/verification/pending")
def list_pending(batch_id: int | None = None, db: Session = Depends(get_db)):
    return {"items": svc.list_pending(db, batch_id)}


@router.get("/verification/stats")
def get_stats(batch_id: int | None = None, db: Session = Depends(get_db)):
    return svc.stats(db, batch_id)


@router.get("/verification/{item_id}")
def get_item(item_id: int, db: Session = Depends(get_db)):
    try:
        item = svc.get_item(db, item_id)
    except svc.VerificationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return svc.item_to_dict(db, item)


@router.get("/verification/{item_id}/crop")
def get_crop(item_id: int, db: Session = Depends(get_db)):
    try:
        item = svc.get_item(db, item_id)
    except svc.VerificationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not item.crop_path or not Path(item.crop_path).exists():
        raise HTTPException(status_code=404, detail="No crop image for this item.")
    return FileResponse(item.crop_path, media_type="image/png")


@router.post("/verification/{item_id}/resolve")
def resolve(item_id: int, payload: ResolveRequest, db: Session = Depends(get_db)):
    try:
        return svc.resolve(
            db,
            item_id,
            payload.action,
            payload.resolved_value,
            payload.resolved_by,
            add_to_roster=payload.add_to_roster,
            roster_name=payload.roster_name,
            class_section=payload.class_section,
            batch_label=payload.batch_label,
        )
    except svc.VerificationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
