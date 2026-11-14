"""
Library:         lib_bejson_ai_features_common.py
Family:          AI
Module Purpose:  Tier 2 Shared Validation, XML/JSON Extraction, Token Estimation & BEJSON 105 Envelope Helpers
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 2: Model Features & Gates)
Version:         1.0.0
Release_Version: 300
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   f3a5c784-1e56-4d0a-e70d-6b9c1d5f7006
"""
from __future__ import annotations

import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from lib_bejson_AI_bejson_errors import (  # noqa: E402
    AIException,
    ERR_AI_INVALID_PAYLOAD,
    ERR_AI_SCHEMA_MISMATCH,
)

VERSION = "1.0.0"

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


def make_bejson_105_field(name: str, field_type: str = "string") -> Dict[str, Any]:
    """Construct a Format 105 Field definition with mandatory UUIDv4 field_uuid."""
    return {
        "name": name,
        "type": field_type,
        "field_uuid": str(uuid.uuid4()),
    }


def build_bejson_105_ai_request(
    prompt: str,
    provider: str = "geminirest",
    model: str = "gemini-2.5-flash",
    system_instruction: str = "",
    temperature: float = 0.7,
    max_tokens: int = 2048,
    response_format: str = "text",
) -> Dict[str, Any]:
    """Build a Format 105 compliant AI_Request BEJSON document."""
    fields = [
        make_bejson_105_field("provider", "string"),
        make_bejson_105_field("model", "string"),
        make_bejson_105_field("system_instruction", "string"),
        make_bejson_105_field("prompt", "string"),
        make_bejson_105_field("temperature", "number"),
        make_bejson_105_field("max_tokens", "integer"),
        make_bejson_105_field("response_format", "string"),
    ]
    record_uuid = str(uuid.uuid4())
    return {
        "Format": "BEJSON",
        "Format_Version": "105",
        "Record_Type_Parent": "AI_Request",
        "Fields": fields,
        "Values": [
            [
                record_uuid,
                provider,
                model,
                system_instruction,
                prompt,
                temperature,
                max_tokens,
                response_format,
            ]
        ],
    }


def build_bejson_105_ai_response(
    provider: str,
    model: str,
    text: str,
    finish_reason: str = "STOP",
    usage: Optional[Dict[str, Any]] = None,
    structured_data: Optional[Any] = None,
) -> Dict[str, Any]:
    """Build a Format 105 compliant AI_Response BEJSON document."""
    fields = [
        make_bejson_105_field("provider", "string"),
        make_bejson_105_field("model", "string"),
        make_bejson_105_field("text", "string"),
        make_bejson_105_field("finish_reason", "string"),
        make_bejson_105_field("usage_json", "string"),
        make_bejson_105_field("structured_json", "string"),
    ]
    record_uuid = str(uuid.uuid4())
    return {
        "Format": "BEJSON",
        "Format_Version": "105",
        "Record_Type_Parent": "AI_Response",
        "Fields": fields,
        "Values": [
            [
                record_uuid,
                provider,
                model,
                text,
                finish_reason,
                json.dumps(usage or {}),
                json.dumps(structured_data) if structured_data is not None else "",
            ]
        ],
    }


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
        field_names = [f["name"] if isinstance(f, dict) else str(f) for f in fields]
        norm = dict(zip(field_names, row[1:]))
        norm["_record_uuid"] = row[0]
        return norm

    if "prompt" not in payload and "messages" not in payload:
        raise AIException(ERR_AI_INVALID_PAYLOAD, "Request payload must include 'prompt' or 'messages'.")
    return dict(payload)
