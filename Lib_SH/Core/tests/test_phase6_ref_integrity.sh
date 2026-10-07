#!/usr/bin/env bash
# Library:        test_phase6_ref_integrity.sh
# Family:         Core
# Description:    Phase 6 (105-series referential integrity) test suite for the SH port: write-time FK checks, restrict/cascade/null delete, cycle guard, droppable check, RI audit and strict_fk. Real sourced libraries, real temp-dir MFDB; no hardcoded absolute paths.
# Version:        1.0.0
# Date:           2026-10-03
# Author:         Elton Boehnen
# Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
# Format_Creator: Elton Boehnen
# RELATIONAL_ID:  d3a85e17-96c2-4b04-a7f1-0e5b2c8d49a6
# Release_Version: 300
#
# Run: bash Lib_SH/Core/tests/test_phase6_ref_integrity.sh

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
build; mfdb_core_enable_ref_integrity "$MP"
expect_eq "enable sets Ref_Integrity header" "$(mfdb_core_is_ref_integrity_enabled "$MP" && echo on || echo off)" on
mfdb_core_disable_ref_integrity "$MP"
expect_eq "disable clears Ref_Integrity header" "$(mfdb_core_is_ref_integrity_enabled "$MP" && echo on || echo off)" off

build; mfdb_core_enable_ref_integrity "$MP"
A="$(add authors '["Ada"]')"
expect_eq "add returns a uuid" "$([[ "$A" =~ ^[0-9a-f-]{36}$ ]] && echo yes || echo no)" yes
add books "[\"B1\",\"$A\"]" >/dev/null
add books '["B2",null]' >/dev/null
expect_rc "add: dangling FK raises 39" 39 mfdb_core_add_entity_record_105 "$MP" books "[\"B3\",\"$(uid)\"]"
expect_eq "add: dangling FK wrote nothing" "$(count books)" 2
expect_eq "add: manifest count synced" "$(mcount books)" 2

build
add books "[\"B\",\"$(uid)\"]" >/dev/null
expect_eq "add: dangling FK accepted when Ref_Integrity off" "$(count books)" 1

build; mfdb_core_enable_ref_integrity "$MP"
A="$(add authors '["Ada"]')"; B="$(add books "[\"B1\",\"$A\"]")"
expect_rc "update: bad FK value raises 39" 39 mfdb_core_update_entity_record_105 "$MP" books "$B" author_id "\"$(uid)\""
expect_rc "update: non-FK field ok" 0 mfdb_core_update_entity_record_105 "$MP" books "$B" title '"Renamed"'
expect_eq "update: value persisted" "$(jq -r '.Values[0][1]' "$DIR/books.bejson")" Renamed
expect_rc "update: unknown record raises 82" 82 mfdb_core_update_entity_record_105 "$MP" books "$(uid)" title '"x"'
expect_rc "update: unknown field raises 54" 54 mfdb_core_update_entity_record_105 "$MP" books "$B" nope '"x"'

build "restrict"; mfdb_core_enable_ref_integrity "$MP"
A="$(add authors '["Ada"]')"; add books "[\"B1\",\"$A\"]" >/dev/null
expect_rc "delete restrict: blocked with 44" 44 mfdb_core_delete_entity_record_105 "$MP" authors "$A"
expect_eq "delete restrict: authors intact" "$(count authors)" 1
expect_eq "delete restrict: books intact" "$(count books)" 1

build restrict restrict null; mfdb_core_enable_ref_integrity "$MP"
A="$(add authors '["Ada"]')"; add notes "[\"n1\",\"$A\"]" >/dev/null
expect_rc "delete null: succeeds" 0 mfdb_core_delete_entity_record_105 "$MP" authors "$A"
expect_eq "delete null: author gone" "$(count authors)" 0
expect_eq "delete null: dependent FK cleared" "$(jq -c '.Values[0][2]' "$DIR/notes.bejson")" null
expect_eq "delete null: dependent row kept" "$(count notes)" 1
expect_eq "delete null: manifest count synced" "$(mcount authors)" 0

build cascade cascade null; mfdb_core_enable_ref_integrity "$MP"
A="$(add authors '["Ada"]')"
B1="$(add books "[\"B1\",\"$A\"]")"; B2="$(add books "[\"B2\",\"$A\"]")"
add reviews "[\"r1\",\"$B1\"]" >/dev/null; add reviews "[\"r2\",\"$B2\"]" >/dev/null
expect_rc "delete cascade: two-level succeeds" 0 mfdb_core_delete_entity_record_105 "$MP" authors "$A"
expect_eq "delete cascade: all gone" "$(count authors)-$(count books)-$(count reviews)" "0-0-0"
expect_eq "delete cascade: manifest counts synced" "$(mcount authors)-$(mcount books)-$(mcount reviews)" "0-0-0"

