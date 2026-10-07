# Library:        lib_bejson_Core_mfdb_core.sh
# Family:         Core
# Description:    Multi-file database orchestrator managing manifests and entity synchronization.
# Version:        2.3.0
# Date:           2026-10-03
# Author:         Elton Boehnen
# Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
# Format_Creator: Elton Boehnen
# RELATIONAL_ID:  dd8382e6-75ce-47a9-bd63-41642a317656
# Release_Version: 300
#
# FEATURE (2026-10-03): Phase 6 SH port -- 105-series Referential Integrity.
# mfdb_core_enable/disable/is_ref_integrity_enabled, mfdb_core_check_fk_write,
# mfdb_core_find_referencing_rows, mfdb_core_check_entity_droppable and the
# uuid-addressed CRUD entry points mfdb_core_add/update/delete_entity_record_105
# (restrict / cascade / null, cycle-guarded). Semantics mirror PY Phase 6
# (including: dependents are resolved on disk as the walk proceeds, and a record
# reachable twice in one cascade is reported as E_MFDB_FK_CASCADE_CYCLE).
# NOTE: no PID lock in SH here (single-process synchronous jq + mv, same as
# mfdb_core_add_entity_record above). value arguments: an empty string or the
# literal `null` means SQL-null; any other string is a record_uuid.
#
# FEATURE (2026-07-31): Meta-GUID debug entity system — full Bash port.
# mfdb_core_enable_debug, mfdb_core_disable_debug, mfdb_core_get_debug_log,
# mfdb_core_get_failed_ops, mfdb_core_clear_debug_log, mfdb_core_debug_summary,
# mfdb_core_detect_schema_drift. Internal _mfdb_meta_log direct writer gated
# by Debug_Mode manifest header — zero overhead when off.
#
# FEATURE (2026-07-29): Network_Role parameter added to mfdb_core_create_database
# (arg $7, default "Standalone"). Federation functions added:
# mfdb_federation_push_config, mfdb_federation_poll_dropzone,
# mfdb_federation_distill_logs, mfdb_core_create_connected_slave_entity.

# NOTE: set -o nounset intentionally omitted — library files must not modify
# global shell options; doing so breaks host scripts that source this file. (SH3)
set -o pipefail

# Source dependencies if not already loaded.
_MFDB_CORE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! declare -f bejson_core_atomic_write > /dev/null 2>&1; then
    # shellcheck source=./lib_bejson_Core_bejson_core.sh
    source "${_MFDB_CORE_DIR}/lib_bejson_Core_bejson_core.sh"
fi

if ! declare -f mfdb_validator_validate_manifest > /dev/null 2>&1; then
    # shellcheck source=./lib_bejson_Core_mfdb_validator.sh
    source "${_MFDB_CORE_DIR}/lib_bejson_Core_mfdb_validator.sh"
fi

#-------------------------------------------------------------------------------
# Error codes (50–79)
#-------------------------------------------------------------------------------

# Error codes sourced from lib_bejson_Core_bejson_errors.sh (via bejson_core.sh chain).
# Local guards remain as fallback for scripts that source mfdb_core.sh directly.
[[ -v E_MFDB_CORE_MANIFEST_NOT_FOUND ]] || readonly E_MFDB_CORE_MANIFEST_NOT_FOUND=50
[[ -v E_MFDB_CORE_ENTITY_NOT_FOUND   ]] || readonly E_MFDB_CORE_ENTITY_NOT_FOUND=51
[[ -v E_MFDB_CORE_WRITE_FAILED       ]] || readonly E_MFDB_CORE_WRITE_FAILED=52
[[ -v E_MFDB_CORE_LOCK_FAILED        ]] || readonly E_MFDB_CORE_LOCK_FAILED=53
[[ -v E_MFDB_CORE_INVALID_OPERATION  ]] || readonly E_MFDB_CORE_INVALID_OPERATION=54
[[ -v E_MFDB_CORE_INDEX_OUT_OF_BOUNDS ]] || readonly E_MFDB_CORE_INDEX_OUT_OF_BOUNDS=55
[[ -v E_MFDB_CORE_ARCHIVE_ERROR      ]] || readonly E_MFDB_CORE_ARCHIVE_ERROR=70
[[ -v E_MFDB_CORE_MOUNT_CONFLICT     ]] || readonly E_MFDB_CORE_MOUNT_CONFLICT=71
[[ -v E_MFDB_CORE_CREATE_FAILED      ]] || readonly E_MFDB_CORE_CREATE_FAILED=72

#-------------------------------------------------------------------------------
# MFDBArchive (v1.2 Feature)
#-------------------------------------------------------------------------------

# mfdb_archive_mount <archive_path> <target_dir> [force]
# Extracts archive to workspace and creates session lock.
mfdb_archive_mount() {
    local archive_path="$1"
    local target_dir="$2"
    local force="${3:-false}"

    if [[ ! -f "$archive_path" ]]; then
        echo "ERROR: Archive not found: $archive_path" >&2
        return $E_MFDB_CORE_ARCHIVE_ERROR
    fi

    local lock_file="$target_dir/.mfdb_lock"
    if [[ -f "$lock_file" && "$force" != "true" ]]; then
        local old_pid
        old_pid=$(jq -r '.pid' "$lock_file")
        if kill -0 "$old_pid" 2>/dev/null; then
            echo "ERROR: Workspace $target_dir is locked by active PID $old_pid" >&2
            return $E_MFDB_CORE_MOUNT_CONFLICT
        fi
    fi

    mkdir -p "$target_dir"
    unzip -q -o "$archive_path" -d "$target_dir" || {
        echo "ERROR: Extraction failed for $archive_path" >&2
        return $E_MFDB_CORE_ARCHIVE_ERROR
    }

    if [[ ! -f "$target_dir/104a.mfdb.bejson" ]]; then
        echo "ERROR: Invalid MFDB Archive: manifest missing" >&2
        rm -rf "$target_dir"
        return $E_MFDB_CORE_ARCHIVE_ERROR
    fi

    local hash
    hash=$(sha256sum "$archive_path" | awk '{print $1}')
    
    jq -n \
        --arg pid "$$" \
        --arg path "$(realpath "$archive_path")" \
        --arg hash "$hash" \
        --arg time "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
        '{pid: $pid|tonumber, archive_path: $path, original_hash: $hash, mounted_at: $time}' \
        > "$lock_file"

    echo "$(realpath "$target_dir/104a.mfdb.bejson")"
}

# mfdb_archive_commit <mount_dir> [archive_path]
# Repacks workspace into .mfdb.zip atomically.
mfdb_archive_commit() {
    local mount_dir="$1"
    local archive_path="${2:-}"
    local lock_file="$mount_dir/.mfdb_lock"

    if [[ ! -f "$lock_file" ]]; then
        echo "ERROR: No active mount session in $mount_dir" >&2
        return $E_MFDB_CORE_INVALID_OPERATION
    fi

    local dest
    if [[ -n "$archive_path" ]]; then
        dest="$archive_path"
    else
        dest=$(jq -r '.archive_path' "$lock_file")
    fi

    local tmp_zip
    tmp_zip="${TMPDIR:-/tmp}/mfdb_commit_$$.zip"
    rm -f "$tmp_zip"

    (cd "$mount_dir" && zip -r -q "$tmp_zip" . -x ".mfdb_lock") || {
        rm -f "$tmp_zip"
        echo "ERROR: Repack failed for $mount_dir" >&2
        return $E_MFDB_CORE_WRITE_FAILED
    }

    mv "$tmp_zip" "$dest" || {
        rm -f "$tmp_zip"
        echo "ERROR: Atomic swap failed for $dest" >&2
        return $E_MFDB_CORE_WRITE_FAILED
    }

    local new_hash
    new_hash=$(sha256sum "$dest" | awk '{print $1}')
    local tmp_lock
    tmp_lock=$(mktemp)
    jq --arg h "$new_hash" '.original_hash = $h' "$lock_file" > "$tmp_lock" && mv "$tmp_lock" "$lock_file"

    echo "$(realpath "$dest")"
}

# mfdb_archive_unmount <mount_dir> [cleanup]
mfdb_archive_unmount() {
    local mount_dir="$1"
    local cleanup="${2:-true}"
    local lock_file="$mount_dir/.mfdb_lock"

    [[ -f "$lock_file" ]] && rm -f "$lock_file"
    [[ "$cleanup" == "true" && -d "$mount_dir" ]] && rm -rf "$mount_dir"
}

