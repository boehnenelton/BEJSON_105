"""
Library:         lib_bejson_BEHTML_core.py
Family:          BEHTML
Module Purpose:  Spatial constants and math (X lanes, Y rows, Z layers), the standard Z layer table, element-type layer rules, rule policy (hard/soft/off) and element helpers.
Architecture:    BEHTML on BEJSON 105: one 105 table, one row per placed element, X0-X7 lanes, Ry=32px rows, Rz=32px layers; all field access via the Core field map.
Version:         1.0.0
Release_Version: 301
Date:            2026-11-13
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   07d3a127-1e31-4412-b06e-d4e77dbc29c4
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import lib_bejson_BEHTML_bootstrap  # noqa: F401 -- puts 105 Core on sys.path

try:
    from lib_bejson_Core_bejson_core import (
        bejson_core_add_record_105,
        bejson_core_delete_record,
        bejson_core_get_field_map,
    )
    from lib_bejson_BEHTML_bejson_errors import (
        E_BEHTML_ELEMENT_NOT_FOUND,
        E_BEHTML_INVALID_BEM_MODIFIER,
        E_BEHTML_INVALID_X_ADDRESS,
        E_BEHTML_INVALID_Y_INDEX,
        E_BEHTML_INVALID_Y_SPAN,
        E_BEHTML_MATRIX_SHATTERED,
        E_BEHTML_PALETTE_VIOLATION,
        E_BEHTML_X_SPAN_OVERFLOW,
        E_BEHTML_Z_INVALID_DEPTH,
        E_BEHTML_Z_LAYER_COLLISION,
        W_BEHTML_Z_CHROME_SCROLLS,
        W_BEHTML_Z_HALF_CONTENT_MISMATCH,
        W_BEHTML_Z_LAYER_CROWDED,
        W_BEHTML_Z_MISSING_SCRIM,
        W_BEHTML_Z_NESTING_NOT_ABOVE,
        W_BEHTML_Z_SEMANTIC_MISMATCH,
        W_BEHTML_Z_SKIPPED_LAYER,
    )
    from lib_bejson_BEHTML_bejson_schema import behtml_schema_field_names
except ImportError as exc:
    logging.critical("[BEHTML_CORE] FATAL: dependency unreachable: %s", exc)
    raise SystemExit(1)

VERSION = "1.0.0"


class BEHTMLError(Exception):
    """Raised for a hard BEHTML spatial-law, palette or Z-law violation."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[E{code}] {message}")


# ---------------------------------------------------------------------------
# Universal spatial constants
# ---------------------------------------------------------------------------
BEHTML_RY_PX = 32                     # Y quantum
BEHTML_RZ_PX = 32                     # Z quantum (one full layer)
BEHTML_RZ_HALF_PX = 16                # half-layer offset above a full layer
BEHTML_X_LANES = 8
BEHTML_X_QUANTUM_PCT = 12.5
BEHTML_QUANTIZATION_TOLERANCE = 0.001
BEHTML_Z_MAX_LAYER = 31               # 31 * 32 = 992px; configurable per policy

BEHTML_COLOR_WHITE = "#FFFFFF"
BEHTML_COLOR_BLACK = "#000000"
BEHTML_COLOR_ACCENT = "#DE2626"


# ---------------------------------------------------------------------------
# Y axis
# ---------------------------------------------------------------------------
def behtml_core_quantize_y(height_px: float) -> int:
    """Nearest positive multiple k of Ry for a pixel height."""
    if height_px is None or height_px < 0:
        raise BEHTMLError(E_BEHTML_INVALID_Y_INDEX, f"height_px must be >= 0, got {height_px}")
    return max(1, round(height_px / BEHTML_RY_PX))


def behtml_core_validate_y_start(y_start: Any) -> bool:
    if isinstance(y_start, bool) or not isinstance(y_start, int) or y_start < 0:
        raise BEHTMLError(E_BEHTML_INVALID_Y_INDEX, f"y_start must be a non-negative integer, got {y_start!r}")
    return True


