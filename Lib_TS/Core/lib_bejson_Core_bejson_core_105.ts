/**
 * Library:        lib_bejson_Core_bejson_core_105.ts
 * Family:         Core
 * Description:    Format_Version 105/105a/105db ("Integrity Era") functions.
 *                 TypeScript parity port of lib_bejson_Core_bejson_core.py's
 *                 3.3.0 UUID features (Phase 2 UUID addressing, Phase 4 upgrade
 *                 utility, define_field). Kept in its own file rather than appended
 *                 to lib_bejson_Core_bejson_core.ts, matching this
 *                 library's existing per-concern file split (field map,
 *                 schema, chunking are already separate files).
 *
 *                 DESIGN ADAPTATIONS FROM THE PYTHON VERSION (deliberate,
 *                 not omissions -- each one matches an existing, established
 *                 convention already present elsewhere in this TS library):
 *
 *                 1. IMMUTABLE RETURNS. Every existing mutator in
 *                    lib_bejson_Core_bejson_core.ts (appendRecord,
 *                    updateRecord, deleteRecord, setFieldValue) takes a doc
 *                    and returns a NEW doc, never mutating the input in
 *                    place. Every 105-series mutator below follows the same
 *                    contract. Python's version mutates doc in place; this
 *                    is the correct adaptation to this file's own idiom,
 *                    not a deviation from it.
 *
 *                 2. UUID-AWARE FIELD MAP. Field lookups (resolveFieldIndex,
 *                    writeCell, defineField's name check, removeField) go
 *                    through bejson_core_get_field_map_105() in
 *                    lib_bejson_Core_bejson_field_map.ts -- byName + byUuid
 *                    maps keyed on the doc's real field identity, so a
 *                    stale map can never be served. Mirrors Python's
 *                    by_name/by_uuid cache. No transaction batching
 *                    primitive (immutable returns make it unnecessary).
 *
 *                 3. NO DISK I/O. This file (like bejson_core.ts) has zero
 *                    filesystem coupling -- no `fs` import anywhere.
 *                    upgradeTo105() is therefore a pure in-memory transform,
 *                    same shape as createEmpty104/serialize. Backup-before-
 *                    write and atomic-write-to-disk (which Python's
 *                    bejson_core_upgrade_to_105 does do) are the caller's
 *                    responsibility here, using whatever fs layer the
 *                    calling application already has -- exactly how
 *                    parse()/serialize() already work in this file.
 *
 *
 *                 5. addField (Python's plain Phase-2 version) is NOT
 *                    ported separately -- defineField() below (Phase 8)
 *                    is a strict superset: called with no optional
 *                    constraint arguments, it behaves identically to what
 *                    a bare addField would have been. Since TS had no
 *                    pre-existing addField to preserve compatibility with
 *                    (unlike Python, where add_field already existed before
 *                    Phase 8 and had to stay untouched), there is no reason
 *                    to ship two functions here.
 *
 * Version:        1.3.0
 * Date:           2026-09-25
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  bd6f0f3c-47af-48a3-ace1-663e51f2ff90
 * Release_Version: 300
 *
 * Changelog:
 *   1.3.0 - REMOVED upsert105, rowChecksum, verifyRowChecksums, paginate105
 *           (and the crypto.subtle checksum plumbing) per Be25 -- only UUID
 *           features, FK referential integrity and the UUID field map stay.
 *           Field lookups now use the cached UUID-aware field map instead of
 *           per-call findIndex scans.
 *   1.2.0 - defineField()/DefineFieldOptions: removed required/unique/enum/min/
 *           max/minLength/maxLength and their option-shape checks, per Be25.
 *           Type check, duplicate-name check and fk_target_entity/fk_on_delete
 *           (FK/cascade) are unchanged.
 *   1.1.0 - Updated defineField()'s duplicate-name throw to use the
 *           renamed E.FIELD_NAME_ALREADY_EXISTS (was E.DUPLICATE_FIELD_NAME,
 *           code unchanged at 84) per lib_bejson_Core_bejson_types.ts v2.7.0.
 */

import {
  BEJSONDocument,
  BEJSONField,
  BEJSONValue,
  BEJSONCoreError,
  BEJSON_105_CODES as E,
} from "./lib_bejson_Core_bejson_types";
import { bejson_core_get_field_map_105 } from "./lib_bejson_Core_bejson_field_map";

const _105_SERIES = new Set(["105", "105a", "105db"]);

