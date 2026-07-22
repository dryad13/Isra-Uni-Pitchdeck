"""M12 — Export & Reporting.

Builds per-session and cumulative-program result tables and serializes them to
CSV or Excel. Two cell modes:
  * literal — A/B/C/D, "Blank", "Multi"
  * binary  — 1 if correct else 0

Subject-split columns are appended (correct count + percentage).
"""

from __future__ import annotations

import io
import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import ExamSession, ScanBatch, SheetResult, SubjectSplit
from app.services import scoring
from app.services.sheet_utils import is_scorable

logger = logging.getLogger(__name__)

MODE_LITERAL = "literal"
MODE_BINARY = "binary"


class ExportError(ValueError):
    """Raised for invalid export requests."""


def _cell(question: dict[str, Any], mode: str) -> Any:
    if mode == MODE_BINARY:
        return 1 if question["status"] == scoring.STATUS_CORRECT else 0
    if question["status"] == scoring.STATUS_BLANK:
        return "Blank"
    if question["status"] == scoring.STATUS_MULTI:
        return "Multi"
    return question["option"]


def _result_row(result: dict[str, Any], q_start: int, q_end: int, mode: str) -> dict[str, Any]:
    row: dict[str, Any] = {"roll_no": result.get("roll_no") or ""}
    by_global = {q["global_q"]: q for q in result["per_question"]}
    for gq in range(q_start, q_end + 1):
        q = by_global.get(gq)
        row[f"Q{gq}"] = _cell(q, mode) if q else ""
    counts = result["counts"]
    row.update(
        {
            "correct": counts[scoring.STATUS_CORRECT],
            "wrong": counts[scoring.STATUS_WRONG],
            "blank": counts[scoring.STATUS_BLANK],
            "multi": counts[scoring.STATUS_MULTI],
            "total": counts["total"],
            "percentage": result["percentage"],
            "secure_score": result["secure_score"],
        }
    )
    for subject in result.get("subjects", []):
        row[f"{subject['subject_name']}_correct"] = subject["correct"]
        row[f"{subject['subject_name']}_pct"] = subject["percentage"]
    return row


def build_session_table(db: Session, session_id: int, mode: str) -> tuple[list[dict], list[str]]:
    scored = scoring.score_session(db, session_id)
    q_start, q_end = scored["global_q_start"], scored["global_q_end"]
    rows = [_result_row(r, q_start, q_end, mode) for r in scored["results"]]
    columns = _columns(q_start, q_end, scored["results"])
    return rows, columns


def _merge_program_answers(
    db: Session,
    sessions: list[ExamSession],
) -> tuple[dict[str, dict[str, str]], dict[str, float], list[str]]:
    """Merge answers by roll; return warnings for duplicate/colliding sheets."""
    merged: dict[str, dict[str, str]] = {}
    roll_ratios: dict[str, float] = {}
    warnings: list[str] = []
    excluded_sheet_ids: set[int] = set()

    sheets = (
        db.query(SheetResult, ScanBatch, ExamSession)
        .join(ScanBatch, SheetResult.batch_id == ScanBatch.id)
        .join(ExamSession, ScanBatch.session_id == ExamSession.id)
        .filter(ScanBatch.session_id.in_([s.id for s in sessions]))
        .all()
    )

    for sheet, _batch, session in sheets:
        if not is_scorable(db, sheet):
            excluded_sheet_ids.add(sheet.id)
            continue
        roll = sheet.roll_no or f"sheet_{sheet.id}"
        answers = json.loads(sheet.answers_json) if sheet.answers_json else {}
        if roll in merged:
            overlap = [k for k in answers if k in merged[roll] and merged[roll][k] != answers[k]]
            if overlap:
                msg = (
                    f"Roll {roll!r}: conflicting answers on sheet #{sheet.id} "
                    f"(overlapping Q: {overlap[:5]})"
                )
                logger.warning(msg)
                warnings.append(msg)
                excluded_sheet_ids.add(sheet.id)
                for other in sheets:
                    other_sheet, _, _ = other
                    if (other_sheet.roll_no or f"sheet_{other_sheet.id}") == roll:
                        excluded_sheet_ids.add(other_sheet.id)
                merged.pop(roll, None)
                roll_ratios.pop(roll, None)
                continue
        merged.setdefault(roll, {}).update(answers)
        roll_ratios[roll] = session.negative_marking_ratio

    return merged, roll_ratios, warnings


def build_program_table(
    db: Session, program_id: int, mode: str
) -> tuple[list[dict], list[str], list[str]]:
    sessions = (
        db.query(ExamSession)
        .filter(ExamSession.program_id == program_id)
        .order_by(ExamSession.session_order.asc())
        .all()
    )
    if not sessions:
        return [], ["roll_no"], []
    q_start = min(s.global_q_start for s in sessions)
    q_end = max(s.global_q_end for s in sessions)
    key = scoring.program_key(db, program_id)
    subjects = (
        db.query(SubjectSplit)
        .filter(SubjectSplit.program_id == program_id, SubjectSplit.session_id.is_(None))
        .all()
    )

    merged, roll_ratios, warnings = _merge_program_answers(db, sessions)

    results = []
    for roll, answers in merged.items():
        ratio = roll_ratios.get(roll, 0.0)
        scored = scoring.score_answers(answers, key, q_start, q_end, ratio)
        if subjects:
            scored["subjects"] = scoring.subject_scores(scored["per_question"], subjects)
        scored["roll_no"] = roll
        results.append(scored)
    results.sort(key=lambda r: r["roll_no"])

    rows = [_result_row(r, q_start, q_end, mode) for r in results]
    columns = _columns(q_start, q_end, results)
    return rows, columns, warnings


def _columns(q_start: int, q_end: int, results: list[dict]) -> list[str]:
    cols = ["roll_no"]
    cols += [f"Q{gq}" for gq in range(q_start, q_end + 1)]
    cols += ["correct", "wrong", "blank", "multi", "total", "percentage", "secure_score"]
    subject_cols: list[str] = []
    for r in results:
        for subject in r.get("subjects", []):
            for suffix in ("_correct", "_pct"):
                name = f"{subject['subject_name']}{suffix}"
                if name not in subject_cols:
                    subject_cols.append(name)
    return cols + subject_cols


def to_csv(rows: list[dict], columns: list[str]) -> bytes:
    import pandas as pd

    df = pd.DataFrame(rows, columns=columns)
    return df.to_csv(index=False).encode("utf-8")


def to_xlsx(rows: list[dict], columns: list[str]) -> bytes:
    import pandas as pd

    df = pd.DataFrame(rows, columns=columns)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
    return buffer.getvalue()


def serialize(rows: list[dict], columns: list[str], file_format: str) -> tuple[bytes, str]:
    if file_format == "csv":
        return to_csv(rows, columns), "text/csv"
    if file_format in {"xlsx", "excel"}:
        return (
            to_xlsx(rows, columns),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    raise ExportError(f"Unknown format {file_format!r} (use csv or xlsx).")
