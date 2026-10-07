# Library:        lib_bejson_Core_mfdb_validator.sh
# Family:         Core
# Description:    Bidirectional path and manifest-entity relationship validator.
#                 Also owns MFDB-132-package validation
#                 (mfdb_validator_is_mfdb132_package,
#                 mfdb_validator_validate_mfdb132_package,
#                 mfdb_validator_detect_mfdb_in_chunk) — relocated here from
#                 lib_bejson_Core_bejson_chunking.sh, which should only own
#                 packaging/IO, not validation logic. See changelog note
#                 dated 2026-07-13.
# Version:        2.3.0
# Date:           2026-10-03
# Author:         Elton Boehnen
# Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
# Format_Creator: Elton Boehnen
# RELATIONAL_ID:  7c8968a0-4958-45d7-b094-38cc37df8b19
# Release_Version: 300
#
# FEATURE (2026-10-03): Phase 6 SH port -- mfdb_validator_check_referential_integrity
# (standalone, read-only, whole-database FK audit; mirrors PY 2.3.0 / TS
# checkReferentialIntegrity) and a REAL strict_fk in mfdb_validator_validate_database
# (previously an accepted-but-ignored no-op). Output: one TSV line per problem,
# CODE<TAB>entity<TAB>detail; return 0 when sound, 1 when problems found.
#
# AUDIT FIX (H1, 2026-09-13): added mfdb_validator_validate_entity_file and
# mfdb_validator_validate_database, ported from the PY reference
# implementation. lib_bejson_Core_bejson_chunking.sh calls
# mfdb_validator_validate_database unguarded from both mfdb132_archive_mount
# (sticky path) and mfdb132_archive_commit (validation gate) -- neither
# function existed in SH before this change, so both call sites would hit
# "command not found" at runtime. Verified against a real fixture manifest +
# entity file (pass and two failure paths: missing entity file, and a
# manifest with unresolvable Fields) before delivery. strict_fk is live as of
# 2.3.0 (see the Phase 6 FEATURE note above).
#
# BUGFIX (2026-07-14): mfdb_validator_detect_mfdb_in_chunk's manifest_content
# extraction piped `jq -r ... | head -n1`. jq -r prints a string's real
# embedded newlines as literal line breaks, so any pretty-printed (multi-line)
# manifest — the normal case — was truncated to its first line ("{"),
# making it fail JSON parsing. Fixed by selecting the first match inside jq
# itself ([.Values[] | select(...)] | .[0]) and removing the shell-side
# `head -n1` truncation entirely. See /docs/BUGFIX_sh_detect_mfdb_truncation.md.

# NOTE: set -o nounset intentionally omitted — library files must not modify
# global shell options; doing so breaks host scripts that source this file. (SH3)
set -o pipefail

# Source base validator if not already loaded
_MFDB_VAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! declare -f bejson_validator_validate_file > /dev/null 2>&1; then
    # shellcheck source=./lib_bejson_Core_bejson_validator.sh
    source "${_MFDB_VAL_DIR}/lib_bejson_Core_bejson_validator.sh"
fi

#-------------------------------------------------------------------------------
# Error codes (30–49)
#-------------------------------------------------------------------------------

