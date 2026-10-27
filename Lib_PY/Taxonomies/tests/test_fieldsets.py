"""
File Name : test_fieldsets.py
Rel. Path : Lib_PY/Taxonomies/tests/test_fieldsets.py
Purpose   : Tests for field sets in lib_bejson_Taxonomies: define, version, retire, BEJSON 104a export/import,
            the validator (members, definition files) and the registry audit rules for sets. Grafting onto
            entities is covered in Tax_Scaffolds/tests/test_graft.py. Sets here are neutral fixtures.
VERSION   : 2.0.1
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : 26551ca2-c1a9-4a4f-93dc-31766495e125
Run       : python3 Lib_PY/Taxonomies/tests/test_fieldsets.py
"""
import copy
import json
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(_HERE, "..")))

import lib_bejson_Taxonomies_core as st  # noqa: E402
import lib_bejson_Taxonomies_core as sb  # noqa: E402
import lib_bejson_Taxonomies_core as core  # noqa: E402
import lib_bejson_Taxonomies_validator as val  # noqa: E402
import lib_bejson_Taxonomies_registry as fsr  # noqa: E402
from lib_bejson_Core_bejson_core import bejson_core_atomic_write, bejson_core_load_file  # noqa: E402
from lib_bejson_Core_mfdb_core import mfdb_core_update_entity_record_105 as upd, mfdb_core_delete_entity_record_105 as delete  # noqa: E402

