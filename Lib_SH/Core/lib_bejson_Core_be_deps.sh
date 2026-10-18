# -----------------------------------------------------------------------------
# Library:         lib_bejson_Core_be_deps.sh
# Family:          Core
# Module Purpose:  Connectivity check and dependency installation for shell tools.
# Architecture:    Runtime or environment helper. It defines no BEJSON format rules.
# Format_Scope:    None (not a format module)
# Glossary:        BEJSON 104, 104a and 104db are the three file formats (Format_Version). 104db = ONE file holding 2+ entity types
#                  (Record_Type_Parent discriminator, null-padding). MFDB is NOT a format and NOT 104db: it is a layer made of one 104a manifest
#                  (104a.mfdb.bejson) plus dense 104 entity files linked by Parent_Hierarchy. MFDB-132 = an MFDB packed into one Chunked-104a document.
# Version:         2.1.2
# Release_Version: 300
# Date:            2026-10-02
# Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
# Format_Creator:  Elton Boehnen
# RELATIONAL_ID:   c255ae9e-ebe3-42a8-957d-863e5adc4857
# -----------------------------------------------------------------------------

# Returns 0 when the network is reachable.
check_internet() {
    # Ping Google DNS with 2s timeout
    if ping -c 1 -W 2 8.8.8.8 > /dev/null 2>&1; then
        return 0 # Online
    else
        return 1 # Offline
    fi
}

# Installs the packages the shell tools need (e.g. jq) with the platform package manager.
install_dependencies() {
    local deps=("rsync" "jq" "figlet" "toilet" "python3" "git")
    local missing=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" > /dev/null 2>&1; then
            missing+=("$dep")
        fi
    done
    
    if [[ ${#missing[@]} -eq 0 ]]; then
        return 0
    fi
    
    echo -e "\033[38;2;222;38;38mMissing dependencies: ${missing[*]}\033[0m"
    
    if check_internet; then
        echo -e "\033[1;37mInternet detected. Attempting to install missing tools...\033[0m"
        # Determine package manager (Termux/apt)
        if command -v pkg > /dev/null 2>&1; then
            pkg install -y "${missing[@]}"
        elif command -v apt-get > /dev/null 2>&1; then
            sudo apt-get update && sudo apt-get install -y "${missing[@]}"
        else
            echo -e "\033[38;2;222;38;38mError: No supported package manager found (pkg/apt).\033[0m"
            return 1
        fi
        
        # Verify installation
        for dep in "${missing[@]}"; do
            if ! command -v "$dep" > /dev/null 2>&1; then
                echo -e "\033[38;2;222;38;38mFailed to install $dep.\033[0m"
                return 1
            fi
        done
        echo -e "\033[1;32mDependencies installed successfully.\033[0m"
    else
        echo -e "\033[38;2;222;38;38mNo internet connection. Skipping dependency installation.\033[0m"
        echo -e "\033[1;37mNote: Some features (like BEPM project creation) may fail without rsync.\033[0m"
        sleep 2
    fi
}