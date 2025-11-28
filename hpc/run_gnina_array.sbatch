#!/bin/bash
#SBATCH --job-name=gnina_docking
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=16
#SBATCH --time=72:00:00
#SBATCH --output=gnina_docking_%j.out
#SBATCH --error=gnina_docking_%j.err
#SBATCH --account=your_account      # TODO: Update with your SLURM account
##SBATCH --array=1-1  # override when submitting: sbatch --array=1-N run_gnina_array.sbatch

set -euo pipefail

PAIRLIST="${PAIRLIST:-$HOME/gnina_test/pairlist.csv}"
WORK_DIR="${WORK_DIR:-$HOME/gnina_test}"
WRAPPER="${WRAPPER:-$HOME/gnina.sh}"

cd "$WORK_DIR"

# Ensure output dirs exist
mkdir -p gnina_out logs

# Fetch the line for this array index (skip header)
LINE_NUM=$((SLURM_ARRAY_TASK_ID + 1))
line=$(sed -n "${LINE_NUM}p" "$PAIRLIST")
if [ -z "${line:-}" ]; then
    echo "No row for SLURM_ARRAY_TASK_ID=${SLURM_ARRAY_TASK_ID} (line ${LINE_NUM})"
    exit 1
fi

IFS=',' read -r receptor ligand center_x center_y center_z size_x size_y size_z site_id <<< "$line"
site_id=${site_id:-site_1}

out_tag="${receptor}_${site_id}_${ligand}"

echo "[INFO] Processing $receptor / $ligand (site: $site_id)"

"$WRAPPER" \
  -r "receptors/${receptor}" \
  -l "ligands/${ligand}" \
  --center_x "$center_x" --center_y "$center_y" --center_z "$center_z" \
  --size_x "$size_x" --size_y "$size_y" --size_z "$size_z" \
  --exhaustiveness 16 --num_modes 20 \
  --cnn fast \
  --device 0 \
  --out "gnina_out/${out_tag}_poses.sdf" \
  --log "logs/${out_tag}.log"

echo "[INFO] Completed $receptor / $ligand"
