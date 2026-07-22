"""Accuracy Lab — diagnostic OMR runs, ground-truth references, and comparison."""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
from sqlalchemy.orm import Session

from app.db.models import PathLayout
from app.omr.omr_settings import current_threshold_defaults, threshold_override_context
from app.omr.pipeline import SheetReader
from app.paths import DATA_DIR, RESOURCE_DIR
from app.services import template_service
from app.services.template_service import TemplateError

FIXTURES_DIR = RESOURCE_DIR / "tests" / "fixtures" / "scans"
MANIFEST_PATH = FIXTURES_DIR / "manifest.json"
REFERENCES_DIR = DATA_DIR / "accuracy_references"
UPLOADS_DIR = DATA_DIR / "accuracy_uploads"

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


class AccuracyError(ValueError):
    """Raised when an accuracy-lab operation cannot proceed."""


def _load_manifest() -> list[dict[str, Any]]:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return []


def list_fixtures() -> dict[str, Any]:
    fixtures = []
    for entry in _load_manifest():
        path = FIXTURES_DIR / entry["path"]
        fixtures.append(
            {
                **entry,
                "available": path.exists(),
            }
        )
    return {
        "fixtures": fixtures,
        "threshold_defaults": current_threshold_defaults(),
    }


def resolve_fixture_path(fixture_id: str) -> Path:
    for entry in _load_manifest():
        if entry["id"] == fixture_id:
            path = FIXTURES_DIR / entry["path"]
            if not path.exists():
                raise AccuracyError(f"Fixture image missing: {entry['path']}")
            return path
    raise AccuracyError(f"Unknown fixture: {fixture_id}")


def resolve_upload_path(upload_id: str) -> Path:
    for suffix in _IMAGE_SUFFIXES:
        path = UPLOADS_DIR / f"{upload_id}{suffix}"
        if path.exists():
            return path
    raise AccuracyError(f"Unknown or expired upload: {upload_id}")


def save_upload(data: bytes, filename: str) -> dict[str, str]:
    suffix = Path(filename).suffix.lower()
    if suffix not in _IMAGE_SUFFIXES:
        raise AccuracyError(
            f"Unsupported file type {suffix!r}. Use JPG, PNG, or TIFF."
        )
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    upload_id = uuid.uuid4().hex
    dest = UPLOADS_DIR / f"{upload_id}{suffix}"
    dest.write_bytes(data)
    return {"upload_id": upload_id, "filename": filename}


def _reference_path(fixture_id: str) -> Path:
    return REFERENCES_DIR / f"{fixture_id}.json"


def load_reference(fixture_id: str) -> dict[str, Any] | None:
    path = _reference_path(fixture_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_reference(
    fixture_id: str,
    *,
    template_family: str,
    roll_no: str | None,
    answers: dict[str, str],
    note: str | None = None,
) -> dict[str, Any]:
    REFERENCES_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "fixture_id": fixture_id,
        "template_family": template_family,
        "roll_no": roll_no,
        "answers": {str(k): v for k, v in answers.items()},
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
        "confirmed_by_note": note,
    }
    _reference_path(fixture_id).write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    return payload


def resolve_template(
    db: Session | None,
    template_family: str,
    layout_id: int | None,
) -> dict[str, Any]:
    if layout_id is not None:
        if db is None:
            raise AccuracyError("Database session required for custom layout.")
        layout = db.get(PathLayout, layout_id)
        if layout is None or not layout.columns_json:
            raise AccuracyError(f"Path layout {layout_id} not found.")
        return json.loads(layout.columns_json)
    return template_service.load_default_template(template_family)