#-------------------------------------------------------------------------------
# Discovery
#-------------------------------------------------------------------------------

# mfdb_core_discover <file_path>
# Prints: 'manifest', 'entity', 'archive', or 'standalone'
mfdb_core_discover() {
    local file_path="$1"

    if [[ ! -f "$file_path" ]]; then
        echo "ERROR: File not found: $file_path" >&2
        return $E_MFDB_CORE_MANIFEST_NOT_FOUND
    fi

    if [[ "$file_path" == *".mfdb.zip" ]]; then
        echo "archive"
        return 0
    fi

    local version filename
    version="$(jq -r '.Format_Version // empty' "$file_path" 2>/dev/null)"
    filename="$(basename "$file_path")"

    if [[ "$version" == "104a" && "$filename" == *".mfdb.bejson" ]]; then
        echo "manifest"
    elif [[ "$version" == "104" ]]; then
        local ph
        ph="$(jq -r '.Parent_Hierarchy // empty' "$file_path" 2>/dev/null)"
        if [[ -n "$ph" ]]; then
            echo "entity"
        else
            echo "standalone"
        fi
    else
        echo "standalone"
    fi
}

#-------------------------------------------------------------------------------
# Internal helpers
#-------------------------------------------------------------------------------

__mfdb_core_resolve() {
    local manifest_path="$1"
    local file_path_rel="$2"
    local manifest_dir
    manifest_dir="$(cd "$(dirname "$manifest_path")" && pwd)"
    realpath -m "$manifest_dir/$file_path_rel" 2>/dev/null || echo "$manifest_dir/$file_path_rel"
}

__mfdb_field_index() {
    local file_path="$1"
    local field_name="$2"
    # Self-maintaining cache: a hit reads neither the file nor jq.
    bejson_core_get_field_index_file "$file_path" "$field_name"
}

__mfdb_core_en_idx() {
    __mfdb_field_index "$1" "entity_name"
}

__mfdb_core_fp_idx() {
    __mfdb_field_index "$1" "file_path"
}

__mfdb_core_get_file_path() {
    local manifest_path="$1"
    local entity_name="$2"
    local en_idx fp_idx
    en_idx="$(__mfdb_core_en_idx "$manifest_path")"
    fp_idx="$(__mfdb_core_fp_idx "$manifest_path")"
    jq -r --argjson ei "$en_idx" --argjson fi "$fp_idx" --arg en "$entity_name" \
        '.Values[] | select(.[$ei] == $en) | .[$fi] // empty' \
        "$manifest_path" 2>/dev/null | head -n1
}

#-------------------------------------------------------------------------------
# Dependency check
#-------------------------------------------------------------------------------

mfdb_core_check_dependencies() {
    mfdb_validator_check_dependencies || return $?
    if ! declare -f bejson_core_atomic_write > /dev/null 2>&1; then
        echo "ERROR: lib_bejson_Core_bejson_core.sh must be sourced before lib_bejson_Core_mfdb_core.sh" >&2
        return 1
    fi
    for cmd in unzip zip sha256sum; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            echo "ERROR: Required command '$cmd' not found" >&2
            return 1
        fi
    done
    return 0
}

#-------------------------------------------------------------------------------
# Read operations
#-------------------------------------------------------------------------------

mfdb_core_load_manifest() {
    local manifest_path="$1"
    if ! mfdb_validator_validate_manifest "$manifest_path"; then
        echo "ERROR: Manifest validation failed: $manifest_path" >&2
        return $E_MFDB_CORE_MANIFEST_NOT_FOUND
    fi
    jq -r '.Values[] | @tsv' "$manifest_path" 2>/dev/null
}

mfdb_core_list_entities() {
    local manifest_path="$1"
    local en_idx
    en_idx="$(__mfdb_core_en_idx "$manifest_path")"
    jq -r --argjson ei "$en_idx" '.Values[] | .[$ei] // empty' "$manifest_path" 2>/dev/null
}

mfdb_core_load_entity() {
    local manifest_path="$1"
    local entity_name="$2"
    local file_path_rel
    file_path_rel="$(__mfdb_core_get_file_path "$manifest_path" "$entity_name")"
    if [[ -z "$file_path_rel" ]]; then
        echo "ERROR: Entity '$entity_name' not found in manifest" >&2
        return $E_MFDB_CORE_ENTITY_NOT_FOUND
    fi
    local resolved
    resolved="$(__mfdb_core_resolve "$manifest_path" "$file_path_rel")"
    if [[ ! -f "$resolved" ]]; then
        echo "ERROR: Entity file not found: $resolved" >&2
        return $E_MFDB_CORE_ENTITY_NOT_FOUND
    fi
    jq -r '[.Fields[].name] | @tsv' "$resolved" 2>/dev/null
    jq -r '.Values[] | @tsv' "$resolved" 2>/dev/null
}

mfdb_core_get_entity_path() {
    local manifest_path="$1"
    local entity_name="$2"
    local file_path_rel
    file_path_rel="$(__mfdb_core_get_file_path "$manifest_path" "$entity_name")"
    if [[ -z "$file_path_rel" ]]; then
        echo "ERROR: Entity '$entity_name' not found in manifest" >&2
        return $E_MFDB_CORE_ENTITY_NOT_FOUND
    fi
    __mfdb_core_resolve "$manifest_path" "$file_path_rel"
}

mfdb_core_get_stats() {
    local manifest_path="$1"
    local db_name schema_version
    db_name="$(jq -r '.DB_Name // "N/A"' "$manifest_path" 2>/dev/null)"
    schema_version="$(jq -r '.Schema_Version // "N/A"' "$manifest_path" 2>/dev/null)"
    echo "=== MFDB Stats ==="
    echo "DB Name        : $db_name"
    echo "Schema Version : $schema_version"
    echo "Manifest       : $manifest_path"
    echo ""
    local en_idx fp_idx
    en_idx="$(__mfdb_core_en_idx "$manifest_path")"
    fp_idx="$(__mfdb_core_fp_idx "$manifest_path")"
    local entity_count=0
    while IFS=$'\t' read -r entity_name file_path_rel; do
        entity_count=$((entity_count + 1))
        local resolved
        resolved="$(__mfdb_core_resolve "$manifest_path" "$file_path_rel")"
        local rec_count="?"
        if [[ -f "$resolved" ]]; then
            rec_count="$(jq -r '.Values | length' "$resolved" 2>/dev/null)"
        fi
        printf "  %-24s  %-36s  records: %s\n" "$entity_name" "$file_path_rel" "$rec_count"
    done < <(jq -r --argjson ei "$en_idx" --argjson fi "$fp_idx" \
        '.Values[] | [.[$ei] // "null", .[$fi] // "null"] | @tsv' \
        "$manifest_path" 2>/dev/null)
    echo ""
    echo "Total entities : $entity_count"
}

#-------------------------------------------------------------------------------
# Write operations
#-------------------------------------------------------------------------------

mfdb_core_add_entity_record() {
    local manifest_path="$1"
    local entity_name="$2"
    local json_values_array="$3"
    local file_path_rel
    file_path_rel="$(__mfdb_core_get_file_path "$manifest_path" "$entity_name")"
    if [[ -z "$file_path_rel" ]]; then
        echo "ERROR: Entity '$entity_name' not found in manifest" >&2
        return $E_MFDB_CORE_ENTITY_NOT_FOUND
    fi
    local resolved
    resolved="$(__mfdb_core_resolve "$manifest_path" "$file_path_rel")"
    if [[ ! -f "$resolved" ]]; then
        echo "ERROR: Entity file not found: $resolved" >&2
        return $E_MFDB_CORE_ENTITY_NOT_FOUND
    fi
    if ! echo "$json_values_array" | jq -e 'if type == "array" then true else error end' > /dev/null 2>&1; then
        echo "ERROR: json_values_array must be a JSON array string" >&2
        return $E_MFDB_CORE_INVALID_OPERATION
    fi
    local tmp_file
    tmp_file="$(mktemp "${resolved}.tmp.XXXXXX")"
    if ! jq --argjson row "$json_values_array" '.Values += [$row]' "$resolved" > "$tmp_file" 2>/dev/null; then
        rm -f "$tmp_file"
        echo "ERROR: Failed to append record to $resolved" >&2
        return $E_MFDB_CORE_WRITE_FAILED
    fi
    mv "$tmp_file" "$resolved"
    mfdb_core_sync_manifest_count "$manifest_path" "$entity_name"
}

