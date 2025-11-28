#!/usr/bin/env python3
"""
Core GNINA Docking Engine with Parallel Processing and Resume Capability

This module provides the main docking engine for executing GNINA docking operations
with integrated parallel processing and resume functionality.

Based on the Enhanced GNINA Docking Pipeline notebook.

References:
- GNINA: https://github.com/gnina/gnina
"""

import os
import sys
import subprocess
import json
import threading
import concurrent.futures
from datetime import datetime
from tqdm import tqdm
import pandas as pd
import numpy as np


class GNINADockingEngine:
    """
    Core GNINA docking engine with integrated parallel processing and resume capability.
    This is the main component that executes all docking operations.
    """
    
    def __init__(self, docking_config, max_workers=4):
        self.config = docking_config
        self.max_workers = max_workers
        self.gnina_binary = './gnina'
        self.results = []
        self.failures = []
        self.progress_lock = threading.Lock()
        
        # Resume capability
        self.resume_file = "docking_state.json"
        self.state_file = f"results/{self.resume_file}"
        
        # Progress tracking
        self.completed_pairs = set()
        self.total_pairs = 0
        
        # Ensure output directories exist
        os.makedirs('gnina_out', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        os.makedirs('results', exist_ok=True)
    
    def build_gnina_command(self, row, flexible_residues=None):
        """Build GNINA command for a single docking run on HPC"""
        receptor = f"receptors/{row['receptor']}.pdbqt"
        ligand = f"ligands/{row['ligand']}.pdbqt"
        
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
        
        # Flexible receptor parameters
        if flexible_residues:
            flexres_str = ",".join(flexible_residues)
            flex_output = f"gnina_out/{tag}_flex.pdbqt"
            gnina_args.extend([
                "--flexres", flexres_str,
                "--flexdist", "3.5",
                "--out_flex", flex_output
            ])
        
        # Build complete Apptainer command
        cmd = self.config.get_apptainer_command(gnina_args)
        
        return cmd, output_sdf, log_file
    
    def run_single_docking(self, row, flexible_residues=None):
        """Run docking for a single ligand-receptor pair"""
        try:
            # Check if already completed (resume capability)
            pair_id = f"{row['receptor']}_{row['site_id']}_{row['ligand']}"
            if pair_id in self.completed_pairs:
                print(f"   ⏭️ Skipping already completed: {pair_id}")
                return None
            
            # Build command
            cmd, output_sdf, log_file = self.build_gnina_command(row, flexible_residues)
            
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
    
    def run_parallel_docking(self, pairlist_df, flexible_residues_dict=None, batch_size=5):
        """Run docking with parallel processing"""
        self.total_pairs = len(pairlist_df)
        print(f"🚀 Starting parallel docking: {self.total_pairs} pairs")
        print(f"   Max workers: {self.max_workers}")
        print(f"   Batch size: {batch_size}")
        
        # Load completed pairs for resume capability
        self.load_completed_pairs()
        
        # Split into batches
        batches = [pairlist_df.iloc[i:i+batch_size] for i in range(0, self.total_pairs, batch_size)]
        
        all_results = []
        successful = 0
        failed = 0
        
        # Process batches in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all batches
            future_to_batch = {
                executor.submit(self._process_batch, batch, batch_idx, flexible_residues_dict): batch_idx 
                for batch_idx, batch in enumerate(batches)
            }
            
            # Collect results as they complete
            for future in tqdm(concurrent.futures.as_completed(future_to_batch), 
                             total=len(batches), desc="Processing batches"):
                batch_idx = future_to_batch[future]
                try:
                    batch_results = future.result()
                    all_results.extend(batch_results)
                    
                    # Count successes/failures
                    for result in batch_results:
                        if result and result['status'] == 'success':
                            successful += 1
                            self.completed_pairs.add(result['pair_id'])
                        elif result:
                            failed += 1
                    
                    # Save progress
                    self.save_docking_state(all_results)
                            
                except Exception as e:
                    print(f"❌ Batch {batch_idx} failed: {e}")
                    failed += len(batches[batch_idx])
        
        # Final summary
        print(f"\n📊 Parallel Docking Summary:")
        print(f"   Total pairs: {self.total_pairs}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {failed}")
        print(f"   Success rate: {successful/self.total_pairs*100:.1f}%")
        
        self.results = all_results
        return all_results
    
    def _process_batch(self, batch_df, batch_idx, flexible_residues_dict):
        """Process a single batch of docking runs"""
        batch_results = []
        
        for idx, row in batch_df.iterrows():
            # Get flexible residues for this receptor
            flexible_residues = None
            if flexible_residues_dict and row['receptor'] in flexible_residues_dict:
                flexible_residues = flexible_residues_dict[row['receptor']]
            
            result = self.run_single_docking(row, flexible_residues)
            if result:
                result['batch_idx'] = batch_idx
                batch_results.append(result)
                
                # Update progress
                with self.progress_lock:
                    status = "✅" if result['status'] == 'success' else "❌"
                    flex_info = " (Flex)" if flexible_residues else ""
                    print(f"   {status} Batch {batch_idx}: {row['receptor']}-{row['ligand']}{flex_info}")
        
        return batch_results
    
    def save_docking_state(self, results):
        """Save docking state for resume capability"""
        state = {
            'timestamp': datetime.now().isoformat(),
            'total_pairs': self.total_pairs,
            'completed_pairs': list(self.completed_pairs),
            'results_count': len(results),
            'config': self.config.active_config
        }
        
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_docking_state(self):
        """Load docking state for resume capability"""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            self.completed_pairs = set(state.get('completed_pairs', []))
            self.total_pairs = state.get('total_pairs', 0)
            
            print(f"✅ Loaded docking state: {len(self.completed_pairs)} completed pairs")
            return True
        return False
    
    def load_completed_pairs(self):
        """Load list of completed pairs from output files"""
        if os.path.exists('gnina_out'):
            for file in os.listdir('gnina_out'):
                if file.endswith('_poses.sdf'):
                    # Extract pair ID from filename
                    pair_id = file.replace('_poses.sdf', '')
                    self.completed_pairs.add(pair_id)
        
        print(f"✅ Found {len(self.completed_pairs)} previously completed pairs")
    
    def run_score_only(self, pairlist_df):
        """Run score-only mode for existing poses"""
        print("🔍 Running score-only mode...")
        
        results = []
        for idx, row in pairlist_df.iterrows():
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
    print("🚀 GNINA Docking Engine Module")
    print("=" * 50)
    
    # Import config
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from config import GNINADockingConfig
    
    # Initialize configuration and engine
    config = GNINADockingConfig()
    engine = GNINADockingEngine(config, max_workers=4)
    
    print("✅ Core GNINA Docking Engine initialized")
    print(f"   Max workers: {engine.max_workers}")
    print(f"   Resume capability: Enabled")
    print(f"   State file: {engine.state_file}")
    
    print("\n🔧 Usage Examples:")
    print("   # Run parallel docking")
    print("   results = engine.run_parallel_docking(pairlist_df)")
    print("   ")
    print("   # Run with flexible residues")
    print("   flex_dict = {'receptor1': ['A:123', 'A:124']}")
    print("   results = engine.run_parallel_docking(pairlist_df, flex_dict)")
    print("   ")
    print("   # Load previous state")
    print("   engine.load_docking_state()")
    print("   ")
    print("   # Run score-only mode")
    print("   results = engine.run_score_only(pairlist_df)")


if __name__ == "__main__":
    main()
