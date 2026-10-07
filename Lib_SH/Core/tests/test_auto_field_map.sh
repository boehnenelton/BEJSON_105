#!/usr/bin/env bash
# Library:        test_auto_field_map.sh
# Family:         Core
# Description:    Tests that the Bash field map is SELF-MAINTAINING (callers never build/refresh it):
#                 parity with Python TestAutoFieldMap, JS bejson_cache.test.js, TS test_auto_field_map.ts.
# Version:        1.0.0
# Date:           2026-10-03
# Author:         Elton Boehnen
# Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
# Format_Creator: Elton Boehnen
# RELATIONAL_ID:  a41f6c0e-93d2-4b75-8e1a-6c2d7f0b5e39
# Release_Version: 300

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
export BEJSON_FM_CACHE_BASE="$WORK/cache"; mkdir -p "$BEJSON_FM_CACHE_BASE"

# jq counting shim: every real jq invocation bumps a counter file.
REAL_JQ="$(command -v jq)"; mkdir -p "$WORK/shim"
printf '#!/usr/bin/env bash\necho x >> "%s/jq_calls"\nexec "%s" "$@"\n' "$WORK" "$REAL_JQ" > "$WORK/shim/jq"; chmod +x "$WORK/shim/jq"
export PATH="$WORK/shim:$PATH"
jq_calls() { [[ -f "$WORK/jq_calls" ]] && wc -l < "$WORK/jq_calls" | tr -d ' ' || echo 0; }

source "$HERE/../lib_bejson_Core_bejson_core.sh"
source "$HERE/../lib_bejson_Core_bejson_chunking.sh" 2>/dev/null
source "$HERE/../lib_bejson_Core_mfdb_core.sh" 2>/dev/null

PASS=0; FAIL=0
eq() { if [[ "$2" == "$3" ]]; then PASS=$((PASS+1)); echo "  ok - $1"; else FAIL=$((FAIL+1)); echo "  FAIL - $1 (got '$2', want '$3')"; fi; }

D104='{"Format":"BEJSON","Format_Version":"104","Format_Creator":"x","Records_Type":["T"],"Fields":[{"name":"id","type":"string"},{"name":"name","type":"string"}],"Values":[["1","a"]]}'
D105='{"Format":"BEJSON","Format_Version":"105","Format_Creator":"x","Records_Type":["T"],"Fields":[{"name":"a","type":"string","field_uuid":"ua"},{"name":"b","type":"string","field_uuid":"ub"}],"Values":[["r1","x","y"]]}'
D105DB='{"Format":"BEJSON","Format_Version":"105db","Format_Creator":"x","Records_Type":["T"],"Fields":[{"name":"a","type":"string","field_uuid":"ua"}],"Values":[["T","r1","x"]]}'

eq "104 lookup, no setup call"          "$(bejson_core_get_field_index "$D104" name)" "1"
eq "104 miss is -1"                     "$(bejson_core_get_field_index "$D104" nope)" "-1"
eq "105 get_field_map returns ROW pos (offset 1)" "$(bejson_core_get_field_map "$D105" | tr '\t\n' '=;')" "a=1;b=2;"
eq "105db offset is 2"                  "$(bejson_core_get_field_map "$D105DB" | tr '\t\n' '=;')" "a=2;"

# The point of the file-backed design: the cache survives $(...) subshells.
bejson_core_get_field_index "$D104" id >/dev/null; before=$(jq_calls)
for _ in 1 2 3 4 5; do v=$(bejson_core_get_field_index "$D104" name); done
eq "repeat lookups across subshells make ZERO jq calls (cache hit)" "$(( $(jq_calls) - before ))" "0"

# Content-addressed: a changed doc can never see an old map.
D104B="${D104/\"id\"/\"zzz\"}"
eq "changed doc is a different key (never stale)" "$(bejson_core_get_field_index "$D104B" zzz)" "0"
eq "old doc still answers from its own entry"      "$(bejson_core_get_field_index "$D104" id)" "0"

# File variant: hit = no jq; rewrite -> rebuilt; atomic_write -> invalidated.
F="$WORK/t.104.bejson"; printf '%s' "$D104" > "$F"
eq "file lookup"                        "$(bejson_core_get_field_index_file "$F" name)" "1"
before=$(jq_calls); v=$(bejson_core_get_field_index_file "$F" name); v=$(bejson_core_get_field_index_file "$F" id)
eq "file cache hit makes ZERO jq calls" "$(( $(jq_calls) - before ))" "0"
sleep 1.1; printf '%s' "${D104/\{\"name\":\"name\"/\{\"name\":\"title\"}" > "$F"
eq "edited file is noticed (new field found)"  "$(bejson_core_get_field_index_file "$F" title)" "1"
eq "edited file is noticed (old field gone)"   "$(bejson_core_get_field_index_file "$F" name)" "-1"
bejson_core_atomic_write "$F" "$D104" false
eq "atomic_write invalidates the file entry"   "$(bejson_core_get_field_index_file "$F" name)" "1"
printf '%s' "$D105" > "$WORK/t.105.bejson"
eq "file variant row column for 105"    "$(bejson_core_get_field_index_file "$WORK/t.105.bejson" b row)" "2"

# Callers wired through the cache
eq "mfdb __mfdb_field_index uses file cache"   "$(__mfdb_field_index "$F" name)" "1"
eq "chunking field_index uses doc cache"       "$(bejson_core_chunking_mfdb_field_index "$D104" name)" "1"
eq "chunking field_index miss prints empty"    "$(bejson_core_chunking_mfdb_field_index "$D104" nope)" ""

# Cache dir is per-shell and removable
bejson_core_clear_field_map_cache
eq "clear removes this shell's cache dir" "$(ls -d "$BEJSON_FM_CACHE_BASE"/bejson_fm_cache.* 2>/dev/null | wc -l | tr -d ' ')" "0"
eq "lookup self-rebuilds after clear"     "$(bejson_core_get_field_index "$D104" name)" "1"

echo "SH field-map tests: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
