"""
Library:         lib_bejson_AI_Core_plugin_base.py
Family:          AI_Core
Module Purpose:  Abstract contract every AI_Extensions plugin implements. One method, process(),
                 whose payload depends on the stage: pre -> request dict, post -> response
                 envelope dict, render -> cleaned envelope dict (set rendered_output / rendered_format).
Version:         2.0.0
Release_Version: 300
Date:            2026-11-17
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   9c41f7b3-2e08-4a6d-b5e1-3f80d2a7c6e4
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

VERSION = "2.0.0"


class BasePlugin(ABC):
    """Subclass, set plugin_id/stage (they must match the manifest), implement process()."""

    plugin_id: str = ""
    stage: str = ""

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        self.config: Dict[str, Any] = dict(config or {})

    @abstractmethod
    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Return the (possibly new) payload dict. Must not mutate shared state outside self."""
        raise NotImplementedError

    def Process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Name_Case forwarder."""
        return self.process(payload)


Base_Plugin = BasePlugin
