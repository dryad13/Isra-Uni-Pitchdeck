"""Contour-based MCQ and roll reading using mask pixel counts."""

from __future__ import annotations

import re

import cv2
import numpy as np

from app.config import get_config
from app.omr import bubbles as template_bubbles
from app.omr.contour_detect import build_otsu_thresh, detect_block_bubbles
from app.omr.grid_map import SheetGridMap, build_sheet_grid_map, map_block_grid
from app.omr import roll_number as roll_reader

_Q_NUM = re.compile(r"(\d+)")


def _is_mcq_block(field_block) -> bool:
    return bool(field_block.traverse_bubbles) and not any(
        b.field_type.startswith("QTYPE_INT") for b in field_block.traverse_bubbles[0]
    )


def _is_roll_block(field_block) -> bool:
    return bool(field_block.traverse_bubbles) and any(
        b.field_type.startswith("QTYPE_INT") for b in field_block.traverse_bubbles[0]
    )


def _sheet_q_number(field_label: str) -> int | None:
    m = _Q_NUM.search(field_label)
    return int(m.group(1)) if m else None


def _mask_fill(thresh: np.ndarray, cx: float, cy: float, radius: float) -> float:
    h, w = thresh.shape[:2]
    r = max(4, int(radius))
    x0 = max(0, int(cx - r))
    y0 = max(0, int(cy - r))
    x1 = min(w, int(cx + r))
    y1 = min(h, int(cy + r))
    if x1 <= x0 or y1 <= y0:
        return 0.0
    mask = np.zeros(thresh.shape, dtype=np.uint8)
    cv2.circle(mask, (int(cx), int(cy)), r, 255, -1)
    return float(cv2.countNonZero(cv2.bitwise_and(thresh, thresh, mask=mask)))


def _resolve_question(fills: dict[str, float], min_mark_pixels: float) -> dict:
    ranked = sorted(fills.items(), key=lambda item: -item[1])
    top_opt, top_val = ranked[0]
    second_val = ranked[1][1] if len(ranked) > 1 else 0.0
    marked = [opt for opt, val in fills.items() if val >= min_mark_pixels]

    if template_bubbles._clear_winner(top_val, second_val):
        return {
            "status": template_bubbles.STATUS_ANSWERED,
            "option": top_opt,
            "marked": [top_opt],
            "fills": fills,
            "read_method": "contour",
        }
    if len(marked) >= 2:
        return {
            "status": template_bubbles.STATUS_MULTI,
            "option": "".join(sorted(marked)),
            "marked": marked,
            "fills": fills,
            "read_method": "contour",
        }
    if len(marked) == 1:
        return {
            "status": template_bubbles.STATUS_ANSWERED,
            "option": marked[0],
            "marked": marked,
            "fills": fills,
            "read_method": "contour",
        }
    return {
        "status": template_bubbles.STATUS_BLANK,
        "option": "",
        "marked": [],
        "fills": fills,
        "read_method": "contour",
    }


def build_contour_context(gray: np.ndarray, template) -> tuple[np.ndarray, SheetGridMap]:
    cfg = get_config().omr
    thresh = build_otsu_thresh(gray) if cfg.perf.shared_otsu else None
    if thresh is None:
        thresh = build_otsu_thresh(gray)

    block_detections: dict[str, list] = {}
    for field_block in template.field_blocks:
        if not field_block.traverse_bubbles:
            continue
        if not (_is_mcq_block(field_block) or _is_roll_block(field_block)):
            continue
        block_detections[field_block.name] = detect_block_bubbles(
            gray, field_block, thresh if cfg.perf.roi_contours_only else None
        )

    grid = build_sheet_grid_map(
        template,
        block_detections,
        max_match_distance=cfg.contour.max_match_distance_px,
    )
    return thresh, grid


