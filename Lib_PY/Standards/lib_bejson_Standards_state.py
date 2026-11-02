"""
File Name : lib_bejson_Standards_state.py
Rel. Path : Lib_PY/Standards/lib_bejson_Standards_state.py
Purpose   : Standards STATE: Stateful context manager for BEJSON 105 Standards Logging.
            Implements the Loaded Chamber Pattern to decouple context acquisition
            (subsystem, category, actor, session, default flags, key prefix) from event emission.
VERSION   : 3.2.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : 7c89d231-1e42-4f09-9b55-d4a8ef71c991
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VERSION: str = "3.2.0"
_STATE_LOCK: threading.RLock = threading.RLock()

# Default state file location: env pointer or user home directory
DEFAULT_STATE_FILE_PATH: str = os.getenv(
    "BEJSON_STANDARDS_STATE_FILE",
    os.path.expanduser("~/.bejson/standards_logging_state.json")
)

# In-memory context cache
_ACTIVE_CONTEXT_CACHE: Dict[str, Any] = {
    "active_subsystem": None,
    "active_category": None,
    "active_actor": None,
    "active_session": None,
    "active_key_prefix": None,
    "active_default_flags": [],
    "active_default_priority": None,
    "active_target_uuid": None,
    "is_locked": False,
    "updated_at": None
}
_STATE_INITIALIZED: bool = False


def _get_effective_state_file_path(custom_state_file_path: Optional[str] = None) -> str:
    """Resolve the authoritative state file path."""
    if custom_state_file_path:
        return os.path.abspath(os.fspath(custom_state_file_path))
    env_override_path = os.getenv("BEJSON_STANDARDS_STATE_FILE")
    if env_override_path:
        return os.path.abspath(os.fspath(env_override_path))
    return os.path.abspath(os.fspath(DEFAULT_STATE_FILE_PATH))


def bejson_standards_load_state(custom_state_file_path: Optional[str] = None) -> Dict[str, Any]:
    """Load persistent logging context state from disk."""
    global _ACTIVE_CONTEXT_CACHE, _STATE_INITIALIZED
    state_file_target_path: str = _get_effective_state_file_path(custom_state_file_path)

    with _STATE_LOCK:
        if not os.path.isfile(state_file_target_path):
            _STATE_INITIALIZED = True
            return dict(_ACTIVE_CONTEXT_CACHE)

        try:
            with open(state_file_target_path, "r", encoding="utf-8") as state_file_handle:
                loaded_state_document: Dict[str, Any] = json.load(state_file_handle)

            # Extract fields from top-level or BEJSON 104a values
            for context_key_name in _ACTIVE_CONTEXT_CACHE.keys():
                if context_key_name in loaded_state_document:
                    _ACTIVE_CONTEXT_CACHE[context_key_name] = loaded_state_document[context_key_name]

            _STATE_INITIALIZED = True
        except Exception:
            # Non-throwing fallback to ensure zero runtime disruptions
            pass

        return dict(_ACTIVE_CONTEXT_CACHE)


def bejson_standards_persist_state(custom_state_file_path: Optional[str] = None) -> bool:
    """Atomically persist current logging context state to disk using temporary file swap."""
    state_file_target_path: str = _get_effective_state_file_path(custom_state_file_path)

    with _STATE_LOCK:
        current_iso_timestamp: str = datetime.now(timezone.utc).isoformat()
        _ACTIVE_CONTEXT_CACHE["updated_at"] = current_iso_timestamp

        os.makedirs(os.path.dirname(state_file_target_path), exist_ok=True)
        temporary_file_path: str = f"{state_file_target_path}.tmp"

        bejson_state_document: Dict[str, Any] = {
            "Format": "BEJSON",
            "Format_Version": "104a",
            "Format_Creator": "Elton Boehnen",
            "Records_Type": ["LoggingContextState"],
            "active_subsystem": _ACTIVE_CONTEXT_CACHE.get("active_subsystem"),
            "active_category": _ACTIVE_CONTEXT_CACHE.get("active_category"),
            "active_actor": _ACTIVE_CONTEXT_CACHE.get("active_actor"),
            "active_session": _ACTIVE_CONTEXT_CACHE.get("active_session"),
            "active_key_prefix": _ACTIVE_CONTEXT_CACHE.get("active_key_prefix"),
            "active_default_flags": _ACTIVE_CONTEXT_CACHE.get("active_default_flags") or [],
            "active_default_priority": _ACTIVE_CONTEXT_CACHE.get("active_default_priority"),
            "active_target_uuid": _ACTIVE_CONTEXT_CACHE.get("active_target_uuid"),
            "is_locked": _ACTIVE_CONTEXT_CACHE.get("is_locked", False),
            "updated_at": current_iso_timestamp,
            "Fields": [
                {"name": "context_key", "type": "string"},
                {"name": "context_value", "type": "any"},
                {"name": "last_modified", "type": "string"}
            ],
            "Values": [
                ["active_subsystem", _ACTIVE_CONTEXT_CACHE.get("active_subsystem"), current_iso_timestamp],
                ["active_category", _ACTIVE_CONTEXT_CACHE.get("active_category"), current_iso_timestamp],
                ["active_actor", _ACTIVE_CONTEXT_CACHE.get("active_actor"), current_iso_timestamp],
                ["active_session", _ACTIVE_CONTEXT_CACHE.get("active_session"), current_iso_timestamp],
                ["active_key_prefix", _ACTIVE_CONTEXT_CACHE.get("active_key_prefix"), current_iso_timestamp],
                ["active_default_flags", _ACTIVE_CONTEXT_CACHE.get("active_default_flags") or [], current_iso_timestamp],
                ["active_default_priority", _ACTIVE_CONTEXT_CACHE.get("active_default_priority"), current_iso_timestamp],
                ["active_target_uuid", _ACTIVE_CONTEXT_CACHE.get("active_target_uuid"), current_iso_timestamp],
                ["is_locked", _ACTIVE_CONTEXT_CACHE.get("is_locked", False), current_iso_timestamp]
            ]
        }

        try:
            with open(temporary_file_path, "w", encoding="utf-8") as temp_handle:
                json.dump(bejson_state_document, temp_handle, indent=2)
                temp_handle.write("\n")
            os.replace(temporary_file_path, state_file_target_path)
            return True
        except Exception:
            return False


def bejson_standards_set_context(
    subsystem: Optional[str] = None,
    category: Optional[str] = None,
    actor: Optional[str] = None,
    session: Optional[str] = None,
    key_prefix: Optional[str] = None,
    flags: Optional[List[str]] = None,
    priority: Optional[int] = None,
    target_uuid: Optional[str] = None,
    is_locked: bool = True,
    persist: bool = True,
    custom_state_file_path: Optional[str] = None
) -> Dict[str, Any]:
    """Lock logging context into persistent state storage."""
    global _ACTIVE_CONTEXT_CACHE, _STATE_INITIALIZED

    with _STATE_LOCK:
        if not _STATE_INITIALIZED:
            bejson_standards_load_state(custom_state_file_path)

        if subsystem is not None:
            _ACTIVE_CONTEXT_CACHE["active_subsystem"] = str(subsystem).strip()
        if category is not None:
            _ACTIVE_CONTEXT_CACHE["active_category"] = str(category).strip().lower()
        if actor is not None:
            _ACTIVE_CONTEXT_CACHE["active_actor"] = str(actor).strip()
        if session is not None:
            _ACTIVE_CONTEXT_CACHE["active_session"] = str(session).strip()
        if key_prefix is not None:
            _ACTIVE_CONTEXT_CACHE["active_key_prefix"] = str(key_prefix).strip()
        if flags is not None:
            _ACTIVE_CONTEXT_CACHE["active_default_flags"] = [str(f).strip() for f in flags if str(f).strip()]
        if priority is not None:
            _ACTIVE_CONTEXT_CACHE["active_default_priority"] = int(priority)
        if target_uuid is not None:
            _ACTIVE_CONTEXT_CACHE["active_target_uuid"] = str(target_uuid).strip()

        _ACTIVE_CONTEXT_CACHE["is_locked"] = bool(is_locked)

        if persist:
            bejson_standards_persist_state(custom_state_file_path)

        return dict(_ACTIVE_CONTEXT_CACHE)


def bejson_standards_get_context(custom_state_file_path: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve the currently active loaded logging context."""
    global _ACTIVE_CONTEXT_CACHE, _STATE_INITIALIZED
    with _STATE_LOCK:
        if not _STATE_INITIALIZED:
            bejson_standards_load_state(custom_state_file_path)
        return dict(_ACTIVE_CONTEXT_CACHE)


