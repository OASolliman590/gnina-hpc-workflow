#!/bin/bash

# HPC Setup Test Script
# This script tests the GNINA pipeline setup on HPC
# Run this script ON the HPC system after copying files

# HPC Configuration
IMG=$HOME/cuda12.3.2-cudnn9-runtime-ubuntu22.04.sif
GNINA_BINARY=$HOME/gnina
WORK_DIR=$HOME/gnina_test

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -n "Testing: $test_name... "
    if eval "$test_command" > /dev/null 2>&1; then
        print_status "$test_name"
        ((TESTS_PASSED++))
        return 0
    else
        print_error "$test_name"
        ((TESTS_FAILED++))
        return 1
    fi
}

print_header "HPC Setup Test Suite"
echo ""

# Test 1: Check if we're on HPC
print_header "Environment Tests"
run_test "Current directory is \$HOME/gnina_test" "[ \"\$(pwd)\" = \"\$WORK_DIR\" ] || cd \$WORK_DIR"

# Test 2: Check Apptainer/Singularity
print_header "Container System Tests"
if command -v apptainer &> /dev/null; then
    print_status "Apptainer found: $(apptainer --version | head -n1)"
    CONTAINER_CMD="apptainer"
elif command -v singularity &> /dev/null; then
    print_status "Singularity found: $(singularity --version | head -n1)"
    CONTAINER_CMD="singularity"
else
    print_error "Neither Apptainer nor Singularity found"
    print_warning "Load module with: module load apptainer/singularity"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    CONTAINER_CMD=""
fi

# Test 3: Check container image
if [ -n "$CONTAINER_CMD" ]; then
    run_test "Container image exists" "[ -f \"\$IMG\" ]"
    
    if [ -f "$IMG" ]; then
        print_status "Image path: $IMG"
        print_status "Image size: $(du -h "$IMG" | cut -f1)"
    fi
fi

# Test 4: Check GNINA binary
print_header "GNINA Binary Tests"
run_test "GNINA binary exists" "[ -f \"\$GNINA_BINARY\" ]"

if [ -f "$GNINA_BINARY" ]; then
    print_status "GNINA binary path: $GNINA_BINARY"
    print_status "GNINA binary size: $(du -h "$GNINA_BINARY" | cut -f1)"
    
    # Test GNINA version (if container available)
    if [ -n "$CONTAINER_CMD" ] && [ -f "$IMG" ]; then
        echo -n "Testing GNINA version... "
        if $CONTAINER_CMD exec --nv "$IMG" "$GNINA_BINARY" --version > /dev/null 2>&1; then
            print_status "GNINA works in container"
            $CONTAINER_CMD exec --nv "$IMG" "$GNINA_BINARY" --version
        else
            print_error "GNINA failed in container"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
    fi
fi

# Test 5: Check Python
print_header "Python Environment Tests"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_status "Python3 found: $PYTHON_VERSION"
    run_test "Python3 is executable" "python3 --version > /dev/null 2>&1"
else
    print_error "Python3 not found"
    print_warning "Load module with: module load python/3.x"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 6: Check project structure
print_header "Project Structure Tests"
run_test "Working directory exists" "[ -d \"\$WORK_DIR\" ]"
run_test "ligands directory exists" "[ -d \"\$WORK_DIR/ligands\" ]"
run_test "receptors directory exists" "[ -d \"\$WORK_DIR/receptors\" ]"
run_test "pairlist.csv exists" "[ -f \"\$WORK_DIR/pairlist.csv\" ]"
run_test "scripts_hpc directory exists" "[ -d \"\$WORK_DIR/scripts_hpc\" ]"

# Test 7: Check HPC scripts
print_header "HPC Scripts Tests"
if [ -d "$WORK_DIR/scripts_hpc" ]; then
    run_test "config_hpc.py exists" "[ -f \"\$WORK_DIR/scripts_hpc/config_hpc.py\" ]"
    run_test "docking_engine_hpc.py exists" "[ -f \"\$WORK_DIR/scripts_hpc/docking_engine_hpc.py\" ]"
    run_test "main_workflow_hpc.py exists" "[ -f \"\$WORK_DIR/scripts_hpc/main_workflow_hpc.py\" ]"
fi

# Test 8: Check run script
run_test "run_gnina_hpc_optimized.sh exists" "[ -f \"\$WORK_DIR/run_gnina_hpc_optimized.sh\" ]"
if [ -f "$WORK_DIR/run_gnina_hpc_optimized.sh" ]; then
    run_test "run_gnina_hpc_optimized.sh is executable" "[ -x \"\$WORK_DIR/run_gnina_hpc_optimized.sh\" ]"
fi

# Test 9: Check SLURM script
run_test "gnina_hpc_optimized.slurm exists" "[ -f \"\$WORK_DIR/gnina_hpc_optimized.slurm\" ]"

# Test 10: Check GPU availability
print_header "GPU Tests"
if command -v nvidia-smi &> /dev/null; then
    print_status "nvidia-smi found"
    echo ""
    echo "GPU Information:"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    echo ""
    run_test "GPU is accessible" "nvidia-smi > /dev/null 2>&1"
else
    print_warning "nvidia-smi not found (GPU may not be available)"
fi

# Test 11: Check pairlist.csv format
print_header "Data Validation Tests"
if [ -f "$WORK_DIR/pairlist.csv" ]; then
    PAIR_COUNT=$(tail -n +2 "$WORK_DIR/pairlist.csv" 2>/dev/null | wc -l)
    if [ "$PAIR_COUNT" -gt 0 ]; then
        print_status "Found $PAIR_COUNT receptor-ligand pairs in pairlist.csv"
    else
        print_warning "pairlist.csv exists but contains no pairs (only header?)"
    fi
    
    # Check if required columns exist
    HEADER=$(head -n1 "$WORK_DIR/pairlist.csv")
    if echo "$HEADER" | grep -q "receptor"; then
        print_status "pairlist.csv has 'receptor' column"
    else
        print_error "pairlist.csv missing 'receptor' column"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
fi

# Test 12: Check output directories
print_header "Output Directory Tests"
mkdir -p "$WORK_DIR/gnina_out" "$WORK_DIR/logs" "$WORK_DIR/results" "$WORK_DIR/visualizations" "$WORK_DIR/enhanced_analysis"
run_test "Output directories created" "[ -d \"\$WORK_DIR/gnina_out\" ]"

# Summary
echo ""
print_header "Test Summary"
echo ""
echo -e "Tests Passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "Tests Failed: ${RED}${TESTS_FAILED}${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    print_status "All tests passed! Your HPC setup is ready."
    echo ""
    echo "Next steps:"
    echo "  1. Run: ./run_gnina_hpc_optimized.sh check"
    echo "  2. Run: ./run_gnina_hpc_optimized.sh test"
    echo "  3. Submit job: sbatch gnina_hpc_optimized.slurm standard"
    exit 0
else
    print_error "Some tests failed. Please fix the issues above."
    exit 1
fi

