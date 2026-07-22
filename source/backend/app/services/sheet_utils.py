"""Helpers for sheet eligibility in scoring and export."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import SheetResult, VerificationQueue


def counts_dict(sheet: SheetResult) -> dict[str, Any]:
    if not sheet.counts_json:
        return {}
    return json.loads(sheet.counts_json)


def is_excluded(sheet: SheetResult) -> bool:
    return bool(counts_dict(sheet).get("excluded"))


def is_scorable(db: Session, sheet: SheetResult) -> bool:
    """False when excluded or pending alignment failure."""
    if is_excluded(sheet):
        return False
    pending_alignment = (
        db.query(VerificationQueue)
        .filter(
            VerificationQueue.sheet_id == sheet.id,
            VerificationQueue.anomaly_type == "alignment_failed",
            VerificationQueue.status == "pending",
        )
        .first()
    )
    return pending_alignment is None
