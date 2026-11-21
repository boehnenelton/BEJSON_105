"""
File Name      : lib_bejson_Standardized_Entities_validator.py
Rel. Path      : Lib_PY/Standardized_Entities/lib_bejson_Standardized_Entities_validator.py
Description    : Standardized_Entities Validator module enforcing read-only 14-field schema invariants and MFDB integrity.
Version        : 1.0.0
Date Created   : 2026-11-20
Author Credit  : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
License        : PolyForm Noncommercial License 1.0.0 (PolyForm-Noncommercial-1.0.0)
RELATIONAL_ID  : 9c3b1e20-8a4d-4b83-a927-2e8d4b1c5f63
"""
from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Sibling family directory Lib_PY/Core resolves dynamically relative to this file
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_CORE_PATH = os.path.normpath(os.path.join(_HERE, "..", "Core"))
if os.path.isdir(_CORE_PATH) and _CORE_PATH not in sys.path:
    sys.path.insert(0, _CORE_PATH)

from lib_bejson_Core_bejson_core import (  # noqa: E402
    bejson_core_get_field_map,
    bejson_core_verify_105_integrity,
)
from lib_bejson_Core_bejson_validator import validate_bejson  # noqa: E402
from lib_bejson_Core_mfdb_core import (  # noqa: E402
    _resolve_entity_path,
    mfdb_core_load_manifest,
)
from lib_bejson_Core_mfdb_validator import validate_mfdb_database  # noqa: E402

from lib_bejson_Standardized_Entities_core import (  # noqa: E402
    SE_CONTEXT_MODES,
    SE_TIMESTAMP_FORMAT,
    SE_VALUE_TYPES,
    STANDARDIZED_ENTITY_FIELDS,
    se_core_parse_entity_name,
)

logger = logging.getLogger(__name__)


