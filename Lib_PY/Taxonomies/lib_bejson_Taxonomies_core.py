"""
File Name : lib_bejson_Taxonomies_core.py
Rel. Path : Lib_PY/Taxonomies/lib_bejson_Taxonomies_core.py
Purpose   : Taxonomies CORE: everything that reads or writes the registry (constants and helpers, taxonomies, field_uuid ledger, schema builder, field-set writes). Checks live in _validator.
VERSION   : 3.1.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : 5a9e2c14-8b73-4f10-9a35-1c4d8e20f115
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional, Union

# Sibling family directories (Lib_PY/Core, Lib_PY/Taxonomies, Lib_PY/Tax_Scaffolds) resolve relative to this file; nothing is hardcoded.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _fam in ('Core', 'Taxonomies', 'Tax_Scaffolds'):
    _p = os.path.normpath(os.path.join(_HERE, "..", _fam))
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

from lib_bejson_Core_bejson_core import (  # noqa: E402
    ResilientPIDLock,
    bejson_core_atomic_write,
    bejson_core_create_104a,
    bejson_core_get_field_map,
    bejson_core_load_file,
)
from lib_bejson_Core_mfdb_core import (  # noqa: E402
    mfdb_core_add_entity_record_105,
    mfdb_core_create_database,
    mfdb_core_delete_entity_record_105,
    mfdb_core_enable_ref_integrity,
    mfdb_core_get_entity_doc,
    mfdb_core_load_manifest,
    mfdb_core_update_entity_record_105,
)

logger = logging.getLogger(__name__)
VERSION = "3.1.0"

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
FIELDSET_STATES = ("active", "retired")
ZSTATE_RESERVED = "reserved"
ZSTATE_BOUND = "bound"
LIFECYCLE_ACTIVE = "active"
LIFECYCLE_RETIRED = "retired"
CORE_OWNED_ENTITIES = ("ConnectedSlave",)  # Core-defined schema; exempt from taxonomy audit
UUID4_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z")
NAMESPACE_RE = re.compile(r"^[a-z][a-z0-9]{0,23}\Z")
SUFFIX_TOKEN_RE = re.compile(r"^_[a-z][a-z0-9_]*\Z")
FIELD_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*\Z")
SET_KEY_RE = re.compile(r"^(?=.{1,64}\Z)[a-z][a-z0-9]*(_[a-z0-9]+)*\Z")        # field set key, e.g. media_asset
DESCRIPTOR_RE = re.compile(r"^(?=.{1,48}\Z)[a-z][a-z0-9]*(_[a-z0-9]+)*\Z")     # member descriptor, e.g. created
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
    "_amount":    ("number",  "monetary or decimal quantity"),
    "_ratio":     ("number",  "fractional or normalized ratio"),
    "_date":      ("string",  "ISO-8601 calendar date"),
    "_duration":  ("number",  "elapsed time duration"),
    "_hash":      ("string",  "cryptographic or content digest"),
    "_json":      ("string",  "serialized JSON payload"),
    "_list":      ("array",   "ordered collection of values"),
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
E_FIELDSET = "LatticeFieldSet"
E_SETMEMBER = "LatticeFieldSetMember"
E_GRAFT = "LatticeFieldGraft"
REGISTRY_ENTITIES = (E_TAXONOMY, E_SUFFIX, E_FIELD, E_DEPLOYMENT, E_ZSPACE, E_LINK, E_FIELDSET, E_SETMEMBER, E_GRAFT)
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
FE_GRAFT = "lattice_field_graft_uuid_fk"
FE_SETMEMBER = "lattice_field_setmember_uuid_fk"
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
# LatticeFieldSet (immutable per (set_key, version))
FS_KEY = "lattice_fieldset_set_key"
FS_NAME = "lattice_fieldset_display_name"
FS_VERSION = "lattice_fieldset_version_metric"
FS_STATE = "lattice_fieldset_state_kind"
FS_CREATED = "lattice_fieldset_created_timestamp"
# LatticeFieldSetMember
SM_DESCRIPTOR = "lattice_setmember_descriptor_key"
SM_SET = "lattice_setmember_set_uuid_fk"
SM_SUFFIX = "lattice_setmember_suffix_key"
SM_TYPE = "lattice_setmember_field_type_kind"
SM_ORDER = "lattice_setmember_order_metric"
# LatticeFieldGraft (a field set stamped onto an entity)
GR_KEY = "lattice_graft_entity_set_key"
GR_SET = "lattice_graft_set_uuid_fk"
GR_ENTITY = "lattice_graft_target_entity_name"
GR_SUBJECT = "lattice_graft_subject_key"
GR_TAXONOMY = "lattice_graft_taxonomy_uuid_fk"
GR_APPLIED = "lattice_graft_applied_timestamp"
# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class TaxonomyError(Exception):
    """Base error for lib_bejson_Taxonomies / lib_bejson_Tax_Scaffolds. `.code` is a stable string."""

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

RuleSpec = Union[str, tuple, list]
# ---------------------------------------------------------------------------
# Rule normalisation / validation
# ---------------------------------------------------------------------------
def _normalise_rules(rules: Dict[str, RuleSpec]) -> Dict[str, tuple]:
    """token -> 'type' | (type, meaning)  ==>  token -> (type, meaning). Validates everything."""
    out: Dict[str, tuple] = {}
    for token, spec in rules.items():
        if not SUFFIX_TOKEN_RE.match(token):
            raise TaxonomyError(f"suffix token {token!r} must look like '_name'", "E_SUFFIX_TOKEN")
        ftype, meaning = (spec, "") if isinstance(spec, str) else (spec[0], spec[1] if len(spec) > 1 else "")
        if ftype not in VALID_FIELD_TYPES:
            raise TaxonomyError(f"suffix {token}: type {ftype!r} not in {VALID_FIELD_TYPES}", "E_SUFFIX_TYPE")
        out[token] = (ftype, meaning)
    for req in REQUIRED_SUFFIXES:
        if req not in out:
            raise TaxonomyError(f"required suffix {req} is missing", "E_SUFFIX_REQUIRED")
        if out[req][0] != "string":
            raise TaxonomyError(f"required suffix {req} must be type string", "E_SUFFIX_TYPE")
    return out
# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------
def bejson_taxonomies_list_taxonomies(manifest_path: str) -> List[Dict[str, Any]]:
    taxa = []
    rules_by_tax: Dict[str, Dict[str, Dict[str, str]]] = {}
    for r in read_rows(manifest_path, E_SUFFIX):
        rules_by_tax.setdefault(r[SX_TAXONOMY], {})[r[SX_TOKEN]] = {
            "field_type": r[SX_TYPE], "meaning": r[SX_MEANING], "rule_uuid": r["record_uuid"]}
    for r in read_rows(manifest_path, E_TAXONOMY):
        taxa.append({
            "taxonomy_uuid": r["record_uuid"],
            "namespace_key": r[TX_NAMESPACE],
            "family_name": r[TX_FAMILY],
            "prefix_key": r[TX_PREFIX],
            "field_count": r[TX_COUNT],
            "zspace_flag": r[TX_ZFLAG],
            "audit_timestamp": r[TX_AUDIT],
            "parent_taxonomy_uuid": r[TX_PARENT],
            "suffix_rules": rules_by_tax.get(r["record_uuid"], {}),
        })
    return taxa
def bejson_taxonomies_get_taxonomy(manifest_path: str, taxonomy_ref: str) -> Dict[str, Any]:
    """Look up by taxonomy_uuid or namespace_key."""
    for t in bejson_taxonomies_list_taxonomies(manifest_path):
        if taxonomy_ref in (t["taxonomy_uuid"], t["namespace_key"]):
            return t
    raise TaxonomyError(f"taxonomy {taxonomy_ref!r} not found", "E_TAXONOMY_NOT_FOUND")
# ---------------------------------------------------------------------------
# Name checks
# ---------------------------------------------------------------------------
def bejson_taxonomies_match_suffix(taxonomy: Dict[str, Any], field_name: str) -> Optional[str]:
    """Longest registered suffix that ends field_name, or None."""
    for token in sorted(taxonomy["suffix_rules"], key=len, reverse=True):
        if field_name.endswith(token):
            return token
    return None
def bejson_taxonomies_check_field_name(taxonomy: Dict[str, Any], field_name: str, field_type: str) -> List[str]:
    """Problems (empty list = compliant) for one field against one taxonomy."""
    problems: List[str] = []
    prefix = taxonomy["prefix_key"]
    if not FIELD_NAME_RE.match(field_name):
        problems.append(f"{field_name!r}: not snake_case [a-z0-9_]")
    if not field_name.startswith(prefix):
        problems.append(f"{field_name!r}: missing prefix {prefix!r}")
    token = bejson_taxonomies_match_suffix(taxonomy, field_name)
    if token is None:
        problems.append(f"{field_name!r}: no suffix registered by taxonomy {taxonomy['namespace_key']!r}")
    else:
        want = taxonomy["suffix_rules"][token]["field_type"]
        if field_type != want:
            problems.append(f"{field_name!r}: type {field_type!r} but suffix {token} requires {want!r}")
        if field_name.startswith(prefix) and len(field_name) <= len(prefix) + len(token):
            problems.append(f"{field_name!r}: no descriptor between prefix and suffix")
    return problems
def bejson_taxonomies_check_entity_name(taxonomy: Dict[str, Any], entity_name: str) -> List[str]:
    ns = taxonomy["namespace_key"]
    if entity_name[:len(ns)].lower() != ns or not entity_name[:1].isupper():
        return [f"entity {entity_name!r}: must start with capitalised namespace {ns.capitalize()!r}"]
    return []
# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------
def bejson_taxonomies_create_taxonomy(
    manifest_path: str,
    namespace_key: str,
    suffix_rules: Optional[Dict[str, RuleSpec]] = None,
    family_name: str = "",
    parent_taxonomy_uuid: Optional[str] = None,
) -> str:
    """Register a taxonomy. Prefix is always `<namespace>_`. Returns the taxonomy_uuid.
    suffix_rules defaults to the lattice defaults; `_uuid_fk` and `_slot` (string) are mandatory."""
    if not NAMESPACE_RE.match(namespace_key):
        raise TaxonomyError(f"namespace {namespace_key!r} must match {NAMESPACE_RE.pattern}", "E_NAMESPACE")
    prefix = f"{namespace_key}_"
    rules = _normalise_rules(suffix_rules if suffix_rules is not None else DEFAULT_SUFFIX_RULES)

    existing = bejson_taxonomies_list_taxonomies(manifest_path)
    for t in existing:
        if t["namespace_key"] == namespace_key:
            raise TaxonomyError(f"namespace {namespace_key!r} already registered", "E_NAMESPACE_EXISTS")
        if t["prefix_key"].startswith(prefix) or prefix.startswith(t["prefix_key"]):
            raise TaxonomyError(
                f"prefix {prefix!r} is ambiguous with existing prefix {t['prefix_key']!r}", "E_PREFIX_AMBIGUOUS")
    if parent_taxonomy_uuid is not None and parent_taxonomy_uuid not in {t["taxonomy_uuid"] for t in existing}:
        raise TaxonomyError(f"parent taxonomy {parent_taxonomy_uuid!r} not found", "E_TAXONOMY_NOT_FOUND")

    taxonomy_uuid = add_row(manifest_path, E_TAXONOMY, build_row(
        manifest_path, E_TAXONOMY,
        **{TX_NAMESPACE: namespace_key, TX_FAMILY: family_name or namespace_key, TX_PREFIX: prefix,
           TX_COUNT: 0, TX_ZFLAG: SLOT_SUFFIX in rules, TX_AUDIT: now_utc(),
           TX_PARENT: parent_taxonomy_uuid}))
    created_rules: List[str] = []
    try:
        for token, (ftype, meaning) in rules.items():
            created_rules.append(add_row(manifest_path, E_SUFFIX, build_row(
                manifest_path, E_SUFFIX,
                **{SX_TOKEN: token, SX_TYPE: ftype, SX_MEANING: meaning or token,
                   SX_TAXONOMY: taxonomy_uuid})))
    except Exception:
        logger.exception("create_taxonomy failed mid-way; rolling back %s", namespace_key)
        for rule_uuid in created_rules:
            mfdb_core_delete_entity_record_105(manifest_path, E_SUFFIX, rule_uuid)
        mfdb_core_delete_entity_record_105(manifest_path, E_TAXONOMY, taxonomy_uuid)
        raise
    return taxonomy_uuid
def bejson_taxonomies_derive_variant(
    manifest_path: str,
    parent_taxonomy_ref: str,
    namespace_key: str,
    suffix_overrides: Optional[Dict[str, RuleSpec]] = None,
    suffix_removals: Optional[List[str]] = None,
    family_name: Optional[str] = None,
) -> str:
    """Copy a parent taxonomy under a new namespace, then add/replace (`suffix_overrides`) and
    drop (`suffix_removals`) suffix rules. The required suffixes can be replaced but not dropped."""
    parent = bejson_taxonomies_get_taxonomy(manifest_path, parent_taxonomy_ref)
    rules: Dict[str, RuleSpec] = {tok: (r["field_type"], r["meaning"]) for tok, r in parent["suffix_rules"].items()}
    for token in suffix_removals or []:
        if token not in rules:
            raise TaxonomyError(f"cannot remove unknown suffix {token!r}", "E_SUFFIX_UNKNOWN")
        del rules[token]
    rules.update(suffix_overrides or {})
    return bejson_taxonomies_create_taxonomy(
        manifest_path, namespace_key, rules,
        family_name=family_name or f"{parent['family_name']} (variant {namespace_key})",
        parent_taxonomy_uuid=parent["taxonomy_uuid"])
def bejson_taxonomies_diff_taxonomies(manifest_path: str, taxonomy_ref_a: str, taxonomy_ref_b: str) -> Dict[str, Any]:
    a = bejson_taxonomies_get_taxonomy(manifest_path, taxonomy_ref_a)
    b = bejson_taxonomies_get_taxonomy(manifest_path, taxonomy_ref_b)
    ra, rb = a["suffix_rules"], b["suffix_rules"]
    only_a = sorted(set(ra) - set(rb))
    only_b = sorted(set(rb) - set(ra))
    changed = {t: (ra[t]["field_type"], rb[t]["field_type"]) for t in set(ra) & set(rb)
               if ra[t]["field_type"] != rb[t]["field_type"]}
    return {
        "prefix_a": a["prefix_key"], "prefix_b": b["prefix_key"],
        "same_prefix": a["prefix_key"] == b["prefix_key"],
        "suffix_only_in_a": only_a, "suffix_only_in_b": only_b, "suffix_type_changed": changed,
        "identical": a["prefix_key"] == b["prefix_key"] and not only_a and not only_b and not changed,
        "a_is_parent_of_b": b["parent_taxonomy_uuid"] == a["taxonomy_uuid"],
        "b_is_parent_of_a": a["parent_taxonomy_uuid"] == b["taxonomy_uuid"],
    }
def bejson_taxonomies_delete_taxonomy(manifest_path: str, taxonomy_ref: str) -> None:
    """Delete a taxonomy and its suffix rules. Refused while any ledger row or deployment uses it.
    Variants derived from it are detached (parent set to null by this function; Core does not do it for self-FKs)."""
    t = bejson_taxonomies_get_taxonomy(manifest_path, taxonomy_ref)
    uid = t["taxonomy_uuid"]
    users = [r for r in read_rows(manifest_path, E_FIELD) if r[FE_TAXONOMY] == uid]
    users += [r for r in read_rows(manifest_path, E_DEPLOYMENT) if r[DP_TAXONOMY] == uid]
    users += [r for r in read_rows(manifest_path, E_GRAFT) if r[GR_TAXONOMY] == uid]
    if users:
        raise TaxonomyError(f"taxonomy {t['namespace_key']!r} is in use by {len(users)} row(s)", "E_TAXONOMY_IN_USE")
    # Core's null-on-delete scan skips an entity's own FKs, so a self-referencing parent link is not
    # cleared by it. Detach variants explicitly (public update API) before deleting the parent.
    for child in bejson_taxonomies_list_taxonomies(manifest_path):
        if child["parent_taxonomy_uuid"] == uid:
            mfdb_core_update_entity_record_105(manifest_path, E_TAXONOMY, child["taxonomy_uuid"], TX_PARENT, None)
    for rule in t["suffix_rules"].values():
        mfdb_core_delete_entity_record_105(manifest_path, E_SUFFIX, rule["rule_uuid"])
    mfdb_core_delete_entity_record_105(manifest_path, E_TAXONOMY, uid)

def _active_ledger(manifest_path: str, entity_name: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = [r for r in read_rows(manifest_path, E_FIELD) if r[FE_LIFECYCLE] == LIFECYCLE_ACTIVE]
    return [r for r in rows if entity_name is None or r[FE_ENTITY] == entity_name]
def bejson_taxonomies_track_fields(
    manifest_path: str, entity_name: str, taxonomy_ref: str, field_names: Optional[List[str]] = None,
    extras: Optional[Dict[str, Dict[str, Any]]] = None,
) -> int:
    """Ledger the given fields (default: every field not yet in the ledger) of an entity under a taxonomy.
    All names are checked first; nothing is written if any field is non-compliant. Returns rows added.
    `extras` maps a field name to extra ledger columns (the graft / set-member links of a grafted field)."""
    taxonomy = bejson_taxonomies_get_taxonomy(manifest_path, taxonomy_ref)
    doc = mfdb_core_get_entity_doc(manifest_path, entity_name)
    tracked = {r[FE_COLUMN] for r in _active_ledger(manifest_path, entity_name)}
    wanted = [f for f in doc["Fields"]
              if (f["name"] in field_names if field_names is not None else f["name"] not in tracked)]
    problems = bejson_taxonomies_check_entity_name(taxonomy, entity_name)
    for f in wanted:
        if f["name"] in tracked:
            problems.append(f"{entity_name}.{f['name']}: already tracked")
        if not UUID4_RE.match(f.get("field_uuid", "")):
            problems.append(f"{entity_name}.{f['name']}: field_uuid missing or not UUIDv4")
        problems += bejson_taxonomies_check_field_name(taxonomy, f["name"], f["type"])
    missing = set(field_names or []) - {f["name"] for f in doc["Fields"]}
    problems += [f"{entity_name}.{n}: no such field" for n in sorted(missing)]
    if problems:
        raise TaxonomyComplianceError(f"cannot track fields of {entity_name}", problems)
    for f in wanted:
        token = bejson_taxonomies_match_suffix(taxonomy, f["name"])
        add_row(manifest_path, E_FIELD, build_row(
            manifest_path, E_FIELD,
            **{FE_COLUMN: f["name"], FE_UUID: f["field_uuid"], FE_ENTITY: entity_name,
               FE_TAXONOMY: taxonomy["taxonomy_uuid"], FE_RULE: taxonomy["suffix_rules"][token]["rule_uuid"],
               FE_LIFECYCLE: LIFECYCLE_ACTIVE, FE_RETIRED: None, **(extras or {}).get(f["name"], {})}))
    return len(wanted)
def bejson_taxonomies_track_entity_fields(manifest_path: str, entity_name: str, taxonomy_ref: str) -> int:
    return bejson_taxonomies_track_fields(manifest_path, entity_name, taxonomy_ref)
def bejson_taxonomies_resolve_field_uuid(manifest_path: str, entity_name: str, field_name: str) -> str:
    doc = mfdb_core_get_entity_doc(manifest_path, entity_name)
    for f in doc["Fields"]:
        if f["name"] == field_name:
            return f["field_uuid"]
    raise TaxonomyError(f"{entity_name}: no field {field_name!r}", "E_FIELD_NOT_FOUND")
def bejson_taxonomies_resolve_field_name(manifest_path: str, entity_name: str, field_uuid: str) -> str:
    """Current name of a field by its (rename-proof) field_uuid."""
    doc = mfdb_core_get_entity_doc(manifest_path, entity_name)
    for f in doc["Fields"]:
        if f["field_uuid"] == field_uuid:
            return f["name"]
    raise TaxonomyError(f"{entity_name}: no field with field_uuid {field_uuid!r}", "E_FIELD_NOT_FOUND")
def _ledger_row(manifest_path: str, entity_name: str, field_uuid: str) -> Dict[str, Any]:
    for r in _active_ledger(manifest_path, entity_name):
        if r[FE_UUID] == field_uuid:
            return r
    raise TaxonomyError(f"{entity_name}: field_uuid {field_uuid!r} has no active ledger row", "E_LEDGER_NOT_FOUND")
def bejson_taxonomies_get_field_entry(manifest_path: str, entity_name: str, field_uuid: str) -> Dict[str, Any]:
    """The active ledger row for a field_uuid (taxonomy_uuid, column name, suffix rule, ...)."""
    row = _ledger_row(manifest_path, entity_name, field_uuid)
    return {"column_name": row[FE_COLUMN], "field_uuid": row[FE_UUID], "entity_name": entity_name,
            "taxonomy_uuid": row[FE_TAXONOMY], "suffix_rule_uuid": row[FE_RULE],
            "ledger_record_uuid": row["record_uuid"]}
def bejson_taxonomies_record_rename(manifest_path: str, entity_name: str, field_uuid: str, new_name: str) -> None:
    """Point the ledger row at a field's new name (after the entity file was renamed).
    The new name is checked against the taxonomy the ledger row belongs to."""
    row = _ledger_row(manifest_path, entity_name, field_uuid)
    taxonomy = bejson_taxonomies_get_taxonomy(manifest_path, row[FE_TAXONOMY])
    doc = mfdb_core_get_entity_doc(manifest_path, entity_name)
    fdef = next((f for f in doc["Fields"] if f["field_uuid"] == field_uuid), None)
    if fdef is None or fdef["name"] != new_name:
        raise TaxonomyError(f"{entity_name}: field {field_uuid} is not named {new_name!r} in the entity file", "E_RENAME_MISMATCH")
    problems = bejson_taxonomies_check_field_name(taxonomy, new_name, fdef["type"])
    if problems:
        raise TaxonomyComplianceError(f"rename to {new_name!r} is not compliant", problems)
    token = bejson_taxonomies_match_suffix(taxonomy, new_name)
    mfdb_core_update_entity_record_105(manifest_path, E_FIELD, row["record_uuid"], FE_COLUMN, new_name)
    mfdb_core_update_entity_record_105(manifest_path, E_FIELD, row["record_uuid"], FE_RULE,
                                       taxonomy["suffix_rules"][token]["rule_uuid"])
def bejson_taxonomies_retire_field(manifest_path: str, entity_name: str, field_uuid: str) -> None:
    row = _ledger_row(manifest_path, entity_name, field_uuid)
    mfdb_core_update_entity_record_105(manifest_path, E_FIELD, row["record_uuid"], FE_LIFECYCLE, LIFECYCLE_RETIRED)
    mfdb_core_update_entity_record_105(manifest_path, E_FIELD, row["record_uuid"], FE_RETIRED, now_utc())
def bejson_taxonomies_sync_ledger(manifest_path: str, entity_name: str) -> Dict[str, List[str]]:
    """Reconcile an entity's ledger with its file: renamed fields (same uuid, new name) are followed,
    removed fields are retired. Fields with no ledger row are reported, never auto-tracked
    (tracking needs an explicit taxonomy)."""
    doc = mfdb_core_get_entity_doc(manifest_path, entity_name)
    by_uuid = {f["field_uuid"]: f for f in doc["Fields"]}
    renamed: List[str] = []
    retired: List[str] = []
    ledgered = set()
    for row in _active_ledger(manifest_path, entity_name):
        fuuid = row[FE_UUID]
        ledgered.add(fuuid)
        fdef = by_uuid.get(fuuid)
        if fdef is None:
            bejson_taxonomies_retire_field(manifest_path, entity_name, fuuid)
            retired.append(row[FE_COLUMN])
        elif fdef["name"] != row[FE_COLUMN]:
            bejson_taxonomies_record_rename(manifest_path, entity_name, fuuid, fdef["name"])
            renamed.append(f"{row[FE_COLUMN]} -> {fdef['name']}")
    return {"renamed": renamed, "retired": retired,
            "unledgered": [f["name"] for f in doc["Fields"] if f["field_uuid"] not in ledgered]}
def bejson_taxonomies_stamp_audit(manifest_path: str) -> None:
    """Refresh each taxonomy's tracked-field count and audit timestamp."""
    counts: Dict[str, int] = {}
    for r in _active_ledger(manifest_path):
        counts[r[FE_TAXONOMY]] = counts.get(r[FE_TAXONOMY], 0) + 1
    now = now_utc()
    for t in bejson_taxonomies_list_taxonomies(manifest_path):
        uid = t["taxonomy_uuid"]
        mfdb_core_update_entity_record_105(manifest_path, E_TAXONOMY, uid, TX_COUNT, counts.get(uid, 0))
        mfdb_core_update_entity_record_105(manifest_path, E_TAXONOMY, uid, TX_AUDIT, now)
