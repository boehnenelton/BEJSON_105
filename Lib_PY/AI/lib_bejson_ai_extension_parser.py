"""
Library:         lib_bejson_ai_extension_parser.py
Family:          AI
Module Purpose:  Tier 2 Localized Custom Python Module & Downstream Library Extension Parser Layer
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 2: Model Features & Gates)
Version:         1.0.0
Release_Version: 300
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   3a5f8b1c-7e2d-4c99-b0a1-8d4e6f2a4021
"""
from __future__ import annotations

import logging
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

_CURRENT_MODULE_DIR = Path(__file__).resolve().parent
if str(_CURRENT_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_MODULE_DIR))

from lib_bejson_ai_tooling_registry import AIGlobalConfigManager  # noqa: E402

VERSION = "1.0.0"

_LOGGER_INSTANCE = logging.getLogger("lib_bejson_ai_extension_parser")


class BaseExtensionModuleParser(ABC):
    """
    Abstract contract for external Python modules and downstream libraries
    to attach custom pre/post transformations into the AI gateway pipeline
    without modifying core library files.
    """

    extension_module_name: str = "generic_python_extension"

    @abstractmethod
    def parse_extension_pre(
        self,
        incoming_request_payload_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Transform or enrich inbound request payload before execution.
        Must return the updated or unmodified request payload dictionary.
        """
        raise NotImplementedError

    @abstractmethod
    def parse_extension_post(
        self,
        incoming_response_envelope_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Transform or enrich outbound response envelope before delivery.
        Must return the updated or unmodified response envelope dictionary.
        """
        raise NotImplementedError

    # Name_Case Method Forwarders
    def Parse_Extension_Pre(
        self,
        incoming_request_payload_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Name_Case forwarder for parse_extension_pre."""
        return self.parse_extension_pre(incoming_request_payload_dict)

    def Parse_Extension_Post(
        self,
        incoming_response_envelope_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Name_Case forwarder for parse_extension_post."""
        return self.parse_extension_post(incoming_response_envelope_dict)


# Canonical Name_Case Alias
Base_Extension_Module_Parser = BaseExtensionModuleParser


class ExtensionParserRegistry:
    """
    Tier 2 Registry governing localized Python extension module parsers.
    Configuration-gated via persistent global setting (`extension_parser_enabled`).
    Sits next to ToolingRegistry and ParserRegistry to allow external Python
    libraries and project tools to register pre/post hooks.
    """

    def __init__(
        self,
        config_manager_instance: Optional[AIGlobalConfigManager] = None,
    ) -> None:
        self.config_manager: AIGlobalConfigManager = config_manager_instance or AIGlobalConfigManager()
        self._registered_extension_parsers_map: Dict[str, BaseExtensionModuleParser] = {}

    def register_extension_parser(
        self,
        extension_module_parser_instance: BaseExtensionModuleParser,
    ) -> None:
        """Register a Python extension module parser under its extension_module_name identifier."""
        clean_extension_module_name_key = extension_module_parser_instance.extension_module_name.lower().strip()
        self._registered_extension_parsers_map[clean_extension_module_name_key] = extension_module_parser_instance

    def unregister_extension_parser(
        self,
        target_extension_module_name_identifier: str,
    ) -> None:
        """Remove a Python extension module parser by name."""
        clean_extension_module_name_key = target_extension_module_name_identifier.lower().strip()
        self._registered_extension_parsers_map.pop(clean_extension_module_name_key, None)

    def list_extension_parsers(self) -> List[str]:
        """Return sorted list of registered Python extension module parser names."""
        return sorted(self._registered_extension_parsers_map.keys())

    def is_enabled(self) -> bool:
        """Query persistent custom Python extension parser gate."""
        return self.config_manager.is_extension_parser_enabled()

    def set_enabled(
        self,
        target_enabled_flag: bool,
    ) -> None:
        """Persistently toggle custom Python extension parser gate."""
        self.config_manager.set_extension_parser_enabled(target_enabled_flag)

    def execute_extension_pre_parsers(
        self,
        incoming_request_payload_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute all registered Python extension module pre-parsers sequentially if gate is enabled.
        Returns the accumulated transformed request payload dictionary.
        """
        if not self.is_enabled():
            return incoming_request_payload_dict

        accumulated_request_payload = dict(incoming_request_payload_dict)
        for single_extension_name_key, single_extension_parser_instance in self._registered_extension_parsers_map.items():
            try:
                accumulated_request_payload = single_extension_parser_instance.parse_extension_pre(accumulated_request_payload)
            except Exception as extension_parser_exception:
                _LOGGER_INSTANCE.warning(
                    "Extension module pre-parser '%s' failed: %s",
                    single_extension_name_key,
                    extension_parser_exception,
                )
        return accumulated_request_payload

    def execute_extension_post_parsers(
        self,
        incoming_response_envelope_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute all registered Python extension module post-parsers sequentially if gate is enabled.
        Returns the accumulated transformed response envelope dictionary.
        """
        if not self.is_enabled():
            return incoming_response_envelope_dict

        accumulated_response_envelope = dict(incoming_response_envelope_dict)
        for single_extension_name_key, single_extension_parser_instance in self._registered_extension_parsers_map.items():
            try:
                accumulated_response_envelope = single_extension_parser_instance.parse_extension_post(accumulated_response_envelope)
            except Exception as extension_parser_exception:
                _LOGGER_INSTANCE.warning(
                    "Extension module post-parser '%s' failed: %s",
                    single_extension_name_key,
                    extension_parser_exception,
                )
        return accumulated_response_envelope

    # Name_Case Method Bindings
    Register_Extension_Parser = register_extension_parser
    Unregister_Extension_Parser = unregister_extension_parser
    List_Extension_Parsers = list_extension_parsers
    Is_Enabled = is_enabled
    Set_Enabled = set_enabled
    Execute_Extension_Pre_Parsers = execute_extension_pre_parsers
    Execute_Extension_Post_Parsers = execute_extension_post_parsers


# Canonical Name_Case Alias
Extension_Parser_Registry = ExtensionParserRegistry
