"""
File Name : lib_bejson_Taxonomies_registry.py
Rel. Path : Lib_PY/Taxonomies/lib_bejson_Taxonomies_registry.py
Purpose   : Taxonomies REGISTRY: the public field-set API (define, version, retire, list, export, import, entities_with_set, resolve_member, read_set_rows).
VERSION   : 3.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : 0a201f4f-ed84-4067-960c-c47b7cdcc8b6
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Optional

# Sibling family directories (Lib_PY/Core, Lib_PY/Taxonomies, Lib_PY/Tax_Scaffolds) resolve relative to this file; nothing is hardcoded.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _fam in ('Taxonomies',):
    _p = os.path.normpath(os.path.join(_HERE, "..", _fam))
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import lib_bejson_Taxonomies_core as txc
from lib_bejson_Core_bejson_core import bejson_core_get_field_map  # noqa: E402
from lib_bejson_Core_mfdb_core import mfdb_core_get_entity_doc  # noqa: E402

logger = logging.getLogger(__name__)
VERSION = "3.0.0"

# ---------------------------------------------------------------------------
# Reads: sets
# ---------------------------------------------------------------------------
def bejson_taxonomies_list_field_sets(manifest_path: str, set_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """Every registered set version (optionally one key), with ordered members, sorted by key then version."""
    members: Dict[str, List[Dict[str, Any]]] = {}
    for m in txc.read_rows(manifest_path, txc.E_SETMEMBER):
        members.setdefault(m[txc.SM_SET], []).append(
            {"member_uuid": m["record_uuid"], "descriptor": m[txc.SM_DESCRIPTOR], "suffix": m[txc.SM_SUFFIX],
             "field_type": m[txc.SM_TYPE], "order": m[txc.SM_ORDER]})
    out = []
    for r in txc.read_rows(manifest_path, txc.E_FIELDSET):
        if set_key is not None and r[txc.FS_KEY] != set_key:
            continue
        ms = sorted(members.get(r["record_uuid"], []), key=lambda x: x["order"])
        out.append({"set_uuid": r["record_uuid"], "set_key": r[txc.FS_KEY], "display_name": r[txc.FS_NAME],
                    "version": r[txc.FS_VERSION], "state": r[txc.FS_STATE], "created_timestamp": r[txc.FS_CREATED],
                    "members": ms, "content_hash": txc.bejson_taxonomies_core_content_hash(ms)})
    return sorted(out, key=lambda x: (x["set_key"], x["version"]))
def bejson_taxonomies_get_field_set(manifest_path: str, set_ref: str, version: Optional[int] = None) -> Dict[str, Any]:
    """By set_key (latest version unless `version` is given) or by a set row's uuid."""
    sets = bejson_taxonomies_list_field_sets(manifest_path)
    by_uuid = next((s for s in sets if s["set_uuid"] == set_ref), None)
    if by_uuid is not None:
        return by_uuid
    versions = [s for s in sets if s["set_key"] == set_ref]
    if not versions:
        raise txc.TaxonomyError(f"field set {set_ref!r} not found", "E_FIELDSET_NOT_FOUND")
    if version is None:
        return versions[-1]
    for s in versions:
        if s["version"] == version:
            return s
    raise txc.TaxonomyError(f"field set {set_ref!r} has no version {version}", "E_FIELDSET_NOT_FOUND")
def _grafts(manifest_path: str, set_key: Optional[str] = None, entity_name: Optional[str] = None) -> List[Dict[str, Any]]:
    set_rows = {r["record_uuid"]: r for r in txc.read_rows(manifest_path, txc.E_FIELDSET)}
    out = []
    for g in txc.read_rows(manifest_path, txc.E_GRAFT):
        s = set_rows.get(g[txc.GR_SET])
        if s is None or (set_key is not None and s[txc.FS_KEY] != set_key):
            continue
        if entity_name is not None and g[txc.GR_ENTITY] != entity_name:
            continue
        out.append({"graft_uuid": g["record_uuid"], "graft_key": g[txc.GR_KEY], "set_key": s[txc.FS_KEY],
                    "set_version": s[txc.FS_VERSION], "set_uuid": g[txc.GR_SET], "entity_name": g[txc.GR_ENTITY],
                    "subject": g[txc.GR_SUBJECT], "taxonomy_uuid": g[txc.GR_TAXONOMY], "applied_timestamp": g[txc.GR_APPLIED]})
    return out
