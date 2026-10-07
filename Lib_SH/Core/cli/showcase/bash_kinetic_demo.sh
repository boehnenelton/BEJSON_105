#!/bin/bash
# Library:        bash_kinetic_demo.sh
# Family:         Core
# Description:    Kinetic Shell (Animations/Spinners) demonstration for Bash. Relational ID: gcli-bash-showcase-kinetic-001
# Version:        2.0.3
# Date:           Unknown
# Author:         Elton Boehnen
# Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
# Format_Creator: Elton Boehnen
# RELATIONAL_ID:  c8d98394-cef1-437f-8259-0076fd790187

run_demo() {
    CURRENT_STATE="KINETIC"
    clear
    draw_header
    
    RED="\033[38;2;222;38;38m"
    WHITE="\033[1;37m"
    RESET="\033[0m"
    
    spinner() {
        local pid=$!
        local delay=0.1
        local spinstr='|/-\'
        tput civis # Hide cursor
        while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
            local temp=${spinstr#?}
            printf " [%c]  " "$spinstr"
            local spinstr=$temp${spinstr%"$temp"}
            sleep $delay
            printf "\b\b\b\b\b\b"
        done
        tput cnorm # Show cursor
        printf "    \b\b\b\b"
    }

    tput cup 3 4
    echo -e "${WHITE_BOLD}Kinetic Shell: Animation Showcase${RESET}"
    
    # 1. Spinner Demo
    tput cup 5 4
    echo -n "Fetching Registry Manifest... "
    (sleep 2) &
    spinner
    echo -e "${RED}DONE${RESET}"

    # 2. Progress Bar Demo
    tput cup 7 4
    echo -e "Synchronizing Slave Mirror:"
    
    local width=40
    for ((i=0; i<=width; i++)); do
        local percent=$((i * 100 / width))
        local bar=$(printf "%${i}s" | tr ' ' '█')
        local space=$(printf "%$((width - i))s" | tr ' ' ' ')
        tput cup 8 4
        printf "${RED}[${bar}${RESET}${space}${RED}]${RESET} %d%%" "$percent"
        sleep 0.05
    done
    echo -e "\n"

    # 3. Pulsing Effect (Simulation)
    tput cup 11 4
    echo -e "${WHITE}Live Signal Monitoring:${RESET}"
    for i in {1..5}; do
        tput cup 12 6
        echo -e "${RED}·· BEATING ··${RESET} (Pulse $i)"
        sleep 0.4
        tput cup 12 6
        echo -e "              "
        sleep 0.2
    done

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
