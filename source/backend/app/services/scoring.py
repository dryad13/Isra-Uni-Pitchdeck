"""M11 — Scoring Engine.

Scores read answers against the program master answer key:
  * per-question: correct / wrong / blank / multi
  * Percentage      = correct / session_question_count * 100
  * Secure Score    = (correct - wrong * negative_marking_ratio) / (total - blank - multi) * 100
  * optional subject-split sub-scores (global ranges intersected with the session)
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import (
    AnswerKey,
    ExamSession,
    ScanBatch,
    SheetResult,
    SubjectSplit,
)
from app.services.sheet_utils import is_scorable

STATUS_CORRECT = "correct"
STATUS_WRONG = "wrong"
STATUS_BLANK = "blank"
STATUS_MULTI = "multi"

VALID_OPTIONS = {"A", "B", "C", "D", "E"}


class ScoringError(ValueError):
    """Raised for invalid scoring requests."""


def program_key(db: Session, program_id: int) -> dict[int, str]:
    rows = db.query(AnswerKey).filter(AnswerKey.program_id == program_id).all()
    return {r.question_no: r.correct_option for r in rows}


def _question_status(option: str, key_option: str | None) -> str:
    if option == "":
        return STATUS_BLANK
    if len(option) > 1 or option not in VALID_OPTIONS:
        return STATUS_MULTI
    if key_option is not None and option == key_option:
        return STATUS_CORRECT
    return STATUS_WRONG


def score_answers(
    answers: dict[str, str],
    key: dict[int, str],
    q_start: int,
    q_end: int,
    negative_marking_ratio: float = 0.0,
) -> dict[str, Any]:
    """Score a single sheet's answers over [q_start, q_end] (global numbering)."""
    per_question: list[dict[str, Any]] = []
    counts = {STATUS_CORRECT: 0, STATUS_WRONG: 0, STATUS_BLANK: 0, STATUS_MULTI: 0}
    total = q_end - q_start + 1

    for global_q in range(q_start, q_end + 1):
        option = answers.get(str(global_q), "")
        key_option = key.get(global_q)
        status = _question_status(option, key_option)
        counts[status] += 1
        per_question.append(
            {
                "global_q": global_q,
                "sheet_q": global_q - q_start + 1,
                "option": option,
                "key": key_option,
                "status": status,
            }
        )

    correct = counts[STATUS_CORRECT]
    percentage = round(correct / total * 100, 2) if total > 0 else 0.0
    denom = total - counts[STATUS_BLANK] - counts[STATUS_MULTI]
    net = correct - (counts[STATUS_WRONG] * negative_marking_ratio)
    secure = round(max(0.0, net) / denom * 100, 2) if denom > 0 else 0.0

    return {
        "counts": {**counts, "total": total},
        "percentage": percentage,
        "secure_score": secure,
        "per_question": per_question,
    }


def subject_scores(
    per_question: list[dict[str, Any]],
    subjects: list[SubjectSplit],
) -> list[dict[str, Any]]:
    """Per-subject correct/total over the questions present in this scoring run."""
    by_global = {q["global_q"]: q for q in per_question}
    out = []
    for subject in subjects:
        correct = total = 0
        for gq in range(subject.q_start, subject.q_end + 1):
            q = by_global.get(gq)
            if q is None:
                continue
            total += 1
            if q["status"] == STATUS_CORRECT:
                correct += 1
        out.append(
            {
                "subject_name": subject.subject_name,
                "q_start": subject.q_start,
                "q_end": subject.q_end,
                "correct": correct,
                "total": total,
                "percentage": round(correct / total * 100, 2) if total > 0 else 0.0,
            }
        )
    return out


def _session_of(db: Session, sheet: SheetResult) -> ExamSession:
    batch = db.get(ScanBatch, sheet.batch_id)
    if batch is None:
        raise ScoringError(f"Batch for sheet {sheet.id} not found.")
    session = db.get(ExamSession, batch.session_id)
    if session is None:
        raise ScoringError(f"Session for sheet {sheet.id} not found.")
    return session


def score_sheet(
    db: Session,
    sheet: SheetResult,
    key: dict[int, str] | None = None,
    subjects: list[SubjectSplit] | None = None,
    negative_marking_ratio: float | None = None,
) -> dict[str, Any]:
    session = _session_of(db, sheet)
    if key is None:
        key = program_key(db, session.program_id)
    ratio = (
        negative_marking_ratio
        if negative_marking_ratio is not None
        else session.negative_marking_ratio
    )
    answers = json.loads(sheet.answers_json) if sheet.answers_json else {}
    result = score_answers(
        answers, key, session.global_q_start, session.global_q_end, ratio
    )
    if subjects:
        result["subjects"] = subject_scores(result["per_question"], subjects)
    return {
        "sheet_id": sheet.id,
        "roll_no": sheet.roll_no,
        "session_id": session.id,
        **result,
    }


def score_session(db: Session, session_id: int) -> dict[str, Any]:
    session = db.get(ExamSession, session_id)
    if session is None:
        raise ScoringError(f"Session {session_id} not found.")
    key = program_key(db, session.program_id)
    subjects = (
        db.query(SubjectSplit)
        .filter(SubjectSplit.program_id == session.program_id)
        .filter(SubjectSplit.q_start >= session.global_q_start)
        .filter(SubjectSplit.q_end <= session.global_q_end)
        .all()
    )
    sheets = (
        db.query(SheetResult)
        .join(ScanBatch, SheetResult.batch_id == ScanBatch.id)
        .filter(ScanBatch.session_id == session_id)
        .all()
    )
    scored = [
        score_sheet(db, s, key=key, subjects=subjects)
        for s in sheets
        if is_scorable(db, s)
    ]
    return {
        "session_id": session_id,
        "session_name": session.name,
        "global_q_start": session.global_q_start,
        "global_q_end": session.global_q_end,
        "sheet_count": len(scored),
        "results": scored,
    }


def score_program(db: Session, program_id: int) -> dict[str, Any]:
    from app.services import export as export_svc
    from app.services.program_service import get_program, list_sessions

    program = get_program(db, program_id)
    sessions = list_sessions(db, program_id)
    if not sessions:
        return {
            "program_id": program_id,
            "session_name": program.name,
            "global_q_start": 0,
            "global_q_end": 0,
            "sheet_count": 0,
            "results": [],
        }
    q_start = min(s.global_q_start for s in sessions)
    q_end = max(s.global_q_end for s in sessions)
    key = program_key(db, program_id)
    subjects = (
        db.query(SubjectSplit)
        .filter(SubjectSplit.program_id == program_id, SubjectSplit.session_id.is_(None))
        .all()
    )
    merged, roll_ratios, _warnings = export_svc._merge_program_answers(db, sessions)
    results = []
    for roll, answers in merged.items():
        ratio = roll_ratios.get(roll, 0.0)
        scored = score_answers(answers, key, q_start, q_end, ratio)
        if subjects:
            scored["subjects"] = subject_scores(scored["per_question"], subjects)
        results.append(
            {
                "sheet_id": None,
                "roll_no": roll,
                "session_id": None,
                "counts": scored["counts"],
                "percentage": scored["percentage"],
                "secure_score": scored["secure_score"],
                "subjects": scored.get("subjects", []),
            }
        )
    results.sort(key=lambda r: r["roll_no"] or "")
    return {
        "program_id": program_id,
        "session_name": program.name,
        "global_q_start": q_start,
        "global_q_end": q_end,
        "sheet_count": len(results),
        "results": results,
    }
