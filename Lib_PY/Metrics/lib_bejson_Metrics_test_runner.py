#!/usr/bin/env python3
"""
Name:          lib_bejson_Metrics_test_runner.py
Description:   Standardized unittest runner emitting BEJSON 105a test_results.105a.bejson and Tri-Color graphs.
Version:       1.0.0
Date Created:  2026-11-18
Author Credit: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID: lib-bejson-metrics-test-runner-20261118
License:       PolyForm-Noncommercial-1.0.0
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

if sys.version_info < (3, 10):
    raise RuntimeError("Python 3.10+ is required.")

_METRICS_DIR: Path = Path(__file__).resolve().parent
_CORE_DIR: Path = _METRICS_DIR.parent / "Core"
for _path_item in (_METRICS_DIR, _CORE_DIR):
    if str(_path_item) not in sys.path:
        sys.path.insert(0, str(_path_item))

from lib_bejson_Core_bejson_core import (
    ResilientPIDLock,
    bejson_core_add_record_105,
    bejson_core_atomic_write,
    bejson_core_get_field_map,
)
from lib_bejson_Core_bejson_validator import validate_bejson
from lib_bejson_Metrics_metrics_errors import E_METRICS_SCHEMA_INVALID, MetricsLibraryError
from lib_bejson_Metrics_metrics_renderer import (
    build_scrollable_dashboard_document,
    capture_visual_audit_screenshots,
    render_tri_color_bar_svg,
)
from lib_bejson_Metrics_metrics_schemas import create_test_results_document

LOGGER_INSTANCE = logging.getLogger("lib_bejson_Metrics.test_runner")


class _TimedBEJSONTestResult(unittest.TestResult):
    """Captures per-test timing and pass/fail/error/skip status."""

    def __init__(self) -> None:
        super().__init__()
        self.recorded_cases: List[Dict[str, Any]] = []
        self._case_starts: Dict[str, float] = {}

    def startTest(self, test: unittest.TestCase) -> None:
        super().startTest(test)
        self._case_starts[test.id()] = time.perf_counter()

    def _finish_case(self, test: unittest.TestCase, status: str, err_msg: str = "") -> None:
        elapsed_ms = (time.perf_counter() - self._case_starts.pop(test.id(), time.perf_counter())) * 1000.0
        parts = test.id().split(".")
        suite_name = parts[-2] if len(parts) >= 2 else "default_suite"
        test_name = parts[-1]
        category = "mfdb" if "mfdb" in test.id().lower() else "bejson"
        self.recorded_cases.append({
            "suite_name": suite_name,
            "test_name": test_name,
            "category": category,
            "status": status,
            "duration_ms": round(elapsed_ms, 3),
            "assertions_count": 1,
            "error_message": err_msg[:300],
            "executed_at": datetime.now(timezone.utc).isoformat(),
        })

    def addSuccess(self, test: unittest.TestCase) -> None:
        super().addSuccess(test)
        self._finish_case(test, "pass")

    def addFailure(self, test: unittest.TestCase, err: Any) -> None:
        super().addFailure(test, err)
        self._finish_case(test, "fail", self._exc_info_to_string(err, test))

    def addError(self, test: unittest.TestCase, err: Any) -> None:
        super().addError(test, err)
        self._finish_case(test, "error", self._exc_info_to_string(err, test))

    def addSkip(self, test: unittest.TestCase, reason: str) -> None:
        super().addSkip(test, reason)
        self._finish_case(test, "skip", reason)


def run_standardized_suites(
    suite_dirs: List[Path],
    output_bejson_path: Path,
    pattern: str = "*test*.py",
) -> Dict[str, Any]:
    """Discover and execute unittest suites, persisting validated BEJSON 105a results."""
    loader = unittest.TestLoader()
    master_suite = unittest.TestSuite()
    for target_dir in suite_dirs:
        if target_dir.is_dir():
            master_suite.addTests(loader.discover(start_dir=str(target_dir), pattern=pattern))

    result = _TimedBEJSONTestResult()
    master_suite.run(result)

    results_doc = create_test_results_document("BEJSON_MFDB_Test_Results")
    for case in result.recorded_cases:
        bejson_core_add_record_105(
            results_doc,
            [
                case["suite_name"],
                case["test_name"],
                case["category"],
                case["status"],
                case["duration_ms"],
                case["assertions_count"],
                case["error_message"],
                case["executed_at"],
            ],
        )

    validation = validate_bejson(results_doc, is_file=False)
    if not validation.is_valid:
        raise MetricsLibraryError(
            f"Test results ledger failed validation: {validation.errors}",
            error_code=E_METRICS_SCHEMA_INVALID,
        )

    output_bejson_path.parent.mkdir(parents=True, exist_ok=True)
    with ResilientPIDLock(str(output_bejson_path), timeout_seconds=10):
        bejson_core_atomic_write(str(output_bejson_path), results_doc)

    return results_doc


def render_test_results_dashboard(
    results_doc: Dict[str, Any],
    output_html_path: Path,
    svg_export_dir: Path | None = None,
) -> Path:
    """Render Tri-Color SVG + HTML5 Canvas test latency and pass/fail dashboard with horizontal scroll containers."""
    fmap = bejson_core_get_field_map(results_doc)
    rows = results_doc.get("Values", [])

    latency_bars: List[Tuple[str, float, str]] = []
    status_counts: Dict[str, int] = {"pass": 0, "fail": 0, "error": 0, "skip": 0}
    for row in rows:
        status_val = str(row[fmap["status"]])
        status_counts[status_val] = status_counts.get(status_val, 0) + 1
        latency_bars.append((
            str(row[fmap["test_name"]])[:26],
            float(row[fmap["duration_ms"]]),
            f"ms [{status_val}]",
        ))

    status_bars: List[Tuple[str, float, str]] = [
        (k.upper(), float(v), "tests") for k, v in status_counts.items() if v > 0
    ] or [("NONE", 0.0, "tests")]
    latency_bars = latency_bars or [("none", 0.0, "ms")]

    latency_svg = render_tri_color_bar_svg(
        "Test Execution Latency (ms)",
        latency_bars,
        width_px=840,
        height_px=max(320, 90 + 44 * len(latency_bars)),
        svg_id="svg-test-latency",
    )
    status_svg = render_tri_color_bar_svg(
        "Test Suite Status Breakdown",
        status_bars,
        width_px=840,
        height_px=260,
        svg_id="svg-test-status",
    )

    if svg_export_dir is not None:
        svg_export_dir.mkdir(parents=True, exist_ok=True)
        (svg_export_dir / "test_latency_chart.svg").write_text(latency_svg, encoding="utf-8")
        (svg_export_dir / "test_status_chart.svg").write_text(status_svg, encoding="utf-8")

    panels_spec = [
        {
            "slug": "test-status",
            "heading": "Suite Status Summary",
            "subtitle": "Pass / Fail / Error Breakdown",
            "svg_markup": status_svg,
            "bars": status_bars,
        },
        {
            "slug": "test-latency",
            "heading": "Test Case Latency",
            "subtitle": "Per-Test Execution Duration (ms)",
            "svg_markup": latency_svg,
            "bars": latency_bars,
        },
    ]

    html_doc = build_scrollable_dashboard_document("Test Results", panels_spec)
    output_html_path.parent.mkdir(parents=True, exist_ok=True)
    output_html_path.write_text(html_doc, encoding="utf-8")
    return output_html_path


def main() -> int:
    """CLI entrypoint for running standardized BEJSON/MFDB test suites and rendering graphs."""
    parser = argparse.ArgumentParser(description="Standardized BEJSON/MFDB Test Runner & Graph Generator")
    parser.add_argument("--suite-dir", action="append", default=[], help="Test suite directory to discover")
    parser.add_argument("--pattern", default="*test*.py", help="Test file glob pattern")
    parser.add_argument("--output", default="", help="Output BEJSON 105a ledger path")
    parser.add_argument("--html", default="", help="Output HTML graphs dashboard path")
    parser.add_argument("--screenshots", default="", help="Optional Playwright screenshots output dir")
    args = parser.parse_args()

    metrics_root = _METRICS_DIR.parent.parent / "dev" / "metrics"
    suite_dirs = [Path(p) for p in args.suite_dir] if args.suite_dir else [
        _METRICS_DIR / "tests",
        metrics_root / "suites" / "standardized",
    ]
    out_bejson = Path(args.output) if args.output else metrics_root / "test_results.105a.bejson"
    out_html = Path(args.html) if args.html else metrics_root / "test_results_graphs.html"

    results_doc = run_standardized_suites(suite_dirs, out_bejson, pattern=args.pattern)
    render_test_results_dashboard(results_doc, out_html, metrics_root / "visual_audit" / "svgs")
    if args.screenshots:
        capture_visual_audit_screenshots(out_html, Path(args.screenshots))
    return 0


if __name__ == "__main__":
    sys.exit(main())
