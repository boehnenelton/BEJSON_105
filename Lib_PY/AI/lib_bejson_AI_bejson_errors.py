"""
Library:         lib_bejson_AI_bejson_errors.py
Family:          AI
Module Purpose:  Centralized Family Error Code Registry for AI Provider Interfaces & Model Dispatch
Architecture:    BEJSON 105 Error Registry Standard (Allocated Range: 200 - 235)
Version:         1.0.0
Release_Version: 300
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   a4f8c210-6b3e-4d91-9e5a-1c7b8d4f2001
"""
from __future__ import annotations

from typing import Dict, Final

VERSION: Final[str] = "1.0.0"

# ---------------------------------------------------------------------------
# AI Provider Interfaces & Model Dispatch (200 - 235)
# Policy §7.5: No raw integers in application logic; import named constants.
# ---------------------------------------------------------------------------
ERR_AI_SUCCESS: Final[int] = 0

# General & Dispatcher Errors (200 - 209)
ERR_AI_BASE: Final[int] = 200
ERR_AI_INVALID_PAYLOAD: Final[int] = 201
ERR_AI_SCHEMA_MISMATCH: Final[int] = 202
ERR_AI_UNKNOWN_PROVIDER: Final[int] = 203
ERR_AI_PROVIDER_NOT_REGISTERED: Final[int] = 204
ERR_AI_DISPATCH_FAILED: Final[int] = 205
ERR_AI_INTENT_UNRESOLVED: Final[int] = 206

# Translator & Pipeline Gate Errors (210 - 219)
ERR_AI_TRANSLATION_FAILED: Final[int] = 210
ERR_AI_PREPROCESS_REJECTED: Final[int] = 211
ERR_AI_TOKEN_LIMIT_EXCEEDED: Final[int] = 212
ERR_AI_XML_PARSE_FAILED: Final[int] = 213
ERR_AI_POSTPROCESS_REJECTED: Final[int] = 214
ERR_AI_OUTPUT_VALIDATION_FAILED: Final[int] = 215
ERR_AI_SANITIZER_BLOCKED: Final[int] = 216
ERR_AI_TOOLING_DISABLED: Final[int] = 217
ERR_AI_TOOLING_SYSTEM_NOT_FOUND: Final[int] = 218
ERR_AI_TOOL_EXECUTION_FAILED: Final[int] = 219

# Security, Vault & JIT Key Errors (220 - 226)
ERR_AI_VAULT_NOT_FOUND: Final[int] = 220
ERR_AI_VAULT_PARSE_FAILED: Final[int] = 221
ERR_AI_KEY_MISSING: Final[int] = 222
ERR_AI_KEY_EXHAUSTED: Final[int] = 223
ERR_AI_KEY_INJECTION_FAILED: Final[int] = 224

# Provider Transport & HTTP REST Errors (227 - 235)
ERR_AI_HTTP_TIMEOUT: Final[int] = 227
ERR_AI_HTTP_AUTH_FAILED: Final[int] = 228
ERR_AI_HTTP_RATE_LIMITED: Final[int] = 229
ERR_AI_HTTP_BAD_RESPONSE: Final[int] = 230
ERR_AI_HTTP_NETWORK_ERROR: Final[int] = 231
ERR_AI_PROVIDER_ERROR: Final[int] = 232
ERR_AI_INTERACTION_STATE_INVALID: Final[int] = 233

ERROR_DESCRIPTIONS: Final[Dict[int, str]] = {
    ERR_AI_SUCCESS: "Operation completed successfully.",
    ERR_AI_BASE: "Unspecified AI family error.",
    ERR_AI_INVALID_PAYLOAD: "The provided AI request or response payload is invalid.",
    ERR_AI_SCHEMA_MISMATCH: "Payload structure does not match BEJSON 105 AI schema.",
    ERR_AI_UNKNOWN_PROVIDER: "Requested AI service provider is not supported.",
    ERR_AI_PROVIDER_NOT_REGISTERED: "No client driver registered for the target provider.",
    ERR_AI_DISPATCH_FAILED: "Dispatcher failed to route or complete the AI request.",
    ERR_AI_INTENT_UNRESOLVED: "Unable to resolve target provider or intent from payload.",
    ERR_AI_TRANSLATION_FAILED: "Failed to translate between BEJSON and provider schema.",
    ERR_AI_PREPROCESS_REJECTED: "Inbound payload rejected by preprocessor control gate.",
    ERR_AI_TOKEN_LIMIT_EXCEEDED: "Prompt buffer exceeds configured token or character limit.",
    ERR_AI_XML_PARSE_FAILED: "Malformed XML control block encountered during preprocessing.",
    ERR_AI_POSTPROCESS_REJECTED: "Outbound response rejected by postprocessor control gate.",
    ERR_AI_OUTPUT_VALIDATION_FAILED: "Provider response failed structured output validation.",
    ERR_AI_SANITIZER_BLOCKED: "Response blocked by postprocessing content sanitizer.",
    ERR_AI_TOOLING_DISABLED: "Tooling system is disabled by external configuration gate.",
    ERR_AI_TOOLING_SYSTEM_NOT_FOUND: "Requested tooling system is not registered in ToolingRegistry.",
    ERR_AI_TOOL_EXECUTION_FAILED: "Execution of local or client tool callable failed.",
    ERR_AI_VAULT_NOT_FOUND: "Environment vault or secret configuration file not found.",
    ERR_AI_VAULT_PARSE_FAILED: "Failed to safely parse environment vault file.",
    ERR_AI_KEY_MISSING: "No API key available for the target provider.",
    ERR_AI_KEY_EXHAUSTED: "All rotated API keys for the provider are exhausted or cooled down.",
    ERR_AI_KEY_INJECTION_FAILED: "JIT key injection failed during client execution.",
    ERR_AI_HTTP_TIMEOUT: "HTTP REST request to AI provider timed out.",
    ERR_AI_HTTP_AUTH_FAILED: "AI provider rejected authentication credentials (HTTP 401/403).",
    ERR_AI_HTTP_RATE_LIMITED: "AI provider rate limit exceeded (HTTP 429).",
    ERR_AI_HTTP_BAD_RESPONSE: "AI provider returned malformed or unexpected HTTP payload.",
    ERR_AI_HTTP_NETWORK_ERROR: "Network transport failure communicating with AI provider.",
    ERR_AI_PROVIDER_ERROR: "AI provider returned an application-level error.",
    ERR_AI_INTERACTION_STATE_INVALID: "Gemini interaction state or step sequence is invalid.",
}


class AIException(Exception):
    """Domain exception enforcing AI family error registry codes (200-235)."""

    def __init__(self, code: int, message: str = "") -> None:
        self.code: int = code
        self.description: str = ERROR_DESCRIPTIONS.get(code, "Unknown AI family error.")
        self.detail: str = message
        full_msg = f"[Error {self.code}] {self.description}"
        if self.detail:
            full_msg += f" Details: {self.detail}"
        super().__init__(full_msg)
