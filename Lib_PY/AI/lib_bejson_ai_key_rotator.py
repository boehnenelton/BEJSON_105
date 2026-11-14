"""
Library:         lib_bejson_ai_key_rotator.py
Family:          AI
Module Purpose:  Tier 3 Key Rotation, Cooldown, Quarantine & BEJSON 105a State Tracker
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 3: Service Callers & Security)
Version:         1.0.0
Release_Version: 300
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   a3b9c512-1f4e-4b78-9d2a-8c6e0f3a4100
"""
from __future__ import annotations

import json
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from lib_bejson_AI_bejson_errors import AIException, ERR_AI_KEY_EXHAUSTED  # noqa: E402

VERSION = "1.0.0"


@dataclass
class KeyHealthRecord:
    provider: str
    key_name: str
    masked_key: str
    uses: int = 0
    successes: int = 0
    rate_limits: int = 0
    errors: int = 0
    quarantined: bool = False
    last_used_epoch: Optional[float] = None
    cooldown_until_epoch: float = 0.0


class KeyRotator:
    """
    Stateful round-robin key rotation & health tracker.
    Tracks only `(provider, key_name, masked_key)` and telemetry — never raw secrets.
    Optionally persists rotation state as a BEJSON 105a document.
    """

    def __init__(
        self,
        cooldown_seconds: float = 60.0,
        state_path: Optional[Path] = None,
    ) -> None:
        self.cooldown_seconds = cooldown_seconds
        self.state_path = Path(state_path).resolve() if state_path else None
        self._lock = threading.Lock()
        self._cursors: Dict[str, int] = {}
        self._records: Dict[Tuple[str, str], KeyHealthRecord] = {}
        if self.state_path and self.state_path.is_file():
            self._load_state(self.state_path)

    def select_next(
        self,
        provider: str,
        candidates: List[Tuple[str, str]],
        mask_fn: Any,
    ) -> Tuple[str, str]:
        """
        Select the next healthy, non-cooled-down, non-quarantined `(key_name, raw_value)`
        from `candidates` using round-robin cursor advancement.
        """
        prov = provider.lower()
        now_epoch = time.time()
        with self._lock:
            start_idx = self._cursors.get(prov, 0) % len(candidates)
            for offset in range(len(candidates)):
                idx = (start_idx + offset) % len(candidates)
                key_name, raw_val = candidates[idx]
                key_health_record = self._records.setdefault(
                    (prov, key_name),
                    KeyHealthRecord(
                        provider=prov,
                        key_name=key_name,
                        masked_key=mask_fn(raw_val),
                    ),
                )
                if key_health_record.quarantined:
                    continue
                if now_epoch >= key_health_record.cooldown_until_epoch:
                    self._cursors[prov] = (idx + 1) % len(candidates)
                    key_health_record.uses += 1
                    key_health_record.last_used_epoch = now_epoch
                    self._maybe_save_state()
                    return key_name, raw_val

        raise AIException(
            ERR_AI_KEY_EXHAUSTED,
            f"All {len(candidates)} key(s) for provider '{provider}' are in cooldown or quarantined.",
        )

    def record_success(self, provider: str, key_name: str) -> None:
        with self._lock:
            key_health_record = self._records.get((provider.lower(), key_name))
            if key_health_record is not None:
                key_health_record.successes += 1
                self._maybe_save_state()

    def record_error(self, provider: str, key_name: str) -> None:
        with self._lock:
            key_health_record = self._records.get((provider.lower(), key_name))
            if key_health_record is not None:
                key_health_record.errors += 1
                self._maybe_save_state()

    def mark_rate_limited(
        self,
        provider: str,
        key_name: str,
        cooldown_override: Optional[float] = None,
    ) -> None:
        duration = cooldown_override if cooldown_override is not None else self.cooldown_seconds
        with self._lock:
            key_health_record = self._records.get((provider.lower(), key_name))
            if key_health_record is not None:
                key_health_record.rate_limits += 1
                key_health_record.cooldown_until_epoch = time.time() + duration
                self._maybe_save_state()

    def quarantine_key(self, provider: str, key_name: str) -> None:
        """Permanently skip a key for this session/state after HTTP 401/403 auth failure."""
        with self._lock:
            key_health_record = self._records.get((provider.lower(), key_name))
            if key_health_record is not None:
                key_health_record.errors += 1
                key_health_record.quarantined = True
                self._maybe_save_state()

    def get_stats(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        now_epoch = time.time()
        with self._lock:
            items = []
            for key_health_record in self._records.values():
                if provider and key_health_record.provider != provider.lower():
                    continue
                items.append(
                    {
                        "provider": key_health_record.provider,
                        "key_name": key_health_record.key_name,
                        "masked_key": key_health_record.masked_key,
                        "uses": key_health_record.uses,
                        "successes": key_health_record.successes,
                        "rate_limits": key_health_record.rate_limits,
                        "errors": key_health_record.errors,
                        "quarantined": key_health_record.quarantined,
                        "last_used_epoch": key_health_record.last_used_epoch,
                        "in_cooldown": now_epoch < key_health_record.cooldown_until_epoch,
                    }
                )
            return items

    def export_bejson_105a_state(self) -> Dict[str, Any]:
        """Export masked rotation telemetry as a Format 105a BEJSON document."""
        fields = [
            {"name": "provider", "type": "string", "field_uuid": str(uuid.uuid4())},
            {"name": "key_name", "type": "string", "field_uuid": str(uuid.uuid4())},
            {"name": "masked_key", "type": "string", "field_uuid": str(uuid.uuid4())},
            {"name": "uses", "type": "integer", "field_uuid": str(uuid.uuid4())},
            {"name": "successes", "type": "integer", "field_uuid": str(uuid.uuid4())},
            {"name": "rate_limits", "type": "integer", "field_uuid": str(uuid.uuid4())},
            {"name": "errors", "type": "integer", "field_uuid": str(uuid.uuid4())},
            {"name": "quarantined", "type": "boolean", "field_uuid": str(uuid.uuid4())},
            {"name": "cooldown_until_epoch", "type": "number", "field_uuid": str(uuid.uuid4())},
        ]
        values = []
        for key_health_record in self._records.values():
            values.append(
                [
                    str(uuid.uuid4()),
                    key_health_record.provider,
                    key_health_record.key_name,
                    key_health_record.masked_key,
                    key_health_record.uses,
                    key_health_record.successes,
                    key_health_record.rate_limits,
                    key_health_record.errors,
                    key_health_record.quarantined,
                    key_health_record.cooldown_until_epoch,
                ]
            )
        return {
            "Format": "BEJSON",
            "Format_Version": "105a",
            "Schema_Name": "AIKeyRotationState",
            "Fields": fields,
            "Values": values,
        }

    def _maybe_save_state(self) -> None:
        if self.state_path is None:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        state_file_temporary_path = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        state_file_temporary_path.write_text(json.dumps(self.export_bejson_105a_state(), indent=2), encoding="utf-8")
        state_file_temporary_path.replace(self.state_path)

    def _load_state(self, path: Path) -> None:
        try:
            serialized_state_document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        bejson_state_field_names_list = [
            field_spec_dict.get("name")
            for field_spec_dict in serialized_state_document.get("Fields", [])
            if isinstance(field_spec_dict, dict)
        ]
        for state_table_record_row in serialized_state_document.get("Values", []):
            if not isinstance(state_table_record_row, list) or len(state_table_record_row) != len(bejson_state_field_names_list) + 1:
                continue
            state_row_field_map = dict(zip(bejson_state_field_names_list, state_table_record_row[1:]))
            target_provider_name = str(state_row_field_map.get("provider", ""))
            target_key_identifier_name = str(state_row_field_map.get("key_name", ""))
            if not target_provider_name or not target_key_identifier_name:
                continue
            self._records[(target_provider_name, target_key_identifier_name)] = KeyHealthRecord(
                provider=target_provider_name,
                key_name=target_key_identifier_name,
                masked_key=str(state_row_field_map.get("masked_key", "***")),
                uses=int(state_row_field_map.get("uses", 0)),
                successes=int(state_row_field_map.get("successes", 0)),
                rate_limits=int(state_row_field_map.get("rate_limits", 0)),
                errors=int(state_row_field_map.get("errors", 0)),
                quarantined=bool(state_row_field_map.get("quarantined", False)),
                cooldown_until_epoch=float(state_row_field_map.get("cooldown_until_epoch", 0.0)),
            )
