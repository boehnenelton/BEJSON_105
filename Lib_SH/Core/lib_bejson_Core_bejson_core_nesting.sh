# -----------------------------------------------------------------------------
# Library:         lib_bejson_Core_bejson_core_nesting.sh
# Family:          Core
# Module Purpose:  Nested-104 detection, validation, field-map cache, safe mutation (append-only schema, null-padding) and dotted-path queries.
# Architecture:    Nested BEJSON 104: a cell of a parent 104 document holds a complete embedded 104 document; the physical cell coordinate (NestAddress) is the implicit foreign key. It is neither 104db nor MFDB.
# Format_Scope:    Nested 104 (NOT 104db, NOT MFDB)
# Glossary:        BEJSON 104, 104a and 104db are the three file formats (Format_Version). 104db = ONE file holding 2+ entity types
#                  (Record_Type_Parent discriminator, null-padding). MFDB is NOT a format and NOT 104db: it is a layer made of one 104a manifest
#                  (104a.mfdb.bejson) plus dense 104 entity files linked by Parent_Hierarchy. MFDB-132 = an MFDB packed into one Chunked-104a document.
# Version:         0.6.0
# Release_Version: 300
# Date:            2026-10-16
# Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
# Format_Creator:  Elton Boehnen
# RELATIONAL_ID:   3b78a025-3e57-4204-bd84-b71dc04bdd4f
# Changelog:
#   0.6.0 (2026-10-16) - Merged lib_bejson_Core_bejson_nesting_query into this module (bejson_nesting_query, bejson_nesting_get_path, bejson_nesting_query_summary); query module removed, no alias.
#           Fixed: _nesting_quick_validate_104 mandatory-key jq test was evaluated against the key string instead of the document, so EVERY nested doc was rejected as not BEJSON (scan found 0 nested cells).
#           Fixed: scan counted every valid nested cell as ALSO invalid (`(( valid++ )) || (( invalid++ ))` runs the || branch when valid was 0); now if/else.
#           Fixed: query skipped null/false cells and returned values as strings (now raw JSON, parity with PY/JS/TS: 2 matches in the smoke fixture).
#           Fixed: no-RELATIONAL_ID fingerprint hashed only Fields (stale cache hits across same-schema documents); now Fields + Values.
#           Validation stays local in Bash: the Core Bash validator is file-based (jq on a path) and cannot validate an in-memory cell.
#   0.5.1 (2026-10-16) - Error codes now sourced from lib_bejson_Core_bejson_errors.sh (nesting errors file removed).
#           No code, API, error-code (130-139) or output change.
#   0.5.0 (2026-10-14) - Moved from the Core_Nesting family into Core (was lib_bejson_CoreNesting_bejson_core_nesting.sh, 0.4.5). Renamed to lib_bejson_Core_bejson_core_nesting.sh;
#           same-directory imports updated. No code, API, error-code (130-139) or output change.
# -----------------------------------------------------------------------------

set -o pipefail
[[ -n "${_LIB_BEJSON_CORE_NESTING_LOADED:-}" ]] && return 0
readonly _LIB_BEJSON_CORE_NESTING_LOADED=1

_NESTING_SH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Fail loudly if the Core errors file is missing, so E_* codes are never silently undefined.
if [[ ! -f "$_NESTING_SH_DIR/lib_bejson_Core_bejson_errors.sh" ]]; then
    echo "ERROR: required dependency not found: $_NESTING_SH_DIR/lib_bejson_Core_bejson_errors.sh" >&2
    return 1 2>/dev/null || exit 1
fi
source "$_NESTING_SH_DIR/lib_bejson_Core_bejson_errors.sh"

readonly NESTING_MAX_DEPTH=16
readonly _NESTING_VALID_VERSION="104"

# ===========================================================================
# NEST MAP CACHE
# Key:   "<parentFingerprint>:<row>:<col>:<depth>"
# Value: JSON blob (NestedCell)
# col_schema map: "<parentFingerprint>:colschema:<col>"  →  Fields JSON string
# ===========================================================================
declare -gA _BEJSON_NEST_MAP=()
declare -gA _BEJSON_COL_SCHEMAS=()

# Prints the cached NestedCell for a NestAddress, or nothing.
bejson_nesting_cache_get() {
    local parent_fingerprint="$1" row="$2" col="$3" depth="$4"
    local cache_key="${parent_fingerprint}:${row}:${col}:${depth}"
    [[ -n "${_BEJSON_NEST_MAP[$cache_key]+_}" ]] && { echo "${_BEJSON_NEST_MAP[$cache_key]}"; return 0; }
    return $E_NESTING_CACHE_MISS
}

