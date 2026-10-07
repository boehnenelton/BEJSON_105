/**
 * Library:        lib_bejson_Core_bejson_validator.js
 * Family:         Core
 * Description:    Structural integrity checker for positional values and mandatory keys.
 * Version:        2.2.0
 * Date:           2026-10-03
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  67ab03b7-54d3-4303-9316-142bbf4bf595
 * Release_Version: 300
 *
 * FEATURE (2026-10-03, 2.2.0): Format_Version 105 / 105a / 105db accepted (parity with
 * PY validator 3.3.0). 105-series docs run bejson_validator_check_105_strict_integrity
 * (unique field_uuid per field, unique record_uuid at the format-correct column,
 * Fail-on-Switch if a 104 doc was re-headered without compiled UUIDs) and a
 * 105-aware values check (row length = fields + 1 for all 105 versions; record_uuid
 * at column 0, or column 1 for 105db; every other cell type-checked against its
 * Field). 105db discriminator (column 0 = Fields[0]) must be a declared Records_Type. Value-level constraints stay purged (Be25).
 *
 * FIX (2026-10-03): the module had NO exports (no module.exports, no window
 * global), so every consumer (parse.js, list_validator.js, mfdb_validator.js)
 * destructured undefined and JS validation was effectively dead. Now exports
 * the full validator API. Field types remain a closed set: string, integer,
 * number, boolean, array, object -- "any" is rejected (E_INVALID_FIELDS).
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

  if (typeof doc['Format_Creator'] !== 'string') {
    _state.addError("Invalid 'Format_Creator': Must be a string", 'Top-Level Keys/Format_Creator');
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
  const count = rt.length;

  if (version === '104' || version === '104a') {
    if (count !== 1 || typeof rt[0] !== 'string') {
      _state.addError(
        `For BEJSON ${version}, 'Records_Type' must contain exactly one string. Found ${count} entries.`,
        'Records_Type',
      );
      throw new BEJSONValidationError('Bad Records_Type', E_INVALID_RECORDS_TYPE);
    }
  } else if (version === '104db') {
    if (count < 2) {
      _state.addError(
        `For BEJSON 104db, 'Records_Type' must contain two or more unique strings. Found ${count} entries.`,
        'Records_Type',
      );
      throw new BEJSONValidationError('Bad Records_Type', E_INVALID_RECORDS_TYPE);
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
      throw new BEJSONValidationError(`Duplicate field: ${name}`, E_INVALID_FIELDS);
    }
    seenNames.add(name);

    const ftype = fieldDef['type'];
    if (typeof ftype !== 'string' || !VALID_FIELD_TYPES.has(ftype)) {
      _state.addError(
        `Field '${name}' (index ${i}): Invalid type '${ftype}'. Valid: ${[...VALID_FIELD_TYPES].join(', ')}`,
        `Fields[${i}]`,
      );
      throw new BEJSONValidationError(`Field ${name} invalid type`, E_INVALID_FIELDS);
    }

    if (version === '104a' && (ftype === 'array' || ftype === 'object')) {
      _state.addError(
        `Field '${name}' (index ${i}): Type '${ftype}' not allowed in 104a.`,
        `Fields[${i}]`,
      );
      throw new BEJSONValidationError(`Field ${name} disallowed type for 104a`, E_INVALID_FIELDS);
    }
  }

  return fields.length;
}

// ---------------------------------------------------------------------------
// 104db Record_Type_Parent validation
// mirrors bejson_validator_check_record_type_parent
// ---------------------------------------------------------------------------

function bejson_validator_check_record_type_parent(doc) {
  const fields = doc['Fields'];
  const first  = fields[0] ?? {};
  if (!fields.length || first['name'] !== 'Record_Type_Parent' || first['type'] !== 'string') {
    _state.addError(
      `For BEJSON 104db, the first field must be {"name": "Record_Type_Parent", "type": "string"}. ` +
      `Found: ${JSON.stringify(first)}`,
      'Fields[0]',
    );
    throw new BEJSONValidationError('Bad Record_Type_Parent field', E_INVALID_RECORD_TYPE_PARENT);
  }

  const validTypes = new Set(doc['Records_Type']);
  for (let i = 0; i < doc['Values'].length; i++) {
    const record = doc['Values'][i];
    if (!Array.isArray(record)) {
      _state.addError(`Values[${i}] must be an array (record)`, `Values[${i}]`);
      throw new BEJSONValidationError(`Bad record at ${i}`, E_INVALID_VALUES);
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
      throw new BEJSONValidationError(`Invalid RTP '${rtp}' at ${i}`, E_INVALID_RECORD_TYPE_PARENT);
    }
  }
}

// ---------------------------------------------------------------------------
// Values validation
// mirrors bejson_validator_check_values
// ---------------------------------------------------------------------------

function _jsonType(value) {
  if (value === null)             return 'null';
  if (typeof value === 'boolean') return 'boolean';
  if (Number.isInteger(value))    return 'integer';
  if (typeof value === 'number')  return 'number';
  if (typeof value === 'string')  return 'string';
  if (Array.isArray(value))       return 'array';
  if (typeof value === 'object')  return 'object';
  return 'unknown';
}

function bejson_validator_check_values(doc, version, fieldsCount) {
  const values = doc['Values'];
  const fields = doc['Fields'];
  // 105-series rows carry ONE extra cell: record_uuid. It sits at column 0 for
  // 105/105a and column 1 for 105db (after the discriminator). In 105db the
  // discriminator is Fields[0] (Record_Type_Parent), exactly as the PY upgrader
  // produces: [disc, uuid, ...rest]. So row length = fields + 1 for every 105 version.
  const is105 = VERSIONS_105.has(version);
  const uuidCol = version === '105db' ? 1 : 0;
  const offset = is105 ? 1 : 0;
  const expectedLen = fieldsCount + offset;

  for (let i = 0; i < values.length; i++) {
    const record = values[i];
    if (!Array.isArray(record)) {
      _state.addError(`Values[${i}] must be an array (record)`, `Values[${i}]`);
      throw new BEJSONValidationError(`Bad record at ${i}`, E_INVALID_VALUES);
    }

    if (record.length !== expectedLen) {
      _state.addError(
        `Record at 'Values' index ${i} has ${record.length} elements, ` +
        `but 'Fields' defines ${fieldsCount} fields` +
        (is105 ? ` (+1 record_uuid cell for ${version}).` : '.'),
        `Values[${i}]`,
      );
      throw new BEJSONValidationError(`Length mismatch at ${i}`, E_RECORD_LENGTH_MISMATCH);
    }

    if (version === '105db') {
      const disc = record[0];
      if (typeof disc !== 'string' || !doc['Records_Type'].includes(disc)) {
        _state.addError(
          `Record at 'Values' index ${i}: 105db discriminator '${disc}' does not match any declared type in 'Records_Type'`,
          `Values[${i}][0]`,
        );
        throw new BEJSONValidationError(`Invalid discriminator at ${i}`, E_INVALID_RECORD_TYPE_PARENT);
      }
    }

    const recordType = (version === '104db' && record.length > 0) ? record[0] : null;

    for (let c = 0; c < record.length; c++) {
      if (is105 && c === uuidCol) continue;          // record_uuid cell: checked by strict integrity
      const j         = (is105 && c > uuidCol) ? c - 1 : c;   // Fields index
      const value     = record[c];
      const fieldDef  = fields[j];
      const fieldName = fieldDef['name'];
      const fieldType = fieldDef['type'];
      const fieldParent = fieldDef['Record_Type_Parent'] ?? '';

      // 104db applicability: field not for this record type → must be null
      if (version === '104db' && fieldParent && j > 0) {
        if (fieldParent !== recordType) {
          if (value !== null) {
            _state.addError(
              `Record at 'Values' index ${i} (type '${recordType}'), ` +
              `field '${fieldName}' (index ${j}): not applicable to this type; must be null.`,
              `Values[${i}][${c}]`,
            );
            throw new BEJSONValidationError('Null violation', E_NULL_VIOLATION);
          }
          continue;
        }
      }

      if (value === null) continue;

      const vtype = _jsonType(value);
      let typeValid = false;

      switch (fieldType) {
        case 'string':
          typeValid = typeof value === 'string';
          break;
        case 'integer':
          typeValid = Number.isInteger(value) && typeof value !== 'boolean';
          break;
        case 'number':
          typeValid = typeof value === 'number' && typeof value !== 'boolean';
          break;
        case 'boolean':
          typeValid = typeof value === 'boolean';
          break;
        case 'array':
          typeValid = Array.isArray(value);
          break;
        case 'object':
          typeValid = typeof value === 'object' && !Array.isArray(value);
          break;
      }

      if (!typeValid) {
        _state.addError(
          `Record at 'Values' index ${i}, field '${fieldName}' (index ${j}): ` +
          `Value '${value}' is of type '${vtype}', but 'Fields' defines type '${fieldType}'.`,
          `Values[${i}][${c}]`,
        );
        throw new BEJSONValidationError(`Type mismatch at [${i}][${c}]`, E_TYPE_MISMATCH);
      }
    }
  }
}

// 105-series strict integrity (mirrors PY bejson_validator_check_105_strict_integrity).
// Throws on the first problem, like the other JS checks. Returns true if sound.
function bejson_validator_check_105_strict_integrity(doc) {
  const fields = doc['Fields'];
  if (!fields.length || !fields.every(f => f && Object.prototype.hasOwnProperty.call(f, 'field_uuid'))) {
    _state.addError(
      "Format_Version claims 105-series but Fields were never compiled with field_uuid keys -- run upgrade-to-105 before using this file",
      'Fields',
    );
    throw new BEJSONValidationError('105 Fields lack field_uuid (Fail-on-Switch)', E_INVALID_FIELDS);
  }
  const seenF = new Set();
  fields.forEach((f, i) => {
    const u = f['field_uuid'];
    if (typeof u !== 'string' || !u) {
      _state.addError(`field '${f['name']}' missing a valid field_uuid key`, `Fields[${i}]`);
      throw new BEJSONValidationError(`Bad field_uuid at ${i}`, E_INVALID_FIELDS);
    }
    if (seenF.has(u)) {
      _state.addError(`duplicate field_uuid '${u}'`, `Fields[${i}]`);
      throw new BEJSONValidationError(`Duplicate field_uuid '${u}'`, E_INVALID_FIELDS);
    }
    seenF.add(u);
  });

  const uuidCol = doc['Format_Version'] === '105db' ? 1 : 0;
  const seenR = new Set();
  doc['Values'].forEach((row, i) => {
    const u = Array.isArray(row) && row.length > uuidCol ? row[uuidCol] : null;
    if (typeof u !== 'string' || !u) {
      _state.addError(`row ${i} missing a valid record_uuid at index ${uuidCol}`, `Values[${i}][${uuidCol}]`);
      throw new BEJSONValidationError(`Bad record_uuid at row ${i}`, E_INVALID_VALUES);
    }
    if (seenR.has(u)) {
      _state.addError(`duplicate record_uuid '${u}' at row ${i}`, `Values[${i}][${uuidCol}]`);
      throw new BEJSONValidationError(`Duplicate record_uuid at row ${i}`, E_INVALID_VALUES);
    }
    seenR.add(u);
  });
  return true;
}

// ---------------------------------------------------------------------------
// Custom headers validation (104a)
// mirrors bejson_validator_check_custom_headers
// ---------------------------------------------------------------------------

const _PASCAL_CASE = /^[A-Z][a-zA-Z0-9_]*$/;

function bejson_validator_check_custom_headers(doc, version) {
  const mandatorySet = new Set(MANDATORY_KEYS);
  for (const key of Object.keys(doc)) {
    if (mandatorySet.has(key) || key === 'Parent_Hierarchy') continue;
    if (version === '104' || version === '104db') {
      _state.addError(
        `For BEJSON ${version}, custom top-level key '${key}' is not permitted.`,
        `Top-Level Keys/${key}`,
      );
      throw new BEJSONValidationError(`Unexpected key: ${key}`, E_RESERVED_KEY_COLLISION);
    }
    // 104a: Custom headers allowed, no strict naming enforcement
    // Audit 2 Finding: Removed PascalCase warning to avoid conflict with 104db rigidity.
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
  bejson_validator_check_custom_headers(doc, version);
  bejson_validator_check_records_type(doc, version);
  const fieldsCount  = bejson_validator_check_fields_structure(doc, version);
  if (version === '104db') bejson_validator_check_record_type_parent(doc);
  if (VERSIONS_105.has(version)) bejson_validator_check_105_strict_integrity(doc);
  bejson_validator_check_values(doc, version, fieldsCount);
  return true;
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
  bejson_validator_check_values, bejson_validator_check_105_strict_integrity, bejson_validator_check_custom_headers,
  bejson_validator_validate_string, bejson_validator_validate_file,
  bejson_validator_get_report,
};
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ValidatorExports;
}
if (typeof window !== 'undefined') {
  window.BEJSON_VALIDATOR = Object.assign(window.BEJSON_VALIDATOR || {}, ValidatorExports);
}
