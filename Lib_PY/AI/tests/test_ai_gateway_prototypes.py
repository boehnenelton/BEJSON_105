"""
Test Suite:      test_ai_gateway_prototypes.py
Family:          AI
Purpose:         Unit & integration tests for BEJSON 105 Multi-AI Gateway prototypes (Gemini REST)
Version:         1.2.0
Release_Version: 300
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:   f4a1c34a-7e1c-4360-e36d-2b5c7d1f3012
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

_AI_DIR = Path(__file__).resolve().parent.parent
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from lib_bejson_AI_bejson_errors import (  # noqa: E402
    AIException,
    ERR_AI_KEY_EXHAUSTED,
    ERR_AI_KEY_MISSING,
    ERR_AI_OUTPUT_VALIDATION_FAILED,
    ERR_AI_PROVIDER_NOT_REGISTERED,
    ERR_AI_TOKEN_LIMIT_EXCEEDED,
    ERR_AI_XML_PARSE_FAILED,
)
from lib_bejson_ai_client_geminiinteractions import GeminiInteractionsClient  # noqa: E402
from lib_bejson_ai_client_geminirest import GeminiRestClient  # noqa: E402
from lib_bejson_ai_dispatcher import (  # noqa: E402
    AIDispatcher,
    Get_Interaction_ID,
    Get_Response_JSON,
    Get_Response_Text,
    Get_Response_Usage,
    Get_Tool_Calls,
    Get_Turn_Continuation_Command,
)
from lib_bejson_ai_env_vault import AIEnvVault  # noqa: E402
from lib_bejson_ai_extension_parser import (  # noqa: E402
    Base_Extension_Module_Parser,
    BaseExtensionModuleParser,
    Extension_Parser_Registry,
    ExtensionParserRegistry,
)
from lib_bejson_ai_features_common import build_bejson_105_ai_request  # noqa: E402
from lib_bejson_ai_jit_key_handler import JITKeyHandler, mask_key  # noqa: E402
from lib_bejson_ai_key_rotator import KeyRotator  # noqa: E402
from lib_bejson_ai_parser_base import (  # noqa: E402
    Base_Modular_Parser,
    BaseModularParser,
)
from lib_bejson_ai_parser_registry import (  # noqa: E402
    Parser_Registry,
    ParserRegistry,
)
from lib_bejson_ai_postprocessor import AIPostprocessor  # noqa: E402
from lib_bejson_ai_preprocessor import AIPreprocessor  # noqa: E402
from lib_bejson_ai_tooling_base import BaseToolingSystem, Base_Tooling_System  # noqa: E402
from lib_bejson_ai_tooling_interactions import (  # noqa: E402
    InteractionsToolingSystem,
    Interactions_Tooling_System,
)
from lib_bejson_ai_tooling_registry import (  # noqa: E402
    AIGlobalConfigManager,
    AI_Global_Config_Manager,
    ToolingRegistry,
    Tooling_Registry,
)


class TestAIGatewayPrototypes(unittest.TestCase):
    def test_bejson_105_request_and_gemini_rest_roundtrip(self) -> None:
        captured = {}

        def mock_transport(req, timeout):
            captured["url"] = req.full_url
            captured["headers"] = dict(req.header_items())
            captured["body"] = json.loads(req.data.decode("utf-8"))
            resp = {
                "candidates": [
                    {
                        "content": {"parts": [{"text": '```json\n{"status": "ok", "tier": 3}\n```'}]},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 12, "candidatesTokenCount": 9},
            }
            return json.dumps(resp).encode("utf-8")

        dispatcher = AIDispatcher()
        dispatcher.register_provider(GeminiRestClient(transport=mock_transport))

        bejson_req = build_bejson_105_ai_request(
            prompt="<system_config>Return JSON only.</system_config>Check gateway health.",
            provider="geminirest",
            model="gemini-2.5-flash",
            response_format="json",
        )
        bejson_resp = dispatcher.dispatch(
            bejson_req,
            explicit_keys=["AIzaSyMockTestKey1234567890"],
            return_bejson_105=True,
        )

        self.assertEqual(bejson_resp["Format"], "BEJSON")
        self.assertEqual(bejson_resp["Format_Version"], "105")
        self.assertEqual(bejson_resp["Record_Type_Parent"], "AI_Response")
        self.assertTrue(all("field_uuid" in f for f in bejson_resp["Fields"]))
        self.assertEqual(len(bejson_resp["Values"][0]), len(bejson_resp["Fields"]) + 1)
        self.assertIn("X-goog-api-key", captured["headers"])
        self.assertNotIn("AIzaSyMockTestKey1234567890", captured["url"])
        self.assertEqual(captured["body"]["systemInstruction"]["parts"][0]["text"], "Return JSON only.")
        self.assertEqual(captured["body"]["contents"][0]["parts"][0]["text"], "Check gateway health.")

    def test_definitions_json_resolves_secureenv_and_rotates_numbered_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sec_path = tmp_path / "secureenv_file.json"
            def_path = tmp_path / "definitions.json"
            state_path = tmp_path / "key_rotation_state.105a.bejson"

            sec_data = {
                "Format": "BEJSON",
                "Format_Version": "104a",
                "Schema_Name": "GlobalEnv",
                "Fields": [
                    {"name": "var_name", "type": "string"},
                    {"name": "var_value", "type": "string"},
                    {"name": "var_type", "type": "string"},
                ],
                "Values": [
                    ["GEMINI_KEY_10", "AIzaSyKeyTen1010101010", "secret"],
                    ["GEMINI_KEY_2", "AIzaSyKeyTwo2222222222", "secret"],
                    ["GEMINI_KEY_1", "AIzaSyKeyOne1111111111", "secret"],
                ],
            }
            sec_path.write_text(json.dumps(sec_data), encoding="utf-8")

            def_data = {
                "Format": "BEJSON",
                "Format_Version": "104a",
                "Schema_Name": "UserPaths",
                "Fields": [
                    {"name": "var_name", "type": "string"},
                    {"name": "var_value", "type": "string"},
                    {"name": "var_type", "type": "string"},
                    {"name": "Type", "type": "string"},
                ],
                "Values": [
                    ["SECUREENV_FILE", str(sec_path), "string", "Path"],
                    ["ADMIN_LIBRARIES_105", "/storage/emulated/0/Admin/Libraries/libraries_105", "string", "Path"],
                ],
            }
            def_path.write_text(json.dumps(def_data), encoding="utf-8")

            vault = AIEnvVault(script_path=tmp_path, definitions_path=def_path)
            rotator = KeyRotator(cooldown_seconds=30.0, state_path=state_path)
            jit = JITKeyHandler(vault=vault, rotator=rotator)

            seen_keys = []

            def rotating_transport(req, timeout):
                key = req.get_header("X-goog-api-key")
                seen_keys.append(key)
                if key == "AIzaSyKeyOne1111111111":
                    raise urllib.error.HTTPError(
                        url=req.full_url,
                        code=429,
                        msg="Too Many Requests",
                        hdrs={},
                        fp=io.BytesIO(b'{"error": "rate limited"}'),
                    )
                return json.dumps(
                    {"candidates": [{"content": {"parts": [{"text": f"OK via {mask_key(key)}"}]}, "finishReason": "STOP"}]}
                ).encode("utf-8")

            dispatcher = AIDispatcher(key_handler=jit)
            dispatcher.register_provider(GeminiRestClient(transport=rotating_transport))

            r1 = dispatcher.dispatch({"prompt": "Ping 1"})
            self.assertEqual(r1["text"], "OK via AIza...2222")

            r2 = dispatcher.dispatch({"prompt": "Ping 2"})
            self.assertEqual(r2["text"], "OK via AIza...1010")

            self.assertEqual(
                seen_keys,
                ["AIzaSyKeyOne1111111111", "AIzaSyKeyTwo2222222222", "AIzaSyKeyTen1010101010"],
            )

            stats = {s["key_name"]: s for s in jit.get_key_stats()}
            self.assertEqual(stats["GEMINI_KEY_1"]["rate_limits"], 1)
            self.assertTrue(stats["GEMINI_KEY_1"]["in_cooldown"])
            self.assertEqual(stats["GEMINI_KEY_2"]["successes"], 1)
            self.assertEqual(stats["GEMINI_KEY_10"]["successes"], 1)

            # Verify persisted BEJSON 105a state contains masked keys only
            self.assertTrue(state_path.is_file())
            persisted = state_path.read_text(encoding="utf-8")
            self.assertNotIn("AIzaSyKeyOne1111111111", persisted)
            self.assertIn("AIza...1111", persisted)

    def test_quarantine_on_401_auth_failure(self) -> None:
        def auth_fail_on_first_transport(req, timeout):
            key = req.get_header("X-goog-api-key")
            if key == "AIzaSyBadKey1111111111":
                raise urllib.error.HTTPError(
                    url=req.full_url,
                    code=401,
                    msg="Unauthorized",
                    hdrs={},
                    fp=io.BytesIO(b'{"error": "invalid key"}'),
                )
            return json.dumps(
                {"candidates": [{"content": {"parts": [{"text": "OK via good key"}]}, "finishReason": "STOP"}]}
            ).encode("utf-8")

        jit = JITKeyHandler()
        jit.vault.get_all_secrets = lambda vault_path=None, allow_process_env=True: {}  # type: ignore[method-assign]
        dispatcher = AIDispatcher(key_handler=jit)
        dispatcher.register_provider(GeminiRestClient(transport=auth_fail_on_first_transport))

        dispatched_execution_response = dispatcher.dispatch(
            {"prompt": "Hello"},
            explicit_keys=["AIzaSyBadKey1111111111", "AIzaSyGoodKey222222222"],
        )
        self.assertEqual(dispatched_execution_response["text"], "OK via good key")
        stats = {s["key_name"]: s for s in jit.get_key_stats()}
        self.assertTrue(stats["EXPLICIT_KEY_1"]["quarantined"])
        self.assertFalse(stats["EXPLICIT_KEY_2"]["quarantined"])

        # If all keys are quarantined, raises ERR_AI_KEY_EXHAUSTED
        jit.quarantine_key("AIzaSyGoodKey222222222")
        with self.assertRaises(AIException) as ctx:
            dispatcher.dispatch(
                {"prompt": "Hello"},
                explicit_keys=["AIzaSyBadKey1111111111", "AIzaSyGoodKey222222222"],
            )
        self.assertEqual(ctx.exception.code, ERR_AI_KEY_EXHAUSTED)

    def test_definitions_py_safe_ast_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_test_directory_path:
            tmp_path = Path(temporary_test_directory_path)
            def_py = tmp_path / "definitions.py"
            def_py.write_text(
                'SECUREENV_FILE = "/tmp/nonexistent_sec.json"\nADMIN_ROOT = "/storage/emulated/0/Admin"\n',
                encoding="utf-8",
            )
            vault = AIEnvVault(script_path=tmp_path, definitions_path=def_py)
            self.assertEqual(vault.get_path("ADMIN_ROOT"), "/storage/emulated/0/Admin")

    def test_preprocessor_and_postprocessor_gates(self) -> None:
        pre = AIPreprocessor(max_input_tokens=5)
        with self.assertRaises(AIException) as ctx_tok:
            pre.process({"prompt": "This prompt is definitely longer than twenty characters."})
        self.assertEqual(ctx_tok.exception.code, ERR_AI_TOKEN_LIMIT_EXCEEDED)

        with self.assertRaises(AIException) as ctx_xml:
            pre.process({"prompt": "<system_config>unclosed"})
        self.assertEqual(ctx_xml.exception.code, ERR_AI_XML_PARSE_FAILED)

        post = AIPostprocessor(redact_api_keys=True)
        cleaned = post.process({"text": "Leaked AIzaSySecretKey12345678901234567 here"})
        self.assertEqual(cleaned["text"], "Leaked [REDACTED_API_KEY] here")

        with self.assertRaises(AIException) as ctx_json:
            post.process({"text": "Not valid JSON"}, expected_format="json")
        self.assertEqual(ctx_json.exception.code, ERR_AI_OUTPUT_VALIDATION_FAILED)

    def test_missing_key_and_unregistered_provider_errors(self) -> None:
        dispatcher = AIDispatcher()
        with self.assertRaises(AIException) as ctx_prov:
            dispatcher.dispatch({"prompt": "hi"}, provider="openrouter")
        self.assertEqual(ctx_prov.exception.code, ERR_AI_PROVIDER_NOT_REGISTERED)

        empty_vault = AIEnvVault(script_path=Path(tempfile.gettempdir()) / "nonexistent_bejson_vault_dir")
        jit = JITKeyHandler(vault=empty_vault)
        jit.vault.get_all_secrets = lambda vault_path=None, allow_process_env=True: {}  # type: ignore[method-assign]
        d2 = AIDispatcher(key_handler=jit)
        with self.assertRaises(AIException) as ctx_key:
            d2.dispatch({"prompt": "hi"})
        self.assertEqual(ctx_key.exception.code, ERR_AI_KEY_MISSING)

    def test_discover_providers(self) -> None:
        dispatcher = AIDispatcher()
        self.assertEqual(dispatcher.list_providers(), ["geminiinteractions", "geminirest"])
        discovered = dispatcher.discover_providers()
        self.assertIn("geminirest", discovered)
        self.assertIn("geminiinteractions", discovered)

    def test_name_case_models_and_model_resolver(self) -> None:
        from lib_bejson_ai_models import (
            Gemini_3_1_Flash_Lite,
            Gemini_4_Hydrogen,
            List_Active_Gemini_Models,
            Resolve_Model_Identifier,
        )

        self.assertEqual(Resolve_Model_Identifier("Gemini_3_1_Flash_Lite"), "gemini-3.1-flash-lite")
        self.assertEqual(Resolve_Model_Identifier("Gemini_4_Hydrogen"), "gemini-4-hydrogen")
        self.assertEqual(Resolve_Model_Identifier("models/gemini-4-argon"), "gemini-4-argon")
        active_models_catalog_list = List_Active_Gemini_Models()
        self.assertIn(Gemini_3_1_Flash_Lite, active_models_catalog_list)
        self.assertIn(Gemini_4_Hydrogen, active_models_catalog_list)

    def test_stdout_routing_and_retrieval_functions(self) -> None:
        import io
        from lib_bejson_ai_dispatcher import (
            Get_Response_JSON,
            Get_Response_Text,
            Get_Response_Usage,
        )

        captured_stream_buffer = io.StringIO()

        def mock_stdout_transport(api_request_object, timeout_seconds_metric):
            mock_network_response_payload = {
                "candidates": [
                    {
                        "content": {"parts": [{"text": '{"result": "success", "status": "active"}'}]},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 8, "candidatesTokenCount": 6},
            }
            return json.dumps(mock_network_response_payload).encode("utf-8")

        mock_gemini_client = GeminiRestClient(transport=mock_stdout_transport)
        test_dispatcher_instance = AIDispatcher()
        test_dispatcher_instance.register_provider(mock_gemini_client)

        dispatched_test_response = test_dispatcher_instance.dispatch(
            {"prompt": "Generate status JSON", "response_format": "json"},
            explicit_keys=["AIzaSyMockTestKey1234567890"],
            stdout_routing=True,
            output_sink=captured_stream_buffer,
        )

        retrieved_response_text_str = Get_Response_Text(dispatched_test_response)
        self.assertIn("success", retrieved_response_text_str)
        self.assertIn("success", captured_stream_buffer.getvalue())

        retrieved_structured_json_dict = Get_Response_JSON(dispatched_test_response)
        self.assertIsInstance(retrieved_structured_json_dict, dict)
        self.assertEqual(retrieved_structured_json_dict.get("result"), "success")

        retrieved_token_usage_dict = Get_Response_Usage(dispatched_test_response)
        self.assertEqual(retrieved_token_usage_dict.get("promptTokenCount"), 8)

    def test_async_dispatch_non_blocking(self) -> None:
        import asyncio
        from lib_bejson_ai_dispatcher import Get_Response_Text

        def mock_async_transport(api_request_object, timeout_seconds_metric):
            mock_payload = {
                "candidates": [
                    {
                        "content": {"parts": [{"text": "Async execution successful"}]},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 4},
            }
            return json.dumps(mock_payload).encode("utf-8")

        mock_gemini_client = GeminiRestClient(transport=mock_async_transport)
        test_dispatcher_instance = AIDispatcher()
        test_dispatcher_instance.register_provider(mock_gemini_client)

        async def run_async_evaluation_coroutine():
            async_dispatched_response_dict = await test_dispatcher_instance.dispatch_async(
                {"prompt": "Run async non-blocking task"},
                explicit_keys=["AIzaSyMockTestKey1234567890"],
            )
            return Get_Response_Text(async_dispatched_response_dict)

        async_execution_result_text_str = asyncio.run(run_async_evaluation_coroutine())
        self.assertEqual(async_execution_result_text_str, "Async execution successful")

    def test_global_config_auto_export_and_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory_path_str:
            target_config_file_path = Path(temporary_directory_path_str) / "test_ai_global_config.105a.bejson"
            self.assertFalse(target_config_file_path.exists())

            configuration_manager_instance = AI_Global_Config_Manager(config_target_file_path=target_config_file_path)
            self.assertTrue(target_config_file_path.exists())
            self.assertFalse(configuration_manager_instance.Is_Tooling_Enabled())
            self.assertEqual(configuration_manager_instance.Get_Active_Tooling_System_Name(), "interactions_tools")

            parsed_exported_document_dict = json.loads(target_config_file_path.read_text(encoding="utf-8"))
            self.assertEqual(parsed_exported_document_dict["Format"], "BEJSON")
            self.assertEqual(parsed_exported_document_dict["Format_Version"], "105a")
            self.assertEqual(parsed_exported_document_dict["Records_Type"], ["AIGlobalConfig"])

            configuration_manager_instance.Update_Setting("tooling_enabled", True)
            configuration_manager_instance.Update_Setting("max_tool_roundtrips", 7)
            self.assertTrue(configuration_manager_instance.Is_Tooling_Enabled())

            reloaded_configuration_manager = AIGlobalConfigManager(config_target_file_path=target_config_file_path)
            self.assertTrue(reloaded_configuration_manager.is_tooling_enabled())
            self.assertEqual(reloaded_configuration_manager.get_setting("max_tool_roundtrips"), 7)

    def test_tooling_gate_disabled_bypasses_tools(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory_path_str:
            target_config_file_path = Path(temporary_directory_path_str) / "disabled_config.105a.bejson"
            configuration_manager_instance = Tooling_Registry(
                config_manager_instance=AIGlobalConfigManager(config_target_file_path=target_config_file_path)
            )
            configuration_manager_instance.set_enabled(False)
            self.assertIsNone(configuration_manager_instance.Get_Active_System())

            captured_network_request_container = {}

            def mock_interactions_transport(request_payload_object, timeout_seconds_metric):
                captured_network_request_container["payload"] = json.loads(request_payload_object.data.decode("utf-8"))
                mock_response_payload = {
                    "id": "interaction-disabled-gate-001",
                    "status": "completed",
                    "steps": [
                        {
                            "type": "model_output",
                            "content": [{"type": "text", "text": "Direct response without tools."}],
                        }
                    ],
                }
                return json.dumps(mock_response_payload).encode("utf-8")

            interactions_client_instance = GeminiInteractionsClient(transport=mock_interactions_transport)
            test_dispatcher_instance = AIDispatcher(tooling_registry_instance=configuration_manager_instance)
            test_dispatcher_instance.register_provider(interactions_client_instance)

            dispatched_execution_response = test_dispatcher_instance.dispatch(
                {"prompt": "Calculate 5 + 5", "provider": "geminiinteractions"},
                explicit_keys=["AIzaSyMockTestKey1234567890"],
            )

            self.assertNotIn("tools", captured_network_request_container["payload"])
            self.assertEqual(Get_Response_Text(dispatched_execution_response), "Direct response without tools.")

    def test_tooling_gate_enabled_with_switchable_system(self) -> None:
        class MockAlternativeToolingSystem(BaseToolingSystem):
            system_name: str = "mock_command_tools"

            def is_enabled(self) -> bool:
                return True

            def register_tool(self, tool_declaration_schema_dict, tool_execution_handler_callable=None) -> None:
                pass

            def list_registered_tool_names(self) -> List[str]:
                return ["mock_shell_executor"]

            def build_provider_tools(self, requested_tool_identifiers_list=None) -> List[Dict[str, Any]]:
                return [{"type": "cli_command", "name": "mock_shell_executor"}]

            def execute_tool_call(self, tool_call_invocation_payload) -> Dict[str, Any]:
                return {"type": "command_result", "output": "execution_successful"}

        with tempfile.TemporaryDirectory() as temporary_directory_path_str:
            target_config_file_path = Path(temporary_directory_path_str) / "switchable_config.105a.bejson"
            tooling_registry_instance = Tooling_Registry(
                config_manager_instance=AIGlobalConfigManager(config_target_file_path=target_config_file_path)
            )
            tooling_registry_instance.Set_Enabled(True)

            interactions_tooling_subsystem = Interactions_Tooling_System()
            mock_alternative_tooling_subsystem = MockAlternativeToolingSystem()

            tooling_registry_instance.Register_Tooling_System(interactions_tooling_subsystem)
            tooling_registry_instance.Register_Tooling_System(mock_alternative_tooling_subsystem)

            registered_subsystem_names_list = tooling_registry_instance.List_Tooling_Systems()
            self.assertIn("interactions_tools", registered_subsystem_names_list)
            self.assertIn("mock_command_tools", registered_subsystem_names_list)

            # Switch to non-interactions system
            tooling_registry_instance.Select_Tooling_System("mock_command_tools")
            active_tooling_subsystem = tooling_registry_instance.Get_Active_System()
            self.assertIsNotNone(active_tooling_subsystem)
            self.assertEqual(active_tooling_subsystem.system_name, "mock_command_tools")

            # Switch back to interactions
            tooling_registry_instance.Select_Tooling_System("interactions_tools")
            reverted_tooling_subsystem = tooling_registry_instance.Get_Active_System()
            self.assertIsNotNone(reverted_tooling_subsystem)
            self.assertEqual(reverted_tooling_subsystem.system_name, "interactions_tools")

    def test_gemini_interactions_roundtrip_and_tool_call_loop(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory_path_str:
            target_config_file_path = Path(temporary_directory_path_str) / "interactions_loop_config.105a.bejson"
            tooling_registry_instance = ToolingRegistry(
                config_manager_instance=AIGlobalConfigManager(config_target_file_path=target_config_file_path)
            )
            tooling_registry_instance.set_enabled(True)

            interactions_tooling_subsystem = InteractionsToolingSystem()

            # Dynamic test verification tool (NOT in library)
            test_arithmetic_tool_declaration = {
                "type": "function",
                "name": "arithmetic_calculator",
                "description": "Calculates the sum of two integer values.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "left_operand_number": {"type": "integer"},
                        "right_operand_number": {"type": "integer"},
                    },
                    "required": ["left_operand_number", "right_operand_number"],
                },
            }

            def test_arithmetic_handler(tool_arguments_payload: Dict[str, Any]) -> Dict[str, Any]:
                left_operand_value = int(tool_arguments_payload.get("left_operand_number", 0))
                right_operand_value = int(tool_arguments_payload.get("right_operand_number", 0))
                return {"computed_sum": left_operand_value + right_operand_value}

            interactions_tooling_subsystem.register_tool(
                test_arithmetic_tool_declaration,
                test_arithmetic_handler,
            )
            tooling_registry_instance.register_tooling_system(interactions_tooling_subsystem)

            recorded_network_requests_list: List[Dict[str, Any]] = []

            def mock_multi_turn_transport(request_payload_object, timeout_seconds_metric):
                parsed_request_body = json.loads(request_payload_object.data.decode("utf-8"))
                recorded_network_requests_list.append(parsed_request_body)

                # Turn 1: Model calls the test tool
                if len(recorded_network_requests_list) == 1:
                    return json.dumps({
                        "id": "interaction-session-turn-1",
                        "status": "action_required",
                        "steps": [
                            {
                                "type": "function_call",
                                "id": "call-arithmetic-999",
                                "name": "arithmetic_calculator",
                                "arguments": {
                                    "left_operand_number": 19,
                                    "right_operand_number": 23,
                                },
                            }
                        ],
                    }).encode("utf-8")

                # Turn 2: Model receives tool result and produces final output
                return json.dumps({
                    "id": "interaction-session-turn-2",
                    "status": "completed",
                    "steps": [
                        {
                            "type": "model_output",
                            "content": [{"type": "text", "text": "The calculated arithmetic sum is 42."}],
                        }
                    ],
                }).encode("utf-8")

            interactions_client_instance = GeminiInteractionsClient(transport=mock_multi_turn_transport)
            test_dispatcher_instance = AIDispatcher(tooling_registry_instance=tooling_registry_instance)
            test_dispatcher_instance.register_provider(interactions_client_instance)

            dispatched_execution_response = test_dispatcher_instance.dispatch(
                {"prompt": "Please compute 19 + 23", "provider": "geminiinteractions"},
                explicit_keys=["AIzaSyMockTestKey1234567890"],
            )

            # Assert 2 roundtrips occurred
            self.assertEqual(len(recorded_network_requests_list), 2)

            # Assert Turn 1 sent tools declaration
            first_turn_payload_dict = recorded_network_requests_list[0]
            self.assertIn("tools", first_turn_payload_dict)
            self.assertEqual(first_turn_payload_dict["tools"][0]["name"], "arithmetic_calculator")

            # Assert Turn 2 provided function_result feedback with previous_interaction_id
            second_turn_payload_dict = recorded_network_requests_list[1]
            self.assertEqual(second_turn_payload_dict.get("previous_interaction_id"), "interaction-session-turn-1")
            second_turn_inputs_list = second_turn_payload_dict.get("input", [])
            self.assertEqual(second_turn_inputs_list[0]["type"], "function_result")
            self.assertEqual(second_turn_inputs_list[0]["call_id"], "call-arithmetic-999")
            self.assertIn("42", second_turn_inputs_list[0]["result"][0]["text"])

            # Assert final extracted response text and interaction ID
            self.assertEqual(Get_Response_Text(dispatched_execution_response), "The calculated arithmetic sum is 42.")
            self.assertEqual(Get_Interaction_ID(dispatched_execution_response), "interaction-session-turn-2")

    def test_gemini_interactions_key_rotation_on_429(self) -> None:
        recorded_request_keys_list: List[str] = []

        def mock_rate_limited_interactions_transport(request_payload_object, timeout_seconds_metric):
            used_api_key_header_value = request_payload_object.get_header("X-goog-api-key")
            recorded_request_keys_list.append(used_api_key_header_value)
            if len(recorded_request_keys_list) == 1:
                raise urllib.error.HTTPError(
                    url=request_payload_object.full_url,
                    code=429,
                    msg="Too Many Requests",
                    hdrs=request_payload_object.headers,
                    fp=io.BytesIO(b'{"error": {"code": 429, "message": "Resource has been exhausted"}}'),
                )
            mock_success_response = {
                "id": "interaction-rotated-key-success",
                "status": "completed",
                "steps": [
                    {
                        "type": "model_output",
                        "content": [{"type": "text", "text": "Recovered on rotated key."}],
                    }
                ],
            }
            return json.dumps(mock_success_response).encode("utf-8")

        interactions_client_instance = GeminiInteractionsClient(transport=mock_rate_limited_interactions_transport)
        test_dispatcher_instance = AIDispatcher()
        test_dispatcher_instance.register_provider(interactions_client_instance)

        dispatched_execution_response = test_dispatcher_instance.dispatch(
            {"prompt": "Test rotation", "provider": "geminiinteractions"},
            explicit_keys=["AIzaSyPrimaryMockKey111", "AIzaSySecondaryMockKey222"],
        )

        self.assertEqual(len(recorded_request_keys_list), 2)
        self.assertEqual(recorded_request_keys_list[0], "AIzaSyPrimaryMockKey111")
        self.assertEqual(recorded_request_keys_list[1], "AIzaSySecondaryMockKey222")
        self.assertEqual(Get_Response_Text(dispatched_execution_response), "Recovered on rotated key.")

    def test_parser_registry_and_extension_parser_config_toggles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory_path_str:
            target_config_file_path = Path(temporary_directory_path_str) / "parser_config.105a.bejson"
            configuration_manager_instance = AIGlobalConfigManager(config_target_file_path=target_config_file_path)

            self.assertFalse(configuration_manager_instance.Is_Global_Pre_Parser_Enabled())
            self.assertFalse(configuration_manager_instance.Is_Global_Post_Parser_Enabled())
            self.assertFalse(configuration_manager_instance.Is_Extension_Parser_Enabled())

            configuration_manager_instance.Set_Global_Pre_Parser_Enabled(True)
            configuration_manager_instance.Set_Global_Post_Parser_Enabled(True)
            configuration_manager_instance.Set_Extension_Parser_Enabled(True)

            self.assertTrue(configuration_manager_instance.is_global_pre_parser_enabled())
            self.assertTrue(configuration_manager_instance.is_global_post_parser_enabled())
            self.assertTrue(configuration_manager_instance.is_extension_parser_enabled())

            reloaded_configuration_manager = AI_Global_Config_Manager(config_target_file_path=target_config_file_path)
            self.assertTrue(reloaded_configuration_manager.Is_Global_Pre_Parser_Enabled())
            self.assertTrue(reloaded_configuration_manager.Is_Global_Post_Parser_Enabled())
            self.assertTrue(reloaded_configuration_manager.Is_Extension_Parser_Enabled())

    def test_modular_turn_continuation_command_parser(self) -> None:
        import re

        class MockTurnContinuationCommandParser(BaseModularParser):
            parser_name: str = "turn_continuation_command_parser"

            def parse_pre(self, incoming_request_payload_dict: Dict[str, Any]) -> Dict[str, Any]:
                return incoming_request_payload_dict

            def parse_post(self, incoming_response_envelope_dict: Dict[str, Any]) -> Dict[str, Any]:
                response_text_content = str(incoming_response_envelope_dict.get("text", ""))
                regex_command_match = re.search(r"<request_turn>(.*?)</request_turn>", response_text_content, re.DOTALL)
                if regex_command_match:
                    continuation_prompt_text = regex_command_match.group(1).strip()
                    cleaned_text_content = re.sub(r"<request_turn>.*?</request_turn>", "", response_text_content, flags=re.DOTALL).strip()
                    updated_response_envelope = dict(incoming_response_envelope_dict)
                    updated_response_envelope["text"] = cleaned_text_content
                    updated_response_envelope["turn_continuation_command"] = {
                        "request_turn": True,
                        "continuation_prompt": continuation_prompt_text,
                    }
                    return updated_response_envelope
                return incoming_response_envelope_dict

        with tempfile.TemporaryDirectory() as temporary_directory_path_str:
            target_config_file_path = Path(temporary_directory_path_str) / "turn_parser_config.105a.bejson"
            configuration_manager_instance = AIGlobalConfigManager(config_target_file_path=target_config_file_path)
            parser_registry_instance = ParserRegistry(config_manager_instance=configuration_manager_instance)

            turn_continuation_parser_instance = MockTurnContinuationCommandParser()
            parser_registry_instance.Register_Parser(turn_continuation_parser_instance)
            self.assertIn("turn_continuation_command_parser", parser_registry_instance.List_Parsers())

            def mock_command_output_transport(request_payload_object, timeout_seconds_metric):
                simulated_response_payload = {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": "Initial answer.<request_turn>Please verify the schema.</request_turn>"
                                    }
                                ]
                            },
                            "finishReason": "STOP",
                        }
                    ],
                    "usageMetadata": {"promptTokenCount": 8, "candidatesTokenCount": 14},
                }
                return json.dumps(simulated_response_payload).encode("utf-8")

            gemini_rest_client_instance = GeminiRestClient(transport=mock_command_output_transport)

            # Test 1: Parser disabled -> output untouched
            parser_registry_instance.Set_Post_Parser_Enabled(False)
            dispatcher_with_disabled_parser = AIDispatcher(
                parser_registry=parser_registry_instance,
                auto_register_defaults=False,
            )
            dispatcher_with_disabled_parser.register_provider(gemini_rest_client_instance)

            dispatched_disabled_response = dispatcher_with_disabled_parser.dispatch(
                {"prompt": "Run step"},
                explicit_keys=["AIzaSyMockTestKey1234567890"],
            )
            self.assertIn("<request_turn>", Get_Response_Text(dispatched_disabled_response))
            self.assertIsNone(Get_Turn_Continuation_Command(dispatched_disabled_response))

            # Test 2: Parser enabled -> output stripped and turn command extracted
            parser_registry_instance.Set_Post_Parser_Enabled(True)
            dispatcher_with_enabled_parser = AIDispatcher(
                parser_registry=parser_registry_instance,
                auto_register_defaults=False,
            )
            dispatcher_with_enabled_parser.register_provider(gemini_rest_client_instance)

            dispatched_enabled_response = dispatcher_with_enabled_parser.dispatch(
                {"prompt": "Run step"},
                explicit_keys=["AIzaSyMockTestKey1234567890"],
            )
            self.assertEqual(Get_Response_Text(dispatched_enabled_response), "Initial answer.")
            extracted_continuation_command_dict = Get_Turn_Continuation_Command(dispatched_enabled_response)
            self.assertIsNotNone(extracted_continuation_command_dict)
            self.assertTrue(extracted_continuation_command_dict.get("request_turn"))
            self.assertEqual(
                extracted_continuation_command_dict.get("continuation_prompt"),
                "Please verify the schema.",
            )

    def test_custom_python_module_extension_parser_attachment(self) -> None:
        class MockDownstreamDomainExtensionParser(BaseExtensionModuleParser):
            extension_module_name: str = "downstream_domain_extension"

            def parse_extension_pre(self, incoming_request_payload_dict: Dict[str, Any]) -> Dict[str, Any]:
                updated_request_payload = dict(incoming_request_payload_dict)
                existing_prompt_text = str(updated_request_payload.get("prompt", ""))
                updated_request_payload["prompt"] = f"[EXT_PRE] {existing_prompt_text}"
                return updated_request_payload

            def parse_extension_post(self, incoming_response_envelope_dict: Dict[str, Any]) -> Dict[str, Any]:
                updated_response_envelope = dict(incoming_response_envelope_dict)
                existing_text_content = str(updated_response_envelope.get("text", ""))
                updated_response_envelope["text"] = f"{existing_text_content} [EXT_POST]"
                return updated_response_envelope

        with tempfile.TemporaryDirectory() as temporary_directory_path_str:
            target_config_file_path = Path(temporary_directory_path_str) / "extension_config.105a.bejson"
            configuration_manager_instance = AIGlobalConfigManager(config_target_file_path=target_config_file_path)
            extension_registry_instance = ExtensionParserRegistry(config_manager_instance=configuration_manager_instance)

            extension_parser_plugin_instance = MockDownstreamDomainExtensionParser()
            extension_registry_instance.Register_Extension_Parser(extension_parser_plugin_instance)
            self.assertIn("downstream_domain_extension", extension_registry_instance.List_Extension_Parsers())

            captured_network_request_body_dict = {}

            def mock_extension_transport(request_payload_object, timeout_seconds_metric):
                captured_network_request_body_dict["body"] = json.loads(request_payload_object.data.decode("utf-8"))
                simulated_response_payload = {
                    "candidates": [
                        {
                            "content": {"parts": [{"text": "Processed output"}]},
                            "finishReason": "STOP",
                        }
                    ],
                    "usageMetadata": {"promptTokenCount": 6, "candidatesTokenCount": 5},
                }
                return json.dumps(simulated_response_payload).encode("utf-8")

            gemini_rest_client_instance = GeminiRestClient(transport=mock_extension_transport)

            # Test 1: Extension parser disabled
            extension_registry_instance.Set_Enabled(False)
            dispatcher_with_disabled_extension = AIDispatcher(
                extension_parser_registry=extension_registry_instance,
                auto_register_defaults=False,
            )
            dispatcher_with_disabled_extension.register_provider(gemini_rest_client_instance)

            dispatched_disabled_response = dispatcher_with_disabled_extension.dispatch(
                {"prompt": "Hello model"},
                explicit_keys=["AIzaSyMockTestKey1234567890"],
            )
            self.assertEqual(Get_Response_Text(dispatched_disabled_response), "Processed output")
            first_turn_sent_prompt = captured_network_request_body_dict["body"]["contents"][0]["parts"][0]["text"]
            self.assertEqual(first_turn_sent_prompt, "Hello model")

            # Test 2: Extension parser enabled
            extension_registry_instance.Set_Enabled(True)
            dispatcher_with_enabled_extension = AIDispatcher(
                extension_parser_registry=extension_registry_instance,
                auto_register_defaults=False,
            )
            dispatcher_with_enabled_extension.register_provider(gemini_rest_client_instance)

            dispatched_enabled_response = dispatcher_with_enabled_extension.dispatch(
                {"prompt": "Hello model"},
                explicit_keys=["AIzaSyMockTestKey1234567890"],
            )
            self.assertEqual(Get_Response_Text(dispatched_enabled_response), "Processed output [EXT_POST]")
            second_turn_sent_prompt = captured_network_request_body_dict["body"]["contents"][0]["parts"][0]["text"]
            self.assertEqual(second_turn_sent_prompt, "[EXT_PRE] Hello model")


if __name__ == "__main__":
    unittest.main()


