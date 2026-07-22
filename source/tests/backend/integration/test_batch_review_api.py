"""Batch review API integration tests."""

from __future__ import annotations

import json

import pytest

from app.db.models import ExamSession, ScanBatch, SheetResult, VerificationQueue


@pytest.mark.integration
def test_batch_review_groups_by_sheet(client, db, seed_verification_item):
    seeded = seed_verification_item()
    sheet = db.get(SheetResult, seeded["sheet_id"])
    assert sheet is not None

    session = db.get(ExamSession, seeded["session_id"])
    assert session is not None
    db.add(
        VerificationQueue(
            sheet_id=sheet.id,
            global_question_no=session.global_q_start + 1,
            anomaly_type="low_confidence",
            detected_values="A",
            status="pending",
        )
    )
    batch = db.get(ScanBatch, sheet.batch_id)
    batch.status = "needs_verification"
    db.commit()

    res = client.get(f"/api/batches/{sheet.batch_id}/review")
    assert res.status_code == 200
    body = res.json()
    assert body["batch_id"] == sheet.batch_id
    assert body["total_pending"] >= 2
    assert body["sheets_needing_review"] >= 1
    row = next(s for s in body["sheets"] if s["sheet_id"] == sheet.id)
    assert row["roll_no"] == "99001"
    assert row["pending_count"] >= 2
    assert len(row["flags"]) >= 2
    assert len(row["items"]) >= 2


@pytest.mark.integration
def test_batch_review_pending_only_filters(client, db, seed_verification_item):
    seeded = seed_verification_item()
    sheet = db.get(SheetResult, seeded["sheet_id"])
    clean = SheetResult(
        batch_id=sheet.batch_id,
        roll_no="99002",
        answers_json=json.dumps({"1": "B"}),
        counts_json=json.dumps({"aligned": True, "source_file": "clean.jpg"}),
    )
    db.add(clean)
    db.commit()

    all_res = client.get(f"/api/batches/{sheet.batch_id}/review?pending_only=false")
    pending_res = client.get(f"/api/batches/{sheet.batch_id}/review?pending_only=true")
    assert len(all_res.json()["sheets"]) >= len(pending_res.json()["sheets"])
