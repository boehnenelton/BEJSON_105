"""
Library:         lib_bejson_ai_models.py
Family:          AI
Module Purpose:  Modern Gemini and Multi-AI Model Taxonomy Registry (Name_Case Constants and Catalog)
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 1: Service Abstractor & Catalog)
Version:         1.0.0
Release_Version: 300
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   b8e2f4a0-7d1c-4389-9e2c-3b5a1f8c9014
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

_CURRENT_MODULE_DIR = Path(__file__).resolve().parent
if str(_CURRENT_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_MODULE_DIR))

from lib_bejson_AI_bejson_errors import AIException, ERR_AI_PROVIDER_ERROR  # noqa: E402

VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Canonical Name_Case Model Identifiers
# ---------------------------------------------------------------------------
Gemini_3_1_Flash_Lite = "gemini-3.1-flash-lite"
Gemini_3_5_Flash_Lite = "gemini-3.5-flash-lite"
Gemini_3_8_Flash = "gemini-3.8-flash"
Gemini_4_Argon = "gemini-4-argon"
Gemini_4_Hydrogen = "gemini-4-hydrogen"
Gemini_Flash_Lite_Latest = "gemini-flash-lite-latest"
Gemini_Flash_Latest = "gemini-flash-latest"
Gemini_Pro_Latest = "gemini-pro-latest"
Gemma_4_31B = "gemma-4-31b-it"
Antigravity_Preview_Latest = "antigravity-preview-latest"

ACTIVE_TEXT_MODELS_REGISTRY: Dict[str, str] = {
    "Gemini_3_1_Flash_Lite": Gemini_3_1_Flash_Lite,
    "Gemini_3_5_Flash_Lite": Gemini_3_5_Flash_Lite,
    "Gemini_3_8_Flash": Gemini_3_8_Flash,
    "Gemini_4_Argon": Gemini_4_Argon,
    "Gemini_4_Hydrogen": Gemini_4_Hydrogen,
    "Gemini_Flash_Lite_Latest": Gemini_Flash_Lite_Latest,
    "Gemini_Flash_Latest": Gemini_Flash_Latest,
    "Gemini_Pro_Latest": Gemini_Pro_Latest,
    "Gemma_4_31B": Gemma_4_31B,
    "Antigravity_Preview_Latest": Antigravity_Preview_Latest,
}


def Resolve_Model_Identifier(requested_model_name_token: str) -> str:
    """
    Resolve a Name_Case or string alias to its canonical Gemini model identifier.
    Example: 'Gemini_3_1_Flash_Lite' -> 'gemini-3.1-flash-lite'
    """
    cleaned_model_name_str = requested_model_name_token.strip()
    if cleaned_model_name_str in ACTIVE_TEXT_MODELS_REGISTRY:
        return ACTIVE_TEXT_MODELS_REGISTRY[cleaned_model_name_str]

    normalized_lookup_token = cleaned_model_name_str.lower().replace("_", "-").replace(" ", "-")
    for canonical_name_case_key, canonical_model_id_str in ACTIVE_TEXT_MODELS_REGISTRY.items():
        if canonical_model_id_str == normalized_lookup_token or canonical_name_case_key.lower() == normalized_lookup_token:
            return canonical_model_id_str

    if cleaned_model_name_str.startswith("models/"):
        return cleaned_model_name_str[len("models/"):]
    return cleaned_model_name_str


def List_Active_Gemini_Models() -> List[str]:
    """Return list of confirmed modern active Gemini models."""
    return list(ACTIVE_TEXT_MODELS_REGISTRY.values())


def Query_Live_Gemini_Models(gemini_api_key_secret: str, timeout_seconds_metric: int = 15) -> List[str]:
    """
    Dynamically query Google Generative Language v1beta endpoint to fetch
    the live list of available models supporting generateContent.
    """
    models_endpoint_url_str = f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_api_key_secret}"
    api_request_object = urllib.request.Request(
        url=models_endpoint_url_str,
        headers={"x-goog-api-key": gemini_api_key_secret},
    )
    try:
        with urllib.request.urlopen(api_request_object, timeout=timeout_seconds_metric) as http_network_response:
            response_json_payload = json.loads(http_network_response.read().decode("utf-8"))
            live_supported_models_list: List[str] = []
            for candidate_model_entry in response_json_payload.get("models", []):
                supported_generation_methods = candidate_model_entry.get("supportedGenerationMethods", [])
                if "generateContent" in supported_generation_methods:
                    raw_model_name_str = str(candidate_model_entry.get("name", ""))
                    if raw_model_name_str.startswith("models/"):
                        raw_model_name_str = raw_model_name_str[len("models/"):]
                    live_supported_models_list.append(raw_model_name_str)
            return live_supported_models_list
    except Exception as exc:
        raise AIException(
            ERR_AI_PROVIDER_ERROR,
            f"Failed to query live Gemini models list: {exc}",
        ) from exc
