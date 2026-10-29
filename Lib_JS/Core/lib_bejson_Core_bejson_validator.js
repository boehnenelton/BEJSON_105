/**
 * Library:        lib_bejson_Core_bejson_validator.js
 * Family:         Core
 * Description:    Structural integrity checker for positional values and mandatory keys.
 * Version:        3.4.1
 * Date:           2026-10-29
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  f15db41c-7720-44e2-9d3a-1cec28c95570
 * Release_Version: 300
 *
 * Changelog:
 *   3.4.1 - 2026-10-29: error-code fix: JS now returns the same code as Python on the conformance corpus.
 *   3.4.0 - 2026-10-27: Full parity with Python validator 3.4.0:
 *           - Strict Records_Type counts for 105/105a (1) and 105db (2+).
 *           - Strict 105a primitives-only enforcement (reject array/object).
 *           - Strict 105db Record_Type_Parent discriminator and owner checks.
 *           - Robust value type validation rejecting boolean as number/integer.
 *           - Advisory UUIDv4 format warnings (_UUID_V4_RE).
 *           - Shape error flood cap (_MAX_SHAPE_ERRORS = 100).
 *           - Exported validate_bejson() and _bejson_validator_type_problem().
 *   2.2.0 - 2026-10-03: Format_Version 105 / 105a / 105db accepted (parity with
 *           PY validator 3.3.0).
 */

'use strict';

// ---------------------------------------------------------------------------
// Error codes (mirror bash readonly values / Python constants)
// ---------------------------------------------------------------------------
const BEJSON_ERRORS = (typeof require !== 'undefined') 
  ? require('./lib_bejson_Core_bejson_errors.js') 
  : (window.BEJSON_ERRORS || {});

const {
  E_INVALID_JSON,
  E_MISSING_MANDATORY_KEY,
  E_INVALID_FORMAT,
  E_INVALID_VERSION,
  E_INVALID_RECORDS_TYPE,
  E_INVALID_FIELDS,
  E_INVALID_VALUES,
  E_TYPE_MISMATCH,
  E_RECORD_LENGTH_MISMATCH,
  E_RESERVED_KEY_COLLISION,
  E_INVALID_RECORD_TYPE_PARENT,
  E_NULL_VIOLATION,
  E_FILE_NOT_FOUND,
  E_PERMISSION_DENIED,
  E_ATOMIC_WRITE_FAILED
} = BEJSON_ERRORS;

const VALID_VERSIONS    = new Set(['104', '104a', '104db', '105', '105a', '105db']);
const VERSIONS_105      = new Set(['105', '105a', '105db']);
const MANDATORY_KEYS    = ['Format', 'Format_Version', 'Format_Creator', 'Records_Type', 'Fields', 'Values'];
const VALID_FIELD_TYPES = new Set(['string', 'integer', 'number', 'boolean', 'array', 'object']);
const _BASE_VERSION     = { '104': '104', '104a': '104a', '104db': '104db', '105': '104', '105a': '104a', '105db': '104db' };
const _UUID_V4_RE       = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const _MAX_SHAPE_ERRORS = 100;

// ---------------------------------------------------------------------------
// Validation exception
// ---------------------------------------------------------------------------

class BEJSONValidationError extends Error {
  
  constructor(message, code) {
    super(message);
    this.name = 'BEJSONValidationError';
    this.code = code;
  }
}

// ---------------------------------------------------------------------------
// Validation state — mirrors bash globals / Python ValidationState
// ---------------------------------------------------------------------------

class ValidationState {
  constructor() {
    this.errors      = [];
    this.warnings    = [];
    this.currentFile = '';
  }

  
  reset() {
    this.errors      = [];
    this.warnings    = [];
    this.currentFile = '';
  }

  
  addError(message, location = '', context = '') {
    let entry = 'ERROR';
    if (location) entry += ` | Location: ${location}`;
    entry += ` | Message: ${message}`;
    if (context) entry += ` | Context: ${context}`;
    this.errors.push(entry);
  }

  
  addWarning(message, location = '') {
    let entry = 'WARNING';
    if (location) entry += ` | Location: ${location}`;
    entry += ` | Message: ${message}`;
    this.warnings.push(entry);
  }

  
  getErrors() { return [...this.errors]; }

  
  getWarnings() { return [...this.warnings]; }

  
  hasErrors() { return this.errors.length > 0; }

  
  hasWarnings() { return this.warnings.length > 0; }

  
  errorCount() { return this.errors.length; }

  
  warningCount() { return this.warnings.length; }
}