# Stores a NestedCell under its NestAddress.
bejson_nesting_cache_put() {
    local parent_fingerprint="$1" row="$2" col="$3" depth="$4" cell_json="$5"
    _BEJSON_NEST_MAP["${parent_fingerprint}:${row}:${col}:${depth}"]="$cell_json"
}

# Clears the NestMap cache (all, or one parent fingerprint).
bejson_nesting_cache_clear() {
    local parent_fingerprint="${1:-}"
    if [[ -z "$parent_fingerprint" ]]; then _BEJSON_NEST_MAP=(); _BEJSON_COL_SCHEMAS=(); return 0; fi
    local cache_key
    for cache_key in "${!_BEJSON_NEST_MAP[@]}";   do [[ "$cache_key" == "${parent_fingerprint}:"* ]] && unset '_BEJSON_NEST_MAP[$cache_key]';   done
    for cache_key in "${!_BEJSON_COL_SCHEMAS[@]}"; do [[ "$cache_key" == "${parent_fingerprint}:"* ]] && unset '_BEJSON_COL_SCHEMAS[$cache_key]'; done
}

# Prints diagnostic counts for the cache.
bejson_nesting_cache_stats() {
    local total_entries="${#_BEJSON_NEST_MAP[@]}"
    local -A fingerprint_set=() depth_set=()
    local cache_key
    for cache_key in "${!_BEJSON_NEST_MAP[@]}"; do
        local key_fingerprint="${cache_key%%:*}"
        fingerprint_set[$key_fingerprint]=1
        local key_depth="${cache_key##*:}"
        depth_set[$key_depth]=1
    done
    local depth_list
    depth_list=$(printf '%s\n' "${!depth_set[@]}" | sort -n | tr '\n' ',' | sed 's/,$//')
    echo "total_entries=${total_entries} unique_parents=${#fingerprint_set[@]} depth_spread=[${depth_list}]"
}

# Prints every cached NestedCell for one parent document and column.
bejson_nesting_cache_lookup_col() {
    local parent_fingerprint="$1" col="$2"
    local cache_key
    for cache_key in "${!_BEJSON_NEST_MAP[@]}"; do
        # key format: parentFingerprint:row:col:depth — extract col field (index 2 after first split on fingerprint)
        local remaining_key="${cache_key#"${parent_fingerprint}:"}"
        local extracted_col
        extracted_col=$(echo "$remaining_key" | cut -d: -f2)
        [[ "$extracted_col" == "$col" ]] && echo "${_BEJSON_NEST_MAP[$cache_key]}"
    done
}

# ===========================================================================
# INTERNAL HELPERS
# ===========================================================================

# Stable identity of a parent document: RELATIONAL_ID, else a hash of its Fields AND Values (content, not just schema).
_nesting_doc_fingerprint() {
    local doc_json="$1"
    local relational_id_value
    relational_id_value=$(echo "$doc_json" | jq -r '.RELATIONAL_ID // .relational_id // empty' 2>/dev/null)
    if [[ -n "$relational_id_value" && "$relational_id_value" != "null" ]]; then echo "$relational_id_value"; return 0; fi
    local hash_value
    hash_value=$(echo "$doc_json" | jq -c '[.Fields // [], .Values // []]' 2>/dev/null | sha256sum | cut -d' ' -f1)
    echo "hash:${hash_value:0:32}"
}

# Returns 0 when a cell looks like an embedded object (starts with { and ends with }).
_nesting_is_candidate() {
    local value_text="$1"
    [[ "$value_text" == "{"* && "$value_text" == *"}" ]] && return 0
    return 1
}

# Canonical string form of a Fields array.
_nesting_fields_signature() {
    echo "$1" | jq -c '.Fields // []' 2>/dev/null
}

