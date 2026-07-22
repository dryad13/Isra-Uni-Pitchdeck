"""Test-only helpers (enabled when OMR_TEST_MODE=1)."""

from __future__ import annotations

import json
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import ScanBatch, SheetResult, VerificationQueue
from app.db.session import get_db
from fastapi import Depends

router = APIRouter(prefix="/test", tags=["test"])


def _require_test_mode() -> None:
    if os.environ.get("OMR_TEST_MODE") != "1":
        raise HTTPException(status_code=404, detail="Not found")


class SeedVerificationRequest(BaseModel):
    session_id: int
    roll_no: str = "99001"
    global_question_no: int | None = None
    anomaly_type: str = "multi_mark"
    detected_values: str = "AB"


class SeedScoredSheetRequest(BaseModel):
    session_id: int
    roll_no: str = "88001"
    answers: dict[str, str] | None = None


@router.post("/seed-verification")
def seed_verification(payload: SeedVerificationRequest, db: Session = Depends(get_db)):
    _require_test_mode()
    from app.services import program_service as svc

    session = svc.get_session(db, payload.session_id)
    global_q = payload.global_question_no or session.global_q_start

    batch = ScanBatch(session_id=session.id, status="needs_verification")
    db.add(batch)
    db.flush()

    answers = {str(i): "A" for i in range(1, session.sheet_question_count + 1)}
    sheet = SheetResult(
        batch_id=batch.id,
        roll_no=payload.roll_no,
        answers_json=json.dumps(answers),
        counts_json=json.dumps({"answered": 1, "blank": 0, "multi": 1, "total": session.sheet_question_count}),
    )
    db.add(sheet)
    db.flush()

    item = VerificationQueue(
        sheet_id=sheet.id,
        global_question_no=global_q,
        anomaly_type=payload.anomaly_type,
        detected_values=payload.detected_values,
        status="pending",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"item_id": item.id, "sheet_id": sheet.id, "batch_id": batch.id}


@router.post("/seed-scored-sheet")
def seed_scored_sheet(payload: SeedScoredSheetRequest, db: Session = Depends(get_db)):
    _require_test_mode()
    from app.services import program_service as svc

    session = svc.get_session(db, payload.session_id)
    answers = payload.answers or {
        str(i): ["A", "B", "C"][i - 1] if i <= 3 else "A"
        for i in range(1, session.sheet_question_count + 1)
    }

    batch = ScanBatch(session_id=session.id, status="done")
    db.add(batch)
    db.flush()
    sheet = SheetResult(
        batch_id=batch.id,
        roll_no=payload.roll_no,
        answers_json=json.dumps(answers),
        counts_json=json.dumps(
            {"answered": len(answers), "blank": 0, "multi": 0, "total": len(answers)}
        ),
    )
    db.add(sheet)
    db.commit()
    db.refresh(sheet)
    return {"sheet_id": sheet.id}
