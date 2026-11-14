"""
Library:         lib_bejson_ai_client_geminirest.py
Family:          AI
Module Purpose:  Tier 3 Zero-Dependency HTTP REST Client for Google Gemini API
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 3: Service Callers & Security)
Version:         1.0.0
Release_Version: 300
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   e2f4b673-0d45-4c99-d6fc-5a8b0c4e6005
"""
from __future__ import annotations

import json
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, Optional

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

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

VERSION = "1.0.0"

DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-lite"


class GeminiRestClient(BaseAIClient):
    """
    Pure-stdlib REST client for Gemini (`generateContent` endpoint).
    Uses `x-goog-api-key` header so API keys never appear in request URLs.
    """

    provider_name: str = "geminirest"
    default_model: str = DEFAULT_GEMINI_MODEL

    def __init__(
        self,
        base_url: str = DEFAULT_GEMINI_BASE_URL,
        transport: Optional[Callable[[urllib.request.Request, int], bytes]] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._transport = transport

    def build_endpoint_url(self, model: Optional[str] = None) -> str:
        target_model = (model or self.default_model).strip()
        if target_model.startswith("models/"):
            target_model = target_model[len("models/"):]
        return f"{self.base_url}/{target_model}:generateContent"

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
                "GeminiRestClient requires a JIT-injected API key.",
            )

        target_endpoint_url = self.build_endpoint_url(model=model)
        body_bytes = json.dumps(provider_payload).encode("utf-8")
        api_request_object = urllib.request.Request(
            url=target_endpoint_url,
            data=body_bytes,
            method="POST",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "x-goog-api-key": api_key,
            },
        )

        try:
            if self._transport is not None:
                raw_bytes = self._transport(api_request_object, timeout)
            else:
                with urllib.request.urlopen(api_request_object, timeout=timeout) as resp:
                    raw_bytes = resp.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            err_body = ""
            try:
                err_body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            if status in (401, 403):
                raise AIException(ERR_AI_HTTP_AUTH_FAILED, f"HTTP {status}: {err_body}") from exc
            if status == 429:
                raise AIException(ERR_AI_HTTP_RATE_LIMITED, f"HTTP 429: {err_body}") from exc
            raise AIException(ERR_AI_PROVIDER_ERROR, f"HTTP {status}: {err_body}") from exc
        except (TimeoutError, socket.timeout) as exc:
            raise AIException(ERR_AI_HTTP_TIMEOUT, f"Request timed out after {timeout}s") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise AIException(ERR_AI_HTTP_TIMEOUT, f"Request timed out: {exc.reason}") from exc
            raise AIException(ERR_AI_HTTP_NETWORK_ERROR, f"Network error: {exc.reason}") from exc

        try:
            parsed = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AIException(ERR_AI_HTTP_BAD_RESPONSE, f"Invalid JSON from Gemini REST: {exc}") from exc

        if not isinstance(parsed, dict):
            raise AIException(ERR_AI_HTTP_BAD_RESPONSE, "Gemini REST response root must be a JSON object.")
        if "error" in parsed:
            raise AIException(ERR_AI_PROVIDER_ERROR, str(parsed["error"]))
        return parsed


# Canonical Name_Case Alias
Gemini_Rest_Client = GeminiRestClient

