"""M09 — Roll-number decode from the 6-digit bubble matrix (bubbles only).

Barcodes are intentionally ignored (per requirement). Each roll column is a
0-9 vertical strip; exactly one bubble should be marked per column.
"""

from __future__ import annotations

import numpy as np

from app.omr.bubble_refine import RefineContext, bubble_origin
from app.omr.threshold import MIN_PLAUSIBLE_FILL, dynamic_threshold, fill_value_adaptive

ROLL_OK = "ok"
ROLL_AMBIGUOUS = "ambiguous"


def _is_roll_block(field_block) -> bool:
    return bool(field_block.traverse_bubbles) and any(
        b.field_type.startswith("QTYPE_INT") for b in field_block.traverse_bubbles[0]
    )


def decode_roll(gray: np.ndarray, template, refine: RefineContext | None = None) -> dict:
    """Return {roll_no, status, columns:[{label, digit, marked}]}.

    `roll_no` is a string; ambiguous/blank columns are rendered as '?'.
    """
    columns: list[dict] = []
    all_fills: list[float] = []
    raw_columns: list[tuple[str, list[tuple[str, float]]]] = []

    for field_block in template.field_blocks:
        if not _is_roll_block(field_block):
            continue
        box_w, box_h = field_block.bubble_dimensions
        for column_bubbles in field_block.traverse_bubbles:
            label = column_bubbles[0].field_label
            digit_fills: list[tuple[str, float]] = []
            for bubble in column_bubbles:
                bx = int(bubble.x + field_block.shift)
                by = int(bubble.y)
                rx, ry = bubble_origin(
                    refine, field_block.name, bx, by, box_w, box_h
                )
                val = fill_value_adaptive(gray, rx, ry, box_w, box_h)
                digit_fills.append((str(bubble.field_value), val))
                all_fills.append(val)
            raw_columns.append((label, digit_fills))

    if not raw_columns:
        return {"roll_no": None, "status": ROLL_AMBIGUOUS, "columns": []}

    threshold = dynamic_threshold(all_fills)
    digits: list[str] = []
    status = ROLL_OK
    for label, digit_fills in raw_columns:
        ranked = sorted(digit_fills, key=lambda item: -item[1])
        top_digit, top_val = ranked[0]
        second_val = ranked[1][1] if len(ranked) > 1 else 0.0
        marked = [d for d, val in digit_fills if val >= threshold]
        if len(marked) == 1:
            digit = marked[0]
        elif top_val >= MIN_PLAUSIBLE_FILL and (
            top_val - second_val >= 18.0 or top_val >= second_val * 1.18
        ):
            digit = top_digit
        else:
            digit = "?"
            status = ROLL_AMBIGUOUS
        digits.append(digit)
        columns.append({"label": label, "digit": digit, "marked": marked})

    roll_no = "".join(digits)
    return {"roll_no": roll_no, "status": status, "columns": columns}
