"""
Library:         lib_bejson_ai_postprocessor.py
Family:          AI
Module Purpose:  Tier 2 Outbound Pipeline Gate (Response Cleaning, JSON/XML Parsing, Content Sanitizers)
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 2: Model Features & Gates)
Version:         1.0.0
Release_Version: 300
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   b9c7e906-3a78-4f2c-a92f-8d1e3f7b9008
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from lib_bejson_AI_bejson_errors import (  # noqa: E402
    AIException,
    ERR_AI_OUTPUT_VALIDATION_FAILED,
    ERR_AI_POSTPROCESS_REJECTED,
    ERR_AI_SANITIZER_BLOCKED,
)
from lib_bejson_ai_features_common import (  # noqa: E402
    extract_json_payload,
    extract_xml_blocks,
)

VERSION = "1.0.0"

_KEY_LEAK_RE = re.compile(r"AIza[0-9A-Za-z\-_]{20,}")


class AIPostprocessor:
    """
    Outbound pipeline filter that cleans model responses, extracts structured JSON/XML
    outputs, validates required response schemas, and strips leaked secrets.
    """

    def __init__(
        self,
        redact_api_keys: bool = True,
        unwrap_xml_tag: Optional[str] = None,
        blocked_patterns: Optional[List[str]] = None,
    ) -> None:
        self.redact_api_keys = redact_api_keys
        self.unwrap_xml_tag = unwrap_xml_tag
        self.blocked_patterns = [re.compile(p) for p in (blocked_patterns or [])]

    def process(
        self,
        normalized_response: Dict[str, Any],
        expected_format: str = "text",
    ) -> Dict[str, Any]:
        """Clean, validate, and enrich normalized response dictionary."""
        out = dict(normalized_response)
        text = str(out.get("text", "") or "").strip()

        if not text:
            raise AIException(
                ERR_AI_POSTPROCESS_REJECTED,
                "Provider returned an empty response text.",
            )

        for pattern in self.blocked_patterns:
            if pattern.search(text):
                raise AIException(
                    ERR_AI_SANITIZER_BLOCKED,
                    "Response matched blocked sanitizer pattern.",
                )

        if self.redact_api_keys:
            text = _KEY_LEAK_RE.sub("[REDACTED_API_KEY]", text)

        if self.unwrap_xml_tag:
            xml_blocks = extract_xml_blocks(text)
            if self.unwrap_xml_tag in xml_blocks and xml_blocks[self.unwrap_xml_tag]:
                text = xml_blocks[self.unwrap_xml_tag][0]

        out["text"] = text
        out["xml_blocks"] = extract_xml_blocks(text)

        if expected_format.lower() == "json":
            parsed = extract_json_payload(text)
            if parsed is None:
                raise AIException(
                    ERR_AI_OUTPUT_VALIDATION_FAILED,
                    "Expected JSON output but response could not be parsed as JSON.",
                )
            out["structured_data"] = parsed

        return out
