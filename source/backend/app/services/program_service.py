"""M05 — Exam Program Manager service.

Owns exam programs, their session chain (with cumulative global question
numbering), subject splits, and the program-level answer-key coverage map.

Core invariant (FR-1.3): a program holds ONE master answer key keyed by global
`question_no`. Each session scores against the slice
`[global_q_start, global_q_end]`. New sessions auto-extend the global range:
`global_q_start = previous_session.global_q_end + 1`.
"""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    AnswerKey,
    AnswerKeyAudit,
    ExamProgram,
    ExamSession,
    IngestedFile,
    PathLayout,
    ScanBatch,
    SheetResult,
    Student,
    SubjectSplit,
    VerificationQueue,
)
from app.services.template_service import FAMILY_REGISTRY

MAX_SHEET_QUESTIONS = 150

# #region agent log
_DEBUG_LOG = Path(__file__).resolve().parents[5] / "debug-cb4b52.log"


def _agent_log(location: str, message: str, data: dict[str, Any], hypothesis_id: str) -> None:
    try:
        payload = {
            "sessionId": "cb4b52",
            "timestamp": int(time.time() * 1000),
            "location": location,
            "message": message,
            "data": data,
            "hypothesisId": hypothesis_id,
        }
        with _DEBUG_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")
    except OSError:
        pass


def _keys_in_range(db: Session, program_id: int, start: int, end: int) -> list[dict[str, Any]]:
    rows = (
        db.query(AnswerKey.question_no, AnswerKey.correct_option)
        .filter(
            AnswerKey.program_id == program_id,
            AnswerKey.question_no >= start,
            AnswerKey.question_no <= end,
        )
        .order_by(AnswerKey.question_no.asc())
        .all()
    )
    return [{"question_no": q, "correct_option": opt} for q, opt in rows]


# #endregion


ROSTER_SYNC_AUTO = "auto"
ROSTER_SYNC_MANUAL = "manual"
VALID_ROSTER_SYNC_MODES = {ROSTER_SYNC_AUTO, ROSTER_SYNC_MANUAL}


class ProgramError(ValueError):
    """Raised for invalid program/session configuration."""


# --- Programs ----------------------------------------------------------------


def create_program(
    db: Session,
    name: str,
    planned_max_questions: int | None = None,
    description: str | None = None,
) -> ExamProgram:
    if not name.strip():
        raise ProgramError("Program name is required.")
    program = ExamProgram(
        name=name.strip(),
        planned_max_questions=planned_max_questions,
        key_coverage_end=0,
        description=description,
    )
    db.add(program)
    db.commit()
    db.refresh(program)
    return program


def list_programs(
    db: Session,
    search: str | None = None,
    include_stats: bool = False,
) -> list[dict[str, Any]]:
    query = db.query(ExamProgram)
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(ExamProgram.name.ilike(term))
    programs = query.order_by(ExamProgram.id.desc()).all()
    if not include_stats:
        return [program_to_dict(p) for p in programs]

    out: list[dict[str, Any]] = []
    for program in programs:
        data = program_to_dict(program)
        pid = program.id
        data["session_count"] = (
            db.query(func.count(ExamSession.id))
            .filter(ExamSession.program_id == pid)
            .scalar()
            or 0
        )
        data["student_count"] = (
            db.query(func.count(Student.id)).filter(Student.program_id == pid).scalar() or 0
        )
        data["sheet_count"] = (
            db.query(func.count(SheetResult.id))
            .join(ScanBatch, SheetResult.batch_id == ScanBatch.id)
            .join(ExamSession, ScanBatch.session_id == ExamSession.id)
            .filter(ExamSession.program_id == pid)
            .scalar()
            or 0
        )
        out.append(data)
    return out


def get_program(db: Session, program_id: int) -> ExamProgram:
    program = db.get(ExamProgram, program_id)
    if program is None:
        raise ProgramError(f"Program {program_id} not found.")
    return program


def delete_program(db: Session, program_id: int) -> None:
    program = get_program(db, program_id)
    db.query(SubjectSplit).filter(SubjectSplit.program_id == program_id).delete()
    db.query(Student).filter(Student.program_id == program_id).delete()
    db.query(AnswerKey).filter(AnswerKey.program_id == program_id).delete()
    db.query(AnswerKeyAudit).filter(AnswerKeyAudit.program_id == program_id).delete()
    db.query(ExamSession).filter(ExamSession.program_id == program_id).delete()
    db.delete(program)
    db.commit()


