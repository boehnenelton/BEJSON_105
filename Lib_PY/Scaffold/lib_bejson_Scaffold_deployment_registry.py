"""
File Name : lib_bejson_Scaffold_deployment_registry.py
Rel. Path : Lib_PY/Scaffold/lib_bejson_Scaffold_deployment_registry.py
Purpose   : LatticeDeployment rows: register / look up deployments (role master|slave, strategy
            rebuild|prebuilt, taxonomy followed) and set the manifest Network_Role.
VERSION   : 1.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : 3b8f61d2-07c5-4e94-a1d3-c2e7905b4f18
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List

_HERE = os.path.dirname(os.path.abspath(__file__))
for _fam in ("Taxonomies", "Scaffold"):
    _p = os.path.normpath(os.path.join(_HERE, "..", _fam))
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import lib_bejson_Taxonomies_store as st  # noqa: E402
import lib_bejson_Taxonomies_taxonomy_registry as reg  # noqa: E402
import lib_bejson_Scaffold_z_space_allocator as zsa  # noqa: E402
from lib_bejson_Core_bejson_core import bejson_core_load_file  # noqa: E402
from lib_bejson_Core_mfdb_core import mfdb_core_update_entity_record_105  # noqa: E402

logger = logging.getLogger(__name__)
VERSION = "1.0.0"


def _as_dict(r: Dict[str, Any]) -> Dict[str, Any]:
    return {"deployment_uuid": r["record_uuid"], "node_key": r[st.DP_NODE], "display_name": r[st.DP_DISPLAY],
            "role_kind": r[st.DP_ROLE], "strategy_kind": r[st.DP_STRATEGY], "zspace_uuid": r[st.DP_ZSPACE],
            "active_flag": r[st.DP_ACTIVE], "created_timestamp": r[st.DP_CREATED], "taxonomy_uuid": r[st.DP_TAXONOMY]}


def bejson_scaffold_list_deployments(manifest_path: str) -> List[Dict[str, Any]]:
    return [_as_dict(r) for r in st.read_rows(manifest_path, st.E_DEPLOYMENT)]


def bejson_scaffold_get_deployment(manifest_path: str, deployment_ref: str) -> Dict[str, Any]:
    """Look up by deployment_uuid or node_key."""
    for d in bejson_scaffold_list_deployments(manifest_path):
        if deployment_ref in (d["deployment_uuid"], d["node_key"]):
            return d
    raise st.TaxonomyError(f"deployment {deployment_ref!r} not found", "E_DEPLOYMENT_NOT_FOUND")


def bejson_scaffold_register_deployment(
    manifest_path: str, node_key: str, display_name: str, role_kind: str, strategy_kind: str, taxonomy_ref: str,
) -> str:
    """Add a LatticeDeployment row. The node references the entity's first Z-space reservation and the
    taxonomy it follows (root or variant). Returns deployment_uuid."""
    if role_kind not in st.ROLE_KINDS:
        raise st.TaxonomyError(f"role_kind must be one of {st.ROLE_KINDS}", "E_ROLE")
    if strategy_kind not in st.STRATEGY_KINDS:
        raise st.TaxonomyError(f"strategy_kind must be one of {st.STRATEGY_KINDS}", "E_STRATEGY")
    if not node_key or any(d["node_key"] == node_key for d in bejson_scaffold_list_deployments(manifest_path)):
        raise st.TaxonomyError(f"node_key {node_key!r} is empty or already registered", "E_NODE_KEY")
    taxonomy = reg.bejson_taxonomies_get_taxonomy(manifest_path, taxonomy_ref)
    slot = zsa.bejson_scaffold_find_slot(manifest_path, st.E_DEPLOYMENT)
    if slot is None:
        raise st.TaxonomyError(f"{st.E_DEPLOYMENT} has no Z-space reservation", "E_ZSPACE_MISSING")
    return st.add_row(manifest_path, st.E_DEPLOYMENT, st.build_row(
        manifest_path, st.E_DEPLOYMENT,
        **{st.DP_NODE: node_key, st.DP_DISPLAY: display_name, st.DP_ROLE: role_kind, st.DP_STRATEGY: strategy_kind,
           st.DP_ZSPACE: slot["reservation_uuid"], st.DP_ACTIVE: True, st.DP_CREATED: st.now_utc(),
           st.DP_TAXONOMY: taxonomy["taxonomy_uuid"]}))


def bejson_scaffold_set_deployment_active(manifest_path: str, deployment_ref: str, active_flag: bool) -> None:
    d = bejson_scaffold_get_deployment(manifest_path, deployment_ref)
    mfdb_core_update_entity_record_105(manifest_path, st.E_DEPLOYMENT, d["deployment_uuid"], st.DP_ACTIVE, bool(active_flag))


def bejson_scaffold_set_network_role(manifest_path: str, network_role: str) -> None:
    """Set the manifest's Network_Role header (Master | Slave) atomically."""
    if network_role not in ("Master", "Slave"):
        raise st.TaxonomyError(f"network_role must be Master or Slave, got {network_role!r}", "E_NETWORK_ROLE")
    with st.entity_lock(manifest_path):
        doc = bejson_core_load_file(manifest_path)
        doc["Network_Role"] = network_role
        st.write_doc(doc, manifest_path)
