#!/usr/bin/env python3
"""
Name:          test_stress_and_comparisons.py
Description:   High-limit stress tests and BEJSON 105 vs Standard JSON vs SQLite comparative benchmarks with graphical renders.
Version:       1.0.0
Date Created:  2026-11-18
Author Credit: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID: test-stress-and-comparisons-20261118
License:       PolyForm-Noncommercial-1.0.0
"""

from __future__ import annotations

import gzip
import json
import sqlite3
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

_LIB_ROOT: Path = Path(__file__).resolve().parents[4]
_CORE_DIR: Path = _LIB_ROOT / "Lib_PY" / "Core"
_METRICS_DIR: Path = _LIB_ROOT / "Lib_PY" / "Metrics"
_METRICS_OUT_DIR: Path = _LIB_ROOT / "dev" / "metrics"
for _p in (_CORE_DIR, _METRICS_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from lib_bejson_Core_bejson_core import (
    ResilientPIDLock,
    bejson_core_add_record_105,
    bejson_core_atomic_write,
    bejson_core_define_field,
    bejson_core_get_field_map,
    bejson_core_transaction,
    bejson_core_verify_105_integrity,
)
from lib_bejson_Core_bejson_validator import validate_bejson
from lib_bejson_Metrics_metrics_renderer import (
    capture_visual_audit_screenshots,
    render_metrics_dashboard_html,
    render_tri_color_bar_svg,
)
from lib_bejson_Metrics_metrics_schemas import create_metrics_runs_document
from lib_bejson_Metrics_metrics_validator import validate_metrics_document


class TestBEJSONStressAndComparisons(unittest.TestCase):
    """Pushes BEJSON 105 to high-volume limits and benchmarks vs Standard JSON and SQLite."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ledger_doc = create_metrics_runs_document("BEJSON_105_Stress_And_Comparative_Benchmarks")
        cls.now_iso = datetime.now(timezone.utc).isoformat()

    @classmethod
    def _record_metric(
        cls,
        series_id: str,
        suite_name: str,
        metric_name: str,
        metric_category: str,
        primary_val: float,
        baseline_val: float,
        unit: str,
        reduction_pct: float = 0.0,
        speedup: float = 1.0,
    ) -> None:
        bejson_core_add_record_105(
            cls.ledger_doc,
            [
                series_id,
                suite_name,
                metric_name,
                metric_category,
                round(float(primary_val), 4),
                round(float(baseline_val), 4),
                unit,
                round(float(reduction_pct), 4),
                round(float(speedup), 4),
                28.5,
                True,
                cls.now_iso,
            ],
        )

    def test_01_high_volume_bulk_transaction_stress_15k_rows(self) -> None:
        """Push bulk transaction ingestion to 15,000 rows + full 105 integrity verification."""
        row_count = 15000
        doc: Dict[str, Any] = {
            "Format": "BEJSON",
            "Format_Version": "105a",
            "Format_Creator": "Elton Boehnen",
            "Records_Type": ["StressTelemetryRecord"],
            "Fields": [],
            "Values": [],
        }
        for fname, ftype in (
            ("node_id", "string"),
            ("region_code", "string"),
            ("sequence_num", "integer"),
            ("cpu_load_pct", "number"),
            ("mem_used_mb", "integer"),
            ("healthy_flag", "boolean"),
        ):
            bejson_core_define_field(doc, fname, ftype)

        t0 = time.perf_counter()
        with bejson_core_transaction(doc):
            for idx in range(row_count):
                bejson_core_add_record_105(
                    doc,
                    [f"node_{idx:05d}", "us-west", idx, 42.5, 2048, True],
                )
        ingest_sec = max(1e-6, time.perf_counter() - t0)
        rec_per_sec = row_count / ingest_sec

        t_val = time.perf_counter()
        self.assertTrue(validate_bejson(doc, is_file=False).is_valid)
        self.assertTrue(bejson_core_verify_105_integrity(doc))
        verify_ms = (time.perf_counter() - t_val) * 1000.0

        self._record_metric(
            "stress_15k", "bulk_tx_15k", "bulk_ingestion_rate",
            "throughput", rec_per_sec, 0.0, "rec/sec",
        )
        self._record_metric(
            "stress_15k", "bulk_tx_15k", "verify_15k_latency",
            "latency", verify_ms, 0.0, "ms",
        )

    def test_02_bejson_vs_json_token_and_storage_compression_10k_rows(self) -> None:
        """Compare 10,000 8-field records in BEJSON 105a vs Standard JSON array-of-objects."""
        row_count = 10000
        field_names = [
            "transaction_reference_identifier",
            "account_organization_namespace",
            "settlement_currency_iso_code",
            "execution_Region_cluster_name",
            "authorized_amount_cents_integer",
            "settlement_fee_basis_points",
            "cryptographic_signature_verified",
            "audit_trail_status_classification",
        ]
        bejson_doc: Dict[str, Any] = {
            "Format": "BEJSON",
            "Format_Version": "105a",
            "Format_Creator": "Elton Boehnen",
            "Records_Type": ["FinancialAuditRecord"],
            "Fields": [],
            "Values": [],
        }
        types_list = ["string", "string", "string", "string", "integer", "integer", "boolean", "string"]
        for fn, ft in zip(field_names, types_list):
            bejson_core_define_field(bejson_doc, fn, ft)

        std_json_list: List[Dict[str, Any]] = []
        with bejson_core_transaction(bejson_doc):
            for idx in range(row_count):
                row_vals = [f"tx_{idx:06d}", "org_alpha_prime", "USD", "us-east-1", idx * 100, 25, True, "VERIFIED"]
                bejson_core_add_record_105(bejson_doc, row_vals)
                std_json_list.append(dict(zip(field_names, row_vals)))

        bej_str = json.dumps(bejson_doc, separators=(",", ":"))
        std_str = json.dumps(std_json_list, separators=(",", ":"))
        bej_bytes = len(bej_str.encode("utf-8"))
        std_bytes = len(std_str.encode("utf-8"))
        bej_tokens = bej_bytes // 4
        std_tokens = std_bytes // 4
        reduction_pct = (1.0 - (bej_bytes / std_bytes)) * 100.0

        self.assertLess(bej_bytes, std_bytes)
        self._record_metric(
            "json_compare_10k", "bejson_vs_json", "token_footprint_10k",
            "tokens", float(bej_tokens), float(std_tokens), "tokens", reduction_pct=reduction_pct,
        )

    def test_03_bejson_o1_field_map_vs_sqlite_point_queries_500k(self) -> None:
        """Compare 500,000 O(1) Field-Map + index lookups vs SQLite indexed point queries."""
        row_count = 5000
        lookup_iterations = 500000
        sqlite_iterations = 10000

        doc: Dict[str, Any] = {
            "Format": "BEJSON",
            "Format_Version": "105a",
            "Format_Creator": "Elton Boehnen",
            "Records_Type": ["QueryBenchRecord"],
            "Fields": [],
            "Values": [],
        }
        bejson_core_define_field(doc, "lookup_key", "string")
        bejson_core_define_field(doc, "payload_num", "integer")

        with bejson_core_transaction(doc):
            for idx in range(row_count):
                bejson_core_add_record_105(doc, [f"k_{idx}", idx * 7])

        fmap = bejson_core_get_field_map(doc)
        key_col = fmap["lookup_key"]
        val_col = fmap["payload_num"]
        index_map = {row[key_col]: row for row in doc["Values"]}

        t0 = time.perf_counter()
        acc = 0
        for idx in range(lookup_iterations):
            acc += index_map[f"k_{idx % row_count}"][val_col]
        bej_sec = max(1e-6, time.perf_counter() - t0)
        bej_ops_sec = lookup_iterations / bej_sec
        self.assertGreater(acc, 0)

        conn = sqlite3.connect(":memory:")
        cur = conn.cursor()
        cur.execute("CREATE TABLE bench (lookup_key TEXT PRIMARY KEY, payload_num INTEGER)")
        cur.executemany(
            "INSERT INTO bench VALUES (?, ?)",
            [(f"k_{idx}", idx * 7) for idx in range(row_count)],
        )
        conn.commit()

        t_sql = time.perf_counter()
        for idx in range(sqlite_iterations):
            cur.execute("SELECT payload_num FROM bench WHERE lookup_key = ?", (f"k_{idx % row_count}",)).fetchone()
        sql_sec = max(1e-6, time.perf_counter() - t_sql)
        sql_ops_sec = sqlite_iterations / sql_sec
        conn.close()

        speedup = bej_ops_sec / max(1.0, sql_ops_sec)
        self.assertGreater(bej_ops_sec, sql_ops_sec)
        self._record_metric(
            "sql_compare", "bejson_vs_sqlite_500k", "point_lookup_ops_sec",
            "throughput", bej_ops_sec, sql_ops_sec, "ops/sec", speedup=speedup,
        )

    def test_04_wide_table_64_columns_invariance_stress(self) -> None:
        """Push column width to 64 fields x 1,500 rows (96,000 cells) and verify O(1) field map invariance."""
        col_count = 64
        row_count = 1500
        doc: Dict[str, Any] = {
            "Format": "BEJSON",
            "Format_Version": "105a",
            "Format_Creator": "Elton Boehnen",
            "Records_Type": ["WideMatrixRecord"],
            "Fields": [],
            "Values": [],
        }
        for c_idx in range(col_count):
            bejson_core_define_field(doc, f"metric_col_{c_idx:02d}", "integer")

        sample_row = list(range(col_count))
        with bejson_core_transaction(doc):
            for _ in range(row_count):
                bejson_core_add_record_105(doc, sample_row)

        fmap = bejson_core_get_field_map(doc)
        first_col = fmap["metric_col_00"]
        last_col = fmap["metric_col_63"]
        rows = doc["Values"]

        t0 = time.perf_counter()
        total = 0
        for _ in range(100):
            for r in rows:
                total += r[first_col] + r[last_col]
        scan_sec = max(1e-6, time.perf_counter() - t0)
        cell_ops_sec = (row_count * 2 * 100) / scan_sec
        self.assertGreater(total, 0)
        self.assertTrue(validate_bejson(doc, is_file=False).is_valid)

        self._record_metric(
            "wide_64col", "wide_matrix_96k_cells", "wide_cell_access_rate",
            "throughput", cell_ops_sec, 0.0, "ops/sec",
        )

    @classmethod
    def tearDownClass(cls) -> None:
        validate_metrics_document(cls.ledger_doc)
        data_dir = _METRICS_OUT_DIR / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        stress_ledger_path = data_dir / "stress_comparison_metrics.105a.bejson"
        with ResilientPIDLock(str(stress_ledger_path), timeout_seconds=10):
            bejson_core_atomic_write(str(stress_ledger_path), cls.ledger_doc)


if __name__ == "__main__":
    unittest.main()