# Prints 'valid' or 'invalid|<reason>': nested cells must be BEJSON 104 (not 104a, 104db or an MFDB manifest). Empty reason = not 104, skip silently.
# Returns "valid" or "invalid|<reason>". Empty reason = not 104, skip silently.
_nesting_quick_validate_104() {
    local doc_json="$1"
    local validation_error_code=$E_NESTING_VALIDATION_FAILED

    echo "$doc_json" | jq -e 'type == "object"' > /dev/null 2>&1 || {
        echo "invalid|E${E_NESTING_NOT_BEJSON}: not an object"; return 1; }

    # Missing mandatory keys → not BEJSON, skip silently
    local has_all_mandatory_keys
    has_all_mandatory_keys=$(echo "$doc_json" | jq -r '
        . as $d
        | ["Format","Format_Version","Format_Creator","Records_Type","Fields","Values"]
        | all(.[]; . as $k | $d | has($k))' 2>/dev/null)
    [[ "$has_all_mandatory_keys" != "true" ]] && { echo "invalid|"; return 1; }

    local format_value version_value
    format_value=$(echo "$doc_json" | jq -r '.Format')
    version_value=$(echo "$doc_json" | jq -r '.Format_Version')
    [[ "$format_value" != "BEJSON" ]]                  && { echo "invalid|"; return 1; }
    [[ "$version_value" != "$_NESTING_VALID_VERSION" ]] && { echo "invalid|"; return 1; }

    local validation_errors=""
    local format_creator_value records_type_check
    format_creator_value=$(echo "$doc_json" | jq -r '.Format_Creator')
    [[ "$format_creator_value" != "Elton Boehnen" ]] && \
        validation_errors+="E${validation_error_code}: Format_Creator must be 'Elton Boehnen';"

    records_type_check=$(echo "$doc_json" | jq '.Records_Type | if type=="array" and length==1 and (.[0]|type)=="string" then 1 else 0 end')
    [[ "$records_type_check" != "1" ]] && \
        validation_errors+="E${validation_error_code}: Records_Type must be a single-string array;"

    # Positional integrity
    local field_count
    field_count=$(echo "$doc_json" | jq '.Fields | length')
    local bad_rows
    bad_rows=$(echo "$doc_json" | jq -r --argjson fc "$field_count" '
        .Values | to_entries[] | select(.value | length != $fc) |
        "E'$validation_error_code': row \(.key) has \(.value|length) values, Fields has \($fc)"')
    [[ -n "$bad_rows" ]] && validation_errors+="${bad_rows};"

    if [[ -z "$validation_errors" ]]; then echo "valid"; else echo "invalid|${validation_errors%;}"; fi
}

# Convention check relating the nested Records_Type name to the parent field name; prints a warning or nothing.
_nesting_check_records_type_convention() {
    local doc_json="$1" parent_field="$2"
    local records_type_value
    records_type_value=$(echo "$doc_json" | jq -r '.Records_Type[0] // empty')
    [[ -z "$records_type_value" ]] && return 0
    local expected_records_type="${parent_field^}"   # bash parameter expansion: capitalize first char
    [[ "$records_type_value" != "$expected_records_type" ]] && \
        echo "W: Records_Type '${records_type_value}' should be '${expected_records_type}' by convention"
}

# ===========================================================================
# CORE WALK
# ===========================================================================

# Recursive scan of one cell; echoes a NestedCell JSON blob when an embedded 104 document is found (returns 1 to skip).
# _nesting_walk_cell <cell_value> <row> <col> <field_name> <depth>
#                   <colon_delimited_seen_fingerprints> <parent_fingerprint> <parent_fingerprint_for_col_schema>
# Echoes a JSON NestedCell blob. Returns 0 on find, 1 on skip.
_nesting_walk_cell() {
    local cell_value="$1" row="$2" col="$3" field_name="$4"
    local depth="$5" seen_fingerprints="$6" parent_fingerprint="$7"

    (( depth > NESTING_MAX_DEPTH )) && {
        echo "[NESTING] WARN: depth cap at row=${row} col=${col}" >&2; return 1; }

    _nesting_is_candidate "$cell_value" || return 1

    local cached_blob
    cached_blob=$(bejson_nesting_cache_get "$parent_fingerprint" "$row" "$col" "$depth" 2>/dev/null) && {
        echo "$cached_blob"; return 0; }

    # Parse — cell_value is a JSON string; try direct parse first
    local parsed_doc
    parsed_doc=$(echo "$cell_value" | jq '.' 2>/dev/null) || return 1
    echo "$parsed_doc" | jq -e 'type == "object"' > /dev/null 2>&1 || return 1

    local validation_result is_valid validation_detail
    validation_result=$(_nesting_quick_validate_104 "$parsed_doc")
    is_valid="${validation_result%%|*}"
    validation_detail="${validation_result#*|}"

    [[ "$is_valid" == "invalid" && -z "$validation_detail" ]] && return 1  # not 104 — skip

    local warnings="" errors=""
    [[ "$is_valid" == "invalid" ]] && errors="$validation_detail"

    # Column schema uniformity
    if [[ "$is_valid" == "valid" ]]; then
        local fields_signature schema_key
        fields_signature=$(_nesting_fields_signature "$parsed_doc")
        schema_key="${parent_fingerprint}:colschema:${col}"
        if [[ -z "${_BEJSON_COL_SCHEMAS[$schema_key]+_}" ]]; then
            _BEJSON_COL_SCHEMAS[$schema_key]="$fields_signature"
        elif [[ "${_BEJSON_COL_SCHEMAS[$schema_key]}" != "$fields_signature" ]]; then
            errors="E${E_NESTING_SCHEMA_MISMATCH}: col ${col} row ${row} Fields schema differs from column contract"
            is_valid="invalid"
        fi
    fi

    # Records_Type convention check
    if [[ "$is_valid" == "valid" ]]; then
        local convention_warning
        convention_warning=$(_nesting_check_records_type_convention "$parsed_doc" "$field_name")
        [[ -n "$convention_warning" ]] && warnings="$convention_warning"
    fi

    local nested_fingerprint
    nested_fingerprint=$(_nesting_doc_fingerprint "$parsed_doc")

    # Circular reference guard
    if [[ ":${seen_fingerprints}:" == *":${nested_fingerprint}:"* ]]; then
        local cell_json
        cell_json=$(jq -nc \
            --argjson row "$row" --argjson col "$col" \
            --arg field_name "$field_name" --argjson depth "$depth" \
            --argjson is_valid false \
            --argjson errors "[\"E${E_NESTING_CIRCULAR_REF}: circular reference at depth ${depth}\"]" \
            --argjson warnings "[]" --argjson children "[]" \
            '{row:$row,col:$col,fieldName:$field_name,depth:$depth,isValid:$is_valid,errors:$errors,warnings:$warnings,children:$children}')
        bejson_nesting_cache_put "$parent_fingerprint" "$row" "$col" "$depth" "$cell_json"
        echo "$cell_json"; return 0
    fi

    # Recurse into nested doc's own Values
    local children_json="[]"
    if [[ "$is_valid" == "valid" ]]; then
        local new_seen_fingerprints="${seen_fingerprints}:${nested_fingerprint}"
        local fields_json values_json row_count col_count
        fields_json=$(echo "$parsed_doc" | jq -c '.Fields // []')
        values_json=$(echo "$parsed_doc" | jq -c '.Values // []')
        row_count=$(echo "$values_json" | jq 'length')
        # Pre-compute field names as a bash array — single jq call, O(1) per cell
        local field_names_json
        field_names_json=$(echo "$fields_json" | jq -r '[.[].name] | @json')
        local -a _child_field_names=()
        while IFS= read -r field_name_item; do
            _child_field_names+=("$field_name_item")
        done < <(echo "$field_names_json" | jq -r '.[]')
        local child_results=()
        local row_index col_index child_cell_value child_field_name child_result
        for (( row_index=0; row_index<row_count; row_index++ )); do
            col_count=$(echo "$values_json" | jq ".[${row_index}] | length")
            for (( col_index=0; col_index<col_count; col_index++ )); do
                child_cell_value=$(echo "$values_json" | jq -r ".[${row_index}][${col_index}]")
                # O(1) bash array lookup vs per-cell jq call (R2-SH)
                child_field_name="${_child_field_names[$col_index]:-col_${col_index}}"
                child_result=$(_nesting_walk_cell \
                    "$child_cell_value" "$row_index" "$col_index" "$child_field_name" \
                    "$(( depth + 1 ))" "$new_seen_fingerprints" "$nested_fingerprint") && \
                    child_results+=("$child_result")
            done
        done
        (( ${#child_results[@]} > 0 )) && \
            children_json=$(printf '%s\n' "${child_results[@]}" | jq -sc '.')
    fi

    local is_valid_bool errors_arr warnings_arr
    [[ "$is_valid" == "valid" ]] && is_valid_bool=true || is_valid_bool=false
    errors_arr=$(  [[ -n "$errors"   ]] && jq -nc --arg e "$errors"   '[$e]' || echo "[]")
    warnings_arr=$([[ -n "$warnings" ]] && jq -nc --arg w "$warnings" '[$w]' || echo "[]")

    local cell_json
    cell_json=$(jq -nc \
        --argjson row "$row" --argjson col "$col" \
        --arg field_name "$field_name" --argjson depth "$depth" \
        --argjson is_valid "$is_valid_bool" \
        --argjson errors "$errors_arr" \
        --argjson warnings "$warnings_arr" \
        --argjson children "$children_json" \
        '{row:$row,col:$col,fieldName:$field_name,depth:$depth,isValid:$is_valid,errors:$errors,warnings:$warnings,children:$children}')
    bejson_nesting_cache_put "$parent_fingerprint" "$row" "$col" "$depth" "$cell_json"
    echo "$cell_json"; return 0
}

# ===========================================================================
# PUBLIC API
# ===========================================================================

# Entry point: scans a parent 104 document for embedded 104 documents and prints a NestingResult JSON. Nested BEJSON is 104-inside-104 through a cell; it is not 104db and not MFDB.
# bejson_nesting_scan <bejson_file_path> [use_cache:1|0]
# Echoes a JSON NestingResult to stdout.
bejson_nesting_scan() {
    local file_path="$1" use_cache="${2:-1}"

    [[ ! -f "$file_path" ]] && {
        echo "{\"error\":\"E${E_FILE_NOT_FOUND}: file not found: ${file_path}\"}" >&2
        return $E_FILE_NOT_FOUND; }

    local doc_json
    doc_json=$(jq '.' "$file_path" 2>/dev/null) || {
        echo "{\"error\":\"E${E_INVALID_JSON}: invalid JSON\"}" >&2
        return $E_INVALID_JSON; }

    local document_fingerprint
    document_fingerprint=$(_nesting_doc_fingerprint "$doc_json")

    local fields_json values_json row_count
    fields_json=$(echo "$doc_json" | jq -c '.Fields // []')
    values_json=$(echo "$doc_json" | jq -c '.Values // []')
    row_count=$(echo "$values_json" | jq 'length')

    local scanned=0 found=0 valid=0 invalid=0 max_depth=0 schema_errors=0
    local collected=()

    local row_index col_index col_count cell_value resolved_field_name nested_result
    for (( row_index=0; row_index<row_count; row_index++ )); do
        col_count=$(echo "$values_json" | jq ".[${row_index}] | length")
        for (( col_index=0; col_index<col_count; col_index++ )); do
            (( scanned++ ))
            cell_value=$(echo "$values_json" | jq -r ".[${row_index}][${col_index}]")
            _nesting_is_candidate "$cell_value" || continue
            resolved_field_name=$(echo "$fields_json" | jq -r ".[${col_index}].name // \"col_${col_index}\"")

            if (( use_cache )); then
                local cached_hit
                if cached_hit=$(bejson_nesting_cache_get "$document_fingerprint" "$row_index" "$col_index" 1 2>/dev/null); then
                    (( found++ ))
                    local cached_is_valid; cached_is_valid=$(echo "$cached_hit" | jq '.isValid')
                    if [[ "$cached_is_valid" == "true" ]]; then valid=$((valid + 1)); else invalid=$((invalid + 1)); fi
                    local cached_depth; cached_depth=$(echo "$cached_hit" | jq '.depth')
                    (( cached_depth > max_depth )) && max_depth=$cached_depth
                    collected+=("$cached_hit"); continue
                fi
            fi

            nested_result=$(_nesting_walk_cell \
                "$cell_value" "$row_index" "$col_index" "$resolved_field_name" 1 "$document_fingerprint" "$document_fingerprint") || continue
            (( found++ ))
            local nested_is_valid; nested_is_valid=$(echo "$nested_result" | jq '.isValid')
            if [[ "$nested_is_valid" == "true" ]]; then valid=$((valid + 1)); else invalid=$((invalid + 1)); fi
            local nested_depth; nested_depth=$(echo "$nested_result" | jq '.depth')
            (( nested_depth > max_depth )) && max_depth=$nested_depth
            # Count schema errors
            local schema_error_count; schema_error_count=$(echo "$nested_result" | jq \
                '[.errors[]? | select(contains("E'$E_NESTING_SCHEMA_MISMATCH'"))] | length')
            (( schema_errors += schema_error_count ))
            collected+=("$nested_result")
        done
    done

    local cells_array="[]"
    (( ${#collected[@]} > 0 )) && \
        cells_array=$(printf '%s\n' "${collected[@]}" | jq -sc '.')

    jq -nc \
        --argjson scanned "$scanned" --argjson found "$found" \
        --argjson valid "$valid" --argjson invalid "$invalid" \
        --argjson max_depth "$max_depth" --argjson schema_errors "$schema_errors" \
        --argjson cells "$cells_array" \
        '{scannedCells:$scanned,nestedFound:$found,nestedValid:$valid,nestedInvalid:$invalid,maxDepthSeen:$max_depth,schemaErrors:$schema_errors,cells:$cells,errors:[],warnings:[]}'
}

# Applies a mutation to a nested document and writes the result back into the parent file atomically.
# bejson_nesting_mutate <parent_file> <row> <col> <jq_mutation_expr>
# jq_mutation_expr: a jq filter applied to the nested doc object, e.g.
#   '.Fields += [{"name":"new_field","type":"string"}]'
# Writes the mutated result back into the parent file atomically.
bejson_nesting_mutate() {
    local parent_file="$1" row="$2" col="$3" jq_mutation_expr="$4"

    [[ ! -f "$parent_file" ]] && return $E_FILE_NOT_FOUND

    local parent_json
    parent_json=$(jq '.' "$parent_file") || return $E_INVALID_JSON

    # Extract nested cell string
    local nested_str
    nested_str=$(echo "$parent_json" | jq -r ".Values[${row}][${col}]")
    local nested_doc
    nested_doc=$(echo "$nested_str" | jq '.') || {
        echo "[NESTING] E${E_NESTING_INVALID_CELL}: cell is not valid JSON" >&2
        return $E_NESTING_INVALID_CELL; }

    local fields_before fields_count_before
    fields_before=$(echo "$nested_doc" | jq -c '.Fields // []')
    fields_count_before=$(echo "$fields_before" | jq 'length')

    # Apply mutation
    local mutated_doc
    mutated_doc=$(echo "$nested_doc" | jq "$jq_mutation_expr") || {
        echo "[NESTING] mutation jq expression failed" >&2; return 1; }

    local fields_count_after
    fields_count_after=$(echo "$mutated_doc" | jq '.Fields | length')

    # Guard: no removals
    (( fields_count_after < fields_count_before )) && {
        echo "[NESTING] E${E_NESTING_SCHEMA_MISMATCH}: mutation removed fields — not permitted" >&2
        return $E_NESTING_SCHEMA_MISMATCH; }

    # Guard: no reorders — first fields_count_before fields must match
    local reorder_check
    reorder_check=$(jq -n \
        --argjson before "$fields_before" \
        --argjson after "$(echo "$mutated_doc" | jq -c '.Fields')" \
        --argjson nb "$fields_count_before" \
        '[$before, $after | .[:$nb]] | .[0] == .[1]')
    [[ "$reorder_check" != "true" ]] && {
        echo "[NESTING] E${E_NESTING_SCHEMA_MISMATCH}: mutation reordered/retyped fields — not permitted" >&2
        return $E_NESTING_SCHEMA_MISMATCH; }

    # Auto null-pad if Fields grew
    if (( fields_count_after > fields_count_before )); then
        local fields_added_count=$(( fields_count_after - fields_count_before ))
        mutated_doc=$(echo "$mutated_doc" | jq --argjson delta "$fields_added_count" \
            '.Values = [.Values[] | . + ([null] * $delta)]')
    fi

    # Serialize mutated doc back into parent, write atomically
    local new_parent tmp_file
    tmp_file="${parent_file}.nesting.tmp"
    new_parent=$(echo "$parent_json" | jq \
        --argjson row "$row" --argjson col "$col" \
        --arg nested_str "$(echo "$mutated_doc" | jq -c '.')" \
        '.Values[$row][$col] = $nested_str')
    echo "$new_parent" > "$tmp_file" && mv "$tmp_file" "$parent_file"
}

# Prints a human-readable summary of a NestingResult.
# bejson_nesting_summary <nesting_result_json>
bejson_nesting_summary() {
    local result_json="$1"
    echo "BEJSON Core_Nesting Scan Summary"
    echo "$result_json" | jq -r '
        "  Cells scanned    : \(.scannedCells)",
        "  Nested found     : \(.nestedFound)",
        "  Valid nested     : \(.nestedValid)",
        "  Invalid nested   : \(.nestedInvalid)",
        "  Max depth seen   : \(.maxDepthSeen)",
        "  Schema errors    : \(.schemaErrors)"
    '
    local error_count warning_count
    error_count=$(echo "$result_json" | jq '.errors | length')
    warning_count=$(echo "$result_json" | jq '.warnings | length')
    (( error_count > 0 )) && {
        echo "  Scan errors:"
        echo "$result_json" | jq -r '.errors[] | "    - \(.)"'
    }
    (( warning_count > 0 )) && {
        echo "  Warnings:"
        echo "$result_json" | jq -r '.warnings[] | "    ~ \(.)"'
    }
    local cell_count
    cell_count=$(echo "$result_json" | jq '[.. | objects | select(has("fieldName"))] | length')
    (( cell_count > 0 )) && {
        echo "  Nested cells:"
        echo "$result_json" | jq -r '
            [.. | objects | select(has("fieldName"))] | .[] |
            "    [\(if .isValid then "VALID" else "INVALID" end)] row=\(.row) col=\(.col) field='"'"'\(.fieldName)'"'"' depth=\(.depth)",
            (.errors[] | "      ! \(.)"),
            (.warnings[] | "      ~ \(.)")
        '
    }
}

# ===========================================================================
# DOTTED-PATH QUERIES (merged in from the former lib_bejson_Core_bejson_nesting_query module)
# e.g. player_inventory[*].item_id
# ===========================================================================

# ===========================================================================
# PATH PARSING
# Segments are encoded as a single string: "name1|sel1;name2|sel2;..."
# sel is "*", an integer, or empty (treated as "*").
# ===========================================================================

# Parses a dotted path such as player_inventory[*].item_id; error on stderr for bad grammar.
# _nesting_query_parse_path <path_string>
# Echoes the encoded segment string, or returns non-zero with an E138/E139
# message on stderr for bad grammar.
_nesting_query_parse_path() {
    local path="$1"
    local trimmed_path="${path#"${path%%[![:space:]]*}"}"
    trimmed_path="${trimmed_path%"${trimmed_path##*[![:space:]]}"}"

    if [[ -z "$trimmed_path" ]]; then
        echo "E${E_NESTING_QUERY_EMPTY_PATH}: path is empty" >&2
        return 1
    fi

    local IFS='.'
    local -a raw_segments=($trimmed_path)
    unset IFS

    local encoded_segments="" raw_segment segment_field_name segment_selector
    for raw_segment in "${raw_segments[@]}"; do
        if [[ "$raw_segment" =~ ^([A-Za-z_][A-Za-z0-9_]*)(\[(\*|[0-9]+)\])?$ ]]; then
            segment_field_name="${BASH_REMATCH[1]}"
            segment_selector="${BASH_REMATCH[3]}"
            [[ -z "$segment_selector" ]] && segment_selector="*"
            encoded_segments+="${segment_field_name}|${segment_selector};"
        else
            echo "E${E_NESTING_QUERY_INVALID_PATH}: bad segment '${raw_segment}' in path '${path}'" >&2
            return 1
        fi
    done
    echo "$encoded_segments"
    return 0
}

# ===========================================================================
# CORE WALK
# ===========================================================================

# Recursive walk of a nested-104 document along the parsed path; prints one QueryMatch JSON per line.
# _nesting_query_walk <doc_json> <encoded_segments> <segment_index> <full_path>
#                      <field_chain_csv> <row_chain_csv> <col_chain_csv>
#                      <match_value_or_empty> <has_match_value:1|0>
# Echoes zero or more JSON QueryMatch blobs, one per line, to stdout.
_nesting_query_walk() {
    local doc_json="$1" encoded_segments="$2" segment_index="$3" full_path="$4"
    local field_chain="$5" row_chain="$6" col_chain="$7"
    local match_value="$8" has_match_value="$9"

    local -a segments
    IFS=';' read -ra segments <<< "$encoded_segments"
    local total_segment_count="${#segments[@]}"
    (( segment_index >= total_segment_count )) && return 0

    local current_segment="${segments[$segment_index]}"
    local field_name="${current_segment%%|*}"
    local selector="${current_segment##*|}"
    local is_last_segment=0
    (( segment_index == total_segment_count - 1 )) && is_last_segment=1

    local col
    col=$(echo "$doc_json" | jq -r --arg fn "$field_name" \
        '(.Fields // []) | to_entries[] | select(.value.name == $fn) | .key' 2>/dev/null | head -n1)
    [[ -z "$col" ]] && return 0   # dead branch — field not present here, not an error

    local row_count
    row_count=$(echo "$doc_json" | jq '(.Values // []) | length' 2>/dev/null)
    [[ -z "$row_count" ]] && row_count=0

    local -a row_indices
    if [[ "$selector" == "*" ]]; then
        local index_counter=0
        row_indices=()
        while (( index_counter < row_count )); do row_indices+=("$index_counter"); ((index_counter++)); done
    else
        row_indices=("$selector")
    fi

    local row_index cell_json cell_value nested_doc new_field_chain new_row_chain new_col_chain
    for row_index in "${row_indices[@]}"; do
        (( row_index < 0 || row_index >= row_count )) && continue
        # Cell as JSON text so null / false / numbers are matched like in the PY/JS/TS ports (null cells are matches).
        cell_json=$(echo "$doc_json" | jq -c --argjson r "$row_index" --argjson c "$col" '.Values[$r][$c]' 2>/dev/null) || continue
        [[ -z "$cell_json" ]] && continue

        new_field_chain="${field_chain}${field_chain:+,}${field_name}"
        new_row_chain="${row_chain}${row_chain:+,}${row_index}"
        new_col_chain="${col_chain}${col_chain:+,}${col}"

        if (( is_last_segment )); then
            if (( has_match_value == 0 )) || \
               [[ "$(jq -nr --argjson v "$cell_json" --arg m "$match_value" '(($v | tostring) == $m) | tostring')" == "true" ]]; then
                jq -nc \
                    --arg path "$full_path" --argjson value "$cell_json" \
                    --arg fchain "$new_field_chain" --arg rchain "$new_row_chain" --arg cchain "$new_col_chain" \
                    '{path:$path, value:$value,
                      fieldChain:($fchain|split(",")),
                      rowChain:($rchain|split(",")|map(tonumber)),
                      colChain:($cchain|split(",")|map(tonumber))}'
            fi
            continue
        fi

        # Only a string cell can hold an embedded document.
        cell_value=$(echo "$cell_json" | jq -r 'if type == "string" then . else empty end' 2>/dev/null)
        [[ -z "$cell_value" ]] && continue
        _nesting_is_candidate "$cell_value" || continue
        nested_doc=$(echo "$cell_value" | jq '.' 2>/dev/null) || continue
        [[ -z "$nested_doc" || "$nested_doc" == "null" ]] && continue

        _nesting_query_walk "$nested_doc" "$encoded_segments" "$((segment_index + 1))" "$full_path" \
            "$new_field_chain" "$new_row_chain" "$new_col_chain" "$match_value" "$has_match_value"
    done
}

# ===========================================================================
# PUBLIC API
# ===========================================================================

# Finds values in a nested 104 document by dotted path. Non-zero only for malformed paths or a missing/invalid file.
# bejson_nesting_query <bejson_file_path> <path_string> [match_value]
# Echoes a JSON array of QueryMatch blobs to stdout.
# Returns non-zero only on malformed path syntax or missing/invalid file.
bejson_nesting_query() {
    local file_path="$1" path="$2" match_value="${3-}"
    local has_match_value=0
    (( $# >= 3 )) && has_match_value=1

    [[ ! -f "$file_path" ]] && {
        echo "E${E_FILE_NOT_FOUND:-1}: file not found: ${file_path}" >&2
        return 1; }

    local doc_json
    doc_json=$(jq '.' "$file_path" 2>/dev/null) || {
        echo "E${E_INVALID_JSON:-2}: invalid JSON in ${file_path}" >&2
        return 1; }

    local encoded_segments
    encoded_segments=$(_nesting_query_parse_path "$path") || return 1

    local matches
    matches=$(_nesting_query_walk "$doc_json" "$encoded_segments" 0 "$path" "" "" "" "$match_value" "$has_match_value")

    if [[ -z "$matches" ]]; then
        echo "[]"
    else
        printf '%s\n' "$matches" | jq -sc '.'
    fi
}

# Safe-get: prints the first value at a path; never aborts the caller's script.
# bejson_nesting_get_path <bejson_file_path> <path_string> [default_value]
# Safe-Get convenience wrapper (Section 9 standard): echoes the value of the
# FIRST match, or default_value if the path resolves to nothing or the file/
# path is invalid. Never aborts the caller's script (no propagated error).
bejson_nesting_get_path() {
    local file_path="$1" path="$2" default_value="${3-}"
    local query_result
    query_result=$(bejson_nesting_query "$file_path" "$path" 2>/dev/null) || { echo "$default_value"; return 0; }
    local first_value
    first_value=$(echo "$query_result" | jq -r '.[0].value // empty' 2>/dev/null)
    if [[ -z "$first_value" ]]; then echo "$default_value"; else echo "$first_value"; fi
}

# Prints a human-readable summary of query matches.
# bejson_nesting_query_summary <matches_json_array>
bejson_nesting_query_summary() {
    local matches_json="$1"
    local match_count
    match_count=$(echo "$matches_json" | jq 'length' 2>/dev/null)
    [[ -z "$match_count" ]] && match_count=0
    if (( match_count == 0 )); then
        echo "BEJSON Core_Nesting Query Summary"
        echo "  0 matches"
        return 0
    fi
    echo "BEJSON Core_Nesting Query Summary — ${match_count} match(es)"
    echo "$matches_json" | jq -r '
        .[] | . as $query_match |
        ( [range(0; $query_match.fieldChain|length)]
          | map("\($query_match.fieldChain[.])[row=\($query_match.rowChain[.]),col=\($query_match.colChain[.])]")
          | join(" -> ")
        ) as $chain_text |
        "  \($chain_text) = \($query_match.value)"
    '
}
