"""
Library:         test_ai_remediation.py
Family:          AI
Module Purpose:  Regression tests for the 2026-11-17 gap-audit remediation (G1, G2, G3, G4, G6, plugin discovery).
Version:         1.0.0
Release_Version: 300
Date:            2026-11-17
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   GUID_PLACEHOLDER
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

_AI_DIR = Path(__file__).resolve().parent.parent
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from lib_bejson_AI_bejson_errors import AIException, ERR_AI_UNKNOWN_PROVIDER  # noqa: E402
from lib_bejson_ai_dispatcher import AIDispatcher  # noqa: E402
from lib_bejson_ai_env_vault import AIEnvVault  # noqa: E402
from lib_bejson_ai_features_common import redact_provider_error_text  # noqa: E402
from lib_bejson_ai_models import Query_Live_Gemini_Models  # noqa: E402
from lib_bejson_ai_tooling_interactions import InteractionsToolingSystem  # noqa: E402
from lib_bejson_ai_tooling_registry import AIGlobalConfigManager  # noqa: E402

MOCK_KEY = "AIzaSyMockRemediationKey1234567890"


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


class TestAIRemediation(unittest.TestCase):
    def test_live_model_query_keeps_key_out_of_url(self) -> None:
        captured_requests = []

        def fake_urlopen(api_request_object, timeout=None):
            captured_requests.append(api_request_object)
            return _FakeResponse(b'{"models": []}')

        with mock.patch.object(urllib.request, "urlopen", fake_urlopen):
            Query_Live_Gemini_Models(MOCK_KEY)
        self.assertEqual(len(captured_requests), 1)
        self.assertNotIn(MOCK_KEY, captured_requests[0].full_url)
        self.assertNotIn("key=", captured_requests[0].full_url)
        self.assertEqual(captured_requests[0].get_header("X-goog-api-key"), MOCK_KEY)

    def test_redact_provider_error_text_masks_keys_and_truncates(self) -> None:
        redacted_text = redact_provider_error_text(f"bad key {MOCK_KEY} here")
        self.assertNotIn(MOCK_KEY, redacted_text)
        self.assertIn("[REDACTED_API_KEY]", redacted_text)
        truncated_text = redact_provider_error_text("x" * 5000)
        self.assertLessEqual(len(truncated_text), 500 + len(" [truncated]"))
        self.assertTrue(truncated_text.endswith("[truncated]"))

    def test_vault_search_paths_have_no_hardcoded_storage_literals(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory_path_str:
            vault = AIEnvVault(script_path=Path(temporary_directory_path_str))
            pointer_path = Path(temporary_directory_path_str) / "pointer_definitions.json"
            with mock.patch.dict(os.environ, {"DEFINITIONS_FILE": str(pointer_path)}):
                definitions_candidates = [str(path) for path in vault.get_definitions_search_paths()]
            secureenv_candidates = [str(path) for path in vault.get_secureenv_search_paths()]
        self.assertIn(str(pointer_path.resolve()), definitions_candidates)
        for candidate_path_str in definitions_candidates + secureenv_candidates:
            self.assertFalse(
                candidate_path_str.startswith("/storage/emulated/0/.env"),
                f"hardcoded literal path survived: {candidate_path_str}",
            )

    def test_corrupt_config_is_preserved_not_discarded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory_path_str:
            config_path = Path(temporary_directory_path_str) / "ai_global_config.105a.bejson"
            config_path.write_text("{ this is not valid json", encoding="utf-8")
            with self.assertLogs("lib_bejson_ai_tooling_registry", level="WARNING"):
                config_manager = AIGlobalConfigManager(config_target_file_path=config_path)
            backups = list(Path(temporary_directory_path_str).glob("ai_global_config.105a.bejson.corrupt-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding="utf-8"), "{ this is not valid json")
            self.assertEqual(config_manager.get_setting("default_provider", None), "geminirest")

    def test_tool_handler_body_type_error_executes_once(self) -> None:
        call_counter = {"count": 0}

        def failing_handler(city: str) -> str:
            call_counter["count"] += 1
            raise TypeError("internal handler bug")

        tooling_system = InteractionsToolingSystem(is_enabled_override_flag=True)
        tooling_system.register_tool({"type": "function", "name": "lookup"}, failing_handler)
        result_step = tooling_system.execute_tool_call(
            {"name": "lookup", "id": "c1", "arguments": {"city": "Oslo"}}
        )
        self.assertEqual(call_counter["count"], 1)
        self.assertTrue(result_step["is_error"])

    def test_tool_handler_single_dict_param_still_supported(self) -> None:
        def dict_handler(payload):
            return {"echo": payload}

        tooling_system = InteractionsToolingSystem(is_enabled_override_flag=True)
        tooling_system.register_tool({"type": "function", "name": "echo"}, dict_handler)
        result_step = tooling_system.execute_tool_call(
            {"name": "echo", "id": "c2", "arguments": {"unmatched_key": 1}}
        )
        self.assertFalse(result_step["is_error"])

    def test_provider_discovery_outside_package_is_blocked(self) -> None:
        dispatcher = AIDispatcher()
        with tempfile.TemporaryDirectory() as temporary_directory_path_str:
            with self.assertRaises(AIException) as raised_context:
                dispatcher.discover_providers(Path(temporary_directory_path_str))
        self.assertEqual(raised_context.exception.code, ERR_AI_UNKNOWN_PROVIDER)


if __name__ == "__main__":
    unittest.main()
