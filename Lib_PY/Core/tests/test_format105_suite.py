"""
Library:        test_format105_suite.py
Family:         Core (tests)
Description:    Exhaustive unittest suite for every Format_Version 105/105a/
                 105db function added in Format105_Master_Plan_Rev2 Phase
                 2-4 (lib_bejson_Core_bejson_core.py, lib_bejson_Core_
                 bejson_validator.py, lib_bejson_Core_bejson_upgrade.py,
                 bejson_upgrade_cli.py). Every test that touches disk creates
                 its own real .bejson file under a fresh temp directory in
                 setUp() and deletes the entire directory in tearDown() --
                 no test leaves a file behind, and no test reuses another
                 test's file. Also carries a 104/104a/104db regression class
                 confirming zero behavior change on the legacy path.

                 Run:  python3 -m unittest tests.test_format105_suite -v
                 or:   python3 tests/test_format105_suite.py

Version:        1.2.1
Date:           2026-10-03
Author:         Elton Boehnen
Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
Format_Creator: Elton Boehnen
RELATIONAL_ID:  f46cfd38-23b1-4a4b-a822-a380ed4f23c4
Release_Version: 300

Changelog:
  1.2.0 - Added TestAutoFieldMap (13 tests): load/upgrade warm the field map;
          lookups, direct Fields edits, renames, replaced Fields lists and
          104-style leftovers are all handled with no manual rebuild.
"""

import os
import sys
import json
import copy
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import lib_bejson_Core_bejson_core as Core
import lib_bejson_Core_bejson_validator as Validator
import lib_bejson_Core_bejson_upgrade as Upgrade
from lib_bejson_Core_bejson_upgrade import BEJSONUpgradeError


def make_104_doc():
    return {
        "Format": "BEJSON", "Format_Version": "104", "Format_Creator": "Elton Boehnen",
        "Records_Type": ["Test"],
        "Fields": [
            {"name": "full_name", "type": "string"},
            {"name": "age", "type": "integer"},
        ],
        "Values": [["Elton", 40], ["Bob", 30], ["Carol", 55]],
    }


def make_104db_doc():
    return {
        "Format": "BEJSON", "Format_Version": "104db", "Format_Creator": "Elton Boehnen",
        "Records_Type": ["TypeA", "TypeB"],
        "Fields": [
            {"name": "Record_Type_Parent", "type": "string"},
            {"name": "val", "type": "string", "Record_Type_Parent": ["TypeA", "TypeB"]},
        ],
        "Values": [["TypeA", "x"], ["TypeB", "y"], ["TypeA", "z"]],
    }


def make_104a_doc():
    return {
        "Format": "BEJSON", "Format_Version": "104a", "Format_Creator": "Elton Boehnen",
        "Records_Type": ["Test"],
        "Fields": [
            {"name": "full_name", "type": "string"},
            {"name": "age", "type": "integer"},
        ],
        "Values": [["Elton", 40], ["Bob", 30]],
        "Custom_Header_Example": "104a permits this; 104/104db do not",
    }


class FileBackedTestCase(unittest.TestCase):
    """Base class: every subclass gets a fresh temp dir + a real .bejson
    file created on disk in setUp(), fully deleted in tearDown()."""

    doc_factory = staticmethod(make_104_doc)

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="bejson105_test_")
        self.path = os.path.join(self.tmpdir, "test.104.bejson")
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.doc_factory(), f)
        self.assertTrue(os.path.exists(self.path), "fixture file must exist after setUp")

    def tearDown(self):
        self.assertTrue(os.path.isdir(self.tmpdir))
        shutil.rmtree(self.tmpdir)
        self.assertFalse(os.path.exists(self.tmpdir), "temp dir must be fully deleted after tearDown")

    def upgrade(self):
        """Loads self.path, upgrades in place, returns the new 105 doc."""
        doc = json.load(open(self.path))
        return Upgrade.bejson_core_upgrade_to_105(doc, self.path)

    def reread(self):
        return json.load(open(self.path))


# ---------------------------------------------------------------------------
# 1. bejson_core_upgrade_to_105 / dry-run  (Phase 4, \u00a74.1/\u00a74.2)
# ---------------------------------------------------------------------------

