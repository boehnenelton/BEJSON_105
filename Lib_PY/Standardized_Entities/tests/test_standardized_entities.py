"""
File Name      : test_standardized_entities.py
Rel. Path      : Lib_PY/Standardized_Entities/tests/test_standardized_entities.py
Description    : Comprehensive test suite for Standardized_Entities Core and Validator modules.
Version        : 1.0.0
Date Created   : 2026-11-20
Author Credit  : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
License        : PolyForm Noncommercial License 1.0.0 (PolyForm-Noncommercial-1.0.0)
RELATIONAL_ID  : b5d9f213-4c8e-4d02-a761-9e3b2d1a5f02
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime

# Path resolution: add Standardized_Entities and Core to sys.path
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SE_DIR = os.path.normpath(os.path.join(_TESTS_DIR, ".."))
_LIB_PY = os.path.normpath(os.path.join(_SE_DIR, ".."))
_CORE_DIR = os.path.join(_LIB_PY, "Core")

for p in (_SE_DIR, _CORE_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from lib_bejson_Core_mfdb_core import mfdb_core_add_entity_record_105
from lib_bejson_Standardized_Entities_core import (
    SE_CONTEXT_MODES,
    SE_TIMESTAMP_FORMAT,
    SE_VALUE_TYPES,
    STANDARDIZED_ENTITY_FIELDS,
    se_core_add_record,
    se_core_build_fields,
    se_core_build_record,
    se_core_deploy_database,
    se_core_parse_entity_name,
    se_core_update_record,
    se_core_write_entity,
)
from lib_bejson_Standardized_Entities_validator import (
    se_validator_validate_database,
    se_validator_validate_entity,
    se_validator_validate_schema,
)


class TestStandardizedEntities(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_se_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_entity_name_parsing(self):
        self.assertEqual(se_core_parse_entity_name("URL_Cloudflare_Site"), ("URL", "Cloudflare_Site"))
        self.assertEqual(se_core_parse_entity_name("Environment_Secure"), ("Environment", "Secure"))
        self.assertEqual(se_core_parse_entity_name("App_Config_Dev_Test"), ("App", "Config_Dev_Test"))

        with self.assertRaises(ValueError):
            se_core_parse_entity_name("InvalidName")
        with self.assertRaises(ValueError):
            se_core_parse_entity_name("_LeadingUnderscore")
        with self.assertRaises(ValueError):
            se_core_parse_entity_name("TrailingUnderscore_")
        with self.assertRaises(ValueError):
            se_core_parse_entity_name("Invalid-Hyphen_Cat")

    def test_build_fields(self):
        fields = se_core_build_fields()
        self.assertEqual(len(fields), 14)
        for idx, (exp_name, exp_type, _, _) in enumerate(STANDARDIZED_ENTITY_FIELDS):
            self.assertEqual(fields[idx]["name"], exp_name)
            self.assertEqual(fields[idx]["type"], exp_type)

    def test_build_record_invariants(self):
        row = se_core_build_record(
            "URL_Cloudflare_Site",
            key="CF_SITE",
            label="My Site",
            value="https://example.com",
            value_type="url",
            details="Site details",
            tags=["site", "cloudflare"],
            flags=["production"],
            context_mode="inject",
            is_active=True,
            sender="admin",
        )
        self.assertEqual(len(row), 14)
        self.assertEqual(row[0], "CF_SITE")
        self.assertEqual(row[1], "My Site")
        self.assertEqual(row[2], "https://example.com")
        self.assertEqual(row[3], "url")
        self.assertEqual(row[4], "URL")
        self.assertEqual(row[5], "Cloudflare_Site")
        self.assertEqual(row[6], "Site details")
        self.assertEqual(row[7], ["site", "cloudflare"])
        self.assertEqual(row[8], ["production"])
        self.assertEqual(row[9], "inject")
        self.assertEqual(row[10], True)
        self.assertIsInstance(row[11], str)  # created_at
        self.assertIsNone(row[12])           # updated_at
        self.assertEqual(row[13], "admin")   # sender

        # Test invalid value_type
        with self.assertRaises(ValueError):
            se_core_build_record("URL_Site", "K", "L", "V", value_type="invalid_type")

        # Test invalid context_mode
        with self.assertRaises(ValueError):
            se_core_build_record("URL_Site", "K", "L", "V", context_mode="super_hidden")

        # Test invalid is_active type
        with self.assertRaises(TypeError):
            se_core_build_record("URL_Site", "K", "L", "V", is_active="true")

        # Test unknown kwargs
        with self.assertRaises(ValueError):
            se_core_build_record("URL_Site", "K", "L", "V", unknown_field="test")

    def test_deploy_database_and_validation(self):
        db_root = os.path.join(self.temp_dir, "registry_db")
        entities = ["URL_Cloudflare_Site", "URL_Youtube"]
        manifest_path = se_core_deploy_database(db_root, "TestRegistry", entities)

        self.assertTrue(os.path.isfile(manifest_path))

        # Check manifest MFDB_Version == "1.40"
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_doc = json.load(f)
        self.assertEqual(manifest_doc.get("MFDB_Version"), "1.40")

        # Validate database via validator
        val_report = se_validator_validate_database(manifest_path, strict_fk=True)
        self.assertTrue(val_report["passed"], f"Validation failed: {val_report['errors']}")
        self.assertEqual(sorted(val_report["entities"]), sorted(entities))

    def test_write_entity_to_existing_database(self):
        db_root = os.path.join(self.temp_dir, "registry_db")
        manifest_path = se_core_deploy_database(db_root, "TestRegistry", ["URL_Cloudflare_Site"])

        # Add another entity
        new_entity_path = se_core_write_entity(manifest_path, "URL_Substack", description="Substack articles")
        self.assertTrue(os.path.isfile(new_entity_path))

        # Duplicate entity write should fail
        with self.assertRaises(ValueError):
            se_core_write_entity(manifest_path, "URL_Substack")

        # Database should validate cleanly with both entities
        val_report = se_validator_validate_database(manifest_path)
        self.assertTrue(val_report["passed"], f"Errors: {val_report['errors']}")
        self.assertIn("URL_Substack", val_report["entities"])

    def test_crud_records_and_invariants(self):
        db_root = os.path.join(self.temp_dir, "registry_db")
        manifest_path = se_core_deploy_database(db_root, "TestRegistry", ["URL_Cloudflare_Site"])

        # Insert record via se_core_add_record
        rec_uuid1 = se_core_add_record(
            manifest_path,
            "URL_Cloudflare_Site",
            key="CF_HOME",
            label="Home Page",
            value="https://home.example.com",
            details="Primary homepage",
            tags=["home", "cloudflare"],
        )
        self.assertTrue(isinstance(rec_uuid1, str) and len(rec_uuid1) == 36)

        # Reject duplicate key
        with self.assertRaises(ValueError):
            se_core_add_record(
                manifest_path,
                "URL_Cloudflare_Site",
                key="CF_HOME",
                label="Home Page Duplicate",
                value="https://home2.example.com",
            )

        # Insert record via se_core_build_record + mfdb_core_add_entity_record_105
        row2 = se_core_build_record(
            "URL_Cloudflare_Site",
            key="CF_BLOG",
            label="Blog Page",
            value="https://blog.example.com",
        )
        doc = mfdb_core_add_entity_record_105(manifest_path, "URL_Cloudflare_Site", row2)
        rec_uuid2 = doc["Values"][-1][0]
        self.assertNotEqual(rec_uuid1, rec_uuid2)

        # Update record via se_core_update_record
        se_core_update_record(
            manifest_path,
            "URL_Cloudflare_Site",
            rec_uuid1,
            changes={"details": "Updated homepage description", "value_type": "url"},
            sender="lead_dev",
        )

        # Verify updated values and updated_at stamp
        entity_path = os.path.join(db_root, "data", "url_cloudflare_site.bejson")
        with open(entity_path, "r", encoding="utf-8") as f:
            ent_doc = json.load(f)

        row_map = {r[0]: r for r in ent_doc["Values"]}
        updated_row = row_map[rec_uuid1]
        self.assertEqual(updated_row[7], "Updated homepage description")  # details
        self.assertEqual(updated_row[4], "url")                          # value_type
        self.assertEqual(updated_row[14], "lead_dev")                   # sender
        self.assertIsNotNone(updated_row[13])                           # updated_at

        # Verify whole DB validates cleanly
        val_report = se_validator_validate_database(manifest_path)
        self.assertTrue(val_report["passed"], f"Errors: {val_report['errors']}")

    def test_validator_rejects_corrupted_data(self):
        db_root = os.path.join(self.temp_dir, "registry_db")
        manifest_path = se_core_deploy_database(db_root, "TestRegistry", ["URL_Youtube"])

        se_core_add_record(
            manifest_path,
            "URL_Youtube",
            key="YT_CHANNEL",
            label="Channel",
            value="https://youtube.com/channel",
        )

        entity_path = os.path.join(db_root, "data", "url_youtube.bejson")
        with open(entity_path, "r", encoding="utf-8") as f:
            doc = json.load(f)

        # 1. Corrupt domain
        doc_corrupt = json.loads(json.dumps(doc))
        doc_corrupt["Values"][0][5] = "WrongDomain"
        res = se_validator_validate_entity(doc_corrupt, is_file=False)
        self.assertFalse(res["passed"])
        self.assertTrue(any("does not match entity domain" in e for e in res["errors"]))

        # 2. Corrupt value_type enum
        doc_corrupt = json.loads(json.dumps(doc))
        doc_corrupt["Values"][0][4] = "invalid_enum"
        res = se_validator_validate_entity(doc_corrupt, is_file=False)
        self.assertFalse(res["passed"])
        self.assertTrue(any("invalid value_type" in e for e in res["errors"]))

        # 3. Missing field in Fields
        doc_corrupt = json.loads(json.dumps(doc))
        doc_corrupt["Fields"].pop()
        res = se_validator_validate_entity(doc_corrupt, is_file=False)
        self.assertFalse(res["passed"])
        self.assertTrue(any("Fields length mismatch" in e for e in res["errors"]))


if __name__ == "__main__":
    unittest.main()
