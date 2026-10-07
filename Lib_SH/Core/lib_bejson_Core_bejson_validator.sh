# Library:        lib_bejson_Core_bejson_validator.sh
# Family:         Core
# Description:    Structural integrity checker for positional values and mandatory keys.
# Version:        2.3.0
# Date:           2026-10-03
# Author:         Elton Boehnen
# Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
# Format_Creator: Elton Boehnen
# RELATIONAL_ID:  3eebff4c-5350-4af0-be78-38bdc9ea18cc
# Release_Version: 300
#
# Changelog:
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

    return 0
}

# Export functions for subshell use
export -f bejson_validator_check_dependencies
export -f bejson_validator_validate_file
