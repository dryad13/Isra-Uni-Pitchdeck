"""M10 — Verification Workflow service.

Operates on `verification_queue` anomalies (multi-mark, ambiguous roll). Resolving
an item applies the operator override back onto the `SheetResult` (answers / roll),
recomputes counts, and finalizes the batch once nothing is pending.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import ExamSession, ScanBatch, SheetResult, VerificationQueue
from app.omr.bubbles import STATUS_ANSWERED, STATUS_BLANK, STATUS_MULTI
from app.services import student_service

VALID_OPTIONS = {"A", "B", "C", "D", "E"}
BLANK_TOKEN = "BLANK"

ACTION_CONFIRM = "confirm"
ACTION_SKIP = "skip"
ACTION_FLAG = "flag"
ACTION_EXCLUDE = "exclude"

DEFAULT_OPERATOR = "operator"


class VerificationError(ValueError):
    """Raised for invalid verification operations."""


def _status_of(option: str) -> str:
    if option == "":
        return STATUS_BLANK
    if len(option) == 1 and option in VALID_OPTIONS:
        return STATUS_ANSWERED
    return STATUS_MULTI


def _recount(answers: dict[str, str]) -> dict[str, int]:
    counts = {STATUS_ANSWERED: 0, STATUS_BLANK: 0, STATUS_MULTI: 0, "total": 0}
    for option in answers.values():
        counts[_status_of(option)] += 1
        counts["total"] += 1
    return counts


def _session_for_sheet(db: Session, sheet: SheetResult) -> ExamSession | None:
    batch = db.get(ScanBatch, sheet.batch_id)
    if batch is None:
        return None
    return db.get(ExamSession, batch.session_id)


def _sheet_q(db: Session, sheet: SheetResult, global_q: int) -> int | None:
    if global_q <= 0:
        return None
    session = _session_for_sheet(db, sheet)
    if session is None:
        return None
    return global_q - session.global_q_start + 1


def _has_source_image(sheet: SheetResult | None) -> bool:
    if sheet is None or not sheet.counts_json:
        return False
    counts = json.loads(sheet.counts_json)
    path = counts.get("source_path")
    return bool(path)


def item_to_dict(db: Session, item: VerificationQueue) -> dict[str, Any]:
    sheet = db.get(SheetResult, item.sheet_id)
    payload: dict[str, Any] = {
        "id": item.id,
        "sheet_id": item.sheet_id,
        "roll_no": sheet.roll_no if sheet else None,
        "batch_id": sheet.batch_id if sheet else None,
        "anomaly_type": item.anomaly_type,
        "global_question_no": item.global_question_no,
        "sheet_question_no": _sheet_q(db, sheet, item.global_question_no) if sheet else None,
        "detected_values": item.detected_values,
        "resolved_value": item.resolved_value,
        "resolved_by": item.resolved_by,
        "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
        "status": item.status,
        "has_crop": bool(item.crop_path),
        "has_source_image": _has_source_image(sheet),
    }
    if item.anomaly_type in {"roll_ambiguous", "roll_unmatched"} and sheet:
        session = _session_for_sheet(db, sheet)
        roll = sheet.roll_no or item.detected_values or ""
        if session and roll:
            payload["on_roster"] = (
                student_service.find_student(db, session.program_id, roll) is not None
            )
        else:
            payload["on_roster"] = None
    return payload


def list_pending(db: Session, batch_id: int | None = None) -> list[dict[str, Any]]:
    query = db.query(VerificationQueue).filter(VerificationQueue.status == "pending")
    if batch_id is not None:
        query = query.join(SheetResult, VerificationQueue.sheet_id == SheetResult.id).filter(
            SheetResult.batch_id == batch_id
        )
    items = query.order_by(VerificationQueue.id.asc()).all()
    return [item_to_dict(db, i) for i in items]


def get_item(db: Session, item_id: int) -> VerificationQueue:
    item = db.get(VerificationQueue, item_id)
    if item is None:
        raise VerificationError(f"Verification item {item_id} not found.")
    return item


def _normalize_override(item: VerificationQueue, resolved_value: str) -> str:
    value = (resolved_value or "").strip().upper()
    if item.anomaly_type == "roll_ambiguous":
        if not value.isdigit():
            raise VerificationError("Roll override must be digits.")
        return value
    if item.anomaly_type == "roll_unmatched":
        if not value.isdigit():
            raise VerificationError("Roll override must be digits.")
        return value
    # MCQ override
    if value in {"", BLANK_TOKEN, "BLANK"}:
        return BLANK_TOKEN
    if value not in VALID_OPTIONS:
        raise VerificationError(f"Override must be one of {sorted(VALID_OPTIONS)} or BLANK.")
    return value


def _apply_to_sheet(
    db: Session,
    item: VerificationQueue,
    value: str,
    *,
    add_to_roster: bool = True,
    roster_name: str | None = None,
    class_section: str | None = None,
    batch_label: str | None = None,
) -> None:
    sheet = db.get(SheetResult, item.sheet_id)
    if sheet is None:
        return
    if item.anomaly_type in {"roll_ambiguous", "roll_unmatched"}:
        sheet.roll_no = value
        counts = json.loads(sheet.counts_json) if sheet.counts_json else {}
        counts["roll_status"] = "resolved"
        sheet.counts_json = json.dumps(counts)
        session = _session_for_sheet(db, sheet)
        if session and add_to_roster:
            student_service.upsert_roll_from_scan(
                db,
                session.program_id,
                value,
                name=roster_name,
                class_section=class_section,
                batch_label=batch_label,
            )
        return

    if item.anomaly_type in {"alignment_failed", "roll_duplicate", "alignment_review"}:
        return

    answers = json.loads(sheet.answers_json) if sheet.answers_json else {}
    key = str(item.global_question_no)
    answers[key] = "" if value == BLANK_TOKEN else value
    sheet.answers_json = json.dumps(answers)
    counts = json.loads(sheet.counts_json) if sheet.counts_json else {}
    counts.update(_recount(answers))
    sheet.counts_json = json.dumps(counts)


def _exclude_sheet(sheet: SheetResult) -> None:
    counts = json.loads(sheet.counts_json) if sheet.counts_json else {}
    counts["excluded"] = True
    sheet.counts_json = json.dumps(counts)
    sheet.answers_json = json.dumps({})


def _finalize_batch_if_done(db: Session, sheet: SheetResult) -> None:
    db.flush()
    pending = (
        db.query(VerificationQueue)
        .join(SheetResult, VerificationQueue.sheet_id == SheetResult.id)
        .filter(SheetResult.batch_id == sheet.batch_id, VerificationQueue.status == "pending")
        .count()
    )
    if pending == 0:
        batch = db.get(ScanBatch, sheet.batch_id)
        if batch is not None and batch.status == "needs_verification":
            batch.status = "completed"


def resolve(
    db: Session,
    item_id: int,
    action: str,
    resolved_value: str | None = None,
    resolved_by: str | None = None,
    *,
    add_to_roster: bool = True,
    roster_name: str | None = None,
    class_section: str | None = None,
    batch_label: str | None = None,
) -> dict[str, Any]:
    item = get_item(db, item_id)
    if item.status != "pending":
        raise VerificationError(f"Item already {item.status}.")

    operator = resolved_by or DEFAULT_OPERATOR
    now = datetime.utcnow()

    if action == ACTION_EXCLUDE:
        if item.anomaly_type not in {"alignment_failed", "roll_duplicate"}:
            raise VerificationError("Exclude is only valid for alignment or duplicate roll items.")
        sheet = db.get(SheetResult, item.sheet_id)
        if sheet is not None:
            _exclude_sheet(sheet)
        item.resolved_value = "EXCLUDED"
        item.status = "resolved"
        item.resolved_by = operator
        item.resolved_at = now
    elif action == ACTION_CONFIRM:
        ack_types = {"alignment_failed", "roll_duplicate", "alignment_review"}
        if resolved_value is None and item.anomaly_type not in ack_types:
            raise VerificationError("resolved_value required to confirm.")
        if item.anomaly_type == "alignment_review":
            value = "ACK"
            _apply_to_sheet(db, item, value)
        else:
            value = _normalize_override(item, resolved_value or "")
            _apply_to_sheet(
                db,
                item,
                value,
                add_to_roster=add_to_roster,
                roster_name=roster_name,
                class_section=class_section,
                batch_label=batch_label,
            )
        item.resolved_value = value
        item.status = "resolved"
        item.resolved_by = operator
        item.resolved_at = now
    elif action == ACTION_SKIP:
        item.status = "skipped"
        item.resolved_by = operator
        item.resolved_at = now
    elif action == ACTION_FLAG:
        item.status = "flagged"
        item.resolved_by = operator
        item.resolved_at = now
    else:
        raise VerificationError(f"Unknown action {action!r}.")

    sheet = db.get(SheetResult, item.sheet_id)
    if sheet is not None:
        _finalize_batch_if_done(db, sheet)
    db.commit()
    db.refresh(item)
    return item_to_dict(db, item)


def stats(db: Session, batch_id: int | None = None) -> dict[str, Any]:
    query = db.query(VerificationQueue)
    if batch_id is not None:
        query = query.join(SheetResult, VerificationQueue.sheet_id == SheetResult.id).filter(
            SheetResult.batch_id == batch_id
        )
    items = query.all()
    by_status: dict[str, int] = {}
    for i in items:
        by_status[i.status] = by_status.get(i.status, 0) + 1
    return {"total": len(items), "by_status": by_status}
