/**
 * Library:        lib_bejson_Core_bejson_validators.ts
 * Family:         Core
 * Description:    Structural integrity checker for positional values and mandatory keys.
 * Version:        2.3.0
 * Date:           2026-10-27
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  244fbc9c-10b6-4c1e-a77a-0a1e6bf999cd
 * Release_Version: 300
 *
 * Changelog:
 *   2.3.0 - 105<->104 parity (port of Python validator 3.4.0): 105-series now
 *           enforces everything its 104 base enforces -- row length
 *           (len(Fields)+1), value types (offset-aware, 105db included),
 *           Records_Type count (105/105a exactly 1, 105db 2+), 105a
 *           primitives-only, 105db Record_Type_Parent rules (first field,
 *           per-field owner, discriminator at column 0), and the custom-header
 *           rules (105/105db forbid, 105a allows). New exports
 *           check105Values(), check105UuidFormat() (advisory warnings only),
 *           valueTypeProblem(), rowColumn(). check105StrictIntegrity() now
 *           includes check105Values(). 104-series behaviour unchanged.
 *   2.2.0 - REMOVED check105SchemaConstraints() and its wrapper/call site in
 *           validateDocument(), plus the now-unused E105/BEJSONValue imports,
 *           per Be25. check105StrictIntegrity() is untouched.
 *   2.1.0 - Phase 2.7 TS parity: validVersions widened to 105/105a/105db;
 *           check105StrictIntegrity() and check105SchemaConstraints()
 *           added and wired into validateDocument() as a guarded branch
 *           replacing _checkValues() for 105-series (same reason as the
 *           Python port: the raw positional length/type check has no
 *           concept of the reserved record_uuid column). 104-series call
 *           sequence is untouched.
 */

import {
  BEJSONDocument,
  BEJSONField,
  BEJSONFieldType,
  BEJSONPrimitiveType,
  ValidationResult,
  ValidationError,
  ValidationWarning,
  BEJSONValidationError,
  BEJSON_VALIDATION_CODES as E,
} from "./lib_bejson_Core_bejson_types";

const FIELD_MAP_KEY = "_bejson_field_map";
const IN_MEMORY_ONLY_KEYS: ReadonlySet<string> = new Set(["_nestingFieldMap"]);

function _checkFieldMapCache(d: Record<string, unknown>, r: ValidationResult): void {
  if (!(FIELD_MAP_KEY in d)) return;
  const cached = d[FIELD_MAP_KEY];
  const fields = Array.isArray(d.Fields) ? (d.Fields as Array<{ name?: unknown }>) : [];
  const ok = cached !== null && typeof cached === "object" && !Array.isArray(cached)
    && Object.keys(cached as object).length === fields.length
    && fields.every((f, i) => !!f && (cached as Record<string, unknown>)[String(f.name)] === i);
  if (!ok) {
    _err(r, E.RESERVED_KEY_COLLISION, "In-memory \"" + FIELD_MAP_KEY + "\" does not match Fields (stale or forged).", FIELD_MAP_KEY);
  }
}

