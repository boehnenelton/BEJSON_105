"""
File Name : lib_bejson_Taxonomies_taxonomy_registry.py
Rel. Path : Lib_PY/Taxonomies/lib_bejson_Taxonomies_taxonomy_registry.py
Purpose   : Create, derive (variant), diff, look up and delete taxonomies in a lattice registry
            database, and check field/entity names against a taxonomy's prefix + suffix rules.
            A taxonomy's UUID is the record_uuid of its LatticeTaxonomy row.
VERSION   : 1.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : 2f6a90d4-7b13-4c85-a9e2-d05c18e7f3b6
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Optional, Union

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import lib_bejson_Taxonomies_store as st  # noqa: E402
from lib_bejson_Core_mfdb_core import (  # noqa: E402
    mfdb_core_delete_entity_record_105,
    mfdb_core_update_entity_record_105,
)

logger = logging.getLogger(__name__)
VERSION = "1.0.0"

RuleSpec = Union[str, tuple, list]


# ---------------------------------------------------------------------------
# Rule normalisation / validation
# ---------------------------------------------------------------------------
def _normalise_rules(rules: Dict[str, RuleSpec]) -> Dict[str, tuple]:
    """token -> 'type' | (type, meaning)  ==>  token -> (type, meaning). Validates everything."""
    out: Dict[str, tuple] = {}
    for token, spec in rules.items():
        if not st.SUFFIX_TOKEN_RE.match(token):
            raise st.TaxonomyError(f"suffix token {token!r} must look like '_name'", "E_SUFFIX_TOKEN")
        ftype, meaning = (spec, "") if isinstance(spec, str) else (spec[0], spec[1] if len(spec) > 1 else "")
        if ftype not in st.VALID_FIELD_TYPES:
            raise st.TaxonomyError(f"suffix {token}: type {ftype!r} not in {st.VALID_FIELD_TYPES}", "E_SUFFIX_TYPE")
        out[token] = (ftype, meaning)
    for req in st.REQUIRED_SUFFIXES:
        if req not in out:
            raise st.TaxonomyError(f"required suffix {req} is missing", "E_SUFFIX_REQUIRED")
        if out[req][0] != "string":
            raise st.TaxonomyError(f"required suffix {req} must be type string", "E_SUFFIX_TYPE")
    return out


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------
def bejson_taxonomies_list_taxonomies(manifest_path: str) -> List[Dict[str, Any]]:
    taxa = []
    rules_by_tax: Dict[str, Dict[str, Dict[str, str]]] = {}
    for r in st.read_rows(manifest_path, st.E_SUFFIX):
        rules_by_tax.setdefault(r[st.SX_TAXONOMY], {})[r[st.SX_TOKEN]] = {
            "field_type": r[st.SX_TYPE], "meaning": r[st.SX_MEANING], "rule_uuid": r["record_uuid"]}
    for r in st.read_rows(manifest_path, st.E_TAXONOMY):
        taxa.append({
            "taxonomy_uuid": r["record_uuid"],
            "namespace_key": r[st.TX_NAMESPACE],
            "family_name": r[st.TX_FAMILY],
            "prefix_key": r[st.TX_PREFIX],
            "field_count": r[st.TX_COUNT],
            "zspace_flag": r[st.TX_ZFLAG],
            "audit_timestamp": r[st.TX_AUDIT],
            "parent_taxonomy_uuid": r[st.TX_PARENT],
            "suffix_rules": rules_by_tax.get(r["record_uuid"], {}),
        })
    return taxa


def bejson_taxonomies_get_taxonomy(manifest_path: str, taxonomy_ref: str) -> Dict[str, Any]:
    """Look up by taxonomy_uuid or namespace_key."""
    for t in bejson_taxonomies_list_taxonomies(manifest_path):
        if taxonomy_ref in (t["taxonomy_uuid"], t["namespace_key"]):
            return t
    raise st.TaxonomyError(f"taxonomy {taxonomy_ref!r} not found", "E_TAXONOMY_NOT_FOUND")


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
    if not st.FIELD_NAME_RE.match(field_name):
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
    if not st.NAMESPACE_RE.match(namespace_key):
        raise st.TaxonomyError(f"namespace {namespace_key!r} must match {st.NAMESPACE_RE.pattern}", "E_NAMESPACE")
    prefix = f"{namespace_key}_"
    rules = _normalise_rules(suffix_rules if suffix_rules is not None else st.DEFAULT_SUFFIX_RULES)

    existing = bejson_taxonomies_list_taxonomies(manifest_path)
    for t in existing:
        if t["namespace_key"] == namespace_key:
            raise st.TaxonomyError(f"namespace {namespace_key!r} already registered", "E_NAMESPACE_EXISTS")
        if t["prefix_key"].startswith(prefix) or prefix.startswith(t["prefix_key"]):
            raise st.TaxonomyError(
                f"prefix {prefix!r} is ambiguous with existing prefix {t['prefix_key']!r}", "E_PREFIX_AMBIGUOUS")
    if parent_taxonomy_uuid is not None and parent_taxonomy_uuid not in {t["taxonomy_uuid"] for t in existing}:
        raise st.TaxonomyError(f"parent taxonomy {parent_taxonomy_uuid!r} not found", "E_TAXONOMY_NOT_FOUND")

    taxonomy_uuid = st.add_row(manifest_path, st.E_TAXONOMY, st.build_row(
        manifest_path, st.E_TAXONOMY,
        **{st.TX_NAMESPACE: namespace_key, st.TX_FAMILY: family_name or namespace_key, st.TX_PREFIX: prefix,
           st.TX_COUNT: 0, st.TX_ZFLAG: st.SLOT_SUFFIX in rules, st.TX_AUDIT: st.now_utc(),
           st.TX_PARENT: parent_taxonomy_uuid}))
    created_rules: List[str] = []
    try:
        for token, (ftype, meaning) in rules.items():
            created_rules.append(st.add_row(manifest_path, st.E_SUFFIX, st.build_row(
                manifest_path, st.E_SUFFIX,
                **{st.SX_TOKEN: token, st.SX_TYPE: ftype, st.SX_MEANING: meaning or token,
                   st.SX_TAXONOMY: taxonomy_uuid})))
    except Exception:
        logger.exception("create_taxonomy failed mid-way; rolling back %s", namespace_key)
        for rule_uuid in created_rules:
            mfdb_core_delete_entity_record_105(manifest_path, st.E_SUFFIX, rule_uuid)
        mfdb_core_delete_entity_record_105(manifest_path, st.E_TAXONOMY, taxonomy_uuid)
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
            raise st.TaxonomyError(f"cannot remove unknown suffix {token!r}", "E_SUFFIX_UNKNOWN")
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
    users = [r for r in st.read_rows(manifest_path, st.E_FIELD) if r[st.FE_TAXONOMY] == uid]
    users += [r for r in st.read_rows(manifest_path, st.E_DEPLOYMENT) if r[st.DP_TAXONOMY] == uid]
    if users:
        raise st.TaxonomyError(f"taxonomy {t['namespace_key']!r} is in use by {len(users)} row(s)", "E_TAXONOMY_IN_USE")
    # Core's null-on-delete scan skips an entity's own FKs, so a self-referencing parent link is not
    # cleared by it. Detach variants explicitly (public update API) before deleting the parent.
    for child in bejson_taxonomies_list_taxonomies(manifest_path):
        if child["parent_taxonomy_uuid"] == uid:
            mfdb_core_update_entity_record_105(manifest_path, st.E_TAXONOMY, child["taxonomy_uuid"], st.TX_PARENT, None)
    for rule in t["suffix_rules"].values():
        mfdb_core_delete_entity_record_105(manifest_path, st.E_SUFFIX, rule["rule_uuid"])
    mfdb_core_delete_entity_record_105(manifest_path, st.E_TAXONOMY, uid)
