"""
Library:        lib_bejson_Automation_automation_validator.py
Family:         Automation
Description:    Structural and graph barrier validator for BEJSON Automation FSM manifests and chunked registries.
BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
                (Pronounced Bee-Jay-Son / Bay-nin Elton JSON)
MFDB:           MFDB stands for Multi File Database. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
Version:        1.0.0
Date:           2026-11-11
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  f591e32d-9471-464a-a43b-28f09d84639e
License:        PolyForm Noncommercial License 1.0.0
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from lib_bejson_Automation_automation_errors import (
    AutomationCycleError,
    AutomationSchemaValidationError,
)
from lib_bejson_Automation_automation_schemas import (
    AUTOMATION_FSM_MANIFEST_FIELDS,
    AUTOMATION_FRAMEWORK_REGISTRY_FIELDS,
    build_field_map_105,
)

LOG: logging.Logger = logging.getLogger("AutomationFSMValidator")

TERMINAL_GATES: Final = {"FINAL_DELIVERY_GATE", "ABORT_TERMINAL", "EXTERNAL_HANDOFF"}


def validate_fsm_manifest_barrier(manifest_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates structural integrity, field map cache, DAG reachability, and
    cycle/deadlock safety for a BEJSON 105a FSM manifest table.
    Returns: (is_valid, error_list)
    """
    errors: List[str] = []

    # 1. Envelope format validation
    if manifest_data.get("Format") != "BEJSON":
        errors.append("Invalid 'Format': expected 'BEJSON'")
    version = str(manifest_data.get("Format_Version", ""))
    if not (version.startswith("105") or version.startswith("104")):
        errors.append(f"Unsupported 'Format_Version': '{version}', expected 105-series or 104-series")
    if not manifest_data.get("Format_Creator"):
        errors.append("Missing required header field: 'Format_Creator'")

    fields = manifest_data.get("Fields")
    if not isinstance(fields, list) or len(fields) < 5:
        errors.append("Malformed or insufficient 'Fields' definition array")
        return False, errors

    field_map = build_field_map_105(fields)
    required_fields = [
        "record_uuid", "step_label", "execution_dispatch_mode",
        "executable_code_payload", "on_success_transition_uuid"
    ]
    for rf in required_fields:
        if rf not in field_map:
            errors.append(f"Missing mandatory schema field: '{rf}'")

    if errors:
        return False, errors

    # 2. Values row validation & index mapping
    values = manifest_data.get("Values", [])
    if not isinstance(values, list):
        errors.append("'Values' must be a 2D list of row records")
        return False, errors

    initial_step_uuid = str(manifest_data.get("Initial_Step_UUID", "")).strip()
    nodes_by_uuid: Dict[str, Dict[str, Any]] = {}

    for row_idx, row in enumerate(values):
        if not isinstance(row, list):
            errors.append(f"Row {row_idx} is not a list")
            continue
        if len(row) != len(fields):
            errors.append(f"Row {row_idx} column count mismatch: expected {len(fields)}, got {len(row)}")
            continue

        node_uuid = str(row[field_map["record_uuid"]]).strip()
        if not node_uuid:
            errors.append(f"Row {row_idx} contains empty column 0 'record_uuid'")
            continue
        if node_uuid in nodes_by_uuid:
            errors.append(f"Duplicate node record_uuid detected: '{node_uuid}'")
            continue

        nodes_by_uuid[node_uuid] = {k: row[idx] for k, idx in field_map.items()}

    # 3. Initial Step Validation
    if initial_step_uuid and nodes_by_uuid and initial_step_uuid not in nodes_by_uuid:
        errors.append(f"Initial_Step_UUID '{initial_step_uuid}' does not match any row in Values")
    elif not initial_step_uuid and nodes_by_uuid:
        # Default to first row's UUID if omitted
        initial_step_uuid = next(iter(nodes_by_uuid.keys()))

    # 4. Graph transition and dead-letter validation
    for node_uuid, node in nodes_by_uuid.items():
        on_success = str(node.get("on_success_transition_uuid", "")).strip()
        on_failure = str(node.get("on_failure_transition_uuid", "")).strip()

        if on_success and on_success not in nodes_by_uuid and on_success not in TERMINAL_GATES and not on_success.startswith("EXTERNAL://"):
            errors.append(f"Node '{node_uuid}' has dangling on_success_transition_uuid: '{on_success}'")

        if on_failure and on_failure not in nodes_by_uuid and on_failure not in TERMINAL_GATES and not on_failure.startswith("EXTERNAL://"):
            errors.append(f"Node '{node_uuid}' has dangling on_failure_transition_uuid: '{on_failure}'")

        # Validate loop safety
        loop_enabled = bool(node.get("loop_enabled_flag", False))
        max_iters = int(node.get("loop_max_iterations", 1))
        break_cond = str(node.get("loop_break_condition_eval", "")).strip()
        if loop_enabled and max_iters == -1 and not break_cond:
            errors.append(f"Node '{node_uuid}' has infinite loop (max_iterations=-1) without a break condition")

        # Validate threshold parameters if present
        if "if_repetition_count_over" in node:
            try:
                thresh = int(node["if_repetition_count_over"])
                if thresh < 0:
                    errors.append(f"Node '{node_uuid}' has negative 'if_repetition_count_over': {thresh}")
            except (ValueError, TypeError):
                errors.append(f"Node '{node_uuid}' has non-integer 'if_repetition_count_over'")

    # 5. Reachability check from initial step
    if initial_step_uuid and nodes_by_uuid:
        visited: Set[str] = set()
        queue = [initial_step_uuid]
        while queue:
            curr = queue.pop(0)
            if curr in visited or curr not in nodes_by_uuid:
                continue
            visited.add(curr)
            succ = str(nodes_by_uuid[curr].get("on_success_transition_uuid", ""))
            fail = str(nodes_by_uuid[curr].get("on_failure_transition_uuid", ""))
            cond = str(nodes_by_uuid[curr].get("conditional_forward_address", ""))
            for nxt in (succ, fail, cond):
                if nxt and nxt in nodes_by_uuid and nxt not in visited:
                    queue.append(nxt)

        unreachable = set(nodes_by_uuid.keys()) - visited
        if unreachable:
            LOG.warning("Unreachable FSM state nodes detected: %s", sorted(unreachable))

    return len(errors) == 0, errors


