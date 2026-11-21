"""
Library:        __init__.py
Family:         Browser
Description:    Package entry point for the BEJSON 105a Browser library family.
Version:        1.0.0
Date:           2026-11-21
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  9bbbc629-3890-440a-b226-eb9e756ea2e5
Release_Version: 300
License:        PolyForm-Noncommercial-1.0.0
"""

from __future__ import annotations

import os
import sys

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

from lib_bejson_Browser_browser_errors import (
    ERR_BROWSER_ACTION_TIMEOUT,
    ERR_BROWSER_IO_FAILURE,
    ERR_BROWSER_LAUNCH_FAILED,
    ERR_BROWSER_LOCATOR_NOT_FOUND,
    ERR_BROWSER_SCHEMA_INVALID,
    ERR_BROWSER_SUCCESS,
    ERR_BROWSER_UNKNOWN_VERB,
    ERROR_DESCRIPTIONS,
    BrowserLibraryError,
)
from lib_bejson_Browser_browser_schemas import (
    BROWSER_ACTION_ROW_FIELDS,
    BROWSER_SESSION_CONFIG_FIELDS,
    create_empty_playbook,
)
from lib_bejson_Browser_browser_validator import (
    ALLOWED_ACTION_VERBS,
    ALLOWED_LOCATOR_STRATEGIES,
    DOM_TARGETING_VERBS,
    validate_browser_barrier,
    validate_browser_playbook,
)
from lib_bejson_Browser_browser_core import (
    BrowserSession,
    run_browser_playbook,
    run_browser_playbook_async,
    run_with_browser,
)

__all__ = [
    "ERR_BROWSER_SUCCESS",
    "ERR_BROWSER_SCHEMA_INVALID",
    "ERR_BROWSER_UNKNOWN_VERB",
    "ERR_BROWSER_LOCATOR_NOT_FOUND",
    "ERR_BROWSER_ACTION_TIMEOUT",
    "ERR_BROWSER_LAUNCH_FAILED",
    "ERR_BROWSER_IO_FAILURE",
    "ERROR_DESCRIPTIONS",
    "BrowserLibraryError",
    "BROWSER_SESSION_CONFIG_FIELDS",
    "BROWSER_ACTION_ROW_FIELDS",
    "create_empty_playbook",
    "ALLOWED_ACTION_VERBS",
    "ALLOWED_LOCATOR_STRATEGIES",
    "DOM_TARGETING_VERBS",
    "validate_browser_barrier",
    "validate_browser_playbook",
    "BrowserSession",
    "run_with_browser",
    "run_browser_playbook",
    "run_browser_playbook_async",
]
