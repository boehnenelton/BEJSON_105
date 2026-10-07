# Library:        lib_bejson_System_be_core.sh
# Family:         Core
# Description:    BE-specific core system abstractions and utility wrappers.
# Version:        2.2.1
# Date:           2026-06-04
# Author:         Elton Boehnen
# Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
# Format_Creator: Elton Boehnen
# RELATIONAL_ID:  baffaf1b-6503-471c-a0df-1ac66754dff9
# Release_Version: 300

# Get the root path of the Admin workspace dynamically
bec_core_get_root() {
    if [[ -n "${ADMIN_ROOT:-}" ]]; then
        echo "$ADMIN_ROOT"
        return 0
    fi
    # Removed hardcoded Brain-Container and legacy SC_ROOT (Phase 6.5)
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

# Export ADMIN_ROOT if not set
bec_core_source_env() {
    if [[ -z "${ADMIN_ROOT:-}" ]]; then
        export ADMIN_ROOT=$(bec_core_get_root)
    fi
}

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