def bejson_standards_clear_context(
    persist: bool = True,
    custom_state_file_path: Optional[str] = None
) -> Dict[str, Any]:
    """Clear all active chamber selections from state."""
    global _ACTIVE_CONTEXT_CACHE
    with _STATE_LOCK:
        for context_key_name in _ACTIVE_CONTEXT_CACHE.keys():
            if context_key_name == "active_default_flags":
                _ACTIVE_CONTEXT_CACHE[context_key_name] = []
            elif context_key_name == "is_locked":
                _ACTIVE_CONTEXT_CACHE[context_key_name] = False
            else:
                _ACTIVE_CONTEXT_CACHE[context_key_name] = None

        if persist:
            bejson_standards_persist_state(custom_state_file_path)
        return dict(_ACTIVE_CONTEXT_CACHE)


def bejson_standards_resolve_context(
    explicit_subsystem: Optional[str] = None,
    explicit_category: Optional[str] = None,
    explicit_actor: Optional[str] = None,
    explicit_session: Optional[str] = None,
    explicit_event_key: Optional[str] = None,
    explicit_flags: Any = None,
    explicit_priority: Optional[int] = None,
    explicit_target_uuid: Optional[str] = None,
    custom_state_file_path: Optional[str] = None
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], str, List[str], Optional[int], Optional[str]]:
    """
    Resolve parameters against active loaded chamber state.
    Explicit arguments override chamber defaults.
    Omitted arguments inherit active chamber variables.
    """
    active_context: Dict[str, Any] = bejson_standards_get_context(custom_state_file_path)

    # 1. Resolve Subsystem
    resolved_subsystem: Optional[str] = explicit_subsystem or active_context.get("active_subsystem")

    # 2. Resolve Category
    resolved_category: Optional[str] = explicit_category or active_context.get("active_category")

    # 3. Resolve Actor
    resolved_actor: Optional[str] = explicit_actor or active_context.get("active_actor")

    # 4. Resolve Session
    resolved_session: Optional[str] = explicit_session or active_context.get("active_session")

    # 5. Resolve Event Key Prefix
    resolved_event_key: str = explicit_event_key or "system.event"
    active_prefix: Optional[str] = active_context.get("active_key_prefix")
    if active_prefix and not resolved_event_key.startswith(f"{active_prefix}."):
        resolved_event_key = f"{active_prefix}.{resolved_event_key}"

    # 6. Resolve & Merge Flags
    resolved_flags_list: List[str] = []
    if explicit_flags:
        if isinstance(explicit_flags, str):
            resolved_flags_list.extend([f.strip() for f in explicit_flags.split(",") if f.strip()])
        else:
            resolved_flags_list.extend([str(f).strip() for f in explicit_flags if str(f).strip()])

    # Merge in default flags from chamber if not already present
    default_flags: List[str] = active_context.get("active_default_flags") or []
    for default_flag_item in default_flags:
        if default_flag_item not in resolved_flags_list:
            resolved_flags_list.append(default_flag_item)

    # 7. Resolve Priority
    resolved_priority: Optional[int] = explicit_priority if explicit_priority is not None else active_context.get("active_default_priority")

    # 8. Resolve Target UUID
    resolved_target_uuid: Optional[str] = explicit_target_uuid or active_context.get("active_target_uuid")

    return (
        resolved_subsystem,
        resolved_category,
        resolved_actor,
        resolved_session,
        resolved_event_key,
        resolved_flags_list,
        resolved_priority,
        resolved_target_uuid
    )
