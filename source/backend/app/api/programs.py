"""M05 — Exam Program + subject-split + coverage API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import program_service as svc

router = APIRouter(prefix="/programs", tags=["programs"])


class ProgramCreate(BaseModel):
    name: str
    planned_max_questions: int | None = None
    description: str | None = None


class ProgramPatch(BaseModel):
    roster_sync_mode: str | None = None


class SubjectSplitCreate(BaseModel):
    subject_name: str
    q_start: int
    q_end: int
    session_id: int | None = None


@router.get("")
def list_programs(
    q: str | None = None,
    include: str | None = None,
    db: Session = Depends(get_db),
):
    include_stats = include == "stats" if include else False
    return {"programs": svc.list_programs(db, search=q, include_stats=include_stats)}


@router.post("", status_code=201)
def create_program(payload: ProgramCreate, db: Session = Depends(get_db)):
    try:
        program = svc.create_program(
            db, payload.name, payload.planned_max_questions, payload.description
        )
    except svc.ProgramError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return svc.program_to_dict(program)


@router.get("/{program_id}")
def get_program(program_id: int, db: Session = Depends(get_db)):
    try:
        program = svc.get_program(db, program_id)
    except svc.ProgramError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "program": svc.program_to_dict(program),
        "sessions": [svc.session_to_dict(s, db) for s in svc.list_sessions(db, program_id)],
        "subjects": [
            svc.subject_split_to_dict(s) for s in svc.list_subject_splits(db, program_id)
        ],
        "coverage": svc.coverage_map(db, program_id),
    }


@router.patch("/{program_id}")
def patch_program(program_id: int, payload: ProgramPatch, db: Session = Depends(get_db)):
    try:
        program = svc.update_program(
            db, program_id, roster_sync_mode=payload.roster_sync_mode
        )
    except svc.ProgramError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return svc.program_to_dict(program)


@router.delete("/{program_id}", status_code=204)
def delete_program(program_id: int, db: Session = Depends(get_db)):
    try:
        svc.delete_program(db, program_id)
    except svc.ProgramError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{program_id}/coverage")
def get_coverage(program_id: int, db: Session = Depends(get_db)):
    try:
        svc.get_program(db, program_id)
    except svc.ProgramError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return svc.coverage_map(db, program_id)


@router.get("/{program_id}/subjects")
def list_subjects(program_id: int, db: Session = Depends(get_db)):
    return {
        "subjects": [
            svc.subject_split_to_dict(s) for s in svc.list_subject_splits(db, program_id)
        ]
    }


@router.post("/{program_id}/subjects", status_code=201)
def create_subject(
    program_id: int, payload: SubjectSplitCreate, db: Session = Depends(get_db)
):
    try:
        split = svc.create_subject_split(
            db,
            program_id,
            payload.subject_name,
            payload.q_start,
            payload.q_end,
            payload.session_id,
        )
    except svc.ProgramError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return svc.subject_split_to_dict(split)


@router.delete("/subjects/{split_id}", status_code=204)
def delete_subject(split_id: int, db: Session = Depends(get_db)):
    try:
        svc.delete_subject_split(db, split_id)
    except svc.ProgramError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
