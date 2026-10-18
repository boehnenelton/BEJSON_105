/**
 * Library:         lib_bejson_Core_bejson_core_nesting.ts
 * Family:          Core
 * Module Purpose:  Nested-104 detection, validation, field-map cache and safe mutation (append-only schema, null-padding).
 * Architecture:    Nested BEJSON 104: a cell of a parent 104 document holds a complete embedded 104 document; the physical cell coordinate (NestAddress) is the implicit foreign key. It is neither 104db nor MFDB.
 * Format_Scope:    Nested 104 (NOT 104db, NOT MFDB)
 * Glossary:        BEJSON 104, 104a and 104db are the three file formats (Format_Version). 104db = ONE file holding 2+ entity types
 *                  (Record_Type_Parent discriminator, null-padding). MFDB is NOT a format and NOT 104db: it is a layer made of one 104a manifest
 *                  (104a.mfdb.bejson) plus dense 104 entity files linked by Parent_Hierarchy. MFDB-132 = an MFDB packed into one Chunked-104a document.
 * Version:         0.6.0
 * Release_Version: 300
 * Date:            2026-10-16
 * Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * Format_Creator:  Elton Boehnen
 * RELATIONAL_ID:   b983a234-6bea-47ca-84a1-889b94d4695c
 * Changelog:
 *   0.6.0 (2026-10-16) - Merged lib_bejson_Core_bejson_nesting_query into this module (bejsonNestingQuery, bejsonNestingGetPath, bejsonNestingQuerySummary, QueryMatch, NESTING_QUERY_ERRORS); query module removed, no alias.
 *           Nested-cell validation now delegates to Core validate104; field maps use Core bejson_core_get_field_map (key _bejson_field_map replaces _nestingFieldMap). Local _buildFieldMap removed.
 *           Fixed: the no-RELATIONAL_ID fingerprint hashed only Fields, so two different documents with the same schema shared NestMap cache entries (stale scan results) and same-schema nesting looked circular; it now hashes Fields + Values.
 *   0.5.1 (2026-10-16) - Error codes now imported from lib_bejson_Core_bejson_types (nesting errors file removed).
 *           No code, API, error-code (130-139) or output change.
 *   0.5.0 (2026-10-14) - Moved from the Core_Nesting family into Core (was lib_bejson_CoreNesting_bejson_core_nesting.ts, 0.4.5). Renamed to lib_bejson_Core_bejson_core_nesting.ts;
 *           same-directory imports updated. No code, API, error-code (130-139) or output change.
 */

// ===========================================================================
// ERROR CODES — sourced from the Core error registry (lib_bejson_Core_bejson_types)
// ===========================================================================
import { CORE_NESTING_ERRORS } from "./lib_bejson_Core_bejson_types";
import type { BEJSONDocument } from "./lib_bejson_Core_bejson_types";
// Core field-map cache and Core validator: the single sources of those rules (no private copies here).
import { bejson_core_get_field_map } from "./lib_bejson_Core_bejson_field_map";
import { validate104 } from "./lib_bejson_Core_bejson_validators";
export const NESTING_ERRORS = CORE_NESTING_ERRORS;

export type NestingErrorCode = typeof NESTING_ERRORS[keyof typeof NESTING_ERRORS];

export const VERSION           = "0.6.0";
export const NESTING_MAX_DEPTH = 16;
const _VALID_VERSION           = "104";

// ===========================================================================
// TYPES
// ===========================================================================

export interface BejsonField {
  name: string;
  type: "string" | "integer" | "number" | "boolean" | "array" | "object";
  Record_Type_Parent?: string;
}

/** Minimal surface of a BEJSON 104 doc used by this library. */
export interface BejsonDoc104 {
  Format:         string;
  Format_Version: string;
  Format_Creator: string;
  Records_Type:   string[];
  Fields:         BejsonField[];
  Values:         unknown[][];
  RELATIONAL_ID?: string;
  relational_id?: string;
  /** Internal: Core field-map cache (bejson_core_get_field_map) — stripped before write-back. */
  _bejson_field_map?: Record<string, number>;
  [key: string]: unknown;
}

