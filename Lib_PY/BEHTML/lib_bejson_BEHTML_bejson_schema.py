"""
Library:         lib_bejson_BEHTML_bejson_schema.py
Family:          BEHTML
Module Purpose:  Element table schema (105) and known element-type / content-kind sets.
Architecture:    BEHTML on BEJSON 105: one 105 table, one row per placed element, X0-X7 lanes, Ry=32px rows, Rz=32px layers; all field access via the Core field map.
Version:         1.0.0
Release_Version: 301
Date:            2026-11-13
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   963e9b9c-f95a-4e68-b917-d4b5ca20cb23
"""

import uuid
from typing import Any, Dict, List

import lib_bejson_BEHTML_bootstrap  # noqa: F401 -- puts 105 Core on sys.path

VERSION = "1.0.0"

BEHTML_ROOT_RECORDS_TYPE = "BEHTMLElement"
BEHTML_FORMAT_VERSION = "105"
BEHTML_ACCEPTED_FORMATS = ("105", "105a")

# Deterministic field_uuid namespace so every build yields identical Fields.
_FIELD_NS = uuid.UUID("b7e4c1d2-0a53-4e8f-9b16-3d2f5c7a9e01")

# Order matters only here; every reader resolves by name through the Core field map.
_ELEMENT_FIELDS_V2 = (
    ("element_id",    "string"),   # unique per document
    ("element_type",  "string"),   # "button", "card", "dialog" ...
    ("y_start",       "integer"),  # row index k, 0-based (Ry = 32px)
    ("y_span",        "integer"),  # rows occupied
    ("x_start",       "integer"),  # lane 0-7
    ("x_span",        "integer"),  # lanes occupied, 1-8
    ("z_layer",       "integer"),  # full layer n, depth n*32px
    ("z_half",        "boolean"),  # true = half-layer above z_layer, depth n*32+16
    ("bem_modifiers", "string"),   # comma-separated modifier tokens
    ("content_ref",   "string"),   # text / bound field / URL / asset
    ("parent_id_fk",  "string"),   # container element_id, null for root
    ("is_active",     "boolean"),  # selection state
    ("content_kind",  "string"),   # see KNOWN_CONTENT_KINDS
)

SCHEMA_BEHTML_ELEMENT_v2: List[Dict[str, str]] = [
    {"name": name, "type": ftype,
     "field_uuid": str(uuid.uuid5(_FIELD_NS, f"BEHTMLElement.{name}"))}
    for name, ftype in _ELEMENT_FIELDS_V2
]

KNOWN_CONTENT_KINDS = {"text", "url", "field_binding", "asset"}
DEFAULT_CONTENT_KIND = "text"

# Soft set: unknown types warn, they never fail (unless strict_types).
KNOWN_ELEMENT_TYPES = {
    # Z0 ground
    "page", "background", "canvas",
    # Z1 surface
    "card", "panel", "section", "table", "media", "image", "container", "grid_cell", "label",
    # Z2 control
    "input", "textarea", "button", "combobox", "checkbox", "radio", "toggle",
    "tab", "link",
    # Z3 chrome
    "header", "sidebar", "toolbar", "footer", "hamburger_menu",
    # Z4 overlay
    "dialog", "modal", "drawer", "dropdown", "popover",
    # Z5 transient
    "toast", "tooltip", "context_menu",
    # half-layer attachments
    "scrim", "shadow", "focus_ring", "resize_handle", "reveal_control",
    "ide_control", "drag_handle",
}


def behtml_schema_field_names() -> List[str]:
    """Field names in canonical order."""
    return [f["name"] for f in SCHEMA_BEHTML_ELEMENT_v2]


def behtml_schema_new_document() -> Dict[str, Any]:
    """Empty, spec-compliant BEHTML 105 document (Values empty)."""
    return {
        "Format": "BEJSON",
        "Format_Version": BEHTML_FORMAT_VERSION,
        "Format_Creator": "Elton Boehnen",
        "Records_Type": [BEHTML_ROOT_RECORDS_TYPE],
        "Fields": [dict(f) for f in SCHEMA_BEHTML_ELEMENT_v2],
        "Values": [],
    }
