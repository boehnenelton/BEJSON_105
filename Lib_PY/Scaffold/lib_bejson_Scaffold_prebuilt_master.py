"""
File Name : lib_bejson_Scaffold_prebuilt_master.py
Rel. Path : Lib_PY/Scaffold/lib_bejson_Scaffold_prebuilt_master.py
Purpose   : Deploy a node from a PREBUILT snapshot (master or slave). A snapshot is a captured lattice
            database with its instance rows (deployments, links, ConnectedSlave) removed, keeping schema,
            taxonomies, suffix rules, field ledger, Z-space reservations and any seeded domain rows.
            Field_uuids and seed record_uuids are preserved, so nodes cut from one snapshot share column
            fingerprints. A snapshot may carry its own (variant) taxonomy; the deployment records which
            taxonomy it follows. Gated by a full audit, before capture and after deployment.
VERSION   : 1.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : f93a1c60-8d27-4e5b-a014-6c7d2b9e3a85
"""
from __future__ import annotations

import logging
import os
import shutil
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
import lib_bejson_Scaffold_deployment_registry as dep  # noqa: E402
from lib_bejson_Scaffold_rebuild_master import ScaffoldError  # noqa: E402
from lib_bejson_Core_bejson_core import bejson_core_load_file  # noqa: E402
from lib_bejson_Core_mfdb_core import (  # noqa: E402
    mfdb_core_create_connected_slave_entity,
    mfdb_core_sync_all_counts,
)

logger = logging.getLogger(__name__)
VERSION = "1.0.0"
MANIFEST_NAME = "104a.mfdb.bejson"
_IGNORE = shutil.ignore_patterns("*.lock", "*.tmp", "__pycache__", ".git")
INSTANCE_ENTITIES = (st.E_LINK, st.E_DEPLOYMENT, "ConnectedSlave")  # link first: it references deployments


def _require_empty(target_dir: str) -> None:
    if os.path.exists(target_dir) and os.listdir(target_dir):
        raise ScaffoldError(f"target directory is not empty: {target_dir}")


def _clear_rows(manifest_path: str, entity_name: str) -> None:
    if entity_name not in st.manifest_entity_names(manifest_path):
        return
    path = st.entity_path(manifest_path, entity_name)
    with st.entity_lock(path):
        doc = bejson_core_load_file(path)
        doc["Values"] = []
        st.write_doc(doc, path)


def bejson_scaffold_capture_snapshot(source_manifest_path: str, snapshot_dir: str) -> str:
    """Copy a lattice database to `snapshot_dir`, strip instance rows, and audit the result.
    The source must itself pass audit. Returns the snapshot's manifest path."""
    source_report = trk.bejson_taxonomies_audit_database(source_manifest_path)
    if not source_report["passed"]:
        raise ScaffoldError("source database failed audit; refusing to snapshot", source_report["problems"])
    _require_empty(snapshot_dir)
    shutil.copytree(os.path.dirname(os.path.abspath(source_manifest_path)), snapshot_dir, ignore=_IGNORE, dirs_exist_ok=True)
    manifest = os.path.join(snapshot_dir, MANIFEST_NAME)
    for entity in INSTANCE_ENTITIES:
        _clear_rows(manifest, entity)
    mfdb_core_sync_all_counts(manifest)
    report = trk.bejson_taxonomies_audit_database(manifest)
    if not report["passed"]:
        raise ScaffoldError("snapshot failed audit", report["problems"])
    return manifest


def _pick_taxonomy(manifest_path: str, taxonomy_ref: Optional[str]) -> str:
    taxa = reg.bejson_taxonomies_list_taxonomies(manifest_path)
    if taxonomy_ref is not None:
        return reg.bejson_taxonomies_get_taxonomy(manifest_path, taxonomy_ref)["taxonomy_uuid"]
    if len(taxa) == 1:
        return taxa[0]["taxonomy_uuid"]
    raise st.TaxonomyError(
        f"snapshot holds {len(taxa)} taxonomies ({', '.join(t['namespace_key'] for t in taxa)}); pass taxonomy_ref",
        "E_TAXONOMY_AMBIGUOUS")


def bejson_scaffold_deploy_prebuilt(
    snapshot_dir: str, target_dir: str, node_key: str, display_name: str,
    role_kind: str = "master", taxonomy_ref: Optional[str] = None,
) -> Dict[str, Any]:
    """Instantiate a node from a snapshot (master or slave). `taxonomy_ref` names the taxonomy the node
    follows (uuid or namespace); optional only when the snapshot holds exactly one."""
    if role_kind not in st.ROLE_KINDS:
        raise st.TaxonomyError(f"role_kind must be one of {st.ROLE_KINDS}", "E_ROLE")
    snap_manifest = os.path.join(snapshot_dir, MANIFEST_NAME)
    if not os.path.isfile(snap_manifest):
        raise ScaffoldError(f"no snapshot manifest in {snapshot_dir}")
    taxonomy_uuid = _pick_taxonomy(snap_manifest, taxonomy_ref)
    _require_empty(target_dir)
    shutil.copytree(snapshot_dir, target_dir, ignore=_IGNORE, dirs_exist_ok=True)
    manifest = os.path.join(target_dir, MANIFEST_NAME)
    try:
        dep.bejson_scaffold_set_network_role(manifest, "Master" if role_kind == "master" else "Slave")
        deployment_uuid = dep.bejson_scaffold_register_deployment(
            manifest, node_key, display_name, role_kind, "prebuilt", taxonomy_uuid)
        if role_kind == "master" and "ConnectedSlave" not in st.manifest_entity_names(manifest):
            mfdb_core_create_connected_slave_entity(manifest)
        trk.bejson_taxonomies_stamp_audit(manifest)
        report = trk.bejson_taxonomies_audit_database(manifest)
        if not report["passed"]:
            raise ScaffoldError(f"prebuilt node {node_key!r} failed audit", report["problems"])
    except Exception:
        logger.exception("prebuilt deployment failed; removing %s", target_dir)
        shutil.rmtree(target_dir, ignore_errors=True)
        raise
    return {"manifest_path": manifest, "deployment_uuid": deployment_uuid, "taxonomy_uuid": taxonomy_uuid,
            "role_kind": role_kind, "strategy_kind": "prebuilt"}


def bejson_scaffold_deploy_master_prebuilt(snapshot_dir: str, target_dir: str, node_key: str, display_name: str, **kwargs: Any) -> Dict[str, Any]:
    return bejson_scaffold_deploy_prebuilt(snapshot_dir, target_dir, node_key, display_name, role_kind="master", **kwargs)


def bejson_scaffold_deploy_slave_prebuilt(snapshot_dir: str, target_dir: str, node_key: str, display_name: str, **kwargs: Any) -> Dict[str, Any]:
    return bejson_scaffold_deploy_prebuilt(snapshot_dir, target_dir, node_key, display_name, role_kind="slave", **kwargs)
