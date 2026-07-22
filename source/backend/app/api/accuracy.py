"""Accuracy Lab API — diagnostic runs and ground-truth references."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import accuracy_service as svc

router = APIRouter(prefix="/accuracy", tags=["accuracy"])


class ThresholdOverrides(BaseModel):
    fill_threshold: float | None = None
    blank_threshold: float | None = None
    multi_mark_threshold: float | None = None
    comfort_margin: float | None = None
    comfort_ratio: float | None = None
    alignment_review_below: float | None = None


class RunRequest(BaseModel):
    fixture_id: str | None = None
    upload_id: str | None = None
    template_family: str = "150Q"
    layout_id: int | None = None
    sheet_question_count: int = 150
    threshold_overrides: ThresholdOverrides | None = None
    include_warp_preview: bool = True


class ReferenceSave(BaseModel):
    template_family: str = "150Q"
    roll_no: str | None = None
    answers: dict[str, str] = Field(default_factory=dict)
    note: str | None = None


@router.get("/fixtures")
def get_fixtures():
    return svc.list_fixtures()


@router.post("/upload")
async def upload_scan(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload.")
    try:
        return svc.save_upload(data, file.filename or "scan.jpg")
    except svc.AccuracyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/run")
def run_diagnostic(payload: RunRequest, db: Session = Depends(get_db)):
    if not payload.fixture_id and not payload.upload_id:
        raise HTTPException(
            status_code=400, detail="Provide fixture_id or upload_id."
        )
    if payload.fixture_id and payload.upload_id:
        raise HTTPException(
            status_code=400, detail="Provide only one of fixture_id or upload_id."
        )

    try:
        if payload.fixture_id:
            image_path = str(svc.resolve_fixture_path(payload.fixture_id))
            fixture_id = payload.fixture_id
        else:
            image_path = str(svc.resolve_upload_path(payload.upload_id or ""))
            fixture_id = payload.upload_id

        template_dict = svc.resolve_template(
            db, payload.template_family, payload.layout_id
        )
        overrides = (
            payload.threshold_overrides.model_dump(exclude_none=True)
            if payload.threshold_overrides
            else None
        )
        return svc.run_diagnostic(
            image_path,
            template_dict=template_dict,
            template_family=payload.template_family,
            sheet_question_count=payload.sheet_question_count,
            fixture_id=fixture_id,
            threshold_overrides=overrides,
            include_warp_preview=payload.include_warp_preview,
        )
    except svc.AccuracyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/reference/{fixture_id}")
def get_reference(fixture_id: str):
    ref = svc.load_reference(fixture_id)
    if ref is None:
        raise HTTPException(status_code=404, detail="No reference saved for this fixture.")
    return ref


@router.put("/reference/{fixture_id}")
def put_reference(fixture_id: str, payload: ReferenceSave):
    return svc.save_reference(
        fixture_id,
        template_family=payload.template_family,
        roll_no=payload.roll_no,
        answers=payload.answers,
        note=payload.note,
    )
