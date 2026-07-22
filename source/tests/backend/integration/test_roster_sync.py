"""Integration tests for roster scan sync."""

from __future__ import annotations

import json

import pytest

from app.db.models import ExamProgram, ExamSession, ScanBatch, SheetResult, Student, VerificationQueue
from app.omr import roll_number as roll_reader
from app.services import batch_processor, student_service


def _seed_roll_sheet(
    db,
    *,
    program_id: int,
    session_id: int,
    roll_no: str,
    roster_sync_mode: str = "auto",
) -> tuple[ScanBatch, SheetResult]:
    program = db.get(ExamProgram, program_id)
    assert program is not None
    program.roster_sync_mode = roster_sync_mode
    db.flush()

    batch = ScanBatch(session_id=session_id, status="processing")
    db.add(batch)
    db.flush()

    sheet = SheetResult(
        batch_id=batch.id,
        roll_no=roll_no,
        answers_json=json.dumps({"1": "A"}),
        counts_json=json.dumps({"roll_status": roll_reader.ROLL_OK, "answered": 1, "total": 1}),
    )
    db.add(sheet)
    db.flush()
    return batch, sheet


@pytest.mark.integration
def test_auto_mode_creates_student_on_scan(db, make_program, make_session):
    program = make_program("Auto Sync")
    session = make_session(program["id"])
    batch, sheet = _seed_roll_sheet(
        db,
        program_id=program["id"],
        session_id=session["id"],
        roll_no="70001",
        roster_sync_mode="auto",
    )
    exam_session = db.get(ExamSession, session["id"])
    batch_processor._check_roll_roster_and_duplicates(db, sheet, exam_session, batch.id)
    db.commit()

    students = db.query(Student).filter(Student.program_id == program["id"]).all()
    assert len(students) == 1
    assert students[0].roll_no == "70001"
    assert students[0].name == "70001"

    pending = (
        db.query(VerificationQueue)
        .filter(VerificationQueue.sheet_id == sheet.id, VerificationQueue.status == "pending")
        .all()
    )
    assert not any(i.anomaly_type == "roll_unmatched" for i in pending)


@pytest.mark.integration
def test_manual_mode_enqueues_roll_unmatched(db, make_program, make_session):
    program = make_program("Manual Sync")
    session = make_session(program["id"])
    batch, sheet = _seed_roll_sheet(
        db,
        program_id=program["id"],
        session_id=session["id"],
        roll_no="70002",
        roster_sync_mode="manual",
    )
    exam_session = db.get(ExamSession, session["id"])
    batch_processor._check_roll_roster_and_duplicates(db, sheet, exam_session, batch.id)
    db.commit()

    assert db.query(Student).filter(Student.program_id == program["id"]).count() == 0
    item = (
        db.query(VerificationQueue)
        .filter(
            VerificationQueue.sheet_id == sheet.id,
            VerificationQueue.anomaly_type == "roll_unmatched",
        )
        .first()
    )
    assert item is not None


@pytest.mark.integration
def test_resolve_roll_unmatched_adds_to_roster(client, db, make_program, make_session):
    program = make_program("Resolve Sync")
    session = make_session(program["id"])
    batch, sheet = _seed_roll_sheet(
        db,
        program_id=program["id"],
        session_id=session["id"],
        roll_no="70003",
        roster_sync_mode="manual",
    )
    exam_session = db.get(ExamSession, session["id"])
    batch_processor._check_roll_roster_and_duplicates(db, sheet, exam_session, batch.id)
    item = VerificationQueue(
        sheet_id=sheet.id,
        global_question_no=0,
        anomaly_type="roll_unmatched",
        detected_values="70003",
        status="pending",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    res = client.post(
        f"/api/verification/{item.id}/resolve",
        json={
            "action": "confirm",
            "resolved_value": "70003",
            "add_to_roster": True,
            "roster_name": "Student 70003",
        },
    )
    assert res.status_code == 200

    students = client.get(f"/api/programs/{program['id']}/students").json()["students"]
    assert any(s["roll_no"] == "70003" and s["name"] == "Student 70003" for s in students)


@pytest.mark.integration
def test_roster_candidates_and_import(client, seed_scored_sheet):
    seeded = seed_scored_sheet()
    program_id = seeded["program_id"]
    session_id = seeded["session_id"]

    candidates = client.get(
        f"/api/programs/{program_id}/roster/candidates?session_id={session_id}"
    ).json()
    assert candidates["candidates"]
    assert any(c["roll_no"] == "88001" and not c["on_roster"] for c in candidates["candidates"])

    result = client.post(
        f"/api/programs/{program_id}/roster/import-from-session",
        json={"session_id": session_id},
    ).json()
    assert result["created"] == 1

    students = client.get(f"/api/programs/{program_id}/students").json()["students"]
    assert any(s["roll_no"] == "88001" for s in students)

    again = client.post(
        f"/api/programs/{program_id}/roster/import-from-session",
        json={"session_id": session_id, "rolls": ["88001"]},
    ).json()
    assert again["created"] == 0
    assert again["skipped"] == 1


@pytest.mark.integration
def test_auto_add_does_not_overwrite_existing_roster(db, make_program, make_session):
    program = make_program("No Overwrite")
    session = make_session(program["id"])
    student_service.upsert_students(
        db,
        program["id"],
        [("70004", "Original Name", "A", "Morning")],
    )

    batch, sheet = _seed_roll_sheet(
        db,
        program_id=program["id"],
        session_id=session["id"],
        roll_no="70004",
        roster_sync_mode="auto",
    )
    exam_session = db.get(ExamSession, session["id"])
    batch_processor._check_roll_roster_and_duplicates(db, sheet, exam_session, batch.id)
    db.commit()

    student = student_service.find_student(db, program["id"], "70004")
    assert student is not None
    assert student.name == "Original Name"
    assert student.class_section == "A"


@pytest.mark.integration
def test_patch_roster_sync_mode(client, make_program):
    program = make_program("Patch Sync")
    res = client.patch(
        f"/api/programs/{program['id']}",
        json={"roster_sync_mode": "manual"},
    )
    assert res.status_code == 200
    assert res.json()["roster_sync_mode"] == "manual"

    listed = client.get("/api/programs").json()["programs"]
    found = next(p for p in listed if p["id"] == program["id"])
    assert found["roster_sync_mode"] == "manual"


@pytest.mark.integration
def test_pending_roll_item_includes_on_roster(client, db, make_program, make_session):
    program = make_program("On Roster Flag")
    session = make_session(program["id"])
    batch, sheet = _seed_roll_sheet(
        db,
        program_id=program["id"],
        session_id=session["id"],
        roll_no="70005",
        roster_sync_mode="manual",
    )
    item = VerificationQueue(
        sheet_id=sheet.id,
        global_question_no=0,
        anomaly_type="roll_unmatched",
        detected_values="70005",
        status="pending",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    pending = client.get("/api/verification/pending").json()["items"]
    roll_item = next(i for i in pending if i["id"] == item.id)
    assert roll_item["on_roster"] is False
