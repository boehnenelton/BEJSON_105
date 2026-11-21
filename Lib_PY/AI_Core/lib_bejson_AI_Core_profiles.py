"""
Library:         lib_bejson_AI_Core_profiles.py
Family:          AI_Core
Module Purpose:  AI Profile data layer on BEJSON 105. Replaces lib_bejson_AI_gemini_standard_profiles (104).
                 One profile per file, Format 105, Records_Type ["AI_Profile"] (1.0, 22 fields) or
                 ["AI_Profile_v2"] (2.0, 31 fields). Every read/write goes through the Core bridge and
                 the Core field map; record_uuid is implicit and never declared. Optional Parser_Language /
                 Parser / Renderer string columns are stored here as data only; validating and running
                 embedded code is AI_Extensions' job (lib_bejson_AI_Extensions_profile_runtime).
                 104 -> 105 conversion: ai_profiles_convert_104_to_105 / ai_profiles_convert_file.
Version:         2.0.2
Release_Version: 300
Date:            2026-11-17
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   35d69430-efec-4014-a179-df009567b0f7

Changelog:
  2.0.2 (2026-11-20) -- Version bump for changes made after 2.0.1 without one: Mode column forbidden (ai_profiles_problems), defaults
          Max_Response_Tokens 42000 / Creativity 1.0 / Tone [Concise, Helpful] / Verbosity Formal, affective-feature global switch
          (ai_profiles_set/get_affective_features_disabled, ai_profiles_bypass_affective_features, honored by ai_profiles_row).
  2.0.1 (2026-11-17) -- ai_profiles_convert_104_to_105 works on a deep copy: core_field_map writes a _bejson_field_map cache
          into the document, so the "source is not modified" guarantee did not hold (found by test_ai_profiles).
  2.0.0 (2026-11-17) -- New. Ported from lib_bejson_AI_gemini_standard_profiles 4.1.0 (104). Changes:
          Format 105 (field_uuid / record_uuid); Record_Type_Parent column dropped (it was a constant that
          duplicated Records_Type and is meaningless outside 104db); API prefix gemini_profiles_* ->
          ai_profiles_* (old names kept as aliases); no direct file I/O (Core bridge); embedded-code
          validation/execution moved to AI_Extensions; Google Search column stays removed.
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from lib_bejson_AI_Core_core_bridge import (
    core_add_record,
    core_define_field,
    core_field_map,
    core_load,
    core_new_document,
    core_rows_as_dicts,
    core_save,
    core_validate,
    core_write_cell,
)
from lib_bejson_AI_Core_errors import (
    AIException,
    ERR_AI_PROFILE_INVALID,
    ERR_AI_PROFILE_MIGRATION_FAILED,
    ERR_AI_PROFILE_NOT_FOUND,
)

VERSION = "2.0.2"
_LOGGER = logging.getLogger("lib_bejson_AI_Core_profiles")

RECORDS_TYPE_V1 = "AI_Profile"
RECORDS_TYPE_V2 = "AI_Profile_v2"
LEGACY_PARENT_FIELD = "Record_Type_Parent"

_SHARED_TAIL: Tuple[Tuple[str, str], ...] = (
    ("Max_Response_Tokens", "integer"), ("Creativity", "number"), ("Tone", "array"),
    ("Formality", "string"), ("Verbosity", "string"),
    ("Emotional_Expression_Enabled", "boolean"), ("Emotional_Expression_Intensity", "number"),
)

# Profile 1.0 (22 fields). Order matches the 104 schema minus Record_Type_Parent.
PROFILE_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("Name", "string"), ("Archetype", "string"), ("Persona", "string"), ("System_Instruction", "string"),
    ("Forbidden_Topics", "array"), ("Avatar_Type", "string"), ("Avatar_Source_Url", "string"),
    ("Avatar_Data", "string"),
) + _SHARED_TAIL + (
    ("Code_Interpreter_Enabled", "boolean"), ("Ephemeral_Memory", "boolean"),
    ("Code_Parsing_Mode", "string"), ("Code_Parsing_Languages", "array"),
    ("Code_Parsing_Structure_Validation", "boolean"), ("Code_Parsing_Version_Control", "boolean"),
    ("Thinking_Supported", "boolean"),
)

# Profile 2.0 (31 fields).
PROFILE_2_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("Name", "string"), ("Archetype", "string"), ("Persona", "string"), ("Job", "string"),
    ("Specialty", "array"), ("Starting_Temper", "integer"), ("Stability", "integer"),
    ("Irritations", "array"), ("Pleasures", "array"), ("Knowledge_Base", "array"),
    ("Knowledge_Directive", "string"), ("System_Instruction", "string"), ("Forbidden_Topics", "array"),
    ("Active", "boolean"), ("Max_Response_Tokens", "integer"), ("Creativity", "number"), ("Tone", "array"),
    ("Formality", "string"), ("Verbosity", "string"),
    ("Emotional_Expression_Enabled", "boolean"), ("Emotional_Expression_Intensity", "number"),
    ("Thinking_Supported", "boolean"), ("Code_Interpreter_Enabled", "boolean"), ("Ephemeral_Memory", "boolean"),
    ("Code_Parsing_Mode", "string"), ("Code_Parsing_Languages", "array"),
    ("Code_Parsing_Structure_Validation", "boolean"), ("Code_Parsing_Version_Control", "boolean"),
    ("Avatar_Type", "string"), ("Avatar_Source_Url", "string"), ("Avatar_Data", "string"),
)

OPTIONAL_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("Parser_Language", "string"), ("Parser", "string"), ("Renderer", "string"),
)

PROFILE_DEFAULTS: Dict[str, Any] = {
    "Forbidden_Topics": [], "Avatar_Type": "Emoji", "Avatar_Source_Url": "", "Avatar_Data": "🤖",
    "Max_Response_Tokens": 42000, "Creativity": 1.0, "Tone": ["Concise", "Helpful"],
    "Formality": "Formal", "Verbosity": "Formal", "Emotional_Expression_Enabled": False,
    "Emotional_Expression_Intensity": 0.0, "Code_Interpreter_Enabled": True, "Ephemeral_Memory": True,
    "Code_Parsing_Mode": "complete", "Code_Parsing_Languages": [],
    "Code_Parsing_Structure_Validation": True, "Code_Parsing_Version_Control": False,
    "Thinking_Supported": True,
    "Job": "Chat", "Specialty": [], "Starting_Temper": 0, "Stability": 2, "Irritations": [], "Pleasures": [],
    "Knowledge_Base": [], "Knowledge_Directive": "", "Active": True,
}

_V1_NAMES = {n for n, _ in PROFILE_FIELDS}
_V2_NAMES = {n for n, _ in PROFILE_2_FIELDS}
_OPTIONAL_NAMES = {n for n, _ in OPTIONAL_FIELDS}


def ai_profiles_is_v2(doc: Dict[str, Any]) -> bool:
    """True when the document declares or carries the Profile 2.0 schema."""
    if not isinstance(doc, dict):
        return False
    if RECORDS_TYPE_V2 in (doc.get("Records_Type") or []):
        return True
    names = {f.get("name") for f in doc.get("Fields", []) if isinstance(f, dict)}
    return _V2_NAMES.issubset(names)


def ai_profiles_problems(doc: Dict[str, Any]) -> List[str]:
    """All reasons *doc* is not a valid 105 AI profile ([] = valid)."""
    if not isinstance(doc, dict):
        return ["not a document"]
    problems = [f"core: {p}" for p in core_validate(doc)]
    if doc.get("Format_Version") != "105":
        problems.append(f"Format_Version must be 105, is {doc.get('Format_Version')!r}")
    v2 = ai_profiles_is_v2(doc)
    expected_type = RECORDS_TYPE_V2 if v2 else RECORDS_TYPE_V1
    if doc.get("Records_Type") != [expected_type]:
        problems.append(f"Records_Type must be [{expected_type!r}]")
    declared = {f.get("name"): f.get("type") for f in doc.get("Fields", []) if isinstance(f, dict)}
    for name, ftype in (PROFILE_2_FIELDS if v2 else PROFILE_FIELDS):
        if name not in declared:
            problems.append(f"missing field {name}")
        elif declared[name] != ftype:
            problems.append(f"field {name} must be {ftype}, is {declared[name]}")
    for name, ftype in OPTIONAL_FIELDS:
        if name in declared and declared[name] != ftype:
            problems.append(f"optional field {name} must be {ftype}, is {declared[name]}")
    if LEGACY_PARENT_FIELD in declared:
        problems.append(f"{LEGACY_PARENT_FIELD} is a 104-only column and must not appear in a 105 profile")
    if "Mode" in declared:
        problems.append("Mode is deprecated and forbidden in profiles")
    if not doc.get("Values"):
        problems.append("profile has no record")
    return problems


def ai_profiles_validate(doc: Dict[str, Any]) -> bool:
    problems = ai_profiles_problems(doc)
    for problem in problems:
        _LOGGER.debug("profile validation: %s", problem)
    return not problems


def ai_profiles_create(
    name: str, archetype: str, persona: str, instruction: str, *, v2: bool = False, **kwargs: Any
) -> Dict[str, Any]:
    """New one-record 105 profile. kwargs are This_Case field names (see PROFILE_DEFAULTS); Parser_Language /
    Parser / Renderer add their (string) columns only when given."""
    schema = PROFILE_2_FIELDS if v2 else PROFILE_FIELDS
    names = {n for n, _ in schema}
    unknown = set(kwargs) - names - _OPTIONAL_NAMES
    if unknown:
        raise AIException(ERR_AI_PROFILE_INVALID, f"unknown profile fields: {sorted(unknown)}")
    values: Dict[str, Any] = {n: PROFILE_DEFAULTS[n] for n in names if n in PROFILE_DEFAULTS}
    values.update({"Name": name, "Archetype": archetype, "Persona": persona, "System_Instruction": instruction})
    values.update({k: v for k, v in kwargs.items() if k in names})
    fields = list(schema) + [f for f in OPTIONAL_FIELDS if kwargs.get(f[0]) is not None]
    doc = core_new_document("105", RECORDS_TYPE_V2 if v2 else RECORDS_TYPE_V1, fields)
    values.update({k: kwargs[k] for k in _OPTIONAL_NAMES if kwargs.get(k) is not None})
    try:
        core_add_record(doc, values)
    except AIException as exc:
        raise AIException(ERR_AI_PROFILE_INVALID, exc.detail) from exc
    return doc


_CONFIG_DISABLE_AFFECTIVE_FEATURES: bool = False


def ai_profiles_set_affective_features_disabled(disabled: bool) -> None:
    """Configures whether v2 mood, temper, irritation, and pleasure features are bypassed."""
    global _CONFIG_DISABLE_AFFECTIVE_FEATURES
    _CONFIG_DISABLE_AFFECTIVE_FEATURES = bool(disabled)


def ai_profiles_get_affective_features_disabled() -> bool:
    """Returns True if v2 affective mood/temper features are globally bypassed."""
    return _CONFIG_DISABLE_AFFECTIVE_FEATURES


def ai_profiles_bypass_affective_features(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Rules v2 mood, temper, irritation, and pleasure entries null so they are completely bypassed."""
    out = copy.deepcopy(doc)
    fmap = core_field_map(out)
    affective_fields = [
        "Starting_Temper", "Stability", "Irritations", "Pleasures",
        "Emotional_Expression_Enabled", "Emotional_Expression_Intensity"
    ]
    for row in out.get("Values", []):
        for field in affective_fields:
            idx = fmap.get(field)
            if idx is not None and idx < len(row):
                if field == "Emotional_Expression_Enabled":
                    row[idx] = False
                elif field == "Emotional_Expression_Intensity":
                    row[idx] = 0.0
                elif field in ("Irritations", "Pleasures"):
                    row[idx] = None
                else:
                    row[idx] = None
    return out


