/**
 * Library:        lib_bejson_Core_bejson_types.ts
 * Family:         Core
 * Description:    Type definitions and interface contracts for TypeScript libraries. NOTE: Error codes are mirrored across SH, JS, PY, and TS registries. Reference canonical codes in lib_bejson_Core_bejson_errors.js / lib_bejson_Core_bejson_errors.sh.
 * Version:        2.9.0
 * Date:           2026-09-25
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  745360d6-76cf-43c1-b65b-78cb115f9bc5
 * Release_Version: 300
 *
 * Changelog:
 *   2.9.0 - REMOVED the Schema Constraints block (110-114: REQUIRED_FIELD_NULL,
 *           UNIQUE_CONSTRAINT_VIOLATION, ENUM_VALUE_INVALID, VALUE_OUT_OF_RANGE,
 *           LENGTH_OUT_OF_RANGE) from BEJSON_105_CODES, and the matching
 *           required/unique/enum/min/max/minLength/maxLength keys from the
 *           BEJSONField interface, per Be25. Field UUIDs + FK/cascade kept.
 *   2.8.0 - AUDIT FIX (C1, 5th claim-then-collide occurrence): renumbered
 *           BEJSON_105_CODES 90-94 -> 110-114 (REQUIRED_FIELD_NULL through
 *           LENGTH_OUT_OF_RANGE). 90-94 collided with MD's error range
 *           (E_MD_CHUNK_NOT_FOUND..E_MD_INDEX_STALE, 90-99). Consumers use
 *           the named E105.* constants, not raw numbers -- no call-site
 *           changes required beyond this file. See errors.bejson for the
 *           live cross-family map; check it before claiming a new range.
 *   2.7.0 - Renamed BEJSON_105_CODES.DUPLICATE_FIELD_NAME (84) to
 *           FIELD_NAME_ALREADY_EXISTS to stop shadowing
 *           BEJSON_VALIDATION_CODES.DUPLICATE_FIELD_NAME (6, unrelated
 *           104-era alias). Same file, two different meanings under one
 *           identifier -- number/registry name (E_DUPLICATE_FIELD_NAME)
 *           unchanged, only the local TS identifier changed.
 *   2.6.0 - Phase 6 TS port: added FK_TARGET_ENTITY_UNKNOWN (43),
 *           FK_RESTRICT_VIOLATION (44), FK_CASCADE_CYCLE (45),
 *           FK_ENTITY_STILL_REFERENCED (46), FK_INVALID_ON_DELETE (47) to
 *           MFDB_VALIDATION_CODES -- numerically mirrors Python exactly.
 *           Reused the pre-existing FK_UNRESOLVED (39) rather than
 *           duplicating it, same as Python did.
 *   2.5.0 - Phase 2.7 TS parity pass: BEJSONVersion widened to include
 *           105/105a/105db, BEJSONField widened with the Phase 2/6/8
 *           optional keys (field_uuid, required, unique, enum, min, max,
 *           minLength, maxLength, fk_target_entity, fk_on_delete), new
 *           BEJSON_105_CODES block (80-85, 90-94) mirroring the Python
 *           registry's numbers exactly. MFDB Referential Integrity (Phase
 *           6) codes 43-47 deliberately NOT added yet -- that's the
 *           mfdb_core.ts/mfdb_validators.ts port, a separate follow-up.
 *   2.4.0 - Removed CORE_NESTING_CODES block — that family now owns its
 *           codes in lib_bejson_CoreNesting_bejson_errors.ts.
 */

// ---------------------------------------------------------------------------
// Primitive and union types
// ---------------------------------------------------------------------------

export type BEJSONVersion = "104" | "104a" | "104db" | "105" | "105a" | "105db";

export type BEJSONFieldType =
  | "string"
  | "integer"
  | "number"
  | "boolean"
  | "array"
  | "object";

export type BEJSONPrimitiveType = "string" | "integer" | "number" | "boolean";

export type BEJSONValue =
  | string
  | number
  | boolean
  | null
  | unknown[]
  | Record<string, unknown>;

// ---------------------------------------------------------------------------
// Field and Document interfaces
// ---------------------------------------------------------------------------

export interface BEJSONField {
  name: string;
  type: BEJSONFieldType;

  Record_Type_Parent?: string;

  // Format 105 additions -- all optional, all opt-in. Absence of every key
  // below means a field behaves exactly as it did pre-105. field_uuid is
  // Phase 2 (105-series addressing); fk_target_entity/fk_on_delete are
  // Phase 6 (Referential Integrity FK declaration). The Phase 8 schema-
  // constraint keys (required/unique/enum/min/max/minLength/maxLength)
  // were removed 2026-09-25 per Be25 -- field UUIDs + FK/cascade are the
  // entire kept 105-series feature set.
  field_uuid?: string;
  fk_target_entity?: string;
  fk_on_delete?: "restrict" | "cascade" | "null";
}

