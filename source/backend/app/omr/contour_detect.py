"""Contour-based bubble detection on warped scans (PyImageSearch-style)."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class DetectedBubble:
    cx: int
    cy: int
    w: int
    h: int
    contour: np.ndarray | None = None


def block_bounds(field_block, pad: int = 14) -> tuple[int, int, int, int]:
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


def build_otsu_thresh(gray: np.ndarray) -> np.ndarray:
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    return thresh


def detect_bubbles_in_roi(
    gray: np.ndarray,
    thresh: np.ndarray | None,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    *,
    min_size: int = 9,
    max_size: int = 30,
    min_aspect: float = 0.65,
    max_aspect: float = 1.45,
) -> list[DetectedBubble]:
    """Return bubble detections in full-image coordinates."""
    h_img, w_img = gray.shape[:2]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w_img, x1), min(h_img, y1)
    if x1 - x0 < 20 or y1 - y0 < 20:
        return []

    roi_gray = gray[y0:y1, x0:x1]
    if thresh is None:
        blur = cv2.GaussianBlur(roi_gray, (5, 5), 0)
        _, roi_thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    else:
        roi_thresh = thresh[y0:y1, x0:x1]

    contours, _ = cv2.findContours(roi_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out: list[DetectedBubble] = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w < min_size or h < min_size or w > max_size or h > max_size:
            continue
        ar = w / float(h)
        if ar < min_aspect or ar > max_aspect:
            continue
        out.append(
            DetectedBubble(
                cx=x0 + x + w // 2,
                cy=y0 + y + h // 2,
                w=w,
                h=h,
                contour=cnt,
            )
        )
    return out


def detect_block_bubbles(
    gray: np.ndarray,
    field_block,
    thresh: np.ndarray | None = None,
) -> list[DetectedBubble]:
    box_w, box_h = field_block.bubble_dimensions
    min_size = max(6, int(min(box_w, box_h) * 0.55))
    max_size = max(min_size + 4, int(max(box_w, box_h) * 1.8))
    x0, y0, x1, y1 = block_bounds(field_block)
    return detect_bubbles_in_roi(
        gray,
        thresh,
        x0,
        y0,
        x1,
        y1,
        min_size=min_size,
        max_size=max_size,
    )


def centroids_from_detected(detected: list[DetectedBubble]) -> list[tuple[int, int]]:
    return [(b.cx, b.cy) for b in detected]
