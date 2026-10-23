"""
File Name : lib_bejson_Taxonomies_uuid_tracker.py
Rel. Path : Lib_PY/Taxonomies/lib_bejson_Taxonomies_uuid_tracker.py
Purpose   : field_uuid ledger (LatticeFieldEntry): track fields under a taxonomy, resolve name <-> uuid,
            follow renames, retire fields, and audit a whole lattice database (taxonomy-aware: each
            field is judged by the taxonomy its ledger row names, so variant nodes verify on their own rules).
VERSION   : 1.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : 8e3b57c1-d204-4a69-b7f8-61c9a0e4d352
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
from lib_bejson_Core_bejson_core import bejson_core_get_field_map  # noqa: E402
from lib_bejson_Core_mfdb_core import mfdb_core_get_entity_doc, mfdb_core_update_entity_record_105  # noqa: E402
from lib_bejson_Core_mfdb_validator import validate_mfdb_database  # noqa: E402

logger = logging.getLogger(__name__)
VERSION = "1.0.0"


def _active_ledger(manifest_path: str, entity_name: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = [r for r in st.read_rows(manifest_path, st.E_FIELD) if r[st.FE_LIFECYCLE] == st.LIFECYCLE_ACTIVE]
    return [r for r in rows if entity_name is None or r[st.FE_ENTITY] == entity_name]


def bejson_taxonomies_track_fields(
    manifest_path: str, entity_name: str, taxonomy_ref: str, field_names: Optional[List[str]] = None,
) -> int:
    """Ledger the given fields (default: every field not yet in the ledger) of an entity under a taxonomy.
    All names are checked first; nothing is written if any field is non-compliant. Returns rows added."""
    taxonomy = reg.bejson_taxonomies_get_taxonomy(manifest_path, taxonomy_ref)
    doc = mfdb_core_get_entity_doc(manifest_path, entity_name)
    tracked = {r[st.FE_COLUMN] for r in _active_ledger(manifest_path, entity_name)}
    wanted = [f for f in doc["Fields"]
              if (f["name"] in field_names if field_names is not None else f["name"] not in tracked)]
    problems = reg.bejson_taxonomies_check_entity_name(taxonomy, entity_name)
    for f in wanted:
        if f["name"] in tracked:
            problems.append(f"{entity_name}.{f['name']}: already tracked")
        if not st.UUID4_RE.match(f.get("field_uuid", "")):
            problems.append(f"{entity_name}.{f['name']}: field_uuid missing or not UUIDv4")
        problems += reg.bejson_taxonomies_check_field_name(taxonomy, f["name"], f["type"])
    missing = set(field_names or []) - {f["name"] for f in doc["Fields"]}
    problems += [f"{entity_name}.{n}: no such field" for n in sorted(missing)]
    if problems:
        raise st.TaxonomyComplianceError(f"cannot track fields of {entity_name}", problems)
    for f in wanted:
        token = reg.bejson_taxonomies_match_suffix(taxonomy, f["name"])
        st.add_row(manifest_path, st.E_FIELD, st.build_row(
            manifest_path, st.E_FIELD,
            **{st.FE_COLUMN: f["name"], st.FE_UUID: f["field_uuid"], st.FE_ENTITY: entity_name,
               st.FE_TAXONOMY: taxonomy["taxonomy_uuid"], st.FE_RULE: taxonomy["suffix_rules"][token]["rule_uuid"],
               st.FE_LIFECYCLE: st.LIFECYCLE_ACTIVE, st.FE_RETIRED: None}))
    return len(wanted)


def bejson_taxonomies_track_entity_fields(manifest_path: str, entity_name: str, taxonomy_ref: str) -> int:
    return bejson_taxonomies_track_fields(manifest_path, entity_name, taxonomy_ref)


def bejson_taxonomies_resolve_field_uuid(manifest_path: str, entity_name: str, field_name: str) -> str:
    doc = mfdb_core_get_entity_doc(manifest_path, entity_name)
    for f in doc["Fields"]:
        if f["name"] == field_name:
            return f["field_uuid"]
    raise st.TaxonomyError(f"{entity_name}: no field {field_name!r}", "E_FIELD_NOT_FOUND")


def bejson_taxonomies_resolve_field_name(manifest_path: str, entity_name: str, field_uuid: str) -> str:
    """Current name of a field by its (rename-proof) field_uuid."""
    doc = mfdb_core_get_entity_doc(manifest_path, entity_name)
    for f in doc["Fields"]:
        if f["field_uuid"] == field_uuid:
            return f["name"]
    raise st.TaxonomyError(f"{entity_name}: no field with field_uuid {field_uuid!r}", "E_FIELD_NOT_FOUND")


def _ledger_row(manifest_path: str, entity_name: str, field_uuid: str) -> Dict[str, Any]:
    for r in _active_ledger(manifest_path, entity_name):
        if r[st.FE_UUID] == field_uuid:
            return r
    raise st.TaxonomyError(f"{entity_name}: field_uuid {field_uuid!r} has no active ledger row", "E_LEDGER_NOT_FOUND")


def bejson_taxonomies_get_field_entry(manifest_path: str, entity_name: str, field_uuid: str) -> Dict[str, Any]:
    """The active ledger row for a field_uuid (taxonomy_uuid, column name, suffix rule, ...)."""
    row = _ledger_row(manifest_path, entity_name, field_uuid)
    return {"column_name": row[st.FE_COLUMN], "field_uuid": row[st.FE_UUID], "entity_name": entity_name,
            "taxonomy_uuid": row[st.FE_TAXONOMY], "suffix_rule_uuid": row[st.FE_RULE],
            "ledger_record_uuid": row["record_uuid"]}


def bejson_taxonomies_record_rename(manifest_path: str, entity_name: str, field_uuid: str, new_name: str) -> None:
    """Point the ledger row at a field's new name (after the entity file was renamed).
    The new name is checked against the taxonomy the ledger row belongs to."""
    row = _ledger_row(manifest_path, entity_name, field_uuid)
    taxonomy = reg.bejson_taxonomies_get_taxonomy(manifest_path, row[st.FE_TAXONOMY])
    doc = mfdb_core_get_entity_doc(manifest_path, entity_name)
    fdef = next((f for f in doc["Fields"] if f["field_uuid"] == field_uuid), None)
    if fdef is None or fdef["name"] != new_name:
        raise st.TaxonomyError(f"{entity_name}: field {field_uuid} is not named {new_name!r} in the entity file", "E_RENAME_MISMATCH")
    problems = reg.bejson_taxonomies_check_field_name(taxonomy, new_name, fdef["type"])
    if problems:
        raise st.TaxonomyComplianceError(f"rename to {new_name!r} is not compliant", problems)
    token = reg.bejson_taxonomies_match_suffix(taxonomy, new_name)
    mfdb_core_update_entity_record_105(manifest_path, st.E_FIELD, row["record_uuid"], st.FE_COLUMN, new_name)
    mfdb_core_update_entity_record_105(manifest_path, st.E_FIELD, row["record_uuid"], st.FE_RULE,
                                       taxonomy["suffix_rules"][token]["rule_uuid"])


def bejson_taxonomies_retire_field(manifest_path: str, entity_name: str, field_uuid: str) -> None:
    row = _ledger_row(manifest_path, entity_name, field_uuid)
    mfdb_core_update_entity_record_105(manifest_path, st.E_FIELD, row["record_uuid"], st.FE_LIFECYCLE, st.LIFECYCLE_RETIRED)
    mfdb_core_update_entity_record_105(manifest_path, st.E_FIELD, row["record_uuid"], st.FE_RETIRED, st.now_utc())


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
        fuuid = row[st.FE_UUID]
        ledgered.add(fuuid)
        fdef = by_uuid.get(fuuid)
        if fdef is None:
            bejson_taxonomies_retire_field(manifest_path, entity_name, fuuid)
            retired.append(row[st.FE_COLUMN])
        elif fdef["name"] != row[st.FE_COLUMN]:
            bejson_taxonomies_record_rename(manifest_path, entity_name, fuuid, fdef["name"])
            renamed.append(f"{row[st.FE_COLUMN]} -> {fdef['name']}")
    return {"renamed": renamed, "retired": retired,
            "unledgered": [f["name"] for f in doc["Fields"] if f["field_uuid"] not in ledgered]}


def bejson_taxonomies_stamp_audit(manifest_path: str) -> None:
    """Refresh each taxonomy's tracked-field count and audit timestamp."""
    counts: Dict[str, int] = {}
    for r in _active_ledger(manifest_path):
        counts[r[st.FE_TAXONOMY]] = counts.get(r[st.FE_TAXONOMY], 0) + 1
    now = st.now_utc()
    for t in reg.bejson_taxonomies_list_taxonomies(manifest_path):
        uid = t["taxonomy_uuid"]
        mfdb_core_update_entity_record_105(manifest_path, st.E_TAXONOMY, uid, st.TX_COUNT, counts.get(uid, 0))
        mfdb_core_update_entity_record_105(manifest_path, st.E_TAXONOMY, uid, st.TX_AUDIT, now)


