"""
Library:        lib_bejson_Browser_browser_schemas.py
Family:         Browser
Description:    Canonical BEJSON 105a schema definitions and factories for Browser Playbooks.
Version:        1.0.0
Date:           2026-11-21
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  3a0018f4-021b-4fda-bdf4-8e7619db51e7
Release_Version: 300
License:        PolyForm-Noncommercial-1.0.0
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Final, List

if sys.version_info < (3, 10):
    raise RuntimeError("Python 3.10+ is required.")

# Sibling family resolution for Core
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_CORE_DIR = os.path.normpath(os.path.join(_CURRENT_DIR, "..", "Core"))
if os.path.isdir(_CORE_DIR) and _CORE_DIR not in sys.path:
    sys.path.insert(0, _CORE_DIR)

# ---------------------------------------------------------------------------
# Format 105a Browser Session Configuration Schema
# ---------------------------------------------------------------------------
BROWSER_SESSION_CONFIG_FIELDS: Final[List[Dict[str, str]]] = [
    {
        "name": "headless",
        "type": "boolean",
        "field_uuid": "159cf06e-5aa5-403d-8869-3d38785fb7de",
        "description": "Whether to launch the browser in headless mode"
    },
    {
        "name": "viewport_width",
        "type": "integer",
        "field_uuid": "2f21dcbb-c5d7-487d-a7d1-c583365f94d9",
        "description": "Browser viewport display width in pixels"
    },
    {
        "name": "viewport_height",
        "type": "integer",
        "field_uuid": "6f6f7698-3f4f-4975-a16d-906cb7677643",
        "description": "Browser viewport display height in pixels"
    },
    {
        "name": "default_timeout_ms",
        "type": "integer",
        "field_uuid": "c7a6130b-7e8b-4874-956a-9804a92ceb98",
        "description": "Default timeout ceiling in milliseconds across all actions"
    },
    {
        "name": "user_agent",
        "type": "string",
        "field_uuid": "96c814e6-c6c2-44d2-a373-3ae4f4261b63",
        "description": "Custom user agent string override for browser requests"
    },
    {
        "name": "storage_state_path",
        "type": "string",
        "field_uuid": "c8898e5f-1a2a-49d3-9a1a-68c276bd9960",
        "description": "File path to authenticated Playwright browser storage state JSON"
    }
]

# ---------------------------------------------------------------------------
# Format 105a Browser Action Row Schema (12 Columns)
# Column 0 is reserved for record_uuid and strictly omitted from Fields
# ---------------------------------------------------------------------------
BROWSER_ACTION_ROW_FIELDS: Final[List[Dict[str, str]]] = [
    {
        "name": "step_index",
        "type": "integer",
        "field_uuid": "eed8b208-f047-4494-8740-9785321f745d",
        "description": "Sequential integer order index of the browser execution step"
    },
    {
        "name": "action_verb",
        "type": "string",
        "field_uuid": "7ffb5389-b9ca-4743-83fc-e426eaae146a",
        "description": "Browser action verb: goto, click, fill, select, press, wait_for, extract_text, extract_attr, screenshot, eval_js"
    },
    {
        "name": "locator_strategy",
        "type": "string",
        "field_uuid": "1ecab4f4-8332-494e-b219-3f772fe4fa8d",
        "description": "Playwright selector strategy: css, role, text, testid, xpath, or none"
    },
    {
        "name": "locator_value",
        "type": "string",
        "field_uuid": "30cc11c5-953a-4c97-aff8-ad782166fdc4",
        "description": "Target selector expression, URL for goto, or empty if strategy is none"
    },
    {
        "name": "input_payload",
        "type": "string",
        "field_uuid": "86d075c3-2c10-419b-bc0a-b0ab215f07b8",
        "description": "Input payload for fill/select/press, script for eval_js, or attribute name"
    },
    {
        "name": "timeout_ms",
        "type": "integer",
        "field_uuid": "5f415851-6a58-403e-a44e-190272107651",
        "description": "Maximum execution timeout in milliseconds for this step (positive integer)"
    },
    {
        "name": "wait_after_ms",
        "type": "integer",
        "field_uuid": "703ed1e9-a32b-4f2b-ad92-a98e3cb5a91a",
        "description": "Settling pause in milliseconds to wait immediately after step execution"
    },
    {
        "name": "save_var_key",
        "type": "string",
        "field_uuid": "7f14b06a-bbd1-439b-8ae0-26e76da60269",
        "description": "Session variable name to bind extracted value or evaluation output"
    },
    {
        "name": "extracted_value",
        "type": "string",
        "field_uuid": "09a6b2fc-f5bc-4539-bf64-1fb49e72096b",
        "description": "Resulting text content or attribute extracted during step execution"
    },
    {
        "name": "artifact_path",
        "type": "string",
        "field_uuid": "80a8bca3-f4af-4c89-9606-1250e33b9f1d",
        "description": "File path where screenshot artifact is captured and saved"
    },
    {
        "name": "is_completed",
        "type": "boolean",
        "field_uuid": "486ed6ac-c4c9-4b2b-bcd5-af90839c6601",
        "description": "Execution status flag indicating whether step finished successfully"
    },
    {
        "name": "error_code",
        "type": "integer",
        "field_uuid": "d4db9974-774f-4606-8705-f24d9161d3c5",
        "description": "Exit status code: 0 for success or Browser family error code on failure"
    }
]


def create_empty_playbook(name: str) -> Dict[str, Any]:
    """
    Emits a canonical, valid BEJSON 105a Browser Playbook document skeleton.
    Record UUIDs are reserved at row index 0 and strictly omitted from 'Fields'.
    """
    return {
        "Format": "BEJSON",
        "Format_Version": "105a",
        "Format_Creator": "Elton Boehnen",
        "Records_Type": ["Browser_Playbook"],
        "Playbook_Name": name,
        "Session_Config": {
            "headless": True,
            "viewport_width": 1280,
            "viewport_height": 720,
            "default_timeout_ms": 30000,
            "user_agent": "",
            "storage_state_path": ""
        },
        "Fields": [dict(field_def) for field_def in BROWSER_ACTION_ROW_FIELDS],
        "Values": []
    }
