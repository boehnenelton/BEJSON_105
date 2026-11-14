"""
Library:         lib_bejson_ai_env_vault.py
Family:          AI
Module Purpose:  Tier 3 Configurable Path & Vault Resolver (definitions.json/.py + secureenv_file.json)
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 3: Service Callers & Security)
Version:         1.1.0
Release_Version: 300
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   c9d2f451-7b23-4e77-b4da-3e6f8a2c4003
"""
from __future__ import annotations

import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from lib_bejson_AI_bejson_errors import (  # noqa: E402
    AIException,
    ERR_AI_VAULT_NOT_FOUND,
    ERR_AI_VAULT_PARSE_FAILED,
)

VERSION = "1.1.0"

_ENV_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")

# Policy §5.3.3: no absolute path may be hardcoded anywhere except paths.json / secureenv_file.json
# themselves. These three are resolved dynamically from the environment (never a literal), mirroring
# Core's own resolve_path() pattern (HOME fallback, no baked-in storage root).
def _canonical_env_root() -> Path:
    override = os.environ.get("BEJSON_ENV_ROOT")
    if override:
        return Path(override).expanduser()
    storage_root = os.environ.get("BEJSON_STORAGE_ROOT") or os.environ.get("HOME") or str(Path.home())
    return Path(storage_root) / ".env"


def _canonical_definitions_json() -> Path:
    return _canonical_env_root() / "user" / "definitions.json"


def _canonical_definitions_py() -> Path:
    return _canonical_env_root() / "user" / "definitions.py"


def _canonical_secureenv_json() -> Path:
    return _canonical_env_root() / "secure" / "secureenv_file.json"


