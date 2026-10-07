# Library:        lib_bejson_Core_bejson_core.sh
# Family:         Core
# Description:    Low-level primitive operations for BEJSON document manipulation.
# BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
#                 do not restate or reinterpret this acronym elsewhere.
# MFDB:           MFDB stands for Multi File Database. Authoritative definition;
#                 do not restate or reinterpret this acronym elsewhere.
# Version:        2.1.0
# Date:           2026-10-03
# Author:         Elton Boehnen
# Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
# Format_Creator: Elton Boehnen
# RELATIONAL_ID:  a6913b04-bce3-436e-b4f3-56c36187a3fd
# Release_Version: 300

#===============================================================================

#-------------------------------------------------------------------------------
# SAFETY & ERROR HANDLING
#-------------------------------------------------------------------------------

# NOTE: set -o nounset intentionally omitted — library files must not modify
# global shell options; doing so breaks host scripts that source this file. (SH3)
set -o pipefail

# Universal library release line (Policy 2026-08-14). Only this file --
# the Core BEJSON file -- defines RELEASE_VERSION as a real variable;
# all other library files declare it in the header comment only.
readonly RELEASE_VERSION=300

# Source the validator library and error registry (assumes same directory)
_CORE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$_CORE_DIR/lib_bejson_Core_bejson_errors.sh" ]]; then
    # shellcheck source=./lib_bejson_Core_bejson_errors.sh
    source "$_CORE_DIR/lib_bejson_Core_bejson_errors.sh"
fi

if [[ -f "$_CORE_DIR/lib_bejson_Core_bejson_validator.sh" ]]; then
    # shellcheck source=./lib_bejson_Core_bejson_validator.sh
    source "$_CORE_DIR/lib_bejson_Core_bejson_validator.sh"
fi

#-------------------------------------------------------------------------------
# ATOMIC FILE OPERATIONS
#-------------------------------------------------------------------------------

__bejson_core_atomic_backup() {
    local file_path="$1"
    [[ ! -f "$file_path" ]] && return 0
    local backup_path="${file_path}.backup.$(date +%Y%m%d_%H%M%S).$$"
    cp -p "$file_path" "$backup_path" 2>/dev/null || return $E_CORE_BACKUP_FAILED
    echo "$backup_path"
    return 0
}

__bejson_core_restore_backup() {
    local file_path="$1"
    local backup_path="$2"
    bejson_core_invalidate_field_map_file "$file_path"
    [[ -f "$backup_path" ]] && mv "$backup_path" "$file_path" 2>/dev/null
}

bejson_core_atomic_write() {
    local file_path="$1"
    local content="$2"
    local create_backup="${3:-true}"
    local backup_path=""

    if [[ "$create_backup" == "true" ]]; then
        backup_path=$(__bejson_core_atomic_backup "$file_path") || return $?
    fi

    local target_dir=$(dirname "$file_path")
    mkdir -p "$target_dir"
    local temp_file="${target_dir}/.bejson_$$.tmp"

    printf '%s' "$content" > "$temp_file" 2>/dev/null || {
        [[ -n "$backup_path" ]] && __bejson_core_restore_backup "$file_path" "$backup_path"
        return $E_CORE_WRITE_FAILED
    }

    # NOTE SH6: On Android exFAT SD card paths (/storage/<UUID>/...), sync(1) may be a
    # no-op or unavailable. The || true swallow is intentional — writes to SD have
    # weaker durability guarantees than internal storage on Android.
    sync "$temp_file" 2>/dev/null || true
    mv "$temp_file" "$file_path" 2>/dev/null || {
        cp -p "$temp_file" "$file_path" 2>/dev/null && rm -f "$temp_file" || {
            [[ -n "$backup_path" ]] && __bejson_core_restore_backup "$file_path" "$backup_path"
            return $E_CORE_WRITE_FAILED
        }
    }
    sync "$(dirname "$file_path")" 2>/dev/null || true
    bejson_core_invalidate_field_map_file "$file_path"   # content changed: drop the cached map
    return 0
}

#-------------------------------------------------------------------------------
# MUTEX LOCKING (Policy Sec. 47)
#-------------------------------------------------------------------------------

