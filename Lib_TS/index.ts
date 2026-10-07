/**
 * Library:        index.ts
 * Family:         Root
 * Description:    Main entry point for TypeScript library family. v2.2.0: Removed Gaming/Backend sub-family exports — Gaming is not part of the 105 library set (Core-only ecosystem for now).
 * Version:        2.4.0
 * Date:           2026-09-25
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  8f1c4a7e-2d9b-4f36-9c5e-7a1d3b8f6c92
 *
 * Changelog:
 *   2.4.0 - Removed check105SchemaConstraints from the named validator
 *           export list -- the function itself was deleted from
 *           lib_bejson_Core_bejson_validators.ts (schema-constraint
 *           removal, per Be25). check105StrictIntegrity is unaffected.
 *   2.3.0 - AUDIT FIX (M2): root index lagged Core/index.ts -- added the
 *           missing lib_bejson_Core_bejson_core_105 export and the two
 *           105-series validator check functions (check105StrictIntegrity,
 *           check105SchemaConstraints). Consumers importing from the
 *           package root can now reach Phase 2.7+ functionality; previously
 *           only importing directly from ./Core/index could.
 */

// Types & error classes
export * from "./Core/lib_bejson_Core_bejson_types";

// Core operations (parse, serialize, record CRUD)
export * from "./Core/lib_bejson_Core_bejson_core";
export * from "./Core/lib_bejson_Core_bejson_field_map";

// Format 105 ("Integrity Era") -- was missing from root index (audit M2);
// Core/index.ts has had this since v2.0.4, root lagged behind it.
export * from "./Core/lib_bejson_Core_bejson_core_105";

// BEJSON validators (104, 104a, 104db, 105, 105a, 105db)
export {
  validateDocument,
  validate104,
  validate104a,
  validate104db,
  assertValid,
  isValid,
  check105StrictIntegrity,
} from "./Core/lib_bejson_Core_bejson_validators";

// MFDB validators
export {
  discoverRole,
  validateManifest,
  validateEntityFile,
  validateDatabase,
  decodeManifestRecords,
  decodeDatabaseMeta,
} from "./Core/lib_bejson_Core_mfdb_validators";

// MFDB core
export {
  createManifest,
  registerEntity,
  unregisterEntity,
  syncRecordCount,
} from "./Core/lib_bejson_Core_mfdb_core";

export type { EntityValidationOptions, DatabaseValidationOptions } from "./Core/lib_bejson_Core_mfdb_validators";
export type { CreateManifestOptions as MFDBCreateManifestOptions } from "./Core/lib_bejson_Core_mfdb_core";

// Schema management
export * from "./Core/lib_bejson_Core_bejson_schema";
