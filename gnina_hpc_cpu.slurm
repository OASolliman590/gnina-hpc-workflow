#!/bin/bash

#SBATCH --job-name=gnina_docking_cpu
#SBATCH --partition=cpu
#SBATCH --nodes=1                # Use 1 node
#SBATCH --ntasks=1                # Use 1 task
#SBATCH --cpus-per-task=16       # 16 CPUs per task
#SBATCH --mem=32G                 # More memory for CPU mode
#SBATCH --time=72:00:00
#SBATCH --output=gnina_docking_cpu_%j.out
#SBATCH --error=gnina_docking_cpu_%j.err
#SBATCH --account=your_account      # TODO: Update with your SLURM account

# HPC-Optimized GNINA Docking Pipeline - CPU Mode
# This script runs the optimized docking pipeline on HPC with SLURM using CPU

echo "=========================================="
echo "HPC-Optimized GNINA Docking Pipeline - CPU Mode"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURMD_NODENAME"
echo "Start Time: $(date)"
echo "=========================================="

# Load required modules (adjust based on your HPC)
# module load apptainer/singularity

# Set working directory
cd $HOME/gnina_test

# Display job information
echo "Working Directory: $(pwd)"
echo "CPU Information:"
echo "  CPUs allocated: $SLURM_CPUS_PER_TASK"
echo "  Total CPUs: $SLURM_CPUS_ON_NODE"
echo ""

# Check if required files exist
echo "Checking required files..."
if [ ! -f "pairlist.csv" ]; then
    echo "ERROR: pairlist.csv not found!"
    exit 1
fi

if [ ! -d "ligands" ]; then
    echo "ERROR: ligands directory not found!"
    exit 1
fi

if [ ! -d "receptors" ]; then
    echo "ERROR: receptors directory not found!"
    exit 1
fi

if [ ! -d "scripts_hpc" ]; then
    echo "ERROR: scripts_hpc directory not found!"
    echo "Please copy the HPC-optimized scripts to your HPC system."
    exit 1
fi

echo "✅ All required files found"
echo ""

# Count pairs to process
PAIR_COUNT=$(tail -n +2 pairlist.csv | wc -l)
echo "Number of receptor-ligand pairs to process: $PAIR_COUNT"
echo ""

# Create output directories
mkdir -p gnina_out logs results visualizations enhanced_analysis

# Set CPU mode environment variable
export USE_CPU_MODE=1
export GNINA_CPU_CORES=${SLURM_CPUS_PER_TASK:-16}

# Choose workflow type (default: standard)
WORKFLOW_TYPE=${1:-"standard"}

echo "Starting HPC-optimized GNINA docking workflow: $WORKFLOW_TYPE (CPU MODE)"
echo "=========================================="

# Run the appropriate workflow with CPU mode
case "$WORKFLOW_TYPE" in
    "score-only")
        echo "Running score-only mode (CPU)..."
        USE_CPU_MODE=1 ./run_gnina_hpc_optimized.sh score-only
        ;;
    "standard")
        echo "Running standard docking workflow (CPU)..."
        USE_CPU_MODE=1 ./run_gnina_hpc_optimized.sh standard
        ;;
    "tiered")
        echo "Running tiered workflow (CPU)..."
        USE_CPU_MODE=1 ./run_gnina_hpc_optimized.sh tiered
        ;;
    "covalent")
        echo "Running covalent docking workflow (CPU)..."
        USE_CPU_MODE=1 ./run_gnina_hpc_optimized.sh covalent
        ;;
    *)
        echo "ERROR: Unknown workflow type: $WORKFLOW_TYPE"
        echo "Available options: score-only, standard, tiered, covalent"
        exit 1
        ;;
esac

# Check if the job completed successfully
if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ HPC-Optimized GNINA Docking Pipeline Completed Successfully!"
    echo "End Time: $(date)"
    echo "=========================================="
    
    # Display results summary
    echo "Results Summary:"
    echo "  Output files: $(ls gnina_out/ | wc -l) files in gnina_out/"
    echo "  Log files: $(ls logs/ | wc -l) files in logs/"
    echo "  Results: $(ls results/ | wc -l) files in results/"
    
    if [ -d "visualizations" ] && [ "$(ls -A visualizations)" ]; then
        echo "  Visualizations: $(ls visualizations/ | wc -l) files in visualizations/"
    fi
    
    if [ -d "enhanced_analysis" ] && [ "$(ls -A enhanced_analysis)" ]; then
        echo "  Analysis: $(ls enhanced_analysis/ | wc -l) files in enhanced_analysis/"
    fi
    
    echo ""
    echo "Job completed successfully!"
    
    # Display top results if available
    if [ -f "results/analysis_report.txt" ]; then
        echo ""
        echo "Top Results (from analysis_report.txt):"
        echo "----------------------------------------"
        head -20 results/analysis_report.txt
    fi
    
else
    echo ""
    echo "=========================================="
    echo "❌ HPC-Optimized GNINA Docking Pipeline Failed!"
    echo "End Time: $(date)"
    echo "=========================================="
    echo "Check the error logs for details."
    exit 1
fi