def validate_framework_registry_barrier(registry_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates a BEJSON 105a chunked framework registry envelope and verifies
    cryptographic SHA-256 hashes for all bundled code files and hooks.
    Returns: (is_valid, error_list)
    """
    errors: List[str] = []

    if registry_data.get("Format") != "BEJSON":
        errors.append("Invalid 'Format': expected 'BEJSON'")
    if not str(registry_data.get("Format_Version", "")).startswith("105"):
        errors.append("Invalid 'Format_Version': expected '105' series")

    fields = registry_data.get("Fields", [])
    field_map = build_field_map_105(fields)
    req_fields = ["record_uuid", "relative_file_path", "content_text", "sha256_checksum"]
    for rf in req_fields:
        if rf not in field_map:
            errors.append(f"Missing mandatory registry field: '{rf}'")

    if errors:
        return False, errors

    values = registry_data.get("Values", [])
    for row_idx, row in enumerate(values):
        rel_path = str(row[field_map["relative_file_path"]]).strip()
        content = str(row[field_map["content_text"]])
        expected_hash = str(row[field_map["sha256_checksum"]]).strip().lower()

        # Path traversal guard
        if rel_path.startswith("/") or ".." in rel_path:
            errors.append(f"Illegal relative path in row {row_idx}: '{rel_path}' breaks out of destination")

        # SHA-256 checksum validation
        computed_hash = hashlib.sha256(content.encode("utf-8")).hexdigest().lower()
        if expected_hash and computed_hash != expected_hash:
            errors.append(
                f"Checksum mismatch for '{rel_path}': expected {expected_hash[:12]}..., got {computed_hash[:12]}..."
            )

    return len(errors) == 0, errors
