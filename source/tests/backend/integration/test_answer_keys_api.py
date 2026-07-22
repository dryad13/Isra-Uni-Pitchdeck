"""Answer keys API integration tests."""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_manual_upsert_keys(client, make_program, make_session):
    program = make_program()
    session = make_session(program["id"], sheet_question_count=3)
    res = client.post(
        f"/api/programs/{program['id']}/answer-keys",
        json={
            "session_id": session["id"],
            "entries": [
                {"question_no": 1, "correct_option": "A"},
                {"question_no": 2, "correct_option": "B"},
                {"question_no": 3, "correct_option": "C"},
            ],
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["created"] >= 3

    status = client.get(f"/api/sessions/{session['id']}/key-status").json()
    assert status["ready"] is True
    assert status["filled"] == 3


@pytest.mark.integration
def test_upload_csv_keys(client, make_program, make_session, upload_key_csv):
    program = make_program()
    session = make_session(program["id"], sheet_question_count=3)
    upload_key_csv(program["id"], session["id"])
    status = client.get(f"/api/sessions/{session['id']}/key-status").json()
    assert status["ready"] is True
