"""
Library:         test_ai_core_geminirest_tools.py
Family:          AI_Core
Module Purpose:  Release 301 tests: geminirest carries tools, tool calls, tool results and verbatim wire parts
Architecture:    unittest, offline (injected transport), no network
Version:         1.0.0
Release_Version: 301
Date:            2026-11-17
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   5b0b9d0e-8f0d-4b8e-9f4e-0d6f3f8c2a11
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

_AI_DIR = Path(__file__).resolve().parent.parent
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from lib_bejson_AI_Core_client_geminirest import GeminiRestClient  # noqa: E402
from lib_bejson_AI_Core_dispatcher import AIDispatcher  # noqa: E402
from lib_bejson_AI_Core_errors import AIException, ERR_AI_POSTPROCESS_REJECTED, ERR_AI_TRANSLATION_FAILED  # noqa: E402
from lib_bejson_AI_Core_postprocessor import AIPostprocessor  # noqa: E402
from lib_bejson_AI_Core_tooling_interactions import InteractionsToolingSystem  # noqa: E402
from lib_bejson_AI_Core_tooling_registry import AIGlobalConfigManager, ToolingRegistry  # noqa: E402
from lib_bejson_AI_Core_translator import AITranslator  # noqa: E402

TEST_KEY = "AIzaSyMockTestKey1234567890"
DECLARATIONS = [{"name": "bash", "description": "Run a command.",
                 "parameters": {"type": "object", "properties": {"command": {"type": "string"}}}}]
FUNCTION_CALL_PARTS = [
    {"text": "Listing now."},
    {"functionCall": {"name": "bash", "args": {"command": "ls"}}, "thoughtSignature": "SIG-1"},
]


def _function_call_response() -> bytes:
    return json.dumps({
        "candidates": [{"content": {"parts": FUNCTION_CALL_PARTS}, "finishReason": "STOP"}],
        "usageMetadata": {"totalTokenCount": 7},
    }).encode("utf-8")


class TranslatorOutboundTests(unittest.TestCase):
    def setUp(self) -> None:
        self.translator = AITranslator()

    def test_tool_declarations_become_function_declarations(self) -> None:
        payload = self.translator.to_provider_payload(
            "geminirest", {"prompt": "hi", "tool_declarations": DECLARATIONS})
        declared = payload["tools"][0]["functionDeclarations"]
        self.assertEqual(declared[0]["name"], "bash")
        self.assertEqual(declared[0]["parameters"]["type"], "object")

    def test_generic_tools_key_is_never_forwarded_to_geminirest(self) -> None:
        payload = self.translator.to_provider_payload(
            "geminirest", {"prompt": "hi", "tools": [{"type": "function", "name": "x"}]})
        self.assertNotIn("tools", payload)

    def test_plain_messages_unchanged(self) -> None:
        payload = self.translator.to_provider_payload("geminirest", {"messages": [
            {"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]})
        self.assertEqual(payload["contents"], [
            {"role": "user", "parts": [{"text": "a"}]}, {"role": "model", "parts": [{"text": "b"}]}])

    def test_wire_parts_are_echoed_verbatim(self) -> None:
        payload = self.translator.to_provider_payload("geminirest", {"messages": [
            {"role": "user", "content": "go"},
            {"role": "assistant", "content": "ignored", "wire_parts": FUNCTION_CALL_PARTS},
        ]})
        self.assertEqual(payload["contents"][1]["parts"], FUNCTION_CALL_PARTS)
        self.assertEqual(payload["contents"][1]["parts"][1]["thoughtSignature"], "SIG-1")

    def test_tool_calls_without_wire_parts_become_function_calls(self) -> None:
        payload = self.translator.to_provider_payload("geminirest", {"messages": [
            {"role": "assistant", "content": "", "tool_calls": [{"name": "bash", "arguments": {"command": "ls"}}]}]})
        self.assertEqual(payload["contents"][0]["parts"], [{"functionCall": {"name": "bash", "args": {"command": "ls"}}}])

    def test_parallel_tool_results_share_one_user_content(self) -> None:
        payload = self.translator.to_provider_payload("geminirest", {"messages": [
            {"role": "tool", "name": "bash", "call_id": "c1", "content": "one"},
            {"role": "tool", "name": "read_file", "call_id": "c2", "content": "two"}]})
        self.assertEqual(len(payload["contents"]), 1)
        parts = payload["contents"][0]["parts"]
        self.assertEqual([p["functionResponse"]["name"] for p in parts], ["bash", "read_file"])
        self.assertEqual(parts[1]["functionResponse"]["response"], {"call_id": "c2", "output": "two"})

    def test_temperature_and_max_tokens_still_carried(self) -> None:
        payload = self.translator.to_provider_payload(
            "geminirest", {"prompt": "x", "temperature": 0.2, "max_tokens": 64})
        self.assertEqual(payload["generationConfig"], {"temperature": 0.2, "maxOutputTokens": 64})


class TranslatorInboundTests(unittest.TestCase):
    def setUp(self) -> None:
        self.translator = AITranslator()

    def test_function_calls_and_wire_parts_extracted(self) -> None:
        envelope = self.translator.from_provider_response(
            "geminirest", json.loads(_function_call_response()), "m")
        self.assertEqual(envelope["tool_calls"], [{"id": "", "name": "bash", "arguments": {"command": "ls"}}])
        self.assertEqual(envelope["wire_parts"], FUNCTION_CALL_PARTS)
        self.assertEqual(envelope["text"], "Listing now.")

    def test_text_only_response_has_no_tool_keys(self) -> None:
        envelope = self.translator.from_provider_response(
            "geminirest", {"candidates": [{"content": {"parts": [{"text": "hi"}]}}]}, "m")
        self.assertNotIn("tool_calls", envelope)
        self.assertNotIn("wire_parts", envelope)

    def test_malformed_function_calls_fail_loudly(self) -> None:
        for bad_part in ({"functionCall": {}}, {"functionCall": {"name": "bash", "args": "ls"}}, {"functionCall": "x"}):
            with self.assertRaises(AIException) as raised:
                self.translator.from_provider_response(
                    "geminirest", {"candidates": [{"content": {"parts": [bad_part]}}]}, "m")
            self.assertEqual(raised.exception.code, ERR_AI_TRANSLATION_FAILED)

    def test_round_trip_wire_parts_survive_next_request(self) -> None:
        envelope = self.translator.from_provider_response(
            "geminirest", json.loads(_function_call_response()), "m")
        next_payload = self.translator.to_provider_payload("geminirest", {"messages": [
            {"role": "user", "content": "go"},
            {"role": "assistant", "content": envelope["text"], "wire_parts": envelope["wire_parts"]},
            {"role": "tool", "name": "bash", "call_id": "x", "content": "out"}]})
        self.assertEqual(next_payload["contents"][1]["parts"], FUNCTION_CALL_PARTS)
        self.assertIn("functionResponse", next_payload["contents"][2]["parts"][0])


class PostprocessorTests(unittest.TestCase):
    def test_tool_call_only_turn_is_accepted(self) -> None:
        cleaned = AIPostprocessor().process({"text": "", "tool_calls": [{"name": "bash"}]})
        self.assertEqual(cleaned["tool_calls"][0]["name"], "bash")

    def test_empty_text_without_tool_calls_still_rejected(self) -> None:
        with self.assertRaises(AIException) as raised:
            AIPostprocessor().process({"text": "  "})
        self.assertEqual(raised.exception.code, ERR_AI_POSTPROCESS_REJECTED)


class DispatcherToolLoopSwitchTests(unittest.TestCase):
    def _dispatcher(self, transport, tooling_active: bool, executed: List[Dict[str, Any]]):
        config_path = Path(self._tmp.name) / "cfg.105a.bejson"
        registry = ToolingRegistry(config_manager_instance=AIGlobalConfigManager(config_target_file_path=config_path))
        if tooling_active:
            registry.set_enabled(True)
            tooling_system = InteractionsToolingSystem()
            tooling_system.register_tool(
                {"type": "function", "name": "bash", "description": "d", "parameters": {"type": "object", "properties": {}}},
                lambda arguments: executed.append(arguments) or {"ran": True})
            registry.register_tooling_system(tooling_system)
        dispatcher = AIDispatcher(tooling_registry=registry, auto_register_defaults=False)
        dispatcher.register_provider(GeminiRestClient(transport=transport))
        return dispatcher

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def test_disabled_loop_never_executes_tools_even_with_tooling_active(self) -> None:
        requests: List[Dict[str, Any]] = []
        executed: List[Dict[str, Any]] = []

        def transport(request_object, timeout_seconds):
            requests.append(json.loads(request_object.data.decode("utf-8")))
            return _function_call_response()

        dispatcher = self._dispatcher(transport, tooling_active=True, executed=executed)
        envelope = dispatcher.dispatch(
            {"messages": [{"role": "user", "content": "ls"}], "tool_declarations": DECLARATIONS},
            provider="geminirest", model="gemini-2.5-flash", explicit_keys=[TEST_KEY], tool_loop_enabled=False)
        self.assertEqual(executed, [])
        self.assertEqual(len(requests), 1)
        self.assertEqual(envelope["tool_calls"][0]["name"], "bash")
        self.assertEqual(envelope["wire_parts"], FUNCTION_CALL_PARTS)
        self.assertEqual(requests[0]["tools"][0]["functionDeclarations"][0]["name"], "bash")

    def test_disabled_loop_does_not_inject_interactions_tools(self) -> None:
        requests: List[Dict[str, Any]] = []

        def transport(request_object, timeout_seconds):
            requests.append(json.loads(request_object.data.decode("utf-8")))
            return json.dumps({"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}).encode("utf-8")

        dispatcher = self._dispatcher(transport, tooling_active=True, executed=[])
        dispatcher.dispatch({"prompt": "hi"}, provider="geminirest", model="gemini-2.5-flash",
                            explicit_keys=[TEST_KEY], tool_loop_enabled=False)
        self.assertNotIn("tools", requests[0])

    def test_async_passes_switch_through(self) -> None:
        import asyncio
        executed: List[Dict[str, Any]] = []
        dispatcher = self._dispatcher(lambda r, t: _function_call_response(), tooling_active=True, executed=executed)
        envelope = asyncio.run(dispatcher.dispatch_async(
            {"prompt": "x"}, provider="geminirest", model="gemini-2.5-flash",
            explicit_keys=[TEST_KEY], tool_loop_enabled=False))
        self.assertEqual(executed, [])
        self.assertEqual(len(envelope["tool_calls"]), 1)


if __name__ == "__main__":
    unittest.main()