/**
 * Canonical 4-part memory address in the NestMap.
 * Same content at two different (parentFingerprint, row, col, depth) = two different addresses.
 * No content-based deduplication.
 */
export interface NestAddress {
  parentFingerprint: string;
  row:      number;
  col:      number;
  depth:    number;
}

/** One cell containing a detected and parsed nested BEJSON 104 doc. */
export interface NestedCell {
  row:       number;
  col:       number;
  fieldName: string;
  depth:     number;
  doc:       BejsonDoc104;   // live reference — mutations write back to parent
  isValid:   boolean;
  errors:    string[];
  warnings:  string[];       // standardization notices
  children:  NestedCell[];
}

export interface NestingResult {
  scannedCells:  number;
  nestedFound:   number;
  nestedValid:   number;
  nestedInvalid: number;
  maxDepthSeen:  number;
  schemaErrors:  number;     // column uniformity violations
  cells:         NestedCell[];
  errors:        string[];
  warnings:      string[];
}

interface ValidationResult104 {
  isValid: boolean;
  errors:  string[];
}

// ===========================================================================
// NEST MAP CACHE
// Key: "<parentFingerprint>:<row>:<col>:<depth>"  →  NestedCell
// ===========================================================================
const _NEST_MAP = new Map<string, NestedCell>();
// Column schema contracts per parent doc: "<parentFingerprint>:col:<col>"  →  Fields JSON
const _COL_SCHEMAS = new Map<string, string>();

/**
 * Builds the NestMap cache key 'fingerprint:row:col:depth' for a NestAddress.
 */
function _addrKey(parentFingerprint: string, row: number, col: number, depth: number): string {
  return `${parentFingerprint}:${row}:${col}:${depth}`;
}

/**
 * Returns the cached NestedCell for (parentFingerprint, row, col, depth), or undefined.
 */
export function bejsonNestingCacheGet(
  parentFingerprint: string, row: number, col: number, depth: number
): NestedCell | null {
  return _NEST_MAP.get(_addrKey(parentFingerprint, row, col, depth)) ?? null;
}

/**
 * Stores a NestedCell under its NestAddress.
 */
export function bejsonNestingCachePut(
  parentFingerprint: string, row: number, col: number, depth: number, cell: NestedCell
): void {
  _NEST_MAP.set(_addrKey(parentFingerprint, row, col, depth), cell);
}

/**
 * Clears all NestMap entries, or only those of one parent fingerprint. Returns the number removed.
 */
export function bejsonNestingCacheClear(parentFingerprint?: string): number {
  if (parentFingerprint === undefined) {
    const totalCount = _NEST_MAP.size;
    _NEST_MAP.clear();
    _COL_SCHEMAS.clear();
    return totalCount;
  }
  const keyPrefix = `${parentFingerprint}:`;
  let removedCount = 0;
  for (const cacheKey of _NEST_MAP.keys()) {
    if (cacheKey.startsWith(keyPrefix)) { _NEST_MAP.delete(cacheKey); removedCount++; }
  }
  for (const schemaKey of _COL_SCHEMAS.keys()) {
    if (schemaKey.startsWith(keyPrefix)) _COL_SCHEMAS.delete(schemaKey);
  }
  return removedCount;
}

/**
 * Diagnostic snapshot: total entries, unique parents, depth spread.
 */
export function bejsonNestingCacheStats(): {
  total_entries: number; unique_parents: number; depth_spread: number[];
} {
  const fingerprintSet = new Set<string>();
  const depthSet = new Set<number>();
  for (const cacheKey of _NEST_MAP.keys()) {
    const keyParts = cacheKey.split(":");
    fingerprintSet.add(keyParts[0]);
    depthSet.add(Number(keyParts[keyParts.length - 1]));
  }
  return {
    total_entries:  _NEST_MAP.size,
    unique_parents: fingerprintSet.size,
    depth_spread:   [...depthSet].sort((a, b) => a - b),
  };
}

