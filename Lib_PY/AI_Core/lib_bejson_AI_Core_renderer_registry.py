"""
Library:         lib_bejson_AI_Core_renderer_registry.py
Family:          AI_Core
Module Purpose:  Tier 2 Configuration-Gated Registry & Pipeline Coordinator for Post-Processing Renderers
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 2: Model Features & Gates)
Version:         2.0.0
Release_Version: 300
Date:            2026-11-17
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   0279d979-bc35-4db6-83db-195e1e7f0d16

Changelog:
  2.0.0 (2026-11-17) -- AI family renamed to AI_Core (was lib_bejson_ai_*). BEJSON read/write now via Core bridge where applicable.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_CURRENT_MODULE_DIR = Path(__file__).resolve().parent
if str(_CURRENT_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_MODULE_DIR))

from lib_bejson_AI_Core_errors import (  # noqa: E402
    AIException,
    ERR_AI_RENDERER_FAILED,
    ERR_AI_RENDERER_NOT_FOUND,
)
from lib_bejson_AI_Core_renderer_base import BaseRenderer  # noqa: E402
from lib_bejson_AI_Core_tooling_registry import AIGlobalConfigManager  # noqa: E402

VERSION = "2.0.0"

_LOGGER_INSTANCE = logging.getLogger("lib_bejson_AI_Core_renderer_registry")


class RendererRegistry:
    """
    Tier 2 Registry governing modular post-processing renderers.
    Configuration-gated via persistent global settings (`renderer_enabled`,
    `active_renderer`) in `config/ai_global_config.105a.bejson`.
    Executes after `AIPostprocessor.process()` so renderers consume validated
    `text`, `xml_blocks`, and `structured_data` safely.
    """

    def __init__(
        self,
        config_manager_instance: Optional[AIGlobalConfigManager] = None,
    ) -> None:
        self.config_manager: AIGlobalConfigManager = config_manager_instance or AIGlobalConfigManager()
        self._registered_renderers_map: Dict[str, BaseRenderer] = {}

    def register_renderer(
        self,
        modular_renderer_instance: BaseRenderer,
    ) -> None:
        """Register a modular renderer plugin under its renderer_name identifier."""
        clean_renderer_name_key = modular_renderer_instance.renderer_name.lower().strip()
        self._registered_renderers_map[clean_renderer_name_key] = modular_renderer_instance

    def unregister_renderer(
        self,
        target_renderer_name_identifier: str,
    ) -> None:
        """Remove a modular renderer plugin by name."""
        clean_renderer_name_key = target_renderer_name_identifier.lower().strip()
        self._registered_renderers_map.pop(clean_renderer_name_key, None)

    def list_renderers(self) -> List[str]:
        """Return sorted list of registered modular renderer names."""
        return sorted(self._registered_renderers_map.keys())

    def is_enabled(self) -> bool:
        """Query persistent global post-processing renderer gate."""
        return self.config_manager.is_renderer_enabled()

    def set_enabled(
        self,
        target_enabled_flag: bool,
    ) -> None:
        """Persistently toggle global post-processing renderer gate."""
        self.config_manager.set_renderer_enabled(target_enabled_flag)

    def select_renderer(
        self,
        target_renderer_name_identifier: str,
    ) -> None:
        """Select and persist the active modular renderer by name."""
        clean_renderer_name_key = target_renderer_name_identifier.lower().strip()
        if clean_renderer_name_key not in self._registered_renderers_map:
            raise AIException(
                ERR_AI_RENDERER_NOT_FOUND,
                f"Renderer '{clean_renderer_name_key}' is not registered. Available: {self.list_renderers()}",
            )
        self.config_manager.set_active_renderer_name(clean_renderer_name_key)

    def get_active_renderer(self) -> Optional[BaseRenderer]:
        """Return the active modular renderer if enabled and registered, else None."""
        if not self.is_enabled():
            return None
        active_renderer_key = self.config_manager.get_active_renderer_name().lower().strip()
        return self._registered_renderers_map.get(active_renderer_key)

    def _resolve_target_renderers(self) -> List[tuple[str, BaseRenderer]]:
        """Resolve which registered renderers should execute based on active_renderer."""
        active_renderer_key = self.config_manager.get_active_renderer_name().lower().strip()
        if active_renderer_key in self._registered_renderers_map:
            return [(active_renderer_key, self._registered_renderers_map[active_renderer_key])]
        if active_renderer_key in ("", "default", "all"):
            return list(self._registered_renderers_map.items())
        _LOGGER_INSTANCE.warning(
            "Configured active_renderer '%s' is not registered; skipping render.",
            active_renderer_key,
        )
        return []

    def execute_renderers(
        self,
        cleaned_response_envelope_dict: Dict[str, Any],
        fail_on_error: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute active modular post-processing renderer(s) if `renderer_enabled` is True.
        Preserves core envelope keys ('text', 'structured_data', 'turn_continuation_command')
        and falls back cleanly on plugin failure unless `fail_on_error=True`.
        """
        if not self.is_enabled():
            return cleaned_response_envelope_dict

        target_renderers_list = self._resolve_target_renderers()
        if not target_renderers_list:
            return cleaned_response_envelope_dict

        accumulated_response_envelope = dict(cleaned_response_envelope_dict)
        for single_renderer_identifier_name, single_renderer_plugin_instance in target_renderers_list:
            try:
                rendered_envelope_candidate = single_renderer_plugin_instance.render(
                    dict(accumulated_response_envelope)
                )
                if isinstance(rendered_envelope_candidate, dict):
                    accumulated_response_envelope = rendered_envelope_candidate
                    if "rendered_format" not in accumulated_response_envelope:
                        accumulated_response_envelope["rendered_format"] = str(
                            getattr(single_renderer_plugin_instance, "output_format", "text")
                        )
                    if "rendered_by" not in accumulated_response_envelope:
                        accumulated_response_envelope["rendered_by"] = single_renderer_identifier_name
            except Exception as renderer_execution_exception:
                _LOGGER_INSTANCE.warning(
                    "Modular renderer '%s' failed: %s",
                    single_renderer_identifier_name,
                    renderer_execution_exception,
                )
                if fail_on_error:
                    raise AIException(
                        ERR_AI_RENDERER_FAILED,
                        f"Renderer '{single_renderer_identifier_name}' failed: {renderer_execution_exception}",
                    ) from renderer_execution_exception

        return accumulated_response_envelope

    # Name_Case Method Bindings
    Register_Renderer = register_renderer
    Unregister_Renderer = unregister_renderer
    List_Renderers = list_renderers
    Is_Enabled = is_enabled
    Set_Enabled = set_enabled
    Select_Renderer = select_renderer
    Get_Active_Renderer = get_active_renderer
    Execute_Renderers = execute_renderers


# Canonical Name_Case Alias
Renderer_Registry = RendererRegistry