def se_validator_validate_schema(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that doc['Fields'] has exactly 14 fields matching STANDARDIZED_ENTITY_FIELDS
    in name, type, and order, with valid unique UUIDv4 field_uuids.
    """
    errors: List[str] = []
    warnings: List[str] = []

    fields = doc.get("Fields")
    if not isinstance(fields, list):
        errors.append("Document missing 'Fields' list.")
        return {"passed": False, "errors": errors, "warnings": warnings}

    if len(fields) != len(STANDARDIZED_ENTITY_FIELDS):
        errors.append(
            f"Fields length mismatch: expected {len(STANDARDIZED_ENTITY_FIELDS)}, got {len(fields)}"
        )
        return {"passed": False, "errors": errors, "warnings": warnings}

    seen_field_uuids: Set[str] = set()
    for idx, (expected_name, expected_type, _, _) in enumerate(STANDARDIZED_ENTITY_FIELDS):
        field = fields[idx]
        if not isinstance(field, dict):
            errors.append(f"Field at index {idx} is not a dictionary.")
            continue

        actual_name = field.get("name")
        actual_type = field.get("type")
        actual_uuid = field.get("field_uuid")

        if actual_name != expected_name:
            errors.append(
                f"Field [{idx}] name mismatch: expected '{expected_name}', got '{actual_name}'"
            )

        if actual_type != expected_type:
            errors.append(
                f"Field [{idx}] type mismatch for '{expected_name}': expected '{expected_type}', got '{actual_type}'"
            )

        if not actual_uuid:
            errors.append(f"Field [{idx}] '{expected_name}' missing 'field_uuid'.")
        else:
            try:
                parsed_uuid = uuid.UUID(str(actual_uuid))
                if parsed_uuid.version != 4:
                    errors.append(
                        f"Field [{idx}] '{expected_name}' field_uuid '{actual_uuid}' is not UUIDv4 (version {parsed_uuid.version})."
                    )
            except Exception as e:
                errors.append(
                    f"Field [{idx}] '{expected_name}' field_uuid '{actual_uuid}' is not a valid UUID: {e}"
                )

            if actual_uuid in seen_field_uuids:
                errors.append(
                    f"Duplicate field_uuid '{actual_uuid}' detected in entity fields at index {idx}."
                )
            seen_field_uuids.add(actual_uuid)

    return {"passed": len(errors) == 0, "errors": errors, "warnings": warnings}


def se_validator_validate_entity(
    entity_path_or_doc: Union[str, Dict[str, Any]],
    is_file: bool = True,
) -> Dict[str, Any]:
    """
    Validate that an entity complies with BEJSON 105, 14-field schema, and all Value Invariants.
    Pure read-only verification gate.
    """
    errors: List[str] = []
    warnings: List[str] = []

    # 1. Base BEJSON Validation
    if is_file:
        if not isinstance(entity_path_or_doc, str) or not os.path.isfile(entity_path_or_doc):
            return {
                "passed": False,
                "errors": [f"Entity file not found: {entity_path_or_doc}"],
                "warnings": [],
            }
        val_res = validate_bejson(entity_path_or_doc, is_file=True)
        if not val_res.is_valid:
            errors.extend([f"[BaseValidation] {e}" for e in val_res.errors])
        try:
            with open(entity_path_or_doc, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            return {
                "passed": False,
                "errors": [f"Failed to read/parse entity JSON: {e}"],
                "warnings": warnings,
            }
    else:
        doc = entity_path_or_doc
        val_res = validate_bejson(doc, is_file=False)
        if not val_res.is_valid:
            errors.extend([f"[BaseValidation] {e}" for e in val_res.errors])

    if not isinstance(doc, dict):
        return {
            "passed": False,
            "errors": ["Entity document is not a JSON object."],
            "warnings": warnings,
        }

    # 2. Format Version check
    fmt_ver = doc.get("Format_Version")
    if fmt_ver != "105":
        errors.append(f"Format_Version mismatch: expected '105', got '{fmt_ver}'")

    # 3. Core 105 Integrity check
    try:
        report = bejson_core_verify_105_integrity(doc)
        if not report.get("ok", False):
            errors.extend([f"[Integrity105] {e}" for e in report.get("errors", [])])
    except Exception as e:
        errors.append(f"bejson_core_verify_105_integrity raised exception: {e}")

    # 4. Schema verification (14 fields, names, types, field_uuids)
    schema_res = se_validator_validate_schema(doc)
    if not schema_res["passed"]:
        errors.extend(schema_res["errors"])

    # 5. Entity Name & Records_Type check
    records_type = doc.get("Records_Type")
    entity_name = None
    expected_domain = None
    expected_category = None
    if not isinstance(records_type, list) or not records_type:
        errors.append("Records_Type is missing or empty.")
    else:
        entity_name = records_type[0]
        try:
            expected_domain, expected_category = se_core_parse_entity_name(entity_name)
        except Exception as e:
            errors.append(f"Records_Type[0] '{entity_name}' is not a valid standardized entity name: {e}")

    # 6. Value Invariants Check
    values = doc.get("Values", [])
    if not isinstance(values, list):
        errors.append("Values is not a list.")
        values = []

    seen_record_uuids: Set[str] = set()
    seen_keys: Set[str] = set()

    for row_idx, row in enumerate(values):
        if not isinstance(row, list):
            errors.append(f"Row {row_idx} is not a list.")
            continue

        # Invariant 1: Exactly 15 cells (record_uuid + 14 fields)
        if len(row) != 15:
            errors.append(
                f"Row {row_idx} length mismatch: expected 15 cells (record_uuid + 14 fields), got {len(row)}"
            )
            continue

        row_uuid = row[0]
        key = row[1]
        label = row[2]
        value = row[3]
        value_type = row[4]
        domain = row[5]
        category = row[6]
        details = row[7]
        tags = row[8]
        flags = row[9]
        context_mode = row[10]
        is_active = row[11]
        created_at = row[12]
        updated_at = row[13]
        sender = row[14]

        # Invariant 2: record_uuid is unique UUIDv4 at index 0
        try:
            parsed_ruuid = uuid.UUID(str(row_uuid))
            if parsed_ruuid.version != 4:
                errors.append(f"Row {row_idx} record_uuid '{row_uuid}' is not UUIDv4.")
        except Exception as e:
            errors.append(f"Row {row_idx} record_uuid '{row_uuid}' is not a valid UUID: {e}")

        if row_uuid in seen_record_uuids:
            errors.append(f"Row {row_idx} duplicate record_uuid '{row_uuid}'.")
        seen_record_uuids.add(row_uuid)

        # Invariant 3: key, label, value, domain, category, created_at non-null non-empty strings
        for field_label, val in (
            ("key", key),
            ("label", label),
            ("value", value),
            ("domain", domain),
            ("category", category),
            ("created_at", created_at),
        ):
            if not isinstance(val, str) or not val.strip():
                errors.append(f"Row {row_idx} field '{field_label}' must be a non-empty string, got {val!r}")

        # Invariant 4: key unique within entity
        if isinstance(key, str):
            if key in seen_keys:
                errors.append(f"Row {row_idx} duplicate key '{key}' detected in entity.")
            seen_keys.add(key)

        # Invariant 5: domain and category match entity_name
        if expected_domain and domain != expected_domain:
            errors.append(
                f"Row {row_idx} domain '{domain}' does not match entity domain '{expected_domain}'"
            )
        if expected_category and category != expected_category:
            errors.append(
                f"Row {row_idx} category '{category}' does not match entity category '{expected_category}'"
            )

        # Invariant 6: value_type in SE_VALUE_TYPES, context_mode in SE_CONTEXT_MODES
        if value_type not in SE_VALUE_TYPES:
            errors.append(
                f"Row {row_idx} invalid value_type '{value_type}'. Must be one of {SE_VALUE_TYPES}"
            )
        if context_mode not in SE_CONTEXT_MODES:
            errors.append(
                f"Row {row_idx} invalid context_mode '{context_mode}'. Must be one of {SE_CONTEXT_MODES}"
            )

        # Invariant 7: is_active is boolean (never null)
        if not isinstance(is_active, bool):
            errors.append(
                f"Row {row_idx} field 'is_active' must be a boolean, got {type(is_active).__name__}"
            )

        # Invariant 8: tags, flags null or array of strings; details, sender null or string
        if tags is not None and (not isinstance(tags, list) or not all(isinstance(t, str) for t in tags)):
            errors.append(f"Row {row_idx} field 'tags' must be null or list of strings.")

        if flags is not None and (not isinstance(flags, list) or not all(isinstance(f, str) for f in flags)):
            errors.append(f"Row {row_idx} field 'flags' must be null or list of strings.")

        if details is not None and not isinstance(details, str):
            errors.append(f"Row {row_idx} field 'details' must be null or string.")

        if sender is not None and not isinstance(sender, str):
            errors.append(f"Row {row_idx} field 'sender' must be null or string.")

        # Invariant 9: created_at / updated_at ISO-8601 formatting and ordering
        dt_created = None
        if isinstance(created_at, str) and created_at.strip():
            try:
                dt_created = datetime.strptime(created_at, SE_TIMESTAMP_FORMAT)
            except Exception:
                errors.append(
                    f"Row {row_idx} created_at '{created_at}' does not match {SE_TIMESTAMP_FORMAT}"
                )

        if updated_at is not None:
            if not isinstance(updated_at, str) or not updated_at.strip():
                errors.append(f"Row {row_idx} updated_at must be null or a non-empty string.")
            else:
                try:
                    dt_updated = datetime.strptime(updated_at, SE_TIMESTAMP_FORMAT)
                    if dt_created and dt_updated < dt_created:
                        errors.append(
                            f"Row {row_idx} updated_at '{updated_at}' is earlier than created_at '{created_at}'"
                        )
                except Exception:
                    errors.append(
                        f"Row {row_idx} updated_at '{updated_at}' does not match {SE_TIMESTAMP_FORMAT}"
                    )

    return {"passed": len(errors) == 0, "errors": errors, "warnings": warnings}


def se_validator_validate_database(
    manifest_path: str,
    strict_fk: bool = True,
) -> Dict[str, Any]:
    """
    Validate an entire MFDB v1.40 database:
    1. Base MFDB validation via validate_mfdb_database.
    2. Manifest check (104a manifest, MFDB_Version == '1.40').
    3. Validate every entity with se_validator_validate_entity.
    4. Verify entity file Records_Type[0] equals manifest entity_name.
    5. Error on any field_uuid repeated across entities.
    """
    errors: List[str] = []
    warnings: List[str] = []
    entity_names: List[str] = []

    if not os.path.isfile(manifest_path):
        return {
            "passed": False,
            "entities": [],
            "errors": [f"Manifest not found: {manifest_path}"],
            "warnings": [],
        }

    # 1. Base MFDB validation
    try:
        base_mfdb_res = validate_mfdb_database(manifest_path, strict_fk=strict_fk)
        if not base_mfdb_res.valid:
            for err in base_mfdb_res.errors:
                errors.append(f"[BaseMFDB] {err}")
        for w in base_mfdb_res.warnings:
            warnings.append(f"[BaseMFDB] {w}")
    except Exception as e:
        errors.append(f"validate_mfdb_database raised exception: {e}")

    # 2. Check manifest format and MFDB_Version
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_doc = json.load(f)
    except Exception as e:
        return {
            "passed": False,
            "entities": [],
            "errors": [f"Failed to read manifest JSON: {e}"],
            "warnings": warnings,
        }

    if manifest_doc.get("MFDB_Version") != "1.40":
        errors.append(
            f"MFDB_Version mismatch: expected '1.40', got '{manifest_doc.get('MFDB_Version')}'"
        )

    # 3. Load manifest entity entries
    try:
        manifest_entries = mfdb_core_load_manifest(manifest_path)
    except Exception as e:
        errors.append(f"Failed to load manifest records: {e}")
        manifest_entries = []

    global_field_uuids: Dict[str, str] = {}  # field_uuid -> entity_name

    for entry in manifest_entries:
        ent_name = entry.get("entity_name")
        rel_path = entry.get("file_path")
        if not ent_name or not rel_path:
            errors.append(f"Invalid manifest entry: {entry}")
            continue

        entity_names.append(ent_name)
        resolved_path = _resolve_entity_path(manifest_path, rel_path)

        # Validate entity
        ent_res = se_validator_validate_entity(resolved_path, is_file=True)
        if not ent_res["passed"]:
            for err in ent_res["errors"]:
                errors.append(f"[{ent_name}] {err}")
        for w in ent_res["warnings"]:
            warnings.append(f"[{ent_name}] {w}")

        # Check Records_Type[0] matches manifest entity_name
        try:
            with open(resolved_path, "r", encoding="utf-8") as f:
                ent_doc = json.load(f)
            rt = ent_doc.get("Records_Type", [])
            if not rt or rt[0] != ent_name:
                errors.append(
                    f"Entity '{resolved_path}' Records_Type[0] '{rt[0] if rt else None}' != manifest entity_name '{ent_name}'"
                )

            # Check cross-entity field_uuid uniqueness
            for f in ent_doc.get("Fields", []):
                fuuid = f.get("field_uuid")
                if fuuid:
                    if fuuid in global_field_uuids:
                        errors.append(
                            f"Field_uuid '{fuuid}' in entity '{ent_name}' is duplicated from entity '{global_field_uuids[fuuid]}'"
                        )
                    else:
                        global_field_uuids[fuuid] = ent_name
        except Exception as e:
            errors.append(f"Failed inspecting entity file '{resolved_path}': {e}")

    return {
        "passed": len(errors) == 0,
        "entities": entity_names,
        "errors": errors,
        "warnings": warnings,
    }
