#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Library:         test_mfdb.sh
# Family:          Core
# Module Purpose:  Tests for the MFDB core and validator: create, add/remove records, count sync, validator catches broken manifests, debug logging.
# Architecture:    Standalone script; sources the libraries relative to this file (no absolute paths); each test builds a database in a temp dir. Needs jq.
# Format_Scope:    MFDB only (104a manifest + 104 entity files; NOT 104db)
# Glossary:        BEJSON 104, 104a and 104db are the three file formats (Format_Version). 104db = ONE file holding 2+ entity types
#                  (Record_Type_Parent discriminator, null-padding). MFDB is NOT a format and NOT 104db: it is a layer made of one 104a manifest
#                  (104a.mfdb.bejson) plus dense 104 entity files linked by Parent_Hierarchy. MFDB-132 = an MFDB packed into one Chunked-104a document.
# Version:         1.0.0
# Release_Version: 300
# Date:            2026-10-16
# Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
# Format_Creator:  Elton Boehnen
# RELATIONAL_ID:   3fabc7d9-65d4-46d2-840e-a64c1e2ab9bf
# -----------------------------------------------------------------------------
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
command -v jq >/dev/null 2>&1 || { echo "SKIP: jq not installed" >&2; exit 2; }
# shellcheck source=../lib_bejson_Core_mfdb_core.sh
source "$HERE/lib_bejson_Core_mfdb_core.sh"

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
ENTITIES='[{"name":"User","fields":[{"name":"id","type":"integer"},{"name":"name","type":"string"}]}]'
failed=0
ok()   { echo "PASS $1"; }
bad()  { echo "FAIL $1" >&2; failed=1; }
fails() { ! "$@" >/dev/null 2>&1; }
check() { local name="$1"; shift; if "$@"; then ok "$name"; else bad "$name"; fi; }
fresh() { local d; d="$(mktemp -d "$TMP/db.XXXXXX")"; mfdb_core_create_database "$d" T "" "$ENTITIES" >/dev/null 2>&1; echo "$d"; }
count_of() { jq '.Values | length' "$1"; }

D="$(fresh)"; M="$D/104a.mfdb.bejson"; E="$D/data/user.bejson"
check fresh_manifest_valid mfdb_validator_validate_manifest "$M"

mfdb_core_add_entity_record "$M" User '[1,"a"]' >/dev/null 2>&1
mfdb_core_add_entity_record "$M" User '[2,"b"]' >/dev/null 2>&1
check add_records_and_manifest_count_in_sync test "$(count_of "$E")" = 2 -a "$(jq '.Values[0][3]' "$M")" = 2
mfdb_core_remove_entity_record "$M" User 0 >/dev/null 2>&1
check remove_record_updates_count test "$(count_of "$E")" = 1 -a "$(jq '.Values[0][3]' "$M")" = 1

check unknown_entity_rejected fails mfdb_core_add_entity_record "$M" Nope "[1]"
check non_array_record_rejected fails mfdb_core_add_entity_record "$M" User "{}"
check out_of_range_remove_rejected fails mfdb_core_remove_entity_record "$M" User 99

jq -c '.Values[0][3]=99' "$M" > "$M.tmp" && mv "$M.tmp" "$M"
mfdb_core_sync_all_counts "$M" >/dev/null 2>&1
check sync_repairs_stale_count test "$(jq '.Values[0][3]' "$M")" = 1

BM="$TMP/bad_manifest.json"; jq -c '.Records_Type=["wrong"]' "$M" > "$BM"
check wrong_records_type_caught fails mfdb_validator_validate_manifest "$BM"
check missing_manifest_caught fails mfdb_validator_validate_manifest "$TMP/none.json"
jq -c '. + {"_bejson_field_map":{"entity_name":0}}' "$M" > "$BM"
check persisted_field_map_in_manifest_caught fails mfdb_validator_validate_manifest "$BM"

# Debug logging (regression: SCHEMA_SNAPSHOT piped plain-text names through jq '.[]' and wrote nothing; writes were never logged)
D2="$(fresh)"; M2="$D2/104a.mfdb.bejson"
meta="$(mfdb_core_enable_debug "$M2" 2>/dev/null)"
check debug_enable_writes_schema_snapshot test "$(mfdb_core_get_debug_log "$M2" | jq 'length')" -ge 1
mfdb_core_add_entity_record "$M2" User '[1,"a"]' >/dev/null 2>&1
check debug_logs_add_record test "$(mfdb_core_get_debug_log "$M2" | jq '[.[] | select(.operation=="ADD_RECORD")] | length')" -ge 1
mfdb_core_disable_debug "$M2" >/dev/null 2>&1
n="$(mfdb_core_get_debug_log "$M2" | jq 'length')"
mfdb_core_add_entity_record "$M2" User '[2,"b"]' >/dev/null 2>&1
check debug_off_stops_logging test "$(mfdb_core_get_debug_log "$M2" | jq 'length')" = "$n"
exit $failed
