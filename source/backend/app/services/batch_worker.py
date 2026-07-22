"""Process-pool workers for parallel OMR batch processing (Windows spawn-safe)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.omr.pipeline import SheetReader

_reader: SheetReader | None = None


def init_worker(template_dict: dict[str, Any], family: str) -> None:
    global _reader
    _reader = SheetReader(template_dict, family)


def process_sheet_task(
    path: str,
    global_q_start: int,
    sheet_question_count: int,
    crop_dir: str,
    crop_prefix: str,
) -> dict[str, Any]:
    if _reader is None:
        raise RuntimeError("Worker not initialized")
    return _reader.process(
        path,
        global_q_start=global_q_start,
        sheet_question_count=sheet_question_count,
        crop_dir=Path(crop_dir),
        crop_prefix=crop_prefix,
    )