build cascade restrict null; mfdb_core_enable_ref_integrity "$MP"
A="$(add authors '["Ada"]')"; B="$(add books "[\"B1\",\"$A\"]")"; add reviews "[\"r1\",\"$B\"]" >/dev/null
expect_rc "delete cascade into restricted grandchild: blocked 44" 44 mfdb_core_delete_entity_record_105 "$MP" authors "$A"
expect_eq "cascade-blocked: nothing deleted" "$(count authors)-$(count books)-$(count reviews)" "1-1-1"

# cycle
DIR="$(mktemp -d)"; MP="$DIR/mfdb.bejson"
mk_entity a.bejson A '[{"name":"label","type":"string"},{"name":"b_id","type":"string","fk_target_entity":"b","fk_on_delete":"cascade"}]'
mk_entity b.bejson B '[{"name":"label","type":"string"},{"name":"a_id","type":"string","fk_target_entity":"a","fk_on_delete":"cascade"}]'
jq -n '{Format:"BEJSON",Format_Version:"104a",Format_Creator:"Elton Boehnen",Records_Type:["mfdb"],
  Fields:[{name:"entity_name",type:"string"},{name:"file_path",type:"string"},{name:"record_count",type:"integer"}],
  Values:[["a","a.bejson",0],["b","b.bejson",0]]}' > "$MP"
A1="$(add a '["a1",null]')"; B1="$(add b "[\"b1\",\"$A1\"]")"
mfdb_core_update_entity_record_105 "$MP" a "$A1" b_id "\"$B1\"" 2>/dev/null
mfdb_core_enable_ref_integrity "$MP"
expect_rc "delete cascade cycle raises 45" 45 mfdb_core_delete_entity_record_105 "$MP" a "$A1"

# droppable / find_referencing
build cascade restrict null
A="$(add authors '["Ada"]')"; A2="$(add authors '["Bob"]')"
add books "[\"B1\",\"$A\"]" >/dev/null; add books "[\"B2\",\"$A2\"]" >/dev/null; add notes "[\"n\",\"$A\"]" >/dev/null
expect_eq "droppable lists every referencing row (3)" "$(mfdb_core_check_entity_droppable "$MP" authors | wc -l | tr -d ' ')" 3
expect_eq "droppable: unreferenced entity is safe" "$(mfdb_core_check_entity_droppable "$MP" reviews | wc -l | tr -d ' ')" 0
expect_eq "find_referencing_rows: only matching uuid" "$(mfdb_core_find_referencing_rows "$MP" authors "$A" | cut -f1 | sort | tr '\n' ,)" "books,notes,"

build
expect_rc "104-series entity rejected with 54" 54 mfdb_core_add_entity_record_105 "$MP" legacy '["x"]'

# validator audit + strict_fk
build; A="$(add authors '["Ada"]')"; add books "[\"B1\",\"$A\"]" >/dev/null
expect_rc "audit: sound DB returns 0" 0 mfdb_validator_check_referential_integrity "$MP"
add books "[\"BAD\",\"$(uid)\"]" >/dev/null     # RI off -> dangling row lands on disk
OUT="$(mfdb_validator_check_referential_integrity "$MP")"; RC=$?
expect_eq "audit: dangling FK returns 1" "$RC" 1
expect_eq "audit: reports E_MFDB_FK_UNRESOLVED" "$(cut -f1 <<< "$OUT" | head -1)" E_MFDB_FK_UNRESOLVED
mfdb_validator_reset_state
mfdb_validator_validate_database "$MP" 0 >/dev/null 2>&1; RC0=$?
mfdb_validator_reset_state
mfdb_validator_validate_database "$MP" 1 >/dev/null 2>&1; RC1=$?
expect_eq "strict_fk=0 ignores FK problems" "$RC0" 0
expect_eq "strict_fk=1 now fails on FK problems" "$RC1" 1
expect_eq "strict_fk=1 records an FK: error" "$(mfdb_validator_get_errors | grep -c 'FK:books')" 1

build; jq '.Fields[1].fk_on_delete="explode"' "$DIR/books.bejson" > "$DIR/t" && mv "$DIR/t" "$DIR/books.bejson"
expect_eq "audit: bad fk_on_delete reported (47)" "$(mfdb_validator_check_referential_integrity "$MP" | cut -f1 | head -1)" E_MFDB_FK_INVALID_ON_DELETE
build; jq '.Fields[1].fk_target_entity="ghost"' "$DIR/books.bejson" > "$DIR/t" && mv "$DIR/t" "$DIR/books.bejson"
expect_eq "audit: unregistered target reported (43)" "$(mfdb_validator_check_referential_integrity "$MP" | cut -f1 | head -1)" E_MFDB_FK_TARGET_ENTITY_UNKNOWN

echo; echo "$PASS passed, $FAIL failed"
[[ "$FAIL" -eq 0 ]]
