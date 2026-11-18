#!/usr/bin/env python3
"""
Name:           test_workflow_state_engine.py
Description:    Unit and conformance test suite for BEJSON 104a workflow
                state engine, skill chaining checkpoints, and long-running job persistence.
Version:        100
Date Created:   2026-11-08
Author Credit:  Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  2e9b14c8-4a7f-4c3d-9b1a-8e2d7f3a9b01
"""

from __future__ import annotations

import sys
if sys.version_info < (3, 10):
    sys.stderr.write("test_workflow_state_engine requires Python 3.10 or newer.\n")
    sys.exit(20)

import os
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

CURRENT_SCRIPT_DIR_PATH: Path = Path(__file__).resolve().parent
PROJECT_ROOT_DIR_PATH: Path = CURRENT_SCRIPT_DIR_PATH.parent
LIB_DIR_PATH: Path = PROJECT_ROOT_DIR_PATH / "lib"

if str(LIB_DIR_PATH) not in sys.path:
    sys.path.insert(0, str(LIB_DIR_PATH))

from workflow_state_engine import (
    WorkflowStateManager,
    WorkflowStageDefinition,
    RestoredWorkflowContext,
    load_bejson_state_document,
    get_bejson_field_map_cache,
    calculate_file_sha256_digest,
    calculate_composite_artifacts_digest
)


