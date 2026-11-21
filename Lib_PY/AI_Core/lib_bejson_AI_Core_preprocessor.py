"""
Library:         lib_bejson_AI_Core_preprocessor.py
Family:          AI_Core
Module Purpose:  Tier 2 Inbound Pipeline Gate (XML Parsing, Context Bubble Assembly, System Injection, Buffer Formatting, Token Limits)
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 2: Model Features & Gates)
Version:         2.1.0
Release_Version: 300
Date:            2026-11-20
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   a6ae25f2-652e-420c-9cd6-e74c9ea05b96

Changelog:
  2.1.0 (2026-11-20) -- Integrated BEJSON 105 Context Bubble engine (ai_bubble_prepare) directly into AIPreprocessor.
  2.0.0 (2026-11-17) -- AI family renamed to AI_Core (was lib_bejson_ai_*). BEJSON read/write now via Core bridge where applicable.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from lib_bejson_AI_Core_context_bubble import ai_bubble_prepare  # noqa: E402
from lib_bejson_AI_Core_errors import (  # noqa: E402
    AIException,
    ERR_AI_PREPROCESS_REJECTED,
    ERR_AI_TOKEN_LIMIT_EXCEEDED,
    ERR_AI_XML_PARSE_FAILED,
)
from lib_bejson_AI_Core_features_common import (  # noqa: E402
    estimate_tokens,
    extract_xml_blocks,
    strip_xml_blocks,
)

VERSION = "2.1.0"


class AIPreprocessor:
    """
    Inbound pipeline filter that extracts XML control directives (`<system_config>`,
    `<context>`), assembles the BEJSON 105 Context Bubble when enabled, injects system
    instructions, formats the prompt buffer, and enforces token/character boundaries
    before translation.
    """

    def __init__(
        self,
        max_input_tokens: int = 32000,
        default_system_instruction: str = "",
        strip_control_xml: bool = True,
        bubble_context_dir: Optional[Path | str] = None,
        bubble_config_dir: Optional[Path | str] = None,
        bubble_enabled: bool = False,
        bubble_rebuild_interval: Optional[int] = None,
    ) -> None:
        self.max_input_tokens = max_input_tokens
        self.default_system_instruction = default_system_instruction
        self.strip_control_xml = strip_control_xml
        self.bubble_context_dir = Path(bubble_context_dir) if bubble_context_dir else None
        self.bubble_config_dir = Path(bubble_config_dir) if bubble_config_dir else None
        self.bubble_enabled = bubble_enabled
        self.bubble_rebuild_interval = bubble_rebuild_interval

    def configure_context_bubble(
        self,
        context_dir: Path | str,
        config_dir: Path | str,
        enabled: bool = True,
        rebuild_interval: Optional[int] = None,
    ) -> None:
        """Configure and enable the BEJSON 105 Context Bubble on this preprocessor."""
        self.bubble_context_dir = Path(context_dir)
        self.bubble_config_dir = Path(config_dir)
        self.bubble_enabled = bool(enabled)
        if rebuild_interval is not None:
            self.bubble_rebuild_interval = int(rebuild_interval)

    def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Mutate and validate inbound normalized request dictionary."""
        out = dict(request)
        prompt = str(out.get("prompt", "") or "")

        if not prompt.strip() and not out.get("messages"):
            raise AIException(ERR_AI_PREPROCESS_REJECTED, "Empty prompt buffer rejected by preprocessor.")

        # Check for unclosed control tags if XML directives are present
        if "<system_config>" in prompt and "</system_config>" not in prompt:
            raise AIException(ERR_AI_XML_PARSE_FAILED, "Unclosed <system_config> block in prompt.")

        xml_blocks = extract_xml_blocks(prompt)
        sys_parts = []
        if self.default_system_instruction:
            sys_parts.append(self.default_system_instruction.strip())
        if out.get("system_instruction"):
            sys_parts.append(str(out["system_instruction"]).strip())
        if "system_config" in xml_blocks:
            sys_parts.extend(xml_blocks["system_config"])

        if self.strip_control_xml and "system_config" in xml_blocks:
            prompt = strip_xml_blocks(prompt, tags=["system_config"])

        out["prompt"] = prompt.strip()
        out["_xml_blocks"] = xml_blocks

        # Execute BEJSON 105 Context Bubble assembly when enabled
        use_bubble = bool(out.get("use_context_bubble", self.bubble_enabled))
        ctx_dir = out.get("bubble_context_dir") or self.bubble_context_dir
        cfg_dir = out.get("bubble_config_dir") or self.bubble_config_dir
        if use_bubble and ctx_dir and cfg_dir:
            extras = dict(out.get("bubble_extras") or {})
            for key in ("url_context", "attached_file_ids", "history", "profile_instruction"):
                if key in out and key not in extras:
                    extras[key] = out[key]
            skip: Tuple[str, ...] = tuple(out.get("bubble_skip") or ())
            interval_override = out.get("bubble_interval_override")
            if interval_override is None:
                interval_override = self.bubble_rebuild_interval
            bubble_result = ai_bubble_prepare(
                context_dir=Path(ctx_dir),
                config_dir=Path(cfg_dir),
                user_msg=out["prompt"],
                extras=extras,
                skip=skip,
                interval_override=interval_override,
            )
            bubble_text = str(bubble_result.get("text") or "").strip()
            if bubble_text:
                sys_parts.append(bubble_text)
            out["_context_bubble"] = bubble_result

        if sys_parts:
            out["system_instruction"] = "\n\n".join(p for p in sys_parts if p)

        # Enforce token boundary gate
        total_text = f"{out.get('system_instruction', '')}\n{out['prompt']}"
        estimated = estimate_tokens(total_text)
        limit = int(out.get("max_input_tokens", self.max_input_tokens))
        if estimated > limit:
            raise AIException(
                ERR_AI_TOKEN_LIMIT_EXCEEDED,
                f"Estimated input tokens ({estimated}) exceed limit ({limit}).",
            )
        out["_estimated_input_tokens"] = estimated
        return out
