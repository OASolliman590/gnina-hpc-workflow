#!/usr/bin/env bash
set -euo pipefail

# Apptainer image with CUDA runtime + cuDNN; override via IMG env var if needed.
IMG="${IMG:-$HOME/cuda12.3.2-cudnn9-runtime-ubuntu22.04.sif}"

# Run GNINA inside the container with GPU support (`--device` passed through by caller).
exec apptainer exec --nv "$IMG" "$HOME/gnina" "$@"
