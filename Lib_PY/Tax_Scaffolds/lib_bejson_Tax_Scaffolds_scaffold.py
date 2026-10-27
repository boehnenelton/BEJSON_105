"""
File Name : lib_bejson_Tax_Scaffolds_scaffold.py
Rel. Path : Lib_PY/Tax_Scaffolds/lib_bejson_Tax_Scaffolds_scaffold.py
Purpose   : Tax_Scaffolds SCAFFOLD: everything that builds or changes a node: Z-space slots, deployments, federation links, rebuild and prebuilt deployment, field-set grafts and entity scaffolding.
VERSION   : 3.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : 357d6457-7cbb-409a-98a5-8ba21fc6620e
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from typing import Any, Dict, List, Optional, Union

# Sibling family directories (Lib_PY/Core, Lib_PY/Taxonomies, Lib_PY/Tax_Scaffolds) resolve relative to this file; nothing is hardcoded.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _fam in ('Taxonomies', 'Tax_Scaffolds'):
    _p = os.path.normpath(os.path.join(_HERE, "..", _fam))
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import lib_bejson_Taxonomies_core as txc
import lib_bejson_Taxonomies_registry as txr
import lib_bejson_Tax_Scaffolds_core as tcore
import lib_bejson_Tax_Scaffolds_validator as tval
from lib_bejson_Core_bejson_core import (  # noqa: E402
    bejson_core_create_104a,
    bejson_core_define_field,
    bejson_core_get_field_map,
    bejson_core_load_file,
    bejson_core_remove_field,
    bejson_core_resolve_field_index,
)
from lib_bejson_Core_mfdb_core import (  # noqa: E402
    mfdb_core_create_connected_slave_entity,
    mfdb_core_delete_entity_record_105,
    mfdb_core_sync_all_counts,
    mfdb_core_update_entity_record_105,
    mfdb_federation_push_config,
)

logger = logging.getLogger(__name__)
VERSION = "3.0.0"

MAX_SLOTS_PER_CALL = 16

def bejson_tax_scaffolds_list_z_space(
    manifest_path: str, entity_name: Optional[str] = None, state_kind: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Reservations, lowest ordinal first, each with the slot's current column name (resolved by field_uuid)."""
    out: List[Dict[str, Any]] = []
    docs: Dict[str, dict] = {}
    for z in txc.read_rows(manifest_path, txc.E_ZSPACE):
        ent = z[txc.ZS_ENTITY]
        if entity_name is not None and ent != entity_name:
            continue
        if state_kind is not None and z[txc.ZS_STATE] != state_kind:
            continue
        if ent not in docs:
            docs[ent] = bejson_core_load_file(txc.entity_path(manifest_path, ent))
        current = next((f["name"] for f in docs[ent]["Fields"] if f["field_uuid"] == z[txc.ZS_FIELD_UUID]), None)
        out.append({"reservation_uuid": z["record_uuid"], "entity_name": ent,
                    "slot_field_uuid": z[txc.ZS_FIELD_UUID], "ordinal": z[txc.ZS_ORDINAL],
                    "state_kind": z[txc.ZS_STATE], "bound_field_name": z[txc.ZS_BOUND],
                    "current_field_name": current})
    return sorted(out, key=lambda r: (r["entity_name"], r["ordinal"]))

