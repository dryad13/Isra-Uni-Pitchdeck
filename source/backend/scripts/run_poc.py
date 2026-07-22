#!/usr/bin/env python3
"""OMR Engine POC — validate alignment and template structure on Isra 150Q blank."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2

BACKEND_ROOT = Path(__file__).resolve().parents[1]
# OMRChecker package root (contains src/)
ENGINE_ROOT = BACKEND_ROOT / "omr_engine"
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from src.defaults import CONFIG_DEFAULTS  # noqa: E402
from src.template import Template  # noqa: E402
from src.utils.parsing import open_config_with_defaults  # noqa: E402


SAMPLE_DIR = BACKEND_ROOT.parent / "samples" / "isra_150q"
BLANK_IMAGE = SAMPLE_DIR / "blank_template.png"
TEMPLATE_PATH = SAMPLE_DIR / "template.json"
CONFIG_PATH = SAMPLE_DIR / "config.json"


def summarize_template(template: Template) -> dict:
    blocks = []
    for block in template.field_blocks:
        blocks.append(
            {
                "name": block.name,
                "origin": block.origin,
                "dimensions": block.dimensions,
                "labels": len(block.parsed_field_labels),
                "bubbles_per_label": len(block.traverse_bubbles[0]) if block.traverse_bubbles else 0,
            }
        )
    return {
        "page_dimensions": template.page_dimensions,
        "bubble_dimensions": template.bubble_dimensions,
        "preprocessors": [pp.__class__.__name__ for pp in template.pre_processors],
        "field_blocks": blocks,
        "output_columns": len(template.output_columns),
    }


def run_alignment_check(template: Template, tuning_config, image_path: Path) -> dict:
    gray = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    original_shape = gray.shape[:2]
    warped = template.image_instance_ops.apply_preprocessors(str(image_path), gray, template)
    aligned = warped is not None
    result = {
        "input_resolution": {"height": original_shape[0], "width": original_shape[1]},
        "alignment_success": aligned,
    }
    if aligned:
        result["warped_resolution"] = {"height": warped.shape[0], "width": warped.shape[1]}
        layout = template.image_instance_ops.draw_template_layout(
            warped, template, shifted=False, border=2
        )
        out_path = SAMPLE_DIR / "poc_layout_overlay.png"
        cv2.imwrite(str(out_path), layout)
        result["layout_overlay"] = str(out_path)
    return result


def main() -> int:
    print("=== Isra 150Q OMR POC ===")
    print(f"Sample dir: {SAMPLE_DIR}")

    if not BLANK_IMAGE.exists():
        print(f"ERROR: missing blank template at {BLANK_IMAGE}")
        return 1
    if not TEMPLATE_PATH.exists():
        print(f"ERROR: missing template at {TEMPLATE_PATH}")
        return 1

    tuning_config = (
        open_config_with_defaults(CONFIG_PATH) if CONFIG_PATH.exists() else CONFIG_DEFAULTS
    )
    template = Template(TEMPLATE_PATH, tuning_config)

    structure = summarize_template(template)
    print("\n--- Template structure ---")
    print(json.dumps(structure, indent=2))

    print("\n--- Alignment check (CropOnMarkers) ---")
    alignment = run_alignment_check(template, tuning_config, BLANK_IMAGE)
    print(json.dumps(alignment, indent=2))

    if alignment["alignment_success"]:
        print("\nRESULT: Alignment OK — corner markers detected and sheet warped.")
        print("NOTE: Bubble coordinates are initial estimates; use --setLayout to tune.")
    else:
        print("\nRESULT: Alignment FAILED — check omr_marker.jpg crop and template thresholds.")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
