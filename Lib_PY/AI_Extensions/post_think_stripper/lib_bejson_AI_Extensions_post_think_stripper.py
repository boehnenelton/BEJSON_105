"""
Library:         lib_bejson_AI_Extensions_post_think_stripper.py
Family:          AI_Extensions
Module Purpose:  Post-stage plugin: removes <think>...</think> reasoning blocks from the response text.
Version:         1.0.0
Release_Version: 300
Date:            2026-11-17
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   b0daea0f-c233-40d1-8f26-a6c343f3990c
"""
from __future__ import annotations

import re
from typing import Any, Dict

from lib_bejson_AI_Core_plugin_base import BasePlugin

VERSION = "1.0.0"
_THINK = re.compile(r"<think>.*?</think>\s*", re.DOTALL | re.IGNORECASE)


class ThinkStripper(BasePlugin):
    plugin_id = "post_think_stripper"
    stage = "post"

    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        text = payload.get("text")
        if not isinstance(text, str) or "<think>" not in text.lower():
            return payload
        return {**payload, "text": _THINK.sub("", text).strip()}
