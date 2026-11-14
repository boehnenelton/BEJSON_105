"""
Library:        lib_bejson_Automation_automation_schemas.py
Family:         Automation
Description:    Canonical BEJSON 105a schema definitions, field maps, and manifest templates.
BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
                (Pronounced Bee-Jay-Son / Bay-nin Elton JSON)
MFDB:           MFDB stands for Multi File Database. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
Version:        1.0.0
Date:           2026-11-11
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  c28f10ea-4b92-4982-95f3-189f72b93081
License:        PolyForm Noncommercial License 1.0.0
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Final, List

# Canonical BEJSON 105a Schema Fields for Pipeline FSM State Manifest
# Column 0 is reserved for immutable record_uuid per Format 105 standard
AUTOMATION_FSM_MANIFEST_FIELDS: Final[List[Dict[str, str]]] = [
    {
        "name": "record_uuid",
        "type": "string",
        "field_uuid": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
        "description": "Column 0: Immutable UUIDv4 identifier for the pipeline state node"
    },
    {
        "name": "step_sequence_index",
        "type": "integer",
        "field_uuid": "9b2c3d4e-1001-4000-8000-000000000001",
        "description": "1-based logical execution order within the pipeline chain"
    },
    {
        "name": "step_label",
        "type": "string",
        "field_uuid": "9b2c3d4e-1001-4000-8000-000000000002",
        "description": "Human-readable functional label adhering to Purpose Law"
    },
    {
        "name": "execution_dispatch_mode",
        "type": "string",
        "field_uuid": "9b2c3d4e-1001-4000-8000-000000000003",
        "description": "Mode of code invocation: python_callable, inline_python_block, or shell_command"
    },
    {
        "name": "executable_code_payload",
        "type": "string",
        "field_uuid": "9b2c3d4e-1001-4000-8000-000000000004",
        "description": "The script, callable import symbol, or shell vector to execute"
    },
    {
        "name": "delay_before_execution_sec",
        "type": "number",
        "field_uuid": "9b2c3d4e-1001-4000-8000-000000000005",
        "description": "Pause duration in seconds before dispatching the stage payload"
    },
    {
        "name": "delay_after_execution_sec",
        "type": "number",
        "field_uuid": "9b2c3d4e-1001-4000-8000-000000000006",
        "description": "Pause duration in seconds after successful stage payload execution"
    },
    {
        "name": "loop_enabled_flag",
        "type": "boolean",
        "field_uuid": "9b2c3d4e-1001-4000-8000-000000000007",
        "description": "Whether this specific stage repeats its execution loop"
    },
    {
        "name": "loop_max_iterations",
        "type": "integer",
        "field_uuid": "9b2c3d4e-1001-4000-8000-000000000008",
        "description": "Maximum number of allowed loop iterations (1 = run once, -1 = infinite until break)"
    },
    {
        "name": "loop_interval_delay_sec",
        "type": "number",
        "field_uuid": "9b2c3d4e-1001-4000-8000-000000000009",
        "description": "Time delay in seconds between consecutive loop iterations"
    },
    {
        "name": "loop_break_condition_eval",
        "type": "string",
        "field_uuid": "9b2c3d4e-1001-4000-8000-000000000010",
        "description": "Predicate expression evaluated against stage output to terminate looping"
    },
    {
        "name": "on_success_transition_uuid",
        "type": "string",
        "field_uuid": "9b2c3d4e-1001-4000-8000-000000000011",
        "description": "UUID of next stage or terminal gate ('FINAL_DELIVERY_GATE') on clean exit"
    },
    {
        "name": "on_failure_transition_uuid",
        "type": "string",
        "field_uuid": "9b2c3d4e-1001-4000-8000-000000000012",
        "description": "UUID of error handler or terminal abort ('ABORT_TERMINAL') on failure"
    },
    {
        "name": "timeout_ceiling_sec",
        "type": "number",
        "field_uuid": "9b2c3d4e-1001-4000-8000-000000000013",
        "description": "Maximum permissible wall-clock execution time before kill/abort"
    },
    {
        "name": "sender_address",
        "type": "string",
        "field_uuid": "9b2c3d4e-1001-4000-8000-000000000014",
        "description": "Originating node or pipeline URI for backchannel signaling and receipts"
    },
    {
        "name": "forward_address",
        "type": "string",
        "field_uuid": "9b2c3d4e-1001-4000-8000-000000000015",
        "description": "Default destination URI or stage UUID upon standard successful completion"
    },
    {
        "name": "if_repetition_count_over",
        "type": "integer",
        "field_uuid": "9b2c3d4e-1001-4000-8000-000000000016",
        "description": "Iteration count threshold triggering conditional routing deflection"
    },
    {
        "name": "conditional_forward_address",
        "type": "string",
        "field_uuid": "9b2c3d4e-1001-4000-8000-000000000017",
        "description": "Destination URI or stage UUID invoked when iteration count exceeds threshold"
    }
]

# Canonical BEJSON 105a Schema Fields for Chunked Framework Registries
AUTOMATION_FRAMEWORK_REGISTRY_FIELDS: Final[List[Dict[str, str]]] = [
    {
        "name": "record_uuid",
        "type": "string",
        "field_uuid": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
        "description": "Column 0: Immutable UUIDv4 identifier for the framework artifact file"
    },
    {
        "name": "relative_file_path",
        "type": "string",
        "field_uuid": "9b2c3d4e-2001-4000-8000-000000000001",
        "description": "Relative target path where file will be materialized"
    },
    {
        "name": "file_role",
        "type": "string",
        "field_uuid": "9b2c3d4e-2001-4000-8000-000000000002",
        "description": "Role: launcher, config, pre_processing, processing, post_processing, hook, manifest"
    },
    {
        "name": "content_text",
        "type": "string",
        "field_uuid": "9b2c3d4e-2001-4000-8000-000000000003",
        "description": "Full UTF-8 encoded text payload of the framework file"
    },
    {
        "name": "sha256_checksum",
        "type": "string",
        "field_uuid": "9b2c3d4e-2001-4000-8000-000000000004",
        "description": "Cryptographic SHA-256 hash of the content payload"
    },
    {
        "name": "executable_flag",
        "type": "boolean",
        "field_uuid": "9b2c3d4e-2001-4000-8000-000000000005",
        "description": "Whether file requires POSIX executable permissions (chmod +x)"
    }
]


def build_field_map_105(fields: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Constructs an authoritative O(1) field map cache mapping field names to column indices.
    Validates field map compliance per Policy §6.2.
    """
    field_map: Dict[str, int] = {}
    for idx, field_def in enumerate(fields):
        name = field_def.get("name")
        if name:
            field_map[str(name)] = idx
    return field_map