export interface BEJSONDocument {
  Format: "BEJSON";
  Format_Version: BEJSONVersion;
  Format_Creator: "Elton Boehnen";
  Records_Type: string[];
  Fields: BEJSONField[];
  Values: BEJSONValue[][];
  
  Parent_Hierarchy?: string;
  [key: string]: unknown; // custom 104a headers + index access
}

// ---------------------------------------------------------------------------
// Validation result types
// ---------------------------------------------------------------------------

export interface ValidationError {
  code: number;
  message: string;
  field?: string;
  recordIndex?: number;
}

export interface ValidationWarning {
  code: number;
  message: string;
  field?: string;
  recordIndex?: number;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

// ---------------------------------------------------------------------------
// MFDB-specific interfaces
// ---------------------------------------------------------------------------

export interface MFDBManifestRecord {
  entity_name: string;
  file_path: string;
  description?: string | null;
  record_count?: number | null;
  schema_version?: string | null;
  primary_key?: string | null;
}

export interface MFDBDatabaseMeta {
  mfdb_version: string;
  db_name: string;
  db_description?: string;
  schema_version?: string;
  author?: string;
  created_at?: string;
}

export type MFDBFileRole = "manifest" | "entity" | "standalone";

// ---------------------------------------------------------------------------
// Error classes
// ---------------------------------------------------------------------------

export class BEJSONValidationError extends Error {
  public readonly code: number;
  constructor(code: number, message: string) {
    super(message);
    this.name = "BEJSONValidationError";
    this.code = code;
  }
}

export class BEJSONCoreError extends Error {
  public readonly code: number;
  constructor(code: number, message: string) {
    super(message);
    this.name = "BEJSONCoreError";
    this.code = code;
  }
}

export class MFDBValidationError extends Error {
  public readonly code: number;
  constructor(code: number, message: string) {
    super(message);
    this.name = "MFDBValidationError";
    this.code = code;
  }
}

export class MFDBCoreError extends Error {
  public readonly code: number;
  constructor(code: number, message: string) {
    super(message);
    this.name = "MFDBCoreError";
    this.code = code;
  }
}

// ---------------------------------------------------------------------------
// Validation error code catalogue
// ---------------------------------------------------------------------------

export const BEJSON_VALIDATION_CODES = {
  
  INVALID_JSON: 1,
  
  MISSING_MANDATORY_KEY: 2,
  
  INVALID_FORMAT_VALUE: 3,
  
  INVALID_FORMAT_VERSION: 4,
  
  INVALID_RECORDS_TYPE: 5,
  
  INVALID_FIELDS: 6,
  
  INVALID_VALUES: 7,
  
  VALUE_TYPE_MISMATCH: 8,
  
  RECORD_LENGTH_MISMATCH: 9,
  
  RESERVED_KEY_COLLISION: 10,
  
  INVALID_RECORD_TYPE_PARENT: 11,
  
  NULL_VIOLATION: 12,
  
  FILE_NOT_FOUND: 13,
  
  PERMISSION_DENIED: 14,
  
  ATOMIC_WRITE_FAILED: 15,
  
  INVALID_FORMAT_CREATOR: 16,
  
  DUPLICATE_FIELD_NAME: 6,        // alias: same block as INVALID_FIELDS (E_INVALID_FIELDS=6)
  VERSION_CONSTRAINT: 4,          // alias: maps to INVALID_FORMAT_VERSION
  FORBIDDEN_CUSTOM_KEY: 10,       // alias: maps to RESERVED_KEY_COLLISION
  INVALID_CUSTOM_KEY: 10,         // alias: maps to RESERVED_KEY_COLLISION
  MISSING_DISCRIMINATOR: 11,      // alias: maps to INVALID_RECORD_TYPE_PARENT
  INVALID_VALUES_STRUCTURE: 7,    // alias: maps to INVALID_VALUES
  MFDB_FK_UNRESOLVED: 39,          // alias: maps to MFDB_VALIDATION_CODES.FK_UNRESOLVED
} as const;

// ---------------------------------------------------------------------------
// Format 105 error codes -- numerically mirrors the Python registry
// (lib_bejson_Core_bejson_errors.py) exactly: 43-47 (FK/cascade, in
// BEJSON_105_FK_CODES below), 80-85 (Core+Validator infrastructure and
// field-identity guards). The 90-114 Schema Constraints block (required/
// unique/enum/min/max/minLength/maxLength) was REMOVED 2026-09-25 per
// Be25 -- see errors.py 2.9.0 changelog. Field UUIDs and FK/cascade are
// the entire kept 105-series feature set now.
// ---------------------------------------------------------------------------
export const BEJSON_105_CODES = {
  FIELD_INTEGRITY_MISMATCH:     80,  // name/field_uuid pair disagree, or target unresolvable
  FORMAT_UNSUPPORTED:           81,  // a 105-only function was called on a non-105-series doc
  RECORD_NOT_FOUND:             82,  // record_uuid does not resolve to any row
  UPGRADE_VALIDATION_FAILED:    83,  // upgradeTo105 built a doc that failed strict-integrity validation
  FIELD_NAME_ALREADY_EXISTS:    84,  // defineField called with a name already present in Fields (canonical registry name: E_DUPLICATE_FIELD_NAME)
  DUPLICATE_FIELD_UUID:         85,  // a generated field_uuid collides with an existing one (defensive; ~impossible)
} as const;

export const BEJSON_CORE_CODES = {
  
  INVALID_VERSION: 20,
  
  INVALID_OPERATION: 21,
  
  INDEX_OUT_OF_BOUNDS: 22,
  
  FIELD_NOT_FOUND: 23,
  
  TYPE_CONVERSION_FAILED: 24,
  
  BACKUP_FAILED: 25,
  
  WRITE_FAILED: 26,
  
  QUERY_FAILED: 27,
  
  ENCRYPTION_FAILED: 28,
  
  DECRYPTION_FAILED: 29,
  
  // Extended core codes (JS-only in errors.js; now unified in TS)
  PARSE_ERROR: 17,
  SERIALIZATION_ERROR: 18,
  NULL_DOCUMENT: 19,
  
  // Aliases for codes referenced in bejson_core.ts
  UNSUPPORTED_OPERATION: 21,      // alias: maps to INVALID_OPERATION
  WRITE_TYPE_MISMATCH: 8,         // alias: maps to TYPE_MISMATCH  
  WRITE_LENGTH_MISMATCH: 9,       // alias: maps to INDEX_OUT_OF_BOUNDS
} as const;

export const MFDB_VALIDATION_CODES = {
  
  NOT_A_MANIFEST: 30,
  
  NOT_AN_ENTITY: 31,
  
  MANIFEST_RECORDS_TYPE_INVALID: 32,
  
  ENTITY_FILE_NOT_FOUND: 33,
  
  ENTITY_NAME_MISMATCH: 34,
  
  DUPLICATE_ENTRY: 35,
  
  MISSING_PARENT_HIERARCHY: 36,
  
  MANIFEST_FILE_NOT_FOUND: 37,
  
  BIDIRECTIONAL_PATH_FAILED: 38,
  
  FK_UNRESOLVED: 39,
  
  MISSING_REQUIRED_MANIFEST_FIELD: 40,
  
  NULL_IN_REQUIRED_MANIFEST_FIELD: 41,
  
  INVALID_ARCHIVE: 42,
  
  // 105-series MFDB Referential Integrity (Phase 6 TS port, 2026-08-26).
  // Numerically mirrors the Python registry exactly.
  FK_TARGET_ENTITY_UNKNOWN: 43,
  FK_RESTRICT_VIOLATION:    44,
  FK_CASCADE_CYCLE:         45,
  FK_ENTITY_STILL_REFERENCED: 46,
  FK_INVALID_ON_DELETE:     47,
} as const;

export const MFDB_CORE_CODES = {
  
  MANIFEST_NOT_FOUND: 50,
  
  ENTITY_NOT_FOUND: 51,
  
  WRITE_FAILED: 52,
  
  LOCK_FAILED: 53,
  
  INVALID_OPERATION: 54,
  
  INDEX_OUT_OF_BOUNDS: 55,
  
  JOIN_FAILED: 56,
  
  DUPLICATE_ENTITY_NAME: 57,
  
  RECORD_COUNT_SYNC_FAILED: 58,
  
  NULL_MANIFEST: 59,
  
  ENTITY_NOT_IN_MANIFEST: 60,
  
  ARCHIVE_ERROR: 70,
  
  MOUNT_CONFLICT: 71,
  
  CREATE_FAILED: 72,
  
  // Referenced in mfdb_validators.ts via MFDB_CORE_CODES — these belong to validation layer
  // but are emitted through MFDB_CORE_CODES in the current validators
  INVALID_MFDB_VERSION: 4,        // alias: maps to INVALID_FORMAT_VERSION
  MISSING_DB_NAME: 2,             // alias: maps to MISSING_MANDATORY_KEY
} as const;

// CORE_NESTING_CODES moved to lib_bejson_CoreNesting_bejson_errors.ts (v2.4.0)