mfdb_core_remove_entity_record() {
    local manifest_path="$1"
    local entity_name="$2"
    local record_index="$3"
    local file_path_rel
    file_path_rel="$(__mfdb_core_get_file_path "$manifest_path" "$entity_name")"
    if [[ -z "$file_path_rel" ]]; then
        echo "ERROR: Entity '$entity_name' not found in manifest" >&2
        return $E_MFDB_CORE_ENTITY_NOT_FOUND
    fi
    local resolved
    resolved="$(__mfdb_core_resolve "$manifest_path" "$file_path_rel")"
    if [[ ! -f "$resolved" ]]; then
        echo "ERROR: Entity file not found: $resolved" >&2
        return $E_MFDB_CORE_ENTITY_NOT_FOUND
    fi
    local rec_count
    rec_count="$(jq -r '.Values | length' "$resolved" 2>/dev/null)"
    if [[ "$record_index" -lt 0 || "$record_index" -ge "$rec_count" ]]; then
        echo "ERROR: Record index $record_index is out of bounds (count: $rec_count)" >&2
        return $E_MFDB_CORE_INDEX_OUT_OF_BOUNDS
    fi
    local tmp_file
    tmp_file="$(mktemp "${resolved}.tmp.XXXXXX")"
    if ! jq --argjson ri "$record_index" 'del(.Values[$ri])' "$resolved" > "$tmp_file" 2>/dev/null; then
        rm -f "$tmp_file"
        echo "ERROR: Failed to remove record $record_index from $resolved" >&2
        return $E_MFDB_CORE_WRITE_FAILED
    fi
    mv "$tmp_file" "$resolved"
    mfdb_core_sync_manifest_count "$manifest_path" "$entity_name"
}

#-------------------------------------------------------------------------------
# Manifest sync
#-------------------------------------------------------------------------------

mfdb_core_sync_manifest_count() {
    local manifest_path="$1"
    local entity_name="$2"
    local file_path_rel
    file_path_rel="$(__mfdb_core_get_file_path "$manifest_path" "$entity_name")"
    [[ -z "$file_path_rel" ]] && return $E_MFDB_CORE_ENTITY_NOT_FOUND
    local resolved
    resolved="$(__mfdb_core_resolve "$manifest_path" "$file_path_rel")"
    [[ ! -f "$resolved" ]] && return $E_MFDB_CORE_ENTITY_NOT_FOUND
    local actual_count
    actual_count="$(jq -r '.Values | length' "$resolved" 2>/dev/null)"
    local en_idx rc_idx
    en_idx="$(__mfdb_core_en_idx "$manifest_path")"
    rc_idx="$(__mfdb_field_index "$manifest_path" "record_count")"
    [[ "$rc_idx" == "-1" ]] && return 0
    local tmp_file
    tmp_file="$(mktemp "${manifest_path}.tmp.XXXXXX")"
    if ! jq --argjson ei "$en_idx" --argjson ri "$rc_idx" \
            --arg en "$entity_name" --argjson count "$actual_count" \
            '(.Values[] | select(.[$ei] == $en) | .[$ri]) = $count' \
            "$manifest_path" > "$tmp_file" 2>/dev/null; then
        rm -f "$tmp_file"
        return $E_MFDB_CORE_WRITE_FAILED
    fi
    mv "$tmp_file" "$manifest_path"
    echo "$actual_count"
}

mfdb_core_sync_all_counts() {
    local manifest_path="$1"
    while IFS= read -r entity_name; do
        local count
        count="$(mfdb_core_sync_manifest_count "$manifest_path" "$entity_name")"
        printf "%-24s  %s records\n" "$entity_name" "$count"
    done < <(mfdb_core_list_entities "$manifest_path")
}

#-------------------------------------------------------------------------------
# Database creation
#-------------------------------------------------------------------------------

mfdb_core_create_entity_file() {
    local manifest_path="$1"
    local entity_name="$2"
    local fields_json="$3"
    local description="${4:-}"
    local primary_key="${5:-}"
    local schema_version="${6:-1.0}"
    local file_path_rel="${7:-}"
    if [[ -z "$file_path_rel" ]]; then
        file_path_rel="data/$(echo "$entity_name" | tr '[:upper:]' '[:lower:]').bejson"
    fi
    local manifest_dir resolved entity_dir rel_to_manifest
    manifest_dir="$(cd "$(dirname "$manifest_path")" && pwd)"
    resolved="$(realpath -m "$manifest_dir/$file_path_rel" 2>/dev/null || echo "$manifest_dir/$file_path_rel")"
    entity_dir="$(dirname "$resolved")"
    mkdir -p "$entity_dir"
    rel_to_manifest="$(realpath --relative-to="$entity_dir" "$manifest_path" 2>/dev/null || echo "../$(basename "$manifest_path")")"
    local tmp_entity
    tmp_entity="$(mktemp "${resolved}.tmp.XXXXXX")"
    jq -n \
        --arg en "$entity_name" \
        --arg ph "$rel_to_manifest" \
        --argjson fields "$fields_json" \
        '{
            "Format":           "BEJSON",
            "Format_Version":   "104",
            "Format_Creator":   "Elton Boehnen",
            "Parent_Hierarchy": $ph,
            "Records_Type":     [$en],
            "Fields":           $fields,
            "Values":           []
        }' > "$tmp_entity" 2>/dev/null && mv "$tmp_entity" "$resolved"
    local en_idx fp_idx
    en_idx="$(__mfdb_core_en_idx "$manifest_path")"
    fp_idx="$(__mfdb_core_fp_idx "$manifest_path")"
    local new_row_json
    new_row_json="$(jq -r \
        --arg en "$entity_name" \
        --arg fp "$file_path_rel" \
        --arg desc "${description:-null}" \
        --arg pk "${primary_key:-null}" \
        --arg sv "$schema_version" \
        '[.Fields[].name] | map(
            if . == "entity_name"    then $en
            elif . == "file_path"    then $fp
            elif . == "description"  then (if $desc == "null" then null else $desc end)
            elif . == "record_count" then 0
            elif . == "schema_version" then $sv
            elif . == "primary_key"  then (if $pk == "null" then null else $pk end)
            else null
            end
        )' "$manifest_path" 2>/dev/null)"
    local tmp_manifest
    tmp_manifest="$(mktemp "${manifest_path}.tmp.XXXXXX")"
    jq --argjson row "$new_row_json" '.Values += [$row]' "$manifest_path" > "$tmp_manifest" && mv "$tmp_manifest" "$manifest_path"
    echo "$resolved"
}

mfdb_core_create_database() {
    local root_dir="$1"
    local db_name="$2"
    local db_description="${3:-}"
    local entities_json="$4"
    local schema_version="${5:-1.0.0}"
    local author="${6:-Elton Boehnen}"
    local network_role="${7:-Standalone}"   # "Master" | "Slave" | "Standalone"
    mkdir -p "$root_dir"
    local manifest_path="$root_dir/104a.mfdb.bejson"
    local created_at
    created_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")"
    # Build manifest Values from entities_json.
    local manifest_values_json
    manifest_values_json="$(echo "$entities_json" | jq -c \
        '[.[] | [
            .name,
            (.file_path // ("data/" + (.name | ascii_downcase) + ".bejson")),
            (.description // null),
            0,
            (.schema_version // "1.0"),
            (.primary_key // null)
        ]]')"

    local tmp_manifest
    tmp_manifest="$(mktemp "${manifest_path}.tmp.XXXXXX")"

    if ! jq -n \
        --arg db_name "$db_name" \
        --arg db_desc "$db_description" \
        --arg sv "$schema_version" \
        --arg author "$author" \
        --arg created_at "$created_at" \
        --arg network_role "$network_role" \
        --argjson values "$manifest_values_json" \
        '{
            "Format":          "BEJSON",
            "Format_Version":  "104a",
            "Format_Creator":  "Elton Boehnen",
            "MFDB_Version":    "1.31",
            "Network_Role":    $network_role,
            "DB_Name":         $db_name,
            "DB_Description":  $db_desc,
            "Schema_Version":  $sv,
            "Author":          $author,
            "Created_At":      $created_at,
            "Records_Type":    ["mfdb"],
            "Fields": [
                {"name":"entity_name",    "type":"string"},
                {"name":"file_path",      "type":"string"},
                {"name":"description",    "type":"string"},
                {"name":"record_count",   "type":"integer"},
                {"name":"schema_version", "type":"string"},
                {"name":"primary_key",    "type":"string"}
            ],
            "Values": $values
        }' > "$tmp_manifest"; then
        rm -f "$tmp_manifest"
        echo "ERROR: Failed to generate manifest JSON" >&2
        return $E_MFDB_CORE_CREATE_FAILED
    fi

    mv "$tmp_manifest" "$manifest_path"

    local entity_count
    entity_count="$(echo "$entities_json" | jq -r 'length')"
    for (( i=0; i<entity_count; i++ )); do
        local ename fp_rel efields
        ename="$(echo "$entities_json" | jq -r ".[$i].name" 2>/dev/null)"
        fp_rel="$(echo "$entities_json" | jq -r ".[$i].file_path // (\"data/\" + (.[$i].name | ascii_downcase) + \".bejson\")" 2>/dev/null)"
        efields="$(echo "$entities_json" | jq -c ".[$i].fields" 2>/dev/null)"
        local resolved entity_dir rel_to_manifest
        resolved="$(realpath -m "$root_dir/$fp_rel" 2>/dev/null || echo "$root_dir/$fp_rel")"
        entity_dir="$(dirname "$resolved")"
        mkdir -p "$entity_dir"
        rel_to_manifest="$(realpath --relative-to="$entity_dir" "$manifest_path" 2>/dev/null || echo "../$(basename "$manifest_path")")"
        local tmp_entity
        tmp_entity="$(mktemp "${resolved}.tmp.XXXXXX")"
        jq -n \
            --arg en "$ename" \
            --arg ph "$rel_to_manifest" \
            --argjson fields "$efields" \
            '{
                "Format":           "BEJSON",
                "Format_Version":   "104",
                "Format_Creator":   "Elton Boehnen",
                "Parent_Hierarchy": $ph,
                "Records_Type":     [$en],
                "Fields":           $fields,
                "Values":           []
            }' > "$tmp_entity" 2>/dev/null && mv "$tmp_entity" "$resolved"
    done
    echo "$manifest_path"
}