def _extract_bejson_104a_env(parsed_bejson_manifest_document: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract `{var_name: var_value}` from BEJSON 104a/105a tabular stores
    such as `definitions.json` (UserPaths) and `secureenv_file.json` (GlobalEnv).
    """
    bejson_table_field_names_list = [
        field_spec_dict.get("name") if isinstance(field_spec_dict, dict) else str(field_spec_dict)
        for field_spec_dict in parsed_bejson_manifest_document.get("Fields", [])
    ]
    extracted_environment_variables_map: Dict[str, Any] = {}
    for entity_table_record_row in parsed_bejson_manifest_document.get("Values", []):
        if not isinstance(entity_table_record_row, list):
            continue
        entity_record_field_map = dict(zip(bejson_table_field_names_list, entity_table_record_row))
        environment_variable_key_name = (
            entity_record_field_map.get("var_name")
            or entity_record_field_map.get("key_name")
            or entity_record_field_map.get("name")
            or entity_record_field_map.get("env_var")
        )
        environment_variable_secret_value = (
            entity_record_field_map.get("var_value")
            if "var_value" in entity_record_field_map
            else entity_record_field_map.get("key_value", entity_record_field_map.get("value", entity_record_field_map.get("secret")))
        )
        if environment_variable_key_name and environment_variable_secret_value is not None and environment_variable_secret_value != "":
            extracted_environment_variables_map[str(environment_variable_key_name)] = environment_variable_secret_value
    return extracted_environment_variables_map


def _safe_parse_python_definitions(raw_python_source_str: str, path: Path) -> Dict[str, Any]:
    """
    Safely parse a `definitions.py` file containing `UPPER_SNAKE = <literal>`
    assignments via `ast.parse` + `ast.literal_eval` (zero `exec()`).
    """
    try:
        parsed_python_syntax_tree = ast.parse(raw_python_source_str, filename=str(path))
    except SyntaxError as exc:
        raise AIException(ERR_AI_VAULT_PARSE_FAILED, f"Syntax error in {path}: {exc}") from exc

    parsed_definitions_map: Dict[str, Any] = {}
    for ast_statement_node in parsed_python_syntax_tree.body:
        if isinstance(ast_statement_node, ast.Assign) and len(ast_statement_node.targets) == 1 and isinstance(ast_statement_node.targets[0], ast.Name):
            definition_variable_identifier = ast_statement_node.targets[0].id
            if not _ENV_KEY_RE.match(definition_variable_identifier):
                continue
            try:
                parsed_definitions_map[definition_variable_identifier] = ast.literal_eval(ast_statement_node.value)
            except (ValueError, TypeError) as exc:
                raise AIException(
                    ERR_AI_VAULT_PARSE_FAILED,
                    f"Non-literal value for '{definition_variable_identifier}' in {path}: {exc}",
                ) from exc
    return parsed_definitions_map


def _safe_parse_env_file(path: Path) -> Dict[str, Any]:
    """
    Safely parse `.json`, `.bejson`, `.py`, or `.env` files as pure data.
    """
    try:
        raw_file_content_str = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AIException(ERR_AI_VAULT_NOT_FOUND, f"Cannot read vault {path}: {exc}") from exc

    suffix = path.suffix.lower()
    if suffix == ".json" or path.name.endswith(".bejson"):
        try:
            vault_json_payload = json.loads(raw_file_content_str)
        except json.JSONDecodeError as exc:
            raise AIException(ERR_AI_VAULT_PARSE_FAILED, f"Invalid JSON in {path}: {exc}") from exc
        if isinstance(vault_json_payload, dict):
            if "Fields" in vault_json_payload and "Values" in vault_json_payload and isinstance(vault_json_payload["Values"], list):
                return _extract_bejson_104a_env(vault_json_payload)
            return {str(payload_entry_key): payload_entry_value for payload_entry_key, payload_entry_value in vault_json_payload.items()}
        raise AIException(ERR_AI_VAULT_PARSE_FAILED, f"Unsupported JSON root in {path}")

    if suffix == ".py":
        return _safe_parse_python_definitions(raw_file_content_str, path)

    parsed_env_file_entries_map: Dict[str, Any] = {}
    for line_number_index, line_content_str in enumerate(raw_file_content_str.splitlines(), start=1):
        stripped_line_str = line_content_str.strip()
        if not stripped_line_str or stripped_line_str.startswith("#"):
            continue
        if "=" not in stripped_line_str:
            raise AIException(ERR_AI_VAULT_PARSE_FAILED, f"Malformed line {line_number_index} in {path}: missing '='")
        parsed_line_key_token, parsed_line_value_token = stripped_line_str.split("=", 1)
        environment_variable_key_identifier = parsed_line_key_token.strip()
        if environment_variable_key_identifier.startswith("export "):
            environment_variable_key_identifier = environment_variable_key_identifier[len("export "):].strip()
        if not _ENV_KEY_RE.match(environment_variable_key_identifier):
            raise AIException(ERR_AI_VAULT_PARSE_FAILED, f"Invalid env identifier '{environment_variable_key_identifier}' at line {line_number_index} in {path}")
        raw_value_token_str = parsed_line_value_token.strip()
        if (raw_value_token_str.startswith('"') and raw_value_token_str.endswith('"')) or (raw_value_token_str.startswith("'") and raw_value_token_str.endswith("'")):
            try:
                parsed_env_file_entries_map[environment_variable_key_identifier] = ast.literal_eval(raw_value_token_str)
            except (SyntaxError, ValueError):
                parsed_env_file_entries_map[environment_variable_key_identifier] = raw_value_token_str[1:-1]
        else:
            parsed_env_file_entries_map[environment_variable_key_identifier] = raw_value_token_str
    return parsed_env_file_entries_map


class AIEnvVault:
    """
    Resolves configurable `definitions` (non-sensitive paths) and `secureenv_file`
    (API secrets) with $SCRIPT_PATH-relative and canonical Android/Termux fallbacks.
    """

    def __init__(
        self,
        script_path: Optional[Path] = None,
        definitions_path: Optional[Path] = None,
        secureenv_path: Optional[Path] = None,
    ) -> None:
        self.script_path: Path = Path(script_path).resolve() if script_path else _HERE
        self.definitions_path: Optional[Path] = Path(definitions_path).resolve() if definitions_path else None
        self.secureenv_path: Optional[Path] = Path(secureenv_path).resolve() if secureenv_path else None
        self._definitions_cache: Dict[str, Any] = {}
        self._secrets_cache: Dict[str, Any] = {}
        self._loaded_sources: List[str] = []

    def get_definitions_search_paths(self) -> List[Path]:
        """Exact ordered list of paths searched for `definitions.json` / `definitions.py`."""
        candidates: List[Path] = []
        if self.definitions_path is not None:
            candidates.append(self.definitions_path)
        env_override = os.environ.get("BEJSON_DEFINITIONS_FILE")
        if env_override:
            candidates.append(Path(env_override).expanduser().resolve())
        candidates.extend([
            self.script_path / "config" / "definitions.json",
            self.script_path / "config" / "definitions.py",
            self.script_path.parent / "config" / "definitions.json",
            _canonical_definitions_json(),
            _canonical_definitions_py(),
            Path("/storage/emulated/0/.env/user/definitions.json"),
            Path("/storage/emulated/0/.env/user/definitions.py"),
        ])
        return candidates

    def get_secureenv_search_paths(self) -> List[Path]:
        """Exact ordered list of paths searched for `secureenv_file.json`."""
        candidates: List[Path] = []
        if self.secureenv_path is not None:
            candidates.append(self.secureenv_path)
        env_override = os.environ.get("BEJSON_SECUREENV_FILE")
        if env_override:
            candidates.append(Path(env_override).expanduser().resolve())
        if "SECUREENV_FILE" in self._definitions_cache and self._definitions_cache["SECUREENV_FILE"]:
            candidates.append(Path(str(self._definitions_cache["SECUREENV_FILE"])).expanduser())
        candidates.extend([
            self.script_path / "config" / "secureenv_file.json",
            self.script_path.parent / "config" / "secureenv_file.json",
            self.script_path / ".env",
            _canonical_secureenv_json(),
            Path("/storage/emulated/0/.env/secure/secureenv_file.json"),
        ])
        return candidates

    def load_vault(
        self,
        vault_path: Optional[Path] = None,
        definitions_path: Optional[Path] = None,
        secureenv_path: Optional[Path] = None,
        force_reload: bool = False,
    ) -> Dict[str, Any]:
        """
        Load definitions first (to resolve `SECUREENV_FILE` if configured),
        then load secure credentials from `secureenv_file.json` or explicit `vault_path`.
        """
        if definitions_path is not None:
            self.definitions_path = Path(definitions_path).resolve()
            force_reload = True
        if secureenv_path is not None:
            self.secureenv_path = Path(secureenv_path).resolve()
            force_reload = True

        if (self._definitions_cache or self._secrets_cache) and not force_reload and vault_path is None:
            merged = dict(self._definitions_cache)
            merged.update(self._secrets_cache)
            return merged

        self._loaded_sources = []
        if force_reload:
            self._definitions_cache.clear()
            self._secrets_cache.clear()

        if vault_path is not None:
            target = Path(vault_path).resolve()
            if not target.exists():
                raise AIException(ERR_AI_VAULT_NOT_FOUND, f"Vault file does not exist: {target}")
            self._secrets_cache.update(_safe_parse_env_file(target))
            self._loaded_sources.append(str(target))
            return dict(self._secrets_cache)

        # Step 1: Load definitions (non-sensitive paths, including SECUREENV_FILE pointer)
        for candidate in self.get_definitions_search_paths():
            if candidate.is_file():
                self._definitions_cache.update(_safe_parse_env_file(candidate))
                self._loaded_sources.append(str(candidate))
                break

        # Step 2: Load secureenv_file (API keys & secrets)
        for candidate in self.get_secureenv_search_paths():
            if candidate.is_file():
                self._secrets_cache.update(_safe_parse_env_file(candidate))
                self._loaded_sources.append(str(candidate))
                break

        merged = dict(self._definitions_cache)
        merged.update(self._secrets_cache)
        return merged

    def get_all_secrets(
        self,
        vault_path: Optional[Path] = None,
        allow_process_env: bool = True,
    ) -> Dict[str, Any]:
        """Return merged dictionary of loaded vault values and optional process env."""
        merged_environment_secrets_dictionary = self.load_vault(vault_path=vault_path)
        if allow_process_env:
            for env_variable_name_token, env_variable_value_token in os.environ.items():
                if env_variable_name_token not in merged_environment_secrets_dictionary and env_variable_value_token:
                    merged_environment_secrets_dictionary[env_variable_name_token] = env_variable_value_token
        return merged_environment_secrets_dictionary

    def get_path(self, name: str) -> Optional[str]:
        """Retrieve a path/definition variable from loaded definitions."""
        if not self._definitions_cache:
            self.load_vault()
        definition_property_value = self._definitions_cache.get(name)
        return str(definition_property_value) if definition_property_value else None

    def get_secret(
        self,
        key: str,
        vault_path: Optional[Path] = None,
        allow_process_env: bool = True,
    ) -> Optional[str]:
        """Retrieve a secret value from vault or (optionally) process environment."""
        if not self._secrets_cache or vault_path is not None:
            self.load_vault(vault_path=vault_path)
        if key in self._secrets_cache and self._secrets_cache[key]:
            return str(self._secrets_cache[key])
        if allow_process_env:
            environment_process_variable_value = os.environ.get(key)
            if environment_process_variable_value:
                return environment_process_variable_value
        return None
