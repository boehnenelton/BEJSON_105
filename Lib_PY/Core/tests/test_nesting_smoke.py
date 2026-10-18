"""
Library:         test_nesting_smoke.py
Family:          Core
Module Purpose:  Smoke/behavior tests for the nesting modules (scan, mutate, query, error codes 130-139); written to prove the Core_Nesting -> Core move changed no behavior.
Architecture:    Standalone script; resolves the nesting modules relative to this file (no absolute paths).
Format_Scope:    Nested 104 (NOT 104db, NOT MFDB)
Glossary:        BEJSON 104, 104a and 104db are the three file formats (Format_Version). 104db = ONE file holding 2+ entity types
                 (Record_Type_Parent discriminator, null-padding). MFDB is NOT a format and NOT 104db: it is a layer made of one 104a manifest
                 (104a.mfdb.bejson) plus dense 104 entity files linked by Parent_Hierarchy. MFDB-132 = an MFDB packed into one Chunked-104a document.
Version:         1.1.0
Release_Version: 300
Date:            2026-10-16
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   e6aa38ee-0051-4e31-9993-295fd26d904e
Changelog:
  1.1.0 (2026-10-16) - Added tests: Core validator rules apply to nested cells; same-schema documents do not share cache entries.
  1.0.2 (2026-10-16) - Query API now read from core_nesting (nesting_query merged).
  1.0.1 (2026-10-16) - Reads codes 130-139 from lib_bejson_Core_bejson_errors (nesting errors file removed).
"""

import importlib
import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, ".."))

N = importlib.import_module("lib_bejson_Core_bejson_core_nesting")
Q = N  # query API lives in core_nesting
E = importlib.import_module("lib_bejson_Core_bejson_errors")

INNER = {"Format": "BEJSON", "Format_Version": "104", "Format_Creator": "Elton Boehnen", "Records_Type": ["Items"],
         "Fields": [{"name": "sku", "type": "string"}, {"name": "qty", "type": "integer"}], "Values": [["a", 1], ["b", 2]]}


def outer():
    return {"Format": "BEJSON", "Format_Version": "104", "Format_Creator": "Elton Boehnen", "Records_Type": ["Order"],
            "Fields": [{"name": "id", "type": "string"}, {"name": "items", "type": "string"}],
            "Values": [["o1", json.dumps(INNER)], ["o2", None]]}


class TestNesting(unittest.TestCase):
    def test_scan(self):
        r = N.bejson_nesting_scan(outer(), use_cache=False)
        self.assertEqual((r.nested_found, r.nested_valid, r.nested_invalid, r.scanned_cells, r.max_depth_seen), (1, 1, 0, 4, 1))
        self.assertIn("Scan Summary", N.bejson_nesting_summary(r))
        cells = N.bejson_nesting_flatten(r)
        self.assertEqual(len(cells), 1)
        self.assertEqual(N.bejson_nesting_get_field_map(cells[0]), {"sku": 0, "qty": 1})

    def test_mutate_appends_field_and_null_pads(self):
        doc = outer()
        r = N.bejson_nesting_scan(doc, use_cache=False)
        N.bejson_nesting_mutate(doc, r.cells[0], lambda d: d["Fields"].append({"name": "note", "type": "string"}))
        self.assertEqual(json.loads(doc["Values"][0][1])["Values"][0], ["a", 1, None])

    def test_mutate_rejects_field_removal(self):
        doc = outer()
        r = N.bejson_nesting_scan(doc, use_cache=False)
        with self.assertRaises(ValueError):
            N.bejson_nesting_mutate(doc, r.cells[0], lambda d: d["Fields"].pop())

    def test_query(self):
        self.assertEqual(len(Q.bejson_nesting_query(outer(), "items")), 2)
        self.assertEqual(Q.bejson_nesting_get_path(outer(), "nope", "DEF"), "DEF")
        with self.assertRaises(ValueError):
            Q.bejson_nesting_query(outer(), "bad..path")

    def _outer_with(self, inner):
        d = outer(); d["Values"][0][1] = json.dumps(inner); return d

    def test_core_validator_rules_apply_to_nested_cells(self):
        bad_creator = dict(INNER, Format_Creator="Someone")
        dup_fields = dict(INNER, Fields=[{"name": "a", "type": "string"}, {"name": "a", "type": "string"}], Values=[["x", "y"]])
        for bad in (bad_creator, dup_fields):
            N.bejson_nesting_cache_clear()
            r = N.bejson_nesting_scan(self._outer_with(bad), use_cache=False)
            self.assertEqual((r.nested_valid, r.nested_invalid), (0, 1))

    def test_same_schema_different_content_is_not_served_from_cache(self):
        N.bejson_nesting_cache_clear()
        N.bejson_nesting_scan(self._outer_with(INNER))
        r = N.bejson_nesting_scan(self._outer_with(dict(INNER, Format_Creator="Someone")))
        self.assertEqual(r.nested_invalid, 1)

    def test_error_codes_unchanged(self):
        self.assertEqual(E.E_NESTING_INVALID_CELL, 130)
        self.assertEqual(E.E_NESTING_QUERY_EMPTY_PATH, 139)
        vals = sorted(v for k, v in vars(E).items() if k.startswith("E_NESTING_") and isinstance(v, int))
        self.assertEqual(vals, list(range(130, 140)))


if __name__ == "__main__":
    unittest.main()
