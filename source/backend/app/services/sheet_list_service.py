"""Session sheet listing for operator tables."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.models import ScanBatch, SheetResult, VerificationQueue
from app.services import scoring
from app.services.program_service import get_session
from app.services.sheet_utils import counts_dict, is_excluded, is_scorable


def _pending_count(db: Session, sheet_id: int) -> int:
    return (
        db.query(VerificationQueue)
        .filter(
            VerificationQueue.sheet_id == sheet_id,
            VerificationQueue.status == "pending",
        )
        .count()
    )


def _sheet_status(db: Session, sheet: SheetResult) -> str:
    counts = counts_dict(sheet)
    if counts.get("excluded"):
        return "excluded"
    if not counts.get("aligned", True):
        return "alignment_failed"
    pending = (
        db.query(VerificationQueue)
        .filter(
            VerificationQueue.sheet_id == sheet.id,
            VerificationQueue.anomaly_type == "alignment_failed",
            VerificationQueue.status == "pending",
        )
        .first()
    )
    if pending:
        return "alignment_failed"
    if _pending_count(db, sheet.id) > 0:
        return "pending_verification"
    if is_scorable(db, sheet):
        return "scored"
    return "excluded"


def _sheet_row(db: Session, sheet: SheetResult, session_id: int) -> dict[str, Any]:
    counts = counts_dict(sheet)
    pending = _pending_count(db, sheet.id)
    status = _sheet_status(db, sheet)
    row: dict[str, Any] = {
        "id": sheet.id,
        "roll_no": sheet.roll_no,
        "batch_id": sheet.batch_id,
        "aligned": bool(counts.get("aligned", True)),
        "pending_verifications": pending,
        "excluded": is_excluded(sheet),
        "status": status,
        "percentage": None,
        "secure_score": None,
        "counts": None,
    }
    if is_scorable(db, sheet):
        scored = scoring.score_sheet(db, sheet)
        row["percentage"] = scored["percentage"]
        row["secure_score"] = scored["secure_score"]
        row["counts"] = scored["counts"]
    else:
        row["counts"] = {
            "correct": 0,
            "wrong": 0,
            "blank": int(counts.get("blank") or 0),
            "multi": int(counts.get("multi") or 0),
            "total": int(counts.get("total") or 0),
        }
    return row


def list_session_sheets(
    db: Session,
    session_id: int,
    search: str | None = None,
    status: str | None = None,
    batch_id: int | None = None,
) -> dict[str, Any]:
    get_session(db, session_id)
    query = (
        db.query(SheetResult)
        .join(ScanBatch, SheetResult.batch_id == ScanBatch.id)
        .filter(ScanBatch.session_id == session_id)
    )
    if batch_id is not None:
        query = query.filter(SheetResult.batch_id == batch_id)
    if search and search.strip():
        query = query.filter(SheetResult.roll_no.like(f"%{search.strip()}%"))
    sheets = query.order_by(SheetResult.id.asc()).all()

    rows = [_sheet_row(db, s, session_id) for s in sheets]
    if status and status.strip():
        rows = [r for r in rows if r["status"] == status.strip()]

    return {
        "session_id": session_id,
        "sheet_count": len(rows),
        "sheets": rows,
    }
