/**
 * Library:         lib_bejson_Core_bejson_bejson.js
 * Family:          Core
 * Module Purpose:  Browser facade (window.BEJSON_Switch.BEJSON) with create104 / create104a / create104db factories and a Format_Creator check.
 * Architecture:    Format-level BEJSON layer that works on any BEJSON document (104, 104a, 104db) through positional Fields/Values and the field-map cache. It does not orchestrate MFDB and is not specific to 104db.
 * Format_Scope:    104 | 104a | 104db (generic)
 * Glossary:        BEJSON 104, 104a and 104db are the three file formats (Format_Version). 104db = ONE file holding 2+ entity types
 *                  (Record_Type_Parent discriminator, null-padding). MFDB is NOT a format and NOT 104db: it is a layer made of one 104a manifest
 *                  (104a.mfdb.bejson) plus dense 104 entity files linked by Parent_Hierarchy. MFDB-132 = an MFDB packed into one Chunked-104a document.
 * Version:         2.0.7
 * Release_Version: 300
 * Date:            2026-10-02
 * Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * Format_Creator:  Elton Boehnen
 * RELATIONAL_ID:   471e8ad0-b44d-43d6-b968-24dc4014ce98
 */

'use strict';

let BEJSON;

(function () {
    window.Core = window.Core || {};
    window.BEJSON_Switch = window.BEJSON_Switch || {};
    const BEJSON_Switch = window.BEJSON_Switch;

    BEJSON = {
        version: "1.0",

        /**
         * Factory: new BEJSON 104 document -- exactly ONE record type, strict (no custom top-level keys). Also the format of every MFDB entity file.
         */
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

        /**
         * Factory: new BEJSON 104a document -- one record type plus optional custom headers (metadata). Also the format of the MFDB manifest.
         */
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

        /**
         * Factory: new BEJSON 104db document -- ONE file holding 2+ record types, Record_Type_Parent first, per-field Record_Type_Parent ownership, null-padding. Single-file format; not MFDB.
         */
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

        /**
         * Column index of a field by name (-1 if missing). Linear scan; prefer bejson_core_get_field_map for repeated lookups.
         */
        getFieldIndex(doc, fieldName) {
            return doc.Fields.findIndex(f => f.name === fieldName);
        },

        /**
         * Returns the rows where fieldName equals value.
         */
        query(doc, fieldName, value) {
            const idx = this.getFieldIndex(doc, fieldName);
            if (idx === -1) return [];
            return doc.Values.filter(row => row[idx] === value);
        },

        /**
         * Quick structural check: Format is BEJSON, Format_Version is 104, 104a or 104db, and Fields/Values exist. Not full validation.
         */
        isValid(doc) {
            return !!(doc && doc.Format === "BEJSON" && ["104", "104a", "104db"].includes(doc.Format_Version) && doc.Format_Creator === "Elton Boehnen");
        }
    };

    // Assign to BEJSON_Switch namespace (Gaming libraries) and window.BEJSON.Core
    BEJSON_Switch.BEJSON = BEJSON;
    window.Core.BEJSON = BEJSON;
    window.BEJSON = window.BEJSON || {};
    window.BEJSON.Core = BEJSON;

    // CommonJS export
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = BEJSON;
    }
})();

// ES module export (consumed by bejson_game.js via `import BEJSON from`)
export default BEJSON;
export { BEJSON };