"""Unit tests for contour bubble detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.omr.align import warp_sheet
from app.omr.contour_detect import build_otsu_thresh, detect_block_bubbles
from app.services import template_service


@pytest.mark.unit
def test_contour_detect_blank_fixture_finds_bubbles():
    fixture = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "scans"
        / "sample_scan_2.jpeg"
    )
    if not fixture.exists():
        pytest.skip("blank fixture missing")

    template_dict = template_service.load_default_template("150Q")
    template, _ = template_service.build_engine_template(template_dict, "150Q")
    warp = warp_sheet(str(fixture), template)
    assert warp is not None

    gray = warp.image
    thresh = build_otsu_thresh(gray)
    total = 0
    for field_block in template.field_blocks:
        if not field_block.traverse_bubbles:
            continue
        is_roll = any(
            b.field_type.startswith("QTYPE_INT")
            for b in field_block.traverse_bubbles[0]
        )
        is_mcq = not is_roll
        if not is_mcq:
            continue
        detected = detect_block_bubbles(gray, field_block, thresh)
        total += len(detected)

    assert total >= 400
