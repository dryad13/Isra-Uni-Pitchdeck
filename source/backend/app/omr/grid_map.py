"""Map detected bubble centroids to template slots."""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field

from app.omr.contour_detect import DetectedBubble, block_bounds

_Q_NUM = re.compile(r"(\d+)")


@dataclass
class MappedSlot:
    slot_id: str
    cx: float
    cy: float
    radius: float
    confidence: float
    sheet_q: int | None = None
    option: str | None = None
    contour: object = None


@dataclass
class BlockGridMap:
    block_name: str
    slots: dict[str, MappedSlot] = field(default_factory=dict)
    grid_confidence: float = 0.0
    expected_slots: int = 0
    matched_slots: int = 0


@dataclass
class SheetGridMap:
    blocks: dict[str, BlockGridMap] = field(default_factory=dict)
    detected_bubbles: list[dict] = field(default_factory=list)

    @property
    def grid_confidence(self) -> float:
        if not self.blocks:
            return 0.0
        return sum(b.grid_confidence for b in self.blocks.values()) / len(self.blocks)

    @property
    def detection_ratio(self) -> float:
        expected = sum(b.expected_slots for b in self.blocks.values())
        matched = sum(b.matched_slots for b in self.blocks.values())
        return matched / expected if expected else 0.0


def _nearest(
    centroids: list[tuple[int, int]],
    x: float,
    y: float,
    max_dist: float,
    used: set[int],
) -> tuple[int, int] | None:
    best_idx: int | None = None
    best_d2 = max_dist * max_dist
    for idx, (cx, cy) in enumerate(centroids):
        if idx in used:
            continue
        d2 = (cx - x) ** 2 + (cy - y) ** 2
        if d2 <= best_d2:
            best_d2 = d2
            best_idx = idx
    if best_idx is None:
        return None
    used.add(best_idx)
    return centroids[best_idx]


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


def map_block_grid(
    field_block,
    detected: list[DetectedBubble],
    max_match_distance: float = 14.0,
) -> BlockGridMap:
    centroids = [(b.cx, b.cy) for b in detected]
    contour_by_centroid = {(b.cx, b.cy): b for b in detected}
    box_w, box_h = field_block.bubble_dimensions
    radius = max(box_w, box_h) / 2.0
    used: set[int] = set()
    slots: dict[str, MappedSlot] = {}
    expected = 0
    matched = 0

    for question_bubbles in field_block.traverse_bubbles:
        label = question_bubbles[0].field_label
        sheet_q = _sheet_q_number(label)
        for bubble in question_bubbles:
            expected += 1
            ex = bubble.x + field_block.shift + box_w / 2.0
            ey = bubble.y + box_h / 2.0
            slot_id = f"{field_block.name}:{label}:{bubble.field_value}"
            hit = _nearest(centroids, ex, ey, max_match_distance, used)
            if hit is None:
                slots[slot_id] = MappedSlot(
                    slot_id=slot_id,
                    cx=ex,
                    cy=ey,
                    radius=radius,
                    confidence=0.0,
                    sheet_q=sheet_q,
                    option=str(bubble.field_value),
                )
                continue
            matched += 1
            det = contour_by_centroid.get(hit)
            slots[slot_id] = MappedSlot(
                slot_id=slot_id,
                cx=float(hit[0]),
                cy=float(hit[1]),
                radius=radius,
                confidence=1.0,
                sheet_q=sheet_q,
                option=str(bubble.field_value),
                contour=det.contour if det else None,
            )

    confidence = matched / expected if expected else 0.0
    return BlockGridMap(
        block_name=field_block.name,
        slots=slots,
        grid_confidence=confidence,
        expected_slots=expected,
        matched_slots=matched,
    )


def build_sheet_grid_map(
    template,
    block_detections: dict[str, list[DetectedBubble]],
    max_match_distance: float = 14.0,
) -> SheetGridMap:
    sheet = SheetGridMap()
    for field_block in template.field_blocks:
        if not field_block.traverse_bubbles:
            continue
        if not (_is_mcq_block(field_block) or _is_roll_block(field_block)):
            continue
        detected = block_detections.get(field_block.name, [])
        block_map = map_block_grid(field_block, detected, max_match_distance)
        sheet.blocks[field_block.name] = block_map
        x0, y0, x1, y1 = block_bounds(field_block)
        for b in detected:
            sheet.detected_bubbles.append(
                {
                    "block": field_block.name,
                    "cx": b.cx,
                    "cy": b.cy,
                    "w": b.w,
                    "h": b.h,
                    "bounds": [x0, y0, x1, y1],
                }
            )
    return sheet