class TestUpgradeTo105(FileBackedTestCase):

    def test_upgrade_round_trip_104(self):
        orig = json.load(open(self.path))
        new_doc = self.upgrade()
        self.assertEqual(new_doc["Format_Version"], "105")
        self.assertEqual(len(new_doc["Values"]), len(orig["Values"]))
        for old_row, new_row in zip(orig["Values"], new_doc["Values"]):
            self.assertEqual(new_row[1:], old_row)  # original values preserved after the uuid

    def test_every_row_gets_unique_record_uuid(self):
        new_doc = self.upgrade()
        uuids = [row[0] for row in new_doc["Values"]]
        self.assertEqual(len(uuids), len(set(uuids)), "record_uuids must be unique")
        self.assertTrue(all(isinstance(u, str) and len(u) == 36 for u in uuids))

    def test_every_field_gets_unique_field_uuid(self):
        new_doc = self.upgrade()
        uuids = [f["field_uuid"] for f in new_doc["Fields"]]
        self.assertEqual(len(uuids), len(set(uuids)))

    def test_reread_from_disk_validates(self):
        self.upgrade()
        reread = self.reread()
        res = Validator.validate_bejson(copy.deepcopy(reread))
        self.assertTrue(res.valid, res.errors)

    def test_backup_written_and_byte_identical(self):
        orig_bytes = open(self.path, "rb").read()
        self.upgrade()
        backup_path = os.path.join(self.tmpdir, "Backups", "test.104.bejson.104.bak")
        self.assertTrue(os.path.exists(backup_path))
        self.assertEqual(open(backup_path, "rb").read(), orig_bytes)

    def test_interrupted_write_leaves_original_untouched(self):
        orig_bytes = open(self.path, "rb").read()
        real_replace = os.replace
        os.replace = lambda a, b: (_ for _ in ()).throw(OSError("simulated crash"))
        try:
            with self.assertRaises(OSError):
                self.upgrade()
        finally:
            os.replace = real_replace
        self.assertEqual(open(self.path, "rb").read(), orig_bytes, "original must survive an interrupted write")
        casualties = [f for f in os.listdir(self.tmpdir) if f.endswith(".105tmp")]
        self.assertEqual(casualties, [], "no orphaned temp file should remain")

    def test_wrong_format_version_rejected(self):
        doc = json.load(open(self.path))
        doc["Format_Version"] = "105"  # already upgraded
        with self.assertRaises(BEJSONUpgradeError) as ctx:
            Upgrade.bejson_core_upgrade_to_105(doc, self.path)
        self.assertIn("E_FORMAT_UNSUPPORTED", str(ctx.exception))

    def test_dry_run_writes_nothing(self):
        orig_bytes = open(self.path, "rb").read()
        doc = json.load(open(self.path))
        report = Upgrade.bejson_core_upgrade_dry_run(doc, self.path)
        self.assertTrue(report["validation_pass"])
        self.assertEqual(report["record_count"], 3)
        self.assertEqual(report["field_count"], 2)
        self.assertEqual(report["target_version"], "105")
        self.assertEqual(open(self.path, "rb").read(), orig_bytes, "dry-run must not touch the source file")
        self.assertFalse(os.path.exists(os.path.join(self.tmpdir, "Backups")), "dry-run must not create a backup")


class TestUpgradeTo105a(FileBackedTestCase):
    """Audit finding (2026-08-16): upgrade_to_105 originally collapsed every
    non-104db source to plain '105', silently dropping '104a' -> '105a'
    despite the file's own docstring promising 105a support. Bug inherited
    verbatim from the master plan's own example code; fixed here, and this
    class exists specifically because the original 65-case suite had zero
    104a coverage and did not catch it."""
    doc_factory = staticmethod(make_104a_doc)

    def test_104a_upgrades_to_105a_not_105(self):
        new_doc = self.upgrade()
        self.assertEqual(new_doc["Format_Version"], "105a")

    def test_104a_custom_header_preserved(self):
        new_doc = self.upgrade()
        self.assertEqual(new_doc["Custom_Header_Example"], "104a permits this; 104/104db do not")

    def test_105a_passes_full_validate_bejson(self):
        self.upgrade()
        reread = self.reread()
        res = Validator.validate_bejson(copy.deepcopy(reread))
        self.assertTrue(res.valid, res.errors)

    def test_105a_uses_single_offset_not_105db_double_offset(self):
        doc = self.upgrade()
        idx = Core.bejson_core_resolve_field_index(doc, "full_name")
        self.assertEqual(idx, 1)  # same offset rule as plain 105, not 105db's +2

    def test_105a_dry_run_also_reports_105a(self):
        doc = json.load(open(self.path))
        report = Upgrade.bejson_core_upgrade_dry_run(doc, self.path)
        self.assertTrue(report["validation_pass"])
        self.assertEqual(report["target_version"], "105a")


class TestUpgradeTo105Db(FileBackedTestCase):
    doc_factory = staticmethod(make_104db_doc)

    def test_discriminator_survives_at_index_0(self):
        new_doc = self.upgrade()
        self.assertEqual(new_doc["Format_Version"], "105db")
        self.assertEqual(new_doc["Values"][0][0], "TypeA")
        self.assertEqual(new_doc["Values"][1][0], "TypeB")
        self.assertEqual(new_doc["Values"][2][0], "TypeA")

    def test_record_uuid_lands_at_index_1(self):
        new_doc = self.upgrade()
        for row in new_doc["Values"]:
            self.assertIsInstance(row[1], str)
            self.assertEqual(len(row[1]), 36)

    def test_per_entity_row_grouping_unchanged(self):
        orig = json.load(open(self.path))
        new_doc = self.upgrade()
        orig_discriminators = [r[0] for r in orig["Values"]]
        new_discriminators = [r[0] for r in new_doc["Values"]]
        self.assertEqual(orig_discriminators, new_discriminators)


