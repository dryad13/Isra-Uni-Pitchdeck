"""Students API integration tests."""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_create_list_delete_students(client, make_program):
    program = make_program()
    res = client.post(
        f"/api/programs/{program['id']}/students",
        json={
            "entries": [
                {"roll_no": "1001", "name": "Alice", "class_section": "A"},
                {"roll_no": "1002", "name": "Bob"},
            ]
        },
    )
    assert res.status_code == 201
    assert res.json()["created"] == 2

    listed = client.get(f"/api/programs/{program['id']}/students").json()
    assert len(listed["students"]) == 2

    search = client.get(f"/api/programs/{program['id']}/students?q=Ali").json()
    assert len(search["students"]) == 1
    assert search["students"][0]["roll_no"] == "1001"

    delete = client.delete(f"/api/programs/{program['id']}/students/1001")
    assert delete.status_code == 204
    assert len(client.get(f"/api/programs/{program['id']}/students").json()["students"]) == 1


@pytest.mark.integration
def test_upload_students_csv(client, make_program):
    program = make_program()
    csv = b"roll_no,name\n2001,Carol\n2002,Dave\n"
    res = client.post(
        f"/api/programs/{program['id']}/students/upload",
        files={"file": ("roster.csv", csv, "text/csv")},
    )
    assert res.status_code == 200
    assert res.json()["created"] == 2
