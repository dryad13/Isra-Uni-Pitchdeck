"""Sessions API integration tests."""

from __future__ import annotations

import pytest


@pytest.mark.smoke
@pytest.mark.integration
def test_create_session_and_key_status(client, make_program, make_session):
    program = make_program()
    session = make_session(program["id"], sheet_question_count=3)
    assert session["global_q_start"] == 1
    assert session["global_q_end"] == 3

    res = client.get(f"/api/sessions/{session['id']}/key-status")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 3
    assert body["ready"] is False


@pytest.mark.integration
def test_suggest_start(client, make_program, make_session):
    program = make_program()
    make_session(program["id"], name="S1", sheet_question_count=3)
    res = client.get(f"/api/programs/{program['id']}/sessions/suggest-start")
    assert res.status_code == 200
    assert res.json()["global_q_start"] == 4


@pytest.mark.integration
def test_delete_session(client, make_program, make_session):
    program = make_program()
    session = make_session(program["id"])
    res = client.delete(f"/api/sessions/{session['id']}")
    assert res.status_code == 204
    res = client.get(f"/api/programs/{program['id']}/sessions")
    assert all(s["id"] != session["id"] for s in res.json()["sessions"])


@pytest.mark.integration
def test_delete_session_clears_answer_keys_for_recreated_session(client, make_program):
    program = make_program()
    create = client.post(
        f"/api/programs/{program['id']}/sessions",
        json={"name": "S1", "template_family": "150Q", "sheet_question_count": 5},
    )
    assert create.status_code == 201
    session = create.json()
    upsert = client.post(
        f"/api/programs/{program['id']}/answer-keys",
        json={"entries": [{"question_no": i, "correct_option": "B"} for i in range(1, 6)]},
    )
    assert upsert.status_code == 200

    delete = client.delete(f"/api/sessions/{session['id']}")
    assert delete.status_code == 204

    recreate = client.post(
        f"/api/programs/{program['id']}/sessions",
        json={"name": "S2", "template_family": "150Q", "sheet_question_count": 5},
    )
    assert recreate.status_code == 201
    new_session = recreate.json()
    assert new_session["key_complete"] is False

    status = client.get(f"/api/sessions/{new_session['id']}/key-status")
    assert status.status_code == 200
    body = status.json()
    assert body["ready"] is False
    assert body["filled"] == 0
    assert body["keys"] == []


@pytest.mark.integration
def test_create_session_with_150q_scan_layout(client, make_program):
    program = make_program()
    res = client.post(
        f"/api/programs/{program['id']}/sessions",
        json={
            "name": "60 on 150",
            "template_family": "60Q",
            "sheet_question_count": 60,
            "scan_template_family": "150Q",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["template_family"] == "60Q"
    assert body["scan_template_family"] == "150Q"


@pytest.mark.integration
def test_create_session_with_negative_marking(client, make_program):
    program = make_program()
    res = client.post(
        f"/api/programs/{program['id']}/sessions",
        json={
            "name": "Neg Session",
            "template_family": "150Q",
            "sheet_question_count": 5,
            "negative_marking_ratio": 0.25,
        },
    )
    assert res.status_code == 201
    assert res.json()["negative_marking_ratio"] == 0.25