/**
 * All cached NestedCells for one parent document and column.
 */
/** Return all cached NestedCells for a given parent doc + column index. */
export function bejsonNestingCacheLookupCol(parentFingerprint: string, col: number): NestedCell[] {
  const matchingCells: NestedCell[] = [];
  for (const [cacheKey, cachedCell] of _NEST_MAP.entries()) {
    const keyParts = cacheKey.split(":");
    if (keyParts[0] === parentFingerprint && Number(keyParts[2]) === col) matchingCells.push(cachedCell);
  }
  return matchingCells;
}

// ===========================================================================
// INTERNAL HELPERS
// ===========================================================================

/**
 * Stable identity of a parent document: RELATIONAL_ID if present, else a hash of its Fields.
 */
function _docFingerprint(doc: BejsonDoc104): string {
  const relationalIdValue = doc["RELATIONAL_ID"] ?? doc["relational_id"];
  if (relationalIdValue) return String(relationalIdValue);
  // Content hash (Fields + Values): FNV-1a and djb2 32-bit hashes plus length, so same-schema documents never share a cache entry.
  const contentRepr = JSON.stringify([doc.Fields ?? [], doc.Values ?? []]);
  let fnvHash = 0x811c9dc5, djbHash = 5381;
  for (let charIndex = 0; charIndex < contentRepr.length; charIndex++) {
    const charCode = contentRepr.charCodeAt(charIndex);
    fnvHash = Math.imul(fnvHash ^ charCode, 0x01000193) >>> 0;
    djbHash = (Math.imul(djbHash, 33) + charCode) >>> 0;
  }
  return `hash:${fnvHash.toString(16)}${djbHash.toString(16)}${contentRepr.length.toString(16)}`;
}

/**
 * Fast pre-filter: a string cell whose trimmed text starts with { and ends with }.
 */
function _isCandidate(value: unknown): value is string {
  if (typeof value !== "string") return false;
  const trimmedValue = value.trim();
  return trimmedValue.startsWith("{") && trimmedValue.endsWith("}");
}

/**
 * JSON.parse of a candidate cell; returns the object or null.
 */
function _parseCell(rawCellText: string): BejsonDoc104 | null {
  try {
    const parsedValue: unknown = JSON.parse(rawCellText);
    if (typeof parsedValue === "object" && parsedValue !== null && !Array.isArray(parsedValue)) return parsedValue as BejsonDoc104;
  } catch { /* ignore */ }
  return null;
}

/**
 * Canonical string form of a Fields array (fingerprints, caches).
 */
function _fieldsSignature(doc: BejsonDoc104): string {
  return JSON.stringify(doc.Fields ?? []);
}

/**
 * Strict check that an embedded document is BEJSON 104 (nested cells must be 104 -- not 104a, not 104db, not an MFDB manifest).
 */
function _quickValidate104(doc: unknown): ValidationResult104 {
  const E = NESTING_ERRORS;
  if (typeof doc !== "object" || doc === null || Array.isArray(doc))
    return { isValid: false, errors: [`E${E.E_NESTING_NOT_BEJSON}: not an object`] };

  const docRecord = doc as Record<string, unknown>;
  const mandatoryKeys = ["Format","Format_Version","Format_Creator","Records_Type","Fields","Values"];
  for (const mandatoryKey of mandatoryKeys) if (!(mandatoryKey in docRecord)) return { isValid: false, errors: [] };
  if (docRecord["Format"] !== "BEJSON")               return { isValid: false, errors: [] };
  if (docRecord["Format_Version"] !== _VALID_VERSION) return { isValid: false, errors: [] };

  // It IS a BEJSON 104 doc: Core's validator is the single source of the rules.
  const coreResult = validate104(doc);
  const validationErrors = coreResult.errors.map(coreError => `E${E.E_NESTING_VALIDATION_FAILED}: ${coreError.message}`);
  return { isValid: validationErrors.length === 0, errors: validationErrors };
}

