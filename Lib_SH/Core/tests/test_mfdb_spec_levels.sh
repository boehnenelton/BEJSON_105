#!/usr/bin/env bash
# Library:        test_mfdb_spec_levels.sh
# Family:         Core
# Description:    MFDB spec Level 1-3 checks for the SH mfdb_validator: entity Records_Type == manifest entity_name (34), bidirectional manifest<->entity (38), orphan (37), missing Parent_Hierarchy (36), duplicates (35), missing/null required (40/41), missing file (33), entity format, record_count drift = warning only. Mirrors PY tests/test_mfdb_spec_levels_suite.py.
# Version:        1.0.0
# Date:           2026-10-28
# Author:         Elton Boehnen
# Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
# Format_Creator: Elton Boehnen
# RELATIONAL_ID:  65cecf8a-59d3-40fb-8348-08df9d5d8a39
# Release_Version: 300
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_PATH}/../lib_bejson_Core_bejson_validator.sh"
source "${SCRIPT_PATH}/../lib_bejson_Core_mfdb_validator.sh"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT; P=0; F=0
ok() { if [[ "$2" == "$3" ]]; then P=$((P+1)); else F=$((F+1)); echo "FAIL $1: got '$2' want '$3'"; fi; }
# mk <name> : fresh DB dir with manifest (entity 'users', file users.bejson, record_count 1) + one entity file
mk() {
  D="$T/$1"; rm -rf "$D"; mkdir -p "$D"
  jq -n '{Format:"BEJSON",Format_Version:"104a",Format_Creator:"Elton Boehnen",Records_Type:["mfdb"],
    Fields:[{name:"entity_name",type:"string"},{name:"file_path",type:"string"},{name:"record_count",type:"integer"}],
    Values:[["users","users.bejson",1]]}' > "$D/104a.mfdb.bejson"
  jq -n '{Format:"BEJSON",Format_Version:"104",Format_Creator:"Elton Boehnen",Parent_Hierarchy:"104a.mfdb.bejson",Records_Type:["users"],
    Fields:[{name:"name",type:"string"}],Values:[["a"]]}' > "$D/users.bejson"
  M="$D/104a.mfdb.bejson"; E="$D/users.bejson"
}
# run <filter-on-file> <file> ; then validate database; prints "rc|codes|warncount"
chk() {
  mfdb_validator_reset_state; mfdb_validator_validate_database "$M" >/dev/null 2>&1; local rc=$?
  local codes; codes=$(mfdb_validator_get_errors | grep -o 'Message: \[[0-9]*\]' | grep -o '[0-9]*' | sort -u | tr '\n' ',')
  local w; w=$(mfdb_validator_get_warnings | grep -c WARNING)
  echo "$rc|${codes%,}|$w"
}
ed() { jq "$1" "$E" > "$E.t" && mv "$E.t" "$E"; }
mn() { jq "$1" "$M" > "$M.t" && mv "$M.t" "$M"; }

mk a;                                   ok clean              "$(chk)" "0||0"
mk a; ed '.Records_Type=["Users"]';     ok rt_case_34         "$(chk)" "1|34|0"
mk a; ed '.Records_Type=["other"]';     ok rt_wrong_34        "$(chk)" "1|34|0"
mk a; ed '.Records_Type=["users","x"]'; ok rt_two_bejson_invalid "$(chk)" "1||0"
mk a; ed 'del(.Parent_Hierarchy)';      ok no_ph_36           "$(chk)" "1|36|0"
mk a; ed '.Parent_Hierarchy="nope.mfdb.bejson"'; ok orphan_37 "$(chk)" "1|37|0"
mk a; mn '.Values[0][1]="gone.bejson"'; ok missing_file_33   "$(chk)" "1|33|0"
mk a; mn '.Values+=[["users","u2.bejson",0]]'; ok dup_name_35 "$(chk)" "1|33,35|0"
mk a; mn '.Values+=[["u2","users.bejson",1]]'; ok dup_path_35 "$(chk)" "1|34,35|0"
mk a; mn '.Values[0][0]=null';          ok null_41            "$(chk)" "1|41|0"
mk a; mn '.Fields=[.Fields[1],.Fields[2]]|.Values=[["users.bejson",1]]'; ok missing_field_40 "$(chk)" "1|40|0"
mk a; mn '.Values[0][2]=9';             ok count_drift_warn   "$(chk)" "0||1"
mk a; mn '.Records_Type=["x"]';         ok man_rt_32          "$(chk | cut -d'|' -f1)" "1"
mk a; ed '.Format_Version="104a"|.Fields[0].type="string"'; ok entity_104a_31 "$(chk)" "1|31|0"
# bidirectional: second manifest in same dir that does not list users.bejson, entity points at it
mk a; cp "$M" "$D/other.mfdb.bejson"; jq '.Values=[["z","z.bejson",0]]' "$D/other.mfdb.bejson" > "$D/o.t" && mv "$D/o.t" "$D/other.mfdb.bejson"
ed '.Parent_Hierarchy="other.mfdb.bejson"'; ok bidi_38 "$(chk)" "1|38|0"
# 105 entity files are valid MFDB entities; 104a / 104db are not
mk a; U() { printf '%08x-0000-4000-8000-%012x' "$1" "$2"; }
ed ".Format_Version=\"105\"|.Fields[0].field_uuid=\"$(U 1 1)\"|.Values=[[\"$(U 2 2)\",\"a\"]]"; ok entity_105_ok "$(chk)" "0||0"
mk a; ed '.Format_Version="104db"'; ok entity_104db_rejected "$(chk | cut -d'|' -f1)" "1"
for R in Master Slave Standalone; do mk a; mn ".Network_Role=\"$R\""; ok "role_$R" "$(chk)" "0||0"; done
mk a; mn '.Network_Role="RogueNode"';   ok role_invalid_30    "$(chk)" "1|30|0"
echo "passed=$P failed=$F"; [[ $F -eq 0 ]]
