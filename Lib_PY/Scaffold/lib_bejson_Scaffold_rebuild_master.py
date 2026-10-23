"""
File Name : lib_bejson_Scaffold_rebuild_master.py
Rel. Path : Lib_PY/Scaffold/lib_bejson_Scaffold_rebuild_master.py
Purpose   : Deploy a node by REBUILDING it from a taxonomy definition: fresh lattice registry, the root
            taxonomy (or a variant derived from it), the node's deployment row (strategy 'rebuild'),
            Network_Role, and (masters) Core's ConnectedSlave registry. Gated by a full audit.
VERSION   : 1.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : 6e02b8a9-4f71-4d35-9c0e-b81a73d5e260
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
import lib_bejson_Taxonomies_schema_builder as sb  # noqa: E402
import lib_bejson_Taxonomies_taxonomy_registry as reg  # noqa: E402
import lib_bejson_Taxonomies_uuid_tracker as trk  # noqa: E402
import lib_bejson_Scaffold_deployment_registry as dep  # noqa: E402
from lib_bejson_Core_mfdb_core import mfdb_core_create_connected_slave_entity  # noqa: E402

logger = logging.getLogger(__name__)
VERSION = "1.0.0"


class ScaffoldError(st.TaxonomyError):
    def __init__(self, message: str, problems: Optional[List[str]] = None):
        super().__init__(message, "E_SCAFFOLD")
        self.problems = problems or []


def bejson_scaffold_deploy_rebuild(
    root_dir: str, node_key: str, display_name: str, role_kind: str = "master",
    taxonomy_namespace: str = st.ROOT_NAMESPACE,
    suffix_overrides: Optional[Dict[str, Any]] = None, suffix_removals: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a new node from scratch under `root_dir`. If `taxonomy_namespace` differs from the root
    namespace, a variant is derived from the root taxonomy (with the given suffix overrides/removals)
    and the node follows it. Returns {manifest_path, deployment_uuid, taxonomy_uuid, role_kind, strategy_kind}."""
    if role_kind not in st.ROLE_KINDS:
        raise st.TaxonomyError(f"role_kind must be one of {st.ROLE_KINDS}", "E_ROLE")
    manifest = sb.bejson_taxonomies_build_registry_database(
        root_dir, network_role="Master" if role_kind == "master" else "Slave")
    if taxonomy_namespace == st.ROOT_NAMESPACE:
        if suffix_overrides or suffix_removals:
            raise st.TaxonomyError("suffix overrides need a variant namespace; the root taxonomy is fixed", "E_TAXONOMY_ROOT")
        taxonomy_uuid = reg.bejson_taxonomies_get_taxonomy(manifest, st.ROOT_NAMESPACE)["taxonomy_uuid"]
    else:
        taxonomy_uuid = reg.bejson_taxonomies_derive_variant(
            manifest, st.ROOT_NAMESPACE, taxonomy_namespace, suffix_overrides, suffix_removals)
    deployment_uuid = dep.bejson_scaffold_register_deployment(
        manifest, node_key, display_name, role_kind, "rebuild", taxonomy_uuid)
    if role_kind == "master":
        mfdb_core_create_connected_slave_entity(manifest)
    trk.bejson_taxonomies_stamp_audit(manifest)
    report = trk.bejson_taxonomies_audit_database(manifest)
    if not report["passed"]:
        raise ScaffoldError(f"rebuilt node {node_key!r} failed audit", report["problems"])
    return {"manifest_path": manifest, "deployment_uuid": deployment_uuid, "taxonomy_uuid": taxonomy_uuid,
            "role_kind": role_kind, "strategy_kind": "rebuild"}


def bejson_scaffold_deploy_master_rebuild(root_dir: str, node_key: str, display_name: str, **kwargs: Any) -> Dict[str, Any]:
    return bejson_scaffold_deploy_rebuild(root_dir, node_key, display_name, role_kind="master", **kwargs)


def bejson_scaffold_deploy_slave_rebuild(root_dir: str, node_key: str, display_name: str, **kwargs: Any) -> Dict[str, Any]:
    return bejson_scaffold_deploy_rebuild(root_dir, node_key, display_name, role_kind="slave", **kwargs)