# ---------------------------------------------------------------------------
# 2. bejson_core_resolve_field_index (\u00a72.1)
# ---------------------------------------------------------------------------

class TestResolveFieldIndex(FileBackedTestCase):

    def setUp(self):
        super().setUp()
        self.doc = self.upgrade()

    def test_resolve_by_name(self):
        idx = Core.bejson_core_resolve_field_index(self.doc, "full_name")
        self.assertEqual(idx, 1)  # offset 1 for plain 105

    def test_resolve_by_uuid(self):
        fuuid = self.doc["Fields"][1]["field_uuid"]  # age
        idx = Core.bejson_core_resolve_field_index(self.doc, fuuid)
        self.assertEqual(idx, 2)

    def test_resolve_by_matching_dict(self):
        f = self.doc["Fields"][0]
        idx = Core.bejson_core_resolve_field_index(self.doc, {"name": f["name"], "field_uuid": f["field_uuid"]})
        self.assertEqual(idx, 1)

    def test_resolve_by_mismatching_dict_raises(self):
        f0, f1 = self.doc["Fields"][0], self.doc["Fields"][1]
        with self.assertRaises(Core.BEJSONCoreError) as ctx:
            Core.bejson_core_resolve_field_index(self.doc, {"name": f0["name"], "field_uuid": f1["field_uuid"]})
        self.assertEqual(ctx.exception.code, 80)  # E_FIELD_INTEGRITY_MISMATCH

    def test_resolve_unknown_target_raises(self):
        with self.assertRaises(Core.BEJSONCoreError):
            Core.bejson_core_resolve_field_index(self.doc, "does_not_exist")

    def test_resolve_rejects_104_series(self):
        doc104 = make_104_doc()
        with self.assertRaises(Core.BEJSONCoreError) as ctx:
            Core.bejson_core_resolve_field_index(doc104, "full_name")
        self.assertEqual(ctx.exception.code, 81)  # E_FORMAT_UNSUPPORTED


class TestResolveFieldIndex105Db(FileBackedTestCase):
    doc_factory = staticmethod(make_104db_doc)

    def test_offset_is_2_for_105db(self):
        doc = self.upgrade()
        idx = Core.bejson_core_resolve_field_index(doc, "val")
        self.assertEqual(idx, 3)  # Fields[1]="val" -> +2 offset = 3


# ---------------------------------------------------------------------------
# 3. bejson_core_write_cell (\u00a72.2)
# ---------------------------------------------------------------------------

class TestWriteCell(FileBackedTestCase):

    def setUp(self):
        super().setUp()
        self.doc = self.upgrade()
        self.record_uuid = self.doc["Values"][0][0]
        self.field_uuid = self.doc["Fields"][0]["field_uuid"]

    def test_exact_match_coordinates_no_heal(self):
        result = Core.bejson_core_write_cell(
            self.doc, self.record_uuid, self.field_uuid, "Elton Boehnen",
            expected_row=0, expected_col=1,
        )
        self.assertFalse(result["healed"])
        self.assertEqual(self.doc["Values"][0][1], "Elton Boehnen")

    def test_drifted_coordinates_heal_and_write_correct_cell(self):
        result = Core.bejson_core_write_cell(
            self.doc, self.record_uuid, self.field_uuid, "Healed Name",
            expected_row=99, expected_col=99,
        )
        self.assertTrue(result["healed"])
        self.assertEqual(result["row"], 0)
        self.assertEqual(result["col"], 1)
        self.assertEqual(self.doc["Values"][0][1], "Healed Name")

    def test_unknown_record_uuid_raises_no_partial_write(self):
        before = copy.deepcopy(self.doc["Values"])
        with self.assertRaises(Core.BEJSONCoreError) as ctx:
            Core.bejson_core_write_cell(self.doc, "nonexistent-uuid", self.field_uuid, "x")
        self.assertEqual(ctx.exception.code, 82)  # E_RECORD_NOT_FOUND
        self.assertEqual(self.doc["Values"], before)

    def test_unknown_field_uuid_raises_no_partial_write(self):
        before = copy.deepcopy(self.doc["Values"])
        with self.assertRaises(Core.BEJSONCoreError) as ctx:
            Core.bejson_core_write_cell(self.doc, self.record_uuid, "nonexistent-uuid", "x")
        self.assertEqual(ctx.exception.code, 80)  # E_FIELD_INTEGRITY_MISMATCH
        self.assertEqual(self.doc["Values"], before)

    def test_rejects_104_series(self):
        doc104 = make_104_doc()
        with self.assertRaises(Core.BEJSONCoreError) as ctx:
            Core.bejson_core_write_cell(doc104, "x", "y", "z")
        self.assertEqual(ctx.exception.code, 81)


# ---------------------------------------------------------------------------
# 4. bejson_core_add_field / bejson_core_add_record_105 (\u00a72.3)
# ---------------------------------------------------------------------------

