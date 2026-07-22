"""Phase 2 — OMR pipeline tests with real scan images."""

from __future__ import annotations

from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[3] / "backend"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "scans"
FILLED = FIXTURES / "sample_scan.jpeg"
BLANK = FIXTURES / "sample_scan_2.jpeg"


@pytest.mark.slow
def test_omr_pipeline_blank_scan_aligns():
    """Blank live-scanner fixture should align and return 150 MCQ reads."""
    if not BLANK.exists():
        pytest.skip("sample_scan_2.jpeg not present")

    from app.omr.pipeline import SheetReader
    from app.services import template_service

    template_dict = template_service.load_default_template("150Q")
    reader = SheetReader(template_dict, "150Q")
    crop_dir = BACKEND / "data" / "test_crops"
    result = reader.process(
        str(BLANK),
        global_q_start=1,
        sheet_question_count=150,
        crop_dir=crop_dir,
        crop_prefix="pipeline_blank",
    )

    assert result["aligned"] is True
    assert result["alignment_quality"] >= 0.55
    assert len(result["per_question"]) == 150


@pytest.mark.slow
def test_omr_pipeline_filled_scan_reports_alignment():
    """Filled live-scanner fixture runs through pipeline (alignment may fail)."""
    if not FILLED.exists():
        pytest.skip("sample_scan.jpeg not present")

    from app.omr.pipeline import SheetReader
    from app.services import template_service

    template_dict = template_service.load_default_template("150Q")
    reader = SheetReader(template_dict, "150Q")
    result = reader.process(
        str(FILLED),
        global_q_start=1,
        sheet_question_count=150,
        crop_dir=BACKEND / "data" / "test_crops",
        crop_prefix="pipeline_filled",
    )

    assert "aligned" in result
    assert "alignment_quality" in result
    if result["aligned"]:
        assert len(result["per_question"]) == 150
    else:
        assert result["alignment_quality"] < 0.55


@pytest.mark.slow
def test_accuracy_diagnostic_includes_fills():
    """Diagnostic run exposes per-option fill values for calibration."""
    if not BLANK.exists():
        pytest.skip("sample_scan_2.jpeg not present")

    from app.services import accuracy_service as svc
    from app.services import template_service

    template_dict = template_service.load_default_template("150Q")
    result = svc.run_diagnostic(
        str(BLANK),
        template_dict=template_dict,
        template_family="150Q",
        sheet_question_count=150,
        fixture_id="sample_scan_2",
        include_warp_preview=False,
    )

    assert result["aligned"] is True
    q1 = result["questions"][0]
    assert "fills" in q1
    assert set(q1["fills"].keys()) == {"A", "B", "C", "D"}