def bejson_taxonomies_audit_database(manifest_path: str) -> Dict[str, Any]:
    """Whole-registry audit (delegates to lib_bejson_Taxonomies_validator). Never raises on findings."""
    import lib_bejson_Taxonomies_validator as val  # local import keeps the validator out of the ledger's import chain
    return val.bejson_taxonomies_validator_audit_database(manifest_path)

def _f(name: str, ftype: str, fk: Optional[str] = None, on_delete: Optional[str] = None) -> Dict[str, Any]:
    d: Dict[str, Any] = {"name": name, "type": ftype}
    if fk:
        d["fk_target_entity"] = fk
    if on_delete:
        d["fk_on_delete"] = on_delete
    return d
# entity -> (owner family, description, primary key, fields). Order matters only for readability.
ENTITY_DEFS: Dict[str, tuple] = {
    E_TAXONOMY: ("Taxonomies", "Registered taxonomies. Taxonomy UUID = row record_uuid.", TX_NAMESPACE, [
        _f(TX_NAMESPACE, "string"), _f(TX_FAMILY, "string"), _f(TX_PREFIX, "string"),
        _f(TX_COUNT, "integer"), _f(TX_ZFLAG, "boolean"), _f(TX_AUDIT, "string"),
        _f(TX_PARENT, "string", E_TAXONOMY, "null"),
    ]),
    E_SUFFIX: ("Taxonomies", "Registered semantic suffixes and the BEJSON type each requires, per taxonomy.", SX_TOKEN, [
        _f(SX_TOKEN, "string"), _f(SX_TYPE, "string"), _f(SX_MEANING, "string"),
        _f(SX_TAXONOMY, "string", E_TAXONOMY, "restrict"),
    ]),
    E_FIELD: ("Taxonomies", "Field-level field_uuid ledger across all schemas.", FE_COLUMN, [
        _f(FE_COLUMN, "string"), _f(FE_UUID, "string"), _f(FE_ENTITY, "string"),
        _f(FE_TAXONOMY, "string", E_TAXONOMY, "restrict"),
        _f(FE_RULE, "string", E_SUFFIX, "restrict"),
        _f(FE_LIFECYCLE, "string"), _f(FE_RETIRED, "string"),
        _f(FE_GRAFT, "string", E_GRAFT, "restrict"),
        _f(FE_SETMEMBER, "string", E_SETMEMBER, "restrict"),
    ]),
    E_DEPLOYMENT: ("Tax_Scaffolds", "Rebuild / prebuilt node deployments (master or slave role). Trailing Z-space slot reserved for the federation link UUID.", DP_NODE, [
        _f(DP_NODE, "string"), _f(DP_DISPLAY, "string"), _f(DP_ROLE, "string"), _f(DP_STRATEGY, "string"),
        _f(DP_ZSPACE, "string", E_ZSPACE, "restrict"),
        _f(DP_ACTIVE, "boolean"), _f(DP_CREATED, "string"),
        _f(DP_TAXONOMY, "string", E_TAXONOMY, "restrict"),
        _f(DP_SLOT, "string", E_LINK, "null"),  # trailing Z-space slot, unbound
    ]),
    E_ZSPACE: ("Tax_Scaffolds", "Z-space slot reservations, addressed by field_uuid (never by positional offset).", ZS_ENTITY, [
        _f(ZS_ENTITY, "string"), _f(ZS_FIELD_UUID, "string"), _f(ZS_ORDINAL, "integer"),
        _f(ZS_STATE, "string"), _f(ZS_BOUND, "string"), _f(ZS_ALLOCATED, "string"),
    ]),
    E_LINK: ("Tax_Scaffolds", "Master/slave federation link records.", LK_KEY, [
        _f(LK_KEY, "string"),
        _f(LK_MASTER, "string", E_DEPLOYMENT, "restrict"),
        _f(LK_SLAVE, "string", E_DEPLOYMENT, "restrict"),
        _f(LK_PROTOCOL, "string"), _f(LK_INTERVAL, "integer"), _f(LK_HEALTHY, "boolean"),
        _f(LK_SYNC, "string"), _f(LK_MATCH, "string"),
    ]),
    E_FIELDSET: ("Taxonomies", "Reusable field sets, one row per (set_key, version); immutable once registered.", FS_KEY, [
        _f(FS_KEY, "string"), _f(FS_NAME, "string"), _f(FS_VERSION, "integer"),
        _f(FS_STATE, "string"), _f(FS_CREATED, "string"),
    ]),
    E_SETMEMBER: ("Taxonomies", "Members of a field set version: descriptor + suffix + type (no prefix).", SM_DESCRIPTOR, [
        _f(SM_DESCRIPTOR, "string"),
        _f(SM_SET, "string", E_FIELDSET, "restrict"),
        _f(SM_SUFFIX, "string"), _f(SM_TYPE, "string"), _f(SM_ORDER, "integer"),
    ]),
    E_GRAFT: ("Tax_Scaffolds", "A field set stamped onto an entity under that entity's taxonomy prefix.", GR_KEY, [
        _f(GR_KEY, "string"),
        _f(GR_SET, "string", E_FIELDSET, "restrict"),
        _f(GR_ENTITY, "string"), _f(GR_SUBJECT, "string"),
        _f(GR_TAXONOMY, "string", E_TAXONOMY, "restrict"),
        _f(GR_APPLIED, "string"),
    ]),
}
def bejson_taxonomies_build_registry_database(
    root_dir: str,
    db_name: str = ROOT_NAMESPACE,
    network_role: str = "Master",
) -> str:
    """Create a fresh lattice registry MFDB under `root_dir` and return its manifest path.
    Seeds: root taxonomy `lattice` + default suffix rules, field ledger for all registry fields,
    and the 'reserved' Z-space row for LatticeDeployment's trailing slot."""
    if network_role not in ("Master", "Slave"):
        raise TaxonomyError(f"network_role must be Master or Slave, got {network_role!r}", "E_NETWORK_ROLE")
    if os.path.exists(os.path.join(root_dir, "104a.mfdb.bejson")):
        raise TaxonomyError(f"a database already exists in {root_dir}", "E_DB_EXISTS")
    entities = [{"name": n, "description": d, "primary_key": pk, "fields": fields,
                 "format_version": "105", "file_path": f"data/{n.lower()}.bejson"}
                for n, (_fam, d, pk, fields) in ENTITY_DEFS.items()]
    manifest = mfdb_core_create_database(
        root_dir, db_name, entities,
        db_description="lattice taxonomy registry: lib_bejson_Tax_Scaffolds + lib_bejson_Taxonomies data contracts.",
        schema_version="1.3.0", mfdb_version="1.40", network_role=network_role)
    mfdb_core_enable_ref_integrity(manifest)

    root_uuid = bejson_taxonomies_create_taxonomy(
        manifest, ROOT_NAMESPACE, family_name="lib_bejson_Tax_Scaffolds+lib_bejson_Taxonomies")
    for ent in ENTITY_DEFS:
        bejson_taxonomies_track_entity_fields(manifest, ent, root_uuid)

    slot = next(f for f in mfdb_core_get_entity_doc(manifest, E_DEPLOYMENT)["Fields"] if f["name"] == DP_SLOT)
    add_row(manifest, E_ZSPACE, build_row(
        manifest, E_ZSPACE,
        **{ZS_ENTITY: E_DEPLOYMENT, ZS_FIELD_UUID: slot["field_uuid"], ZS_ORDINAL: 1,
           ZS_STATE: ZSTATE_RESERVED, ZS_BOUND: None, ZS_ALLOCATED: now_utc()}))
    bejson_taxonomies_stamp_audit(manifest)
    logger.info("built lattice registry at %s", manifest)
    return manifest
