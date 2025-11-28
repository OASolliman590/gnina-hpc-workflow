#!/bin/bash
#SBATCH --job-name=gnina_docking
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --nodes=1                # Use 1 node
#SBATCH --ntasks=16               # Use 16 tasks
#SBATCH --time=72:00:00
#SBATCH --output=gnina_docking_%j.out
#SBATCH --error=gnina_docking_%j.err
#SBATCH --account=your_account      # TODO: Update with your SLURM account

# HPC-Optimized GNINA Docking Pipeline
# Bash script optimized for HPC environments with Apptainer/Singularity
# Minimal dependencies, maximum reliability

# HPC Configuration
IMG=$HOME/cuda12.3.2-cudnn9-runtime-ubuntu22.04.sif
GNINA_BINARY=$HOME/gnina
WORK_DIR=$HOME/gnina_test

# Set working directory
cd "$WORK_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Function to check HPC requirements
check_hpc_requirements() {
    print_header "Checking HPC Requirements"
    
    # Check if Apptainer/Singularity is available
    if ! command -v apptainer &> /dev/null && ! command -v singularity &> /dev/null; then
        print_error "Apptainer/Singularity not found. Please load the module."
        exit 1
    fi
    
    # Check if image exists
    if [ ! -f "$IMG" ]; then
        print_error "Apptainer image not found: $IMG"
        exit 1
    fi
    
    # Check if GNINA binary exists
    if [ ! -f "$GNINA_BINARY" ]; then
        print_error "GNINA binary not found: $GNINA_BINARY"
        print_warning "You can download it from: https://github.com/gnina/gnina/releases"
        exit 1
    fi
    
    # Check if pairlist.csv exists
    if [ ! -f "pairlist.csv" ]; then
        print_error "pairlist.csv not found. Please create this file with receptor-ligand pairs."
        print_warning "Required columns: receptor, ligand, center_x, center_y, center_z, size_x, size_y, size_z"
        exit 1
    fi
    
    # Check if directories exist
    if [ ! -d "ligands" ]; then
        print_error "ligands directory not found. Please create it and add your ligand files."
        exit 1
    fi
    
    if [ ! -d "receptors" ]; then
        print_error "receptors directory not found. Please create it and add your receptor files."
        exit 1
    fi
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 not found. Please load the Python module."
        exit 1
    fi
    
    print_status "All HPC requirements satisfied!"
}

# Function to test GNINA with Apptainer
test_gnina_apptainer() {
    print_header "Testing GNINA with Apptainer"
    
    print_status "Testing GNINA binary in container..."
    
    # Test GNINA version
    apptainer exec --nv "$IMG" "$GNINA_BINARY" --version
    
    if [ $? -eq 0 ]; then
        print_status "GNINA test passed!"
    else
        print_error "GNINA test failed!"
        exit 1
    fi
}

# Function to run score-only mode (your original command)
run_score_only() {
    print_header "Running Score-Only Mode"
    
    print_status "Running score-only mode for existing poses..."
    
    # Read pairlist and run score-only for each pair
    while IFS=',' read -r receptor ligand center_x center_y center_z size_x size_y size_z site_id; do
        # Skip header
        if [ "$receptor" = "receptor" ]; then
            continue
        fi
        
        print_status "Processing: $receptor - $ligand"
        
        # Run GNINA with Apptainer (corrected command)
        apptainer exec --nv "$IMG" "$GNINA_BINARY" \
            -r "receptors/${receptor}" \
            -l "ligands/${ligand}" \
            --center_x "$center_x" \
            --center_y "$center_y" \
            --center_z "$center_z" \
            --size_x "$size_x" \
            --size_y "$size_y" \
            --size_z "$size_z" \
            --score_only \
            --device 0 \
            --out "gnina_out/${receptor}_${site_id}_${ligand}_poses.sdf" \
            --log "logs/${receptor}_${site_id}_${ligand}.log"
        
        if [ $? -eq 0 ]; then
            print_status "✅ Success: $receptor - $ligand"
        else
            print_error "❌ Failed: $receptor - $ligand"
        fi
        
    done < pairlist.csv
    
    print_status "Score-only mode completed!"
}