/**
 * Convention check relating the nested Records_Type name to the parent field name; returns a warning string or null.
 */
function _checkRecordsTypeConvention(doc: BejsonDoc104, parentFieldName: string): string | null {
  const recordsTypeValue = doc.Records_Type?.[0];
  if (!recordsTypeValue) return null;
  const expectedRecordsType = parentFieldName ? parentFieldName[0].toUpperCase() + parentFieldName.slice(1) : "";
  return recordsTypeValue !== expectedRecordsType
    ? `W: Records_Type '${recordsTypeValue}' should be '${expectedRecordsType}' by convention`
    : null;
}

// ===========================================================================
// CORE WALK
// ===========================================================================

/**
 * Recursive scan of one cell: records a NestedCell for an embedded 104 document and descends into its cells, up to depth 16, tracking fingerprints to stop cycles.
 */
function _walkCell(
  value:               unknown,
  row:                 number,
  col:                 number,
  fieldName:           string,
  depth:               number,
  seenFingerprints:    ReadonlySet<string>,
  parentFingerprint:   string,
  parentDoc:           BejsonDoc104,
  colSchemas:          Map<number, string>,   // col → Fields signature (per nesting level)
): NestedCell | null {
  const E = NESTING_ERRORS;

  if (depth > NESTING_MAX_DEPTH) {
    console.warn(`[NESTING] depth cap ${NESTING_MAX_DEPTH} at row=${row} col=${col}`);
    return null;
  }
  if (!_isCandidate(value)) return null;

  const cachedCell = bejsonNestingCacheGet(parentFingerprint, row, col, depth);
  if (cachedCell !== null) return cachedCell;

  const parsedDoc = _parseCell(value);
  if (parsedDoc === null) return null;

  const { isValid: rawIsValid, errors: cellErrors } = _quickValidate104(parsedDoc);
  if (!rawIsValid && cellErrors.length === 0) return null;  // not 104 — skip silently

  const cellWarnings: string[] = [];
  let isValid = rawIsValid;

  if (isValid) {
    const fieldsSignature = _fieldsSignature(parsedDoc);
    if (!colSchemas.has(col)) {
      colSchemas.set(col, fieldsSignature);
    } else if (colSchemas.get(col) !== fieldsSignature) {
      cellErrors.push(
        `E${E.E_NESTING_SCHEMA_MISMATCH}: nested doc at row=${row} col=${col} ` +
        `has different Fields schema than other docs in this column`
      );
      isValid = false;
    }
  }

  // Eager field map injection — O(1) for all subsequent consumers (R2)
  if (isValid) bejson_core_get_field_map(parsedDoc as unknown as BEJSONDocument);  // Core field-map cache (stored as _bejson_field_map)

  if (isValid) {
    const conventionWarning = _checkRecordsTypeConvention(parsedDoc, fieldName);
    if (conventionWarning) cellWarnings.push(conventionWarning);
  }

  const nestedFingerprint = _docFingerprint(parsedDoc);

  if (seenFingerprints.has(nestedFingerprint)) {
    const circularCell: NestedCell = {
      row, col, fieldName, depth, doc: parsedDoc, isValid: false,
      errors: [`E${E.E_NESTING_CIRCULAR_REF}: circular reference at depth ${depth}`],
      warnings: cellWarnings, children: [],
    };
    bejsonNestingCachePut(parentFingerprint, row, col, depth, circularCell);
    return circularCell;
  }

  const childCells: NestedCell[] = [];

  if (isValid) {
    const childSeenFingerprints: ReadonlySet<string> = new Set([...seenFingerprints, nestedFingerprint]);
    const childColSchemas: Map<number, string> = new Map();
    // Pre-built inverted field map: idx → name (O(1) vs fields[c]?.name per cell)
    const childFieldMap = bejson_core_get_field_map(parsedDoc as unknown as BEJSONDocument);
    const childFieldNameByIndex: Record<number, string> = Object.fromEntries(
      Object.entries(childFieldMap).map(([fieldNameKey, indexValue]) => [indexValue, fieldNameKey])
    );
    const childValues = parsedDoc.Values ?? [];
    for (let childRowIndex = 0; childRowIndex < childValues.length; childRowIndex++) {
      const childRowArray = childValues[childRowIndex];
      if (!Array.isArray(childRowArray)) continue;
      for (let childColIndex = 0; childColIndex < childRowArray.length; childColIndex++) {
        const childFieldName = childFieldNameByIndex[childColIndex] ?? `col_${childColIndex}`;
        const childCell = _walkCell(
          childRowArray[childColIndex], childRowIndex, childColIndex, childFieldName, depth + 1,
          childSeenFingerprints, nestedFingerprint, parsedDoc, childColSchemas
        );
        if (childCell !== null) childCells.push(childCell);
      }
    }
  }

  const resolvedCell: NestedCell = { row, col, fieldName, depth, doc: parsedDoc, isValid, errors: cellErrors, warnings: cellWarnings, children: childCells };
  bejsonNestingCachePut(parentFingerprint, row, col, depth, resolvedCell);
  return resolvedCell;
}

