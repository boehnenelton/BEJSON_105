"""
File Name : test_cms_mtv.py
Rel. Path : Lib_PY/CMS/tests/test_cms_mtv.py
Purpose   : Comprehensive unit tests for lib_bejson_CMS MTV Scaffolding Engine.
VERSION   : 1.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : 5b281f9a-6c3e-4d81-8720-31e9c8a02d41
Run       : python3 Lib_PY/CMS/tests/test_cms_mtv.py
"""

import os
import sys
import shutil
import tempfile
import unittest
import subprocess
from pathlib import Path

# Add Lib_PY and CMS family to path
TEST_DIR = Path(__file__).resolve().parent
CMS_DIR = TEST_DIR.parent
LIB_PY_DIR = CMS_DIR.parent

for candidate_dir in (str(CMS_DIR), str(LIB_PY_DIR), str(LIB_PY_DIR / "Core")):
    if candidate_dir not in sys.path:
        sys.path.insert(0, candidate_dir)

import lib_bejson_CMS_mtv_core as mtv_core
import lib_bejson_CMS_mtv_scaffold as mtv_scaffold
import lib_bejson_CMS_mtv_validator as mtv_validator


class TestCMSMTVCore(unittest.TestCase):
    def test_list_and_get_archetypes(self):
        archetypes = mtv_core.bejson_cms_list_archetypes()
        self.assertEqual(len(archetypes), 4)
        arch_ids = {a["archetype_id"] for a in archetypes}
        self.assertEqual(arch_ids, {"video_hub", "documentation", "editorial", "portfolio"})

        video_hub = mtv_core.bejson_cms_get_archetype("video_hub")
        self.assertEqual(video_hub["archetype_name"], "Video Streaming & Media Hub")
        self.assertIn("Category", [e["entity_name"] for e in video_hub["entities"]])

    def test_field_descriptor_synthesis(self):
        desc = mtv_core.bejson_105_construct_field_descriptor(
            field_name_identifier="page_title",
            field_primitive_type="string",
            field_description_text="Article title"
        )
        self.assertEqual(desc["name"], "page_title")
        self.assertEqual(desc["type"], "string")
        self.assertTrue(mtv_core.UUID4_PATTERN_REGEX.match(desc["field_uuid"]))

    def test_invalid_field_name_rejected(self):
        with self.assertRaises(ValueError):
            mtv_core.bejson_105_construct_field_descriptor("Invalid-Field-Name", "string")

    def test_field_map_cache(self):
        sample_doc = {
            "Fields": [
                {"name": "record_uuid", "type": "string"},
                {"name": "cat_name", "type": "string"},
                {"name": "cat_order", "type": "integer"}
            ]
        }
        fmap = mtv_core.bejson_105_get_field_map(sample_doc)
        self.assertEqual(fmap["record_uuid"], 0)
        self.assertEqual(fmap["cat_name"], 1)
        self.assertEqual(fmap["cat_order"], 2)


class TestCMSMTVSynthesizer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="cms_mtv_test_")
        self.project_path = Path(self.temp_dir) / "test_video_hub"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_end_to_end_scaffold_video_hub(self):
        synthesizer = mtv_scaffold.MTVScaffoldSynthesizer(self.project_path)
        report = synthesizer.instantiate_archetype_scaffold("video_hub", "Test Video Portal")

        self.assertEqual(report["status"], "success")
        self.assertTrue(self.project_path.exists())

        # Check Model ($M$)
        manifest_file = self.project_path / "storage" / "mfdb" / "105a.mfdb.bejson"
        self.assertTrue(manifest_file.exists())
        category_table = self.project_path / "storage" / "mfdb" / "data" / "category.105.bejson"
        self.assertTrue(category_table.exists())

        # Check Template ($T$)
        template_file = self.project_path / "templates" / "scaffold_video_player.html"
        self.assertTrue(template_file.exists())
        master_index = self.project_path / "templates" / "scaffold_master_index.html"
        self.assertTrue(master_index.exists())

        # Check View ($V$)
        build_script = self.project_path / "build_site.py"
        self.assertTrue(build_script.exists())

        # Execute standalone build_site.py
        proc = subprocess.run([sys.executable, str(build_script)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"build_site.py failed: {proc.stderr}")
        dist_index = self.project_path / "dist" / "index.html"
        self.assertTrue(dist_index.exists())

        # Run MTV Validator
        validation = mtv_validator.validate_mtv_project_scaffold(self.project_path)
        self.assertTrue(validation["passed"], f"Validation failed: {validation['problems']}")

    def test_end_to_end_scaffold_documentation(self):
        doc_project_path = Path(self.temp_dir) / "test_docs_hub"
        synthesizer = mtv_scaffold.MTVScaffoldSynthesizer(doc_project_path)
        report = synthesizer.instantiate_archetype_scaffold("documentation", "Docs Manual")

        self.assertEqual(report["status"], "success")
        validation = mtv_validator.validate_mtv_project_scaffold(doc_project_path)
        self.assertTrue(validation["passed"], f"Validation failed: {validation['problems']}")

    def test_end_to_end_scaffold_editorial(self):
        edit_project_path = Path(self.temp_dir) / "test_editorial_pub"
        synthesizer = mtv_scaffold.MTVScaffoldSynthesizer(edit_project_path)
        report = synthesizer.instantiate_archetype_scaffold("editorial", "Editorial Publication")

        self.assertEqual(report["status"], "success")
        validation = mtv_validator.validate_mtv_project_scaffold(edit_project_path)
        self.assertTrue(validation["passed"], f"Validation failed: {validation['problems']}")

    def test_end_to_end_scaffold_portfolio(self):
        port_project_path = Path(self.temp_dir) / "test_portfolio_showcase"
        synthesizer = mtv_scaffold.MTVScaffoldSynthesizer(port_project_path)
        report = synthesizer.instantiate_archetype_scaffold("portfolio", "Portfolio Showcase")

        self.assertEqual(report["status"], "success")
        validation = mtv_validator.validate_mtv_project_scaffold(port_project_path)
        self.assertTrue(validation["passed"], f"Validation failed: {validation['problems']}")


if __name__ == "__main__":
    unittest.main()
