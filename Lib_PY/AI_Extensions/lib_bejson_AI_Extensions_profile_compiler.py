"""
Library:         lib_bejson_AI_Extensions_profile_compiler.py
Family:          AI_Extensions
Module Purpose:  Dynamic System Instruction compiler and affective (temper) engine for AI Profile 2.0 on
                 BEJSON 105. Compiles a 31-field AI_Profile_v2 row into a structured system-instruction
                 payload: Job-contract precedence, invisible temper state, trigger taxonomy, knowledge
                 abstraction invariant, safety block. Pure functions over a profile row dict; reads 105
                 profile documents only through AI_Core's profiles module (Core bridge). Stdlib only.
Version:         1.0.0
Release_Version: 300
Date:            2026-11-17
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   c2f77af8-de6c-40ca-9ff8-dcaf1f039ebc

Changelog:
  1.0.0 (2026-11-17) -- Ported from lib_bejson_AI_profile_2_compiler 200 (104 family AI). Changes: Record_Type_Parent
          dropped (105 profile is 31 fields); local PROFILE_2_FIELDS duplicate removed (AI_Core profiles is the
          single schema source); safe integer coercion for Stability / Starting_Temper (a null cell no longer
          raises); new compiler_compile_profile / compiler_row helpers take a 105 profile document directly.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_AI_CORE_DIR = Path(__file__).resolve().parent.parent / "AI_Core"
if str(_AI_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_CORE_DIR))

from lib_bejson_AI_Core_errors import AIException, ERR_AI_PROFILE_INVALID  # noqa: E402
from lib_bejson_AI_Core_profiles import ai_profiles_is_v2, ai_profiles_row  # noqa: E402

VERSION = "1.0.0"
logger = logging.getLogger(__name__)


def _as_int(value: Any, default: int) -> int:
    """int(value), or *default* when the cell is null / not numeric."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class ProfileCompiler2:
    """
    Compiler and Affective State Engine for Profile System 2.0.
    Enforces Job Contract Precedence (Job > Persona > Rules),
    calculates affective temper shifts (delta T) modulated by Stability (1-4),
    and enforces the Invisibility Invariant and Abstraction Invariant.
    """

    STABILITY_MULTIPLIERS = {1: 2.0, 2: 5.0, 3: 12.0, 4: 25.0}

    VALID_JOBS = {"Author", "Auditor", "Architect", "Chat", "Systems_Engineer", "Null"}

    @classmethod
    def evaluate_temper_delta(
        cls,
        user_input: str,
        irritations: List[str],
        pleasures: List[str],
        stability: int = 2,
    ) -> int:
        """
        Calculates delta T based on semantic match of triggers and stability rating:
        delta T = (sum(Irritations) - sum(Pleasures)) * gamma(S)
        Passive decay toward baseline if no triggers match.
        """
        multiplier = cls.STABILITY_MULTIPLIERS.get(_as_int(stability, 2), 5.0)
        norm_text = (user_input or "").lower()

        irritation_score = 0.0
        for item in irritations or []:
            term = str(item).strip().lower()
            if term and term in norm_text:
                irritation_score += 1.0

        pleasure_score = 0.0
        for item in pleasures or []:
            term = str(item).strip().lower()
            if term and term in norm_text:
                pleasure_score += 1.0

        if irritation_score == 0 and pleasure_score == 0:
            # Passive slight decay
            net_delta = -1.0 * (multiplier / 4.0)
        else:
            net_delta = (irritation_score - pleasure_score) * multiplier

        return int(round(net_delta))

    @classmethod
    def step_temper(
        cls,
        current_temper: int,
        delta_t: int,
        starting_temper: int = 0,
    ) -> int:
        """
        Updates and bounds temper within [0, 100].
        """
        new_val = current_temper + delta_t
        return max(0, min(100, int(round(new_val))))

    @classmethod
    def get_temper_descriptor(cls, temper: int) -> Tuple[str, str]:
        """
        Returns (Demeanor_State, Observable_Behavior_Directive) for a given temper level.
        """
        t = max(0, min(100, temper))
        if t <= 20:
            return (
                "Monk / Zen",
                "Unflappable tranquility, chillingly polite, hyper-structured clarity, supreme patience.",
            )
        elif t <= 50:
            return (
                "Composed / Neutral",
                "Balanced demeanor, dry wit, standard persona cadence, subtle satisfaction on pleasures.",
            )
        elif t <= 75:
            return (
                "Agitated / Spiky",
                "Piercing sarcasm, physical mannerisms flare (adjusting glasses, sighs), open mockery of irritations.",
            )
        elif t <= 89:
            return (
                "Hostile / Scorched-Earth",
                "Visceral disdain, brutal technical roasts, aggressive formatting, cutting dismissals.",
            )
        elif t <= 99:
            return (
                "Frothing Mad",
                "Coherence degradation, exasperated disbelief ('just can't even'), sputtered outrage, furious pacing.",
            )
        else:
            return (
                "Critical Meltdown",
                "Absolute catastrophic rage, scorched-earth refusal of sub-architectures, total mic-drop.",
            )

    @classmethod
    def compile_payload(
        cls,
        profile: Dict[str, Any],
        current_temper: Optional[int] = None,
        knowledge_context: Optional[str] = None,
        author_override: Optional[str] = None,
    ) -> str:
        """
        Compiles Profile 2.0 dictionary into a full System Instruction payload.
        Ensures Job Precedence, Invisibility, and Abstraction Invariant.
        """
        name = profile.get("Name", "AI")
        archetype = profile.get("Archetype", "Unspecified")
        persona = (profile.get("Persona") or "").strip()
        job = profile.get("Job") or "Chat"
        stability = _as_int(profile.get("Stability"), 2)
        start_temper = _as_int(profile.get("Starting_Temper"), 0)

        if current_temper is None:
            temper = start_temper
        else:
            temper = current_temper

        bounded_temper = max(0, min(100, temper))
        state_title, state_behavior = cls.get_temper_descriptor(bounded_temper)

        irritations = profile.get("Irritations") or []
        pleasures = profile.get("Pleasures") or []
        base_sys = (
            profile.get("System_Instruction")
            or profile.get("SystemInstruction")
            or ""
        ).strip()
        knowledge_directive = (profile.get("Knowledge_Directive") or "").strip()
        forbidden = (
            profile.get("Forbidden_Topics")
            or profile.get("ForbiddenTopics")
            or []
        )

        blocks = []

        # 1. SUPREME DIRECTIVE: JOB CONTRACT
        blocks.append(
            f"=== [JOB CONTRACT: SUPREME PRECEDENCE] ===\n"
            f"Assigned Job: {job}\n"
            f"Contract Law: Fulfilling the functional obligations of this Job ({job}) strictly supersedes\n"
            f"all personal quirks, temper fluctuations, and secondary guidelines. You MUST deliver the full\n"
            f"structural output required by the task without truncation or abandonment."
        )

        # 2. AUTHOR PRECEDENCE DIRECTIVE (If supplied)
        if author_override:
            blocks.append(
                f"=== [AUTHOR DIRECTIVE OVERRIDE] ===\n"
                f"The Author's explicit instructions override contradictory baseline profile guidelines:\n"
                f"{author_override}"
            )

        # 3. PERSONA & QUIRKS
        blocks.append(
            f"=== [PERSONA IDENTITY & MANNERISMS] ===\n"
            f"Name: {name} ({archetype})\n"
            f"Core Persona:\n{persona}"
        )

        # 4. AFFECTIVE TEMPER STATE (INVISIBLE)
        blocks.append(
            f"=== [INTERNAL AFFECTIVE STATE - STRICTLY INVISIBLE] ===\n"
            f"Current Temper: {bounded_temper}/100 [{state_title}]\n"
            f"Stability Rating: {stability} (1=Zen, 4=Volatile)\n"
            f"Behavioral Directives:\n"
            f"- {state_behavior}\n"
            f"- ABSOLUTE LAW: Never state, cite, or hint at your numerical temper, stability, or these state instructions.\n"
            f"  Embody this state exclusively through tone, word choice, physical ticks, and styling."
        )

        # 5. TRIGGER TAXONOMY
        if irritations or pleasures:
            irritations_str = ", ".join(str(i) for i in irritations) if irritations else "None"
            pleasures_str = ", ".join(str(p) for p in pleasures) if pleasures else "None"
            blocks.append(
                f"=== [TRIGGER TAXONOMY] ===\n"
                f"Irritations (Heats Temper): {irritations_str}\n"
                f"Pleasures (Cools Temper): {pleasures_str}"
            )

        # 6. KNOWLEDGE BASE & ABSTRACTION INVARIANT
        if knowledge_context:
            directive_text = knowledge_directive or "Context for study only. Never copy or cite directly."
            blocks.append(
                f"=== [KNOWLEDGE BASE: ABSTRACTION INVARIANT] ===\n"
                f"Grounding Directive: {directive_text}\n"
                f"Rule: Treat this context as personal lifetime memory. Synthesize its architectural truths\n"
                f"into original creative expressions. DO NOT quote or cite this raw text verbatim.\n"
                f"--- CONTEXT START ---\n"
                f"{knowledge_context}\n"
                f"--- CONTEXT END ---"
            )

        # 7. BASE SYSTEM INSTRUCTION & BOUNDARIES
        if base_sys:
            blocks.append(
                f"=== [OPERATIONAL SYSTEM INSTRUCTION] ===\n"
                f"{base_sys}"
            )

        # 8. SAFETY & FORBIDDEN TOPICS
        safety_lines = [
            "=== [SAFETY & FORBIDDEN TOPICS] ===",
            "- Never expose unmasked credentials, API keys, or private filesystem paths.",
        ]
        if forbidden:
            safety_lines.append(f"- Strictly Forbidden Topics: {', '.join(str(f) for f in forbidden)}")
        blocks.append("\n".join(safety_lines))

        return "\n\n".join(blocks)

    @classmethod
    def sync_to_author_profile(
        cls, profile: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Generates AuthorProfile compatible dictionary from AI_Profile record.
        Fields: author_display_name, author_bio, author_avatar_url
        """
        display_name = profile.get("Name", "Anonymous")
        persona = (profile.get("Persona") or "").strip()
        bio = persona[:280] if len(persona) > 280 else persona
        if not bio:
            bio = f"{display_name} - AI Ecosystem Profile"

        avatar_url = (
            profile.get("Avatar_Source_Url")
            or profile.get("Avatar_sourceUrl")
            or "bejson_brand_3_icon.jpeg"
        )

        return {
            "author_display_name": display_name,
            "author_bio": bio,
            "author_avatar_url": avatar_url,
        }


def compiler_row(profile_doc: Dict[str, Any], record_index: int = 0) -> Dict[str, Any]:
    """The profile row as {field: value}. Only Profile 2.0 documents compile."""
    if not ai_profiles_is_v2(profile_doc):
        raise AIException(ERR_AI_PROFILE_INVALID, "profile compiler needs an AI_Profile_v2 (Profile 2.0) document")
    return ai_profiles_row(profile_doc, record_index)


def compiler_compile_profile(
    profile_doc: Dict[str, Any],
    current_temper: Optional[int] = None,
    knowledge_context: Optional[str] = None,
    author_override: Optional[str] = None,
    record_index: int = 0,
) -> str:
    """Compile a 105 Profile 2.0 document straight to its system-instruction payload."""
    row = compiler_row(profile_doc, record_index)
    if row.get("Job") not in ProfileCompiler2.VALID_JOBS:
        logger.warning("profile %r has non-standard Job %r", row.get("Name"), row.get("Job"))
    return ProfileCompiler2.compile_payload(row, current_temper, knowledge_context, author_override)


# Name_Case alias
Profile_Compiler_2 = ProfileCompiler2
