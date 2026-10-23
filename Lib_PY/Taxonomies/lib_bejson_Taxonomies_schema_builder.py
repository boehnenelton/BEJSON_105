"""
File Name : lib_bejson_Taxonomies_schema_builder.py
Rel. Path : Lib_PY/Taxonomies/lib_bejson_Taxonomies_schema_builder.py
Purpose   : Owns the six-entity `lattice` registry schema (single source of truth), builds a fresh
            registry database (MFDB v1.40, Format 105, Ref_Integrity on) seeded with the root taxonomy,
            its suffix rules, the field_uuid ledger and the LatticeDeployment Z-space reservation; and
            builds taxonomy-compliant field definitions / names for domain entities.
VERSION   : 1.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : e0b94a6d-31c7-4f28-8a5e-b7d3f1c6092a
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import lib_bejson_Taxonomies_store as st  # noqa: E402
import lib_bejson_Taxonomies_taxonomy_registry as reg  # noqa: E402
import lib_bejson_Taxonomies_uuid_tracker as trk  # noqa: E402
from lib_bejson_Core_mfdb_core import (  # noqa: E402
    mfdb_core_create_database,
    mfdb_core_enable_ref_integrity,
    mfdb_core_get_entity_doc,
)

logger = logging.getLogger(__name__)
VERSION = "1.0.0"


def _f(name: str, ftype: str, fk: Optional[str] = None, on_delete: Optional[str] = None) -> Dict[str, Any]:
    d: Dict[str, Any] = {"name": name, "type": ftype}
    if fk:
        d["fk_target_entity"] = fk
    if on_delete:
        d["fk_on_delete"] = on_delete
    return d


# entity -> (owner family, description, primary key, fields). Order matters only for readability.
ENTITY_DEFS: Dict[str, tuple] = {
    st.E_TAXONOMY: ("Taxonomies", "Registered taxonomies. Taxonomy UUID = row record_uuid.", st.TX_NAMESPACE, [
        _f(st.TX_NAMESPACE, "string"), _f(st.TX_FAMILY, "string"), _f(st.TX_PREFIX, "string"),
        _f(st.TX_COUNT, "integer"), _f(st.TX_ZFLAG, "boolean"), _f(st.TX_AUDIT, "string"),
        _f(st.TX_PARENT, "string", st.E_TAXONOMY, "null"),
    ]),
    st.E_SUFFIX: ("Taxonomies", "Registered semantic suffixes and the BEJSON type each requires, per taxonomy.", st.SX_TOKEN, [
        _f(st.SX_TOKEN, "string"), _f(st.SX_TYPE, "string"), _f(st.SX_MEANING, "string"),
        _f(st.SX_TAXONOMY, "string", st.E_TAXONOMY, "restrict"),
    ]),
    st.E_FIELD: ("Taxonomies", "Field-level field_uuid ledger across all schemas.", st.FE_COLUMN, [
        _f(st.FE_COLUMN, "string"), _f(st.FE_UUID, "string"), _f(st.FE_ENTITY, "string"),
        _f(st.FE_TAXONOMY, "string", st.E_TAXONOMY, "restrict"),
        _f(st.FE_RULE, "string", st.E_SUFFIX, "restrict"),
        _f(st.FE_LIFECYCLE, "string"), _f(st.FE_RETIRED, "string"),
    ]),
    st.E_DEPLOYMENT: ("Scaffold", "Rebuild / prebuilt node deployments (master or slave role). Trailing Z-space slot reserved for the federation link UUID.", st.DP_NODE, [
        _f(st.DP_NODE, "string"), _f(st.DP_DISPLAY, "string"), _f(st.DP_ROLE, "string"), _f(st.DP_STRATEGY, "string"),
        _f(st.DP_ZSPACE, "string", st.E_ZSPACE, "restrict"),
        _f(st.DP_ACTIVE, "boolean"), _f(st.DP_CREATED, "string"),
        _f(st.DP_TAXONOMY, "string", st.E_TAXONOMY, "restrict"),
        _f(st.DP_SLOT, "string", st.E_LINK, "null"),  # trailing Z-space slot, unbound
    ]),
    st.E_ZSPACE: ("Scaffold", "Z-space slot reservations, addressed by field_uuid (never by positional offset).", st.ZS_ENTITY, [
        _f(st.ZS_ENTITY, "string"), _f(st.ZS_FIELD_UUID, "string"), _f(st.ZS_ORDINAL, "integer"),
        _f(st.ZS_STATE, "string"), _f(st.ZS_BOUND, "string"), _f(st.ZS_ALLOCATED, "string"),
    ]),
    st.E_LINK: ("Scaffold", "Master/slave federation link records.", st.LK_KEY, [
        _f(st.LK_KEY, "string"),
        _f(st.LK_MASTER, "string", st.E_DEPLOYMENT, "restrict"),
        _f(st.LK_SLAVE, "string", st.E_DEPLOYMENT, "restrict"),
        _f(st.LK_PROTOCOL, "string"), _f(st.LK_INTERVAL, "integer"), _f(st.LK_HEALTHY, "boolean"),
        _f(st.LK_SYNC, "string"), _f(st.LK_MATCH, "string"),
    ]),
}


def bejson_taxonomies_build_registry_database(
    root_dir: str,
    db_name: str = st.ROOT_NAMESPACE,
    network_role: str = "Master",
) -> str:
    """Create a fresh lattice registry MFDB under `root_dir` and return its manifest path.
    Seeds: root taxonomy `lattice` + default suffix rules, field ledger for all registry fields,
    and the 'reserved' Z-space row for LatticeDeployment's trailing slot."""
    if network_role not in ("Master", "Slave"):
        raise st.TaxonomyError(f"network_role must be Master or Slave, got {network_role!r}", "E_NETWORK_ROLE")
    if os.path.exists(os.path.join(root_dir, "104a.mfdb.bejson")):
        raise st.TaxonomyError(f"a database already exists in {root_dir}", "E_DB_EXISTS")
    entities = [{"name": n, "description": d, "primary_key": pk, "fields": fields,
                 "format_version": "105", "file_path": f"data/{n.lower()}.bejson"}
                for n, (_fam, d, pk, fields) in ENTITY_DEFS.items()]
    manifest = mfdb_core_create_database(
        root_dir, db_name, entities,
        db_description="lattice taxonomy registry: lib_bejson_Scaffold + lib_bejson_Taxonomies data contracts.",
        schema_version="1.1.0", mfdb_version="1.40", network_role=network_role)
    mfdb_core_enable_ref_integrity(manifest)

    root_uuid = reg.bejson_taxonomies_create_taxonomy(
        manifest, st.ROOT_NAMESPACE, family_name="lib_bejson_Scaffold+lib_bejson_Taxonomies")
    for ent in ENTITY_DEFS:
        trk.bejson_taxonomies_track_entity_fields(manifest, ent, root_uuid)

    slot = next(f for f in mfdb_core_get_entity_doc(manifest, st.E_DEPLOYMENT)["Fields"] if f["name"] == st.DP_SLOT)
    st.add_row(manifest, st.E_ZSPACE, st.build_row(
        manifest, st.E_ZSPACE,
        **{st.ZS_ENTITY: st.E_DEPLOYMENT, st.ZS_FIELD_UUID: slot["field_uuid"], st.ZS_ORDINAL: 1,
           st.ZS_STATE: st.ZSTATE_RESERVED, st.ZS_BOUND: None, st.ZS_ALLOCATED: st.now_utc()}))
    trk.bejson_taxonomies_stamp_audit(manifest)
    logger.info("built lattice registry at %s", manifest)
    return manifest