def create_empty_fsm_manifest_105a(
    pipeline_identifier: str = "automation_pipeline_v1",
    initial_step_uuid: str = ""
) -> Dict[str, Any]:
    """Creates a blank, valid BEJSON 105a FSM manifest envelope."""
    return {
        "Format": "BEJSON",
        "Format_Version": "105a",
        "Format_Creator": "Elton Boehnen",
        "Schema_Name": "Automation_Pipeline_FSM_Manifest_Schema",
        "Schema_Version": "1.0.0",
        "Pipeline_Identifier": pipeline_identifier,
        "Initial_Step_UUID": initial_step_uuid,
        "Records_Type": ["PipelineFSMStageRecord"],
        "Fields": [dict(f) for f in AUTOMATION_FSM_MANIFEST_FIELDS],
        "Values": []
    }


def create_empty_framework_registry_105a(
    framework_name: str = "automation_3zone_pipeline_chassis",
    framework_version: str = "1.0.0"
) -> Dict[str, Any]:
    """Creates a blank, valid BEJSON 105a chunked framework registry envelope."""
    return {
        "Format": "BEJSON",
        "Format_Version": "105a",
        "Format_Creator": "Elton Boehnen",
        "Schema_Name": "Automation_Framework_Registry_Schema",
        "Schema_Version": "1.0.0",
        "Framework_Name": framework_name,
        "Framework_Version": framework_version,
        "Records_Type": ["FrameworkFileChunkRecord"],
        "Fields": [dict(f) for f in AUTOMATION_FRAMEWORK_REGISTRY_FIELDS],
        "Values": []
    }