def read_mcq_contour(
    gray: np.ndarray,
    template,
    thresh: np.ndarray | None = None,
    grid: SheetGridMap | None = None,
) -> tuple[dict[int, dict], SheetGridMap]:
    cfg = get_config().omr
    if thresh is None or grid is None:
        thresh, grid = build_contour_context(gray, template)

    raw: dict[int, dict[str, float]] = {}

    for field_block in template.field_blocks:
        if not _is_mcq_block(field_block):
            continue
        block_map = grid.blocks.get(field_block.name)
        if block_map is None:
            block_map = map_block_grid(
                field_block,
                detect_block_bubbles(gray, field_block, thresh),
                cfg.contour.max_match_distance_px,
            )
            grid.blocks[field_block.name] = block_map

        for question_bubbles in field_block.traverse_bubbles:
            label = question_bubbles[0].field_label
            sheet_q = _sheet_q_number(label)
            if sheet_q is None:
                continue
            fills = raw.setdefault(sheet_q, {})
            for bubble in question_bubbles:
                slot_id = f"{field_block.name}:{label}:{bubble.field_value}"
                slot = block_map.slots.get(slot_id)
                if slot is None:
                    continue
                val = _mask_fill(thresh, slot.cx, slot.cy, slot.radius)
                fills[str(bubble.field_value)] = round(val, 1)

    from app.omr.threshold import dynamic_threshold

    all_fills = [val for fills in raw.values() for val in fills.values()]
    mark_threshold = max(cfg.contour.min_mark_pixels, dynamic_threshold(all_fills))

    questions: dict[int, dict] = {}
    for sheet_q, fills in raw.items():
        if not fills:
            continue
        questions[sheet_q] = _resolve_question(fills, mark_threshold)
    return questions, grid


def decode_roll_contour(
    gray: np.ndarray,
    template,
    thresh: np.ndarray | None = None,
    grid: SheetGridMap | None = None,
) -> dict:
    cfg = get_config().omr
    if thresh is None or grid is None:
        thresh, grid = build_contour_context(gray, template)

    columns: list[dict] = []
    all_fills: list[float] = []
    raw_columns: list[tuple[str, list[tuple[str, float]]]] = []

    for field_block in template.field_blocks:
        if not _is_roll_block(field_block):
            continue
        block_map = grid.blocks.get(field_block.name)
        if block_map is None:
            block_map = map_block_grid(
                field_block,
                detect_block_bubbles(gray, field_block, thresh),
                cfg.contour.max_match_distance_px,
            )
            grid.blocks[field_block.name] = block_map

        for column_bubbles in field_block.traverse_bubbles:
            label = column_bubbles[0].field_label
            digit_fills: list[tuple[str, float]] = []
            for bubble in column_bubbles:
                slot_id = f"{field_block.name}:{label}:{bubble.field_value}"
                slot = block_map.slots.get(slot_id)
                if slot is None:
                    digit_fills.append((str(bubble.field_value), 0.0))
                    continue
                val = _mask_fill(thresh, slot.cx, slot.cy, slot.radius)
                digit_fills.append((str(bubble.field_value), val))
                all_fills.append(val)
            raw_columns.append((label, digit_fills))

    if not raw_columns:
        return {"roll_no": None, "status": roll_reader.ROLL_AMBIGUOUS, "columns": []}

    from app.omr.threshold import dynamic_threshold, MIN_PLAUSIBLE_FILL

    threshold = dynamic_threshold(all_fills)
    digits: list[str] = []
    status = roll_reader.ROLL_OK
    for label, digit_fills in raw_columns:
        ranked = sorted(digit_fills, key=lambda item: -item[1])
        top_digit, top_val = ranked[0]
        second_val = ranked[1][1] if len(ranked) > 1 else 0.0
        marked = [d for d, val in digit_fills if val >= cfg.contour.min_mark_pixels]
        if len(marked) == 1:
            digit = marked[0]
        elif top_val >= MIN_PLAUSIBLE_FILL and (
            top_val - second_val >= 18.0 or top_val >= second_val * 1.18
        ):
            digit = top_digit
        else:
            digit = "?"
            status = roll_reader.ROLL_AMBIGUOUS
        digits.append(digit)
        columns.append({"label": label, "digit": digit, "marked": marked})

    roll_no = "".join(digits)
    return {"roll_no": roll_no, "status": status, "columns": columns, "read_method": "contour"}
