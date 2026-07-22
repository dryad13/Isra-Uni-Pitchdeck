"""Merge contour-first and template reads per question."""

from __future__ import annotations

from typing import Any

from app.config import get_config
from app.omr import bubbles as template_bubbles
from app.omr.grid_map import SheetGridMap


def _normalize_option(q: dict | None) -> str:
    if not q:
        return ""
    return (q.get("option") or "").upper()


def _should_fallback_sheet(grid: SheetGridMap | None, alignment_quality: float) -> bool:
    cfg = get_config().omr
    if grid is None:
        return True
    if grid.grid_confidence < cfg.contour.min_grid_confidence:
        return True
    if grid.detection_ratio < cfg.contour.min_sheet_detection_ratio:
        return True
    return False


def arbitrate_mcq(
    template_mcq: dict[int, dict],
    contour_mcq: dict[int, dict],
    *,
    grid: SheetGridMap | None,
    alignment_quality: float,
    sheet_question_count: int,
) -> tuple[dict[int, dict], dict[str, Any]]:
    cfg = get_config().omr
    fallback = _should_fallback_sheet(grid, alignment_quality)
    meta: dict[str, Any] = {
        "fallback_used": fallback,
        "grid_confidence": round(grid.grid_confidence, 3) if grid else 0.0,
        "detection_ratio": round(grid.detection_ratio, 3) if grid else 0.0,
        "read_method_summary": "template" if fallback else "hybrid",
        "per_question_methods": {},
    }

    if fallback or cfg.read_mode == "template":
        out = {}
        for sheet_q in range(1, sheet_question_count + 1):
            q = template_mcq.get(sheet_q)
            if q is None:
                continue
            merged = dict(q)
            merged["method"] = "template_fallback" if fallback else "template"
            out[sheet_q] = merged
            meta["per_question_methods"][sheet_q] = merged["method"]
        if fallback:
            meta["read_method_summary"] = "template_fallback"
        return out, meta

    if cfg.read_mode == "contour":
        out = {}
        for sheet_q in range(1, sheet_question_count + 1):
            q = contour_mcq.get(sheet_q)
            if q is None:
                continue
            merged = dict(q)
            merged["method"] = "contour"
            out[sheet_q] = merged
            meta["per_question_methods"][sheet_q] = "contour"
        meta["read_method_summary"] = "contour"
        return out, meta

    agreed = 0
    compared = 0
    out: dict[int, dict] = {}

    for sheet_q in range(1, sheet_question_count + 1):
        t_q = template_mcq.get(sheet_q)
        c_q = contour_mcq.get(sheet_q)
        if t_q is None and c_q is None:
            continue
        t_opt = _normalize_option(t_q)
        c_opt = _normalize_option(c_q)
        compared += 1

        if t_opt == c_opt:
            agreed += 1
            merged = dict(c_q or t_q)
            merged["method"] = "consensus"
            out[sheet_q] = merged
            meta["per_question_methods"][sheet_q] = "consensus"
            continue

        if alignment_quality < 0.55:
            winner = c_q or t_q
            method = "contour_weak_align"
            meta["per_question_methods"][sheet_q] = method
            merged = dict(winner)
            merged["method"] = method
            out[sheet_q] = merged
            continue

        t_clear = t_q and template_bubbles._clear_winner(
            *sorted(t_q.get("fills", {}).values(), reverse=True)[:2]
            if len(t_q.get("fills", {})) >= 2
            else (t_q.get("fills", {}).get(t_q.get("option", ""), 0), 0)
        )
        c_clear = c_q and template_bubbles._clear_winner(
            *sorted(c_q.get("fills", {}).values(), reverse=True)[:2]
            if len(c_q.get("fills", {})) >= 2
            else (c_q.get("fills", {}).get(c_q.get("option", ""), 0), 0)
        )

        block_conf = grid.grid_confidence if grid else 0.0
        if block_conf >= cfg.contour.min_grid_confidence and c_clear and not t_clear:
            merged = dict(c_q)
            merged["method"] = "contour"
            out[sheet_q] = merged
            meta["per_question_methods"][sheet_q] = "contour"
        elif alignment_quality >= 0.72 and t_clear:
            merged = dict(t_q)
            merged["method"] = "template"
            out[sheet_q] = merged
            meta["per_question_methods"][sheet_q] = "template"
        else:
            winner = c_q if block_conf >= cfg.contour.min_grid_confidence else t_q
            merged = dict(winner or t_q or c_q)
            merged["method"] = "disputed"
            merged["template_option"] = t_opt
            merged["contour_option"] = c_opt
            out[sheet_q] = merged
            meta["per_question_methods"][sheet_q] = "disputed"

    meta["contour_agreement_pct"] = round(100.0 * agreed / compared, 2) if compared else 0.0
    return out, meta


def arbitrate_roll(template_roll: dict, contour_roll: dict, *, fallback_used: bool) -> dict:
    cfg = get_config().omr
    if fallback_used or cfg.read_mode == "template":
        out = dict(template_roll)
        out["method"] = "template_fallback" if fallback_used else "template"
        return out
    if cfg.read_mode == "contour":
        out = dict(contour_roll)
        out["method"] = "contour"
        return out
    if template_roll.get("roll_no") == contour_roll.get("roll_no"):
        out = dict(contour_roll)
        out["method"] = "consensus"
        return out
    if template_roll.get("status") == "ok":
        out = dict(template_roll)
        out["method"] = "template"
        return out
    out = dict(contour_roll)
    out["method"] = "contour"
    return out