def behtml_core_y_span_to_px(y_span: int) -> int:
    if isinstance(y_span, bool) or not isinstance(y_span, int) or y_span < 1:
        raise BEHTMLError(E_BEHTML_INVALID_Y_SPAN, f"y_span must be a positive integer, got {y_span}")
    return y_span * BEHTML_RY_PX


def behtml_core_validate_quantization(actual_px: float, y_span: int,
                                      tolerance: float = BEHTML_QUANTIZATION_TOLERANCE) -> bool:
    expected_px = behtml_core_y_span_to_px(y_span)
    if abs(actual_px - expected_px) >= tolerance:
        raise BEHTMLError(E_BEHTML_MATRIX_SHATTERED,
                          f"actual_px={actual_px} deviates from {expected_px} (y_span={y_span})")
    return True


def behtml_core_control_padding_y(visual_height_px: float, y_span: int = 1) -> float:
    """Symmetric padding so a shorter control (e.g. 28px) still fills y_span * Ry."""
    footprint_px = behtml_core_y_span_to_px(y_span)
    gap = footprint_px - visual_height_px
    if gap < 0:
        raise BEHTMLError(E_BEHTML_MATRIX_SHATTERED,
                          f"visual_height_px={visual_height_px} exceeds footprint {footprint_px}")
    return gap / 2.0


# ---------------------------------------------------------------------------
# X axis
# ---------------------------------------------------------------------------
def behtml_core_validate_x_address(x_start: int, x_span: int = 1) -> bool:
    if isinstance(x_start, bool) or not isinstance(x_start, int) or not (0 <= x_start < BEHTML_X_LANES):
        raise BEHTMLError(E_BEHTML_INVALID_X_ADDRESS, f"x_start must be 0-{BEHTML_X_LANES - 1}, got {x_start}")
    if isinstance(x_span, bool) or not isinstance(x_span, int) or x_span < 1:
        raise BEHTMLError(E_BEHTML_X_SPAN_OVERFLOW, f"x_span must be a positive integer, got {x_span}")
    if x_start + x_span > BEHTML_X_LANES:
        raise BEHTMLError(E_BEHTML_X_SPAN_OVERFLOW,
                          f"x_start({x_start}) + x_span({x_span}) exceeds {BEHTML_X_LANES} lanes")
    return True


def behtml_core_x_span_to_percent(x_span: int) -> float:
    return round(x_span * BEHTML_X_QUANTUM_PCT, 4)


def behtml_core_percent_to_x_span(percent: float) -> int:
    return max(1, round(percent / BEHTML_X_QUANTUM_PCT))


# ---------------------------------------------------------------------------
# Z axis: depth math
# ---------------------------------------------------------------------------
def behtml_core_z_validate(z_layer: Any, z_half: Any = False, max_layer: int = BEHTML_Z_MAX_LAYER) -> bool:
    """Hard check: z_layer is an int in 0..max_layer, z_half is a bool."""
    if isinstance(z_layer, bool) or not isinstance(z_layer, int) or z_layer < 0 or z_layer > max_layer:
        raise BEHTMLError(E_BEHTML_Z_INVALID_DEPTH, f"z_layer must be an integer 0-{max_layer}, got {z_layer!r}")
    if not isinstance(z_half, bool):
        raise BEHTMLError(E_BEHTML_Z_INVALID_DEPTH, f"z_half must be a boolean, got {z_half!r}")
    return True


def behtml_core_z_depth_px(z_layer: int, z_half: bool = False) -> int:
    """Depth in px: n*32, or n*32+16 for a half-layer."""
    behtml_core_z_validate(z_layer, z_half, max_layer=10 ** 6)
    return z_layer * BEHTML_RZ_PX + (BEHTML_RZ_HALF_PX if z_half else 0)


