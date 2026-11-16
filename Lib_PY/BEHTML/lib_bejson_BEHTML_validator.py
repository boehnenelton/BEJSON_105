"""
Library:         lib_bejson_BEHTML_validator.py
Family:          BEHTML
Module Purpose:  Anti-Drift Auditor for BEHTML 105 documents: structure, X/Y spatial laws and the Z layer rules, each rule hard, soft or off per policy.
Architecture:    BEHTML on BEJSON 105: one 105 table, one row per placed element, X0-X7 lanes, Ry=32px rows, Rz=32px layers; all field access via the Core field map.
Version:         1.0.0
Release_Version: 301
Date:            2026-11-13
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   6aa6c7f5-8e3f-4622-a1e3-9b6e7aacd1f0
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import lib_bejson_BEHTML_bootstrap  # noqa: F401 -- puts 105 Core on sys.path

try:
    from lib_bejson_Core_bejson_validator import validate_bejson
    from lib_bejson_BEHTML_bejson_errors import (
        E_BEHTML_DUPLICATE_ELEMENT_ID,
        E_BEHTML_INVALID_CONTENT_KIND,
        E_BEHTML_INVALID_ELEMENT_TYPE,
        E_BEHTML_INVALID_URL,
        E_BEHTML_MISSING_ELEMENT_ID,
        E_BEHTML_MISSING_FIELD_BINDING,
        E_BEHTML_NOT_BEJSON,
        E_BEHTML_PARENT_NOT_FOUND,
        E_BEHTML_SCHEMA_MISMATCH,
        behtml_errors_name_of,
    )
    from lib_bejson_BEHTML_bejson_schema import (
        BEHTML_ACCEPTED_FORMATS,
        BEHTML_ROOT_RECORDS_TYPE,
        KNOWN_CONTENT_KINDS,
        KNOWN_ELEMENT_TYPES,
    )
    from lib_bejson_BEHTML_core import (
        BEHTML_CHROME_TYPES,
        BEHTML_MODAL_TYPES,
        BEHTML_RZ_PX,
        BEHTML_RZ_HALF_PX,
        BEHTML_SCRIM_TYPE,
        BEHTML_Z_RULES,
        SEVERITY_HARD,
        SEVERITY_OFF,
        SEVERITY_SOFT,
        BEHTMLError,
        ZPolicy,
        behtml_core_build_z_policy,
        behtml_core_layer_name,
        behtml_core_row_to_dict,
        behtml_core_validate_x_address,
        behtml_core_validate_y_start,
        behtml_core_y_span_to_px,
        behtml_core_z_depth_px,
        behtml_core_z_validate,
    )
    from lib_bejson_Core_bejson_core import bejson_core_get_field_map
except ImportError as exc:
    logging.critical("[BEHTML_VALIDATOR] FATAL: dependency unreachable: %s", exc)
    raise SystemExit(1)

VERSION = "1.0.0"
_STRUCTURE_RULE = "structure"


@dataclass(frozen=True)
class Finding:
    """One audit result. severity is 'hard' (validate raises) or 'soft' (advisory)."""
    code: int
    name: str
    rule: str
    severity: str
    element_id: Optional[str]
    message: str

    def __str__(self) -> str:
        who = f" [{self.element_id}]" if self.element_id else ""
        return f"{self.severity.upper()} {self.name}({self.code}){who}: {self.message}"


def _finding(code: int, rule: str, severity: str, element_id: Optional[str], message: str) -> Finding:
    return Finding(code, behtml_errors_name_of(code), rule, severity, element_id, message)


def behtml_validator_validate_container(doc: Any, core_check: bool = True) -> None:
    """Hard container checks: dict, 105/105a, Records_Type, and (optionally) the 105 Core validator."""
    if not isinstance(doc, dict):
        raise BEHTMLError(E_BEHTML_NOT_BEJSON, "doc must be a dict")
    if doc.get("Format_Version") not in BEHTML_ACCEPTED_FORMATS:
        raise BEHTMLError(E_BEHTML_SCHEMA_MISMATCH,
                          f"Format_Version must be one of {BEHTML_ACCEPTED_FORMATS}, got {doc.get('Format_Version')!r}")
    if doc.get("Records_Type") != [BEHTML_ROOT_RECORDS_TYPE]:
        raise BEHTMLError(E_BEHTML_SCHEMA_MISMATCH,
                          f"Records_Type must be ['{BEHTML_ROOT_RECORDS_TYPE}'], got {doc.get('Records_Type')}")
    if core_check:
        result = validate_bejson(doc)
        if not getattr(result, "is_valid", getattr(result, "valid", False)):
            detail = getattr(result, "errors", None) or getattr(result, "error", None) or result
            raise BEHTMLError(E_BEHTML_SCHEMA_MISMATCH, f"Core 105 validation failed: {detail}")


def behtml_validator_audit_document(doc: Dict[str, Any], strict_types: bool = False,
                                    policy: Optional[ZPolicy] = None,
                                    core_check: bool = True) -> List[Finding]:
    """
    Collect every finding without raising on element-level faults. Container faults
    (not a dict, wrong format) still raise. Z rule severities come from the policy.
    """
    policy = policy or behtml_core_build_z_policy()
    behtml_validator_validate_container(doc, core_check=core_check)
    if not bejson_core_get_field_map(doc):
        raise BEHTMLError(E_BEHTML_SCHEMA_MISMATCH, "document has no Fields")

    findings: List[Finding] = []
    elements: Dict[str, Dict[str, Any]] = {}
    ordered: List[Dict[str, Any]] = []
    good_xy: Set[str] = set()
    good_z: Set[str] = set()

    def z_add(rule: str, element_id: Optional[str], message: str) -> None:
        level = policy.level(rule)
        if level != SEVERITY_OFF:
            findings.append(_finding(BEHTML_Z_RULES[rule][0], rule, level, element_id, message))

    # ---- Pass 1: per-row structure, X/Y, depth --------------------------------
    for row in doc.get("Values", []):
        el = behtml_core_row_to_dict(doc, row)
        eid = el.get("element_id")
        if not eid:
            findings.append(_finding(E_BEHTML_MISSING_ELEMENT_ID, _STRUCTURE_RULE, SEVERITY_HARD, None,
                                     f"record missing element_id: {el}"))
            continue
        if eid in elements:
            findings.append(_finding(E_BEHTML_DUPLICATE_ELEMENT_ID, _STRUCTURE_RULE, SEVERITY_HARD, eid,
                                     f"duplicate element_id: {eid}"))
            continue
        elements[eid] = el
        ordered.append(el)

        etype = el.get("element_type")
        if etype not in KNOWN_ELEMENT_TYPES:
            findings.append(_finding(E_BEHTML_INVALID_ELEMENT_TYPE, "element_type",
                                     SEVERITY_HARD if strict_types else SEVERITY_SOFT, eid,
                                     f"unrecognized element_type '{etype}'"))
        try:
            behtml_core_validate_x_address(el.get("x_start"), el.get("x_span"))
            behtml_core_y_span_to_px(el.get("y_span"))
            behtml_core_validate_y_start(el.get("y_start"))
            good_xy.add(eid)
        except BEHTMLError as exc:
            findings.append(_finding(exc.code, _STRUCTURE_RULE, SEVERITY_HARD, eid, exc.message))
        try:
            behtml_core_z_validate(el.get("z_layer"), el.get("z_half"), policy.max_layer)
            good_z.add(eid)
        except BEHTMLError as exc:
            z_add("invalid_depth", eid, exc.message)

        ckind = el.get("content_kind")
        cref = el.get("content_ref") or ""
        if ckind not in KNOWN_CONTENT_KINDS:
            findings.append(_finding(E_BEHTML_INVALID_CONTENT_KIND, _STRUCTURE_RULE, SEVERITY_HARD, eid,
                                     f"content_kind '{ckind}' not in {sorted(KNOWN_CONTENT_KINDS)}"))
        elif ckind == "url" and not (cref.startswith(("https://", "http://", "/")) and not cref.lower().startswith("javascript:")):
            findings.append(_finding(E_BEHTML_INVALID_URL, _STRUCTURE_RULE, SEVERITY_HARD, eid,
                                     f"content_kind='url' requires http(s):// or / path, got '{cref}'"))
        elif ckind == "field_binding" and not str(cref).strip():
            findings.append(_finding(E_BEHTML_MISSING_FIELD_BINDING, _STRUCTURE_RULE, SEVERITY_HARD, eid,
                                     "content_kind='field_binding' requires a non-empty content_ref"))

    # ---- Pass 2: parent references ---------------------------------------------
    for el in ordered:
        parent = el.get("parent_id_fk")
        if parent is not None and parent not in elements:
            findings.append(_finding(E_BEHTML_PARENT_NOT_FOUND, _STRUCTURE_RULE, SEVERITY_HARD, el["element_id"],
                                     f"parent_id_fk '{parent}' not found in document"))

    def depth_of(el: Dict[str, Any]) -> int:
        return behtml_core_z_depth_px(el["z_layer"], el["z_half"])

    # ---- Pass 3: Z rules ---------------------------------------------------------
    scrims: Set[Tuple[Optional[str], int]] = set()
    groups: Dict[Tuple[Optional[str], int], List[str]] = defaultdict(list)
    for el in ordered:
        if el["element_id"] in good_z:
            depth = depth_of(el)
            groups[(el.get("parent_id_fk"), depth)].append(el["element_id"])
            if el.get("element_type") == BEHTML_SCRIM_TYPE:
                scrims.add((el.get("parent_id_fk"), depth))

    for el in ordered:
        eid = el["element_id"]
        if eid not in good_z:
            continue
        etype = el.get("element_type")
        layer, half = el["z_layer"], el["z_half"]
        depth = depth_of(el)

        if half:
            if etype not in policy.half_types:
                z_add("half_content_mismatch", eid,
                      f"'{etype}' sits on half-layer {depth}px; half-layers hold attachments "
                      f"({', '.join(sorted(policy.half_types))})")
        else:
            if etype in policy.half_types:
                z_add("semantic_mismatch", eid,
                      f"attachment '{etype}' sits on full layer z{layer}; use a half-layer")
            rule = policy.type_rules.get(etype)
            if rule and not (rule.min_layer <= layer <= rule.max_layer):
                z_add("semantic_mismatch", eid,
                      f"'{etype}' is on z{layer} ({behtml_core_layer_name(layer)}); "
                      f"allowed z{rule.min_layer}-z{rule.max_layer}")

        parent = elements.get(el.get("parent_id_fk")) if el.get("parent_id_fk") else None
        if parent is not None and parent["element_id"] in good_z:
            gap = depth - depth_of(parent)
            if gap <= 0:
                z_add("nesting_not_above", eid,
                      f"depth {depth}px is not above container '{parent['element_id']}' ({depth_of(parent)}px)")
            elif not half and gap > BEHTML_RZ_PX:
                z_add("skipped_layer", eid,
                      f"{gap}px above container '{parent['element_id']}' skips "
                      f"{gap // BEHTML_RZ_PX - 1} layer(s)")

        if etype in BEHTML_MODAL_TYPES and not half and layer >= 1:
            if (el.get("parent_id_fk"), depth - BEHTML_RZ_HALF_PX) not in scrims:
                z_add("missing_scrim", eid,
                      f"'{etype}' at {depth}px has no scrim at {depth - BEHTML_RZ_HALF_PX}px")

        if etype in BEHTML_CHROME_TYPES:
            tokens = [t.strip() for t in (el.get("bem_modifiers") or "").split(",")]
            if "scroll" in tokens:
                z_add("chrome_scrolls", eid, f"docked chrome '{etype}' carries the 'scroll' modifier")

    for (scope, depth), ids in groups.items():
        if len(ids) > policy.crowd_limit:
            z_add("layer_crowded", None,
                  f"{len(ids)} elements at {depth}px in scope {scope!r} (limit {policy.crowd_limit})")

    # Same-scope, same-depth cell collisions (cell index, O(cells)).
    if policy.level("layer_collision") != SEVERITY_OFF:
        owners: Dict[Tuple[Optional[str], int, int, int], str] = {}
        reported: Set[Tuple[str, str]] = set()
        for el in ordered:
            eid = el["element_id"]
            if eid not in good_z or eid not in good_xy:
                continue
            scope, depth = el.get("parent_id_fk"), depth_of(el)
            for dx in range(el["x_span"]):
                for dy in range(el["y_span"]):
                    key = (scope, depth, el["x_start"] + dx, el["y_start"] + dy)
                    other = owners.setdefault(key, eid)
                    if other != eid:
                        pair = tuple(sorted((other, eid)))
                        if pair not in reported:
                            reported.add(pair)
                            z_add("layer_collision", eid,
                                  f"overlaps '{other}' on the same layer ({depth}px) at x={key[2]}, y={key[3]}")
    return findings


def behtml_validator_validate_document(doc: Dict[str, Any], strict_types: bool = False,
                                       policy: Optional[ZPolicy] = None,
                                       core_check: bool = True) -> List[Finding]:
    """
    Audit and enforce. Raises BEHTMLError for the first hard finding; returns the
    soft findings (warnings) otherwise.
    """
    findings = behtml_validator_audit_document(doc, strict_types=strict_types, policy=policy, core_check=core_check)
    for item in findings:
        if item.severity == SEVERITY_HARD:
            raise BEHTMLError(item.code, item.message)
    return findings


def behtml_validator_format_report(findings: List[Finding]) -> str:
    """Plain-text report: one line per finding plus a hard/soft tally."""
    hard = sum(1 for f in findings if f.severity == SEVERITY_HARD)
    soft = sum(1 for f in findings if f.severity == SEVERITY_SOFT)
    lines = [str(f) for f in findings] or ["clean"]
    lines.append(f"-- {hard} hard, {soft} soft")
    return "\n".join(lines)
