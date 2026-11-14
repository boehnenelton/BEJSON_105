"""
Library:         lib_bejson_ai_translator.py
Family:          AI
Module Purpose:  Tier 1 Payload Normalizer (BEJSON 105 <-> Provider-Specific Schemas)
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 1: Abstraction Layers)
Version:         1.1.0
Release_Version: 300
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   c0d8f017-4b89-403d-b03a-9e2f4a8c0009
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_CURRENT_MODULE_DIR = Path(__file__).resolve().parent
if str(_CURRENT_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_MODULE_DIR))

from lib_bejson_AI_bejson_errors import (  # noqa: E402
    AIException,
    ERR_AI_TRANSLATION_FAILED,
    ERR_AI_UNKNOWN_PROVIDER,
)
from lib_bejson_ai_features_common import build_bejson_105_ai_response  # noqa: E402

VERSION = "1.1.0"


class AITranslator:
    """
    Translates standardized internal / BEJSON 105 request objects into provider-native
    HTTP payloads and normalizes provider responses back into canonical & BEJSON 105 envelopes.
    """

    def to_provider_payload(
        self,
        target_provider_identifier_name: str,
        standardized_request_payload_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        normalized_provider_token = target_provider_identifier_name.lower().strip()
        if normalized_provider_token == "geminirest":
            return self._to_gemini_rest(standardized_request_payload_dict)
        if normalized_provider_token == "geminiinteractions":
            return self._to_gemini_interactions(standardized_request_payload_dict)
        raise AIException(
            ERR_AI_UNKNOWN_PROVIDER,
            f"Translator has no outbound schema for '{target_provider_identifier_name}'.",
        )

    def from_provider_response(
        self,
        target_provider_identifier_name: str,
        raw_provider_response_dict: Dict[str, Any],
        target_model_name_identifier: str,
    ) -> Dict[str, Any]:
        normalized_provider_token = target_provider_identifier_name.lower().strip()
        if normalized_provider_token == "geminirest":
            return self._from_gemini_rest(raw_provider_response_dict, model_name_identifier=target_model_name_identifier)
        if normalized_provider_token == "geminiinteractions":
            return self._from_gemini_interactions(raw_provider_response_dict, model_name_identifier=target_model_name_identifier)
        raise AIException(
            ERR_AI_UNKNOWN_PROVIDER,
            f"Translator has no inbound schema for '{target_provider_identifier_name}'.",
        )

    def to_bejson_105_response(
        self,
        normalized_response_envelope_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        return build_bejson_105_ai_response(
            provider=str(normalized_response_envelope_dict.get("provider", "geminirest")),
            model=str(normalized_response_envelope_dict.get("model", "")),
            text=str(normalized_response_envelope_dict.get("text", "")),
            finish_reason=str(normalized_response_envelope_dict.get("finish_reason", "STOP")),
            usage=normalized_response_envelope_dict.get("usage"),
            structured_data=normalized_response_envelope_dict.get("structured_data"),
        )

    def _to_gemini_rest(
        self,
        standardized_request_payload_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        formatted_contents_list: List[Dict[str, Any]] = []
        if "messages" in standardized_request_payload_dict and isinstance(standardized_request_payload_dict["messages"], list):
            for message_entry_record in standardized_request_payload_dict["messages"]:
                source_role_label = message_entry_record.get("role", "user")
                mapped_gemini_role = "model" if source_role_label in ("assistant", "model") else "user"
                formatted_contents_list.append({
                    "role": mapped_gemini_role,
                    "parts": [{"text": str(message_entry_record.get("content", ""))}],
                })
        else:
            formatted_contents_list.append({
                "role": "user",
                "parts": [{"text": str(standardized_request_payload_dict.get("prompt", ""))}],
            })

        outbound_payload_dict: Dict[str, Any] = {"contents": formatted_contents_list}

        system_instruction_text = str(standardized_request_payload_dict.get("system_instruction", "") or "").strip()
        if system_instruction_text:
            outbound_payload_dict["systemInstruction"] = {"parts": [{"text": system_instruction_text}]}

        generation_config_dictionary: Dict[str, Any] = {}
        if "temperature" in standardized_request_payload_dict and standardized_request_payload_dict["temperature"] is not None:
            generation_config_dictionary["temperature"] = float(standardized_request_payload_dict["temperature"])
        if "max_tokens" in standardized_request_payload_dict and standardized_request_payload_dict["max_tokens"] is not None:
            generation_config_dictionary["maxOutputTokens"] = int(standardized_request_payload_dict["max_tokens"])
        if str(standardized_request_payload_dict.get("response_format", "")).lower() == "json":
            generation_config_dictionary["responseMimeType"] = "application/json"
        if generation_config_dictionary:
            outbound_payload_dict["generationConfig"] = generation_config_dictionary

        return outbound_payload_dict

    def _to_gemini_interactions(
        self,
        standardized_request_payload_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Format payload for Google Gemini Interactions API (/v1beta/interactions).
        Encodes input items, model identifier, previous interaction reference, and tools.
        """
        target_model_identifier = str(standardized_request_payload_dict.get("model", "gemini-3.1-flash-lite")).strip()

        # Build inputs list
        interaction_inputs_list: List[Dict[str, Any]] = []
        if "inputs" in standardized_request_payload_dict and isinstance(standardized_request_payload_dict["inputs"], list):
            interaction_inputs_list.extend(standardized_request_payload_dict["inputs"])
        elif "messages" in standardized_request_payload_dict and isinstance(standardized_request_payload_dict["messages"], list):
            for message_entry_record in standardized_request_payload_dict["messages"]:
                if isinstance(message_entry_record, dict):
                    message_role_token = str(message_entry_record.get("role", "user")).lower()
                    message_content_payload = message_entry_record.get("content", "")
                    if message_role_token == "tool":
                        interaction_inputs_list.append({
                            "type": "function_result",
                            "name": str(message_entry_record.get("name", "tool")),
                            "call_id": str(message_entry_record.get("call_id", "")),
                            "result": [{"type": "text", "text": str(message_content_payload)}],
                        })
                    else:
                        interaction_inputs_list.append({
                            "type": "text",
                            "text": str(message_content_payload),
                        })
        else:
            prompt_content_string = str(standardized_request_payload_dict.get("prompt", ""))
            interaction_inputs_list.append({
                "type": "text",
                "text": prompt_content_string,
            })

        outbound_payload_dict: Dict[str, Any] = {
            "model": target_model_identifier,
            "input": interaction_inputs_list,
            "store": True,
        }

        # Multi-turn interaction chaining reference
        previous_interaction_id_token = standardized_request_payload_dict.get("previous_interaction_id")
        if previous_interaction_id_token:
            outbound_payload_dict["previous_interaction_id"] = str(previous_interaction_id_token).strip()

        # Wire tool definitions
        wire_tool_definitions_list = standardized_request_payload_dict.get("tools")
        if wire_tool_definitions_list and isinstance(wire_tool_definitions_list, list):
            outbound_payload_dict["tools"] = wire_tool_definitions_list

        return outbound_payload_dict

    def _from_gemini_rest(
        self,
        raw_provider_response_dict: Dict[str, Any],
        model_name_identifier: str,
    ) -> Dict[str, Any]:
        response_candidates_list = raw_provider_response_dict.get("candidates")
        if not isinstance(response_candidates_list, list) or not response_candidates_list:
            raise AIException(
                ERR_AI_TRANSLATION_FAILED,
                "Gemini REST response missing 'candidates' list.",
            )
        primary_candidate_record = response_candidates_list[0]
        candidate_content_container = primary_candidate_record.get("content", {})
        candidate_content_parts_list = candidate_content_container.get("parts", [])
        text_content_chunks_list = [
            str(part_entry_record.get("text", ""))
            for part_entry_record in candidate_content_parts_list
            if isinstance(part_entry_record, dict) and "text" in part_entry_record
        ]
        aggregated_response_text_str = "".join(text_content_chunks_list)
        candidate_finish_reason_token = str(primary_candidate_record.get("finishReason", "STOP"))
        token_usage_metadata_dict = raw_provider_response_dict.get("usageMetadata", {})
        return {
            "provider": "geminirest",
            "model": model_name_identifier,
            "text": aggregated_response_text_str,
            "finish_reason": candidate_finish_reason_token,
            "usage": token_usage_metadata_dict,
            "raw": raw_provider_response_dict,
        }

    def _from_gemini_interactions(
        self,
        raw_provider_response_dict: Dict[str, Any],
        model_name_identifier: str,
    ) -> Dict[str, Any]:
        """
        Normalize response from Google Gemini Interactions API (/v1beta/interactions).
        Extracts interaction_id, text from model_output steps, thoughts, and tool_calls.
        """
        interaction_session_id_token = str(raw_provider_response_dict.get("id", ""))
        interaction_lifecycle_status_token = str(raw_provider_response_dict.get("status", "completed"))
        interaction_execution_steps_list = raw_provider_response_dict.get("steps", [])

        extracted_text_chunks_list: List[str] = []
        extracted_thought_chunks_list: List[str] = []
        extracted_tool_calls_list: List[Dict[str, Any]] = []

        if isinstance(interaction_execution_steps_list, list):
            for step_record_dictionary in interaction_execution_steps_list:
                if not isinstance(step_record_dictionary, dict):
                    continue
                step_type_name_token = str(step_record_dictionary.get("type", "")).lower()

                if step_type_name_token == "model_output":
                    output_content_payload = step_record_dictionary.get("content", [])
                    if isinstance(output_content_payload, list):
                        for output_part_record in output_content_payload:
                            if isinstance(output_part_record, dict) and "text" in output_part_record:
                                extracted_text_chunks_list.append(str(output_part_record["text"]))
                    elif isinstance(output_content_payload, str):
                        extracted_text_chunks_list.append(output_content_payload)

                elif step_type_name_token == "thought":
                    thought_content_payload = step_record_dictionary.get("content") or step_record_dictionary.get("text", "")
                    if isinstance(thought_content_payload, list):
                        for thought_part_record in thought_content_payload:
                            if isinstance(thought_part_record, dict) and "text" in thought_part_record:
                                extracted_thought_chunks_list.append(str(thought_part_record["text"]))
                    elif isinstance(thought_content_payload, str):
                        extracted_thought_chunks_list.append(thought_content_payload)

                elif step_type_name_token == "function_call":
                    raw_tool_arguments_payload = step_record_dictionary.get("arguments", {})
                    parsed_arguments_dict: Dict[str, Any] = {}
                    if isinstance(raw_tool_arguments_payload, dict):
                        parsed_arguments_dict = raw_tool_arguments_payload
                    elif isinstance(raw_tool_arguments_payload, str):
                        try:
                            parsed_arguments_dict = json.loads(raw_tool_arguments_payload)
                        except (json.JSONDecodeError, TypeError):
                            parsed_arguments_dict = {"raw": raw_tool_arguments_payload}

                    extracted_tool_calls_list.append({
                        "id": str(step_record_dictionary.get("id", "")),
                        "name": str(step_record_dictionary.get("name", "")),
                        "arguments": parsed_arguments_dict,
                    })

        aggregated_response_text_str = "".join(extracted_text_chunks_list)
        aggregated_thought_text_str = "".join(extracted_thought_chunks_list)
        token_usage_metadata_dict = raw_provider_response_dict.get("usage", {})

        return {
            "provider": "geminiinteractions",
            "model": model_name_identifier,
            "text": aggregated_response_text_str,
            "thought": aggregated_thought_text_str,
            "finish_reason": interaction_lifecycle_status_token.upper(),
            "interaction_id": interaction_session_id_token,
            "tool_calls": extracted_tool_calls_list,
            "usage": token_usage_metadata_dict,
            "raw": raw_provider_response_dict,
        }

    # Name_Case Method Bindings
    To_Provider_Payload = to_provider_payload
    From_Provider_Response = from_provider_response
    To_BEJSON_105_Response = to_bejson_105_response


# Canonical Name_Case Alias
AI_Translator = AITranslator
