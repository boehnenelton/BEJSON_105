"""
Library:         lib_bejson_ai_dispatcher.py
Family:          AI
Module Purpose:  Tier 1 Master Ingress & Universal Router for the Multi-AI Provider Gateway
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 1: Abstraction Layers)
Version:         1.4.0
Release_Version: 300
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   d1e9a128-5c9a-414e-c14b-0f3a5b9d1010
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_CURRENT_MODULE_DIR = Path(__file__).resolve().parent
if str(_CURRENT_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_MODULE_DIR))

from lib_bejson_AI_bejson_errors import (  # noqa: E402
    AIException,
    ERR_AI_HTTP_AUTH_FAILED,
    ERR_AI_HTTP_RATE_LIMITED,
    ERR_AI_PROVIDER_NOT_REGISTERED,
)
from lib_bejson_ai_client_base import BaseAIClient  # noqa: E402
from lib_bejson_ai_client_geminiinteractions import GeminiInteractionsClient  # noqa: E402
from lib_bejson_ai_client_geminirest import GeminiRestClient  # noqa: E402
from lib_bejson_ai_features_common import normalize_inbound_payload  # noqa: E402
from lib_bejson_ai_jit_key_handler import JITKeyHandler  # noqa: E402
from lib_bejson_ai_extension_parser import ExtensionParserRegistry  # noqa: E402
from lib_bejson_ai_models import Resolve_Model_Identifier  # noqa: E402
from lib_bejson_ai_parser_registry import ParserRegistry  # noqa: E402
from lib_bejson_ai_postprocessor import AIPostprocessor  # noqa: E402
from lib_bejson_ai_preprocessor import AIPreprocessor  # noqa: E402
from lib_bejson_ai_tooling_interactions import InteractionsToolingSystem  # noqa: E402
from lib_bejson_ai_tooling_registry import ToolingRegistry  # noqa: E402
from lib_bejson_ai_translator import AITranslator  # noqa: E402

VERSION = "1.5.0"


class AIDispatcher:
    """
    Master ingress router coordinating:
      Tier 1: Dispatcher -> Translator
      Tier 2: Preprocessor -> Postprocessor + ToolingRegistry + ParserRegistry + ExtensionParserRegistry
      Tier 3: JITKeyHandler + KeyRotator + BaseAIClient drivers (GeminiRestClient, GeminiInteractionsClient)
    """

    def __init__(
        self,
        preprocessor: Optional[AIPreprocessor] = None,
        postprocessor: Optional[AIPostprocessor] = None,
        translator: Optional[AITranslator] = None,
        key_handler: Optional[JITKeyHandler] = None,
        tooling_registry: Optional[ToolingRegistry] = None,
        parser_registry: Optional[ParserRegistry] = None,
        extension_parser_registry: Optional[ExtensionParserRegistry] = None,
        auto_register_defaults: bool = True,
        **extra_keyword_arguments: Any,
    ) -> None:
        self.preprocessor: AIPreprocessor = (
            preprocessor or extra_keyword_arguments.get("preprocessor_instance") or AIPreprocessor()
        )
        self.postprocessor: AIPostprocessor = (
            postprocessor or extra_keyword_arguments.get("postprocessor_instance") or AIPostprocessor()
        )
        self.translator: AITranslator = (
            translator or extra_keyword_arguments.get("translator_instance") or AITranslator()
        )
        self.key_handler: JITKeyHandler = (
            key_handler or extra_keyword_arguments.get("key_handler_instance") or JITKeyHandler()
        )
        self.tooling_registry: ToolingRegistry = (
            tooling_registry or extra_keyword_arguments.get("tooling_registry_instance") or ToolingRegistry()
        )
        self.parser_registry: ParserRegistry = (
            parser_registry
            or extra_keyword_arguments.get("parser_registry_instance")
            or ParserRegistry(config_manager_instance=self.tooling_registry.config_manager)
        )
        self.extension_parser_registry: ExtensionParserRegistry = (
            extension_parser_registry
            or extra_keyword_arguments.get("extension_parser_registry_instance")
            or ExtensionParserRegistry(config_manager_instance=self.tooling_registry.config_manager)
        )
        self._registered_providers_map: Dict[str, BaseAIClient] = {}

        auto_register_flag = (
            auto_register_defaults
            if "auto_register_defaults_flag" not in extra_keyword_arguments
            else bool(extra_keyword_arguments["auto_register_defaults_flag"])
        )
        if auto_register_flag:
            self.register_provider(GeminiRestClient())
            self.register_provider(GeminiInteractionsClient())
            # Ensure interactions tooling system is registered in tooling registry
            if "interactions_tools" not in self.tooling_registry.list_tooling_systems():
                self.tooling_registry.register_tooling_system(InteractionsToolingSystem())

    def register_provider(self, client_driver_instance: BaseAIClient) -> None:
        """Register a `BaseAIClient` driver under its canonical `provider_name`."""
        clean_provider_name_key = client_driver_instance.provider_name.lower().strip()
        self._registered_providers_map[clean_provider_name_key] = client_driver_instance

    def list_providers(self) -> List[str]:
        """Return sorted list of registered provider names."""
        return sorted(self._registered_providers_map.keys())

    def discover_providers(self, library_target_directory_path: Optional[Path] = None) -> List[str]:
        """
        Scan directory for `lib_bejson_ai_client_*.py` modules (excluding `base`)
        and return discovered provider names.
        """
        target_directory = Path(library_target_directory_path) if library_target_directory_path else _CURRENT_MODULE_DIR
        discovered_provider_names_list: List[str] = []
        for file_candidate_path in sorted(target_directory.glob("lib_bejson_ai_client_*.py")):
            module_file_stem = file_candidate_path.stem
            module_suffix_name = module_file_stem.replace("lib_bejson_ai_client_", "", 1)
            if module_suffix_name == "base":
                continue
            importlib.import_module(module_file_stem)
            discovered_provider_names_list.append(module_suffix_name)
        return discovered_provider_names_list

    def _execute_client_call_with_key_rotation(
        self,
        client_driver_instance: BaseAIClient,
        target_provider_identifier_name: str,
        provider_wire_payload_dictionary: Dict[str, Any],
        resolved_model_identifier_name: str,
        vault_custom_file_path: Optional[Path] = None,
        explicit_api_keys_list: Optional[List[str]] = None,
        maximum_key_rotation_retries: int = 2,
    ) -> Dict[str, Any]:
        """Execute client call with automated JIT key injection and 429/401/403 rotation."""
        key_rotation_attempt_counter = 0
        while True:
            key_rotation_attempt_counter += 1
            acquired_api_key_secret = self.key_handler.acquire_key(
                target_provider_identifier_name,
                vault_path=vault_custom_file_path,
                explicit_keys=explicit_api_keys_list,
            )
            try:
                raw_provider_response_dict = client_driver_instance.execute_call(
                    provider_payload=provider_wire_payload_dictionary,
                    api_key=acquired_api_key_secret,
                    model=resolved_model_identifier_name,
                )
                self.key_handler.record_success(acquired_api_key_secret)
                return raw_provider_response_dict
            except AIException as client_call_exception:
                if client_call_exception.code == ERR_AI_HTTP_RATE_LIMITED and key_rotation_attempt_counter <= maximum_key_rotation_retries:
                    self.key_handler.mark_rate_limited(acquired_api_key_secret)
                    continue
                if client_call_exception.code == ERR_AI_HTTP_AUTH_FAILED and key_rotation_attempt_counter <= maximum_key_rotation_retries:
                    self.key_handler.quarantine_key(acquired_api_key_secret)
                    continue
                self.key_handler.record_error(acquired_api_key_secret)
                raise

    def dispatch(
        self,
        payload: Dict[str, Any],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        vault_path: Optional[Path] = None,
        explicit_keys: Optional[List[str]] = None,
        return_bejson_105: bool = False,
        stdout_routing: bool = False,
        output_sink: Optional[Any] = None,
        max_key_retries: int = 2,
        **extra_keyword_arguments: Any,
    ) -> Dict[str, Any]:
        """
        Execute the full 3-tier gateway pipeline for an inbound dict or BEJSON 105 AI_Request.
        Supports multi-turn tool loops, dynamic model resolution, and stdout routing.
        """
        normalized_request_payload = normalize_inbound_payload(
            payload or extra_keyword_arguments.get("incoming_request_payload")
        )
        target_provider_identifier = (
            provider
            or extra_keyword_arguments.get("provider_name_override")
            or normalized_request_payload.get("provider")
            or "geminirest"
        ).lower().strip()

        if target_provider_identifier not in self._registered_providers_map:
            raise AIException(
                ERR_AI_PROVIDER_NOT_REGISTERED,
                f"Provider '{target_provider_identifier}' is not registered. Available: {self.list_providers()}",
            )
        provider_client_instance = self._registered_providers_map[target_provider_identifier]
        unresolved_model_token = str(
            model
            or extra_keyword_arguments.get("model_name_override")
            or normalized_request_payload.get("model")
            or provider_client_instance.default_model
        )
        resolved_model_identifier_name = Resolve_Model_Identifier(unresolved_model_token)

        resolved_vault_file_path = vault_path or extra_keyword_arguments.get("vault_file_path_override")
        resolved_explicit_keys = explicit_keys or extra_keyword_arguments.get("explicit_api_keys_list")
        resolved_return_bejson_105_flag = (
            return_bejson_105
            if "return_bejson_105_flag" not in extra_keyword_arguments
            else bool(extra_keyword_arguments["return_bejson_105_flag"])
        )
        resolved_stdout_routing_flag = (
            stdout_routing
            if "stdout_routing_flag" not in extra_keyword_arguments
            else bool(extra_keyword_arguments["stdout_routing_flag"])
        )
        resolved_stdout_destination_sink = output_sink or extra_keyword_arguments.get("stdout_destination_sink")
        resolved_maximum_key_retries = (
            max_key_retries
            if "maximum_key_rotation_retries" not in extra_keyword_arguments
            else int(extra_keyword_arguments["maximum_key_rotation_retries"])
        )

        # Tier 2 Inbound Gate (AIPreprocessor + Modular Pre-Parsers + Extension Pre-Parsers)
        preprocessed_request_payload = self.preprocessor.process(normalized_request_payload)
        if self.parser_registry.is_pre_parser_enabled():
            preprocessed_request_payload = self.parser_registry.execute_pre_parsers(preprocessed_request_payload)
        if self.extension_parser_registry.is_enabled():
            preprocessed_request_payload = self.extension_parser_registry.execute_extension_pre_parsers(preprocessed_request_payload)

        # Tier 2 Tooling Gate & Injection
        active_tooling_subsystem = self.tooling_registry.get_active_system()
        if active_tooling_subsystem is not None and "tools" not in preprocessed_request_payload:
            compiled_provider_tools_list = active_tooling_subsystem.build_provider_tools()
            if compiled_provider_tools_list:
                preprocessed_request_payload["tools"] = compiled_provider_tools_list

        # Tier 1 Outbound Translation
        outbound_provider_wire_payload = self.translator.to_provider_payload(
            target_provider_identifier,
            preprocessed_request_payload,
        )

        # Tier 3 Initial Provider Execution
        raw_provider_response_dict = self._execute_client_call_with_key_rotation(
            client_driver_instance=provider_client_instance,
            target_provider_identifier_name=target_provider_identifier,
            provider_wire_payload_dictionary=outbound_provider_wire_payload,
            resolved_model_identifier_name=resolved_model_identifier_name,
            vault_custom_file_path=resolved_vault_file_path,
            explicit_api_keys_list=resolved_explicit_keys,
            maximum_key_rotation_retries=resolved_maximum_key_retries,
        )

        # Tier 1 Initial Inbound Translation
        normalized_response_envelope = self.translator.from_provider_response(
            target_provider_identifier,
            raw_provider_response_dict,
            target_model_name_identifier=resolved_model_identifier_name,
        )

        # Multi-Turn Tool Execution Loop (Interactions or active tooling system)
        if active_tooling_subsystem is not None:
            maximum_tool_roundtrips_limit = int(
                self.tooling_registry.config_manager.get_setting("max_tool_roundtrips", 5)
            )
            tool_execution_roundtrip_counter = 0

            while (
                normalized_response_envelope.get("tool_calls")
                and tool_execution_roundtrip_counter < maximum_tool_roundtrips_limit
            ):
                tool_execution_roundtrip_counter += 1
                pending_tool_calls_list = normalized_response_envelope["tool_calls"]
                interaction_session_id_token = normalized_response_envelope.get("interaction_id")

                tool_feedback_inputs_list: List[Dict[str, Any]] = []
                for single_tool_call_record in pending_tool_calls_list:
                    tool_execution_result_envelope = active_tooling_subsystem.execute_tool_call(
                        single_tool_call_record
                    )
                    tool_feedback_inputs_list.append({
                        "type": "function_result",
                        "name": str(tool_execution_result_envelope.get("name", "")),
                        "call_id": str(tool_execution_result_envelope.get("call_id", "")),
                        "result": tool_execution_result_envelope.get("result", []),
                    })

                next_turn_request_payload: Dict[str, Any] = {
                    "model": resolved_model_identifier_name,
                    "inputs": tool_feedback_inputs_list,
                }
                if interaction_session_id_token:
                    next_turn_request_payload["previous_interaction_id"] = interaction_session_id_token
                if "tools" in preprocessed_request_payload:
                    next_turn_request_payload["tools"] = preprocessed_request_payload["tools"]

                next_turn_wire_payload = self.translator.to_provider_payload(
                    target_provider_identifier,
                    next_turn_request_payload,
                )

                raw_next_turn_response = self._execute_client_call_with_key_rotation(
                    client_driver_instance=provider_client_instance,
                    target_provider_identifier_name=target_provider_identifier,
                    provider_wire_payload_dictionary=next_turn_wire_payload,
                    resolved_model_identifier_name=resolved_model_identifier_name,
                    vault_custom_file_path=resolved_vault_file_path,
                    explicit_api_keys_list=resolved_explicit_keys,
                    maximum_key_rotation_retries=resolved_maximum_key_retries,
                )

                normalized_response_envelope = self.translator.from_provider_response(
                    target_provider_identifier,
                    raw_next_turn_response,
                    target_model_name_identifier=resolved_model_identifier_name,
                )

        # Tier 2 Outbound Modular & Extension Parsers
        if self.parser_registry.is_post_parser_enabled():
            normalized_response_envelope = self.parser_registry.execute_post_parsers(normalized_response_envelope)
        if self.extension_parser_registry.is_enabled():
            normalized_response_envelope = self.extension_parser_registry.execute_extension_post_parsers(normalized_response_envelope)

        # Tier 2 Outbound Gate
        expected_response_format_token = str(preprocessed_request_payload.get("response_format", "text"))
        cleaned_response_envelope = self.postprocessor.process(
            normalized_response_envelope,
            expected_format=expected_response_format_token,
        )

        if resolved_stdout_routing_flag:
            response_text_content_str = str(cleaned_response_envelope.get("text", ""))
            output_target_stream = resolved_stdout_destination_sink if resolved_stdout_destination_sink is not None else sys.stdout
            output_target_stream.write(response_text_content_str + "\n")
            output_target_stream.flush()

        if resolved_return_bejson_105_flag:
            return self.translator.to_bejson_105_response(cleaned_response_envelope)
        return cleaned_response_envelope

    async def dispatch_async(
        self,
        payload: Dict[str, Any],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        vault_path: Optional[Path] = None,
        explicit_keys: Optional[List[str]] = None,
        return_bejson_105: bool = False,
        stdout_routing: bool = False,
        output_sink: Optional[Any] = None,
        max_key_retries: int = 2,
        **extra_keyword_arguments: Any,
    ) -> Dict[str, Any]:
        """Asynchronous non-blocking wrapper around dispatch()."""
        import asyncio

        return await asyncio.to_thread(
            self.dispatch,
            payload=payload,
            provider=provider,
            model=model,
            vault_path=vault_path,
            explicit_keys=explicit_keys,
            return_bejson_105=return_bejson_105,
            stdout_routing=stdout_routing,
            output_sink=output_sink,
            max_key_retries=max_key_retries,
            **extra_keyword_arguments,
        )

    # Name_Case Method Aliases
    Dispatch = dispatch
    Dispatch_Async = dispatch_async
    Register_Provider = register_provider
    List_Providers = list_providers
    Discover_Providers = discover_providers


def Get_Response_Text(response_payload_dictionary: Dict[str, Any]) -> str:
    """Extract and return text response from a clean response or BEJSON 105 payload."""
    if "text" in response_payload_dictionary:
        return str(response_payload_dictionary["text"])
    if response_payload_dictionary.get("Format") == "BEJSON" and "Values" in response_payload_dictionary:
        bejson_field_names_list = [
            field_spec_dict.get("name") if isinstance(field_spec_dict, dict) else str(field_spec_dict)
            for field_spec_dict in response_payload_dictionary.get("Fields", [])
        ]
        for entity_table_record_row in response_payload_dictionary.get("Values", []):
            table_row_field_mapping = dict(
                zip(
                    bejson_field_names_list,
                    entity_table_record_row[1:]
                    if len(entity_table_record_row) == len(bejson_field_names_list) + 1
                    else entity_table_record_row,
                )
            )
            if "text" in table_row_field_mapping:
                return str(table_row_field_mapping["text"])
    return ""


def Get_Response_JSON(response_payload_dictionary: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Retrieve structured parsed JSON data if present."""
    return response_payload_dictionary.get("structured_data")


