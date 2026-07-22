"""Programs API integration tests."""

from __future__ import annotations

import pytest


@pytest.mark.smoke
@pytest.mark.integration
def test_create_and_list_program(client, make_program):
    program = make_program("Weekly Test A")
    res = client.get("/api/programs")
    assert res.status_code == 200
    names = [p["name"] for p in res.json()["programs"]]
    assert "Weekly Test A" in names
    assert program["id"] is not None


@pytest.mark.integration
def test_get_program_detail(client, make_program):
    program = make_program("Detail Exam")
    res = client.get(f"/api/programs/{program['id']}")
    assert res.status_code == 200
    body = res.json()
    assert body["program"]["name"] == "Detail Exam"
    assert body["sessions"] == []


@pytest.mark.integration
def test_delete_program(client, make_program):
    program = make_program("To Delete")
    res = client.delete(f"/api/programs/{program['id']}")
    assert res.status_code == 204
    res = client.get(f"/api/programs/{program['id']}")
    assert res.status_code == 404


@pytest.mark.integration
def test_get_missing_program_404(client):
    res = client.get("/api/programs/999999")
    assert res.status_code == 404


@pytest.mark.integration
def test_subject_split_crud(client, make_program):
    program = make_program("Subject Exam")
    create = client.post(
        f"/api/programs/{program['id']}/subjects",
        json={"subject_name": "Physics", "q_start": 1, "q_end": 10},
    )
    assert create.status_code == 201
    split_id = create.json()["id"]

    listed = client.get(f"/api/programs/{program['id']}/subjects").json()
    assert len(listed["subjects"]) == 1
    assert listed["subjects"][0]["subject_name"] == "Physics"

    delete = client.delete(f"/api/programs/subjects/{split_id}")
    assert delete.status_code == 204
    assert client.get(f"/api/programs/{program['id']}/subjects").json()["subjects"] == []
