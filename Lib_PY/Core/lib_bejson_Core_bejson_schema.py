"""
Library:        lib_bejson_Core_bejson_schema.py
Family:         Core
Description:    Unified registry for authoritative BEJSON schemas.
Version:        2.3.0
Date:           2026-10-03
Author:         Elton Boehnen
Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
Format_Creator: Elton Boehnen
RELATIONAL_ID:  7a8d88a4-3346-41aa-90f0-8c5eed413570
Release_Version: 300

Changelog:
  2.3.0 - 2026-10-03: Schema API parity with JS/TS/SH. Added
          bejson_schema_validate_against_detailed (full {valid, errors}
          result against a schema DOCUMENT, mirrors JS validateAgainst),
          bejson_schema_get_field_map (name -> definition) and
          bejson_schema_infer_from_data. BUG FIX: bejson_schema_extract used
          a shallow dict.copy(), so the returned schema aliased the source
          document's Fields list (mutating one mutated the other); now a deep
          copy. The existing bool bejson_schema_validate_against(doc,
          schema_fields) is unchanged for backward compatibility.
  2.2.0 - SCHEMA_MODEL_REGISTRY renamed to SCHEMA_MODEL_REGISTRY_GEMINI to
          eliminate the name collision with the OpenRouter registry defined
          in lib_bejson_AI_bejson_openrouter.py (Step 1 — 1.32 finalization).
          Downstream consumer lib_bejson_AI_bejson_gemini.py import updated.
  2.1.5 - Gemini 3.6 Flash released 2026-07-21; now the active default
          (thinking + Google Search on by default per Google's release).
          3.5 Flash demoted to an inactive row, not removed.
  2.1.4 - Re-added gemini-2.5-flash (inactive row) per direct instruction —
          kept as a cheap high-volume option, not the active default.
  2.1.3 - Library-immutability exception (see policy Sec 3.5.2): fixed
          SCHEMA_MODEL_REGISTRY default seed data, which pointed at a
          now-legacy default model and included a preview model ID that
          Google has since shut down. See docs/BUGFIX_gemini_model_registry.md.
"""

import copy
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# ===========================================================================
# AUTHORITATIVE SCHEMA DEFINITIONS
# ===========================================================================

# 1. Project Management v1.4.0 (22 Fields)
# Aligns ProjectService with official tracking standards.
# field names corrected from PascalCase to snake_case per BEJSON spec §14.7.
# NOTE: This is a breaking schema migration — any persisted data using old field names
#       (Project_ID, Project_Name, etc.) must be migrated before using this schema.
SCHEMA_PROJECT_v140 = [
    {"name": "record_type_parent",    "type": "string"},  # 0
    {"name": "project_id",            "type": "string"},  # 1
    {"name": "project_name",          "type": "string"},  # 2
    {"name": "project_path",          "type": "string"},  # 3
    {"name": "version",               "type": "string"},  # 4
    {"name": "created_at",            "type": "string"},  # 5
    {"name": "project_type",          "type": "string"},  # 6
    {"name": "is_active",             "type": "boolean"}, # 7
    {"name": "is_visible",            "type": "boolean"}, # 8
    {"name": "is_missing",            "type": "boolean"}, # 9
    {"name": "description",           "type": "string"},  # 10
    {"name": "tags",                  "type": "string"},  # 11
    {"name": "primary_agent",         "type": "string"},  # 12
    {"name": "last_sync",             "type": "string"},  # 13
    {"name": "file_count",            "type": "integer"}, # 14
    {"name": "total_size_kb",         "type": "number"},  # 15
    {"name": "git_enabled",           "type": "boolean"}, # 16
    {"name": "priority",              "type": "integer"}, # 17
    {"name": "category",              "type": "string"},  # 18
    {"name": "internal_notes",        "type": "string"},  # 19
    {"name": "is_archived",           "type": "boolean"}, # 20
    {"name": "is_reset_protected",    "type": "boolean"}, # 21
]

# 2. MFDB Chunker v5 Entity (6 Fields)
# Authoritative for project file contents.
SCHEMA_MFDB_ENTITY_v5 = [
    {"name": "version",   "type": "string"},
    {"name": "file_path", "type": "string"},
    {"name": "file_name", "type": "string"},
    {"name": "content",   "type": "string"},
    {"name": "is_binary", "type": "boolean"},
    {"name": "is_base64", "type": "boolean"},
]

# 3. MFDB Chunker v5 Manifest (9 Fields)
SCHEMA_MFDB_MANIFEST_v5 = [
    {"name": "entity_name",    "type": "string"},
    {"name": "file_path",      "type": "string"},
    {"name": "description",    "type": "string"},
    {"name": "record_count",   "type": "integer"},
    {"name": "schema_version", "type": "string"},
    {"name": "primary_key",    "type": "string"},
    {"name": "changelog",      "type": "string"},
    {"name": "chunked_at",     "type": "string"},
    {"name": "tags",           "type": "string"},
]