// ===========================================================================
// PUBLIC API
// ===========================================================================

/**
 * Entry point; call AFTER normal 104 validation of the parent. Finds all embedded 104 documents and returns a NestingResult. Nested BEJSON is 104-inside-104 through a cell; it is not 104db and not MFDB.
 */
/**
 * Entry point. Call AFTER normal Core 104 validation passes.
 * Walks doc.Values for embedded BEJSON 104 docs.
 */
export function bejsonNestingScan(doc: BejsonDoc104, useCache = true): NestingResult {
  const E = NESTING_ERRORS;
  const result: NestingResult = {
    scannedCells: 0, nestedFound: 0, nestedValid: 0,
    nestedInvalid: 0, maxDepthSeen: 0, schemaErrors: 0,
    cells: [], errors: [], warnings: [],
  };

  if (typeof doc !== "object" || doc === null) {
    result.errors.push(`E${E.E_NESTING_NOT_BEJSON}: doc must be an object`);
    return result;
  }

  const fieldsList = doc.Fields ?? [];
  const valuesList = doc.Values ?? [];
  if (!Array.isArray(fieldsList) || !Array.isArray(valuesList)) {
    result.errors.push(`E${E.E_NESTING_VALIDATION_FAILED}: Fields/Values malformed`);
    return result;
  }

  const documentFingerprint = _docFingerprint(doc);
  const rootSeenFingerprints: ReadonlySet<string> = new Set([documentFingerprint]);
  const colSchemas: Map<number, string> = new Map();

  for (let rowIndex = 0; rowIndex < valuesList.length; rowIndex++) {
    const row = valuesList[rowIndex];
    if (!Array.isArray(row)) continue;
    for (let colIndex = 0; colIndex < row.length; colIndex++) {
      result.scannedCells++;
      const cellValue = row[colIndex];
      if (!_isCandidate(cellValue)) continue;

      const resolvedFieldName = fieldsList[colIndex]?.name ?? `col_${colIndex}`;

      if (useCache) {
        const cachedHit = bejsonNestingCacheGet(documentFingerprint, rowIndex, colIndex, 1);
        if (cachedHit !== null) {
          result.nestedFound++;
          cachedHit.isValid ? result.nestedValid++ : result.nestedInvalid++;
          result.maxDepthSeen = Math.max(result.maxDepthSeen, cachedHit.depth);
          result.schemaErrors += cachedHit.errors.filter(errorMessage => errorMessage.includes(`E${E.E_NESTING_SCHEMA_MISMATCH}`)).length;
          result.cells.push(cachedHit);
          continue;
        }
      }

      const nestedCell = _walkCell(cellValue, rowIndex, colIndex, resolvedFieldName, 1, rootSeenFingerprints, documentFingerprint, doc, colSchemas);
      if (nestedCell === null) continue;

      result.nestedFound++;
      nestedCell.isValid ? result.nestedValid++ : result.nestedInvalid++;
      result.maxDepthSeen = Math.max(result.maxDepthSeen, nestedCell.depth);
      result.schemaErrors += nestedCell.errors.filter(errorMessage => errorMessage.includes(`E${E.E_NESTING_SCHEMA_MISMATCH}`)).length;
      for (const warningMessage of nestedCell.warnings) result.warnings.push(warningMessage);
      result.cells.push(nestedCell);
    }
  }
  return result;
}

