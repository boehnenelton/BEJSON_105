# -----------------------------------------------------------------------------
# Library:         lib_bejson_Core_be_core.sh
# Family:          Core
# Module Purpose:  Root-path resolution, environment sourcing and state save/load for shell tools.
# Architecture:    Runtime or environment helper. It defines no BEJSON format rules.
# Format_Scope:    None (not a format module)
# Glossary:        BEJSON 104, 104a and 104db are the three file formats (Format_Version). 104db = ONE file holding 2+ entity types
#                  (Record_Type_Parent discriminator, null-padding). MFDB is NOT a format and NOT 104db: it is a layer made of one 104a manifest
#                  (104a.mfdb.bejson) plus dense 104 entity files linked by Parent_Hierarchy. MFDB-132 = an MFDB packed into one Chunked-104a document.
# Version:         2.2.5
# Release_Version: 300
# Date:            2026-10-02
# Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
# Format_Creator:  Elton Boehnen
# RELATIONAL_ID:   e1671aeb-816a-4608-88f3-493d9739b69f
# -----------------------------------------------------------------------------

# Echoes the root path: ADMIN_ROOT, or BEJSON_STORAGE_ROOT when ADMIN_ROOT is unset.
bec_core_get_root() {
    if [[ -n "${ADMIN_ROOT:-}" ]]; then
        echo "$ADMIN_ROOT"
        return 0
    fi
    # BEJSON_STORAGE_ROOT must be set when ADMIN_ROOT is not
    local storage_root="${BEJSON_STORAGE_ROOT:-}"
    if [[ -z "$storage_root" ]]; then
        echo "ERROR: BEJSON_STORAGE_ROOT is not set." >&2
        return 1
    fi
    
    # Resolve Admin Root
    local root_file="${storage_root}/Admin/data/state/ADMIN_ROOT.txt"
    if [[ -f "$root_file" ]]; then
        cat "$root_file"
    else
        echo "${storage_root}/Admin"
    fi
}

# Sources the environment files and exports ADMIN_ROOT if it is not set.
# Export ADMIN_ROOT if not set
bec_core_source_env() {
    if [[ -z "${ADMIN_ROOT:-}" ]]; then
        export ADMIN_ROOT=$(bec_core_get_root)
    fi
}

# Saves one key/value pair to a manager state file. Shell-tool state; not a BEJSON format feature.
# State Management - Save a key-value pair to a manager state file
bec_core_save_state() {
    local manager="$1" # "bash" or "python"
    local key="$2"
    local value="$3"
    local state_file="$(bec_core_get_root)/data/state/${manager}_manager_state.txt"
    
    mkdir -p "$(dirname "$state_file")"
    touch "$state_file"
    
    if grep -q "^${key}=" "$state_file"; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$state_file"
    else
        echo "${key}=${value}" >> "$state_file"
    fi
}

# Prints the value stored for a key in a manager state file.
# State Management - Load a value by key from a manager state file
bec_core_load_state() {
    local manager="$1"
    local key="$2"
    local state_file="$(bec_core_get_root)/data/state/${manager}_manager_state.txt"
    
    if [[ -f "$state_file" ]]; then
        grep "^${key}=" "$state_file" | cut -d'=' -f2
    fi
}

export -f bec_core_get_root
export -f bec_core_source_env
export -f bec_core_save_state
export -f bec_core_load_state