def behtml_core_z_from_depth_px(depth_px: int) -> Tuple[int, bool]:
    """Inverse of z_depth_px. Depth must sit on the 16px grid."""
    if isinstance(depth_px, bool) or not isinstance(depth_px, int) or depth_px < 0 or depth_px % BEHTML_RZ_HALF_PX:
        raise BEHTMLError(E_BEHTML_Z_INVALID_DEPTH, f"depth_px must be a non-negative multiple of 16, got {depth_px!r}")
    return depth_px // BEHTML_RZ_PX, bool(depth_px % BEHTML_RZ_PX)


def behtml_core_z_index(z_layer: int, z_half: bool = False) -> int:
    """CSS z-index. Equals the depth in px, so the layer is readable from the CSS."""
    return behtml_core_z_depth_px(z_layer, z_half)


def behtml_core_z_css(z_layer: int, z_half: bool = False, three_d: bool = False) -> str:
    """Inline CSS for a layer. three_d=True (optional) adds a real translateZ."""
    depth = behtml_core_z_depth_px(z_layer, z_half)
    css = f"z-index:{depth};"
    if three_d:
        css += f"transform:translateZ({depth}px);"
    return css


def behtml_core_z_scrim_slot(z_layer: int) -> Tuple[int, bool]:
    """(layer, half) that sits one half-layer below a full layer: where its scrim goes."""
    if isinstance(z_layer, bool) or not isinstance(z_layer, int) or z_layer < 1:
        raise BEHTMLError(E_BEHTML_Z_INVALID_DEPTH, f"a scrim needs z_layer >= 1, got {z_layer!r}")
    return z_layer - 1, True


# ---------------------------------------------------------------------------
# Z axis: standard layer table (data -- edit freely)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ZLayerSpec:
    layer: int
    name: str
    description: str


BEHTML_Z_LAYERS: Tuple[ZLayerSpec, ...] = (
    ZLayerSpec(0, "ground", "App/site background, canvas, wallpaper"),
    ZLayerSpec(1, "surface", "Cards, body sections, panels, tables, media"),
    ZLayerSpec(2, "control", "Buttons, inputs, tabs, toggles, links"),
    ZLayerSpec(3, "chrome", "Docked header, sidebar nav, toolbar, footer"),
    ZLayerSpec(4, "overlay", "Dialogs, drawers, dropdowns, popovers"),
    ZLayerSpec(5, "transient", "Toasts, tooltips, context menus, drag ghost"),
    ZLayerSpec(6, "system", "Reserved: system alerts, debug overlays"),
)


def behtml_core_layer_name(z_layer: int) -> str:
    for spec in BEHTML_Z_LAYERS:
        if spec.layer == z_layer:
            return spec.name
    return f"z{z_layer}"


@dataclass(frozen=True)
class ZTypeRule:
    """Where an element_type may live: default placement and allowed (min, max) full layer."""
    default_layer: int
    min_layer: int
    max_layer: int


def _make_z_type_rule(default: int, low: int, high: int) -> ZTypeRule:
    return ZTypeRule(default, low, high)