resilient_lock_acquire() {
    local target="$1"
    local lock_dir="${target}.lockdir"
    local meta="${lock_dir}/lock_meta.json"
    local timeout="${2:-10}"
    local start
    start=$(date +%s)
    
    while true; do
        if mkdir "$lock_dir" 2>/dev/null; then
            # Lock acquired — write PID metadata
            printf '{"pid": %d, "timestamp": %d}\n' "$$" "$(date +%s)" > "$meta"
            return 0
        fi
        
        # Check for dead-process orphan
        if [[ -f "$meta" ]]; then
            local pid
            pid=$(jq -r '.pid // empty' "$meta" 2>/dev/null)
            if [[ -n "$pid" ]] && ! kill -0 "$pid" 2>/dev/null; then
                # Safe reclamation: owner process is dead
                rm -rf "$lock_dir" 2>/dev/null
                continue
            fi
        fi
        
        if [[ $(($(date +%s) - start)) -ge $timeout ]]; then
            return 53  # E_MFDB_CORE_LOCK_FAILED
        fi
        sleep 0.2
    done
}

resilient_lock_release() {
    local target="$1"
    local lock_dir="${target}.lockdir"
    [[ -d "$lock_dir" ]] && rm -rf "$lock_dir" 2>/dev/null
    return 0
}

bejson_core_load_file() {
    local file_path="$1"
    if [[ ! -f "$file_path" ]]; then
        return $E_CORE_FIELD_NOT_FOUND
    fi
    cat "$file_path"
}

#-------------------------------------------------------------------------------
# FIELD & RECORD OPERATIONS
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# FIELD MAP CACHE -- SELF-MAINTAINING (v2.1.0, parity with PY 3.4.0/3.5.0,
# JS 2.1.0, TS field_map 2.4.0). Callers never build or refresh anything:
# bejson_core_get_field_index / _get_field_map / _get_field_index_file build
# the map on first touch and every later lookup is a cache hit (zero jq).
#
# Bash can't hold state across $(...) subshells, so the cache is FILE-backed
# under a per-shell directory (keyed by the top-level shell's $$, shared by
# every subshell). Never stale by construction:
#   * doc-string lookups are content-addressed (key = digest of the whole
#     doc), so any change to the doc is simply a different key;
#   * file lookups are validated with [[ file -nt cache ]] (builtin, no fork)
#     and the cache entry is dropped on atomic_write / backup restore.
# 105-series row offsets (105/105a +1, 105db +2) are included: column 3 of an
# entry is the ROW position, so row[map[name]] is right on every version.
# Entry format (one field per line): name<TAB>fields_idx<TAB>row_idx<TAB>field_uuid
#-------------------------------------------------------------------------------

__BEJSON_FM_DIR=""

__bejson_fm_dir() {
    if [[ -z "$__BEJSON_FM_DIR" ]]; then
        local base="${BEJSON_FM_CACHE_BASE:-${TMPDIR:-/tmp}}"
        local d
        # Reap cache dirs left by shells that are gone (done once per process).
        for d in "$base"/bejson_fm_cache.*; do
            [[ -d "$d" ]] || continue
            kill -0 "${d##*.}" 2>/dev/null || rm -rf "$d" 2>/dev/null
        done
        __BEJSON_FM_DIR="$base/bejson_fm_cache.$$"
        mkdir -p "$__BEJSON_FM_DIR" 2>/dev/null && chmod 700 "$__BEJSON_FM_DIR" 2>/dev/null
    fi
    [[ -d "$__BEJSON_FM_DIR" ]] || { __BEJSON_FM_DIR=""; return 1; }
    return 0
}

# Prints a hex digest of stdin (md5sum, else cksum -- keys only, not security).
__bejson_fm_digest() {
    if command -v md5sum >/dev/null 2>&1; then md5sum | cut -d' ' -f1
    else cksum | tr ' ' '_'; fi
}

