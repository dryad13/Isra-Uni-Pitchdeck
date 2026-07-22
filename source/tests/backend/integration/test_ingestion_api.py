"""Ingestion API smoke tests (no file processing in Phase 1)."""

from __future__ import annotations

import pytest


@pytest.mark.smoke
@pytest.mark.integration
def test_ingestion_status_shape(client):
    res = client.get("/api/ingestion/status")
    assert res.status_code == 200
    body = res.json()
    assert "watching" in body
    assert "dropzone_path" in body
    assert "pending_count" in body


@pytest.mark.integration
def test_ingestion_start_stop(client, make_program, make_session):
    program = make_program()
    session = make_session(program["id"], sheet_question_count=3)

    start = client.post("/api/ingestion/start", json={"session_id": session["id"]})
    assert start.status_code == 200

    status = client.get("/api/ingestion/status").json()
    assert status["watching"] is True
    assert status["active_session_id"] == session["id"]

    stop = client.post("/api/ingestion/stop")
    assert stop.status_code == 200
    assert client.get("/api/ingestion/status").json()["watching"] is False


@pytest.mark.integration
def test_ingestion_start_with_expected_count(client, make_program, make_session):
    program = make_program()
    session = make_session(program["id"], sheet_question_count=3)

    start = client.post(
        "/api/ingestion/start",
        json={"session_id": session["id"], "expected_count": 50},
    )
    assert start.status_code == 200
    status = client.get("/api/ingestion/status").json()
    assert status["expected_count"] == 50

    client.post("/api/ingestion/stop")