BEHTML_Z_TYPE_RULES: Dict[str, ZTypeRule] = {
    # ground
    "page": _make_z_type_rule(0, 0, 0), "background": _make_z_type_rule(0, 0, 0), "canvas": _make_z_type_rule(0, 0, 0),
    # surface (containers may nest upward inside overlays)
    "card": _make_z_type_rule(1, 1, 5), "panel": _make_z_type_rule(1, 1, 5), "section": _make_z_type_rule(1, 1, 5), "table": _make_z_type_rule(1, 1, 5),
    "media": _make_z_type_rule(1, 1, 5), "image": _make_z_type_rule(1, 1, 5), "container": _make_z_type_rule(1, 1, 5), "grid_cell": _make_z_type_rule(1, 1, 5),
    # control (a control inside an overlay rises with it)
    "input": _make_z_type_rule(2, 2, 5), "textarea": _make_z_type_rule(2, 2, 5), "button": _make_z_type_rule(2, 2, 5), "combobox": _make_z_type_rule(2, 2, 5),
    "checkbox": _make_z_type_rule(2, 2, 5), "radio": _make_z_type_rule(2, 2, 5), "toggle": _make_z_type_rule(2, 2, 5), "tab": _make_z_type_rule(2, 2, 5),
    "link": _make_z_type_rule(2, 2, 5), "label": _make_z_type_rule(1, 1, 5),
    # chrome
    "header": _make_z_type_rule(3, 3, 3), "sidebar": _make_z_type_rule(3, 3, 3), "toolbar": _make_z_type_rule(3, 3, 3),
    "footer": _make_z_type_rule(3, 3, 3), "hamburger_menu": _make_z_type_rule(3, 3, 3),
    # overlay
    "dialog": _make_z_type_rule(4, 4, 5), "modal": _make_z_type_rule(4, 4, 5), "drawer": _make_z_type_rule(4, 4, 5),
    "dropdown": _make_z_type_rule(4, 4, 5), "popover": _make_z_type_rule(4, 4, 5),
    # transient
    "toast": _make_z_type_rule(5, 5, 6), "tooltip": _make_z_type_rule(5, 5, 6), "context_menu": _make_z_type_rule(5, 5, 6),
}

# Element types allowed on a half-layer (attachment layer).
BEHTML_Z_HALF_TYPES = frozenset({
    "scrim", "shadow", "focus_ring", "resize_handle", "reveal_control", "ide_control", "drag_handle",
})
BEHTML_MODAL_TYPES = frozenset({"dialog", "modal", "drawer"})
BEHTML_CHROME_TYPES = frozenset({"header", "sidebar", "toolbar", "footer", "hamburger_menu"})
BEHTML_SCRIM_TYPE = "scrim"


# ---------------------------------------------------------------------------
# Z axis: rule policy (every rule hard / soft / off)
# ---------------------------------------------------------------------------
SEVERITY_HARD = "hard"
SEVERITY_SOFT = "soft"
SEVERITY_OFF = "off"
_SEVERITIES = (SEVERITY_HARD, SEVERITY_SOFT, SEVERITY_OFF)

# rule id -> (code constant, default severity)
BEHTML_Z_RULES: Dict[str, Tuple[int, str]] = {
    "invalid_depth":    (E_BEHTML_Z_INVALID_DEPTH, SEVERITY_HARD),
    "layer_collision":  (E_BEHTML_Z_LAYER_COLLISION, SEVERITY_HARD),
    "nesting_not_above": (W_BEHTML_Z_NESTING_NOT_ABOVE, SEVERITY_SOFT),
    "semantic_mismatch": (W_BEHTML_Z_SEMANTIC_MISMATCH, SEVERITY_SOFT),
    "skipped_layer":    (W_BEHTML_Z_SKIPPED_LAYER, SEVERITY_SOFT),
    "missing_scrim":    (W_BEHTML_Z_MISSING_SCRIM, SEVERITY_SOFT),
    "layer_crowded":    (W_BEHTML_Z_LAYER_CROWDED, SEVERITY_SOFT),
    "half_content_mismatch": (W_BEHTML_Z_HALF_CONTENT_MISMATCH, SEVERITY_SOFT),
    "chrome_scrolls":   (W_BEHTML_Z_CHROME_SCROLLS, SEVERITY_SOFT),
}


@dataclass
class ZPolicy:
    """Resolved Z rule set. Build with behtml_core_build_z_policy()."""
    severity: Dict[str, str] = field(default_factory=dict)
    crowd_limit: int = 64
    max_layer: int = BEHTML_Z_MAX_LAYER
    type_rules: Dict[str, ZTypeRule] = field(default_factory=dict)
    half_types: frozenset = BEHTML_Z_HALF_TYPES

    def level(self, rule_id: str) -> str:
        return self.severity.get(rule_id, SEVERITY_OFF)


