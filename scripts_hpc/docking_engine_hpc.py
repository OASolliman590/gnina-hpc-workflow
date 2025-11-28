#!/usr/bin/env python3
"""
HPC-Optimized GNINA Docking Engine

This module provides a simplified docking engine for executing GNINA docking operations
optimized for HPC environments with Apptainer/Singularity containers.

Minimal dependencies - only uses standard Python libraries.
References: https://github.com/gnina/gnina
"""

import os
import sys
import subprocess
import csv
import time
from datetime import datetime

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config_hpc import HPCGNINAConfig


class HPCGNINAEngine:
    """
    Simplified GNINA docking engine optimized for HPC environments.
    Uses direct subprocess calls with minimal dependencies.
    """
    
    def __init__(self, max_workers=4):
        self.config = HPCGNINAConfig()
        self.max_workers = max_workers
        
        # Ensure output directories exist
        self.create_directories()
        
        # Progress tracking
        self.completed_pairs = set()
        self.total_pairs = 0
    
    def create_directories(self):
        """Create necessary output directories"""
        dirs = ['gnina_out', 'logs', 'results', 'visualizations', 'enhanced_analysis']
        for dir_name in dirs:
            os.makedirs(dir_name, exist_ok=True)
    
    def read_pairlist(self, filename='pairlist.csv'):
        """Read pairlist CSV file"""
        pairs = []
        try:
            with open(filename, 'r') as f:
                reader = csv.DictReader(f)
                required_cols = ['receptor', 'ligand', 'center_x', 'center_y', 'center_z', 'size_x', 'size_y', 'size_z']
                for line_num, row in enumerate(reader, start=2):  # start=2 accounts for header line
                    # Normalize keys/values
                    normalized = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}

                    # Check required columns
                    missing = [col for col in required_cols if col not in normalized or normalized[col] in (None, '')]
                    if missing:
                        print(f"❌ Missing columns {missing} at line {line_num} in {filename}")
                        return []

                    # Convert numeric fields
                    numeric_fields = ['center_x', 'center_y', 'center_z', 'size_x', 'size_y', 'size_z']
                    for field in numeric_fields:
                        try:
                            normalized[field] = float(normalized[field])
                        except (TypeError, ValueError):
                            print(f"❌ Non-numeric value for {field} at line {line_num}: {normalized[field]}")
                            return []

                    # Default site_id
                    if 'site_id' not in normalized or normalized['site_id'] in (None, ''):
                        normalized['site_id'] = 'site_1'

                    pairs.append(normalized)

            print(f"✅ Loaded {len(pairs)} pairs from {filename}")
        except Exception as e:
            print(f"❌ Error reading {filename}: {e}")
            return []
        return pairs
    
    def build_gnina_command(self, row):
        """Build GNINA command for a single docking run on HPC"""
        # Add .pdbqt extension if not present
        receptor_name = row['receptor']
        if not receptor_name.endswith('.pdbqt'):
            receptor_name += '.pdbqt'
        receptor = f"receptors/{receptor_name}"
        
        ligand_name = row['ligand']
        if not ligand_name.endswith('.pdbqt'):
            ligand_name += '.pdbqt'
        ligand = f"ligands/{ligand_name}"
        
        # Output files
        tag = f"{row['receptor']}_{row['site_id']}_{row['ligand']}"
        output_sdf = f"gnina_out/{tag}_poses.sdf"
        log_file = f"logs/{tag}.log"
        
        # GNINA arguments (without binary)
        gnina_args = [
            "--receptor", receptor,
            "--ligand", ligand,
            "--out", output_sdf,
            "--log", log_file,
        ]
        
        # Docking box parameters
        gnina_args.extend([
            "--center_x", str(row['center_x']),
            "--center_y", str(row['center_y']),
            "--center_z", str(row['center_z']),
            "--size_x", str(row['size_x']),
            "--size_y", str(row['size_y']),
            "--size_z", str(row['size_z']),
        ])
        
        # Add base configuration arguments (includes GPU/CPU selection)
        gnina_args.extend(self.config.get_gnina_command_base())
        
        # Build complete Apptainer command
        cmd = self.config.get_apptainer_command(gnina_args)
        
        return cmd, output_sdf, log_file
    
    def run_single_docking(self, row):
        """Run docking for a single ligand-receptor pair"""
        try:
            # Check if already completed (resume capability)
            pair_id = f"{row['receptor']}_{row['site_id']}_{row['ligand']}"
            if pair_id in self.completed_pairs:
                print(f"   ⏭️ Skipping already completed: {pair_id}")
                return None
            
            # Build command
            cmd, output_sdf, log_file = self.build_gnina_command(row)
            
            # Run GNINA
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=self.config.active_config['timeout']
            )
            
            # Parse results
            if result.returncode == 0 and os.path.exists(output_sdf):
                scores = self.parse_gnina_output(output_sdf, log_file)
                return {
                    'status': 'success',
                    'receptor': row['receptor'],
                    'ligand': row['ligand'],
                    'site_id': row['site_id'],
                    'output_file': output_sdf,
                    'log_file': log_file,
                    'scores': scores,
                    'command': ' '.join(cmd),
                    'pair_id': pair_id
                }
            else:
                return {
                    'status': 'error',
                    'receptor': row['receptor'],
                    'ligand': row['ligand'],
                    'site_id': row['site_id'],
                    'error': result.stderr,
                    'returncode': result.returncode,
                    'pair_id': pair_id
                }
                
        except subprocess.TimeoutExpired:
            return {
                'status': 'timeout',
                'receptor': row['receptor'],
                'ligand': row['ligand'],
                'site_id': row['site_id'],
                'error': f"Timeout after {self.config.active_config['timeout']}s",
                'pair_id': pair_id
            }
        except Exception as e:
            return {
                'status': 'error',
                'receptor': row['receptor'],
                'ligand': row['ligand'],
                'site_id': row['site_id'],
                'error': str(e),
                'pair_id': pair_id
            }
    
    def parse_gnina_output(self, output_sdf, log_file):
        """Parse GNINA output files to extract scores"""
        scores = []
        
        try:
            # Parse SDF file for pose information
            if os.path.exists(output_sdf):
                with open(output_sdf, 'r') as f:
                    content = f.read()
                    
                # Extract scores from SDF data
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'CNNscore' in line:
                        try:
                            cnn_score = float(line.split()[-1])
                            scores.append({
                                'pose_id': len(scores) + 1,
                                'cnn_score': cnn_score,
                                'cnn_affinity': cnn_score  # Simplified
                            })
                        except:
                            continue
            
            # Parse log file for additional information
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    log_content = f.read()
                    
                # Extract timing and other metrics
                if 'Total time' in log_content:
                    # Add timing information if available
                    pass
                    
        except Exception as e:
            print(f"⚠️ Error parsing output for {output_sdf}: {e}")
        
        return scores
    
    def run_batch_docking(self, pairlist_file='pairlist.csv'):
        """Run docking for all pairs in batch mode"""
        pairs = self.read_pairlist(pairlist_file)
        
        if not pairs:
            print("❌ No pairs to process")
            return []
        
        self.total_pairs = len(pairs)
        print(f"🚀 Starting batch docking: {self.total_pairs} pairs")
        print(f"   CNN Scoring: {self.config.active_config['cnn_scoring']}")
        print(f"   GPU: {'Enabled' if self.config.active_config.get('use_gpu', False) else 'Disabled'}")
        print(f"   Exhaustiveness: {self.config.active_config['exhaustiveness']}")
        print()
        
        # Load completed pairs for resume capability
        self.load_completed_pairs()
        
        results = []
        successful = 0
        failed = 0
        
        for i, row in enumerate(pairs, 1):
            print(f"[{i}/{self.total_pairs}] ", end="")
            result = self.run_single_docking(row)
            
            if result:
                results.append(result)
                
                if result['status'] == 'success':
                    successful += 1
                    self.completed_pairs.add(result['pair_id'])
                    print(f"✅ {row['receptor']}-{row['ligand']}")
                else:
                    failed += 1
                    print(f"❌ {row['receptor']}-{row['ligand']} ({result['status']})")
        
        # Final summary
        print(f"\n📊 Batch Docking Summary:")
        print(f"   Total pairs: {self.total_pairs}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {failed}")
        print(f"   Success rate: {successful/self.total_pairs*100:.1f}%")
        
        # Save results
        self.save_results(results)
        
        return results
    
    def load_completed_pairs(self):
        """Load list of completed pairs from output files"""
        if os.path.exists('gnina_out'):
            for file in os.listdir('gnina_out'):
                if file.endswith('_poses.sdf'):
                    # Extract pair ID from filename
                    pair_id = file.replace('_poses.sdf', '')
                    self.completed_pairs.add(pair_id)
        
        print(f"✅ Found {len(self.completed_pairs)} previously completed pairs")
    
    def save_results(self, results):
        """Save results to file"""
        try:
            with open('results/docking_results.txt', 'w') as f:
                f.write(f"GNINA Docking Results - {datetime.now().isoformat()}\n")
                f.write("=" * 50 + "\n\n")
                
                for result in results:
                    f.write(f"Pair: {result['receptor']}-{result['ligand']}\n")
                    f.write(f"Status: {result['status']}\n")
                    if result['status'] == 'success' and 'scores' in result:
                        f.write(f"Scores: {len(result['scores'])} poses\n")
                        for score in result['scores']:
                            f.write(f"  Pose {score['pose_id']}: CNN Score = {score['cnn_score']:.3f}\n")
                    f.write("\n")
            
            print("✅ Results saved to results/docking_results.txt")
        except Exception as e:
            print(f"⚠️ Error saving results: {e}")
    
    def run_score_only(self, pairlist_file='pairlist.csv'):
        """Run score-only mode for existing poses"""
        print("🔍 Running score-only mode...")
        
        pairs = self.read_pairlist(pairlist_file)
        results = []
        
        for row in pairs:
            pair_id = f"{row['receptor']}_{row['site_id']}_{row['ligand']}"
            output_sdf = f"gnina_out/{pair_id}_poses.sdf"
            
            if os.path.exists(output_sdf):
                scores = self.parse_gnina_output(output_sdf, f"logs/{pair_id}.log")
                results.append({
                    'status': 'success',
                    'receptor': row['receptor'],
                    'ligand': row['ligand'],
                    'site_id': row['site_id'],
                    'output_file': output_sdf,
                    'scores': scores,
                    'pair_id': pair_id,
                    'mode': 'score_only'
                })
                print(f"   ✅ Scored: {pair_id} ({len(scores)} poses)")
            else:
                results.append({
                    'status': 'error',
                    'receptor': row['receptor'],
                    'ligand': row['ligand'],
                    'site_id': row['site_id'],
                    'error': f"Output file not found: {output_sdf}",
                    'pair_id': pair_id,
                    'mode': 'score_only'
                })
                print(f"   ❌ No output file: {pair_id}")
        
        return results


def main():
    """Main function for testing docking engine"""
    print("🚀 HPC GNINA Docking Engine")
    print("=" * 50)
    
    # Initialize engine
    engine = HPCGNINAEngine(max_workers=4)
    
    print("✅ HPC GNINA Docking Engine initialized")
    print(f"   Max workers: {engine.max_workers}")
    print(f"   Resume capability: Enabled")
    
    print("\n🔧 Usage Examples:")
    print("   # Run batch docking")
    print("   results = engine.run_batch_docking('pairlist.csv')")
    print("   ")
    print("   # Run score-only mode")
    print("   results = engine.run_score_only('pairlist.csv')")


if __name__ == "__main__":
    main()
