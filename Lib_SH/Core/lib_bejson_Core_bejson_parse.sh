# Library:        lib_bejson_Core_bejson_parse.sh
# Family:         Core
# Description:    Rapid indexing and retrieval engine for dense tabular data.
# Version:        2.0.2
# Date:           2026-06-02
# Author:         Elton Boehnen
# Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
# Format_Creator: Elton Boehnen
# RELATIONAL_ID:  e7728b93-48e7-4896-a413-bd4f468f0fe7
# Release_Version: 300

# NOTE: set -o nounset intentionally omitted — library files must not modify
# global shell options; doing so breaks host scripts that source this file. (SH3)
set -o pipefail

BEJSON_PARSE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$BEJSON_PARSE_DIR/lib_bejson_Core_bejson_core.sh" ]]; then
    source "$BEJSON_PARSE_DIR/lib_bejson_Core_bejson_core.sh"
fi

if [[ -f "$BEJSON_PARSE_DIR/lib_bejson_Core_bejson_validator.sh" ]]; then
    source "$BEJSON_PARSE_DIR/lib_bejson_Core_bejson_validator.sh"
fi

BEJSON_PARSE_DEFAULT_OUT="${BEJSON_PARSE_DIR}/output"

BEJSON_PROJECT_NAME="My_Project"
BEJSON_FILES_NAMES=()
BEJSON_FILES_CONTENTS=()

bejson_parse_json() {
    local text="$1"
    if declare -f bejson_validator_check_dependencies >/dev/null 2>&1; then
        bejson_validator_check_dependencies || return 1
    elif ! command -v jq >/dev/null 2>&1; then
        echo "ERROR: jq is required" >&2
        return 1
    fi

    # Optimal jq-driven extraction: handles markdown fences and fallback to first '{'
    local clean
    clean=$(echo "$text" | jq -Rr '
        # 1. Attempt to extract from markdown code blocks first
        if contains("```json") then
            split("```json")[1] | split("```")[0]
        elif contains("```") then
            split("```")[1] | split("```")[0]
        else
            # 2. Fallback: find the first { and last }
            capture("(?<s>\\{.*\\})"; "s") | .s
        end
    ' 2>/dev/null)

    # If extraction failed, try raw text (in case it is already bare JSON)
    if [[ -z "$clean" || "$clean" == "null" ]]; then
        clean="$text"
    fi

    if echo "$clean" | jq '.' > /dev/null 2>&1; then
        echo "$clean" | jq '.'
        return 0
    fi
    echo "ERROR: bejson_parse_json failed" >&2
    return 1
}

bejson_extract_data() {
    local json="$1"
    BEJSON_PROJECT_NAME="My_Project"
    BEJSON_FILES_NAMES=()
    BEJSON_FILES_CONTENTS=()

    # 1. Optimal Project Name Extraction (Single jq call)
    local proj_name
    proj_name=$(echo "$json" | jq -r '
        .Fields as $fields |
        ["zipfilename", "projectname", "containername"] as $cands |
        ($fields | to_entries[] | select((.value.name | ascii_downcase | gsub("[^a-z0-9]";"")) as $n | $cands | contains([$n])) | .key) as $idx |
        .Values[] | if (. | length) > $idx then .[$idx] else null end | select(. != null and . != "") | tostring
    ' 2>/dev/null | head -1)
    
    if [[ -n "$proj_name" && "$proj_name" != "null" ]]; then
        BEJSON_PROJECT_NAME=$(echo "$proj_name" | sed 's/[<>:"\/\\|?*]/_/g')
    fi

    # 2. Optimal Batch File Extraction (Single jq call for all files)
    # Extract pairs of filename and content using a delimiter
    local pairs
    pairs=$(echo "$json" | jq -r '
        .Fields as $fields |
        # Generate 1..50 mapping
        [
            range(1; 51) as $n | 
            ("file" + tostring + "name") as $nk | 
            ("file" + tostring + "content") as $ck |
            {
                name_idx: ($fields | to_entries[] | select((.value.name | ascii_downcase | gsub("[^a-z0-9]";"")) == $nk) | .key),
                cont_idx: ($fields | to_entries[] | select((.value.name | ascii_downcase | gsub("[^a-z0-9]";"")) == $ck) | .key)
            } | select(.name_idx != null and .cont_idx != null)
        ] as $indices |
        
        if ($indices | length) > 0 then
            .Values[] as $row |
            $indices[] as $i |
            $row[$i.name_idx] as $fn |
            $row[$i.cont_idx] as $fc |
            if ($fn != null and $fn != "" and $fc != null and $fc != "") then
                "$fn" + "\t" + ($fc | tostring | gsub("\n";"\\n") | gsub("\t";"\\t"))
            else
                empty
            end
        else
            empty
        end
    ')

    while IFS=$'\t' read -r fname fcont; do
        if [[ -n "$fname" ]]; then
            BEJSON_FILES_NAMES+=("$fname")
            # Unescape newlines and tabs
            BEJSON_FILES_CONTENTS+=("$(printf '%b' "$fcont")")
        fi
    done <<< "$pairs"

    [[ ${#BEJSON_FILES_NAMES[@]} -eq 0 ]] && return 1
    return 0
}

bejson_save_files() {
    local proj="${1:-My_Project}"
    local base_dir="${2:-$BEJSON_PARSE_DEFAULT_OUT}"
    local overwrite="${3:-false}"
    local target
    [[ "$overwrite" == "true" ]] && target="${base_dir}/${proj}" || target="${base_dir}/$(date +"%Y%m%d_%H%M%S")_${proj}"
    mkdir -p "$target" 2>/dev/null
    for i in "${!BEJSON_FILES_NAMES[@]}"; do
        local fpath="${target}/${BEJSON_FILES_NAMES[$i]}"
        mkdir -p "$(dirname "$fpath")"
        printf '%s' "${BEJSON_FILES_CONTENTS[$i]}" > "$fpath"
    done
    sync "$target" 2>/dev/null || sync 2>/dev/null || true
    echo "{\"success\":true,\"path\":\"$target\",\"file_count\":${#BEJSON_FILES_NAMES[@]}}"
}

export -f bejson_parse_json
export -f bejson_extract_data
export -f bejson_save_files
