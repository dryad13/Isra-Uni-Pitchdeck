"""Batch recovery — startup reconcile and ingestion state persistence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.config import get_config
from app.db.models import BatchFile, IngestionState, ScanBatch


def _file_counts(db: Session, batch_id: int) -> dict[str, int]:
    rows = db.query(BatchFile.status).filter(BatchFile.batch_id == batch_id).all()
    counts = {"queued": 0, "processing": 0, "done": 0, "failed": 0, "cancelled": 0}
    for (status,) in rows:
        counts[status] = counts.get(status, 0) + 1
    counts["total"] = sum(counts.values())
    return counts


def recover_batches_on_startup(db: Session) -> int:
    """Mark orphaned running batches interrupted; reset stale processing files."""
    now = datetime.utcnow()
    recovered = 0
    running = db.query(ScanBatch).filter(ScanBatch.status == "running").all()
    for batch in running:
        batch.status = "interrupted"
        batch.updated_at = now
        db.query(BatchFile).filter(
            BatchFile.batch_id == batch.id,
            BatchFile.status == "processing",
        ).update({"status": "queued", "updated_at": now}, synchronize_session=False)
        recovered += 1
    resuming = db.query(ScanBatch).filter(ScanBatch.status == "resuming").all()
    for batch in resuming:
        batch.status = "interrupted"
        batch.updated_at = now
        db.query(BatchFile).filter(
            BatchFile.batch_id == batch.id,
            BatchFile.status == "processing",
        ).update({"status": "queued", "updated_at": now}, synchronize_session=False)
        recovered += 1
    if recovered:
        db.commit()
    return recovered


def get_ingestion_state(db: Session) -> IngestionState | None:
    return db.get(IngestionState, 1)


def save_ingestion_state(
    db: Session,
    *,
    active_session_id: int | None,
    expected_count: int | None,
    watching: bool,
) -> IngestionState:
    row = db.get(IngestionState, 1)
    if row is None:
        row = IngestionState(id=1)
        db.add(row)
    row.active_session_id = active_session_id
    row.expected_count = expected_count
    row.watching = watching
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


def recover_ingestion_on_startup(db: Session) -> dict | None:
    """Return persisted ingestion state; does not auto-start dropzone."""
    cfg = get_config()
    if not cfg.processing.auto_resume_ingestion:
        return None
    row = get_ingestion_state(db)
    if row is None or not row.watching or row.active_session_id is None:
        return None
    return {
        "active_session_id": row.active_session_id,
        "expected_count": row.expected_count,
        "watching": row.watching,
    }


def batch_file_summary(db: Session, batch_id: int) -> dict[str, int]:
    return _file_counts(db, batch_id)


def can_resume_batch(db: Session, batch: ScanBatch, is_running: bool) -> bool:
    if is_running:
        return False
    if batch.status not in {"interrupted", "running", "resuming"}:
        return False
    counts = _file_counts(db, batch.id)
    return counts["queued"] > 0 or counts["processing"] > 0
