"""Batch recovery startup and resume tests."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from app.db.models import BatchFile, ScanBatch
from app.services import batch_processor, batch_recovery


@pytest.mark.integration
def test_startup_marks_running_batch_interrupted(db):
    batch = ScanBatch(session_id=1, status="running", progress_pct=50.0)
    db.add(batch)
    db.commit()
    db.refresh(batch)
    db.add(
        BatchFile(
            batch_id=batch.id,
            source_path="/tmp/a.jpg",
            sort_order=0,
            status="processing",
        )
    )
    db.commit()

    count = batch_recovery.recover_batches_on_startup(db)
    assert count == 1
    db.refresh(batch)
    assert batch.status == "interrupted"
    row = db.query(BatchFile).filter(BatchFile.batch_id == batch.id).first()
    assert row.status == "queued"


@pytest.mark.integration
def test_resume_batch_processes_remaining_files(db, make_program, make_session, upload_key_csv, tmp_path):
    program = make_program()
    session = make_session(program_id=program["id"], sheet_question_count=3)
    upload_key_csv(program["id"], session["id"])

    f1 = tmp_path / "a.jpg"
    f2 = tmp_path / "b.jpg"
    f1.write_bytes(b"\xff\xd8\xff\xd9")
    f2.write_bytes(b"\xff\xd8\xff\xe0")

    with patch("app.services.batch_processor.get_config") as cfg:
        cfg.return_value.processing.max_workers = 1
        batch_id = batch_processor.start_batch(session["id"], [str(f1), str(f2)])

        deadline = time.time() + 30
        while time.time() < deadline:
            summary = batch_processor.batch_summary(db, batch_id)
            if not summary["is_running"]:
                break
            time.sleep(0.2)

    summary = batch_processor.batch_summary(db, batch_id)
    assert summary["total_files"] == 2
    assert summary["sheet_count"] == 2
