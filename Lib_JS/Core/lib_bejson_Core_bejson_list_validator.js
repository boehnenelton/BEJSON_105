/**
 * Library:        lib_bejson_Core_bejson_list_validator.js
 * Family:         Core
 * Description:    JS implementation of the Hierarchical List Validator.
 * Version:        1.3.0
 * Date:           2026-09-13
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  f4b7e2d9-1a6c-4f83-9e0d-2c8a5f4b7e19
 * Release_Version: 300
 *
 * Changelog:
 *   1.3.0 - AUDIT FIX (H5): removed trailing `export {...}` / `export default`
 *           lines that coexisted with `module.exports`. In Node CJS the
 *           `export` keyword is a SyntaxError; as ESM the `require()` calls
 *           in this file fail. Loaded in neither mode. Now CJS + browser
 *           global only, matching the sibling convention already fixed in
 *           lib_bejson_Core_bejson_chunking.js (v1.8.0).
 */

'use strict';

const StandardValidator = (typeof require !== 'undefined') 
  ? require('./lib_bejson_Core_bejson_validator.js') 
  : (window.BEJSON_VALIDATOR || {});

const ListValidator = {
    validate: function(jsonString) {
        if (!StandardValidator.bejson_validator_validate_string(jsonString)) {
            return { is_valid: false, errors: StandardValidator.bejson_validator_get_errors() };
        }
        const doc = JSON.parse(jsonString);
        if (doc.Format_Version !== '104a') return { is_valid: false, errors: ['Must be 104a'] };
        // R7: single-pass field map instead of two findIndex O(F) scans
        const _fm = {};
        doc.Fields.forEach((f, i) => { _fm[f.name] = i; });
        const idIdx  = _fm['id']        !== undefined ? _fm['id']        : -1;
        const pidIdx = _fm['parent_id'] !== undefined ? _fm['parent_id'] : -1;
        if (idIdx === -1 || pidIdx === -1) return { is_valid: false, errors: ['Missing core fields'] };
        const ids = new Set();
        const parentRefs = new Map();
        for (let row of doc.Values) {
            ids.add(row[idIdx]);
            if (row[pidIdx]) parentRefs.set(row[idIdx], row[pidIdx]);
        }
        for (let [uid, pid] of parentRefs) {
            if (!ids.has(pid)) return { is_valid: false, errors: ['Orphan detected'] };
        }
        return { is_valid: true, errors: [] };
    }
};

// --- Array Field Homogeneity Validator (merged from engine dump) ---
// Genuinely distinct capability from ListValidator.validate() above: checks that every
// element of an array-typed field matches an expected JS type, rather than checking
// hierarchical id/parent_id orphan references. Matches this file's original header
// description ("ensure array homogeneity"), which ListValidator.validate() does not.
const bejson_core = (typeof require !== 'undefined') ? require('./lib_bejson_Core_bejson_core.js') : (window.BEJSON || {});
const { bejson_core_get_field_map } = bejson_core;

function validateListField(doc, fieldName, allowedType) {
    const fieldMap = bejson_core_get_field_map ? bejson_core_get_field_map(doc) : null;
    const idx = fieldMap ? fieldMap[fieldName] : doc.Fields.findIndex(f => f.name === fieldName);
    if (idx === undefined || idx === -1) {
        throw new Error(`Field '${fieldName}' not found in document.`);
    }

    doc.Values.forEach((row, rIdx) => {
        const val = row[idx];
        if (val !== null) {
            if (!Array.isArray(val)) {
                throw new Error(`Row ${rIdx} validation error: Field '${fieldName}' must be an array.`);
            }
            val.forEach((item, iIdx) => {
                if (typeof item !== allowedType) {
                    throw new Error(`Row ${rIdx} list item ${iIdx} type mismatch: expected '${allowedType}', got '${typeof item}'`);
                }
            });
        }
    });

    return true;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ...ListValidator, validateListField };
} else {
    window.BEJSON_LIST_VALIDATOR = window.BEJSON_LIST_VALIDATOR || {};
    Object.assign(window.BEJSON_LIST_VALIDATOR, { ...ListValidator, validateListField });
}
