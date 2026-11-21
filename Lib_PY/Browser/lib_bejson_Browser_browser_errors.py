"""
Library:        lib_bejson_Browser_browser_errors.py
Family:         Browser
Description:    Canonical error registry and exception classes for BEJSON Browser Playbook execution.
Version:        1.0.0
Date:           2026-11-21
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  691fa8ce-4c0f-4f5f-9add-8cccecb50e4b
Release_Version: 300
License:        PolyForm-Noncommercial-1.0.0
"""

from __future__ import annotations

import sys
from typing import Dict, Final

if sys.version_info < (3, 10):
    raise RuntimeError("Python 3.10+ is required.")

# ---------------------------------------------------------------------------
# Browser Domain Error Codes (600-629)
# ---------------------------------------------------------------------------
# Non-overlapping range starting at 600
# Graphics: 500-519, Gaming_Editors: 520-530, Metrics: 580-584.
ERR_BROWSER_SUCCESS: Final[int] = 0
ERR_BROWSER_SCHEMA_INVALID: Final[int] = 601
ERR_BROWSER_UNKNOWN_VERB: Final[int] = 602
ERR_BROWSER_LOCATOR_NOT_FOUND: Final[int] = 603
ERR_BROWSER_ACTION_TIMEOUT: Final[int] = 604
ERR_BROWSER_LAUNCH_FAILED: Final[int] = 605
ERR_BROWSER_IO_FAILURE: Final[int] = 606

ERROR_DESCRIPTIONS: Final[Dict[int, str]] = {
    ERR_BROWSER_SUCCESS: "Success",
    ERR_BROWSER_SCHEMA_INVALID: "Document failed BEJSON 105a or Browser Playbook schema validation",
    ERR_BROWSER_UNKNOWN_VERB: "Playbook action verb is unrecognized or not supported",
    ERR_BROWSER_LOCATOR_NOT_FOUND: "Specified DOM locator was not found within the timeout period",
    ERR_BROWSER_ACTION_TIMEOUT: "Action execution or navigation exceeded the configured timeout ceiling",
    ERR_BROWSER_LAUNCH_FAILED: "Underlying Playwright or Termux browser process failed to initialize",
    ERR_BROWSER_IO_FAILURE: "Disk I/O error during playbook load, screenshot capture, or atomic writeback",
}


class BrowserLibraryError(Exception):
    """
    Base exception class for Browser library family operations.
    Encapsulates numeric family error codes and descriptive messages so
    that caller logic never relies on raw magic numbers.
    """

    def __init__(self, code: int, message: str) -> None:
        self.code: int = code
        self.message: str = message
        self.description: str = ERROR_DESCRIPTIONS.get(code, "Unknown Browser library error")
        super().__init__(f"[Error {self.code}] {self.description}: {self.message}")
