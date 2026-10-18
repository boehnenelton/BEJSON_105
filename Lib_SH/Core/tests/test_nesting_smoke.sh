# -----------------------------------------------------------------------------
# Library:         test_nesting_smoke.sh
# Family:          Core
# Module Purpose:  Smoke/behavior tests for the nesting modules (scan, mutate, query, error codes 130-139); written to prove the Core_Nesting -> Core move changed no behavior.
# Architecture:    Standalone script; resolves the nesting modules relative to this file (no absolute paths).
# Format_Scope:    Nested 104 (NOT 104db, NOT MFDB)
# Glossary:        BEJSON 104, 104a and 104db are the three file formats (Format_Version). 104db = ONE file holding 2+ entity types
#                  (Record_Type_Parent discriminator, null-padding). MFDB is NOT a format and NOT 104db: it is a layer made of one 104a manifest
#                  (104a.mfdb.bejson) plus dense 104 entity files linked by Parent_Hierarchy. MFDB-132 = an MFDB packed into one Chunked-104a document.
# Version:         1.2.0
# Release_Version: 300
# Date:            2026-10-16
# Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
# Format_Creator:  Elton Boehnen
# RELATIONAL_ID:   fd840c9d-62dc-46da-8cdb-dfba02c3b80c
# Changelog:
#   1.2.0 (2026-10-16) - Added test: nested document failing validation is reported invalid and not served from another document's cache entry.
#   1.1.0 (2026-10-16) - Bash nesting defects fixed (scan found 0 nested cells; query returned 1 match): the two expected-failure checks are now real checks; query API read from core_nesting.
# -----------------------------------------------------------------------------

_T_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$_T_DIR/../lib_bejson_Core_bejson_core_nesting.sh"

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
check() { if [[ "$2" == "ok" ]]; then PASS=$((PASS+1)); echo "ok   - $1"; else FAIL=$((FAIL+1)); echo "FAIL - $1"; fi; }

cat > "$TMP/o.bejson" <<'JSON'
{"Format":"BEJSON","Format_Version":"104","Format_Creator":"Elton Boehnen","Records_Type":["Order"],"Fields":[{"name":"id","type":"string"},{"name":"items","type":"string"}],"Values":[["o1","{\"Format\":\"BEJSON\",\"Format_Version\":\"104\",\"Format_Creator\":\"Elton Boehnen\",\"Records_Type\":[\"Items\"],\"Fields\":[{\"name\":\"sku\",\"type\":\"string\"},{\"name\":\"qty\",\"type\":\"integer\"}],\"Values\":[[\"a\",1],[\"b\",2]]}"],["o2",null]]}
JSON

R=$(bejson_nesting_scan "$TMP/o.bejson" 0)
check "scan counts (PY/JS/TS: 1 nested found)" "$([[ "$(jq -c '[.nestedFound,.nestedValid,.nestedInvalid,.scannedCells,.maxDepthSeen]' <<< "$R")" == "[1,1,0,4,1]" ]] && echo ok)"
check "query returns 2 matches (PY/JS/TS parity)" "$([[ "$(bejson_nesting_query "$TMP/o.bejson" items | jq length)" == "2" ]] && echo ok)"
# Same schema, different content: a second document must not be served from the first one's cache entry.
INNER_BAD='{"Format":"BEJSON","Format_Version":"104","Format_Creator":"Someone","Records_Type":["Items"],"Fields":[{"name":"sku","type":"string"}],"Values":[["a"]]}'
jq --arg inner "$INNER_BAD" '.Values[0][1] = $inner' "$TMP/o.bejson" > "$TMP/o_bad.bejson"
bejson_nesting_scan "$TMP/o.bejson" 1 >/dev/null
RB=$(bejson_nesting_scan "$TMP/o_bad.bejson" 1)
check "bad Format_Creator in nested cell is invalid, not served from cache" "$([[ "$(jq -c '[.nestedValid,.nestedInvalid]' <<< "$RB")" == "[0,1]" ]] && echo ok)"
check "get_path default" "$([[ "$(bejson_nesting_get_path "$TMP/o.bejson" nope DEF)" == "DEF" ]] && echo ok)"
bejson_nesting_query "$TMP/o.bejson" "bad..path" >/dev/null 2>&1; check "bad path fails" "$([[ $? -ne 0 ]] && echo ok)"
check "error codes unchanged" "$([[ $E_NESTING_INVALID_CELL -eq 130 && $E_NESTING_QUERY_EMPTY_PATH -eq 139 ]] && echo ok)"
echo; echo "$PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
