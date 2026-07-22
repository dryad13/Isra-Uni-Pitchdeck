"""Tests for decoupled scan vs answer-key template families."""

from __future__ import annotations

import pytest

from app.db.models import ExamSession
from app.services import template_service


@pytest.mark.unit
def test_resolve_scan_template_uses_150q_for_mixed_session(db):
    session = ExamSession(
        id=1,
        program_id=1,
        template_family="60Q",
        scan_template_family="150Q",
        session_order=1,
        name="Mixed",
        path_layout_id=None,
        sheet_question_count=60,
        global_q_start=1,
        global_q_end=60,
        key_complete=False,
        negative_marking_ratio=0.0,
    )
    template_dict, family = template_service.resolve_scan_template(db, session)
    assert family == "150Q"
    assert template_dict["fieldBlocks"]["MCQ_Block_1"]["fieldLabels"] == ["q1..30"]

    key_dict, key_family = template_service.resolve_session_template(db, session)
    assert key_family == "60Q"
    assert key_dict["fieldBlocks"]["MCQ_Block_1"]["fieldLabels"] == ["q1..15"]
