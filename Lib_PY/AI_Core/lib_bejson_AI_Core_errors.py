"""
Library:         lib_bejson_AI_Core_errors.py
Family:          AI_Core
Module Purpose:  Centralized Family Error Code Registry for AI Provider Interfaces & Model Dispatch
Architecture:    BEJSON 105 Error Registry Standard (Allocated Range: 200 - 249)
Version:         2.0.0
Release_Version: 300
Date:            2026-11-17
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   6501066b-af29-4f1a-ad02-b60af586b544

Changelog:
  2.0.0 (2026-11-17) -- AI family renamed to AI_Core (was lib_bejson_AI_bejson_errors.py). BEJSON read/write now via Core bridge where applicable.
"""
from __future__ import annotations

from typing import Dict, Final

VERSION: Final[str] = "2.0.0"

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

# Core Dependency & Document I/O Errors (207 - 209, 225 - 226)
ERR_AI_CORE_DEP_UNAVAILABLE: Final[int] = 207
ERR_AI_FAMILY_VALIDATION_FAILED: Final[int] = 208
ERR_AI_DOCUMENT_INVALID: Final[int] = 209
ERR_AI_DOCUMENT_WRITE_FAILED: Final[int] = 225
ERR_AI_FREEZE_MANIFEST_MISMATCH: Final[int] = 226

# Plugin Registry Errors (236 - 245)
ERR_AI_PLUGIN_BASE: Final[int] = 236
ERR_AI_PLUGIN_MANIFEST_INVALID: Final[int] = 237
ERR_AI_PLUGIN_DUPLICATE: Final[int] = 238
ERR_AI_PLUGIN_NOT_FOUND: Final[int] = 239
ERR_AI_PLUGIN_STAGE_INVALID: Final[int] = 240
ERR_AI_PLUGIN_LOAD_FAILED: Final[int] = 241
ERR_AI_PLUGIN_UNTRUSTED_DIRECTORY: Final[int] = 242
ERR_AI_PLUGIN_CORE_VERSION_INCOMPATIBLE: Final[int] = 243
ERR_AI_PLUGIN_EXECUTION_FAILED: Final[int] = 244
# 245 reserved

# Profile Errors (246 - 249)
ERR_AI_PROFILE_INVALID: Final[int] = 246
ERR_AI_PROFILE_NOT_FOUND: Final[int] = 247
ERR_AI_PROFILE_MIGRATION_FAILED: Final[int] = 248

# Provider Transport & HTTP REST Errors (227 - 235)
ERR_AI_HTTP_TIMEOUT: Final[int] = 227
ERR_AI_HTTP_AUTH_FAILED: Final[int] = 228
ERR_AI_HTTP_RATE_LIMITED: Final[int] = 229
ERR_AI_HTTP_BAD_RESPONSE: Final[int] = 230
ERR_AI_HTTP_NETWORK_ERROR: Final[int] = 231
ERR_AI_PROVIDER_ERROR: Final[int] = 232
ERR_AI_INTERACTION_STATE_INVALID: Final[int] = 233
ERR_AI_RENDERER_NOT_FOUND: Final[int] = 234
ERR_AI_RENDERER_FAILED: Final[int] = 235

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
    ERR_AI_RENDERER_NOT_FOUND: "Requested modular renderer is not registered in RendererRegistry.",
    ERR_AI_RENDERER_FAILED: "Modular post-processing renderer execution failed.",
    ERR_AI_CORE_DEP_UNAVAILABLE: "The main Core family (BEJSON read/write) could not be located.",
    ERR_AI_FAMILY_VALIDATION_FAILED: "AI_Core family validation reported violations.",
    ERR_AI_DOCUMENT_INVALID: "BEJSON document failed Core validation or could not be read.",
    ERR_AI_DOCUMENT_WRITE_FAILED: "Core atomic write of a BEJSON document failed.",
    ERR_AI_FREEZE_MANIFEST_MISMATCH: "AI_Core files differ from the pinned freeze manifest.",
    ERR_AI_PLUGIN_BASE: "Unspecified AI plugin error.",
    ERR_AI_PLUGIN_MANIFEST_INVALID: "Plugin manifest does not conform to the AI plugin 105a schema.",
    ERR_AI_PLUGIN_DUPLICATE: "A plugin with this plugin_id is already registered.",
    ERR_AI_PLUGIN_NOT_FOUND: "Requested plugin is not registered.",
    ERR_AI_PLUGIN_STAGE_INVALID: "Plugin stage must be one of pre, post, render.",
    ERR_AI_PLUGIN_LOAD_FAILED: "Plugin module could not be loaded or its entry class is invalid.",
    ERR_AI_PLUGIN_UNTRUSTED_DIRECTORY: "Plugin discovery outside the trusted extensions directory is disabled.",
    ERR_AI_PLUGIN_CORE_VERSION_INCOMPATIBLE: "Plugin requires a newer AI_Core plugin API than this host provides.",
    ERR_AI_PLUGIN_EXECUTION_FAILED: "Plugin raised while processing a pipeline stage.",
    ERR_AI_PROFILE_INVALID: "AI profile document does not conform to the 105 profile schema.",
    ERR_AI_PROFILE_NOT_FOUND: "Requested AI profile was not found.",
    ERR_AI_PROFILE_MIGRATION_FAILED: "104 to 105 profile conversion failed.",
}


class AIException(Exception):
    """Domain exception enforcing AI family error registry codes (200-249)."""

    def __init__(self, code: int, message: str = "") -> None:
        self.code: int = code
        self.description: str = ERROR_DESCRIPTIONS.get(code, "Unknown AI family error.")
        self.detail: str = message
        full_msg = f"[Error {self.code}] {self.description}"
        if self.detail:
            full_msg += f" Details: {self.detail}"
        super().__init__(full_msg)