def ai_profiles_get_field_map(profile: Dict[str, Any]) -> Dict[str, int]:
    return core_field_map(profile)


def ai_profiles_row(profile: Dict[str, Any], record_index: int = 0) -> Dict[str, Any]:
    """The record as a plain name -> value dict (plus record_uuid)."""
    rows = core_rows_as_dicts(profile)
    if record_index >= len(rows):
        raise AIException(ERR_AI_PROFILE_NOT_FOUND, f"record {record_index}")
    row = dict(rows[record_index])
    if _CONFIG_DISABLE_AFFECTIVE_FEATURES or profile.get("Affective_Features_Disabled") is True:
        for f in ("Starting_Temper", "Stability", "Irritations", "Pleasures"):
            if f in row:
                row[f] = None
        if "Emotional_Expression_Enabled" in row:
            row["Emotional_Expression_Enabled"] = False
        if "Emotional_Expression_Intensity" in row:
            row["Emotional_Expression_Intensity"] = 0.0
    return row


def ai_profiles_get_value(profile: Dict[str, Any], field_name: str, record_index: int = 0) -> Any:
    fmap = core_field_map(profile)
    rows = profile.get("Values", [])
    idx = fmap.get(field_name)
    if idx is None or record_index >= len(rows) or idx >= len(rows[record_index]):
        return None
    return rows[record_index][idx]


