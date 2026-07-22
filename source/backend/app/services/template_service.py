"""M04 — Template & Path Manager service.

Owns OMRChecker-compatible `template.json` handling for path layouts:
  * template-family registry (150Q / 60Q)
  * exact bubble geometry + warped-image preview (reuses vendored OMRChecker)
  * seeding the Isra 150Q path layout from samples/
  * template/session compatibility validation

The geometry and warping are delegated to the vendored OMRChecker engine so the
calibrator overlay is pixel-consistent with what the read pipeline (M09) will use.
This directly addresses the "warped vs page dimensions" calibration blocker: the
calibrator works in the warped `pageDimensions` coordinate space, not the raw scan.
"""

from __future__ import annotations

import base64
import copy
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import ExamSession, PathLayout
from app.paths import ENGINE_ROOT, SAMPLES_ROOT


# --- Template-family registry ------------------------------------------------

FAMILY_REGISTRY: dict[str, dict[str, Any]] = {
    "150Q": {
        "max_questions": 150,
        "columns": 5,
        "rows_per_column": 30,
        "sample_dir": "isra_150q",
        "blank_image": "blank_template.png",
        "template_file": "template.json",
    },
    "60Q": {
        "max_questions": 60,
        "columns": 4,
        "rows_per_column": 15,
        "sample_dir": "isra_60q",
        "blank_image": "blank_template.png",
        "template_file": "template.json",
    },
}


class TemplateError(RuntimeError):
    """Raised for invalid templates or unavailable engine dependencies."""


def list_families() -> list[dict[str, Any]]:
    families = []
    for family, meta in FAMILY_REGISTRY.items():
        sample_dir = SAMPLES_ROOT / meta["sample_dir"]
        blank = sample_dir / meta["blank_image"]
        template = sample_dir / meta["template_file"]
        families.append(
            {
                "family": family,
                "max_questions": meta["max_questions"],
                "columns": meta["columns"],
                "rows_per_column": meta["rows_per_column"],
                "blank_image_available": blank.exists(),
                "seed_template_available": template.exists(),
            }
        )
    return families


def _family_meta(family: str) -> dict[str, Any]:
    meta = FAMILY_REGISTRY.get(family)
    if meta is None:
        raise TemplateError(f"Unknown template family: {family}")
    return meta


def family_sample_dir(family: str) -> Path:
    return SAMPLES_ROOT / _family_meta(family)["sample_dir"]


def family_blank_image(family: str) -> Path:
    meta = _family_meta(family)
    return SAMPLES_ROOT / meta["sample_dir"] / meta["blank_image"]


