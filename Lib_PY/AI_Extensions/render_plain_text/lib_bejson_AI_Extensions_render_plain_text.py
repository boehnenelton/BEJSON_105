"""
Library:         lib_bejson_AI_Extensions_render_plain_text.py
Family:          AI_Extensions
Module Purpose:  Render-stage plugin: strips Markdown emphasis/heading/fence markers into terminal-friendly plain text (rendered_output, rendered_format=text).
Version:         1.0.0
Release_Version: 300
Date:            2026-11-17
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   18c94795-271f-408b-854e-e14a4b0f5250
"""
from __future__ import annotations

import re
from typing import Any, Dict

from lib_bejson_AI_Core_plugin_base import BasePlugin

VERSION = "1.0.0"
_FENCE = re.compile(r"^```[A-Za-z0-9_+-]*\s*$", re.MULTILINE)
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+", re.MULTILINE)
_EMPHASIS = re.compile(r"(\*\*|__|\*|_|`)(?=\S)(.+?)(?<=\S)\1")


class PlainTextRenderer(BasePlugin):
    plugin_id = "render_plain_text"
    stage = "render"

    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        text = payload.get("text")
        if not isinstance(text, str):
            return payload
        plain = _EMPHASIS.sub(r"\2", _HEADING.sub("", _FENCE.sub("", text)))
        return {**payload, "rendered_output": plain.strip(), "rendered_format": "text"}