def bejson_taxonomies_make_field_name(taxonomy: Dict[str, Any], subject: str, descriptor: str, suffix: str) -> str:
    """`<prefix><subject>_<descriptor><suffix>`; suffix must be registered. Raises if non-compliant."""
    if suffix not in taxonomy["suffix_rules"]:
        raise TaxonomyError(f"suffix {suffix!r} not registered in taxonomy {taxonomy['namespace_key']!r}", "E_SUFFIX_UNKNOWN")
    name = f"{taxonomy['prefix_key']}{subject}_{descriptor}{suffix}".lower()
    want = taxonomy["suffix_rules"][suffix]["field_type"]
    problems = bejson_taxonomies_check_field_name(taxonomy, name, want)
    if problems:
        raise TaxonomyComplianceError(f"cannot build field name {name!r}", problems)
    return name
def bejson_taxonomies_build_field_definition(
    taxonomy: Dict[str, Any], name: str, field_type: str,
    fk_target_entity: Optional[str] = None, fk_on_delete: Optional[str] = None,
) -> Dict[str, Any]:
    """A validated field dict for mfdb_core_create_entity_file(format_version='105') (Core stamps field_uuid)."""
    problems = bejson_taxonomies_check_field_name(taxonomy, name, field_type)
    if fk_on_delete is not None and fk_target_entity is None:
        problems.append(f"{name!r}: fk_on_delete requires fk_target_entity")
    if fk_on_delete is not None and fk_on_delete not in ("restrict", "cascade", "null"):
        problems.append(f"{name!r}: fk_on_delete must be restrict/cascade/null")
    if fk_target_entity and not name.endswith((FK_SUFFIX, SLOT_SUFFIX)):
        problems.append(f"{name!r}: FK fields must end in {FK_SUFFIX}")
    if problems:
        raise TaxonomyComplianceError(f"field definition {name!r} rejected", problems)
    return _f(name, field_type, fk_target_entity, fk_on_delete)
