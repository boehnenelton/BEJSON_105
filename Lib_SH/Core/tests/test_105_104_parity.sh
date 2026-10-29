#!/usr/bin/env bash
# Library:        test_105_104_parity.sh
# Family:         Core
# Description:    105-series parity with 104 in the SH validator (row length, value types, Records_Type count, 105a primitives, 105db rules, uuids, custom headers) plus 104-writer refusal on 105 docs/entities. Mirrors PY tests/test_105_104_parity_suite.py.
# Version:        1.0.0
# Date:           2026-10-27
# Author:         Elton Boehnen
# Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
# Format_Creator: Elton Boehnen
# RELATIONAL_ID:  6c1e8a37-9d42-4f05-b1a8-3e7d5c90f2a1
# Release_Version: 300
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_PATH}/../lib_bejson_Core_bejson_validator.sh"
source "${SCRIPT_PATH}/../lib_bejson_Core_bejson_core.sh"
source "${SCRIPT_PATH}/../lib_bejson_Core_mfdb_core.sh"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT; P=0; F=0
U() { printf '%08x-0000-4000-8000-%012x' "$1" "$2"; }
v() { bejson_validator_validate_file "$1" >/dev/null 2>&1; echo $?; }
ok() { # name got want
  if [[ "$2" == "$3" ]]; then P=$((P+1)); else F=$((F+1)); echo "FAIL $1: got $2 want $3"; fi; }
