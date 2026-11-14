"""
Library:         lib_bejson_ai_client_geminiinteractions.py
Family:          AI
Module Purpose:  Tier 3 Zero-Dependency HTTP Client for Google Gemini Interactions API
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 3: Service Callers & Security)
Version:         1.0.0
Release_Version: 300
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   b5e1a2c3-4d6f-4789-9e0a-1b2c3d4e5018
"""
from __future__ import annotations

import json
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, Optional

_CURRENT_MODULE_DIR = Path(__file__).resolve().parent
if str(_CURRENT_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_MODULE_DIR))

from lib_bejson_AI_bejson_errors import (  # noqa: E402
    AIException,
    ERR_AI_HTTP_AUTH_FAILED,
    ERR_AI_HTTP_BAD_RESPONSE,
    ERR_AI_HTTP_NETWORK_ERROR,
    ERR_AI_HTTP_RATE_LIMITED,
    ERR_AI_HTTP_TIMEOUT,
    ERR_AI_KEY_INJECTION_FAILED,
    ERR_AI_PROVIDER_ERROR,
)
from lib_bejson_ai_client_base import BaseAIClient  # noqa: E402
from lib_bejson_ai_models import Gemini_3_1_Flash_Lite  # noqa: E402

VERSION = "1.0.0"

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
            error_response_body_text = ""
            try:
                error_response_body_text = http_error_exception.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            if response_status_code in (401, 403):
                raise AIException(
                    ERR_AI_HTTP_AUTH_FAILED,
                    f"HTTP {response_status_code}: {error_response_body_text}",
                ) from http_error_exception
            if response_status_code == 429:
                raise AIException(
                    ERR_AI_HTTP_RATE_LIMITED,
                    f"HTTP 429: {error_response_body_text}",
                ) from http_error_exception
            raise AIException(
                ERR_AI_PROVIDER_ERROR,
                f"HTTP {response_status_code}: {error_response_body_text}",
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

