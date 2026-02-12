#!/bin/bash

# A2AC Movement Agent Monitor
# A "Brutalist" CLI for Mission Oversight

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
RESET='\033[0m'

# --- CONFIG ---
SERVICE_NAME="Movement Voice Swarm Monitor [v5.2.0]"
APP_URL="http://localhost:8080"
POLL_INTERVAL=2

clear

while true; do
    # Get Health & Stats
    HEALTH=$(curl -s $API_URL/health)
    CAMPAIGN=$(curl -s $API_URL/api/campaigns/status)
    AUDIT=$(curl -s $API_URL/api/audit)
    
    # Extract values
    STATUS=$(echo $HEALTH | grep -o 'healthy' || echo "OFFLINE")
    PERSONA=$(echo $HEALTH | grep -o '"persona":"[^"]*"' | cut -d'"' -f4)
    RUNNING=$(echo $CAMPAIGN | grep -o '"is_running":[^,]*' | cut -d':' -f2)
    DIALED=$(echo $CAMPAIGN | grep -o '"dialed":[^,]*' | cut -d':' -f2)
    APPTS=$(echo $CAMPAIGN | grep -o '"appointments":[^,]*' | cut -d':' -f2)
    
    # Draw Interface
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${CYAN}${BOLD}  CORE VOICE AGENT MONITOR | AGENT: ${PERSONA} | MISSION CONTROL${RESET}"
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "  DATE: $(date +'%Y-%m-%d %H:%M:%S')"
    echo -e "  SYSTEM STATUS: ${GREEN}${BOLD}${STATUS}${RESET}"
    echo ""
    
    echo -e "${BOLD}--- MISSION CONTROL: JASON v4.1.0 ---${RESET}"
    if [ "$RUNNING" == "true" ]; then
        echo -e "  STATUS: ${GREEN}${BOLD}ACTIVE RUNNING${RESET}"
    else
        echo -e "  STATUS: ${YELLOW}IDLE${RESET}"
    fi
    echo -e "  TOTAL DIALED: ${WHITE}${DIALED}${RESET}"
    echo -e "  APPOINTMENTS: ${GREEN}${BOLD}${APPTS}${RESET}"
    echo ""
    
    echo -e "${BOLD}[ LATEST AUDIT LOG ]${RESET}"
    # Show last 3 events if possible
    # (Simplified for bash without jq dependency)
    echo -e "  - Initializing Movement Logic..."
    echo -e "  - Persona '${PERSONA}' Active..."
    echo ""
    
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "  PRESS [CTRL+C] TO EXIT | POLLING: ${POLL_INTERVAL}s"
    
    sleep $POLL_INTERVAL
    clear
done
