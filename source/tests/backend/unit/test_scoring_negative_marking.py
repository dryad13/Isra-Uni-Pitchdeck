"""Negative marking scoring unit tests."""

from __future__ import annotations

import pytest

from app.services import scoring


@pytest.mark.unit
def test_secure_score_without_negative_marking():
    answers = {"1": "A", "2": "B", "3": "C"}
    key = {1: "A", 2: "B", 3: "X"}
    result = scoring.score_answers(answers, key, 1, 3, negative_marking_ratio=0.0)
    assert result["counts"]["correct"] == 2
    assert result["counts"]["wrong"] == 1
    assert result["secure_score"] == pytest.approx(66.67, abs=0.01)


@pytest.mark.unit
def test_secure_score_with_negative_marking():
    answers = {"1": "A", "2": "B", "3": "C"}
    key = {1: "A", 2: "B", 3: "X"}
    result = scoring.score_answers(answers, key, 1, 3, negative_marking_ratio=0.25)
    # net = 2 - 1*0.25 = 1.75; denom = 3
    assert result["secure_score"] == pytest.approx(58.33, abs=0.01)


@pytest.mark.unit
def test_secure_score_never_negative():
    answers = {"1": "X", "2": "X", "3": "X"}
    key = {1: "A", 2: "B", 3: "C"}
    result = scoring.score_answers(answers, key, 1, 3, negative_marking_ratio=1.0)
    assert result["secure_score"] == 0.0
