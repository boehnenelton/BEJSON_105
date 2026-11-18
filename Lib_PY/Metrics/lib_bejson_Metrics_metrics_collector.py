#!/usr/bin/env python3
"""
Name:          lib_bejson_Metrics_metrics_collector.py
Description:   Collects and normalizes test_series_1..3 and benchmark runs into canonical BEJSON 105a metrics_runs.105a.bejson.
Version:       1.0.0
Date Created:  2026-11-18
Author Credit: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID: lib-bejson-metrics-collector-20261118
License:       PolyForm-Noncommercial-1.0.0
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

if sys.version_info < (3, 10):
    raise RuntimeError("Python 3.10+ is required.")

_CORE_DIR: Path = Path(__file__).resolve().parent.parent / "Core"
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

from lib_bejson_Core_bejson_core import (
    ResilientPIDLock,
    bejson_core_add_record_105,
    bejson_core_atomic_write,
)
from lib_bejson_Metrics_metrics_errors import E_METRICS_MISSING_SOURCE, MetricsLibraryError
from lib_bejson_Metrics_metrics_schemas import create_metrics_runs_document
from lib_bejson_Metrics_metrics_validator import validate_metrics_document

LOGGER_INSTANCE = logging.getLogger("lib_bejson_Metrics.collector")


def _append_metric_row(
    ledger_doc: Dict[str, Any],
    series_id: str,
    suite_name: str,
    metric_name: str,
    metric_category: str,
    primary_value: float,
    baseline_value: float,
    unit: str,
    reduction_pct: float,
    speedup_factor: float,
    peak_rss_mb: float,
    passed: bool,
    recorded_at: str,
) -> str:
    """Append one standardized MetricRunRecord row using Core 105 UUID-addressed writer."""
    return bejson_core_add_record_105(
        ledger_doc,
        [
            series_id,
            suite_name,
            metric_name,
            metric_category,
            round(float(primary_value), 4),
            round(float(baseline_value), 4),
            unit,
            round(float(reduction_pct), 4),
            round(float(speedup_factor), 4),
            round(float(peak_rss_mb), 4),
            bool(passed),
            recorded_at,
        ],
    )


def ingest_test_series_directory(metrics_root_dir: Path) -> Dict[str, Any]:
    """Ingest test_series_1, test_series_2, test_series_3, and consolidated suite runs into a BEJSON 105a ledger."""
    if not metrics_root_dir.is_dir():
        raise MetricsLibraryError(
            f"Metrics root directory not found: {metrics_root_dir}",
            error_code=E_METRICS_MISSING_SOURCE,
        )

    ledger_doc = create_metrics_runs_document("BEJSON_105_Metrics_Ledger")

    # Series 1: Core & Federation
    s1_file = metrics_root_dir / "test_series_1" / "benchmark_summary.json"
    if s1_file.is_file():
        s1 = json.loads(s1_file.read_text(encoding="utf-8"))
        ts1 = str(s1.get("timestamp", ""))
        scale1 = s1.get("scale_metrics", {})
        speed1 = s1.get("speed_metrics", {})
        rss1 = float(scale1.get("peak_rss_mb", 0.0))
        all_ok1 = all(bool(v) for v in s1.get("stage_verification", {}).values())
        _append_metric_row(
            ledger_doc, "test_series_1", "federation_core", "token_consumption",
            "tokens", float(scale1.get("bej_tokens", 0.0)), float(scale1.get("std_tokens", 0.0)),
            "tokens", float(scale1.get("token_reduction_pct", 0.0)), 1.0, rss1, all_ok1, ts1,
        )
        _append_metric_row(
            ledger_doc, "test_series_1", "federation_core", "point_lookup_throughput",
            "throughput", float(speed1.get("lookups_per_sec", 0.0)), 0.0,
            "ops/sec", 0.0, 1.0, rss1, all_ok1, ts1,
        )

    # Series 2: BEJSON 105 vs SQLite
    s2_file = metrics_root_dir / "test_series_2" / "sql_comparison_summary.json"
    if s2_file.is_file():
        s2 = json.loads(s2_file.read_text(encoding="utf-8"))
        ts2 = str(s2.get("timestamp", ""))
        qm2 = s2.get("query_and_storage_metrics", {})
        tm2 = s2.get("llm_token_metrics", {})
        rss2 = float(s2.get("system_telemetry", {}).get("vm_rss_mb", 0.0))
        _append_metric_row(
            ledger_doc, "test_series_2", "bejson_vs_sqlite", "point_query_throughput",
            "throughput", float(qm2.get("bejson_point_query_ops_sec", 0.0)),
            float(qm2.get("sql_point_query_ops_sec", 0.0)), "ops/sec",
            0.0, float(qm2.get("query_speedup_factor", 1.0)), rss2, True, ts2,
        )
        _append_metric_row(
            ledger_doc, "test_series_2", "bejson_vs_sqlite", "llm_token_savings",
            "tokens", float(tm2.get("bejson_tokens", 0.0)),
            float(tm2.get("sql_json_tokens", 0.0)), "tokens",
            float(tm2.get("token_savings_pct", 0.0)), 1.0, rss2, True, ts2,
        )

    # Series 3: High-Scale Ingestion (25k vs 60k)
    s3_file = metrics_root_dir / "test_series_3" / "scale_benchmarks_summary.json"
    if s3_file.is_file():
        s3 = json.loads(s3_file.read_text(encoding="utf-8"))
        ts3 = str(s3.get("timestamp", ""))
        for wl_key in ("workload_1_25k", "workload_2_60k"):
            wl = s3.get(wl_key, {})
            if wl:
                _append_metric_row(
                    ledger_doc, "test_series_3", str(wl.get("workload_name", wl_key)),
                    "ingestion_throughput", "throughput",
                    float(wl.get("ingestion_records_per_sec", 0.0)), 0.0, "rec/sec",
                    0.0, 1.0, float(wl.get("peak_rss_mb", 0.0)), True, ts3,
                )
                _append_metric_row(
                    ledger_doc, "test_series_3", str(wl.get("workload_name", wl_key)),
                    "point_lookup_throughput", "throughput",
                    float(wl.get("avg_point_lookup_ops_sec", 0.0)), 0.0, "ops/sec",
                    0.0, 1.0, float(wl.get("peak_rss_mb", 0.0)), True, ts3,
                )

    validate_metrics_document(ledger_doc)
    return ledger_doc


def collect_and_save_metrics(
    metrics_root_dir: Path,
    output_filename: str = "metrics_runs.105a.bejson",
) -> Path:
    """Ingest metrics, validate against 105a schema, and atomically persist under PID lock in data/."""
    ledger_doc = ingest_test_series_directory(metrics_root_dir)
    data_dir = metrics_root_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    output_path = data_dir / output_filename
    lock_handle = ResilientPIDLock(str(output_path), timeout_seconds=10)
    with lock_handle:
        bejson_core_atomic_write(str(output_path), ledger_doc)
    LOGGER_INSTANCE.info("Saved %d standardized metric records to %s", len(ledger_doc["Values"]), output_path)
    return output_path
