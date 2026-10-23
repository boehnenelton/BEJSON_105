"""
File Name : lib_bejson_Scaffold_federation_bridge.py
Rel. Path : Lib_PY/Scaffold/lib_bejson_Scaffold_federation_bridge.py
Purpose   : Federation links between deployments, bound into each node's Z-space slot.
            create link -> compute taxonomy match kind (identical|variant) from the two nodes' taxonomies;
            bind        -> make sure the node's slot is bound to `<prefix>deployment_federation_uuid_fk`
                           and write the link UUID into it;
            resolve     -> follow the slot by field_uuid (works whatever the bound name is);
            teardown    -> delete the link; Core's null-on-delete clears the slot on both nodes.
            Transport is Core's mfdb_federation_push_config (atomic drop-zone); no second transport.
            Applying a pushed config into a slave database (mirroring rows with preserved UUIDs) is NOT
            implemented in this release.
VERSION   : 1.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : d71c94e5-28a0-4f6b-8e33-5a0b9c4e17f2
"""
from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Dict, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
for _fam in ("Taxonomies", "Scaffold"):
    _p = os.path.normpath(os.path.join(_HERE, "..", _fam))
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import lib_bejson_Taxonomies_store as st  # noqa: E402
import lib_bejson_Taxonomies_taxonomy_registry as reg  # noqa: E402
import lib_bejson_Taxonomies_uuid_tracker as trk  # noqa: E402
import lib_bejson_Scaffold_z_space_allocator as zsa  # noqa: E402
import lib_bejson_Scaffold_deployment_registry as dep  # noqa: E402
from lib_bejson_Core_bejson_core import bejson_core_create_104a  # noqa: E402
from lib_bejson_Core_mfdb_core import (  # noqa: E402
    mfdb_core_delete_entity_record_105,
    mfdb_core_update_entity_record_105,
    mfdb_federation_push_config,
)

logger = logging.getLogger(__name__)
VERSION = "1.0.0"

# Transport config document (104a). Field names follow the lattice taxonomy.
CFG_KEY = "lattice_config_entry_key"
CFG_VALUE = "lattice_config_entry_name"


def _link_dict(r: Dict[str, Any]) -> Dict[str, Any]:
    return {"link_uuid": r["record_uuid"], "link_key": r[st.LK_KEY], "master_deployment_uuid": r[st.LK_MASTER],
            "slave_deployment_uuid": r[st.LK_SLAVE], "protocol_kind": r[st.LK_PROTOCOL],
            "interval_seconds": r[st.LK_INTERVAL], "healthy_flag": r[st.LK_HEALTHY],
            "sync_timestamp": r[st.LK_SYNC], "match_kind": r[st.LK_MATCH]}


def bejson_scaffold_get_federation_link(manifest_path: str, link_ref: str) -> Dict[str, Any]:
    for r in st.read_rows(manifest_path, st.E_LINK):
        if link_ref in (r["record_uuid"], r[st.LK_KEY]):
            return _link_dict(r)
    raise st.TaxonomyError(f"federation link {link_ref!r} not found", "E_LINK_NOT_FOUND")


def bejson_scaffold_create_federation_link(
    manifest_path: str, master_deployment_ref: str, slave_deployment_ref: str,
    protocol_kind: str = "dropzone_polling", interval_seconds: int = 30,
) -> str:
    """Link a master deployment to a slave deployment. match_kind is computed, never supplied:
    'identical' when both follow the same taxonomy, else 'variant'. Returns link_uuid."""
    master = dep.bejson_scaffold_get_deployment(manifest_path, master_deployment_ref)
    slave = dep.bejson_scaffold_get_deployment(manifest_path, slave_deployment_ref)
    if master["role_kind"] != "master" or slave["role_kind"] != "slave":
        raise st.TaxonomyError("link needs a master-role deployment and a slave-role deployment", "E_LINK_ROLES")
    if interval_seconds < 1:
        raise st.TaxonomyError("interval_seconds must be >= 1", "E_LINK_INTERVAL")
    for existing in st.read_rows(manifest_path, st.E_LINK):
        if (existing[st.LK_MASTER], existing[st.LK_SLAVE]) == (master["deployment_uuid"], slave["deployment_uuid"]):
            raise st.TaxonomyError("these deployments are already linked", "E_LINK_EXISTS")
    kind = "identical" if master["taxonomy_uuid"] == slave["taxonomy_uuid"] else "variant"
    return st.add_row(manifest_path, st.E_LINK, st.build_row(
        manifest_path, st.E_LINK,
        **{st.LK_KEY: f"{master['node_key']}:{slave['node_key']}", st.LK_MASTER: master["deployment_uuid"],
           st.LK_SLAVE: slave["deployment_uuid"], st.LK_PROTOCOL: protocol_kind, st.LK_INTERVAL: int(interval_seconds),
           st.LK_HEALTHY: True, st.LK_SYNC: st.now_utc(), st.LK_MATCH: kind}))


def _federation_slot(manifest_path: str) -> Dict[str, Any]:
    slot = zsa.bejson_scaffold_find_slot(manifest_path, st.E_DEPLOYMENT)
    if slot is None:
        raise st.TaxonomyError(f"{st.E_DEPLOYMENT} has no Z-space reservation", "E_ZSPACE_MISSING")
    return slot