class TestAddFieldAddRecord(FileBackedTestCase):

    def setUp(self):
        super().setUp()
        self.doc = self.upgrade()

    def test_add_field_returns_uuid_and_registers(self):
        fuuid = Core.bejson_core_add_field(self.doc, "email", "string")
        self.assertIsInstance(fuuid, str)
        self.assertEqual(self.doc["Fields"][-1]["name"], "email")
        self.assertEqual(self.doc["Fields"][-1]["field_uuid"], fuuid)

    def test_add_field_pads_every_existing_row(self):
        row_count = len(self.doc["Values"])
        Core.bejson_core_add_field(self.doc, "email", "string")
        self.assertEqual(len(self.doc["Values"]), row_count)
        self.assertTrue(all(len(r) == 4 for r in self.doc["Values"]))  # uuid + 2 orig + 1 new
        self.assertTrue(all(r[-1] is None for r in self.doc["Values"]))

    def test_add_field_duplicate_name_rejected(self):
        Core.bejson_core_add_field(self.doc, "email", "string")
        with self.assertRaises(Core.BEJSONCoreError) as ctx:
            Core.bejson_core_add_field(self.doc, "email", "string")
        self.assertEqual(ctx.exception.code, 84)  # E_DUPLICATE_FIELD_NAME

    def test_add_field_generated_uuid_never_collides(self):
        # Force a "collision" once, confirm the regeneration loop produces a fresh one.
        real_uuid4 = Core._uuid.uuid4
        forced = str(real_uuid4())
        self.doc["Fields"][0]["field_uuid"] = forced  # plant a collision target
        calls = {"n": 0}
        def rigged():
            calls["n"] += 1
            return forced if calls["n"] == 1 else real_uuid4()
        Core._uuid.uuid4 = rigged
        try:
            new_uuid = Core.bejson_core_add_field(self.doc, "phone", "string")
        finally:
            Core._uuid.uuid4 = real_uuid4
        self.assertNotEqual(new_uuid, forced)
        self.assertGreaterEqual(calls["n"], 2, "collision must trigger a regeneration")

    def test_add_record_105_returns_record_uuid(self):
        ruuid = Core.bejson_core_add_record_105(self.doc, ["Dana", 22])
        self.assertIsInstance(ruuid, str)
        self.assertEqual(self.doc["Values"][-1][0], ruuid)
        self.assertEqual(self.doc["Values"][-1][1:], ["Dana", 22])

    def test_add_record_105_rejects_104_series(self):
        doc104 = make_104_doc()
        with self.assertRaises(Core.BEJSONCoreError) as ctx:
            Core.bejson_core_add_record_105(doc104, ["x", 1])
        self.assertEqual(ctx.exception.code, 81)

    def test_add_field_legacy_104_pads_rows(self):
        doc104 = make_104_doc()
        row_count = len(doc104["Values"])
        result = Core.bejson_core_add_field(doc104, "email", "string")
        self.assertIsNone(result)  # no uuid concept for legacy
        self.assertEqual(len(doc104["Values"]), row_count)
        self.assertTrue(all(len(r) == 3 for r in doc104["Values"]))


class TestAddRecord105Db(FileBackedTestCase):
    doc_factory = staticmethod(make_104db_doc)

    def test_discriminator_stays_at_index_0_on_new_record(self):
        doc = self.upgrade()
        ruuid = Core.bejson_core_add_record_105(doc, ["TypeB", "new_val"])
        new_row = doc["Values"][-1]
        self.assertEqual(new_row[0], "TypeB")
        self.assertEqual(new_row[1], ruuid)
        self.assertEqual(new_row[2], "new_val")


# ---------------------------------------------------------------------------
# 5. bejson_core_remove_field / bejson_core_delete_record (\u00a72.5)
# ---------------------------------------------------------------------------

