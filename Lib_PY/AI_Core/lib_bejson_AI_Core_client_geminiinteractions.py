"""
Library:         lib_bejson_AI_Core_client_geminiinteractions.py
Family:          AI_Core
Module Purpose:  Tier 3 Zero-Dependency HTTP Client for Google Gemini Interactions API
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 3: Service Callers & Security)
Version:         2.0.0
Release_Version: 300
Date:            2026-11-17
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   0af481da-284a-430e-8e1e-4082382914ef

Changelog:
  2.0.0 (2026-11-17) -- AI family renamed to AI_Core (was lib_bejson_ai_*). BEJSON read/write now via Core bridge where applicable.
"""
from __future__ import annotations

import json
import logging
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, Optional

_CURRENT_MODULE_DIR = Path(__file__).resolve().parent
if str(_CURRENT_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_MODULE_DIR))

from lib_bejson_AI_Core_errors import (  # noqa: E402
    AIException,
    ERR_AI_HTTP_AUTH_FAILED,
    ERR_AI_HTTP_BAD_RESPONSE,
    ERR_AI_HTTP_NETWORK_ERROR,
    ERR_AI_HTTP_RATE_LIMITED,
    ERR_AI_HTTP_TIMEOUT,
    ERR_AI_KEY_INJECTION_FAILED,
    ERR_AI_PROVIDER_ERROR,
)
from lib_bejson_AI_Core_client_base import BaseAIClient  # noqa: E402
from lib_bejson_AI_Core_models import Gemini_3_1_Flash_Lite  # noqa: E402

from lib_bejson_AI_Core_features_common import redact_provider_error_text  # noqa: E402

_LOGGER_INSTANCE = logging.getLogger("lib_bejson_AI_Core_client_geminiinteractions")

VERSION = "2.0.0"

DEFAULT_GEMINI_INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
DEFAULT_INTERACTIONS_MODEL = Gemini_3_1_Flash_Lite


class GeminiInteractionsClient(BaseAIClient):
    """
    Pure-stdlib REST client for Gemini Interactions API (`/v1beta/interactions` endpoint).
    Uses `x-goog-api-key` header so API keys never appear in request URLs.
    Supports multi-turn state via `previous_interaction_id` and server-managed session graphs.
    """

    provider_name: str = "geminiinteractions"
    default_model: str = DEFAULT_INTERACTIONS_MODEL

    def __init__(
        self,
        base_url: str = DEFAULT_GEMINI_INTERACTIONS_URL,
        transport: Optional[Callable[[urllib.request.Request, int], bytes]] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._transport = transport

    def build_endpoint_url(self, model: Optional[str] = None) -> str:
        """Interactions API uses a single canonical endpoint with model specified inside JSON payload."""
        return self.base_url

    def execute_call(
        self,
        provider_payload: Dict[str, Any],
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 60,
    ) -> Dict[str, Any]:
        if not api_key:
            raise AIException(
                ERR_AI_KEY_INJECTION_FAILED,
                "GeminiInteractionsClient requires a JIT-injected API key.",
            )

        target_endpoint_url = self.build_endpoint_url(model=model)
        request_body_bytes = json.dumps(provider_payload).encode("utf-8")
        api_request_object = urllib.request.Request(
            url=target_endpoint_url,
            data=request_body_bytes,
            method="POST",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "x-goog-api-key": api_key,
            },
        )

        try:
            if self._transport is not None:
                raw_response_bytes = self._transport(api_request_object, timeout)
            else:
                with urllib.request.urlopen(api_request_object, timeout=timeout) as network_http_response:
                    raw_response_bytes = network_http_response.read()
        except urllib.error.HTTPError as http_error_exception:
            response_status_code = http_error_exception.code
            _LOGGER_INSTANCE.warning("Gemini Interactions HTTP %s", response_status_code)
            error_response_body_text = ""
            try:
                error_response_body_text = http_error_exception.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            if response_status_code in (401, 403):
                raise AIException(
                    ERR_AI_HTTP_AUTH_FAILED,
                    f"HTTP {response_status_code}: {redact_provider_error_text(error_response_body_text)}",
                ) from http_error_exception
            if response_status_code == 429:
                raise AIException(
                    ERR_AI_HTTP_RATE_LIMITED,
                    f"HTTP 429: {redact_provider_error_text(error_response_body_text)}",
                ) from http_error_exception
            raise AIException(
                ERR_AI_PROVIDER_ERROR,
                f"HTTP {response_status_code}: {redact_provider_error_text(error_response_body_text)}",
            ) from http_error_exception
        except (TimeoutError, socket.timeout) as timeout_exception:
            raise AIException(
                ERR_AI_HTTP_TIMEOUT,
                f"Request timed out after {timeout}s",
            ) from timeout_exception
        except urllib.error.URLError as url_network_exception:
            if isinstance(url_network_exception.reason, (TimeoutError, socket.timeout)):
                raise AIException(
                    ERR_AI_HTTP_TIMEOUT,
                    f"Request timed out: {url_network_exception.reason}",
                ) from url_network_exception
            raise AIException(
                ERR_AI_HTTP_NETWORK_ERROR,
                f"Network error: {url_network_exception.reason}",
            ) from url_network_exception

        try:
            parsed_json_response = json.loads(raw_response_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as json_decode_exception:
            raise AIException(
                ERR_AI_HTTP_BAD_RESPONSE,
                f"Invalid JSON from Gemini Interactions: {json_decode_exception}",
            ) from json_decode_exception

        if not isinstance(parsed_json_response, dict):
            raise AIException(
                ERR_AI_HTTP_BAD_RESPONSE,
                "Gemini Interactions response root must be a JSON object.",
            )
        if "error" in parsed_json_response:
            raise AIException(ERR_AI_PROVIDER_ERROR, str(parsed_json_response["error"]))
        return parsed_json_response


# Canonical Name_Case Alias
Gemini_Interactions_Client = GeminiInteractionsClient