/**
 * Applies mutationFn to a nested document and writes the re-serialized document back into the parent cell. The nested schema is append-only.
 */
/**
 * Apply mutationFn to nestedCell.doc in-place, write back into parentDoc.Values[row][col].
 * Field additions are safe (null-padding applied). Removals and reorders throw.
 */
export function bejsonNestingMutate(
  parentDoc:  BejsonDoc104,
  nestedCell: NestedCell,
  mutationFn: (doc: BejsonDoc104) => void,
): void {
  const E = NESTING_ERRORS;
  const { row, col } = nestedCell;
  const parentValues = parentDoc.Values ?? [];

  if (row >= parentValues.length || col >= ((parentValues[row] as unknown[]) ?? []).length)
    throw new Error(`E${E.E_NESTING_INVALID_CELL}: address row=${row} col=${col} out of bounds`);

  const doc = nestedCell.doc;
  const fieldsBefore = (doc.Fields ?? []).map(fieldDef => ({ ...fieldDef }));
  const fieldsCountBefore = fieldsBefore.length;

  mutationFn(doc);

  const fieldsAfter = doc.Fields ?? [];
  const fieldsCountAfter = fieldsAfter.length;

  if (fieldsCountAfter < fieldsCountBefore)
    throw new Error(`E${E.E_NESTING_SCHEMA_MISMATCH}: mutation removed fields — not permitted`);

  for (let fieldIndex = 0; fieldIndex < fieldsCountBefore; fieldIndex++) {
    if (fieldsBefore[fieldIndex].name !== fieldsAfter[fieldIndex]?.name || fieldsBefore[fieldIndex].type !== fieldsAfter[fieldIndex]?.type)
      throw new Error(
        `E${E.E_NESTING_SCHEMA_MISMATCH}: mutation reordered/retyped field at index ${fieldIndex} — not permitted`
      );
  }

  if (fieldsCountAfter > fieldsCountBefore) {
    const fieldsAddedCount = fieldsCountAfter - fieldsCountBefore;
    for (const valueRow of (doc.Values ?? [])) {
      if (Array.isArray(valueRow)) for (let padIndex = 0; padIndex < fieldsAddedCount; padIndex++) (valueRow as unknown[]).push(null);
    }
  }

  delete doc._bejson_field_map;
  (parentDoc.Values[row] as unknown[])[col] = JSON.stringify(doc);
}

/**
 * Field-name -> column map for a NestedCell's embedded document.
 */
/** Field-name→col-index map via the Core field-map cache (freshness-guarded; stored on doc._bejson_field_map). */
export function bejsonNestingGetFieldMap(nestedCell: NestedCell): Record<string, number> {
  return { ...bejson_core_get_field_map(nestedCell.doc as unknown as BEJSONDocument) };
}

/**
 * Depth-first flat list of every NestedCell in a NestingResult.
 */
/** Depth-first flat list of every NestedCell in the result tree. */
export function bejsonNestingFlatten(result: NestingResult): NestedCell[] {
  const flattenedCells: NestedCell[] = [];
  /**
   * Inner helper of flatten: pushes cells and recurses into children.
   */
  function collect(cells: NestedCell[]): void {
    for (const cellItem of cells) { flattenedCells.push(cellItem); collect(cellItem.children); }
  }
  collect(result.cells);
  return flattenedCells;
}

