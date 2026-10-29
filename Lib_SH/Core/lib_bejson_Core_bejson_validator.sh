# Library:        lib_bejson_Core_bejson_validator.sh
# Family:         Core
# Description:    Structural integrity checker for positional values and mandatory keys.
# Version:        2.5.0
# Date:           2026-10-27
# Author:         Elton Boehnen
# Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
# Format_Creator: Elton Boehnen
# RELATIONAL_ID:  3eebff4c-5350-4af0-be78-38bdc9ea18cc
# Release_Version: 300
#
# Changelog:
#   2.5.0 - 2026-10-27: version rules now apply to 104/104a/104db too (single jq pass shared with 105-series):
#           custom-header rule, Records_Type count, 104a primitives-only, 104db Record_Type_Parent rules,
#           per-cell value types. Function renamed __bejson_validator_check_version_rules.
#   2.4.0 - 2026-10-27: 105-series parity with 104 (port of PY validator 3.4.0).
#           105/105a/105db files now ALSO get: custom-header rule (105/105db forbid),
#           Records_Type count (105/105a exactly 1, 105db 2+), 105a primitives-only,
#           105db Record_Type_Parent rules (first field, per-field owner, row
#           discriminator in Records_Type at col 0), field_uuid present+unique,
#           record_uuid present+unique at the right column, Fail-on-Switch, and
#           per-cell value types (offset-aware). The first failure's detail is left in
#           BEJSON_VALIDATOR_LAST_ERROR. 104/104a/104db behaviour is UNCHANGED (SH has
#           never run Records_Type/value-type checks on 104-series; not added here).
#           Not ported: UUIDv4-format advisory warnings (no warning channel in SH).
#   2.3.0 - 2026-10-03: field-type check added (parity with PY/JS/TS). SH had NO
#           type validation, so Fields[].type values such as "any" were accepted.
#           Types are a closed set: string, integer, number, boolean, array,
#           object. Anything else -> E_INVALID_FIELDS.
#   2.2.0 - BUG FIX (2026-10-03): record-length check was 105-blind. It required
#           every row to have exactly len(Fields) cells, but every 105-series row
#           carries one extra record_uuid cell (col 0 for 105/105a, col 1 for 105db
#           after the discriminator, which is Fields[0]) so EVERY populated
#           105-series file failed with
#           E_RECORD_LENGTH_MISMATCH -- which also made
#           mfdb_validator_validate_database fail on any 105 MFDB. Expected row
#           length is now len(Fields) + 1 for 105-series. 104/104a/104db
#           behaviour is unchanged (offset 0). NOTE: SH still does not validate
#           105-specific integrity (field_uuid / record_uuid uniqueness); PY and
#           TS do. Tracked as follow-up.
#   2.1.0 - Step 2 (1.32 finalization): removed local re-declarations of legacy
#           E_VAL_* aliases and migrated all 5 return sites to primary unified
#           codes (E_INVALID_JSON, E_MISSING_MANDATORY_KEY, E_INVALID_FORMAT,
#           E_INVALID_FORMAT_CREATOR, E_RECORD_LENGTH_MISMATCH). Aliases no
#           longer exist in lib_bejson_Core_bejson_errors.sh.

set -o pipefail

# Source the error registry (assumes same directory)
_VAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$_VAL_DIR/lib_bejson_Core_bejson_errors.sh" ]]; then
    # shellcheck source=./lib_bejson_Core_bejson_errors.sh
    source "$_VAL_DIR/lib_bejson_Core_bejson_errors.sh"
fi

#-------------------------------------------------------------------------------
# CORE VALIDATION
#-------------------------------------------------------------------------------

bejson_validator_check_dependencies() {
    if ! command -v jq >/dev/null 2>&1; then
        echo "ERROR: jq is required for BEJSON validation" >&2
        return 1
    fi
    local jq_ver
    jq_ver=$(jq --version | sed 's/jq-//')
    local jq_major jq_minor
    jq_major="${jq_ver%%.*}"
    jq_minor="${jq_ver#*.}"; jq_minor="${jq_minor%%.*}"
    if [[ "$jq_major" -lt 1 ]] || { [[ "$jq_major" -eq 1 ]] && [[ "$jq_minor" -lt 6 ]]; }; then
        echo "ERROR: jq >= 1.6 is required. Found: $jq_ver" >&2
        return 1
    fi
    return 0
}

