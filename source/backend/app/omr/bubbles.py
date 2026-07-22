"""M09 — MCQ bubble reading (per-question A/B/C/D with blank/multi flagging)."""

from __future__ import annotations

import re

import numpy as np

from app.omr.bubble_refine import RefineContext, bubble_origin
from app.omr.omr_settings import (
    comfort_margin,
    comfort_ratio,
    hard_multi_margin,
    hard_multi_ratio,
    min_dominance_ratio,
    min_mark_margin,
    min_plausible_fill,
)
from app.omr.threshold import dynamic_threshold, fill_value_adaptive

STATUS_ANSWERED = "answered"
STATUS_BLANK = "blank"
STATUS_MULTI = "multi"

_Q_NUM = re.compile(r"(\d+)")


def _is_mcq_block(field_block) -> bool:
    # Roll/integer blocks use QTYPE_INT*; everything else is treated as MCQ.
    return not any(b.field_type.startswith("QTYPE_INT") for b in field_block.traverse_bubbles[0])


def _sheet_q_number(field_label: str) -> int | None:
    m = _Q_NUM.search(field_label)
    return int(m.group(1)) if m else None


def _clear_winner(top_val: float, second_val: float) -> bool:
    if top_val < min_plausible_fill():
        return False
    margin = top_val - second_val
    ratio = top_val / max(second_val, 1e-6)
    return margin >= min_mark_margin() or ratio >= min_dominance_ratio()


def is_hard_multi(q: dict) -> bool:
    """True when marks are genuinely ambiguous and need human review."""
    if q.get("status") != STATUS_MULTI:
        return False
    fills = sorted(q.get("fills", {}).values(), reverse=True)
    if len(fills) < 2:
        return False
    top, second = fills[0], fills[1]
    if top < min_plausible_fill() or second < min_plausible_fill():
        return False
    margin = top - second
    ratio = top / max(second, 1e-6)
    return margin < hard_multi_margin() and ratio < hard_multi_ratio()


def is_low_confidence(q: dict) -> bool:
    """Answered by auto-threshold but winning margin is uncomfortably small."""
    if q.get("status") != STATUS_ANSWERED:
        return False
    fills = sorted(q.get("fills", {}).values(), reverse=True)
    if len(fills) < 2:
        return False
    top, second = fills[0], fills[1]
    if not _clear_winner(top, second):
        return False
    margin = top - second
    ratio = top / max(second, 1e-6)
    return margin < comfort_margin() and ratio < comfort_ratio()


def read_mcq(
    gray: np.ndarray,
    template,
    refine: RefineContext | None = None,
) -> dict[int, dict]:
    """Read every MCQ question on the sheet.

    Returns: { sheet_question_no: {option, status, fills: {opt: val}} }
    keyed by the numeric part of the template field label (sheet question number).
    """
    raw: list[tuple[int, str, float, str]] = []  # (sheet_q, option, fill, label)
    all_fills: list[float] = []

    for field_block in template.field_blocks:
        if not field_block.traverse_bubbles or not _is_mcq_block(field_block):
            continue
        box_w, box_h = field_block.bubble_dimensions
        for question_bubbles in field_block.traverse_bubbles:
            label = question_bubbles[0].field_label
            sheet_q = _sheet_q_number(label)
            if sheet_q is None:
                continue
            for bubble in question_bubbles:
                bx = int(bubble.x + field_block.shift)
                by = int(bubble.y)
                rx, ry = bubble_origin(
                    refine, field_block.name, bx, by, box_w, box_h
                )
                val = fill_value_adaptive(gray, rx, ry, box_w, box_h)
                raw.append((sheet_q, str(bubble.field_value), val, label))
                all_fills.append(val)

    threshold = dynamic_threshold(all_fills)

    questions: dict[int, dict] = {}
    for sheet_q, option, val, _label in raw:
        q = questions.setdefault(sheet_q, {"fills": {}})
        q["fills"][option] = round(val, 1)

    for sheet_q, q in questions.items():
        fills = q["fills"]
        ranked = sorted(fills.items(), key=lambda item: -item[1])
        top_opt, top_val = ranked[0]
        second_val = ranked[1][1]
        marked_global = [opt for opt, val in fills.items() if val >= threshold]

        if _clear_winner(top_val, second_val):
            q["status"] = STATUS_ANSWERED
            q["option"] = top_opt
            q["marked"] = [top_opt]
        elif len(marked_global) >= 2:
            q["status"] = STATUS_MULTI
            q["option"] = "".join(sorted(marked_global))
            q["marked"] = marked_global
        elif len(marked_global) == 1:
            q["status"] = STATUS_ANSWERED
            q["option"] = marked_global[0]
            q["marked"] = marked_global
        else:
            q["status"] = STATUS_BLANK
            q["option"] = ""
            q["marked"] = []
    return questions
