"""
File Name : lib_bejson_Scaffold_z_space_allocator.py
Rel. Path : Lib_PY/Scaffold/lib_bejson_Scaffold_z_space_allocator.py
Purpose   : Z-space = a trailing block of nullable, unbound `_slot` columns on an entity, reserved so a
            taxonomy-compliant value (e.g. a federation link UUID) can be bound later WITHOUT rewriting rows.
            reserve  -> append slot columns (field_uuid stamped by Core), ledger them, record the reservation.
            bind     -> rename a slot to its compliant name; field_uuid and column position never change.
            Slots are addressed by field_uuid, never by positional offset.
VERSION   : 1.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : a5d27c80-4e19-4f3b-b6a7-90c1e8d3f524
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
for _fam in ("Taxonomies", "Scaffold"):
    _p = os.path.normpath(os.path.join(_HERE, "..", _fam))
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import lib_bejson_Taxonomies_store as st  # noqa: E402
import lib_bejson_Taxonomies_taxonomy_registry as reg  # noqa: E402
import lib_bejson_Taxonomies_uuid_tracker as trk  # noqa: E402
from lib_bejson_Core_bejson_core import (  # noqa: E402
    bejson_core_define_field,
    bejson_core_get_field_map,
    bejson_core_load_file,
    bejson_core_remove_field,
    bejson_core_resolve_field_index,
    # Sanctioned by clarification.md §5.6 (owner grant): the ONE Core private helper these families may call.
    _bejson_core_invalidate_cache,
)
from lib_bejson_Core_mfdb_core import (  # noqa: E402
    mfdb_core_delete_entity_record_105,
    mfdb_core_update_entity_record_105,
)

logger = logging.getLogger(__name__)
VERSION = "1.0.0"
MAX_SLOTS_PER_CALL = 16


def bejson_scaffold_list_z_space(
    manifest_path: str, entity_name: Optional[str] = None, state_kind: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Reservations, lowest ordinal first, each with the slot's current column name (resolved by field_uuid)."""
    out: List[Dict[str, Any]] = []
    docs: Dict[str, dict] = {}
    for z in st.read_rows(manifest_path, st.E_ZSPACE):
        ent = z[st.ZS_ENTITY]
        if entity_name is not None and ent != entity_name:
            continue
        if state_kind is not None and z[st.ZS_STATE] != state_kind:
            continue
        if ent not in docs:
            docs[ent] = bejson_core_load_file(st.entity_path(manifest_path, ent))
        current = next((f["name"] for f in docs[ent]["Fields"] if f["field_uuid"] == z[st.ZS_FIELD_UUID]), None)
        out.append({"reservation_uuid": z["record_uuid"], "entity_name": ent,
                    "slot_field_uuid": z[st.ZS_FIELD_UUID], "ordinal": z[st.ZS_ORDINAL],
                    "state_kind": z[st.ZS_STATE], "bound_field_name": z[st.ZS_BOUND],
                    "current_field_name": current})
    return sorted(out, key=lambda r: (r["entity_name"], r["ordinal"]))


