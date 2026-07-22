"""Alembic migration smoke test."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect

from app.db import session as session_mod


@pytest.mark.smoke
@pytest.mark.integration
def test_alembic_upgrade_creates_core_tables():
    assert session_mod.engine is not None
    inspector = inspect(session_mod.engine)
    tables = set(inspector.get_table_names())
    for name in (
        "exam_programs",
        "exam_sessions",
        "students",
        "verification_queue",
        "scan_batches",
        "sheet_results",
    ):
        assert name in tables

    cols = {c["name"] for c in inspector.get_columns("exam_sessions")}
    assert "negative_marking_ratio" in cols

    vq_cols = {c["name"] for c in inspector.get_columns("verification_queue")}
    assert "resolved_by" in vq_cols
    assert "resolved_at" in vq_cols

    batch_cols = {c["name"] for c in inspector.get_columns("scan_batches")}
    assert "expected_count" in batch_cols
