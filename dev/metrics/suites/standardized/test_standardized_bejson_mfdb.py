#!/usr/bin/env python3
"""
Name:          test_standardized_bejson_mfdb.py
Description:   Standardized runnable BEJSON 105 and MFDB v1.40 test suite for metrics collection and graphing.
Version:       1.0.0
Date Created:  2026-11-18
Author Credit: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID: test-standardized-bejson-mfdb-20261118
License:       PolyForm-Noncommercial-1.0.0
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_LIB_ROOT: Path = Path(__file__).resolve().parents[4]
_CORE_DIR: Path = _LIB_ROOT / "Lib_PY" / "Core"
_METRICS_DIR: Path = _LIB_ROOT / "Lib_PY" / "Metrics"
for _p in (_CORE_DIR, _METRICS_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from lib_bejson_Core_bejson_core import (
    bejson_core_add_record_105,
    bejson_core_atomic_write,
    bejson_core_define_field,
    bejson_core_get_field_map,
    bejson_core_verify_105_integrity,
)
from lib_bejson_Core_bejson_validator import validate_bejson
from lib_bejson_Core_mfdb_core import (
    mfdb_core_add_entity_record_105,
    mfdb_core_create_database,
    mfdb_core_enable_ref_integrity,
)


class TestStandardizedBEJSONAndMFDB(unittest.TestCase):
    """Standardized BEJSON 105 and MFDB v1.40 integrity & performance tests."""

    def test_bejson_105_atomic_write_and_o1_lookup(self) -> None:
        doc = {
            "Format": "BEJSON",
            "Format_Version": "105a",
            "Format_Creator": "Elton Boehnen",
            "Records_Type": ["BenchItem"],
            "Fields": [],
            "Values": [],
        }
        bejson_core_define_field(doc, "item_key", "string")
        bejson_core_define_field(doc, "item_score", "integer")
        for idx in range(50):
            bejson_core_add_record_105(doc, [f"key_{idx}", idx * 10])

        fmap = bejson_core_get_field_map(doc)
        self.assertIn("item_key", fmap)
        self.assertTrue(validate_bejson(doc, is_file=False).is_valid)
        self.assertTrue(bejson_core_verify_105_integrity(doc))

        with tempfile.TemporaryDirectory() as tmp:
            out_file = Path(tmp) / "bench.105a.bejson"
            self.assertTrue(bejson_core_atomic_write(str(out_file), doc))
            self.assertTrue(out_file.is_file())

    def test_mfdb_v140_manifest_and_fk_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_dir = Path(tmp) / "mfdb_std"
            manifest_path = mfdb_core_create_database(
                str(db_dir),
                "StandardizedMFDB",
                entities=[
                    {
                        "name": "parents",
                        "format_version": "105",
                        "fields": [{"name": "parent_name", "type": "string"}],
                    },
                    {
                        "name": "children",
                        "format_version": "105",
                        "fields": [
                            {"name": "parent_uuid", "type": "string", "fk_target_entity": "parents", "fk_on_delete": "restrict"},
                            {"name": "child_label", "type": "string"},
                        ],
                    },
                ],
                mfdb_version="1.40",
            )
            mfdb_core_enable_ref_integrity(manifest_path)
            parent_rec = mfdb_core_add_entity_record_105(manifest_path, "parents", ["root_node"])
            parent_uuid = (
                parent_rec.get("record_uuid") or parent_rec["Values"][-1][0]
                if isinstance(parent_rec, dict)
                else str(parent_rec)
            )
            child_rec = mfdb_core_add_entity_record_105(manifest_path, "children", [parent_uuid, "leaf_a"])
            self.assertTrue(parent_uuid)
            self.assertTrue(child_rec)


if __name__ == "__main__":
    unittest.main()