def bejson_scaffold_find_slot(
    manifest_path: str, entity_name: str, state_kind: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Lowest-ordinal reservation for an entity (optionally filtered by state), or None."""
    found = bejson_scaffold_list_z_space(manifest_path, entity_name, state_kind)
    return found[0] if found else None


def _rollback_reserve(manifest_path: str, entity_name: str, path: str, new_uuids: List[str],
                      ledger_uuids: List[str], zspace_uuids: List[str]) -> None:
    for zu in zspace_uuids:
        mfdb_core_delete_entity_record_105(manifest_path, st.E_ZSPACE, zu)
    for lu in ledger_uuids:
        mfdb_core_delete_entity_record_105(manifest_path, st.E_FIELD, lu)
    doc = bejson_core_load_file(path)
    for fuuid in new_uuids:
        bejson_core_remove_field(doc, fuuid)  # by field_uuid; Core drops the column from every row
    st.write_doc(doc, path)


def bejson_scaffold_reserve_z_space_slot(
    manifest_path: str, entity_name: str, taxonomy_ref: str, slot_count: int = 1,
    fk_target_entity: Optional[str] = None, fk_on_delete: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Append `slot_count` unbound slot columns to `entity_name` (named `<prefix>zspace_NN_reserved_slot`
    under `taxonomy_ref`), ledger them and record the reservations. Existing rows get null in each slot.
    FK metadata may be pre-set so binding later is a pure rename. All-or-nothing."""
    if not 1 <= slot_count <= MAX_SLOTS_PER_CALL:
        raise st.TaxonomyError(f"slot_count must be 1..{MAX_SLOTS_PER_CALL}", "E_ZSPACE_COUNT")
    taxonomy = reg.bejson_taxonomies_get_taxonomy(manifest_path, taxonomy_ref)
    path = st.entity_path(manifest_path, entity_name)
    ordinals = [z["ordinal"] for z in bejson_scaffold_list_z_space(manifest_path, entity_name)]
    next_ordinal = (max(ordinals) if ordinals else 0) + 1

    new_names: List[str] = []
    new_uuids: List[str] = []
    with st.entity_lock(path):
        doc = bejson_core_load_file(path)
        names = [f["name"] for f in doc["Fields"]]
        unbound = [i for i, n in enumerate(names) if n.endswith(st.SLOT_SUFFIX)]
        if unbound and unbound != list(range(len(names) - len(unbound), len(names))):
            raise st.TaxonomyError(f"{entity_name}: existing slots are not a trailing block", "E_ZSPACE_LAYOUT")
        for k in range(slot_count):
            name = f"{taxonomy['prefix_key']}zspace_{next_ordinal + k:02d}_reserved_slot"
            problems = reg.bejson_taxonomies_check_field_name(taxonomy, name, "string")
            if problems or name in names:
                raise st.TaxonomyComplianceError(f"cannot reserve slot {name!r}", problems or [f"{name!r} already exists"])
            new_names.append(name)
        for name in new_names:
            new_uuids.append(bejson_core_define_field(
                doc, name, "string", fk_target_entity=fk_target_entity, fk_on_delete=fk_on_delete))
        st.write_doc(doc, path)

    ledger_uuids: List[str] = []
    zspace_uuids: List[str] = []
    result: List[Dict[str, Any]] = []
    try:
        trk.bejson_taxonomies_track_fields(manifest_path, entity_name, taxonomy["taxonomy_uuid"], new_names)
        ledger_uuids = [trk.bejson_taxonomies_get_field_entry(manifest_path, entity_name, u)["ledger_record_uuid"]
                        for u in new_uuids]
        for k, (name, fuuid) in enumerate(zip(new_names, new_uuids)):
            zspace_uuids.append(st.add_row(manifest_path, st.E_ZSPACE, st.build_row(
                manifest_path, st.E_ZSPACE,
                **{st.ZS_ENTITY: entity_name, st.ZS_FIELD_UUID: fuuid, st.ZS_ORDINAL: next_ordinal + k,
                   st.ZS_STATE: st.ZSTATE_RESERVED, st.ZS_BOUND: None, st.ZS_ALLOCATED: st.now_utc()})))
            result.append({"slot_name": name, "slot_field_uuid": fuuid, "ordinal": next_ordinal + k,
                           "reservation_uuid": zspace_uuids[-1]})
    except Exception:
        logger.exception("reserve_z_space_slot failed for %s; rolling back", entity_name)
        with st.entity_lock(path):
            if not ledger_uuids:  # ledger step itself failed part-way: remove any rows it did add
                ledger_uuids = [r["record_uuid"] for r in st.read_rows(manifest_path, st.E_FIELD)
                                if r[st.FE_ENTITY] == entity_name and r[st.FE_UUID] in new_uuids]
            _rollback_reserve(manifest_path, entity_name, path, new_uuids, ledger_uuids, zspace_uuids)
        raise
    return result


def bejson_scaffold_bind_z_space_slot(
    manifest_path: str, entity_name: str, slot_field_uuid: str, bound_field_name: str,
) -> str:
    """Rename a reserved slot to `bound_field_name` (must comply with the slot's taxonomy and must not end in
    `_slot`; a slot with FK metadata must be bound to a `_uuid_fk` name). field_uuid and column position are
    unchanged and no row is rewritten. Returns the bound name."""
    reservation = next((z for z in bejson_scaffold_list_z_space(manifest_path, entity_name)
                        if z["slot_field_uuid"] == slot_field_uuid), None)
    if reservation is None:
        raise st.TaxonomyError(f"{entity_name}: no reservation for slot {slot_field_uuid!r}", "E_ZSPACE_NOT_FOUND")
    if reservation["state_kind"] != st.ZSTATE_RESERVED:
        raise st.TaxonomyError(f"{entity_name}.{reservation['current_field_name']} is already bound", "E_ZSPACE_ALREADY_BOUND")

    entry = trk.bejson_taxonomies_get_field_entry(manifest_path, entity_name, slot_field_uuid)
    taxonomy = reg.bejson_taxonomies_get_taxonomy(manifest_path, entry["taxonomy_uuid"])
    path = st.entity_path(manifest_path, entity_name)
    old_name = reservation["current_field_name"]

    with st.entity_lock(path):
        doc = bejson_core_load_file(path)
        fdef = next(f for f in doc["Fields"] if f["field_uuid"] == slot_field_uuid)
        problems = reg.bejson_taxonomies_check_field_name(taxonomy, bound_field_name, fdef["type"])
        if bound_field_name.endswith(st.SLOT_SUFFIX):
            problems.append(f"{bound_field_name!r}: a bound name must not end in {st.SLOT_SUFFIX}")
        if fdef.get("fk_target_entity") and not bound_field_name.endswith(st.FK_SUFFIX):
            problems.append(f"{bound_field_name!r}: slot carries FK metadata, so it must end in {st.FK_SUFFIX}")
        if any(f["name"] == bound_field_name for f in doc["Fields"]):
            problems.append(f"{bound_field_name!r}: already exists in {entity_name}")
        if problems:
            raise st.TaxonomyComplianceError(f"cannot bind slot to {bound_field_name!r}", problems)

        position_before = bejson_core_get_field_map(doc)[old_name]
        fdef["name"] = bound_field_name
        _bejson_core_invalidate_cache(doc)  # sanctioned helper: rebuild by_name/by_uuid/by_name_row
        position_after = bejson_core_resolve_field_index(doc, {"name": bound_field_name, "field_uuid": slot_field_uuid})
        if position_before != position_after:  # cannot happen for a rename; guards against a Core regression
            raise st.TaxonomyError("slot moved during rename", "E_ZSPACE_POSITION")
        st.write_doc(doc, path)

    try:
        trk.bejson_taxonomies_record_rename(manifest_path, entity_name, slot_field_uuid, bound_field_name)
        mfdb_core_update_entity_record_105(manifest_path, st.E_ZSPACE, reservation["reservation_uuid"], st.ZS_STATE, st.ZSTATE_BOUND)
        mfdb_core_update_entity_record_105(manifest_path, st.E_ZSPACE, reservation["reservation_uuid"], st.ZS_BOUND, bound_field_name)
    except Exception:
        logger.exception("bind bookkeeping failed; reverting rename %s -> %s", bound_field_name, old_name)
        with st.entity_lock(path):
            doc = bejson_core_load_file(path)
            next(f for f in doc["Fields"] if f["field_uuid"] == slot_field_uuid)["name"] = old_name
            _bejson_core_invalidate_cache(doc)
            st.write_doc(doc, path)
        raise
    return bound_field_name
