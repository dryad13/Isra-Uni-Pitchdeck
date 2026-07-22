"""M09 — Bubble fill measurement + dynamic thresholding.

Fill value convention: `255 - mean(grayscale box)`, so a darker (filled) bubble
yields a HIGHER fill value. The dynamic threshold finds the widest gap in the
sorted fill values (the separation between the "empty" and "marked" clusters),
an approach borrowed from OMRChecker's global-threshold and open-mcr's adaptive
density idea. This avoids a brittle fixed cutoff across scans/printers.
"""

from __future__ import annotations

import numpy as np

from app.omr.omr_settings import min_plausible_fill, min_separation

# Backwards-compatible module-level aliases (tests may import these).
MIN_SEPARATION = 18.0
MIN_PLAUSIBLE_FILL = 40.0
# When the grid is slightly off, search this many pixels around each bubble centre.
BUBBLE_SEARCH_RADIUS = 3
# Only search neighbours when the centred sample is below this (avoids noise on blank sheets).
SEARCH_IF_BELOW = 55.0


def fill_value(gray: np.ndarray, x: int, y: int, w: int, h: int) -> float:
    """Mean darkness of a bubble box (0 = white/empty, 255 = solid black)."""
    h_img, w_img = gray.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(w_img, x + w), min(h_img, y + h)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    box = gray[y0:y1, x0:x1]
    if box.size == 0:
        return 0.0
    return 255.0 - float(box.mean())


def fill_value_search(
    gray: np.ndarray, x: int, y: int, w: int, h: int, radius: int = BUBBLE_SEARCH_RADIUS
) -> float:
    """Best fill value within a small neighbourhood (tolerates torn-page grid drift)."""
    best = 0.0
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            best = max(best, fill_value(gray, x + dx, y + dy, w, h))
    return best


def fill_value_adaptive(gray: np.ndarray, x: int, y: int, w: int, h: int) -> float:
    """Centre sample first; widen search only when the mark may be slightly off-grid."""
    centre = fill_value(gray, x, y, w, h)
    if centre >= SEARCH_IF_BELOW:
        return centre
    return max(centre, fill_value_search(gray, x, y, w, h))


def dynamic_threshold(values: list[float]) -> float:
    """Return a fill-value cutoff separating marked from empty bubbles.

    If no clear separation exists, return a high cutoff so nothing is marked
    (the strip is treated as empty/blank).
    """
    if not values:
        return 255.0
    vals = sorted(values)
    if len(vals) == 1:
        return vals[0] + 1.0

    max_gap = 0.0
    cut = 255.0
    for i in range(1, len(vals)):
        gap = vals[i] - vals[i - 1]
        if gap > max_gap:
            max_gap = gap
            cut = (vals[i] + vals[i - 1]) / 2.0

    if max_gap < min_separation():
        # No distinct marked cluster -> nothing should pass.
        return max(vals[-1] + 1.0, min_plausible_fill())
    return max(cut, min_plausible_fill())