# base 105 doc; $1 = jq filter applied afterwards
mk105() { jq -n --arg u1 "$(U 1 1)" --arg u2 "$(U 2 2)" --arg r1 "$(U 3 3)" '
  {Format:"BEJSON",Format_Version:"105",Format_Creator:"Elton Boehnen",Records_Type:["T"],
   Fields:[{name:"name",type:"string",field_uuid:$u1},{name:"age",type:"integer",field_uuid:$u2}],
   Values:[[$r1,"a",1]]}' | jq "${1:-.}" > "$T/d.json"; }
mk105db() { jq -n --arg a "$(U 1 1)" --arg b "$(U 2 2)" --arg c "$(U 3 3)" --arg r1 "$(U 4 4)" --arg r2 "$(U 5 5)" '
  {Format:"BEJSON",Format_Version:"105db",Format_Creator:"Elton Boehnen",Records_Type:["D","E"],
   Fields:[{name:"Record_Type_Parent",type:"string",field_uuid:$a},{name:"dept",type:"string",Record_Type_Parent:"D",field_uuid:$b},{name:"emp",type:"string",Record_Type_Parent:"E",field_uuid:$c}],
   Values:[["D",$r1,"eng",null],["E",$r2,null,"al"]]}' | jq "${1:-.}" > "$T/d.json"; }

mk105;                       ok baseline105 "$(v $T/d.json)" 0
mk105 '.Format_Version="105a"'; ok baseline105a "$(v $T/d.json)" 0
mk105db;                     ok baseline105db "$(v $T/d.json)" 0
# row length
mk105 '.Values=[[.Values[0][0],"a"]]';          ok short_row "$(v $T/d.json)" 9
mk105 '.Values=[[.Values[0][0],"a",1,9]]';      ok long_row "$(v $T/d.json)" 9
mk105 '.Values=[["a",1]]';                      ok no_uuid_slot "$(v $T/d.json)" 9
# value types
mk105 '.Values[0][2]="x"';                      ok string_in_int "$(v $T/d.json)" 8
mk105 '.Values[0][2]=true';                     ok bool_in_int "$(v $T/d.json)" 8
mk105 '.Values[0][2]=null';                     ok null_ok "$(v $T/d.json)" 0
mk105 '.Fields[0].type="array"|.Values[0][1]="s"'; ok string_in_array "$(v $T/d.json)" 8
mk105 '.Fields[0].type="object"|.Values[0][1]={"k":1}'; ok object_ok "$(v $T/d.json)" 0
# records type counts
mk105 '.Records_Type=["A","B"]';                ok rt_two_105 "$(v $T/d.json)" 5
mk105 '.Format_Version="105a"|.Records_Type=["A","B"]'; ok rt_two_105a "$(v $T/d.json)" 5
mk105 '.Records_Type=[]';                       ok rt_empty "$(v $T/d.json)" 5
mk105db '.Records_Type=["D"]';                  ok rt_one_105db "$(v $T/d.json)" 5
# 105a primitives
mk105 '.Format_Version="105a"|.Fields[0].type="array"|.Values[0][1]=[1]'; ok a_array "$(v $T/d.json)" 6
mk105 '.Fields[0].type="array"|.Values[0][1]=[1]'; ok plain105_array_ok "$(v $T/d.json)" 0
# 105db rules
mk105db 'del(.Fields[1].Record_Type_Parent)';   ok db_no_owner "$(v $T/d.json)" 11
mk105db '.Fields[0].name="oops"';               ok db_first_field "$(v $T/d.json)" 11
mk105db '.Values[0][0]="Nope"';                 ok db_bad_discriminator "$(v $T/d.json)" 11
mk105db '.Values[0]=[.Values[0][1],"D","eng",null]'; ok db_uuid_col0 "$(v $T/d.json)" 11
mk105db '.Values[0]=["D",.Values[0][1],"eng"]'; ok db_short "$(v $T/d.json)" 9
mk105db '.Values[1][3]=5';                      ok db_type_last_col "$(v $T/d.json)" 8
# uuids
mk105 'del(.Fields[0].field_uuid)';             ok fail_on_switch "$(v $T/d.json)" 6
mk105 '.Fields[1].field_uuid=.Fields[0].field_uuid'; ok dup_field_uuid "$(v $T/d.json)" 6
mk105 '.Values+=[.Values[0]]';                  ok dup_record_uuid "$(v $T/d.json)" 7
mk105 '.Values[0][0]=""';                       ok empty_record_uuid "$(v $T/d.json)" 7
# custom headers
mk105 '.Extra="x"';                             ok custom_hdr_105 "$(v $T/d.json)" 10
mk105 '.Format_Version="105a"|.Extra="x"';      ok custom_hdr_105a_ok "$(v $T/d.json)" 0
mk105db '.Extra="x"';                           ok custom_hdr_105db "$(v $T/d.json)" 10
mk105 '.Parent_Hierarchy="../m.bejson"';        ok parent_hierarchy_ok "$(v $T/d.json)" 0
# 104 unchanged
jq -n '{Format:"BEJSON",Format_Version:"104",Format_Creator:"Elton Boehnen",Records_Type:["T"],Fields:[{name:"a",type:"string"}],Values:[["x"],["y"]]}' > "$T/d.json"
ok v104_ok "$(v $T/d.json)" 0
# 104 adder refuses 105 doc
mk105; doc="$(cat $T/d.json)"
bejson_core_add_record "$doc" '["a",1]' >/dev/null 2>&1; ok add_record_refuses_105 "$?" 81
bejson_core_add_record "$(jq '.Format_Version="104"|.Fields|=map(del(.field_uuid))|.Values=[["a",1]]' <<<"$doc")" '["b",2]' >/dev/null 2>&1; ok add_record_104_works "$?" 0
# MFDB: 104 writer blocked on 105 entity
D="$T/db"; mfdb_core_create_database "$D" Shop "" '[{"name":"Customer","fields":[{"name":"n","type":"string"}]}]' >/dev/null 2>&1
M="$(ls "$D"/*.mfdb.bejson 2>/dev/null | head -1)"
if [[ -n "$M" ]]; then
  E="$(mfdb_core_get_entity_path "$M" Customer 2>/dev/null)"
  jq --arg u "$(U 9 9)" --arg r "$(U 8 8)" '.Format_Version="105"|.Fields[0].field_uuid=$u|.Values=[[$r,"ann"]]' "$E" > "$E.t" && mv "$E.t" "$E"
  before="$(cat "$E")"
  mfdb_core_add_entity_record "$M" Customer '["bob"]' >/dev/null 2>&1; ok mfdb_add_blocked_105 "$?" 54
  ok mfdb_105_file_untouched "$([[ "$(cat "$E")" == "$before" ]] && echo y || echo n)" y
  ok mfdb_discover_105_entity "$(mfdb_core_discover "$E")" entity
else
  F=$((F+1)); echo "FAIL could not build MFDB fixture"
fi
echo "SH 105/104 parity tests: $P passed, $F failed"; [[ $F -eq 0 ]]
