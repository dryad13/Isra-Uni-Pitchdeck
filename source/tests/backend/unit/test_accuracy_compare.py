"""Unit tests for accuracy reference comparison."""

from __future__ import annotations

from app.services.accuracy_service import compare_to_reference


def test_compare_all_match():
    questions = [
        {"sheet_q": 1, "detected": "A", "status": "answered"},
        {"sheet_q": 2, "detected": "B", "status": "answered"},
    ]
    reference = {"answers": {"1": "A", "2": "B"}, "roll_no": "123456"}
    enriched, summary = compare_to_reference(questions, "123456", reference)

    assert summary["accuracy_pct"] == 100.0
    assert summary["matched"] == 2
    assert summary["roll_match"] is True
    assert all(q["match"] is True for q in enriched)


def test_compare_mismatch_and_roll():
    questions = [
        {"sheet_q": 1, "detected": "C", "status": "answered"},
        {"sheet_q": 2, "detected": "", "status": "blank"},
    ]
    reference = {"answers": {"1": "A", "2": "B"}, "roll_no": "111111"}
    enriched, summary = compare_to_reference(questions, "222222", reference)

    assert summary["accuracy_pct"] == 0.0
    assert summary["mismatches"] == 2
    assert summary["roll_match"] is False
    assert enriched[0]["match"] is False
    assert enriched[1]["match"] is False


def test_compare_without_reference():
    questions = [{"sheet_q": 1, "detected": "A", "status": "answered"}]
    enriched, summary = compare_to_reference(questions, "123", None)

    assert summary["accuracy_pct"] is None
    assert summary["roll_match"] is None
    assert enriched[0]["match"] is None
    assert enriched[0]["reference"] is None