function _isMulti(doc: BEJSONDocument): boolean {
  return doc.Format_Version === "105db";
}
function _offset(doc: BEJSONDocument): number {
  return _isMulti(doc) ? 2 : 1;
}
function _uuidCol(doc: BEJSONDocument): number {
  return _isMulti(doc) ? 1 : 0;
}
function _assert105(doc: BEJSONDocument, fnName: string): void {
  if (!_105_SERIES.has(doc.Format_Version)) {
    throw new BEJSONCoreError(
      E.FORMAT_UNSUPPORTED,
      `${fnName} requires a 105-series document, got ${JSON.stringify(doc.Format_Version)}`
    );
  }
}
function _cloneWith(doc: BEJSONDocument, overrides: Partial<BEJSONDocument>): BEJSONDocument {
  return Object.assign({}, doc, overrides);
}
function _uuid4(): string {
  // crypto.randomUUID is available in Node 16.7+ and all evergreen browsers,
  // matching this file's existing use of the global `crypto` object
  // (crypto.subtle, crypto.getRandomValues) elsewhere in the Core family.
  return crypto.randomUUID();
}
function _findRowByUuid(doc: BEJSONDocument, recordUuid: string): number {
  const col = _uuidCol(doc);
  for (let i = 0; i < doc.Values.length; i++) {
    if (doc.Values[i][col] === recordUuid) return i;
  }
  return -1;
}

// ---------------------------------------------------------------------------
// \u00a72.1 Hybrid Index Resolver
// ---------------------------------------------------------------------------

export type FieldTarget = string | { name?: string; field_uuid?: string };

/**
 * Resolves a field's absolute column index (i.e. its position in a Values
 * row, including the reserved record_uuid/discriminator offset) by name,
 * by field_uuid, or both (a {name, field_uuid} pair, which must agree).
 */
export function resolveFieldIndex(doc: BEJSONDocument, target: FieldTarget): number {
  _assert105(doc, "resolveFieldIndex");
  const offset = _offset(doc);

  const fmap = bejson_core_get_field_map_105(doc);

  if (typeof target === "object") {
    const byName = fmap.byName.get(target.name as string) ?? -1;
    const byUuid = fmap.byUuid.get(target.field_uuid as string) ?? -1;
    if (byName === -1 || byUuid === -1 || byName !== byUuid) {
      throw new BEJSONCoreError(
        E.FIELD_INTEGRITY_MISMATCH,
        `name=${JSON.stringify(target.name)} resolves to ${byName}, field_uuid=${JSON.stringify(target.field_uuid)} resolves to ${byUuid}`
      );
    }
    return byName + offset;
  }

  const byUuidIdx = fmap.byUuid.get(target);
  if (byUuidIdx !== undefined) return byUuidIdx + offset;
  const byNameIdx = fmap.byName.get(target);
  if (byNameIdx !== undefined) return byNameIdx + offset;

  throw new BEJSONCoreError(E.FIELD_INTEGRITY_MISMATCH, `unresolvable target ${JSON.stringify(target)}`);
}

// ---------------------------------------------------------------------------
// \u00a72.2 Dual-Key Write Verification
// ---------------------------------------------------------------------------

export interface WriteCellResult {
  doc: BEJSONDocument;
  row: number;
  col: number;
  healed: boolean;
}

/**
 * Writes newValue into the cell identified by (recordUuid, fieldUuid).
 * expectedRow/expectedCol are the caller's last-known coordinates -- a
 * mismatch does not fail the write; it re-locates and heals it, reporting
 * healed: true so the caller can refresh its cached coordinates. Returns a
 * NEW document (immutable contract -- see file header, adaptation 1).
 */
export function writeCell(
  doc: BEJSONDocument,
  recordUuid: string,
  fieldUuid: string,
  newValue: BEJSONValue,
  opts: { expectedRow?: number; expectedCol?: number } = {}
): WriteCellResult {
  _assert105(doc, "writeCell");

  const fieldIdx = bejson_core_get_field_map_105(doc).byUuid.get(fieldUuid) ?? -1;
  if (fieldIdx === -1) {
    throw new BEJSONCoreError(E.FIELD_INTEGRITY_MISMATCH, `unknown field_uuid ${JSON.stringify(fieldUuid)}`);
  }
  const row = _findRowByUuid(doc, recordUuid);
  if (row === -1) {
    throw new BEJSONCoreError(E.RECORD_NOT_FOUND, `unknown record_uuid ${JSON.stringify(recordUuid)}`);
  }

  const col = fieldIdx + _offset(doc);
  const healed =
    (opts.expectedRow !== undefined && opts.expectedRow !== row) ||
    (opts.expectedCol !== undefined && opts.expectedCol !== col);

  const newRow = [...doc.Values[row]];
  newRow[col] = newValue;
  const newValues = doc.Values.map((r, i) => (i === row ? newRow : r));

  return { doc: _cloneWith(doc, { Values: newValues }), row, col, healed };
}

