#!/usr/bin/env bash
# Library:        test_adversarial_remediation.sh
# Family:         Core
# Description:    Regression tests for adversarial-review remediation (SH): non-transactional cascade delete (sibling restrict must leave every file untouched) and 105db column mapping.
# Version:        1.0.0
# Date:           2026-10-09
# Author:         Elton Boehnen
# Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
# Format_Creator: Elton Boehnen
# RELATIONAL_ID:  be5e739e-2874-4feb-b911-95abcb1a02a2
# Release_Version: 300
#
# Run: bash Lib_SH/Core/tests/test_adversarial_remediation.sh

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib_bejson_Core_mfdb_core.sh
source "${SCRIPT_PATH}/../lib_bejson_Core_mfdb_core.sh"

PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); echo "PASS  $1"; }
bad()  { FAIL=$((FAIL+1)); echo "FAIL  $1  ${2:-}"; }
# expect_rc <name> <expected_rc> <cmd...>
expect_rc() {
    local name="$1" want="$2"; shift 2
    local out rc
    out="$("$@" 2>&1)"; rc=$?
    if [[ "$rc" -eq "$want" ]]; then ok "$name"; else bad "$name" "(rc=$rc want=$want) $out"; fi
}
expect_eq() { if [[ "$2" == "$3" ]]; then ok "$1"; else bad "$1" "(got '$2' want '$3')"; fi; }

uid() { cat /proc/sys/kernel/random/uuid; }
count()  { jq '.Values | length' "$DIR/$1.bejson"; }
mcount() { jq --arg n "$1" '.Values[] | select(.[0]==$n) | .[2]' "$MP"; }

# mk_entity <file> <records_type> <fields_json_without_uuid>
mk_entity() {
    local file="$1" rt="$2" fields="$3"
    jq -n --arg rt "$rt" --argjson f "$fields" '
      {Format:"BEJSON",Format_Version:"105",Format_Creator:"Elton Boehnen",Parent_Hierarchy:"mfdb.bejson",Records_Type:[$rt],
       Fields:($f | map(. + {field_uuid: ("fu-" + .name + "-" + $rt)})),Values:[]}' > "$DIR/$file"
}
# build <book_on_delete> <review_on_delete> <note_on_delete>
build() {
    DIR="$(mktemp -d)"; MP="$DIR/mfdb.bejson"
    mk_entity authors.bejson Author '[{"name":"name","type":"string"}]'
    mk_entity books.bejson   Book   "[{\"name\":\"title\",\"type\":\"string\"},{\"name\":\"author_id\",\"type\":\"string\",\"fk_target_entity\":\"authors\",\"fk_on_delete\":\"${1:-restrict}\"}]"
    mk_entity reviews.bejson Review "[{\"name\":\"text\",\"type\":\"string\"},{\"name\":\"book_id\",\"type\":\"string\",\"fk_target_entity\":\"books\",\"fk_on_delete\":\"${2:-restrict}\"}]"
    mk_entity notes.bejson   Note   "[{\"name\":\"text\",\"type\":\"string\"},{\"name\":\"author_id\",\"type\":\"string\",\"fk_target_entity\":\"authors\",\"fk_on_delete\":\"${3:-null}\"}]"
    jq -n '{Format:"BEJSON",Format_Version:"104",Format_Creator:"Elton Boehnen",Parent_Hierarchy:"mfdb.bejson",Records_Type:["Legacy"],Fields:[{name:"x",type:"string"}],Values:[]}' > "$DIR/legacy.bejson"
    jq -n '{Format:"BEJSON",Format_Version:"104a",Format_Creator:"Elton Boehnen",Records_Type:["mfdb"],
      Fields:[{name:"entity_name",type:"string"},{name:"file_path",type:"string"},{name:"record_count",type:"integer"}],
      Values:[["authors","authors.bejson",0],["books","books.bejson",0],["reviews","reviews.bejson",0],["notes","notes.bejson",0],["legacy","legacy.bejson",0]]}' > "$MP"
}
add() { mfdb_core_add_entity_record_105 "$MP" "$1" "$2" 2>/dev/null; }

# ---------------------------------------------------------------- tests
snap() { (cd "$DIR" && sha256sum authors.bejson books.bejson reviews.bejson notes.bejson mfdb.bejson | sha256sum); }

# F2: sibling restrict reached AFTER a cascading sibling must not leave partial deletes
build cascade restrict restrict; mfdb_core_enable_ref_integrity "$MP"
A="$(add authors '["Ada"]')"; add books "[\"B1\",\"$A\"]" >/dev/null; add notes "[\"N1\",\"$A\"]" >/dev/null
BEFORE="$(snap)"
expect_rc "sibling restrict blocks cascade with 44" 44 mfdb_core_delete_entity_record_105 "$MP" authors "$A"
expect_eq "sibling restrict: every file byte-identical" "$(snap)" "$BEFORE"
expect_eq "sibling restrict: counts intact" "$(count authors)-$(count books)-$(count notes)" "1-1-1"

# multi-level cascade still works
build cascade cascade null; mfdb_core_enable_ref_integrity "$MP"
A="$(add authors '["Ada"]')"; B="$(add books "[\"B1\",\"$A\"]")"; add reviews "[\"R1\",\"$B\"]" >/dev/null
expect_rc "cascade chain succeeds" 0 mfdb_core_delete_entity_record_105 "$MP" authors "$A"
expect_eq "cascade chain: all gone" "$(count authors)-$(count books)-$(count reviews)" "0-0-0"

# F1: 105db columns: Fields[0] -> col 0, Fields[i>0] -> col i+1
D='{"Format":"BEJSON","Format_Version":"105db","Format_Creator":"x","Records_Type":["T"],"Fields":[{"name":"Record_Type_Parent","type":"string","field_uuid":"u0"},{"name":"b","type":"string","field_uuid":"u1"},{"name":"c","type":"string","field_uuid":"u2"}],"Values":[["T","r1","x","y"]]}'
expect_eq "105db map" "$(bejson_core_get_field_map "$D" | tr '\t\n' '=;' | tr -d ' ')" "Record_Type_Parent=0;b=2;c=3;"

echo; echo "${PASS} passed, ${FAIL} failed"
[[ "$FAIL" -eq 0 ]]
