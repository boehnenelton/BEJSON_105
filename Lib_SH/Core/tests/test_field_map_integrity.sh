#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Library:         test_field_map_integrity.sh
# Family:          Core
# Module Purpose:  Regression tests for the field-map cache: forged or persisted maps, stale caches, shared-map isolation, comma/duplicate field names, validator rules, lookup cost. Needs jq.
# Architecture:    Standalone script; resolves the library modules relative to this file (no absolute paths).
# Format_Scope:    104 | 104a | 104db (generic)
# Glossary:        BEJSON 104, 104a and 104db are the three file formats (Format_Version). 104db = ONE file holding 2+ entity types
#                  (Record_Type_Parent discriminator, null-padding). MFDB is NOT a format and NOT 104db: it is a layer made of one 104a manifest
#                  (104a.mfdb.bejson) plus dense 104 entity files linked by Parent_Hierarchy. MFDB-132 = an MFDB packed into one Chunked-104a document.
# Version:         1.0.0
# Release_Version: 300
# Date:            2026-10-15
# Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
# Format_Creator:  Elton Boehnen
# RELATIONAL_ID:   e8f329fe-7778-44eb-be51-783dad863aae
# -----------------------------------------------------------------------------
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=./lib_bejson_Core_bejson_validator.sh
source "$HERE/lib_bejson_Core_bejson_validator.sh"
command -v jq >/dev/null 2>&1 || { echo "SKIP: jq not installed" >&2; exit 2; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
BASE='{"Format":"BEJSON","Format_Version":"104a","Format_Creator":"Elton Boehnen","Records_Type":["T"],"Fields":[{"name":"a","type":"string"},{"name":"b","type":"string"}],"Values":[["x","y"]]}'
echo "$BASE" > "$TMP/ok.json"
echo "$BASE" | jq -c '.Fields[1].name="a"' > "$TMP/dup.json"
echo "$BASE" | jq -c '. + {"_bejson_field_map":{"a":1,"b":0}}' > "$TMP/poison.json"

failed=0
expect() { # name file want_zero(0|1)
    bejson_validator_validate_file "$2" >/dev/null 2>&1; rc=$?
    if { [[ "$3" == 0 ]] && (( rc == 0 )); } || { [[ "$3" == 1 ]] && (( rc != 0 )); }; then echo "PASS $1 (rc=$rc)"
    else echo "FAIL $1 (rc=$rc)" >&2; failed=1; fi
}
expect valid_file_accepted "$TMP/ok.json" 0
expect duplicate_field_names_rejected "$TMP/dup.json" 1
expect persisted_field_map_rejected "$TMP/poison.json" 1
for k in _anything _nesting_field_map; do
    echo "$BASE" | jq -c --arg k "$k" '. + {($k):1}' > "$TMP/u_$k.json"
    expect "underscore_key_${k}_rejected" "$TMP/u_$k.json" 1
done
echo "$BASE" | jq -c '. + {"Custom_Header":1}' > "$TMP/custom.json"
expect custom_header_still_accepted "$TMP/custom.json" 0
exit $failed