# --- Sessions ----------------------------------------------------------------


def _last_session(db: Session, program_id: int) -> ExamSession | None:
    return (
        db.query(ExamSession)
        .filter(ExamSession.program_id == program_id)
        .order_by(ExamSession.session_order.desc())
        .first()
    )


def suggest_next_start(db: Session, program_id: int) -> int:
    last = _last_session(db, program_id)
    return (last.global_q_end + 1) if last else 1


def create_session(
    db: Session,
    program_id: int,
    name: str,
    template_family: str,
    sheet_question_count: int,
    path_layout_id: int | None = None,
    global_q_start: int | None = None,
    exam_date: date | None = None,
    batch_name: str | None = None,
    export_mode: str = "literal",
    negative_marking_ratio: float = 0.0,
    scan_template_family: str | None = None,
) -> ExamSession:
    program = get_program(db, program_id)
    if not name.strip():
        raise ProgramError("Session name is required.")
    if sheet_question_count <= 0:
        raise ProgramError("sheet_question_count must be positive.")
    if sheet_question_count > MAX_SHEET_QUESTIONS:
        raise ProgramError(
            f"sheet_question_count cannot exceed {MAX_SHEET_QUESTIONS} per session."
        )

    meta = FAMILY_REGISTRY.get(template_family)
    if meta is None:
        raise ProgramError(f"Unknown template family: {template_family}")
    if sheet_question_count > meta["max_questions"]:
        raise ProgramError(
            f"sheet_question_count {sheet_question_count} exceeds {template_family} "
            f"max {meta['max_questions']}."
        )

    scan_family = scan_template_family or template_family
    scan_meta = FAMILY_REGISTRY.get(scan_family)
    if scan_meta is None:
        raise ProgramError(f"Unknown scan template family: {scan_family}")
    if sheet_question_count > scan_meta["max_questions"]:
        raise ProgramError(
            f"sheet_question_count {sheet_question_count} exceeds scan layout "
            f"{scan_family} max {scan_meta['max_questions']}."
        )

    if path_layout_id is not None:
        layout = db.get(PathLayout, path_layout_id)
        if layout is None:
            raise ProgramError(f"Path layout {path_layout_id} not found.")
        if layout.template_family != template_family:
            raise ProgramError(
                f"Path layout family {layout.template_family} != session family "
                f"{template_family}."
            )

    start = global_q_start if global_q_start is not None else suggest_next_start(db, program_id)
    if start < 1:
        raise ProgramError("global_q_start must be >= 1.")
    end = start + sheet_question_count - 1

    # Reject overlap with existing sessions (gaps are allowed but discouraged).
    for existing in db.query(ExamSession).filter(ExamSession.program_id == program_id):
        if start <= existing.global_q_end and end >= existing.global_q_start:
            raise ProgramError(
                f"Global range Q{start}-Q{end} overlaps session "
                f"'{existing.name}' (Q{existing.global_q_start}-Q{existing.global_q_end})."
            )

    next_order = (
        db.query(func.coalesce(func.max(ExamSession.session_order), 0))
        .filter(ExamSession.program_id == program_id)
        .scalar()
        + 1
    )

    session = ExamSession(
        program_id=program_id,
        template_family=template_family,
        scan_template_family=scan_template_family,
        session_order=next_order,
        name=name.strip(),
        path_layout_id=path_layout_id,
        sheet_question_count=sheet_question_count,
        global_q_start=start,
        global_q_end=end,
        key_complete=False,
        exam_date=exam_date,
        batch_name=batch_name,
        export_mode=export_mode,
        negative_marking_ratio=negative_marking_ratio,
    )
    db.add(session)
    db.flush()
    session.key_complete = _is_slice_complete(db, program_id, start, end)
    # #region agent log
    _agent_log(
        "program_service.py:create_session",
        "session created",
        {
            "session_id": session.id,
            "program_id": program_id,
            "global_q_start": start,
            "global_q_end": end,
            "key_complete": session.key_complete,
            "existing_keys_in_range": _keys_in_range(db, program_id, start, end),
        },
        "B,C",
    )
    # #endregion
    db.commit()
    db.refresh(session)
    return session


def list_sessions(db: Session, program_id: int) -> list[ExamSession]:
    return (
        db.query(ExamSession)
        .filter(ExamSession.program_id == program_id)
        .order_by(ExamSession.session_order.asc())
        .all()
    )