// Module-level default state (mirrors bash global arrays / Python _state)
const _state = new ValidationState();

// ---------------------------------------------------------------------------
// Convenience accessors that operate on the module-level state
// (mirror the exported bash / Python functions)
// ---------------------------------------------------------------------------

function bejson_validator_reset_state() {
  _state.reset();
}

function bejson_validator_get_errors() {
  return _state.getErrors();
}

function bejson_validator_get_warnings() {
  return _state.getWarnings();
}

function bejson_validator_has_errors() {
  return _state.hasErrors();
}

function bejson_validator_has_warnings() {
  return _state.hasWarnings();
}

function bejson_validator_error_count() {
  return _state.errorCount();
}

function bejson_validator_warning_count() {
  return _state.warningCount();
}

// ---------------------------------------------------------------------------
// Dependency check (no-op in JS — JSON is built-in)
// mirrors bejson_validator_check_dependencies
// ---------------------------------------------------------------------------

function bejson_validator_check_dependencies() {
  return true;
}

// ---------------------------------------------------------------------------
// JSON syntax validation
// mirrors bejson_validator_check_json_syntax
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Environment Abstraction Layer
// ---------------------------------------------------------------------------

const IO_PROVIDER = {
  readFile: (path) => {
    if (typeof require !== 'undefined') {
      try {
        const fs = require('fs');
        return fs.readFileSync(path, 'utf8');
      } catch (e) {
        throw new Error(`Node.js fs failed: ${e.message}`);
      }
    }
    throw new Error('File I/O not available in this environment');
  },
  exists: (path) => {
    if (typeof require !== 'undefined') {
      try {
        const fs = require('fs');
        return fs.existsSync(path);
      } catch (e) {
        return false;
      }
    }
    return false;
  }
};

function bejson_validator_check_json_syntax(input, isFile = false) {
  let text;

  if (isFile) {
    if (!IO_PROVIDER.exists(input)) {
      _state.addError(`File not found: ${input}`, 'File System');
      throw new BEJSONValidationError(`File not found: ${input}`, E_FILE_NOT_FOUND);
    }
    try {
      text = IO_PROVIDER.readFile(input);
      _state.currentFile = input;
    } catch (err) {
      _state.addError(`IO Error: ${err.message}`, 'File System');
      throw new BEJSONValidationError(`IO Error: ${err.message}`, E_FILE_NOT_FOUND);
    }
  } else {
    text = input;
  }

  if (typeof text === 'object' && text !== null) {
    return text; // already parsed
  }

  try {
    return JSON.parse(text);
  } catch (err) {
    _state.addError(`Invalid JSON syntax: ${err.message}`, 'JSON Parse');
    throw new BEJSONValidationError(`Invalid JSON syntax: ${err.message}`, E_INVALID_JSON);
  }
}

// ---------------------------------------------------------------------------
// Mandatory key validation
// mirrors bejson_validator_check_mandatory_keys
// ---------------------------------------------------------------------------

function bejson_validator_check_mandatory_keys(doc) {
  for (const key of MANDATORY_KEYS) {
    if (!(key in doc)) {
      _state.addError(`Missing mandatory top-level key: '${key}'`, 'Top-Level Keys');
      throw new BEJSONValidationError(`Missing mandatory key: ${key}`, E_MISSING_MANDATORY_KEY);
    }
  }

  if (doc['Format'] !== 'BEJSON') {
    _state.addError(
      `Invalid 'Format' value: Expected 'BEJSON', got '${doc['Format']}'`,
      'Top-Level Keys/Format',
    );
    throw new BEJSONValidationError('Invalid Format', E_INVALID_FORMAT);
  }

  const version = doc['Format_Version'] ?? '';

  if (!VALID_VERSIONS.has(version)) {
    _state.addError(
      `Invalid 'Format_Version': Expected '104', '104a', '104db', '105', '105a' or '105db', got '${version}'`,
      'Top-Level Keys/Format_Version',
    );
    throw new BEJSONValidationError(`Invalid version: ${version}`, E_INVALID_VERSION);
  }

  if (doc['Format_Creator'] !== 'Elton Boehnen') {
    _state.addError("Invalid 'Format_Creator': Must be 'Elton Boehnen'", 'Top-Level Keys/Format_Creator');
    throw new BEJSONValidationError('Invalid Format_Creator', E_INVALID_FORMAT);
  }

  const checks = [
    ['Records_Type', E_INVALID_RECORDS_TYPE, 'Top-Level Keys/Records_Type'],
    ['Fields',       E_INVALID_FIELDS,       'Top-Level Keys/Fields'],
    ['Values',       E_INVALID_VALUES,       'Top-Level Keys/Values'],
  ];
  for (const [key, code, section] of checks) {
    if (!Array.isArray(doc[key])) {
      _state.addError(`Invalid '${key}': Must be an array`, section);
      throw new BEJSONValidationError(`Invalid ${key}`, code);
    }
  }

  return version;
}

