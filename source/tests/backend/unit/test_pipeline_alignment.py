"""Pipeline alignment failure tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.omr.pipeline import ANOMALY_ALIGNMENT, MIN_ALIGNMENT_QUALITY, SheetReader


@pytest.fixture()
def reader():
    template = {"pageDimensions": [100, 100], "fieldBlocks": []}
    with patch(
        "app.omr.pipeline.template_service.build_engine_template",
        return_value=(MagicMock(), MagicMock()),
    ):
        yield SheetReader(template, "150Q")


@pytest.mark.unit
def test_alignment_failed_when_warp_is_none(reader, tmp_path):
    img = tmp_path / "scan.jpg"
    img.write_bytes(b"\xff\xd8\xff")

    with patch("app.omr.pipeline.warp_sheet", return_value=None):
        result = reader.process(str(img), 1, 3, tmp_path / "crops", "s1")

    assert result["aligned"] is False
    assert len(result["anomalies"]) == 1
    assert result["anomalies"][0]["type"] == ANOMALY_ALIGNMENT
    assert result["source_path"] == str(img.resolve())


@pytest.mark.unit
def test_alignment_failed_when_quality_low(reader, tmp_path):
    img = tmp_path / "scan.jpg"
    img.write_bytes(b"\xff\xd8\xff")
    warp = MagicMock()
    warp.quality = MIN_ALIGNMENT_QUALITY - 0.1
    warp.image = MagicMock()

    with patch("app.omr.pipeline.warp_sheet", return_value=warp):
        result = reader.process(str(img), 1, 3, tmp_path / "crops", "s1")

    assert result["aligned"] is False
    assert result["anomalies"][0]["type"] == ANOMALY_ALIGNMENT


@pytest.mark.unit
def test_alignment_ok_when_quality_at_threshold(reader, tmp_path):
    img = tmp_path / "scan.jpg"
    img.write_bytes(b"\xff\xd8\xff")
    warp = MagicMock()
    warp.quality = MIN_ALIGNMENT_QUALITY
    warp.image = MagicMock()

    with (
        patch("app.omr.pipeline.warp_sheet", return_value=warp),
        patch("app.omr.pipeline.build_refine_context"),
        patch("app.omr.pipeline.build_contour_context", return_value=(MagicMock(), MagicMock(grid_confidence=0.0, detection_ratio=0.0, detected_bubbles=[]))),
        patch("app.omr.pipeline.read_mcq_contour", return_value=({}, MagicMock(grid_confidence=0.0, detection_ratio=0.0, detected_bubbles=[]))),
        patch("app.omr.pipeline.decode_roll_contour", return_value={"status": "ok", "roll_no": "123"}),
        patch("app.omr.pipeline.mcq_reader.read_mcq", return_value={}),
        patch("app.omr.pipeline.roll_reader.decode_roll", return_value={"status": "ok", "roll_no": "123"}),
    ):
        result = reader.process(str(img), 1, 3, tmp_path / "crops", "s1")

    assert result["aligned"] is True
    assert not any(a["type"] == ANOMALY_ALIGNMENT for a in result["anomalies"])