// ---------------------------------------------------------------------------
// \u00a72.3 / Phase 8 -- defineField (supersedes a bare addField; see header)
// ---------------------------------------------------------------------------

export interface DefineFieldOptions {
  fk_target_entity?: string;
  fk_on_delete?: "restrict" | "cascade" | "null";
}

export interface DefineFieldResult {
  doc: BEJSONDocument;
  fieldUuid: string;
}

const VALID_FIELD_TYPES = new Set(["string", "integer", "number", "boolean", "array", "object"]);

/**
 * The one sanctioned way to add a field to a 105-series document under
 * construction. Validates EAGERLY, before anything is appended:
 *   - type must be one of the 6 canonical BEJSON types
 *   - name must not already exist
 *   - fk_on_delete requires fk_target_entity, and must be restrict/cascade/null
 * Returns a NEW document plus the generated field_uuid.
 */
export function defineField(
  doc: BEJSONDocument,
  name: string,
  type: string,
  opts: DefineFieldOptions = {}
): DefineFieldResult {
  _assert105(doc, "defineField");

  if (!VALID_FIELD_TYPES.has(type)) {
    throw new BEJSONCoreError(
      E.FIELD_INTEGRITY_MISMATCH,
      `type must be one of ${JSON.stringify([...VALID_FIELD_TYPES])}, got ${JSON.stringify(type)}`
    );
  }
  if (bejson_core_get_field_map_105(doc).byName.has(name)) {
    throw new BEJSONCoreError(E.FIELD_NAME_ALREADY_EXISTS, `${JSON.stringify(name)} already exists`);
  }
  if (opts.fk_on_delete !== undefined) {
    if (opts.fk_target_entity === undefined) {
      throw new BEJSONCoreError(E.FIELD_INTEGRITY_MISMATCH, "fk_on_delete requires fk_target_entity to also be set");
    }
    if (!["restrict", "cascade", "null"].includes(opts.fk_on_delete)) {
      throw new BEJSONCoreError(E.FIELD_INTEGRITY_MISMATCH, `fk_on_delete must be restrict/cascade/null, got ${opts.fk_on_delete}`);
    }
  }

  let fieldUuid = _uuid4();
  const existingUuids = new Set(doc.Fields.map((f) => f.field_uuid));
  while (existingUuids.has(fieldUuid)) fieldUuid = _uuid4(); // ~impossible; defensive regenerate

  const field: BEJSONField = { name, type: type as BEJSONField["type"], field_uuid: fieldUuid };
  if (opts.fk_target_entity !== undefined) field.fk_target_entity = opts.fk_target_entity;
  if (opts.fk_on_delete !== undefined)     field.fk_on_delete = opts.fk_on_delete;

  const newFields = [...doc.Fields, field];
  const newValues = doc.Values.map((row) => [...row, null]); // positional integrity, matches Python's Phase-2 bugfix

  return { doc: _cloneWith(doc, { Fields: newFields, Values: newValues }), fieldUuid };
}

// ---------------------------------------------------------------------------
// \u00a72.3 addRecord105
// ---------------------------------------------------------------------------

export interface AddRecordResult {
  doc: BEJSONDocument;
  recordUuid: string;
}

export function addRecord105(doc: BEJSONDocument, values: BEJSONValue[]): AddRecordResult {
  _assert105(doc, "addRecord105");

  const recordUuid = _uuid4();
  const row: BEJSONValue[] = _isMulti(doc)
    ? [values[0], recordUuid, ...values.slice(1)]
    : [recordUuid, ...values];

  return { doc: _cloneWith(doc, { Values: [...doc.Values, row] }), recordUuid };
}

// ---------------------------------------------------------------------------
// \u00a72.5 removeField / deleteRecord105
// ---------------------------------------------------------------------------

export function removeField(doc: BEJSONDocument, target: string): BEJSONDocument {
  _assert105(doc, "removeField");

  const fmap = bejson_core_get_field_map_105(doc);
  const col = fmap.byUuid.get(target) ?? fmap.byName.get(target) ?? -1;
  if (col === -1) {
    throw new BEJSONCoreError(E.FIELD_INTEGRITY_MISMATCH, `unknown field ${JSON.stringify(target)}`);
  }
  const offset = _offset(doc);
  const newFields = doc.Fields.filter((_, i) => i !== col);
  const newValues = doc.Values.map((row) => row.filter((_, i) => i !== col + offset));

  return _cloneWith(doc, { Fields: newFields, Values: newValues });
}

