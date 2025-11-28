#!/bin/bash

# Enhanced GNINA Docking Pipeline
# Bash script to execute all Python scripts for molecular docking
# Based on the Enhanced GNINA Docking Pipeline notebook

# Set script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

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

# Function to check if required files exist
check_requirements() {
    print_header "Checking Requirements"
    
    # Check if GNINA binary exists
    if [ ! -f "./gnina" ]; then
        print_error "GNINA binary not found. Please ensure gnina is in the current directory."
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
        print_error "Python3 not found. Please install Python3."
        exit 1
    fi
    
    print_status "All requirements satisfied!"
}

# Function to install Python dependencies
install_dependencies() {
    print_header "Installing Python Dependencies"
    
    if [ -f "requirements.txt" ]; then
        print_status "Installing dependencies from requirements.txt..."
        pip3 install -r requirements.txt
    else
        print_warning "requirements.txt not found. Installing basic dependencies..."
        pip3 install pandas numpy matplotlib seaborn tqdm
    fi
    
    print_status "Dependencies installation completed!"
}

# Function to run configuration test
run_config_test() {
    print_header "Testing Configuration"
    
    print_status "Running configuration test..."
    python3 scripts/config.py
    
    if [ $? -eq 0 ]; then
        print_status "Configuration test passed!"
    else
        print_error "Configuration test failed!"
        exit 1
    fi
}

# Function to run standard docking
run_standard_docking() {
    print_header "Running Standard Docking"
    
    print_status "Starting standard docking workflow..."
    python3 -c "
import sys
sys.path.append('scripts')
from main_workflow import run_complete_workflow, load_and_validate_pairlist

# Load pairlist
pairlist_df = load_and_validate_pairlist()
if pairlist_df is not None:
    # Run standard docking with flexible receptors
    results = run_complete_workflow(pairlist_df, 'standard', use_flexible=True, cnn_mode='rescore')
    print(f'Standard docking completed with {len(results)} results')
else:
    print('Failed to load pairlist')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        print_status "Standard docking completed successfully!"
    else
        print_error "Standard docking failed!"
        exit 1
    fi
}

# Function to run tiered workflow
run_tiered_workflow() {
    print_header "Running Tiered Workflow"
    
    print_status "Starting tiered workflow (Stages A and B)..."
    python3 -c "
import sys
sys.path.append('scripts')
from main_workflow import run_complete_workflow, load_and_validate_pairlist

# Load pairlist
pairlist_df = load_and_validate_pairlist()
if pairlist_df is not None:
    # Run tiered workflow
    results = run_complete_workflow(pairlist_df, 'tiered', stages=['A', 'B'], use_flexible=True)
    print(f'Tiered workflow completed with {len(results)} results')
else:
    print('Failed to load pairlist')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        print_status "Tiered workflow completed successfully!"
    else
        print_error "Tiered workflow failed!"
        exit 1
    fi
}

# Function to run covalent docking
run_covalent_docking() {
    print_header "Running Covalent Docking"
    
    print_status "Starting covalent docking workflow..."
    print_warning "Make sure to set the correct covalent residue and atom in the script!"
    
    python3 -c "
import sys
sys.path.append('scripts')
from main_workflow import run_complete_workflow, load_and_validate_pairlist

# Load pairlist
pairlist_df = load_and_validate_pairlist()
if pairlist_df is not None:
    # Run covalent docking (modify residue and atom as needed)
    results = run_complete_workflow(pairlist_df, 'covalent', 
                                  covalent_residue='A:123', 
                                  covalent_atom='SG', 
                                  use_flexible=True)
    print(f'Covalent docking completed with {len(results)} results')
else:
    print('Failed to load pairlist')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        print_status "Covalent docking completed successfully!"
    else
        print_error "Covalent docking failed!"
        exit 1
    fi
}

# Function to run analysis only
run_analysis_only() {
    print_header "Running Analysis Only"
    
    print_status "Running post-docking analysis..."
    python3 -c "
import sys
sys.path.append('scripts')
from main_workflow import load_workflow_results
from analysis_tools import DockingAnalysisDashboard, QualityControlValidator

# Load results from previous runs
results = load_workflow_results('standard_docking')
if not results:
    results = load_workflow_results('tiered_workflow')
if not results:
    results = load_workflow_results('covalent_docking')

if results:
    # Run analysis
    dashboard = DockingAnalysisDashboard()
    qc_validator = QualityControlValidator()
    
    dashboard.create_score_distribution_plot(results)
    qc_validator.validate_docking_results(results)
    qc_validator.generate_quality_report()
    
    print(f'Analysis completed for {len(results)} results')
else:
    print('No results found to analyze')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        print_status "Analysis completed successfully!"
    else
        print_error "Analysis failed!"
        exit 1
    fi
}

# Function to run score-only mode
run_score_only() {
    print_header "Running Score-Only Mode"
    
    print_status "Running score-only mode for existing poses..."
    python3 -c "
import sys
sys.path.append('scripts')
from main_workflow import load_and_validate_pairlist
from docking_engine import GNINADockingEngine
from config import GNINADockingConfig

# Load pairlist
pairlist_df = load_and_validate_pairlist()
if pairlist_df is not None:
    # Initialize engine
    config = GNINADockingConfig()
    engine = GNINADockingEngine(config, max_workers=4)
    
    # Run score-only mode
    results = engine.run_score_only(pairlist_df)
    print(f'Score-only mode completed with {len(results)} results')
else:
    print('Failed to load pairlist')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        print_status "Score-only mode completed successfully!"
    else
        print_error "Score-only mode failed!"
        exit 1
    fi
}

# Function to show help
show_help() {
    echo "Enhanced GNINA Docking Pipeline"
    echo ""
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  standard     Run standard docking workflow"
    echo "  tiered       Run tiered workflow (stages A and B)"
    echo "  covalent     Run covalent docking workflow"
    echo "  analysis     Run analysis only (requires existing results)"
    echo "  score-only   Run score-only mode for existing poses"
    echo "  test         Run configuration test only"
    echo "  install      Install Python dependencies"
    echo "  check        Check requirements only"
    echo "  help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 standard     # Run standard docking"
    echo "  $0 tiered       # Run tiered workflow"
    echo "  $0 covalent     # Run covalent docking"
    echo "  $0 analysis     # Analyze existing results"
    echo ""
    echo "Note: Comment out unwanted sections in the script to customize the workflow."
}

# Main execution
main() {
    print_header "Enhanced GNINA Docking Pipeline"
    print_status "Starting GNINA docking pipeline..."
    
    # Check requirements
    check_requirements
    
    # Parse command line arguments
    case "${1:-standard}" in
        "standard")
            install_dependencies
            run_config_test
            run_standard_docking
            ;;
        "tiered")
            install_dependencies
            run_config_test
            run_tiered_workflow
            ;;
        "covalent")
            install_dependencies
            run_config_test
            run_covalent_docking
            ;;
        "analysis")
            run_analysis_only
            ;;
        "score-only")
            install_dependencies
            run_score_only
            ;;
        "test")
            install_dependencies
            run_config_test
            ;;
        "install")
            install_dependencies
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
    print_status "Check the visualizations/ directory for plots."
    print_status "Check the enhanced_analysis/ directory for quality reports."
}

# Run main function
main "$@"
