#!/bin/bash
# Library:        bash_showcase_master.sh
# Family:         Core
# Description:    Numeric-driven master controller for GEMINI Bash Terminal Showcases.
# Version:        1.0.0
# Date:           Unknown
# Author:         Elton Boehnen
# Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
# Format_Creator: Elton Boehnen
# RELATIONAL_ID:  ae418b20-f916-4602-b36f-0a927dddc7fb

VERSION="1.0.0"

# Mandatory Portability (Sec. 20.1 Fallback Pattern)
get_script_path() {
    local source="${BASH_SOURCE[0]}"
    while [ -h "$source" ]; do
        local dir="$( cd -P "$( dirname "$source" )" >/dev/null 2>&1 && pwd )"
        source="$(readlink "$source")"
        [[ $source != /* ]] && source="$dir/$source"
    done
    echo "$( cd -P "$( dirname "$source" )" >/dev/null 2>&1 && pwd )"
}
SCRIPT_PATH=$(get_script_path)

# BEJSON Red Accent
RED_RGB="\033[38;2;222;38;38m"
BG_RED_RGB="\033[48;2;222;38;38m"
WHITE_BOLD="\033[1;37m"
RESET="\033[0m"

# State Management
CURRENT_STATE="MAIN"

clear_screen() {
    clear
}

draw_header() {
    local cols=$(tput cols)
    local header=" GEMINI BASH SHOWCASE v${VERSION} | STATE: ${CURRENT_STATE} "
    printf "${BG_RED_RGB}${WHITE_BOLD}%*s${RESET}\n" "$cols" | sed "s/ / /g"
    tput cup 0 0
    echo -e "${BG_RED_RGB}${WHITE_BOLD}$(printf '%*s' "$(( (cols + ${#header}) / 2 ))" "$header" | printf '%-*s' "$cols")${RESET}"
}

draw_footer() {
    local cols=$(tput cols)
    local rows=$(tput lines)
    local footer=" [ 0 ] Exit | [ 1-5 ] Select Module "
    tput cup $((rows - 1)) 0
    echo -e "${BG_RED_RGB}${WHITE_BOLD}$(printf '%*s' "$(( (cols + ${#footer}) / 2 ))" "$footer" | printf '%-*s' "$cols")${RESET}"
}

main_menu() {
    clear_screen
    draw_header
    
    tput cup 3 2
    echo -e "${RED_RGB}  ▄████████  ▄████████  ▄▄▄▄███▄▄▄  ▄█  ███▄▄▄▄   ▄█  ${RESET}"
    tput cup 4 2
    echo -e "${RED_RGB} ███    ███ ███    ███ ███▀▀▀███▀▀▀ ███  ███▀▀▀██▄ ███  ${RESET}"
    tput cup 5 2
    echo -e "${RED_RGB} ███    █▀  ███    █▀  ███   ███    ███▌ ███   ███ ███▌ ${RESET}"
    tput cup 6 2
    echo -e "${RED_RGB}▄███▄▄▄     ███        ███   ███    ███▌ ███   ███ ███▌ ${RESET}"
    tput cup 7 2
    echo -e "${RED_RGB}▀▀███▀▀▀    ███        ███   ███    ███▌ ███   ███ ███▌ ${RESET}"
    tput cup 8 2
    echo -e "${RED_RGB}  ███    █▄ ███    █▄  ███   ███    ███  ███   ███ ███  ${RESET}"
    tput cup 9 2
    echo -e "${RED_RGB}  ███    ███ ███    ███ ███   ███    ███  ███   ███ ███  ${RESET}"
    tput cup 10 2
    echo -e "${RED_RGB}  ████████▀  ▀████████▀  ▀█   █▀     █▀    ▀█   █▀  █▀   ${RESET}"

    tput cup 13 4
    echo -e "${WHITE_BOLD}Select a Bash Showcase Module:${RESET}"
    tput cup 15 6
    echo -e "${RED_RGB}1.${RESET} Advanced Statement Manager (Logging)"
    tput cup 16 6
    echo -e "${RED_RGB}2.${RESET} Kinetic Shell (Animations/Spinners)"
    tput cup 17 6
    echo -e "${RED_RGB}3.${RESET} Function-Based Refreshing (Live UI)"
    tput cup 18 6
    echo -e "${RED_RGB}4.${RESET} Secondary Library Bridge (Integration)"
    tput cup 19 6
    echo -e "${RED_RGB}5.${RESET} Registry Explorer (Mockup)"
    
    draw_footer
}

run_module() {
    local choice=$1
    case $choice in
        1) source "${SCRIPT_PATH}/bash_statement_demo.sh" ;;
        2) source "${SCRIPT_PATH}/bash_kinetic_demo.sh" ;;
        3) source "${SCRIPT_PATH}/bash_refresh_demo.sh" ;;
        4) source "${SCRIPT_PATH}/bash_bridge_demo.sh" ;;
        5) source "${SCRIPT_PATH}/bash_registry_demo.sh" ;;
        *) return ;;
    esac
    run_demo
}

# Main Loop
while true; do
    main_menu
    read -n 1 -s choice
    if [[ "$choice" == "0" ]]; then
        clear_screen
        echo -e "${RED_RGB}GEMINI Bash Session Terminated.${RESET}"
        exit 0
    fi
    if [[ "$choice" =~ [1-5] ]]; then
        run_module "$choice"
    fi
done
