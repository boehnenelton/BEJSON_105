#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Library:         lib_bejson_Core_bejson_schema.sh
# Family:          Core
# Module Purpose:  Schema extract, validate-against and infer helpers for BEJSON documents.
# Architecture:    Format-level BEJSON layer that works on any BEJSON document (104, 104a, 104db) through positional Fields/Values and the field-map cache. It does not orchestrate MFDB and is not specific to 104db.
# Format_Scope:    104 | 104a | 104db (generic)
# Glossary:        BEJSON 104, 104a and 104db are the three file formats (Format_Version). 104db = ONE file holding 2+ entity types
#                  (Record_Type_Parent discriminator, null-padding). MFDB is NOT a format and NOT 104db: it is a layer made of one 104a manifest
#                  (104a.mfdb.bejson) plus dense 104 entity files linked by Parent_Hierarchy. MFDB-132 = an MFDB packed into one Chunked-104a document.
# Version:         2.0.3
# Release_Version: 300
# Date:            2026-10-02
# Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
# Format_Creator:  Elton Boehnen
# RELATIONAL_ID:   ca1ea901-63ec-48b2-97a5-8dddbd24544e
# -----------------------------------------------------------------------------

# Echoes a document's schema: header keys and Fields with Values emptied (any BEJSON version).
function bejson_schema_extract() {
    local input_file="$1"
    # Extract all except Values, set Values to []
    jq 'del(.Values) | .Values = []' "$input_file"
}

# Compares a document's Fields with a schema (names, types, order). Structure comparison only; not the 104/104a/104db validity rules.
function bejson_schema_validate_against() {
    local doc_file="$1"
    local schema_file="$2"
    
    # 1. Check Format_Version
    local doc_ver=$(jq -r '.Format_Version' "$doc_file")
    local sch_ver=$(jq -r '.Format_Version' "$schema_file")
    if [ "$doc_ver" != "$sch_ver" ]; then
        echo "FAIL: Version mismatch (Doc: $doc_ver, Schema: $sch_ver)"
        return 1
    fi
    
    # 2. Check Fields count
    local doc_f_count=$(jq '.Fields | length' "$doc_file")
    local sch_f_count=$(jq '.Fields | length' "$schema_file")
    if [ "$doc_f_count" -ne "$sch_f_count" ]; then
        echo "FAIL: Field count mismatch (Doc: $doc_f_count, Schema: $sch_f_count)"
        return 1
    fi
    
    # 3. Deep check fields structure (names and types)
    local doc_f_sig=$(jq -c '.Fields | map({name, type, Record_Type_Parent})' "$doc_file")
    local sch_f_sig=$(jq -c '.Fields | map({name, type, Record_Type_Parent})' "$schema_file")
    if [ "$doc_f_sig" != "$sch_f_sig" ]; then
        echo "FAIL: Field signature mismatch."
        return 1
    fi
    
    echo "SUCCESS: Document matches schema."
    return 0
}

# Builds a schema document from field names/types.
function bejson_schema_infer() {
    local record_type="$1"
    local fields_json="$2" # Expected as JSON array string
    local version="${3:-104a}"
    
    jq -n \
        --arg rt "$record_type" \
        --arg ver "$version" \
        --arg creator "Elton Boehnen" \
        --argjson fields "$fields_json" \
        '{
            Format: "BEJSON",
            Format_Version: $ver,
            Format_Creator: $creator,
            Records_Type: [$rt],
            Fields: $fields,
            Values: []
        }'
}