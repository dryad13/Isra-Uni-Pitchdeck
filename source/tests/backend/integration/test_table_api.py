"""Integration tests for list/table API endpoints."""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_programs_list_with_stats(client, make_program, make_session):
    program = make_program("Stats Exam")
    make_session(program_id=program["id"])

    res = client.get("/api/programs?include=stats")
    assert res.status_code == 200
    programs = res.json()["programs"]
    found = next(p for p in programs if p["id"] == program["id"])
    assert found["session_count"] == 1
    assert found["student_count"] == 0
    assert found["sheet_count"] == 0

    search = client.get("/api/programs?q=Stats").json()
    assert any(p["id"] == program["id"] for p in search["programs"])


@pytest.mark.integration
def test_students_class_batch_filters(client, make_program):
    program = make_program()
    client.post(
        f"/api/programs/{program['id']}/students",
        json={
            "entries": [
                {"roll_no": "3001", "name": "Eve", "class_section": "B", "batch_label": "Morning"},
                {"roll_no": "3002", "name": "Frank", "class_section": "A", "batch_label": "Evening"},
            ]
        },
    )
    by_class = client.get(
        f"/api/programs/{program['id']}/students?class_section=B"
    ).json()
    assert len(by_class["students"]) == 1
    assert by_class["students"][0]["roll_no"] == "3001"

    by_batch = client.get(
        f"/api/programs/{program['id']}/students?batch_label=Evening"
    ).json()
    assert len(by_batch["students"]) == 1
    assert by_batch["students"][0]["roll_no"] == "3002"


@pytest.mark.integration
def test_session_sheets_and_program_scores(client, seed_scored_sheet):
    seeded = seed_scored_sheet()
    session_id = seeded["session_id"]
    program_id = seeded["program_id"]
    sheet_id = seeded["sheet_id"]

    sheets = client.get(f"/api/sessions/{session_id}/sheets").json()
    assert sheets["sheet_count"] >= 1
    assert any(s["id"] == sheet_id for s in sheets["sheets"])

    filtered = client.get(
        f"/api/sessions/{session_id}/sheets?q=88001&status=scored"
    ).json()
    assert filtered["sheet_count"] >= 1

    scores = client.get(f"/api/programs/{program_id}/scores").json()
    assert scores["sheet_count"] >= 1
    assert any(r["roll_no"] == "88001" for r in scores["results"])
