"""
Library:        test_105_104_parity_suite.py
Family:         Core (tests)
Description:    Proves the 105-series enforces everything its 104 base enforces
                (row length, value types, Records_Type count, 105a primitives,
                105db Record_Type_Parent rules), that 105 writers and the
                upgrade path reject bad input, and that MFDB maintenance
                (deep_verify / self_heal / discover / 104 writer) is safe on
                105 entities. Run: python3 tests/test_105_104_parity_suite.py
Version:        1.0.0
Date:           2026-10-26
Author:         Elton Boehnen
Format_Creator: Elton Boehnen
RELATIONAL_ID:  3f0c6a52-8d1e-4b7a-9c35-6e2a41d7b9f0
Release_Version: 300
"""

import copy
import json
import os
import shutil
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import lib_bejson_Core_bejson_validator as V
import lib_bejson_Core_bejson_core as C
import lib_bejson_Core_bejson_upgrade as U
import lib_bejson_Core_mfdb_core as M
import lib_bejson_Core_mfdb_validator as MV

U4 = lambda: str(uuid.uuid4())
HDR = {"Format": "BEJSON", "Format_Creator": "Elton Boehnen"}


def d105(version="105", types=("T",), fields=None, values=None):
    fields = fields or [("name", "string"), ("age", "integer")]
    fl = [{"name": n, "type": t, "field_uuid": U4()} for n, t in fields]
    return {**HDR, "Format_Version": version, "Records_Type": list(types), "Fields": fl,
            "Values": values if values is not None else [[U4(), "a", 1]]}


def d105db():
    fl = [{"name": "Record_Type_Parent", "type": "string", "field_uuid": U4()},
          {"name": "dept", "type": "string", "Record_Type_Parent": "D", "field_uuid": U4()},
          {"name": "emp", "type": "string", "Record_Type_Parent": "E", "field_uuid": U4()}]
    return {**HDR, "Format_Version": "105db", "Records_Type": ["D", "E"], "Fields": fl,
            "Values": [["D", U4(), "eng", None], ["E", U4(), None, "al"]]}


def errs(doc):
    return V.validate_bejson(doc, is_file=False).errors