MEMBERS = [
    {"descriptor": "title", "suffix": "_name", "field_type": "string"},
    {"descriptor": "width", "suffix": "_metric", "field_type": "integer"},
    {"descriptor": "created", "suffix": "_timestamp", "field_type": "string"},
]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="fieldset_test_")
        self.m = sb.bejson_taxonomies_build_registry_database(os.path.join(self.tmp, "a"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def problems(self, m=None):
        return "\n".join(val.bejson_taxonomies_validator_audit_database(m or self.m)["problems"])

    def ok(self, m=None):
        r = val.bejson_taxonomies_validator_audit_database(m or self.m)
        self.assertTrue(r["passed"], r["problems"])
        return r


class TestRegistry(Base):
    def test_define_list_get_and_audit(self):
        uid = fsr.bejson_taxonomies_define_field_set(self.m, "media_asset", MEMBERS, "Media asset")
        s = fsr.bejson_taxonomies_get_field_set(self.m, "media_asset")
        self.assertEqual((s["set_uuid"], s["version"], s["state"], [m["descriptor"] for m in s["members"]]),
                         (uid, 1, "active", ["title", "width", "created"]))
        self.assertEqual(fsr.bejson_taxonomies_get_field_set(self.m, uid)["set_key"], "media_asset")
        self.assertEqual(len(fsr.bejson_taxonomies_list_field_sets(self.m)), 1)
        r = self.ok()
        self.assertEqual(r["entities"], 9)
        with self.assertRaises(st.TaxonomyError) as cx:
            fsr.bejson_taxonomies_define_field_set(self.m, "media_asset", MEMBERS)
        self.assertEqual(cx.exception.code, "E_FIELDSET_EXISTS")
        with self.assertRaises(st.TaxonomyError) as cx:
            fsr.bejson_taxonomies_get_field_set(self.m, "nope")
        self.assertEqual(cx.exception.code, "E_FIELDSET_NOT_FOUND")

    def test_bad_definitions_rejected_and_nothing_written(self):
        bad_cases = [
            ("Bad Key", MEMBERS), ("ok_key", []), ("ok_key", [{"descriptor": "a", "suffix": "name", "field_type": "string"}]),
            ("ok_key", [{"descriptor": "a", "suffix": "_name", "field_type": "text"}]),
            ("ok_key", [{"descriptor": "A b", "suffix": "_name", "field_type": "string"}]),
            ("ok_key", MEMBERS + [MEMBERS[0]]), ("ok_key", [{"descriptor": "a", "suffix": "_name"}]),
        ]
        for key, members in bad_cases:
            with self.assertRaises(st.TaxonomyComplianceError, msg=(key, members)):
                fsr.bejson_taxonomies_define_field_set(self.m, key, members)
        self.assertEqual(st.read_rows(self.m, st.E_FIELDSET), [])
        self.assertEqual(st.read_rows(self.m, st.E_SETMEMBER), [])

    def test_versions_are_additive_and_immutable(self):
        fsr.bejson_taxonomies_define_field_set(self.m, "media_asset", MEMBERS)
        v2 = fsr.bejson_taxonomies_new_version(self.m, "media_asset", [{"descriptor": "duration", "suffix": "_metric", "field_type": "integer"}])
        latest = fsr.bejson_taxonomies_get_field_set(self.m, "media_asset")
        self.assertEqual((latest["set_uuid"], latest["version"], [m["descriptor"] for m in latest["members"]]),
                         (v2, 2, ["title", "width", "created", "duration"]))
        self.assertEqual(len(fsr.bejson_taxonomies_get_field_set(self.m, "media_asset", 1)["members"]), 3)
        with self.assertRaises(st.TaxonomyError) as cx:
            fsr.bejson_taxonomies_new_version(self.m, "media_asset", [MEMBERS[0]])
        self.assertEqual(cx.exception.code, "E_FIELDSET_MEMBER_EXISTS")
        with self.assertRaises(st.TaxonomyError):
            fsr.bejson_taxonomies_get_field_set(self.m, "media_asset", 9)
        self.ok()

    def test_retire_marks_every_version(self):
        fsr.bejson_taxonomies_define_field_set(self.m, "media_asset", MEMBERS)
        fsr.bejson_taxonomies_new_version(self.m, "media_asset", [{"descriptor": "duration", "suffix": "_metric", "field_type": "integer"}])
        self.assertEqual(fsr.bejson_taxonomies_retire_field_set(self.m, "media_asset"), 2)
        self.assertEqual({s["state"] for s in fsr.bejson_taxonomies_list_field_sets(self.m)}, {"retired"})
        with self.assertRaises(st.TaxonomyError) as cx:
            fsr.bejson_taxonomies_new_version(self.m, "media_asset", [{"descriptor": "x", "suffix": "_name", "field_type": "string"}])
        self.assertEqual(cx.exception.code, "E_FIELDSET_RETIRED")
        self.ok()


class TestExportImport(Base):
    def setUp(self):
        super().setUp()
        self.b = sb.bejson_taxonomies_build_registry_database(os.path.join(self.tmp, "b"))
        fsr.bejson_taxonomies_define_field_set(self.m, "media_asset", MEMBERS, "Media asset")
        self.path = os.path.join(self.tmp, "media_asset.v1.bejson")

    def test_roundtrip_between_registries_and_idempotent_reimport(self):
        fsr.bejson_taxonomies_export_field_set(self.m, "media_asset", self.path)
        doc = bejson_core_load_file(self.path)
        self.assertEqual((doc["Format_Version"], doc["Records_Type"], len(doc["Values"])), ("104a", ["LatticeFieldSetDefinition"], 3))
        uid = fsr.bejson_taxonomies_import_field_set(self.b, self.path)
        a = fsr.bejson_taxonomies_get_field_set(self.m, "media_asset")
        b = fsr.bejson_taxonomies_get_field_set(self.b, uid)
        self.assertEqual((a["content_hash"], a["display_name"], a["version"]), (b["content_hash"], b["display_name"], b["version"]))
        self.assertEqual(fsr.bejson_taxonomies_import_field_set(self.b, self.path), uid)  # idempotent
        self.assertEqual(len(fsr.bejson_taxonomies_list_field_sets(self.b)), 1)
        self.ok(self.b)

    def test_conflict_when_same_version_differs(self):
        fsr.bejson_taxonomies_export_field_set(self.m, "media_asset", self.path)
        other = sb.bejson_taxonomies_build_registry_database(os.path.join(self.tmp, "c"))
        fsr.bejson_taxonomies_define_field_set(other, "media_asset", MEMBERS[:2])
        with self.assertRaises(st.TaxonomyError) as cx:
            fsr.bejson_taxonomies_import_field_set(other, self.path)
        self.assertEqual(cx.exception.code, "E_FIELDSET_CONFLICT")

    def test_version_ordering_on_import(self):
        fsr.bejson_taxonomies_new_version(self.m, "media_asset", [{"descriptor": "duration", "suffix": "_metric", "field_type": "integer"}])
        v2 = os.path.join(self.tmp, "v2.bejson")
        fsr.bejson_taxonomies_export_field_set(self.m, "media_asset", v2, version=2)
        with self.assertRaises(st.TaxonomyError) as cx:
            fsr.bejson_taxonomies_import_field_set(self.b, v2)  # v1 not present on B
        self.assertEqual(cx.exception.code, "E_FIELDSET_VERSION")
        fsr.bejson_taxonomies_export_field_set(self.m, "media_asset", self.path, version=1)
        fsr.bejson_taxonomies_import_field_set(self.b, self.path)
        fsr.bejson_taxonomies_import_field_set(self.b, v2)
        self.assertEqual(fsr.bejson_taxonomies_get_field_set(self.b, "media_asset")["version"], 2)
        self.ok(self.b)

    def test_export_refuses_overwrite_unless_asked(self):
        fsr.bejson_taxonomies_export_field_set(self.m, "media_asset", self.path)
        with self.assertRaises(st.TaxonomyError) as cx:
            fsr.bejson_taxonomies_export_field_set(self.m, "media_asset", self.path)
        self.assertEqual(cx.exception.code, "E_EXISTS")
        fsr.bejson_taxonomies_export_field_set(self.m, "media_asset", self.path, overwrite=True)

    def test_import_rejects_damaged_files(self):
        fsr.bejson_taxonomies_export_field_set(self.m, "media_asset", self.path)
        good = bejson_core_load_file(self.path)

        def damaged(fn):
            doc = copy.deepcopy(good)
            fn(doc)
            p = os.path.join(self.tmp, "damaged.bejson")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(doc, fh)
            return p

        cases = {
            "format": lambda d: d.__setitem__("Format_Version", "104db"),
            "records type": lambda d: d.__setitem__("Records_Type", ["Other"]),
            "fields": lambda d: d["Fields"].pop(),
            "order": lambda d: d["Values"][1].__setitem__(6, 7),
            "suffix": lambda d: d["Values"][0].__setitem__(4, "name"),
            "type": lambda d: d["Values"][0].__setitem__(5, "text"),
            "mixed sets": lambda d: d["Values"][2].__setitem__(0, "other_set"),
            "duplicate descriptor": lambda d: d["Values"][1].__setitem__(3, "title"),
            "no rows": lambda d: d.__setitem__("Values", []),
        }
        for label, fn in cases.items():
            with self.assertRaises(st.TaxonomyError, msg=label):
                fsr.bejson_taxonomies_import_field_set(self.b, damaged(fn))
        with self.assertRaises(st.TaxonomyError) as cx:
            fsr.bejson_taxonomies_import_field_set(self.b, os.path.join(self.tmp, "missing.bejson"))
        self.assertEqual(cx.exception.code, "E_DEFINITION_NOT_FOUND")
        self.assertEqual(st.read_rows(self.b, st.E_FIELDSET), [])


class TestValidatorAndAudit(Base):
    def test_content_hash_depends_on_content_and_order_only(self):
        h = core.bejson_taxonomies_core_content_hash
        self.assertEqual(h(MEMBERS), h(copy.deepcopy(MEMBERS)))
        self.assertNotEqual(h(MEMBERS), h(MEMBERS[::-1]))
        self.assertNotEqual(h(MEMBERS), h(MEMBERS[:2]))

    def test_check_member_against_taxonomy(self):
        tx = {"namespace_key": "t", "suffix_rules": {"_name": {"field_type": "string"}}}
        self.assertEqual(val.bejson_taxonomies_validator_check_member_against_taxonomy(tx, MEMBERS[0]), [])
        self.assertIn("not registered", val.bejson_taxonomies_validator_check_member_against_taxonomy(tx, MEMBERS[1])[0])
        tx["suffix_rules"]["_metric"] = {"field_type": "string"}
        self.assertIn("requires 'string'", val.bejson_taxonomies_validator_check_member_against_taxonomy(tx, MEMBERS[1])[0])

    def test_audit_catches_non_additive_version_missing_members_and_bad_state(self):
        fsr.bejson_taxonomies_define_field_set(self.m, "media_asset", MEMBERS)
        fsr.bejson_taxonomies_new_version(self.m, "media_asset", [{"descriptor": "duration", "suffix": "_metric", "field_type": "integer"}])
        self.ok()
        v2 = fsr.bejson_taxonomies_get_field_set(self.m, "media_asset", 2)
        drop = next(m for m in v2["members"] if m["descriptor"] == "width")
        delete(self.m, st.E_SETMEMBER, drop["member_uuid"])
        text = self.problems()
        self.assertIn("drops or changes members of v1", text)
        self.assertIn("order_metric must run 1..n", text)
        v1 = fsr.bejson_taxonomies_get_field_set(self.m, "media_asset", 1)
        upd(self.m, st.E_FIELDSET, v1["set_uuid"], st.FS_STATE, "paused")
        self.assertIn("not in ('active', 'retired')", self.problems())

    def test_audit_catches_duplicate_version_and_empty_set(self):
        fsr.bejson_taxonomies_define_field_set(self.m, "media_asset", MEMBERS)
        st.add_row(self.m, st.E_FIELDSET, st.build_row(self.m, st.E_FIELDSET, **{
            st.FS_KEY: "media_asset", st.FS_NAME: "dup", st.FS_VERSION: 1, st.FS_STATE: "active", st.FS_CREATED: st.now_utc()}))
        text = self.problems()
        self.assertIn("registered twice", text)
        self.assertIn("has no members", text)

    def test_audit_reports_registry_without_set_entities(self):
        old = os.path.join(self.tmp, "old")
        m = sb.bejson_taxonomies_build_registry_database(old)
        manifest = bejson_core_load_file(m)
        manifest["Values"] = [r for r in manifest["Values"] if r[0] not in (st.E_FIELDSET, st.E_SETMEMBER, st.E_GRAFT)]
        # an old-schema registry is reported, not crashed on (audit never raises)
        bejson_core_atomic_write(m, manifest)
        self.assertFalse(val.bejson_taxonomies_validator_audit_database(m)["passed"])


class TestHardening(Base):
    def test_trailing_newline_and_overlong_names_are_rejected(self):
        for bad in ("box\n", "a" * 65, "Box", "a b", "../x", ""):
            with self.assertRaises(st.TaxonomyError, msg=repr(bad)):
                fsr.bejson_taxonomies_define_field_set(self.m, bad, MEMBERS)
        for bad in ("title\n", "t" * 49, "Title", "1abc", ""):
            with self.assertRaises(st.TaxonomyError, msg=repr(bad)):
                fsr.bejson_taxonomies_define_field_set(self.m, "ok_set", [{"descriptor": bad, "suffix": "_name", "field_type": "string"}])
        self.assertEqual(fsr.bejson_taxonomies_list_field_sets(self.m), [])

    def test_boundary_lengths_are_accepted(self):
        fsr.bejson_taxonomies_define_field_set(self.m, "a" * 64, [{"descriptor": "d" * 48, "suffix": "_name", "field_type": "string"}])
        self.assertTrue(self.ok())

    def test_namespace_and_other_names_reject_trailing_newline(self):
        for rx in (st.NAMESPACE_RE, st.FIELD_NAME_RE, st.SET_KEY_RE, st.DESCRIPTOR_RE):
            self.assertIsNone(rx.match("abc\n"))
        self.assertIsNone(st.UUID4_RE.match("0b7d3f6e-52a1-4c8e-9d40-7e1a6f2c85b3\n"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
