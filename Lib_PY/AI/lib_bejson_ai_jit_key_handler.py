"""
Library:         lib_bejson_ai_jit_key_handler.py
Family:          AI
Module Purpose:  Tier 3 Just-In-Time (JIT) Credential Broker delegating rotation to KeyRotator
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 3: Service Callers & Security)
Version:         1.2.0
Release_Version: 300
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   d1e3a562-9c34-4b88-c5eb-4f7a9b3d5004
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from lib_bejson_AI_bejson_errors import AIException, ERR_AI_KEY_MISSING  # noqa: E402
from lib_bejson_ai_env_vault import AIEnvVault  # noqa: E402
from lib_bejson_ai_key_rotator import KeyRotator  # noqa: E402

VERSION = "1.2.0"

PROVIDER_KEY_PREFIXES: Dict[str, List[str]] = {
    "geminirest": ["GEMINI_KEY_", "GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEYS"],
    "geminiinteractions": ["GEMINI_KEY_", "GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEYS"],
}


def mask_key(api_key: str) -> str:
    """Return a redacted representation safe for logs and telemetry."""
    if not api_key:
        return "<empty>"
    if len(api_key) <= 8:
        return "***"
    return f"{api_key[:4]}...{api_key[-4:]}"


def _natural_key_sort(key_metadata_tuple: Tuple[str, str]) -> Tuple[str, int, str]:
    """Sort `GEMINI_KEY_1`, `GEMINI_KEY_2`, ..., `GEMINI_KEY_13` in natural numeric order."""
    candidate_key_name = key_metadata_tuple[0]
    regex_suffix_match = re.search(r"(\d+)$", candidate_key_name)
    if regex_suffix_match:
        return (candidate_key_name[: regex_suffix_match.start()], int(regex_suffix_match.group(1)), candidate_key_name)
    return (candidate_key_name, 0, candidate_key_name)


class JITKeyHandler:
    """
    Silent JIT credential broker:
      1. Fetches candidate secrets from `AIEnvVault` (`secureenv_file.json` / env).
      2. Delegates selection & health tracking to `KeyRotator` (masked-only state).
      3. Delivers the raw key JIT to `BaseAIClient.execute_call()`.
    """

    def __init__(
        self,
        vault: Optional[AIEnvVault] = None,
        rotator: Optional[KeyRotator] = None,
        cooldown_seconds: float = 60.0,
    ) -> None:
        self.vault = vault or AIEnvVault()
        self.rotator = rotator or KeyRotator(cooldown_seconds=cooldown_seconds)
        self._active_key_meta: Dict[str, Tuple[str, str]] = {}

    def resolve_keys(
        self,
        provider: str,
        vault_path: Optional[Path] = None,
        explicit_keys: Optional[List[str]] = None,
        allow_process_env: bool = True,
    ) -> List[Tuple[str, str]]:
        """Collect all configured `(key_name, key_value)` pairs for `provider` in natural order."""
        found: List[Tuple[str, str]] = []
        seen_values = set()

        if explicit_keys:
            for explicit_key_index, explicit_api_key_str in enumerate(explicit_keys, start=1):
                cleaned = explicit_api_key_str.strip() if explicit_api_key_str else ""
                if cleaned and cleaned not in seen_values:
                    seen_values.add(cleaned)
                    found.append((f"EXPLICIT_KEY_{explicit_key_index}", cleaned))

        all_env = self.vault.get_all_secrets(vault_path=vault_path, allow_process_env=allow_process_env)
        prefixes = PROVIDER_KEY_PREFIXES.get(
            provider.lower(),
            [f"{provider.upper()}_KEY_", f"{provider.upper()}_API_KEY"],
        )

        matched_pairs: List[Tuple[str, str]] = []
        for var_name, var_val in all_env.items():
            if not var_val:
                continue
            for prefix in prefixes:
                if (prefix.endswith("_") and var_name.startswith(prefix)) or var_name == prefix:
                    for part in str(var_val).split(","):
                        cleaned = part.strip()
                        if cleaned:
                            matched_pairs.append((var_name, cleaned))
                    break

        matched_pairs.sort(key=_natural_key_sort)
        for matched_key_identifier_name, matched_key_secret_value in matched_pairs:
            if matched_key_secret_value not in seen_values:
                seen_values.add(matched_key_secret_value)
                found.append((matched_key_identifier_name, matched_key_secret_value))
        return found

    def acquire_key(
        self,
        provider: str,
        vault_path: Optional[Path] = None,
        explicit_keys: Optional[List[str]] = None,
        allow_process_env: bool = True,
    ) -> str:
        """Select the next healthy key via `KeyRotator` and return the raw secret JIT."""
        pairs = self.resolve_keys(
            provider,
            vault_path=vault_path,
            explicit_keys=explicit_keys,
            allow_process_env=allow_process_env,
        )
        if not pairs:
            raise AIException(
                ERR_AI_KEY_MISSING,
                f"No API key configured for provider '{provider}'.",
            )
        key_name, raw_key = self.rotator.select_next(provider, pairs, mask_key)
        self._active_key_meta[raw_key] = (provider.lower(), key_name)
        return raw_key

    def record_success(self, api_key: str) -> None:
        meta = self._active_key_meta.get(api_key)
        if meta:
            self.rotator.record_success(meta[0], meta[1])

    def record_error(self, api_key: str) -> None:
        meta = self._active_key_meta.get(api_key)
        if meta:
            self.rotator.record_error(meta[0], meta[1])

    def mark_rate_limited(self, api_key: str, cooldown_override: Optional[float] = None) -> None:
        meta = self._active_key_meta.get(api_key)
        if meta:
            self.rotator.mark_rate_limited(meta[0], meta[1], cooldown_override=cooldown_override)

    def quarantine_key(self, api_key: str) -> None:
        meta = self._active_key_meta.get(api_key)
        if meta:
            self.rotator.quarantine_key(meta[0], meta[1])

    def get_key_stats(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.rotator.get_stats(provider=provider)