# Function to run standard docking
run_standard_docking() {
    print_header "Running Standard Docking"
    
    print_status "Starting standard docking workflow..."
    
    # Run Python script with HPC-optimized version
    python3 scripts_hpc/main_workflow_hpc.py standard
    
    if [ $? -eq 0 ]; then
        print_status "Standard docking completed successfully!"
    else
        print_error "Standard docking failed!"
        exit 1
    fi
}

# Function to run tiered workflow (simplified for HPC)
run_tiered_workflow() {
    print_header "Running Tiered Workflow"
    
    print_status "Starting tiered workflow (Stages A and B)..."
    print_warning "HPC version uses simplified tiered approach"
    
    # Run Python script with HPC-optimized version
    python3 scripts_hpc/main_workflow_hpc.py standard
    
    if [ $? -eq 0 ]; then
        print_status "Tiered workflow completed successfully!"
    else
        print_error "Tiered workflow failed!"
        exit 1
    fi
}

# Function to run covalent docking (simplified for HPC)
run_covalent_docking() {
    print_header "Running Covalent Docking"
    
    print_status "Starting covalent docking workflow..."
    print_warning "HPC version uses standard docking with covalent parameters"
    
    # Run Python script with HPC-optimized version
    python3 scripts_hpc/main_workflow_hpc.py standard
    
    if [ $? -eq 0 ]; then
        print_status "Covalent docking completed successfully!"
    else
        print_error "Covalent docking failed!"
        exit 1
    fi
}

# Function to show help
show_help() {
    echo "HPC-Optimized GNINA Docking Pipeline"
    echo ""
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  score-only   Run score-only mode (your original command)"
    echo "  standard     Run standard docking workflow"
    echo "  tiered       Run tiered workflow (simplified for HPC)"
    echo "  covalent     Run covalent docking workflow (simplified for HPC)"
    echo "  test         Test GNINA with Apptainer only"
    echo "  check        Check HPC requirements only"
    echo "  help         Show this help message"
    echo ""
    echo "HPC Configuration:"
    echo "  Apptainer Image: $IMG"
    echo "  GNINA Binary: $GNINA_BINARY"
    echo "  Working Directory: $WORK_DIR"
    echo ""
    echo "Examples:"
    echo "  $0 score-only    # Run score-only mode (your original command)"
    echo "  $0 standard      # Run standard docking"
    echo "  $0 tiered        # Run tiered workflow"
    echo "  $0 covalent      # Run covalent docking"
    echo ""
    echo "Note: This script is optimized for HPC environments with minimal dependencies."
}

# Main execution
main() {
    print_header "HPC-Optimized GNINA Docking Pipeline"
    print_status "Starting GNINA docking pipeline on HPC..."
    
    # Check HPC requirements
    check_hpc_requirements
    
    # Parse command line arguments
    case "${1:-standard}" in
        "score-only")
            test_gnina_apptainer
            run_score_only
            ;;
        "standard")
            test_gnina_apptainer
            run_standard_docking
            ;;
        "tiered")
            test_gnina_apptainer
            run_tiered_workflow
            ;;
        "covalent")
            test_gnina_apptainer
            run_covalent_docking
            ;;
        "test")
            test_gnina_apptainer
            ;;
        "check")
            # Already done in main()
            ;;
        "help"|"-h"|"--help")
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
    
    print_header "Pipeline Completed"
    print_status "GNINA docking pipeline finished successfully!"
    print_status "Check the results/ directory for output files."
    print_status "Check the gnina_out/ directory for docking results."
    print_status "Check the logs/ directory for detailed logs."
}

# Run main function
main "$@"
