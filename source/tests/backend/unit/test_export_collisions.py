"""Export merge collision detection unit tests."""

from __future__ import annotations

import json

import pytest

from app.db.models import ExamSession, ScanBatch, SheetResult
from app.services import export as export_svc


@pytest.mark.integration
def test_build_program_table_excludes_conflicting_rolls(db, make_program, make_session):
    program = make_program()
    s1 = make_session(program["id"], name="S1", sheet_question_count=3)
    s2 = make_session(program["id"], name="S2", sheet_question_count=3)

    session1 = db.get(ExamSession, s1["id"])
    session2 = db.get(ExamSession, s2["id"])
    assert session1 and session2

    batch1 = ScanBatch(session_id=session1.id, status="done")
    batch2 = ScanBatch(session_id=session2.id, status="done")
    db.add(batch1)
    db.add(batch2)
    db.flush()

    db.add(
        SheetResult(
            batch_id=batch1.id,
            roll_no="777",
            answers_json=json.dumps({"1": "A", "2": "B", "3": "C"}),
            counts_json=json.dumps({"answered": 3, "blank": 0, "multi": 0, "total": 3}),
        )
    )
    db.add(
        SheetResult(
            batch_id=batch2.id,
            roll_no="777",
            answers_json=json.dumps({"1": "A", "2": "X", "3": "C"}),
            counts_json=json.dumps({"answered": 3, "blank": 0, "multi": 0, "total": 3}),
        )
    )
    db.commit()

    rows, _columns, warnings = export_svc.build_program_table(db, program["id"], "literal")
    rolls = [r["roll_no"] for r in rows]
    assert "777" not in rolls
    assert warnings
