"""
Library:        lib_bejson_Core_bejson_validator.py
Family:         Core
Description:    Structural integrity checker for positional values and mandatory keys.
Version:        3.3.0
Date:           2026-09-25
Author:         Elton Boehnen
Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
Format_Creator: Elton Boehnen
RELATIONAL_ID:  75385f04-f2b5-470d-b6be-6bebaa24d675
Release_Version: 300

Changelog:
  3.3.0 - REMOVED bejson_validator_check_105_schema_constraints() entirely
          and its call site in validate_bejson(), per Be25 -- schema-value
          constraints (required/unique/enum/min/max/length) are cut.
          bejson_validator_check_105_strict_integrity() (field_uuid/FK
          structural checks) is untouched.
  3.2.0 - bejson_validator_check_105_schema_constraints(): required, unique,
          enum, min/max, minLength/maxLength -- audit-only, wired into
          validate_bejson() as a second added branch for 105-series
          (alongside the existing strict-integrity check). Every key is
          independently opt-in; a field declaring none of them is skipped
          without a row scan. Implements the Tier-1 + top-of-Tier-2
          suggestions from the Format 105 Validation Extensions proposal.
Changelog:
  3.1.0 - MERGE (2026-08-19): a parallel session independently fixed
          bejson_validator_check_fields_structure to reject any Field
          "type" outside the 6 canonical values (string/integer/number/
          boolean/array/object), shipped as v2.1.0 on the pre-105 baseline
          (didn't have 3.0.0's 105-series work). Version numbers diverged
          rather than one being simply behind: merged both lineages here
          rather than picking one. New VALID_FIELD_TYPES constant runs
          unconditionally for every version including 105/105a/105db (no
          version gate needed -- 105-series Fields use the same type
          vocabulary). Re-verified against the full 70-case suite plus
          three new cases for the merged check; all pass.
  3.0.0 - Format_Version 105/105a/105db registered (Format105_Master_Plan_Rev2
          Phase 3, \u00a73.1-\u00a73.2, paired with Core's 3.0.0). New
          bejson_validator_check_105_strict_integrity() enforces unique
          field_uuid per field, unique record_uuid at the format-correct row
          offset, and the Fail-on-Switch constraint (a 104 doc re-headered to
          105 without compiled UUIDs fails loudly here, not silently
          downstream). validate_bejson() gets exactly one added branch: the
          104-series call sequence and bejson_validator_check_values() (which
          assumes no UUID columns) are untouched and still run unmodified for
          104/104a/104db; 105-series docs run the new check instead, since
          check_values's raw positional length/type check does not account
          for the reserved record_uuid (+ discriminator, for 105db) columns.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Set, Union

try:
    from lib_bejson_Core_bejson_errors import (
        E_INVALID_JSON,
        E_MISSING_MANDATORY_KEY,
        E_INVALID_FORMAT,
        E_INVALID_VERSION,
        E_INVALID_RECORDS_TYPE,
        E_INVALID_FIELDS,
        E_INVALID_VALUES,
        E_TYPE_MISMATCH,
        E_RECORD_LENGTH_MISMATCH,
        E_RESERVED_KEY_COLLISION,
        E_INVALID_RECORD_TYPE_PARENT,
        E_FILE_NOT_FOUND
    )
except ImportError as e:
    import logging
    logging.critical(f"[VALIDATOR] FATAL: Error registry unreachable: {e}")
    raise SystemExit(1)

VALID_VERSIONS = {
    "104", "104a", "104db",
    "105", "105a", "105db",  # Integrity Era (Format105_Master_Plan_Rev2)
}
VALID_FIELD_TYPES = {"string", "integer", "number", "boolean", "array", "object"}
MANDATORY_KEYS = ("Format", "Format_Version", "Format_Creator", "Records_Type", "Fields", "Values")

@dataclass
class ValidationResult:
    valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    current_file: str = ""

    def add_error(self, message: str):
        self.valid = False
        self.errors.append(message)

    def add_warning(self, message: str):
        self.warnings.append(message)

    @property
    def is_valid(self) -> bool:
        """Alias for .valid. A caller reaching for result.is_valid instead
        of result.valid is a reasonable, common guess at this class's own
        API -- cheap to make both spellings work rather than requiring
        every consumer to know the exact attribute name. (Synced from the
        same fix applied in NewAgent's local copy of this file, 2026-08-13,
        after an AttributeError surfaced in a PROFILER-style caller.)"""
        return self.valid

class BEJSONValidationError(Exception):
    def __init__(self, message: str, code: int):
        super().__init__(message)
        self.code = code

def bejson_validator_check_json_syntax(input_, res: ValidationResult, is_file=False):
    if is_file:
        path = Path(input_)
        if not path.exists(): raise BEJSONValidationError(f"File not found: {input_}", E_FILE_NOT_FOUND)
        text = path.read_text(encoding="utf-8")
        res.current_file = str(path)
    else: text = input_
    if isinstance(text, dict): return text
    try: return json.loads(text)
    except Exception as e: raise BEJSONValidationError(f"Invalid JSON: {e}", E_INVALID_JSON)

def bejson_validator_check_mandatory_keys(doc):
    for key in MANDATORY_KEYS:
        if key not in doc: raise BEJSONValidationError(f"Missing key: {key}", E_MISSING_MANDATORY_KEY)
    if doc["Format"] != "BEJSON": raise BEJSONValidationError("Invalid Format", E_INVALID_FORMAT)
    if doc["Format_Creator"] != "Elton Boehnen":
        raise BEJSONValidationError("Invalid Format_Creator: Must be 'Elton Boehnen'", E_INVALID_FORMAT)
    version = doc.get("Format_Version", "")
    if version not in VALID_VERSIONS: raise BEJSONValidationError(f"Invalid version: {version}", E_INVALID_VERSION)
    return version

def bejson_validator_check_records_type(doc, version):
    rt = doc["Records_Type"]
    if not isinstance(rt, list):
        raise BEJSONValidationError("Records_Type must be a list", E_INVALID_RECORDS_TYPE)
    count = len(rt)
    if version in ("104", "104a"):
        if count != 1:
            raise BEJSONValidationError(f"BEJSON {version} must have exactly 1 record type. Found {count}.", E_INVALID_RECORDS_TYPE)
    elif version == "104db":
        if count < 2:
            raise BEJSONValidationError("104db requires 2+ types", E_INVALID_RECORDS_TYPE)

def bejson_validator_check_record_type_parent(doc, version):
    if version != "104db": return True
    fields = doc["Fields"]
    if not fields or fields[0].get("name") != "Record_Type_Parent":
        raise BEJSONValidationError("104db first field must be 'Record_Type_Parent'", E_INVALID_RECORD_TYPE_PARENT)
    valid_types = set(doc["Records_Type"])
    for i, record in enumerate(doc["Values"]):
        if not record: continue
        rtp = record[0]
        if rtp not in valid_types:
            raise BEJSONValidationError(f"Invalid Record_Type_Parent '{rtp}' at row {i}", E_INVALID_RECORD_TYPE_PARENT)
    return True

def bejson_validator_check_fields_structure(doc, version):
    fields = doc["Fields"]
    for i, f in enumerate(fields):
        fname = f.get("name")
        ftype = f.get("type")
        if not fname or not ftype:
            raise BEJSONValidationError(f"Field {i} missing name or type", E_INVALID_FIELDS)
        if ftype not in VALID_FIELD_TYPES:
            raise BEJSONValidationError(
                f"Field '{fname}' (index {i}) has invalid type '{ftype}'. "
                f"Must be exactly one of {sorted(VALID_FIELD_TYPES)} (lowercase).",
                E_INVALID_FIELDS,
            )
        if version == "104a" and ftype in ("array", "object"):
            raise BEJSONValidationError(f"104a forbids complex type: {ftype}", E_INVALID_FIELDS)
        if version == "104db" and fname != "Record_Type_Parent" and "Record_Type_Parent" not in f:
            raise BEJSONValidationError(f"Field '{fname}' missing Record_Type_Parent in 104db", E_INVALID_RECORD_TYPE_PARENT)
    return len(fields)

def bejson_validator_check_values(doc, version, fields_count):
    fields = doc["Fields"]
    for i, record in enumerate(doc["Values"]):
        if len(record) != fields_count:
            raise BEJSONValidationError(f"Length mismatch at row {i}", E_RECORD_LENGTH_MISMATCH)
        for j, val in enumerate(record):
            ftype = fields[j].get("type")
            if val is None: continue
            
            # Full type validation including array/object
            if ftype == "string" and not isinstance(val, str):
                 raise BEJSONValidationError(f"Type mismatch at row {i}, col {j} ({fields[j]['name']}): expected string", E_TYPE_MISMATCH)
            elif ftype == "integer" and (not isinstance(val, int) or isinstance(val, bool)):
                 raise BEJSONValidationError(f"Type mismatch at row {i}, col {j} ({fields[j]['name']}): expected integer", E_TYPE_MISMATCH)
            elif ftype == "number" and (not isinstance(val, (int, float)) or isinstance(val, bool)):
                 # bool is a subclass of int in Python, so True/False pass isinstance(int,float).
                 # Explicitly exclude bool — BEJSON "number" means a numeric value, not a boolean.
                 raise BEJSONValidationError(f"Type mismatch at row {i}, col {j} ({fields[j]['name']}): expected number, got bool", E_TYPE_MISMATCH)
            elif ftype == "boolean" and not isinstance(val, bool):
                 raise BEJSONValidationError(f"Type mismatch at row {i}, col {j} ({fields[j]['name']}): expected boolean", E_TYPE_MISMATCH)
            elif ftype == "array" and not isinstance(val, list):
                 raise BEJSONValidationError(f"Type mismatch at row {i}, col {j} ({fields[j]['name']}): expected array", E_TYPE_MISMATCH)
            elif ftype == "object" and not isinstance(val, dict):
                 raise BEJSONValidationError(f"Type mismatch at row {i}, col {j} ({fields[j]['name']}): expected object", E_TYPE_MISMATCH)

def bejson_validator_check_custom_headers(doc, version):
    mandatory_set = set(MANDATORY_KEYS)
    for key in doc:
        if key in mandatory_set or key == "Parent_Hierarchy": continue
        if version in ("104", "104db"):
            raise BEJSONValidationError(f"Custom key '{key}' forbidden in {version}", E_RESERVED_KEY_COLLISION)
        # 104a: Custom headers allowed, no strict PascalCase enforcement
        # Audit 2 Finding: Removed warning to avoid conflict with 104db rigidity.

def bejson_validator_check_105_strict_integrity(doc: dict) -> list:
    """
    Three checks, each mapped to an existing Core error code: every field
    must carry a unique field_uuid (E_INVALID_FIELDS), every record row must
    carry a unique, non-null record_uuid at the format-correct offset
    (E_INVALID_VALUES), and -- the Fail-on-Switch constraint -- a document
    whose version header was bumped to 105 without the UUIDs actually being
    compiled must fail immediately rather than passing structural validation
    and drifting silently downstream.
    """
    errors = []

    seen_field_uuids = set()
    for field in doc.get("Fields", []):
        fuuid = field.get("field_uuid")
        if not fuuid or not isinstance(fuuid, str):
            errors.append({
                "code": "E_INVALID_FIELDS",
                "detail": f"field {field.get('name')!r} missing a valid field_uuid key",
            })
        elif fuuid in seen_field_uuids:
            errors.append({
                "code": "E_INVALID_FIELDS",
                "detail": f"duplicate field_uuid {fuuid!r}",
            })
        else:
            seen_field_uuids.add(fuuid)

    offset = 2 if doc.get("Format_Version") == "105db" else 1
    uuid_col = offset - 1
    seen_record_uuids = set()
    for i, row in enumerate(doc.get("Values", [])):
        ruuid = row[uuid_col] if len(row) > uuid_col else None
        if not ruuid or not isinstance(ruuid, str):
            errors.append({
                "code": "E_INVALID_VALUES",
                "detail": f"row {i} missing a valid record_uuid at index {uuid_col}",
            })
        elif ruuid in seen_record_uuids:
            errors.append({
                "code": "E_INVALID_VALUES",
                "detail": f"duplicate record_uuid {ruuid!r} at row {i}",
            })
        else:
            seen_record_uuids.add(ruuid)

    # Fail-on-Switch: a 104 file re-headered to 105 without compiling
    # field_uuids must fail loudly here, not drift silently downstream.
    if not doc.get("Fields") or not all("field_uuid" in f for f in doc["Fields"]):
        errors.append({
            "code": "E_INVALID_FIELDS",
            "detail": "Format_Version claims 105-series but Fields were never compiled "
                      "with field_uuid keys -- run bejson_core_upgrade_to_105() before using this file",
        })

    return errors


def validate_bejson(input_data: Union[str, dict], is_file: bool = False) -> ValidationResult:
    """Thread-safe validation. Returns a ValidationResult object."""
    res = ValidationResult()
    try:
        doc = bejson_validator_check_json_syntax(input_data, res, is_file=is_file)
        version = bejson_validator_check_mandatory_keys(doc)
        bejson_validator_check_custom_headers(doc, version)
        bejson_validator_check_records_type(doc, version)
        bejson_validator_check_record_type_parent(doc, version)
        fields_count = bejson_validator_check_fields_structure(doc, version)
        if version in ("105", "105a", "105db"):
            for err in bejson_validator_check_105_strict_integrity(doc):
                res.add_error(f"[{err['code']}] {err['detail']}")
        else:
            bejson_validator_check_values(doc, version, fields_count)
    except BEJSONValidationError as e:
        res.add_error(str(e))
    except Exception as e:
        res.add_error(f"Unexpected validation error: {e}")
    return res

def bejson_validator_get_report(input_data, is_file: bool = False) -> str:
    """Return a human-readable validation report string."""
    res = validate_bejson(input_data, is_file=is_file)
    lines = ["BEJSON Validation Report"]
    lines.append("  File: " + (res.current_file or "<string>"))
    lines.append("  Valid: " + str(res.valid))
    if res.errors:
        lines.append("  Errors:")
        for e in res.errors:
            lines.append("    - " + e)
    if res.warnings:
        lines.append("  Warnings:")
        for w in res.warnings:
            lines.append("    - " + w)
    return "\n".join(lines)

# Compatibility wrappers (now internal state is gone)
def bejson_validator_validate_string(json_string):
    res = validate_bejson(json_string)
    if not res.valid:
        raise BEJSONValidationError(res.errors[0], E_INVALID_FORMAT)
    return True

def bejson_validator_validate_file(file_path):
    res = validate_bejson(file_path, is_file=True)
    if not res.valid:
        raise BEJSONValidationError(res.errors[0], E_INVALID_FORMAT)
    return True