function _checkReservedKeys(d: Record<string, unknown>, r: ValidationResult): void {
  for (const key of Object.keys(d)) {
    if (key.startsWith("_") && key !== FIELD_MAP_KEY && !IN_MEMORY_ONLY_KEYS.has(key)) {
      _err(r, E.RESERVED_KEY_COLLISION, "Key \"" + key + "\" uses the reserved \"_\" prefix.", key);
    }
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function validateDocument(doc: unknown): ValidationResult {
  const result = _makeResult();

  // Step 1: structural sanity before touching any BEJSON fields
  if (doc === null || doc === undefined || typeof doc !== "object" || Array.isArray(doc)) {
    _err(result, E.INVALID_FORMAT_VALUE, "Document root must be a non-null object.");
    return result;
  }

  const d = doc as Record<string, unknown>;

  _checkFieldMapCache(d, result);
  _checkReservedKeys(d, result);

  // Step 2: mandatory keys
  _checkMandatoryKeys(d, result);
  if (!result.valid) return result; // can't proceed without the six keys

  const bej = doc as BEJSONDocument;

  // Step 3: top-level value checks (Format, Format_Creator, Format_Version)
  _checkTopLevel(bej, result);
  if (!result.valid) return result;

  // Step 4: Fields array
  _checkFields(bej, result);
  if (!result.valid) return result;

  // Step 5: Values array. 105-series has a reserved record_uuid (+
  // discriminator for 105db) column that _checkValues's raw positional
  // length/type check does not account for -- skip it for 105-series and
  // run the dedicated 105 checks instead (mirrors the Python validator's
  // exact same guard, added for the exact same reason).
  const is105Series = bej.Format_Version === "105" || bej.Format_Version === "105a" || bej.Format_Version === "105db";
  if (!is105Series) {
    _checkValues(bej, result);
  } else {
    for (const e of _check105StrictIntegrity(bej)) _err(result, e.code, e.message);
    for (const w of check105UuidFormat(bej)) _warn(result, E.INVALID_VALUES, w);
    _check105Specific(bej, result);
  }

  // Step 6: version-specific rules. Unchanged for 104-series; 105-series
  // never reaches any of these three (each one gates on the literal
  // "104"/"104a"/"104db" string), same bypass behavior as Python.
  switch (bej.Format_Version) {
    case "104":
      _check104Specific(bej, result);
      break;
    case "104a":
      _check104aSpecific(bej, result);
      break;
    case "104db":
      _check104dbSpecific(bej, result);
      break;
  }

  return result;
}

export function validate104(doc: unknown): ValidationResult {
  const result = validateDocument(doc);
  if (result.valid) {
    const bej = doc as BEJSONDocument;
    if (bej.Format_Version !== "104") {
      _err(result, E.INVALID_FORMAT_VERSION, "Expected Format_Version \"104\", got \"" + bej.Format_Version + "\".");
    }
  }
  return result;
}

export function validate104a(doc: unknown): ValidationResult {
  const result = validateDocument(doc);
  if (result.valid) {
    const bej = doc as BEJSONDocument;
    if (bej.Format_Version !== "104a") {
      _err(result, E.INVALID_FORMAT_VERSION, "Expected Format_Version \"104a\", got \"" + bej.Format_Version + "\".");
    }
  }
  return result;
}

export function validate104db(doc: unknown): ValidationResult {
  const result = validateDocument(doc);
  if (result.valid) {
    const bej = doc as BEJSONDocument;
    if (bej.Format_Version !== "104db") {
      _err(result, E.INVALID_FORMAT_VERSION, "Expected Format_Version \"104db\", got \"" + bej.Format_Version + "\".");
    }
  }
  return result;
}

export function assertValid(doc: unknown): void {
  const result = validateDocument(doc);
  if (!result.valid && result.errors.length > 0) {
    const e = result.errors[0];
    throw new BEJSONValidationError(e.code, e.message);
  }
}

export function isValid(doc: unknown): boolean {
  return validateDocument(doc).valid;
}

// ---------------------------------------------------------------------------
// Step 2 — mandatory keys
// ---------------------------------------------------------------------------

const MANDATORY_KEYS = ["Format", "Format_Version", "Format_Creator", "Records_Type", "Fields", "Values"] as const;

function _checkMandatoryKeys(d: Record<string, unknown>, r: ValidationResult): void {
  for (const key of MANDATORY_KEYS) {
    if (!(key in d) || d[key] === undefined) {
      _err(r, E.MISSING_MANDATORY_KEY, "Missing mandatory key: " + key, key);
    }
  }
}

// ---------------------------------------------------------------------------
// Step 3 — top-level value constraints
// ---------------------------------------------------------------------------

function _checkTopLevel(doc: BEJSONDocument, r: ValidationResult): void {
  if (doc.Format !== "BEJSON") {
    _err(r, E.INVALID_FORMAT_VALUE, "Format must be \"BEJSON\", got \"" + doc.Format + "\".", "Format");
  }

  const validVersions = ["104", "104a", "104db", "105", "105a", "105db"];
  if (!validVersions.includes(doc.Format_Version as string)) {
    _err(r, E.INVALID_FORMAT_VERSION, "Format_Version must be one of " + JSON.stringify(validVersions) + ", got \"" + doc.Format_Version + "\".", "Format_Version");
  }

  if (doc.Format_Creator !== "Elton Boehnen") {
    _err(r, E.INVALID_FORMAT_CREATOR, "Format_Creator must be \"Elton Boehnen\", got \"" + doc.Format_Creator + "\".", "Format_Creator");
  }

  if (!Array.isArray(doc.Records_Type) || doc.Records_Type.length === 0) {
    _err(r, E.INVALID_RECORDS_TYPE, "Records_Type must be a non-empty array.", "Records_Type");
  } else {
    for (const rt of doc.Records_Type) {
      if (typeof rt !== "string" || rt.trim() === "") {
        _err(r, E.INVALID_RECORDS_TYPE, "All Records_Type entries must be non-empty strings.", "Records_Type");
        break;
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Step 4 — Fields array
// ---------------------------------------------------------------------------

const VALID_TYPES: BEJSONFieldType[] = ["string", "integer", "number", "boolean", "array", "object"];

function _checkFields(doc: BEJSONDocument, r: ValidationResult): void {
  if (!Array.isArray(doc.Fields) || doc.Fields.length === 0) {
    _err(r, E.INVALID_FIELDS, "Fields must be a non-empty array.", "Fields");
    return;
  }

  const seen = new Set<string>();
  for (let i = 0; i < doc.Fields.length; i++) {
    const field = doc.Fields[i] as BEJSONField;

    if (!field || typeof field !== "object") {
      _err(r, E.INVALID_FIELDS, "Fields[" + i + "] must be an object.", "Fields");
      continue;
    }
    if (typeof field.name !== "string" || field.name.trim() === "") {
      _err(r, E.INVALID_FIELDS, "Fields[" + i + "].name must be a non-empty string.", "Fields");
    }
    if (!VALID_TYPES.includes(field.type as BEJSONFieldType)) {
      _err(r, E.INVALID_FIELDS, "Fields[" + i + "].type is invalid: \"" + field.type + "\".", "Fields");
    }
    if (seen.has(field.name)) {
      _err(r, E.DUPLICATE_FIELD_NAME, "Duplicate field name: \"" + field.name + "\".", field.name);
    } else {
      seen.add(field.name);
    }
  }
}

// ---------------------------------------------------------------------------
// Step 5 — Values array
// ---------------------------------------------------------------------------

function _checkValues(doc: BEJSONDocument, r: ValidationResult): void {
  if (!Array.isArray(doc.Values)) {
    _err(r, E.INVALID_VALUES_STRUCTURE, "Values must be an array.", "Values");
    return;
  }

  const fieldCount = doc.Fields.length;

  for (let i = 0; i < doc.Values.length; i++) {
    const row = doc.Values[i];
    if (!Array.isArray(row)) {
      _err(r, E.INVALID_VALUES_STRUCTURE, "Values[" + i + "] must be an array.", undefined, i);
      continue;
    }
    if (row.length !== fieldCount) {
      _err(r, E.RECORD_LENGTH_MISMATCH,
        "Values[" + i + "] has " + row.length + " elements but Fields has " + fieldCount + ".",
        undefined, i);
      continue;
    }

    // Type-check each cell
    for (let fi = 0; fi < fieldCount; fi++) {
      const field = doc.Fields[fi];
      const val = row[fi];
      if (val === null) continue; // null always valid
      if (!_typeMatches(val, field.type)) {
        _err(r, E.VALUE_TYPE_MISMATCH,
          "Values[" + i + "][" + fi + "] (" + field.name + "): expected " + field.type + ", got " + typeof val + ".",
          field.name, i);
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Format 105 ("Integrity Era") checks -- 105/105a/105db only. Mirrors
// lib_bejson_Core_bejson_validator.py's bejson_validator_check_105_
// strict_integrity() exactly (same logic, numeric error codes instead of Python's string
// codes, matching this file's own ValidationError.code: number contract).
// ---------------------------------------------------------------------------

function _is105Multi(doc: BEJSONDocument): boolean {
  return doc.Format_Version === "105db";
}

/**
 * Every field must carry a unique field_uuid; every record row must carry
 * a unique, non-null record_uuid at the format-correct offset; and --
 * Fail-on-Switch -- a document whose header was bumped to 105 without the
 * UUIDs actually being compiled must fail here, not drift silently
 * downstream.
 */
export function check105StrictIntegrity(doc: BEJSONDocument): { code: number; message: string }[] {
  const errors: { code: number; message: string }[] = [];

  const seenFieldUuids = new Set<string>();
  for (const field of doc.Fields) {
    if (!field.field_uuid) {
      errors.push({ code: E.INVALID_FIELDS, message: `field ${JSON.stringify(field.name)} missing a valid field_uuid` });
    } else if (seenFieldUuids.has(field.field_uuid)) {
      errors.push({ code: E.INVALID_FIELDS, message: `duplicate field_uuid ${field.field_uuid}` });
    } else {
      seenFieldUuids.add(field.field_uuid);
    }
  }

  const isMulti = _is105Multi(doc);
  const uuidCol = isMulti ? 1 : 0;
  const seenRecordUuids = new Set<string>();
  (Array.isArray(doc.Values) ? doc.Values : []).forEach((row, i) => {
    const ruuid = Array.isArray(row) ? row[uuidCol] : undefined;
    if (typeof ruuid !== "string" || !ruuid) {
      errors.push({ code: E.INVALID_VALUES, message: `row ${i} missing a valid record_uuid at index ${uuidCol}` });
    } else if (seenRecordUuids.has(ruuid)) {
      errors.push({ code: E.INVALID_VALUES, message: `duplicate record_uuid ${ruuid} at row ${i}` });
    } else {
      seenRecordUuids.add(ruuid);
    }
  });

  if (doc.Fields.length === 0 || !doc.Fields.every((f) => "field_uuid" in f)) {
    errors.push({
      code: E.INVALID_FIELDS,
      message: "Format_Version claims 105-series but Fields were never compiled with field_uuid keys -- run upgradeTo105() first",
    });
  }

  errors.push(...check105Values(doc));
  return errors;
}

const MAX_SHAPE_ERRORS = 100; // cap row/type findings so a huge broken file cannot flood the result

/** Single source of truth for value typing: null if val conforms to type (null always conforms), else 'expected X'. */
export function valueTypeProblem(val: unknown, type: string): string | null {
  if (val === null || val === undefined) return val === null ? null : "expected " + type + ", got undefined";
  switch (type) {
    case "string": return typeof val === "string" ? null : "expected string";
    case "integer": return typeof val === "number" && Number.isInteger(val) ? null : "expected integer";
    case "number": return typeof val === "number" ? null : (typeof val === "boolean" ? "expected number, got bool" : "expected number");
    case "boolean": return typeof val === "boolean" ? null : "expected boolean";
    case "array": return Array.isArray(val) ? null : "expected array";
    case "object": return typeof val === "object" && !Array.isArray(val) ? null : "expected object";
    default: return null;
  }
}

/** Absolute Values-row column of Fields[fieldIdx]: i (104-series), i+1 (105/105a), 0 for 105db Fields[0] else i+1. */
export function rowColumn(version: string, fieldIdx: number): number {
  if (version === "105db") return fieldIdx === 0 ? 0 : fieldIdx + 1;
  return fieldIdx + (version === "105" || version === "105a" ? 1 : 0);
}

/**
 * 105-series mirror of _checkValues(): every row must be exactly len(Fields)+1
 * cells (reserved record_uuid column) and every data cell must match its field
 * type. Reports up to MAX_SHAPE_ERRORS findings (104 stops at the first).
 */
export function check105Values(doc: BEJSONDocument): { code: number; message: string }[] {
  const errors: { code: number; message: string }[] = [];
  if (!Array.isArray(doc.Values)) {
    errors.push({ code: E.INVALID_VALUES_STRUCTURE, message: "Values must be an array." });
    return errors;
  }
  const version = doc.Format_Version as string;
  const expectedLen = doc.Fields.length + 1;
  for (let i = 0; i < doc.Values.length; i++) {
    if (errors.length >= MAX_SHAPE_ERRORS) {
      errors.push({ code: E.RECORD_LENGTH_MISMATCH, message: "[E_RECORD_LENGTH_MISMATCH] further row/type findings suppressed after " + MAX_SHAPE_ERRORS });
      break;
    }
    const row = doc.Values[i] as unknown;
    if (!Array.isArray(row) || row.length !== expectedLen) {
      const actual = Array.isArray(row) ? String(row.length) : typeof row;
      errors.push({
        code: E.RECORD_LENGTH_MISMATCH,
        message: "[E_RECORD_LENGTH_MISMATCH] Length mismatch at row " + i + ": expected " + expectedLen +
          " cells (record_uuid + " + (expectedLen - 1) + " fields), got " + actual,
      });
      continue;
    }
    for (let j = 0; j < doc.Fields.length; j++) {
      const col = rowColumn(version, j);
      const problem = valueTypeProblem(row[col], doc.Fields[j].type);
      if (problem) {
        errors.push({
          code: E.VALUE_TYPE_MISMATCH,
          message: "[E_TYPE_MISMATCH] Type mismatch at row " + i + ", col " + col + " (" + doc.Fields[j].name + "): " + problem,
        });
      }
    }
  }
  return errors;
}

const UUID_V4_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

/** Advisory only (returned as warnings, never errors): field_uuid / record_uuid that are not canonical lowercase UUIDv4. */
export function check105UuidFormat(doc: BEJSONDocument): string[] {
  const warnings: string[] = [];
  for (const f of doc.Fields) {
    const u = f && (f as BEJSONField).field_uuid;
    if (typeof u === "string" && u && !UUID_V4_RE.test(u)) {
      warnings.push("field_uuid " + JSON.stringify(u) + " on field " + JSON.stringify(f.name) + " is not a UUIDv4");
    }
  }
  const uuidCol = doc.Format_Version === "105db" ? 1 : 0;
  (Array.isArray(doc.Values) ? doc.Values : []).forEach((row, i) => {
    if (Array.isArray(row) && row.length > uuidCol) {
      const u = row[uuidCol];
      if (typeof u === "string" && u && !UUID_V4_RE.test(u)) {
        warnings.push("record_uuid " + JSON.stringify(u) + " at row " + i + " is not a UUIDv4");
      }
    }
  });
  return warnings;
}

/** 105-series mirrors of the 104/104a/104db version rules (Records_Type count, custom headers, 105a primitives, 105db RTP rules). */
function _check105Specific(doc: BEJSONDocument, r: ValidationResult): void {
  const v = doc.Format_Version as string;
  const count = doc.Records_Type.length;
  if (v === "105" || v === "105a") {
    if (count !== 1) _err(r, E.INVALID_RECORDS_TYPE, "BEJSON " + v + " must have exactly 1 record type. Found " + count + ".", "Records_Type");
  } else if (count < 2) {
    _err(r, E.INVALID_RECORDS_TYPE, v + " requires 2+ types", "Records_Type");
  }

  if (v === "105" || v === "105db") {
    for (const key of Object.keys(doc)) {
      if (FORBIDDEN_CUSTOM_KEYS_104.has(key as typeof MANDATORY_KEYS[number]) || key === "Parent_Hierarchy" || key.startsWith("_")) continue;
      _err(r, E.FORBIDDEN_CUSTOM_KEY, "Custom key \"" + key + "\" forbidden in " + v, key);
    }
  }

  if (v === "105a") {
    for (const field of doc.Fields) {
      if (field.type === "array" || field.type === "object") {
        _err(r, E.INVALID_FIELDS, "105a forbids complex type: " + field.type, field.name);
      }
    }
  }

  if (v === "105db") {
    if (doc.Fields.length === 0 || doc.Fields[0].name !== "Record_Type_Parent") {
      _err(r, E.INVALID_RECORD_TYPE_PARENT, "105db first field must be 'Record_Type_Parent'", "Fields");
      return;
    }
    for (let i = 1; i < doc.Fields.length; i++) {
      const f = doc.Fields[i];
      if (!("Record_Type_Parent" in f)) {
        _err(r, E.INVALID_RECORD_TYPE_PARENT, "Field '" + f.name + "' missing Record_Type_Parent in 105db", f.name);
      }
    }
    const valid = new Set(doc.Records_Type);
    (Array.isArray(doc.Values) ? doc.Values : []).forEach((row, i) => {
      if (!Array.isArray(row) || row.length === 0) return;
      if (!valid.has(row[0] as string)) {
        _err(r, E.INVALID_RECORD_TYPE_PARENT, "Invalid Record_Type_Parent '" + row[0] + "' at row " + i, "Record_Type_Parent", i);
      }
    });
  }
}

function _check105StrictIntegrity(doc: BEJSONDocument): { code: number; message: string }[] {
  return check105StrictIntegrity(doc);
}

// ---------------------------------------------------------------------------
// Step 6a — 104-specific rules
// ---------------------------------------------------------------------------

const FORBIDDEN_CUSTOM_KEYS_104 = new Set(MANDATORY_KEYS);

function _check104Specific(doc: BEJSONDocument, r: ValidationResult): void {
  // Single record type
  if (doc.Records_Type.length !== 1) {
    _err(r, E.VERSION_CONSTRAINT, "BEJSON 104 requires exactly one Records_Type entry.", "Records_Type");
  }

  // No custom top-level keys (Parent_Hierarchy is the only exception)
  for (const key of Object.keys(doc)) {
    if (!FORBIDDEN_CUSTOM_KEYS_104.has(key as typeof MANDATORY_KEYS[number]) && key !== "Parent_Hierarchy" && !key.startsWith("_")) {
      _err(r, E.FORBIDDEN_CUSTOM_KEY, "BEJSON 104 forbids custom top-level key: \"" + key + "\".", key);
    }
  }

  // Parent_Hierarchy, if present, must be a string
  if ("Parent_Hierarchy" in doc && typeof doc.Parent_Hierarchy !== "string") {
    _err(r, E.VERSION_CONSTRAINT, "Parent_Hierarchy must be a string when present.", "Parent_Hierarchy");
  }
}

// ---------------------------------------------------------------------------
// Step 6b — 104a-specific rules
// ---------------------------------------------------------------------------

const PRIMITIVE_TYPES: BEJSONPrimitiveType[] = ["string", "integer", "number", "boolean"];
const PASCAL_CASE_RE = /^[A-Z][A-Za-z0-9]*(_[A-Za-z0-9]+)*$/;

function _check104aSpecific(doc: BEJSONDocument, r: ValidationResult): void {
  // Single record type
  if (doc.Records_Type.length !== 1) {
    _err(r, E.VERSION_CONSTRAINT, "BEJSON 104a requires exactly one Records_Type entry.", "Records_Type");
  }

  // Fields must be primitive-only
  for (let i = 0; i < doc.Fields.length; i++) {
    const field = doc.Fields[i];
    if (!PRIMITIVE_TYPES.includes(field.type as BEJSONPrimitiveType)) {
      _err(r, E.VERSION_CONSTRAINT,
        "BEJSON 104a: Fields[" + i + "].type \"" + field.type + "\" is not a primitive type.", field.name);
    }
  }

  // Custom keys: must be PascalCase, must not collide with mandatory keys
  for (const key of Object.keys(doc)) {
    if (FORBIDDEN_CUSTOM_KEYS_104.has(key as typeof MANDATORY_KEYS[number])) continue;
    if (key.startsWith("_")) continue; // checked by _checkFieldMapCache / _checkReservedKeys
    if (key === "Parent_Hierarchy") {
      // Parent_Hierarchy is not defined for 104a but not strictly forbidden;
      // emit a warning rather than an error since the spec is silent here.
      continue;
    }
    if (!PASCAL_CASE_RE.test(key)) {
      _err(r, E.INVALID_CUSTOM_KEY,
        "BEJSON 104a: custom header \"" + key + "\" must be PascalCase.", key);
    }
  }
}

// ---------------------------------------------------------------------------
// Step 6c — 104db-specific rules
// ---------------------------------------------------------------------------

function _check104dbSpecific(doc: BEJSONDocument, r: ValidationResult): void {
  // Two or more record types
  if (doc.Records_Type.length < 2) {
    _err(r, E.VERSION_CONSTRAINT, "BEJSON 104db requires at least two Records_Type entries.", "Records_Type");
  }

  // No custom top-level keys (not even Parent_Hierarchy)
  for (const key of Object.keys(doc)) {
    if (!FORBIDDEN_CUSTOM_KEYS_104.has(key as typeof MANDATORY_KEYS[number]) && !key.startsWith("_")) {
      _err(r, E.FORBIDDEN_CUSTOM_KEY, "BEJSON 104db forbids custom top-level key: \"" + key + "\".", key);
    }
  }

  // First field must be Record_Type_Parent: string
  if (doc.Fields.length === 0 || doc.Fields[0].name !== "Record_Type_Parent") {
    _err(r, E.MISSING_DISCRIMINATOR, "BEJSON 104db: first field must be named \"Record_Type_Parent\".", "Fields");
    return; // can't continue safely
  }
  if (doc.Fields[0].type !== "string") {
    _err(r, E.MISSING_DISCRIMINATOR, "BEJSON 104db: Record_Type_Parent field type must be \"string\".", "Record_Type_Parent");
  }

  // Every field except Record_Type_Parent must have Record_Type_Parent property
  const validEntities = new Set(doc.Records_Type);
  for (let i = 1; i < doc.Fields.length; i++) {
    const field = doc.Fields[i];
    if (!field.Record_Type_Parent) {
      _err(r, E.MISSING_DISCRIMINATOR,
        "BEJSON 104db: Fields[" + i + "] (\"" + field.name + "\") is missing Record_Type_Parent assignment.", field.name);
    } else if (!validEntities.has(field.Record_Type_Parent)) {
      _err(r, E.VERSION_CONSTRAINT,
        "BEJSON 104db: Fields[" + i + "].Record_Type_Parent \"" + field.Record_Type_Parent + "\" is not in Records_Type.", field.name);
    }
  }

  // Every record's discriminator must match a declared entity
  if (Array.isArray(doc.Values)) {
    for (let i = 0; i < doc.Values.length; i++) {
      const row = doc.Values[i];
      if (!Array.isArray(row) || row.length === 0) continue;
      const discriminator = row[0];
      if (typeof discriminator !== "string" || !validEntities.has(discriminator)) {
        _err(r, E.VERSION_CONSTRAINT,
          "Values[" + i + "][0] discriminator \"" + discriminator + "\" not in Records_Type.", "Record_Type_Parent", i);
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Type matching helper
// ---------------------------------------------------------------------------

function _typeMatches(val: unknown, type: BEJSONFieldType): boolean {
  if (val === null) return true;
  switch (type) {
    case "string":
      return typeof val === "string";
    case "integer":
      return typeof val === "number" && Number.isInteger(val);
    case "number":
      return typeof val === "number";
    case "boolean":
      return typeof val === "boolean";
    case "array":
      return Array.isArray(val);
    case "object":
      return typeof val === "object" && !Array.isArray(val) && val !== null;
    default:
      return false;
  }
}

// ---------------------------------------------------------------------------
// Result helpers
// ---------------------------------------------------------------------------

function _makeResult(): ValidationResult {
  return { valid: true, errors: [], warnings: [] };
}

function _err(
  r: ValidationResult,
  code: number,
  message: string,
  field?: string,
  recordIndex?: number
): void {
  r.valid = false;
  const e: ValidationError = { code, message };
  if (field !== undefined) e.field = field;
  if (recordIndex !== undefined) e.recordIndex = recordIndex;
  r.errors.push(e);
}

function _warn(
  r: ValidationResult,
  code: number,
  message: string,
  field?: string,
  recordIndex?: number
): void {
  const w: ValidationWarning = { code, message };
  if (field !== undefined) w.field = field;
  if (recordIndex !== undefined) w.recordIndex = recordIndex;
  r.warnings.push(w);
}

// Export _warn so mfdb_validators can reuse the pattern
export { _warn as _emitWarning, _err as _emitError, _makeResult };