[[ -v E_MFDB_NOT_MANIFEST ]] || readonly E_MFDB_NOT_MANIFEST=30
[[ -v E_MFDB_NOT_ENTITY_FILE ]] || readonly E_MFDB_NOT_ENTITY_FILE=31
[[ -v E_MFDB_MANIFEST_RECORDS_TYPE ]] || readonly E_MFDB_MANIFEST_RECORDS_TYPE=32
[[ -v E_MFDB_ENTITY_NOT_FOUND ]] || readonly E_MFDB_ENTITY_NOT_FOUND=33
[[ -v E_MFDB_ENTITY_NAME_MISMATCH ]] || readonly E_MFDB_ENTITY_NAME_MISMATCH=34
[[ -v E_MFDB_DUPLICATE_ENTRY ]] || readonly E_MFDB_DUPLICATE_ENTRY=35
[[ -v E_MFDB_NO_PARENT_HIERARCHY ]] || readonly E_MFDB_NO_PARENT_HIERARCHY=36
[[ -v E_MFDB_MANIFEST_NOT_FOUND ]] || readonly E_MFDB_MANIFEST_NOT_FOUND=37
[[ -v E_MFDB_BIDIRECTIONAL_FAIL ]] || readonly E_MFDB_BIDIRECTIONAL_FAIL=38
[[ -v E_MFDB_FK_UNRESOLVED ]] || readonly E_MFDB_FK_UNRESOLVED=39
[[ -v E_MFDB_MISSING_REQUIRED_FIELD ]] || readonly E_MFDB_MISSING_REQUIRED_FIELD=40
[[ -v E_MFDB_NULL_REQUIRED ]] || readonly E_MFDB_NULL_REQUIRED=41
[[ -v E_MFDB_INVALID_ARCHIVE ]] || readonly E_MFDB_INVALID_ARCHIVE=42

#-------------------------------------------------------------------------------
# Validation state
#-------------------------------------------------------------------------------

__MFDB_VALIDATION_ERRORS=()
__MFDB_VALIDATION_WARNINGS=()

mfdb_validator_reset_state() {
    __MFDB_VALIDATION_ERRORS=()
    __MFDB_VALIDATION_WARNINGS=()
}

__mfdb_add_error() {
    local message="$1"
    local location="${2:-}"
    __MFDB_VALIDATION_ERRORS+=("ERROR | Location: $location | Message: $message")
}