def bejson_scaffold_bind_federation_link(manifest_path: str, node_deployment_ref: str, federation_link_uuid: str) -> str:
    """Write `federation_link_uuid` into the node's Z-space slot, binding the slot first if it is still reserved
    (to `<slot taxonomy prefix>deployment_federation_uuid_fk`). Returns the bound field name."""
    node = dep.bejson_scaffold_get_deployment(manifest_path, node_deployment_ref)
    link = bejson_scaffold_get_federation_link(manifest_path, federation_link_uuid)
    if node["deployment_uuid"] not in (link["master_deployment_uuid"], link["slave_deployment_uuid"]):
        raise st.TaxonomyError("node is neither end of that link", "E_LINK_NOT_ENDPOINT")
    slot = _federation_slot(manifest_path)
    if slot["state_kind"] == st.ZSTATE_RESERVED:
        entry = trk.bejson_taxonomies_get_field_entry(manifest_path, st.E_DEPLOYMENT, slot["slot_field_uuid"])
        prefix = reg.bejson_taxonomies_get_taxonomy(manifest_path, entry["taxonomy_uuid"])["prefix_key"]
        subject = st.E_DEPLOYMENT[len(prefix) - 1:].lower()  # 'LatticeDeployment' -> 'deployment'
        zsa.bejson_scaffold_bind_z_space_slot(
            manifest_path, st.E_DEPLOYMENT, slot["slot_field_uuid"], f"{prefix}{subject}_federation{st.FK_SUFFIX}")
        slot = _federation_slot(manifest_path)
    bound = slot["current_field_name"]
    mfdb_core_update_entity_record_105(manifest_path, st.E_DEPLOYMENT, node["deployment_uuid"], bound, link["link_uuid"])
    return bound


def bejson_scaffold_resolve_federation_link(manifest_path: str, node_deployment_ref: str) -> Optional[Dict[str, Any]]:
    """The link a node is bound to, or None. Follows the slot by field_uuid, so it works for any bound name."""
    node = dep.bejson_scaffold_get_deployment(manifest_path, node_deployment_ref)
    slot = _federation_slot(manifest_path)
    if slot["state_kind"] != st.ZSTATE_BOUND:
        return None
    row = next(r for r in st.read_rows(manifest_path, st.E_DEPLOYMENT) if r["record_uuid"] == node["deployment_uuid"])
    link_uuid = row[slot["current_field_name"]]
    return None if link_uuid is None else bejson_scaffold_get_federation_link(manifest_path, link_uuid)


def bejson_scaffold_teardown_federation_link(manifest_path: str, link_ref: str) -> None:
    """Delete a link. Both nodes survive; their slot cells are nulled by Core's fk_on_delete='null'."""
    link = bejson_scaffold_get_federation_link(manifest_path, link_ref)
    mfdb_core_delete_entity_record_105(manifest_path, st.E_LINK, link["link_uuid"])


def bejson_scaffold_build_link_config(manifest_path: str, link_ref: str) -> Dict[str, Any]:
    """A 104a document describing a link (both nodes, their taxonomies and suffix rules) for the slave side."""
    link = bejson_scaffold_get_federation_link(manifest_path, link_ref)
    nodes = {k: dep.bejson_scaffold_get_deployment(manifest_path, link[f"{k}_deployment_uuid"]) for k in ("master", "slave")}
    items = [("link_uuid", link["link_uuid"]), ("link_key", link["link_key"]), ("match_kind", link["match_kind"]),
             ("protocol_kind", link["protocol_kind"]), ("interval_seconds", str(link["interval_seconds"]))]
    for side, node in nodes.items():
        tx = reg.bejson_taxonomies_get_taxonomy(manifest_path, node["taxonomy_uuid"])
        items += [(f"{side}_deployment_uuid", node["deployment_uuid"]), (f"{side}_node_key", node["node_key"]),
                  (f"{side}_taxonomy_uuid", tx["taxonomy_uuid"]), (f"{side}_taxonomy_prefix", tx["prefix_key"]),
                  (f"{side}_taxonomy_suffix_rules",
                   json.dumps({t: r["field_type"] for t, r in sorted(tx["suffix_rules"].items())}, sort_keys=True))]
    return bejson_core_create_104a(
        "FederationLinkConfig",
        [{"name": CFG_KEY, "type": "string"}, {"name": CFG_VALUE, "type": "string"}],
        [[k, v] for k, v in items],
        Link_UUID=link["link_uuid"], Generated_At=st.now_utc())


def bejson_scaffold_push_link_config(manifest_path: str, link_ref: str, slave_dropzone_dir: str) -> bool:
    """Atomically drop the link config into a slave's dropzone using Core's federation transport."""
    config = bejson_scaffold_build_link_config(manifest_path, link_ref)
    dest = os.path.join(slave_dropzone_dir, f"link_{config['Link_UUID']}.bejson")
    return mfdb_federation_push_config(config, dest)


def bejson_scaffold_read_link_config(config_doc: Dict[str, Any]) -> Dict[str, str]:
    """Parse a pushed config back into {key: value}. Suffix-rule entries stay JSON strings."""
    if config_doc.get("Records_Type") != ["FederationLinkConfig"]:
        raise st.TaxonomyError("not a FederationLinkConfig document", "E_LINK_CONFIG")
    names = [f["name"] for f in config_doc["Fields"]]
    k, v = names.index(CFG_KEY), names.index(CFG_VALUE)
    return {row[k]: row[v] for row in config_doc["Values"]}
