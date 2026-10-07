"""
Library:        test_schema_api.py
Family:         Core (tests)
Description:    unittest suite for the PY Schema API (extract, validate_against,
                 validate_against_detailed, get_field_map, infer_from_data).
                 Real imports of the committed source; no exec() strings.
Version:        1.0.0
Date:           2026-10-03
Author:         Elton Boehnen
Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
Format_Creator: Elton Boehnen
RELATIONAL_ID:  b2f6a1d4-5c93-4e7a-8d10-3a9c7e4f5b61
Release_Version: 300

Run:  python3 -m unittest tests.test_schema_api -v
"""

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import lib_bejson_Core_bejson_schema as S


def make_doc():
    return {
        "Format": "BEJSON", "Format_Version": "104a", "Format_Creator": "Elton Boehnen",
        "Records_Type": ["Item"],
        "Fields": [{"name": "id", "type": "string"}, {"name": "qty", "type": "integer"}],
        "Values": [["a", 1], ["b", 2]],
    }


class TestExtract(unittest.TestCase):
    def test_values_emptied_structure_kept(self):
        sch = S.bejson_schema_extract(make_doc())
        self.assertEqual(sch["Values"], [])
        self.assertEqual([f["name"] for f in sch["Fields"]], ["id", "qty"])

    def test_does_not_alias_source(self):
        doc = make_doc()
        sch = S.bejson_schema_extract(doc)
        sch["Fields"].append({"name": "x", "type": "string"})
        sch["Records_Type"].append("Other")
        self.assertEqual(len(doc["Fields"]), 2)
        self.assertEqual(doc["Records_Type"], ["Item"])
        self.assertEqual(len(doc["Values"]), 2)


class TestValidateAgainstBool(unittest.TestCase):
    def test_legacy_bool_api_unchanged(self):
        doc = make_doc()
        self.assertTrue(S.bejson_schema_validate_against(doc, doc["Fields"]))
        self.assertFalse(S.bejson_schema_validate_against(doc, doc["Fields"][:1]))


class TestValidateAgainstDetailed(unittest.TestCase):
    def test_valid(self):
        doc = make_doc()
        r = S.bejson_schema_validate_against_detailed(doc, S.bejson_schema_extract(doc))
        self.assertEqual(r, {"valid": True, "errors": []})

    def test_version_mismatch(self):
        doc = make_doc(); sch = S.bejson_schema_extract(doc); sch["Format_Version"] = "104"
        r = S.bejson_schema_validate_against_detailed(doc, sch)
        self.assertFalse(r["valid"]); self.assertTrue(r["errors"][0].startswith("Version mismatch"))

    def test_records_type_mismatch(self):
        doc = make_doc(); sch = S.bejson_schema_extract(doc); sch["Records_Type"] = ["Other"]
        r = S.bejson_schema_validate_against_detailed(doc, sch)
        self.assertIn("Records_Type mismatch: Document types do not match schema types.", r["errors"])

    def test_field_count_mismatch_short_circuits_field_checks(self):
        doc = make_doc(); sch = S.bejson_schema_extract(doc); sch["Fields"].pop()
        r = S.bejson_schema_validate_against_detailed(doc, sch)
        self.assertEqual(len(r["errors"]), 1); self.assertTrue(r["errors"][0].startswith("Field count mismatch"))

    def test_name_type_and_parent_mismatch_all_reported(self):
        doc = make_doc(); sch = S.bejson_schema_extract(doc)
        sch["Fields"][0]["name"] = "uid"
        sch["Fields"][1]["type"] = "string"
        sch["Fields"][1]["Record_Type_Parent"] = "Item"
        r = S.bejson_schema_validate_against_detailed(doc, sch)
        joined = " | ".join(r["errors"])
        self.assertFalse(r["valid"])
        self.assertIn("Field name mismatch at index 0: expected 'uid', found 'id'", joined)
        self.assertIn("Field type mismatch for 'qty': expected 'string', found 'integer'", joined)
        self.assertIn("Record_Type_Parent mismatch for 'qty'", joined)

    def test_missing_keys_do_not_raise(self):
        r = S.bejson_schema_validate_against_detailed({}, {})
        self.assertTrue(r["valid"])


class TestFieldMapAndInfer(unittest.TestCase):
    def test_get_field_map_maps_name_to_definition(self):
        fm = S.bejson_schema_get_field_map(make_doc())
        self.assertEqual(fm["qty"], {"name": "qty", "type": "integer"})
        self.assertEqual(S.bejson_schema_get_field_map({}), {})

    def test_infer_from_data_defaults_and_wrapping(self):
        fields = [{"name": "id", "type": "string"}]
        sch = S.bejson_schema_infer_from_data("Item", fields)
        self.assertEqual((sch["Format"], sch["Format_Version"], sch["Records_Type"], sch["Values"]),
                         ("BEJSON", "104a", ["Item"], []))
        sch2 = S.bejson_schema_infer_from_data(["A", "B"], fields, "104db")
        self.assertEqual((sch2["Format_Version"], sch2["Records_Type"]), ("104db", ["A", "B"]))

    def test_infer_from_data_does_not_alias_input_fields(self):
        fields = [{"name": "id", "type": "string"}]
        sch = S.bejson_schema_infer_from_data("Item", fields)
        fields[0]["name"] = "changed"
        self.assertEqual(sch["Fields"][0]["name"], "id")

    def test_roundtrip_inferred_schema_validates_matching_doc(self):
        doc = make_doc()
        sch = S.bejson_schema_infer_from_data(doc["Records_Type"], doc["Fields"], doc["Format_Version"])
        self.assertTrue(S.bejson_schema_validate_against_detailed(doc, sch)["valid"])


class TestFieldTypeClosedSet(unittest.TestCase):
    """"any" (and any non-spec type) must be rejected by the validator."""
    def test_any_rejected_and_spec_types_accepted(self):
        import json
        import lib_bejson_Core_bejson_validator as V
        def doc(t):
            return json.dumps({"Format": "BEJSON", "Format_Version": "104", "Format_Creator": "Elton Boehnen",
                               "Records_Type": ["R"], "Fields": [{"name": "a", "type": t}], "Values": []})
        for bad in ("any", "ANY", "String", "text", ""):
            with self.assertRaises(Exception, msg=bad):
                V.bejson_validator_validate_string(doc(bad))
        for good in ("string", "integer", "number", "boolean", "array", "object"):
            self.assertTrue(V.bejson_validator_validate_string(doc(good)), good)
        self.assertNotIn("any", V.VALID_FIELD_TYPES)


if __name__ == "__main__":
    unittest.main()