# __bejson_fm_build <cache_file> <doc_json|-> [file_path]
# One jq call builds the whole map, written atomically (tmp + mv).
__bejson_fm_build() {
    local cf="$1" doc="$2" src="${3:-}" tmp="$1.$$.tmp"
    local prog='(.Format_Version // "") as $v
        | (if $v == "105db" then 2 elif ($v == "105" or $v == "105a") then 1 else 0 end) as $o
        | (.Fields // []) | to_entries[]
        | [.value.name, .key, (.key + $o), (.value.field_uuid // "")] | @tsv'
    {
        printf '#bejson_fm_v1\n'
        if [[ -n "$src" ]]; then jq -r "$prog" "$src"
        else printf '%s' "$doc" | jq -r "$prog"; fi
    } > "$tmp" 2>/dev/null || { rm -f "$tmp" 2>/dev/null; return 1; }
    mv -f "$tmp" "$cf" 2>/dev/null
}

# __bejson_fm_lookup <cache_file> <name> <col: fields|row>  -> prints index or -1
__bejson_fm_lookup() {
    local cf="$1" want="$2" col="${3:-fields}" nm fi ri uu
    while IFS=$'\t' read -r nm fi ri uu; do
        [[ "$nm" == "#bejson_fm_v1" ]] && continue
        if [[ "$nm" == "$want" ]]; then
            if [[ "$col" == "row" ]]; then printf '%s\n' "$ri"; else printf '%s\n' "$fi"; fi
            return 0
        fi
    done < "$cf"
    printf '%s\n' "-1"
}

# Sets __BEJSON_FM_FILE to the (built-on-demand) cache entry for a doc string.
__bejson_fm_entry_for_doc() {
    local doc="$1" key
    __BEJSON_FM_FILE=""
    __bejson_fm_dir || return 1
    key=$(printf '%s' "$doc" | __bejson_fm_digest)
    __BEJSON_FM_FILE="$__BEJSON_FM_DIR/doc_$key"
    [[ -s "$__BEJSON_FM_FILE" ]] || __bejson_fm_build "$__BEJSON_FM_FILE" "$doc" || return 1
}

# Sets __BEJSON_FM_FILE to the (built-on-demand, mtime-validated) entry for a file.
__bejson_fm_entry_for_file() {
    local path="$1" key
    __BEJSON_FM_FILE=""
    [[ -f "$path" ]] || return 1
    __bejson_fm_dir || return 1
    key="${path//%/%25}"; key="${key//\//%2F}"
    (( ${#key} > 200 )) && key=$(printf '%s' "$path" | __bejson_fm_digest)
    __BEJSON_FM_FILE="$__BEJSON_FM_DIR/file_$key"
    if [[ ! -s "$__BEJSON_FM_FILE" || "$path" -nt "$__BEJSON_FM_FILE" ]]; then
        __bejson_fm_build "$__BEJSON_FM_FILE" "" "$path" || return 1
    fi
}

# Drops the cached map for one file (called after writes / backup restores).
bejson_core_invalidate_field_map_file() {
    local path="$1" key
    [[ -n "$__BEJSON_FM_DIR" ]] || return 0
    key="${path//%/%25}"; key="${key//\//%2F}"
    (( ${#key} > 200 )) && key=$(printf '%s' "$path" | __bejson_fm_digest)
    rm -f "$__BEJSON_FM_DIR/file_$key" 2>/dev/null
    return 0
}

# Drops every cached map for this shell (memory/disk control; never needed for correctness).
bejson_core_clear_field_map_cache() {
    [[ -n "$__BEJSON_FM_DIR" ]] && rm -rf "$__BEJSON_FM_DIR" 2>/dev/null
    __BEJSON_FM_DIR=""
    return 0
}

# bejson_core_get_field_index <doc_json> <field_name>  -> Fields index, or -1
bejson_core_get_field_index() {
    local doc="$1" field_name="$2"
    if __bejson_fm_entry_for_doc "$doc"; then
        __bejson_fm_lookup "$__BEJSON_FM_FILE" "$field_name" fields
    else   # cache dir unusable: fall back to the original single jq call
        echo "$doc" | jq --arg fn "$field_name" '.Fields | map(.name) | index($fn) // -1'
    fi
}

# bejson_core_get_field_index_file <path> <field_name> [fields|row] -> index, or -1
# File variant: on a cache hit this touches neither jq nor the file's contents.
bejson_core_get_field_index_file() {
    local path="$1" field_name="$2" col="${3:-fields}"
    if __bejson_fm_entry_for_file "$path"; then
        __bejson_fm_lookup "$__BEJSON_FM_FILE" "$field_name" "$col"
    else
        jq --arg fn "$field_name" '.Fields | map(.name) | index($fn) // -1' "$path"
    fi
}

# bejson_core_get_field_map <doc_json> -> "name<TAB>row_index" lines (105-aware ROW positions)
bejson_core_get_field_map() {
    local doc="$1" nm fi ri uu
    __bejson_fm_entry_for_doc "$doc" || return 1
    while IFS=$'\t' read -r nm fi ri uu; do
        [[ "$nm" == "#bejson_fm_v1" ]] && continue
        printf '%s\t%s\n' "$nm" "$ri"
    done < "$__BEJSON_FM_FILE"
}

bejson_core_get_record_count() {
    local doc="$1"
    echo "$doc" | jq '.Values | length'
}

bejson_core_add_record() {
    local doc="$1"
    local values_json="$2"
    echo "$doc" | jq --argjson row "$values_json" '.Values += [$row]'
}

bejson_core_remove_record() {
    local doc="$1"
    local index="$2"
    echo "$doc" | jq --argjson idx "$index" 'del(.Values[$idx])'
}

bejson_core_update_field() {
    # --arg always writes a JSON string. Inspect declared field type and use
    # --argjson when the field is not a string so integers/booleans/numbers round-trip
    # correctly. Falls back to --arg only for string-typed fields.
    local doc="$1"
    local rec_idx="$2"
    local field_name="$3"
    local new_val="$4"
    local f_idx
    f_idx=$(bejson_core_get_field_index "$doc" "$field_name")
    if [[ "$f_idx" == "-1" ]]; then return $E_CORE_FIELD_NOT_FOUND; fi

    local field_type
    field_type=$(echo "$doc" | jq -r --argjson fi "$f_idx" '.Fields[$fi].type // "string"')

    if [[ "$field_type" == "string" ]]; then
        echo "$doc" | jq --argjson ri "$rec_idx" --argjson fi "$f_idx" --arg nv "$new_val" '(.Values[$ri][$fi]) = $nv'
    else
        # Use --argjson so the value is written as the correct JSON type (number, boolean, etc.)
        echo "$doc" | jq --argjson ri "$rec_idx" --argjson fi "$f_idx" --argjson nv "$new_val" '(.Values[$ri][$fi]) = $nv'
    fi
}

#-------------------------------------------------------------------------------
# QUERY & SORT
#-------------------------------------------------------------------------------

bejson_core_filter_rows() {
    local doc="$1"
    local field_name="$2"
    local value="$3"
    local f_idx=$(bejson_core_get_field_index "$doc" "$field_name")
    if [[ "$f_idx" == "-1" ]]; then return $E_CORE_FIELD_NOT_FOUND; fi
    echo "$doc" | jq --argjson fi "$f_idx" --arg val "$value" '.Values | map(select(.[$fi] == $val))'
}

bejson_core_sort_by_field() {
    local doc="$1"
    local field_name="$2"
    local ascending="${3:-true}"
    local f_idx=$(bejson_core_get_field_index "$doc" "$field_name")
    if [[ "$f_idx" == "-1" ]]; then return $E_CORE_FIELD_NOT_FOUND; fi
    if [[ "$ascending" == "true" ]]; then
        echo "$doc" | jq --argjson fi "$f_idx" '.Values |= sort_by(.[$fi])'
    else
        echo "$doc" | jq --argjson fi "$f_idx" '.Values |= (sort_by(.[$fi]) | reverse)'
    fi
}

# Export functions
export -f bejson_core_atomic_write
export -f bejson_core_load_file
export -f bejson_core_get_field_index
export -f bejson_core_get_field_index_file
export -f bejson_core_get_field_map
export -f bejson_core_invalidate_field_map_file
export -f bejson_core_clear_field_map_cache
export -f bejson_core_get_record_count
export -f bejson_core_add_record
export -f bejson_core_remove_record
export -f bejson_core_update_field
export -f bejson_core_filter_rows
export -f bejson_core_sort_by_field
export -f resilient_lock_acquire
export -f resilient_lock_release
