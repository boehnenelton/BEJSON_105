/**
 * Library:        lib_bejson_Core_bejson_schema.js
 * Family:         Core
 * Description:    Schema management and enforcement for JavaScript.
 * Version:        2.0.2
 * Date:           2026-06-20
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  dee0baa4-7e45-44aa-bf3d-c541550b03c8
 * Release_Version: 300
 */

const BEJSONSchema = {
    /**
     * Extracts the schema (structure) from a BEJSON document.
     */
    extract: function(doc) {
        const schema = JSON.parse(JSON.stringify(doc));
        schema.Values = [];
        return schema;
    },

    /**
     * Validates a BEJSON document against a specific schema.
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
     * Returns a mapping of field names to their definitions.
     */
    getFieldMap: function(schema) {
        const map = {};
        (schema.Fields || []).forEach(f => {
            map[f.name] = f;
        });
        return map;
    },

    /**
     * Utility to create a schema object from scratch.
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
