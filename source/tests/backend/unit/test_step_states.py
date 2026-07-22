"""Step state logic mirrored from frontend Stepper."""

from __future__ import annotations

import pytest

StepState = str


def derive_step_states(
    has_session: bool, key_ready: bool, scanning: bool
) -> tuple[StepState, StepState, StepState]:
    if not has_session:
        return ("active", "locked", "locked")
    if not key_ready:
        return ("done", "active", "locked")
    if scanning:
        return ("done", "done", "active")
    return ("done", "done", "active")


@pytest.mark.parametrize(
    ("has_session", "key_ready", "scanning", "expected"),
    [
        (False, False, False, ("active", "locked", "locked")),
        (True, False, False, ("done", "active", "locked")),
        (True, True, True, ("done", "done", "active")),
        (True, True, False, ("done", "done", "active")),
    ],
)
def test_derive_step_states(has_session, key_ready, scanning, expected):
    assert derive_step_states(has_session, key_ready, scanning) == expected
