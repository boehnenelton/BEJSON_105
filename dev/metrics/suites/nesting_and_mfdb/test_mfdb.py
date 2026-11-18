"""
Library:         test_mfdb.py
Family:          Core
Module Purpose:  Tests for the MFDB core and validator: create, add/remove records, count sync, validator catches broken databases, debug logging.
Architecture:    Standalone unittest script; resolves the library modules relative to this file (no absolute paths); each test builds a database in a temp dir.
Format_Scope:    MFDB only (104a manifest + 104 entity files; NOT 104db)
Glossary:        BEJSON 104, 104a and 104db are the three file formats (Format_Version). 104db = ONE file holding 2+ entity types
                 (Record_Type_Parent discriminator, null-padding). MFDB is NOT a format and NOT 104db: it is a layer made of one 104a manifest
                 (104a.mfdb.bejson) plus dense 104 entity files linked by Parent_Hierarchy. MFDB-132 = an MFDB packed into one Chunked-104a document.
Version:         1.0.0
Release_Version: 300
Date:            2026-10-16
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   947d035a-e5e4-4963-bef0-301b42764baa
"""
import json
import logging
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
logging.disable(logging.CRITICAL)

import lib_bejson_Core_mfdb_core as core
import lib_bejson_Core_mfdb_validator as validator

ENTITY = {"name": "User", "fields": [{"name": "id", "type": "integer"}, {"name": "name", "type": "string"}]}


def read(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)


class MfdbTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.manifest = core.mfdb_core_create_database(self.tmp.name, "T", [ENTITY])
        self.entity = os.path.join(self.tmp.name, "data", "user.bejson")

    def test_fresh_database_is_valid(self):
        self.assertTrue(validator.validate_mfdb_database(self.manifest).valid)

    def test_add_and_remove_keep_count_in_sync(self):
        core.mfdb_core_add_entity_record(self.manifest, "User", [1, "a"])
        core.mfdb_core_add_entity_record(self.manifest, "User", [2, "b"])
        self.assertEqual(read(self.manifest)["Values"][0][3], 2)
        self.assertEqual(len(read(self.entity)["Values"]), 2)
        self.assertTrue(validator.validate_mfdb_database(self.manifest).valid)

    def test_missing_entity_file_is_caught(self):
        os.remove(self.entity)
        self.assertFalse(validator.validate_mfdb_database(self.manifest).valid)

    def test_wrong_parent_hierarchy_is_caught(self):
        doc = read(self.entity)
        doc["Parent_Hierarchy"] = "../nope.bejson"
        write(self.entity, doc)
        self.assertFalse(validator.validate_mfdb_database(self.manifest).valid)

    def test_missing_parent_hierarchy_is_caught(self):
        doc = read(self.entity)
        del doc["Parent_Hierarchy"]
        write(self.entity, doc)
        self.assertFalse(validator.validate_mfdb_database(self.manifest).valid)

    def test_entity_row_length_mismatch_is_caught(self):
        doc = read(self.entity)
        doc["Values"].append([1])
        write(self.entity, doc)
        self.assertFalse(validator.validate_mfdb_database(self.manifest).valid)

    def test_persisted_field_map_in_entity_is_caught(self):
        doc = read(self.entity)
        doc["_bejson_field_map"] = {"id": 0, "name": 1}
        write(self.entity, doc)
        self.assertFalse(validator.validate_mfdb_database(self.manifest).valid)

    def test_sync_repairs_stale_count(self):
        core.mfdb_core_add_entity_record(self.manifest, "User", [1, "a"])
        man = read(self.manifest)
        man["Values"][0][3] = 99
        write(self.manifest, man)
        core.mfdb_core_sync_all_counts(self.manifest)
        self.assertEqual(read(self.manifest)["Values"][0][3], 1)

    def test_debug_logging_records_writes(self):
        core.mfdb_core_enable_debug(self.manifest)
        core.mfdb_core_add_entity_record(self.manifest, "User", [1, "a"])
        self.assertGreater(len(core.mfdb_core_get_debug_log(self.manifest)), 0)
        core.mfdb_core_disable_debug(self.manifest)
        before = len(core.mfdb_core_get_debug_log(self.manifest))
        core.mfdb_core_add_entity_record(self.manifest, "User", [2, "b"])
        self.assertEqual(len(core.mfdb_core_get_debug_log(self.manifest)), before)


if __name__ == "__main__":
    unittest.main()