def behtml_core_build_z_policy(overrides: Optional[Dict[str, Any]] = None) -> ZPolicy:
    """
    Merge optional overrides onto the defaults. Accepted keys:
      severity:    {rule_id: "hard"|"soft"|"off"}
      crowd_limit: int
      max_layer:   int
      type_rules:  {element_type: [default, min, max]}   (adds or replaces)
      half_types:  [element_type, ...]                   (replaces the set)
    Unknown keys or rule ids raise ValueError so a typo never silently disables a rule.
    """
    overrides = overrides or {}
    unknown = set(overrides) - {"severity", "crowd_limit", "max_layer", "type_rules", "half_types"}
    if unknown:
        raise ValueError(f"unknown Z policy keys: {sorted(unknown)}")
    policy = ZPolicy(
        severity={rid: sev for rid, (_code, sev) in BEHTML_Z_RULES.items()},
        type_rules=dict(BEHTML_Z_TYPE_RULES),
    )
    for rid, sev in (overrides.get("severity") or {}).items():
        if rid not in BEHTML_Z_RULES:
            raise ValueError(f"unknown Z rule id: {rid!r}")
        if sev not in _SEVERITIES:
            raise ValueError(f"severity for {rid!r} must be one of {_SEVERITIES}, got {sev!r}")
        policy.severity[rid] = sev
    if "crowd_limit" in overrides:
        policy.crowd_limit = int(overrides["crowd_limit"])
    if "max_layer" in overrides:
        policy.max_layer = int(overrides["max_layer"])
    for etype, triple in (overrides.get("type_rules") or {}).items():
        policy.type_rules[etype] = ZTypeRule(*[int(v) for v in triple])
    if "half_types" in overrides:
        policy.half_types = frozenset(overrides["half_types"])
    return policy


def behtml_core_load_z_policy(path: str) -> ZPolicy:
    """Load overrides from a JSON file path supplied by the caller (never hardcoded)."""
    with open(path, "r", encoding="utf-8") as handle:
        return behtml_core_build_z_policy(json.load(handle))


def behtml_core_default_layer(element_type: str, policy: Optional[ZPolicy] = None) -> int:
    """Standard layer for an element_type (Z1 surface when the type is unknown)."""
    rules = (policy or behtml_core_build_z_policy()).type_rules
    rule = rules.get(element_type)
    return rule.default_layer if rule else 1


# ---------------------------------------------------------------------------
# Z axis: collision (same scope, same depth, overlapping cells)
# ---------------------------------------------------------------------------
def behtml_core_rects_overlap(x1: int, xs1: int, y1: int, ys1: int,
                              x2: int, xs2: int, y2: int, ys2: int) -> bool:
    return (x1 < x2 + xs2 and x2 < x1 + xs1) and (y1 < y2 + ys2 and y2 < y1 + ys1)