def get_session(db: Session, session_id: int) -> ExamSession:
    session = db.get(ExamSession, session_id)
    if session is None:
        raise ProgramError(f"Session {session_id} not found.")
    return session


def delete_session(db: Session, session_id: int) -> None:
    session = get_session(db, session_id)
    program_id = session.program_id
    q_start = session.global_q_start
    q_end = session.global_q_end
    # #region agent log
    keys_before = _keys_in_range(db, program_id, q_start, q_end)
    _agent_log(
        "program_service.py:delete_session",
        "deleting session",
        {
            "session_id": session_id,
            "program_id": program_id,
            "global_q_start": q_start,
            "global_q_end": q_end,
            "answer_keys_in_range_before_delete": keys_before,
            "answer_key_count": len(keys_before),
        },
        "A",
    )
    # #endregion

    keys_to_delete = (
        db.query(AnswerKey)
        .filter(
            AnswerKey.program_id == program_id,
            AnswerKey.question_no >= q_start,
            AnswerKey.question_no <= q_end,
        )
        .all()
    )
    for key in keys_to_delete:
        db.add(
            AnswerKeyAudit(
                program_id=program_id,
                question_no=key.question_no,
                old_value=key.correct_option,
                new_value=None,
                changed_by="system:session_delete",
            )
        )
        db.delete(key)

    batch_ids = [
        row[0]
        for row in db.query(ScanBatch.id).filter(ScanBatch.session_id == session_id).all()
    ]
    if batch_ids:
        sheet_ids = [
            row[0]
            for row in db.query(SheetResult.id).filter(SheetResult.batch_id.in_(batch_ids)).all()
        ]
        if sheet_ids:
            db.query(VerificationQueue).filter(VerificationQueue.sheet_id.in_(sheet_ids)).delete(
                synchronize_session=False
            )
            db.query(SheetResult).filter(SheetResult.id.in_(sheet_ids)).delete(
                synchronize_session=False
            )
        db.query(ScanBatch).filter(ScanBatch.id.in_(batch_ids)).delete(synchronize_session=False)

    db.query(IngestedFile).filter(IngestedFile.session_id == session_id).delete(
        synchronize_session=False
    )
    db.query(SubjectSplit).filter(SubjectSplit.session_id == session_id).delete(
        synchronize_session=False
    )
    db.delete(session)
    db.commit()
    refresh_key_completeness(db, program_id)
    # #region agent log
    keys_after = _keys_in_range(db, program_id, q_start, q_end)
    _agent_log(
        "program_service.py:delete_session",
        "session deleted",
        {
            "session_id": session_id,
            "program_id": program_id,
            "global_q_start": q_start,
            "global_q_end": q_end,
            "answer_keys_in_range_after_delete": keys_after,
            "answer_key_count": len(keys_after),
            "runId": "post-fix",
        },
        "A",
    )
    # #endregion


# --- Answer-key coverage -----------------------------------------------------


def _covered_questions(db: Session, program_id: int) -> set[int]:
    rows = (
        db.query(AnswerKey.question_no)
        .filter(AnswerKey.program_id == program_id)
        .all()
    )
    return {r[0] for r in rows}


def _is_slice_complete(db: Session, program_id: int, start: int, end: int) -> bool:
    covered = _covered_questions(db, program_id)
    return all(q in covered for q in range(start, end + 1))


def refresh_key_completeness(db: Session, program_id: int) -> None:
    """Recompute `key_complete` for every session and program coverage end."""
    covered = _covered_questions(db, program_id)
    for session in list_sessions(db, program_id):
        session.key_complete = all(
            q in covered for q in range(session.global_q_start, session.global_q_end + 1)
        )
    program = get_program(db, program_id)
    program.key_coverage_end = max(covered) if covered else 0
    db.commit()


def _compress_ranges(numbers: set[int]) -> list[list[int]]:
    if not numbers:
        return []
    ordered = sorted(numbers)
    ranges: list[list[int]] = [[ordered[0], ordered[0]]]
    for n in ordered[1:]:
        if n == ranges[-1][1] + 1:
            ranges[-1][1] = n
        else:
            ranges.append([n, n])
    return ranges