class TestRemoveFieldDeleteRecord(FileBackedTestCase):

    def setUp(self):
        super().setUp()
        self.doc = self.upgrade()

    def test_remove_field_by_uuid(self):
        fuuid = Core.bejson_core_add_field(self.doc, "email", "string")
        Core.bejson_core_remove_field(self.doc, fuuid)
        self.assertEqual([f["name"] for f in self.doc["Fields"]], ["full_name", "age"])
        self.assertTrue(all(len(r) == 3 for r in self.doc["Values"]))

    def test_remove_field_by_name(self):
        Core.bejson_core_add_field(self.doc, "email", "string")
        Core.bejson_core_remove_field(self.doc, "email")
        self.assertEqual([f["name"] for f in self.doc["Fields"]], ["full_name", "age"])

    def test_remove_field_unaffected_by_concurrent_column_insertion(self):
        """Remove field targeting the ORIGINAL field_uuid after a new column
        was inserted -- proves removal is uuid-anchored, not position-anchored."""
        original_age_uuid = self.doc["Fields"][1]["field_uuid"]
        Core.bejson_core_add_field(self.doc, "email", "string")  # shifts nothing for age (appended at end)
        Core.bejson_core_add_field(self.doc, "phone", "string")
        Core.bejson_core_remove_field(self.doc, original_age_uuid)
        self.assertNotIn("age", [f["name"] for f in self.doc["Fields"]])
        self.assertEqual([f["name"] for f in self.doc["Fields"]], ["full_name", "email", "phone"])

    def test_remove_field_unknown_raises(self):
        with self.assertRaises(Core.BEJSONCoreError) as ctx:
            Core.bejson_core_remove_field(self.doc, "nonexistent")
        self.assertEqual(ctx.exception.code, 80)

    def test_remove_field_cache_evicted(self):
        fmap_before = Core._bejson_get_field_map_cache(self.doc)
        Core.bejson_core_remove_field(self.doc, "age")
        fmap_after = self.doc.get("_bejson_field_map")
        self.assertNotEqual(fmap_before["content_hash"], fmap_after["content_hash"] if fmap_after else None)

    def test_delete_record_by_uuid(self):
        target_uuid = self.doc["Values"][1][0]
        Core.bejson_core_delete_record(self.doc, target_uuid)
        remaining_uuids = [r[0] for r in self.doc["Values"]]
        self.assertNotIn(target_uuid, remaining_uuids)
        self.assertEqual(len(self.doc["Values"]), 2)

    def test_delete_record_unaffected_by_concurrent_row_insertion(self):
        target_uuid = self.doc["Values"][0][0]
        Core.bejson_core_add_record_105(self.doc, ["Zed", 99])  # insert before deleting
        Core.bejson_core_delete_record(self.doc, target_uuid)
        remaining_uuids = [r[0] for r in self.doc["Values"]]
        self.assertNotIn(target_uuid, remaining_uuids)
        self.assertIn("Zed", [r[1] for r in self.doc["Values"]])

    def test_delete_record_unknown_uuid_raises(self):
        with self.assertRaises(Core.BEJSONCoreError) as ctx:
            Core.bejson_core_delete_record(self.doc, "nonexistent-uuid")
        self.assertEqual(ctx.exception.code, 82)

    def test_delete_record_rejects_104_series(self):
        doc104 = make_104_doc()
        with self.assertRaises(Core.BEJSONCoreError) as ctx:
            Core.bejson_core_delete_record(doc104, "x")
        self.assertEqual(ctx.exception.code, 81)


# ---------------------------------------------------------------------------
# 6. bejson_core_transaction / cache invalidation (\u00a72.4)
# ---------------------------------------------------------------------------

class TestTransactionAndCache(FileBackedTestCase):

    def setUp(self):
        super().setUp()
        self.doc = self.upgrade()

    def _count_rebuilds(self, fn):
        calls = {"n": 0}
        real = Core._bejson_core_build_field_map
        def counting(doc):
            calls["n"] += 1
            return real(doc)
        Core._bejson_core_build_field_map = counting
        try:
            fn()
        finally:
            Core._bejson_core_build_field_map = real
        return calls["n"]

    def test_five_mutations_in_transaction_trigger_exactly_one_rebuild(self):
        def do_work():
            with Core.bejson_core_transaction(self.doc):
                for i in range(5):
                    Core.bejson_core_add_record_105(self.doc, [f"P{i}", 20 + i])
        n = self._count_rebuilds(do_work)
        self.assertEqual(n, 1)

    def test_same_five_mutations_outside_transaction_trigger_five_rebuilds(self):
        def do_work():
            for i in range(5):
                Core.bejson_core_add_field(self.doc, f"f{i}", "string")
        n = self._count_rebuilds(do_work)
        self.assertEqual(n, 5)

    def test_cache_invalidates_on_out_of_band_fields_edit(self):
        Core._bejson_get_field_map_cache(self.doc)  # warm
        self.doc["Fields"].append({"name": "out_of_band", "type": "string", "field_uuid": "manual-uuid"})
        fmap = Core._bejson_get_field_map_cache(self.doc)
        self.assertIn("out_of_band", fmap["by_name"])

    def test_no_cold_cache_reads_outside_transaction(self):
        """Every mutation outside a transaction rebuilds immediately -- the
        very next lookup must reflect it without triggering another rebuild."""
        Core.bejson_core_add_field(self.doc, "zzz", "string")
        cached_before = self.doc["_bejson_field_map"]
        idx = Core.bejson_core_resolve_field_index(self.doc, "zzz")
        cached_after = self.doc["_bejson_field_map"]
        self.assertIs(cached_before, cached_after, "lookup right after a mutation must hit warm cache, not rebuild")
        self.assertIsInstance(idx, int)


# ---------------------------------------------------------------------------
# 7. bejson_core_serialize (strip-on-serialize)
# ---------------------------------------------------------------------------

class TestSerialize(FileBackedTestCase):

    def test_runtime_keys_stripped(self):
        doc = self.upgrade()
        Core._bejson_get_field_map_cache(doc)  # populates _bejson_field_map
        with Core.bejson_core_transaction(doc):
            pass  # leaves _bejson_txn_active False but proves it never survives serialize either way
        clean = Core.bejson_core_serialize(doc)
        self.assertNotIn("_bejson_field_map", clean)
        self.assertNotIn("_bejson_txn_active", clean)
        self.assertNotIn("_bejson_txn_dirty", clean)
        self.assertIn("Fields", clean)
        self.assertIn("Values", clean)

    def test_serialized_doc_is_json_serializable(self):
        doc = self.upgrade()
        clean = Core.bejson_core_serialize(doc)
        json.dumps(clean)  # must not raise