/**
 * All NestedCells found in one parent column.
 */
/** Return all top-level NestedCells for a specific column index. */
export function bejsonNestingGetColumn(result: NestingResult, col: number): NestedCell[] {
  return result.cells.filter(cellItem => cellItem.col === col);
}

/**
 * Human-readable summary string of a NestingResult.
 */
/** Human-readable summary of a NestingResult. */
export function bejsonNestingSummary(result: NestingResult): string {
  const summaryLines: string[] = [
    "BEJSON Core_Nesting Scan Summary",
    `  Cells scanned    : ${result.scannedCells}`,
    `  Nested found     : ${result.nestedFound}`,
    `  Valid nested     : ${result.nestedValid}`,
    `  Invalid nested   : ${result.nestedInvalid}`,
    `  Max depth seen   : ${result.maxDepthSeen}`,
    `  Schema errors    : ${result.schemaErrors}`,
  ];
  if (result.errors.length)   { summaryLines.push("  Scan errors:");  result.errors.forEach(errorMessage => summaryLines.push(`    - ${errorMessage}`)); }
  if (result.warnings.length) { summaryLines.push("  Warnings:");     result.warnings.forEach(warningMessage => summaryLines.push(`    ~ ${warningMessage}`)); }
  for (const cellItem of bejsonNestingFlatten(result)) {
    const statusLabel = cellItem.isValid ? "VALID" : "INVALID";
    const indent = "  " + "  ".repeat(cellItem.depth - 1);
    summaryLines.push(`${indent}[${statusLabel}] row=${cellItem.row} col=${cellItem.col} field='${cellItem.fieldName}' depth=${cellItem.depth}`);
    cellItem.errors.forEach(errorMessage   => summaryLines.push(`${indent}  ! ${errorMessage}`));
    cellItem.warnings.forEach(warningMessage => summaryLines.push(`${indent}  ~ ${warningMessage}`));
  }
  return summaryLines.join("\n");
}

// ===========================================================================
// DOTTED-PATH QUERIES (merged in from the former lib_bejson_Core_bejson_nesting_query module)
// e.g. player_inventory[*].item_id
// ===========================================================================
export const NESTING_QUERY_ERRORS = {
  E_NESTING_QUERY_INVALID_PATH: CORE_NESTING_ERRORS.E_NESTING_QUERY_INVALID_PATH,
  E_NESTING_QUERY_EMPTY_PATH:   CORE_NESTING_ERRORS.E_NESTING_QUERY_EMPTY_PATH,
} as const;

type Selector = "*" | number | null;

interface PathSegment {
  name: string;
  selector: Selector;
}

export interface QueryMatch {
  path: string;
  value: unknown;
  fieldChain: string[];
  rowChain: number[];
  colChain: number[];
}

const _SEGMENT_RE = /^([A-Za-z_][A-Za-z0-9_]*)(\[(\*|\d+)\])?$/;

/**
 * Parses a dotted path such as player_inventory[*].item_id into (fieldName, selector) steps.
 */
function _parsePath(path: string): PathSegment[] {
  if (!path || !path.trim()) {
    throw new Error(`E${NESTING_QUERY_ERRORS.E_NESTING_QUERY_EMPTY_PATH}: path is empty`);
  }
  return path.trim().split(".").map((rawSegment) => {
    const segmentMatch = _SEGMENT_RE.exec(rawSegment);
    if (!segmentMatch) {
      throw new Error(
        `E${NESTING_QUERY_ERRORS.E_NESTING_QUERY_INVALID_PATH}: bad segment '${rawSegment}' in path '${path}'`
      );
    }
    const [, segmentFieldName, , selectorText] = segmentMatch;
    let selector: Selector = null;
    if (selectorText === "*") selector = "*";
    else if (selectorText !== undefined) selector = parseInt(selectorText, 10);
    return { name: segmentFieldName, selector };
  });
}

/**
 * Recursive walk of a nested-104 document along parsed path steps, collecting matches.
 */
