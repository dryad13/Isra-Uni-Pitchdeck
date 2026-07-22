"""Sheet detail and source image API."""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.models import SheetResult, VerificationQueue
from app.db.session import get_db
from app.services import scoring
from app.services.sheet_utils import counts_dict, is_scorable

router = APIRouter(tags=["sheets"])


def _guess_media_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "application/octet-stream"


@router.get("/sheets/{sheet_id}")
def get_sheet_detail(sheet_id: int, db: Session = Depends(get_db)):
    sheet = db.get(SheetResult, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found.")

    counts = counts_dict(sheet)
    answers = json.loads(sheet.answers_json) if sheet.answers_json else {}
    scored = None
    if is_scorable(db, sheet):
        scored = scoring.score_sheet(db, sheet)

    verification_items = (
        db.query(VerificationQueue).filter(VerificationQueue.sheet_id == sheet_id).all()
    )

    return {
        "id": sheet.id,
        "batch_id": sheet.batch_id,
        "roll_no": sheet.roll_no,
        "answers": answers,
        "counts": counts,
        "scored": scored,
        "has_source_image": bool(counts.get("source_path")),
        "verification_items": [
            {
                "id": v.id,
                "anomaly_type": v.anomaly_type,
                "status": v.status,
                "detected_values": v.detected_values,
                "resolved_value": v.resolved_value,
                "resolved_by": v.resolved_by,
                "resolved_at": v.resolved_at.isoformat() if v.resolved_at else None,
            }
            for v in verification_items
        ],
    }


@router.get("/sheets/{sheet_id}/source-image")
def get_source_image(sheet_id: int, db: Session = Depends(get_db)):
    sheet = db.get(SheetResult, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found.")
    counts = counts_dict(sheet)
    source_path = counts.get("source_path")
    if not source_path or not Path(source_path).exists():
        raise HTTPException(status_code=404, detail="No source scan image for this sheet.")
    path = Path(source_path)
    return FileResponse(path, media_type=_guess_media_type(path))
