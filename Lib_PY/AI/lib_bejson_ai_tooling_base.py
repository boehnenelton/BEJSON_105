"""
Library:         lib_bejson_ai_tooling_base.py
Family:          AI
Module Purpose:  Tier 2 Abstract Base Contract for Configuration-Gated Tooling & Skill Systems
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 2: Model Features & Gates)
Version:         1.0.0
Release_Version: 300
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   c1f4e2a8-8b3d-4c77-a92c-5d1e8b2f9015
"""
from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_CURRENT_MODULE_DIR = Path(__file__).resolve().parent
if str(_CURRENT_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_MODULE_DIR))

VERSION = "1.0.0"


class BaseToolingSystem(ABC):
    """
    Abstract contract for model tooling and skill abstraction layers.
    Purely generic; contains zero hardcoded application tools.
    """

    system_name: str = "generic_tooling"

    @abstractmethod
    def is_enabled(self) -> bool:
        """Return True if this tooling subsystem is enabled by the active configuration gate."""
        raise NotImplementedError

    @abstractmethod
    def register_tool(
        self,
        tool_declaration_schema_dict: Dict[str, Any],
        tool_execution_handler_callable: Optional[Callable[..., Any]] = None,
    ) -> None:
        """Register a tool declaration and optional execution callable handler."""
        raise NotImplementedError

    @abstractmethod
    def list_registered_tool_names(self) -> List[str]:
        """Return list of registered tool names."""
        raise NotImplementedError

    @abstractmethod
    def build_provider_tools(
        self,
        requested_tool_identifiers_list: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Compile provider-compliant tool declaration dictionaries for API wire payloads.
        Returns empty list if tooling is disabled.
        """
        raise NotImplementedError

    @abstractmethod
    def execute_tool_call(
        self,
        tool_call_invocation_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a single tool call from the model and return structured result payload."""
        raise NotImplementedError

    # Name_Case Method Forwarders
    def Is_Enabled(self) -> bool:
        return self.is_enabled()

    def Register_Tool(
        self,
        tool_declaration_schema_dict: Dict[str, Any],
        tool_execution_handler_callable: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.register_tool(tool_declaration_schema_dict, tool_execution_handler_callable)

    def List_Registered_Tool_Names(self) -> List[str]:
        return self.list_registered_tool_names()

    def Build_Provider_Tools(
        self,
        requested_tool_identifiers_list: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        return self.build_provider_tools(requested_tool_identifiers_list)

    def Execute_Tool_Call(
        self,
        tool_call_invocation_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self.execute_tool_call(tool_call_invocation_payload)


# Canonical Name_Case Alias
Base_Tooling_System = BaseToolingSystem

