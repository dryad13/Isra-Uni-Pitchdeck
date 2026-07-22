"""Integration tests for Accuracy Lab API."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "scans"
FILLED = FIXTURES / "sample_scan.jpeg"
BLANK = FIXTURES / "sample_scan_2.jpeg"


@pytest.fixture()
def filled_scan_available() -> bool:
    return FILLED.exists()


def test_list_fixtures(client):
    res = client.get("/api/accuracy/fixtures")
    assert res.status_code == 200
    body = res.json()
    assert "fixtures" in body
    assert "threshold_defaults" in body
    ids = {f["id"] for f in body["fixtures"]}
    assert "sample_scan" in ids
    assert "sample_scan_2" in ids


def test_save_and_load_reference(client):
    payload = {
        "template_family": "150Q",
        "roll_no": "569192",
        "answers": {"1": "A", "2": "B", "3": "C"},
        "note": "test",
    }
    put = client.put("/api/accuracy/reference/sample_scan", json=payload)
    assert put.status_code == 200
    assert put.json()["fixture_id"] == "sample_scan"

    get = client.get("/api/accuracy/reference/sample_scan")
    assert get.status_code == 200
    assert get.json()["answers"]["2"] == "B"


def test_run_requires_source(client):
    res = client.post("/api/accuracy/run", json={"template_family": "150Q"})
    assert res.status_code == 400


@pytest.mark.slow
def test_run_filled_fixture(client, filled_scan_available):
    if not filled_scan_available:
        pytest.skip("sample_scan.jpeg not present")

    res = client.post(
        "/api/accuracy/run",
        json={
            "fixture_id": "sample_scan",
            "template_family": "150Q",
            "sheet_question_count": 150,
            "include_warp_preview": False,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert "alignment_quality" in body
    assert body["summary"]["total"] == 150
    if body["aligned"]:
        assert len(body["questions"]) == 150
    else:
        assert body["alignment_quality"] < 0.55
        assert body["questions"] == []


@pytest.mark.slow
def test_run_blank_fixture_alignment(client):
    if not BLANK.exists():
        pytest.skip("sample_scan_2.jpeg not present")

    res = client.post(
        "/api/accuracy/run",
        json={
            "fixture_id": "sample_scan_2",
            "template_family": "150Q",
            "sheet_question_count": 150,
            "include_warp_preview": False,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert "alignment_quality" in body
    assert body["summary"]["blank"] >= 0