def load_default_template(family: str) -> dict[str, Any]:
    """Load the built-in template.json for a sheet family from samples/."""
    meta = _family_meta(family)
    path = SAMPLES_ROOT / meta["sample_dir"] / meta["template_file"]
    if not path.exists():
        raise TemplateError(f"No default template.json for family {family} at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_seed_template(family: str) -> dict[str, Any]:
    """Backward-compatible alias for load_default_template."""
    return load_default_template(family)


def _default_layout_name(family: str) -> str:
    return f"Isra {family}"


def _legacy_layout_names(family: str) -> tuple[str, ...]:
    return (_default_layout_name(family), f"Isra {family} (seed)")


def _find_default_layout(db: Session, family: str) -> PathLayout | None:
    for name in _legacy_layout_names(family):
        layout = (
            db.query(PathLayout)
            .filter(
                PathLayout.template_family == family,
                PathLayout.name == name,
            )
            .first()
        )
        if layout is not None:
            return layout
    return None


def resolve_session_template(db: Session, session: ExamSession) -> tuple[dict[str, Any], str]:
    """Return (template_dict, template_family) for OMR read/scan."""
    if session.path_layout_id is not None:
        layout = db.get(PathLayout, session.path_layout_id)
        if layout is None or not layout.columns_json:
            raise TemplateError(
                f"Path layout {session.path_layout_id} is missing or has no template."
            )
        return json.loads(layout.columns_json), session.template_family

    layout = _find_default_layout(db, session.template_family)
    if layout is not None and layout.columns_json:
        return json.loads(layout.columns_json), session.template_family

    return load_default_template(session.template_family), session.template_family


def effective_scan_family(session: ExamSession) -> str:
    """Physical OMR layout used for student scan batches."""
    return session.scan_template_family or session.template_family


def resolve_scan_template(db: Session, session: ExamSession) -> tuple[dict[str, Any], str]:
    """Return (template_dict, family) for reading scanned student sheets.

    Answer keys and the calibrator use ``resolve_session_template`` (logical sheet).
    When ``scan_template_family`` differs — e.g. 60Q exam keyed on 60Q paper but
    students fill the first 60 bubbles on a 150Q sheet — use the scan family's
    built-in layout for batch OMR.
    """
    family = effective_scan_family(session)
    if family == session.template_family:
        return resolve_session_template(db, session)
    return load_default_template(family), family


# --- Vendored OMRChecker bridge ---------------------------------------------


def _load_engine():
    """Import the vendored OMRChecker lazily.

    Kept lazy so the core API stays importable even if OMRChecker's runtime
    extras (rich/dotmap/matplotlib/...) are not installed.
    """
    if str(ENGINE_ROOT) not in sys.path:
        sys.path.insert(0, str(ENGINE_ROOT))
    try:
        from src.defaults import CONFIG_DEFAULTS  # type: ignore
        from src.template import Template  # type: ignore
        from src.utils.parsing import open_config_with_defaults  # type: ignore
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise TemplateError(
            "OMRChecker engine dependencies not installed. Run "
            "`pip install -r backend/requirements.txt`."
        ) from exc
    return Template, CONFIG_DEFAULTS, open_config_with_defaults


def _build_engine_template(template_dict: dict[str, Any], family: str):
    """Construct an OMRChecker Template from an in-memory dict.

    The template is written into the family sample dir so relative marker paths
    (e.g. `omr_marker.jpg`) resolve correctly.
    """
    Template, CONFIG_DEFAULTS, open_config_with_defaults = _load_engine()
    sample_dir = family_sample_dir(family)
    if not sample_dir.exists():
        raise TemplateError(f"Sample dir missing for family {family}: {sample_dir}")

    config_path = sample_dir / "config.json"
    tuning_config = (
        open_config_with_defaults(config_path) if config_path.exists() else CONFIG_DEFAULTS
    )

    # Written into the family sample dir (not the OS temp dir) so the template's
    # relative marker path (e.g. omr_marker.jpg) resolves against the samples.
    tmp_path = sample_dir / f"_calibrator_{uuid.uuid4().hex}.json"
    try:
        tmp_path.write_text(json.dumps(template_dict), encoding="utf-8")
        template = Template(tmp_path, tuning_config)
        return template, tuning_config
    finally:
        tmp_path.unlink(missing_ok=True)


def build_engine_template(template_dict: dict[str, Any], family: str):
    """Public: construct a vendored OMRChecker Template + tuning config.

    Build once per batch and reuse across sheets (the read pipeline calls this).
    """
    return _build_engine_template(template_dict, family)


def compute_overlay(template_dict: dict[str, Any], family: str) -> dict[str, Any]:
    """Return exact bubble geometry for the calibrator overlay.

    Bubble positions match the read pipeline because they come straight from the
    OMRChecker Template grid generator.
    """
    template, _ = _build_engine_template(template_dict, family)
    bubble_w, bubble_h = template.bubble_dimensions
    blocks = []
    bubbles = []
    for block in template.field_blocks:
        blocks.append(
            {
                "name": block.name,
                "origin": list(block.origin),
                "dimensions": list(block.dimensions),
                "labels": len(block.parsed_field_labels),
                "bubbles_per_label": (
                    len(block.traverse_bubbles[0]) if block.traverse_bubbles else 0
                ),
            }
        )
        for field_bubbles in block.traverse_bubbles:
            for bubble in field_bubbles:
                bubbles.append(
                    {
                        "block": block.name,
                        "field_label": bubble.field_label,
                        "field_value": str(bubble.field_value),
                        "x": int(bubble.x),
                        "y": int(bubble.y),
                        "w": int(bubble_w),
                        "h": int(bubble_h),
                    }
                )
    return {
        "page_dimensions": list(template.page_dimensions),
        "bubble_dimensions": [int(bubble_w), int(bubble_h)],
        "blocks": blocks,
        "bubbles": bubbles,
    }


def warp_blank_image(template_dict: dict[str, Any], family: str) -> dict[str, Any]:
    """Warp the family blank scan into pageDimensions space and return base64 PNG.

    This is the calibration backdrop: operators tune coordinates against the
    warped sheet, eliminating raw-scan vs. warped coordinate drift.
    """
    import cv2  # local import keeps API importable without cv2 in some envs

    template, _ = _build_engine_template(template_dict, family)
    blank = family_blank_image(family)
    if not blank.exists():
        raise TemplateError(f"No blank image for family {family} at {blank}")

    gray = cv2.imread(str(blank), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise TemplateError(f"Cannot read blank image: {blank}")

    warped = template.image_instance_ops.apply_preprocessors(str(blank), gray, template)
    if warped is None:
        return {"aligned": False, "image": None, "width": None, "height": None}

    # The read pipeline resizes the warped sheet to pageDimensions before reading
    # bubbles (core.read_omr_response). Match that here so the returned backdrop
    # shares the exact coordinate space as the overlay bubbles.
    page_w, page_h = template.page_dimensions
    warped = cv2.resize(warped, (int(page_w), int(page_h)))

    ok, buf = cv2.imencode(".png", warped)
    if not ok:
        raise TemplateError("Failed to encode warped image")
    encoded = base64.b64encode(buf.tobytes()).decode("ascii")
    return {
        "aligned": True,
        "image": f"data:image/png;base64,{encoded}",
        "width": int(warped.shape[1]),
        "height": int(warped.shape[0]),
    }


# --- Validation --------------------------------------------------------------


def validate_template_dict(template_dict: dict[str, Any]) -> list[str]:
    """Structural checks independent of the engine."""
    issues: list[str] = []
    if not isinstance(template_dict, dict):
        return ["Template must be a JSON object."]
    if "pageDimensions" not in template_dict:
        issues.append("Missing `pageDimensions`.")
    if "bubbleDimensions" not in template_dict:
        issues.append("Missing `bubbleDimensions`.")
    field_blocks = template_dict.get("fieldBlocks")
    if not field_blocks:
        issues.append("Missing `fieldBlocks`.")
    return issues


def count_template_questions(template_dict: dict[str, Any], family: str) -> int:
    """Count MCQ question fields the template defines (excludes roll/INT blocks)."""
    overlay = compute_overlay(template_dict, family)
    total = 0
    for block in overlay["blocks"]:
        if block["bubbles_per_label"] == 4:  # MCQ4
            total += block["labels"]
    return total


def validate_for_session(
    template_dict: dict[str, Any],
    family: str,
    sheet_question_count: int | None = None,
) -> dict[str, Any]:
    """Validate a template for use by a session (used at batch start, FR-1.3)."""
    issues = validate_template_dict(template_dict)
    if issues:
        return {"ok": False, "issues": issues, "mcq_questions": None}

    meta = FAMILY_REGISTRY.get(family)
    if meta is None:
        return {"ok": False, "issues": [f"Unknown family {family}"], "mcq_questions": None}

    try:
        mcq_questions = count_template_questions(template_dict, family)
    except TemplateError as exc:
        return {"ok": False, "issues": [str(exc)], "mcq_questions": None}

    if mcq_questions > meta["max_questions"]:
        issues.append(
            f"Template defines {mcq_questions} MCQ questions, exceeds family max "
            f"{meta['max_questions']}."
        )
    if sheet_question_count is not None and sheet_question_count > mcq_questions:
        issues.append(
            f"Session expects {sheet_question_count} questions but template only "
            f"maps {mcq_questions}."
        )
    return {"ok": not issues, "issues": issues, "mcq_questions": mcq_questions}


# --- PathLayout persistence --------------------------------------------------


def _split_template(template_dict: dict[str, Any]) -> dict[str, Any]:
    """Derive roll/anchor sub-objects for the dedicated columns."""
    field_blocks = template_dict.get("fieldBlocks", {})
    roll = {k: v for k, v in field_blocks.items() if v.get("fieldType", "").startswith("QTYPE_INT")}
    anchor = {"preProcessors": template_dict.get("preProcessors", [])}
    return {"roll": roll, "anchor": anchor}


def path_layout_to_dict(layout: PathLayout, include_template: bool = False) -> dict[str, Any]:
    data = {
        "id": layout.id,
        "template_family": layout.template_family,
        "name": layout.name,
        "max_questions": layout.max_questions,
        "created_at": layout.created_at.isoformat() if layout.created_at else None,
    }
    if include_template and layout.columns_json:
        data["template"] = json.loads(layout.columns_json)
    return data


def create_path_layout(
    db: Session,
    name: str,
    template_family: str,
    template_dict: dict[str, Any],
    max_questions: int | None = None,
) -> PathLayout:
    meta = _family_meta(template_family)
    parts = _split_template(template_dict)
    layout = PathLayout(
        template_family=template_family,
        name=name,
        max_questions=max_questions or meta["max_questions"],
        columns_json=json.dumps(template_dict),
        roll_number_json=json.dumps(parts["roll"]),
        anchor_json=json.dumps(parts["anchor"]),
    )
    db.add(layout)
    db.commit()
    db.refresh(layout)
    return layout


def update_path_layout(
    db: Session,
    layout: PathLayout,
    name: str | None = None,
    template_dict: dict[str, Any] | None = None,
) -> PathLayout:
    if name is not None:
        layout.name = name
    if template_dict is not None:
        parts = _split_template(template_dict)
        layout.columns_json = json.dumps(template_dict)
        layout.roll_number_json = json.dumps(parts["roll"])
        layout.anchor_json = json.dumps(parts["anchor"])
    db.commit()
    db.refresh(layout)
    return layout


def seed_default_layouts(db: Session) -> int:
    """Ensure each family has a default PathLayout synced from samples/.

    Built-in layouts are refreshed from disk on startup so calibrator / batch
    processing pick up template changes under samples/<family>/. Custom layouts
    (other names) are never touched.
    """
    changed = 0
    for family, meta in FAMILY_REGISTRY.items():
        template_path = SAMPLES_ROOT / meta["sample_dir"] / meta["template_file"]
        if not template_path.exists():
            continue
        template_dict = json.loads(template_path.read_text(encoding="utf-8"))
        default_name = _default_layout_name(family)
        layout = _find_default_layout(db, family)
        if layout is None:
            create_path_layout(
                db,
                name=default_name,
                template_family=family,
                template_dict=copy.deepcopy(template_dict),
            )
            changed += 1
            continue
        if layout.name != default_name:
            layout.name = default_name
            changed += 1
        stored = json.loads(layout.columns_json) if layout.columns_json else {}
        if stored != template_dict:
            update_path_layout(
                db, layout, template_dict=copy.deepcopy(template_dict)
            )
            changed += 1
    if changed:
        db.commit()
    return changed
