"""Export and scores API integration tests."""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_scores_empty_session(client, make_program, make_session):
    program = make_program()
    session = make_session(program["id"], sheet_question_count=3)
    res = client.get(f"/api/sessions/{session['id']}/scores")
    assert res.status_code == 200
    body = res.json()
    assert body["sheet_count"] == 0
    assert body["results"] == []


@pytest.mark.integration
def test_scores_with_sheet(client, seed_scored_sheet):
    seeded = seed_scored_sheet()
    res = client.get(f"/api/sessions/{seeded['session_id']}/scores")
    assert res.status_code == 200
    body = res.json()
    assert body["sheet_count"] == 1
    assert body["results"][0]["roll_no"] == "88001"


@pytest.mark.integration
def test_export_csv_headers(client, seed_scored_sheet):
    seeded = seed_scored_sheet()
    res = client.get(
        f"/api/sessions/{seeded['session_id']}/export",
        params={"mode": "literal", "format": "csv"},
    )
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    text = res.text
    assert "roll_no" in text.lower() or "Q1" in text
