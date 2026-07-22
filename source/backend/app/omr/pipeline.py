"""M09 — OMR read pipeline orchestrator.

image -> align (warp to pageDimensions) -> read roll + MCQ -> map sheet
questions to GLOBAL question numbers for the session -> flag anomalies and save
crops. Build a `SheetReader` once per batch (engine template is reused).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import cv2

from app.config import get_config
from app.omr import bubbles as mcq_reader
from app.omr import roll_number as roll_reader
from app.omr.align import warp_sheet
from app.omr.arbitration import arbitrate_mcq, arbitrate_roll
from app.omr.bubble_refine import build_refine_context
from app.omr.contour_read import build_contour_context, decode_roll_contour, read_mcq_contour
from app.omr.omr_settings import alignment_review_below, strict_review_enabled
from app.services import template_service

ANOMALY_MULTI = "multi"
ANOMALY_ROLL = "roll_ambiguous"
ANOMALY_ALIGNMENT = "alignment_failed"
ANOMALY_LOW_CONFIDENCE = "low_confidence"
ANOMALY_ALIGNMENT_REVIEW = "alignment_review"

MIN_ALIGNMENT_QUALITY = 0.55

_PAD = 6
_Q_NUM = re.compile(r"(\d+)")


def _alignment_anomaly(detected: str) -> dict[str, Any]:
    return {
        "global_q": 0,
        "sheet_q": 0,
        "type": ANOMALY_ALIGNMENT,
        "detected": detected,
        "crop_path": None,
    }


class SheetReader:
    """Reusable reader bound to one calibrated template (one batch)."""

    def __init__(self, template_dict: dict[str, Any], template_family: str):
        self.template, self.tuning_config = template_service.build_engine_template(
            template_dict, template_family
        )
        self._question_bbox: dict[int, tuple[int, int, int, int]] = {}
        self._roll_bbox: tuple[int, int, int, int] | None = None
        self._precompute_bboxes()

    def _precompute_bboxes(self) -> None:
        roll_pts: list[tuple[int, int]] = []
        for field_block in self.template.field_blocks:
            if not field_block.traverse_bubbles:
                continue
            box_w, box_h = field_block.bubble_dimensions
            is_roll = any(
                b.field_type.startswith("QTYPE_INT")
                for b in field_block.traverse_bubbles[0]
            )
            for field_bubbles in field_block.traverse_bubbles:
                xs = [b.x for b in field_bubbles]
                ys = [b.y for b in field_bubbles]
                bbox = (
                    min(xs) - _PAD,
                    min(ys) - _PAD,
                    max(xs) + box_w + _PAD,
                    max(ys) + box_h + _PAD,
                )
                if is_roll:
                    roll_pts.extend([(bbox[0], bbox[1]), (bbox[2], bbox[3])])
                else:
                    label = field_bubbles[0].field_label
                    m = _Q_NUM.search(label)
                    if m:
                        self._question_bbox[int(m.group(1))] = bbox
        if roll_pts:
            self._roll_bbox = (
                min(p[0] for p in roll_pts),
                min(p[1] for p in roll_pts),
                max(p[0] for p in roll_pts),
                max(p[1] for p in roll_pts),
            )

    def _save_crop(self, warped, bbox, out_path: Path) -> str | None:
        if bbox is None:
            return None
        h, w = warped.shape[:2]
        x0, y0, x1, y1 = bbox
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w, x1), min(h, y1)
        if x1 <= x0 or y1 <= y0:
            return None
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_path), warped[y0:y1, x0:x1])
        return str(out_path)

    def _read_sheet(self, warped, warp, alignment_quality: float, sheet_question_count: int):
        cfg = get_config().omr
        refine = build_refine_context(warped, self.template, warp)
        template_mcq = mcq_reader.read_mcq(warped, self.template, refine)
        template_roll = roll_reader.decode_roll(warped, self.template, refine)

        read_mode = cfg.read_mode
        grid = None
        thresh = None
        contour_mcq: dict[int, dict] = {}
        contour_roll: dict = {"roll_no": None, "status": roll_reader.ROLL_AMBIGUOUS, "columns": []}
        arb_meta: dict[str, Any] = {
            "read_method_summary": "template",
            "grid_confidence": 0.0,
            "contour_agreement_pct": 0.0,
            "fallback_used": False,
        }

        if read_mode in {"hybrid", "contour"}:
            thresh, grid = build_contour_context(warped, self.template)
            skip_contour = (
                cfg.perf.skip_contour_on_low_grid
                and grid.grid_confidence < cfg.contour.min_grid_confidence
                and read_mode == "hybrid"
            )
            if not skip_contour:
                contour_mcq, grid = read_mcq_contour(warped, self.template, thresh, grid)
                contour_roll = decode_roll_contour(warped, self.template, thresh, grid)

        if read_mode == "template":
            mcq = template_mcq
            roll = template_roll
        elif read_mode == "contour":
            mcq = contour_mcq or template_mcq
            roll = contour_roll
            arb_meta["read_method_summary"] = "contour"
        else:
            mcq, arb_meta = arbitrate_mcq(
                template_mcq,
                contour_mcq,
                grid=grid,
                alignment_quality=alignment_quality,
                sheet_question_count=sheet_question_count,
            )
            roll = arbitrate_roll(
                template_roll,
                contour_roll,
                fallback_used=arb_meta.get("fallback_used", False),
            )

        return mcq, roll, refine, grid, arb_meta, template_mcq, contour_mcq

    def process(
        self,
        image_path: str,
        global_q_start: int,
        sheet_question_count: int,
        crop_dir: Path,
        crop_prefix: str,
    ) -> dict[str, Any]:
        source_path = str(Path(image_path).resolve())
        warp = warp_sheet(image_path, self.template)
        if warp is None:
            return {
                "aligned": False,
                "roll_no": None,
                "roll_status": None,
                "answers": {},
                "per_question": [],
                "counts": {"answered": 0, "blank": 0, "multi": 0, "total": 0},
                "anomalies": [_alignment_anomaly("alignment failed: markers not found")],
                "alignment_quality": 0.0,
                "grid_refined": False,
                "source_path": source_path,
            }

        alignment_quality = round(warp.quality, 3)
        if alignment_quality < MIN_ALIGNMENT_QUALITY:
            return {
                "aligned": False,
                "roll_no": None,
                "roll_status": None,
                "answers": {},
                "per_question": [],
                "counts": {"answered": 0, "blank": 0, "multi": 0, "total": 0},
                "anomalies": [
                    _alignment_anomaly(f"low alignment quality: {alignment_quality}")
                ],
                "alignment_quality": alignment_quality,
                "grid_refined": False,
                "source_path": source_path,
            }

        warped = warp.image
        mcq, roll, refine, grid, arb_meta, template_mcq, contour_mcq = self._read_sheet(
            warped, warp, alignment_quality, sheet_question_count
        )

        strict = strict_review_enabled()
        review_below = alignment_review_below()

        answers: dict[int, str] = {}
        per_question: list[dict[str, Any]] = []
        anomalies: list[dict[str, Any]] = []
        counts = {"answered": 0, "blank": 0, "multi": 0, "total": 0}

        if strict and MIN_ALIGNMENT_QUALITY <= alignment_quality < review_below:
            anomalies.append(
                {
                    "global_q": 0,
                    "sheet_q": 0,
                    "type": ANOMALY_ALIGNMENT_REVIEW,
                    "detected": f"quality {alignment_quality}",
                    "crop_path": None,
                }
            )

        for sheet_q in range(1, sheet_question_count + 1):
            global_q = global_q_start + sheet_q - 1
            q = mcq.get(sheet_q)
            if q is None:
                continue
            status, option = q["status"], q["option"]

            if status == mcq_reader.STATUS_MULTI:
                if strict:
                    answers[global_q] = ""
                    counts["total"] += 1
                    counts[mcq_reader.STATUS_MULTI] = counts.get(mcq_reader.STATUS_MULTI, 0) + 1
                    per_question.append(
                        {
                            "global_q": global_q,
                            "sheet_q": sheet_q,
                            "option": option,
                            "status": status,
                            "method": q.get("method"),
                        }
                    )
                    crop = self._save_crop(
                        warped,
                        self._question_bbox.get(sheet_q),
                        crop_dir / f"{crop_prefix}_q{global_q}.png",
                    )
                    anomalies.append(
                        {
                            "global_q": global_q,
                            "sheet_q": sheet_q,
                            "type": ANOMALY_MULTI,
                            "detected": "".join(q.get("marked", [])),
                            "crop_path": crop,
                        }
                    )
                    continue
                if not mcq_reader.is_hard_multi(q):
                    ranked = sorted(q["fills"].items(), key=lambda item: -item[1])
                    option = ranked[0][0]
                    status = mcq_reader.STATUS_ANSWERED

            answers[global_q] = option
            counts["total"] += 1
            counts[status] = counts.get(status, 0) + 1
            per_question.append(
                {
                    "global_q": global_q,
                    "sheet_q": sheet_q,
                    "option": option,
                    "status": status,
                    "method": q.get("method"),
                }
            )

            if strict and status == mcq_reader.STATUS_ANSWERED and mcq_reader.is_low_confidence(q):
                crop = self._save_crop(
                    warped,
                    self._question_bbox.get(sheet_q),
                    crop_dir / f"{crop_prefix}_q{global_q}.png",
                )
                anomalies.append(
                    {
                        "global_q": global_q,
                        "sheet_q": sheet_q,
                        "type": ANOMALY_LOW_CONFIDENCE,
                        "detected": option,
                        "crop_path": crop,
                    }
                )
            elif status == mcq_reader.STATUS_MULTI and mcq_reader.is_hard_multi(q):
                crop = self._save_crop(
                    warped,
                    self._question_bbox.get(sheet_q),
                    crop_dir / f"{crop_prefix}_q{global_q}.png",
                )
                anomalies.append(
                    {
                        "global_q": global_q,
                        "sheet_q": sheet_q,
                        "type": ANOMALY_MULTI,
                        "detected": "".join(q.get("marked", [])),
                        "crop_path": crop,
                    }
                )

        if roll.get("status") != roll_reader.ROLL_OK:
            crop = self._save_crop(
                warped, self._roll_bbox, crop_dir / f"{crop_prefix}_roll.png"
            )
            anomalies.append(
                {
                    "global_q": 0,
                    "sheet_q": 0,
                    "type": ANOMALY_ROLL,
                    "detected": roll.get("roll_no"),
                    "crop_path": crop,
                }
            )

        return {
            "aligned": True,
            "roll_no": roll.get("roll_no"),
            "roll_status": roll.get("status"),
            "answers": answers,
            "per_question": per_question,
            "counts": counts,
            "anomalies": anomalies,
            "alignment_quality": alignment_quality,
            "grid_refined": refine.active,
            "source_path": source_path,
            "read_method_summary": arb_meta.get("read_method_summary"),
            "grid_confidence": arb_meta.get("grid_confidence"),
            "contour_agreement_pct": arb_meta.get("contour_agreement_pct"),
            "fallback_used": arb_meta.get("fallback_used"),
            "detected_bubbles": grid.detected_bubbles if grid else [],
            "template_mcq": template_mcq,
            "contour_mcq": contour_mcq,
        }
