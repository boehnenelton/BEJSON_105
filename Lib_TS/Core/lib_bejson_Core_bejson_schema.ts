/**
 * Library:         lib_bejson_Core_bejson_schema.ts
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
 * RELATIONAL_ID:   f50ebfb3-2ef6-4058-8f57-1316144c992f
 */

import {
  BEJSONDocument,
  BEJSONField,
  ValidationResult,
} from "./lib_bejson_Core_bejson_types";

export const BEJSONSchema = {
    /**
     * Returns a schema copy of a document: all header keys and Fields, Values emptied. Any BEJSON version.
     */
    /**
     * Extracts the schema (structure) from a BEJSON document.
     */
    extract(doc: BEJSONDocument): BEJSONDocument {
        const schema = JSON.parse(JSON.stringify(doc)) as BEJSONDocument;
        schema.Values = [];
        return schema;
    },

    /**
     * Compares a document's Format_Version and Fields (names, types, order) with a schema. Structure comparison only; it does not apply the 104/104a/104db validity rules.
     */
    /**
     * Validates a BEJSON document against a specific schema.
     */
    validateAgainst(doc: BEJSONDocument, schema: BEJSONDocument): ValidationResult {
        const result: ValidationResult = { valid: true, errors: [], warnings: [] };

        // 1. Version Check
        if (doc.Format_Version !== schema.Format_Version) {
            result.valid = false;
            result.errors.push({
                code: 4,
                message: `Version mismatch: Document is ${doc.Format_Version}, Schema is ${schema.Format_Version}`
            });
        }

        // 2. Records_Type Check
        if (JSON.stringify(doc.Records_Type) !== JSON.stringify(schema.Records_Type)) {
            result.valid = false;
            result.errors.push({
                code: 5,
                message: "Records_Type mismatch: Document types do not match schema types."
            });
        }

        // 3. Fields Check
        const docFields = doc.Fields || [];
        const schFields = schema.Fields || [];

        if (docFields.length !== schFields.length) {
            result.valid = false;
            result.errors.push({
                code: 9,
                message: `Field count mismatch: Document has ${docFields.length}, Schema has ${schFields.length}`
            });
        } else {
            for (let i = 0; i < docFields.length; i++) {
                const df = docFields[i] as BEJSONField;
                const sf = schFields[i] as BEJSONField;

                if (df.name !== sf.name) {
                    result.valid = false;
                    result.errors.push({
                        code: 6,
                        message: `Field name mismatch at index ${i}: expected '${sf.name}', found '${df.name}'`
                    });
                }
                if (df.type !== sf.type) {
                    result.valid = false;
                    result.errors.push({
                        code: 8,
                        message: `Field type mismatch for '${sf.name}': expected '${sf.type}', found '${df.type}'`
                    });
                }
                if (df.Record_Type_Parent !== sf.Record_Type_Parent) {
                    result.valid = false;
                    result.errors.push({
                        code: 11,
                        message: `Record_Type_Parent mismatch for '${sf.name}': expected '${sf.Record_Type_Parent}', found '${df.Record_Type_Parent}'`
                    });
                }
            }
        }

        return result;
    },

    /**
     * {fieldName: field definition} for a schema (definitions, not column indices).
     */
    /**
     * Returns a mapping of field names to their definitions.
     */
    getFieldMap(schema: BEJSONDocument): Record<string, BEJSONField> {
        const map: Record<string, BEJSONField> = {};
        (schema.Fields || []).forEach(f => {
            const field = f as BEJSONField;
            map[field.name] = field;
        });
        return map;
    },

    /**
     * Creates an empty schema document for the given Records_Type and Fields; version defaults to '104a'.
     */
    /**
     * Utility to create a schema object from scratch.
     */
    inferFromData(recordsType: string | string[], fields: any[], version: string = "104a"): BEJSONDocument {
        return {
            Format: "BEJSON",
            Format_Version: version as any,
            Format_Creator: "Elton Boehnen",
            Records_Type: Array.isArray(recordsType) ? recordsType : [recordsType],
            Fields: fields,
            Values: []
        } as BEJSONDocument;
    }
};