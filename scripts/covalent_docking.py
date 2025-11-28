#!/usr/bin/env python3
"""
Covalent Docking Configuration

This module provides specialized configuration for covalent docking using GNINA.
Follows the same procedure as standard docking but with covalent bond formation parameters.

Based on the Enhanced GNINA Docking Pipeline notebook.

References:
- GNINA: https://github.com/gnina/gnina
"""

import os
import sys
import subprocess
import json
from datetime import datetime


class CovalentDockingConfig:
    """Configuration for covalent docking with GNINA"""
    
    def __init__(self, base_docking_config):
        self.base_config = base_docking_config
        self.covalent_config = {
            'covalent_docking': True,
            'covalent_residue': None,  # e.g., 'A:123'
            'covalent_atom': None,     # e.g., 'SG' for cysteine
            'covalent_bond_type': 'single',  # single, double, triple
            'covalent_bond_length': 1.8,     # Angstroms
            'covalent_bond_angle': 109.5,    # Degrees
            'covalent_torsion': 0.0,         # Degrees
            'covalent_energy_penalty': 0.0,  # Energy penalty for covalent bond
        }
        
        # Covalent-specific parameters
        self.covalent_parameters = {
            'exhaustiveness': 64,      # Higher for covalent docking
            'num_modes': 30,          # More modes for covalent poses
            'cnn_scoring': 'refinement',  # Use refinement for better accuracy
            'min_rmsd_filter': 0.5,   # Stricter RMSD filter
            'pose_sort_order': 0,     # Sort by CNN score
        }
    
    def set_covalent_residue(self, residue_id, atom_name='SG'):
        """Set the covalent residue and atom"""
        self.covalent_config['covalent_residue'] = residue_id
        self.covalent_config['covalent_atom'] = atom_name
        print(f"✅ Covalent residue set: {residue_id}:{atom_name}")
    
    def set_covalent_bond_parameters(self, bond_length=1.8, bond_angle=109.5, torsion=0.0):
        """Set covalent bond geometry parameters"""
        self.covalent_config['covalent_bond_length'] = bond_length
        self.covalent_config['covalent_bond_angle'] = bond_angle
        self.covalent_config['covalent_torsion'] = torsion
        print(f"✅ Covalent bond parameters set:")
        print(f"   Bond length: {bond_length} Å")
        print(f"   Bond angle: {bond_angle}°")
        print(f"   Torsion: {torsion}°")
    
    def get_covalent_gnina_command(self, row):
        """Get GNINA command with covalent docking parameters"""
        receptor = f"receptors/{row['receptor']}.pdbqt"
        ligand = f"ligands/{row['ligand']}.pdbqt"
        
        # Output files
        tag = f"{row['receptor']}_{row['site_id']}_{row['ligand']}_covalent"
        output_sdf = f"gnina_out/{tag}_poses.sdf"
        log_file = f"logs/{tag}.log"
        
        # Base command
        cmd = [
            './gnina',
            "--receptor", receptor,
            "--ligand", ligand,
            "--out", output_sdf,
            "--log", log_file,
        ]
        
        # Docking box parameters
        cmd.extend([
            "--center_x", str(row['center_x']),
            "--center_y", str(row['center_y']),
            "--center_z", str(row['center_z']),
            "--size_x", str(row['size_x']),
            "--size_y", str(row['size_y']),
            "--size_z", str(row['size_z']),
        ])
        
        # Covalent-specific parameters
        cmd.extend([
            "--exhaustiveness", str(self.covalent_parameters['exhaustiveness']),
            "--num_modes", str(self.covalent_parameters['num_modes']),
            "--seed", str(self.base_config.active_config['seed']),
            "--cnn_scoring", self.covalent_parameters['cnn_scoring'],
            "--min_rmsd_filter", str(self.covalent_parameters['min_rmsd_filter']),
            "--pose_sort_order", str(self.covalent_parameters['pose_sort_order']),
        ])
        
        # GPU acceleration (prioritized over CPU)
        if self.base_config.active_config.get('use_gpu', False) and self.base_config.base_config.get('use_gpu', False):
            cmd.extend(['--gpu', '--device', str(self.base_config.active_config.get('gpu_device', 0))])
        else:
            # Fallback to CPU
            cmd.extend(['--cpu', str(self.base_config.active_config['cpu_cores'])])
        
        # Covalent docking parameters
        if self.covalent_config['covalent_residue']:
            cmd.extend([
                "--covalent_residue", self.covalent_config['covalent_residue'],
                "--covalent_atom", self.covalent_config['covalent_atom'],
                "--covalent_bond_length", str(self.covalent_config['covalent_bond_length']),
                "--covalent_bond_angle", str(self.covalent_config['covalent_bond_angle']),
                "--covalent_torsion", str(self.covalent_config['covalent_torsion']),
            ])
        
        return cmd, output_sdf, log_file
    
    def display_covalent_configuration(self):
        """Display current covalent docking configuration"""
        print("🔗 Covalent Docking Configuration:")
        print(f"   Covalent residue: {self.covalent_config['covalent_residue']}")
        print(f"   Covalent atom: {self.covalent_config['covalent_atom']}")
        print(f"   Bond length: {self.covalent_config['covalent_bond_length']} Å")
        print(f"   Bond angle: {self.covalent_config['covalent_bond_angle']}°")
        print(f"   Torsion: {self.covalent_config['covalent_torsion']}°")
        print(f"   Exhaustiveness: {self.covalent_parameters['exhaustiveness']}")
        print(f"   Num modes: {self.covalent_parameters['num_modes']}")
        print(f"   CNN scoring: {self.covalent_parameters['cnn_scoring']}")
    
    def save_covalent_config(self, filename='results/covalent_config.json'):
        """Save covalent docking configuration to file"""
        config_data = {
            'timestamp': datetime.now().isoformat(),
            'covalent_config': self.covalent_config,
            'covalent_parameters': self.covalent_parameters
        }
        
        with open(filename, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        print(f"✅ Covalent docking configuration saved to {filename}")
    
    def load_covalent_config(self, filename='results/covalent_config.json'):
        """Load covalent docking configuration from file"""
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                config_data = json.load(f)
            
            self.covalent_config = config_data.get('covalent_config', self.covalent_config)
            self.covalent_parameters = config_data.get('covalent_parameters', self.covalent_parameters)
            
            print(f"✅ Covalent docking configuration loaded from {filename}")
            return True
        else:
            print(f"⚠️ Covalent docking configuration file not found: {filename}")
            return False


class CovalentDockingEngine:
    """Covalent docking engine extending the base docking engine"""
    
    def __init__(self, covalent_config, max_workers=4):
        self.covalent_config = covalent_config
        self.max_workers = max_workers
        self.gnina_binary = './gnina'
        
        # Ensure output directories exist
        os.makedirs('gnina_out', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        os.makedirs('results', exist_ok=True)
    
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
    
    def run_covalent_docking(self, pairlist_df, covalent_residue, covalent_atom='SG'):
        """Run covalent docking for all pairs"""
        print(f"🔗 Starting covalent docking with residue {covalent_residue}:{covalent_atom}")
        
        # Set covalent parameters
        self.covalent_config.set_covalent_residue(covalent_residue, covalent_atom)
        
        # Display configuration
        self.covalent_config.display_covalent_configuration()
        
        # Run docking with covalent parameters
        results = []
        for idx, row in pairlist_df.iterrows():
            print(f"\n🔗 Processing covalent docking: {row['receptor']}-{row['ligand']}")
            
            # Build covalent command
            cmd, output_sdf, log_file = self.covalent_config.get_covalent_gnina_command(row)
            
            try:
                # Run GNINA with covalent parameters
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.covalent_config.base_config.active_config['timeout']
                )
                
                # Parse results
                if result.returncode == 0 and os.path.exists(output_sdf):
                    scores = self.parse_gnina_output(output_sdf, log_file)
                    results.append({
                        'status': 'success',
                        'receptor': row['receptor'],
                        'ligand': row['ligand'],
                        'site_id': row['site_id'],
                        'output_file': output_sdf,
                        'log_file': log_file,
                        'scores': scores,
                        'covalent_residue': covalent_residue,
                        'covalent_atom': covalent_atom,
                        'docking_type': 'covalent'
                    })
                    print(f"   ✅ Success: {len(scores)} poses generated")
                else:
                    results.append({
                        'status': 'error',
                        'receptor': row['receptor'],
                        'ligand': row['ligand'],
                        'site_id': row['site_id'],
                        'error': result.stderr,
                        'returncode': result.returncode,
                        'docking_type': 'covalent'
                    })
                    print(f"   ❌ Error: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                results.append({
                    'status': 'timeout',
                    'receptor': row['receptor'],
                    'ligand': row['ligand'],
                    'site_id': row['site_id'],
                    'error': f"Timeout after {self.covalent_config.base_config.active_config['timeout']}s",
                    'docking_type': 'covalent'
                })
                print(f"   ⏰ Timeout")
            except Exception as e:
                results.append({
                    'status': 'error',
                    'receptor': row['receptor'],
                    'ligand': row['ligand'],
                    'site_id': row['site_id'],
                    'error': str(e),
                    'docking_type': 'covalent'
                })
                print(f"   ❌ Exception: {e}")
        
        # Summary
        successful = len([r for r in results if r['status'] == 'success'])
        print(f"\n📊 Covalent Docking Summary:")
        print(f"   Total pairs: {len(pairlist_df)}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {len(pairlist_df) - successful}")
        print(f"   Success rate: {successful/len(pairlist_df)*100:.1f}%")
        
        return results
    
    def save_covalent_results(self, results, filename='results/covalent_docking_results.json'):
        """Save covalent docking results to file"""
        results_data = {
            'timestamp': datetime.now().isoformat(),
            'docking_type': 'covalent',
            'covalent_config': self.covalent_config.covalent_config,
            'results': results,
            'summary': {
                'total_pairs': len(results),
                'successful': len([r for r in results if r['status'] == 'success']),
                'failed': len([r for r in results if r['status'] != 'success'])
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"✅ Covalent docking results saved to {filename}")
    
    def load_covalent_results(self, filename='results/covalent_docking_results.json'):
        """Load covalent docking results from file"""
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                results_data = json.load(f)
            
            print(f"✅ Covalent docking results loaded from {filename}")
            return results_data['results']
        else:
            print(f"⚠️ Covalent docking results file not found: {filename}")
            return []


def main():
    """Main function for testing covalent docking"""
    print("🚀 Covalent Docking Module")
    print("=" * 50)
    
    # Import config
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from config import GNINADockingConfig
    
    # Initialize configuration and engine
    config = GNINADockingConfig()
    covalent_config = CovalentDockingConfig(config)
    covalent_engine = CovalentDockingEngine(covalent_config, max_workers=4)
    
    print("✅ Covalent Docking Engine initialized")
    
    print("\n🔧 Usage Examples:")
    print("   # Set covalent residue (e.g., cysteine at position 123 in chain A)")
    print("   covalent_config.set_covalent_residue('A:123', 'SG')")
    print("   ")
    print("   # Set covalent bond parameters")
    print("   covalent_config.set_covalent_bond_parameters(bond_length=1.8, bond_angle=109.5)")
    print("   ")
    print("   # Run covalent docking")
    print("   covalent_results = covalent_engine.run_covalent_docking(pairlist_df, 'A:123', 'SG')")
    print("   ")
    print("   # Display configuration")
    print("   covalent_config.display_covalent_configuration()")
    print("   ")
    print("   # Save results")
    print("   covalent_engine.save_covalent_results(covalent_results)")
    
    print("\n💡 Covalent Docking Notes:")
    print("   • Requires reactive groups in ligands (e.g., Michael acceptors, electrophiles)")
    print("   • Target residue must have reactive atom (e.g., Cys-SG, Lys-NZ, Ser-OG)")
    print("   • Higher exhaustiveness recommended for better sampling")
    print("   • Use refinement CNN scoring for better accuracy")
    print("   • Consider flexible receptor for better pose quality")
    print("   • Common reactive residues: Cys (SG), Lys (NZ), Ser (OG), Thr (OG1)")
    print("   • Common reactive groups: Michael acceptors, aldehydes, epoxides")


if __name__ == "__main__":
    main()