def bejson_taxonomies_list_grafts(manifest_path: str, set_key: Optional[str] = None,
                                  entity_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Grafts (a set stamped on an entity), optionally filtered by set key and/or entity."""
    return _grafts(manifest_path, set_key, entity_name)
# ---------------------------------------------------------------------------
# Writes: define / version / retire
# ---------------------------------------------------------------------------
def bejson_taxonomies_define_field_set(
    manifest_path: str, set_key: str, members: List[Dict[str, Any]], display_name: str = "",
) -> str:
    """Register version 1 of a new field set. members: [{"descriptor", "suffix", "field_type"}, ...] in order."""
    if any(s["set_key"] == set_key for s in bejson_taxonomies_list_field_sets(manifest_path)):
        raise txc.TaxonomyError(f"field set {set_key!r} already exists; use new_version", "E_FIELDSET_EXISTS")
    return txc.bejson_taxonomies_core_register_field_set(manifest_path, set_key, display_name, 1, members)
def bejson_taxonomies_new_version(
    manifest_path: str, set_key: str, add_members: List[Dict[str, Any]], display_name: Optional[str] = None,
) -> str:
    """Register the next version: every member of the latest version plus `add_members` (appended).
    Versions are additive, so existing grafts stay valid."""
    latest = bejson_taxonomies_get_field_set(manifest_path, set_key)
    if latest["state"] != "active":
        raise txc.TaxonomyError(f"field set {set_key!r} is retired", "E_FIELDSET_RETIRED")
    have = {m["descriptor"] for m in latest["members"]}
    clash = sorted(m.get("descriptor") for m in add_members if m.get("descriptor") in have)
    if clash:
        raise txc.TaxonomyError(f"members already in {set_key} v{latest['version']}: {clash}", "E_FIELDSET_MEMBER_EXISTS")
    if not add_members:
        raise txc.TaxonomyError("add_members is empty; nothing to version", "E_FIELDSET_EMPTY")
    carried = [{"descriptor": m["descriptor"], "suffix": m["suffix"], "field_type": m["field_type"]} for m in latest["members"]]
    return txc.bejson_taxonomies_core_register_field_set(
        manifest_path, set_key, display_name or latest["display_name"], latest["version"] + 1, carried + list(add_members))
def bejson_taxonomies_retire_field_set(manifest_path: str, set_key: str) -> int:
    """Retire every version of a set. Refused while any entity still carries it. Returns versions retired."""
    sets = [s for s in bejson_taxonomies_list_field_sets(manifest_path, set_key)]
    if not sets:
        raise txc.TaxonomyError(f"field set {set_key!r} not found", "E_FIELDSET_NOT_FOUND")
    grafted = _grafts(manifest_path, set_key)
    if grafted:
        raise txc.TaxonomyError(f"field set {set_key!r} is grafted on {[g['entity_name'] for g in grafted]}", "E_FIELDSET_IN_USE")
    for s in sets:
        txc.bejson_taxonomies_core_set_state(manifest_path, s["set_uuid"], "retired")
    return len(sets)
# ---------------------------------------------------------------------------
# Export / import (BEJSON 104a definition files)
# ---------------------------------------------------------------------------
def bejson_taxonomies_export_field_set(
    manifest_path: str, set_ref: str, path: str, version: Optional[int] = None, overwrite: bool = False,
) -> str:
    s = bejson_taxonomies_get_field_set(manifest_path, set_ref, version)
    doc = txc.bejson_taxonomies_core_build_definition_doc(s["set_key"], s["display_name"], s["version"], s["members"])
    return txc.bejson_taxonomies_core_write_definition(path, doc, overwrite=overwrite)
def bejson_taxonomies_import_field_set(manifest_path: str, path: str) -> str:
    """Register a definition file. Same (set_key, version) already present: idempotent when the content hash
    matches, E_FIELDSET_CONFLICT when it differs. A new version needs the previous one present and kept in full.
    Returns the set row uuid."""
    d = txc.bejson_taxonomies_core_read_definition(path)
    existing = bejson_taxonomies_list_field_sets(manifest_path, d["set_key"])
    same = next((s for s in existing if s["version"] == d["version"]), None)
    new_hash = txc.bejson_taxonomies_core_content_hash(d["members"])
    if same is not None:
        if same["content_hash"] != new_hash:
            raise txc.TaxonomyError(
                f"field set {d['set_key']} v{d['version']} exists here with different content (hash mismatch)", "E_FIELDSET_CONFLICT")
        return same["set_uuid"]
    latest = existing[-1]["version"] if existing else 0
    if d["version"] != latest + 1:
        raise txc.TaxonomyError(
            f"field set {d['set_key']}: file is v{d['version']} but this registry holds up to v{latest}; import v{latest + 1} first", "E_FIELDSET_VERSION")
    if existing:
        prev = {(m["descriptor"], m["suffix"], m["field_type"]) for m in existing[-1]["members"]}
        if not prev <= {(m["descriptor"], m["suffix"], m["field_type"]) for m in d["members"]}:
            raise txc.TaxonomyError(f"field set {d['set_key']} v{d['version']} does not keep every member of v{latest}", "E_FIELDSET_VERSION")
    return txc.bejson_taxonomies_core_register_field_set(manifest_path, d["set_key"], d["display_name"], d["version"], d["members"])
# ---------------------------------------------------------------------------
# Reads across entities
# ---------------------------------------------------------------------------
def bejson_taxonomies_entities_with_set(manifest_path: str, set_key: str) -> List[Dict[str, Any]]:
    """Every entity that carries the set: [{entity_name, subject, set_version, graft_uuid, taxonomy_uuid}]."""
    return [{k: g[k] for k in ("entity_name", "subject", "set_version", "graft_uuid", "taxonomy_uuid")}
            for g in _grafts(manifest_path, set_key)]
def _member_columns(manifest_path: str, entity_name: str, set_key: str) -> Dict[str, Dict[str, Any]]:
    """descriptor -> {field_uuid, field_name, field_type, suffix} for the live (active) grafted columns."""
    graft = next(iter(_grafts(manifest_path, set_key, entity_name)), None)
    if graft is None:
        raise txc.TaxonomyError(f"{entity_name} does not carry field set {set_key!r}", "E_GRAFT_NOT_FOUND")
    members = {m["record_uuid"]: m for m in txc.read_rows(manifest_path, txc.E_SETMEMBER)}
    out: Dict[str, Dict[str, Any]] = {}
    doc = mfdb_core_get_entity_doc(manifest_path, entity_name)
    by_uuid = {f["field_uuid"]: f for f in doc["Fields"]}
    for row in txc.read_rows(manifest_path, txc.E_FIELD):
        if row[txc.FE_GRAFT] != graft["graft_uuid"] or row[txc.FE_LIFECYCLE] != txc.LIFECYCLE_ACTIVE:
            continue
        m = members.get(row[txc.FE_SETMEMBER])
        f = by_uuid.get(row[txc.FE_UUID])
        if m is not None and f is not None:
            out[m[txc.SM_DESCRIPTOR]] = {"field_uuid": f["field_uuid"], "field_name": f["name"],
                                        "field_type": f["type"], "suffix": m[txc.SM_SUFFIX]}
    return out
def bejson_taxonomies_member_columns(manifest_path: str, entity_name: str, set_key: str) -> Dict[str, Dict[str, Any]]:
    """descriptor -> {field_uuid, field_name, field_type, suffix} for every live column the set contributed."""
    return _member_columns(manifest_path, entity_name, set_key)
def bejson_taxonomies_resolve_member(manifest_path: str, entity_name: str, set_key: str, descriptor: str) -> Dict[str, Any]:
    """The live column behind a set member on one entity. Rename-proof: the ledger holds the field_uuid."""
    cols = _member_columns(manifest_path, entity_name, set_key)
    if descriptor not in cols:
        raise txc.TaxonomyError(f"{entity_name}: field set {set_key!r} has no active member {descriptor!r}", "E_MEMBER_NOT_FOUND")
    return dict(cols[descriptor])
def bejson_taxonomies_read_set_rows(
    manifest_path: str, entity_name: str, set_key: str, descriptors: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Rows of an entity keyed by set descriptor (plus record_uuid): the same call works on every entity
    that carries the set, whatever its prefix or subject."""
    cols = _member_columns(manifest_path, entity_name, set_key)
    wanted = list(cols) if descriptors is None else descriptors
    unknown = [d for d in wanted if d not in cols]
    if unknown:
        raise txc.TaxonomyError(f"{entity_name}: field set {set_key!r} has no active member(s) {unknown}", "E_MEMBER_NOT_FOUND")
    doc = mfdb_core_get_entity_doc(manifest_path, entity_name)
    fmap = bejson_core_get_field_map(doc)
    out = []
    for row in doc["Values"]:
        item = {d: row[fmap[cols[d]["field_name"]]] for d in wanted}
        item["record_uuid"] = row[0]
        out.append(item)
    return out
