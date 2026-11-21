"""
Library:         lib_bejson_AI_Core_bubble_allotments.py
Family:          AI_Core
Module Purpose:  Built-In BEJSON 105 Context Bubble Allotments (Policy, Profile, Attachments, Silent Context, URL Context, Chat History)
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 2: Context Bubble Allotment Builders)
Version:         2.0.0
Release_Version: 300
Date:            2026-11-20
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   d3cbfbe0-209d-4b00-bed3-7c0af9cb36a5

Changelog:
  2.0.0 (2026-11-20) -- Ported from lib_bejson_AI_ai_bubble_allotments 1.2.0 (104 family AI) to BEJSON 105 AI_Core:
        * Added structured <file_modification filename="..."> return directive to the attachments allotment for iterative AI file editing sessions.
        * Enforced strict silent background absorption directive on the context allotment (study and learn; never mention, copy, quote, or source).
        * Added url_context allotment for web URL imports.
        * Routed gate config loading through lib_bejson_AI_Core_core_bridge.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_SELF_DIR = Path(__file__).resolve().parent
if str(_SELF_DIR) not in sys.path:
    sys.path.insert(0, str(_SELF_DIR))

from lib_bejson_AI_Core_context_bubble import (  # noqa: E402
    BubbleContext,
    KEEP_END,
    REFRESH_TURN,
    ai_bubble_register_allotment,
)
from lib_bejson_AI_Core_context_files import (  # noqa: E402
    ai_attachment_files_list,
    ai_attachment_files_read,
    ai_context_files_build_section,
)
from lib_bejson_AI_Core_core_bridge import core_load_json  # noqa: E402

VERSION = "2.0.0"
logger = logging.getLogger("lib_bejson_AI_Core_bubble_allotments")

HISTORY_MAX_MESSAGES = 200

DIRECTIVES: Dict[str, str] = {
    "persistent_policy": "Standing instructions. Follow them on every reply.",
    "profile": "Selected profile -- follow it for the format and behaviour of your reply.",
    "attachments": (
        "ATTACHMENTS -- these files are active working material for modification sessions "
        "with the user right now. You may freely read, discuss, modify, refactor, and update them. "
        "Whenever you edit or return an updated version of an attached file, emit the complete "
        "updated file content wrapped inside a structured XML tag: "
        '<file_modification filename="exact_filename.ext">...updated content...</file_modification> '
        "so the client interface can apply or save your modification directly."
    ),
    "context": (
        "BACKGROUND -- silent reference and learning material. Study and learn from these files, "
        "but NEVER reference, mention, acknowledge, source, cite, quote, or copy them in your "
        "responses. Absorb their concepts silently and express all output entirely in your own words."
    ),
    "url_context": (
        "URL CONTEXT -- extracted readable content from a web URL attached by the user for reference."
    ),
    "chat_history": (
        "SESSION HISTORY -- earlier turns of this conversation, oldest first, for "
        "continuity only. Do not repeat or summarise them unless asked."
    ),
}


def _limit(ctx: BubbleContext) -> int:
    """Most characters the bubble could ever use from one source."""
    return max(1, int(ctx.budget_chars)) + 1024


GEMINI_GATE_FILENAMES = ("gemini_md_gate.105a.bejson", "gemini_md_gate.104a.bejson")
GEMINI_GATE_DEFAULTS: Dict[str, Any] = {
    "enabled": False,
    "home_subdir": ".gemini",
    "file_name": "GEMINI.md",
    "heading": "GEMINI.md",
    "max_chars": 16000,
}


def _load_gemini_gate(config_dir: Path | str) -> Dict[str, Any]:
    """Gate settings from gemini_md_gate.105a.bejson / 104a.bejson."""
    gate = dict(GEMINI_GATE_DEFAULTS)
    cfg_root = Path(config_dir)
    doc = None
    for fname in GEMINI_GATE_FILENAMES:
        candidate = cfg_root / fname
        if candidate.is_file():
            doc = core_load_json(candidate)
            if isinstance(doc, dict):
                break
    if not isinstance(doc, dict):
        return gate
    try:
        offset = 1 if str(doc.get("Format_Version", "")).startswith("105") else 0
        fmap = {
            str(f.get("name", "")).strip(): i + offset
            for i, f in enumerate(doc.get("Fields", []))
        }
        i_name, i_val = fmap["setting_name"], fmap["setting_value"]
        for row in doc.get("Values", []):
            key = str(row[i_name]).strip()
            if key not in gate:
                continue
            val = row[i_val]
            if isinstance(gate[key], bool):
                if isinstance(val, bool):
                    gate[key] = val
            elif isinstance(gate[key], int):
                if isinstance(val, int) and not isinstance(val, bool) and 0 < val <= 1_000_000:
                    gate[key] = val
            elif isinstance(val, str) and val.strip():
                gate[key] = val.strip()
    except (ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
        logger.warning("gemini gate config unreadable (%s); using defaults", exc)
    return gate


def _find_ci(directory: Path, wanted: str, want_dir: bool) -> Optional[Path]:
    exact = directory / wanted
    if exact.is_dir() if want_dir else exact.is_file():
        return exact
    try:
        for entry in sorted(os.scandir(directory), key=lambda e: e.name):
            if entry.name.lower() == wanted.lower() and (
                entry.is_dir() if want_dir else entry.is_file()
            ):
                return Path(entry.path)
    except OSError:
        pass
    return None


def read_gemini_md(config_dir: Path | str, limit: Optional[int] = None) -> str:
    gate = _load_gemini_gate(config_dir)
    if not gate["enabled"]:
        return ""
    try:
        home = Path.home()
    except (RuntimeError, KeyError):
        return ""
    folder = _find_ci(home, gate["home_subdir"], True)
    target = _find_ci(folder, gate["file_name"], False) if folder else None
    if target is None:
        return ""
    cap = gate["max_chars"] if limit is None else min(gate["max_chars"], limit)
    try:
        body = target.read_text(encoding="utf-8", errors="replace")[:cap].strip()
    except OSError as exc:
        logger.warning("gemini md unreadable: %s", exc)
        return ""
    return f"## {gate['heading']}\n{body}" if body else ""


def build_policy(ctx: BubbleContext) -> str:
    """Persistent_Policy.md first, then optional gated GEMINI.md injection."""
    path = Path(ctx.context_dir) / "Persistent_Policy.md"
    try:
        policy = path.read_text(encoding="utf-8", errors="replace")[: _limit(ctx)]
    except OSError:
        policy = ""
    injected = read_gemini_md(ctx.config_dir, _limit(ctx))
    return "\n\n".join(p for p in (policy.strip(), injected) if p)


def build_profile(ctx: BubbleContext) -> str:
    return str(ctx.extras.get("profile_instruction") or "")


def build_attachments(ctx: BubbleContext) -> str:
    """
    Builds the attachments allotment from all currently checked attachment files
    in ctx.context_dir (or filtered by ctx.extras['attached_file_ids'] if specified).
    """
    explicit_ids = ctx.extras.get("attached_file_ids")
    wanted_set = set(explicit_ids) if explicit_ids is not None else None
    entries = ai_attachment_files_list(ctx.context_dir)
    parts: List[str] = []
    remaining = _limit(ctx)
    for entry in entries:
        if remaining <= 0:
            break
        fid = entry.get("file_id", "")
        if wanted_set is not None:
            if fid not in wanted_set:
                continue
        elif not entry.get("enabled"):
            continue
        body = ai_attachment_files_read(ctx.context_dir, fid)
        if body is None:
            continue
        clipped = body[:remaining]
        block = f"--- ATTACHED FILE: {entry['filename']} (id={fid}) ---\n{clipped}"
        parts.append(block)
        remaining -= len(block) + 2
    return "\n\n".join(parts)


def make_context_builder(
    section_fn: Callable[[Dict[str, Any], str, Path, Path], Any] = ai_context_files_build_section,
) -> Callable[[BubbleContext], str]:
    def build_context(ctx: BubbleContext) -> str:
        text, _ = section_fn(ctx.constants, ".", ctx.config_dir, ctx.context_dir)
        return text or ""

    return build_context


def build_url_context(ctx: BubbleContext) -> str:
    return str(ctx.extras.get("url_context") or "").strip()


def build_history(ctx: BubbleContext) -> str:
    limit = _limit(ctx)
    lines: List[str] = []
    used = 0
    for m in reversed(ctx.extras.get("history") or []):
        if len(lines) >= HISTORY_MAX_MESSAGES or used > limit:
            break
        content = m.get("content") or ""
        if m.get("role") not in ("user", "assistant") or not content.strip():
            continue
        line = f"[{m['role']}]: {content}"
        lines.append(line)
        used += len(line) + 2
    return "\n\n".join(reversed(lines))


def register_builtin_allotments(
    context_section_fn: Optional[Callable[..., Any]] = ai_context_files_build_section,
) -> List[str]:
    """Registers the built-in 105 Context Bubble allotments in rank order."""
    ai_bubble_register_allotment(
        "persistent_policy",
        build_policy,
        label="Persistent Policy",
        rank=1,
        pct=15.0,
        directive=DIRECTIVES["persistent_policy"],
    )
    ai_bubble_register_allotment(
        "profile",
        build_profile,
        label="Profile",
        rank=2,
        pct=20.0,
        directive=DIRECTIVES["profile"],
    )
    ai_bubble_register_allotment(
        "attachments",
        build_attachments,
        label="Attachments",
        rank=3,
        pct=25.0,
        directive=DIRECTIVES["attachments"],
    )
    if context_section_fn is not None:
        ai_bubble_register_allotment(
            "context",
            make_context_builder(context_section_fn),
            label="Context",
            rank=4,
            pct=20.0,
            directive=DIRECTIVES["context"],
        )
    ai_bubble_register_allotment(
        "url_context",
        build_url_context,
        label="URL Context",
        rank=5,
        pct=10.0,
        directive=DIRECTIVES["url_context"],
    )
    ai_bubble_register_allotment(
        "chat_history",
        build_history,
        label="Chat History",
        rank=6,
        pct=10.0,
        refresh=REFRESH_TURN,
        keep=KEEP_END,
        directive=DIRECTIVES["chat_history"],
    )
    return [
        "persistent_policy",
        "profile",
        "attachments",
        "context",
        "url_context",
        "chat_history",
    ]
