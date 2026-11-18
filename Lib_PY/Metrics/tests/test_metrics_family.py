#!/usr/bin/env python3
"""
Name:          test_metrics_family.py
Description:   Unit, schema conformance, validation, round-trip, and SVG/HTML render tests for Lib_PY/Metrics.
Version:       1.0.0
Date Created:  2026-11-18
Author Credit: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID: test-lib-bejson-metrics-20261118
License:       PolyForm-Noncommercial-1.0.0
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_METRICS_DIR: Path = Path(__file__).resolve().parent.parent
_LIB_ROOT: Path = _METRICS_DIR.parent.parent
_METRICS_DATA_DIR: Path = _LIB_ROOT / "dev" / "metrics"
if str(_METRICS_DIR) not in sys.path:
    sys.path.insert(0, str(_METRICS_DIR))

from lib_bejson_Metrics_metrics_collector import collect_and_save_metrics, ingest_test_series_directory
from lib_bejson_Metrics_metrics_errors import E_METRICS_NEGATIVE_VALUE, MetricsLibraryError
from lib_bejson_Metrics_metrics_renderer import render_metrics_dashboard_html, render_tri_color_bar_svg
from lib_bejson_Metrics_metrics_schemas import create_metrics_runs_document
from lib_bejson_Metrics_metrics_validator import validate_metrics_document, validate_metrics_file


class TestMetricsFamily(unittest.TestCase):
    """Conformance, validation, collection, and rendering tests for Lib_PY/Metrics."""

    def test_schema_creation_and_validation(self) -> None:
        doc = create_metrics_runs_document()
        self.assertEqual(doc["Format_Version"], "105a")
        res = validate_metrics_document(doc)
        self.assertTrue(res["valid"])
        self.assertEqual(res["record_count"], 0)

    def test_negative_metric_rejected(self) -> None:
        doc = ingest_test_series_directory(_METRICS_DATA_DIR)
        doc["Values"][0][5] = -5.0  # primary_value column
        with self.assertRaises(MetricsLibraryError) as ctx:
            validate_metrics_document(doc)
        self.assertEqual(ctx.exception.error_code, E_METRICS_NEGATIVE_VALUE)

    def test_round_trip_collect_and_render(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            ledger = ingest_test_series_directory(_METRICS_DATA_DIR)
            self.assertGreaterEqual(len(ledger["Values"]), 6)
            html_out = render_metrics_dashboard_html(ledger, tmp_path / "graphs.html", tmp_path / "svgs")
            self.assertTrue(html_out.is_file())
            self.assertTrue((tmp_path / "svgs" / "throughput_chart.svg").is_file())
            svg_text = render_tri_color_bar_svg("Unit Bar", [("BEJSON", 10.0, "ops")])
            self.assertIn("#DE2626", svg_text)
            self.assertIn("#000000", svg_text)

    def test_live_metrics_ledger_persisted_and_valid(self) -> None:
        out_path = collect_and_save_metrics(_METRICS_DATA_DIR)
        summary = validate_metrics_file(out_path)
        self.assertTrue(summary["valid"])
        self.assertGreaterEqual(summary["record_count"], 6)


if __name__ == "__main__":
    unittest.main()
