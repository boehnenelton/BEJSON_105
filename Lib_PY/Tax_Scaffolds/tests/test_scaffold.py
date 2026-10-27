"""
File Name : test_scaffold.py
Rel. Path : Lib_PY/Tax_Scaffolds/tests/test_scaffold.py
Purpose   : Tests for lib_bejson_Tax_Scaffolds (Z-space, deployments, federation, rebuild, prebuilt) against unmodified Core.
VERSION   : 2.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : 679546b9-05bb-4875-86e3-0ebe47e51989
Run       : python3 Lib_PY/Tax_Scaffolds/tests/test_scaffold.py
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
for _fam in ("Tax_Scaffolds", "Taxonomies"):
    sys.path.insert(0, os.path.normpath(os.path.join(_HERE, "..", "..", _fam)))

import lib_bejson_Taxonomies_core as st  # noqa: E402
import lib_bejson_Taxonomies_core as sb  # noqa: E402
import lib_bejson_Taxonomies_core as reg  # noqa: E402
import lib_bejson_Taxonomies_core as trk  # noqa: E402
import lib_bejson_Tax_Scaffolds_scaffold as zsa  # noqa: E402
import lib_bejson_Tax_Scaffolds_scaffold as dep  # noqa: E402
import lib_bejson_Tax_Scaffolds_scaffold as fb  # noqa: E402
import lib_bejson_Tax_Scaffolds_scaffold as rb  # noqa: E402
import lib_bejson_Tax_Scaffolds_scaffold as pb  # noqa: E402
from lib_bejson_Core_bejson_core import bejson_core_atomic_write, bejson_core_get_field_map, bejson_core_load_file  # noqa: E402
from lib_bejson_Core_mfdb_core import mfdb_core_get_entity_doc  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="scaf_test_")
        self.m = sb.bejson_taxonomies_build_registry_database(os.path.join(self.tmp, "reg"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def ok(self, manifest=None):
        r = trk.bejson_taxonomies_audit_database(manifest or self.m)
        self.assertTrue(r["passed"], r["problems"])
        return r

    def variant_entity(self, rows=0):
        reg.bejson_taxonomies_derive_variant(self.m, "lattice", "lv", {"_ref": "string"})
        tx = reg.bejson_taxonomies_get_taxonomy(self.m, "lv")
        fd = sb.bejson_taxonomies_build_field_definition
        sb.bejson_taxonomies_create_domain_entity(
            self.m, "lv", "LvNode", [fd(tx, "lv_node_label_key", "string"), fd(tx, "lv_node_owner_ref", "string")])
        for i in range(rows):
            st.add_row(self.m, "LvNode", [f"n{i}", "x"])


class TestZSpace(Base):
    def test_seeded_reservation(self):
        z = zsa.bejson_tax_scaffolds_list_z_space(self.m)
        self.assertEqual([(r["entity_name"], r["state_kind"], r["current_field_name"]) for r in z],
                         [(st.E_DEPLOYMENT, "reserved", st.DP_SLOT)])

    def test_reserve_two_slots_on_populated_entity(self):
        self.variant_entity(rows=3)
        res = zsa.bejson_tax_scaffolds_reserve_z_space_slot(self.m, "LvNode", "lv", slot_count=2)
        self.assertEqual([r["slot_name"] for r in res], ["lv_zspace_01_reserved_slot", "lv_zspace_02_reserved_slot"])
        doc = mfdb_core_get_entity_doc(self.m, "LvNode")
        fm = bejson_core_get_field_map(doc)
        self.assertEqual([f["name"] for f in doc["Fields"]][-2:], [r["slot_name"] for r in res])
        for row in doc["Values"]:
            self.assertEqual((len(row), row[fm["lv_zspace_01_reserved_slot"]], row[fm["lv_zspace_02_reserved_slot"]]),
                             (len(doc["Fields"]) + 1, None, None))
        self.ok()

    def test_second_reserve_continues_ordinals(self):
        self.variant_entity()
        zsa.bejson_tax_scaffolds_reserve_z_space_slot(self.m, "LvNode", "lv")
        r = zsa.bejson_tax_scaffolds_reserve_z_space_slot(self.m, "LvNode", "lv")
        self.assertEqual(r[0]["ordinal"], 2)
        self.ok()

    def test_failed_reserve_rolls_back_completely(self):
        self.variant_entity(rows=2)
        before = bejson_core_load_file(st.entity_path(self.m, "LvNode"))
        n_ledger = len(st.read_rows(self.m, st.E_FIELD))
        n_z = len(st.read_rows(self.m, st.E_ZSPACE))
        with self.assertRaises(st.TaxonomyComplianceError):   # entity 'LvNode' does not belong to taxonomy 'lattice'
            zsa.bejson_tax_scaffolds_reserve_z_space_slot(self.m, "LvNode", "lattice")
        after = bejson_core_load_file(st.entity_path(self.m, "LvNode"))
        self.assertEqual([f["name"] for f in after["Fields"]], [f["name"] for f in before["Fields"]])
        self.assertEqual(after["Values"], before["Values"])
        self.assertEqual((len(st.read_rows(self.m, st.E_FIELD)), len(st.read_rows(self.m, st.E_ZSPACE))), (n_ledger, n_z))
        self.ok()

    def test_bind_keeps_uuid_position_and_rows(self):
        self.variant_entity(rows=2)
        (slot,) = zsa.bejson_tax_scaffolds_reserve_z_space_slot(
            self.m, "LvNode", "lv", fk_target_entity=st.E_LINK, fk_on_delete="null")
        d0 = mfdb_core_get_entity_doc(self.m, "LvNode")
        pos0 = bejson_core_get_field_map(d0)[slot["slot_name"]]
        rows0 = json.dumps(d0["Values"])
        name = zsa.bejson_tax_scaffolds_bind_z_space_slot(self.m, "LvNode", slot["slot_field_uuid"], "lv_node_federation_uuid_fk")
        d1 = mfdb_core_get_entity_doc(self.m, "LvNode")
        fm1 = bejson_core_get_field_map(d1)
        self.assertEqual(fm1[name], pos0)
        self.assertEqual(json.dumps(d1["Values"]), rows0)
        self.assertEqual(trk.bejson_taxonomies_resolve_field_uuid(self.m, "LvNode", name), slot["slot_field_uuid"])
        z = zsa.bejson_tax_scaffolds_find_slot(self.m, "LvNode")
        self.assertEqual((z["state_kind"], z["bound_field_name"]), ("bound", name))
        self.ok()

    def test_bind_refusals(self):
        self.variant_entity()
        (slot,) = zsa.bejson_tax_scaffolds_reserve_z_space_slot(
            self.m, "LvNode", "lv", fk_target_entity=st.E_LINK, fk_on_delete="null")
        bind = lambda n: zsa.bejson_tax_scaffolds_bind_z_space_slot(self.m, "LvNode", slot["slot_field_uuid"], n)
        for bad in ("lv_node_federation_slot",      # still a slot
                    "node_federation_uuid_fk",      # prefix
                    "lv_node_federation_name",      # FK slot must end _uuid_fk
                    "lv_node_label_key"):           # exists
            with self.assertRaises(st.TaxonomyComplianceError, msg=bad):
                bind(bad)
        self.ok()  # refusals changed nothing
        bind("lv_node_federation_uuid_fk")
        with self.assertRaises(st.TaxonomyError) as c:
            bind("lv_node_other_uuid_fk")
        self.assertEqual(c.exception.code, "E_ZSPACE_ALREADY_BOUND")

    def test_unknown_slot_and_entity(self):
        with self.assertRaises(st.TaxonomyError):
            zsa.bejson_tax_scaffolds_bind_z_space_slot(self.m, st.E_DEPLOYMENT, "66666666-6666-4666-8666-666666666666", "lattice_x_uuid_fk")
        with self.assertRaises(st.TaxonomyError):
            zsa.bejson_tax_scaffolds_reserve_z_space_slot(self.m, "NoSuchEntity", "lattice")

    def test_reserve_after_bind_keeps_trailing_block(self):
        self.variant_entity()
        (s1,) = zsa.bejson_tax_scaffolds_reserve_z_space_slot(self.m, "LvNode", "lv")
        zsa.bejson_tax_scaffolds_bind_z_space_slot(self.m, "LvNode", s1["slot_field_uuid"], "lv_node_extra_key")
        zsa.bejson_tax_scaffolds_reserve_z_space_slot(self.m, "LvNode", "lv")
        self.ok()


class TestDeployments(Base):
    def test_register_and_lookup(self):
        u = dep.bejson_tax_scaffolds_register_deployment(self.m, "n1", "Node 1", "master", "rebuild", "lattice")
        self.assertEqual(dep.bejson_tax_scaffolds_get_deployment(self.m, "n1")["deployment_uuid"], u)
        self.assertEqual(dep.bejson_tax_scaffolds_get_deployment(self.m, u)["node_key"], "n1")
        self.ok()

    def test_all_role_strategy_combinations_legal(self):
        for i, (role, strat) in enumerate([("master", "rebuild"), ("master", "prebuilt"), ("slave", "rebuild"), ("slave", "prebuilt")]):
            dep.bejson_tax_scaffolds_register_deployment(self.m, f"n{i}", "x", role, strat, "lattice")
        self.assertEqual(len(dep.bejson_tax_scaffolds_list_deployments(self.m)), 4)
        self.ok()

    def test_validation(self):
        reg_ = lambda **k: dep.bejson_tax_scaffolds_register_deployment(
            self.m, **{"node_key": "n", "display_name": "x", "role_kind": "master", "strategy_kind": "rebuild", "taxonomy_ref": "lattice", **k})
        for bad in ({"role_kind": "boss"}, {"strategy_kind": "magic"}, {"node_key": ""}, {"taxonomy_ref": "nope"}):
            with self.assertRaises(st.TaxonomyError, msg=bad):
                reg_(**bad)
        reg_()
        with self.assertRaises(st.TaxonomyError):
            reg_()  # duplicate key
        self.ok()

    def test_active_flag_and_network_role(self):
        dep.bejson_tax_scaffolds_register_deployment(self.m, "n1", "x", "master", "rebuild", "lattice")
        dep.bejson_tax_scaffolds_set_deployment_active(self.m, "n1", False)
        self.assertFalse(dep.bejson_tax_scaffolds_get_deployment(self.m, "n1")["active_flag"])
        dep.bejson_tax_scaffolds_set_network_role(self.m, "Slave")
        self.assertEqual(bejson_core_load_file(self.m)["Network_Role"], "Slave")
        with self.assertRaises(st.TaxonomyError):
            dep.bejson_tax_scaffolds_set_network_role(self.m, "Boss")
        self.ok()


class TestFederation(Base):
    def setUp(self):
        super().setUp()
        reg.bejson_taxonomies_derive_variant(self.m, "lattice", "lv")
        r = dep.bejson_tax_scaffolds_register_deployment
        self.a = r(self.m, "node-a", "A", "master", "rebuild", "lattice")
        self.b = r(self.m, "node-b", "B", "slave", "prebuilt", "lattice")
        self.c = r(self.m, "node-c", "C", "slave", "prebuilt", "lv")

    def test_identical_and_variant_match_kinds(self):
        l1 = fb.bejson_tax_scaffolds_create_federation_link(self.m, "node-a", "node-b")
        l2 = fb.bejson_tax_scaffolds_create_federation_link(self.m, "node-a", "node-c")
        self.assertEqual(fb.bejson_tax_scaffolds_get_federation_link(self.m, l1)["match_kind"], "identical")
        self.assertEqual(fb.bejson_tax_scaffolds_get_federation_link(self.m, l2)["match_kind"], "variant")
        self.ok()

    def test_link_validation(self):
        with self.assertRaises(st.TaxonomyError):      # roles reversed
            fb.bejson_tax_scaffolds_create_federation_link(self.m, "node-b", "node-a")
        with self.assertRaises(st.TaxonomyError):
            fb.bejson_tax_scaffolds_create_federation_link(self.m, "node-a", "node-b", interval_seconds=0)
        fb.bejson_tax_scaffolds_create_federation_link(self.m, "node-a", "node-b")
        with self.assertRaises(st.TaxonomyError) as c:
            fb.bejson_tax_scaffolds_create_federation_link(self.m, "node-a", "node-b")
        self.assertEqual(c.exception.code, "E_LINK_EXISTS")

    def test_bind_resolve_and_slot_becomes_bound(self):
        lk = fb.bejson_tax_scaffolds_create_federation_link(self.m, "node-a", "node-c")
        self.assertIsNone(fb.bejson_tax_scaffolds_resolve_federation_link(self.m, "node-a"))
        name = fb.bejson_tax_scaffolds_bind_federation_link(self.m, "node-a", lk)
        self.assertEqual(name, st.DP_FEDERATION_BOUND)
        self.assertEqual(fb.bejson_tax_scaffolds_bind_federation_link(self.m, "node-c", lk), name)  # second bind reuses slot
        for node in ("node-a", "node-c"):
            self.assertEqual(fb.bejson_tax_scaffolds_resolve_federation_link(self.m, node)["link_uuid"], lk)
        self.assertIsNone(fb.bejson_tax_scaffolds_resolve_federation_link(self.m, "node-b"))
        self.assertEqual(zsa.bejson_tax_scaffolds_find_slot(self.m, st.E_DEPLOYMENT)["state_kind"], "bound")
        self.ok()

    def test_bind_rejects_non_endpoint(self):
        lk = fb.bejson_tax_scaffolds_create_federation_link(self.m, "node-a", "node-b")
        with self.assertRaises(st.TaxonomyError) as c:
            fb.bejson_tax_scaffolds_bind_federation_link(self.m, "node-c", lk)
        self.assertEqual(c.exception.code, "E_LINK_NOT_ENDPOINT")

    def test_teardown_unlinks_nodes_without_deleting_them(self):
        lk = fb.bejson_tax_scaffolds_create_federation_link(self.m, "node-a", "node-b")
        fb.bejson_tax_scaffolds_bind_federation_link(self.m, "node-a", lk)
        fb.bejson_tax_scaffolds_bind_federation_link(self.m, "node-b", lk)
        fb.bejson_tax_scaffolds_teardown_federation_link(self.m, lk)
        self.assertEqual(len(dep.bejson_tax_scaffolds_list_deployments(self.m)), 3)
        for node in ("node-a", "node-b"):
            self.assertIsNone(fb.bejson_tax_scaffolds_resolve_federation_link(self.m, node))
        self.ok()

    def test_cannot_delete_linked_deployment(self):
        from lib_bejson_Core_mfdb_core import mfdb_core_delete_entity_record_105
        fb.bejson_tax_scaffolds_create_federation_link(self.m, "node-a", "node-b")
        with self.assertRaises(Exception):  # restrict: link still references the deployment
            mfdb_core_delete_entity_record_105(self.m, st.E_DEPLOYMENT, self.a)

    def test_link_config_round_trip_through_dropzone(self):
        lk = fb.bejson_tax_scaffolds_create_federation_link(self.m, "node-a", "node-c")
        drop = os.path.join(self.tmp, "dropzone")
        self.assertTrue(fb.bejson_tax_scaffolds_push_link_config(self.m, lk, drop))
        (fname,) = os.listdir(drop)
        with open(os.path.join(drop, fname), encoding="utf-8") as fh:
            doc = json.load(fh)
        cfg = fb.bejson_tax_scaffolds_read_link_config(doc)
        self.assertEqual((cfg["link_uuid"], cfg["match_kind"], cfg["slave_taxonomy_prefix"], cfg["master_taxonomy_prefix"]),
                         (lk, "variant", "lv_", "lattice_"))
        self.assertIn("_uuid_fk", json.loads(cfg["slave_taxonomy_suffix_rules"]))
        with self.assertRaises(st.TaxonomyError):
            fb.bejson_tax_scaffolds_read_link_config({"Records_Type": ["Other"]})


class TestRebuild(Base):
    def test_master_and_slave_rebuild(self):
        m = rb.bejson_tax_scaffolds_deploy_master_rebuild(os.path.join(self.tmp, "m"), "m1", "Master 1")
        s = rb.bejson_tax_scaffolds_deploy_slave_rebuild(os.path.join(self.tmp, "s"), "s1", "Slave 1")
        self.assertEqual(bejson_core_load_file(m["manifest_path"])["Network_Role"], "Master")
        self.assertEqual(bejson_core_load_file(s["manifest_path"])["Network_Role"], "Slave")
        self.assertIn("ConnectedSlave", st.manifest_entity_names(m["manifest_path"]))
        self.assertNotIn("ConnectedSlave", st.manifest_entity_names(s["manifest_path"]))
        for r in (m, s):
            self.ok(r["manifest_path"])
            d = dep.bejson_tax_scaffolds_get_deployment(r["manifest_path"], r["deployment_uuid"])
            self.assertEqual(d["strategy_kind"], "rebuild")

    def test_rebuild_with_variant_taxonomy(self):
        r = rb.bejson_tax_scaffolds_deploy_master_rebuild(
            os.path.join(self.tmp, "v"), "v1", "Variant", taxonomy_namespace="lv",
            suffix_overrides={"_ref": "string"}, suffix_removals=["_kind"])
        tx = reg.bejson_taxonomies_get_taxonomy(r["manifest_path"], r["taxonomy_uuid"])
        self.assertEqual((tx["namespace_key"], "_ref" in tx["suffix_rules"], "_kind" in tx["suffix_rules"]), ("lv", True, False))
        self.ok(r["manifest_path"])

    def test_rebuild_refusals(self):
        with self.assertRaises(st.TaxonomyError):
            rb.bejson_tax_scaffolds_deploy_rebuild(os.path.join(self.tmp, "x"), "x", "x", role_kind="boss")
        with self.assertRaises(st.TaxonomyError):      # root taxonomy cannot be edited at deploy time
            rb.bejson_tax_scaffolds_deploy_rebuild(os.path.join(self.tmp, "y"), "y", "y", suffix_removals=["_kind"])
        with self.assertRaises(st.TaxonomyError):      # variant may not drop a required suffix
            rb.bejson_tax_scaffolds_deploy_rebuild(os.path.join(self.tmp, "z"), "z", "z", taxonomy_namespace="lv", suffix_removals=["_slot"])


class TestPrebuilt(Base):
    def make_source(self, variant=False):
        src = rb.bejson_tax_scaffolds_deploy_master_rebuild(os.path.join(self.tmp, "src"), "src", "Source")
        m = src["manifest_path"]
        if variant:
            reg.bejson_taxonomies_derive_variant(m, "lattice", "lv", {"_ref": "string"})
            tx = reg.bejson_taxonomies_get_taxonomy(m, "lv")
            sb.bejson_taxonomies_create_domain_entity(
                m, "lv", "LvNode", [sb.bejson_taxonomies_build_field_definition(tx, "lv_node_label_key", "string")])
            st.add_row(m, "LvNode", ["seed-row"])
        lk_slave = dep.bejson_tax_scaffolds_register_deployment(m, "peer", "Peer", "slave", "prebuilt", "lattice")
        fb.bejson_tax_scaffolds_create_federation_link(m, "src", "peer")
        return m

    def test_snapshot_strips_instances_keeps_schema_and_seed(self):
        m = self.make_source(variant=True)
        snap = pb.bejson_tax_scaffolds_capture_snapshot(m, os.path.join(self.tmp, "snap"))
        for ent in (st.E_DEPLOYMENT, st.E_LINK, "ConnectedSlave"):
            self.assertEqual(st.read_rows(snap, ent), [], ent)
        self.assertEqual(len(st.read_rows(snap, "LvNode")), 1)           # seed row kept
        self.assertEqual(len(reg.bejson_taxonomies_list_taxonomies(snap)), 2)
        self.assertEqual(len(st.read_rows(snap, st.E_ZSPACE)), 1)        # reservation kept
        self.ok(snap)
        self.assertEqual(len(dep.bejson_tax_scaffolds_list_deployments(m)), 2)  # source untouched

    def test_deploy_master_and_slave_share_fingerprints(self):
        snap = pb.bejson_tax_scaffolds_capture_snapshot(self.make_source(), os.path.join(self.tmp, "snap"))
        a = pb.bejson_tax_scaffolds_deploy_master_prebuilt(os.path.join(self.tmp, "snap"), os.path.join(self.tmp, "a"), "a", "A")
        b = pb.bejson_tax_scaffolds_deploy_slave_prebuilt(os.path.join(self.tmp, "snap"), os.path.join(self.tmp, "b"), "b", "B")
        self.assertEqual(a["taxonomy_uuid"], b["taxonomy_uuid"])
        fields = lambda mp: [(e, f["field_uuid"]) for e in (st.E_TAXONOMY, st.E_DEPLOYMENT, st.E_LINK)
                             for f in mfdb_core_get_entity_doc(mp, e)["Fields"]]
        self.assertEqual(fields(a["manifest_path"]), fields(b["manifest_path"]))
        self.assertEqual(bejson_core_load_file(a["manifest_path"])["Network_Role"], "Master")
        self.assertEqual(bejson_core_load_file(b["manifest_path"])["Network_Role"], "Slave")
        self.assertIn("ConnectedSlave", st.manifest_entity_names(a["manifest_path"]))
        for r in (a, b):
            self.ok(r["manifest_path"])
            self.assertEqual(dep.bejson_tax_scaffolds_get_deployment(r["manifest_path"], r["deployment_uuid"])["strategy_kind"], "prebuilt")

    def test_variant_snapshot_needs_taxonomy_choice(self):
        snap = pb.bejson_tax_scaffolds_capture_snapshot(self.make_source(variant=True), os.path.join(self.tmp, "snap"))
        with self.assertRaises(st.TaxonomyError) as c:
            pb.bejson_tax_scaffolds_deploy_slave_prebuilt(os.path.join(self.tmp, "snap"), os.path.join(self.tmp, "v0"), "v0", "V")
        self.assertEqual(c.exception.code, "E_TAXONOMY_AMBIGUOUS")
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "v0")))
        r = pb.bejson_tax_scaffolds_deploy_slave_prebuilt(os.path.join(self.tmp, "snap"), os.path.join(self.tmp, "v1"), "v1", "V", taxonomy_ref="lv")
        self.assertEqual(reg.bejson_taxonomies_get_taxonomy(r["manifest_path"], r["taxonomy_uuid"])["namespace_key"], "lv")
        self.ok(r["manifest_path"])

    def test_prebuilt_nodes_with_different_taxonomies_link_as_variant(self):
        snap = pb.bejson_tax_scaffolds_capture_snapshot(self.make_source(variant=True), os.path.join(self.tmp, "snap"))
        # both nodes registered in one registry (the master's) following different taxonomies
        mp = os.path.join(self.tmp, "hub")
        hub = pb.bejson_tax_scaffolds_deploy_master_prebuilt(os.path.join(self.tmp, "snap"), mp, "hub", "Hub", taxonomy_ref="lattice")
        dep.bejson_tax_scaffolds_register_deployment(hub["manifest_path"], "edge", "Edge", "slave", "prebuilt", "lv")
        lk = fb.bejson_tax_scaffolds_create_federation_link(hub["manifest_path"], "hub", "edge")
        self.assertEqual(fb.bejson_tax_scaffolds_get_federation_link(hub["manifest_path"], lk)["match_kind"], "variant")
        self.ok(hub["manifest_path"])

    def test_refusals_and_cleanup(self):
        src = self.make_source()
        snap = pb.bejson_tax_scaffolds_capture_snapshot(src, os.path.join(self.tmp, "snap"))
        with self.assertRaises(rb.ScaffoldError):      # snapshot target not empty
            pb.bejson_tax_scaffolds_capture_snapshot(src, os.path.join(self.tmp, "snap"))
        os.makedirs(os.path.join(self.tmp, "full"))
        open(os.path.join(self.tmp, "full", "x"), "w").close()
        with self.assertRaises(rb.ScaffoldError):
            pb.bejson_tax_scaffolds_deploy_master_prebuilt(os.path.join(self.tmp, "snap"), os.path.join(self.tmp, "full"), "f", "F")
        with self.assertRaises(st.TaxonomyError):      # failure after copy removes the target
            pb.bejson_tax_scaffolds_deploy_master_prebuilt(os.path.join(self.tmp, "snap"), os.path.join(self.tmp, "bad"), "", "F")
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "bad")))
        with self.assertRaises(rb.ScaffoldError):
            pb.bejson_tax_scaffolds_deploy_master_prebuilt(os.path.join(self.tmp, "nosuch"), os.path.join(self.tmp, "n"), "n", "N")

    def test_snapshot_refuses_failing_source(self):
        m = self.make_source()
        p = st.entity_path(m, st.E_ZSPACE)
        doc = bejson_core_load_file(p)
        doc["Fields"][2]["type"] = "string"
        bejson_core_atomic_write(p, doc)
        with self.assertRaises(rb.ScaffoldError):
            pb.bejson_tax_scaffolds_capture_snapshot(m, os.path.join(self.tmp, "snap"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