# Export functions
export -f mfdb_archive_mount
export -f mfdb_archive_commit
export -f mfdb_archive_unmount
export -f mfdb_core_check_dependencies
export -f mfdb_core_discover
export -f mfdb_core_load_manifest
export -f mfdb_core_list_entities
export -f mfdb_core_load_entity
export -f mfdb_core_get_entity_path
export -f mfdb_core_get_stats
export -f mfdb_core_add_entity_record
export -f mfdb_core_remove_entity_record
export -f mfdb_core_sync_manifest_count
export -f mfdb_core_sync_all_counts
export -f mfdb_core_create_entity_file
export -f mfdb_core_create_database

# ── Federated Master / Slave node system ───────────────────────────────────────
# Network_Role ("Master"|"Slave"|"Standalone") is now emitted on
# mfdb_core_create_database. This block wires the full runtime federation
# protocol: ConnectedSlave entity creator, Master→Slave atomic push,
# Slave dropzone poller, and Slave→Master log distillation.

# mfdb_core_create_connected_slave_entity <manifest_path>
# Creates the ConnectedSlave entity file and registers it in the manifest.
# Fails if Network_Role != "Master".
mfdb_core_create_connected_slave_entity() {
    local manifest_path="$1"
    local role
    role=$(jq -r '.Network_Role // ""' "$manifest_path" 2>/dev/null)
    if [[ "$role" != "Master" ]]; then
        echo "[MFDB_FEDERATION] ERROR: ConnectedSlave may only be created on a Master node. Got: '$role'" >&2
        return 1
    fi

    local fields_json='[
        {"name":"slave_id",           "type":"string"},
        {"name":"label",              "type":"string"},
        {"name":"url",                "type":"string"},
        {"name":"role",               "type":"string"},
        {"name":"status",             "type":"string"},
        {"name":"supported_entities", "type":"array"}
    ]'
    mfdb_core_create_entity_file \
        "$manifest_path" "ConnectedSlave" "$fields_json" \
        "Registry of Slave nodes connected to this Master." "slave_id"
}
export -f mfdb_core_create_connected_slave_entity

# mfdb_federation_push_config <config_json_string> <slave_target_path>
# Master → Slave atomic drop-zone push. Writes config via same-dir temp + mv.
# Returns 0 on success, 1 on error.
mfdb_federation_push_config() {
    local config_json="$1"
    local slave_target_path="$2"
    local dest_dir
    dest_dir="$(dirname "$slave_target_path")"
    mkdir -p "$dest_dir"
    local temp_path="$slave_target_path.tmp.$$"
    if echo "$config_json" > "$temp_path" && mv "$temp_path" "$slave_target_path"; then
        return 0
    else
        rm -f "$temp_path"
        echo "[MFDB_FEDERATION] ERROR: push_config failed for $slave_target_path" >&2
        return 1
    fi
}
export -f mfdb_federation_push_config

