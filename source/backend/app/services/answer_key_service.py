"""M06 — Answer Key Manager service.

Maintains the program-level master answer key, built incrementally per session
(FR-1.2 / FR-1.3). Upserts by GLOBAL `question_no`, records an audit trail for
every change, and recomputes session key-completeness so scanning can be gated.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AnswerKey, AnswerKeyAudit, ExamSession
from app.services import program_service
from app.services.answer_key_parser import ALLOWED_OPTIONS

DEFAULT_USER = "operator"


class AnswerKeyError(ValueError):
    """Raised for invalid answer-key operations."""


def _validate_option(option: str) -> str:
    opt = option.strip().upper()
    if opt not in ALLOWED_OPTIONS:
        raise AnswerKeyError(f"Invalid option {option!r} (expected one of {sorted(ALLOWED_OPTIONS)}).")
    return opt


def upsert_keys(
    db: Session,
    program_id: int,
    entries: list[tuple[int, str]],
    changed_by: str | None = None,
    restrict_range: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Insert/update master-key entries; log audit rows; refresh completeness."""
    program_service.get_program(db, program_id)
    user = changed_by or DEFAULT_USER

    if restrict_range is not None:
        lo, hi = restrict_range
        out_of_range = [q for q, _ in entries if q < lo or q > hi]
        if out_of_range:
            raise AnswerKeyError(
                f"Questions {out_of_range[:10]} fall outside the allowed range Q{lo}-Q{hi}."
            )

    created, updated, unchanged = 0, 0, 0
    for question_no, option in entries:
        opt = _validate_option(option)
        existing = (
            db.query(AnswerKey)
            .filter(AnswerKey.program_id == program_id, AnswerKey.question_no == question_no)
            .first()
        )
        if existing is None:
            db.add(
                AnswerKey(
                    program_id=program_id,
                    question_no=question_no,
                    correct_option=opt,
                )
            )
            db.add(
                AnswerKeyAudit(
                    program_id=program_id,
                    question_no=question_no,
                    old_value=None,
                    new_value=opt,
                    changed_by=user,
                )
            )
            created += 1
        elif existing.correct_option != opt:
            db.add(
                AnswerKeyAudit(
                    program_id=program_id,
                    question_no=question_no,
                    old_value=existing.correct_option,
                    new_value=opt,
                    changed_by=user,
                )
            )
            existing.correct_option = opt
            updated += 1
        else:
            unchanged += 1

    db.commit()
    program_service.refresh_key_completeness(db, program_id)
    return {"created": created, "updated": updated, "unchanged": unchanged, "total": len(entries)}


def list_keys(
    db: Session, program_id: int, start: int | None = None, end: int | None = None
) -> list[dict[str, Any]]:
    program_service.get_program(db, program_id)
    query = db.query(AnswerKey).filter(AnswerKey.program_id == program_id)
    if start is not None:
        query = query.filter(AnswerKey.question_no >= start)
    if end is not None:
        query = query.filter(AnswerKey.question_no <= end)
    return [
        {"question_no": k.question_no, "correct_option": k.correct_option}
        for k in query.order_by(AnswerKey.question_no.asc()).all()
    ]


def delete_key(db: Session, program_id: int, question_no: int, changed_by: str | None = None) -> None:
    existing = (
        db.query(AnswerKey)
        .filter(AnswerKey.program_id == program_id, AnswerKey.question_no == question_no)
        .first()
    )
    if existing is None:
        raise AnswerKeyError(f"No key for Q{question_no}.")
    db.add(
        AnswerKeyAudit(
            program_id=program_id,
            question_no=question_no,
            old_value=existing.correct_option,
            new_value=None,
            changed_by=changed_by or DEFAULT_USER,
        )
    )
    db.delete(existing)
    db.commit()
    program_service.refresh_key_completeness(db, program_id)


def list_audit(db: Session, program_id: int, limit: int = 200) -> list[dict[str, Any]]:
    rows = (
        db.query(AnswerKeyAudit)
        .filter(AnswerKeyAudit.program_id == program_id)
        .order_by(AnswerKeyAudit.changed_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "question_no": r.question_no,
            "old_value": r.old_value,
            "new_value": r.new_value,
            "changed_by": r.changed_by,
            "changed_at": r.changed_at.isoformat() if r.changed_at else None,
        }
        for r in rows
    ]


def session_slice_status(db: Session, session_id: int) -> dict[str, Any]:
    """Coverage/readiness for a single session's slice (used to gate scanning)."""
    session = program_service.get_session(db, session_id)
    keys = list_keys(db, session.program_id, session.global_q_start, session.global_q_end)
    covered_set = {k["question_no"] for k in keys}
    total = session.global_q_end - session.global_q_start + 1
    missing = [
        q for q in range(session.global_q_start, session.global_q_end + 1) if q not in covered_set
    ]
    filled = total - len(missing)
    result = {
        "session_id": session.id,
        "global_q_start": session.global_q_start,
        "global_q_end": session.global_q_end,
        "filled": filled,
        "total": total,
        "covered": filled,  # legacy alias
        "missing": missing,
        "ready": len(missing) == 0,
        "keys": keys,
    }
    # #region agent log
    import json
    import time
    from pathlib import Path

    try:
        payload = {
            "sessionId": "cb4b52",
            "timestamp": int(time.time() * 1000),
            "location": "answer_key_service.py:session_slice_status",
            "message": "key status read",
            "data": {
                "session_id": session_id,
                "program_id": session.program_id,
                "global_q_start": session.global_q_start,
                "global_q_end": session.global_q_end,
                "ready": result["ready"],
                "filled": filled,
                "key_sample": keys[:5],
                "key_count": len(keys),
            },
            "hypothesisId": "C,D",
        }
        Path(__file__).resolve().parents[5].joinpath("debug-cb4b52.log").open(
            "a", encoding="utf-8"
        ).write(json.dumps(payload) + "\n")
    except OSError:
        pass
    # #endregion
    return result


def session_range(db: Session, session_id: int) -> tuple[int, int, ExamSession]:
    session = program_service.get_session(db, session_id)
    return session.global_q_start, session.global_q_end, session
