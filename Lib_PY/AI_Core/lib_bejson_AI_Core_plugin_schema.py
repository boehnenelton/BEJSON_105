"""
Library:         lib_bejson_AI_Core_plugin_schema.py
Family:          AI_Core
Module Purpose:  Standard schema for AI plugin manifests (BEJSON 105a, record type AIPluginManifest).
                 Every plug-and-play module in the AI_Extensions family ships one extension.105a.bejson
                 describing itself; the registry refuses anything that does not validate here.
Architecture:    AI_Core defines the contract; AI_Extensions supplies conforming modules.
Version:         2.0.0
Release_Version: 300
Date:            2026-11-17
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   0d6e3a92-8b14-4c57-a1f0-72c9e5d4b8a1
"""
from __future__ import annotations

import re
from typing import Any, Dict, Final, List, Optional, Tuple

from lib_bejson_AI_Core_core_bridge import core_add_record, core_new_document, core_rows_as_dicts

VERSION: Final[str] = "2.0.0"
PLUGIN_API_VERSION: Final[str] = "1.0"
PLUGIN_MANIFEST_FILENAME: Final[str] = "extension.105a.bejson"
PLUGIN_RECORDS_TYPE: Final[str] = "AIPluginManifest"
PLUGIN_STAGES: Final[Tuple[str, ...]] = ("pre", "post", "render")

# (name, type, required)
PLUGIN_MANIFEST_FIELDS: Final[Tuple[Tuple[str, str, bool], ...]] = (
    ("plugin_id", "string", True),
    ("plugin_name", "string", True),
    ("plugin_version", "string", True),
    ("stage", "string", True),
    ("priority", "integer", True),
    ("module_file", "string", True),
    ("entry_class", "string", True),
    ("requires_plugin_api", "string", True),
    ("enabled_default", "boolean", True),
    ("description", "string", False),
    ("author", "string", False),
    ("module_sha256", "string", False),
    ("config_json", "string", False),
)

_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,47}$")
_VERSION_RE = re.compile(r"^\d+\.\d+(\.\d+)?$")
_MODULE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*\.py$")
_CLASS_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def plugin_api_tuple(version_text: str) -> Tuple[int, int]:
    major, minor = (version_text.split(".") + ["0"])[:2]
    return int(major), int(minor)


def plugin_manifest_new(
    plugin_id: str,
    plugin_name: str,
    plugin_version: str,
    stage: str,
    module_file: str,
    entry_class: str,
    *,
    priority: int = 100,
    requires_plugin_api: str = PLUGIN_API_VERSION,
    enabled_default: bool = True,
    description: str = "",
    author: str = "Elton Boehnen",
    module_sha256: Optional[str] = None,
    config_json: str = "{}",
) -> Dict[str, Any]:
    """Build a one-record manifest document through Core."""
    doc = core_new_document("105a", PLUGIN_RECORDS_TYPE, [(n, t) for n, t, _ in PLUGIN_MANIFEST_FIELDS],
                            Plugin_API_Version=PLUGIN_API_VERSION)
    core_add_record(doc, {
        "plugin_id": plugin_id, "plugin_name": plugin_name, "plugin_version": plugin_version,
        "stage": stage, "priority": priority, "module_file": module_file, "entry_class": entry_class,
        "requires_plugin_api": requires_plugin_api, "enabled_default": enabled_default,
        "description": description, "author": author, "module_sha256": module_sha256,
        "config_json": config_json,
    })
    return doc


def plugin_manifest_validate(doc: Dict[str, Any]) -> List[str]:
    """Schema problems for a manifest document ([] = conforms). Core-level validity is checked separately by core_load."""
    problems: List[str] = []
    if doc.get("Format_Version") != "105a":
        problems.append("Format_Version must be 105a")
    if doc.get("Records_Type") != [PLUGIN_RECORDS_TYPE]:
        problems.append(f"Records_Type must be [{PLUGIN_RECORDS_TYPE!r}]")
    declared = {f.get("name"): f.get("type") for f in doc.get("Fields", []) if isinstance(f, dict)}
    for name, ftype, required in PLUGIN_MANIFEST_FIELDS:
        if name not in declared:
            if required:
                problems.append(f"missing required field {name}")
        elif declared[name] != ftype:
            problems.append(f"field {name} must be {ftype}, is {declared[name]}")
    if problems:
        return problems
    rows = core_rows_as_dicts(doc)
    if len(rows) != 1:
        return [f"manifest must hold exactly one record, has {len(rows)}"]
    row = rows[0]
    if not _ID_RE.match(str(row["plugin_id"] or "")):
        problems.append("plugin_id must match ^[a-z][a-z0-9_]{2,47}$")
    if not str(row["plugin_name"] or "").strip():
        problems.append("plugin_name is empty")
    if not _VERSION_RE.match(str(row["plugin_version"] or "")):
        problems.append("plugin_version must be MAJOR.MINOR[.PATCH]")
    if row["stage"] not in PLUGIN_STAGES:
        problems.append(f"stage must be one of {list(PLUGIN_STAGES)}")
    priority = row["priority"]
    if not isinstance(priority, int) or isinstance(priority, bool) or not 0 <= priority <= 1000:
        problems.append("priority must be an integer 0..1000 (lower runs first)")
    if not _MODULE_RE.match(str(row["module_file"] or "")):
        problems.append("module_file must be a bare *.py filename (no path)")
    if not _CLASS_RE.match(str(row["entry_class"] or "")):
        problems.append("entry_class must be a Python identifier")
    if not _VERSION_RE.match(str(row["requires_plugin_api"] or "")):
        problems.append("requires_plugin_api must be MAJOR.MINOR")
    elif plugin_api_tuple(row["requires_plugin_api"]) > plugin_api_tuple(PLUGIN_API_VERSION):
        problems.append(f"requires plugin API {row['requires_plugin_api']} > host {PLUGIN_API_VERSION}")
    if row.get("module_sha256") and not _SHA_RE.match(str(row["module_sha256"])):
        problems.append("module_sha256 must be 64 lowercase hex chars")
    return problems
