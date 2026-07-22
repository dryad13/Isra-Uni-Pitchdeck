"""Batch Review — group pending verification items by sheet/roll for operator UI."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import ScanBatch, SheetResult, VerificationQueue
from app.services import batch_processor, sheet_list_service
from app.services.verification_service import item_to_dict

_FLAG_LABELS: dict[str, str] = {
    "alignment_review": "Alignment",
    "alignment_failed": "Alignment failed",
    "roll_ambiguous": "Roll",
    "roll_unmatched": "Unmatched",
    "roll_duplicate": "Duplicate roll",
    "multi": "Multi",
    "low_confidence": "Low confidence",
}


def _flag_label(anomaly_type: str, global_q: int) -> str:
    if anomaly_type in _FLAG_LABELS:
        return _FLAG_LABELS[anomaly_type]
    if global_q > 0:
        return f"Q{global_q}"
    return anomaly_type


def _counts_dict(sheet: SheetResult) -> dict[str, Any]:
    if not sheet.counts_json:
        return {}
    return json.loads(sheet.counts_json)


def _sheet_sort_key(sheet: SheetResult) -> tuple:
    counts = _counts_dict(sheet)
    roll = sheet.roll_no or ""
    source = counts.get("source_file") or ""
    return (roll == "", roll, source, sheet.id)


def _flags_from_items(items: list[VerificationQueue]) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    for item in items:
        entry: dict[str, Any] = {
            "type": item.anomaly_type,
            "label": _flag_label(item.anomaly_type, item.global_question_no),
        }
        if item.global_question_no > 0:
            entry["global_q"] = item.global_question_no
        flags.append(entry)
    return flags


def batch_review(
    db: Session,
    batch_id: int,
    *,
    pending_only: bool = True,
) -> dict[str, Any]:
    batch = db.get(ScanBatch, batch_id)
    if batch is None:
        raise batch_processor.BatchError(f"Batch {batch_id} not found.")

    sheets = (
        db.query(SheetResult).filter(SheetResult.batch_id == batch_id).order_by(SheetResult.id).all()
    )

    total_pending = 0
    sheets_needing_review = 0
    sheet_rows: list[dict[str, Any]] = []

    for sheet in sorted(sheets, key=_sheet_sort_key):
        pending_items = (
            db.query(VerificationQueue)
            .filter(
                VerificationQueue.sheet_id == sheet.id,
                VerificationQueue.status == "pending",
            )
            .order_by(VerificationQueue.id.asc())
            .all()
        )
        pending_count = len(pending_items)
        total_pending += pending_count

        if pending_only and pending_count == 0:
            continue

        if pending_count > 0:
            sheets_needing_review += 1

        counts = _counts_dict(sheet)
        status = sheet_list_service._sheet_status(db, sheet)  # noqa: SLF001

        sheet_rows.append(
            {
                "sheet_id": sheet.id,
                "roll_no": sheet.roll_no,
                "source_file": counts.get("source_file"),
                "alignment_quality": counts.get("alignment_quality"),
                "status": status,
                "pending_count": pending_count,
                "flags": _flags_from_items(pending_items),
                "items": [item_to_dict(db, i) for i in pending_items],
            }
        )

    return {
        "batch_id": batch_id,
        "status": batch.status,
        "total_pending": total_pending,
        "sheets_needing_review": sheets_needing_review,
        "sheets": sheet_rows,
    }