def _is_exempt(entity_name: str) -> bool:
    return entity_name in st.CORE_OWNED_ENTITIES or entity_name.startswith("meta-")


def bejson_taxonomies_audit_database(manifest_path: str) -> Dict[str, Any]:
    """Full taxonomy-aware audit. Returns {passed, problems, entities, taxonomies, fields_total, ledger_rows, ...}.
    Never raises on findings (including a structurally damaged registry); they are returned in `problems`."""
    problems: List[str] = []
    stats: Dict[str, int] = {"entities": 0, "taxonomies": 0, "fields_total": 0, "ledger_rows": 0}
    try:
        _audit_body(manifest_path, problems, stats)
    except Exception as exc:  # damaged registry entity (missing field, unreadable file, ...) is a finding
        logger.debug("audit aborted", exc_info=True)
        problems.append(f"audit aborted, registry structure damaged: {type(exc).__name__}: {exc}")
    return {
        "verified_utc": st.now_utc(),
        "entities": stats["entities"],
        "taxonomies": stats["taxonomies"],
        "fields_total": stats["fields_total"],
        "ledger_rows": stats["ledger_rows"],
        "problems": problems,
        "passed": not problems,
    }


def _audit_body(manifest_path: str, problems: List[str], stats: Dict[str, int]) -> None:
    res = validate_mfdb_database(manifest_path, strict_fk=True)
    if not res.valid:
        problems += [f"MFDB: {e}" for e in res.errors]

    taxa = {t["taxonomy_uuid"]: t for t in reg.bejson_taxonomies_list_taxonomies(manifest_path)}
    for t in taxa.values():
        for req in st.REQUIRED_SUFFIXES:
            if req not in t["suffix_rules"]:
                problems.append(f"taxonomy {t['namespace_key']}: required suffix {req} not registered")
        if t["parent_taxonomy_uuid"] is not None and t["parent_taxonomy_uuid"] not in taxa:
            problems.append(f"taxonomy {t['namespace_key']}: parent {t['parent_taxonomy_uuid']} not found")
    rule_owner = {r["rule_uuid"]: (t["taxonomy_uuid"], tok)
                  for t in taxa.values() for tok, r in t["suffix_rules"].items()}

    ledger_rows = _active_ledger(manifest_path)
    stats["taxonomies"] = len(taxa)
    stats["ledger_rows"] = len(ledger_rows)
    ledger: Dict[tuple, Dict[str, Any]] = {}
    for r in ledger_rows:
        key = (r[st.FE_ENTITY], r[st.FE_COLUMN])
        if key in ledger:
            problems.append(f"ledger has duplicate active entry for {key[0]}.{key[1]}")
        ledger[key] = r

    seen = set()
    entity_names = st.manifest_entity_names(manifest_path)
    stats["entities"] = len(entity_names)
    for ent in entity_names:
        if _is_exempt(ent):
            continue
        doc = mfdb_core_get_entity_doc(manifest_path, ent)
        fmap = bejson_core_get_field_map(doc)
        names = [f["name"] for f in doc["Fields"]]
        for f in doc["Fields"]:
            key = (ent, f["name"])
            seen.add(key)
            if not st.UUID4_RE.match(f.get("field_uuid", "")):
                problems.append(f"{ent}.{f['name']}: field_uuid not UUIDv4")
            row = ledger.get(key)
            if row is None:
                problems.append(f"{ent}.{f['name']}: not in field ledger")
                continue
            if row[st.FE_UUID] != f.get("field_uuid"):
                problems.append(f"{ent}.{f['name']}: ledger uuid != field_uuid")
            t = taxa.get(row[st.FE_TAXONOMY])
            if t is None:
                problems.append(f"{ent}.{f['name']}: ledger taxonomy not found")
                continue
            problems += [f"{ent}: {p}" for p in reg.bejson_taxonomies_check_field_name(t, f["name"], f["type"])]
            problems += reg.bejson_taxonomies_check_entity_name(t, ent)
            token = reg.bejson_taxonomies_match_suffix(t, f["name"])
            if token is not None and rule_owner.get(row[st.FE_RULE]) != (t["taxonomy_uuid"], token):
                problems.append(f"{ent}.{f['name']}: ledger suffix rule does not match {token}")
            if f.get("fk_target_entity") and token not in (st.FK_SUFFIX, st.SLOT_SUFFIX):
                problems.append(f"{ent}.{f['name']}: FK metadata on non-FK suffix")
        for i, vrow in enumerate(doc["Values"]):
            if not st.UUID4_RE.match(str(vrow[0])):
                problems.append(f"{ent} row {i}: record_uuid not UUIDv4")
            if len(vrow) != len(doc["Fields"]) + 1:
                problems.append(f"{ent} row {i}: width {len(vrow)} != {len(doc['Fields']) + 1}")
        slots = [i for i, n in enumerate(names) if n.endswith(st.SLOT_SUFFIX)]
        if slots and slots != list(range(len(names) - len(slots), len(names))):
            problems.append(f"{ent}: Z-space slots are not the trailing block")
        for i in slots:
            if any(v[fmap[names[i]]] is not None for v in doc["Values"]):
                problems.append(f"{ent}.{names[i]}: unbound slot holds data")
    stats["fields_total"] = len(seen)
    stale = set(ledger) - seen
    if stale:
        problems.append(f"ledger has {len(stale)} active entr(ies) for missing fields (run sync_ledger)")

    # Z-space reservations must agree with the entity files
    for z in st.read_rows(manifest_path, st.E_ZSPACE):
        ent = z[st.ZS_ENTITY]
        if ent not in entity_names:
            problems.append(f"zspace: entity {ent} not in manifest")
            continue
        fdef = next((f for f in mfdb_core_get_entity_doc(manifest_path, ent)["Fields"]
                     if f["field_uuid"] == z[st.ZS_FIELD_UUID]), None)
        if fdef is None:
            problems.append(f"zspace: {ent} slot {z[st.ZS_FIELD_UUID]} missing from entity")
        elif z[st.ZS_STATE] == st.ZSTATE_RESERVED:
            if not fdef["name"].endswith(st.SLOT_SUFFIX) or z[st.ZS_BOUND] is not None:
                problems.append(f"zspace: {ent}.{fdef['name']} marked reserved but looks bound")
        elif z[st.ZS_STATE] == st.ZSTATE_BOUND:
            if fdef["name"] != z[st.ZS_BOUND] or fdef["name"].endswith(st.SLOT_SUFFIX):
                problems.append(f"zspace: {ent}.{fdef['name']} marked bound to {z[st.ZS_BOUND]!r} but differs")
        else:
            problems.append(f"zspace: state {z[st.ZS_STATE]!r} not in (reserved, bound)")

    # Deployments and links
    dep_tax: Dict[str, str] = {}
    for d in st.read_rows(manifest_path, st.E_DEPLOYMENT):
        dep_tax[d["record_uuid"]] = d[st.DP_TAXONOMY]
        if d[st.DP_ROLE] not in st.ROLE_KINDS:
            problems.append(f"deployment {d[st.DP_NODE]}: role {d[st.DP_ROLE]!r} not in {st.ROLE_KINDS}")
        if d[st.DP_STRATEGY] not in st.STRATEGY_KINDS:
            problems.append(f"deployment {d[st.DP_NODE]}: strategy {d[st.DP_STRATEGY]!r} not in {st.STRATEGY_KINDS}")
    for i, k in enumerate(st.read_rows(manifest_path, st.E_LINK)):
        kind = k[st.LK_MATCH]
        if kind not in st.MATCH_KINDS:
            problems.append(f"link row {i}: match_kind {kind!r} not in {st.MATCH_KINDS}")
            continue
        actual = "identical" if dep_tax.get(k[st.LK_MASTER]) == dep_tax.get(k[st.LK_SLAVE]) else "variant"
        if kind != actual:
            problems.append(f"link row {i}: declared {kind} but taxonomies are {actual}")
