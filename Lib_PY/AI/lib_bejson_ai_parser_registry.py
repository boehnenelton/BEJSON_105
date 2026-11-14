"""
Library:         lib_bejson_ai_parser_registry.py
Family:          AI
Module Purpose:  Tier 2 Configuration-Gated Registry & Pipeline Coordinator for Modular Parsers
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 2: Model Features & Gates)
Version:         1.0.0
Release_Version: 300
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   1d3e5f7a-9b2c-4e88-a1c0-7f6e8d9b3020
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_CURRENT_MODULE_DIR = Path(__file__).resolve().parent
if str(_CURRENT_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_MODULE_DIR))

from lib_bejson_ai_parser_base import BaseModularParser  # noqa: E402
from lib_bejson_ai_tooling_registry import AIGlobalConfigManager  # noqa: E402

VERSION = "1.0.0"

_LOGGER_INSTANCE = logging.getLogger("lib_bejson_ai_parser_registry")


class ParserRegistry:
    """
    Tier 2 Registry governing modular pre- and post-processing parsers.
    Configuration-gated via persistent global settings (`global_pre_parser_enabled`,
    `global_post_parser_enabled`). Allows dynamic attachment and detachment of
    turn-command parsers, sanitizers, and diagnostic inspectors.
    """

    def __init__(
        self,
        config_manager_instance: Optional[AIGlobalConfigManager] = None,
    ) -> None:
        self.config_manager: AIGlobalConfigManager = config_manager_instance or AIGlobalConfigManager()
        self._registered_modular_parsers_map: Dict[str, BaseModularParser] = {}

    def register_parser(
        self,
        modular_parser_instance: BaseModularParser,
    ) -> None:
        """Register a modular parser plugin under its parser_name identifier."""
        clean_parser_name_key = modular_parser_instance.parser_name.lower().strip()
        self._registered_modular_parsers_map[clean_parser_name_key] = modular_parser_instance

    def unregister_parser(
        self,
        target_parser_name_identifier: str,
    ) -> None:
        """Remove a modular parser plugin by name."""
        clean_parser_name_key = target_parser_name_identifier.lower().strip()
        self._registered_modular_parsers_map.pop(clean_parser_name_key, None)

    def list_parsers(self) -> List[str]:
        """Return sorted list of registered modular parser names."""
        return sorted(self._registered_modular_parsers_map.keys())

    def is_pre_parser_enabled(self) -> bool:
        """Query persistent global pre-parser gate."""
        return self.config_manager.is_global_pre_parser_enabled()

    def set_pre_parser_enabled(
        self,
        target_enabled_flag: bool,
    ) -> None:
        """Persistently toggle global pre-parser gate."""
        self.config_manager.set_global_pre_parser_enabled(target_enabled_flag)

    def is_post_parser_enabled(self) -> bool:
        """Query persistent global post-parser gate."""
        return self.config_manager.is_global_post_parser_enabled()

    def set_post_parser_enabled(
        self,
        target_enabled_flag: bool,
    ) -> None:
        """Persistently toggle global post-parser gate."""
        self.config_manager.set_global_post_parser_enabled(target_enabled_flag)

    def execute_pre_parsers(
        self,
        incoming_request_payload_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute all registered modular pre-parsers sequentially if gate is enabled.
        Returns the accumulated transformed request payload dictionary.
        """
        if not self.is_pre_parser_enabled():
            return incoming_request_payload_dict

        accumulated_request_payload = dict(incoming_request_payload_dict)
        for single_parser_identifier_name, single_parser_plugin_instance in self._registered_modular_parsers_map.items():
            try:
                accumulated_request_payload = single_parser_plugin_instance.parse_pre(accumulated_request_payload)
            except Exception as parser_execution_exception:
                _LOGGER_INSTANCE.warning(
                    "Modular pre-parser '%s' failed: %s",
                    single_parser_identifier_name,
                    parser_execution_exception,
                )
        return accumulated_request_payload

    def execute_post_parsers(
        self,
        incoming_response_envelope_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute all registered modular post-parsers sequentially if gate is enabled.
        Returns the accumulated transformed response envelope dictionary.
        """
        if not self.is_post_parser_enabled():
            return incoming_response_envelope_dict

        accumulated_response_envelope = dict(incoming_response_envelope_dict)
        for single_parser_identifier_name, single_parser_plugin_instance in self._registered_modular_parsers_map.items():
            try:
                accumulated_response_envelope = single_parser_plugin_instance.parse_post(accumulated_response_envelope)
            except Exception as parser_execution_exception:
                _LOGGER_INSTANCE.warning(
                    "Modular post-parser '%s' failed: %s",
                    single_parser_identifier_name,
                    parser_execution_exception,
                )
        return accumulated_response_envelope

    # Name_Case Method Bindings
    Register_Parser = register_parser
    Unregister_Parser = unregister_parser
    List_Parsers = list_parsers
    Is_Pre_Parser_Enabled = is_pre_parser_enabled
    Set_Pre_Parser_Enabled = set_pre_parser_enabled
    Is_Post_Parser_Enabled = is_post_parser_enabled
    Set_Post_Parser_Enabled = set_post_parser_enabled
    Execute_Pre_Parsers = execute_pre_parsers
    Execute_Post_Parsers = execute_post_parsers


# Canonical Name_Case Alias
Parser_Registry = ParserRegistry