bejson_validator_validate_file() {
    local file_path="$1"
    if [[ ! -f "$file_path" ]]; then
        echo "ERROR: File not found: $file_path" >&2
        return 1
    fi

    # 1. Basic JSON check
    if ! jq . "$file_path" >/dev/null 2>&1; then
        return $E_INVALID_JSON
    fi

    # 2. Mandatory Keys — exact presence check via jq (FIX SH1)
    #    Using =~ on a joined key string caused substring collisions:
    #    "Format" matched inside "Format_Creator", making missing bare "Format" go undetected.
    for k in Format Format_Version Format_Creator Records_Type Fields Values; do
        if ! jq -e --arg key "$k" 'has($key)' "$file_path" >/dev/null 2>&1; then
            return $E_MISSING_MANDATORY_KEY
        fi
    done

    # 3. Format & Creator check
    local fmt creator
    fmt=$(jq -r '.Format' "$file_path")
    creator=$(jq -r '.Format_Creator' "$file_path")
    [[ "$fmt"     != "BEJSON"        ]] && return $E_INVALID_FORMAT
    [[ "$creator" != "Elton Boehnen" ]] && return $E_INVALID_FORMAT_CREATOR

    # 3b. Field type check (closed set; "any" is NOT valid)
    local bad_types
    bad_types=$(jq -r '[.Fields[] | .type | select(IN("string","integer","number","boolean","array","object") | not)] | length' "$file_path")
    if [[ "$bad_types" -gt 0 ]]; then
        return $E_INVALID_FIELDS
    fi

    # 4. Records Length check
    local field_count bad_records
    field_count=$(jq '.Fields | length' "$file_path")
    local row_offset
    row_offset=$(jq -r '.Format_Version | if . == "105" or . == "105a" or . == "105db" then 1 else 0 end' "$file_path")
    bad_records=$(jq --argjson fc "$field_count" --argjson off "$row_offset" '.Values | map(select(length != ($fc + $off))) | length' "$file_path")
    if [[ "$bad_records" -gt 0 ]]; then
        return $E_RECORD_LENGTH_MISMATCH
    fi

    # 4b. The '_' prefix is reserved for in-memory caches; a file never carries one
    if jq -e 'keys | map(select(startswith("_"))) | length > 0' "$file_path" >/dev/null 2>&1; then
        return $E_RESERVED_KEY_COLLISION
    fi

    # 5. Field names must be unique
    if ! jq -e '(.Fields | map(.name)) as $n | ($n | length) == ($n | unique | length)' "$file_path" >/dev/null 2>&1; then
        return $E_INVALID_FIELDS
    fi

    # 6. Version-specific rules (104 and 105 series; see 2.5.0)
    local vr_rc
    __bejson_validator_check_version_rules "$file_path"
    vr_rc=$?
    [[ $vr_rc -ne 0 ]] && return $vr_rc

    return 0
}

