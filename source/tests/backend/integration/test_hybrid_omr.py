"""Hybrid OMR integration smoke tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.omr.pipeline import SheetReader
from app.services import template_service


@pytest.mark.integration
def test_hybrid_blank_fixture_reads_blanks():
    fixture = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "scans"
        / "sample_scan_2.jpeg"
    )
    if not fixture.exists():
        pytest.skip("blank fixture missing")

    template_dict = template_service.load_default_template("150Q")
    reader = SheetReader(template_dict, "150Q")
    result = reader.process(
        str(fixture),
        global_q_start=1,
        sheet_question_count=150,
        crop_dir=Path("/tmp/omr_crops"),
        crop_prefix="hybrid_test",
    )
    assert result["aligned"] is True
    assert result.get("read_method_summary") in {"hybrid", "contour", "template_fallback"}
    assert result.get("grid_confidence", 0) >= 0.5
    counts = result["counts"]
    assert counts["total"] == 150