def bejson_taxonomies_create_domain_entity(
    manifest_path: str, taxonomy_ref: str, entity_name: str, fields: List[Dict[str, Any]],
    description: str = "", primary_key: str = "",
) -> str:
    """Create a 105 entity whose fields all comply with `taxonomy_ref`, and ledger every field.
    Validates first; nothing is created if any name is non-compliant. Returns the entity file path."""
    from lib_bejson_Core_mfdb_core import mfdb_core_create_entity_file
    taxonomy = bejson_taxonomies_get_taxonomy(manifest_path, taxonomy_ref)
    problems = bejson_taxonomies_check_entity_name(taxonomy, entity_name)
    for f in fields:
        problems += bejson_taxonomies_check_field_name(taxonomy, f["name"], f["type"])
    if problems:
        raise TaxonomyComplianceError(f"entity {entity_name!r} rejected", problems)
    path = mfdb_core_create_entity_file(
        manifest_path, entity_name, fields, description=description, primary_key=primary_key, format_version="105")
    bejson_taxonomies_track_entity_fields(manifest_path, entity_name, taxonomy["taxonomy_uuid"])
    return path

def bejson_taxonomies_core_content_hash(members: List[Dict[str, Any]]) -> str:
    """sha256 over the ordered (descriptor, suffix, field_type) triples; identical content <=> identical hash."""
    canon = json.dumps([[m["descriptor"], m["suffix"], m["field_type"]] for m in members], separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()
def bejson_taxonomies_core_register_field_set(
    manifest_path: str, set_key: str, display_name: str, version: int, members: List[Dict[str, Any]],
) -> str:
    """Write one field-set version (set row + member rows). Returns the set row's record_uuid.
    Validated first; if a row write fails the rows already written are removed again."""
    problems = _val().bejson_taxonomies_validator_check_definition(
        {"set_key": set_key, "display_name": display_name, "version": version, "members": members})
    if problems:
        raise TaxonomyComplianceError(f"field set {set_key!r} rejected", problems)
    set_uuid = add_row(manifest_path, E_FIELDSET, build_row(
        manifest_path, E_FIELDSET,
        **{FS_KEY: set_key, FS_NAME: display_name or set_key, FS_VERSION: version,
           FS_STATE: "active", FS_CREATED: now_utc()}))
    written: List[str] = []
    try:
        for order, m in enumerate(members, start=1):
            written.append(add_row(manifest_path, E_SETMEMBER, build_row(
                manifest_path, E_SETMEMBER,
                **{SM_DESCRIPTOR: m["descriptor"], SM_SET: set_uuid, SM_SUFFIX: m["suffix"],
                   SM_TYPE: m["field_type"], SM_ORDER: order})))
    except Exception:
        logger.exception("register_field_set failed mid-way; rolling back %s v%s", set_key, version)
        for member_uuid in written:
            mfdb_core_delete_entity_record_105(manifest_path, E_SETMEMBER, member_uuid)
        mfdb_core_delete_entity_record_105(manifest_path, E_FIELDSET, set_uuid)
        raise
    return set_uuid
def bejson_taxonomies_core_set_state(manifest_path: str, set_uuid: str, state: str) -> None:
    if state not in FIELDSET_STATES:
        raise TaxonomyError(f"state must be one of {FIELDSET_STATES}", "E_FIELDSET_STATE")
    mfdb_core_update_entity_record_105(manifest_path, E_FIELDSET, set_uuid, FS_STATE, state)
# ---------------------------------------------------------------------------
# Definition files (BEJSON 104a)
# ---------------------------------------------------------------------------
def bejson_taxonomies_core_build_definition_doc(
    set_key: str, display_name: str, version: int, members: List[Dict[str, Any]],
) -> Dict[str, Any]:
    fields = [{"name": n, "type": t} for n, t in _val().DEFINITION_FIELDS]
    values = [[set_key, display_name or set_key, version, m["descriptor"], m["suffix"], m["field_type"], i]
              for i, m in enumerate(members, start=1)]
    return bejson_core_create_104a(_val().DEFINITION_RECORDS_TYPE, fields, values)
def bejson_taxonomies_core_write_definition(path: str, doc: Dict[str, Any], overwrite: bool = False) -> str:
    """Validate and atomically write a definition file. Refuses to replace an existing file unless asked."""
    problems = _val().bejson_taxonomies_validator_check_definition_doc(doc)
    if problems:
        raise TaxonomyComplianceError("definition file rejected", problems)
    if os.path.exists(path) and not overwrite:
        raise TaxonomyError(f"{path} already exists", "E_EXISTS")
    write_doc(doc, path)
    return path
def bejson_taxonomies_core_read_definition(path: str) -> Dict[str, Any]:
    """Load and validate a definition file; returns {set_key, display_name, version, members}."""
    if not os.path.isfile(path):
        raise TaxonomyError(f"definition file not found: {path}", "E_DEFINITION_NOT_FOUND")
    doc = bejson_core_load_file(path)
    problems = _val().bejson_taxonomies_validator_check_definition_doc(doc)
    if problems:
        raise TaxonomyComplianceError(f"definition file {path} rejected", problems)
    fm = bejson_core_get_field_map(doc)
    rows = doc["Values"]
    first = rows[0]
    return {
        "set_key": first[fm["lattice_defn_set_key"]],
        "display_name": first[fm["lattice_defn_display_name"]],
        "version": first[fm["lattice_defn_version_metric"]],
        "members": [
            {
                "descriptor": r[fm["lattice_defn_descriptor_key"]],
                "suffix": r[fm["lattice_defn_suffix_key"]],
                "field_type": r[fm["lattice_defn_field_type_kind"]],
            }
            for r in rows
        ],
    }


def _val():
    """Lazy import: the validator imports this module, so it is loaded on first use."""
    import lib_bejson_Taxonomies_validator as _v
    return _v
