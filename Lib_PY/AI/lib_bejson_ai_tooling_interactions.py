"""
Library:         lib_bejson_ai_tooling_interactions.py
Family:          AI
Module Purpose:  Tier 2 Generic Tooling System for Gemini Interactions API
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 2: Model Features & Gates)
Version:         1.0.0
Release_Version: 300
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   a7f3e1b9-2c4d-4e88-b1a0-9e5d2c8f1017
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_CURRENT_MODULE_DIR = Path(__file__).resolve().parent
if str(_CURRENT_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_MODULE_DIR))

from lib_bejson_AI_bejson_errors import (  # noqa: E402
    AIException,
    ERR_AI_TOOL_EXECUTION_FAILED,
)
from lib_bejson_ai_tooling_base import BaseToolingSystem  # noqa: E402

VERSION = "1.0.0"

_LOGGER_INSTANCE = logging.getLogger("lib_bejson_ai_tooling_interactions")


class InteractionsToolingSystem(BaseToolingSystem):
    """
    Generic tooling system adapter for Google Gemini Interactions API wire schema.
    Contains zero hardcoded application tools; accepts dynamic client tool registrations.
    """

    system_name: str = "interactions_tools"

    def __init__(self, is_enabled_override_flag: Optional[bool] = None) -> None:
        self._is_enabled_override_flag: Optional[bool] = is_enabled_override_flag
        self._registered_tool_declarations_map: Dict[str, Dict[str, Any]] = {}
        self._registered_tool_callables_map: Dict[str, Callable[..., Any]] = {}

    def is_enabled(self) -> bool:
        if self._is_enabled_override_flag is not None:
            return self._is_enabled_override_flag
        return True

    def register_tool(
        self,
        tool_declaration_schema_dict: Dict[str, Any],
        tool_execution_handler_callable: Optional[Callable[..., Any]] = None,
    ) -> None:
        """Register a generic function or built-in tool schema and optional execution handler."""
        raw_tool_type_token = tool_declaration_schema_dict.get("type", "function")
        if raw_tool_type_token == "function":
            tool_identifier_name_token = str(tool_declaration_schema_dict.get("name", "")).strip()
            if not tool_identifier_name_token:
                raise AIException(
                    ERR_AI_TOOL_EXECUTION_FAILED,
                    "Function tool declaration missing required 'name' attribute.",
                )
            self._registered_tool_declarations_map[tool_identifier_name_token] = dict(tool_declaration_schema_dict)
            if tool_execution_handler_callable is not None:
                self._registered_tool_callables_map[tool_identifier_name_token] = tool_execution_handler_callable
        else:
            # Built-in tool (e.g. code_execution)
            self._registered_tool_declarations_map[raw_tool_type_token] = dict(tool_declaration_schema_dict)

    def list_registered_tool_names(self) -> List[str]:
        return sorted(self._registered_tool_declarations_map.keys())

    def build_provider_tools(
        self,
        requested_tool_identifiers_list: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Compile registered tools into flat list matching Interactions API tools specification."""
        if not self.is_enabled():
            return []

        compiled_provider_tools_list: List[Dict[str, Any]] = []
        if requested_tool_identifiers_list:
            for requested_identifier_token in requested_tool_identifiers_list:
                clean_identifier_key = requested_identifier_token.strip()
                if clean_identifier_key in self._registered_tool_declarations_map:
                    compiled_provider_tools_list.append(self._registered_tool_declarations_map[clean_identifier_key])
        else:
            compiled_provider_tools_list = list(self._registered_tool_declarations_map.values())
        return compiled_provider_tools_list

    def execute_tool_call(
        self,
        tool_call_invocation_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute a function_call step and format the function_result response step.
        """
        target_tool_name_identifier = str(tool_call_invocation_payload.get("name", "")).strip()
        target_tool_call_id_token = str(
            tool_call_invocation_payload.get("id")
            or tool_call_invocation_payload.get("call_id")
            or ""
        )
        tool_invocation_arguments_payload = tool_call_invocation_payload.get("arguments", {})

        if isinstance(tool_invocation_arguments_payload, str):
            try:
                tool_invocation_arguments_payload = json.loads(tool_invocation_arguments_payload)
            except Exception:
                tool_invocation_arguments_payload = {}

        if target_tool_name_identifier not in self._registered_tool_callables_map:
            error_message_text_str = f"Tool '{target_tool_name_identifier}' has no registered execution handler."
            return {
                "type": "function_result",
                "name": target_tool_name_identifier,
                "call_id": target_tool_call_id_token,
                "result": [{"type": "text", "text": error_message_text_str}],
                "is_error": True,
            }

        target_handler_callable = self._registered_tool_callables_map[target_tool_name_identifier]
        try:
            if isinstance(tool_invocation_arguments_payload, dict):
                try:
                    raw_execution_result_payload = target_handler_callable(**tool_invocation_arguments_payload)
                except TypeError:
                    raw_execution_result_payload = target_handler_callable(tool_invocation_arguments_payload)
            else:
                raw_execution_result_payload = target_handler_callable(tool_invocation_arguments_payload)

            serialized_execution_result_str = (
                json.dumps(raw_execution_result_payload)
                if isinstance(raw_execution_result_payload, (dict, list))
                else str(raw_execution_result_payload)
            )
            return {
                "type": "function_result",
                "name": target_tool_name_identifier,
                "call_id": target_tool_call_id_token,
                "result": [{"type": "text", "text": serialized_execution_result_str}],
                "is_error": False,
            }
        except Exception as execution_failure_exception:
            _LOGGER_INSTANCE.warning(
                "Execution failed for tool '%s': %s",
                target_tool_name_identifier,
                execution_failure_exception,
            )
            return {
                "type": "function_result",
                "name": target_tool_name_identifier,
                "call_id": target_tool_call_id_token,
                "result": [{"type": "text", "text": f"Tool execution failed: {execution_failure_exception}"}],
                "is_error": True,
            }

    # Name_Case Method Bindings
    Is_Enabled = is_enabled
    Register_Tool = register_tool
    List_Registered_Tool_Names = list_registered_tool_names
    Build_Provider_Tools = build_provider_tools
    Execute_Tool_Call = execute_tool_call


# Canonical Name_Case Alias
Interactions_Tooling_System = InteractionsToolingSystem

