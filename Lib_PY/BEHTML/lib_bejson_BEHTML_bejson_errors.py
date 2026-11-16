"""
Library:         lib_bejson_BEHTML_bejson_errors.py
Family:          BEHTML
Module Purpose:  BEHTML family error registry (300-329). Hard codes are E_, soft (advisory) codes are W_.
Architecture:    BEHTML on BEJSON 105: one 105 table, one row per placed element, X0-X7 lanes, Ry=32px rows, Rz=32px layers; all field access via the Core field map.
Version:         1.0.0
Release_Version: 301
Date:            2026-11-13
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   66fea4d3-225c-409c-96db-8f18ace29b24
"""

VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# BEHTML (300-329) -- this family owns the whole range.
# ---------------------------------------------------------------------------
E_BEHTML_NOT_BEJSON            = 300  # Doc argument is not a dict
E_BEHTML_SCHEMA_MISMATCH       = 301  # Format_Version / Records_Type is not a BEHTML 105 table
E_BEHTML_MISSING_ELEMENT_ID    = 302  # element_id field absent or null
E_BEHTML_DUPLICATE_ELEMENT_ID  = 303  # element_id collides with another record
E_BEHTML_INVALID_Y_INDEX       = 304  # y_start negative or not an integer
E_BEHTML_INVALID_X_ADDRESS     = 305  # x_start outside the 0-7 lane range
E_BEHTML_X_SPAN_OVERFLOW       = 306  # x_start + x_span exceeds 8 lanes
E_BEHTML_INVALID_Y_SPAN        = 307  # y_span is not a positive integer
E_BEHTML_MATRIX_SHATTERED      = 308  # computed px height not a multiple of Ry (32px)
E_BEHTML_INVALID_ELEMENT_TYPE  = 309  # element_type not in the known set (strict mode only)
E_BEHTML_PARENT_NOT_FOUND      = 310  # parent_id_fk points to a missing element_id
E_BEHTML_INVALID_BEM_MODIFIER  = 311  # modifier string fails BEM grammar
E_BEHTML_PALETTE_VIOLATION     = 312  # black-on-red contrast law violated
E_BEHTML_ELEMENT_NOT_FOUND     = 313  # element_id not present in document
E_BEHTML_INVALID_CONTENT_KIND  = 314  # content_kind not in KNOWN_CONTENT_KINDS
E_BEHTML_INVALID_URL           = 315  # content_kind="url" but content_ref fails URL validation
E_BEHTML_MISSING_FIELD_BINDING = 316  # content_kind="field_binding" but content_ref is empty
E_BEHTML_OVERLAP_DETECTED      = 317  # rectangle collides with an existing element
E_BEHTML_RENDER_FAILED         = 318  # renderer raised while producing markup

# --- Z-axis (Rz = 32px layers, 16px half-layers) ---------------------------
E_BEHTML_Z_INVALID_DEPTH       = 319  # z_layer not a non-negative integer <= max, or z_half not a boolean
E_BEHTML_Z_LAYER_COLLISION     = 320  # same scope + same depth + overlapping X/Y cells
W_BEHTML_Z_NESTING_NOT_ABOVE   = 321  # child is not above its container's depth
W_BEHTML_Z_SEMANTIC_MISMATCH   = 322  # element_type sits outside its allowed layer range
W_BEHTML_Z_SKIPPED_LAYER       = 323  # child is more than one full layer above its container
W_BEHTML_Z_MISSING_SCRIM       = 324  # modal overlay without a scrim one half-layer below it
W_BEHTML_Z_LAYER_CROWDED       = 325  # more elements on one layer/scope than the crowd limit
W_BEHTML_Z_HALF_CONTENT_MISMATCH = 326  # half-layer holds something other than an attachment element
W_BEHTML_Z_CHROME_SCROLLS      = 327  # docked chrome element carries the 'scroll' modifier

# 328-329 reserved.

BEHTML_ERROR_NAMES = {
    value: name for name, value in dict(globals()).items()
    if (name.startswith("E_BEHTML_") or name.startswith("W_BEHTML_")) and isinstance(value, int)
}


def behtml_errors_name_of(code: int) -> str:
    """Return the constant name for a BEHTML code, or 'UNKNOWN'."""
    return BEHTML_ERROR_NAMES.get(code, "UNKNOWN")
