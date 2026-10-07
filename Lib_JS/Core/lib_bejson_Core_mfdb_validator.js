/**
 * Library:        lib_bejson_Core_mfdb_validator.js
 * Family:         Core
 * Description:    Bidirectional path and manifest-entity relationship validator.
 *                 Also owns MFDB-132-package validation
 *                 (mfdb_validator_is_mfdb132_package,
 *                 mfdb_validator_validate_mfdb132_package,
 *                 mfdb_validator_detect_mfdb_in_chunk) — relocated here from
 *                 lib_bejson_Core_bejson_chunking.js, which should only own
 *                 packaging/IO, not validation logic. See changelog note
 *                 dated 2026-07-13.
 * Version:        2.1.1
 * Date:           2026-10-03
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  3b8a3acb-fdf0-4042-b5a2-5be99b6ea59c
 * Release_Version: 300
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

function _mReset()                  { _mErrors = []; _mWarnings = []; }
function _mAddError(msg, loc)       { _mErrors.push(   'ERROR'   + (loc ? ` | Location: ${loc}` : '') + ` | Message: ${msg}`); }
function _mAddWarning(msg, loc)     { _mWarnings.push( 'WARNING' + (loc ? ` | Location: ${loc}` : '') + ` | Message: ${msg}`); }
function _mHasErrors()              { return _mErrors.length   > 0; }
function _mHasWarnings()            { return _mWarnings.length > 0; }

// ---------------------------------------------------------------------------
// Internal helpers (also exported for lib_bejson_Core_mfdb_core.js)
// ---------------------------------------------------------------------------

// require('fs') and require('path') are Node.js-only. In browser environments
// these helpers are non-functional. Guard all calls with a Node check so that importing
// this module in a browser context does not throw immediately on function definition.
function _isNode() {
  return typeof process !== 'undefined' && process.versions && !!process.versions.node;
}

// Field-map warm-on-load comes from Core (optional: validator still works standalone).
let _bejsonCore = null;
try { _bejsonCore = (typeof require !== 'undefined') ? require('./lib_bejson_Core_bejson_core.js') : (window.BEJSON || null); } catch (e) { _bejsonCore = null; }

function _loadJson(filePath) {
  if (!_isNode()) {
    throw new MFDBValidationError('_loadJson is only available in Node.js environments', E_MFDB_ENTITY_NOT_FOUND);
  }
  const fs = require('fs');
  const doc = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  return _bejsonCore && _bejsonCore.bejson_core_warm ? _bejsonCore.bejson_core_warm(doc) : doc;
}

function _rowsAsDicts(doc) {
  const names = doc.Fields.map(f => f.name);
  return doc.Values.map(row => Object.fromEntries(names.map((n, i) => [n, row[i]])));
}

function _resolveEntityPath(manifestPath, filePathRel) {
  if (!_isNode()) {
    throw new MFDBValidationError('_resolveEntityPath is only available in Node.js environments', E_MFDB_ENTITY_NOT_FOUND);
  }
  const path = require('path');
  return path.resolve(path.dirname(manifestPath), filePathRel);
}

function _fileExists(filePath) {
  if (!_isNode()) return false;  // In browser: assume non-existent, caller handles
  const fs = require('fs');
  return fs.existsSync(filePath);
}

// ---------------------------------------------------------------------------
// Archive Validation (v1.2 Feature)
// ---------------------------------------------------------------------------

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
    _mAddError(`Records_Type must be ["mfdb"]. Found: ${JSON.stringify(rt)}`, 'Records_Type');
    throw new MFDBValidationError('Bad manifest Records_Type', E_MFDB_MANIFEST_RECORDS_TYPE);
  }

  const fieldNames = (doc.Fields || []).map(f => f.name);
  for (const required of ['entity_name', 'file_path']) {
    if (!fieldNames.includes(required)) {
      _mAddError(`Manifest Fields must include '${required}'`, 'Fields');
      throw new MFDBValidationError(`Missing required field '${required}'`, E_MFDB_MISSING_REQUIRED_FIELD);
    }
  }

  const entries    = _rowsAsDicts(doc);
  const seenNames  = new Set();
  const seenPaths  = new Set();

  for (let i = 0; i < entries.length; i++) {
    const entry      = entries[i];
    const entityName = entry.entity_name;
    const filePath   = entry.file_path;

    if (!entityName) {
      _mAddError(`Record ${i}: entity_name is null or missing`, `Values[${i}]`);
      throw new MFDBValidationError('Null entity_name', E_MFDB_NULL_REQUIRED);
    }
    if (!filePath) {
      _mAddError(`Record ${i}: file_path is null or missing`, `Values[${i}]`);
      throw new MFDBValidationError('Null file_path', E_MFDB_NULL_REQUIRED);
    }
    if (seenNames.has(entityName)) {
      _mAddError(`Duplicate entity_name: '${entityName}'`, `Values[${i}]`);
      throw new MFDBValidationError(`Duplicate entity_name: ${entityName}`, E_MFDB_DUPLICATE_ENTRY);
    }
    seenNames.add(entityName);

    if (seenPaths.has(filePath)) {
      _mAddError(`Duplicate file_path: '${filePath}'`, `Values[${i}]`);
      throw new MFDBValidationError(`Duplicate file_path: ${filePath}`, E_MFDB_DUPLICATE_ENTRY);
    }
    seenPaths.add(filePath);

    const resolved = _resolveEntityPath(manifestPath, filePath);
    if (!_fileExists(resolved)) {
      _mAddError(`Entity file '${filePath}' not found (resolved: ${resolved})`, `Values[${i}]/file_path`);
      throw new MFDBValidationError(`Entity file not found: ${resolved}`, E_MFDB_ENTITY_NOT_FOUND);
    }
  }

  return true;
}

// ---------------------------------------------------------------------------
// Entity File Validation  (Spec §8.2)
// ---------------------------------------------------------------------------

function mfdb_validator_validate_entity_file(entityPath, checkBidirectional = true) {
  const path = require('path');
  _mReset();

  if (!_fileExists(entityPath)) {
    _mAddError(`Entity file not found: ${entityPath}`, 'File System');
    throw new MFDBValidationError(`File not found: ${entityPath}`, E_MFDB_ENTITY_NOT_FOUND);
  }

  try {
    bejson_validator_validate_file(entityPath);
  } catch (exc) {
    _mAddError(`BEJSON 104 validation failed: ${exc.message}`, 'BEJSON Validation');
    throw new MFDBValidationError(exc.message, E_MFDB_NOT_ENTITY_FILE);
  }

  const doc = _loadJson(entityPath);

  if (doc.Format_Version !== '104') {
    _mAddError("Entity file must be Format_Version '104'", 'Format_Version');
    throw new MFDBValidationError('Entity file must be 104', E_MFDB_NOT_ENTITY_FILE);
  }

  const parentHierarchy = doc.Parent_Hierarchy;
  if (!parentHierarchy) {
    _mAddError('Entity file must contain Parent_Hierarchy pointing to the manifest', 'Parent_Hierarchy');
    throw new MFDBValidationError('Missing Parent_Hierarchy', E_MFDB_NO_PARENT_HIERARCHY);
  }

  const entityDir    = path.dirname(path.resolve(entityPath));
  const manifestPath = path.resolve(entityDir, parentHierarchy);

  if (!_fileExists(manifestPath)) {
    _mAddError(
      `Parent_Hierarchy '${parentHierarchy}' resolves to '${manifestPath}' which does not exist`,
      'Parent_Hierarchy',
    );
    throw new MFDBValidationError(`Manifest not found: ${manifestPath}`, E_MFDB_MANIFEST_NOT_FOUND);
  }

  if (!path.basename(manifestPath).endsWith('.mfdb.bejson')) {
    _mAddWarning(
      `Parent_Hierarchy target '${manifestPath}' does not end in '.mfdb.bejson'. Expected: 104a.mfdb.bejson`,
      'Parent_Hierarchy',
    );
  }

  const rt = doc.Records_Type || [];
  if (rt.length !== 1) {
    _mAddError(`Entity file Records_Type must have exactly one entry. Found: ${JSON.stringify(rt)}`, 'Records_Type');
    throw new MFDBValidationError('Entity Records_Type must be single-entry', E_MFDB_NOT_ENTITY_FILE);
  }

  const entityName = rt[0];

  let manifestDoc, entries, manifestEntityNames;
  try {
    manifestDoc        = _loadJson(manifestPath);
    entries            = _rowsAsDicts(manifestDoc);
    manifestEntityNames = entries.map(e => e.entity_name);
  } catch (exc) {
    _mAddError(`Could not read manifest: ${exc.message}`, 'Manifest');
    throw new MFDBValidationError(`Cannot read manifest: ${exc.message}`, E_MFDB_MANIFEST_NOT_FOUND);
  }

  if (!manifestEntityNames.includes(entityName)) {
    _mAddError(
      `Records_Type '${entityName}' does not appear as entity_name in the manifest`,
      'Records_Type vs Manifest',
    );
    throw new MFDBValidationError(
      `Entity '${entityName}' not registered in manifest`, E_MFDB_ENTITY_NAME_MISMATCH,
    );
  }

  if (checkBidirectional) {
    const match = entries.find(e => e.entity_name === entityName);
    if (match) {
      const manifestDir    = path.dirname(path.resolve(manifestPath));
      const fromManifest   = path.resolve(manifestDir, match.file_path || '');
      const thisFile       = path.resolve(entityPath);
      if (fromManifest !== thisFile) {
        _mAddError(
          `Bidirectional check failed for entity '${entityName}': ` +
          `manifest points to '${fromManifest}', but this file is '${thisFile}'`,
          'Bidirectional Path Check',
        );
        throw new MFDBValidationError('Bidirectional path check failed', E_MFDB_BIDIRECTIONAL_FAIL);
      }
    }
  }

  return true;
}

// ---------------------------------------------------------------------------
// Database-Level Validation  (Spec §8.3)
// ---------------------------------------------------------------------------

function mfdb_validator_validate_database(manifestPath, strictFk = false) {
  _mReset();

  try {
    mfdb_validator_validate_manifest(manifestPath);
  } catch (exc) {
    throw exc;
  }

  const manifestDoc = _loadJson(manifestPath);
  const entries     = _rowsAsDicts(manifestDoc);

  const pkMap = {};
  for (const e of entries) {
    if (e.primary_key) pkMap[e.entity_name] = e.primary_key;
  }

  for (const entry of entries) {
    const entityName    = entry.entity_name;
    const filePathRel   = entry.file_path;
    const declaredCount = entry.record_count;

    const resolved = _resolveEntityPath(manifestPath, filePathRel);

    try {
      mfdb_validator_validate_entity_file(resolved, true);
    } catch (exc) {
      _mAddError(`Entity '${entityName}' failed validation: ${exc.message}`, `Entity/${entityName}`);
      throw exc;
    }

    if (declaredCount !== null && declaredCount !== undefined) {
      const edoc        = _loadJson(resolved);
      const actualCount = (edoc.Values || []).length;
      if (actualCount !== declaredCount) {
        _mAddWarning(
          `Entity '${entityName}': manifest declares record_count=${declaredCount}, ` +
          `actual=${actualCount}. Call mfdb_core_sync_all_counts() to correct.`,
          `Entity/${entityName}/record_count`,
        );
      }
    }

    if (strictFk) {
      const edoc    = _loadJson(resolved);
      const fkFields = (edoc.Fields || []).filter(f => f.name.endsWith('_fk')).map(f => f.name);
      for (const fkField of fkFields) {
        const targetFound = Object.entries(pkMap).some(
          ([en, pk]) => pk && (fkField.includes(pk) || fkField.toLowerCase().includes(en.toLowerCase()))
        );
        if (!targetFound) {
          _mAddWarning(
            `Entity '${entityName}': FK field '${fkField}' has no matching primary_key ` +
            `declaration in the manifest. Consider adding a Relationships header (MFDB v1.1).`,
            `Entity/${entityName}/${fkField}`,
          );
        }
      }
    }
  }

  return true;
}

// ---------------------------------------------------------------------------
// Validation report
// ---------------------------------------------------------------------------

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
// Relocated from lib_bejson_Core_bejson_chunking.js (2026-07-13). The
// chunking library still owns bejsonCoreChunkingCreateMfdb132Package/
// bejsonCoreChunkingUnchunkMfdb132Package (packaging and IO), but calls back
// into these functions for the actual validation — validation logic belongs
// in the validator family, not the chunker.

const MFDB_MANIFEST_FILENAME = "104a.mfdb.bejson";

function mfdb_validator_is_mfdb132_package(doc) {
  return (
    doc.Format_Version === "104a" &&
    doc.Schema_Name === "MFDB-132" &&
    doc.Package_Format === "MFDB-Chunked-104a" &&
    !!doc.MFDB_Version &&
    !!doc.DB_Name
  );
}

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

function mfdb_validator_reset_state()      { _mReset(); }
function mfdb_validator_has_errors()       { return _mHasErrors(); }
function mfdb_validator_has_warnings()     { return _mHasWarnings(); }
function mfdb_validator_get_errors()       { return [..._mErrors]; }
function mfdb_validator_get_warnings()     { return [..._mWarnings]; }
function mfdb_validator_error_count()      { return _mErrors.length; }
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