def ai_profiles_update_value(profile: Dict[str, Any], field_name: str, new_value: Any, record_index: int = 0) -> bool:
    """Type-checked update (Core write_cell). False when the field/record does not exist or the type is wrong."""
    rows = profile.get("Values", [])
    if record_index >= len(rows) or field_name not in core_field_map(profile):
        _LOGGER.warning("ai_profiles_update_value: field %r or record %d not found", field_name, record_index)
        return False
    try:
        core_write_cell(profile, rows[record_index][0], field_name, new_value)
    except AIException as exc:
        _LOGGER.warning("ai_profiles_update_value rejected: %s", exc.detail)
        return False
    return True


def _set_optional(profile: Dict[str, Any], field_name: str, value: Optional[str], record_index: int) -> bool:
    clean = value if isinstance(value, str) and value.strip() else None
    if field_name not in core_field_map(profile):
        if clean is None:
            return True
        core_define_field(profile, field_name, "string")
    return ai_profiles_update_value(profile, field_name, clean, record_index)


def _get_optional(profile: Dict[str, Any], field_name: str, record_index: int) -> Optional[str]:
    value = ai_profiles_get_value(profile, field_name, record_index)
    return value if isinstance(value, str) and value.strip() else None


def ai_profiles_get_parser(profile: Dict[str, Any], record_index: int = 0) -> Optional[Dict[str, str]]:
    code = _get_optional(profile, "Parser", record_index)
    language = _get_optional(profile, "Parser_Language", record_index)
    if code is None or language is None:
        return None
    return {"language": language.strip().lower(), "code": code}


