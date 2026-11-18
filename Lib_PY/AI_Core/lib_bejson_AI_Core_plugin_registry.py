"""
Library:         lib_bejson_AI_Core_plugin_registry.py
Family:          AI_Core
Module Purpose:  Plug-and-play registry for AI_Extensions modules. Discovers extension.105a.bejson
                 manifests, validates them, loads the declared module (optionally SHA-256 pinned),
                 and runs plugins per stage (pre / post / render) in priority order. Gated by the
                 persistent `plugins_enabled` setting; a failing plugin is logged and skipped.
Architecture:    Tier 2 registry beside ToolingRegistry / ParserRegistry / RendererRegistry.
Version:         2.0.0
Release_Version: 300
Date:            2026-11-17
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   e27b5d08-6f19-4c3a-8a94-d1c0b7e35f62
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from lib_bejson_AI_Core_core_bridge import core_load, core_rows_as_dicts
from lib_bejson_AI_Core_errors import (
    AIException,
    ERR_AI_DOCUMENT_INVALID,
    ERR_AI_PLUGIN_DUPLICATE,
    ERR_AI_PLUGIN_LOAD_FAILED,
    ERR_AI_PLUGIN_MANIFEST_INVALID,
    ERR_AI_PLUGIN_NOT_FOUND,
    ERR_AI_PLUGIN_STAGE_INVALID,
    ERR_AI_PLUGIN_UNTRUSTED_DIRECTORY,
)
from lib_bejson_AI_Core_plugin_base import BasePlugin
from lib_bejson_AI_Core_plugin_schema import (
    PLUGIN_MANIFEST_FILENAME,
    PLUGIN_STAGES,
    plugin_manifest_validate,
)
from lib_bejson_AI_Core_tooling_registry import AIGlobalConfigManager

VERSION = "2.0.0"
_LOGGER = logging.getLogger("lib_bejson_AI_Core_plugin_registry")
_HERE = Path(__file__).resolve().parent


def default_extensions_directory() -> Path:
    """Trusted plugin root: $BEJSON_AI_EXTENSIONS_DIR, else the sibling AI_Extensions family."""
    override = os.environ.get("BEJSON_AI_EXTENSIONS_DIR")
    return Path(override).expanduser().resolve() if override else (_HERE.parent / "AI_Extensions").resolve()


class PluginRegistry:
    def __init__(self, config_manager_instance: Optional[AIGlobalConfigManager] = None) -> None:
        self.config_manager = config_manager_instance or AIGlobalConfigManager()
        self._plugins: Dict[str, BasePlugin] = {}
        self._meta: Dict[str, Dict[str, Any]] = {}
        self._enabled: Dict[str, bool] = {}

    # -- gate ----------------------------------------------------------------
    def is_enabled(self) -> bool:
        return self.config_manager.is_plugins_enabled()

    def set_enabled(self, flag: bool) -> None:
        self.config_manager.set_plugins_enabled(flag)

    # -- registration --------------------------------------------------------
    def register_plugin(self, plugin: BasePlugin, *, priority: int = 100, enabled: bool = True,
                        meta: Optional[Dict[str, Any]] = None) -> None:
        if plugin.stage not in PLUGIN_STAGES:
            raise AIException(ERR_AI_PLUGIN_STAGE_INVALID, f"{plugin.plugin_id!r}: {plugin.stage!r}")
        if not plugin.plugin_id:
            raise AIException(ERR_AI_PLUGIN_MANIFEST_INVALID, "plugin_id is empty")
        if plugin.plugin_id in self._plugins:
            raise AIException(ERR_AI_PLUGIN_DUPLICATE, plugin.plugin_id)
        self._plugins[plugin.plugin_id] = plugin
        self._meta[plugin.plugin_id] = {"priority": priority, **(meta or {})}
        self._enabled[plugin.plugin_id] = enabled

    def unregister_plugin(self, plugin_id: str) -> None:
        if plugin_id not in self._plugins:
            raise AIException(ERR_AI_PLUGIN_NOT_FOUND, plugin_id)
        for table in (self._plugins, self._meta, self._enabled):
            del table[plugin_id]

    def set_plugin_enabled(self, plugin_id: str, flag: bool) -> None:
        if plugin_id not in self._plugins:
            raise AIException(ERR_AI_PLUGIN_NOT_FOUND, plugin_id)
        self._enabled[plugin_id] = bool(flag)

    def list_plugins(self, stage: Optional[str] = None) -> List[str]:
        """Plugin ids in execution order (priority, then id)."""
        ids = [i for i, p in self._plugins.items() if stage is None or p.stage == stage]
        return sorted(ids, key=lambda i: (self._meta[i]["priority"], i))

    # -- discovery -----------------------------------------------------------
    def discover_plugins(self, directory: Optional[Path] = None, allow_external_directory: bool = False) -> List[str]:
        """
        Scan `directory` (default: the trusted AI_Extensions family) one level deep for
        extension.105a.bejson manifests and register each valid plugin. Importing runs plugin
        code, so directories outside the trusted root need allow_external_directory=True.
        Invalid plugins are logged and skipped; returns the ids registered.
        """
        trusted = default_extensions_directory()
        target = Path(directory).resolve() if directory else trusted
        if target != trusted and not allow_external_directory:
            raise AIException(ERR_AI_PLUGIN_UNTRUSTED_DIRECTORY, str(target))
        registered: List[str] = []
        manifests = sorted(target.glob(PLUGIN_MANIFEST_FILENAME)) + sorted(target.glob(f"*/{PLUGIN_MANIFEST_FILENAME}"))
        for manifest_path in manifests:
            try:
                registered.append(self._load_one(manifest_path))
            except AIException as exc:
                _LOGGER.warning("Skipping plugin at %s: %s", manifest_path.parent, exc)
        return registered

    def _load_one(self, manifest_path: Path) -> str:
        document = core_load(manifest_path)
        problems = plugin_manifest_validate(document)
        if problems:
            raise AIException(ERR_AI_PLUGIN_MANIFEST_INVALID, "; ".join(problems))
        row = core_rows_as_dicts(document)[0]
        module_path = (manifest_path.parent / row["module_file"]).resolve()
        if module_path.parent != manifest_path.parent.resolve() or not module_path.is_file():
            raise AIException(ERR_AI_PLUGIN_LOAD_FAILED, f"module_file not beside manifest: {row['module_file']}")
        if row.get("module_sha256"):
            actual = hashlib.sha256(module_path.read_bytes()).hexdigest()
            if actual != row["module_sha256"]:
                raise AIException(ERR_AI_PLUGIN_LOAD_FAILED, f"{row['module_file']} sha256 does not match manifest pin")
        try:
            spec = importlib.util.spec_from_file_location(f"ai_plugin_{row['plugin_id']}", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            entry = getattr(module, row["entry_class"])
            config = json.loads(row.get("config_json") or "{}")
            plugin = entry(config)
        except Exception as exc:
            raise AIException(ERR_AI_PLUGIN_LOAD_FAILED, f"{row['plugin_id']}: {type(exc).__name__}: {exc}") from exc
        if not isinstance(plugin, BasePlugin):
            raise AIException(ERR_AI_PLUGIN_LOAD_FAILED, f"{row['entry_class']} is not a BasePlugin")
        if plugin.plugin_id != row["plugin_id"] or plugin.stage != row["stage"]:
            raise AIException(ERR_AI_PLUGIN_MANIFEST_INVALID, "class plugin_id/stage do not match manifest")
        self.register_plugin(plugin, priority=row["priority"], enabled=bool(row["enabled_default"]),
                             meta={"name": row["plugin_name"], "version": row["plugin_version"]})
        return plugin.plugin_id

    # -- execution -----------------------------------------------------------
    def run_stage(self, stage: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Run enabled plugins of `stage` in order. No-op when the gate is off."""
        if stage not in PLUGIN_STAGES:
            raise AIException(ERR_AI_PLUGIN_STAGE_INVALID, stage)
        if not self.is_enabled():
            return payload
        current = payload
        for plugin_id in self.list_plugins(stage):
            if not self._enabled[plugin_id]:
                continue
            try:
                current = self._plugins[plugin_id].process(current)
            except Exception as exc:
                _LOGGER.warning("Plugin '%s' (%s) failed: %s", plugin_id, stage, exc)
        return current

    Register_Plugin = register_plugin
    Unregister_Plugin = unregister_plugin
    List_Plugins = list_plugins
    Discover_Plugins = discover_plugins
    Run_Stage = run_stage
    Is_Enabled = is_enabled
    Set_Enabled = set_enabled


Plugin_Registry = PluginRegistry
