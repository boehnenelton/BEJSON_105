"""
Library:         lib_bejson_AI_Core_features_common.py
Family:          AI_Core
Module Purpose:  Tier 2 Shared Validation, XML/JSON Extraction, Token Estimation & BEJSON 105 Envelope Helpers
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 2: Model Features & Gates)
Version:         2.0.1
Release_Version: 300
Date:            2026-11-19
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   074f10ad-55f8-4a50-9652-e72afd775adf

Changelog:
  2.0.1 (2026-11-19) -- Single default-model constant DEFAULT_TEXT_MODEL_ID (gemini-3.8-flash, registry-verified); merged newest Nov-18 agent-side changes.
  2.0.0 (2026-11-17) -- AI family renamed to AI_Core (was lib_bejson_ai_*). BEJSON read/write now via Core bridge where applicable.
"""
from __future__ import annotations

import logging
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from lib_bejson_AI_Core_core_bridge import core_add_record, core_field_map, core_new_document  # noqa: E402
from lib_bejson_AI_Core_errors import (  # noqa: E402
    AIException,
    ERR_AI_INVALID_PAYLOAD,
    ERR_AI_SCHEMA_MISMATCH,
)

VERSION = "2.0.1"
_LOGGER_INSTANCE = logging.getLogger("lib_bejson_AI_Core_features_common")

_API_KEY_LEAK_RE = re.compile(r"AIza[0-9A-Za-z\-_]{20,}")
MAX_PROVIDER_ERROR_TEXT_CHARS = 500
# Single source for the default text model id. Must be a value in lib_bejson_AI_Core_models.ACTIVE_TEXT_MODELS_REGISTRY (enforced by test).
DEFAULT_TEXT_MODEL_ID = "gemini-3.8-flash"


def redact_provider_error_text(raw_error_text: str, max_chars: int = MAX_PROVIDER_ERROR_TEXT_CHARS) -> str:
    """Redact API-key-shaped tokens and cap length before text is embedded in an exception."""
    redacted_error_text = _API_KEY_LEAK_RE.sub("[REDACTED_API_KEY]", str(raw_error_text))
    if len(redacted_error_text) > max_chars:
        return redacted_error_text[:max_chars] + " [truncated]"
    return redacted_error_text

_XML_TAG_RE = re.compile(r"<([a-zA-Z_][a-zA-Z0-9_-]*)>(.*?)</\1>", re.DOTALL)
_CODE_FENCE_JSON_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL | re.IGNORECASE)


def estimate_tokens(text: str) -> int:
    """Fast heuristic token estimator (~4 chars per token)."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def extract_xml_blocks(text: str) -> Dict[str, List[str]]:
    """Extract top-level `<tag>...</tag>` blocks into a dict of tag -> list of inner strings."""
    blocks: Dict[str, List[str]] = {}
    if not text:
        return blocks
    for match in _XML_TAG_RE.finditer(text):
        tag = match.group(1)
        body = match.group(2).strip()
        blocks.setdefault(tag, []).append(body)
    return blocks


def strip_xml_blocks(text: str, tags: Optional[List[str]] = None) -> str:
    """Remove specified XML tag blocks (or all matched XML blocks if tags is None)."""
    if not text:
        return ""
    if tags is None:
        return _XML_TAG_RE.sub("", text).strip()
    tag_set = set(tags)
    return _XML_TAG_RE.sub(lambda m: "" if m.group(1) in tag_set else m.group(0), text).strip()


def extract_json_payload(text: str) -> Optional[Any]:
    """Attempt to parse raw JSON or a ```json ... ``` fenced block from model output."""
    if not text:
        return None
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    for match in _CODE_FENCE_JSON_RE.finditer(stripped):
        candidate = match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


_REQUEST_FIELDS = (
    ("provider", "string"), ("model", "string"), ("system_instruction", "string"), ("prompt", "string"),
    ("temperature", "number"), ("max_tokens", "integer"), ("response_format", "string"),
)
_RESPONSE_FIELDS = (
    ("provider", "string"), ("model", "string"), ("text", "string"), ("finish_reason", "string"),
    ("usage_json", "string"), ("structured_json", "string"), ("interaction_id", "string"),
    ("rendered_output", "string"), ("rendered_format", "string"), ("turn_continuation_json", "string"),
)


def build_bejson_105_ai_request(
    prompt: str,
    provider: str = "geminirest",
    model: str = DEFAULT_TEXT_MODEL_ID,
    system_instruction: str = "",
    temperature: float = 0.7,
    max_tokens: int = 2048,
    response_format: str = "text",
) -> Dict[str, Any]:
    """Build a Format 105 compliant AI_Request BEJSON document (via Core)."""
    request_document = core_new_document("105", "AI_Request", _REQUEST_FIELDS)
    core_add_record(request_document, {
        "provider": provider, "model": model, "system_instruction": system_instruction,
        "prompt": prompt, "temperature": float(temperature), "max_tokens": int(max_tokens),
        "response_format": response_format,
    })
    return request_document


def build_bejson_105_ai_response(
    provider: str,
    model: str,
    text: str,
    finish_reason: str = "STOP",
    usage: Optional[Dict[str, Any]] = None,
    structured_data: Optional[Any] = None,
    interaction_id: str = "",
    rendered_output: Optional[str] = None,
    rendered_format: str = "",
    turn_continuation_command: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a Format 105 compliant AI_Response BEJSON document (via Core)."""
    response_document = core_new_document("105", "AI_Response", _RESPONSE_FIELDS)
    core_add_record(response_document, {
        "provider": provider, "model": model, "text": text, "finish_reason": finish_reason,
        "usage_json": json.dumps(usage or {}),
        "structured_json": json.dumps(structured_data) if structured_data is not None else "",
        "interaction_id": interaction_id,
        "rendered_output": rendered_output if rendered_output is not None else "",
        "rendered_format": rendered_format,
        "turn_continuation_json": json.dumps(turn_continuation_command) if turn_continuation_command is not None else "",
    })
    return response_document


def normalize_inbound_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accept either a plain dict request or a Format 105 BEJSON AI_Request document
    and return a normalized internal request dictionary.
    """
    if not isinstance(payload, dict):
        raise AIException(ERR_AI_INVALID_PAYLOAD, "Inbound payload must be a dict.")

    if "Fields" in payload and "Values" in payload:
        fmt_ver = str(payload.get("Format_Version", ""))
        if fmt_ver and fmt_ver != "105":
            raise AIException(
                ERR_AI_SCHEMA_MISMATCH,
                f"Expected BEJSON Format_Version '105', got '{fmt_ver}'.",
            )
        fields = payload["Fields"]
        values = payload["Values"]
        if not isinstance(fields, list) or not isinstance(values, list) or not values:
            raise AIException(ERR_AI_SCHEMA_MISMATCH, "BEJSON 105 AI_Request requires non-empty Fields and Values.")
        row = values[0]
        if not isinstance(row, list) or len(row) != len(fields) + 1:
            raise AIException(
                ERR_AI_SCHEMA_MISMATCH,
                "BEJSON 105 row must include reserved record_uuid at index 0 (+1 offset).",
            )
        field_map = core_field_map(payload)
        norm = {field_name: row[row_index] for field_name, row_index in field_map.items()}
        norm["_record_uuid"] = row[0]
        return norm

    if "prompt" not in payload and "messages" not in payload:
        raise AIException(ERR_AI_INVALID_PAYLOAD, "Request payload must include 'prompt' or 'messages'.")
    return dict(payload)
