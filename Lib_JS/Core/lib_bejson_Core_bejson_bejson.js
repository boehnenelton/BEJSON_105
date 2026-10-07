/**
 * Library:        lib_bejson_Core_bejson_bejson.js
 * Family:         Core
 * Description:    Recursive BEJSON utility for managing BEJSON files within BEJSON.
 * Version:        2.1.0
 * Date:           2026-09-13
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  1d9e6b3a-4f2c-4a81-8e5d-7c3b9f1a6d24
 * Release_Version: 300
 *
 * Changelog:
 *   2.1.0 - AUDIT FIX (H5): removed trailing `export default`/`export {}`
 *           (dead -- no file in this chunk imports it via ESM, and the
 *           referenced bejson_game.js does not exist here). Also replaced
 *           unconditional top-level `window.*` references with a
 *           `_globalCtx` (window || globalThis) guard so the module can be
 *           `require()`-d under Node without throwing before it even
 *           reaches the CommonJS export line. Now loads correctly in both
 *           Node (CJS) and the browser, matching the sibling convention
 *           already fixed in lib_bejson_Core_bejson_chunking.js (v1.8.0).
 */

'use strict';

let BEJSON;
const _hasWindow = typeof window !== 'undefined';
const _globalCtx = _hasWindow ? window : (typeof globalThis !== 'undefined' ? globalThis : {});

(function () {
    _globalCtx.Core = _globalCtx.Core || {};
    _globalCtx.BEJSON_Switch = _globalCtx.BEJSON_Switch || {};
    const BEJSON_Switch = _globalCtx.BEJSON_Switch;

    BEJSON = {
        version: "1.0",

        create104(recordType, fields, values) {
            return {
                Format: "BEJSON",
                Format_Version: "104",
                Format_Creator: "Elton Boehnen",
                Records_Type: [recordType],
                Fields: fields,
                Values: values
            };
        },

        create104a(recordType, fields, values, metadata = {}) {
            return {
                Format: "BEJSON",
                Format_Version: "104a",
                Format_Creator: "Elton Boehnen",
                Records_Type: [recordType],
                ...metadata,
                Fields: fields,
                Values: values
            };
        },

        create104db(recordTypes, fields, values) {
            return {
                Format: "BEJSON",
                Format_Version: "104db",
                Format_Creator: "Elton Boehnen",
                Records_Type: recordTypes,
                Fields: fields,
                Values: values
            };
        },

        getFieldIndex(doc, fieldName) {
            return doc.Fields.findIndex(f => f.name === fieldName);
        },

        query(doc, fieldName, value) {
            const idx = this.getFieldIndex(doc, fieldName);
            if (idx === -1) return [];
            return doc.Values.filter(row => row[idx] === value);
        },

        isValid(doc) {
            return !!(doc && doc.Format === "BEJSON" && ["104", "104a", "104db"].includes(doc.Format_Version) && doc.Format_Creator === "Elton Boehnen");
        }
    };

    // Assign to BEJSON_Switch namespace (Gaming libraries) and global.BEJSON.Core
    BEJSON_Switch.BEJSON = BEJSON;
    _globalCtx.Core.BEJSON = BEJSON;
    _globalCtx.BEJSON = _globalCtx.BEJSON || {};
    _globalCtx.BEJSON.Core = BEJSON;

    // CommonJS export
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = BEJSON;
    }
})();
