"""M08 — Batch processing API + progress WebSocket."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import SheetResult
from app.db.session import SessionLocal, get_db
from app.services import batch_processor, batch_review_service

router = APIRouter(tags=["batches"])


class BatchStart(BaseModel):
    session_id: int
    file_paths: list[str]


@router.post("/batches/start", status_code=201)
def start_batch(payload: BatchStart):
    try:
        batch_id = batch_processor.start_batch(payload.session_id, payload.file_paths)
    except batch_processor.BatchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"batch_id": batch_id}


@router.get("/batches/{batch_id}")
def get_batch(batch_id: int, db: Session = Depends(get_db)):
    try:
        return batch_processor.batch_summary(db, batch_id)
    except batch_processor.BatchError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/batches")
def list_session_batches(
    session_id: int,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    return {"batches": batch_processor.list_batches(db, session_id, status=status)}


@router.post("/batches/{batch_id}/resume")
def resume_batch(batch_id: int):
    try:
        batch_processor.resume_batch(batch_id)
    except batch_processor.BatchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"batch_id": batch_id, "resumed": True}


@router.post("/batches/{batch_id}/cancel")
def cancel_batch(batch_id: int):
    try:
        return batch_processor.cancel_batch(batch_id)
    except batch_processor.BatchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/batches/{batch_id}/review")
def batch_review(batch_id: int, pending_only: bool = True, db: Session = Depends(get_db)):
    try:
        return batch_review_service.batch_review(db, batch_id, pending_only=pending_only)
    except batch_processor.BatchError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/batches/{batch_id}/sheets")
def list_sheets(batch_id: int, db: Session = Depends(get_db)):
    sheets = db.query(SheetResult).filter(SheetResult.batch_id == batch_id).all()
    out = []
    for s in sheets:
        out.append(
            {
                "id": s.id,
                "roll_no": s.roll_no,
                "answers": json.loads(s.answers_json) if s.answers_json else {},
                "counts": json.loads(s.counts_json) if s.counts_json else {},
            }
        )
    return {"sheets": out}


@router.websocket("/ws/batch/{batch_id}")
async def batch_progress(websocket: WebSocket, batch_id: int):
    await websocket.accept()
    try:
        while True:
            db = SessionLocal()
            try:
                summary = batch_processor.batch_summary(db, batch_id)
            except batch_processor.BatchError:
                await websocket.send_json({"error": "batch not found"})
                break
            finally:
                db.close()
            await websocket.send_json(summary)
            if summary["status"] in {
                "completed",
                "failed",
                "needs_verification",
                "interrupted",
            }:
                break
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        return
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass
