/**
 * Library:         lib_bejson_Core_mfdb_validator.js
 * Family:          Core
 * Module Purpose:  MFDB validator: manifest (Level 1), entity files (Level 2) and database-level checks (Level 3, e.g. record_count accuracy).
 * Architecture:    MFDB (a database architecture layered on BEJSON, not a BEJSON format version): one BEJSON 104a manifest (104a.mfdb.bejson, Records_Type ["mfdb"]) registers many BEJSON 104 entity files, one entity per file, dense records, each with Parent_Hierarchy pointing back to the manifest. It is not 104db and uses no null-padding.
 * Format_Scope:    MFDB only (104a manifest + 104 entity files; NOT 104db)
 * Glossary:        BEJSON 104, 104a and 104db are the three file formats (Format_Version). 104db = ONE file holding 2+ entity types
 *                  (Record_Type_Parent discriminator, null-padding). MFDB is NOT a format and NOT 104db: it is a layer made of one 104a manifest
 *                  (104a.mfdb.bejson) plus dense 104 entity files linked by Parent_Hierarchy. MFDB-132 = an MFDB packed into one Chunked-104a document.
 * Version:         2.1.5
 * Release_Version: 300
 * Date:            2026-10-29
 * Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * Format_Creator:  Elton Boehnen
 * RELATIONAL_ID:   111769a2-5a7d-4349-8d67-3f2836e69f81
 */

'use strict';

const {
  BEJSONValidationError,
  bejson_validator_validate_file,
  bejson_validator_validate_string,
} = (typeof require !== 'undefined')
  ? require('./lib_bejson_Core_bejson_validator.js')
  : window.BEJSON_VALIDATOR;

const BEJSON_ERRORS = (typeof require !== 'undefined') 
  ? require('./lib_bejson_Core_bejson_errors.js') 
  : (window.BEJSON_ERRORS || {});

const {
  E_MFDB_NOT_MANIFEST,
  E_MFDB_NOT_ENTITY_FILE,
  E_MFDB_MANIFEST_RECORDS_TYPE,
  E_MFDB_ENTITY_NOT_FOUND,
  E_MFDB_ENTITY_NAME_MISMATCH,
  E_MFDB_DUPLICATE_ENTRY,
  E_MFDB_NO_PARENT_HIERARCHY,
  E_MFDB_MANIFEST_NOT_FOUND,
  E_MFDB_BIDIRECTIONAL_FAIL,
  E_MFDB_FK_UNRESOLVED,
  E_MFDB_MISSING_REQUIRED_FIELD,
  E_MFDB_NULL_REQUIRED,
  E_MFDB_INVALID_ARCHIVE
} = BEJSON_ERRORS;

class MFDBValidationError extends Error {
  /**
   * Error type for MFDB validation failures (MFDBValidationError); carries a numeric code.
   */
  constructor(message, code) {
    super(message);
    this.name = 'MFDBValidationError';
    this.code = code;
  }
}

// ---------------------------------------------------------------------------
// Validation state
// ---------------------------------------------------------------------------

let _mErrors   = [];
let _mWarnings = [];

/**
 * Clears the module's error and warning lists before a validation run.
 */
function _mReset()                  { _mErrors = []; _mWarnings = []; }
/**
 * Records a hard MFDB error (structural failure) with an optional location.
 */
function _mAddError(msg, loc)       { _mErrors.push(   'ERROR'   + (loc ? ` | Location: ${loc}` : '') + ` | Message: ${msg}`); }
/**
 * Records a warning (convention failure, e.g. record_count drift) -- does not invalidate the MFDB.
 */
function _mAddWarning(msg, loc)     { _mWarnings.push( 'WARNING' + (loc ? ` | Location: ${loc}` : '') + ` | Message: ${msg}`); }
/**
 * True if any error was recorded.
 */
function _mHasErrors()              { return _mErrors.length   > 0; }
/**
 * True if any warning was recorded.
 */
function _mHasWarnings()            { return _mWarnings.length > 0; }

// ---------------------------------------------------------------------------
// Internal helpers (also exported for lib_bejson_Core_mfdb_core.js)
// ---------------------------------------------------------------------------

/**
 * True when running under Node.js (file-system access available). In a browser the file-based validators cannot read files.
 */
// require('fs') and require('path') are Node.js-only. In browser environments
// these helpers are non-functional. Guard all calls with a Node check so that importing
// this module in a browser context does not throw immediately on function definition.
function _isNode() {
  return typeof process !== 'undefined' && process.versions && !!process.versions.node;
}

/**
 * Reads and parses a JSON file (Node only). Throws on failure.
 */
function _loadJson(filePath) {
  if (!_isNode()) {
    throw new MFDBValidationError('_loadJson is only available in Node.js environments', E_MFDB_ENTITY_NOT_FOUND);
  }
  const fs = require('fs');
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

/**
 * Turns a BEJSON document's Values into {fieldName: value} objects using Fields.
 * 105-series aware: surfaces record_uuid and Record_Type_Parent without column misalignment.
 */
function _rowsAsDicts(doc) {
  const names = (doc.Fields || []).map(f => f.name);
  const fmt = doc.Format_Version;
  if (['105', '105a', '105db'].includes(fmt)) {
    const isMulti = fmt === '105db';
    const offset = isMulti ? 2 : 1;
    const dataNames = isMulti ? names.slice(1) : names;
    return (doc.Values || []).map(row => {
      const d = Object.fromEntries(dataNames.map((n, i) => [n, row[offset + i]]));
      d.record_uuid = isMulti ? row[1] : row[0];
      if (isMulti) {
        d.Record_Type_Parent = row[0];
      }
      return d;
    });
  }
  return (doc.Values || []).map(row => Object.fromEntries(names.map((n, i) => [n, row[i]])));
}

/**
 * Resolves an entity's file_path (relative to the manifest) against the manifest's directory.
 */
function _resolveEntityPath(manifestPath, filePathRel) {
  if (!_isNode()) {
    throw new MFDBValidationError('_resolveEntityPath is only available in Node.js environments', E_MFDB_ENTITY_NOT_FOUND);
  }
  const path = require('path');
  return path.resolve(path.dirname(manifestPath), filePathRel);
}

/**
 * Relative-depth path traversal check.
 * Normalizes separators then counts directory depth segment by segment.
 * Returns true (unsafe) if any '..' drops depth below 0.
 */
function _bejson_mfdb_escapes_root(relativePath) {
  if (!relativePath || typeof relativePath !== 'string') return false;
  const normalized = relativePath.replace(/\\/g, '/');
  const parts = normalized.split('/');
  let depth = 0;
  for (const part of parts) {
    if (part === '..') {
      depth -= 1;
      if (depth < 0) return true;
    } else if (part !== '.' && part !== '') {
      depth += 1;
    }
  }
  return false;
}

/**
 * File-existence check; assumes false in a browser.
 */
function _fileExists(filePath) {
  if (!_isNode()) return false;  // In browser: assume non-existent, caller handles
  const fs = require('fs');
  return fs.existsSync(filePath);
}

// ---------------------------------------------------------------------------
// Archive Validation (v1.2 Feature)
// ---------------------------------------------------------------------------

/**
 * Validates a .mfdb.zip archive as an MFDB container (manifest + entity files inside).
 */
function mfdb_validator_validate_archive(archivePath) {
  _mReset();
  const AdmZip = require('adm-zip');

  if (!_fileExists(archivePath)) {
    _mAddError(`Archive not found: ${archivePath}`, 'File System');
    throw new MFDBValidationError(`Archive not found: ${archivePath}`, E_MFDB_MANIFEST_NOT_FOUND);
  }

  try {
    const zip = new AdmZip(archivePath);
    const zipEntries = zip.getEntries();
    const hasManifest = zipEntries.some(e => e.entryName === '104a.mfdb.bejson');
    if (!hasManifest) {
      _mAddError("Archive missing 104a.mfdb.bejson at root", "Zip Structure");
      throw new MFDBValidationError("Missing manifest inside archive", E_MFDB_INVALID_ARCHIVE);
    }
  } catch (exc) {
    _mAddError(`Invalid zip file: ${exc.message}`, "Zip Parser");
    throw new MFDBValidationError(exc.message, E_MFDB_INVALID_ARCHIVE);
  }

  return true;
}

// ---------------------------------------------------------------------------
// Manifest Validation  (Spec §8.1)
// ---------------------------------------------------------------------------

/**
 * Level 1: the manifest must be a BEJSON 104a document named *.mfdb.bejson with Records_Type ["mfdb"] and the required manifest headers/fields. A 104db file or a plain 104a is not an MFDB manifest.
 */
function mfdb_validator_validate_manifest(manifestPath) {
  _mReset();
  if (!_isNode()) {
    _mAddError('mfdb_validator_validate_manifest requires a Node.js environment', 'Environment');
    return false;
  }

  if (!_fileExists(manifestPath)) {
    _mAddError(`Manifest file not found: ${manifestPath}`, 'File System');
    throw new MFDBValidationError(`File not found: ${manifestPath}`, E_MFDB_MANIFEST_NOT_FOUND);
  }

  try {
    bejson_validator_validate_file(manifestPath);
  } catch (exc) {
    _mAddError(`BEJSON 104a validation failed: ${exc.message}`, 'BEJSON Validation');
    throw new MFDBValidationError(exc.message, E_MFDB_NOT_MANIFEST);
  }

  const doc = _loadJson(manifestPath);

  if (doc.Format_Version !== '104a') {
    _mAddError("Manifest must be Format_Version '104a'", 'Format_Version');
    throw new MFDBValidationError('Manifest must be 104a', E_MFDB_NOT_MANIFEST);
  }

  const rt = doc.Records_Type || [];
  if (!(rt.length === 1 && rt[0] === 'mfdb')) {
    _mAddError(`[${E_MFDB_MANIFEST_RECORDS_TYPE}] Records_Type must be ["mfdb"]. Found: ${JSON.stringify(rt)}`, 'Records_Type');
    throw new MFDBValidationError('Bad manifest Records_Type', E_MFDB_MANIFEST_RECORDS_TYPE);
  }

  const fieldNames = (doc.Fields || []).map(f => f.name);
  for (const required of ['entity_name', 'file_path']) {
    if (!fieldNames.includes(required)) {
      _mAddError(`[${E_MFDB_MISSING_REQUIRED_FIELD}] Missing required field: ${required}`, 'Fields');
      throw new MFDBValidationError(`Missing required field: ${required}`, E_MFDB_MISSING_REQUIRED_FIELD);
    }
  }

  const entries    = _rowsAsDicts(doc);
  const seenNames  = new Set();
  const seenPaths  = new Set();

  for (let i = 0; i < entries.length; i++) {
    const entry      = entries[i];
    const entityName = entry.entity_name;
    const filePath   = entry.file_path;

    if (!entityName || !filePath) {
      _mAddError(`[${E_MFDB_NULL_REQUIRED}] Record ${i}: null entity_name or file_path`, `Values[${i}]`);
      throw new MFDBValidationError('Null entity_name or file_path', E_MFDB_NULL_REQUIRED);
    }
    if (seenNames.has(entityName)) {
      _mAddError(`[${E_MFDB_DUPLICATE_ENTRY}] Duplicate entity: ${entityName}`, `Values[${i}]`);
      throw new MFDBValidationError(`Duplicate entity: ${entityName}`, E_MFDB_DUPLICATE_ENTRY);
    }
    seenNames.add(entityName);

    if (seenPaths.has(filePath)) {
      _mAddError(`[${E_MFDB_DUPLICATE_ENTRY}] Duplicate path: ${filePath}`, `Values[${i}]`);
      throw new MFDBValidationError(`Duplicate path: ${filePath}`, E_MFDB_DUPLICATE_ENTRY);
    }
    seenPaths.add(filePath);

    if (_bejson_mfdb_escapes_root(filePath)) {
      _mAddError(`[${E_MFDB_ENTITY_NOT_FOUND}] Path escapes root: ${filePath}`, `Values[${i}]/file_path`);
      throw new MFDBValidationError(`Path escapes root: ${filePath}`, E_MFDB_ENTITY_NOT_FOUND);
    }

    const resolved = _resolveEntityPath(manifestPath, filePath);
    if (!_fileExists(resolved)) {
      _mAddError(`[${E_MFDB_ENTITY_NOT_FOUND}] Entity file not found: ${filePath}`, `Values[${i}]/file_path`);
      throw new MFDBValidationError(`Entity file not found: ${resolved}`, E_MFDB_ENTITY_NOT_FOUND);
    }
  }

  return true;
}

// ---------------------------------------------------------------------------
// Entity File Validation  (Spec §8.2)
// ---------------------------------------------------------------------------

/**
 * Level 2: an entity file must be BEJSON 104 or 105 (one Records_Type) with Parent_Hierarchy;
 * with checkBidirectional also confirms the manifest lists it back.
 */
function mfdb_validator_validate_entity_file(entityPath, checkBidirectional = true, expectedEntityName = null, expectedManifest = null) {
  const path = require('path');
  _mReset();

  if (!_fileExists(entityPath)) {
    _mAddError(`[${E_MFDB_ENTITY_NOT_FOUND}] Entity file not found: ${entityPath}`, 'File System');
    throw new MFDBValidationError(`File not found: ${entityPath}`, E_MFDB_ENTITY_NOT_FOUND);
  }

  try {
    bejson_validator_validate_file(entityPath);
  } catch (exc) {
    _mAddError(`[${E_MFDB_NOT_ENTITY_FILE}] BEJSON validation failed: ${exc.message}`, 'BEJSON Validation');
    throw new MFDBValidationError(exc.message, E_MFDB_NOT_ENTITY_FILE);
  }

  const doc = _loadJson(entityPath);

  if (doc.Format_Version !== '104' && doc.Format_Version !== '105') {
    _mAddError(`[${E_MFDB_NOT_ENTITY_FILE}] Entity file must be Format_Version 104 or 105`, 'Format_Version');
    throw new MFDBValidationError('Entity file must be 104 or 105', E_MFDB_NOT_ENTITY_FILE);
  }

  const parentHierarchy = doc.Parent_Hierarchy;
  if (!parentHierarchy) {
    _mAddError(`[${E_MFDB_NO_PARENT_HIERARCHY}] Missing Parent_Hierarchy`, 'Structure');
    throw new MFDBValidationError('Missing Parent_Hierarchy', E_MFDB_NO_PARENT_HIERARCHY);
  }

  const entityDir    = path.dirname(path.resolve(entityPath));
  const manifestPath = path.resolve(entityDir, parentHierarchy);

  if (!_fileExists(manifestPath)) {
    _mAddError(
      `[${E_MFDB_MANIFEST_NOT_FOUND}] Manifest not found at ${manifestPath} (orphan entity)`,
      'Parent_Hierarchy',
    );
    throw new MFDBValidationError(`Manifest not found at ${manifestPath} (orphan entity)`, E_MFDB_MANIFEST_NOT_FOUND);
  }

  if (!path.basename(manifestPath).endsWith('.mfdb.bejson')) {
    _mAddWarning(
      `Parent_Hierarchy target '${manifestPath}' does not end in '.mfdb.bejson'. Expected: 104a.mfdb.bejson`,
      'Parent_Hierarchy',
    );
  }

  const rt = doc.Records_Type || [];
  if (!Array.isArray(rt) || rt.length !== 1 || typeof rt[0] !== 'string' || !rt[0]) {
    _mAddError(`[${E_MFDB_ENTITY_NAME_MISMATCH}] Records_Type must contain exactly one string (the entity name)`, 'Records_Type');
    throw new MFDBValidationError('Entity Records_Type must be single-entry', E_MFDB_ENTITY_NAME_MISMATCH);
  }

  const entityName = rt[0];

  if (expectedManifest !== null && expectedManifest !== undefined) {
    if (path.resolve(manifestPath) !== path.resolve(expectedManifest)) {
      _mAddError(
        `[${E_MFDB_BIDIRECTIONAL_FAIL}] Parent_Hierarchy points to ${manifestPath}, not to the manifest that lists this file (${expectedManifest})`,
        'Parent_Hierarchy',
      );
      throw new MFDBValidationError('Bidirectional check failed', E_MFDB_BIDIRECTIONAL_FAIL);
    }
  }

  if (expectedEntityName !== null && expectedEntityName !== undefined) {
    if (entityName !== expectedEntityName) {
      _mAddError(
        `[${E_MFDB_ENTITY_NAME_MISMATCH}] Records_Type '${entityName}' does not match manifest entity_name '${expectedEntityName}' (case-sensitive)`,
        'Records_Type',
      );
      throw new MFDBValidationError(`Records_Type '${entityName}' does not match manifest entity_name '${expectedEntityName}'`, E_MFDB_ENTITY_NAME_MISMATCH);
    }
  }

  if (checkBidirectional) {
    let manifestDoc, entries;
    try {
      manifestDoc = _loadJson(manifestPath);
      if (manifestDoc.Format_Version !== '104a' || JSON.stringify(manifestDoc.Records_Type) !== JSON.stringify(['mfdb'])) {
        _mAddError(`[${E_MFDB_NOT_MANIFEST}] Parent_Hierarchy target is not an MFDB manifest`, 'Parent_Hierarchy');
        throw new MFDBValidationError('Parent_Hierarchy target is not an MFDB manifest', E_MFDB_NOT_MANIFEST);
      }
      entries = _rowsAsDicts(manifestDoc);
    } catch (exc) {
      if (exc instanceof MFDBValidationError) throw exc;
      _mAddError(`[${E_MFDB_NOT_MANIFEST}] Parent_Hierarchy target unreadable as a manifest: ${exc.message}`, 'Parent_Hierarchy');
      throw new MFDBValidationError(`Cannot read manifest: ${exc.message}`, E_MFDB_NOT_MANIFEST);
    }

    const resolvedEntity = path.resolve(entityPath);
    const mine = entries.filter(r => r.file_path && !_bejson_mfdb_escapes_root(r.file_path) && path.resolve(_resolveEntityPath(manifestPath, r.file_path)) === resolvedEntity);

    if (mine.length === 0) {
      _mAddError(
        `[${E_MFDB_BIDIRECTIONAL_FAIL}] Bidirectional check failed: manifest ${manifestPath} has no file_path that resolves to this entity file`,
        'Parent_Hierarchy',
      );
      throw new MFDBValidationError('Bidirectional check failed', E_MFDB_BIDIRECTIONAL_FAIL);
    } else if (expectedEntityName === null && !mine.some(r => r.entity_name === entityName)) {
      _mAddError(
        `[${E_MFDB_ENTITY_NAME_MISMATCH}] Records_Type '${entityName}' does not match the manifest entity_name for this file ('${mine[0].entity_name}')`,
        'Records_Type',
      );
      throw new MFDBValidationError('Records_Type mismatch', E_MFDB_ENTITY_NAME_MISMATCH);
    }
  }

  return true;
}

// ---------------------------------------------------------------------------
// Database-Level Validation  (Spec §8.3)
// ---------------------------------------------------------------------------

/**
 * Level 3: whole MFDB -- manifest, every entity file, record_count accuracy and *_fk conventions.
 */
function mfdb_validator_validate_database(manifestPath, strictFk = false) {
  _mReset();

  try {
    mfdb_validator_validate_manifest(manifestPath);
  } catch (exc) {
    throw exc;
  }

  const manifestDoc = _loadJson(manifestPath);
  const entries     = _rowsAsDicts(manifestDoc);

  for (const entry of entries) {
    const entityName    = entry.entity_name;
    const filePathRel   = entry.file_path;
    const declaredCount = entry.record_count;

    const resolved = _resolveEntityPath(manifestPath, filePathRel);

    try {
      mfdb_validator_validate_entity_file(resolved, true, entityName, manifestPath);
    } catch (exc) {
      _mAddError(`Entity '${entityName}' failed validation: ${exc.message}`, `Entity/${entityName}`);
      throw exc;
    }

    if (declaredCount !== null && declaredCount !== undefined) {
      try {
        const edoc        = _loadJson(resolved);
        const actualCount = (edoc.Values || []).length;
        if (actualCount !== declaredCount) {
          _mAddWarning(
            `record_count ${declaredCount} in manifest != ${actualCount} rows in file`,
            `Entity:${entityName}`,
          );
        }
      } catch (e) {
        _mAddWarning(`could not compare record_count: ${e.message}`, `Entity:${entityName}`);
      }
    }
  }

  if (strictFk) {
    const fkErrors = mfdb_validator_check_referential_integrity(manifestPath);
    if (fkErrors && fkErrors.length > 0) {
      for (const err of fkErrors) {
        _mAddError(`[${err.code || E_MFDB_FK_UNRESOLVED}] ${err.detail || err.message || err}`, `Entity`);
      }
      throw new MFDBValidationError('Referential integrity validation failed', E_MFDB_FK_UNRESOLVED);
    }
  }

  return true;
}

function validate_mfdb_database(manifestPath, strictFk = false) {
  const savedErrors = [..._mErrors];
  const savedWarnings = [..._mWarnings];
  let valid = true;
  _mReset();
  try {
    mfdb_validator_validate_database(manifestPath, strictFk);
  } catch (_) {
    valid = false;
  }
  const errors = [..._mErrors];
  const warnings = [..._mWarnings];
  _mErrors = savedErrors;
  _mWarnings = savedWarnings;
  return { valid: valid && errors.length === 0, is_valid: valid && errors.length === 0, errors, warnings };
}

function validate_mfdb_entity_file(entityPath, checkBidirectional = true, expectedEntityName = null, expectedManifest = null) {
  const savedErrors = [..._mErrors];
  const savedWarnings = [..._mWarnings];
  let valid = true;
  _mReset();
  try {
    mfdb_validator_validate_entity_file(entityPath, checkBidirectional, expectedEntityName, expectedManifest);
  } catch (_) {
    valid = false;
  }
  const errors = [..._mErrors];
  const warnings = [..._mWarnings];
  _mErrors = savedErrors;
  _mWarnings = savedWarnings;
  return { valid: valid && errors.length === 0, is_valid: valid && errors.length === 0, errors, warnings };
}

function validate_mfdb_manifest(manifestPath) {
  const savedErrors = [..._mErrors];
  const savedWarnings = [..._mWarnings];
  let valid = true;
  _mReset();
  try {
    mfdb_validator_validate_manifest(manifestPath);
  } catch (_) {
    valid = false;
  }
  const errors = [..._mErrors];
  const warnings = [..._mWarnings];
  _mErrors = savedErrors;
  _mWarnings = savedWarnings;
  return { valid: valid && errors.length === 0, is_valid: valid && errors.length === 0, errors, warnings };
}

function validate_mfdb_archive(archivePath) {
  const savedErrors = [..._mErrors];
  const savedWarnings = [..._mWarnings];
  let valid = true;
  _mReset();
  try {
    mfdb_validator_validate_archive(archivePath);
  } catch (_) {
    valid = false;
  }
  const errors = [..._mErrors];
  const warnings = [..._mWarnings];
  _mErrors = savedErrors;
  _mWarnings = savedWarnings;
  return { valid: valid && errors.length === 0, is_valid: valid && errors.length === 0, errors, warnings };
}

// ---------------------------------------------------------------------------
// Validation report
// ---------------------------------------------------------------------------

/**
 * Runs validate_database and returns a human-readable report string.
 */
function mfdb_validator_get_report(manifestPath, strictFk = false) {
  let valid = false;
  try {
    valid = mfdb_validator_validate_database(manifestPath, strictFk);
  } catch (_) {}

  const lines = [
    '=== MFDB Validation Report ===',
    `Manifest : ${manifestPath}`,
    `Status   : ${valid ? 'VALID' : 'INVALID'}`,
    '',
    `Errors   : ${_mErrors.length}`,
  ];
  if (_mHasErrors()) {
    lines.push('---');
    lines.push(..._mErrors);
  }
  lines.push('', `Warnings : ${_mWarnings.length}`);
  if (_mHasWarnings()) {
    lines.push('---');
    lines.push(..._mWarnings);
  }
  return lines.join('\n');
}

// ---------------------------------------------------------------------------
// MFDB 1.32 chunked-package validation
// ---------------------------------------------------------------------------
// The chunking library owns bejsonCoreChunkingCreateMfdb132Package/bejsonCoreChunkingUnchunkMfdb132Package
// (packaging and IO) and calls these functions for validation; validation logic lives in the validator family.

const MFDB_MANIFEST_FILENAME = "104a.mfdb.bejson";

/**
 * True if a Chunked-104a document is a packaged MFDB-132 (an MFDB stored in one chunk document).
 */
function mfdb_validator_is_mfdb132_package(doc) {
  return (
    doc.Format_Version === "104a" &&
    doc.Schema_Name === "MFDB-132" &&
    doc.Package_Format === "MFDB-Chunked-104a" &&
    !!doc.MFDB_Version &&
    !!doc.DB_Name
  );
}

/**
 * Level-1 check of an MFDB-132 package document (manifest row and entity rows present, paths consistent). Returns {valid, errors, warnings}.
 */
function mfdb_validator_validate_mfdb132_package(doc) {
  const errors = [];
  const warnings = [];

  if (!mfdb_validator_is_mfdb132_package(doc)) {
    errors.push(
      "Document is not a recognized MFDB-132 package (missing/incorrect " +
        "Schema_Name/Package_Format/MFDB_Version/DB_Name)."
    );
    return { valid: false, errors, warnings };
  }

  if (JSON.stringify(doc.Records_Type) !== JSON.stringify(["MFDB-132"])) {
    errors.push("Records_Type must be exactly ['MFDB-132'] for an MFDB-132 package.");
  }

  const fields = doc.Fields || [];
  const fm = {};
  fields.forEach((f, i) => (fm[f.name] = i));

  let manifestFound = false;
  for (const row of doc.Values || []) {
    if (row[fm["Relative_Path"]] === MFDB_MANIFEST_FILENAME) {
      manifestFound = true;
      break;
    }
  }

  if (!manifestFound) {
    errors.push(
      `Chunked package does not contain the MFDB manifest (${MFDB_MANIFEST_FILENAME}) — ` +
        "not a complete MFDB package."
    );
  }

  return { valid: errors.length === 0, errors, warnings };
}

/**
 * Finds the chunk-document row whose Relative_Path matches; null if absent.
 */
function _mfdbValidatorFindRowByRelPath(doc, relPath) {
  const fields = doc.Fields || [];
  const fm = {};
  fields.forEach((f, i) => (fm[f.name] = i));
  const relIdx = fm["Relative_Path"];
  if (relIdx === undefined) return null;
  for (const row of doc.Values || []) {
    if (row[relIdx] === relPath) return row;
  }
  return null;
}

/**
 * Finds and validates an MFDB embedded in any Chunked-104a document; returns a report object.
 */
function mfdb_validator_detect_mfdb_in_chunk(doc) {
  const result = {
    mfdb_detected: false,
    valid: false,
    db_name: null,
    mfdb_version: null,
    entities: [],
    errors: [],
    warnings: [],
  };

  const fields = doc.Fields || [];
  const fm = {};
  fields.forEach((f, i) => (fm[f.name] = i));
  const required = ["Relative_Path", "File_Content", "Is_Binary"];
  if (required.some((k) => fm[k] === undefined)) {
    result.errors.push("Chunk document is missing required Chunked-104 fields.");
    return result;
  }

  const manifestRow = _mfdbValidatorFindRowByRelPath(doc, MFDB_MANIFEST_FILENAME);
  if (manifestRow === null) {
    result.errors.push(`No manifest (${MFDB_MANIFEST_FILENAME}) found in chunk — no MFDB present.`);
    return result;
  }

  if (manifestRow[fm["Is_Binary"]]) {
    result.errors.push("Manifest row is flagged Is_Binary — its content was never stored, cannot validate.");
    return result;
  }

  let manifestDoc;
  try {
    manifestDoc = JSON.parse(manifestRow[fm["File_Content"]]);
  } catch (e) {
    result.errors.push(`Manifest content is not valid JSON: ${e.message}`);
    return result;
  }

  result.mfdb_detected = true;
  result.db_name = manifestDoc.DB_Name ?? null;
  result.mfdb_version = manifestDoc.MFDB_Version ?? null;

  if (manifestDoc.Format_Version !== "104a") {
    result.errors.push("Manifest Format_Version must be '104a'.");
  }
  if (JSON.stringify(manifestDoc.Records_Type) !== JSON.stringify(["mfdb"])) {
    result.errors.push("Manifest Records_Type must be exactly ['mfdb'].");
  }

  const manifestFields = manifestDoc.Fields || [];
  const manifestFm = {};
  manifestFields.forEach((f, i) => (manifestFm[f.name] = i));
  if (manifestFm["entity_name"] === undefined || manifestFm["file_path"] === undefined) {
    result.errors.push("Manifest Fields must include 'entity_name' and 'file_path'.");
    return result;
  }

  const seenEntityNames = new Set();
  const seenFilePaths = new Set();

  for (const entityRow of manifestDoc.Values || []) {
    const entityName = entityRow[manifestFm["entity_name"]];
    const filePath = entityRow[manifestFm["file_path"]];
    const entityResult = {
      entity_name: entityName,
      file_path: filePath,
      found_in_chunk: false,
      valid: false,
      errors: [],
    };

    if (!entityName || !filePath) {
      entityResult.errors.push("entity_name/file_path must not be null.");
    }
    if (seenEntityNames.has(entityName)) {
      entityResult.errors.push(`Duplicate entity_name '${entityName}' in manifest.`);
    }
    if (seenFilePaths.has(filePath)) {
      entityResult.errors.push(`Duplicate file_path '${filePath}' in manifest.`);
    }
    seenEntityNames.add(entityName);
    seenFilePaths.add(filePath);

    const entityChunkRow = _mfdbValidatorFindRowByRelPath(doc, filePath);
    if (entityChunkRow === null) {
      entityResult.errors.push(`Entity file '${filePath}' listed in manifest was not found in chunk.`);
      result.entities.push(entityResult);
      continue;
    }

    entityResult.found_in_chunk = true;
    if (entityChunkRow[fm["Is_Binary"]]) {
      entityResult.errors.push("Entity row is flagged Is_Binary — content was never stored, cannot validate.");
      result.entities.push(entityResult);
      continue;
    }

    let entityDoc;
    try {
      entityDoc = JSON.parse(entityChunkRow[fm["File_Content"]]);
    } catch (e) {
      entityResult.errors.push(`Entity file content is not valid JSON: ${e.message}`);
      result.entities.push(entityResult);
      continue;
    }

    if (entityDoc.Format_Version !== "104") {
      entityResult.errors.push("Entity Format_Version must be '104'.");
    }
    if (JSON.stringify(entityDoc.Records_Type) !== JSON.stringify([entityName])) {
      entityResult.errors.push(`Entity Records_Type must be exactly ['${entityName}'].`);
    }
    if (!("Parent_Hierarchy" in entityDoc)) {
      entityResult.errors.push("Entity is missing mandatory 'Parent_Hierarchy' key.");
    }

    entityResult.valid = entityResult.errors.length === 0;
    result.entities.push(entityResult);
  }

  result.valid = result.errors.length === 0 && result.entities.every((e) => e.valid);
  return result;
}

// ---------------------------------------------------------------------------
// State accessors
// ---------------------------------------------------------------------------

/**
 * Clears the validator's accumulated errors and warnings.
 */
function mfdb_validator_reset_state()      { _mReset(); }
/**
 * True if the last run recorded errors.
 */
function mfdb_validator_has_errors()       { return _mHasErrors(); }
/**
 * True if the last run recorded warnings.
 */
function mfdb_validator_has_warnings()     { return _mHasWarnings(); }
/**
 * Copy of the error list.
 */
function mfdb_validator_get_errors()       { return [..._mErrors]; }
/**
 * Copy of the warning list.
 */
function mfdb_validator_get_warnings()     { return [..._mWarnings]; }
/**
 * Number of errors.
 */
function mfdb_validator_error_count()      { return _mErrors.length; }
/**
 * Number of warnings.
 */
function mfdb_validator_warning_count()    { return _mWarnings.length; }

// ---------------------------------------------------------------------------
// Exports (CommonJS + browser global)
// ---------------------------------------------------------------------------

const exports_ = {
  // Error codes
  E_MFDB_NOT_MANIFEST,
  E_MFDB_NOT_ENTITY_FILE,
  E_MFDB_MANIFEST_RECORDS_TYPE,
  E_MFDB_ENTITY_NOT_FOUND,
  E_MFDB_ENTITY_NAME_MISMATCH,
  E_MFDB_DUPLICATE_ENTRY,
  E_MFDB_NO_PARENT_HIERARCHY,
  E_MFDB_MANIFEST_NOT_FOUND,
  E_MFDB_BIDIRECTIONAL_FAIL,
  E_MFDB_FK_UNRESOLVED,
  E_MFDB_MISSING_REQUIRED_FIELD,
  E_MFDB_NULL_REQUIRED,
  E_MFDB_INVALID_ARCHIVE,
  // Class
  MFDBValidationError,
  // Internal helpers (needed by lib_bejson_Core_mfdb_core.js)
  _loadJson,
  _rowsAsDicts,
  _resolveEntityPath,
  _fileExists,
  // Validation functions
  validate_mfdb_archive,
  validate_mfdb_manifest,
  validate_mfdb_entity_file,
  validate_mfdb_database,
  mfdb_validator_validate_archive,
  mfdb_validator_validate_manifest,
  mfdb_validator_validate_entity_file,
  mfdb_validator_validate_database,
  mfdb_validator_get_report,
  // MFDB 1.32 chunked-package validation (relocated from bejson_chunking.js)
  mfdb_validator_is_mfdb132_package,
  mfdb_validator_validate_mfdb132_package,
  mfdb_validator_detect_mfdb_in_chunk,
  // State accessors
  mfdb_validator_reset_state,
  mfdb_validator_has_errors,
  mfdb_validator_has_warnings,
  mfdb_validator_get_errors,
  mfdb_validator_get_warnings,
  mfdb_validator_error_count,
  mfdb_validator_warning_count,
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = exports_;
}
if (typeof window !== 'undefined') {
  window.MFDB_VALIDATOR = exports_;
}