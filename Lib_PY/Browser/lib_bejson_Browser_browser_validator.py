"""
Library:        lib_bejson_Browser_browser_validator.py
Family:         Browser
Description:    Read-only two-tier structural and semantic validator for Browser Playbooks.
Version:        1.0.0
Date:           2026-11-21
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  2e9191d0-a6aa-4d90-97fb-226bb78a53a5
Release_Version: 300
License:        PolyForm-Noncommercial-1.0.0
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Final, List, Set, Union

if sys.version_info < (3, 10):
    raise RuntimeError("Python 3.10+ is required.")

# Sibling family resolution for Core and Browser
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
for _family_name in ("Core", "Browser"):
    _family_path = os.path.normpath(os.path.join(_CURRENT_DIR, "..", _family_name))
    if os.path.isdir(_family_path) and _family_path not in sys.path:
        sys.path.insert(0, _family_path)

from lib_bejson_Core_bejson_core import (
    bejson_core_get_field_map,
    bejson_core_verify_105_integrity,
)
from lib_bejson_Core_bejson_validator import (
    ValidationResult,
    validate_bejson,
)
from lib_bejson_Browser_browser_errors import (
    ERR_BROWSER_LOCATOR_NOT_FOUND,
    ERR_BROWSER_SCHEMA_INVALID,
    ERR_BROWSER_UNKNOWN_VERB,
    ERROR_DESCRIPTIONS,
)

logger: logging.Logger = logging.getLogger("BrowserPlaybookValidator")

# Allowed action verbs enum
ALLOWED_ACTION_VERBS: Final[Set[str]] = {
    "goto",
    "click",
    "fill",
    "select",
    "press",
    "wait_for",
    "extract_text",
    "extract_attr",
    "screenshot",
    "eval_js",
}

# Verbs that strictly target DOM nodes
DOM_TARGETING_VERBS: Final[Set[str]] = {
    "click",
    "fill",
    "select",
    "press",
    "wait_for",
    "extract_text",
    "extract_attr",
}

# Allowed locator strategies
ALLOWED_LOCATOR_STRATEGIES: Final[Set[str]] = {
    "css",
    "role",
    "text",
    "testid",
    "xpath",
    "none",
}

REQUIRED_PLAYBOOK_FIELDS: Final[List[str]] = [
    "step_index",
    "action_verb",
    "locator_strategy",
    "locator_value",
    "input_payload",
    "timeout_ms",
    "wait_after_ms",
    "save_var_key",
    "extracted_value",
    "artifact_path",
    "is_completed",
    "error_code",
]


def validate_browser_playbook(
    input_data: Union[str, Path, Dict[str, Any]],
    is_file: bool = False
) -> ValidationResult:
    """
    Read-only Two-Tier Barrier of Entry validator for BEJSON 105a Browser Playbooks.
    Never mutates files or documents on disk.

    Tier 1 (Core Integrity Gate):
      - Executes validate_bejson() to verify structural JSON envelope compliance.
      - Executes bejson_core_verify_105_integrity() to ensure 105a record_uuid
        and field_uuid invariants hold.

    Tier 2 (Browser Semantic Gate):
      - Resolves column offsets dynamically through bejson_core_get_field_map().
      - Verifies action_verb belongs to the permitted enum.
      - Enforces that verbs targeting DOM nodes declare a non-empty locator_value.
      - Confirms locator_strategy is valid (css, role, text, testid, xpath, none).
      - Confirms timeout_ms is a strictly positive integer (> 0).
    """
    # -------------------------------------------------------------------------
    # Tier 1: Foundational Core Family Barrier
    # -------------------------------------------------------------------------
    core_result: ValidationResult = validate_bejson(input_data, is_file=is_file)
    if not core_result.valid:
        core_result.errors.insert(
            0,
            f"[{ERR_BROWSER_SCHEMA_INVALID}] {ERROR_DESCRIPTIONS[ERR_BROWSER_SCHEMA_INVALID]}: "
            f"Core validator rejected document ({len(core_result.errors)} errors)"
        )
        return core_result

    # Load document without mutation
    document: Dict[str, Any]
    if is_file or (isinstance(input_data, (str, Path)) and os.path.isfile(str(input_data))):
        try:
            with open(str(input_data), "r", encoding="utf-8") as file_handle:
                document = json.load(file_handle)
        except Exception as read_exception:
            core_result.add_error(
                f"[{ERR_BROWSER_SCHEMA_INVALID}] Failed to read playbook file: {read_exception}"
            )
            return core_result
    elif isinstance(input_data, dict):
        document = input_data
    elif isinstance(input_data, str):
        try:
            document = json.loads(input_data)
        except Exception as parse_exception:
            core_result.add_error(
                f"[{ERR_BROWSER_SCHEMA_INVALID}] Failed to parse playbook JSON string: {parse_exception}"
            )
            return core_result
    else:
        core_result.add_error(
            f"[{ERR_BROWSER_SCHEMA_INVALID}] Unsupported input_data type: {type(input_data)}"
        )
        return core_result

    # Tier 1.2: Strict 105-series integrity check
    integrity_status = bejson_core_verify_105_integrity(document)
    if not integrity_status.get("ok", False):
        integrity_errors: List[str] = integrity_status.get("errors", [])
        for err_msg in integrity_errors:
            core_result.add_error(
                f"[{ERR_BROWSER_SCHEMA_INVALID}] 105 Integrity failure: {err_msg}"
            )
        return core_result

    # -------------------------------------------------------------------------
    # Tier 2: Browser Domain Semantic Barrier
    # -------------------------------------------------------------------------
    try:
        field_map = bejson_core_get_field_map(document)
    except Exception as map_exception:
        core_result.add_error(
            f"[{ERR_BROWSER_SCHEMA_INVALID}] Failed to build field map: {map_exception}"
        )
        return core_result

    # Verify all expected columns exist in schema
    for expected_column in REQUIRED_PLAYBOOK_FIELDS:
        if expected_column not in field_map:
            core_result.add_error(
                f"[{ERR_BROWSER_SCHEMA_INVALID}] Missing mandatory column '{expected_column}' in playbook schema"
            )

    if not core_result.valid:
        return core_result

    rows: List[List[Any]] = document.get("Values", [])
    for row_position, row_values in enumerate(rows):
        # 1. Action verb validation
        action_verb_raw = row_values[field_map["action_verb"]]
        if not isinstance(action_verb_raw, str):
            core_result.add_error(
                f"[{ERR_BROWSER_SCHEMA_INVALID}] Row {row_position}: "
                f"action_verb must be string, got {type(action_verb_raw).__name__}"
            )
            continue

        action_verb = action_verb_raw.strip()
        if action_verb not in ALLOWED_ACTION_VERBS:
            core_result.add_error(
                f"[{ERR_BROWSER_UNKNOWN_VERB}] Row {row_position}: "
                f"unrecognized action_verb '{action_verb}'. Permitted: {sorted(ALLOWED_ACTION_VERBS)}"
            )

        # 2. Locator strategy validation
        locator_strategy_raw = row_values[field_map["locator_strategy"]]
        locator_strategy = str(locator_strategy_raw).strip() if locator_strategy_raw is not None else ""
        if locator_strategy not in ALLOWED_LOCATOR_STRATEGIES:
            core_result.add_error(
                f"[{ERR_BROWSER_SCHEMA_INVALID}] Row {row_position}: "
                f"invalid locator_strategy '{locator_strategy}'. Permitted: {sorted(ALLOWED_LOCATOR_STRATEGIES)}"
            )

        # 3. DOM node targeting locator_value verification
        locator_value_raw = row_values[field_map["locator_value"]]
        locator_value = str(locator_value_raw).strip() if locator_value_raw is not None else ""
        if action_verb in DOM_TARGETING_VERBS:
            if not locator_value:
                core_result.add_error(
                    f"[{ERR_BROWSER_LOCATOR_NOT_FOUND}] Row {row_position}: "
                    f"action_verb '{action_verb}' targets DOM nodes but locator_value is empty"
                )
            if locator_strategy == "none" and action_verb != "wait_for":
                core_result.add_error(
                    f"[{ERR_BROWSER_SCHEMA_INVALID}] Row {row_position}: "
                    f"action_verb '{action_verb}' targets DOM nodes but locator_strategy is 'none'"
                )

        # 4. Timeout validation: positive integer
        timeout_raw = row_values[field_map["timeout_ms"]]
        if isinstance(timeout_raw, bool) or not isinstance(timeout_raw, int) or timeout_raw <= 0:
            core_result.add_error(
                f"[{ERR_BROWSER_SCHEMA_INVALID}] Row {row_position}: "
                f"timeout_ms must be a positive integer (>0), got {timeout_raw!r}"
            )

    return core_result


# Canonical alias matching two-tier barrier naming convention
validate_browser_barrier = validate_browser_playbook
