"""
Test Suite:     test_lib_bejson_Automation_core.py
Family:         Automation
Description:    Unit tests for BEJSON Automation FSM core, validator, and framework chunk exporter.
Author:         Elton Boehnen · boehnenelton2024@gmail.com
License:        PolyForm Noncommercial License 1.0.0
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

# Link to Automation library
_LIB_DIR = Path(__file__).resolve().parent.parent
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from lib_bejson_Automation_automation_core import (
    BEJSONAutomationFSM,
    FSMExecutionContext,
    export_automation_framework_registry,
    scaffold_pipeline_from_registry,
)
from lib_bejson_Automation_automation_errors import (
    EXIT_OK,
    EXIT_PARTIAL_FAILURE,
    AutomationSchemaValidationError,
)
from lib_bejson_Automation_automation_schemas import (
    create_empty_fsm_manifest_105a,
)
from lib_bejson_Automation_automation_validator import (
    validate_framework_registry_barrier,
    validate_fsm_manifest_barrier,
)


class TestAutomationFSMCore(unittest.TestCase):

    def setUp(self) -> None:
        self.temp_dir = Path("/data/data/com.termux/files/home/.gemini/antigravity-cli/brain/f43c3c01-3bb1-4cbe-9116-aedefdb63578/scratch/fsm_tests")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_empty_manifest_validation(self) -> None:
        doc = create_empty_fsm_manifest_105a("test_pipe", "step_001")
        is_valid, errors = validate_fsm_manifest_barrier(doc)
        self.assertTrue(is_valid, f"Validation failed: {errors}")

    def test_framework_export_and_scaffold(self) -> None:
        reg_path = self.temp_dir / "framework_registry.105a.bejson"
        reg_doc = export_automation_framework_registry(reg_path)
        self.assertTrue(reg_path.exists())

        is_valid, errors = validate_framework_registry_barrier(reg_doc)
        self.assertTrue(is_valid, f"Registry invalid: {errors}")

        target_pipe = self.temp_dir / "scaffolded_pipe"
        created = scaffold_pipeline_from_registry(reg_doc, target_pipe)
        self.assertGreaterEqual(len(created), 6)
        self.assertTrue((target_pipe / "launcher.py").exists())
        self.assertTrue((target_pipe / "routing" / "pipeline_fsm_manifest.105a.bejson").exists())

    def test_fsm_row_by_row_execution(self) -> None:
        reg_doc = export_automation_framework_registry()
        pipe_dir = self.temp_dir / "exec_pipe"
        scaffold_pipeline_from_registry(reg_doc, pipe_dir)

        manifest_path = pipe_dir / "routing" / "pipeline_fsm_manifest.105a.bejson"
        staged_dir = pipe_dir / "staged"
        asset_file = staged_dir / "document.txt"
        asset_file.write_text("Test Payload Content", encoding="utf-8")

        fsm = BEJSONAutomationFSM(manifest_path)
        ctx = FSMExecutionContext("test_pipe", asset_file, staged_dir)
        result = fsm.execute_pipeline(ctx)

        self.assertTrue(result.success)
        self.assertEqual(result.exit_code, EXIT_OK)
        self.assertEqual(result.terminal_disposition, "FINAL_DELIVERY_GATE")


if __name__ == "__main__":
    unittest.main()
