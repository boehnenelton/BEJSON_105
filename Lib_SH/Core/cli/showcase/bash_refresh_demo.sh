#!/bin/bash
# Library:        bash_refresh_demo.sh
# Family:         Core
# Description:    Function-Based Refreshing (Live UI) demonstration for Bash. Relational ID: gcli-bash-showcase-refresh-001
# Version:        2.0.3
# Date:           Unknown
# Author:         Elton Boehnen
# Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
# Format_Creator: Elton Boehnen
# RELATIONAL_ID:  467f8535-dd54-4199-aaa6-f60708e943a7

run_demo() {
    CURRENT_STATE="LIVE_UI"
    clear
    draw_header
    
    RED="\033[38;2;222;38;38m"
    WHITE="\033[1;37m"
    RESET="\033[0m"
    
    update_time() {
        tput cup 3 $(( $(tput cols) - 10 ))
        echo -e "${RED}$(date +"%H:%M:%S")${RESET}"
    }

    update_load() {
        local load=$((RANDOM % 100))
        tput cup 5 6
        echo -e "${WHITE}SYSTEM LOAD:${RESET} [$(printf "%-10s" "$(printf "%.s|" $(seq 1 $((load/10))))" | tr ' ' '-')] ${RED}${load}%${RESET}"
    }

    tput cup 3 4
    echo -e "${WHITE_BOLD}Live Refresh Dashboard${RESET}"
    
    tput cup 7 4
    echo -e "Press ${RED}[ Any Key ]${RESET} to halt live feed and return."
    
    tput civis # Hide cursor
    while true; do
        update_time
        update_load
        
        # Non-blocking read simulation
        read -t 0.5 -n 1 key
        if [[ $? -eq 0 ]]; then
            break
        fi
    done
    tput cnorm # Show cursor
    
    CURRENT_STATE="MAIN"
}