def Get_Response_Usage(response_payload_dictionary: Dict[str, Any]) -> Dict[str, int]:
    """Retrieve token usage dictionary."""
    token_usage_metadata_dict = response_payload_dictionary.get("usage")
    return token_usage_metadata_dict if isinstance(token_usage_metadata_dict, dict) else {}


def Get_Interaction_ID(response_payload_dictionary: Dict[str, Any]) -> str:
    """Retrieve Gemini Interactions session ID if present."""
    return str(response_payload_dictionary.get("interaction_id", ""))


def Get_Tool_Calls(response_payload_dictionary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Retrieve list of tool calls requested by model."""
    tool_calls_payload = response_payload_dictionary.get("tool_calls")
    return tool_calls_payload if isinstance(tool_calls_payload, list) else []


def Get_Turn_Continuation_Command(response_payload_dictionary: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Retrieve turn continuation command details if signaled by a modular parser."""
    turn_command_payload = response_payload_dictionary.get("turn_continuation_command")
    if isinstance(turn_command_payload, dict):
        return turn_command_payload
    if response_payload_dictionary.get("request_turn") or response_payload_dictionary.get("continuation_requested"):
        return {
            "request_turn": True,
            "continuation_prompt": str(response_payload_dictionary.get("continuation_prompt", "")),
        }
    return None



_DEFAULT_DISPATCHER_SINGLETON: Optional[AIDispatcher] = None


def AI_Dispatch(
    payload: Dict[str, Any],
    provider: Optional[str] = None,
    model: Optional[str] = None,
    vault_path: Optional[Path] = None,
    explicit_keys: Optional[List[str]] = None,
    return_bejson_105: bool = False,
    stdout_routing: bool = False,
    output_sink: Optional[Any] = None,
    max_key_retries: int = 2,
) -> Dict[str, Any]:
    """Top-level Name_Case dispatch entrypoint."""
    global _DEFAULT_DISPATCHER_SINGLETON
    if _DEFAULT_DISPATCHER_SINGLETON is None:
        _DEFAULT_DISPATCHER_SINGLETON = AIDispatcher()
    return _DEFAULT_DISPATCHER_SINGLETON.dispatch(
        incoming_request_payload=payload,
        provider_name_override=provider,
        model_name_override=model,
        vault_file_path_override=vault_path,
        explicit_api_keys_list=explicit_keys,
        return_bejson_105_flag=return_bejson_105,
        stdout_routing_flag=stdout_routing,
        stdout_destination_sink=output_sink,
        maximum_key_rotation_retries=max_key_retries,
    )


async def AI_Dispatch_Async(
    payload: Dict[str, Any],
    provider: Optional[str] = None,
    model: Optional[str] = None,
    vault_path: Optional[Path] = None,
    explicit_keys: Optional[List[str]] = None,
    return_bejson_105: bool = False,
    stdout_routing: bool = False,
    output_sink: Optional[Any] = None,
    max_key_retries: int = 2,
) -> Dict[str, Any]:
    """Top-level Name_Case asynchronous dispatch entrypoint."""
    global _DEFAULT_DISPATCHER_SINGLETON
    if _DEFAULT_DISPATCHER_SINGLETON is None:
        _DEFAULT_DISPATCHER_SINGLETON = AIDispatcher()
    return await _DEFAULT_DISPATCHER_SINGLETON.dispatch_async(
        incoming_request_payload=payload,
        provider_name_override=provider,
        model_name_override=model,
        vault_file_path_override=vault_path,
        explicit_api_keys_list=explicit_keys,
        return_bejson_105_flag=return_bejson_105,
        stdout_routing_flag=stdout_routing,
        stdout_destination_sink=output_sink,
        maximum_key_rotation_retries=max_key_retries,
    )


# Canonical Name_Case Alias
AI_Dispatcher = AIDispatcher
