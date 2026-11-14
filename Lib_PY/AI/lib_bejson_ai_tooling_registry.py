"""
Library:         lib_bejson_ai_tooling_registry.py
Family:          AI
Module Purpose:  Tier 2 Configuration Gate & Persistent Registry for AI Tooling Systems
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 2: Model Features & Gates)
Version:         1.0.0
Release_Version: 300
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   e8a2b1c4-5d9f-4371-9c0b-6a4e7f8d1016
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

_CURRENT_MODULE_DIR = Path(__file__).resolve().parent
if str(_CURRENT_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_MODULE_DIR))

from lib_bejson_AI_bejson_errors import (  # noqa: E402
    AIException,
    ERR_AI_TOOLING_SYSTEM_NOT_FOUND,
)
from lib_bejson_ai_tooling_base import BaseToolingSystem  # noqa: E402

VERSION = "1.0.0"

DEFAULT_GLOBAL_CONFIG_FILENAME = "ai_global_config.105a.bejson"

DEFAULT_SETTINGS_INITIAL_VALUES: Dict[str, Any] = {
    "tooling_enabled": False,
    "active_tooling_system": "interactions_tools",
    "default_provider": "geminirest",
    "default_model": "gemini-3.1-flash-lite",
    "max_tool_roundtrips": 5,
    "stdout_routing": False,
    "global_pre_parser_enabled": False,
    "global_post_parser_enabled": False,
    "extension_parser_enabled": False,
}


def _resolve_canonical_config_path(explicit_config_path: Optional[Path] = None) -> Path:
    """Resolve configuration file location honoring Policy §5.3.3 dynamic environment root."""
    if explicit_config_path is not None:
        return Path(explicit_config_path).resolve()
    env_override_path_str = os.environ.get("BEJSON_AI_GLOBAL_CONFIG")
    if env_override_path_str:
        return Path(env_override_path_str).expanduser().resolve()
    return _CURRENT_MODULE_DIR / "config" / DEFAULT_GLOBAL_CONFIG_FILENAME


class AIGlobalConfigManager:
    """
    Manages persistent AI library configuration in BEJSON 105a format.
    Auto-exports canonical defaults on first use if file does not exist,
    and atomically persists setting changes to disk for subsequent sessions.
    """

    def __init__(self, config_target_file_path: Optional[Path] = None) -> None:
        self.config_target_file_path: Path = _resolve_canonical_config_path(config_target_file_path)
        self._cached_configuration_settings_map: Dict[str, Any] = {}
        self.ensure_configuration_loaded()

    def build_default_bejson_105a_document(self) -> Dict[str, Any]:
        """Construct the canonical BEJSON 105a envelope containing default settings."""
        field_definitions_list = [
            {"name": "setting_key", "type": "string", "field_uuid": str(uuid.uuid4())},
            {"name": "setting_value_json", "type": "string", "field_uuid": str(uuid.uuid4())},
            {"name": "setting_type_label", "type": "string", "field_uuid": str(uuid.uuid4())},
        ]
        values_rows_list = []
        for setting_key_identifier, setting_initial_value in DEFAULT_SETTINGS_INITIAL_VALUES.items():
            setting_type_name_token = type(setting_initial_value).__name__
            serialized_setting_value_str = json.dumps(setting_initial_value)
            values_rows_list.append([
                str(uuid.uuid4()),
                setting_key_identifier,
                serialized_setting_value_str,
                setting_type_name_token,
            ])
        return {
            "Format": "BEJSON",
            "Format_Version": "105a",
            "Format_Creator": "Elton Boehnen",
            "Records_Type": ["AIGlobalConfig"],
            "Fields": field_definitions_list,
            "Values": values_rows_list,
        }

    def ensure_configuration_loaded(self, force_reload_flag: bool = False) -> None:
        """Load settings from disk, or auto-export defaults if file is missing."""
        if self._cached_configuration_settings_map and not force_reload_flag:
            return

        if not self.config_target_file_path.exists():
            self.auto_export_default_configuration()
            return

        try:
            raw_file_content_str = self.config_target_file_path.read_text(encoding="utf-8")
            parsed_bejson_document = json.loads(raw_file_content_str)
            table_field_names_list = [
                field_spec_dict.get("name")
                for field_spec_dict in parsed_bejson_document.get("Fields", [])
                if isinstance(field_spec_dict, dict)
            ]
            loaded_settings_map: Dict[str, Any] = {}
            for entity_table_record_row in parsed_bejson_document.get("Values", []):
                if not isinstance(entity_table_record_row, list) or len(entity_table_record_row) < 3:
                    continue
                record_field_mapping = dict(zip(table_field_names_list, entity_table_record_row[1:]))
                setting_key_name = str(record_field_mapping.get("setting_key", ""))
                serialized_raw_value = record_field_mapping.get("setting_value_json", "")
                if setting_key_name:
                    try:
                        loaded_settings_map[setting_key_name] = json.loads(str(serialized_raw_value))
                    except (json.JSONDecodeError, TypeError):
                        loaded_settings_map[setting_key_name] = serialized_raw_value
            self._cached_configuration_settings_map = loaded_settings_map
        except Exception:
            self.auto_export_default_configuration()

    def auto_export_default_configuration(self) -> None:
        """Export default 105a configuration file to disk atomically."""
        self.config_target_file_path.parent.mkdir(parents=True, exist_ok=True)
        default_bejson_document = self.build_default_bejson_105a_document()
        atomic_temporary_file_path = self.config_target_file_path.with_suffix(self.config_target_file_path.suffix + ".tmp")
        atomic_temporary_file_path.write_text(json.dumps(default_bejson_document, indent=2), encoding="utf-8")
        atomic_temporary_file_path.replace(self.config_target_file_path)
        self._cached_configuration_settings_map = dict(DEFAULT_SETTINGS_INITIAL_VALUES)

    def persist_current_configuration_to_disk(self) -> None:
        """Atomically persist active in-memory settings to the BEJSON 105a file."""
        self.config_target_file_path.parent.mkdir(parents=True, exist_ok=True)
        field_definitions_list = [
            {"name": "setting_key", "type": "string", "field_uuid": str(uuid.uuid4())},
            {"name": "setting_value_json", "type": "string", "field_uuid": str(uuid.uuid4())},
            {"name": "setting_type_label", "type": "string", "field_uuid": str(uuid.uuid4())},
        ]
        values_rows_list = []
        for setting_key_identifier, setting_active_value in self._cached_configuration_settings_map.items():
            setting_type_name_token = type(setting_active_value).__name__
            serialized_setting_value_str = json.dumps(setting_active_value)
            values_rows_list.append([
                str(uuid.uuid4()),
                setting_key_identifier,
                serialized_setting_value_str,
                setting_type_name_token,
            ])
        export_document_dict = {
            "Format": "BEJSON",
            "Format_Version": "105a",
            "Format_Creator": "Elton Boehnen",
            "Records_Type": ["AIGlobalConfig"],
            "Fields": field_definitions_list,
            "Values": values_rows_list,
        }
        atomic_temporary_file_path = self.config_target_file_path.with_suffix(self.config_target_file_path.suffix + ".tmp")
        atomic_temporary_file_path.write_text(json.dumps(export_document_dict, indent=2), encoding="utf-8")
        atomic_temporary_file_path.replace(self.config_target_file_path)

    def get_setting(self, setting_name_identifier: str, fallback_default_value: Any = None) -> Any:
        """Retrieve a configuration value."""
        self.ensure_configuration_loaded()
        return self._cached_configuration_settings_map.get(setting_name_identifier, fallback_default_value)

    def update_setting(self, setting_name_identifier: str, new_setting_target_value: Any) -> None:
        """Update a configuration value and atomically persist change to disk."""
        self.ensure_configuration_loaded()
        self._cached_configuration_settings_map[setting_name_identifier] = new_setting_target_value
        self.persist_current_configuration_to_disk()

    def is_tooling_enabled(self) -> bool:
        """Check master boolean tooling gate."""
        return bool(self.get_setting("tooling_enabled", False))

    def set_tooling_enabled(self, target_enabled_flag: bool) -> None:
        """Toggle master tooling gate and persist."""
        self.update_setting("tooling_enabled", bool(target_enabled_flag))

    def get_active_tooling_system_name(self) -> str:
        """Get identifier of selected tooling system."""
        return str(self.get_setting("active_tooling_system", "interactions_tools"))

    def set_active_tooling_system_name(self, target_system_identifier_name: str) -> None:
        """Switch active tooling system identifier and persist."""
        self.update_setting("active_tooling_system", str(target_system_identifier_name).strip())

    def is_global_pre_parser_enabled(self) -> bool:
        """Check persistent global pre-parser gate."""
        return bool(self.get_setting("global_pre_parser_enabled", False))

    def set_global_pre_parser_enabled(self, target_enabled_flag: bool) -> None:
        """Toggle persistent global pre-parser gate."""
        self.update_setting("global_pre_parser_enabled", bool(target_enabled_flag))

    def is_global_post_parser_enabled(self) -> bool:
        """Check persistent global post-parser gate."""
        return bool(self.get_setting("global_post_parser_enabled", False))

    def set_global_post_parser_enabled(self, target_enabled_flag: bool) -> None:
        """Toggle persistent global post-parser gate."""
        self.update_setting("global_post_parser_enabled", bool(target_enabled_flag))

    def is_extension_parser_enabled(self) -> bool:
        """Check persistent custom Python module extension parser gate."""
        return bool(self.get_setting("extension_parser_enabled", False))

    def set_extension_parser_enabled(self, target_enabled_flag: bool) -> None:
        """Toggle persistent custom Python module extension parser gate."""
        self.update_setting("extension_parser_enabled", bool(target_enabled_flag))

    # Name_Case Method Bindings
    Get_Setting = get_setting
    Update_Setting = update_setting
    Is_Tooling_Enabled = is_tooling_enabled
    Set_Tooling_Enabled = set_tooling_enabled
    Get_Active_Tooling_System_Name = get_active_tooling_system_name
    Set_Active_Tooling_System_Name = set_active_tooling_system_name
    Is_Global_Pre_Parser_Enabled = is_global_pre_parser_enabled
    Set_Global_Pre_Parser_Enabled = set_global_pre_parser_enabled
    Is_Global_Post_Parser_Enabled = is_global_post_parser_enabled
    Set_Global_Post_Parser_Enabled = set_global_post_parser_enabled
    Is_Extension_Parser_Enabled = is_extension_parser_enabled
    Set_Extension_Parser_Enabled = set_extension_parser_enabled
    Ensure_Configuration_Loaded = ensure_configuration_loaded
    Auto_Export_Default_Configuration = auto_export_default_configuration
    Persist_Current_Configuration_To_Disk = persist_current_configuration_to_disk



class ToolingRegistry:
    """
    Tier 2 Registry governing tooling/skill systems, configuration gating,
    and multi-turn tool execution orchestration.
    """

    def __init__(self, config_manager_instance: Optional[AIGlobalConfigManager] = None) -> None:
        self.config_manager: AIGlobalConfigManager = config_manager_instance or AIGlobalConfigManager()
        self._registered_tooling_systems_map: Dict[str, BaseToolingSystem] = {}

    def register_tooling_system(self, tooling_subsystem_instance: BaseToolingSystem) -> None:
        """Register a tooling system under its system_name identifier."""
        clean_system_name_key = tooling_subsystem_instance.system_name.lower().strip()
        self._registered_tooling_systems_map[clean_system_name_key] = tooling_subsystem_instance

    def list_tooling_systems(self) -> List[str]:
        """Return list of all registered tooling system names."""
        return sorted(self._registered_tooling_systems_map.keys())

    def is_enabled(self) -> bool:
        """Query persistent master tooling gate."""
        return self.config_manager.is_tooling_enabled()

    def set_enabled(self, target_enabled_state_flag: bool) -> None:
        """Persistently switch master tooling gate."""
        self.config_manager.set_tooling_enabled(target_enabled_state_flag)

    def select_tooling_system(self, target_system_name_str: str) -> None:
        """Persistently switch active tooling system."""
        clean_target_name = target_system_name_str.lower().strip()
        self.config_manager.set_active_tooling_system_name(clean_target_name)

    def get_active_system(self) -> Optional[BaseToolingSystem]:
        """
        Return active tooling system if master gate is enabled.
        Returns None if tooling is disabled.
        Raises AIException if enabled but system is not registered.
        """
        if not self.is_enabled():
            return None

        active_system_name = self.config_manager.get_active_tooling_system_name().lower()
        if active_system_name not in self._registered_tooling_systems_map:
            raise AIException(
                ERR_AI_TOOLING_SYSTEM_NOT_FOUND,
                f"Active tooling system '{active_system_name}' is not registered. Available: {self.list_tooling_systems()}",
            )
        return self._registered_tooling_systems_map[active_system_name]

    # Name_Case Method Aliases
    Register_Tooling_System = register_tooling_system
    List_Tooling_Systems = list_tooling_systems
    Is_Enabled = is_enabled
    Set_Enabled = set_enabled
    Select_Tooling_System = select_tooling_system
    Get_Active_System = get_active_system
    Enable_Tooling = lambda self: self.set_enabled(True)
    Disable_Tooling = lambda self: self.set_enabled(False)


# Canonical Name_Case Aliases
Tooling_Registry = ToolingRegistry
AI_Global_Config_Manager = AIGlobalConfigManager

