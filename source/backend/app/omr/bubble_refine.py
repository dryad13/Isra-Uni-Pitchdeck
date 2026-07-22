"""Hybrid bubble localization — snap template coordinates to detected contours.

When marker alignment is imperfect (torn pages, damaged corners), reading at
fixed template coordinates bleeds into neighbouring bubbles. This module finds
bubble-like contours on the warped sheet (PyImageSearch-style) and nudges each
read position toward the nearest detected ring centre within the block.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

import cv2
import numpy as np

from app.omr.align import WarpResult

# Minimum contour matches before applying a block-level offset.
_MIN_BLOCK_MATCHES = 10
# Max distance (px) from expected centre to accept a contour as the same bubble.
_MAX_MATCH_DIST = 16
# Max snap distance (px) from offset-adjusted template position.
_MAX_SNAP_DIST = 12
# Reject offset outliers beyond this from the block median (px).
_MAX_OFFSET_OUTLIER = 8
# On good alignment, ignore tiny contour drift (noise).
_MIN_APPLY_OFFSET = 2.0


@dataclass
class RefineContext:
    """Optional per-block drift correction derived from contour detection."""

    block_offsets: dict[str, tuple[float, float]] = field(default_factory=dict)
    block_centroids: dict[str, list[tuple[int, int]]] = field(default_factory=dict)
    active: bool = False


def _is_mcq_block(field_block) -> bool:
    return bool(field_block.traverse_bubbles) and not any(
        b.field_type.startswith("QTYPE_INT") for b in field_block.traverse_bubbles[0]
    )


def _is_roll_block(field_block) -> bool:
    return bool(field_block.traverse_bubbles) and any(
        b.field_type.startswith("QTYPE_INT") for b in field_block.traverse_bubbles[0]
    )


def _detect_centroids(
    gray: np.ndarray,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    min_size: int = 9,
    max_size: int = 30,
) -> list[tuple[int, int]]:
    """Return (cx, cy) bubble centres in full-image coordinates."""
    h_img, w_img = gray.shape[:2]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w_img, x1), min(h_img, y1)
    if x1 - x0 < 20 or y1 - y0 < 20:
        return []

    roi = gray[y0:y1, x0:x1]
    blur = cv2.GaussianBlur(roi, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    centres: list[tuple[int, int]] = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w < min_size or h < min_size or w > max_size or h > max_size:
            continue
        ar = w / float(h)
        if ar < 0.65 or ar > 1.45:
            continue
        cx = x0 + x + w // 2
        cy = y0 + y + h // 2
        centres.append((cx, cy))
    return centres


def _block_bounds(field_block, pad: int = 14) -> tuple[int, int, int, int]:
    box_w, box_h = field_block.bubble_dimensions
    xs: list[int] = []
    ys: list[int] = []
    for question_bubbles in field_block.traverse_bubbles:
        for bubble in question_bubbles:
            xs.append(int(bubble.x + field_block.shift))
            ys.append(int(bubble.y))
            xs.append(int(bubble.x + field_block.shift + box_w))
            ys.append(int(bubble.y + box_h))
    return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad


def _nearest(
    centroids: list[tuple[int, int]], x: float, y: float, max_dist: float
) -> tuple[int, int] | None:
    best: tuple[int, int] | None = None
    best_d2 = max_dist * max_dist
    for cx, cy in centroids:
        d2 = (cx - x) ** 2 + (cy - y) ** 2
        if d2 <= best_d2:
            best_d2 = d2
            best = (cx, cy)
    return best


def _median_offset(
    field_block,
    centroids: list[tuple[int, int]],
    min_matches: int,
) -> tuple[float, float] | None:
    box_w, box_h = field_block.bubble_dimensions
    pairs: list[tuple[float, float]] = []
    for question_bubbles in field_block.traverse_bubbles:
        for bubble in question_bubbles:
            ex = bubble.x + field_block.shift + box_w / 2.0
            ey = bubble.y + box_h / 2.0
            hit = _nearest(centroids, ex, ey, _MAX_MATCH_DIST)
            if hit is None:
                continue
            pairs.append((hit[0] - ex, hit[1] - ey))

    if len(pairs) < min_matches:
        return None

    med_dx = statistics.median(p[0] for p in pairs)
    med_dy = statistics.median(p[1] for p in pairs)
    filtered = [
        p
        for p in pairs
        if abs(p[0] - med_dx) <= _MAX_OFFSET_OUTLIER and abs(p[1] - med_dy) <= _MAX_OFFSET_OUTLIER
    ]
    if len(filtered) < min_matches:
        filtered = pairs

    return (
        float(statistics.median(p[0] for p in filtered)),
        float(statistics.median(p[1] for p in filtered)),
    )


def build_refine_context(gray: np.ndarray, template, warp: WarpResult | None) -> RefineContext:
    """Detect bubbles on the warped sheet and compute per-block drift corrections."""
    ctx = RefineContext()
    if gray is None:
        return ctx

    # Always attempt refinement; only activate blocks with enough contour matches.
    force = warp is not None and (
        warp.corners_repaired
        or warp.quality < 0.72
        or min(warp.marker_scores[2], warp.marker_scores[3]) < 0.55
    )

    for field_block in template.field_blocks:
        if not field_block.traverse_bubbles:
            continue
        is_mcq = _is_mcq_block(field_block)
        is_roll = _is_roll_block(field_block)
        if not is_mcq and not is_roll:
            continue

        x0, y0, x1, y1 = _block_bounds(field_block)
        centroids = _detect_centroids(gray, x0, y0, x1, y1)
        if not centroids:
            continue

        min_matches = _MIN_BLOCK_MATCHES if is_mcq else 6
        offset = _median_offset(field_block, centroids, min_matches)
        if offset is None:
            if not force:
                continue
            ctx.block_centroids[field_block.name] = centroids
            ctx.active = True
            continue

        apply_offset = force or abs(offset[0]) >= _MIN_APPLY_OFFSET or abs(offset[1]) >= _MIN_APPLY_OFFSET
        if apply_offset:
            ctx.block_offsets[field_block.name] = offset
        ctx.block_centroids[field_block.name] = centroids
        ctx.active = True

    return ctx


def bubble_origin(
    ctx: RefineContext | None,
    block_name: str,
    x: int,
    y: int,
    box_w: int,
    box_h: int,
) -> tuple[int, int]:
    """Top-left (x, y) for reading a bubble, with optional refine/snap."""
    if ctx is None or not ctx.active:
        return x, y

    ox, oy = ctx.block_offsets.get(block_name, (0.0, 0.0))
    cx = x + box_w / 2.0 + ox
    cy = y + box_h / 2.0 + oy

    centroids = ctx.block_centroids.get(block_name)
    if centroids:
        hit = _nearest(centroids, cx, cy, _MAX_SNAP_DIST)
        if hit is not None:
            return int(hit[0] - box_w / 2), int(hit[1] - box_h / 2)

    return int(x + ox), int(y + oy)
