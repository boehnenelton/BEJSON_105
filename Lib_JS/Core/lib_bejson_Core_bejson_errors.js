/**
 * Library:        lib_bejson_Core_bejson_errors.js
 * Family:         Core
 * Description:    Unified error registry for BEJSON ecosystem.
 * Version:        2.4.0
 * Date:           2026-07-18
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  2a4e37d8-e4ca-4aa0-9c25-cb3a1a044945
 * Release_Version: 300
 *
 * Changelog:
 *   2.4.0 - 2026-10-03: Added 105-series codes mirroring PY/SH registries:
 *           FK/cascade referential integrity (43-47) and field/record
 *           identity guards (80-85). FK_UNRESOLVED (39) reused, not duplicated.
 *   2.3.0 - Removed Core_Nesting range (130-159) — that family now owns
 *           its codes in lib_bejson_CoreNesting_bejson_errors.js. Removed
 *           the Cognition range (270-275): verified zero references
 *           anywhere in Lib_JS (no Lib_JS/Cognition family exists) and
 *           dropped as dead code per the dead-code cleanup policy, rather
 *           than moved, since there is nowhere in JS to move it to.
 *           MFDB codes (30-49, 50-72) remain here: MFDB is implemented
 *           as part of the Core family, not a separate family directory.
 */

const BEJSON_ERRORS = {
    // BEJSON Core/Validator (1-29)
    E_INVALID_JSON: 1,
    E_MISSING_MANDATORY_KEY: 2,
    E_INVALID_FORMAT: 3,
    E_INVALID_VERSION: 4,
    E_INVALID_RECORDS_TYPE: 5,
    E_INVALID_FIELDS: 6,
    E_INVALID_VALUES: 7,
    E_TYPE_MISMATCH: 8,
    E_RECORD_LENGTH_MISMATCH: 9,
    E_RESERVED_KEY_COLLISION: 10,
    E_INVALID_RECORD_TYPE_PARENT: 11,
    E_NULL_VIOLATION: 12,
    E_FILE_NOT_FOUND: 13,
    E_PERMISSION_DENIED: 14,
    E_ATOMIC_WRITE_FAILED: 15,
    E_INVALID_FORMAT_CREATOR: 16,

    // Core Extended (17-19) — merged from engine dump, verified unallocated in canonical registry
    E_CORE_PARSE_ERROR: 17,
    E_CORE_SERIALIZATION_ERROR: 18,
    E_CORE_NULL_DOCUMENT: 19,
    
    E_CORE_INVALID_VERSION: 20,
    E_CORE_INVALID_OPERATION: 21,
    E_CORE_INDEX_OUT_OF_BOUNDS: 22,
    E_CORE_FIELD_NOT_FOUND: 23,
    E_CORE_TYPE_CONVERSION_FAILED: 24,
    E_CORE_BACKUP_FAILED: 25,
    E_CORE_WRITE_FAILED: 26,
    E_CORE_QUERY_FAILED: 27,
    E_CORE_ENCRYPTION_FAILED: 28,
    E_CORE_DECRYPTION_FAILED: 29,

    // MFDB Core/Validator (30-49)
    E_MFDB_NOT_MANIFEST: 30,
    E_MFDB_NOT_ENTITY_FILE: 31,
    E_MFDB_MANIFEST_RECORDS_TYPE: 32,
    E_MFDB_ENTITY_NOT_FOUND: 33,
    E_MFDB_ENTITY_NAME_MISMATCH: 34,
    E_MFDB_DUPLICATE_ENTRY: 35,
    E_MFDB_NO_PARENT_HIERARCHY: 36,
    E_MFDB_MANIFEST_NOT_FOUND: 37,
    E_MFDB_BIDIRECTIONAL_FAIL: 38,
    E_MFDB_FK_UNRESOLVED: 39,
    E_MFDB_MISSING_REQUIRED_FIELD: 40,
    E_MFDB_NULL_REQUIRED: 41,
    E_MFDB_INVALID_ARCHIVE: 42,
    // 105-series FK / cascade referential integrity (Phase 6)
    E_MFDB_FK_TARGET_ENTITY_UNKNOWN: 43,
    E_MFDB_FK_RESTRICT_VIOLATION: 44,
    E_MFDB_FK_CASCADE_CYCLE: 45,
    E_MFDB_FK_ENTITY_STILL_REFERENCED: 46,
    E_MFDB_FK_INVALID_ON_DELETE: 47,
    
    E_MFDB_CORE_MANIFEST_NOT_FOUND: 50,
    E_MFDB_CORE_ENTITY_NOT_FOUND: 51,
    E_MFDB_CORE_WRITE_FAILED: 52,
    E_MFDB_CORE_LOCK_FAILED: 53,
    E_MFDB_CORE_INVALID_OPERATION: 54,
    E_MFDB_CORE_INDEX_OUT_OF_BOUNDS: 55,
    E_MFDB_CORE_JOIN_FAILED: 56,
    E_MFDB_CORE_ARCHIVE_ERROR: 70,
    E_MFDB_CORE_MOUNT_CONFLICT: 71,
    E_MFDB_CORE_CREATE_FAILED: 72,

    // 105-series field / record identity guards
    E_FIELD_INTEGRITY_MISMATCH: 80,
    E_FORMAT_UNSUPPORTED: 81,
    E_RECORD_NOT_FOUND: 82,
    E_UPGRADE_VALIDATION_FAILED: 83,
    E_DUPLICATE_FIELD_NAME: 84,
    E_DUPLICATE_FIELD_UUID: 85,

    // Cognition (270-275) removed v2.3.0 — dead code, no Lib_JS/Cognition family exists
    // Core_Nesting codes moved to lib_bejson_CoreNesting_bejson_errors.js (v2.3.0)
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = BEJSON_ERRORS;
}
if (typeof window !== 'undefined') {
    window.BEJSON_ERRORS = BEJSON_ERRORS;
}