// ---------------------------------------------------------------------------
// Records_Type validation
// mirrors bejson_validator_check_records_type
// ---------------------------------------------------------------------------

function bejson_validator_check_records_type(doc, version) {
  const rt    = doc['Records_Type'];
  if (!Array.isArray(rt)) {
    _state.addError("'Records_Type' must be an array of strings", 'Records_Type');
    throw new BEJSONValidationError('Records_Type not an array', E_INVALID_RECORDS_TYPE);
  }
  const count = rt.length;
  const base = _BASE_VERSION[version] || version;

  if (base === '104' || base === '104a') {
    if (count !== 1 || typeof rt[0] !== 'string') {
      _state.addError(
        `For BEJSON ${version}, 'Records_Type' must contain exactly one string. Found ${count} entries.`,
        'Records_Type',
      );
      throw new BEJSONValidationError(`BEJSON ${version} must have exactly 1 record type. Found ${count}.`, E_INVALID_RECORDS_TYPE);
    }
  } else if (base === '104db') {
    if (count < 2) {
      _state.addError(
        `For BEJSON ${version}, 'Records_Type' must contain two or more unique strings. Found ${count} entries.`,
        'Records_Type',
      );
      throw new BEJSONValidationError(`${version} requires 2+ types`, E_INVALID_RECORDS_TYPE);
    }
    const seen = new Set();
    for (let i = 0; i < rt.length; i++) {
      if (typeof rt[i] !== 'string') {
        _state.addError(`Records_Type[${i}] must be a string`, `Records_Type[${i}]`);
        throw new BEJSONValidationError('Bad Records_Type entry', E_INVALID_RECORDS_TYPE);
      }
      if (seen.has(rt[i])) {
        _state.addError(`Duplicate type '${rt[i]}' found in 'Records_Type'`, 'Records_Type');
        throw new BEJSONValidationError(`Duplicate Records_Type: ${rt[i]}`, E_INVALID_RECORDS_TYPE);
      }
      seen.add(rt[i]);
    }
  }
}

// ---------------------------------------------------------------------------
// Fields structure validation
// mirrors bejson_validator_check_fields_structure
// ---------------------------------------------------------------------------

function bejson_validator_check_fields_structure(doc, version) {
  const fields = doc['Fields'];
  if (!fields || fields.length === 0) {
    _state.addError("'Fields' array cannot be empty", 'Fields Array');
    throw new BEJSONValidationError('Empty Fields', E_INVALID_FIELDS);
  }

  const seenNames = new Set();
  for (let i = 0; i < fields.length; i++) {
    const fieldDef = fields[i];
    if (typeof fieldDef !== 'object' || fieldDef === null || Array.isArray(fieldDef)) {
      _state.addError(`Field at index ${i} must be an object`, `Fields[${i}]`);
      throw new BEJSONValidationError(`Field ${i} not an object`, E_INVALID_FIELDS);
    }

    const name = fieldDef['name'];
    if (typeof name !== 'string') {
      _state.addError(
        `Field at index ${i}: Missing or invalid 'name' (must be string)`,
        `Fields[${i}]`,
      );
      throw new BEJSONValidationError(`Field ${i} bad name`, E_INVALID_FIELDS);
    }

    if (seenNames.has(name)) {
      _state.addError(`Duplicate field name '${name}' found in 'Fields' array`, `Fields[${i}]`);
      throw new BEJSONValidationError(`Duplicate field name: '${name}'`, E_INVALID_FIELDS);
    }
    seenNames.add(name);

    const ftype = fieldDef['type'];
    if (typeof ftype !== 'string' || !VALID_FIELD_TYPES.has(ftype)) {
      _state.addError(
        `Field '${name}' (index ${i}): Invalid type '${ftype}'. Valid: ${[...VALID_FIELD_TYPES].join(', ')}`,
        `Fields[${i}]`,
      );
      throw new BEJSONValidationError(`Field '${name}' (index ${i}) has invalid type '${ftype}'. Must be exactly one of ${JSON.stringify([...VALID_FIELD_TYPES].sort())} (lowercase).`, E_INVALID_FIELDS);
    }

    const base = _BASE_VERSION[version] || version;
    if (base === '104a' && (ftype === 'array' || ftype === 'object')) {
      _state.addError(
        `[${E_INVALID_FIELDS}] ${version} forbids complex type: ${ftype} (Field '${name}' index ${i})`,
        `Fields[${i}]`,
      );
      throw new BEJSONValidationError(`${version} forbids complex type: ${ftype}`, E_INVALID_FIELDS);
    }

    if (base === '104db' && name !== 'Record_Type_Parent' && !fieldDef['Record_Type_Parent']) {
      _state.addError(
        `Field '${name}' missing Record_Type_Parent in ${version}`,
        `Fields[${i}]`,
      );
      throw new BEJSONValidationError(`Field '${name}' missing Record_Type_Parent in ${version}`, E_INVALID_RECORD_TYPE_PARENT);
    }
  }

  return fields.length;
}

// ---------------------------------------------------------------------------
// 104db / 105db Record_Type_Parent validation
// mirrors bejson_validator_check_record_type_parent
// ---------------------------------------------------------------------------

function bejson_validator_check_record_type_parent(doc, version) {
  const base = _BASE_VERSION[version] || version;
  if (base !== '104db') return;
  const fields = doc['Fields'];
  const first  = fields[0] ?? {};
  if (!fields.length || first['name'] !== 'Record_Type_Parent' || first['type'] !== 'string') {
    _state.addError(
      `For BEJSON ${version}, the first field must be {"name": "Record_Type_Parent", "type": "string"}. ` +
      `Found: ${JSON.stringify(first)}`,
      'Fields[0]',
    );
    throw new BEJSONValidationError(`${version} first field must be 'Record_Type_Parent'`, E_INVALID_RECORD_TYPE_PARENT);
  }

  const expectedLen = fields.length + (VERSIONS_105.has(version) ? 1 : 0);
  const validTypes = new Set(doc['Records_Type']);
  for (let i = 0; i < doc['Values'].length; i++) {
    const record = doc['Values'][i];
    if (!Array.isArray(record)) {
      _state.addError(`Values[${i}] must be an array (record)`, `Values[${i}]`);
      throw new BEJSONValidationError(`Bad record at ${i}`, E_INVALID_VALUES);
    }
    if (record.length !== expectedLen) {
      _state.addError(
        `[E_RECORD_LENGTH_MISMATCH] Record at 'Values' index ${i} has ${record.length} elements, expected ${expectedLen} ('Fields' defines ${fields.length} fields` +
        (VERSIONS_105.has(version) ? ` + 1 record_uuid cell for ${version}).` : ').'),
        `Values[${i}]`
      );
      throw new BEJSONValidationError(`Length mismatch at ${i}`, E_RECORD_LENGTH_MISMATCH);
    }
    const rtp = record[0] ?? null;
    if (!rtp) {
      _state.addError(
        `Record at 'Values' index ${i}: 'Record_Type_Parent' is missing or null`,
        `Values[${i}][0]`,
      );
      throw new BEJSONValidationError(`Missing RTP at ${i}`, E_INVALID_RECORD_TYPE_PARENT);
    }
    if (!validTypes.has(rtp)) {
      _state.addError(
        `Record at 'Values' index ${i}: 'Record_Type_Parent' value '${rtp}' ` +
        `does not match any declared type in 'Records_Type'`,
        `Values[${i}][0]`,
      );
      throw new BEJSONValidationError(`Invalid Record_Type_Parent '${rtp}' at row ${i}`, E_INVALID_RECORD_TYPE_PARENT);
    }
  }
}

// ---------------------------------------------------------------------------
// Type matching helper (mirrors Python _bejson_validator_type_problem)
// ---------------------------------------------------------------------------

function _bejson_validator_type_problem(val, ftype) {
  if (val === null || val === undefined) return null;
  if (ftype === 'string') {
    return (typeof val === 'string') ? null : 'expected string';
  }
  if (ftype === 'integer') {
    if (typeof val === 'boolean') return 'expected integer';
    return (typeof val === 'number' && Number.isInteger(val)) ? null : 'expected integer';
  }
  if (ftype === 'number') {
    if (typeof val === 'boolean') return 'expected number, got bool';
    return (typeof val === 'number') ? null : 'expected number';
  }
  if (ftype === 'boolean') {
    return (typeof val === 'boolean') ? null : 'expected boolean';
  }
  if (ftype === 'array') {
    return Array.isArray(val) ? null : 'expected array';
  }
  if (ftype === 'object') {
    return (typeof val === 'object' && !Array.isArray(val)) ? null : 'expected object';
  }
  return null;
}

function bejson_validator_row_col(version, fieldIdx) {
  if (version === '105db') {
    return fieldIdx === 0 ? 0 : fieldIdx + 1;
  }
  return fieldIdx + (VERSIONS_105.has(version) ? 1 : 0);
}

// ---------------------------------------------------------------------------
// 104-series Values validation
// ---------------------------------------------------------------------------

function bejson_validator_check_values(doc, version, fieldsCount) {
  const values = doc['Values'];
  const fields = doc['Fields'];

  for (let i = 0; i < values.length; i++) {
    const record = values[i];
    if (!Array.isArray(record)) {
      _state.addError(`Values[${i}] must be an array (record)`, `Values[${i}]`);
      throw new BEJSONValidationError(`Length mismatch at row ${i}`, E_RECORD_LENGTH_MISMATCH);
    }

    if (record.length !== fieldsCount) {
      _state.addError(
        `Length mismatch at row ${i}`,
        `Values[${i}]`,
      );
      throw new BEJSONValidationError(`Length mismatch at row ${i}`, E_RECORD_LENGTH_MISMATCH);
    }

    const recordType = (version === '104db' && record.length > 0) ? record[0] : null;

    for (let c = 0; c < record.length; c++) {
      const fieldDef  = fields[c];
      const fieldName = fieldDef['name'];
      const fieldType = fieldDef['type'];
      const fieldParent = fieldDef['Record_Type_Parent'] ?? '';

      // 104db applicability: field not for this record type → must be null
      if (version === '104db' && fieldParent && c > 0) {
        if (fieldParent !== recordType) {
          if (record[c] !== null) {
            _state.addError(
              `Record at 'Values' index ${i} (type '${recordType}'), ` +
              `field '${fieldName}' (index ${c}): not applicable to this type; must be null.`,
              `Values[${i}][${c}]`,
            );
            throw new BEJSONValidationError('Null violation', E_NULL_VIOLATION);
          }
          continue;
        }
      }

      const problem = _bejson_validator_type_problem(record[c], fieldType);
      if (problem) {
        _state.addError(
          `Type mismatch at row ${i}, col ${c} (${fieldName}): ${problem}`,
          `Values[${i}][${c}]`,
        );
        throw new BEJSONValidationError(`Type mismatch at row ${i}, col ${c} (${fieldName}): ${problem}`, E_TYPE_MISMATCH);
      }
    }
  }
}

// ---------------------------------------------------------------------------
// 105-series strict integrity & values validation
// ---------------------------------------------------------------------------

