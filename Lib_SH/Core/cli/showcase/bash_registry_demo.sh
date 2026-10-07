#!/bin/bash
# Library:        bash_registry_demo.sh
# Family:         Core
# Description:    Registry Explorer (Mockup) demonstration for Bash. Relational ID: gcli-bash-showcase-registry-001
# Version:        2.0.3
# Date:           Unknown
# Author:         Elton Boehnen
# Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
# Format_Creator: Elton Boehnen
# RELATIONAL_ID:  a2525338-93bb-490a-bed2-21001b9e6b38

run_demo() {
    CURRENT_STATE="REGISTRY"
    clear
    draw_header
    
    RED="\033[38;2;222;38;38m"
    WHITE="\033[1;37m"
    RESET="\033[0m"
    
    tput cup 3 4
    echo -e "${WHITE_BOLD}Registry Explorer: Entity Navigation${RESET}"
    
    draw_table() {
        tput cup 5 2
        echo -e "${RED}+----------------+----------------------+${RESET}"
        tput cup 6 2
        echo -e "${RED}|${RESET} ${WHITE}Entity Name${RESET}    ${RED}|${RESET} ${WHITE}Status${RESET}               ${RED}|${RESET}"
        tput cup 7 2
        echo -e "${RED}+----------------+----------------------+${RESET}"
        tput cup 8 2
        echo -e "${RED}|${RESET} User           ${RED}|${RESET} ${RED}CONNECTED${RESET}            ${RED}|${RESET}"
        tput cup 9 2
        echo -e "${RED}|${RESET} Registry       ${RED}|${RESET} ${RED}IDLE${RESET}                 ${RED}|${RESET}"
        tput cup 10 2
        echo -e "${RED}|${RESET} Environment    ${RED}|${RESET} ${RED}SYNCING...${RESET}           ${RED}|${RESET}"
        tput cup 11 2
        echo -e "${RED}+----------------+----------------------+${RESET}"
    }

    draw_table
    
    tput cup 13 4
    echo -e "Exploring entity: ${RED}Environment${RESET}"
    tput cup 14 6
    echo -e "· SYNC_INTERVAL: 300s"
    tput cup 15 6
    echo -e "· IS_RESTRICTED: true"
    
    tput cup $(( $(tput lines) - 3 )) 4
    echo -e "${RED}Press [ 0 ] to return to menu...${RESET}"
    
    while true; do
        read -n 1 -s key
        if [[ "$key" == "0" ]]; then
            CURRENT_STATE="MAIN"
            break
        fi
    done
}