def ai_profiles_set_parser(
    profile: Dict[str, Any], language: Optional[str], code: Optional[str], record_index: int = 0,
    code_validator: Optional[Callable[[Optional[str], str], List[str]]] = None,
) -> bool:
    """Sets (or clears when code is blank) Parser + Parser_Language. Pass AI_Extensions'
    runtime_validate_parser as code_validator to reject bad code; nothing is written on rejection."""
    if code is None or not str(code).strip():
        ok = _set_optional(profile, "Parser", None, record_index)
        return _set_optional(profile, "Parser_Language", None, record_index) and ok
    if code_validator is not None:
        problems = code_validator(language, code)
        if problems:
            _LOGGER.warning("ai_profiles_set_parser rejected: %s", "; ".join(problems))
            return False
    ok = _set_optional(profile, "Parser_Language", (language or "").strip().lower() or None, record_index)
    return _set_optional(profile, "Parser", code, record_index) and ok


def ai_profiles_get_renderer(profile: Dict[str, Any], record_index: int = 0) -> Optional[str]:
    return _get_optional(profile, "Renderer", record_index)


def ai_profiles_set_renderer(
    profile: Dict[str, Any], code: Optional[str], record_index: int = 0,
    code_validator: Optional[Callable[[str], List[str]]] = None,
) -> bool:
    if code is None or not str(code).strip():
        return _set_optional(profile, "Renderer", None, record_index)
    if code_validator is not None:
        problems = code_validator(code)
        if problems:
            _LOGGER.warning("ai_profiles_set_renderer rejected: %s", "; ".join(problems))
            return False
    return _set_optional(profile, "Renderer", code, record_index)


