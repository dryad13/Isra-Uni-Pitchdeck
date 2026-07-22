#!/usr/bin/env python3
"""OMR Engine POC — validate alignment and template on Isra 60Q blank."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ENGINE_ROOT = BACKEND_ROOT / "omr_engine"
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from src.defaults import CONFIG_DEFAULTS  # noqa: E402
from src.template import Template  # noqa: E402
from src.utils.parsing import open_config_with_defaults  # noqa: E402

SAMPLE_DIR = BACKEND_ROOT.parent / "samples" / "isra_60q"
BLANK_IMAGE = SAMPLE_DIR / "blank_template.png"
TEMPLATE_PATH = SAMPLE_DIR / "template.json"
CONFIG_PATH = SAMPLE_DIR / "config.json"


def main() -> int:
    print("=== Isra 60Q OMR POC ===")
    tuning = open_config_with_defaults(CONFIG_PATH) if CONFIG_PATH.exists() else CONFIG_DEFAULTS
    template = Template(TEMPLATE_PATH, tuning)

    blocks = []
    for block in template.field_blocks:
        blocks.append({"name": block.name, "origin": block.origin, "labels": len(block.parsed_field_labels)})
    print(json.dumps({"blocks": blocks, "output_columns": len(template.output_columns)}, indent=2))

    gray = cv2.imread(str(BLANK_IMAGE), cv2.IMREAD_GRAYSCALE)
    warped = template.image_instance_ops.apply_preprocessors(str(BLANK_IMAGE), gray, template)
    if warped is None:
        print("ALIGNMENT FAILED")
        return 2

    page_w, page_h = template.page_dimensions
    warped = cv2.resize(warped, (int(page_w), int(page_h)))
    layout = template.image_instance_ops.draw_template_layout(warped, template, shifted=False, border=2)
    out = SAMPLE_DIR / "poc_layout_overlay.png"
    cv2.imwrite(str(out), layout)
    print(f"Alignment OK — overlay: {out}")
    print(f"Output columns: {len(template.output_columns)} (expected 66 = 60 MCQ + 6 roll)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
