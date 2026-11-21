"""
File Name      : lib_bejson_Standardized_Entities_core.py
Rel. Path      : Lib_PY/Standardized_Entities/lib_bejson_Standardized_Entities_core.py
Description    : Standardized_Entities Core module owning 14-field schema constants and MFDB v1.40 writers.
Version        : 1.0.0
Date Created   : 2026-11-20
Author Credit  : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
License        : PolyForm Noncommercial License 1.0.0 (PolyForm-Noncommercial-1.0.0)
RELATIONAL_ID  : 8f4a2b10-7e3c-4a92-b816-1d9c3a0b4e52
"""
from __future__ import annotations

import logging
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

# Sibling family directory Lib_PY/Core resolves dynamically relative to this file
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_CORE_PATH = os.path.normpath(os.path.join(_HERE, "..", "Core"))
if os.path.isdir(_CORE_PATH) and _CORE_PATH not in sys.path:
    sys.path.insert(0, _CORE_PATH)

from lib_bejson_Core_bejson_core import (  # noqa: E402
    ResilientPIDLock,
    bejson_core_get_field_map,
)
from lib_bejson_Core_mfdb_core import (  # noqa: E402
    mfdb_core_add_entity_record_105,
    mfdb_core_create_database,
    mfdb_core_create_entity_file,
    mfdb_core_enable_ref_integrity,
    mfdb_core_get_entity_doc,
    mfdb_core_load_manifest,
    mfdb_core_update_entity_record_105,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Universal 14-Field Schema Constants & Enums
# ---------------------------------------------------------------------------
STANDARDIZED_ENTITY_FIELDS: Tuple[Tuple[str, str, bool, Any], ...] = (
    ("key", "string", True, None),
    ("label", "string", True, None),
    ("value", "string", True, None),
    ("value_type", "string", False, "string"),
    ("domain", "string", True, None),
    ("category", "string", True, None),
    ("details", "string", False, None),
    ("tags", "array", False, None),
    ("flags", "array", False, None),
    ("context_mode", "string", False, "inject"),
    ("is_active", "boolean", False, True),
    ("created_at", "string", True, None),
    ("updated_at", "string", False, None),
    ("sender", "string", False, None),
)

SE_VALUE_TYPES: Tuple[str, ...] = (
    "string",
    "url",
    "path",
    "env_var",
    "secret_ref",
    "json",
    "text",
)

SE_CONTEXT_MODES: Tuple[str, ...] = (
    "inject",
    "reference",
    "hidden",
)

SE_TIMESTAMP_FORMAT: str = "%Y-%m-%dT%H:%M:%SZ"

_ENTITY_NAME_REGEX: re.Pattern = re.compile(r"^[A-Za-z0-9]+_[A-Za-z0-9_]+$")
_MUTABLE_FIELDS = {
    "key",
    "label",
    "value",
    "value_type",
    "details",
    "tags",
    "flags",
    "context_mode",
    "is_active",
    "sender",
}
_IMMUTABLE_FIELDS = {"record_uuid", "domain", "category", "created_at"}


# ---------------------------------------------------------------------------
# Schema Functions
# ---------------------------------------------------------------------------
def se_core_parse_entity_name(entity_name: str) -> Tuple[str, str]:
    """
    Validate ^[A-Za-z0-9]+_[A-Za-z0-9_]+$ and split on first '_' into (domain, category).
    Domain contains no '_'; Category may contain '_'.
    """
    if not isinstance(entity_name, str) or not _ENTITY_NAME_REGEX.match(entity_name):
        raise ValueError(
            f"Invalid entity name '{entity_name}'. Must match ^[A-Za-z0-9]+_[A-Za-z0-9_]+$"
        )
    domain, category = entity_name.split("_", 1)
    return domain, category


def se_core_build_fields() -> List[Dict[str, str]]:
    """
    Emit the exact 14 {'name', 'type'} field definitions in canonical order.
    Core stamps fresh UUIDv4 field_uuids at write time.
    """
    return [{"name": name, "type": ftype} for name, ftype, _, _ in STANDARDIZED_ENTITY_FIELDS]


def se_core_deploy_database(
    root_dir: str,
    db_name: str,
    entities: List[str],
    network_role: str = "Master",
) -> str:
    """
    Deploy a fresh MFDB v1.40 database with the specified standardized entities.
    Wraps mfdb_core_create_database with format_version='105', schema-templated fields,
    and enables referential integrity.
    """
    if not entities:
        raise ValueError("At least one entity must be provided for se_core_deploy_database.")

    entity_defs: List[Dict[str, Any]] = []
    seen_entities = set()
    for ent_name in entities:
        se_core_parse_entity_name(ent_name)
        if ent_name in seen_entities:
            raise ValueError(f"Duplicate entity name '{ent_name}' in deployment list.")
        seen_entities.add(ent_name)
        entity_defs.append(
            {
                "name": ent_name,
                "format_version": "105",
                "fields": se_core_build_fields(),
                "description": f"Standardized entity {ent_name}",
            }
        )

    manifest_path = mfdb_core_create_database(
        root_dir=root_dir,
        db_name=db_name,
        entities=entity_defs,
        mfdb_version="1.40",
        network_role=network_role,
    )
    mfdb_core_enable_ref_integrity(manifest_path)
    return manifest_path


def se_core_write_entity(
    manifest_path: str,
    entity_name: str,
    description: str = "",
) -> str:
    """
    Deploy a single schema-templated Format 105 entity into an existing MFDB manifest.
    Rejects duplicate entity names.
    """
    se_core_parse_entity_name(entity_name)
    manifest_records = mfdb_core_load_manifest(manifest_path)
    existing_entities = {rec.get("entity_name") for rec in manifest_records}
    if entity_name in existing_entities:
        raise ValueError(f"Entity '{entity_name}' already exists in manifest '{manifest_path}'.")

    return mfdb_core_create_entity_file(
        manifest_path=manifest_path,
        entity_name=entity_name,
        fields=se_core_build_fields(),
        description=description,
        format_version="105",
    )


def se_core_build_record(
    entity_name: str,
    key: str,
    label: str,
    value: str,
    **kwargs: Any,
) -> List[Any]:
    """
    Construct the 14-value row list (WITHOUT record_uuid) adhering to STANDARDIZED_ENTITY_FIELDS.
    Auto-derives domain and category from entity_name, stamps created_at, and enforces enums.
    """
    domain, category = se_core_parse_entity_name(entity_name)

    if not isinstance(key, str) or not key.strip():
        raise ValueError("Field 'key' must be a non-empty string.")
    if not isinstance(label, str) or not label.strip():
        raise ValueError("Field 'label' must be a non-empty string.")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Field 'value' must be a non-empty string.")

    value_type = kwargs.pop("value_type", "string")
    details = kwargs.pop("details", None)
    tags = kwargs.pop("tags", None)
    flags = kwargs.pop("flags", None)
    context_mode = kwargs.pop("context_mode", "inject")
    is_active = kwargs.pop("is_active", True)
    sender = kwargs.pop("sender", None)

    if kwargs:
        unknown_keys = sorted(kwargs.keys())
        raise ValueError(f"Unknown kwargs passed to se_core_build_record: {unknown_keys}")

    if value_type not in SE_VALUE_TYPES:
        raise ValueError(f"Invalid value_type '{value_type}'. Must be one of {SE_VALUE_TYPES}")

    if context_mode not in SE_CONTEXT_MODES:
        raise ValueError(f"Invalid context_mode '{context_mode}'. Must be one of {SE_CONTEXT_MODES}")

    if not isinstance(is_active, bool):
        raise TypeError(f"Field 'is_active' must be a boolean, got {type(is_active).__name__}")

    if details is not None and not isinstance(details, str):
        raise TypeError("Field 'details' must be a string or None.")

    if sender is not None and not isinstance(sender, str):
        raise TypeError("Field 'sender' must be a string or None.")

    if tags is not None:
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            raise TypeError("Field 'tags' must be a list of strings or None.")

    if flags is not None:
        if not isinstance(flags, list) or not all(isinstance(f, str) for f in flags):
            raise TypeError("Field 'flags' must be a list of strings or None.")

    created_at = datetime.now(timezone.utc).strftime(SE_TIMESTAMP_FORMAT)
    updated_at = None

    return [
        key,
        label,
        value,
        value_type,
        domain,
        category,
        details,
        tags,
        flags,
        context_mode,
        is_active,
        created_at,
        updated_at,
        sender,
    ]


def se_core_add_record(
    manifest_path: str,
    entity_name: str,
    key: str,
    label: str,
    value: str,
    **kwargs: Any,
) -> str:
    """
    Validate key uniqueness, build record, and append via mfdb_core_add_entity_record_105.
    Returns the newly minted record_uuid.
    """
    doc = mfdb_core_get_entity_doc(manifest_path, entity_name)
    field_map = bejson_core_get_field_map(doc)
    key_idx = field_map.get("key")
    if key_idx is None:
        raise ValueError(f"Entity '{entity_name}' does not contain 'key' field.")

    for row in doc.get("Values", []):
        if row[key_idx] == key:
            raise ValueError(f"Duplicate key '{key}' already exists in entity '{entity_name}'.")

    row_values = se_core_build_record(entity_name, key, label, value, **kwargs)
    updated_doc = mfdb_core_add_entity_record_105(manifest_path, entity_name, row_values)
    new_record_uuid = updated_doc["Values"][-1][0]
    return new_record_uuid


def se_core_update_record(
    manifest_path: str,
    entity_name: str,
    record_uuid: str,
    changes: Dict[str, Any],
    sender: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update mutable fields on an existing record addressed by record_uuid.
    Enforces immutability of record_uuid, domain, category, created_at.
    Checks uniqueness if key is updated, and updates updated_at timestamp.
    """
    if not isinstance(changes, dict) or not changes:
        if sender is None:
            raise ValueError("No changes provided to se_core_update_record.")
        changes = {}

    for k in changes:
        if k in _IMMUTABLE_FIELDS:
            raise ValueError(f"Field '{k}' is immutable and cannot be updated.")
        if k not in _MUTABLE_FIELDS:
            raise ValueError(f"Field '{k}' is not a valid mutable field.")

    # Validate change values
    if "key" in changes:
        new_key = changes["key"]
        if not isinstance(new_key, str) or not new_key.strip():
            raise ValueError("Field 'key' must be a non-empty string.")
        # Check uniqueness against other records in entity
        doc = mfdb_core_get_entity_doc(manifest_path, entity_name)
        field_map = bejson_core_get_field_map(doc)
        key_idx = field_map["key"]
        for row in doc.get("Values", []):
            if row[0] != record_uuid and row[key_idx] == new_key:
                raise ValueError(f"Duplicate key '{new_key}' already exists in entity '{entity_name}'.")

    if "value_type" in changes:
        vt = changes["value_type"]
        if vt not in SE_VALUE_TYPES:
            raise ValueError(f"Invalid value_type '{vt}'. Must be one of {SE_VALUE_TYPES}")

    if "context_mode" in changes:
        cm = changes["context_mode"]
        if cm not in SE_CONTEXT_MODES:
            raise ValueError(f"Invalid context_mode '{cm}'. Must be one of {SE_CONTEXT_MODES}")

    if "is_active" in changes:
        ia = changes["is_active"]
        if not isinstance(ia, bool):
            raise TypeError(f"Field 'is_active' must be a boolean, got {type(ia).__name__}")

    if "details" in changes and changes["details"] is not None and not isinstance(changes["details"], str):
        raise TypeError("Field 'details' must be a string or None.")

    if "tags" in changes and changes["tags"] is not None:
        t = changes["tags"]
        if not isinstance(t, list) or not all(isinstance(x, str) for x in t):
            raise TypeError("Field 'tags' must be a list of strings or None.")

    if "flags" in changes and changes["flags"] is not None:
        fl = changes["flags"]
        if not isinstance(fl, list) or not all(isinstance(x, str) for x in fl):
            raise TypeError("Field 'flags' must be a list of strings or None.")

    if "label" in changes and (not isinstance(changes["label"], str) or not changes["label"].strip()):
        raise ValueError("Field 'label' must be a non-empty string.")

    if "value" in changes and (not isinstance(changes["value"], str) or not changes["value"].strip()):
        raise ValueError("Field 'value' must be a non-empty string.")

    # Apply changes field-by-field
    last_doc = None
    for field_name, new_val in changes.items():
        last_doc = mfdb_core_update_entity_record_105(
            manifest_path=manifest_path,
            entity_name=entity_name,
            record_uuid=record_uuid,
            field_name=field_name,
            new_value=new_val,
        )

    if sender is not None:
        if not isinstance(sender, str):
            raise TypeError("Param 'sender' must be a string.")
        last_doc = mfdb_core_update_entity_record_105(
            manifest_path=manifest_path,
            entity_name=entity_name,
            record_uuid=record_uuid,
            field_name="sender",
            new_value=sender,
        )

    # Stamp updated_at
    now_iso = datetime.now(timezone.utc).strftime(SE_TIMESTAMP_FORMAT)
    last_doc = mfdb_core_update_entity_record_105(
        manifest_path=manifest_path,
        entity_name=entity_name,
        record_uuid=record_uuid,
        field_name="updated_at",
        new_value=now_iso,
    )

    return last_doc
