#!/usr/bin/env python3
"""Benchmark per-sheet OMR processing time on fixture scans."""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = BACKEND_ROOT.parent / "tests" / "fixtures" / "scans"
SAMPLES_60Q = BACKEND_ROOT.parent / "samples" / "isra_60q"


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * pct / 100.0
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    if f == c:
        return ordered[f]
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def main() -> int:
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))

    from app.omr.pipeline import SheetReader
    from app.services import template_service

    template_path = SAMPLES_60Q / "template.json"
    if not template_path.exists():
        print(f"Missing template: {template_path}", file=sys.stderr)
        return 1

    import json as json_mod

    template_dict = json_mod.loads(template_path.read_text(encoding="utf-8"))
    reader = SheetReader(template_dict, "60Q")

    scans = sorted(FIXTURES.glob("*.jpeg")) + sorted(FIXTURES.glob("*.jpg"))
    if not scans:
        print(f"No scans in {FIXTURES}", file=sys.stderr)
        return 1

    crop_dir = BACKEND_ROOT / "data" / "benchmark_crops"
    crop_dir.mkdir(parents=True, exist_ok=True)

    timings: list[float] = []
    for scan in scans:
        start = time.perf_counter()
        reader.process(
            str(scan),
            global_q_start=1,
            sheet_question_count=60,
            crop_dir=crop_dir,
            crop_prefix=scan.stem,
        )
        elapsed = time.perf_counter() - start
        timings.append(elapsed)
        print(f"{scan.name}: {elapsed:.3f}s")

    report = {
        "scan_count": len(timings),
        "p50_seconds": round(statistics.median(timings), 3),
        "p95_seconds": round(_percentile(timings, 95), 3),
        "mean_seconds": round(statistics.mean(timings), 3),
        "scans": [s.name for s in scans],
    }
    out = BACKEND_ROOT / "data" / "benchmark_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Report written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
