"""
Unit Test Suite: test_ai_components_unit.py
Family:          AI_Core
Purpose:         Comprehensive component-level unit tests for every module in Lib_PY/AI_Core.
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
License:         PolyForm-Noncommercial-1.0.0
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from typing import Any, Dict, Optional
from unittest import mock

_TESTS_DIR = Path(__file__).resolve().parent
_AI_DIR = _TESTS_DIR.parent
_LIB_PY_DIR = _AI_DIR.parent
_CORE_DIR = _LIB_PY_DIR / "Core"

for _p in (_LIB_PY_DIR, _AI_DIR, _CORE_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from lib_bejson_Core_bejson_validator import validate_bejson  # noqa: E402

import AI_Core as ai_pkg  # noqa: E402
import lib_bejson_AI_Core_errors as ai_errors  # noqa: E402
from lib_bejson_AI_Core_errors import (  # noqa: E402
    AIException,
    ERR_AI_HTTP_NETWORK_ERROR,
    ERR_AI_HTTP_TIMEOUT,
    ERR_AI_KEY_EXHAUSTED,
    ERR_AI_OUTPUT_VALIDATION_FAILED,
    ERR_AI_POSTPROCESS_REJECTED,
    ERR_AI_PREPROCESS_REJECTED,
    ERR_AI_RENDERER_NOT_FOUND,
    ERR_AI_SANITIZER_BLOCKED,
    ERR_AI_SUCCESS,
    ERR_AI_TOKEN_LIMIT_EXCEEDED,
    ERR_AI_TOOLING_SYSTEM_NOT_FOUND,
    ERR_AI_UNKNOWN_PROVIDER,
    ERR_AI_XML_PARSE_FAILED,
    ERROR_DESCRIPTIONS,
)
from lib_bejson_AI_Core_client_base import BaseAIClient  # noqa: E402
from lib_bejson_AI_Core_client_geminiinteractions import GeminiInteractionsClient  # noqa: E402
from lib_bejson_AI_Core_client_geminirest import GeminiRestClient  # noqa: E402
from lib_bejson_AI_Core_dispatcher import (  # noqa: E402
    AIDispatcher,
    Get_Interaction_ID,
    Get_Rendered_Output,
    Get_Response_JSON,
    Get_Response_Text,
    Get_Response_Usage,
    Get_Tool_Calls,
    Get_Turn_Continuation_Command,
)
from lib_bejson_AI_Core_env_vault import AIEnvVault  # noqa: E402
from lib_bejson_AI_Core_features_common import (  # noqa: E402
    build_bejson_105_ai_request,
    build_bejson_105_ai_response,
    redact_provider_error_text,
)
from lib_bejson_AI_Core_jit_key_handler import JITKeyHandler, mask_key  # noqa: E402
from lib_bejson_AI_Core_key_rotator import KeyRotator  # noqa: E402
from lib_bejson_AI_Core_models import (  # noqa: E402
    ACTIVE_TEXT_MODELS_REGISTRY,
    List_Active_Gemini_Models,
    Resolve_Model_Identifier,
)
from lib_bejson_AI_Core_postprocessor import AIPostprocessor  # noqa: E402
from lib_bejson_AI_Core_preprocessor import AIPreprocessor  # noqa: E402
from lib_bejson_AI_Core_renderer_registry import RendererRegistry  # noqa: E402
from lib_bejson_AI_Core_tooling_registry import AIGlobalConfigManager, ToolingRegistry  # noqa: E402
from lib_bejson_AI_Core_translator import AITranslator  # noqa: E402


class TestAIErrorRegistry(unittest.TestCase):
    def test_all_error_codes_in_allocated_range_and_described(self) -> None:
        constants = {
            name: val
            for name, val in vars(ai_errors).items()
            if name.startswith("ERR_AI_") and isinstance(val, int)
        }
        self.assertGreaterEqual(len(constants), 25)
        values = list(constants.values())
        self.assertEqual(len(values), len(set(values)), "Duplicate ERR_AI_* codes found.")
        for name, code in constants.items():
            if code != ERR_AI_SUCCESS:
                self.assertTrue(200 <= code <= 249, f"{name}={code} outside allocated ranges 200-249")
            self.assertIn(code, ERROR_DESCRIPTIONS, f"Missing description for {name}={code}")

    def test_ai_exception_formatting(self) -> None:
        exc_plain = AIException(ERR_AI_UNKNOWN_PROVIDER)
        self.assertEqual(exc_plain.code, ERR_AI_UNKNOWN_PROVIDER)
        self.assertIn(f"[Error {ERR_AI_UNKNOWN_PROVIDER}]", str(exc_plain))

        exc_detail = AIException(ERR_AI_UNKNOWN_PROVIDER, "provider=foo")
        self.assertIn("Details: provider=foo", str(exc_detail))


class TestAIPackageAndConfig(unittest.TestCase):
    def test_package_exports_present(self) -> None:
        expected_symbols = [
            "AIDispatcher",
            "AI_Dispatcher",
            "AITranslator",
            "AI_Translator",
            "GeminiRestClient",
            "Gemini_Rest_Client",
            "GeminiInteractionsClient",
            "Gemini_Interactions_Client",
            "AIGlobalConfigManager",
            "AI_Global_Config_Manager",
            "ToolingRegistry",
            "Tooling_Registry",
            "ParserRegistry",
            "Parser_Registry",
            "ExtensionParserRegistry",
            "Extension_Parser_Registry",
            "RendererRegistry",
            "Renderer_Registry",
        ]
        for symbol in expected_symbols:
            self.assertTrue(hasattr(ai_pkg, symbol), f"Missing package export: {symbol}")

    def test_shipped_global_config_is_valid_bejson_105a(self) -> None:
        config_path = _AI_DIR / "config" / "ai_global_config.105a.bejson"
        self.assertTrue(config_path.is_file())
        result = validate_bejson(str(config_path), is_file=True)
        self.assertTrue(result.valid, f"Invalid config BEJSON: {result.errors}")


class TestAIModels(unittest.TestCase):
    def test_resolve_model_identifier_variants(self) -> None:
        self.assertEqual(Resolve_Model_Identifier("Gemini_3_1_Flash_Lite"), "gemini-3.1-flash-lite")
        self.assertEqual(Resolve_Model_Identifier("gemini_4_hydrogen"), "gemini-4-hydrogen")
        self.assertEqual(Resolve_Model_Identifier("models/gemini-4-argon"), "gemini-4-argon")
        self.assertEqual(Resolve_Model_Identifier("custom-model-v1"), "custom-model-v1")

    def test_list_active_gemini_models(self) -> None:
        models = List_Active_Gemini_Models()
        self.assertEqual(models, list(ACTIVE_TEXT_MODELS_REGISTRY.values()))
        self.assertGreaterEqual(len(models), 8)


class TestAIFeaturesCommon(unittest.TestCase):
    def test_bejson_105_request_and_response_pass_validator(self) -> None:
        req = build_bejson_105_ai_request(
            provider="geminirest",
            model="gemini-4-hydrogen",
            prompt="hello world",
            temperature=0.2,
            max_tokens=128,
        )
        req_val = validate_bejson(req, is_file=False)
        self.assertTrue(req_val.valid, f"Request failed BEJSON validation: {req_val.errors}")

        resp = build_bejson_105_ai_response(
            provider="geminirest",
            model="gemini-4-hydrogen",
            text="hi there",
            usage={"prompt_tokens": 2, "completion_tokens": 2, "total_tokens": 4},
        )
        resp_val = validate_bejson(resp, is_file=False)
        self.assertTrue(resp_val.valid, f"Response failed BEJSON validation: {resp_val.errors}")

    def test_redact_provider_error_text(self) -> None:
        raw = "HTTP 400 key=AIzaSyDummySecretValue1234567890ABCD " + ("x" * 600)
        redacted = redact_provider_error_text(raw, max_chars=200)
        self.assertNotIn("AIzaSyDummySecretValue", redacted)
        self.assertLessEqual(len(redacted), 220)


class TestAIEnvVaultAndKeys(unittest.TestCase):
    def test_vault_reads_secureenv_and_respects_allow_process_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_file = Path(tmpdir) / "secureenv_file.json"
            vault_file.write_text(json.dumps({"GEMINI_KEY_1": "AIzaVaultSecret1234567890"}), encoding="utf-8")

            vault = AIEnvVault()
            with mock.patch.dict(os.environ, {"GEMINI_KEY_2": "AIzaEnvSecret1234567890"}, clear=False):
                secrets_no_env = vault.get_all_secrets(vault_path=vault_file, allow_process_env=False)
                self.assertIn("GEMINI_KEY_1", secrets_no_env)
                self.assertNotIn("GEMINI_KEY_2", secrets_no_env)

                secrets_with_env = vault.get_all_secrets(vault_path=vault_file, allow_process_env=True)
                self.assertIn("GEMINI_KEY_1", secrets_with_env)
                self.assertIn("GEMINI_KEY_2", secrets_with_env)

    def test_mask_key_and_natural_sorting(self) -> None:
        self.assertEqual(mask_key(""), "<empty>")
        self.assertEqual(mask_key("12345678"), "***")
        self.assertEqual(mask_key("AIzaSy1234567890WXYZ"), "AIza...WXYZ")

        with tempfile.TemporaryDirectory() as tmpdir:
            vault_file = Path(tmpdir) / "secureenv_file.json"
            vault_file.write_text(
                json.dumps({
                    "GEMINI_KEY_10": "AIzaKeyTen1234567890",
                    "GEMINI_KEY_2": "AIzaKeyTwo1234567890",
                    "GEMINI_KEY_1": "AIzaKeyOne1234567890",
                }),
                encoding="utf-8",
            )
            handler = JITKeyHandler()
            pairs = handler.resolve_keys("geminirest", vault_path=vault_file, allow_process_env=False)
            self.assertEqual([name for name, _ in pairs], ["GEMINI_KEY_1", "GEMINI_KEY_2", "GEMINI_KEY_10"])

    def test_key_rotator_round_robin_exhaustion_and_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "rotator_state.105a.bejson"
            rotator = KeyRotator(cooldown_seconds=60.0, state_path=state_file)
            candidates = [("K1", "AIzaSecretOne123456789"), ("K2", "AIzaSecretTwo123456789")]

            n1, _ = rotator.select_next("geminirest", candidates, mask_key)
            n2, _ = rotator.select_next("geminirest", candidates, mask_key)
            self.assertEqual((n1, n2), ("K1", "K2"))

            rotator.mark_rate_limited("geminirest", "K1", cooldown_override=120.0)
            rotator.quarantine_key("geminirest", "K2")

            with self.assertRaises(AIException) as ctx:
                rotator.select_next("geminirest", candidates, mask_key)
            self.assertEqual(ctx.exception.code, ERR_AI_KEY_EXHAUSTED)

            stats = rotator.get_stats("geminirest")
            self.assertEqual(len(stats), 2)
            self.assertTrue(state_file.is_file())

            # Reload persisted state into a fresh KeyRotator instance
            rotator_reloaded = KeyRotator(cooldown_seconds=60.0, state_path=state_file)
            reloaded_stats = {row["key_name"]: row for row in rotator_reloaded.get_stats("geminirest")}
            self.assertTrue(reloaded_stats["K2"]["quarantined"])


class TestAIPreAndPostProcessors(unittest.TestCase):
    def test_preprocessor_gates(self) -> None:
        pre = AIPreprocessor(max_input_tokens=100, default_system_instruction="Base sys")
        with self.assertRaises(AIException) as ctx_empty:
            pre.process({"prompt": "   "})
        self.assertEqual(ctx_empty.exception.code, ERR_AI_PREPROCESS_REJECTED)

        with self.assertRaises(AIException) as ctx_xml:
            pre.process({"prompt": "<system_config>unclosed"})
        self.assertEqual(ctx_xml.exception.code, ERR_AI_XML_PARSE_FAILED)

        with self.assertRaises(AIException) as ctx_tok:
            pre.process({"prompt": "word " * 400})
        self.assertEqual(ctx_tok.exception.code, ERR_AI_TOKEN_LIMIT_EXCEEDED)

        out = pre.process({"prompt": "<system_config>Be concise.</system_config>Hello"})
        self.assertEqual(out["prompt"], "Hello")
        self.assertIn("Base sys", out["system_instruction"])
        self.assertIn("Be concise.", out["system_instruction"])

    def test_postprocessor_gates(self) -> None:
        post = AIPostprocessor(redact_api_keys=True, unwrap_xml_tag="answer", blocked_patterns=[r"FORBIDDEN_TOKEN"])

        with self.assertRaises(AIException) as ctx_empty:
            post.process({"text": "  "})
        self.assertEqual(ctx_empty.exception.code, ERR_AI_POSTPROCESS_REJECTED)

        with self.assertRaises(AIException) as ctx_blk:
            post.process({"text": "contains FORBIDDEN_TOKEN here"})
        self.assertEqual(ctx_blk.exception.code, ERR_AI_SANITIZER_BLOCKED)

        with self.assertRaises(AIException) as ctx_json:
            post.process({"text": "not json at all"}, expected_format="json")
        self.assertEqual(ctx_json.exception.code, ERR_AI_OUTPUT_VALIDATION_FAILED)

        out = post.process(
            {"text": "<answer>{\"ok\": true, \"leak\": \"AIzaSyDummyLeakValue1234567890\"}</answer>"},
            expected_format="json",
        )
        self.assertNotIn("AIzaSyDummyLeakValue", out["text"])
        self.assertEqual(out["structured_data"]["ok"], True)


class TestAITranslator(unittest.TestCase):
    def test_translator_gemini_rest_and_interactions_and_errors(self) -> None:
        translator = AITranslator()

        rest_payload = translator.to_provider_payload(
            "geminirest",
            {
                "messages": [
                    {"role": "user", "content": "Hi"},
                    {"role": "assistant", "content": "Hello"},
                ],
                "system_instruction": "Sys",
                "temperature": 0.3,
                "max_tokens": 50,
                "response_format": "json",
            },
        )
        self.assertEqual(rest_payload["contents"][0]["role"], "user")
        self.assertEqual(rest_payload["contents"][1]["role"], "model")
        self.assertEqual(rest_payload["generationConfig"]["responseMimeType"], "application/json")

        inter_payload = translator.to_provider_payload(
            "geminiinteractions",
            {
                "model": "gemini-4-hydrogen",
                "messages": [{"role": "tool", "name": "calc", "call_id": "c1", "content": "42"}],
            },
        )
        self.assertEqual(inter_payload["input"][0]["type"], "function_result")

        with self.assertRaises(AIException) as ctx_out:
            translator.to_provider_payload("unknown_provider", {"prompt": "hi"})
        self.assertEqual(ctx_out.exception.code, ERR_AI_UNKNOWN_PROVIDER)

        with self.assertRaises(AIException) as ctx_in:
            translator.from_provider_response("unknown_provider", {}, "m")
        self.assertEqual(ctx_in.exception.code, ERR_AI_UNKNOWN_PROVIDER)


class TestAIClientsBaseAndErrors(unittest.TestCase):
    def test_base_ai_client_abstract_and_health_check(self) -> None:
        with self.assertRaises(TypeError):
            BaseAIClient()  # type: ignore[abstract]

        class DummyClient(BaseAIClient):
            provider_name = "dummy"
            default_model = "dummy-1"

            def execute_call(
                self,
                provider_payload: Dict[str, Any],
                api_key: Optional[str] = None,
                model: Optional[str] = None,
                timeout: int = 60,
            ) -> Dict[str, Any]:
                return {"ok": True}

        client = DummyClient()
        hc = client.health_check()
        self.assertEqual(hc["provider"], "dummy")
        self.assertEqual(hc["status"], "ready")

    def test_gemini_rest_network_and_timeout_mapping(self) -> None:
        client = GeminiRestClient()
        with mock.patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            with self.assertRaises(AIException) as ctx_t:
                client.execute_call({"contents": []}, api_key="AIzaFakeKey1234567890")
            self.assertEqual(ctx_t.exception.code, ERR_AI_HTTP_TIMEOUT)

        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("dns fail")):
            with self.assertRaises(AIException) as ctx_n:
                client.execute_call({"contents": []}, api_key="AIzaFakeKey1234567890")
            self.assertEqual(ctx_n.exception.code, ERR_AI_HTTP_NETWORK_ERROR)

    def test_gemini_interactions_network_and_timeout_mapping(self) -> None:
        client = GeminiInteractionsClient()
        with mock.patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            with self.assertRaises(AIException) as ctx_t:
                client.execute_call({"input": []}, api_key="AIzaFakeKey1234567890")
            self.assertEqual(ctx_t.exception.code, ERR_AI_HTTP_TIMEOUT)

        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("dns fail")):
            with self.assertRaises(AIException) as ctx_n:
                client.execute_call({"input": []}, api_key="AIzaFakeKey1234567890")
            self.assertEqual(ctx_n.exception.code, ERR_AI_HTTP_NETWORK_ERROR)


class TestAIRegistriesAndDispatcherAccessors(unittest.TestCase):
    def test_tooling_and_renderer_missing_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = AIGlobalConfigManager(Path(tmpdir) / "cfg.105a.bejson")
            t_reg = ToolingRegistry(cfg)
            t_reg.set_enabled(True)
            t_reg.select_tooling_system("nonexistent_system")
            with self.assertRaises(AIException) as ctx_t:
                t_reg.get_active_system()
            self.assertEqual(ctx_t.exception.code, ERR_AI_TOOLING_SYSTEM_NOT_FOUND)

            r_reg = RendererRegistry(cfg)
            with self.assertRaises(AIException) as ctx_r:
                r_reg.select_renderer("nonexistent_renderer")
            self.assertEqual(ctx_r.exception.code, ERR_AI_RENDERER_NOT_FOUND)

    def test_dispatcher_accessors_on_empty_or_partial_envelopes(self) -> None:
        self.assertEqual(Get_Response_Text({}), "")
        self.assertIsNone(Get_Response_JSON({}))
        self.assertEqual(Get_Response_Usage({}), {})
        self.assertEqual(Get_Interaction_ID({}), "")
        self.assertEqual(Get_Tool_Calls({}), [])
        self.assertEqual(Get_Rendered_Output({}), "")
        self.assertIsNone(Get_Turn_Continuation_Command({}))

        dispatcher = AIDispatcher()
        self.assertIsNotNone(dispatcher.translator)


if __name__ == "__main__":
    unittest.main()