class TestValidatorParity(unittest.TestCase):

    def test_baseline_valid(self):
        for d in (d105(), d105("105a"), d105db()):
            self.assertEqual(errs(d), [], d["Format_Version"])

    def test_row_too_short_long_and_no_uuid_slot(self):
        for bad in ([U4(), "a"], [U4(), "a", 1, 9], ["a", 1]):
            d = d105(values=[bad])
            self.assertTrue(any("E_RECORD_LENGTH_MISMATCH" in e for e in errs(d)), bad)

    def test_value_type_mismatch(self):
        d = d105(values=[[U4(), "a", "not-int"]])
        self.assertTrue(any("E_TYPE_MISMATCH" in e for e in errs(d)))
        d = d105(values=[[U4(), "a", True]])  # bool is not an integer
        self.assertTrue(any("E_TYPE_MISMATCH" in e for e in errs(d)))
        d = d105(fields=[("x", "number")], values=[[U4(), True]])
        self.assertTrue(any("bool" in e for e in errs(d)))

    def test_null_always_allowed(self):
        self.assertEqual(errs(d105(values=[[U4(), None, None]])), [])

    def test_all_six_types_checked(self):
        f = [("s", "string"), ("i", "integer"), ("n", "number"), ("b", "boolean"), ("a", "array"), ("o", "object")]
        good = [U4(), "x", 1, 1.5, True, [1], {"k": 1}]
        self.assertEqual(errs(d105(fields=f, values=[good])), [])
        for col in range(1, 7):
            bad = list(good)
            bad[col] = object() if False else ({"z": 1} if col in (1, 2, 3, 4, 5) else [1])
            if col == 5: bad[col] = "str"
            self.assertTrue(any("E_TYPE_MISMATCH" in e for e in errs(d105(fields=f, values=[bad]))), col)

    def test_records_type_counts(self):
        self.assertTrue(errs(d105(types=("A", "B"))))
        self.assertTrue(errs(d105("105a", types=("A", "B"))))
        self.assertTrue(errs(d105(types=())))
        d = d105db(); d["Records_Type"] = ["D"]
        self.assertTrue(errs(d))

    def test_105a_primitives_only(self):
        d = d105("105a", fields=[("tags", "array")], values=[[U4(), [1]]])
        self.assertTrue(any("forbids complex type" in e for e in errs(d)))
        d = d105("105a", fields=[("o", "object")], values=[[U4(), {}]])
        self.assertTrue(errs(d))
        # 105 (non-a) still allows complex types
        self.assertEqual(errs(d105(fields=[("tags", "array")], values=[[U4(), [1]]])), [])

    def test_105db_rules(self):
        d = d105db(); d["Fields"][1].pop("Record_Type_Parent")
        self.assertTrue(errs(d), "field missing owner")
        d = d105db(); d["Fields"][0]["name"] = "oops"
        self.assertTrue(errs(d), "first field must be Record_Type_Parent")
        d = d105db(); d["Values"][0][0] = "Nope"
        self.assertTrue(errs(d), "discriminator not in Records_Type")
        d = d105db(); d["Values"][0] = [d["Values"][0][1], "D", "eng", None]  # uuid in col 0
        self.assertTrue(errs(d), "record_uuid at col 0")
        d = d105db(); d["Values"][0] = ["D", U4(), "eng"]  # short
        self.assertTrue(any("E_RECORD_LENGTH_MISMATCH" in e for e in errs(d)))
        d = d105db(); d["Values"][1][3] = 5  # wrong type at last col
        self.assertTrue(any("E_TYPE_MISMATCH" in e for e in errs(d)))

    def test_uuid_format_is_advisory_warning_not_error(self):
        d = d105(values=[["not-a-uuid", "a", 1]]); d["Fields"][0]["field_uuid"] = "abc"
        r = V.validate_bejson(d, is_file=False)
        self.assertTrue(r.valid)
        self.assertEqual(len(r.warnings), 2)

    def test_error_flood_is_capped(self):
        d = d105(values=[[U4(), "a", "bad"] for _ in range(500)])
        n = len(errs(d))
        self.assertLessEqual(n, V._MAX_SHAPE_ERRORS + 1)

    def test_104_messages_unchanged(self):
        d = {**HDR, "Format_Version": "104", "Records_Type": ["T"],
             "Fields": [{"name": "a", "type": "integer"}], "Values": [["x"]]}
        e = errs(d)
        self.assertEqual(len(e), 1)
        self.assertIn("Type mismatch at row 0, col 0 (a): expected integer", e[0])


