#!/bin/bash

# Sync Script to Copy Files to HPC
# This script copies necessary files to your HPC system

# HPC Configuration
# TODO: Update these with your HPC credentials
HPC_USER="your_username"
HPC_HOST="login.hpc.example.org"
# Remote home will be detected automatically
HPC_WORK_DIR_RELATIVE="gnina_test"

# Local project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Check for SSH key
SSH_KEY_PATH=""
if [ -n "$1" ]; then
    SSH_KEY_PATH="$1"
    if [ ! -f "$SSH_KEY_PATH" ]; then
        print_error "SSH key not found: $SSH_KEY_PATH"
        exit 1
    fi
fi

# Build SSH command
SSH_CMD="ssh"
if [ -n "$SSH_KEY_PATH" ]; then
    SSH_CMD="ssh -i $SSH_KEY_PATH"
fi

SCP_CMD="scp"
if [ -n "$SSH_KEY_PATH" ]; then
    SCP_CMD="scp -i $SSH_KEY_PATH"
fi

print_header "Syncing Files to HPC"
echo ""
echo -e "Target: ${GREEN}${HPC_USER}@${HPC_HOST}${NC}"
echo ""

# Test connection and get remote home directory
print_status "Testing connection to HPC..."
REMOTE_HOME=$($SSH_CMD "${HPC_USER}@${HPC_HOST}" "echo \$HOME" 2>/dev/null)
if [ -z "$REMOTE_HOME" ]; then
    print_error "Failed to connect to HPC"
    print_warning "Make sure your SSH key is configured"
    print_warning "Usage: $0 [path_to_ssh_key]"
    exit 1
fi

HPC_WORK_DIR="${REMOTE_HOME}/${HPC_WORK_DIR_RELATIVE}"
print_status "Connection successful! Remote home: ${REMOTE_HOME}"
print_status "Working directory: ${HPC_WORK_DIR}"

# Create remote directory structure
print_status "Creating remote directory structure..."
$SSH_CMD "${HPC_USER}@${HPC_HOST}" "mkdir -p ${HPC_WORK_DIR}/{ligands,receptors,scripts_hpc,gnina_out,logs,results,visualizations,enhanced_analysis}"

# Copy scripts_hpc directory
print_status "Copying scripts_hpc directory..."
$SCP_CMD -r "${SCRIPT_DIR}/scripts_hpc/" "${HPC_USER}@${HPC_HOST}:${HPC_WORK_DIR}/"

# Copy HPC scripts
print_status "Copying HPC execution scripts..."
$SCP_CMD "${SCRIPT_DIR}/run_gnina_hpc_optimized.sh" "${HPC_USER}@${HPC_HOST}:${HPC_WORK_DIR}/"
$SCP_CMD "${SCRIPT_DIR}/gnina_hpc_optimized.slurm" "${HPC_USER}@${HPC_HOST}:${HPC_WORK_DIR}/"
$SCP_CMD "${SCRIPT_DIR}/test_hpc_setup.sh" "${HPC_USER}@${HPC_HOST}:${HPC_WORK_DIR}/"

# Copy HPC array job script if exists
if [ -f "${SCRIPT_DIR}/hpc/run_gnina_array.sbatch" ]; then
    print_status "Copying HPC array job script..."
    $SSH_CMD "${HPC_USER}@${HPC_HOST}" "mkdir -p ${HPC_WORK_DIR}/hpc"
    $SCP_CMD "${SCRIPT_DIR}/hpc/run_gnina_array.sbatch" "${HPC_USER}@${HPC_HOST}:${HPC_WORK_DIR}/hpc/"
fi

# Copy test script
print_status "Copying test script..."

# Copy requirements if exists
if [ -f "${SCRIPT_DIR}/requirements.txt" ]; then
    print_status "Copying requirements.txt..."
    $SCP_CMD "${SCRIPT_DIR}/requirements.txt" "${HPC_USER}@${HPC_HOST}:${HPC_WORK_DIR}/"
fi

# Copy documentation
print_status "Copying documentation..."
$SCP_CMD "${SCRIPT_DIR}/HPC_SETUP_INSTRUCTIONS.md" "${HPC_USER}@${HPC_HOST}:${HPC_WORK_DIR}/" 2>/dev/null || true

# Set permissions
print_status "Setting file permissions on HPC..."
$SSH_CMD "${HPC_USER}@${HPC_HOST}" "chmod +x ${HPC_WORK_DIR}/run_gnina_hpc_optimized.sh ${HPC_WORK_DIR}/test_hpc_setup.sh ${HPC_WORK_DIR}/gnina_hpc_optimized.slurm 2>/dev/null || true"

echo ""
print_header "Sync Complete"
echo ""
print_status "Files copied successfully!"
echo ""
echo "Next steps:"
echo "  1. Connect to HPC: ./connect_hpc.sh [path_to_ssh_key]"
echo "  2. Navigate to: cd ${HPC_WORK_DIR}"
echo "  3. Run test: ./test_hpc_setup.sh"
echo "  4. Copy your data files (pairlist.csv, ligands/, receptors/)"
echo ""
print_warning "Don't forget to copy your data files:"
echo "  - pairlist.csv"
echo "  - ligands/ directory"
echo "  - receptors/ directory"
echo ""
print_warning "You can copy them manually with:"
echo "  scp -i [key] pairlist.csv ${HPC_USER}@${HPC_HOST}:${HPC_WORK_DIR}/"
echo "  scp -r -i [key] ligands/ ${HPC_USER}@${HPC_HOST}:${HPC_WORK_DIR}/"
echo "  scp -r -i [key] receptors/ ${HPC_USER}@${HPC_HOST}:${HPC_WORK_DIR}/"

