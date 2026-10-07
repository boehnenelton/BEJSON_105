# Library:        lib_bejson_Core_bejson_list_validator.sh
# Family:         Core
# Description:    Hierarchical list validator for BEJSON 104a documents. Validates
#                 id/parent_id integrity and orphan/cycle detection.
# Version:        1.1.0
# Date:           2026-06-28
# Author:         Elton Boehnen
# Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
# Format_Creator: Elton Boehnen
# RELATIONAL_ID:  1bcc48c9-36c0-4a25-8aac-1e163a231384
# Release_Version: 300

source "$(dirname "$BASH_SOURCE")/lib_bejson_Core_bejson_validator.sh"

bejson_list_validator_validate() {
    local file="$1"
    bejson_validator_validate_file "$file" || return $?
    local ver=$(jq -r ".Format_Version" "$file")
    [[ "$ver" != "104a" ]] && return 4
    return 0
}
