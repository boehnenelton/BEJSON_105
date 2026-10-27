"""
File Name : lib_bejson_Taxonomies_validator.py
Rel. Path : Lib_PY/Taxonomies/lib_bejson_Taxonomies_validator.py
Purpose   : Taxonomies VALIDATOR: every check (set keys, members, definition files, member vs taxonomy) and the full registry audit. Never writes.
VERSION   : 3.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : 2725a1a9-951e-4fbb-b676-6d60b7932d16
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Optional

# Sibling family directories (Lib_PY/Core, Lib_PY/Taxonomies, Lib_PY/Tax_Scaffolds) resolve relative to this file; nothing is hardcoded.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _fam in ('Taxonomies',):
    _p = os.path.normpath(os.path.join(_HERE, "..", _fam))
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import lib_bejson_Taxonomies_core as txc
from lib_bejson_Core_bejson_core import bejson_core_get_field_map  # noqa: E402
from lib_bejson_Core_bejson_validator import validate_bejson  # noqa: E402
from lib_bejson_Core_mfdb_core import mfdb_core_get_entity_doc  # noqa: E402
from lib_bejson_Core_mfdb_validator import validate_mfdb_database  # noqa: E402

logger = logging.getLogger(__name__)
VERSION = "3.0.0"

DEFINITION_RECORDS_TYPE = "LatticeFieldSetDefinition"
DEFINITION_FIELDS = (  # (name, type), in column order; shared with the core's writer
    ("lattice_defn_set_key", "string"), ("lattice_defn_display_name", "string"), ("lattice_defn_version_metric", "integer"),
    ("lattice_defn_descriptor_key", "string"), ("lattice_defn_suffix_key", "string"),
    ("lattice_defn_field_type_kind", "string"), ("lattice_defn_order_metric", "integer"),
)
# ---------------------------------------------------------------------------
# Field-set specs and definition files
# ---------------------------------------------------------------------------
def bejson_taxonomies_validator_check_set_key(set_key: Any) -> List[str]:
    if not isinstance(set_key, str) or not txc.SET_KEY_RE.match(set_key):
        return [f"set_key {set_key!r} must match {txc.SET_KEY_RE.pattern}"]
    return []
def bejson_taxonomies_validator_check_members(members: Any) -> List[str]:
    """Problems with a list of member dicts {descriptor, suffix, field_type} (empty list = valid)."""
    if not isinstance(members, list) or not members:
        return ["members must be a non-empty list"]
    problems: List[str] = []
    seen = set()
    for i, m in enumerate(members):
        if not isinstance(m, dict):
            problems.append(f"member {i}: must be an object")
            continue
        unknown = set(m) - {"descriptor", "suffix", "field_type"}
        if unknown:
            problems.append(f"member {i}: unknown keys {sorted(unknown)}")
        d, sfx, ft = m.get("descriptor"), m.get("suffix"), m.get("field_type")
        if not isinstance(d, str) or not txc.DESCRIPTOR_RE.match(d):
            problems.append(f"member {i}: descriptor {d!r} must match {txc.DESCRIPTOR_RE.pattern}")
        elif d in seen:
            problems.append(f"member {i}: descriptor {d!r} listed twice")
        seen.add(d)
        if not isinstance(sfx, str) or not txc.SUFFIX_TOKEN_RE.match(sfx):
            problems.append(f"member {i} ({d}): suffix {sfx!r} must look like '_name'")
        if ft not in txc.VALID_FIELD_TYPES:
            problems.append(f"member {i} ({d}): field_type {ft!r} not in {txc.VALID_FIELD_TYPES}")
    return problems
def bejson_taxonomies_validator_check_definition(defn: Any) -> List[str]:
    """Problems with a definition dict {set_key, display_name, version, members}."""
    if not isinstance(defn, dict):
        return ["definition must be an object"]
    problems = []
    unknown = set(defn) - {"set_key", "display_name", "version", "members"}
    if unknown:
        problems.append(f"definition: unknown keys {sorted(unknown)}")
    problems += bejson_taxonomies_validator_check_set_key(defn.get("set_key"))
    if not isinstance(defn.get("display_name", ""), str):
        problems.append("display_name must be a string")
    v = defn.get("version", 1)
    if not isinstance(v, int) or isinstance(v, bool) or v < 1:
        problems.append(f"version {v!r} must be an integer >= 1")
    return problems + bejson_taxonomies_validator_check_members(defn.get("members"))
def bejson_taxonomies_validator_check_definition_doc(doc: Any) -> List[str]:
    """Problems with a field-set definition FILE (BEJSON 104a): BEJSON validity first, then shape and content."""
    if not isinstance(doc, dict):
        return ["definition file: not a JSON object"]
    res = validate_bejson(doc)
    if not res.valid:
        return [f"BEJSON: {e}" for e in res.errors]
    problems: List[str] = []
    if doc.get("Format_Version") != "104a":
        problems.append(f"definition file: Format_Version must be 104a, got {doc.get('Format_Version')!r}")
    if doc.get("Records_Type") != [DEFINITION_RECORDS_TYPE]:
        problems.append(f"definition file: Records_Type must be [{DEFINITION_RECORDS_TYPE!r}]")
    fields = [(f.get("name"), f.get("type")) for f in doc.get("Fields", [])]
    if fields != list(DEFINITION_FIELDS):
        problems.append("definition file: Fields do not match the definition schema")
        return problems
    rows = doc.get("Values", [])
    if not rows:
        return problems + ["definition file: no member rows"]
    heads = {(r[0], r[1], r[2]) for r in rows}
    if len(heads) != 1:
        problems.append("definition file: rows disagree on set_key / display_name / version")
    orders = [r[6] for r in rows]
    if orders != list(range(1, len(rows) + 1)):
        problems.append("definition file: order_metric must run 1..n in row order")
    members = [{"descriptor": r[3], "suffix": r[4], "field_type": r[5]} for r in rows]
    problems += bejson_taxonomies_validator_check_members(members)
    if len(heads) == 1:
        set_key, _name, version = next(iter(heads))
        problems += bejson_taxonomies_validator_check_set_key(set_key)
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            problems.append(f"definition file: version {version!r} must be an integer >= 1")
    return problems
def bejson_taxonomies_validator_check_member_against_taxonomy(taxonomy: Dict[str, Any], member: Dict[str, Any]) -> List[str]:
    """A member can be stamped under `taxonomy` only if it registers the member's suffix with the same type."""
    rule = taxonomy["suffix_rules"].get(member["suffix"])
    if rule is None:
        return [f"member {member['descriptor']!r}: suffix {member['suffix']} is not registered by taxonomy {taxonomy['namespace_key']!r}"]
    if rule["field_type"] != member["field_type"]:
        return [f"member {member['descriptor']!r}: type {member['field_type']!r} but taxonomy {taxonomy['namespace_key']!r} requires {rule['field_type']!r} for {member['suffix']}"]
    return []
