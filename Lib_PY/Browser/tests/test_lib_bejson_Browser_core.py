"""
Library:        test_lib_bejson_Browser_core.py
Family:         Browser
Description:    Unit tests for BEJSON 105a Browser Playbook core, validator, and runner.
Version:        1.0.0
Date:           2026-11-21
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  00f26a01-162d-4d14-8998-f213443f0f31
Release_Version: 300
License:        PolyForm-Noncommercial-1.0.0
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

# Sibling library resolution
_CURRENT_DIR = Path(__file__).resolve().parent.parent
_CORE_DIR = _CURRENT_DIR.parent / "Core"
if str(_CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_DIR))
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

from lib_bejson_Core_bejson_core import bejson_core_atomic_write

from lib_bejson_Browser_browser_core import (
    BrowserSession,
    run_browser_playbook,
    run_with_browser,
)
from lib_bejson_Browser_browser_errors import (
    ERR_BROWSER_ACTION_TIMEOUT,
    ERR_BROWSER_LOCATOR_NOT_FOUND,
    ERR_BROWSER_SCHEMA_INVALID,
    ERR_BROWSER_SUCCESS,
    ERR_BROWSER_UNKNOWN_VERB,
    BrowserLibraryError,
)
from lib_bejson_Browser_browser_schemas import (
    BROWSER_ACTION_ROW_FIELDS,
    create_empty_playbook,
)
from lib_bejson_Browser_browser_validator import (
    validate_browser_barrier,
    validate_browser_playbook,
)


class TestBrowserLibraryCore(unittest.TestCase):
    """
    Offline test suite for BEJSON 105a Browser Playbook core engine.
    Ensures zero hardcoded Termux paths by utilizing temporary directories and file:// fixtures.
    """

    def setUp(self) -> None:
        self.test_directory = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.test_directory.name)

        # Create a self-contained local HTML fixture
        self.fixture_path = self.temp_path / "test_fixture.html"
        self.fixture_html = """<!DOCTYPE html>
<html>
<head><title>Playbook Test Page</title></head>
<body>
  <input id="username" type="text" value="" />
  <button id="submit-btn" onclick="document.getElementById('greeting').innerText = 'Welcome ' + document.getElementById('username').value">Submit</button>
  <div id="greeting">Waiting...</div>
  <a id="test-link" href="https://example.com" data-category="alpha">Link</a>
