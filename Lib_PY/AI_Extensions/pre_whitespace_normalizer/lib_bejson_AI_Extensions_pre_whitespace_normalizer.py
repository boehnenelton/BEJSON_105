"""
Library:         lib_bejson_AI_Extensions_pre_whitespace_normalizer.py
Family:          AI_Extensions
Module Purpose:  Pre-stage plugin: collapses runs of blank lines and trailing spaces in the prompt.
Version:         1.0.0
Release_Version: 300
Date:            2026-11-17
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   29f4b80d-7bd3-4796-8784-6611a27f8024
"""
from __future__ import annotations

import re
from typing import Any, Dict

from lib_bejson_AI_Core_plugin_base import BasePlugin

VERSION = "1.0.0"
_BLANKS = re.compile(r"\n{3,}")
_TRAILING = re.compile(r"[ \t]+$", re.MULTILINE)


class WhitespaceNormalizer(BasePlugin):
    plugin_id = "pre_whitespace_normalizer"
    stage = "pre"

    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        prompt = payload.get("prompt")
        if not isinstance(prompt, str):
            return payload
        cleaned = _BLANKS.sub("\n\n", _TRAILING.sub("", prompt)).strip()
        return {**payload, "prompt": cleaned}