export function deleteRecord105(doc: BEJSONDocument, recordUuid: string): BEJSONDocument {
  _assert105(doc, "deleteRecord105");

  const row = _findRowByUuid(doc, recordUuid);
  if (row === -1) {
    throw new BEJSONCoreError(E.RECORD_NOT_FOUND, `unknown record_uuid ${JSON.stringify(recordUuid)}`);
  }
  return _cloneWith(doc, { Values: doc.Values.filter((_, i) => i !== row) });
}

// ---------------------------------------------------------------------------
// \u00a72.6 verify105Integrity (read-only)
// ---------------------------------------------------------------------------

export interface Integrity105Report {
  ok: boolean;
  fieldCount: number;
  recordCount: number;
  errors: { code: string; detail: string }[];
  reason?: string;
}

/**
 * Read-only health check. Never mutates doc. Mirrors
 * check105StrictIntegrity's logic directly (kept independent of
 * lib_bejson_Core_bejson_validators.ts to avoid a circular import --
 * same reasoning as Python's lazy in-function import).
 */
export function verify105Integrity(doc: BEJSONDocument): Integrity105Report {
  if (!_105_SERIES.has(doc.Format_Version)) {
    return { ok: false, fieldCount: 0, recordCount: 0, errors: [], reason: "E_FORMAT_UNSUPPORTED" };
  }

  const errors: { code: string; detail: string }[] = [];
  const seenFieldUuids = new Set<string>();
  for (const field of doc.Fields) {
    if (!field.field_uuid) {
      errors.push({ code: "E_INVALID_FIELDS", detail: `field ${field.name} missing a valid field_uuid` });
    } else if (seenFieldUuids.has(field.field_uuid)) {
      errors.push({ code: "E_INVALID_FIELDS", detail: `duplicate field_uuid ${field.field_uuid}` });
    } else {
      seenFieldUuids.add(field.field_uuid);
    }
  }

  const uuidCol = _uuidCol(doc);
  const seenRecordUuids = new Set<string>();
  doc.Values.forEach((row, i) => {
    const ruuid = row[uuidCol];
    if (typeof ruuid !== "string" || !ruuid) {
      errors.push({ code: "E_INVALID_VALUES", detail: `row ${i} missing a valid record_uuid at index ${uuidCol}` });
    } else if (seenRecordUuids.has(ruuid)) {
      errors.push({ code: "E_INVALID_VALUES", detail: `duplicate record_uuid ${ruuid} at row ${i}` });
    } else {
      seenRecordUuids.add(ruuid);
    }
  });

  if (doc.Fields.length === 0 || !doc.Fields.every((f) => "field_uuid" in f)) {
    errors.push({
      code: "E_INVALID_FIELDS",
      detail: "Format_Version claims 105-series but Fields were never compiled with field_uuid keys -- run upgradeTo105() first",
    });
  }

  return { ok: errors.length === 0, fieldCount: doc.Fields.length, recordCount: doc.Values.length, errors };
}

// ---------------------------------------------------------------------------
// Phase 4 -- upgradeTo105 (pure in-memory transform; see header adaptation 3)
// ---------------------------------------------------------------------------

/**
 * Upgrades a 104/104a/104db document to 105/105a/105db in memory.
 * 104 -> 105, 104a -> 105a, 104db -> 105db (explicit mapping -- this is
 * the exact bug the Python port shipped with initially and then fixed;
 * ported here already correct). Does NOT write to disk, back up, or
 * validate the result -- pure transform, caller's responsibility for the
 * rest, matching this file's zero-fs-coupling design (adaptation 3).
 */
export function upgradeTo105(doc: BEJSONDocument): BEJSONDocument {
  if (!["104", "104a", "104db"].includes(doc.Format_Version)) {
    throw new BEJSONCoreError(E.FORMAT_UNSUPPORTED, `upgradeTo105 takes a 104-series doc, got ${doc.Format_Version}`);
  }
  const isMulti = doc.Format_Version === "104db";
  const targetVersion = ({ "104": "105", "104a": "105a", "104db": "105db" } as const)[
    doc.Format_Version as "104" | "104a" | "104db"
  ];

  const newFields = doc.Fields.map((f) => ({ ...f, field_uuid: _uuid4() }));
  const newValues = doc.Values.map((row) => {
    const recordUuid = _uuid4();
    return isMulti ? [row[0], recordUuid, ...row.slice(1)] : [recordUuid, ...row];
  });

  return _cloneWith(doc, { Format_Version: targetVersion, Fields: newFields, Values: newValues });
}