</body>
</html>"""
        with open(self.fixture_path, "w", encoding="utf-8") as fixture_file:
            fixture_file.write(self.fixture_html)

    def tearDown(self) -> None:
        self.test_directory.cleanup()

    def test_105a_validation_pass_and_fail(self) -> None:
        """
        Verifies Tier 1 Core integrity and Tier 2 semantic validation on 105a playbooks.
        """
        # 1. Empty playbook passes
        playbook = create_empty_playbook("Empty_Valid_Playbook")
        validation_result = validate_browser_playbook(playbook)
        self.assertTrue(validation_result.valid, f"Validation failed: {validation_result.errors}")

        # 2. Valid playbook with compliant row contract
        playbook_file = self.temp_path / "valid_playbook.105a.bejson"
        playbook_valid = create_empty_playbook("Valid_Playbook")
        playbook_valid["Values"] = [
            [
                str(uuid.uuid4()),
                1, "goto", "none", f"file://{self.fixture_path.resolve()}", "", 15000, 100, "", "", "", False, 0
            ],
            [
                str(uuid.uuid4()),
                2, "fill", "css", "#username", "Elton", 5000, 50, "", "", "", False, 0
            ]
        ]
        bejson_core_atomic_write(str(playbook_file), playbook_valid)

        file_validation = validate_browser_playbook(playbook_file, is_file=True)
        self.assertTrue(file_validation.valid, f"File validation failed: {file_validation.errors}")

        # 3. Invalid action verb fails
        invalid_verb_doc = create_empty_playbook("Invalid_Verb")
        invalid_verb_doc["Values"] = [
            [str(uuid.uuid4()), 1, "explode_dom", "css", "#username", "", 5000, 0, "", "", "", False, 0]
        ]
        invalid_verb_result = validate_browser_playbook(invalid_verb_doc)
        self.assertFalse(invalid_verb_result.valid)
        self.assertTrue(any(str(ERR_BROWSER_UNKNOWN_VERB) in msg for msg in invalid_verb_result.errors))

        # 4. DOM verb with empty locator fails
        empty_locator_doc = create_empty_playbook("Empty_Locator")
        empty_locator_doc["Values"] = [
            [str(uuid.uuid4()), 1, "click", "css", "", "", 5000, 0, "", "", "", False, 0]
        ]
        empty_locator_result = validate_browser_playbook(empty_locator_doc)
        self.assertFalse(empty_locator_result.valid)

        # 5. Invalid non-positive timeout fails
        bad_timeout_doc = create_empty_playbook("Bad_Timeout")
        bad_timeout_doc["Values"] = [
            [str(uuid.uuid4()), 1, "wait_for", "none", "", "", -100, 0, "", "", "", False, 0]
        ]
        bad_timeout_result = validate_browser_playbook(bad_timeout_doc)
        self.assertFalse(bad_timeout_result.valid)

    def test_row_by_row_execution_flow(self) -> None:
        """
        Executes a complete multi-step playbook:
        goto -> fill with {{var}} -> click -> extract_text -> screenshot
        """
        screenshot_path = self.temp_path / "artifacts" / "test_screenshot.png"
        playbook_path = self.temp_path / "execution_playbook.105a.bejson"

        playbook = create_empty_playbook("Test_Execution_Flow")
        playbook["Values"] = [
            [
                str(uuid.uuid4()),
                1, "goto", "none", f"file://{self.fixture_path.resolve()}", "", 10000, 100, "", "", "", False, 0
            ],
            [
                str(uuid.uuid4()),
                2, "fill", "css", "#username", "{{user_name}}", 5000, 50, "", "", "", False, 0
            ],
            [
                str(uuid.uuid4()),
                3, "click", "css", "#submit-btn", "", 5000, 100, "", "", "", False, 0
            ],
            [
                str(uuid.uuid4()),
                4, "extract_text", "css", "#greeting", "", 5000, 50, "saved_greeting", "", "", False, 0
            ],
            [
                str(uuid.uuid4()),
                5, "screenshot", "none", "", "", 5000, 0, "", "", str(screenshot_path), False, 0
            ]
        ]

        with open(playbook_path, "w", encoding="utf-8") as file_handle:
            json.dump(playbook, file_handle, indent=2)

        # Execute playbook synchronously with variable interpolation
        updated_playbook = run_browser_playbook(
            playbook_path=playbook_path,
            vars_override={"user_name": "AntigravityUser"},
            resume=True
        )

        # Verify on-disk progress and atomic persistence
        with open(playbook_path, "r", encoding="utf-8") as result_file:
            disk_doc = json.load(result_file)

        rows = disk_doc["Values"]
        self.assertEqual(len(rows), 5)

        # Ensure all steps completed with success code 0
        for current_row in rows:
            is_completed = current_row[11]  # is_completed index
            error_code = current_row[12]    # error_code index
            self.assertTrue(is_completed, f"Row step {current_row[1]} is not completed")
            self.assertEqual(error_code, ERR_BROWSER_SUCCESS)

        # Verify extracted text matches DOM state
        extracted_greeting = rows[3][9]  # extracted_value index
        self.assertEqual(extracted_greeting, "Welcome AntigravityUser")

        # Verify screenshot file exists and is populated
        self.assertTrue(screenshot_path.exists())
        self.assertGreater(screenshot_path.stat().st_size, 0)

    def test_resumability_and_failure_atomic_writeback(self) -> None:
        """
        Verifies that mid-table failure updates the specific row with error code,
        persists atomically, and allows resuming cleanly after correction.
        """
        playbook_path = self.temp_path / "resume_playbook.105a.bejson"

        playbook = create_empty_playbook("Test_Resume_Flow")
        playbook["Values"] = [
            [
                str(uuid.uuid4()),
                1, "goto", "none", f"file://{self.fixture_path.resolve()}", "", 10000, 50, "", "", "", False, 0
            ],
            [
                str(uuid.uuid4()),
                2, "click", "css", "#nonexistent-element-fail-here", "", 500, 0, "", "", "", False, 0
            ],
            [
                str(uuid.uuid4()),
                3, "extract_text", "css", "#greeting", "", 5000, 0, "", "", "", False, 0
            ]
        ]

        with open(playbook_path, "w", encoding="utf-8") as file_handle:
            json.dump(playbook, file_handle, indent=2)

        # 1. Expect failure on Step 2
        with self.assertRaises(BrowserLibraryError) as exc_context:
            run_browser_playbook(playbook_path=playbook_path, resume=True)

        self.assertIn(
            exc_context.exception.code,
            (ERR_BROWSER_LOCATOR_NOT_FOUND, ERR_BROWSER_ACTION_TIMEOUT)
        )

        # 2. Check disk state after failure
        with open(playbook_path, "r", encoding="utf-8") as disk_check:
            failed_doc = json.load(disk_check)

        rows = failed_doc["Values"]
        self.assertTrue(rows[0][11])  # Step 1 is_completed == True
        self.assertEqual(rows[0][12], ERR_BROWSER_SUCCESS)

        self.assertFalse(rows[1][11])  # Step 2 is_completed == False
        self.assertNotEqual(rows[1][12], ERR_BROWSER_SUCCESS)

        self.assertFalse(rows[2][11])  # Step 3 is_completed == False

        # 3. Correct Step 2 to target a real element (#submit-btn) with adequate timeout
        rows[1][4] = "#submit-btn"
        rows[1][6] = 5000  # timeout_ms
        bejson_core_atomic_write(str(playbook_path), failed_doc)

        # 4. Resume execution
        run_browser_playbook(playbook_path=playbook_path, resume=True)

        # 5. Check disk state after resumed execution
        with open(playbook_path, "r", encoding="utf-8") as disk_resume_check:
            resumed_doc = json.load(disk_resume_check)

        resumed_rows = resumed_doc["Values"]
        self.assertTrue(resumed_rows[0][11])
        self.assertTrue(resumed_rows[1][11])
        self.assertTrue(resumed_rows[2][11])
        self.assertEqual(resumed_rows[1][12], ERR_BROWSER_SUCCESS)
        self.assertEqual(resumed_rows[2][12], ERR_BROWSER_SUCCESS)

    def test_run_with_browser_sync_helper(self) -> None:
        """
        Verifies that run_with_browser executes a one-off async closure against a page.
        """
        async def _eval_expression(page: Any) -> int:
            await page.set_content("<div id='calc'>42</div>")
            text = await page.text_content("#calc")
            return int(text)

        result_value = run_with_browser(_eval_expression, headless=True)
        self.assertEqual(result_value, 42)


if __name__ == "__main__":
    unittest.main()
