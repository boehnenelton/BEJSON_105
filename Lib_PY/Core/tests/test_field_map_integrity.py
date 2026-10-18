"""
Library:         test_field_map_integrity.py
Family:          Core
Module Purpose:  Regression tests for the field-map cache: forged or persisted maps, stale caches, shared-map isolation, comma/duplicate field names, validator rules, lookup cost.
Architecture:    Standalone script; resolves the library modules relative to this file (no absolute paths).
Format_Scope:    104 | 104a | 104db (generic)
Glossary:        BEJSON 104, 104a and 104db are the three file formats (Format_Version). 104db = ONE file holding 2+ entity types
                 (Record_Type_Parent discriminator, null-padding). MFDB is NOT a format and NOT 104db: it is a layer made of one 104a manifest
                 (104a.mfdb.bejson) plus dense 104 entity files linked by Parent_Hierarchy. MFDB-132 = an MFDB packed into one Chunked-104a document.
Version:         1.0.0
Release_Version: 300
Date:            2026-10-15
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   c26dc71b-0ae6-48c7-9fea-34d71c524e24
"""
import copy
import json
import logging
import os
import sys
import tempfile
import timeit
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
logging.disable(logging.CRITICAL)

import lib_bejson_Core_bejson_core as core
import lib_bejson_Core_bejson_validator as validator

NAMES = [f"f{i}" for i in range(6)]


def make_doc(names=NAMES, version="104a", cache=None):
    doc = {
        "Format": "BEJSON", "Format_Version": version, "Format_Creator": "Elton Boehnen",
        "Records_Type": ["T"], "Fields": [{"name": n, "type": "string"} for n in names],
        "Values": [[f"v_{n}" for n in names]],
    }
    if cache is not None:
        doc["_bejson_field_map"] = cache
    return doc


def swapped_inner_map():
    forged = {n: i for i, n in enumerate(NAMES)}
    forged["f1"], forged["f2"] = 2, 1  # first/middle/last still look correct
    return forged


class FieldMapIntegrity(unittest.TestCase):
    def value_for(self, doc, name):
        return doc["Values"][0][core.bejson_core_get_field_index(doc, name)]

    def test_forged_map_from_json_is_rebuilt(self):
        doc = json.loads(json.dumps(make_doc(cache=swapped_inner_map())))
        self.assertEqual(self.value_for(doc, "f1"), "v_f1")

    def test_cache_round_trip_through_json_and_deepcopy(self):
        doc = make_doc()
        core.bejson_core_get_field_map(doc)
        self.assertEqual(self.value_for(json.loads(json.dumps(doc)), "f3"), "v_f3")
        self.assertEqual(core.bejson_core_get_field_index(copy.deepcopy(doc), "f5"), 5)

    def test_persisted_file_cache_is_stripped_on_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "poison.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(make_doc(cache=swapped_inner_map()), fh)
            loaded = core.bejson_core_load_file(path)
            self.assertNotIn("_bejson_field_map", loaded)
            self.assertFalse(validator.validate_bejson(path, is_file=True).valid)

    def test_stale_after_fields_mutation(self):
        doc = make_doc(names=["a", "b", "c"])
        core.bejson_core_get_field_map(doc)
        doc["Fields"].append({"name": "d", "type": "string"})
        self.assertEqual(core.bejson_core_get_field_index(doc, "d"), 3)
        doc["Fields"].pop(0)
        self.assertEqual(core.bejson_core_get_field_index(doc, "a"), -1)
        self.assertEqual(core.bejson_core_get_field_index(doc, "b"), 0)

    def test_maps_are_not_shared_between_documents(self):
        first, second = make_doc(), make_doc()
        core.bejson_core_get_field_map(first)["f0"] = 99
        self.assertEqual(core.bejson_core_get_field_map(second)["f0"], 0)

    def test_duplicate_field_names_rejected(self):
        self.assertFalse(validator.validate_bejson(make_doc(names=["x", "x"])).valid)

    def test_validator_dict_rules(self):
        self.assertFalse(validator.validate_bejson(make_doc(cache=swapped_inner_map())).valid)
        honest = make_doc()
        core.bejson_core_get_field_map(honest)
        self.assertTrue(validator.validate_bejson(honest).valid)
        plain = make_doc(version="104")
        core.bejson_core_get_field_map(plain)
        self.assertTrue(validator.validate_bejson(plain).valid)

    def test_reserved_underscore_keys(self):
        for ver in ("104", "104a", "104db"):
            doc = make_doc(version=ver)
            doc["_anything"] = 1
            self.assertFalse(validator.validate_bejson(json.dumps(doc)).valid, f"{ver} persisted _anything")
        persisted = make_doc()
        persisted["_nesting_field_map"] = {}
        self.assertFalse(validator.validate_bejson(json.dumps(persisted)).valid)
        mem = make_doc()
        mem["_anything"] = 1
        self.assertFalse(validator.validate_bejson(mem).valid)
        mem = make_doc()
        mem["_nesting_field_map"] = {}
        self.assertTrue(validator.validate_bejson(mem).valid)
        mem = make_doc()
        mem["Custom_Header"] = 1
        self.assertTrue(validator.validate_bejson(mem).valid)

    def test_lookup_cost_is_flat_in_field_count(self):
        def cost(count):
            doc = make_doc(names=[f"f{i}" for i in range(count)])
            core.bejson_core_get_field_map(doc)
            return min(timeit.repeat(lambda: core.bejson_core_get_field_index(doc, "f7"), number=20000, repeat=5))
        self.assertLess(cost(10000) / cost(10), 3.0)


if __name__ == "__main__":
    unittest.main()
