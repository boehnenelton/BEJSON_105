#!/usr/bin/env bash
# Library:        test_validator_types.sh
# Family:         Core
# Description:    Field type closed-set tests for the SH validator: "any" and other non-spec types rejected (E_INVALID_FIELDS=6); six spec types accepted.
# Version:        1.0.0
# Date:           2026-10-03
# Author:         Elton Boehnen
# Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
# Format_Creator: Elton Boehnen
# RELATIONAL_ID:  91c7d3f2-4b08-4e65-8a1d-5f3e7b2c0d94
# Release_Version: 300
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_PATH}/../lib_bejson_Core_bejson_validator.sh"
T="$(mktemp -d)"; P=0; F=0
chk() { local t="$1" want="$2" f="$T/d.json"
  jq -n --arg t "$t" '{Format:"BEJSON",Format_Version:"104",Format_Creator:"Elton Boehnen",Records_Type:["R"],Fields:[{name:"a",type:$t}],Values:[]}' > "$f"
  bejson_validator_validate_file "$f"; local rc=$?
  if [[ $rc -eq $want ]]; then P=$((P+1)); else F=$((F+1)); echo "FAIL type='$t' rc=$rc want=$want"; fi; }
for b in any ANY String text ""; do chk "$b" 6; done
for g in string integer number boolean array object; do chk "$g" 0; done
echo "SH validator type tests: $P passed, $F failed"; [[ $F -eq 0 ]]