def behtml_core_z_collides(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """
    True when two element dicts share a parent scope and a Z depth and overlap in X/Y.
    Elements on different depths may overlap freely: that is what layers are for.
    """
    if a.get("parent_id_fk") != b.get("parent_id_fk"):
        return False
    if behtml_core_z_depth_px(a["z_layer"], a["z_half"]) != behtml_core_z_depth_px(b["z_layer"], b["z_half"]):
        return False
    return behtml_core_rects_overlap(a["x_start"], a["x_span"], a["y_start"], a["y_span"],
                                     b["x_start"], b["x_span"], b["y_start"], b["y_span"])


def behtml_core_assert_z_free(doc: Dict[str, Any], candidate: Dict[str, Any],
                              exclude_element_id: Optional[str] = None) -> bool:
    """Raise E_BEHTML_Z_LAYER_COLLISION if candidate collides with an existing element."""
    for row in doc.get("Values", []):
        other = behtml_core_row_to_dict(doc, row)
        if other.get("element_id") == exclude_element_id:
            continue
        if behtml_core_z_collides(candidate, other):
            raise BEHTMLError(E_BEHTML_Z_LAYER_COLLISION,
                              f"candidate collides with {other.get('element_id')!r} on the same layer")
    return True


# ---------------------------------------------------------------------------
# BEM + palette
# ---------------------------------------------------------------------------
_BEM_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _validate_bem_token(token: str, label: str) -> None:
    if not token or not _BEM_TOKEN_RE.match(token):
        raise BEHTMLError(E_BEHTML_INVALID_BEM_MODIFIER,
                          f"{label} '{token}' fails BEM grammar (lowercase, digits, hyphens only)")


def behtml_core_bem_class(block: str, element: Optional[str] = None, modifier: Optional[str] = None) -> str:
    """behtml_core_bem_class('grid','cell','w-50') -> 'behtml-grid__cell--w-50'."""
    _validate_bem_token(block, "block")
    cls = f"behtml-{block}"
    if element:
        _validate_bem_token(element, "element")
        cls += f"__{element}"
    if modifier:
        _validate_bem_token(modifier, "modifier")
        cls += f"--{modifier}"
    return cls


def behtml_core_grid_cell_classes(x_start: int, x_span: int, y_span: int = 1, active: bool = False) -> List[str]:
    behtml_core_validate_x_address(x_start, x_span)
    pct_slug = str(behtml_core_x_span_to_percent(x_span)).replace(".0", "").replace(".", "-")
    classes = [
        behtml_core_bem_class("grid", "cell"),
        behtml_core_bem_class("grid", "cell", f"w-{pct_slug}"),
        behtml_core_bem_class("grid", "row", f"{y_span}r"),
    ]
    if active:
        classes.append(behtml_core_bem_class("grid", "cell", "active-column"))
    return classes


def behtml_core_validate_contrast(font_color: str, background_color: str) -> bool:
    """First Law: black font on #DE2626 is prohibited."""
    if (background_color or "").upper() == BEHTML_COLOR_ACCENT and (font_color or "").upper() == BEHTML_COLOR_BLACK:
        raise BEHTMLError(E_BEHTML_PALETTE_VIOLATION, "Black font on #DE2626 violates the First Law of Palette")
    return True


# ---------------------------------------------------------------------------
# Element helpers (field-map access only)
# ---------------------------------------------------------------------------
def behtml_core_row_to_dict(doc: Dict[str, Any], row: List[Any]) -> Dict[str, Any]:
    """Row -> {field_name: value} through the Core field map (no positional indices)."""
    field_map = bejson_core_get_field_map(doc)
    return {name: row[pos] for name, pos in field_map.items()}


def behtml_core_add_element(doc: Dict[str, Any], element_id: str, element_type: str,
                            y_start: int, x_start: int, x_span: int = 1, y_span: int = 1,
                            z_layer: Optional[int] = None, z_half: bool = False,
                            bem_modifiers: Optional[str] = None, content_ref: Optional[str] = None,
                            parent_id_fk: Optional[str] = None, is_active: bool = False,
                            content_kind: str = "text", policy: Optional[ZPolicy] = None,
                            check_collision: bool = True) -> str:
    """
    Append one element. z_layer defaults to the standard layer for element_type.
    Hard checks (depth, X/Y address, Z collision) run before the write; soft rules
    are the validator's job. Returns the new record_uuid.
    """
    policy = policy or behtml_core_build_z_policy()
    if z_layer is None:
        z_layer = behtml_core_default_layer(element_type, policy)
    behtml_core_z_validate(z_layer, z_half, policy.max_layer)
    behtml_core_validate_x_address(x_start, x_span)
    behtml_core_validate_y_start(y_start)
    behtml_core_y_span_to_px(y_span)
    values_by_name = {
        "element_id": element_id, "element_type": element_type,
        "y_start": y_start, "y_span": y_span, "x_start": x_start, "x_span": x_span,
        "z_layer": z_layer, "z_half": z_half, "bem_modifiers": bem_modifiers,
        "content_ref": content_ref, "parent_id_fk": parent_id_fk,
        "is_active": is_active, "content_kind": content_kind,
    }
    if check_collision and policy.level("layer_collision") != SEVERITY_OFF:
        behtml_core_assert_z_free(doc, values_by_name)
    ordered = [values_by_name[name] for name in behtml_schema_field_names()]
    return bejson_core_add_record_105(doc, ordered)


def _find_element_row(doc: Dict[str, Any], element_id: str) -> Tuple[Dict[str, int], int, List[Any]]:
    field_map = bejson_core_get_field_map(doc)
    eid_col = field_map["element_id"]
    for idx, row in enumerate(doc.get("Values", [])):
        if row[eid_col] == element_id:
            return field_map, idx, row
    raise BEHTMLError(E_BEHTML_ELEMENT_NOT_FOUND, f"element_id '{element_id}' not found")


def behtml_core_get_element(doc: Dict[str, Any], element_id: str) -> Dict[str, Any]:
    """Return one element dict by element_id or raise E_BEHTML_ELEMENT_NOT_FOUND."""
    _fm, _idx, row = _find_element_row(doc, element_id)
    return behtml_core_row_to_dict(doc, row)


def behtml_core_list_elements(doc: Dict[str, Any], parent_id_fk: Optional[str] = None,
                              z_layer: Optional[int] = None, filter_parent: bool = False) -> List[Dict[str, Any]]:
    """Return element dicts, optionally filtered by parent_id_fk and/or z_layer."""
    result: List[Dict[str, Any]] = []
    for row in doc.get("Values", []):
        el = behtml_core_row_to_dict(doc, row)
        if filter_parent and el.get("parent_id_fk") != parent_id_fk:
            continue
        if z_layer is not None and el.get("z_layer") != z_layer:
            continue
        result.append(el)
    return result


def behtml_core_update_element(doc: Dict[str, Any], element_id: str, policy: Optional[ZPolicy] = None,
                               check_collision: bool = True, **updates: Any) -> Dict[str, Any]:
    """Update fields on an existing element via the Core field map with X/Y/Z re-validation."""
    policy = policy or behtml_core_build_z_policy()
    field_map, _idx, row = _find_element_row(doc, element_id)
    candidate = {name: row[pos] for name, pos in field_map.items()}
    for key, val in updates.items():
        if key not in field_map or key == "record_uuid":
            raise ValueError(f"invalid update field: {key!r}")
        candidate[key] = val
    behtml_core_z_validate(candidate["z_layer"], candidate["z_half"], policy.max_layer)
    behtml_core_validate_x_address(candidate["x_start"], candidate["x_span"])
    behtml_core_validate_y_start(candidate["y_start"])
    behtml_core_y_span_to_px(candidate["y_span"])
    if check_collision and policy.level("layer_collision") != SEVERITY_OFF:
        behtml_core_assert_z_free(doc, candidate, exclude_element_id=element_id)
    for key, val in updates.items():
        row[field_map[key]] = val
    return candidate


def behtml_core_delete_element(doc: Dict[str, Any], element_id: str, cascade: bool = False) -> int:
    """Delete an element (and optionally its descendants) via 105 Core record_uuid. Returns count deleted."""
    field_map, _idx, row = _find_element_row(doc, element_id)
    uuid_col = field_map.get("record_uuid", 0)
    to_delete = [row[uuid_col]]
    if cascade:
        target_ids = {element_id}
        changed = True
        while changed:
            changed = False
            for r in doc.get("Values", []):
                r_el = behtml_core_row_to_dict(doc, r)
                if r_el.get("parent_id_fk") in target_ids and r_el.get("element_id") not in target_ids:
                    target_ids.add(r_el["element_id"])
                    to_delete.append(r[uuid_col])
                    changed = True
    for rec_uuid in to_delete:
        bejson_core_delete_record(doc, rec_uuid)
    return len(to_delete)

