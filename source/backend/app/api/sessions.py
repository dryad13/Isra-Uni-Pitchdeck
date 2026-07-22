"""M05 — Exam Session chain API (cumulative global question numbering)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import program_service as svc

router = APIRouter(tags=["sessions"])


class SessionCreate(BaseModel):
    name: str
    template_family: str
    sheet_question_count: int = Field(..., ge=1, le=150)
    path_layout_id: int | None = None
    global_q_start: int | None = None
    exam_date: date | None = None
    batch_name: str | None = None
    export_mode: str = "literal"
    negative_marking_ratio: float = 0.0
    scan_template_family: str | None = None


@router.get("/programs/{program_id}/sessions")
def list_sessions(program_id: int, db: Session = Depends(get_db)):
    try:
        svc.get_program(db, program_id)
    except svc.ProgramError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"sessions": [svc.session_to_dict(s, db) for s in svc.list_sessions(db, program_id)]}


@router.get("/programs/{program_id}/sessions/suggest-start")
def suggest_start(program_id: int, db: Session = Depends(get_db)):
    try:
        svc.get_program(db, program_id)
    except svc.ProgramError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"global_q_start": svc.suggest_next_start(db, program_id)}


@router.post("/programs/{program_id}/sessions", status_code=201)
def create_session(
    program_id: int, payload: SessionCreate, db: Session = Depends(get_db)
):
    try:
        session = svc.create_session(
            db,
            program_id=program_id,
            name=payload.name,
            template_family=payload.template_family,
            sheet_question_count=payload.sheet_question_count,
            path_layout_id=payload.path_layout_id,
            global_q_start=payload.global_q_start,
            exam_date=payload.exam_date,
            batch_name=payload.batch_name,
            export_mode=payload.export_mode,
            negative_marking_ratio=payload.negative_marking_ratio,
            scan_template_family=payload.scan_template_family,
        )
    except svc.ProgramError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return svc.session_to_dict(session, db)


@router.get("/sessions/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db)):
    try:
        session = svc.get_session(db, session_id)
    except svc.ProgramError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return svc.session_to_dict(session, db)


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: int, db: Session = Depends(get_db)):
    try:
        svc.delete_session(db, session_id)
    except svc.ProgramError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
