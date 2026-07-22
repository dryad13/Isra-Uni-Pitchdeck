"""M09 — Alignment: warp a raw scan into pageDimensions space.

Reuses the vendored OMRChecker CropOnMarkers bullseye detection + perspective
warp, then resizes to the template's pageDimensions so bubble coordinates from
the calibrated template line up with the read image.

When bottom corner markers are obscured by filled bubbles (common on pre-marked
key sheets), bottom corners are extrapolated from the blank-template reference
using the reliably detected top markers.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

# Bottom marker scores below this are treated as unreliable.
_MIN_MARKER_SCORE = 0.55
# Allow reconstruction when at least one corner is this confident (torn pages).
_MIN_ANCHOR_SCORE = 0.38
# Bottom corners should sit in the lower portion of the processing canvas.
_MIN_BOTTOM_Y_RATIO = 0.72


@dataclass(frozen=True)
class WarpResult:
    """Warped page image plus alignment diagnostics."""

    image: np.ndarray
    marker_scores: tuple[float, float, float, float]
    quality: float
    corners_repaired: bool


def _alignment_quality(scores: list[float], corners_repaired: bool) -> float:
    if not scores:
        return 0.0
    top = min(scores[0], scores[1])
    bottom = min(scores[2], scores[3])
    if corners_repaired:
        return min(top, bottom * 0.85)
    return min(top, bottom)


def _load_image_utils():
    from src.utils.image import ImageUtils

    return ImageUtils


def _preprocessed_gray(gray: np.ndarray, crop_on_markers) -> np.ndarray:
    ImageUtils = _load_image_utils()
    if crop_on_markers.apply_erode_subtract:
        return ImageUtils.normalize_util(gray)
    eroded = cv2.erode(gray, kernel=np.ones((5, 5)), iterations=5)
    return ImageUtils.normalize_util(gray - eroded)


def _detect_marker_centres(
    image_eroded_sub: np.ndarray, crop_on_markers
) -> tuple[list[list[float]], list[float], float | None]:
    """Return (centres TL/TR/BL/BR, match scores, best scale)."""
    ImageUtils = _load_image_utils()
    h1, w1 = image_eroded_sub.shape[:2]
    midh, midw = h1 // 3, w1 // 2
    origins = [[0, 0], [midw, 0], [0, midh], [midw, midh]]
    quads = [
        image_eroded_sub[0:midh, 0:midw],
        image_eroded_sub[0:midh, midw:w1],
        image_eroded_sub[midh:h1, 0:midw],
        image_eroded_sub[midh:h1, midw:w1],
    ]

    best_scale, _all_max_t = crop_on_markers.getBestMatch(image_eroded_sub)
    if best_scale is None:
        return [], [], None

    optimal_marker = ImageUtils.resize_util_h(
        crop_on_markers.marker,
        u_height=int(crop_on_markers.marker.shape[0] * best_scale),
    )
    _h, w = optimal_marker.shape[:2]
    centres: list[list[float]] = []
    scores: list[float] = []
    for k in range(4):
        res = cv2.matchTemplate(quads[k], optimal_marker, cv2.TM_CCOEFF_NORMED)
        max_t = float(res.max())
        scores.append(max_t)
        pt = np.argwhere(res == max_t)[0]
        pt = [int(pt[1]), int(pt[0])]
        pt[0] += origins[k][0]
        pt[1] += origins[k][1]
        centres.append([pt[0] + w / 2, pt[1] + _h / 2])
    return centres, scores, best_scale


def _needs_bottom_extrapolation(
    centres: list[list[float]], scores: list[float], img_height: int
) -> bool:
    if len(centres) != 4 or len(scores) != 4:
        return True
    if min(scores[2], scores[3]) < _MIN_MARKER_SCORE:
        return True
    bottom_y = max(centres[2][1], centres[3][1])
    if bottom_y < img_height * _MIN_BOTTOM_Y_RATIO:
        return True
    # Both bottom markers at the same row far from the page bottom → false match.
    if (
        abs(centres[2][1] - centres[3][1]) < 40
        and bottom_y < img_height * 0.85
    ):
        return True
    return False


def _needs_corner_repair(scores: list[float]) -> bool:
    return any(s < _MIN_MARKER_SCORE for s in scores)


def _repair_corners(
    centres: list[list[float]],
    scores: list[float],
    reference: list[list[float]],
) -> list[list[float]] | None:
    """Infer missing/damaged corner markers from good corners + blank-template geometry."""
    if len(centres) != 4 or len(scores) != 4 or len(reference) != 4:
        return None
    if max(scores) < _MIN_ANCHOR_SCORE:
        return None

    c = [np.array(p, dtype=float) for p in centres]
    r = [np.array(p, dtype=float) for p in reference]
    out = [p.copy() for p in c]

    tl_tr = r[1] - r[0]
    tl_bl = r[2] - r[0]
    tr_br = r[3] - r[1]
    bl_br = r[3] - r[2]

    # Offsets from anchor corner -> target corner (reference geometry).
    offsets: dict[int, dict[int, np.ndarray]] = {
        0: {1: tl_tr, 2: tl_bl, 3: tl_bl + bl_br},
        1: {0: -tl_tr, 2: tl_bl - tl_tr, 3: tr_br},
        2: {0: -tl_bl, 1: tl_tr - tl_bl, 3: bl_br},
        3: {1: -tr_br, 2: -bl_br, 0: -(tl_bl + bl_br)},
    }

    anchors = [i for i in range(4) if scores[i] >= _MIN_MARKER_SCORE]
    if not anchors:
        anchors = [int(np.argmax(scores))]

    for i in range(4):
        if scores[i] >= _MIN_MARKER_SCORE:
            continue
        anchor = max(anchors, key=lambda idx: scores[idx])
        if i not in offsets.get(anchor, {}):
            return None
        out[i] = out[anchor] + offsets[anchor][i]

    return [list(p) for p in out]


def _reference_corners_from_pp(crop_on_markers, processing_width: int, processing_height: int):
    cache_key = (
        str(crop_on_markers.relative_dir),
        int(processing_width),
        int(processing_height),
    )
    if cache_key in _REFERENCE_CACHE:
        return _REFERENCE_CACHE[cache_key]

    ImageUtils = _load_image_utils()
    blank_path = Path(crop_on_markers.relative_dir) / "blank_template.png"
    if not blank_path.exists():
        return None

    gray = cv2.imread(str(blank_path), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        return None

    resized = ImageUtils.resize_util(gray, processing_width, processing_height)
    prepped = _preprocessed_gray(resized, crop_on_markers)
    centres, scores, scale = _detect_marker_centres(prepped, crop_on_markers)
    if scale is None or len(centres) != 4:
        return None
    _REFERENCE_CACHE[cache_key] = (centres, scores)
    return centres, scores


_REFERENCE_CACHE: dict[tuple[str, int, int], tuple[list[list[float]], list[float]]] = {}


def _extrapolate_bottom_corners(
    top_centres: list[list[float]],
    reference_centres: list[list[float]],
) -> list[list[float]]:
    off_bl = np.array(reference_centres[2]) - np.array(reference_centres[0])
    off_br = np.array(reference_centres[3]) - np.array(reference_centres[1])
    return [
        top_centres[0],
        top_centres[1],
        list(np.array(top_centres[0]) + off_bl),
        list(np.array(top_centres[1]) + off_br),
    ]


def _apply_corner_repair(
    centres: list[list[float]],
    scores: list[float],
    reference_centres: list[list[float]],
    img_height: int,
) -> list[list[float]] | None:
    if _needs_corner_repair(scores):
        repaired = _repair_corners(centres, scores, reference_centres)
        if repaired is not None:
            return repaired
    if _needs_bottom_extrapolation(centres, scores, img_height):
        return _extrapolate_bottom_corners(centres[:2], reference_centres)
    return centres


def warp_sheet(image_path: str, template) -> WarpResult | None:
    """Align a scan to pageDimensions and return the warped image + marker diagnostics."""
    ImageUtils = _load_image_utils()
    gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        return None

    if not template.pre_processors:
        return None
    crop_on_markers = template.pre_processors[0]
    tuning = template.image_instance_ops.tuning_config
    proc_w = int(tuning.dimensions.processing_width)
    proc_h = int(tuning.dimensions.processing_height)

    resized = ImageUtils.resize_util(gray, proc_w, proc_h)
    prepped = _preprocessed_gray(resized, crop_on_markers)
    centres, scores, scale = _detect_marker_centres(prepped, crop_on_markers)
    if scale is None or len(centres) != 4:
        return None

    if max(scores) < _MIN_ANCHOR_SCORE:
        return None

    corners_repaired = _needs_corner_repair(scores) or _needs_bottom_extrapolation(
        centres, scores, prepped.shape[0]
    )

    ref = _reference_corners_from_pp(crop_on_markers, proc_w, proc_h)
    if ref is None:
        if min(scores[0], scores[1]) < crop_on_markers.min_matching_threshold:
            return None
    else:
        reference_centres, _ref_scores = ref
        repaired = _apply_corner_repair(
            centres, scores, reference_centres, prepped.shape[0]
        )
        if repaired is None:
            return None
        centres = repaired

    warped = ImageUtils.four_point_transform(resized, np.array(centres))
    if warped is None:
        return None

    page_w, page_h = template.page_dimensions
    image = cv2.resize(warped, (int(page_w), int(page_h)))
    score_tuple = (float(scores[0]), float(scores[1]), float(scores[2]), float(scores[3]))
    return WarpResult(
        image=image,
        marker_scores=score_tuple,
        quality=_alignment_quality(scores, corners_repaired),
        corners_repaired=corners_repaired,
    )


def warp_to_page(image_path: str, template) -> np.ndarray | None:
    """Return the warped grayscale sheet at pageDimensions, or None if alignment fails."""
    result = warp_sheet(image_path, template)
    return result.image if result is not None else None