class TestCoreWriters(unittest.TestCase):

    def test_add_record_105_checks_length_and_type(self):
        d = d105()
        with self.assertRaises(C.BEJSONCoreError) as cm:
            C.bejson_core_add_record_105(d, ["only-one"])
        self.assertEqual(cm.exception.code, 9)
        with self.assertRaises(C.BEJSONCoreError) as cm:
            C.bejson_core_add_record_105(d, ["a", "nope"])
        self.assertEqual(cm.exception.code, 8)
        self.assertEqual(len(d["Values"]), 1, "nothing written on failure")
        u = C.bejson_core_add_record_105(d, ["b", None])
        self.assertTrue(u)
        self.assertEqual(errs(d), [])

    def test_add_record_105_105db_discriminator(self):
        d = d105db()
        with self.assertRaises(C.BEJSONCoreError):
            C.bejson_core_add_record_105(d, ["Nope", "x", None])
        C.bejson_core_add_record_105(d, ["D", "ops", None])
        self.assertEqual(errs(d), [])

    def test_write_cell_type_checked(self):
        d = d105()
        ru, fu = d["Values"][0][0], d["Fields"][1]["field_uuid"]
        with self.assertRaises(C.BEJSONCoreError) as cm:
            C.bejson_core_write_cell(d, ru, fu, "text")
        self.assertEqual(cm.exception.code, 8)
        self.assertEqual(d["Values"][0][2], 1)
        C.bejson_core_write_cell(d, ru, fu, 7)
        self.assertEqual(d["Values"][0][2], 7)

    def test_add_field_rejects_bad_type_on_105(self):
        d = d105()
        with self.assertRaises(C.BEJSONCoreError):
            C.bejson_core_add_field(d, "ts", "timestamp")
        self.assertEqual(len(d["Fields"]), 2)

    def test_104_adder_refuses_105_doc(self):
        d = d105()
        with self.assertRaises(C.BEJSONCoreError) as cm:
            C.bejson_core_add_record(d, ["a", 1])
        self.assertEqual(cm.exception.code, 81)
        self.assertEqual(len(d["Values"]), 1)

    def test_verify_105_integrity_now_catches_shape_and_types(self):
        d = d105(values=[[U4(), "a"]])
        self.assertFalse(C.bejson_core_verify_105_integrity(d)["ok"])
        d = d105(values=[[U4(), "a", "x"]])
        self.assertFalse(C.bejson_core_verify_105_integrity(d)["ok"])
        self.assertTrue(C.bejson_core_verify_105_integrity(d105())["ok"])


class TestUpgradeSource(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="par_up_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _src(self, values, rt=("T",), version="104"):
        return {**HDR, "Format_Version": version, "Records_Type": list(rt),
                "Fields": [{"name": "a", "type": "string"}, {"name": "b", "type": "integer"}], "Values": values}

    def test_short_row_source_rejected_and_untouched(self):
        d = self._src([["x"]])
        p = os.path.join(self.tmp, "s.bejson")
        json.dump(d, open(p, "w"))
        before = open(p).read()
        with self.assertRaises(U.BEJSONUpgradeError) as cm:
            U.bejson_core_upgrade_to_105(d, p)
        self.assertEqual(cm.exception.code, 83)
        self.assertEqual(open(p).read(), before)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "Backups")))

    def test_bad_type_and_records_type_source_rejected(self):
        p = os.path.join(self.tmp, "s.bejson")
        for d in (self._src([["x", "y"]]), self._src([["x", 1]], rt=("A", "B"))):
            with self.assertRaises(U.BEJSONUpgradeError):
                U.bejson_core_upgrade_to_105(d, p)

    def test_dry_run_reports_source_errors(self):
        r = U.bejson_core_upgrade_dry_run(self._src([["x"]]), "s.bejson")
        self.assertFalse(r["validation_pass"])
        self.assertTrue(r["errors"])
        r = U.bejson_core_upgrade_dry_run(self._src([["x", 1]]), "s.bejson")
        self.assertTrue(r["validation_pass"])

    def test_valid_source_still_upgrades_and_validates(self):
        d = self._src([["x", 1], ["y", None]])
        p = os.path.join(self.tmp, "s.bejson")
        json.dump(d, open(p, "w"))
        up = U.bejson_core_upgrade_to_105(d, p)
        self.assertEqual(up["Format_Version"], "105")
        self.assertEqual(errs(up), [])
        self.assertEqual(V.validate_bejson(p, is_file=True).errors, [])