def ai_profiles_embedded_fingerprint(profile: Dict[str, Any], record_index: int = 0) -> Optional[str]:
    """SHA-256 over (language, parser, renderer) for approval pinning; None when no embedded code.
    Identical to the 104 library's value so existing approvals carry over."""
    parser = ai_profiles_get_parser(profile, record_index)
    renderer = ai_profiles_get_renderer(profile, record_index)
    if parser is None and renderer is None:
        return None
    blob = json.dumps(
        [parser["language"] if parser else "", parser["code"] if parser else "", renderer or ""],
        ensure_ascii=False,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def ai_profiles_save(profile: Dict[str, Any], path: Path | str) -> None:
    """Validate as a profile, then write through Core."""
    problems = ai_profiles_problems(profile)
    if problems:
        raise AIException(ERR_AI_PROFILE_INVALID, "; ".join(problems))
    core_save(path, profile)


def ai_profiles_load(path: Path | str) -> Dict[str, Any]:
    """Read through Core and require a valid 105 profile."""
    doc = core_load(path)
    problems = ai_profiles_problems(doc)
    if problems:
        raise AIException(ERR_AI_PROFILE_INVALID, f"{path}: {'; '.join(problems)}")
    return doc


def ai_profiles_query_by_name(profiles_dir: Path | str, profile_name: str) -> Optional[Dict[str, Any]]:
    """First *.bejson in *profiles_dir* whose Name equals *profile_name* (case-sensitive); unreadable files skipped."""
    for candidate in sorted(Path(profiles_dir).glob("*.bejson")):
        try:
            doc = ai_profiles_load(candidate)
        except AIException as exc:
            _LOGGER.debug("skipping %s: %s", candidate, exc.detail)
            continue
        if ai_profiles_get_value(doc, "Name") == profile_name:
            return doc
    return None


# -- 104 -> 105 conversion ----------------------------------------------------

def ai_profiles_convert_104_to_105(doc104: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert an in-memory 104/104a AI profile (1.0 or 2.0) into a 105 profile. Lossless for every
    schema column and for Parser_Language / Parser / Renderer when present; Record_Type_Parent and the
    legacy Mode column are dropped. Rows are read by field name (never by position). The source is not
    modified. Raises AIException(ERR_AI_PROFILE_MIGRATION_FAILED) when the source is not a profile.
    """
    if doc104.get("Format_Version") not in ("104", "104a"):
        raise AIException(ERR_AI_PROFILE_MIGRATION_FAILED, f"expected 104/104a, got {doc104.get('Format_Version')!r}")
    declared = {f.get("name") for f in doc104.get("Fields", []) if isinstance(f, dict)}
    v2 = ai_profiles_is_v2(doc104)
    schema = PROFILE_2_FIELDS if v2 else PROFILE_FIELDS
    missing = {n for n, _ in schema} - declared
    if missing:
        raise AIException(ERR_AI_PROFILE_MIGRATION_FAILED, f"missing profile fields: {sorted(missing)}")
    doc104 = copy.deepcopy(doc104)  # core_field_map caches into the document; never touch the caller's copy
    fmap = core_field_map(doc104)
    carried_optional = [f for f in OPTIONAL_FIELDS if f[0] in declared]
    out = core_new_document("105", RECORDS_TYPE_V2 if v2 else RECORDS_TYPE_V1, list(schema) + carried_optional)
    wanted = [n for n, _ in schema] + [n for n, _ in carried_optional]
    for row in doc104.get("Values", []):
        core_add_record(out, {n: (row[fmap[n]] if fmap[n] < len(row) else None) for n in wanted})
    problems = ai_profiles_problems(out)
    if problems:
        raise AIException(ERR_AI_PROFILE_MIGRATION_FAILED, "; ".join(problems))
    return out


def ai_profiles_convert_file(source_path: Path | str, target_path: Path | str) -> Dict[str, Any]:
    """Read a 104 profile file, write the 105 conversion to *target_path* (never in place), return the 105 doc."""
    if Path(source_path).resolve() == Path(target_path).resolve():
        raise AIException(ERR_AI_PROFILE_MIGRATION_FAILED, "target must differ from source; the 104 file is never overwritten")
    converted = ai_profiles_convert_104_to_105(core_load(source_path))
    ai_profiles_save(converted, target_path)
    return converted


# -- Profile_Config helpers (selection / enable switch) -----------------------

def ai_profiles_get_config_value(config_path: Path | str, key: str) -> Optional[str]:
    """Value for Config_Key *key* in a Profile_Config document (104a or 105a); None when absent/unreadable."""
    try:
        doc = core_load(config_path)
    except AIException as exc:
        _LOGGER.warning("profile config unreadable: %s", exc.detail)
        return None
    for row in core_rows_as_dicts(doc):
        if row.get("Config_Key") == key:
            return row.get("Config_Value")
    return None


def ai_profiles_get_selected(config_path: Path | str) -> str:
    return ai_profiles_get_config_value(config_path, "Selected_Profile") or "default"


def ai_profiles_is_enabled(config_path: Path | str) -> bool:
    return str(ai_profiles_get_config_value(config_path, "Profiles_Enabled") or "false").strip().lower() == "true"


# Migration aliases (names the 104 library exported)
gemini_profiles_validate = ai_profiles_validate
gemini_profiles_create = ai_profiles_create
gemini_profiles_get_value = ai_profiles_get_value
gemini_profiles_update_value = ai_profiles_update_value
gemini_profiles_get_field_map = ai_profiles_get_field_map
gemini_profiles_save = ai_profiles_save
gemini_profiles_query_by_name = ai_profiles_query_by_name
gemini_profiles_get_selected = ai_profiles_get_selected
gemini_profiles_is_enabled = ai_profiles_is_enabled
gemini_profiles_is_v2 = ai_profiles_is_v2
gemini_profiles_get_parser = ai_profiles_get_parser
gemini_profiles_set_parser = ai_profiles_set_parser
gemini_profiles_get_renderer = ai_profiles_get_renderer
gemini_profiles_set_renderer = ai_profiles_set_renderer
gemini_profiles_embedded_fingerprint = ai_profiles_embedded_fingerprint
