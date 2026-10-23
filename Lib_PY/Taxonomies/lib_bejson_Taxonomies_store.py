"""
File Name : lib_bejson_Taxonomies_store.py
Rel. Path : Lib_PY/Taxonomies/lib_bejson_Taxonomies_store.py
Purpose   : Shared internals for the lib_bejson_Taxonomies and lib_bejson_Scaffold families:
            entity/field-name constants of the `lattice` registry contract, error types,
            and thin row/lock helpers built ONLY on public lib_bejson_Core primitives.
            Not a public API surface; other modules re-export what they need.
VERSION   : 1.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : c4e81f07-9a2d-4b53-8d16-7f0a3e5b92c1
"""
from __future__ import annotations

import logging
import os
import re
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional

# Sibling family directories (Lib_PY/Core, Lib_PY/Taxonomies, Lib_PY/Scaffold) are resolved
# relative to this file; nothing is hardcoded.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _fam in ("Core", "Taxonomies", "Scaffold"):
    _p = os.path.normpath(os.path.join(_HERE, "..", _fam))
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

from lib_bejson_Core_bejson_core import (  # noqa: E402
    ResilientPIDLock,
    bejson_core_atomic_write,
    bejson_core_get_field_map,
)
from lib_bejson_Core_mfdb_core import (  # noqa: E402
    mfdb_core_add_entity_record_105,
    mfdb_core_get_entity_doc,
    mfdb_core_load_manifest,
)

logger = logging.getLogger(__name__)

VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Taxonomy constants
# ---------------------------------------------------------------------------
ROOT_NAMESPACE = "lattice"
VALID_FIELD_TYPES = ("string", "integer", "number", "boolean", "array", "object")
REQUIRED_SUFFIXES = ("_uuid_fk", "_slot")
SLOT_SUFFIX = "_slot"
FK_SUFFIX = "_uuid_fk"
MATCH_KINDS = ("identical", "variant")
ROLE_KINDS = ("master", "slave")
STRATEGY_KINDS = ("rebuild", "prebuilt")
ZSTATE_RESERVED = "reserved"
ZSTATE_BOUND = "bound"
LIFECYCLE_ACTIVE = "active"
LIFECYCLE_RETIRED = "retired"
CORE_OWNED_ENTITIES = ("ConnectedSlave",)  # Core-defined schema; exempt from taxonomy audit
UUID4_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
NAMESPACE_RE = re.compile(r"^[a-z][a-z0-9]{0,23}$")
SUFFIX_TOKEN_RE = re.compile(r"^_[a-z][a-z0-9_]*$")
FIELD_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")

# suffix token -> (BEJSON type, meaning)
DEFAULT_SUFFIX_RULES: Dict[str, tuple] = {
    "_uuid_fk":   ("string",  "foreign key to another row's record_uuid"),
    "_timestamp": ("string",  "ISO-8601 UTC timestamp"),
    "_metric":    ("integer", "count or measure"),
    "_flag":      ("boolean", "on/off state"),
    "_uuid":      ("string",  "tracked UUID value (not a foreign key)"),
    "_slot":      ("string",  "reserved, unbound Z-space column"),
    "_key":       ("string",  "natural identifier"),
    "_name":      ("string",  "display label"),
    "_kind":      ("string",  "enumerated value"),
}

# ---------------------------------------------------------------------------
# Registry entity + field names (the lattice data contract)
# ---------------------------------------------------------------------------
E_TAXONOMY = "LatticeTaxonomy"
E_SUFFIX = "LatticeSuffixRule"
E_FIELD = "LatticeFieldEntry"
E_DEPLOYMENT = "LatticeDeployment"
E_ZSPACE = "LatticeZSpace"
E_LINK = "LatticeFederationLink"

