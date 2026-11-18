#!/usr/bin/env python3
"""
Name:          lib_bejson_Metrics_metrics_schemas.py
Description:   Canonical BEJSON 105a schema definitions for standardized benchmark and test metrics.
Version:       1.0.0
Date Created:  2026-11-18
Author Credit: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID: lib-bejson-metrics-schemas-20261118
License:       PolyForm-Noncommercial-1.0.0
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

if sys.version_info < (3, 10):
    raise RuntimeError("Python 3.10+ is required.")

_CORE_DIR: Path = Path(__file__).resolve().parent.parent / "Core"
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

from lib_bejson_Core_bejson_core import bejson_core_define_field

METRICS_RUN_RECORD_TYPE: str = "MetricRunRecord"

METRICS_RUN_FIELD_SPECS: List[Tuple[str, str]] = [
    ("series_id", "string"),
    ("suite_name", "string"),
    ("metric_name", "string"),
    ("metric_category", "string"),
    ("primary_value", "number"),
    ("baseline_value", "number"),
    ("unit", "string"),
    ("reduction_pct", "number"),
    ("speedup_factor", "number"),
    ("peak_rss_mb", "number"),
    ("passed", "boolean"),
    ("recorded_at", "string"),
]


def create_metrics_runs_document(schema_name: str = "MetricsRunsLedger") -> Dict[str, Any]:
    """Create a canonical BEJSON 105a metrics ledger with Core-stamped field_uuid values."""
    document_payload: Dict[str, Any] = {
        "Format": "BEJSON",
        "Format_Version": "105a",
        "Format_Creator": "Elton Boehnen",
        "Schema_Name": schema_name,
        "Records_Type": [METRICS_RUN_RECORD_TYPE],
        "Fields": [],
        "Values": [],
    }
    for field_name, field_type in METRICS_RUN_FIELD_SPECS:
        bejson_core_define_field(document_payload, field_name, field_type)
    return document_payload


TEST_EXECUTION_RECORD_TYPE: str = "TestExecutionRecord"

TEST_EXECUTION_FIELD_SPECS: List[Tuple[str, str]] = [
    ("suite_name", "string"),
    ("test_name", "string"),
    ("category", "string"),
    ("status", "string"),
    ("duration_ms", "number"),
    ("assertions_count", "integer"),
    ("error_message", "string"),
    ("executed_at", "string"),
]


def create_test_results_document(schema_name: str = "StandardizedTestResultsLedger") -> Dict[str, Any]:
    """Create a canonical BEJSON 105a test execution ledger with Core-stamped field_uuid values."""
    document_payload: Dict[str, Any] = {
        "Format": "BEJSON",
        "Format_Version": "105a",
        "Format_Creator": "Elton Boehnen",
        "Schema_Name": schema_name,
        "Records_Type": [TEST_EXECUTION_RECORD_TYPE],
        "Fields": [],
        "Values": [],
    }
    for field_name, field_type in TEST_EXECUTION_FIELD_SPECS:
        bejson_core_define_field(document_payload, field_name, field_type)
    return document_payload
