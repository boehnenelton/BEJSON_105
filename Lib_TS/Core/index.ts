/**
 * Library:        index.ts
 * Family:         Core
 * Description:    Main entry point for TypeScript Core library family. Corrected paths (v2.0.3): removed self-referential ./Core/ prefix.
 * Version:        2.0.7
 * Date:           2026-10-03
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  20b36e9b-be7b-43c9-b00c-9330c4561271
 * Release_Version: 300
 *
 * Changelog:
 *   2.0.6 - Removed check105SchemaConstraints from the validators export list
 *           (function deleted in validators 2.2.0).
 *   2.0.5 - BUG FIX (architecture): removed 7 `export * from "../Gaming/..."`
 *           lines. Core is a leaf dependency -- every other family imports
 *           FROM Core, Core must never import from a feature family like
 *           Gaming. This inversion meant Core/index.ts could not be used
 *           standalone (broke the moment Gaming wasn't present alongside
 *           it) and carried real circular-dependency risk. Predates this
 *           session's Phase 2.7 work entirely -- present since at least
 *           v2.0.3. Checked: this was the only file in either Lib_TS/Core
 *           or Lib_PY/Core with an outbound import to a non-Core family;
 *           Python Core is and was clean. Anyone who needs Gaming's
 *           exports imports lib_bejson_Gaming_* directly -- that's the
 *           correct direction (Gaming depends on Core, not the reverse).
 *   2.0.4 - Phase 2.7 TS parity: export lib_bejson_Core_bejson_core_105.ts
 *           and the two new 105-series check functions from the validator.
 */

// Types & error classes
export * from "./lib_bejson_Core_bejson_types";

// Core operations (parse, serialize, record CRUD)
export * from "./lib_bejson_Core_bejson_core";
export * from "./lib_bejson_Core_bejson_field_map";

// Format 105 ("Integrity Era") -- Phase 2.7 TS parity port
export * from "./lib_bejson_Core_bejson_core_105";

// BEJSON validators (104, 104a, 104db, 105, 105a, 105db)
export {
  validateDocument,
  validate104,
  validate104a,
  validate104db,
  assertValid,
  isValid,
  check105StrictIntegrity,
} from "./lib_bejson_Core_bejson_validators";

// MFDB validators
export {
  discoverRole,
  validateManifest,
  validateEntityFile,
  validateDatabase,
  decodeManifestRecords,
  decodeDatabaseMeta,
} from "./lib_bejson_Core_mfdb_validators";

// MFDB core
export {
  createManifest,
  registerEntity,
  unregisterEntity,
  syncRecordCount,
} from "./lib_bejson_Core_mfdb_core";

export type { EntityValidationOptions, DatabaseValidationOptions } from "./lib_bejson_Core_mfdb_validators";
export type { CreateManifestOptions as MFDBCreateManifestOptions } from "./lib_bejson_Core_mfdb_core";

// Schema management
export * from "./lib_bejson_Core_bejson_schema";
