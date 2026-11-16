"""
Library:         lib_bejson_ai_renderer_base.py
Family:          AI
Module Purpose:  Tier 2 Abstract Base Contract for Modular Post-Processing Renderers
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 2: Model Features & Gates)
Version:         1.0.0
Release_Version: 300
Date:            2026-11-16
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   7e4b91a2-5c3d-4f88-9b12-3a6e7d8c5031
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


class BaseRenderer(ABC):
    """
    Abstract contract for modular post-processing renderer plugins.
    Executes after AIPostprocessor.process() so security redaction,
    blocked-pattern checks, xml_blocks extraction, and structured_data
    parsing are already complete before rendering begins.
    """

    renderer_name: str = "generic_modular_renderer"
    output_format: str = "text"

    @abstractmethod
    def render(
        self,
        cleaned_response_envelope_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Render a post-processed response envelope into a presentation or
        export representation (e.g., setting 'rendered_output' and
        'rendered_format') while preserving 'text', 'structured_data',
        and 'turn_continuation_command'.
        """
        raise NotImplementedError

    # Name_Case Method Forwarder
    def Render(
        self,
        cleaned_response_envelope_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Name_Case forwarder for render."""
        return self.render(cleaned_response_envelope_dict)


# Canonical Name_Case Alias
Base_Renderer = BaseRenderer