def bejson_tax_scaffolds_find_slot(
    manifest_path: str, entity_name: str, state_kind: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Lowest-ordinal reservation for an entity (optionally filtered by state), or None."""
    found = bejson_tax_scaffolds_list_z_space(manifest_path, entity_name, state_kind)
    return found[0] if found else None

def _rollback_reserve(manifest_path: str, entity_name: str, path: str, new_uuids: List[str],
                      ledger_uuids: List[str], zspace_uuids: List[str]) -> None:
    for zu in zspace_uuids:
        mfdb_core_delete_entity_record_105(manifest_path, txc.E_ZSPACE, zu)
    for lu in ledger_uuids:
        mfdb_core_delete_entity_record_105(manifest_path, txc.E_FIELD, lu)
    doc = bejson_core_load_file(path)
    for fuuid in new_uuids:
        bejson_core_remove_field(doc, fuuid)  # by field_uuid; Core drops the column from every row
    txc.write_doc(doc, path)

def bejson_tax_scaffolds_reserve_z_space_slot(
    manifest_path: str, entity_name: str, taxonomy_ref: str, slot_count: int = 1,
    fk_target_entity: Optional[str] = None, fk_on_delete: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Append `slot_count` unbound slot columns to `entity_name` (named `<prefix>zspace_NN_reserved_slot`
    under `taxonomy_ref`), ledger them and record the reservations. Existing rows get null in each slot.
    FK metadata may be pre-set so binding later is a pure rename. All-or-nothing."""
    if not 1 <= slot_count <= MAX_SLOTS_PER_CALL:
        raise txc.TaxonomyError(f"slot_count must be 1..{MAX_SLOTS_PER_CALL}", "E_ZSPACE_COUNT")
    taxonomy = txc.bejson_taxonomies_get_taxonomy(manifest_path, taxonomy_ref)
    path = txc.entity_path(manifest_path, entity_name)
    ordinals = [z["ordinal"] for z in bejson_tax_scaffolds_list_z_space(manifest_path, entity_name)]
    next_ordinal = (max(ordinals) if ordinals else 0) + 1

    new_names: List[str] = []
    new_uuids: List[str] = []
    with txc.entity_lock(path):
        doc = bejson_core_load_file(path)
        names = [f["name"] for f in doc["Fields"]]
        unbound = [i for i, n in enumerate(names) if n.endswith(txc.SLOT_SUFFIX)]
        if unbound and unbound != list(range(len(names) - len(unbound), len(names))):
            raise txc.TaxonomyError(f"{entity_name}: existing slots are not a trailing block", "E_ZSPACE_LAYOUT")
        for k in range(slot_count):
            name = f"{taxonomy['prefix_key']}zspace_{next_ordinal + k:02d}_reserved_slot"
            problems = txc.bejson_taxonomies_check_field_name(taxonomy, name, "string")
            if problems or name in names:
                raise txc.TaxonomyComplianceError(f"cannot reserve slot {name!r}", problems or [f"{name!r} already exists"])
            new_names.append(name)
        for name in new_names:
            new_uuids.append(bejson_core_define_field(
                doc, name, "string", fk_target_entity=fk_target_entity, fk_on_delete=fk_on_delete))
        txc.write_doc(doc, path)

    ledger_uuids: List[str] = []
    zspace_uuids: List[str] = []
    result: List[Dict[str, Any]] = []
    try:
        txc.bejson_taxonomies_track_fields(manifest_path, entity_name, taxonomy["taxonomy_uuid"], new_names)
        ledger_uuids = [txc.bejson_taxonomies_get_field_entry(manifest_path, entity_name, u)["ledger_record_uuid"]
                        for u in new_uuids]
        for k, (name, fuuid) in enumerate(zip(new_names, new_uuids)):
            zspace_uuids.append(txc.add_row(manifest_path, txc.E_ZSPACE, txc.build_row(
                manifest_path, txc.E_ZSPACE,
                **{txc.ZS_ENTITY: entity_name, txc.ZS_FIELD_UUID: fuuid, txc.ZS_ORDINAL: next_ordinal + k,
                   txc.ZS_STATE: txc.ZSTATE_RESERVED, txc.ZS_BOUND: None, txc.ZS_ALLOCATED: txc.now_utc()})))
            result.append({"slot_name": name, "slot_field_uuid": fuuid, "ordinal": next_ordinal + k,
                           "reservation_uuid": zspace_uuids[-1]})
    except Exception:
        logger.exception("reserve_z_space_slot failed for %s; rolling back", entity_name)
        with txc.entity_lock(path):
            if not ledger_uuids:  # ledger step itself failed part-way: remove any rows it did add
                ledger_uuids = [r["record_uuid"] for r in txc.read_rows(manifest_path, txc.E_FIELD)
                                if r[txc.FE_ENTITY] == entity_name and r[txc.FE_UUID] in new_uuids]
            _rollback_reserve(manifest_path, entity_name, path, new_uuids, ledger_uuids, zspace_uuids)
        raise
    return result

def bejson_tax_scaffolds_bind_z_space_slot(
    manifest_path: str, entity_name: str, slot_field_uuid: str, bound_field_name: str,
) -> str:
    """Rename a reserved slot to `bound_field_name` (must comply with the slot's taxonomy and must not end in
    `_slot`; a slot with FK metadata must be bound to a `_uuid_fk` name). field_uuid and column position are
    unchanged and no row is rewritten. Returns the bound name."""
    reservation = next((z for z in bejson_tax_scaffolds_list_z_space(manifest_path, entity_name)
                        if z["slot_field_uuid"] == slot_field_uuid), None)
    if reservation is None:
        raise txc.TaxonomyError(f"{entity_name}: no reservation for slot {slot_field_uuid!r}", "E_ZSPACE_NOT_FOUND")
    if reservation["state_kind"] != txc.ZSTATE_RESERVED:
        raise txc.TaxonomyError(f"{entity_name}.{reservation['current_field_name']} is already bound", "E_ZSPACE_ALREADY_BOUND")

    entry = txc.bejson_taxonomies_get_field_entry(manifest_path, entity_name, slot_field_uuid)
    taxonomy = txc.bejson_taxonomies_get_taxonomy(manifest_path, entry["taxonomy_uuid"])
    path = txc.entity_path(manifest_path, entity_name)
    old_name = reservation["current_field_name"]

    with txc.entity_lock(path):
        doc = bejson_core_load_file(path)
        fdef = next(f for f in doc["Fields"] if f["field_uuid"] == slot_field_uuid)
        problems = txc.bejson_taxonomies_check_field_name(taxonomy, bound_field_name, fdef["type"])
        if bound_field_name.endswith(txc.SLOT_SUFFIX):
            problems.append(f"{bound_field_name!r}: a bound name must not end in {txc.SLOT_SUFFIX}")
        if fdef.get("fk_target_entity") and not bound_field_name.endswith(txc.FK_SUFFIX):
            problems.append(f"{bound_field_name!r}: slot carries FK metadata, so it must end in {txc.FK_SUFFIX}")
        if any(f["name"] == bound_field_name for f in doc["Fields"]):
            problems.append(f"{bound_field_name!r}: already exists in {entity_name}")
        if problems:
            raise txc.TaxonomyComplianceError(f"cannot bind slot to {bound_field_name!r}", problems)

        position_before = bejson_core_get_field_map(doc)[old_name]
        fdef["name"] = bound_field_name
        tcore.bejson_tax_scaffolds_core_invalidate_cache(doc)  # sanctioned helper: rebuild by_name/by_uuid/by_name_row
        position_after = bejson_core_resolve_field_index(doc, {"name": bound_field_name, "field_uuid": slot_field_uuid})
        if position_before != position_after:  # cannot happen for a rename; guards against a Core regression
            raise txc.TaxonomyError("slot moved during rename", "E_ZSPACE_POSITION")
        txc.write_doc(doc, path)

    try:
        txc.bejson_taxonomies_record_rename(manifest_path, entity_name, slot_field_uuid, bound_field_name)
        mfdb_core_update_entity_record_105(manifest_path, txc.E_ZSPACE, reservation["reservation_uuid"], txc.ZS_STATE, txc.ZSTATE_BOUND)
        mfdb_core_update_entity_record_105(manifest_path, txc.E_ZSPACE, reservation["reservation_uuid"], txc.ZS_BOUND, bound_field_name)
    except Exception:
        logger.exception("bind bookkeeping failed; reverting rename %s -> %s", bound_field_name, old_name)
        with txc.entity_lock(path):
            doc = bejson_core_load_file(path)
            next(f for f in doc["Fields"] if f["field_uuid"] == slot_field_uuid)["name"] = old_name
            tcore.bejson_tax_scaffolds_core_invalidate_cache(doc)
            txc.write_doc(doc, path)
        raise
    return bound_field_name


def _as_dict(r: Dict[str, Any]) -> Dict[str, Any]:
    return {"deployment_uuid": r["record_uuid"], "node_key": r[txc.DP_NODE], "display_name": r[txc.DP_DISPLAY],
            "role_kind": r[txc.DP_ROLE], "strategy_kind": r[txc.DP_STRATEGY], "zspace_uuid": r[txc.DP_ZSPACE],
            "active_flag": r[txc.DP_ACTIVE], "created_timestamp": r[txc.DP_CREATED], "taxonomy_uuid": r[txc.DP_TAXONOMY]}

def bejson_tax_scaffolds_list_deployments(manifest_path: str) -> List[Dict[str, Any]]:
    return [_as_dict(r) for r in txc.read_rows(manifest_path, txc.E_DEPLOYMENT)]

def bejson_tax_scaffolds_get_deployment(manifest_path: str, deployment_ref: str) -> Dict[str, Any]:
    """Look up by deployment_uuid or node_key."""
    for d in bejson_tax_scaffolds_list_deployments(manifest_path):
        if deployment_ref in (d["deployment_uuid"], d["node_key"]):
            return d
    raise txc.TaxonomyError(f"deployment {deployment_ref!r} not found", "E_DEPLOYMENT_NOT_FOUND")

def bejson_tax_scaffolds_register_deployment(
    manifest_path: str, node_key: str, display_name: str, role_kind: str, strategy_kind: str, taxonomy_ref: str,
) -> str:
    """Add a LatticeDeployment row. The node references the entity's first Z-space reservation and the
    taxonomy it follows (root or variant). Returns deployment_uuid."""
    if role_kind not in txc.ROLE_KINDS:
        raise txc.TaxonomyError(f"role_kind must be one of {txc.ROLE_KINDS}", "E_ROLE")
    if strategy_kind not in txc.STRATEGY_KINDS:
        raise txc.TaxonomyError(f"strategy_kind must be one of {txc.STRATEGY_KINDS}", "E_STRATEGY")
    if not node_key or any(d["node_key"] == node_key for d in bejson_tax_scaffolds_list_deployments(manifest_path)):
        raise txc.TaxonomyError(f"node_key {node_key!r} is empty or already registered", "E_NODE_KEY")
    taxonomy = txc.bejson_taxonomies_get_taxonomy(manifest_path, taxonomy_ref)
    slot = bejson_tax_scaffolds_find_slot(manifest_path, txc.E_DEPLOYMENT)
    if slot is None:
        raise txc.TaxonomyError(f"{txc.E_DEPLOYMENT} has no Z-space reservation", "E_ZSPACE_MISSING")
    return txc.add_row(manifest_path, txc.E_DEPLOYMENT, txc.build_row(
        manifest_path, txc.E_DEPLOYMENT,
        **{txc.DP_NODE: node_key, txc.DP_DISPLAY: display_name, txc.DP_ROLE: role_kind, txc.DP_STRATEGY: strategy_kind,
           txc.DP_ZSPACE: slot["reservation_uuid"], txc.DP_ACTIVE: True, txc.DP_CREATED: txc.now_utc(),
           txc.DP_TAXONOMY: taxonomy["taxonomy_uuid"]}))

def bejson_tax_scaffolds_set_deployment_active(manifest_path: str, deployment_ref: str, active_flag: bool) -> None:
    d = bejson_tax_scaffolds_get_deployment(manifest_path, deployment_ref)
    mfdb_core_update_entity_record_105(manifest_path, txc.E_DEPLOYMENT, d["deployment_uuid"], txc.DP_ACTIVE, bool(active_flag))

def bejson_tax_scaffolds_set_network_role(manifest_path: str, network_role: str) -> None:
    """Set the manifest's Network_Role header (Master | Slave) atomically."""
    if network_role not in ("Master", "Slave"):
        raise txc.TaxonomyError(f"network_role must be Master or Slave, got {network_role!r}", "E_NETWORK_ROLE")
    with txc.entity_lock(manifest_path):
        doc = bejson_core_load_file(manifest_path)
        doc["Network_Role"] = network_role
        txc.write_doc(doc, manifest_path)

# Transport config document (104a). Field names follow the lattice taxonomy.
CFG_KEY = "lattice_config_entry_key"
CFG_VALUE = "lattice_config_entry_name"

def _link_dict(r: Dict[str, Any]) -> Dict[str, Any]:
    return {"link_uuid": r["record_uuid"], "link_key": r[txc.LK_KEY], "master_deployment_uuid": r[txc.LK_MASTER],
            "slave_deployment_uuid": r[txc.LK_SLAVE], "protocol_kind": r[txc.LK_PROTOCOL],
            "interval_seconds": r[txc.LK_INTERVAL], "healthy_flag": r[txc.LK_HEALTHY],
            "sync_timestamp": r[txc.LK_SYNC], "match_kind": r[txc.LK_MATCH]}

def bejson_tax_scaffolds_get_federation_link(manifest_path: str, link_ref: str) -> Dict[str, Any]:
    for r in txc.read_rows(manifest_path, txc.E_LINK):
        if link_ref in (r["record_uuid"], r[txc.LK_KEY]):
            return _link_dict(r)
    raise txc.TaxonomyError(f"federation link {link_ref!r} not found", "E_LINK_NOT_FOUND")

def bejson_tax_scaffolds_create_federation_link(
    manifest_path: str, master_deployment_ref: str, slave_deployment_ref: str,
    protocol_kind: str = "dropzone_polling", interval_seconds: int = 30,
) -> str:
    """Link a master deployment to a slave deployment. match_kind is computed, never supplied:
    'identical' when both follow the same taxonomy, else 'variant'. Returns link_uuid."""
    master = bejson_tax_scaffolds_get_deployment(manifest_path, master_deployment_ref)
    slave = bejson_tax_scaffolds_get_deployment(manifest_path, slave_deployment_ref)
    if master["role_kind"] != "master" or slave["role_kind"] != "slave":
        raise txc.TaxonomyError("link needs a master-role deployment and a slave-role deployment", "E_LINK_ROLES")
    if interval_seconds < 1:
        raise txc.TaxonomyError("interval_seconds must be >= 1", "E_LINK_INTERVAL")
    for existing in txc.read_rows(manifest_path, txc.E_LINK):
        if (existing[txc.LK_MASTER], existing[txc.LK_SLAVE]) == (master["deployment_uuid"], slave["deployment_uuid"]):
            raise txc.TaxonomyError("these deployments are already linked", "E_LINK_EXISTS")
    kind = "identical" if master["taxonomy_uuid"] == slave["taxonomy_uuid"] else "variant"
    return txc.add_row(manifest_path, txc.E_LINK, txc.build_row(
        manifest_path, txc.E_LINK,
        **{txc.LK_KEY: f"{master['node_key']}:{slave['node_key']}", txc.LK_MASTER: master["deployment_uuid"],
           txc.LK_SLAVE: slave["deployment_uuid"], txc.LK_PROTOCOL: protocol_kind, txc.LK_INTERVAL: int(interval_seconds),
           txc.LK_HEALTHY: True, txc.LK_SYNC: txc.now_utc(), txc.LK_MATCH: kind}))

def _federation_slot(manifest_path: str) -> Dict[str, Any]:
    slot = bejson_tax_scaffolds_find_slot(manifest_path, txc.E_DEPLOYMENT)
    if slot is None:
        raise txc.TaxonomyError(f"{txc.E_DEPLOYMENT} has no Z-space reservation", "E_ZSPACE_MISSING")
    return slot

def bejson_tax_scaffolds_bind_federation_link(manifest_path: str, node_deployment_ref: str, federation_link_uuid: str) -> str:
    """Write `federation_link_uuid` into the node's Z-space slot, binding the slot first if it is still reserved
    (to `<slot taxonomy prefix>deployment_federation_uuid_fk`). Returns the bound field name."""
    node = bejson_tax_scaffolds_get_deployment(manifest_path, node_deployment_ref)
    link = bejson_tax_scaffolds_get_federation_link(manifest_path, federation_link_uuid)
    if node["deployment_uuid"] not in (link["master_deployment_uuid"], link["slave_deployment_uuid"]):
        raise txc.TaxonomyError("node is neither end of that link", "E_LINK_NOT_ENDPOINT")
    slot = _federation_slot(manifest_path)
    if slot["state_kind"] == txc.ZSTATE_RESERVED:
        entry = txc.bejson_taxonomies_get_field_entry(manifest_path, txc.E_DEPLOYMENT, slot["slot_field_uuid"])
        prefix = txc.bejson_taxonomies_get_taxonomy(manifest_path, entry["taxonomy_uuid"])["prefix_key"]
        subject = txc.E_DEPLOYMENT[len(prefix) - 1:].lower()  # 'LatticeDeployment' -> 'deployment'
        bejson_tax_scaffolds_bind_z_space_slot(
            manifest_path, txc.E_DEPLOYMENT, slot["slot_field_uuid"], f"{prefix}{subject}_federation{txc.FK_SUFFIX}")
        slot = _federation_slot(manifest_path)
    bound = slot["current_field_name"]
    mfdb_core_update_entity_record_105(manifest_path, txc.E_DEPLOYMENT, node["deployment_uuid"], bound, link["link_uuid"])
    return bound

def bejson_tax_scaffolds_resolve_federation_link(manifest_path: str, node_deployment_ref: str) -> Optional[Dict[str, Any]]:
    """The link a node is bound to, or None. Follows the slot by field_uuid, so it works for any bound name."""
    node = bejson_tax_scaffolds_get_deployment(manifest_path, node_deployment_ref)
    slot = _federation_slot(manifest_path)
    if slot["state_kind"] != txc.ZSTATE_BOUND:
        return None
    row = next(r for r in txc.read_rows(manifest_path, txc.E_DEPLOYMENT) if r["record_uuid"] == node["deployment_uuid"])
    link_uuid = row[slot["current_field_name"]]
    return None if link_uuid is None else bejson_tax_scaffolds_get_federation_link(manifest_path, link_uuid)

def bejson_tax_scaffolds_teardown_federation_link(manifest_path: str, link_ref: str) -> None:
    """Delete a link. Both nodes survive; their slot cells are nulled by Core's fk_on_delete='null'."""
    link = bejson_tax_scaffolds_get_federation_link(manifest_path, link_ref)
    mfdb_core_delete_entity_record_105(manifest_path, txc.E_LINK, link["link_uuid"])

def bejson_tax_scaffolds_build_link_config(manifest_path: str, link_ref: str) -> Dict[str, Any]:
    """A 104a document describing a link (both nodes, their taxonomies and suffix rules) for the slave side."""
    link = bejson_tax_scaffolds_get_federation_link(manifest_path, link_ref)
    nodes = {k: bejson_tax_scaffolds_get_deployment(manifest_path, link[f"{k}_deployment_uuid"]) for k in ("master", "slave")}
    items = [("link_uuid", link["link_uuid"]), ("link_key", link["link_key"]), ("match_kind", link["match_kind"]),
             ("protocol_kind", link["protocol_kind"]), ("interval_seconds", str(link["interval_seconds"]))]
    for side, node in nodes.items():
        tx = txc.bejson_taxonomies_get_taxonomy(manifest_path, node["taxonomy_uuid"])
        items += [(f"{side}_deployment_uuid", node["deployment_uuid"]), (f"{side}_node_key", node["node_key"]),
                  (f"{side}_taxonomy_uuid", tx["taxonomy_uuid"]), (f"{side}_taxonomy_prefix", tx["prefix_key"]),
                  (f"{side}_taxonomy_suffix_rules",
                   json.dumps({t: r["field_type"] for t, r in sorted(tx["suffix_rules"].items())}, sort_keys=True))]
    return bejson_core_create_104a(
        "FederationLinkConfig",
        [{"name": CFG_KEY, "type": "string"}, {"name": CFG_VALUE, "type": "string"}],
        [[k, v] for k, v in items],
        Link_UUID=link["link_uuid"], Generated_At=txc.now_utc())

def bejson_tax_scaffolds_push_link_config(manifest_path: str, link_ref: str, slave_dropzone_dir: str) -> bool:
    """Atomically drop the link config into a slave's dropzone using Core's federation transport."""
    config = bejson_tax_scaffolds_build_link_config(manifest_path, link_ref)
    dest = os.path.join(slave_dropzone_dir, f"link_{config['Link_UUID']}.bejson")
    return mfdb_federation_push_config(config, dest)

def bejson_tax_scaffolds_read_link_config(config_doc: Dict[str, Any]) -> Dict[str, str]:
    """Parse a pushed config back into {key: value}. Suffix-rule entries stay JSON strings."""
    if config_doc.get("Records_Type") != ["FederationLinkConfig"]:
        raise txc.TaxonomyError("not a FederationLinkConfig document", "E_LINK_CONFIG")
    names = [f["name"] for f in config_doc["Fields"]]
    k, v = names.index(CFG_KEY), names.index(CFG_VALUE)
    return {row[k]: row[v] for row in config_doc["Values"]}


class ScaffoldError(txc.TaxonomyError):
    def __init__(self, message: str, problems: Optional[List[str]] = None):
        super().__init__(message, "E_SCAFFOLD")
        self.problems = problems or []

def _apply_field_sets(manifest: str, taxonomy_uuid: str, field_sets: Optional[List[Any]],
                      entities: Optional[List[Dict[str, Any]]]) -> List[str]:
    """Register field sets, then scaffold entities (with their grafts) under the node's taxonomy."""
    if field_sets:
        bejson_tax_scaffolds_register_field_sets(manifest, field_sets)
    if entities:
        return [r["entity_name"] for r in bejson_tax_scaffolds_scaffold_entities(manifest, taxonomy_uuid, entities)]
    return []

def bejson_tax_scaffolds_deploy_rebuild(
    root_dir: str, node_key: str, display_name: str, role_kind: str = "master",
    taxonomy_namespace: str = txc.ROOT_NAMESPACE,
    suffix_overrides: Optional[Dict[str, Any]] = None, suffix_removals: Optional[List[str]] = None,
    field_sets: Optional[List[Any]] = None, entities: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build a new node from scratch under `root_dir`. If `taxonomy_namespace` differs from the root
    namespace, a variant is derived from the root taxonomy (with the given suffix overrides/removals)
    and the node follows it. `field_sets` (definition file paths or {set_key, members} dicts) are registered, then
    `entities` ({name, fields, field_sets?, ...}) are scaffolded under the node's taxonomy, with their field sets grafted.
    Returns {manifest_path, deployment_uuid, taxonomy_uuid, role_kind, strategy_kind, entities_scaffolded}."""
    if role_kind not in txc.ROLE_KINDS:
        raise txc.TaxonomyError(f"role_kind must be one of {txc.ROLE_KINDS}", "E_ROLE")
    manifest = txc.bejson_taxonomies_build_registry_database(
        root_dir, network_role="Master" if role_kind == "master" else "Slave")
    if taxonomy_namespace == txc.ROOT_NAMESPACE:
        if suffix_overrides or suffix_removals:
            raise txc.TaxonomyError("suffix overrides need a variant namespace; the root taxonomy is fixed", "E_TAXONOMY_ROOT")
        taxonomy_uuid = txc.bejson_taxonomies_get_taxonomy(manifest, txc.ROOT_NAMESPACE)["taxonomy_uuid"]
    else:
        taxonomy_uuid = txc.bejson_taxonomies_derive_variant(
            manifest, txc.ROOT_NAMESPACE, taxonomy_namespace, suffix_overrides, suffix_removals)
    deployment_uuid = bejson_tax_scaffolds_register_deployment(
        manifest, node_key, display_name, role_kind, "rebuild", taxonomy_uuid)
    if role_kind == "master":
        mfdb_core_create_connected_slave_entity(manifest)
    scaffolded = _apply_field_sets(manifest, taxonomy_uuid, field_sets, entities)
    txc.bejson_taxonomies_stamp_audit(manifest)
    report = txc.bejson_taxonomies_audit_database(manifest)
    if not report["passed"]:
        raise ScaffoldError(f"rebuilt node {node_key!r} failed audit", report["problems"])
    return {"manifest_path": manifest, "deployment_uuid": deployment_uuid, "taxonomy_uuid": taxonomy_uuid,
            "role_kind": role_kind, "strategy_kind": "rebuild", "entities_scaffolded": scaffolded}

def bejson_tax_scaffolds_deploy_master_rebuild(root_dir: str, node_key: str, display_name: str, **kwargs: Any) -> Dict[str, Any]:
    return bejson_tax_scaffolds_deploy_rebuild(root_dir, node_key, display_name, role_kind="master", **kwargs)

def bejson_tax_scaffolds_deploy_slave_rebuild(root_dir: str, node_key: str, display_name: str, **kwargs: Any) -> Dict[str, Any]:
    return bejson_tax_scaffolds_deploy_rebuild(root_dir, node_key, display_name, role_kind="slave", **kwargs)

SetSpec = Union[str, Dict[str, Any]]  # a set_key, or {"set_key", "version"?, "subject"?, "fk_targets"?}

class GraftError(txc.TaxonomyError):
    def __init__(self, message: str, problems: Optional[List[str]] = None):
        super().__init__(message, "E_GRAFT")
        self.problems = problems or []

def _apply(manifest_path: str, plan: Dict[str, Any], entity_name: str) -> Dict[str, Any]:
    """Apply a validated plan. Caller holds the all-or-nothing wrapper."""
    taxonomy, fset, existing = plan["taxonomy"], plan["fset"], plan["existing_graft"]
    uuids = tcore.bejson_tax_scaffolds_core_insert_columns(manifest_path, entity_name, [
        {k: c[k] for k in ("name", "type", "fk_target_entity", "fk_on_delete") if k in c} for c in plan["columns"]])
    if existing is None:
        graft_uuid = txc.add_row(manifest_path, txc.E_GRAFT, txc.build_row(
            manifest_path, txc.E_GRAFT,
            **{txc.GR_KEY: f"{entity_name}:{fset['set_key']}", txc.GR_SET: fset["set_uuid"], txc.GR_ENTITY: entity_name,
               txc.GR_SUBJECT: plan["subject"], txc.GR_TAXONOMY: taxonomy["taxonomy_uuid"], txc.GR_APPLIED: txc.now_utc()}))
    else:
        graft_uuid = existing["graft_uuid"]
        mfdb_core_update_entity_record_105(manifest_path, txc.E_GRAFT, graft_uuid, txc.GR_SET, fset["set_uuid"])
        mfdb_core_update_entity_record_105(manifest_path, txc.E_GRAFT, graft_uuid, txc.GR_APPLIED, txc.now_utc())
    names = [c["name"] for c in plan["columns"]]
    txc.bejson_taxonomies_track_fields(
        manifest_path, entity_name, taxonomy["taxonomy_uuid"], names,
        extras={c["name"]: {txc.FE_GRAFT: graft_uuid, txc.FE_SETMEMBER: c["member_uuid"]} for c in plan["columns"]})
    txc.bejson_taxonomies_stamp_audit(manifest_path)
    problems = tval.bejson_tax_scaffolds_validator_audit_gate(manifest_path)
    if problems:
        raise GraftError(f"grafting {fset['set_key']!r} onto {entity_name!r} failed audit", problems)
    return {"graft_uuid": graft_uuid, "set_key": fset["set_key"], "set_version": fset["version"],
            "entity_name": entity_name, "subject": plan["subject"],
            "columns": [{"descriptor": c["descriptor"], "field_name": c["name"], "field_uuid": u}
                        for c, u in zip(plan["columns"], uuids)]}

def bejson_tax_scaffolds_graft_field_set(
    manifest_path: str, entity_name: str, set_ref: str, version: Optional[int] = None,
    subject: Optional[str] = None, fk_targets: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Stamp a field set onto an entity under the entity's own prefix and subject. Existing rows get null in
    the new columns. Returns {graft_uuid, set_key, set_version, entity_name, subject, columns:[{descriptor,
    field_name, field_uuid}]}. Raises GraftError (.problems) before writing anything if the plan has problems."""
    plan, problems = tval.bejson_tax_scaffolds_validator_plan_graft(
        manifest_path, entity_name, set_ref, version, subject, fk_targets)
    if problems:
        raise GraftError(f"cannot graft {set_ref!r} onto {entity_name!r}", problems)
    with tcore.bejson_tax_scaffolds_core_all_or_nothing(manifest_path):
        return _apply(manifest_path, plan, entity_name)

def bejson_tax_scaffolds_upgrade_graft(
    manifest_path: str, entity_name: str, set_key: str, version: Optional[int] = None,
    fk_targets: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Bring an existing graft up to a newer version (default: latest) by adding only the new members."""
    plan, problems = tval.bejson_tax_scaffolds_validator_plan_graft(
        manifest_path, entity_name, set_key, version, None, fk_targets, upgrade=True)
    if problems:
        raise GraftError(f"cannot upgrade {set_key!r} on {entity_name!r}", problems)
    with tcore.bejson_tax_scaffolds_core_all_or_nothing(manifest_path):
        return _apply(manifest_path, plan, entity_name)

def bejson_tax_scaffolds_scaffold_entity(
    manifest_path: str, taxonomy_ref: str, entity_name: str, own_fields: List[Dict[str, Any]],
    field_sets: Optional[List[SetSpec]] = None, description: str = "", primary_key: str = "",
) -> Dict[str, Any]:
    """Create an entity (own_fields, all compliant with the taxonomy; at least one) and graft field sets onto
    it in one all-or-nothing step. Returns {entity_name, grafts:[...]}."""
    taxonomy = txc.bejson_taxonomies_get_taxonomy(manifest_path, taxonomy_ref)
    clash = [n for n in txc.manifest_entity_names(manifest_path) if n.lower() == entity_name.lower()]
    if clash:
        raise GraftError(f"cannot scaffold {entity_name!r}", [
            f"entity name collides with existing {clash[0]!r} (names are compared case-insensitively because entity files share a folder)"])
    with tcore.bejson_tax_scaffolds_core_all_or_nothing(manifest_path):
        txc.bejson_taxonomies_create_domain_entity(
            manifest_path, taxonomy["taxonomy_uuid"], entity_name,
            [txc.bejson_taxonomies_build_field_definition(taxonomy, f["name"], f["type"], f.get("fk_target_entity"), f.get("fk_on_delete"))
             for f in own_fields], description=description, primary_key=primary_key)
        grafts = []
        for spec in field_sets or []:
            spec = {"set_key": spec} if isinstance(spec, str) else dict(spec)
            plan, problems = tval.bejson_tax_scaffolds_validator_plan_graft(
                manifest_path, entity_name, spec["set_key"], spec.get("version"), spec.get("subject"), spec.get("fk_targets"))
            if problems:
                raise GraftError(f"cannot graft {spec['set_key']!r} onto new entity {entity_name!r}", problems)
            grafts.append(_apply(manifest_path, plan, entity_name))
    return {"entity_name": entity_name, "grafts": grafts}

def bejson_tax_scaffolds_register_field_sets(manifest_path: str, specs: List[Union[str, Dict[str, Any]]]) -> List[str]:
    """Make sure each set exists in this registry. A spec is a definition file path (imported), or a dict
    {set_key, display_name?, members} (defined, or accepted if the same content is already there).
    Returns the set row uuids."""
    out: List[str] = []
    for spec in specs:
        if isinstance(spec, str):
            out.append(txr.bejson_taxonomies_import_field_set(manifest_path, spec))
            continue
        existing = [s for s in txr.bejson_taxonomies_list_field_sets(manifest_path, spec.get("set_key"))]
        if not existing:
            out.append(txr.bejson_taxonomies_define_field_set(
                manifest_path, spec["set_key"], spec["members"], spec.get("display_name", "")))
            continue
        if txc.bejson_taxonomies_core_content_hash(existing[0]["members"]) != txc.bejson_taxonomies_core_content_hash(spec["members"]):
            raise txc.TaxonomyError(f"field set {spec['set_key']!r} already exists with different content", "E_FIELDSET_CONFLICT")
        out.append(existing[0]["set_uuid"])
    return out

def bejson_tax_scaffolds_scaffold_entities(
    manifest_path: str, default_taxonomy_ref: str, specs: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Scaffold several entities. A spec: {name, fields, field_sets?, description?, primary_key?, taxonomy?};
    `taxonomy` defaults to `default_taxonomy_ref` (normally the node's own taxonomy)."""
    return [bejson_tax_scaffolds_scaffold_entity(
        manifest_path, s.get("taxonomy", default_taxonomy_ref), s["name"], s["fields"], s.get("field_sets"),
        s.get("description", ""), s.get("primary_key", "")) for s in specs]

MANIFEST_NAME = "104a.mfdb.bejson"
_IGNORE = shutil.ignore_patterns("*.lock", "*.tmp", "__pycache__", ".git")
INSTANCE_ENTITIES = (txc.E_LINK, txc.E_DEPLOYMENT, "ConnectedSlave")  # link first: it references deployments; field sets and grafts stay

def _require_empty(target_dir: str) -> None:
    if os.path.exists(target_dir) and os.listdir(target_dir):
        raise ScaffoldError(f"target directory is not empty: {target_dir}")

def _clear_rows(manifest_path: str, entity_name: str) -> None:
    if entity_name not in txc.manifest_entity_names(manifest_path):
        return
    path = txc.entity_path(manifest_path, entity_name)
    with txc.entity_lock(path):
        doc = bejson_core_load_file(path)
        doc["Values"] = []
        txc.write_doc(doc, path)

def bejson_tax_scaffolds_capture_snapshot(source_manifest_path: str, snapshot_dir: str) -> str:
    """Copy a lattice database to `snapshot_dir`, strip instance rows, and audit the result.
    The source must itself pass audit. Returns the snapshot's manifest path."""
    source_report = txc.bejson_taxonomies_audit_database(source_manifest_path)
    if not source_report["passed"]:
        raise ScaffoldError("source database failed audit; refusing to snapshot", source_report["problems"])
    _require_empty(snapshot_dir)
    shutil.copytree(os.path.dirname(os.path.abspath(source_manifest_path)), snapshot_dir, ignore=_IGNORE, dirs_exist_ok=True)
    manifest = os.path.join(snapshot_dir, MANIFEST_NAME)
    for entity in INSTANCE_ENTITIES:
        _clear_rows(manifest, entity)
    mfdb_core_sync_all_counts(manifest)
    report = txc.bejson_taxonomies_audit_database(manifest)
    if not report["passed"]:
        raise ScaffoldError("snapshot failed audit", report["problems"])
    return manifest

def _pick_taxonomy(manifest_path: str, taxonomy_ref: Optional[str]) -> str:
    taxa = txc.bejson_taxonomies_list_taxonomies(manifest_path)
    if taxonomy_ref is not None:
        return txc.bejson_taxonomies_get_taxonomy(manifest_path, taxonomy_ref)["taxonomy_uuid"]
    if len(taxa) == 1:
        return taxa[0]["taxonomy_uuid"]
    raise txc.TaxonomyError(
        f"snapshot holds {len(taxa)} taxonomies ({', '.join(t['namespace_key'] for t in taxa)}); pass taxonomy_ref",
        "E_TAXONOMY_AMBIGUOUS")

def bejson_tax_scaffolds_deploy_prebuilt(
    snapshot_dir: str, target_dir: str, node_key: str, display_name: str,
    role_kind: str = "master", taxonomy_ref: Optional[str] = None,
    field_sets: Optional[List[Any]] = None, entities: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Instantiate a node from a snapshot (master or slave). `taxonomy_ref` names the taxonomy the node
    follows (uuid or namespace); optional only when the snapshot holds exactly one taxonomy.
    The snapshot's field sets and grafts come along; `field_sets` / `entities` add more at deploy time."""
    if role_kind not in txc.ROLE_KINDS:
        raise txc.TaxonomyError(f"role_kind must be one of {txc.ROLE_KINDS}", "E_ROLE")
    snap_manifest = os.path.join(snapshot_dir, MANIFEST_NAME)
    if not os.path.isfile(snap_manifest):
        raise ScaffoldError(f"no snapshot manifest in {snapshot_dir}")
    taxonomy_uuid = _pick_taxonomy(snap_manifest, taxonomy_ref)
    _require_empty(target_dir)
    shutil.copytree(snapshot_dir, target_dir, ignore=_IGNORE, dirs_exist_ok=True)
    manifest = os.path.join(target_dir, MANIFEST_NAME)
    try:
        bejson_tax_scaffolds_set_network_role(manifest, "Master" if role_kind == "master" else "Slave")
        deployment_uuid = bejson_tax_scaffolds_register_deployment(
            manifest, node_key, display_name, role_kind, "prebuilt", taxonomy_uuid)
        if role_kind == "master" and "ConnectedSlave" not in txc.manifest_entity_names(manifest):
            mfdb_core_create_connected_slave_entity(manifest)
        scaffolded = _apply_field_sets(manifest, taxonomy_uuid, field_sets, entities)
        txc.bejson_taxonomies_stamp_audit(manifest)
        report = txc.bejson_taxonomies_audit_database(manifest)
        if not report["passed"]:
            raise ScaffoldError(f"prebuilt node {node_key!r} failed audit", report["problems"])
    except Exception:
        logger.exception("prebuilt deployment failed; removing %s", target_dir)
        shutil.rmtree(target_dir, ignore_errors=True)
        raise
    return {"manifest_path": manifest, "deployment_uuid": deployment_uuid, "taxonomy_uuid": taxonomy_uuid,
            "role_kind": role_kind, "strategy_kind": "prebuilt", "entities_scaffolded": scaffolded}

def bejson_tax_scaffolds_deploy_master_prebuilt(snapshot_dir: str, target_dir: str, node_key: str, display_name: str, **kwargs: Any) -> Dict[str, Any]:
    return bejson_tax_scaffolds_deploy_prebuilt(snapshot_dir, target_dir, node_key, display_name, role_kind="master", **kwargs)

def bejson_tax_scaffolds_deploy_slave_prebuilt(snapshot_dir: str, target_dir: str, node_key: str, display_name: str, **kwargs: Any) -> Dict[str, Any]:
    return bejson_tax_scaffolds_deploy_prebuilt(snapshot_dir, target_dir, node_key, display_name, role_kind="slave", **kwargs)