# LatticeTaxonomy
TX_NAMESPACE = "lattice_taxonomy_namespace_key"
TX_FAMILY = "lattice_taxonomy_family_name"
TX_PREFIX = "lattice_taxonomy_prefix_key"
TX_COUNT = "lattice_taxonomy_field_count_metric"
TX_ZFLAG = "lattice_taxonomy_zspace_flag"
TX_AUDIT = "lattice_taxonomy_audit_timestamp"
TX_PARENT = "lattice_taxonomy_parent_uuid_fk"
# LatticeSuffixRule
SX_TOKEN = "lattice_suffix_token_key"
SX_TYPE = "lattice_suffix_field_type_kind"
SX_MEANING = "lattice_suffix_meaning_name"
SX_TAXONOMY = "lattice_suffix_taxonomy_uuid_fk"
# LatticeFieldEntry
FE_COLUMN = "lattice_field_column_name_key"
FE_UUID = "lattice_field_tracked_uuid"
FE_ENTITY = "lattice_field_parent_entity_name"
FE_TAXONOMY = "lattice_field_taxonomy_uuid_fk"
FE_RULE = "lattice_field_suffix_rule_uuid_fk"
FE_LIFECYCLE = "lattice_field_lifecycle_kind"
FE_RETIRED = "lattice_field_retired_timestamp"
# LatticeDeployment
DP_NODE = "lattice_deployment_node_key"
DP_DISPLAY = "lattice_deployment_display_name"
DP_ROLE = "lattice_deployment_role_kind"
DP_STRATEGY = "lattice_deployment_strategy_kind"
DP_ZSPACE = "lattice_deployment_zspace_uuid_fk"
DP_ACTIVE = "lattice_deployment_active_flag"
DP_CREATED = "lattice_deployment_created_timestamp"
DP_TAXONOMY = "lattice_deployment_taxonomy_uuid_fk"
DP_SLOT = "lattice_zspace_01_reserved_slot"
DP_FEDERATION_BOUND = "lattice_deployment_federation_uuid_fk"
# LatticeZSpace
ZS_ENTITY = "lattice_zspace_target_entity_name"
ZS_FIELD_UUID = "lattice_zspace_slot_field_uuid"
ZS_ORDINAL = "lattice_zspace_slot_ordinal_metric"
ZS_STATE = "lattice_zspace_state_kind"
ZS_BOUND = "lattice_zspace_bound_field_name"
ZS_ALLOCATED = "lattice_zspace_allocated_timestamp"
# LatticeFederationLink
LK_KEY = "lattice_federation_link_key"
LK_MASTER = "lattice_federation_master_uuid_fk"
LK_SLAVE = "lattice_federation_slave_uuid_fk"
LK_PROTOCOL = "lattice_federation_protocol_kind"
LK_INTERVAL = "lattice_federation_interval_metric"
LK_HEALTHY = "lattice_federation_healthy_flag"
LK_SYNC = "lattice_federation_sync_timestamp"
LK_MATCH = "lattice_federation_taxonomy_match_kind"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class TaxonomyError(Exception):
    """Base error for lib_bejson_Taxonomies / lib_bejson_Scaffold. `.code` is a stable string."""

    def __init__(self, message: str, code: str = "E_TAXONOMY"):
        super().__init__(message)
        self.code = code


class TaxonomyComplianceError(TaxonomyError):
    def __init__(self, message: str, problems: Optional[List[str]] = None):
        super().__init__(message, "E_TAXONOMY_COMPLIANCE")
        self.problems = problems or []


# ---------------------------------------------------------------------------
# Helpers over public Core primitives
# ---------------------------------------------------------------------------
def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def entity_path(manifest_path: str, entity_name: str) -> str:
    """Resolve an entity file path from the manifest (relative to the manifest directory)."""
    for entry in mfdb_core_load_manifest(manifest_path):
        if entry["entity_name"] == entity_name:
            return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(manifest_path)), entry["file_path"]))
    raise TaxonomyError(f"entity {entity_name!r} is not in manifest {manifest_path}", "E_ENTITY_NOT_FOUND")


def manifest_entity_names(manifest_path: str) -> List[str]:
    return [e["entity_name"] for e in mfdb_core_load_manifest(manifest_path)]


def read_rows(manifest_path: str, entity_name: str) -> List[Dict[str, Any]]:
    """All rows of a 105 entity as dicts keyed by field name, plus 'record_uuid'.
    Positions come from Core's field-map cache; no positional literals."""
    doc = mfdb_core_get_entity_doc(manifest_path, entity_name)
    fmap = bejson_core_get_field_map(doc)
    out = []
    for row in doc.get("Values", []):
        item = {name: row[idx] for name, idx in fmap.items()}
        item["record_uuid"] = row[0]
        out.append(item)
    return out


def add_row(manifest_path: str, entity_name: str, values: list) -> str:
    """Append a row through Core (FK-checked when Ref_Integrity is on). Returns the new record_uuid."""
    doc = mfdb_core_add_entity_record_105(manifest_path, entity_name, values)
    return doc["Values"][-1][0]


def build_row(manifest_path: str, entity_name: str, **named: Any) -> list:
    """Order named values by the entity's declared Fields (unnamed fields become None)."""
    doc = mfdb_core_get_entity_doc(manifest_path, entity_name)
    unknown = set(named) - {f["name"] for f in doc["Fields"]}
    if unknown:
        raise TaxonomyError(f"{entity_name}: unknown fields {sorted(unknown)}", "E_UNKNOWN_FIELD")
    return [named.get(f["name"]) for f in doc["Fields"]]


@contextmanager
def entity_lock(path: str) -> Iterator[None]:
    with ResilientPIDLock(path, timeout_seconds=10):
        yield


def write_doc(doc: dict, path: str) -> None:
    if not bejson_core_atomic_write(path, doc):
        raise TaxonomyError(f"atomic write failed: {path}", "E_WRITE_FAILED")
