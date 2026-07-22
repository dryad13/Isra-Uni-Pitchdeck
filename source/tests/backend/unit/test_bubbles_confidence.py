"""Bubble confidence detection unit tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.omr import bubbles


@pytest.mark.unit
def test_is_low_confidence_when_margin_and_ratio_weak():
    q = {
        "status": bubbles.STATUS_ANSWERED,
        "fills": {"A": 62.0, "B": 48.0, "C": 40.0, "D": 38.0},
    }
    assert bubbles.is_low_confidence(q) is True


@pytest.mark.unit
def test_is_not_low_confidence_when_margin_strong():
    q = {
        "status": bubbles.STATUS_ANSWERED,
        "fills": {"A": 90.0, "B": 40.0, "C": 35.0, "D": 30.0},
    }
    assert bubbles.is_low_confidence(q) is False


@pytest.mark.unit
def test_is_hard_multi_when_marks_close():
    q = {
        "status": bubbles.STATUS_MULTI,
        "fills": {"A": 55.0, "B": 52.0, "C": 40.0, "D": 38.0},
    }
    assert bubbles.is_hard_multi(q) is True


@pytest.mark.unit
@patch("app.omr.pipeline.strict_review_enabled", return_value=True)
@patch("app.omr.pipeline.alignment_review_below", return_value=0.72)
def test_strict_review_queues_all_multi(_below, _strict):
    from unittest.mock import MagicMock

    from app.omr.pipeline import ANOMALY_MULTI, SheetReader

    template = {"pageDimensions": [100, 100], "fieldBlocks": []}
    with patch(
        "app.omr.pipeline.template_service.build_engine_template",
        return_value=(MagicMock(), MagicMock()),
    ):
        reader = SheetReader(template, "150Q")

    warp = MagicMock()
    warp.quality = 0.8
    warp.image = MagicMock()

    mcq = {
        1: {
            "status": bubbles.STATUS_MULTI,
            "option": "AB",
            "marked": ["A", "B"],
            "fills": {"A": 55.0, "B": 52.0, "C": 40.0, "D": 38.0},
        }
    }

    with (
        patch("app.omr.pipeline.warp_sheet", return_value=warp),
        patch("app.omr.pipeline.build_refine_context"),
        patch("app.omr.pipeline.build_contour_context", return_value=(MagicMock(), MagicMock(grid_confidence=0.0, detection_ratio=0.0, detected_bubbles=[]))),
        patch("app.omr.pipeline.read_mcq_contour", return_value=({}, MagicMock(grid_confidence=0.0, detection_ratio=0.0, detected_bubbles=[]))),
        patch("app.omr.pipeline.decode_roll_contour", return_value={"status": "ok", "roll_no": "123"}),
        patch("app.omr.pipeline.mcq_reader.read_mcq", return_value=mcq),
        patch("app.omr.pipeline.roll_reader.decode_roll", return_value={"status": "ok", "roll_no": "123"}),
    ):
        result = reader.process("/tmp/x.jpg", 1, 1, MagicMock(), "pfx")

    assert result["answers"].get(1) == ""
    assert any(a["type"] == ANOMALY_MULTI for a in result["anomalies"])
