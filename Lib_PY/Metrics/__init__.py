#!/usr/bin/env python3
"""
Name:          __init__.py (Metrics)
Description:   BEJSON 105 Metrics Standardization, Validation, and Canvas Visualization Library Family.
Version:       1.0.0
Date Created:  2026-11-18
Author Credit: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID: lib-bejson-metrics-init-20261118
License:       PolyForm-Noncommercial-1.0.0
"""

from lib_bejson_Metrics_metrics_errors import (
    E_METRICS_SCHEMA_INVALID,
    E_METRICS_NEGATIVE_VALUE,
    E_METRICS_MISSING_SOURCE,
    E_METRICS_RENDER_FAILED,
    E_METRICS_LOCK_TIMEOUT,
    MetricsLibraryError,
)
from lib_bejson_Metrics_metrics_schemas import (
    METRICS_RUN_RECORD_TYPE,
    METRICS_RUN_FIELD_SPECS,
    create_metrics_runs_document,
)
from lib_bejson_Metrics_metrics_validator import (
    validate_metrics_document,
    validate_metrics_file,
)
from lib_bejson_Metrics_metrics_collector import (
    collect_and_save_metrics,
    ingest_test_series_directory,
)
from lib_bejson_Metrics_metrics_renderer import (
    audit_dashboard_quirks,
    build_scrollable_dashboard_document,
    capture_visual_audit_screenshots,
    render_metrics_dashboard_html,
    render_tri_color_bar_svg,
)

__all__ = [
    "E_METRICS_SCHEMA_INVALID",
    "E_METRICS_NEGATIVE_VALUE",
    "E_METRICS_MISSING_SOURCE",
    "E_METRICS_RENDER_FAILED",
    "E_METRICS_LOCK_TIMEOUT",
    "MetricsLibraryError",
    "METRICS_RUN_RECORD_TYPE",
    "METRICS_RUN_FIELD_SPECS",
    "create_metrics_runs_document",
    "validate_metrics_document",
    "validate_metrics_file",
    "collect_and_save_metrics",
    "ingest_test_series_directory",
    "audit_dashboard_quirks",
    "build_scrollable_dashboard_document",
    "render_metrics_dashboard_html",
    "render_tri_color_bar_svg",
    "capture_visual_audit_screenshots",
]