function _queryWalk(
  doc: BejsonDoc104,
  segments: PathSegment[],
  segmentIndex: number,
  fullPath: string,
  fieldChain: string[],
  rowChain: number[],
  colChain: number[],
  matchValue: unknown,
  results: QueryMatch[]
): void {
  if (typeof doc !== "object" || doc === null) return;

  const { name: fieldName, selector } = segments[segmentIndex];
  const fieldMap = bejson_core_get_field_map(doc as unknown as BEJSONDocument);
  if (!(fieldName in fieldMap)) return; // dead branch — not an error

  const col = fieldMap[fieldName];
  const values = Array.isArray(doc.Values) ? doc.Values : [];
  const isLastSegment = segmentIndex === segments.length - 1;

  const rowIndices: number[] =
    selector === null || selector === "*" ? values.map((_, indexValue) => indexValue) : [selector];

  for (const rowIndex of rowIndices) {
    if (rowIndex < 0 || rowIndex >= values.length) continue;
    const row = values[rowIndex];
    if (!Array.isArray(row) || col >= row.length) continue;
    const cellValue = row[col];

    if (isLastSegment) {
      if (matchValue === undefined || cellValue === matchValue) {
        results.push({
          path: fullPath,
          value: cellValue,
          fieldChain: [...fieldChain, fieldName],
          rowChain: [...rowChain, rowIndex],
          colChain: [...colChain, col],
        });
      }
      continue;
    }

    if (!_isCandidate(cellValue)) continue;
    const nestedDoc = _parseCell(cellValue as string);
    if (nestedDoc === null) continue;

    _queryWalk(
      nestedDoc, segments, segmentIndex + 1, fullPath,
      [...fieldChain, fieldName], [...rowChain, rowIndex], [...colChain, col],
      matchValue, results
    );
  }
}

/**
 * Finds values in a nested 104 document by dotted path (selectors [*], [n]; optional matchValue filter). Returns QueryMatch objects.
 */
/**
 * Resolve a dotted path through doc and its nested BEJSON 104 cells.
 * @throws {Error} On malformed path syntax only — never on missing data.
 */
export function bejsonNestingQuery(
  doc: BejsonDoc104, path: string, matchValue?: unknown
): QueryMatch[] {
  const parsedSegments = _parsePath(path); // throws on bad grammar
  const matchResults: QueryMatch[] = [];
  _queryWalk(doc, parsedSegments, 0, path, [], [], [], matchValue, matchResults);
  return matchResults;
}

/**
 * Safe-get: first value at a path, or defaultValue.
 */
/**
 * Safe-Get convenience wrapper (Section 9 standard): returns the value of
 * the FIRST match for path, or `defaultValue` if the path resolves to
 * nothing or is malformed. Never throws.
 */
export function bejsonNestingGetPath(
  doc: BejsonDoc104, path: string, defaultValue: unknown = null
): unknown {
  let matches: QueryMatch[];
  try {
    matches = bejsonNestingQuery(doc, path);
  } catch {
    return defaultValue;
  }
  return matches.length ? matches[0].value : defaultValue;
}

/**
 * Human-readable summary of query results.
 */
/** Human-readable summary of a query() result list. */
export function bejsonNestingQuerySummary(matches: QueryMatch[]): string {
  if (!matches || matches.length === 0) {
    return "BEJSON Core_Nesting Query Summary\n  0 matches";
  }
  const summaryLines = [`BEJSON Core_Nesting Query Summary — ${matches.length} match(es)`];
  for (const queryMatch of matches) {
    const chainText = queryMatch.fieldChain
      .map((chainFieldName, chainIndex) => `${chainFieldName}[row=${queryMatch.rowChain[chainIndex]},col=${queryMatch.colChain[chainIndex]}]`)
      .join(" -> ");
    summaryLines.push(`  ${chainText} = ${JSON.stringify(queryMatch.value)}`);
  }
  return summaryLines.join("\n");
}
