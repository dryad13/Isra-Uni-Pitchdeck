"""Parallel batch processor integration smoke test."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services import batch_processor


@pytest.mark.integration
def test_batch_runs_with_single_worker(client, db, make_program, make_session, upload_key_csv):
    program = make_program()
    session = make_session(program_id=program["id"], sheet_question_count=3)
    upload_key_csv(program["id"], session["id"])

    import time

    with patch("app.services.batch_processor.get_config") as cfg:
        cfg.return_value.processing.max_workers = 1
        batch_id = batch_processor.start_batch(
            session["id"], ["/nonexistent/a.jpg", "/nonexistent/b.jpg"]
        )

        deadline = time.time() + 30
        while time.time() < deadline:
            summary = batch_processor.batch_summary(db, batch_id)
            if not summary["is_running"]:
                break
            time.sleep(0.2)

    summary = batch_processor.batch_summary(db, batch_id)
    assert summary["sheet_count"] == 2
    assert summary["status"] in {"needs_verification", "completed", "failed"}
