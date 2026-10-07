"""
Library:        test_phase8_suite.py
Family:         Core (tests)
Description:    Test suite for bejson_core_define_field() (field_uuid +
                 FK/cascade options only) -- the one Phase 8 function that
                 remains after the 2026-09-25 cuts (schema constraints,
                 upsert_105, row_checksum, paginate_105). See errors.py
                 2.9.0 / validator.py 3.3.0 / core.py 3.3.0 changelogs.

                 Run:  python3 tests/test_phase8_suite.py

Version:        1.2.0
Date:           2026-09-25
Author:         Elton Boehnen
Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
Format_Creator: Elton Boehnen
RELATIONAL_ID:  1dd6b2ce-f9f5-465c-89bf-949fc3e9c97f
Release_Version: 300

Changelog:
  1.1.0 - Removed TestRequiredConstraint, TestUniqueConstraint,
          TestEnumConstraint, TestBoundsConstraint entirely, and the
          constraint-specific methods inside TestDefineField
          (test_constraint_keys_land_on_field_dict,
          test_min_max_on_string_field_rejected,
          test_length_bounds_on_integer_field_rejected,
          test_empty_enum_rejected,
          test_field_then_fails_schema_constraint_check_when_violated).
          FK/cascade tests are unchanged.
  1.2.0 - Removed TestUpsert105, TestRowChecksum104/105, TestPaginate105/Db
          along with the four functions they covered (upsert_105,
          row_checksum, verify_row_checksums, paginate_105), per Be25:
          only UUIDs, referential integrity and the UUID field map stay.
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


def make_104_doc():
    return {
        "Format": "BEJSON", "Format_Version": "104", "Format_Creator": "Elton Boehnen",
        "Records_Type": ["Test"],
        "Fields": [{"name": "full_name", "type": "string"}, {"name": "age", "type": "integer"}],
        "Values": [["Elton", 40], ["Bob", 30]],
    }


class FileBackedTestCase(unittest.TestCase):
    doc_factory = staticmethod(make_104_doc)

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="phase8_test_")
        self.path = os.path.join(self.tmpdir, "test.104.bejson")
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.doc_factory(), f)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        self.assertFalse(os.path.exists(self.tmpdir))

    def upgrade(self):
        doc = json.load(open(self.path))
        return Upgrade.bejson_core_upgrade_to_105(doc, self.path)


# ---------------------------------------------------------------------------
# 2. bejson_core_define_field
# ---------------------------------------------------------------------------

class TestDefineField(FileBackedTestCase):

    def setUp(self):
        super().setUp()
        self.doc = self.upgrade()

    def test_basic_field_creation(self):
        fuuid = Core.bejson_core_define_field(self.doc, "email", "string")
        self.assertIsInstance(fuuid, str)
        self.assertEqual(self.doc["Fields"][-1]["field_uuid"], fuuid)

    def test_pads_existing_rows(self):
        Core.bejson_core_define_field(self.doc, "email", "string")
        self.assertTrue(all(len(r) == 4 for r in self.doc["Values"]))

    def test_duplicate_name_rejected_nothing_appended(self):
        count_before = len(self.doc["Fields"])
        with self.assertRaises(Core.BEJSONCoreError) as ctx:
            Core.bejson_core_define_field(self.doc, "full_name", "string")
        self.assertEqual(ctx.exception.code, Core.E_DUPLICATE_FIELD_NAME)
        self.assertEqual(len(self.doc["Fields"]), count_before)

    def test_invalid_type_rejected(self):
        with self.assertRaises(Core.BEJSONCoreError):
            Core.bejson_core_define_field(self.doc, "x", "any")

    def test_fk_on_delete_without_target_entity_rejected(self):
        with self.assertRaises(Core.BEJSONCoreError):
            Core.bejson_core_define_field(self.doc, "x", "string", fk_on_delete="restrict")

    def test_invalid_fk_on_delete_value_rejected(self):
        with self.assertRaises(Core.BEJSONCoreError):
            Core.bejson_core_define_field(self.doc, "x", "string",
                                            fk_target_entity="authors", fk_on_delete="destroy")

    def test_valid_fk_definition(self):
        fuuid = Core.bejson_core_define_field(
            self.doc, "author_fk", "string", fk_target_entity="authors", fk_on_delete="restrict"
        )
        field = self.doc["Fields"][-1]
        self.assertEqual(field["fk_target_entity"], "authors")
        self.assertEqual(field["fk_on_delete"], "restrict")

    def test_rejects_104_series(self):
        doc104 = make_104_doc()
        with self.assertRaises(Core.BEJSONCoreError) as ctx:
            Core.bejson_core_define_field(doc104, "x", "string")
        self.assertEqual(ctx.exception.code, Core.E_FORMAT_UNSUPPORTED)


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    result = runner.run(suite)
    print(f"\n{'='*70}\nRan {result.testsRun} tests | "
          f"Failures: {len(result.failures)} | Errors: {len(result.errors)}\n{'='*70}")
    sys.exit(0 if result.wasSuccessful() else 1)
