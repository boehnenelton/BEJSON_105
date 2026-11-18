"""
Library:         lib_bejson_AI_Core_client_base.py
Family:          AI_Core
Module Purpose:  Tier 3 Parent Abstract Interface for all AI Provider Drivers
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 3: Service Callers & Security)
Version:         2.0.0
Release_Version: 300
Date:            2026-11-17
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   d12d4cf9-06b0-4f00-bf57-cf64b0aa8a53

Changelog:
  2.0.0 (2026-11-17) -- AI family renamed to AI_Core (was lib_bejson_ai_*). BEJSON read/write now via Core bridge where applicable.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

VERSION = "2.0.0"


class BaseAIClient(ABC):
    """
    Abstract base contract for all `lib_bejson_AI_Core_client_<provider>` drivers.

    Every provider driver must expose `provider_name` and implement `execute_call()`
    accepting a translated provider payload and a JIT-injected API key.
    """

    provider_name: str = "base"
    default_model: str = ""

    @abstractmethod
    def execute_call(
        self,
        provider_payload: Dict[str, Any],
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """
        Execute a synchronous call against the target AI service provider.

        Args:
            provider_payload: Provider-native request dictionary produced by Tier 1 Translator.
            api_key: Secret credential injected JIT by `lib_bejson_AI_Core_jit_key_handler`.
            model: Optional model identifier override.
            timeout: Request timeout in seconds.

        Returns:
            Raw provider response dictionary ready for Tier 1 Translator normalization.
        """
        raise NotImplementedError

    def health_check(self) -> Dict[str, Any]:
        """Return lightweight driver readiness metadata without making network calls."""
        return {
            "provider": self.provider_name,
            "default_model": self.default_model,
            "status": "ready",
            "version": VERSION,
        }