function bejson_validator_check_105_strict_integrity(doc) {
  const fields = doc['Fields'] || [];
  if (!fields.length || !fields.every(f => f && Object.prototype.hasOwnProperty.call(f, 'field_uuid'))) {
    const msg = "Format_Version claims 105-series but Fields were never compiled with field_uuid keys -- run bejson_core_upgrade_to_105() before using this file";
    _state.addError(`[E_INVALID_FIELDS] ${msg}`, 'Fields');
    throw new BEJSONValidationError(msg, E_INVALID_FIELDS);
  }

  const seenF = new Set();
  for (let i = 0; i < fields.length; i++) {
    const f = fields[i];
    const u = f['field_uuid'];
    if (typeof u !== 'string' || !u) {
      const msg = `field '${f['name']}' missing a valid field_uuid key`;
      _state.addError(`[E_INVALID_FIELDS] ${msg}`, `Fields[${i}]`);
      throw new BEJSONValidationError(msg, E_INVALID_FIELDS);
    }
    if (seenF.has(u)) {
      const msg = `duplicate field_uuid '${u}'`;
      _state.addError(`[E_INVALID_FIELDS] ${msg}`, `Fields[${i}]`);
      throw new BEJSONValidationError(msg, E_INVALID_FIELDS);
    }
    seenF.add(u);
  }

  const version = doc['Format_Version'];
  const uuidCol = version === '105db' ? 1 : 0;
  const seenR = new Set();
  const values = doc['Values'] || [];

  for (let i = 0; i < values.length; i++) {
    const row = values[i];
    const u = Array.isArray(row) && row.length > uuidCol ? row[uuidCol] : null;
    if (typeof u !== 'string' || !u) {
      const msg = `row ${i} missing a valid record_uuid at index ${uuidCol}`;
      _state.addError(`[E_INVALID_VALUES] ${msg}`, `Values[${i}][${uuidCol}]`);
      throw new BEJSONValidationError(msg, E_INVALID_VALUES);
    }
    if (seenR.has(u)) {
      const msg = `duplicate record_uuid '${u}' at row ${i}`;
      _state.addError(`[E_INVALID_VALUES] ${msg}`, `Values[${i}][${uuidCol}]`);
      throw new BEJSONValidationError(msg, E_INVALID_VALUES);
    }
    seenR.add(u);
  }

  // Check 105 values (row length and types)
  const expectedLen = fields.length + 1;
  let shapeErrorCount = 0;
  let firstErr = null;

  for (let i = 0; i < values.length; i++) {
    if (shapeErrorCount >= _MAX_SHAPE_ERRORS) {
      _state.addError(`[E_RECORD_LENGTH_MISMATCH] further row/type findings suppressed after ${_MAX_SHAPE_ERRORS}`, 'Values');
      break;
    }
    const row = values[i];
    if (!Array.isArray(row) || row.length !== expectedLen) {
      const actual = Array.isArray(row) ? row.length : typeof row;
      const msg = `Length mismatch at row ${i}: expected ${expectedLen} cells (record_uuid + ${expectedLen - 1} fields), got ${actual}`;
      _state.addError(`[E_RECORD_LENGTH_MISMATCH] ${msg}`, `Values[${i}]`);
      if (!firstErr) firstErr = { msg, code: E_RECORD_LENGTH_MISMATCH };
      shapeErrorCount++;
      continue;
    }

    for (let j = 0; j < fields.length; j++) {
      const col = bejson_validator_row_col(version, j);
      const fDef = fields[j];
      const problem = _bejson_validator_type_problem(row[col], fDef['type']);
      if (problem) {
        const msg = `Type mismatch at row ${i}, col ${col} (${fDef['name']}): ${problem}`;
        _state.addError(`[E_TYPE_MISMATCH] ${msg}`, `Values[${i}][${col}]`);
        if (!firstErr) firstErr = { msg, code: E_TYPE_MISMATCH };
        shapeErrorCount++;
        if (shapeErrorCount >= _MAX_SHAPE_ERRORS) break;
      }
    }
  }

  if (firstErr) {
    throw new BEJSONValidationError(firstErr.msg, firstErr.code);
  }

  return true;
}

function bejson_validator_check_105_uuid_format(doc) {
  const fields = doc['Fields'] || [];
  for (const f of fields) {
    if (f && typeof f === 'object') {
      const u = f.field_uuid;
      if (typeof u === 'string' && u && !_UUID_V4_RE.test(u)) {
        _state.addWarning(`field_uuid '${u}' on field '${f.name}' is not a UUIDv4`, 'Fields');
      }
    }
  }
  const uuidCol = doc['Format_Version'] === '105db' ? 1 : 0;
  const values = doc['Values'] || [];
  for (let i = 0; i < values.length; i++) {
    const row = values[i];
    if (Array.isArray(row) && row.length > uuidCol) {
      const u = row[uuidCol];
      if (typeof u === 'string' && u && !_UUID_V4_RE.test(u)) {
        _state.addWarning(`record_uuid '${u}' at row ${i} is not a UUIDv4`, `Values[${i}][${uuidCol}]`);
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Custom headers validation (104a)
// mirrors bejson_validator_check_custom_headers
// ---------------------------------------------------------------------------

const _PASCAL_CASE = /^[A-Z][a-zA-Z0-9_]*$/;

const IN_MEMORY_ONLY_KEYS = new Set(['_nestingFieldMap', '_bejson_field_map_fp']);
function bejson_validator_check_custom_headers(doc, version, persisted = true) {
  const mandatorySet = new Set(MANDATORY_KEYS);
  for (const key of Object.keys(doc)) {
    if (mandatorySet.has(key) || key === 'Parent_Hierarchy' || key === '_bejson_field_map') continue;
    if (key.startsWith('_')) {
      if (persisted || !IN_MEMORY_ONLY_KEYS.has(key)) {
        _state.addError(`Reserved key '${key}' uses the reserved '_' prefix.`, `Top-Level Keys/${key}`);
        throw new BEJSONValidationError(`Reserved key collision: ${key}`, E_RESERVED_KEY_COLLISION);
      }
      continue;
    }
    if (version === '104' || version === '104db' || version === '105' || version === '105db') {
      _state.addError(
        `For BEJSON ${version}, custom top-level key '${key}' is not permitted.`,
        `Top-Level Keys/${key}`,
      );
      throw new BEJSONValidationError(`Unexpected key: ${key}`, E_RESERVED_KEY_COLLISION);
    }
  }
  return true;
}

function bejson_validator_check_field_map_cache(doc, persisted) {
  if (!Object.prototype.hasOwnProperty.call(doc, '_bejson_field_map')) return;
  if (persisted) {
    _state.addError("Reserved key '_bejson_field_map' must not be persisted (in-memory cache only)", "Top-Level Keys/_bejson_field_map");
    throw new BEJSONValidationError("Reserved key '_bejson_field_map' must not be persisted", E_RESERVED_KEY_COLLISION);
  }
  const cached = doc._bejson_field_map;
  const fields = Array.isArray(doc.Fields) ? doc.Fields : [];
  if (cached && typeof cached === "object" && cached.by_name && VERSIONS_105.has(doc.Format_Version)) {
    const ok = Object.keys(cached.by_name).length === fields.length && fields.every((f, i) => f && cached.by_name[f.name] === i);
    if (!ok) {
      _state.addError("In-memory '_bejson_field_map' does not match Fields", "Top-Level Keys/_bejson_field_map");
      throw new BEJSONValidationError("In-memory '_bejson_field_map' does not match Fields", E_RESERVED_KEY_COLLISION);
    }
    return;
  }
  const ok = cached && typeof cached === 'object' && Object.keys(cached).length === fields.length
    && fields.every((f, i) => f && cached[f.name] === i);
  if (!ok) {
    _state.addError("In-memory '_bejson_field_map' does not match Fields (stale or forged)", "Top-Level Keys/_bejson_field_map");
    throw new BEJSONValidationError("In-memory '_bejson_field_map' does not match Fields", E_RESERVED_KEY_COLLISION);
  }
}

// ---------------------------------------------------------------------------
// Main validation entry points
// mirrors bejson_validator_validate_string / bejson_validator_validate_file
// ---------------------------------------------------------------------------

function bejson_validator_validate_string(jsonString) {
  bejson_validator_reset_state();
  const doc          = bejson_validator_check_json_syntax(jsonString, false);
  const version      = bejson_validator_check_mandatory_keys(doc);
  const persisted    = typeof jsonString === 'string';
  bejson_validator_check_field_map_cache(doc, persisted);
  bejson_validator_check_custom_headers(doc, version, persisted);
  bejson_validator_check_records_type(doc, version);
  const fieldsCount  = bejson_validator_check_fields_structure(doc, version);
  bejson_validator_check_record_type_parent(doc, version);
  if (VERSIONS_105.has(version)) {
    bejson_validator_check_105_strict_integrity(doc);
    bejson_validator_check_105_uuid_format(doc);
  } else {
    bejson_validator_check_values(doc, version, fieldsCount);
  }
  return true;
}

function bejson_validator_validate_object(doc) {
  const saved = { errors: _state.errors, warnings: _state.warnings, currentFile: _state.currentFile };
  let valid = true;
  let errors = [];
  let warnings = [];
  try {
    try {
      bejson_validator_validate_string(doc);
    } catch (_) {
      valid = false;
    }
    errors = _state.getErrors();
    warnings = _state.getWarnings();
    if (errors.length) valid = false;
  } finally {
    _state.errors = saved.errors;
    _state.warnings = saved.warnings;
    _state.currentFile = saved.currentFile;
  }
  return { valid, is_valid: valid, errors, warnings };
}

function validate_bejson(inputData, isFile = false) {
  if (isFile) {
    const saved = { errors: _state.errors, warnings: _state.warnings, currentFile: _state.currentFile };
    let valid = true;
    try {
      bejson_validator_validate_file(inputData);
    } catch (_) {
      valid = false;
    }
    const errors = _state.getErrors();
    const warnings = _state.getWarnings();
    const currentFile = _state.currentFile;
    _state.errors = saved.errors;
    _state.warnings = saved.warnings;
    _state.currentFile = saved.currentFile;
    return {
      valid: valid && errors.length === 0,
      is_valid: valid && errors.length === 0,
      errors,
      warnings,
      current_file: currentFile,
    };
  }
  return bejson_validator_validate_object(inputData);
}

function bejson_validator_validate_file(filePath) {
  bejson_validator_reset_state();
  try {
    const text = IO_PROVIDER.readFile(filePath);
    _state.currentFile = filePath;
    return bejson_validator_validate_string(text);
  } catch (err) {
    _state.addError(`IO Error: ${err.message}`, 'File System');
    throw new BEJSONValidationError(`IO Error: ${err.message}`, E_FILE_NOT_FOUND);
  }
}

// ---------------------------------------------------------------------------
// Validation report
// mirrors bejson_validator_get_report
// ---------------------------------------------------------------------------

function bejson_validator_get_report(input, isFile = false) {
  let valid = false;
  try {
    if (isFile) {
      valid = bejson_validator_validate_file(input);
    } else {
      valid = bejson_validator_validate_string(input);
    }
  } catch (_) {
    // errors captured in _state
  }

  const lines = [
    '=== BEJSON Validation Report ===',
    `Status: ${valid ? 'VALID' : 'INVALID'}`,
    '',
    `Errors: ${bejson_validator_error_count()}`,
  ];
  if (bejson_validator_has_errors()) {
    lines.push('---');
    lines.push(...bejson_validator_get_errors());
  }
  lines.push('', `Warnings: ${bejson_validator_warning_count()}`);
  if (bejson_validator_has_warnings()) {
    lines.push('---');
    lines.push(...bejson_validator_get_warnings());
  }

  return lines.join('\n');
}

const ValidatorExports = {
  BEJSONValidationError, ValidationState, VALID_FIELD_TYPES, VALID_VERSIONS, VERSIONS_105,
  bejson_validator_reset_state, bejson_validator_get_errors, bejson_validator_get_warnings,
  bejson_validator_has_errors, bejson_validator_has_warnings,
  bejson_validator_error_count, bejson_validator_warning_count,
  bejson_validator_check_dependencies, bejson_validator_check_json_syntax,
  bejson_validator_check_mandatory_keys, bejson_validator_check_records_type,
  bejson_validator_check_fields_structure, bejson_validator_check_record_type_parent,
  bejson_validator_check_values, bejson_validator_check_105_strict_integrity, bejson_validator_check_105_uuid_format,
  bejson_validator_check_custom_headers, bejson_validator_check_field_map_cache,
  bejson_validator_validate_string, bejson_validator_validate_object, bejson_validator_validate_file,
  validate_bejson,
  bejson_validator_get_report,
  _bejson_validator_type_problem,
  bejson_validator_row_col,
  _MAX_SHAPE_ERRORS,
};
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ValidatorExports;
}
if (typeof window !== 'undefined') {
  window.BEJSON_VALIDATOR = Object.assign(window.BEJSON_VALIDATOR || {}, ValidatorExports);
}