def coverage_map(db: Session, program_id: int) -> dict[str, Any]:
    """Key coverage map for the program (FR-1.4 UI)."""
    covered = _covered_questions(db, program_id)
    sessions = list_sessions(db, program_id)
    session_status = []
    for s in sessions:
        rng = range(s.global_q_start, s.global_q_end + 1)
        missing = [q for q in rng if q not in covered]
        session_status.append(
            {
                "session_id": s.id,
                "name": s.name,
                "global_q_start": s.global_q_start,
                "global_q_end": s.global_q_end,
                "covered": len(rng) - len(missing),
                "total": len(rng),
                "missing": missing,
                "key_complete": len(missing) == 0,
            }
        )
    return {
        "program_id": program_id,
        "covered_ranges": _compress_ranges(covered),
        "covered_count": len(covered),
        "max_covered": max(covered) if covered else 0,
        "sessions": session_status,
    }


# --- Subject splits ----------------------------------------------------------


def create_subject_split(
    db: Session,
    program_id: int,
    subject_name: str,
    q_start: int,
    q_end: int,
    session_id: int | None = None,
) -> SubjectSplit:
    get_program(db, program_id)
    if not subject_name.strip():
        raise ProgramError("subject_name is required.")
    if q_start < 1 or q_end < q_start:
        raise ProgramError("Invalid subject range.")
    if session_id is not None:
        get_session(db, session_id)
    split = SubjectSplit(
        program_id=program_id,
        session_id=session_id,
        subject_name=subject_name.strip(),
        q_start=q_start,
        q_end=q_end,
    )
    db.add(split)
    db.commit()
    db.refresh(split)
    return split


def list_subject_splits(db: Session, program_id: int) -> list[SubjectSplit]:
    return (
        db.query(SubjectSplit)
        .filter(SubjectSplit.program_id == program_id)
        .order_by(SubjectSplit.q_start.asc())
        .all()
    )


def delete_subject_split(db: Session, split_id: int) -> None:
    split = db.get(SubjectSplit, split_id)
    if split is None:
        raise ProgramError(f"Subject split {split_id} not found.")
    db.delete(split)
    db.commit()


# --- Serialization -----------------------------------------------------------


def program_to_dict(program: ExamProgram) -> dict[str, Any]:
    return {
        "id": program.id,
        "name": program.name,
        "planned_max_questions": program.planned_max_questions,
        "key_coverage_end": program.key_coverage_end,
        "description": program.description,
        "roster_sync_mode": getattr(program, "roster_sync_mode", ROSTER_SYNC_AUTO)
        or ROSTER_SYNC_AUTO,
    }


def update_program(
    db: Session,
    program_id: int,
    *,
    roster_sync_mode: str | None = None,
) -> ExamProgram:
    program = get_program(db, program_id)
    if roster_sync_mode is not None:
        if roster_sync_mode not in VALID_ROSTER_SYNC_MODES:
            raise ProgramError(f"roster_sync_mode must be one of {sorted(VALID_ROSTER_SYNC_MODES)}.")
        program.roster_sync_mode = roster_sync_mode
    db.commit()
    db.refresh(program)
    return program


def _session_key_counts(db: Session, session: ExamSession) -> tuple[int, int]:
    """Return (answers filled, total) for this session's global question slice."""
    covered = _covered_questions(db, session.program_id)
    start, end = session.global_q_start, session.global_q_end
    filled = sum(1 for q in range(start, end + 1) if q in covered)
    return filled, end - start + 1


def session_to_dict(session: ExamSession, db: Session | None = None) -> dict[str, Any]:
    data = {
        "id": session.id,
        "program_id": session.program_id,
        "template_family": session.template_family,
        "scan_template_family": session.scan_template_family,
        "session_order": session.session_order,
        "name": session.name,
        "path_layout_id": session.path_layout_id,
        "sheet_question_count": session.sheet_question_count,
        "global_q_start": session.global_q_start,
        "global_q_end": session.global_q_end,
        "key_complete": session.key_complete,
        "exam_date": session.exam_date.isoformat() if session.exam_date else None,
        "batch_name": session.batch_name,
        "export_mode": session.export_mode,
        "negative_marking_ratio": session.negative_marking_ratio,
    }
    if db is not None:
        filled, total = _session_key_counts(db, session)
        data["key_filled"] = filled
        data["key_total"] = total
    return data


def subject_split_to_dict(split: SubjectSplit) -> dict[str, Any]:
    return {
        "id": split.id,
        "program_id": split.program_id,
        "session_id": split.session_id,
        "subject_name": split.subject_name,
        "q_start": split.q_start,
        "q_end": split.q_end,
    }
