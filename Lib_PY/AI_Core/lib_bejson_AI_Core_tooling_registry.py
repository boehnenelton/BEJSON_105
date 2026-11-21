"""
Library:         lib_bejson_AI_Core_tooling_registry.py
Family:          AI_Core
Module Purpose:  Tier 2 Configuration Gate & Persistent Registry for AI Tooling Systems
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 2: Model Features & Gates)
Version:         2.0.1
Release_Version: 300
Date:            2026-11-19
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   f57d0081-a456-425d-ad2c-a60309c52d5e

Changelog:
  2.0.1 (2026-11-19) -- Single default-model constant DEFAULT_TEXT_MODEL_ID (gemini-3.8-flash, registry-verified); merged newest Nov-18 agent-side changes.
  2.0.0 (2026-11-17) -- AI family renamed to AI_Core (was lib_bejson_ai_*). BEJSON read/write now via Core bridge where applicable.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_CURRENT_MODULE_DIR = Path(__file__).resolve().parent
if str(_CURRENT_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_MODULE_DIR))

from lib_bejson_AI_Core_errors import (  # noqa: E402
    AIException,
    ERR_AI_TOOLING_SYSTEM_NOT_FOUND,
)
from lib_bejson_AI_Core_core_bridge import (  # noqa: E402
    core_add_record,
    core_load,
    core_lock,
    core_new_document,
    core_quarantine,
    core_rows_as_dicts,
    core_save,
)
from lib_bejson_AI_Core_tooling_base import BaseToolingSystem  # noqa: E402
from lib_bejson_AI_Core_features_common import DEFAULT_TEXT_MODEL_ID  # noqa: E402

_LOGGER_INSTANCE = logging.getLogger("lib_bejson_AI_Core_tooling_registry")

VERSION = "2.0.1"

DEFAULT_GLOBAL_CONFIG_FILENAME = "ai_global_config.105a.bejson"

DEFAULT_SETTINGS_INITIAL_VALUES: Dict[str, Any] = {
    "tooling_enabled": False,
    "active_tooling_system": "interactions_tools",
    "default_provider": "geminirest",
    "default_model": DEFAULT_TEXT_MODEL_ID,
    "max_tool_roundtrips": 5,
    "stdout_routing": False,
    "global_pre_parser_enabled": False,
    "global_post_parser_enabled": False,
    "extension_parser_enabled": False,
    "renderer_enabled": False,
    "active_renderer": "default",
    "plugins_enabled": False,
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

    _CONFIG_FIELDS = (("setting_key", "string"), ("setting_value_json", "string"), ("setting_type_label", "string"))

    def _build_document(self, settings_map: Dict[str, Any]) -> Dict[str, Any]:
        """Build the 105a config document through Core (field_uuids and record_uuids stamped by Core)."""
        config_document = core_new_document("105a", "AIGlobalConfig", self._CONFIG_FIELDS)
        for setting_key_identifier, setting_value in settings_map.items():
            core_add_record(config_document, {
                "setting_key": setting_key_identifier,
                "setting_value_json": json.dumps(setting_value),
                "setting_type_label": type(setting_value).__name__,
            })
        return config_document

    def build_default_bejson_105a_document(self) -> Dict[str, Any]:
        """Construct the canonical BEJSON 105a document containing default settings."""
        return self._build_document(DEFAULT_SETTINGS_INITIAL_VALUES)

    def ensure_configuration_loaded(self, force_reload_flag: bool = False) -> None:
        """Load settings from disk (via Core), or auto-export defaults if the file is missing."""
        if self._cached_configuration_settings_map and not force_reload_flag:
            return
        if not self.config_target_file_path.exists():
            self.auto_export_default_configuration()
            return
        try:
            parsed_bejson_document = core_load(self.config_target_file_path)
            loaded_settings_map: Dict[str, Any] = {}
            for config_row in core_rows_as_dicts(parsed_bejson_document):
                setting_key_name = str(config_row.get("setting_key") or "")
                serialized_raw_value = config_row.get("setting_value_json", "")
                if setting_key_name:
                    try:
                        loaded_settings_map[setting_key_name] = json.loads(str(serialized_raw_value))
                    except (json.JSONDecodeError, TypeError):
                        loaded_settings_map[setting_key_name] = serialized_raw_value
            self._cached_configuration_settings_map = loaded_settings_map
        except Exception as config_load_exception:
            core_quarantine(self.config_target_file_path, config_load_exception)
            self.auto_export_default_configuration()

    def auto_export_default_configuration(self) -> None:
        """Export default 105a configuration file to disk atomically (Core write)."""
        core_save(self.config_target_file_path, self.build_default_bejson_105a_document())
        self._cached_configuration_settings_map = dict(DEFAULT_SETTINGS_INITIAL_VALUES)

    def persist_current_configuration_to_disk(self) -> None:
        """Atomically persist active in-memory settings to the BEJSON 105a file (Core write, under Core lock)."""
        with core_lock(self.config_target_file_path):
            core_save(self.config_target_file_path, self._build_document(self._cached_configuration_settings_map))

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

    def is_plugins_enabled(self) -> bool:
        """Check persistent plugin registry gate."""
        return bool(self.get_setting("plugins_enabled", False))

    def set_plugins_enabled(self, target_enabled_flag: bool) -> None:
        """Toggle persistent plugin registry gate."""
        self.update_setting("plugins_enabled", bool(target_enabled_flag))

    def is_renderer_enabled(self) -> bool:
        """Check persistent modular post-processing renderer gate."""
        return bool(self.get_setting("renderer_enabled", False))

    def set_renderer_enabled(self, target_enabled_flag: bool) -> None:
        """Toggle persistent modular post-processing renderer gate."""
        self.update_setting("renderer_enabled", bool(target_enabled_flag))

    def get_active_renderer_name(self) -> str:
        """Get identifier of selected modular renderer."""
        return str(self.get_setting("active_renderer", "default"))

    def set_active_renderer_name(self, target_renderer_identifier_name: str) -> None:
        """Switch active modular renderer identifier and persist."""
        self.update_setting("active_renderer", str(target_renderer_identifier_name).strip())

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
    Is_Renderer_Enabled = is_renderer_enabled
    Set_Renderer_Enabled = set_renderer_enabled
    Get_Active_Renderer_Name = get_active_renderer_name
    Set_Active_Renderer_Name = set_active_renderer_name
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

