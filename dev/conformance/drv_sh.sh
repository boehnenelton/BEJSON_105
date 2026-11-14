#!/usr/bin/env bash
# usage: drv_sh.sh <Lib_SH/Core dir> <corpus> [104]
CORE="$1"; CORPUS="$2"; ONLY104="${3:-}"
source "$CORE/lib_bejson_Core_bejson_validator.sh" 2>/dev/null
source "$CORE/lib_bejson_Core_mfdb_validator.sh" 2>/dev/null
keep(){ [[ -z "$ONLY104" || "$1" == 104* || "$1" == bad_version ]]; }
n=0; bad=0
for CASE_ in $(jq -r 'keys[]' "$CORPUS/validate_expected.json"); do
  keep "$CASE_" || continue; n=$((n+1))
  exp=$(jq -r --arg k "$CASE_" '.[$k].valid' "$CORPUS/validate_expected.json")
  bejson_validator_validate_file "$CORPUS/validate/$CASE_.json" >/dev/null 2>&1; rc=$?
  got=false; [[ $rc -eq 0 ]] && got=true
  if [[ "$got" != "$exp" ]]; then bad=$((bad+1)); echo "DIFF validate $CASE_ got=$got exp=$exp rc=$rc"; fi
done
for CASE_ in $(jq -r 'keys[]' "$CORPUS/mfdb_expected.json"); do
  keep "$CASE_" || continue; n=$((n+1))
  exp=$(jq -r --arg k "$CASE_" '.[$k].valid' "$CORPUS/mfdb_expected.json")
  ew=$(jq -r --arg k "$CASE_" '.[$k].warnings' "$CORPUS/mfdb_expected.json")
  mfdb_validator_validate_database "$CORPUS/mfdb/$CASE_/104a.mfdb.bejson" >/dev/null 2>&1; rc=$?
  got=false; [[ $rc -eq 0 ]] && got=true
  gw=$(mfdb_validator_get_warnings 2>/dev/null | grep -c .)
  p=""
  [[ "$got" != "$exp" ]] && p="valid got=$got exp=$exp rc=$rc"
  a=0; b=0; [[ $gw -gt 0 ]] && a=1; [[ $ew -gt 0 ]] && b=1
  [[ $a -ne $b ]] && p="$p warnings $gw vs $ew"
  gc=$(mfdb_validator_get_errors 2>/dev/null | grep -o 'Message: \[[0-9]*\]' | grep -o '[0-9]*' | sort -u | tr '\n' ' ' | sed 's/ $//')
  ec=$(jq -r --arg k "$CASE_" '.[$k].codes | join(" ")' "$CORPUS/mfdb_expected.json")
  if [[ "$exp" == false && -n "$ec" && "$gc" != "$ec" ]]; then p="$p codes [$gc] vs [$ec]"; fi
  if [[ -n "$p" ]]; then bad=$((bad+1)); echo "DIFF mfdb $CASE_ $p"; fi
done
echo "$n cases, $bad differences"