# ---------------------------------------------------------------------------
# 8. bejson_core_verify_105_integrity (\u00a72.6, read-only)
# ---------------------------------------------------------------------------

class TestVerify105Integrity(FileBackedTestCase):

    def test_ok_true_on_healthy_doc(self):
        doc = self.upgrade()
        report = Core.bejson_core_verify_105_integrity(doc)
        self.assertTrue(report["ok"])
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["record_count"], 3)
        self.assertEqual(report["field_count"], 2)

    def test_ok_false_on_corrupt_doc_missing_field_uuid(self):
        doc = self.upgrade()
        del doc["Fields"][0]["field_uuid"]
        report = Core.bejson_core_verify_105_integrity(doc)
        self.assertFalse(report["ok"])
        self.assertTrue(len(report["errors"]) > 0)

    def test_ok_false_on_duplicate_record_uuid(self):
        doc = self.upgrade()
        doc["Values"][1][0] = doc["Values"][0][0]  # force a duplicate
        report = Core.bejson_core_verify_105_integrity(doc)
        self.assertFalse(report["ok"])

    def test_performs_zero_writes(self):
        """Read-only contract: verifying must never touch the filesystem.
        Point it at a manifest whose containing directory we then remove
        write permission from, and confirm no exception / no mutation."""
        doc = self.upgrade()
        before_mtime = os.path.getmtime(self.path)
        os.chmod(self.tmpdir, 0o555)
        try:
            report = Core.bejson_core_verify_105_integrity(doc)
            self.assertTrue(report["ok"])
        finally:
            os.chmod(self.tmpdir, 0o755)  # restore so tearDown can delete it
        after_mtime = os.path.getmtime(self.path)
        self.assertEqual(before_mtime, after_mtime, "verify must not write to disk")

    def test_reason_reported_for_non_105_doc(self):
        report = Core.bejson_core_verify_105_integrity(make_104_doc())
        self.assertFalse(report["ok"])
        self.assertEqual(report["reason"], "E_FORMAT_UNSUPPORTED")


# ---------------------------------------------------------------------------
# 9. Validator: bejson_validator_check_105_strict_integrity (\u00a73.1/\u00a73.2)
# ---------------------------------------------------------------------------

class TestValidator105(FileBackedTestCase):

    def test_valid_versions_includes_105_series(self):
        self.assertIn("105", Validator.VALID_VERSIONS)
        self.assertIn("105a", Validator.VALID_VERSIONS)
        self.assertIn("105db", Validator.VALID_VERSIONS)

    def test_healthy_doc_passes_full_validate_bejson(self):
        self.upgrade()
        reread = self.reread()
        res = Validator.validate_bejson(copy.deepcopy(reread))
        self.assertTrue(res.valid, res.errors)

    def test_missing_field_uuid_fails_E_INVALID_FIELDS(self):
        doc = self.upgrade()
        del doc["Fields"][0]["field_uuid"]
        errors = Validator.bejson_validator_check_105_strict_integrity(doc)
        self.assertTrue(any(e["code"] == "E_INVALID_FIELDS" for e in errors))

    def test_duplicate_record_uuid_fails_E_INVALID_VALUES(self):
        doc = self.upgrade()
        doc["Values"][1][0] = doc["Values"][0][0]
        errors = Validator.bejson_validator_check_105_strict_integrity(doc)
        self.assertTrue(any(e["code"] == "E_INVALID_VALUES" for e in errors))

    def test_fail_on_switch_header_only_change_fails(self):
        """A 104 doc with only Format_Version flipped to '105' must fail
        validation, not silently pass through as structurally sound."""
        doc = make_104_doc()
        doc["Format_Version"] = "105"
        errors = Validator.bejson_validator_check_105_strict_integrity(doc)
        self.assertTrue(len(errors) > 0)
        self.assertTrue(any("never compiled" in e["detail"] for e in errors))

    def test_full_validate_bejson_catches_fail_on_switch(self):
        doc = make_104_doc()
        doc["Format_Version"] = "105"
        res = Validator.validate_bejson(doc)
        self.assertFalse(res.valid)

    def test_invalid_field_type_rejected(self):
        """Merged fix (v3.1.0): a Field with a type outside the 6 canonical
        values must fail structural validation, for both 104 and 105-series."""
        doc = make_104_doc()
        doc["Fields"][0]["type"] = "any"
        res = Validator.validate_bejson(copy.deepcopy(doc))
        self.assertFalse(res.valid)
        self.assertTrue(any("invalid type" in e for e in res.errors))

    def test_invalid_field_type_rejected_case_sensitive(self):
        doc = make_104_doc()
        doc["Fields"][1]["type"] = "Number"  # capitalized -- not canonical
        res = Validator.validate_bejson(copy.deepcopy(doc))
        self.assertFalse(res.valid)

    def test_valid_field_type_still_passes_on_105_series(self):
        doc = self.upgrade()
        reread = self.reread()
        res = Validator.validate_bejson(copy.deepcopy(reread))
        self.assertTrue(res.valid, res.errors)


