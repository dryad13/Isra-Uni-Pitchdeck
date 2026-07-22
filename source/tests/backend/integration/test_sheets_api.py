"""Sheets detail API integration tests."""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_get_sheet_detail(client, seed_scored_sheet):
    seeded = seed_scored_sheet()
    res = client.get(f"/api/sheets/{seeded['sheet_id']}")
    assert res.status_code == 200
    body = res.json()
    assert body["roll_no"] == "88001"
    assert body["scored"] is not None
    assert len(body["scored"]["per_question"]) == 3


@pytest.mark.integration
def test_source_image_404_without_path(client, seed_scored_sheet):
    seeded = seed_scored_sheet()
    res = client.get(f"/api/sheets/{seeded['sheet_id']}/source-image")
    assert res.status_code == 404
