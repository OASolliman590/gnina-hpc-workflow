# Enhanced GNINA Docking Pipeline

A production-ready molecular docking pipeline using [GNINA](https://github.com/gnina/gnina) optimized for both local and HPC environments. Includes comprehensive bug fixes, SLURM integration, and support for multiple docking modes.

## 🎯 Features

### Core Functionality
- **Standard Docking**: Single-stage docking with configurable CNN modes
- **Tiered Workflow**: Multi-stage funnel approach (A → B → C) for large libraries
- **Covalent Docking**: Specialized covalent bond formation
- **Score-Only Mode**: Fast re-scoring of existing poses
- **Flexible Receptors**: Auto-detection and manual specification
- **Parallel Processing**: Multi-threaded execution with resume capability
- **GPU/CPU Support**: Automatic detection and optimization for both

### HPC Optimizations
- ✅ **Tested on HPC**: Successfully tested on HPC systems with SLURM
- ✅ **SLURM Integration**: Ready-to-use job scripts for GPU and CPU partitions
- ✅ **Minimal Dependencies**: HPC version uses only standard Python libraries
- ✅ **Container Support**: Optimized for Apptainer/Singularity
- ✅ **Bug Fixes**: Resolved critical GNINA command-line argument issues

### Analysis & Visualization
- **Score Distribution Analysis**: Comprehensive statistical analysis
- **Interactive Dashboards**: Plotly-based visualizations (local version)
- **Quality Control**: Automated validation and recommendations
- **Progress Tracking**: Real-time progress monitoring
- **Export Capabilities**: JSON, CSV, and visualization exports

## 📦 Installation

### Prerequisites
- Python 3.7+
- GNINA binary (download from [GitHub releases](https://github.com/gnina/gnina/releases))
- CUDA-compatible GPU (optional, for acceleration)
- Apptainer/Singularity (for HPC)

### Local Setup
1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd gnina-hpc-workflow
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   # Or minimal dependencies:
   pip install -r requirements-core.txt
   ```

3. (Optional) Create conda environment:
   ```bash
   conda env create -f environment.yml
   conda activate gnina-auto
   ```

4. Download GNINA binary:
   ```bash
   wget https://github.com/gnina/gnina/releases/download/v1.3.2/gnina
   chmod +x gnina
   ```

5. Validate your pairlist:
   ```bash
   python3 scripts/validate_pairlist.py pairlist.csv
   ```

## 🚀 Quick Start

### Local Usage

#### Standard Docking (Recommended)
```bash
./run_gnina_docking.sh standard
```

#### Other Workflows
```bash
./run_gnina_docking.sh tiered      # For large libraries
./run_gnina_docking.sh covalent    # For covalent inhibitors
./run_gnina_docking.sh score-only  # Re-score existing poses
./run_gnina_docking.sh test        # Test setup
```

### HPC Usage

#### 1. Sync Files to HPC
```bash
./sync_to_hpc.sh [path_to_ssh_key]
```

#### 2. Connect to HPC
```bash
./connect_hpc.sh [path_to_ssh_key]
```

#### 3. Copy Data Files
```bash
scp -i [key] pairlist.csv user@hpc:$HOME/gnina_test/
scp -r -i [key] ligands/ user@hpc:$HOME/gnina_test/
scp -r -i [key] receptors/ user@hpc:$HOME/gnina_test/
```

#### 4. Test Setup
```bash
ssh user@hpc
cd $HOME/gnina_test
./test_hpc_setup.sh
```

#### 5. Submit Job
```bash
# GPU job
sbatch gnina_hpc_optimized.slurm standard

# CPU job
sbatch gnina_hpc_cpu.slurm standard

# Check status
squeue -u $USER
```

## 📁 Project Structure

```
gnina-hpc-workflow/
├── scripts/                  # Local Python modules (full-featured)
│   ├── config.py
│   ├── docking_engine.py
│   ├── tiered_workflow.py
│   ├── flexible_receptor.py
│   ├── covalent_docking.py
│   ├── analysis_tools.py
│   └── main_workflow.py
│
├── scripts_hpc/             # HPC Python modules (minimal dependencies)
│   ├── config_hpc.py
│   ├── docking_engine_hpc.py
│   └── main_workflow_hpc.py
│
├── ligands/                 # Ligand PDBQT files (gitignored)
├── receptors/               # Receptor PDBQT files (gitignored)
│
├── run_gnina_docking.sh     # Local workflow runner
├── run_gnina_hpc_optimized.sh  # HPC workflow runner
├── gnina_hpc_optimized.slurm   # GPU SLURM script
├── gnina_hpc_cpu.slurm      # CPU SLURM script
├── sync_to_hpc.sh           # HPC file sync utility
├── connect_hpc.sh           # HPC connection helper
├── test_hpc_setup.sh        # HPC setup tester
│
├── hpc/                     # HPC array job scripts
│   └── run_gnina_array.sbatch
│
├── infra/                   # Infrastructure scripts
│   └── gnina.sh
│
├── example_usage.py         # Usage examples
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## 🎯 Docking Modes

### 1. Score-Only Mode
**Fastest mode** - Scores existing poses without docking.

**Use Cases:**
- Re-scoring poses from other docking software
- Validating experimental structures
- Comparing scoring functions

**Command:**
```bash
# Local
./run_gnina_docking.sh score-only

# HPC
sbatch gnina_hpc_optimized.slurm score-only
```

**Speed:** ⚡⚡⚡⚡⚡ (Seconds per pose)

---

### 2. Standard Docking
**Most versatile** - Full docking with configurable CNN modes.

**Use Cases:**
- General-purpose molecular docking
- Virtual screening
- Binding mode prediction
- Lead optimization

**CNN Mode Options:**

| Mode | Speed | Accuracy | Best For |
|------|-------|----------|----------|
| `rescore` (default) | ⚡⚡⚡⚡ | ⭐⭐⭐⭐ | General-purpose, large libraries |
| `refinement` | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | Higher accuracy, smaller libraries |
| `all` | ⚡⚡ | ⭐⭐⭐⭐⭐ | Maximum accuracy, very small libraries |
| `none` | ⚡⚡⚡⚡⚡ | ⭐⭐⭐ | Quick screening, no GPU |

**Command:**
```bash
# Local
./run_gnina_docking.sh standard

# HPC
sbatch gnina_hpc_optimized.slurm standard
```

**Speed:** ⚡⚡⚡⚡ (1-5 min/pair on GPU, 10-30 min/pair on CPU)

---

### 3. Tiered Workflow
**Multi-stage funnel** - Progressively filters ligands through increasingly accurate stages.

**Stages:**
- **Stage A**: Broad screening (`rescore`, fast) → Top 10%
- **Stage B**: Focused refinement (`refinement`, medium) → Top 1%
- **Stage C**: High-accuracy validation (`all`, slow) → Top 0.1%

**Use Cases:**
- Large virtual screening libraries (>1000 compounds)
- When computational resources are limited
- Progressive filtering workflows

**Command:**
```bash
# Local
./run_gnina_docking.sh tiered

# HPC
sbatch gnina_hpc_optimized.slurm tiered
```

---

### 4. Covalent Docking
**Specialized mode** - For covalent inhibitors that form bonds with proteins.

**Requirements:**
- Reactive residue (e.g., `A:123` for chain A, residue 123)
- Reactive atom (e.g., `SG` for cysteine)
- Ligand with reactive groups (Michael acceptors, aldehydes, epoxides)

**Common Targets:**
- Cysteine (SG) - Most common
- Lysine (NZ)
- Serine (OG)
- Threonine (OG1)

**Command:**
```bash
# Local
./run_gnina_docking.sh covalent

# HPC
sbatch gnina_hpc_optimized.slurm covalent
```

---

## 🔧 Configuration

### Performance Parameters

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| `exhaustiveness` | 8-64 | 32 | Search thoroughness (higher = more thorough) |
| `num_modes` | 1-50 | 20 | Maximum binding modes to generate |
| `cpu_cores` | 1-16 | 4 | CPU cores for fallback |
| `timeout` | seconds | 300 | Timeout per docking |

### CNN Scoring Modes

- **`none`**: No CNNs, empirical scoring only (fastest, no GPU needed)
- **`rescore`**: CNN reranking of final poses (fast, default, recommended)
- **`refinement`**: CNN pose refinement (10x slower, higher accuracy)
- **`all`**: CNN throughout entire procedure (100x slower, best accuracy)

### GPU vs CPU

- **GPU**: 10-50x speedup, use `--device 0` when available
- **CPU**: Automatic fallback, slower but reliable
- **HPC**: Set `USE_CPU_MODE=1` environment variable for CPU-only jobs

## 🖥️ HPC Setup

### Prerequisites
- Apptainer/Singularity module loaded
- GNINA binary at `$HOME/gnina`
- Container image at `$HOME/cuda12.3.2-cudnn9-runtime-ubuntu22.04.sif`
- Working directory: `$HOME/gnina_test`

### Quick Setup Steps

1. **Sync files:**
   ```bash
   ./sync_to_hpc.sh [ssh_key_path]
   ```

2. **Connect and test:**
   ```bash
   ./connect_hpc.sh [ssh_key_path]
   cd $HOME/gnina_test
   ./test_hpc_setup.sh
   ```

3. **Copy data files:**
   ```bash
   # From local machine
   scp -i [key] pairlist.csv user@hpc:$HOME/gnina_test/
   scp -r -i [key] ligands/ user@hpc:$HOME/gnina_test/
   scp -r -i [key] receptors/ user@hpc:$HOME/gnina_test/
   ```

4. **Submit job:**
   ```bash
   sbatch gnina_hpc_optimized.slurm standard
   ```

### SLURM Scripts

#### GPU Job (`gnina_hpc_optimized.slurm`)
```bash
#!/bin/bash
#SBATCH --job-name=gnina_docking
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=16
#SBATCH --time=72:00:00
#SBATCH --account=your_account      # TODO: Update with your SLURM account
```

#### CPU Job (`gnina_hpc_cpu.slurm`)
```bash
#!/bin/bash
#SBATCH --job-name=gnina_docking_cpu
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=72:00:00
#SBATCH --account=your_account      # TODO: Update with your SLURM account
```

### Monitoring Jobs

```bash
# Check job status
squeue -u $USER

# View output
tail -f gnina_docking_*.out

# Check progress
ls -lh gnina_out/*.sdf | wc -l

# Monitor specific job
squeue -j JOBID
```

## 🐛 Bug Fixes Included

This repository includes fixes for common GNINA issues:

1. **`--addH` flag**: Now correctly passes `--addH on` instead of just `--addH`
2. **`--pose_sort_order`**: Uses string values (`CNNscore`, `CNNaffinity`, `Energy`) instead of numbers
3. **File extensions**: Automatically adds `.pdbqt` extension if missing
4. **GPU flag**: Uses `--device 0` instead of deprecated `--gpu`
5. **CPU mode**: Proper environment variable support (`USE_CPU_MODE=1`)

## 📊 Performance Expectations

### Speed Comparison

| Mode | GPU Time | CPU Time | Relative Speed |
|------|----------|----------|----------------|
| Score-only | 5-10 sec | 30-60 sec | 10x faster |
| Standard (rescore) | 1-5 min | 10-30 min | Baseline |
| Standard (refinement) | 10-50 min | 2-8 hours | 10x slower |
| Standard (all) | 1-5 hours | 10-50 hours | 100x slower |

### Accuracy Comparison

| Mode | Binding Affinity | Pose Quality | Overall |
|------|-----------------|--------------|---------|
| `none` | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| `rescore` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| `refinement` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| `all` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## 🚨 Troubleshooting

### Common Issues

1. **"Command line parse error: the required argument for option '--addH' is missing"**
   - **Fixed**: Code now passes `--addH on` correctly

2. **"Command line parse error: the argument for option '--pose_sort_order' is invalid"**
   - **Fixed**: Code now uses string values (`CNNscore`) instead of numbers

3. **"could not open ligands/... for reading"**
   - **Fixed**: Code automatically adds `.pdbqt` extension if missing

4. **"unrecognised option '--gpu'"**
   - **Fixed**: Uses `--device 0` instead

5. **GPU not detected**
   - **Solution**: Use `--nv` flag with Apptainer
   - **Check**: Run `nvidia-smi` inside container
   - **Fallback**: Pipeline automatically uses CPU

### Performance Tips

- **Always use GPU** when available (10-50x speedup)
- **Start with `rescore`** mode (best balance)
- **Use tiered workflow** for libraries >1000 compounds
- **Increase exhaustiveness** for better accuracy (32-64)
- **Monitor resources** with `nvidia-smi` or `htop`

## 📝 Input Format

### pairlist.csv

Required columns:
```csv
receptor,ligand,center_x,center_y,center_z,size_x,size_y,size_z,site_id
receptor1.pdbqt,ligand1.pdbqt,10.5,20.3,15.7,20,20,20,site_1
```

- **receptor**: Receptor PDBQT filename (with or without `.pdbqt`)
- **ligand**: Ligand PDBQT filename (with or without `.pdbqt`)
- **center_x/y/z**: Binding site center coordinates (Angstroms)
- **size_x/y/z**: Search box dimensions (Angstroms)
- **site_id**: Optional site identifier (defaults to `site_1`)

## 📚 Python API

### Basic Usage

```python
import sys
sys.path.append('scripts')
from main_workflow import run_complete_workflow, load_and_validate_pairlist

# Load pairlist
pairlist_df = load_and_validate_pairlist()

# Standard docking
results = run_complete_workflow(
    pairlist_df, 
    'standard', 
    use_flexible=True, 
    cnn_mode='rescore'
)

# Tiered workflow
results = run_complete_workflow(
    pairlist_df, 
    'tiered', 
    stages=['A', 'B']
)

# Covalent docking
results = run_complete_workflow(
    pairlist_df, 
    'covalent', 
    covalent_residue='A:123', 
    covalent_atom='SG'
)
```

### Custom Configuration

```python
from config import GNINADockingConfig

config = GNINADockingConfig()
config.set_performance_params(exhaustiveness=48, num_modes=30)
config.set_gpu_acceleration(use_gpu=True, gpu_device=0)
config.set_cnn_mode('refinement')
```

## 🎯 Choosing the Right Mode

### Decision Tree

```
Do you have existing poses?
├─ YES → Use "score-only" mode
└─ NO → Continue

Is it a covalent inhibitor?
├─ YES → Use "covalent" mode
└─ NO → Continue

How many ligands?
├─ < 100 → Use "standard" with "refinement" or "all"
├─ 100-1000 → Use "standard" with "rescore"
└─ > 1000 → Use "tiered" workflow

Do you need maximum accuracy?
├─ YES → Use "refinement" or "all" mode
└─ NO → Use "rescore" mode (default)
```

## 📖 References

- **GNINA Repository**: https://github.com/gnina/gnina
- **GNINA Paper**: McNutt et al., J. Chem. Inf. Model. (2021)
- **Apptainer Documentation**: https://apptainer.org/docs/
- **SLURM Documentation**: https://slurm.schedmd.com/

## 🤝 Contributing

Contributions are welcome! Please ensure:
- Code follows existing style (snake_case for functions, CapWords for classes)
- Tests pass
- Documentation is updated
- Bug fixes are documented

## 📄 License

This project is based on the Enhanced GNINA Docking Pipeline and follows the same licensing terms as GNINA.

## ⚠️ Important Notes

- **Data Files**: `pairlist.csv` and data directories are gitignored - you must provide your own
- **Binaries**: GNINA binary and container images are not included - download separately
- **HPC Configuration**: Update SLURM scripts with your account and email
- **File Extensions**: Code automatically handles missing `.pdbqt` extensions

## 🎉 Production Ready

This workflow has been successfully tested and is production-ready:
- ✅ **HPC Tested**: Successfully running on HPC systems with SLURM
- ✅ **Tested**: Multiple receptor-ligand pairs processed successfully
- ✅ **Configuration**: Supports exhaustiveness 32, CPU/GPU modes
- ✅ **Status**: Production-ready and working

---

**Last Updated**: November 2024  
**GNINA Version**: v1.3  
**Status**: ✅ Production Ready
