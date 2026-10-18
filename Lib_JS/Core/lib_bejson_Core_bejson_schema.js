/**
 * Library:         lib_bejson_Core_bejson_schema.js
 * Family:          Core
 * Module Purpose:  Schema extraction and validate-against helpers for BEJSON documents.
 * Architecture:    Format-level BEJSON layer that works on any BEJSON document (104, 104a, 104db) through positional Fields/Values and the field-map cache. It does not orchestrate MFDB and is not specific to 104db.
 * Format_Scope:    104 | 104a | 104db (generic)
 * Glossary:        BEJSON 104, 104a and 104db are the three file formats (Format_Version). 104db = ONE file holding 2+ entity types
 *                  (Record_Type_Parent discriminator, null-padding). MFDB is NOT a format and NOT 104db: it is a layer made of one 104a manifest
 *                  (104a.mfdb.bejson) plus dense 104 entity files linked by Parent_Hierarchy. MFDB-132 = an MFDB packed into one Chunked-104a document.
 * Version:         2.0.4
 * Release_Version: 300
 * Date:            2026-10-02
 * Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * Format_Creator:  Elton Boehnen
 * RELATIONAL_ID:   e42eb63a-4ea9-4b27-9701-16e339c4d068
 */

const BEJSONSchema = {
    /**
     * Extracts the schema (structure) from a BEJSON document: every header key and Fields, with Values emptied.
     * Works for 104, 104a and 104db documents (a 104db schema keeps its Record_Type_Parent columns).
     */
    extract: function(doc) {
        const schema = JSON.parse(JSON.stringify(doc));
        schema.Values = [];
        return schema;
    },

    /**
     * Validates a document against a schema document: same Format_Version, same Fields (names and types, in order).
     * Structure comparison only; it does not apply the 104/104a/104db validity rules (use bejson_validator for those).
     */
    validateAgainst: function(doc, schema) {
        const result = { valid: true, errors: [] };

        // 1. Version Check
        if (doc.Format_Version !== schema.Format_Version) {
            result.valid = false;
            result.errors.push(`Version mismatch: Document is ${doc.Format_Version}, Schema is ${schema.Format_Version}`);
        }

        // 2. Records_Type Check
        if (JSON.stringify(doc.Records_Type) !== JSON.stringify(schema.Records_Type)) {
            result.valid = false;
            result.errors.push("Records_Type mismatch: Document types do not match schema types.");
        }

        // 3. Fields Check
        const docFields = doc.Fields || [];
        const schFields = schema.Fields || [];

        if (docFields.length !== schFields.length) {
            result.valid = false;
            result.errors.push(`Field count mismatch: Document has ${docFields.length}, Schema has ${schFields.length}`);
        } else {
            for (let i = 0; i < docFields.length; i++) {
                const df = docFields[i];
                const sf = schFields[i];

                if (df.name !== sf.name) {
                    result.valid = false;
                    result.errors.push(`Field name mismatch at index ${i}: expected '${sf.name}', found '${df.name}'`);
                }
                if (df.type !== sf.type) {
                    result.valid = false;
                    result.errors.push(`Field type mismatch for '${sf.name}': expected '${sf.type}', found '${df.type}'`);
                }
                if (df.Record_Type_Parent !== sf.Record_Type_Parent) {
                    result.valid = false;
                    result.errors.push(`Record_Type_Parent mismatch for '${sf.name}': expected '${sf.Record_Type_Parent}', found '${df.Record_Type_Parent}'`);
                }
            }
        }

        return result;
    },

    /**
     * Returns {fieldName: fieldDefinition} for a schema (the definition objects, not column indices;
     * for indices use bejson_core_get_field_map).
     */
    getFieldMap: function(schema) {
        const map = {};
        (schema.Fields || []).forEach(f => {
            map[f.name] = f;
        });
        return map;
    },

    /**
     * Creates an empty schema document (no rows) for the given Records_Type and Fields. version defaults to '104a';
     * pass '104db' only with a 2+ type Records_Type and Record_Type_Parent fields.
     */
    inferFromData: function(recordsType, fields, version = "104a") {
        return {
            Format: "BEJSON",
            Format_Version: version,
            Format_Creator: "Elton Boehnen",
            Records_Type: Array.isArray(recordsType) ? recordsType : [recordsType],
            Fields: fields,
            Values: []
        };
    }
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = BEJSONSchema;
}
if (typeof window !== 'undefined') {
    window.BEJSON_SCHEMA = BEJSONSchema;
}