# ---------------------------------------------------------------------------
# 10. bejson_upgrade_cli.py end-to-end
# ---------------------------------------------------------------------------

class TestUpgradeCLI(FileBackedTestCase):

    def _run_cli(self, *args):
        import subprocess
        cli_path = os.path.join(os.path.dirname(__file__), "..", "cli", "bejson_upgrade_cli.py")
        result = subprocess.run(
            [sys.executable, cli_path, *args],
            capture_output=True, text=True, timeout=15,
        )
        return result

    def test_dry_run_writes_nothing_and_reports_pass(self):
        orig_bytes = open(self.path, "rb").read()
        result = self._run_cli(self.path, "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS", result.stdout)
        self.assertIn("fields and", result.stdout)
        self.assertIn("Dependent files", result.stdout)
        self.assertEqual(open(self.path, "rb").read(), orig_bytes)
        self.assertFalse(os.path.exists(os.path.join(self.tmpdir, "Backups")))

    def test_real_run_upgrades_and_writes_backup(self):
        result = self._run_cli(self.path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Upgraded", result.stdout)
        reread = json.load(open(self.path))
        self.assertEqual(reread["Format_Version"], "105")
        self.assertTrue(os.path.exists(os.path.join(self.tmpdir, "Backups", "test.104.bejson.104.bak")))

    def test_missing_file_reports_error_nonzero_exit(self):
        result = self._run_cli(os.path.join(self.tmpdir, "does_not_exist.bejson"))
        self.assertNotEqual(result.returncode, 0)


# ---------------------------------------------------------------------------
# 11. Legacy 104/104a/104db regression -- confirms zero behavior change
# ---------------------------------------------------------------------------

class TestLegacyRegressionUnaffected(FileBackedTestCase):

    def test_legacy_add_record_signature_unchanged(self):
        doc104 = make_104_doc()
        ok = Core.bejson_core_add_record(doc104, ["Frank", 33])
        self.assertIs(ok, True)
        self.assertEqual(doc104["Values"][-1], ["Frank", 33])

    def test_104_doc_validates_exactly_as_before(self):
        res = Validator.validate_bejson(copy.deepcopy(make_104_doc()))
        self.assertTrue(res.valid, res.errors)

    def test_104db_doc_validates_exactly_as_before(self):
        res = Validator.validate_bejson(copy.deepcopy(make_104db_doc()))
        self.assertTrue(res.valid, res.errors)

    def test_legacy_field_map_cache_still_works(self):
        doc104 = make_104_doc()
        fmap = Core.bejson_core_get_field_map(doc104)
        self.assertEqual(fmap.get("full_name"), 0)
        self.assertEqual(fmap.get("age"), 1)

    def test_new_105_functions_reject_104_uniformly(self):
        doc104 = make_104_doc()
        for fn, args in [
            (Core.bejson_core_resolve_field_index, (doc104, "full_name")),
            (Core.bejson_core_write_cell, (doc104, "x", "y", "z")),
            (Core.bejson_core_add_record_105, (doc104, ["x"])),
            (Core.bejson_core_delete_record, (doc104, "x")),
        ]:
            with self.assertRaises(Core.BEJSONCoreError) as ctx:
                fn(*args)
            self.assertEqual(ctx.exception.code, 81, f"{fn.__name__} should raise E_FORMAT_UNSUPPORTED")


# ---------------------------------------------------------------------------
# 9. Automatic field map maintenance -- no caller ever builds/refreshes it
# ---------------------------------------------------------------------------

class TestAutoFieldMap(FileBackedTestCase):
    """Every test here does ordinary work (load, look up, edit, write) and
    never calls _bejson_get_field_map_cache / a rebuild itself."""

    def _is_warm(self, doc):
        return Core._bejson_is_105_cache(doc.get("_bejson_field_map"))

    def test_upgraded_doc_is_born_warm(self):
        self.assertTrue(self._is_warm(self.upgrade()))

    def test_loading_a_105_file_builds_the_map(self):
        self.upgrade()                                  # file on disk is now 105
        doc = Core.bejson_core_load_file(self.path)
        self.assertTrue(self._is_warm(doc), "load alone must warm the field map")

    def test_loading_a_104_file_is_untouched(self):
        doc = Core.bejson_core_load_file(self.path)    # still 104 on disk
        self.assertNotIn("_bejson_field_map", doc)

    def test_plain_lookup_returns_row_position_on_105(self):
        doc = self.upgrade()
        row = doc["Values"][0]
        idx = Core.bejson_core_get_field_index(doc, "age")
        self.assertEqual(row[idx], 40, "row[get_field_index] must hit the right column")

    def test_lookup_after_a_105_operation_is_never_minus_one(self):
        doc = self.upgrade()
        Core.bejson_core_define_field(doc, "email", "string")
        self.assertNotEqual(Core.bejson_core_get_field_index(doc, "age"), -1)
        self.assertNotEqual(Core.bejson_core_get_field_index(doc, "email"), -1)

    def test_plain_lookup_then_105_call_does_not_crash(self):
        doc = self.upgrade()
        doc.pop("_bejson_field_map", None)
        Core.bejson_core_get_field_index(doc, "age")
        self.assertIsInstance(Core.bejson_core_resolve_field_index(doc, "age"), int)

    def test_stale_legacy_shaped_cache_is_rebuilt_not_trusted(self):
        doc = self.upgrade()
        doc["_bejson_field_map"] = {"full_name": 0, "age": 1}   # a 104-style map left in the slot
        self.assertEqual(Core.bejson_core_resolve_field_index(doc, "age"), 2)
        self.assertTrue(self._is_warm(doc))

    def test_direct_edit_to_fields_is_noticed_on_next_lookup(self):
        doc = self.upgrade()
        doc["Fields"].append({"name": "added_by_hand", "type": "string", "field_uuid": "u-hand"})
        for row in doc["Values"]:
            row.append(None)
        self.assertEqual(Core.bejson_core_get_field_index(doc, "added_by_hand"), 3)
        self.assertEqual(Core.bejson_core_resolve_field_index(doc, "u-hand"), 3)

    def test_rename_is_noticed_and_uuid_still_resolves(self):
        doc = self.upgrade()
        fuuid = doc["Fields"][1]["field_uuid"]
        doc["Fields"][1]["name"] = "years"
        self.assertEqual(Core.bejson_core_get_field_index(doc, "years"), 2)
        self.assertEqual(Core.bejson_core_get_field_index(doc, "age"), -1)
        self.assertEqual(Core.bejson_core_resolve_field_index(doc, fuuid), 2)

    def test_replacing_the_whole_fields_list_is_noticed(self):
        doc = self.upgrade()
        doc["Fields"] = [dict(f) for f in reversed(doc["Fields"])]
        for row in doc["Values"]:
            row[1:] = reversed(row[1:])
        self.assertEqual(Core.bejson_core_get_field_index(doc, "age"), 1)

    def test_unchanged_doc_reuses_the_same_cache_object(self):
        doc = self.upgrade()
        first = doc["_bejson_field_map"]
        Core.bejson_core_get_field_index(doc, "age")
        Core.bejson_core_resolve_field_index(doc, "full_name")
        self.assertIs(doc["_bejson_field_map"], first, "no rebuild when nothing changed")

    def test_reads_inside_a_transaction_see_fresh_fields(self):
        doc = self.upgrade()
        with Core.bejson_core_transaction(doc):
            Core.bejson_core_add_field(doc, "t1", "string")
            self.assertNotEqual(Core.bejson_core_get_field_index(doc, "t1"), -1)

    def test_cache_never_reaches_disk(self):
        doc = self.upgrade()
        Core.bejson_core_get_field_index(doc, "age")
        Core.bejson_core_atomic_write(self.path, doc)
        self.assertNotIn("_bejson_field_map", self.reread())


class TestSelfValidating104FieldMap(unittest.TestCase):
    """3.5.0: the 104-series map is checked against the live field layout on
    every read, so it can never go stale -- callers never refresh it."""

    def _doc(self):
        return Core.bejson_core_create_104("T", [{"name": "a", "type": "string"}], [["x"]])

    def test_add_field_is_visible_immediately(self):
        d = self._doc()
        self.assertEqual(Core.bejson_core_get_field_index(d, "a"), 0)
        Core.bejson_core_add_field(d, "b", "string")
        self.assertEqual(Core.bejson_core_get_field_index(d, "b"), 1)

    def test_out_of_band_fields_edit_is_noticed(self):
        d = self._doc()
        Core.bejson_core_get_field_map(d)
        d["Fields"].append({"name": "c", "type": "string"})
        self.assertEqual(Core.bejson_core_get_field_index(d, "c"), 1)
        d["Fields"].reverse()
        self.assertEqual(Core.bejson_core_get_field_map(d), {"c": 0, "a": 1})

    def test_unchanged_doc_hits_cache(self):
        d = self._doc()
        m1 = Core.bejson_core_get_field_map(d)
        self.assertIs(Core.bejson_core_get_field_map(d), m1)

    def test_load_stays_untouched_and_keys_never_reach_disk(self):
        d = self._doc(); Core.bejson_core_get_field_map(d)
        clean = Core.bejson_core_serialize(d)
        self.assertNotIn("_bejson_field_map", clean)
        self.assertNotIn("_bejson_field_map_fp", clean)

    def test_upgrade_in_place_rebuilds_as_105_shape(self):
        d = self._doc(); Core.bejson_core_get_field_map(d)   # plain 104 map in the slot
        d["Format_Version"] = "105"
        d["Fields"][0]["field_uuid"] = "u1"
        self.assertEqual(Core.bejson_core_get_field_index(d, "a"), 1)  # ROW position (record_uuid offset)


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    result = runner.run(suite)
    print(f"\n{'='*70}\nRan {result.testsRun} tests | "
          f"Failures: {len(result.failures)} | Errors: {len(result.errors)}\n{'='*70}")
    sys.exit(0 if result.wasSuccessful() else 1)