# ---------------------------------------------------------------------------
# Registry audit
# ---------------------------------------------------------------------------
def _active_ledger(manifest_path: str, entity_name: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = [r for r in txc.read_rows(manifest_path, txc.E_FIELD) if r[txc.FE_LIFECYCLE] == txc.LIFECYCLE_ACTIVE]
    return [r for r in rows if entity_name is None or r[txc.FE_ENTITY] == entity_name]
def _is_exempt(entity_name: str) -> bool:
    return entity_name in txc.CORE_OWNED_ENTITIES or entity_name.startswith("meta-")
def _chain_uuids(taxa: Dict[str, Dict[str, Any]], taxonomy_uuid: str) -> List[str]:
    """taxonomy_uuid plus every ancestor, loop-safe (loops are reported elsewhere)."""
    out: List[str] = []
    cur = taxa.get(taxonomy_uuid)
    while cur is not None and cur["taxonomy_uuid"] not in out:
        out.append(cur["taxonomy_uuid"])
        cur = taxa.get(cur["parent_taxonomy_uuid"]) if cur["parent_taxonomy_uuid"] else None
    return out
def bejson_taxonomies_validator_audit_database(manifest_path: str) -> Dict[str, Any]:
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
        "verified_utc": txc.now_utc(),
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

    taxa = {t["taxonomy_uuid"]: t for t in txc.bejson_taxonomies_list_taxonomies(manifest_path)}
    for t in taxa.values():
        for req in txc.REQUIRED_SUFFIXES:
            if req not in t["suffix_rules"]:
                problems.append(f"taxonomy {t['namespace_key']}: required suffix {req} not registered")
        if t["parent_taxonomy_uuid"] is not None and t["parent_taxonomy_uuid"] not in taxa:
            problems.append(f"taxonomy {t['namespace_key']}: parent {t['parent_taxonomy_uuid']} not found")
    for t in taxa.values():  # parent chains must terminate
        hops, cur = 0, t
        while cur is not None and cur["parent_taxonomy_uuid"] is not None and hops <= len(taxa):
            cur, hops = taxa.get(cur["parent_taxonomy_uuid"]), hops + 1
        if hops > len(taxa):
            problems.append(f"taxonomy {t['namespace_key']}: parent chain loops")
    rule_owner = {r["rule_uuid"]: (t["taxonomy_uuid"], tok)
                  for t in taxa.values() for tok, r in t["suffix_rules"].items()}

    ledger_rows = _active_ledger(manifest_path)
    stats["taxonomies"] = len(taxa)
    stats["ledger_rows"] = len(ledger_rows)
    ledger: Dict[tuple, Dict[str, Any]] = {}
    for r in ledger_rows:
        key = (r[txc.FE_ENTITY], r[txc.FE_COLUMN])
        if key in ledger:
            problems.append(f"ledger has duplicate active entry for {key[0]}.{key[1]}")
        ledger[key] = r

    seen = set()
    entity_names = txc.manifest_entity_names(manifest_path)
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
            if not txc.UUID4_RE.match(f.get("field_uuid", "")):
                problems.append(f"{ent}.{f['name']}: field_uuid not UUIDv4")
            row = ledger.get(key)
            if row is None:
                problems.append(f"{ent}.{f['name']}: not in field ledger")
                continue
            if row[txc.FE_UUID] != f.get("field_uuid"):
                problems.append(f"{ent}.{f['name']}: ledger uuid != field_uuid")
            t = taxa.get(row[txc.FE_TAXONOMY])
            if t is None:
                problems.append(f"{ent}.{f['name']}: ledger taxonomy not found")
                continue
            problems += [f"{ent}: {p}" for p in txc.bejson_taxonomies_check_field_name(t, f["name"], f["type"])]
            problems += txc.bejson_taxonomies_check_entity_name(t, ent)
            token = txc.bejson_taxonomies_match_suffix(t, f["name"])
            if token is not None and rule_owner.get(row[txc.FE_RULE]) != (t["taxonomy_uuid"], token):
                problems.append(f"{ent}.{f['name']}: ledger suffix rule does not match {token}")
            if f.get("fk_target_entity") and token not in (txc.FK_SUFFIX, txc.SLOT_SUFFIX):
                problems.append(f"{ent}.{f['name']}: FK metadata on non-FK suffix")
        for i, vrow in enumerate(doc["Values"]):
            if not txc.UUID4_RE.match(str(vrow[0])):
                problems.append(f"{ent} row {i}: record_uuid not UUIDv4")
            if len(vrow) != len(doc["Fields"]) + 1:
                problems.append(f"{ent} row {i}: width {len(vrow)} != {len(doc['Fields']) + 1}")
        slots = [i for i, n in enumerate(names) if n.endswith(txc.SLOT_SUFFIX)]
        if slots and slots != list(range(len(names) - len(slots), len(names))):
            problems.append(f"{ent}: Z-space slots are not the trailing block")
        for i in slots:
            if any(v[fmap[names[i]]] is not None for v in doc["Values"]):
                problems.append(f"{ent}.{names[i]}: unbound slot holds data")
    stats["fields_total"] = len(seen)
    stale = set(ledger) - seen
    if stale:
        problems.append(f"ledger has {len(stale)} active entr(ies) for missing fields (run sync_ledger)")

    _audit_field_sets(manifest_path, taxa, ledger_rows, entity_names, problems)

    # Z-space reservations must agree with the entity files
    for z in txc.read_rows(manifest_path, txc.E_ZSPACE):
        ent = z[txc.ZS_ENTITY]
        if ent not in entity_names:
            problems.append(f"zspace: entity {ent} not in manifest")
            continue
        fdef = next((f for f in mfdb_core_get_entity_doc(manifest_path, ent)["Fields"]
                     if f["field_uuid"] == z[txc.ZS_FIELD_UUID]), None)
        if fdef is None:
            problems.append(f"zspace: {ent} slot {z[txc.ZS_FIELD_UUID]} missing from entity")
        elif z[txc.ZS_STATE] == txc.ZSTATE_RESERVED:
            if not fdef["name"].endswith(txc.SLOT_SUFFIX) or z[txc.ZS_BOUND] is not None:
                problems.append(f"zspace: {ent}.{fdef['name']} marked reserved but looks bound")
        elif z[txc.ZS_STATE] == txc.ZSTATE_BOUND:
            if fdef["name"] != z[txc.ZS_BOUND] or fdef["name"].endswith(txc.SLOT_SUFFIX):
                problems.append(f"zspace: {ent}.{fdef['name']} marked bound to {z[txc.ZS_BOUND]!r} but differs")
        else:
            problems.append(f"zspace: state {z[txc.ZS_STATE]!r} not in (reserved, bound)")

    # Deployments and links
    dep_tax: Dict[str, str] = {}
    for d in txc.read_rows(manifest_path, txc.E_DEPLOYMENT):
        dep_tax[d["record_uuid"]] = d[txc.DP_TAXONOMY]
        if d[txc.DP_ROLE] not in txc.ROLE_KINDS:
            problems.append(f"deployment {d[txc.DP_NODE]}: role {d[txc.DP_ROLE]!r} not in {txc.ROLE_KINDS}")
        if d[txc.DP_STRATEGY] not in txc.STRATEGY_KINDS:
            problems.append(f"deployment {d[txc.DP_NODE]}: strategy {d[txc.DP_STRATEGY]!r} not in {txc.STRATEGY_KINDS}")
    for i, k in enumerate(txc.read_rows(manifest_path, txc.E_LINK)):
        kind = k[txc.LK_MATCH]
        if kind not in txc.MATCH_KINDS:
            problems.append(f"link row {i}: match_kind {kind!r} not in {txc.MATCH_KINDS}")
            continue
        actual = "identical" if dep_tax.get(k[txc.LK_MASTER]) == dep_tax.get(k[txc.LK_SLAVE]) else "variant"
        if kind != actual:
            problems.append(f"link row {i}: declared {kind} but taxonomies are {actual}")
def _audit_field_sets(manifest_path: str, taxa: Dict[str, Dict[str, Any]], ledger_rows: List[Dict[str, Any]],
                      entity_names: List[str], problems: List[str]) -> None:
    """Field sets (immutable, additive versions) and grafts (a set stamped on an entity)."""
    if not {txc.E_FIELDSET, txc.E_SETMEMBER, txc.E_GRAFT} <= set(entity_names):
        problems.append("registry lacks the field-set entities (schema older than 1.3.0)")
        return
    sets = {r["record_uuid"]: r for r in txc.read_rows(manifest_path, txc.E_FIELDSET)}
    members: Dict[str, List[Dict[str, Any]]] = {}
    by_key_version: Dict[tuple, str] = {}
    for uid, r in sets.items():
        key, ver = r[txc.FS_KEY], r[txc.FS_VERSION]
        problems += [f"field set {key!r}: {p}" for p in bejson_taxonomies_validator_check_set_key(key)]
        if r[txc.FS_STATE] not in txc.FIELDSET_STATES:
            problems.append(f"field set {key!r} v{ver}: state {r[txc.FS_STATE]!r} not in {txc.FIELDSET_STATES}")
        if not isinstance(ver, int) or isinstance(ver, bool) or ver < 1:
            problems.append(f"field set {key!r}: version {ver!r} must be an integer >= 1")
        if (key, ver) in by_key_version:
            problems.append(f"field set {key!r} v{ver}: registered twice")
        by_key_version[(key, ver)] = uid
    for m in txc.read_rows(manifest_path, txc.E_SETMEMBER):
        if m[txc.SM_SET] not in sets:
            problems.append(f"set member {m[txc.SM_DESCRIPTOR]!r}: field set not found")
            continue
        members.setdefault(m[txc.SM_SET], []).append(m)
    triples: Dict[str, set] = {}
    for uid, ms in members.items():
        label = f"{sets[uid][txc.FS_KEY]} v{sets[uid][txc.FS_VERSION]}"
        probs = bejson_taxonomies_validator_check_members(
            [{"descriptor": m[txc.SM_DESCRIPTOR], "suffix": m[txc.SM_SUFFIX], "field_type": m[txc.SM_TYPE]}
             for m in sorted(ms, key=lambda x: x[txc.SM_ORDER])])
        problems += [f"field set {label}: {p}" for p in probs]
        if sorted(m[txc.SM_ORDER] for m in ms) != list(range(1, len(ms) + 1)):
            problems.append(f"field set {label}: member order_metric must run 1..n")
        triples[uid] = {(m[txc.SM_DESCRIPTOR], m[txc.SM_SUFFIX], m[txc.SM_TYPE]) for m in ms}
    for uid in sets:
        if uid not in members:
            problems.append(f"field set {sets[uid][txc.FS_KEY]} v{sets[uid][txc.FS_VERSION]}: has no members")
    for (key, ver), uid in by_key_version.items():  # versions are additive: v(n) keeps every member of v(n-1)
        prev = by_key_version.get((key, ver - 1))
        if prev is not None and not triples.get(prev, set()) <= triples.get(uid, set()):
            problems.append(f"field set {key} v{ver}: drops or changes members of v{ver - 1} (versions are additive)")

    owner: Dict[str, str] = {}
    for r in ledger_rows:
        owner.setdefault(r[txc.FE_ENTITY], r[txc.FE_TAXONOMY])
    grafts = {g["record_uuid"]: g for g in txc.read_rows(manifest_path, txc.E_GRAFT)}
    all_ledger = txc.read_rows(manifest_path, txc.E_FIELD)
    member_rows = {m["record_uuid"]: m for ms in members.values() for m in ms}
    by_graft: Dict[str, List[Dict[str, Any]]] = {}
    for row in all_ledger:
        g_fk, m_fk = row[txc.FE_GRAFT], row[txc.FE_SETMEMBER]
        if (g_fk is None) != (m_fk is None):
            problems.append(f"{row[txc.FE_ENTITY]}.{row[txc.FE_COLUMN]}: graft and set-member links must be set together")
        if g_fk is not None:
            if g_fk not in grafts:
                problems.append(f"{row[txc.FE_ENTITY]}.{row[txc.FE_COLUMN]}: graft not found")
            by_graft.setdefault(g_fk, []).append(row)
    seen_keys = set()
    for guid, g in grafts.items():
        label = g[txc.GR_KEY]
        if label in seen_keys:
            problems.append(f"graft {label}: registered twice")
        seen_keys.add(label)
        fset = sets.get(g[txc.GR_SET])
        tax = taxa.get(g[txc.GR_TAXONOMY])
        ent = g[txc.GR_ENTITY]
        if fset is None:
            problems.append(f"graft {label}: field set not found")
            continue
        if tax is None:
            problems.append(f"graft {label}: taxonomy not found")
            continue
        if fset[txc.FS_STATE] == "retired":
            problems.append(f"graft {label}: field set {fset[txc.FS_KEY]!r} is retired but still grafted")
        if ent not in entity_names:
            problems.append(f"graft {label}: entity {ent!r} not in manifest")
            continue
        if owner.get(ent) != tax["taxonomy_uuid"]:
            problems.append(f"graft {label}: entity {ent!r} is not owned by taxonomy {tax['namespace_key']!r}")
        if not txc.FIELD_NAME_RE.match(g[txc.GR_SUBJECT] or ""):
            problems.append(f"graft {label}: subject {g[txc.GR_SUBJECT]!r} is not snake_case")
        edoc = mfdb_core_get_entity_doc(manifest_path, ent)
        by_uuid = {f["field_uuid"]: f for f in edoc["Fields"]}
        descriptors = set()
        for row in by_graft.get(guid, []):
            m = member_rows.get(row[txc.FE_SETMEMBER])
            where = f"graft {label}: {row[txc.FE_COLUMN]}"
            if m is None:
                problems.append(f"{where}: set member not found")
                continue
            if sets[m[txc.SM_SET]][txc.FS_KEY] != fset[txc.FS_KEY]:
                problems.append(f"{where}: member belongs to field set {sets[m[txc.SM_SET]][txc.FS_KEY]!r}, not {fset[txc.FS_KEY]!r}")
            if m[txc.SM_DESCRIPTOR] in descriptors:
                problems.append(f"{where}: descriptor {m[txc.SM_DESCRIPTOR]!r} grafted twice")
            descriptors.add(m[txc.SM_DESCRIPTOR])
            if row[txc.FE_LIFECYCLE] != txc.LIFECYCLE_ACTIVE:
                continue
            fdef = by_uuid.get(row[txc.FE_UUID])
            if fdef is None:
                problems.append(f"{where}: field missing from {ent}")
                continue
            if fdef["type"] != m[txc.SM_TYPE]:
                problems.append(f"{where}: type {fdef['type']!r} but member {m[txc.SM_DESCRIPTOR]!r} is {m[txc.SM_TYPE]!r}")
            if not fdef["name"].endswith(m[txc.SM_SUFFIX]):
                problems.append(f"{where}: name does not end in member suffix {m[txc.SM_SUFFIX]}")
            problems += [f"{where}: {p}" for p in bejson_taxonomies_validator_check_member_against_taxonomy(
                tax, {"descriptor": m[txc.SM_DESCRIPTOR], "suffix": m[txc.SM_SUFFIX], "field_type": m[txc.SM_TYPE]})]
        missing = {m[txc.SM_DESCRIPTOR] for m in members.get(g[txc.GR_SET], [])} - descriptors
        if missing:
            problems.append(f"graft {label}: incomplete, missing members {sorted(missing)}")
