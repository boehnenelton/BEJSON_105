"""
Library:         lib_bejson_ai_preprocessor.py
Family:          AI
Module Purpose:  Tier 2 Inbound Pipeline Gate (XML Parsing, System Injection, Buffer Formatting, Token Limits)
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 2: Model Features & Gates)
Version:         1.0.0
Release_Version: 300
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   a8b6d895-2f67-4e1b-f81e-7c0d2e6a8007
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from lib_bejson_AI_bejson_errors import (  # noqa: E402
    AIException,
    ERR_AI_PREPROCESS_REJECTED,
    ERR_AI_TOKEN_LIMIT_EXCEEDED,
    ERR_AI_XML_PARSE_FAILED,
)
from lib_bejson_ai_features_common import (  # noqa: E402
    estimate_tokens,
    extract_xml_blocks,
    strip_xml_blocks,
)

VERSION = "1.0.0"


class AIPreprocessor:
    """
    Inbound pipeline filter that extracts XML control directives (`<system_config>`,
    `<context>`), injects system instructions, formats the prompt buffer, and enforces
    token/character boundaries before translation.
    """

    def __init__(
        self,
        max_input_tokens: int = 32000,
        default_system_instruction: str = "",
        strip_control_xml: bool = True,
    ) -> None:
        self.max_input_tokens = max_input_tokens
        self.default_system_instruction = default_system_instruction
        self.strip_control_xml = strip_control_xml

    def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Mutate and validate inbound normalized request dictionary."""
        out = dict(request)
        prompt = str(out.get("prompt", "") or "")

        if not prompt.strip() and not out.get("messages"):
            raise AIException(ERR_AI_PREPROCESS_REJECTED, "Empty prompt buffer rejected by preprocessor.")

        # Check for unclosed control tags if XML directives are present
        if "<system_config>" in prompt and "</system_config>" not in prompt:
            raise AIException(ERR_AI_XML_PARSE_FAILED, "Unclosed <system_config> block in prompt.")

        xml_blocks = extract_xml_blocks(prompt)
        sys_parts = []
        if self.default_system_instruction:
            sys_parts.append(self.default_system_instruction.strip())
        if out.get("system_instruction"):
            sys_parts.append(str(out["system_instruction"]).strip())
        if "system_config" in xml_blocks:
            sys_parts.extend(xml_blocks["system_config"])

        if sys_parts:
            out["system_instruction"] = "\n\n".join(p for p in sys_parts if p)

        if self.strip_control_xml and "system_config" in xml_blocks:
            prompt = strip_xml_blocks(prompt, tags=["system_config"])

        out["prompt"] = prompt.strip()
        out["_xml_blocks"] = xml_blocks

        # Enforce token boundary gate
        total_text = f"{out.get('system_instruction', '')}\n{out['prompt']}"
        estimated = estimate_tokens(total_text)
        limit = int(out.get("max_input_tokens", self.max_input_tokens))
        if estimated > limit:
            raise AIException(
                ERR_AI_TOKEN_LIMIT_EXCEEDED,
                f"Estimated input tokens ({estimated}) exceed limit ({limit}).",
            )
        out["_estimated_input_tokens"] = estimated
        return out
