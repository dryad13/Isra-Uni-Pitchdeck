"""M11/M12 — Scores (JSON) + Export (CSV/Excel download) API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import export as export_svc
from app.services import scoring
from app.services import sheet_list_service
from app.services.program_service import ProgramError

router = APIRouter(tags=["export"])


@router.get("/sessions/{session_id}/scores")
def session_scores(session_id: int, db: Session = Depends(get_db)):
    try:
        return scoring.score_session(db, session_id)
    except scoring.ScoringError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/programs/{program_id}/scores")
def program_scores(program_id: int, db: Session = Depends(get_db)):
    try:
        return scoring.score_program(db, program_id)
    except ProgramError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/sheets")
def list_session_sheets(
    session_id: int,
    q: str | None = None,
    status: str | None = None,
    batch_id: int | None = None,
    db: Session = Depends(get_db),
):
    try:
        return sheet_list_service.list_session_sheets(
            db, session_id, search=q, status=status, batch_id=batch_id
        )
    except ProgramError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _download(rows, columns, file_format: str, filename_base: str) -> Response:
    try:
        data, media_type = export_svc.serialize(rows, columns, file_format)
    except export_svc.ExportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    ext = "csv" if file_format == "csv" else "xlsx"
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename_base}.{ext}"'},
    )


@router.get("/sessions/{session_id}/export")
def export_session(
    session_id: int,
    mode: str = "literal",
    format: str = "csv",
    db: Session = Depends(get_db),
):
    try:
        rows, columns = export_svc.build_session_table(db, session_id, mode)
    except scoring.ScoringError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _download(rows, columns, format, f"session_{session_id}_{mode}")


@router.get("/programs/{program_id}/export")
def export_program(
    program_id: int,
    mode: str = "literal",
    format: str = "csv",
    db: Session = Depends(get_db),
):
    rows, columns, _warnings = export_svc.build_program_table(db, program_id, mode)
    return _download(rows, columns, format, f"program_{program_id}_{mode}")