# 4. AI Model Registry — Gemini v2.1.2 (Positional Integrity Fix)
# Renamed from SCHEMA_MODEL_REGISTRY to SCHEMA_MODEL_REGISTRY_GEMINI (v2.2.0)
# to eliminate collision with SCHEMA_MODEL_REGISTRY_OPENROUTER in openrouter.py.
SCHEMA_MODEL_REGISTRY_GEMINI = {
    "Format": "BEJSON",
    "Format_Version": "104a",
    "Format_Creator": "Elton Boehnen",
    "Records_Type": ["AI_Model"],
    "Fields": [
        {"name": "display_name",          "type": "string"},  # 0
        {"name": "model_id",              "type": "string"},  # 1
        {"name": "currently_active",      "type": "boolean"}, # 2
        {"name": "thinking_enabled",      "type": "boolean"}, # 3
        {"name": "google_search_enabled", "type": "boolean"}  # 4
    ],
    "Values": [
        ["Gemini 3.6 Flash", "gemini-3.6-flash", True, True, True],
        ["Gemini 3.1 Pro (Preview)", "gemini-3.1-pro-preview", False, True, True],
        ["Gemini 3.1 Flash-Lite", "gemini-3.1-flash-lite", False, False, False],
        ["Gemini 2.5 Flash", "gemini-2.5-flash", False, False, False]
    ]
}

# ===========================================================================
# UTILITY FUNCTIONS
# ===========================================================================

def bejson_schema_extract(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Return the structure of doc with Values emptied. Deep copy: the result
    never aliases doc's Fields/Records_Type (2.3.0 fix; was a shallow copy)."""
    schema = copy.deepcopy(doc)
    schema["Values"] = []
    return schema

def bejson_schema_validate_against(doc: Dict[str, Any], schema_fields: List[Dict[str, Any]]) -> bool:
    doc_fields = doc.get("Fields", [])
    if len(doc_fields) != len(schema_fields):
        return False
    for i, (df, sf) in enumerate(zip(doc_fields, schema_fields)):
        if df.get("name") != sf.get("name") or df.get("type") != sf.get("type"):
            return False
    return True

def bejson_schema_validate_against_detailed(doc: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """Validate doc against a schema DOCUMENT (e.g. from bejson_schema_extract
    or bejson_schema_infer_from_data). Returns {"valid": bool, "errors": [str]}.
    Checks Format_Version, Records_Type, field count, and per-field name, type
    and Record_Type_Parent -- same checks, same order, as JS validateAgainst."""
    result: Dict[str, Any] = {"valid": True, "errors": []}

    if doc.get("Format_Version") != schema.get("Format_Version"):
        result["valid"] = False
        result["errors"].append(
            f"Version mismatch: Document is {doc.get('Format_Version')}, Schema is {schema.get('Format_Version')}")

    if doc.get("Records_Type") != schema.get("Records_Type"):
        result["valid"] = False
        result["errors"].append("Records_Type mismatch: Document types do not match schema types.")

    doc_fields = doc.get("Fields") or []
    sch_fields = schema.get("Fields") or []
    if len(doc_fields) != len(sch_fields):
        result["valid"] = False
        result["errors"].append(
            f"Field count mismatch: Document has {len(doc_fields)}, Schema has {len(sch_fields)}")
    else:
        for i, (df, sf) in enumerate(zip(doc_fields, sch_fields)):
            if df.get("name") != sf.get("name"):
                result["valid"] = False
                result["errors"].append(
                    f"Field name mismatch at index {i}: expected '{sf.get('name')}', found '{df.get('name')}'")
            if df.get("type") != sf.get("type"):
                result["valid"] = False
                result["errors"].append(
                    f"Field type mismatch for '{sf.get('name')}': expected '{sf.get('type')}', found '{df.get('type')}'")
            if df.get("Record_Type_Parent") != sf.get("Record_Type_Parent"):
                result["valid"] = False
                result["errors"].append(
                    f"Record_Type_Parent mismatch for '{sf.get('name')}': "
                    f"expected '{sf.get('Record_Type_Parent')}', found '{df.get('Record_Type_Parent')}'")
    return result


def bejson_schema_get_field_map(schema: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Field name -> full field definition (not an index; for index lookup use
    the Core field map cache)."""
    return {f["name"]: f for f in (schema.get("Fields") or [])}


def bejson_schema_infer_from_data(
    records_type: Union[str, List[str]],
    fields: List[Dict[str, Any]],
    version: str = "104a",
) -> Dict[str, Any]:
    """Build an empty schema document from scratch."""
    return {
        "Format": "BEJSON",
        "Format_Version": version,
        "Format_Creator": "Elton Boehnen",
        "Records_Type": list(records_type) if isinstance(records_type, (list, tuple)) else [records_type],
        "Fields": copy.deepcopy(fields),
        "Values": [],
    }

# 5. List Manager v1.0.0
# Authoritative for hierarchical list data used in JS Lister.
SCHEMA_LIST_MANAGER_v100 = [
    {"name": "id",          "type": "string"},  # Unique identifier
    {"name": "parent_id",   "type": "string"},  # Parent ID for hierarchy (null for root)
    {"name": "title",       "type": "string"},  # Item title
    {"name": "description", "type": "string"},  # Detailed description
]
