"""Extract an answer key from a pre-filled OMR sheet (same template as student sheets).

Reads marked bubbles via the M09 pipeline, maps sheet question numbers to the
session's global range, and upserts the program master key.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import ExamSession
from app.omr.align import warp_sheet
from app.omr.bubble_refine import build_refine_context
from app.omr import bubbles as mcq_reader
from app.paths import DATA_DIR
from app.services import answer_key_service, program_service, template_service
from app.services.answer_key_service import AnswerKeyError
from app.services.template_service import TemplateError
from app.watcher.dropzone import expand_to_pages

UPLOAD_DIR = DATA_DIR / "key_sheet_uploads"

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".pdf"}


class AnswerKeyExtractError(ValueError):
    """Raised when a marked key sheet cannot be read reliably."""

    def __init__(self, message: str, issues: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.issues = issues or []


def resolve_template_for_session(db: Session, session: ExamSession) -> tuple[dict[str, Any], str]:
    """Return (template_dict, template_family) for OMR read."""
    try:
        return template_service.resolve_session_template(db, session)
    except TemplateError as exc:
        raise AnswerKeyError(str(exc)) from exc


def _save_upload(data: bytes, filename: str) -> Path:
    suffix = Path(filename).suffix.lower()
    if suffix not in _IMAGE_SUFFIXES:
        raise AnswerKeyExtractError(
            f"Unsupported file type {suffix!r}. Use JPG, PNG, TIFF, or PDF."
        )
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    dest.write_bytes(data)
    return dest


def extract_entries_from_image(
    image_path: str,
    session: ExamSession,
    template_dict: dict[str, Any],
    family: str,
) -> tuple[list[tuple[int, str]], list[dict[str, Any]]]:
    """Read MCQ marks and map sheet Q numbers to global question numbers."""
    try:
        template, _ = template_service.build_engine_template(template_dict, family)
    except TemplateError as exc:
        raise AnswerKeyExtractError(str(exc)) from exc
    warp = warp_sheet(image_path, template)
    if warp is None:
        raise AnswerKeyExtractError(
            "Could not align the sheet — corner markers were not detected. "
            "Use a flat scan of the same answer-sheet template."
        )

    refine = build_refine_context(warp.image, template, warp)
    mcq = mcq_reader.read_mcq(warp.image, template, refine)
    entries: list[tuple[int, str]] = []
    issues: list[dict[str, Any]] = []

    for sheet_q in range(1, session.sheet_question_count + 1):
        global_q = session.global_q_start + sheet_q - 1
        q = mcq.get(sheet_q)
        if q is None:
            issues.append(
                {
                    "global_q": global_q,
                    "sheet_q": sheet_q,
                    "type": "missing",
                    "detail": "Question not found on template.",
                }
            )
            continue
        status = q["status"]
        if status == mcq_reader.STATUS_ANSWERED:
            entries.append((global_q, q["option"]))
        elif status == mcq_reader.STATUS_BLANK:
            issues.append(
                {
                    "global_q": global_q,
                    "sheet_q": sheet_q,
                    "type": "blank",
                    "detail": "No bubble marked.",
                }
            )
        else:
            issues.append(
                {
                    "global_q": global_q,
                    "sheet_q": sheet_q,
                    "type": "multi",
                    "detail": f"Multiple marks detected: {''.join(q.get('marked', []))}",
                }
            )

    return entries, issues


def import_from_upload(
    db: Session,
    program_id: int,
    session_id: int,
    data: bytes,
    filename: str,
    changed_by: str | None = None,
) -> dict[str, Any]:
    """Save upload, OMR-read marks, and upsert the session's key slice."""
    session = program_service.get_session(db, session_id)
    if session.program_id != program_id:
        raise AnswerKeyError("Session does not belong to this program.")

    saved = _save_upload(data, filename)
    try:
        pages = expand_to_pages(saved)
        if not pages:
            if saved.suffix.lower() == ".pdf":
                raise AnswerKeyExtractError(
                    "Could not read PDF. Install Poppler for Windows and add its "
                    "bin folder to PATH (pdftoppm/pdffinfo required), or upload a "
                    "JPG/PNG/TIFF scan instead."
                )
            raise AnswerKeyExtractError("Could not read the uploaded image file.")
        if len(pages) > 1:
            raise AnswerKeyExtractError(
                f"PDF has {len(pages)} pages; upload a single-page key sheet."
            )

        template_dict, family = resolve_template_for_session(db, session)
        entries, issues = extract_entries_from_image(
            pages[0], session, template_dict, family
        )

        if issues:
            preview = "; ".join(
                f"Q{i['global_q']} ({i['type']})" for i in issues[:8]
            )
            extra = f" (+{len(issues) - 8} more)" if len(issues) > 8 else ""
            raise AnswerKeyExtractError(
                f"Key sheet has {len(issues)} problem(s) — each question needs exactly "
                f"one mark: {preview}{extra}",
                issues=issues,
            )

        if not entries:
            raise AnswerKeyExtractError("No marked answers found on the sheet.")

        restrict = (session.global_q_start, session.global_q_end)
        result = answer_key_service.upsert_keys(
            db,
            program_id,
            entries,
            changed_by=changed_by or "omr_key_sheet",
            restrict_range=restrict,
        )
        result["source"] = "omr_sheet"
        result["page_used"] = Path(pages[0]).name
        result["extracted"] = [
            {"question_no": q, "correct_option": opt} for q, opt in entries
        ]
        return result
    finally:
        saved.unlink(missing_ok=True)