def bejson_taxonomies_make_field_name(taxonomy: Dict[str, Any], subject: str, descriptor: str, suffix: str) -> str:
    """`<prefix><subject>_<descriptor><suffix>`; suffix must be registered. Raises if non-compliant."""
    if suffix not in taxonomy["suffix_rules"]:
        raise st.TaxonomyError(f"suffix {suffix!r} not registered in taxonomy {taxonomy['namespace_key']!r}", "E_SUFFIX_UNKNOWN")
    name = f"{taxonomy['prefix_key']}{subject}_{descriptor}{suffix}".lower()
    want = taxonomy["suffix_rules"][suffix]["field_type"]
    problems = reg.bejson_taxonomies_check_field_name(taxonomy, name, want)
    if problems:
        raise st.TaxonomyComplianceError(f"cannot build field name {name!r}", problems)
    return name


def bejson_taxonomies_build_field_definition(
    taxonomy: Dict[str, Any], name: str, field_type: str,
    fk_target_entity: Optional[str] = None, fk_on_delete: Optional[str] = None,
) -> Dict[str, Any]:
    """A validated field dict for mfdb_core_create_entity_file(format_version='105') (Core stamps field_uuid)."""
    problems = reg.bejson_taxonomies_check_field_name(taxonomy, name, field_type)
    if fk_on_delete is not None and fk_target_entity is None:
        problems.append(f"{name!r}: fk_on_delete requires fk_target_entity")
    if fk_on_delete is not None and fk_on_delete not in ("restrict", "cascade", "null"):
        problems.append(f"{name!r}: fk_on_delete must be restrict/cascade/null")
    if fk_target_entity and not name.endswith((st.FK_SUFFIX, st.SLOT_SUFFIX)):
        problems.append(f"{name!r}: FK fields must end in {st.FK_SUFFIX}")
    if problems:
        raise st.TaxonomyComplianceError(f"field definition {name!r} rejected", problems)
    return _f(name, field_type, fk_target_entity, fk_on_delete)


def bejson_taxonomies_create_domain_entity(
    manifest_path: str, taxonomy_ref: str, entity_name: str, fields: List[Dict[str, Any]],
    description: str = "", primary_key: str = "",
) -> str:
    """Create a 105 entity whose fields all comply with `taxonomy_ref`, and ledger every field.
    Validates first; nothing is created if any name is non-compliant. Returns the entity file path."""
    from lib_bejson_Core_mfdb_core import mfdb_core_create_entity_file
    taxonomy = reg.bejson_taxonomies_get_taxonomy(manifest_path, taxonomy_ref)
    problems = reg.bejson_taxonomies_check_entity_name(taxonomy, entity_name)
    for f in fields:
        problems += reg.bejson_taxonomies_check_field_name(taxonomy, f["name"], f["type"])
    if problems:
        raise st.TaxonomyComplianceError(f"entity {entity_name!r} rejected", problems)
    path = mfdb_core_create_entity_file(
        manifest_path, entity_name, fields, description=description, primary_key=primary_key, format_version="105")
    trk.bejson_taxonomies_track_entity_fields(manifest_path, entity_name, taxonomy["taxonomy_uuid"])
    return path