def compare_to_reference(
    questions: list[dict[str, Any]],
    detected_roll: str | None,
    reference: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Attach reference + match flags; compute summary accuracy metrics."""
    ref_answers = (reference or {}).get("answers") or {}
    ref_roll = (reference or {}).get("roll_no")

    matched = 0
    compared = 0
    mismatches: list[int] = []

    enriched: list[dict[str, Any]] = []
    for q in questions:
        sheet_q = q["sheet_q"]
        ref_val = ref_answers.get(str(sheet_q))
        row = dict(q)
        row["reference"] = ref_val if ref_val is not None else None
        if ref_val is None:
            row["match"] = None
        else:
            compared += 1
            detected = (q.get("detected") or "").upper()
            expected = (ref_val or "").upper()
            is_match = detected == expected
            row["match"] = is_match
            if is_match:
                matched += 1
            else:
                mismatches.append(sheet_q)
        enriched.append(row)

    roll_match: bool | None = None
    if ref_roll is not None:
        roll_match = (detected_roll or "") == str(ref_roll)

    accuracy_pct: float | None = None
    if compared > 0:
        accuracy_pct = round(100.0 * matched / compared, 2)

    summary_extra = {
        "reference_questions": len(ref_answers),
        "compared": compared,
        "matched": matched,
        "mismatches": len(mismatches),
        "mismatch_sheet_qs": mismatches,
        "accuracy_pct": accuracy_pct,
        "roll_match": roll_match,
    }
    return enriched, summary_extra


def _encode_warp_preview(warped) -> str | None:
    if warped is None:
        return None
    ok, buf = cv2.imencode(".jpeg", warped, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        return None
    encoded = base64.b64encode(buf.tobytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _resolve_mcq_option(q: dict[str, Any]) -> tuple[str, str]:
    """Mirror pipeline auto-resolution for display (non-strict)."""
    from app.omr import bubbles as mcq_reader

    status = q.get("status", mcq_reader.STATUS_BLANK)
    option = q.get("option") or ""
    if status == mcq_reader.STATUS_MULTI and not mcq_reader.is_hard_multi(q):
        ranked = sorted(q.get("fills", {}).items(), key=lambda item: -item[1])
        if ranked:
            option = ranked[0][0]
            status = mcq_reader.STATUS_ANSWERED
    return option, status


def run_diagnostic(
    image_path: str,
    *,
    template_dict: dict[str, Any],
    template_family: str,
    sheet_question_count: int,
    fixture_id: str | None = None,
    threshold_overrides: dict[str, float] | None = None,
    include_warp_preview: bool = True,
    reference: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run OMR with per-question fill diagnostics for the Accuracy Lab."""
    import time

    start = time.perf_counter()
    thresholds_used = current_threshold_defaults()

    with threshold_override_context(threshold_overrides):
        thresholds_used = current_threshold_defaults()
        try:
            reader = SheetReader(template_dict, template_family)
        except TemplateError as exc:
            raise AccuracyError(str(exc)) from exc

        result = reader.process(
            image_path,
            global_q_start=1,
            sheet_question_count=sheet_question_count,
            crop_dir=UPLOADS_DIR,
            crop_prefix=f"acc_{fixture_id or 'upload'}",
        )
        timing_ms = round((time.perf_counter() - start) * 1000)

        if not result.get("aligned"):
            return {
                "fixture_id": fixture_id,
                "aligned": False,
                "alignment_quality": result.get("alignment_quality", 0.0),
                "roll_no": None,
                "roll_status": None,
                "timing_ms": timing_ms,
                "thresholds_used": thresholds_used,
                "dynamic_threshold": None,
                "grid_refined": False,
                "grid_confidence": result.get("grid_confidence"),
                "fallback_used": result.get("fallback_used"),
                "contour_agreement_pct": result.get("contour_agreement_pct"),
                "read_method_summary": result.get("read_method_summary"),
                "questions": [],
                "summary": {
                    "total": sheet_question_count,
                    "answered": 0,
                    "blank": 0,
                    "multi": 0,
                    "anomalies": 1,
                    "accuracy_pct": None,
                    "roll_match": None,
                },
                "warp_preview": None,
                "overlay": None,
                "detected_bubbles": [],
            }

        from app.omr import bubbles as mcq_reader
        from app.omr import roll_number as roll_reader
        from app.omr.threshold import dynamic_threshold

        template_mcq = result.get("template_mcq") or {}
        contour_mcq = result.get("contour_mcq") or {}
        final_mcq = {}
        for sheet_q in range(1, sheet_question_count + 1):
            pq = next(
                (p for p in result.get("per_question", []) if p.get("sheet_q") == sheet_q),
                None,
            )
            if pq:
                final_mcq[sheet_q] = {
                    "status": pq.get("status"),
                    "option": pq.get("option"),
                    "method": pq.get("method"),
                }

        all_fills = [
            val for q in template_mcq.values() for val in q.get("fills", {}).values()
        ]
        dyn_threshold = round(dynamic_threshold(all_fills), 2) if all_fills else None

        questions: list[dict[str, Any]] = []
        counts = {"answered": 0, "blank": 0, "multi": 0, "total": 0}
        anomalies = 0

        for sheet_q in range(1, sheet_question_count + 1):
            q = template_mcq.get(sheet_q)
            c_q = contour_mcq.get(sheet_q)
            f_q = final_mcq.get(sheet_q)
            if q is None and c_q is None:
                continue
            option, status = _resolve_mcq_option(q or c_q or {})
            t_opt, _ = _resolve_mcq_option(q) if q else ("", status)
            c_opt, _ = _resolve_mcq_option(c_q) if c_q else ("", status)
            low_conf = (
                status == mcq_reader.STATUS_ANSWERED
                and q is not None
                and mcq_reader.is_low_confidence(q)
            )
            hard_multi = status == mcq_reader.STATUS_MULTI and q is not None and mcq_reader.is_hard_multi(q)

            if hard_multi or low_conf:
                anomalies += 1

            counts["total"] += 1
            counts[status] = counts.get(status, 0) + 1

            questions.append(
                {
                    "sheet_q": sheet_q,
                    "detected": option,
                    "template_detected": t_opt,
                    "contour_detected": c_opt,
                    "final_detected": f_q.get("option") if f_q else option,
                    "method": f_q.get("method") if f_q else None,
                    "status": status,
                    "fills": (q or c_q or {}).get("fills", {}),
                    "contour_fills": (c_q or {}).get("fills", {}),
                    "low_confidence": low_conf,
                    "hard_multi": hard_multi,
                }
            )

        roll_status = result.get("roll_status")
        if roll_status != roll_reader.ROLL_OK:
            anomalies += 1

        timing_ms = round((time.perf_counter() - start) * 1000)

        ref = reference
        if ref is None and fixture_id:
            ref = load_reference(fixture_id)

        enriched, compare_summary = compare_to_reference(
            questions, result.get("roll_no"), ref
        )

        summary = {
            "total": sheet_question_count,
            "answered": counts.get("answered", 0),
            "blank": counts.get("blank", 0),
            "multi": counts.get("multi", 0),
            "anomalies": anomalies,
            **compare_summary,
        }

        overlay = None
        try:
            overlay = template_service.compute_overlay(template_dict, template_family)
        except TemplateError:
            pass

        warp_preview = None
        if include_warp_preview:
            from app.omr.align import warp_sheet

            template, _ = template_service.build_engine_template(
                template_dict, template_family
            )
            warp = warp_sheet(image_path, template)
            if warp is not None:
                warp_preview = _encode_warp_preview(warp.image)

        return {
            "fixture_id": fixture_id,
            "aligned": True,
            "alignment_quality": result.get("alignment_quality"),
            "roll_no": result.get("roll_no"),
            "roll_status": roll_status,
            "timing_ms": timing_ms,
            "thresholds_used": thresholds_used,
            "dynamic_threshold": dyn_threshold,
            "grid_refined": result.get("grid_refined"),
            "grid_confidence": result.get("grid_confidence"),
            "fallback_used": result.get("fallback_used"),
            "contour_agreement_pct": result.get("contour_agreement_pct"),
            "read_method_summary": result.get("read_method_summary"),
            "questions": enriched,
            "summary": summary,
            "warp_preview": warp_preview,
            "overlay": overlay,
            "detected_bubbles": result.get("detected_bubbles") or [],
        }