class TestWorkflowStateEngine(unittest.TestCase):
    """Test suite verifying standardized BEJSON state persistence and restoration."""

    def setUp(self) -> None:
        self.temporary_test_directory: Path = Path(tempfile.mkdtemp(prefix="test_bejson_state_"))
        self.state_file_path: Path = self.temporary_test_directory / "test_workflow_state.104a.bejson"
        self.state_manager = WorkflowStateManager(self.state_file_path)

        self.mock_stage_definitions_list: List[WorkflowStageDefinition] = [
            WorkflowStageDefinition(
                stage_skill_canonical_name="mock-planner-skill",
                stage_phase_description="Mock Architecture Planning Phase",
                stage_input_parameters_payload={"target_domain": "web_portal"}
            ),
            WorkflowStageDefinition(
                stage_skill_canonical_name="mock-builder-skill",
                stage_phase_description="Mock Component Synthesis Phase",
                stage_input_parameters_payload={"target_engine": "behtml"}
            ),
            WorkflowStageDefinition(
                stage_skill_canonical_name="mock-auditor-skill",
                stage_phase_description="Mock Verification Audit Phase",
                stage_input_parameters_payload={"strict_mode": True}
            )
        ]

    def tearDown(self) -> None:
        if self.temporary_test_directory.exists():
            shutil.rmtree(self.temporary_test_directory, ignore_errors=True)

    def test_bejson_104a_initialization(self) -> None:
        """Verifies correct BEJSON 104a header keys, fields, and record values upon initialization."""
        document_state: Dict[str, Any] = self.state_manager.initialize_new_workflow(
            workflow_pipeline_name="Unit Test Pipeline",
            workflow_goal_description="Verify workflow state engine capabilities.",
            stage_definitions_list=self.mock_stage_definitions_list,
            initial_shared_context={"test_key": "test_value"}
        )

        self.assertEqual(document_state["Format"], "BEJSON")
        self.assertEqual(document_state["Format_Version"], "104a")
        self.assertEqual(document_state["Format_Creator"], "Elton Boehnen")
        self.assertEqual(document_state["workflow_lifecycle_status"], "INITIALIZED")
        self.assertEqual(document_state["total_stages_count"], 3)
        self.assertEqual(document_state["active_stage_index"], 1)
        self.assertEqual(len(document_state["Values"]), 3)

        # Verify field map cache mandate
        field_map_cache: Dict[str, int] = get_bejson_field_map_cache(document_state)
        first_row: List[Any] = document_state["Values"][0]
        self.assertEqual(first_row[field_map_cache["stage_sequence_order_index"]], 1)
        self.assertEqual(first_row[field_map_cache["stage_skill_canonical_name"]], "mock-planner-skill")
        self.assertEqual(first_row[field_map_cache["stage_lifecycle_state"]], "PENDING")

    def test_checkpoint_and_atomic_write(self) -> None:
        """Verifies checkpointing updates stage row with SHA-256 and leaves no stray temp files."""
        self.state_manager.initialize_new_workflow(
            workflow_pipeline_name="Unit Test Pipeline",
            workflow_goal_description="Verify atomic checkpointing.",
            stage_definitions_list=self.mock_stage_definitions_list
        )

        test_artifact_path: Path = self.temporary_test_directory / "output_artifact.txt"
        with open(test_artifact_path, "w", encoding="utf-8") as file_stream:
            file_stream.write("Artifact test payload content.")

        updated_document: Dict[str, Any] = self.state_manager.checkpoint_stage_execution(
            stage_sequence_order_index=1,
            stage_output_result_payload={"result_data": "pass"},
            stage_produced_artifacts_manifest=[str(test_artifact_path)],
            shared_context_delta_payload={"step_1_done": True},
            stage_gate_audit_passed_flag=True,
            stage_execution_duration_milliseconds=42
        )

        field_map_cache: Dict[str, int] = get_bejson_field_map_cache(updated_document)
        first_row: List[Any] = updated_document["Values"][0]
        self.assertEqual(first_row[field_map_cache["stage_lifecycle_state"]], "VERIFIED")
        self.assertTrue(first_row[field_map_cache["stage_gate_audit_passed_flag"]])
        self.assertEqual(first_row[field_map_cache["stage_execution_duration_milliseconds"]], 42)

        recorded_sha256: str = first_row[field_map_cache["stage_checkpoint_sha256_digest"]]
        expected_sha256: str = calculate_composite_artifacts_digest([str(test_artifact_path)])
        self.assertEqual(recorded_sha256, expected_sha256)

        # Verify next active stage index
        self.assertEqual(updated_document["active_stage_index"], 2)
        self.assertEqual(updated_document["shared_context_state_payload"]["step_1_done"], True)

        # Check for zero stray .tmp files
        temporary_files: List[Path] = list(self.temporary_test_directory.glob(".tmp_*"))
        self.assertEqual(len(temporary_files), 0)

    def test_pause_and_restore_lifecycle(self) -> None:
        """Verifies pausing workflow, recording pause reason, and restoring full context."""
        self.state_manager.initialize_new_workflow(
            workflow_pipeline_name="Pause and Restore Lifecycle Test",
            workflow_goal_description="Verify pause and restore execution.",
            stage_definitions_list=self.mock_stage_definitions_list,
            contextualize_plan_flag=True,
            contextualize_last_flag=True
        )

        # Checkpoint stage 1
        test_artifact_path: Path = self.temporary_test_directory / "step1.json"
        with open(test_artifact_path, "w", encoding="utf-8") as file_stream:
            json.dump({"manifest": "ready"}, file_stream)

        self.state_manager.checkpoint_stage_execution(
            stage_sequence_order_index=1,
            stage_output_result_payload={"spec_version": "1.0"},
            stage_produced_artifacts_manifest=[str(test_artifact_path)],
            shared_context_delta_payload={"contract_signed": True}
        )

        # Pause workflow
        paused_document: Dict[str, Any] = self.state_manager.pause_workflow("User requested pause after step 1.")
        self.assertEqual(paused_document["workflow_lifecycle_status"], "PAUSED")
        self.assertEqual(paused_document["shared_context_state_payload"]["_pause_reason"], "User requested pause after step 1.")

        # Restore workflow
        restored_context: RestoredWorkflowContext = self.state_manager.restore_workflow()
        self.assertEqual(restored_context.workflow_lifecycle_status, "RESUMED")
        self.assertEqual(restored_context.active_stage_index, 2)
        self.assertEqual(len(restored_context.completed_stages_summary_list), 1)
        self.assertEqual(restored_context.completed_stages_summary_list[0]["stage_skill_name"], "mock-planner-skill")
        self.assertIsNotNone(restored_context.active_stage_definition)
        self.assertEqual(restored_context.active_stage_definition["stage_skill_canonical_name"], "mock-builder-skill")
        self.assertEqual(restored_context.last_verified_output_payload, {"spec_version": "1.0"})
        self.assertEqual(restored_context.shared_context_state_payload["contract_signed"], True)

    def test_stage_gate_audit_failure_handling(self) -> None:
        """Verifies that an audit failure marks stage as FAILED and halts progression."""
        self.state_manager.initialize_new_workflow(
            workflow_pipeline_name="Audit Failure Test",
            workflow_goal_description="Verify audit failure halts workflow.",
            stage_definitions_list=self.mock_stage_definitions_list
        )

        failed_document: Dict[str, Any] = self.state_manager.checkpoint_stage_execution(
            stage_sequence_order_index=1,
            stage_output_result_payload={"error": "Syntax violation"},
            stage_produced_artifacts_manifest=[],
            stage_gate_audit_passed_flag=False,
            stage_gate_audit_fail_reason="Schema validation failed on line 14"
        )

        field_map_cache: Dict[str, int] = get_bejson_field_map_cache(failed_document)
        first_row: List[Any] = failed_document["Values"][0]

        self.assertEqual(first_row[field_map_cache["stage_lifecycle_state"]], "FAILED")
        self.assertFalse(first_row[field_map_cache["stage_gate_audit_passed_flag"]])
        self.assertEqual(first_row[field_map_cache["stage_gate_audit_fail_reason"]], "Schema validation failed on line 14")
        self.assertEqual(failed_document["workflow_lifecycle_status"], "FAILED")
        # Active stage index remains 1 because it failed and must be remediated
        self.assertEqual(failed_document["active_stage_index"], 1)


if __name__ == "__main__":
    unittest.main()
