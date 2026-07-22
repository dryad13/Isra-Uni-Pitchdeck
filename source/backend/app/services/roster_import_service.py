"""Import roster rolls from processed scan sessions."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ScanBatch, SheetResult, Student
from app.services import program_service, student_service


class RosterImportError(ValueError):
    """Raised for invalid roster import operations."""


def list_candidates(db: Session, program_id: int, session_id: int) -> list[dict]:
    program_service.get_program(db, program_id)
    batches = select(ScanBatch.id).where(ScanBatch.session_id == session_id).scalar_subquery()
    rows = (
        db.query(
            SheetResult.roll_no,
            func.count(SheetResult.id).label("sheet_count"),
            func.max(SheetResult.batch_id).label("last_batch_id"),
        )
        .filter(
            SheetResult.batch_id.in_(batches),
            SheetResult.roll_no.isnot(None),
            SheetResult.roll_no != "",
        )
        .group_by(SheetResult.roll_no)
        .order_by(SheetResult.roll_no.asc())
        .all()
    )
    roster_rolls = {
        s.roll_no
        for s in db.query(Student.roll_no).filter(Student.program_id == program_id).all()
    }
    return [
        {
            "roll_no": roll_no,
            "on_roster": roll_no in roster_rolls,
            "sheet_count": sheet_count,
            "last_batch_id": last_batch_id,
        }
        for roll_no, sheet_count, last_batch_id in rows
    ]


def import_rolls(
    db: Session,
    program_id: int,
    session_id: int,
    rolls: list[str] | None = None,
) -> dict[str, int]:
    candidates = list_candidates(db, program_id, session_id)
    if rolls is None:
        to_import = [c["roll_no"] for c in candidates if not c["on_roster"]]
    else:
        wanted = {r.strip() for r in rolls if r.strip()}
        to_import = [c["roll_no"] for c in candidates if c["roll_no"] in wanted]
    created = 0
    skipped = 0
    for roll in to_import:
        was_created, _ = student_service.upsert_roll_from_scan(db, program_id, roll)
        if was_created:
            created += 1
        else:
            skipped += 1
    db.commit()
    return {"created": created, "skipped": skipped}
