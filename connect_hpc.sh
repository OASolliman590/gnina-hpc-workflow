#!/bin/bash

# HPC Connection Helper Script
# Connects to HPC system with configured SSH key

# HPC Configuration
# TODO: Update these with your HPC credentials
HPC_USER="your_username"
HPC_HOST="login.hpc.example.org"
HPC_WORK_DIR="$HOME/gnina_test"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}HPC Connection Helper${NC}"
echo -e "${BLUE}================================${NC}"
echo ""
echo -e "Connecting to: ${GREEN}${HPC_USER}@${HPC_HOST}${NC}"
echo -e "Working Directory: ${GREEN}${HPC_WORK_DIR}${NC}"
echo ""

# Check if SSH key exists (common locations)
SSH_KEY_FOUND=false
SSH_KEY_PATH=""

# Check common SSH key locations
if [ -f "$HOME/.ssh/id_rsa" ]; then
    SSH_KEY_PATH="$HOME/.ssh/id_rsa"
    SSH_KEY_FOUND=true
elif [ -f "$HOME/.ssh/id_ed25519" ]; then
    SSH_KEY_PATH="$HOME/.ssh/id_ed25519"
    SSH_KEY_FOUND=true
elif [ -f "$HOME/.ssh/id_ecdsa" ]; then
    SSH_KEY_PATH="$HOME/.ssh/id_ecdsa"
    SSH_KEY_FOUND=true
fi

# If device key is specified, use it
if [ -n "$1" ]; then
    SSH_KEY_PATH="$1"
    if [ -f "$SSH_KEY_PATH" ]; then
        SSH_KEY_FOUND=true
        echo -e "${GREEN}Using specified SSH key: ${SSH_KEY_PATH}${NC}"
    else
        echo -e "${YELLOW}Warning: Specified SSH key not found: ${SSH_KEY_PATH}${NC}"
        echo -e "${YELLOW}Attempting connection with default SSH keys...${NC}"
    fi
fi

# Connect to HPC
if [ "$SSH_KEY_FOUND" = true ] && [ -n "$SSH_KEY_PATH" ]; then
    echo -e "${GREEN}Connecting with SSH key: ${SSH_KEY_PATH}${NC}"
    ssh -i "$SSH_KEY_PATH" "${HPC_USER}@${HPC_HOST}"
else
    echo -e "${YELLOW}Connecting with default SSH configuration...${NC}"
    echo -e "${YELLOW}(If you have a device key, specify it as: $0 /path/to/key)${NC}"
    ssh "${HPC_USER}@${HPC_HOST}"
fi