class TestMFDBOn105(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="par_mfdb_")
        S = lambda n: {"name": n, "type": "string"}
        self.m = M.mfdb_core_create_database(os.path.join(self.tmp, "db"), "Shop", [
            {"name": "Customer", "fields": [S("cust_name")], "format_version": "105"},
            {"name": "Order", "format_version": "105", "fields": [
                S("code"), {"name": "total", "type": "number"}]},
            {"name": "Legacy", "fields": [S("x"), {"name": "n", "type": "integer"}]},
        ], mfdb_version="1.40")
        M.mfdb_core_add_entity_record_105(self.m, "Customer", ["ann"])
        M.mfdb_core_add_entity_record_105(self.m, "Order", ["O1", 9.5])
        M.mfdb_core_add_entity_record(self.m, "Legacy", ["a", 1])

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _entity_bytes(self, name):
        return open(M._get_entity_path(self.m, name)).read()

    def test_105_add_rejects_wrong_length_and_type(self):
        with self.assertRaises(Exception):
            M.mfdb_core_add_entity_record_105(self.m, "Order", ["only"])
        with self.assertRaises(Exception):
            M.mfdb_core_add_entity_record_105(self.m, "Order", ["O2", "str"])
        self.assertEqual(len(M.mfdb_core_load_entity(self.m, "Order")), 1)

    def test_104_writer_blocked_on_105_entity(self):
        before = self._entity_bytes("Customer")
        with self.assertRaises(Exception):
            M.mfdb_core_add_entity_record(self.m, "Customer", ["bob"])
        self.assertEqual(self._entity_bytes("Customer"), before)
        # 104 entity unaffected
        M.mfdb_core_add_entity_record(self.m, "Legacy", ["b", 2])
        self.assertEqual(len(M.mfdb_core_load_entity(self.m, "Legacy")), 2)

    def test_deep_verify_clean_on_healthy_105(self):
        bad = [f for f in M.mfdb_core_deep_verify(self.m) if f.get("error") or f.get("warning") == "TYPE_MISMATCH"]
        self.assertEqual(bad, [])

    def test_deep_verify_still_flags_real_105_violation(self):
        p = M._get_entity_path(self.m, "Order")
        doc = json.load(open(p)); doc["Values"][0].pop()
        json.dump(doc, open(p, "w"))
        f = [x for x in M.mfdb_core_deep_verify(self.m) if x.get("error") == "POSITIONAL_VIOLATION"]
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]["expected"], 3)

    def test_self_heal_never_changes_healthy_105(self):
        snap = {n: self._entity_bytes(n) for n in ("Customer", "Order", "Legacy")}
        rep = M.mfdb_core_self_heal(self.m)
        self.assertEqual(rep["remaining_errors"], [])
        for n, b in snap.items():
            self.assertEqual(self._entity_bytes(n), b, n)

    def test_self_heal_does_not_guess_on_broken_105_row(self):
        p = M._get_entity_path(self.m, "Order")
        doc = json.load(open(p)); doc["Values"][0].pop()
        json.dump(doc, open(p, "w"))
        raw = open(p).read()
        rep = M.mfdb_core_self_heal(self.m)
        self.assertTrue(any("not auto-repaired" in e for e in rep["remaining_errors"]))
        self.assertEqual(open(p).read(), raw)

    def test_self_heal_still_repairs_104(self):
        p = M._get_entity_path(self.m, "Legacy")
        doc = json.load(open(p)); doc["Values"][0].pop()
        json.dump(doc, open(p, "w"))
        rep = M.mfdb_core_self_heal(self.m)
        self.assertTrue(any("Repaired" in a for a in rep["actions"]))
        self.assertEqual(len(json.load(open(p))["Values"][0]), 2)

    def test_discover_classifies_105_entities(self):
        self.assertEqual(M.mfdb_core_discover(M._get_entity_path(self.m, "Order")), "entity")
        self.assertEqual(M.mfdb_core_discover(M._get_entity_path(self.m, "Legacy")), "entity")
        self.assertEqual(M.mfdb_core_discover(self.m), "manifest")

    def test_database_validates_and_catches_bad_105_row(self):
        self.assertTrue(MV.validate_mfdb_database(self.m).valid)
        p = M._get_entity_path(self.m, "Order")
        doc = json.load(open(p)); doc["Values"][0][2] = "text"
        json.dump(doc, open(p, "w"))
        self.assertFalse(MV.validate_mfdb_database(self.m).valid)


if __name__ == "__main__":
    unittest.main(verbosity=1)
