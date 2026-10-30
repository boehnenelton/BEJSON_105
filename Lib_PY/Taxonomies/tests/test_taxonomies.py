"""
File Name : test_taxonomies.py
Rel. Path : Lib_PY/Taxonomies/tests/test_taxonomies.py
Purpose   : Tests for lib_bejson_Taxonomies (registry, ledger, schema builder, audit) against unmodified Core.
VERSION   : 2.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : ce347f09-9b43-4e88-af5f-ab68c75bb417
Run       : python3 Lib_PY/Taxonomies/tests/test_taxonomies.py
"""
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
import lib_bejson_Taxonomies_core as reg  # noqa: E402
import lib_bejson_Taxonomies_core as trk  # noqa: E402
from lib_bejson_Core_bejson_core import bejson_core_atomic_write, bejson_core_load_file  # noqa: E402


class TaxonomyTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tax_test_")
        self.m = sb.bejson_taxonomies_build_registry_database(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def audit(self):
        return trk.bejson_taxonomies_audit_database(self.m)

    def edit_entity(self, entity, fn):
        p = st.entity_path(self.m, entity)
        doc = bejson_core_load_file(p)
        fn(doc)
        self.assertTrue(bejson_core_atomic_write(p, doc))


class TestBuildAndAudit(TaxonomyTestBase):
    def test_fresh_registry_passes(self):
        r = self.audit()
        self.assertTrue(r["passed"], r["problems"])
        self.assertEqual((r["entities"], r["taxonomies"], r["fields_total"], r["ledger_rows"]), (9, 1, 59, 59))

    def test_refuses_second_build_in_same_dir(self):
        with self.assertRaises(st.TaxonomyError):
            sb.bejson_taxonomies_build_registry_database(self.tmp)

    def test_audit_counts_stamped(self):
        t = reg.bejson_taxonomies_get_taxonomy(self.m, "lattice")
        self.assertEqual(t["field_count"], 59)

    def test_audit_catches_wrong_type(self):
        self.edit_entity(st.E_ZSPACE, lambda d: d["Fields"][2].__setitem__("type", "string"))
        self.assertFalse(self.audit()["passed"])

    def test_audit_reports_damaged_registry_instead_of_raising(self):
        self.edit_entity(st.E_ZSPACE, lambda d: d["Fields"][0].__setitem__("name", "renamed_without_ledger"))
        r = self.audit()
        self.assertFalse(r["passed"])
        self.assertTrue(r["problems"])

    def test_audit_catches_unledgered_field(self):
        self.edit_entity(st.E_FIELD, lambda d: d["Values"].pop())
        self.assertTrue(any("not in field ledger" in p for p in self.audit()["problems"]))

    def test_audit_catches_non_v4_record_uuid(self):
        self.edit_entity(st.E_ZSPACE, lambda d: d["Values"][0].__setitem__(0, "019280a1-7c4e-7001-9000-000000000001"))
        self.assertTrue(any("not UUIDv4" in p for p in self.audit()["problems"]))


class TestRegistry(TaxonomyTestBase):
    def test_bad_namespace(self):
        for bad in ("Lv", "1x", "a_b", "", "x" * 30):
            with self.assertRaises(st.TaxonomyError, msg=bad):
                reg.bejson_taxonomies_create_taxonomy(self.m, bad)

    def test_duplicate_and_ambiguous_prefix(self):
        reg.bejson_taxonomies_create_taxonomy(self.m, "lv")
        with self.assertRaises(st.TaxonomyError) as c:
            reg.bejson_taxonomies_create_taxonomy(self.m, "lv")
        self.assertEqual(c.exception.code, "E_NAMESPACE_EXISTS")

    def test_required_suffixes_enforced(self):
        rules = dict(st.DEFAULT_SUFFIX_RULES)
        del rules["_slot"]
        with self.assertRaises(st.TaxonomyError) as c:
            reg.bejson_taxonomies_create_taxonomy(self.m, "lv", rules)
        self.assertEqual(c.exception.code, "E_SUFFIX_REQUIRED")
        rules = dict(st.DEFAULT_SUFFIX_RULES, _slot="integer")
        with self.assertRaises(st.TaxonomyError):
            reg.bejson_taxonomies_create_taxonomy(self.m, "lv", rules)
        self.assertEqual(len(reg.bejson_taxonomies_list_taxonomies(self.m)), 1)  # nothing half-created

    def test_variant_derivation_and_diff(self):
        v = reg.bejson_taxonomies_derive_variant(self.m, "lattice", "lv", {"_ref": "string"}, ["_kind"])
        t = reg.bejson_taxonomies_get_taxonomy(self.m, v)
        self.assertEqual(t["prefix_key"], "lv_")
        self.assertIn("_ref", t["suffix_rules"])
        self.assertNotIn("_kind", t["suffix_rules"])
        d = reg.bejson_taxonomies_diff_taxonomies(self.m, "lattice", "lv")
        self.assertEqual((d["suffix_only_in_a"], d["suffix_only_in_b"], d["identical"], d["a_is_parent_of_b"]),
                         (["_kind"], ["_ref"], False, True))
        self.assertTrue(self.audit()["passed"])

    def test_variant_cannot_drop_required_suffix(self):
        with self.assertRaises(st.TaxonomyError):
            reg.bejson_taxonomies_derive_variant(self.m, "lattice", "lv", suffix_removals=["_slot"])

    def test_check_field_name(self):
        t = reg.bejson_taxonomies_get_taxonomy(self.m, "lattice")
        ok = reg.bejson_taxonomies_check_field_name
        self.assertEqual(ok(t, "lattice_node_label_name", "string"), [])
        self.assertEqual(ok(t, "lattice_node_price_amount", "number"), [])
        self.assertEqual(ok(t, "lattice_node_score_ratio", "number"), [])
        self.assertEqual(ok(t, "lattice_node_birth_date", "string"), [])
        self.assertEqual(ok(t, "lattice_node_run_duration", "number"), [])
        self.assertEqual(ok(t, "lattice_node_content_hash", "string"), [])
        self.assertEqual(ok(t, "lattice_node_payload_json", "string"), [])
        self.assertEqual(ok(t, "lattice_node_tags_list", "array"), [])
        self.assertTrue(ok(t, "node_label_name", "string"))                 # prefix
        self.assertTrue(ok(t, "lattice_node_label_flag", "string"))         # type
        self.assertTrue(ok(t, "lattice_node_label_tag", "string"))          # unregistered suffix
        self.assertTrue(ok(t, "lattice_name", "string"))                    # no descriptor
        self.assertTrue(ok(t, "lattice_Node_name", "string"))               # case

    def test_delete_taxonomy_guarded_by_use(self):
        with self.assertRaises(st.TaxonomyError) as c:
            reg.bejson_taxonomies_delete_taxonomy(self.m, "lattice")
        self.assertEqual(c.exception.code, "E_TAXONOMY_IN_USE")
        v = reg.bejson_taxonomies_derive_variant(self.m, "lattice", "lv")
        reg.bejson_taxonomies_delete_taxonomy(self.m, "lv")
        self.assertEqual([t["namespace_key"] for t in reg.bejson_taxonomies_list_taxonomies(self.m)], ["lattice"])
        self.assertTrue(self.audit()["passed"])

    def test_deleting_parent_detaches_variant(self):
        reg.bejson_taxonomies_derive_variant(self.m, "lattice", "lv")
        p = reg.bejson_taxonomies_create_taxonomy(self.m, "tmpa")
        c = reg.bejson_taxonomies_derive_variant(self.m, "tmpa", "tmpb")
        reg.bejson_taxonomies_delete_taxonomy(self.m, "tmpa")
        self.assertIsNone(reg.bejson_taxonomies_get_taxonomy(self.m, c)["parent_taxonomy_uuid"])
        self.assertTrue(self.audit()["passed"], self.audit()["problems"])


class TestSchemaBuilderAndLedger(TaxonomyTestBase):
    def setUp(self):
        super().setUp()
        reg.bejson_taxonomies_derive_variant(self.m, "lattice", "lv", {"_ref": "string"})
        self.tx = reg.bejson_taxonomies_get_taxonomy(self.m, "lv")
        fd = sb.bejson_taxonomies_build_field_definition
        self.fields = [fd(self.tx, "lv_node_label_key", "string"), fd(self.tx, "lv_node_owner_ref", "string")]

    def test_make_field_name(self):
        self.assertEqual(sb.bejson_taxonomies_make_field_name(self.tx, "node", "owner", "_ref"), "lv_node_owner_ref")
        with self.assertRaises(st.TaxonomyError):
            sb.bejson_taxonomies_make_field_name(self.tx, "node", "owner", "_nope")

    def test_noncompliant_entity_creates_nothing(self):
        bad = self.fields + [{"name": "node_extra_name", "type": "string"}]
        with self.assertRaises(st.TaxonomyComplianceError):
            sb.bejson_taxonomies_create_domain_entity(self.m, "lv", "LvNode", bad)
        self.assertNotIn("LvNode", st.manifest_entity_names(self.m))
        with self.assertRaises(st.TaxonomyComplianceError):
            sb.bejson_taxonomies_create_domain_entity(self.m, "lv", "NodeLv", self.fields)

    def test_domain_entity_is_ledgered_and_audits(self):
        sb.bejson_taxonomies_create_domain_entity(self.m, "lv", "LvNode", self.fields, primary_key="lv_node_label_key")
        r = self.audit()
        self.assertTrue(r["passed"], r["problems"])
        self.assertEqual(r["fields_total"], 61)

    def test_resolve_both_ways_and_rename_followed(self):
        sb.bejson_taxonomies_create_domain_entity(self.m, "lv", "LvNode", self.fields)
        fu = trk.bejson_taxonomies_resolve_field_uuid(self.m, "LvNode", "lv_node_owner_ref")
        self.assertTrue(st.UUID4_RE.match(fu))
        self.assertEqual(trk.bejson_taxonomies_resolve_field_name(self.m, "LvNode", fu), "lv_node_owner_ref")
        self.edit_entity("LvNode", lambda d: d["Fields"][1].__setitem__("name", "lv_node_parent_ref"))
        self.assertFalse(self.audit()["passed"])  # ledger now stale
        res = trk.bejson_taxonomies_sync_ledger(self.m, "LvNode")
        self.assertEqual(res["renamed"], ["lv_node_owner_ref -> lv_node_parent_ref"])
        self.assertEqual(trk.bejson_taxonomies_resolve_field_uuid(self.m, "LvNode", "lv_node_parent_ref"), fu)
        self.assertTrue(self.audit()["passed"], self.audit()["problems"])

    def test_noncompliant_rename_refused_by_ledger(self):
        sb.bejson_taxonomies_create_domain_entity(self.m, "lv", "LvNode", self.fields)
        fu = trk.bejson_taxonomies_resolve_field_uuid(self.m, "LvNode", "lv_node_owner_ref")
        self.edit_entity("LvNode", lambda d: d["Fields"][1].__setitem__("name", "owner_ref"))
        with self.assertRaises(st.TaxonomyComplianceError):
            trk.bejson_taxonomies_sync_ledger(self.m, "LvNode")

    def test_removed_field_is_retired_not_deleted(self):
        sb.bejson_taxonomies_create_domain_entity(self.m, "lv", "LvNode", self.fields)
        def drop(d):
            del d["Fields"][1]
            for row in d["Values"]:
                del row[2]
        self.edit_entity("LvNode", drop)
        res = trk.bejson_taxonomies_sync_ledger(self.m, "LvNode")
        self.assertEqual(res["retired"], ["lv_node_owner_ref"])
        retired = [r for r in st.read_rows(self.m, st.E_FIELD) if r[st.FE_LIFECYCLE] == st.LIFECYCLE_RETIRED]
        self.assertEqual(len(retired), 1)
        self.assertIsNotNone(retired[0][st.FE_RETIRED])
        self.assertTrue(self.audit()["passed"], self.audit()["problems"])

    def test_sync_reports_unledgered(self):
        sb.bejson_taxonomies_create_domain_entity(self.m, "lv", "LvNode", self.fields)
        def add(d):
            d["Fields"].append({"name": "lv_node_extra_key", "type": "string", "field_uuid": "55555555-5555-4555-8555-555555555555"})
            for row in d["Values"]:
                row.append(None)
        self.edit_entity("LvNode", add)
        self.assertEqual(trk.bejson_taxonomies_sync_ledger(self.m, "LvNode")["unledgered"], ["lv_node_extra_key"])
        self.assertEqual(trk.bejson_taxonomies_track_fields(self.m, "LvNode", "lv"), 1)
        self.assertTrue(self.audit()["passed"], self.audit()["problems"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
