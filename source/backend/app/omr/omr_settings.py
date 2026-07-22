"""OMR threshold accessors — values driven by config.yaml with code defaults."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from typing import Any

from app.config import OmrConfig, get_config

_threshold_overrides: ContextVar[dict[str, float] | None] = ContextVar(
    "threshold_overrides", default=None
)

# Code defaults (used when config fields are on legacy 0–1 scale).
_DEFAULT_MIN_PLAUSIBLE_FILL = 40.0
_DEFAULT_MIN_SEPARATION = 18.0
_DEFAULT_MIN_MARK_MARGIN = 18.0
_DEFAULT_MIN_DOMINANCE_RATIO = 1.18
_DEFAULT_HARD_MULTI_MARGIN = 10.0
_DEFAULT_HARD_MULTI_RATIO = 1.12
_DEFAULT_COMFORT_MARGIN = 28.0
_DEFAULT_COMFORT_RATIO = 1.35
_DEFAULT_ALIGNMENT_REVIEW_BELOW = 0.72


def _scale_threshold(value: float, *, code_default: float, legacy_scale: float = 100.0) -> float:
    """Map config values: legacy 0–1 fractions scale up; explicit values pass through."""
    if value <= 0:
        return code_default
    if value < 1.0:
        return value * legacy_scale
    return value


@lru_cache
def omr_settings() -> OmrConfig:
    return get_config().omr


def reload_omr_settings() -> OmrConfig:
    omr_settings.cache_clear()
    get_config.cache_clear()
    return omr_settings()


def current_threshold_defaults() -> dict[str, float]:
    """Active OMR thresholds (config defaults or request-scoped overrides)."""
    cfg = omr_settings()
    overrides = _threshold_overrides.get() or {}
    return {
        "fill_threshold": overrides.get("fill_threshold", cfg.fill_threshold),
        "blank_threshold": overrides.get("blank_threshold", cfg.blank_threshold),
        "multi_mark_threshold": overrides.get(
            "multi_mark_threshold", cfg.multi_mark_threshold
        ),
        "comfort_margin": overrides.get("comfort_margin", cfg.comfort_margin),
        "comfort_ratio": overrides.get("comfort_ratio", cfg.comfort_ratio),
        "alignment_review_below": overrides.get(
            "alignment_review_below", cfg.alignment_review_below
        ),
    }


@contextmanager
def threshold_override_context(overrides: dict[str, Any] | None):
    """Apply temporary threshold overrides for a single diagnostic run."""
    cleaned = {
        k: float(v)
        for k, v in (overrides or {}).items()
        if k in current_threshold_defaults() and v is not None
    }
    token = _threshold_overrides.set(cleaned or None)
    try:
        yield
    finally:
        _threshold_overrides.reset(token)


def _override(key: str, fallback: float) -> float:
    overrides = _threshold_overrides.get()
    if overrides and key in overrides:
        return float(overrides[key])
    return fallback


def min_plausible_fill() -> float:
    cfg = omr_settings()
    raw = _override("fill_threshold", cfg.fill_threshold)
    return _scale_threshold(raw, code_default=_DEFAULT_MIN_PLAUSIBLE_FILL)


def min_separation() -> float:
    cfg = omr_settings()
    raw = _override("blank_threshold", cfg.blank_threshold)
    return _scale_threshold(raw, code_default=_DEFAULT_MIN_SEPARATION)


def min_mark_margin() -> float:
    return _DEFAULT_MIN_MARK_MARGIN


def min_dominance_ratio() -> float:
    return _DEFAULT_MIN_DOMINANCE_RATIO


def hard_multi_margin() -> float:
    cfg = omr_settings()
    raw = _override("multi_mark_threshold", cfg.multi_mark_threshold)
    return _scale_threshold(raw, code_default=_DEFAULT_HARD_MULTI_MARGIN, legacy_scale=40.0)


def hard_multi_ratio() -> float:
    cfg = omr_settings()
    base = _override("multi_mark_threshold", cfg.multi_mark_threshold)
    if base <= 0:
        return _DEFAULT_HARD_MULTI_RATIO
    if base < 1.0:
        return 1.0 + base * 0.48
    return base


def comfort_margin() -> float:
    cfg = omr_settings()
    raw = _override("comfort_margin", cfg.comfort_margin)
    return raw or _DEFAULT_COMFORT_MARGIN


def comfort_ratio() -> float:
    cfg = omr_settings()
    raw = _override("comfort_ratio", cfg.comfort_ratio)
    return raw or _DEFAULT_COMFORT_RATIO


def alignment_review_below() -> float:
    cfg = omr_settings()
    raw = _override("alignment_review_below", cfg.alignment_review_below)
    return raw or _DEFAULT_ALIGNMENT_REVIEW_BELOW


def strict_review_enabled() -> bool:
    return bool(omr_settings().strict_review)
