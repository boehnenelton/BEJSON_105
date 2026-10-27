"""
File Name : lib_bejson_Tax_Scaffolds_validator.py
Rel. Path : Lib_PY/Tax_Scaffolds/lib_bejson_Tax_Scaffolds_validator.py
Purpose   : Tax_Scaffolds VALIDATOR: plans and checks a graft before anything is written (plan_graft, subject derivation, audit gate). Never writes.
VERSION   : 3.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : e1ec4fbe-9d8c-43d8-9b0f-40a3a2deeecf
"""
from __future__ import annotations

import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

# Sibling family directories (Lib_PY/Core, Lib_PY/Taxonomies, Lib_PY/Tax_Scaffolds) resolve relative to this file; nothing is hardcoded.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _fam in ('Taxonomies', 'Tax_Scaffolds'):
    _p = os.path.normpath(os.path.join(_HERE, "..", _fam))
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import lib_bejson_Taxonomies_core as txc
import lib_bejson_Taxonomies_registry as txr
import lib_bejson_Taxonomies_validator as txv
from lib_bejson_Core_mfdb_core import mfdb_core_get_entity_doc  # noqa: E402

logger = logging.getLogger(__name__)
VERSION = "3.0.0"

FkTarget = Union[str, Tuple[str, str]]  # "Entity" or ("Entity", "cascade"|"restrict"|"null")
def bejson_tax_scaffolds_validator_entity_owner(manifest_path: str, entity_name: str) -> Optional[str]:
    """taxonomy_uuid that owns an entity according to the active field ledger, or None if untracked."""
    for r in txc.read_rows(manifest_path, txc.E_FIELD):
        if r[txc.FE_ENTITY] == entity_name and r[txc.FE_LIFECYCLE] == txc.LIFECYCLE_ACTIVE:
            return r[txc.FE_TAXONOMY]
    return None
def bejson_tax_scaffolds_validator_derive_subject(taxonomy: Dict[str, Any], entity_name: str) -> Optional[str]:
    """CmsVideoLibrary under namespace 'cms' -> 'video_library'. None if the name does not fit."""
    ns = taxonomy["namespace_key"]
    if entity_name[:len(ns)].lower() != ns:
        return None
    rest = entity_name[len(ns):]
    if not rest or not rest[0].isupper():
        return None
    return re.sub(r"(?<!^)(?=[A-Z])", "_", rest).lower()