# mfdb_federation_poll_dropzone <dropzone_dir> <handler_function> [poll_interval_sec=2] [timeout_sec=60]
# Slave: polls dropzone_dir for incoming .bejson files from Master.
# Each file is passed to handler_function <file_path> then removed.
# handler_function must be exported with export -f.
# Returns count of configs processed on stdout.
mfdb_federation_poll_dropzone() {
    local dropzone_dir="$1"
    local handler_fn="$2"
    local poll_interval="${3:-2}"
    local timeout="${4:-60}"
    mkdir -p "$dropzone_dir"

    local processed=0
    local deadline=$(( $(date +%s) + timeout ))

    while [[ "$(date +%s)" -lt "$deadline" ]]; do
        for fpath in "$dropzone_dir"/*.bejson; do
            [[ -f "$fpath" ]] || continue
            if "$handler_fn" "$fpath"; then
                rm -f "$fpath"
                (( processed++ )) || true
            else
                echo "[MFDB_FEDERATION] poll_dropzone: handler failed for $fpath" >&2
            fi
        done
        sleep "$poll_interval"
    done

    echo "$processed"
}
export -f mfdb_federation_poll_dropzone

# mfdb_federation_distill_logs <slave_manifest_path> <entity_name> <master_poll_dir> [max_rows=100]
# Slave → Master one-way log push. Overflow rows pushed as distilled summary,
# local entity truncated to max_rows. Returns 0 on success, 1 on error.
mfdb_federation_distill_logs() {
    local slave_manifest="$1"
    local entity_name="$2"
    local master_poll_dir="$3"
    local max_rows="${4:-100}"

    # Resolve entity file path
    local entity_path
    entity_path=$(mfdb_core_get_entity_path "$slave_manifest" "$entity_name" 2>/dev/null)
    [[ -z "$entity_path" || ! -f "$entity_path" ]] && {
        echo "[MFDB_FEDERATION] ERROR: entity '$entity_name' not found." >&2; return 1
    }

    local total_rows
    total_rows=$(jq '.Values | length' "$entity_path" 2>/dev/null)
    [[ "$total_rows" -le "$max_rows" ]] && return 0  # Nothing to distill

    # Build overflow and kept arrays
    local overflow_json kept_json
    overflow_json=$(jq --argjson mr "$max_rows" '.Values[0:(.Values|length)-$mr]' "$entity_path")
    kept_json=$(jq --argjson mr "$max_rows" '.Values[(.Values|length)-$mr:]' "$entity_path")

    # Push distilled summary to Master poll dir
    mkdir -p "$master_poll_dir"
    local ts dest summary_json fields_json
    ts=$(date -u +"%Y%m%dT%H%M%SZ")
    dest="$master_poll_dir/distilled_${entity_name}_${ts}.bejson"
    fields_json=$(jq -c '.Fields' "$entity_path")

    summary_json=$(jq -n \
        --arg src "$entity_name" \
        --arg ts "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
        --argjson fields "$fields_json" \
        --argjson values "$overflow_json" \
        '{
            "Format":"BEJSON","Format_Version":"104a","Format_Creator":"Elton Boehnen",
            "Distill_Source":$src,"Distill_Timestamp":$ts,
            "Records_Type":["DistilledLog"],"Fields":$fields,"Values":$values
        }')

    mfdb_federation_push_config "$summary_json" "$dest" || return 1

    # Truncate local entity
    local tmp_entity
    tmp_entity="$(mktemp "${entity_path}.tmp.XXXXXX")"
    jq --argjson kept "$kept_json" '.Values = $kept' "$entity_path" > "$tmp_entity" \
        && mv "$tmp_entity" "$entity_path" \
        || { rm -f "$tmp_entity"; return 1; }

    # Update manifest record count
    mfdb_core_sync_manifest_count "$slave_manifest" "$entity_name"
    return 0
}
export -f mfdb_federation_distill_logs

# ── Meta-GUID Debug Entity System (Bash) ───────────────────────────────────────
# All functions gate on Debug_Mode manifest header. _mfdb_meta_log is a direct
# jq-based writer — bypasses mfdb_core_add_entity_record to prevent recursion.
# Requires jq >= 1.6.

_mfdb_debug_is_enabled() {
    local manifest_path="$1"
    local mode
    mode=$(jq -r '.Debug_Mode // "false"' "$manifest_path" 2>/dev/null)
    [[ "${mode,,}" == "true" ]]
}

_mfdb_debug_reads_enabled() {
    local manifest_path="$1"
    local flag
    flag=$(jq -r '.Debug_Reads // "false"' "$manifest_path" 2>/dev/null)
    [[ "${flag,,}" == "true" ]]
}

_mfdb_debug_get_meta_name() {
    jq -r '.Debug_Meta_Entity // ""' "$1" 2>/dev/null
}

_mfdb_debug_get_entity_path() {
    local manifest_path="$1"
    local entity_name="$2"
    local rel_path
    rel_path=$(jq -r --arg e "$entity_name" \
        '[.Fields | to_entries | .[] | select(.value.name=="entity_name") | .key][0] as $ei |
         [.Fields | to_entries | .[] | select(.value.name=="file_path") | .key][0] as $fi |
         .Values[] | select(.[$ei]==$e) | .[$fi]' \
        "$manifest_path" 2>/dev/null | head -1)
    [[ -z "$rel_path" ]] && return 1
    echo "$(dirname "$(realpath "$manifest_path")")/$rel_path"
}

# _mfdb_meta_log <manifest> <operation> <target_entity> <field_name|-> <field_exists|-> <row_index|-> <success:0|1> <duration_ms> <notes> [reads_only:0|1]
_mfdb_meta_log() {
    local manifest_path="$1"
    local operation="$2"
    local target_entity="$3"
    local field_name="${4:--}"
    local field_exists="${5:--}"    # "true", "false", or "-" (null)
    local row_index="${6:--}"       # integer or "-" (null)
    local success="${7:-1}"         # 1=true 0=false
    local duration_ms="${8:-0}"
    local notes="${9:-}"
    local reads_only="${10:-0}"

    _mfdb_debug_is_enabled "$manifest_path" || return 0
    if [[ "$reads_only" -eq 1 ]]; then
        _mfdb_debug_reads_enabled "$manifest_path" || return 0
    fi

    local meta_name
    meta_name=$(_mfdb_debug_get_meta_name "$manifest_path")
    [[ -z "$meta_name" ]] && return 0

    local meta_path
    meta_path=$(_mfdb_debug_get_entity_path "$manifest_path" "$meta_name") || return 0

    local ts
    ts=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")

    # Build null-safe values for optional fields
    local jq_field_name jq_field_exists jq_row_index
    [[ "$field_name"   == "-" ]] && jq_field_name="null"   || jq_field_name="\"$field_name\""
    [[ "$field_exists" == "-" ]] && jq_field_exists="null" || jq_field_exists="$field_exists"
    [[ "$row_index"    == "-" ]] && jq_row_index="null"    || jq_row_index="$row_index"
    local jq_success
    [[ "$success" -eq 1 ]] && jq_success="true" || jq_success="false"

    local tmp
    tmp=$(mktemp "${meta_path}.tmp.XXXXXX")
    jq --argjson ts "\"$ts\"" \
       --argjson op "\"$operation\"" \
       --argjson te "\"$target_entity\"" \
       --argjson fn "$jq_field_name" \
       --argjson fe "$jq_field_exists" \
       --argjson ri "$jq_row_index" \
       --argjson sc "$jq_success" \
       --argjson dm "$duration_ms" \
       --argjson pid "$$" \
       --argjson nt "\"$notes\"" \
       '.Values += [[$ts,$op,$te,$fn,$fe,$ri,$sc,$dm,$pid,$nt]]' \
       "$meta_path" > "$tmp" && mv "$tmp" "$meta_path" || rm -f "$tmp"

    # Auto-trim
    local cap
    cap=$(jq -r '.Debug_Row_Cap // "500"' "$manifest_path" 2>/dev/null)
    local count
    count=$(jq '.Values | length' "$meta_path" 2>/dev/null)
    if [[ "$count" -gt "$cap" ]]; then
        local keep_from=$(( count - cap ))
        local tmp2
        tmp2=$(mktemp "${meta_path}.tmp.XXXXXX")
        jq --argjson kf "$keep_from" '.Values = .Values[$kf:]' "$meta_path" > "$tmp2" \
            && mv "$tmp2" "$meta_path" || rm -f "$tmp2"
    fi
}
export -f _mfdb_meta_log

_mfdb_debug_schema_snapshot() {
    local manifest_path="$1"
    local meta_name="$2"

    local entities_json
    entities_json=$(mfdb_core_list_entities "$manifest_path" 2>/dev/null)

    echo "$entities_json" | jq -r '.[]' 2>/dev/null | while IFS= read -r ename; do
        [[ -z "$ename" || "$ename" == "$meta_name" ]] && continue
        local entity_path
        entity_path=$(_mfdb_debug_get_entity_path "$manifest_path" "$ename") || continue
        [[ -f "$entity_path" ]] || continue
        local fields
        fields=$(jq -r '[.Fields[].name] | join(",")' "$entity_path" 2>/dev/null)
        local fc
        fc=$(jq '.Fields | length' "$entity_path" 2>/dev/null)
        _mfdb_meta_log "$manifest_path" "SCHEMA_SNAPSHOT" "$ename" \
            "$fields" "true" "-" 1 0 "field_count=$fc"
    done
}
export -f _mfdb_debug_schema_snapshot

# mfdb_core_enable_debug <manifest_path> [row_cap=500] [debug_reads=0]
# Creates meta-{uuid} entity, sets debug headers, logs initial SCHEMA_SNAPSHOT.
# Prints meta entity name. Returns 0 on success.
mfdb_core_enable_debug() {
    local manifest_path="$1"
    local row_cap="${2:-500}"
    local debug_reads="${3:-0}"
    local debug_reads_str="false"
    [[ "$debug_reads" -eq 1 ]] && debug_reads_str="true"

    local existing_meta
    existing_meta=$(_mfdb_debug_get_meta_name "$manifest_path")

    local meta_name
    if [[ -n "$existing_meta" ]]; then
        meta_name="$existing_meta"
    else
        meta_name="meta-$(cat /proc/sys/kernel/random/uuid 2>/dev/null || uuidgen 2>/dev/null || date +%s%N)"
    fi

    # Update manifest headers
    local tmp
    tmp=$(mktemp "${manifest_path}.tmp.XXXXXX")
    jq --arg mn "$meta_name" --arg rc "$row_cap" --arg dr "$debug_reads_str" \
        '.Debug_Mode="true" | .Debug_Meta_Entity=$mn | .Debug_Row_Cap=$rc | .Debug_Reads=$dr' \
        "$manifest_path" > "$tmp" && mv "$tmp" "$manifest_path" || { rm -f "$tmp"; return 1; }

    # Create meta entity file if it doesn't exist
    local manifest_dir
    manifest_dir="$(dirname "$(realpath "$manifest_path")")"
    local meta_fp_rel="data/${meta_name}.bejson"
    local meta_abs="$manifest_dir/$meta_fp_rel"

    if [[ ! -f "$meta_abs" ]]; then
        mkdir -p "$(dirname "$meta_abs")"
        local rel_to_manifest
        rel_to_manifest=$(realpath --relative-to="$(dirname "$meta_abs")" "$manifest_path")
        jq -n \
            --arg ph "$rel_to_manifest" \
            --arg rt "$meta_name" \
            '{
                "Format":"BEJSON","Format_Version":"104","Format_Creator":"Elton Boehnen",
                "Parent_Hierarchy":$ph,"Records_Type":[$rt],
                "Fields":[
                    {"name":"timestamp","type":"string"},
                    {"name":"operation","type":"string"},
                    {"name":"target_entity","type":"string"},
                    {"name":"field_name","type":"string"},
                    {"name":"field_exists","type":"boolean"},
                    {"name":"row_index","type":"integer"},
                    {"name":"success","type":"boolean"},
                    {"name":"duration_ms","type":"integer"},
                    {"name":"pid","type":"integer"},
                    {"name":"notes","type":"string"}
                ],
                "Values":[]
            }' > "$meta_abs"

        # Register entity in manifest
        local already
        already=$(jq -r --arg e "$meta_name" \
            '[.Fields | to_entries | .[] | select(.value.name=="entity_name") | .key][0] as $ei |
             .Values[] | select(.[$ei]==$e) | .[$ei]' \
            "$manifest_path" 2>/dev/null | head -1)
        if [[ -z "$already" ]]; then
            local tmp2
            tmp2=$(mktemp "${manifest_path}.tmp.XXXXXX")
            jq --arg mn "$meta_name" --arg fp "$meta_fp_rel" \
                '.Values += [[$mn,$fp,"Debug audit log (auto-generated)",0,"1.0",null]]' \
                "$manifest_path" > "$tmp2" && mv "$tmp2" "$manifest_path" || rm -f "$tmp2"
        fi
    fi

    _mfdb_debug_schema_snapshot "$manifest_path" "$meta_name"
    echo "$meta_name"
    return 0
}
export -f mfdb_core_enable_debug

# mfdb_core_disable_debug <manifest_path>
mfdb_core_disable_debug() {
    local tmp
    tmp=$(mktemp "${1}.tmp.XXXXXX")
    jq '.Debug_Mode="false"' "$1" > "$tmp" && mv "$tmp" "$1" || rm -f "$tmp"
}
export -f mfdb_core_disable_debug

# mfdb_core_get_debug_log <manifest_path>
# Outputs the meta entity Values array as a JSON array of objects.
mfdb_core_get_debug_log() {
    local manifest_path="$1"
    local meta_name
    meta_name=$(_mfdb_debug_get_meta_name "$manifest_path")
    [[ -z "$meta_name" ]] && echo "[]" && return 0
    local meta_path
    meta_path=$(_mfdb_debug_get_entity_path "$manifest_path" "$meta_name") || { echo "[]"; return 0; }
    [[ -f "$meta_path" ]] || { echo "[]"; return 0; }
    jq '[.Fields as $f | .Values[] |
         . as $row |
         reduce range($f | length) as $i ({};
           . + {($f[$i].name): $row[$i]})]' "$meta_path" 2>/dev/null || echo "[]"
}
export -f mfdb_core_get_debug_log

# mfdb_core_get_failed_ops <manifest_path>
# Outputs failed (success=false) rows sorted by timestamp.
mfdb_core_get_failed_ops() {
    mfdb_core_get_debug_log "$1" | \
        jq '[.[] | select(.success==false)] | sort_by(.timestamp)' 2>/dev/null || echo "[]"
}
export -f mfdb_core_get_failed_ops

# mfdb_core_clear_debug_log <manifest_path>
# Wipes all Values from meta entity. Prints rows deleted.
mfdb_core_clear_debug_log() {
    local manifest_path="$1"
    local meta_name
    meta_name=$(_mfdb_debug_get_meta_name "$manifest_path")
    [[ -z "$meta_name" ]] && echo "0" && return 0
    local meta_path
    meta_path=$(_mfdb_debug_get_entity_path "$manifest_path" "$meta_name") || { echo "0"; return 0; }
    local deleted
    deleted=$(jq '.Values | length' "$meta_path" 2>/dev/null || echo 0)
    local tmp
    tmp=$(mktemp "${meta_path}.tmp.XXXXXX")
    jq '.Values=[]' "$meta_path" > "$tmp" && mv "$tmp" "$meta_path" || rm -f "$tmp"
    mfdb_core_sync_manifest_count "$manifest_path" "$meta_name" 2>/dev/null
    echo "$deleted"
}
export -f mfdb_core_clear_debug_log

# mfdb_core_debug_summary <manifest_path>
# Outputs a JSON summary object with aggregated debug stats.
mfdb_core_debug_summary() {
    local manifest_path="$1"
    _mfdb_debug_is_enabled "$manifest_path" || { echo "{}"; return 0; }
    local log
    log=$(mfdb_core_get_debug_log "$manifest_path")
    echo "$log" | jq '
        if length == 0 then {total_ops:0}
        else
          . as $rows |
          ($rows | length) as $total |
          ($rows | map(select(.success==false)) | length) as $failed |
          ($rows | map(select(.field_exists==false)) | length) as $drift |
          ($rows | map(select(.operation=="READ")) | length) as $reads |
          ($rows | map(select(.operation|IN("ADD","REMOVE","UPDATE","UPDATE_BULK"))) | length) as $writes |
          ($rows | group_by(.operation) | map({key:.[0].operation,value:length}) | from_entries) as $by_type |
          ($rows | unique_by(.target_entity) | map(.target_entity) | sort) as $entities |
          ($rows | sort_by(-.duration_ms) | .[0:3] |
           map({op:.operation,entity:.target_entity,duration_ms:.duration_ms})) as $slowest |
          {
            total_ops:$total, unique_entities:$entities,
            failed_ops:$failed, schema_drift_hits:$drift,
            top_3_slowest:$slowest, reads_logged:$reads,
            writes_logged:$writes, ops_by_type:$by_type
          }
        end
    ' 2>/dev/null || echo "{}"
}
export -f mfdb_core_debug_summary

# mfdb_core_detect_schema_drift <manifest_path>
# Diffs live Fields[] against SCHEMA_SNAPSHOT baseline in the debug log.
# Outputs a JSON object keyed by entity_name.
mfdb_core_detect_schema_drift() {
    local manifest_path="$1"
    _mfdb_debug_is_enabled "$manifest_path" || { echo "{}"; return 0; }
    local log
    log=$(mfdb_core_get_debug_log "$manifest_path")

    # Extract most-recent SCHEMA_SNAPSHOT per entity
    local snapshots
    snapshots=$(echo "$log" | jq '
        [ .[] | select(.operation=="SCHEMA_SNAPSHOT" and .field_name!=null) ] |
        group_by(.target_entity) | map(last) |
        map({key:.target_entity, value:(.field_name|split(","))}) |
        from_entries
    ' 2>/dev/null)

    [[ -z "$snapshots" || "$snapshots" == "null" || "$snapshots" == "{}" ]] && { echo "{}"; return 0; }

    local manifest_dir
    manifest_dir="$(dirname "$(realpath "$manifest_path")")"

    # For each entity in snapshots, load live fields and diff
    echo "$snapshots" | jq -r 'keys[]' | while IFS= read -r ename; do
        local entity_path
        entity_path=$(_mfdb_debug_get_entity_path "$manifest_path" "$ename") 2>/dev/null || continue
        [[ -f "$entity_path" ]] || continue
        local live_fields snap_fields added removed drifted
        live_fields=$(jq '[.Fields[].name]' "$entity_path" 2>/dev/null)
        snap_fields=$(echo "$snapshots" | jq --arg e "$ename" '.[$e]')
        added=$(jq -n --argjson l "$live_fields" --argjson s "$snap_fields" \
            '[$l[] | select(. as $f | $s | index($f) | not)] | sort')
        removed=$(jq -n --argjson l "$live_fields" --argjson s "$snap_fields" \
            '[$s[] | select(. as $f | $l | index($f) | not)] | sort')
        drifted=$(jq -n --argjson a "$added" --argjson r "$removed" \
            '($a | length > 0) or ($r | length > 0)')
        printf '"%s":{"added_fields":%s,"removed_fields":%s,"drifted":%s}\n' \
            "$ename" "$added" "$removed" "$drifted"
    done | jq -s 'map(split(":") | {key:.[0][1:-1], value:(.[1:] | join(":") | fromjson)}) | from_entries' \
        2>/dev/null || echo "{}"
}
export -f mfdb_core_detect_schema_drift


#-------------------------------------------------------------------------------
# Phase 6 -- 105-series MFDB Referential Integrity (2026-10-03)
# Additive only: gated on Format_Version 105/105a/105db. The 104-series CRUD
# above is untouched.
#-------------------------------------------------------------------------------
[[ -v E_MFDB_FK_UNRESOLVED             ]] || readonly E_MFDB_FK_UNRESOLVED=39
[[ -v E_MFDB_FK_TARGET_ENTITY_UNKNOWN  ]] || readonly E_MFDB_FK_TARGET_ENTITY_UNKNOWN=43
[[ -v E_MFDB_FK_RESTRICT_VIOLATION     ]] || readonly E_MFDB_FK_RESTRICT_VIOLATION=44
[[ -v E_MFDB_FK_CASCADE_CYCLE          ]] || readonly E_MFDB_FK_CASCADE_CYCLE=45
[[ -v E_MFDB_FK_ENTITY_STILL_REFERENCED ]] || readonly E_MFDB_FK_ENTITY_STILL_REFERENCED=46
[[ -v E_MFDB_FK_INVALID_ON_DELETE      ]] || readonly E_MFDB_FK_INVALID_ON_DELETE=47
[[ -v E_RECORD_NOT_FOUND               ]] || readonly E_RECORD_NOT_FOUND=82

__MFDB_RI_VISITED=""

__mfdb_ri_is105() { case "$1" in 105|105a|105db) return 0 ;; esac; return 1; }

__mfdb_ri_new_uuid() {
    if [[ -r /proc/sys/kernel/random/uuid ]]; then
        cat /proc/sys/kernel/random/uuid
    elif command -v uuidgen >/dev/null 2>&1; then
        uuidgen | tr 'A-Z' 'a-z'
    else
        echo "ERROR: no uuid source (/proc/sys/kernel/random/uuid or uuidgen)" >&2
        return $E_MFDB_CORE_WRITE_FAILED
    fi
}

# __mfdb_ri_jq_write <file> <jq args...>   atomic jq rewrite of a file in place
__mfdb_ri_jq_write() {
    local target="$1"; shift
    local tmp
    tmp="$(mktemp "${target}.tmp.XXXXXX")"
    if ! jq "$@" "$target" > "$tmp" 2>/dev/null; then
        rm -f "$tmp"
        return $E_MFDB_CORE_WRITE_FAILED
    fi
    mv "$tmp" "$target"
    bejson_core_invalidate_field_map_file "$target" 2>/dev/null || true
}

mfdb_core_enable_ref_integrity()  { __mfdb_ri_jq_write "$1" '.Ref_Integrity = "true"'; }
mfdb_core_disable_ref_integrity() { __mfdb_ri_jq_write "$1" '.Ref_Integrity = "false"'; }
mfdb_core_is_ref_integrity_enabled() {
    [[ "$(jq -r '.Ref_Integrity // "false"' "$1" 2>/dev/null)" == "true" ]]
}

# mfdb_core_check_fk_write <manifest> <from_entity> <fk_field_name> <value>
# Write-time exists-check. Empty/`null` passes. Returns 39/43/47 on failure.
mfdb_core_check_fk_write() {
    local manifest="$1" from_entity="$2" fk_name="$3" value="${4:-}"
    [[ -z "$value" || "$value" == "null" ]] && return 0
    local epath
    epath="$(mfdb_core_get_entity_path "$manifest" "$from_entity")" || return $?
    local fk_json target on_delete
    fk_json="$(jq -c --arg n "$fk_name" '.Fields[] | select(.name == $n)' "$epath" 2>/dev/null)"
    if [[ -z "$fk_json" ]]; then
        echo "ERROR: Field '$fk_name' not in $from_entity" >&2
        return $E_MFDB_CORE_INVALID_OPERATION
    fi
    target="$(jq -r '.fk_target_entity // empty' <<< "$fk_json")"
    [[ -z "$target" ]] && return 0
    on_delete="$(jq -r '.fk_on_delete // "restrict"' <<< "$fk_json")"
    case "$on_delete" in
        restrict|cascade|null) ;;
        *) echo "ERROR: $from_entity.$fk_name: fk_on_delete must be restrict/cascade/null, got '$on_delete'" >&2
           return $E_MFDB_FK_INVALID_ON_DELETE ;;
    esac
    local tpath
    if ! tpath="$(mfdb_core_get_entity_path "$manifest" "$target" 2>/dev/null)"; then
        echo "ERROR: $from_entity.$fk_name: fk_target_entity '$target' is not registered in this manifest" >&2
        return $E_MFDB_FK_TARGET_ENTITY_UNKNOWN
    fi
    if [[ ! -f "$tpath" ]]; then
        echo "ERROR: Entity file not found: $tpath" >&2
        return $E_MFDB_CORE_ENTITY_NOT_FOUND
    fi
    local tver tcol=0 found
    tver="$(jq -r '.Format_Version' "$tpath")"
    if ! __mfdb_ri_is105 "$tver"; then
        echo "ERROR: $from_entity.$fk_name: fk_target_entity '$target' is not a 105-series entity" >&2
        return $E_MFDB_FK_TARGET_ENTITY_UNKNOWN
    fi
    [[ "$tver" == "105db" ]] && tcol=1
    found="$(jq -r --arg v "$value" --argjson c "$tcol" '[.Values[] | select(length > $c and .[$c] == $v)] | length' "$tpath")"
    if [[ "${found:-0}" -lt 1 ]]; then
        echo "ERROR: $from_entity.$fk_name: '$value' does not exist in $target" >&2
        return $E_MFDB_FK_UNRESOLVED
    fi
    return 0
}

# __mfdb_ri_check_row <manifest> <entity> <entity_path> <json_values_array>
__mfdb_ri_check_row() {
    local manifest="$1" entity="$2" epath="$3" vals="$4"
    local fk_name fk_val
    while IFS=$'\t' read -r fk_name fk_val; do
        [[ -z "$fk_name" ]] && continue
        mfdb_core_check_fk_write "$manifest" "$entity" "$fk_name" "$fk_val" || return $?
    done < <(jq -r --argjson vals "$vals" '
        . as $d
        | (if $d.Format_Version == "105db" then $vals[1:] else $vals end) as $fv
        | $d.Fields | to_entries[]
        | select(.value.fk_target_entity)
        | select(.key < ($fv | length))
        | [.value.name, ($fv[.key] | if . == null then "null" else tostring end)] | @tsv' "$epath")
    return 0
}

# mfdb_core_find_referencing_rows <manifest> <target_entity> <target_uuid>
# Prints entity<TAB>fk_field<TAB>record_uuid for every row in OTHER 105-series
# entities whose declared FK field points at (target_entity, target_uuid).
mfdb_core_find_referencing_rows() {
    local manifest="$1" target_entity="$2" target_uuid="$3"
    local en_idx fp_idx name rel path
    en_idx="$(__mfdb_core_en_idx "$manifest")"; fp_idx="$(__mfdb_core_fp_idx "$manifest")"
    while IFS=$'\t' read -r name rel; do
        [[ -z "$name" || "$name" == "$target_entity" ]] && continue
        path="$(__mfdb_core_resolve "$manifest" "$rel")"
        [[ -f "$path" ]] || continue
        jq -r --arg te "$target_entity" --arg tu "$target_uuid" --arg en "$name" '
            select(.Format_Version | IN("105","105a","105db"))
            | (if .Format_Version == "105db" then 1 else 0 end) as $uc
            | (if .Format_Version == "105db" then 2 else 1 end) as $off
            | . as $d
            | ([$d.Fields | to_entries[] | select(.value.fk_target_entity == $te)
                | {n: .value.name, c: (.key + $off)}][]) as $f
            | $d.Values[] | select(length > $f.c and .[$f.c] == $tu)
            | [$en, $f.n, .[$uc]] | @tsv' "$path" 2>/dev/null
    done < <(jq -r --argjson ei "$en_idx" --argjson fi "$fp_idx" '.Values[] | [.[$ei], .[$fi]] | @tsv' "$manifest")
}

# mfdb_core_check_entity_droppable <manifest> <entity>
# Read-only. Prints entity<TAB>fk_field<TAB>record_uuid for every row of every
# OTHER entity whose FK schema targets <entity>. No output == safe to drop.
mfdb_core_check_entity_droppable() {
    local manifest="$1" entity_name="$2"
    local en_idx fp_idx name rel path
    en_idx="$(__mfdb_core_en_idx "$manifest")"; fp_idx="$(__mfdb_core_fp_idx "$manifest")"
    while IFS=$'\t' read -r name rel; do
        [[ -z "$name" || "$name" == "$entity_name" ]] && continue
        path="$(__mfdb_core_resolve "$manifest" "$rel")"
        [[ -f "$path" ]] || continue
        jq -r --arg te "$entity_name" --arg en "$name" '
            (if .Format_Version == "105db" then 1 else 0 end) as $uc
            | . as $d
            | ([$d.Fields[] | select(.fk_target_entity == $te) | .name][]) as $fname
            | $d.Values[] | select(length > $uc) | [$en, $fname, .[$uc]] | @tsv' "$path" 2>/dev/null
    done < <(jq -r --argjson ei "$en_idx" --argjson fi "$fp_idx" '.Values[] | [.[$ei], .[$fi]] | @tsv' "$manifest")
    return 0
}

# __mfdb_ri_record_exists <entity_path> <record_uuid>
__mfdb_ri_record_exists() {
    local epath="$1" ru="$2" n
    n="$(jq -r --arg u "$ru" '(if .Format_Version == "105db" then 1 else 0 end) as $uc
        | [.Values[] | select(length > $uc and .[$uc] == $u)] | length' "$epath")"
    [[ "${n:-0}" -ge 1 ]]
}

__mfdb_ri_delete_raw() {
    local manifest="$1" entity="$2" ru="$3" epath
    epath="$(mfdb_core_get_entity_path "$manifest" "$entity")" || return $?
    if ! __mfdb_ri_record_exists "$epath" "$ru"; then
        echo "ERROR: unknown record_uuid '$ru' in $entity" >&2
        return $E_RECORD_NOT_FOUND
    fi
    __mfdb_ri_jq_write "$epath" --arg u "$ru" '
        (if .Format_Version == "105db" then 1 else 0 end) as $uc
        | .Values |= map(select((length > $uc and .[$uc] == $u) | not))' || return $?
    mfdb_core_sync_manifest_count "$manifest" "$entity" >/dev/null
}

# __mfdb_ri_write_cell <manifest> <entity> <record_uuid> <field_name> <json_value>
__mfdb_ri_write_cell() {
    local manifest="$1" entity="$2" ru="$3" fname="$4" jval="$5" epath
    epath="$(mfdb_core_get_entity_path "$manifest" "$entity")" || return $?
    if ! __mfdb_ri_record_exists "$epath" "$ru"; then
        echo "ERROR: unknown record_uuid '$ru' in $entity" >&2
        return $E_RECORD_NOT_FOUND
    fi
    __mfdb_ri_jq_write "$epath" --arg u "$ru" --arg fn "$fname" --argjson v "$jval" '
        (if .Format_Version == "105db" then 1 else 0 end) as $uc
        | (if .Format_Version == "105db" then 2 else 1 end) as $off
        | ([.Fields[].name] | index($fn)) as $i
        | (.Values | to_entries | map(select(.value | (length > $uc and .[$uc] == $u))) | .[0].key) as $r
        | .Values[$r][$i + $off] = $v'
}

__mfdb_ri_cascade() {
    local manifest="$1" entity="$2" ru="$3"
    local key="${entity}#${ru}"
    if [[ $'\n'"$__MFDB_RI_VISITED" == *$'\n'"$key"$'\n'* ]]; then
        echo "ERROR: Cascade cycle detected: $key revisited during cascade delete" >&2
        return $E_MFDB_FK_CASCADE_CYCLE
    fi
    __MFDB_RI_VISITED+="${key}"$'\n'

    local refs rent rfield ruuid rpath on_delete rc
    refs="$(mfdb_core_find_referencing_rows "$manifest" "$entity" "$ru")"
    while IFS=$'\t' read -r rent rfield ruuid; do
        [[ -z "$rent" ]] && continue
        rpath="$(mfdb_core_get_entity_path "$manifest" "$rent")" || return $?
        on_delete="$(jq -r --arg n "$rfield" '.Fields[] | select(.name == $n) | .fk_on_delete // "restrict"' "$rpath")"
        case "$on_delete" in
            restrict)
                echo "ERROR: Cannot delete ${entity}#${ru}: restricted by ${rent}.${rfield} -> record ${ruuid}" >&2
                return $E_MFDB_FK_RESTRICT_VIOLATION ;;
            null)
                __mfdb_ri_write_cell "$manifest" "$rent" "$ruuid" "$rfield" null || return $? ;;
            cascade)
                __mfdb_ri_cascade "$manifest" "$rent" "$ruuid" || return $?
                __mfdb_ri_delete_raw "$manifest" "$rent" "$ruuid" || return $? ;;
            *)
                echo "ERROR: ${rent}.${rfield}: fk_on_delete must be restrict/cascade/null, got '$on_delete'" >&2
                return $E_MFDB_FK_INVALID_ON_DELETE ;;
        esac
    done <<< "$refs"
    return 0
}

# __mfdb_ri_require105 <manifest> <entity> <legacy_fn_hint>  -> prints entity path
__mfdb_ri_require105() {
    local manifest="$1" entity="$2" hint="$3" epath ver
    epath="$(mfdb_core_get_entity_path "$manifest" "$entity")" || return $?
    [[ -f "$epath" ]] || { echo "ERROR: Entity file not found: $epath" >&2; return $E_MFDB_CORE_ENTITY_NOT_FOUND; }
    ver="$(jq -r '.Format_Version' "$epath")"
    if ! __mfdb_ri_is105 "$ver"; then
        echo "ERROR: $entity is '$ver', not 105-series -- use $hint for 104-series entities" >&2
        return $E_MFDB_CORE_INVALID_OPERATION
    fi
    printf '%s' "$epath"
}

# mfdb_core_add_entity_record_105 <manifest> <entity> <json_values_array>
# Prints the new record_uuid. values exclude the record_uuid (105db: values[0]
# is the discriminator). FK values are checked first when Ref_Integrity is on.
mfdb_core_add_entity_record_105() {
    local manifest="$1" entity="$2" vals="$3" epath ru
    epath="$(__mfdb_ri_require105 "$manifest" "$entity" "mfdb_core_add_entity_record()")" || return $?
    if ! jq -e 'if type == "array" then true else error end' <<< "$vals" >/dev/null 2>&1; then
        echo "ERROR: json_values_array must be a JSON array string" >&2
        return $E_MFDB_CORE_INVALID_OPERATION
    fi
    if mfdb_core_is_ref_integrity_enabled "$manifest"; then
        __mfdb_ri_check_row "$manifest" "$entity" "$epath" "$vals" || return $?
    fi
    ru="$(__mfdb_ri_new_uuid)" || return $?
    __mfdb_ri_jq_write "$epath" --argjson row "$vals" --arg u "$ru" '
        if .Format_Version == "105db" then .Values += [[$row[0], $u] + $row[1:]]
        else .Values += [[$u] + $row] end' || return $?
    mfdb_core_sync_manifest_count "$manifest" "$entity" >/dev/null
    printf '%s\n' "$ru"
}

# mfdb_core_update_entity_record_105 <manifest> <entity> <record_uuid> <field_name> <json_value>
mfdb_core_update_entity_record_105() {
    local manifest="$1" entity="$2" ru="$3" fname="$4" jval="$5" epath
    epath="$(__mfdb_ri_require105 "$manifest" "$entity" "mfdb_core_update_entity_record()")" || return $?
    local fdef
    fdef="$(jq -c --arg n "$fname" '.Fields[] | select(.name == $n)' "$epath")"
    if [[ -z "$fdef" ]]; then
        echo "ERROR: Field '$fname' not in $entity" >&2
        return $E_MFDB_CORE_INVALID_OPERATION
    fi
    if mfdb_core_is_ref_integrity_enabled "$manifest" && [[ "$(jq -r '.fk_target_entity // empty' <<< "$fdef")" != "" ]]; then
        local raw
        raw="$(jq -r 'if . == null then "null" else tostring end' <<< "$jval")"
        mfdb_core_check_fk_write "$manifest" "$entity" "$fname" "$raw" || return $?
    fi
    __mfdb_ri_write_cell "$manifest" "$entity" "$ru" "$fname" "$jval"
}

# mfdb_core_delete_entity_record_105 <manifest> <entity> <record_uuid>
# With Ref_Integrity on, dependents are resolved first per fk_on_delete.
mfdb_core_delete_entity_record_105() {
    local manifest="$1" entity="$2" ru="$3" epath
    epath="$(__mfdb_ri_require105 "$manifest" "$entity" "mfdb_core_remove_entity_record()")" || return $?
    if ! __mfdb_ri_record_exists "$epath" "$ru"; then
        echo "ERROR: unknown record_uuid '$ru' in $entity" >&2
        return $E_RECORD_NOT_FOUND
    fi
    if mfdb_core_is_ref_integrity_enabled "$manifest"; then
        __MFDB_RI_VISITED=""
        __mfdb_ri_cascade "$manifest" "$entity" "$ru" || return $?
    fi
    __mfdb_ri_delete_raw "$manifest" "$entity" "$ru"
}

export -f mfdb_core_enable_ref_integrity mfdb_core_disable_ref_integrity mfdb_core_is_ref_integrity_enabled
export -f mfdb_core_check_fk_write mfdb_core_find_referencing_rows mfdb_core_check_entity_droppable
export -f mfdb_core_add_entity_record_105 mfdb_core_update_entity_record_105 mfdb_core_delete_entity_record_105
