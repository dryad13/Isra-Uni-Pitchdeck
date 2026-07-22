"""M04 — Template & Path Manager API.

Endpoints for the Layout Calibrator UI and downstream batch-start validation.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import PathLayout
from app.db.session import get_db
from app.services import template_service as svc

router = APIRouter(prefix="/templates", tags=["templates"])


# --- Schemas -----------------------------------------------------------------


class TemplateCreate(BaseModel):
    name: str
    template_family: str
    template: dict[str, Any]
    max_questions: int | None = None


class TemplateUpdate(BaseModel):
    name: str | None = None
    template: dict[str, Any] | None = None


class OverlayRequest(BaseModel):
    template_family: str
    template: dict[str, Any]


class ValidateRequest(BaseModel):
    template_family: str
    template: dict[str, Any]
    sheet_question_count: int | None = None


# --- Family defaults ---------------------------------------------------------


@router.get("/families")
def get_families():
    return {"families": svc.list_families()}


@router.get("/families/{family}/default")
def get_default_template(family: str):
    try:
        return {"template_family": family, "template": svc.load_default_template(family)}
    except svc.TemplateError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/families/{family}/seed")
def get_seed_template(family: str):
    """Deprecated alias — use /default."""
    return get_default_template(family)


# --- Path layout CRUD --------------------------------------------------------


@router.get("")
def list_layouts(db: Session = Depends(get_db)):
    layouts = db.query(PathLayout).order_by(PathLayout.created_at.desc()).all()
    return {"layouts": [svc.path_layout_to_dict(l) for l in layouts]}


@router.post("", status_code=201)
def create_layout(payload: TemplateCreate, db: Session = Depends(get_db)):
    issues = svc.validate_template_dict(payload.template)
    if issues:
        raise HTTPException(status_code=422, detail={"issues": issues})
    try:
        layout = svc.create_path_layout(
            db,
            name=payload.name,
            template_family=payload.template_family,
            template_dict=payload.template,
            max_questions=payload.max_questions,
        )
    except svc.TemplateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return svc.path_layout_to_dict(layout, include_template=True)


@router.get("/{layout_id}")
def get_layout(layout_id: int, db: Session = Depends(get_db)):
    layout = db.get(PathLayout, layout_id)
    if layout is None:
        raise HTTPException(status_code=404, detail="Path layout not found")
    return svc.path_layout_to_dict(layout, include_template=True)


@router.put("/{layout_id}")
def update_layout(layout_id: int, payload: TemplateUpdate, db: Session = Depends(get_db)):
    layout = db.get(PathLayout, layout_id)
    if layout is None:
        raise HTTPException(status_code=404, detail="Path layout not found")
    if payload.template is not None:
        issues = svc.validate_template_dict(payload.template)
        if issues:
            raise HTTPException(status_code=422, detail={"issues": issues})
    layout = svc.update_path_layout(
        db, layout, name=payload.name, template_dict=payload.template
    )
    return svc.path_layout_to_dict(layout, include_template=True)


@router.delete("/{layout_id}", status_code=204)
def delete_layout(layout_id: int, db: Session = Depends(get_db)):
    layout = db.get(PathLayout, layout_id)
    if layout is None:
        raise HTTPException(status_code=404, detail="Path layout not found")
    db.delete(layout)
    db.commit()


# --- Calibration helpers -----------------------------------------------------


@router.post("/overlay")
def overlay(payload: OverlayRequest):
    """Exact bubble geometry for the given template (calibrator overlay)."""
    issues = svc.validate_template_dict(payload.template)
    if issues:
        raise HTTPException(status_code=422, detail={"issues": issues})
    try:
        return svc.compute_overlay(payload.template, payload.template_family)
    except svc.TemplateError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/warp")
def warp(payload: OverlayRequest):
    """Warp the family blank scan into pageDimensions space (calibration backdrop)."""
    try:
        return svc.warp_blank_image(payload.template, payload.template_family)
    except svc.TemplateError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/validate")
def validate(payload: ValidateRequest):
    return svc.validate_for_session(
        payload.template, payload.template_family, payload.sheet_question_count
    )