def bejson_tax_scaffolds_validator_plan_graft(
    manifest_path: str, entity_name: str, set_ref: str, version: Optional[int] = None,
    subject: Optional[str] = None, fk_targets: Optional[Dict[str, FkTarget]] = None, upgrade: bool = False,
) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """Plan stamping a field set onto an entity. Returns (plan, problems); plan is None when problems exist.
    plan = {taxonomy, fset, subject, columns:[{name,type,fk..., descriptor, member_uuid}], existing_graft}.
    With upgrade=True an existing graft is extended with the members it lacks (a newer set version)."""
    problems: List[str] = []
    try:
        fset = txr.bejson_taxonomies_get_field_set(manifest_path, set_ref, version)
    except txc.TaxonomyError as exc:
        return None, [str(exc)]
    if fset["state"] != "active":
        problems.append(f"field set {fset['set_key']!r} is retired")
    if entity_name not in txc.manifest_entity_names(manifest_path):
        return None, problems + [f"entity {entity_name!r} is not in the manifest"]
    if entity_name in txc.REGISTRY_ENTITIES:
        return None, problems + [f"entity {entity_name!r} is a registry entity; its schema is fixed and cannot take field sets"]
    owner = bejson_tax_scaffolds_validator_entity_owner(manifest_path, entity_name)
    if owner is None:
        return None, problems + [f"entity {entity_name!r} is not tracked under any taxonomy (track its fields first)"]
    taxonomy = txc.bejson_taxonomies_get_taxonomy(manifest_path, owner)
    derived = bejson_tax_scaffolds_validator_derive_subject(taxonomy, entity_name)
    subject = subject or derived
    if subject is None:
        return None, problems + [f"entity {entity_name!r}: cannot derive a subject under namespace {taxonomy['namespace_key']!r}; pass subject="]
    if not txc.FIELD_NAME_RE.match(subject):
        return None, problems + [f"subject {subject!r} must be snake_case"]

    existing = next(iter(txr.bejson_taxonomies_list_grafts(manifest_path, fset["set_key"], entity_name)), None)
    if existing is not None and not upgrade:
        problems.append(f"{entity_name} already carries field set {fset['set_key']!r} (v{existing['set_version']}); use upgrade_graft")
    if existing is None and upgrade:
        problems.append(f"{entity_name} does not carry field set {fset['set_key']!r}; nothing to upgrade")
    if existing is not None and subject != existing["subject"]:
        problems.append(f"subject {subject!r} differs from the graft's subject {existing['subject']!r}")
    have = set()
    if existing is not None:
        cols = txr.bejson_taxonomies_member_columns(manifest_path, entity_name, fset["set_key"])
        have = set(cols)
        if existing["set_version"] >= fset["version"]:
            problems.append(f"{entity_name} already carries {fset['set_key']} v{existing['set_version']} (requested v{fset['version']})")

    fk_targets = dict(fk_targets or {})
    entity_names = set(txc.manifest_entity_names(manifest_path))
    existing_names = {f["name"] for f in mfdb_core_get_entity_doc(manifest_path, entity_name)["Fields"]}
    columns: List[Dict[str, Any]] = []
    planned = set()
    for m in fset["members"]:
        if m["descriptor"] in have:
            fk_targets.pop(m["descriptor"], None)
            continue
        problems += txv.bejson_taxonomies_validator_check_member_against_taxonomy(taxonomy, m)
        if m["suffix"] == txc.SLOT_SUFFIX:
            problems.append(f"member {m['descriptor']!r}: Z-space slots cannot be part of a field set")
        name = f"{taxonomy['prefix_key']}{subject}_{m['descriptor']}{m['suffix']}"
        problems += [f"{entity_name}: {p}" for p in txc.bejson_taxonomies_check_field_name(taxonomy, name, m["field_type"])]
        if name in existing_names or name in planned:
            problems.append(f"{entity_name}: column {name!r} already exists")
        planned.add(name)
        col: Dict[str, Any] = {"name": name, "type": m["field_type"], "descriptor": m["descriptor"], "member_uuid": m["member_uuid"]}
        if m["suffix"] == txc.FK_SUFFIX:
            target = fk_targets.pop(m["descriptor"], None)
            if target is None:
                problems.append(f"member {m['descriptor']!r} is a foreign key; pass fk_targets={{'{m['descriptor']}': 'Entity'}}")
            else:
                ent, on_delete = (target, "restrict") if isinstance(target, str) else target
                if ent not in entity_names:
                    problems.append(f"member {m['descriptor']!r}: FK target entity {ent!r} is not in the manifest")
                if on_delete not in ("restrict", "cascade", "null"):
                    problems.append(f"member {m['descriptor']!r}: fk_on_delete must be restrict/cascade/null")
                col["fk_target_entity"], col["fk_on_delete"] = ent, on_delete
        else:
            if fk_targets.pop(m["descriptor"], None) is not None:
                problems.append(f"member {m['descriptor']!r} is not a foreign key; fk_targets entry not allowed")
        columns.append(col)
    for stray in fk_targets:
        problems.append(f"fk_targets names unknown member {stray!r}")
    if not columns and existing is not None and not problems:
        problems.append(f"{entity_name}: nothing to add; the graft already has every member of v{fset['version']}")
    if problems:
        return None, problems
    return {"taxonomy": taxonomy, "fset": fset, "subject": subject, "columns": columns, "existing_graft": existing}, []
def bejson_tax_scaffolds_validator_audit_gate(manifest_path: str) -> List[str]:
    """Problems of the node's full audit (empty list = passes). The deploy/graft functions raise on any."""
    return txv.bejson_taxonomies_validator_audit_database(manifest_path)["problems"]
