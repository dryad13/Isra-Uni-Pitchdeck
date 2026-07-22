"""M06 — Answer Key Manager API.

Master answer key per program, built incrementally per session slice:
  * manual grid upsert
  * CSV/Excel upload (optionally scoped to a session's global range)
  * audit trail + per-session readiness (gates scanning)
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import answer_key_service as svc
from app.services import program_service
from app.services.answer_key_from_sheet import AnswerKeyExtractError, import_from_upload
from app.services.answer_key_parser import AnswerKeyParseError, parse_answer_key
from app.services.template_service import TemplateError

router = APIRouter(tags=["answer-keys"])


class KeyEntry(BaseModel):
    question_no: int
    correct_option: str


class KeyUpsert(BaseModel):
    entries: list[KeyEntry]
    session_id: int | None = None
    changed_by: str | None = None


def _restrict_for_session(db: Session, program_id: int, session_id: int | None):
    if session_id is None:
        return None
    start, end, session = svc.session_range(db, session_id)
    if session.program_id != program_id:
        raise HTTPException(status_code=400, detail="Session does not belong to this program.")
    return (start, end)


@router.get("/programs/{program_id}/answer-keys")
def list_keys(
    program_id: int,
    start: int | None = None,
    end: int | None = None,
    db: Session = Depends(get_db),
):
    try:
        return {"keys": svc.list_keys(db, program_id, start, end)}
    except program_service.ProgramError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/programs/{program_id}/answer-keys")
def upsert_keys(program_id: int, payload: KeyUpsert, db: Session = Depends(get_db)):
    try:
        restrict = _restrict_for_session(db, program_id, payload.session_id)
        result = svc.upsert_keys(
            db,
            program_id,
            [(e.question_no, e.correct_option) for e in payload.entries],
            changed_by=payload.changed_by,
            restrict_range=restrict,
        )
    except program_service.ProgramError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except svc.AnswerKeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


def _is_sheet_upload(filename: str) -> bool:
    return Path(filename or "").suffix.lower() in {
        ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".pdf",
    }


@router.post("/programs/{program_id}/answer-keys/upload")
async def upload_keys(
    program_id: int,
    file: UploadFile = File(...),
    session_id: int | None = Form(None),
    changed_by: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """Upload CSV/Excel key file, or OMR-read a marked answer sheet (image/PDF)."""
    data = await file.read()
    filename = file.filename or "upload.csv"
    try:
        if _is_sheet_upload(filename):
            if session_id is None:
                raise HTTPException(
                    status_code=400,
                    detail="Select a session before uploading a marked answer sheet.",
                )
            return import_from_upload(
                db,
                program_id,
                session_id,
                data,
                filename,
                changed_by=changed_by,
            )

        entries = parse_answer_key(data, filename)
        restrict = _restrict_for_session(db, program_id, session_id)
        result = svc.upsert_keys(
            db, program_id, entries, changed_by=changed_by, restrict_range=restrict
        )
    except AnswerKeyParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AnswerKeyExtractError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TemplateError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except program_service.ProgramError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except svc.AnswerKeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {exc}",
        ) from exc
    return result


@router.post("/programs/{program_id}/answer-keys/from-sheet")
async def upload_key_sheet(
    program_id: int,
    file: UploadFile = File(...),
    session_id: int = Form(...),
    changed_by: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """OMR-read a pre-filled answer sheet (alias for /upload with image/PDF)."""
    data = await file.read()
    try:
        return import_from_upload(
            db,
            program_id,
            session_id,
            data,
            file.filename or "key_sheet.jpg",
            changed_by=changed_by,
        )
    except AnswerKeyExtractError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TemplateError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except program_service.ProgramError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except svc.AnswerKeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}") from exc


@router.delete("/programs/{program_id}/answer-keys/{question_no}", status_code=204)
def delete_key(program_id: int, question_no: int, db: Session = Depends(get_db)):
    try:
        svc.delete_key(db, program_id, question_no)
    except (program_service.ProgramError, svc.AnswerKeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/programs/{program_id}/answer-keys/audit")
def list_audit(program_id: int, db: Session = Depends(get_db)):
    try:
        program_service.get_program(db, program_id)
    except program_service.ProgramError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"audit": svc.list_audit(db, program_id)}


@router.get("/sessions/{session_id}/key-status")
def session_key_status(session_id: int, db: Session = Depends(get_db)):
    try:
        return svc.session_slice_status(db, session_id)
    except program_service.ProgramError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
