"""Pytest fixtures with isolated SQLite DB and temp dropzone."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[2] / "backend"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

_test_root = Path(tempfile.mkdtemp(prefix="omr_pytest_"))
os.environ["OMR_TEST_MODE"] = "1"
os.environ["OMR_DATABASE_URL"] = f"sqlite:///{_test_root / 'test.db'}"
os.environ["OMR_DROPZONE_PATH"] = str(_test_root / "dropzone") + os.sep
(_test_root / "dropzone").mkdir(parents=True, exist_ok=True)

from app.db.base import Base  # noqa: E402
from app.db.models import (  # noqa: E402
    ExamProgram,
    ExamSession,
    ScanBatch,
    SheetResult,
    VerificationQueue,
)
from app.db.session import SessionLocal, init_db, reset_engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services import program_service as program_svc  # noqa: E402
from app.services import template_service  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_paths():
    """Ensure test env vars are set once per session."""
    yield


@pytest.fixture(autouse=True)
def _fresh_db():
    reset_engine()
    from app.db import session as session_mod

    assert session_mod.engine is not None
    with session_mod.engine.connect() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
        conn.commit()
    Base.metadata.drop_all(bind=session_mod.engine)
    session_mod.run_migrations()
    db = SessionLocal()
    try:
        template_service.seed_default_layouts(db)
    finally:
        db.close()
    yield


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def make_program(client):
    created_ids: list[int] = []

    def _make(name: str | None = None) -> dict:
        label = name or f"Test Exam {len(created_ids)}"
        res = client.post("/api/programs", json={"name": label})
        assert res.status_code == 201, res.text
        body = res.json()
        created_ids.append(body["id"])
        return body

    yield _make

    for pid in reversed(created_ids):
        client.delete(f"/api/programs/{pid}")


@pytest.fixture()
def make_session(client, make_program):
    def _make(
        program_id: int | None = None,
        *,
        name: str = "Session A",
        sheet_question_count: int = 3,
    ) -> dict:
        pid = program_id or make_program()["id"]
        res = client.post(
            f"/api/programs/{pid}/sessions",
            json={
                "name": name,
                "template_family": "150Q",
                "sheet_question_count": sheet_question_count,
            },
        )
        assert res.status_code == 201, res.text
        return res.json()

    return _make


@pytest.fixture()
def test_key_path() -> Path:
    return FIXTURES / "test_key.csv"


@pytest.fixture()
def upload_key_csv(client, test_key_path):
    def _upload(program_id: int, session_id: int) -> dict:
        with test_key_path.open("rb") as fh:
            res = client.post(
                f"/api/programs/{program_id}/answer-keys/upload",
                files={"file": ("test_key.csv", fh, "text/csv")},
                data={"session_id": str(session_id)},
            )
        assert res.status_code == 200, res.text
        return res.json()

    return _upload


@pytest.fixture()
def seed_verification_item(db, make_program, make_session):
    """Create a pending verification queue item for integration tests."""

    def _seed(program_id: int | None = None, session_id: int | None = None) -> dict:
        if program_id is None:
            program = program_svc.create_program(db, f"Verify Prog {session_id}")
            program_id = program.id
            db.commit()
        if session_id is None:
            session = program_svc.create_session(
                db,
                program_id=program_id,
                name="Verify Session",
                template_family="150Q",
                sheet_question_count=3,
            )
            session_id = session.id
            db.commit()

        session = db.get(ExamSession, session_id)
        assert session is not None

        batch = ScanBatch(session_id=session_id, status="processing")
        db.add(batch)
        db.flush()

        answers = {str(i): "A" for i in range(1, session.sheet_question_count + 1)}
        answers["2"] = "AB"
        sheet = SheetResult(
            batch_id=batch.id,
            roll_no="99001",
            answers_json=json.dumps(answers),
            counts_json=json.dumps({"answered": 2, "blank": 0, "multi": 1, "total": 3}),
        )
        db.add(sheet)
        db.flush()

        item = VerificationQueue(
            sheet_id=sheet.id,
            global_question_no=session.global_q_start + 1,
            anomaly_type="multi_mark",
            detected_values="AB",
            status="pending",
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return {
            "program_id": program_id,
            "session_id": session_id,
            "item_id": item.id,
            "sheet_id": sheet.id,
        }

    return _seed


@pytest.fixture()
def seed_scored_sheet(db, make_program, make_session, upload_key_csv, client):
    """Session with answer key + one scored sheet for export tests."""

    def _seed() -> dict:
        program = make_program()
        session = make_session(program["id"])
        upload_key_csv(program["id"], session["id"])

        batch = ScanBatch(session_id=session["id"], status="done")
        db.add(batch)
        db.flush()
        answers = {"1": "A", "2": "B", "3": "C"}
        sheet = SheetResult(
            batch_id=batch.id,
            roll_no="88001",
            answers_json=json.dumps(answers),
            counts_json=json.dumps({"answered": 3, "blank": 0, "multi": 0, "total": 3}),
        )
        db.add(sheet)
        db.commit()
        return {
            "program_id": program["id"],
            "session_id": session["id"],
            "sheet_id": sheet.id,
        }

    return _seed