# __bejson_validator_check_version_rules <file>
# Version-specific rules for 104/104a/104db and 105/105a/105db (Records_Type count, custom headers, 104a primitives,
# 104db Record_Type_Parent rules, 105 uuids, row length/types with offsets). Sets BEJSON_VALIDATOR_LAST_ERROR on failure.
__bejson_validator_check_version_rules() {
    local file_path="$1" out code detail
    BEJSON_VALIDATOR_LAST_ERROR=""
    out=$(jq -r '
      def tok($t; $x):
        if $x == null then true
        elif $t == "string"  then ($x|type) == "string"
        elif $t == "integer" then (($x|type) == "number") and ($x == ($x|floor))
        elif $t == "number"  then ($x|type) == "number"
        elif $t == "boolean" then ($x|type) == "boolean"
        elif $t == "array"   then ($x|type) == "array"
        elif $t == "object"  then ($x|type) == "object"
        else true end;
      . as $d | .Format_Version as $v
      | if ($v | IN("104","104a","104db","105","105a","105db") | not) then ""
        else
          ($d.Fields) as $F | ($d.Records_Type) as $rt
          | (if $v == "105db" then 1 else 0 end) as $uc
          | ({"104":"104","104a":"104a","104db":"104db","105":"104","105a":"104a","105db":"104db"}[$v]) as $b
          | (if $v | IN("105","105a") then 1 else 0 end) as $off
          | def col($i): if $v == "105db" then (if $i == 0 then 0 else $i + 1 end) else $i + $off end;
          if ($b | IN("104","104db")) and ([$d | keys[] | select(IN("Format","Format_Version","Format_Creator","Records_Type","Fields","Values","Parent_Hierarchy") | not)] | length > 0) then
            "E_RESERVED_KEY_COLLISION\tcustom header forbidden in " + $v
          elif ($rt | type) != "array" then "E_INVALID_RECORDS_TYPE\tRecords_Type must be a list"
          elif ($b | IN("104","104a")) and ($rt | length) != 1 then "E_INVALID_RECORDS_TYPE\t" + $v + " must have exactly 1 record type, found " + ($rt|length|tostring)
          elif $b == "104db" and ($rt | length) < 2 then "E_INVALID_RECORDS_TYPE\t" + $v + " requires 2+ types"
          elif $b == "104db" and (($F[0].name // "") != "Record_Type_Parent") then "E_INVALID_RECORD_TYPE_PARENT\t" + $v + " first field must be Record_Type_Parent"
          elif $b == "104db" and ([$d.Values[] | select(length > 0) | select((.[0]) as $x | ($rt | index($x)) == null)] | length > 0) then "E_INVALID_RECORD_TYPE_PARENT\t" + $v + " row discriminator not in Records_Type"
          elif $b == "104a" and ([$F[] | select(.type | IN("array","object"))] | length > 0) then "E_INVALID_FIELDS\t" + $v + " forbids complex types"
          elif $b == "104db" and ([$F[1:][] | select(has("Record_Type_Parent") | not)] | length > 0) then "E_INVALID_RECORD_TYPE_PARENT\t" + $v + " field missing Record_Type_Parent owner"
          elif ($v|startswith("105")) and (($F | length) == 0 or ([$F[] | select(has("field_uuid") | not)] | length > 0)) then "E_INVALID_FIELDS\tFormat_Version claims 105-series but Fields lack field_uuid (Fail-on-Switch)"
          elif ($v|startswith("105")) and ([$F[] | .field_uuid | select((type != "string") or (. == ""))] | length > 0) then "E_INVALID_FIELDS\tfield_uuid must be a non-empty string"
          elif ($v|startswith("105")) and (([$F[] | .field_uuid] | length) != ([$F[] | .field_uuid] | unique | length)) then "E_INVALID_FIELDS\tduplicate field_uuid"
          elif ($v|startswith("105")) and ([$d.Values[] | .[$uc]] | map(select((type != "string") or (. == ""))) | length > 0) then "E_INVALID_VALUES\trow missing record_uuid at col " + ($uc|tostring)
          elif ($v|startswith("105")) and (([$d.Values[] | .[$uc]] | length) != ([$d.Values[] | .[$uc]] | unique | length)) then "E_INVALID_VALUES\tduplicate record_uuid"
          elif ([ $d.Values | to_entries[] | .key as $r | .value as $row | ($F | to_entries[]) | select(tok(.value.type; $row[col(.key)]) | not) ] | length > 0) then
            ([ $d.Values | to_entries[] | .key as $r | .value as $row | ($F | to_entries[]) | select(tok(.value.type; $row[col(.key)]) | not) | "row \($r), col \(col(.key)) (\(.value.name)): expected \(.value.type)" ] | .[0]) as $m
            | "E_TYPE_MISMATCH\tType mismatch at " + $m
          else "" end
        end' "$file_path" 2>/dev/null)
    [[ -z "$out" ]] && return 0
    code="${out%%$'\t'*}"; detail="${out#*$'\t'}"
    BEJSON_VALIDATOR_LAST_ERROR="$detail"
    echo "$detail" >&2
    case "$code" in
        E_RESERVED_KEY_COLLISION)      return $E_RESERVED_KEY_COLLISION ;;
        E_INVALID_RECORDS_TYPE)        return $E_INVALID_RECORDS_TYPE ;;
        E_INVALID_RECORD_TYPE_PARENT)  return $E_INVALID_RECORD_TYPE_PARENT ;;
        E_INVALID_FIELDS)              return $E_INVALID_FIELDS ;;
        E_INVALID_VALUES)              return $E_INVALID_VALUES ;;
        E_TYPE_MISMATCH)               return $E_TYPE_MISMATCH ;;
    esac
    return 1
}

# Export functions for subshell use
export -f __bejson_validator_check_version_rules
export -f bejson_validator_check_dependencies
export -f bejson_validator_validate_file
