"""Student roster API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import program_service, roster_import_service, student_service as svc
from app.services.student_parser import StudentParseError, parse_students

router = APIRouter(tags=["students"])


class StudentEntry(BaseModel):
    roll_no: str
    name: str
    class_section: str | None = None
    batch_label: str | None = None


class StudentBulkCreate(BaseModel):
    entries: list[StudentEntry]


class RosterImportRequest(BaseModel):
    session_id: int
    rolls: list[str] | None = None


@router.get("/programs/{program_id}/students")
def list_students(
    program_id: int,
    q: str | None = None,
    class_section: str | None = None,
    batch_label: str | None = None,
    db: Session = Depends(get_db),
):
    try:
        rows = svc.list_students(
            db, program_id, search=q, class_section=class_section, batch_label=batch_label
        )
    except program_service.ProgramError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"students": [svc.student_to_dict(s) for s in rows]}


@router.post("/programs/{program_id}/students", status_code=201)
def create_students(program_id: int, payload: StudentBulkCreate, db: Session = Depends(get_db)):
    try:
        result = svc.upsert_students(
            db,
            program_id,
            [
                (e.roll_no, e.name, e.class_section, e.batch_label)
                for e in payload.entries
            ],
        )
    except (program_service.ProgramError, svc.StudentError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.post("/programs/{program_id}/students/upload")
async def upload_students(
    program_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    data = await file.read()
    filename = file.filename or "roster.csv"
    try:
        entries = parse_students(data, filename)
        result = svc.upsert_students(db, program_id, entries)
    except StudentParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (program_service.ProgramError, svc.StudentError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.delete("/programs/{program_id}/students/{roll_no}", status_code=204)
def delete_student(program_id: int, roll_no: str, db: Session = Depends(get_db)):
    try:
        svc.delete_student(db, program_id, roll_no)
    except (program_service.ProgramError, svc.StudentError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/programs/{program_id}/roster/candidates")
def list_roster_candidates(
    program_id: int,
    session_id: int,
    db: Session = Depends(get_db),
):
    try:
        candidates = roster_import_service.list_candidates(db, program_id, session_id)
    except program_service.ProgramError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"candidates": candidates}


@router.post("/programs/{program_id}/roster/import-from-session")
def import_roster_from_session(
    program_id: int,
    payload: RosterImportRequest,
    db: Session = Depends(get_db),
):
    try:
        result = roster_import_service.import_rolls(
            db, program_id, payload.session_id, payload.rolls
        )
    except program_service.ProgramError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result
