"""Verification API integration tests."""

from __future__ import annotations

import json

import pytest

from app.db.models import SheetResult, VerificationQueue


@pytest.mark.integration
def test_list_pending_empty(client):
    res = client.get("/api/verification/pending")
    assert res.status_code == 200
    assert isinstance(res.json()["items"], list)


@pytest.mark.integration
def test_resolve_confirm_removes_pending(client, seed_verification_item):
    seeded = seed_verification_item()
    item_id = seeded["item_id"]

    pending = client.get("/api/verification/pending").json()["items"]
    assert any(i["id"] == item_id for i in pending)

    res = client.post(
        f"/api/verification/{item_id}/resolve",
        json={"action": "confirm", "resolved_value": "A"},
    )
    assert res.status_code == 200

    pending_after = client.get("/api/verification/pending").json()["items"]
    assert all(i["id"] != item_id for i in pending_after)


@pytest.mark.integration
def test_resolve_skip(client, seed_verification_item):
    seeded = seed_verification_item()
    res = client.post(
        f"/api/verification/{seeded['item_id']}/resolve",
        json={"action": "skip"},
    )
    assert res.status_code == 200


@pytest.mark.integration
def test_resolve_alignment_review_ack(client, db, seed_verification_item):
    seeded = seed_verification_item()
    item = VerificationQueue(
        sheet_id=seeded["sheet_id"],
        global_question_no=0,
        anomaly_type="alignment_review",
        detected_values="quality 0.61",
        status="pending",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    res = client.post(
        f"/api/verification/{item.id}/resolve",
        json={"action": "confirm"},
    )
    assert res.status_code == 200
    assert res.json()["resolved_value"] == "ACK"
    pending = client.get("/api/verification/pending").json()["items"]
    assert all(i["id"] != item.id for i in pending)


@pytest.mark.integration
def test_resolve_exclude_removes_sheet_from_scores(client, db, seed_verification_item):
    seeded = seed_verification_item()
    sheet = db.get(SheetResult, seeded["sheet_id"])
    assert sheet is not None
    sheet.counts_json = json.dumps({"excluded": False, "source_path": "/tmp/x.jpg"})
    db.commit()

    item = VerificationQueue(
        sheet_id=seeded["sheet_id"],
        global_question_no=0,
        anomaly_type="alignment_failed",
        detected_values="low quality",
        status="pending",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    res = client.post(
        f"/api/verification/{item.id}/resolve",
        json={"action": "exclude", "resolved_by": "test-operator"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["resolved_by"] == "test-operator"
    assert body["resolved_at"] is not None

    scores = client.get(f"/api/sessions/{seeded['session_id']}/scores").json()
    assert scores["sheet_count"] == 0
