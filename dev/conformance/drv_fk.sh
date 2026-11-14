#!/usr/bin/env bash
CORE="$1"; CORPUS="$2"
source "$CORE/lib_bejson_Core_bejson_validator.sh" 2>/dev/null; source "$CORE/lib_bejson_Core_mfdb_validator.sh" 2>/dev/null
n=0; bad=0
for CASE_ in $(jq -r 'keys[]' "$CORPUS/fk_expected.json"); do n=$((n+1)); M="$CORPUS/fk/$CASE_/104a.mfdb.bejson"
  a=$(mfdb_validator_check_referential_integrity "$M" 2>/dev/null | awk -F'\t' '{print $1"|"$2}' | sort | jq -R . | jq -sc .)
  mfdb_validator_validate_database "$M" 1 >/dev/null 2>&1; rc=$?; v=false; [[ $rc -eq 0 ]] && v=true
  ea=$(jq -c --arg k "$CASE_" '.[$k].audit' "$CORPUS/fk_expected.json"); ev=$(jq -r --arg k "$CASE_" '.[$k].strict_valid' "$CORPUS/fk_expected.json")
  if [[ "$a" != "$ea" || "$v" != "$ev" ]]; then bad=$((bad+1)); echo "DIFF fk $CASE_ got $a $v vs $ea $ev"; fi
done; echo "$n fk cases, $bad differences"