mfdb_validator_has_errors()   { [[ ${#__MFDB_VALIDATION_ERRORS[@]}   -gt 0 ]]; }
mfdb_validator_get_errors()    { printf '%s\n' "${__MFDB_VALIDATION_ERRORS[@]+"${__MFDB_VALIDATION_ERRORS[@]}"}"; }

#-------------------------------------------------------------------------------
# Archive Validation
#-------------------------------------------------------------------------------

# mfdb_validator_validate_archive <archive_path>
mfdb_validator_validate_archive() {
    local archive_path="$1"
    mfdb_validator_reset_state
    if [[ ! -f "$archive_path" ]]; then
        __mfdb_add_error "Archive not found: $archive_path" "File System"
        return $E_MFDB_MANIFEST_NOT_FOUND
    fi

    if ! unzip -l "$archive_path" | grep -q "104a.mfdb.bejson"; then
        __mfdb_add_error "Missing 104a.mfdb.bejson manifest inside archive" "Zip Structure"
        return $E_MFDB_INVALID_ARCHIVE
    fi
    return 0
}

#-------------------------------------------------------------------------------
# Main validation
#-------------------------------------------------------------------------------

mfdb_validator_validate_manifest() {
    local manifest_path="$1"
    mfdb_validator_reset_state
    [[ ! -f "$manifest_path" ]] && return $E_MFDB_MANIFEST_NOT_FOUND
    bejson_validator_validate_file "$manifest_path" || return $E_MFDB_NOT_MANIFEST
    
    local rt=$(jq -r '.Records_Type | @json' "$manifest_path" 2>/dev/null)
    [[ "$rt" != '["mfdb"]' ]] && return $E_MFDB_MANIFEST_RECORDS_TYPE
    return 0
}

#-------------------------------------------------------------------------------
# Entity-file and whole-database validation (AUDIT FIX H1, 2026-09-13)
#-------------------------------------------------------------------------------
# Ported from lib_bejson_Core_mfdb_validator.py's validate_mfdb_entity_file /
# validate_mfdb_database (PY/JS/TS all have these; SH did not). Added because
# lib_bejson_Core_bejson_chunking.sh calls mfdb_validator_validate_database
# unguarded from both mfdb132_archive_mount (sticky path) and
# mfdb132_archive_commit (validation gate) -- without this function defined,
# both hit "command not found" at runtime.

# __mfdb_resolve_entity_path <manifest_path> <file_path_rel>
# Mirrors Python's _resolve_entity_path: resolve file_path_rel relative to
# the manifest's directory (not relative to CWD).
__mfdb_resolve_entity_path() {
    local manifest_path="$1"
    local file_path_rel="$2"
    local manifest_dir
    manifest_dir="$(cd "$(dirname "$manifest_path")" >/dev/null 2>&1 && pwd)"
    [[ -z "$manifest_dir" ]] && { printf '%s' "$file_path_rel"; return; }
    printf '%s' "$manifest_dir/$file_path_rel"
}

# mfdb_validator_validate_entity_file <entity_path>
# Returns 0 if the entity file is a well-formed 104/105-series BEJSON file
# with a resolvable Parent_Hierarchy back to a manifest. Accumulates errors
# via __mfdb_add_error like the rest of this file. Does NOT reset state on
# entry (callers, e.g. validate_database, aggregate across many entities).
mfdb_validator_validate_entity_file() {
    local entity_path="$1"

    if [[ ! -f "$entity_path" ]]; then
        __mfdb_add_error "Entity file not found: $entity_path" "File System"
        return 1
    fi

    if ! bejson_validator_validate_file "$entity_path" >/dev/null 2>&1; then
        __mfdb_add_error "Entity file failed BEJSON validation: $entity_path" "BEJSON Validation"
        return 1
    fi

    local fmt_version
    fmt_version=$(jq -r '.Format_Version // empty' "$entity_path" 2>/dev/null)
    case "$fmt_version" in
        104|105|105a|105db) ;;
        *)
            __mfdb_add_error "Entity file must be 104 or 105-series: $entity_path" "Format_Version"
            return 1
            ;;
    esac

    local parent_hierarchy
    parent_hierarchy=$(jq -r '.Parent_Hierarchy // empty' "$entity_path" 2>/dev/null)
    if [[ -z "$parent_hierarchy" ]]; then
        __mfdb_add_error "Missing Parent_Hierarchy: $entity_path" "Structure"
        return 1
    fi

    local entity_dir manifest_check_path
    entity_dir="$(cd "$(dirname "$entity_path")" >/dev/null 2>&1 && pwd)"
    manifest_check_path="$entity_dir/$parent_hierarchy"
    if [[ ! -f "$manifest_check_path" ]]; then
        __mfdb_add_error "Manifest not found at $manifest_check_path" "Parent_Hierarchy"
        return 1
    fi

    return 0
}

# mfdb_validator_validate_database <manifest_path> [strict_fk=0]
# Returns 0 if the manifest is valid AND every entity it lists resolves and
# validates. strict_fk is accepted for signature parity with PY/JS/TS
# strict_fk=1 (or "true") additionally runs
# mfdb_validator_check_referential_integrity and records each problem via
# __mfdb_add_error (Location "FK:<entity>").
mfdb_validator_validate_database() {
    local manifest_path="$1"
    local strict_fk="${2:-0}"

    mfdb_validator_validate_manifest "$manifest_path"
    local manifest_rc=$?
    if [[ $manifest_rc -ne 0 ]]; then
        __mfdb_add_error "Manifest failed validation: $manifest_path" "Manifest"
        return 1
    fi

    local rows
    rows=$(jq -c '.Values[]' "$manifest_path" 2>/dev/null)
    if [[ -z "$rows" ]]; then
        return 0
    fi

    local overall_rc=0
    local fields_json en_idx fp_idx
    fields_json=$(jq -c '.Fields | map(.name)' "$manifest_path" 2>/dev/null)
    en_idx=$(printf '%s' "$fields_json" | jq -r 'index("entity_name") // -1')
    fp_idx=$(printf '%s' "$fields_json" | jq -r 'index("file_path") // -1')
    if [[ "$en_idx" -lt 0 || "$fp_idx" -lt 0 ]]; then
        __mfdb_add_error "Manifest Fields must include entity_name and file_path" "Structure"
        return 1
    fi

    while IFS= read -r row; do
        [[ -z "$row" ]] && continue
        local entity_name file_path resolved
        entity_name=$(printf '%s' "$row" | jq -r ".[$en_idx]")
        file_path=$(printf '%s' "$row" | jq -r ".[$fp_idx]")
        resolved=$(__mfdb_resolve_entity_path "$manifest_path" "$file_path")
        if ! mfdb_validator_validate_entity_file "$resolved"; then
            __mfdb_add_error "Entity '$entity_name' failed validation" "Entity:$entity_name"
            overall_rc=1
        fi
    done <<< "$rows"

    if [[ "$strict_fk" == "1" || "$strict_fk" == "true" ]]; then
        local fk_line fk_code fk_entity fk_detail
        while IFS=$'\t' read -r fk_code fk_entity fk_detail; do
            [[ -z "$fk_code" ]] && continue
            __mfdb_add_error "[$fk_code] $fk_detail" "FK:$fk_entity"
            overall_rc=1
        done < <(mfdb_validator_check_referential_integrity "$manifest_path")
    fi

    return $overall_rc
}

#-------------------------------------------------------------------------------
# Dependency check
#-------------------------------------------------------------------------------

mfdb_validator_check_dependencies() {
    if ! command -v unzip >/dev/null 2>&1; then
        echo "ERROR: Required command 'unzip' not found" >&2
        return 1
    fi
    # Strictly enforce jq >= 1.6 via base validator
    if ! bejson_validator_check_dependencies; then
        return 1
    fi
    return 0
}

#-------------------------------------------------------------------------------
# MFDB 1.32 chunked-package validation
#-------------------------------------------------------------------------------
# Relocated from lib_bejson_Core_bejson_chunking.sh (2026-07-13). The chunking
# library still owns bejson_core_chunking_create_mfdb132_package /
# bejson_core_chunking_unchunk_mfdb132_package (packaging and IO), but calls
# back into these functions for the actual validation — validation logic
# belongs in the validator family, not the chunker.

MFDB_VALIDATOR_MANIFEST_FILENAME="104a.mfdb.bejson"

# mfdb_validator_is_mfdb132_package <doc_json>
# Echoes "true" or "false".
mfdb_validator_is_mfdb132_package() {
    local doc_json="$1"
    printf '%s' "$doc_json" | jq -r '
        if (.Format_Version == "104a")
           and (.Schema_Name == "MFDB-132")
           and (.Package_Format == "MFDB-Chunked-104a")
           and (.MFDB_Version != null and .MFDB_Version != "")
           and (.DB_Name != null and .DB_Name != "")
        then "true" else "false" end'
}

# mfdb_validator_validate_mfdb132_package <doc_json>
# Prints {"valid":bool,"errors":[...],"warnings":[...]} as JSON.
mfdb_validator_validate_mfdb132_package() {
    local doc_json="$1"
    local is_pkg
    is_pkg=$(mfdb_validator_is_mfdb132_package "$doc_json")

    if [[ "$is_pkg" != "true" ]]; then
        jq -n '{"valid": false, "errors": ["Document is not a recognized MFDB-132 package (missing/incorrect Schema_Name/Package_Format/MFDB_Version/DB_Name)."], "warnings": []}'
        return
    fi

    printf '%s' "$doc_json" | jq \
        --arg manifest "$MFDB_VALIDATOR_MANIFEST_FILENAME" '
        def records_type_ok: (.Records_Type == ["MFDB-132"]);
        def manifest_found: ([.Values[] | select(.[5] == $manifest)] | length) > 0;
        {
          "valid": (records_type_ok and manifest_found),
          "errors": (
            (if records_type_ok then [] else ["Records_Type must be exactly [\"MFDB-132\"] for an MFDB-132 package."] end)
            +
            (if manifest_found then [] else ["Chunked package does not contain the MFDB manifest (\($manifest)) — not a complete MFDB package."] end)
          ),
          "warnings": []
        }'
}

# mfdb_validator_detect_mfdb_in_chunk <doc_json>
# Prints a JSON object: {mfdb_detected, valid, db_name, mfdb_version,
# entities: [...], errors: [...], warnings: [...]}
mfdb_validator_detect_mfdb_in_chunk() {
    local doc_json="$1"
    local manifest_name="$MFDB_VALIDATOR_MANIFEST_FILENAME"

    local manifest_content
    manifest_content=$(printf '%s' "$doc_json" | jq -r --arg m "$manifest_name" '
        ([.Values[] | select(.[5] == $m)] | .[0]) as $row
        | if $row == null then "__NOT_FOUND__"
          elif $row[6] == true then "__IS_BINARY__"
          else $row[2] end' 2>/dev/null)

    if [[ "$manifest_content" == "__NOT_FOUND__" || -z "$manifest_content" ]]; then
        jq -n --arg m "$manifest_name" '{
            "mfdb_detected": false, "valid": false, "db_name": null, "mfdb_version": null,
            "entities": [], "errors": ["No manifest (\($m)) found in chunk — no MFDB present."], "warnings": []
        }'
        return
    fi
    if [[ "$manifest_content" == "__IS_BINARY__" ]]; then
        jq -n '{
            "mfdb_detected": false, "valid": false, "db_name": null, "mfdb_version": null,
            "entities": [], "errors": ["Manifest row is flagged Is_Binary — its content was never stored, cannot validate."], "warnings": []
        }'
        return
    fi

    if ! printf '%s' "$manifest_content" | jq -e . >/dev/null 2>&1; then
        jq -n '{
            "mfdb_detected": true, "valid": false, "db_name": null, "mfdb_version": null,
            "entities": [], "errors": ["Manifest content is not valid JSON."], "warnings": []
        }'
        return
    fi

    # Level 1 manifest checks + build the entity list with per-entity Level 2
    # checks, by looking each entity's file_path up in the chunk itself.
    jq -n \
        --argjson doc "$doc_json" \
        --argjson manifest "$manifest_content" \
        --arg m "$manifest_name" '
        def find_row($rel): ([$doc.Values[] | select(.[5] == $rel)] | if length > 0 then .[0] else null end);

        ($manifest.Format_Version == "104a") as $fmt_ok |
        ($manifest.Records_Type == ["mfdb"]) as $rt_ok |
        ($manifest.Fields // [] | map(.name)) as $mfields |
        ($mfields | index("entity_name")) as $en_idx |
        ($mfields | index("file_path")) as $fp_idx |

        if ($en_idx == null or $fp_idx == null) then
          {
            "mfdb_detected": true, "valid": false,
            "db_name": ($manifest.DB_Name // null),
            "mfdb_version": ($manifest.MFDB_Version // null),
            "entities": [],
            "errors": (
              (if $fmt_ok then [] else ["Manifest Format_Version must be \"104a\"."] end)
              + (if $rt_ok then [] else ["Manifest Records_Type must be exactly [\"mfdb\"]."] end)
              + ["Manifest Fields must include \"entity_name\" and \"file_path\"."]
            ),
            "warnings": []
          }
        else
        {
          "mfdb_detected": true,
          "db_name": ($manifest.DB_Name // null),
          "mfdb_version": ($manifest.MFDB_Version // null),
          "entities": [
            $manifest.Values[] as $erow |
            ($erow[$en_idx]) as $entity_name |
            ($erow[$fp_idx]) as $file_path |
            (find_row($file_path)) as $chunk_row |
            {
              "entity_name": $entity_name,
              "file_path": $file_path,
              "found_in_chunk": ($chunk_row != null),
              "errors": (
                (if ($entity_name != null and $file_path != null) then [] else ["entity_name/file_path must not be null."] end)
                + (if $chunk_row == null then
                     ["Entity file \($file_path) listed in manifest was not found in chunk."]
                   elif $chunk_row[6] == true then
                     ["Entity row is flagged Is_Binary — content was never stored, cannot validate."]
                   else
                     ($chunk_row[2] | try (fromjson) as $edoc | (
                        (if $edoc.Format_Version == "104" then [] else ["Entity Format_Version must be \"104\"."] end)
                        + (if $edoc.Records_Type == [$entity_name] then [] else ["Entity Records_Type must be exactly [\"\($entity_name)\"]."] end)
                        + (if ($edoc | has("Parent_Hierarchy")) then [] else ["Entity is missing mandatory \"Parent_Hierarchy\" key."] end)
                     ) catch ["Entity file content is not valid JSON."])
                   end)
              )
            }
            | . + {"valid": (.errors | length == 0)}
          ],
          "errors": (
            (if $fmt_ok then [] else ["Manifest Format_Version must be \"104a\"."] end)
            + (if $rt_ok then [] else ["Manifest Records_Type must be exactly [\"mfdb\"]."] end)
          ),
          "warnings": []
        }
        | . + {"valid": ((.errors | length == 0) and (.entities | all(.valid)))}
        end'
}

# Export functions
export -f mfdb_validator_validate_archive
export -f mfdb_validator_validate_manifest
export -f mfdb_validator_validate_entity_file
export -f mfdb_validator_validate_database
export -f mfdb_validator_reset_state
export -f mfdb_validator_has_errors
export -f mfdb_validator_get_errors
export -f mfdb_validator_check_dependencies
export -f mfdb_validator_is_mfdb132_package
export -f mfdb_validator_validate_mfdb132_package
export -f mfdb_validator_detect_mfdb_in_chunk

#-------------------------------------------------------------------------------
# Phase 6 -- 105-series referential integrity audit (2026-10-03)
#-------------------------------------------------------------------------------
[[ -v E_MFDB_FK_TARGET_ENTITY_UNKNOWN ]] || readonly E_MFDB_FK_TARGET_ENTITY_UNKNOWN=43
[[ -v E_MFDB_FK_INVALID_ON_DELETE     ]] || readonly E_MFDB_FK_INVALID_ON_DELETE=47

# mfdb_validator_check_referential_integrity <manifest_path>
# Standalone, read-only, whole-database FK audit. Independent of the live
# Ref_Integrity switch. 104-series entities are never inspected. Prints one
# line per problem:  CODE<TAB>entity<TAB>detail   Returns 0 if sound, else 1.
mfdb_validator_check_referential_integrity() {
    local manifest_path="$1"
    if [[ ! -f "$manifest_path" ]]; then
        echo "ERROR: Manifest not found: $manifest_path" >&2
        return $E_MFDB_MANIFEST_NOT_FOUND
    fi
    local rc=0 en_idx fp_idx
    en_idx=$(jq -r '.Fields | map(.name) | index("entity_name") // -1' "$manifest_path" 2>/dev/null)
    fp_idx=$(jq -r '.Fields | map(.name) | index("file_path") // -1' "$manifest_path" 2>/dev/null)
    if [[ -z "$en_idx" || "$en_idx" -lt 0 || -z "$fp_idx" || "$fp_idx" -lt 0 ]]; then
        echo "ERROR: Manifest Fields must include entity_name and file_path" >&2
        return 1
    fi

    local -A ri_known=() ri_path=()
    local name rel resolved
    while IFS=$'\t' read -r name rel; do
        [[ -z "$name" ]] && continue
        ri_known["$name"]=1
        resolved=$(__mfdb_resolve_entity_path "$manifest_path" "$rel")
        if [[ -f "$resolved" ]] && jq -e . "$resolved" >/dev/null 2>&1; then
            ri_path["$name"]="$resolved"
        else
            printf 'E_MFDB_ENTITY_NOT_FOUND\t%s\tcould not load entity file: %s\n' "$name" "$resolved"
            rc=1
        fi
    done < <(jq -r --argjson ei "$en_idx" --argjson fi "$fp_idx" '.Values[] | [.[$ei], .[$fi]] | @tsv' "$manifest_path")

    local ename epath ever
    while IFS= read -r ename; do
        [[ -z "$ename" ]] && continue
        epath="${ri_path[$ename]}"
        ever=$(jq -r '.Format_Version' "$epath")
        case "$ever" in 105|105a|105db) ;; *) continue ;; esac
        local uuid_col=0 offset=1
        [[ "$ever" == "105db" ]] && { uuid_col=1; offset=2; }

        local fk_name fk_target fk_on_delete fk_idx
        while IFS=$'\t' read -r fk_name fk_target fk_on_delete fk_idx; do
            [[ -z "$fk_name" ]] && continue
            case "$fk_on_delete" in
                restrict|cascade|null) ;;
                *)
                    printf 'E_MFDB_FK_INVALID_ON_DELETE\t%s\t%s.%s: fk_on_delete=%s is not restrict/cascade/null\n' \
                        "$ename" "$ename" "$fk_name" "$fk_on_delete"
                    rc=1; continue ;;
            esac
            if [[ -z "${ri_known[$fk_target]:-}" ]]; then
                printf 'E_MFDB_FK_TARGET_ENTITY_UNKNOWN\t%s\t%s.%s: fk_target_entity %s is not registered in this manifest\n' \
                    "$ename" "$ename" "$fk_name" "$fk_target"
                rc=1; continue
            fi
            local tpath="${ri_path[$fk_target]:-}" tver=""
            [[ -n "$tpath" ]] && tver=$(jq -r '.Format_Version' "$tpath")
            case "$tver" in
                105|105a|105db) ;;
                *)
                    printf 'E_MFDB_FK_TARGET_ENTITY_UNKNOWN\t%s\t%s.%s: target entity %s is not a 105-series entity\n' \
                        "$ename" "$ename" "$fk_name" "$fk_target"
                    rc=1; continue ;;
            esac
            local tcol=0
            [[ "$tver" == "105db" ]] && tcol=1
            local tuuids
            tuuids=$(jq -c --argjson c "$tcol" '[.Values[] | select(length > $c) | .[$c]]' "$tpath")

            local ref_uuid fk_val
            while IFS=$'\t' read -r ref_uuid fk_val; do
                [[ -z "$ref_uuid" && -z "$fk_val" ]] && continue
                printf 'E_MFDB_FK_UNRESOLVED\t%s\t%s#%s.%s = %s does not exist in %s\n' \
                    "$ename" "$ename" "$ref_uuid" "$fk_name" "$fk_val" "$fk_target"
                rc=1
            done < <(jq -r --argjson col "$((fk_idx + offset))" --argjson uc "$uuid_col" --argjson tu "$tuuids" '
                .Values[]
                | select(length > $col)
                | select(.[$col] != null)
                | select(.[$col] as $v | ($tu | index($v)) == null)
                | [(if length > $uc then .[$uc] else "?" end), (.[$col] | tostring)] | @tsv' "$epath")
        done < <(jq -r '.Fields | to_entries[] | select(.value.fk_target_entity) |
                [.value.name, .value.fk_target_entity, (.value.fk_on_delete // "restrict"), .key] | @tsv' "$epath")
    done < <(printf '%s\n' "${!ri_path[@]}" | sort)

    return $rc
}
export -f mfdb_validator_check_referential_integrity
