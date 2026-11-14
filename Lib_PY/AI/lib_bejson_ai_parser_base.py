"""
Library:         lib_bejson_ai_parser_base.py
Family:          AI
Module Purpose:  Tier 2 Abstract Base Contract for Modular Pre/Post Parser Plugins
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 2: Model Features & Gates)
Version:         1.0.0
Release_Version: 300
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   9c2b4d1e-8f3a-4a7b-a01c-6d5e9f8a2019
"""
from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict

_CURRENT_MODULE_DIR = Path(__file__).resolve().parent
if str(_CURRENT_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_MODULE_DIR))

VERSION = "1.0.0"


class BaseModularParser(ABC):
    """
    Abstract contract for modular pre/post processing plugins.
    Allows attaching and detaching parser plugins to inspect or transform
    inbound requests and outbound responses (e.g. client turn-continuation commands).
    """

    parser_name: str = "generic_modular_parser"

    @abstractmethod
    def parse_pre(
        self,
        incoming_request_payload_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Transform or inspect inbound normalized request payload before dispatch.
        Must return the updated or unmodified request payload dictionary.
        """
        raise NotImplementedError

    @abstractmethod
    def parse_post(
        self,
        incoming_response_envelope_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Transform or inspect outbound response envelope from provider before delivery.
        Must return the updated or unmodified response envelope dictionary.
        """
        raise NotImplementedError

    # Name_Case Method Forwarders
    def Parse_Pre(
        self,
        incoming_request_payload_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Name_Case forwarder for parse_pre."""
        return self.parse_pre(incoming_request_payload_dict)

    def Parse_Post(
        self,
        incoming_response_envelope_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Name_Case forwarder for parse_post."""
        return self.parse_post(incoming_response_envelope_dict)


# Canonical Name_Case Alias
Base_Modular_Parser = BaseModularParser
