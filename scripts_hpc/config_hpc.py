#!/usr/bin/env python3
"""
HPC-Optimized GNINA Configuration Module

This module provides simplified configuration for the GNINA docking pipeline
optimized for HPC environments with Apptainer/Singularity containers.

Minimal dependencies - only uses standard Python libraries.
References: https://github.com/gnina/gnina
"""

import os
import subprocess


class HPCGNINAConfig:
    """Simplified configuration class for GNINA docking parameters on HPC"""
    
    def __init__(self):
        # Check for CPU mode environment variable
        use_cpu_mode = os.environ.get('USE_CPU_MODE', '0') == '1'
        cpu_cores_env = os.environ.get('GNINA_CPU_CORES', None)
        
        # HPC-specific configuration
        self.hpc_config = {
            'use_apptainer': True,
            'apptainer_image': os.path.expandvars('$HOME/cuda12.3.2-cudnn9-runtime-ubuntu22.04.sif'),
            'gnina_binary': os.path.expandvars('$HOME/gnina'),
            'working_directory': os.path.expandvars('$HOME/gnina_test'),
            'use_gpu_flag': '--nv' if not use_cpu_mode else '',  # Apptainer GPU flag (empty for CPU)
        }
        
        # Base configuration optimized for HPC
        cpu_cores = int(cpu_cores_env) if cpu_cores_env else 4
        self.base_config = {
            'exhaustiveness': 32,           # Global search exhaustiveness
            'num_modes': 20,                # Maximum binding modes
            'seed': 42,                     # Random seed for reproducibility
            'cpu_cores': cpu_cores,         # CPU cores to use (from env or default)
            'timeout': 300,                 # Timeout in seconds
            'min_rmsd_filter': 1.0,         # RMSD filter for pose diversity
            'pose_sort_order': 'CNNscore',  # CNNscore (default), CNNaffinity, Energy
            'cnn_rotation': 0,              # CNN rotation evaluation
            'add_hydrogens': True,          # Auto-add hydrogens
            'strip_hydrogens': False,       # Remove polar hydrogens
            'use_gpu': not use_cpu_mode,    # GPU acceleration (disabled if CPU mode)
            'gpu_device': 0,                # GPU device ID
        }
        
        # CNN scoring modes as per GNINA documentation
        self.cnn_modes = {
            'none': {
                'description': 'No CNNs used - empirical scoring only',
                'speed': 'fastest',
                'accuracy': 'baseline',
                'use_case': 'Quick screening, baseline comparison'
            },
            'rescore': {
                'description': 'CNN used for reranking final poses (default)',
                'speed': 'fast',
                'accuracy': 'good',
                'use_case': 'Large library screening, first-pass ranking'
            },
            'refinement': {
                'description': 'CNN used to refine poses after Monte Carlo',
                'speed': 'medium (10x slower than rescore on GPU)',
                'accuracy': 'better',
                'use_case': 'Focused re-docking, pose refinement'
            },
            'all': {
                'description': 'CNN used throughout entire procedure',
                'speed': 'slowest (extremely intensive)',
                'accuracy': 'best',
                'use_case': 'Final validation, small high-value sets'
            }
        }
        
        # Current active configuration
        self.active_config = self.base_config.copy()
        self.active_config['cnn_scoring'] = 'rescore'  # Default mode
        
        # Detect GPU availability
        self._detect_gpu()
    
    def _detect_gpu(self):
        """Detect GPU availability for CUDA support on HPC"""
        try:
            gpu_info = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
            if gpu_info.returncode == 0:
                print("✅ GPU detected on HPC")
                self.base_config['use_gpu'] = True
                self.active_config['use_gpu'] = True
            else:
                print("⚠️ No GPU detected, using CPU")
                self.base_config['use_gpu'] = False
                self.active_config['use_gpu'] = False
        except:
            print("⚠️ GPU check failed, using CPU")
            self.base_config['use_gpu'] = False
            self.active_config['use_gpu'] = False
    
    def set_cnn_mode(self, mode):
        """Set CNN scoring mode"""
        if mode not in self.cnn_modes:
            raise ValueError(f"Invalid CNN mode: {mode}. Available: {list(self.cnn_modes.keys())}")
        
        self.active_config['cnn_scoring'] = mode
        print(f"✅ CNN scoring mode set to: {mode}")
        print(f"   Description: {self.cnn_modes[mode]['description']}")
        print(f"   Speed: {self.cnn_modes[mode]['speed']}")
        print(f"   Use case: {self.cnn_modes[mode]['use_case']}")
    
    def set_performance_params(self, exhaustiveness=None, num_modes=None, cpu_cores=None):
        """Set performance parameters"""
        if exhaustiveness is not None:
            self.active_config['exhaustiveness'] = exhaustiveness
        if num_modes is not None:
            self.active_config['num_modes'] = num_modes
        if cpu_cores is not None:
            self.active_config['cpu_cores'] = cpu_cores
        
        print("✅ Performance parameters updated:")
        print(f"   Exhaustiveness: {self.active_config['exhaustiveness']}")
        print(f"   Num modes: {self.active_config['num_modes']}")
        print(f"   CPU cores: {self.active_config['cpu_cores']}")
    
    def set_gpu_acceleration(self, use_gpu=True, gpu_device=0):
        """Configure GPU acceleration settings"""
        self.active_config['use_gpu'] = use_gpu
        self.active_config['gpu_device'] = gpu_device
        
        if use_gpu and self.base_config.get('use_gpu', False):
            print(f"✅ GPU acceleration enabled (device {gpu_device})")
        elif use_gpu and not self.base_config.get('use_gpu', False):
            print("⚠️ GPU requested but not available, will use CPU")
            self.active_config['use_gpu'] = False
        else:
            print("✅ CPU acceleration enabled")
    
    def get_gnina_command_base(self):
        """Get base GNINA command arguments with HPC and GPU prioritization"""
        cmd_args = [
            '--exhaustiveness', str(self.active_config['exhaustiveness']),
            '--num_modes', str(self.active_config['num_modes']),
            '--seed', str(self.active_config['seed']),
            '--cnn_scoring', self.active_config['cnn_scoring'],
            '--cnn_rotation', str(self.active_config['cnn_rotation']),
            '--min_rmsd_filter', str(self.active_config['min_rmsd_filter']),
            '--pose_sort_order', self.active_config['pose_sort_order'],
        ]
        
        # GPU acceleration (prioritized over CPU) - Use --device for newer GNINA versions
        if self.active_config.get('use_gpu', False) and self.base_config.get('use_gpu', False):
            cmd_args.extend(['--device', str(self.active_config.get('gpu_device', 0))])
            print(f"   🚀 Using GPU acceleration (device {self.active_config.get('gpu_device', 0)})")
        else:
            # Fallback to CPU
            cmd_args.extend(['--cpu', str(self.active_config['cpu_cores'])])
            print(f"   💻 Using CPU cores: {self.active_config['cpu_cores']}")
        
        # --addH requires an argument and is "on" by default
        # Only add it explicitly if we want to change from default
        if self.active_config['add_hydrogens']:
            cmd_args.extend(['--addH', 'on'])
        else:
            cmd_args.extend(['--addH', 'off'])
        
        # --stripH also requires an argument
        if self.active_config['strip_hydrogens']:
            cmd_args.extend(['--stripH', 'on'])
        else:
            cmd_args.extend(['--stripH', 'off'])
        
        return cmd_args
    
    def get_apptainer_command(self, gnina_args):
        """Get complete Apptainer command for HPC execution"""
        if not self.hpc_config['use_apptainer']:
            return gnina_args
        
        # Build Apptainer command
        apptainer_cmd = ['apptainer', 'exec']
        
        # Add GPU flag only if GPU is enabled and flag is not empty
        if self.hpc_config['use_gpu_flag']:
            apptainer_cmd.append(self.hpc_config['use_gpu_flag'])  # --nv for GPU
        
        apptainer_cmd.extend([
            self.hpc_config['apptainer_image'],
            self.hpc_config['gnina_binary']
        ])
        
        # Add GNINA arguments
        apptainer_cmd.extend(gnina_args)
        
        return apptainer_cmd
    
    def display_configuration(self):
        """Display current configuration"""
        print("🔧 Current GNINA Docking Configuration (HPC):")
        print(f"   HPC Environment: {'Apptainer' if self.hpc_config['use_apptainer'] else 'Native'}")
        if self.hpc_config['use_apptainer']:
            print(f"   Apptainer Image: {self.hpc_config['apptainer_image']}")
            print(f"   GNINA Binary: {self.hpc_config['gnina_binary']}")
        print(f"   CNN Scoring: {self.active_config['cnn_scoring']}")
        print(f"   Exhaustiveness: {self.active_config['exhaustiveness']}")
        print(f"   Num Modes: {self.active_config['num_modes']}")
        print(f"   Acceleration: {'GPU' if self.active_config.get('use_gpu', False) and self.base_config.get('use_gpu', False) else 'CPU'}")
        if self.active_config.get('use_gpu', False) and self.base_config.get('use_gpu', False):
            print(f"   GPU Device: {self.active_config.get('gpu_device', 0)}")
        else:
            print(f"   CPU Cores: {self.active_config['cpu_cores']}")
        print(f"   Seed: {self.active_config['seed']}")
        print(f"   Timeout: {self.active_config['timeout']}s")
        print(f"   RMSD Filter: {self.active_config['min_rmsd_filter']}Å")
        print(f"   Pose Sort: {self.active_config['pose_sort_order']} (0=CNNscore)")
    
    def display_cnn_modes(self):
        """Display available CNN modes"""
        print("🧠 Available CNN Scoring Modes:")
        for mode, info in self.cnn_modes.items():
            print(f"   {mode}: {info['description']}")
            print(f"      Speed: {info['speed']}")
            print(f"      Use case: {info['use_case']}")
            print()


def main():
    """Main function for testing configuration"""
    print("🚀 HPC GNINA Docking Configuration Module")
    print("=" * 50)
    
    # Initialize configuration
    config = HPCGNINAConfig()
    
    # Display available options
    config.display_cnn_modes()
    config.display_configuration()
    
    print("\n💡 Configuration Examples:")
    print("   # Set CNN mode")
    print("   config.set_cnn_mode('refinement')")
    print("   ")
    print("   # Set performance parameters")
    print("   config.set_performance_params(exhaustiveness=48, num_modes=20)")
    print("   ")
    print("   # Configure GPU acceleration (prioritized)")
    print("   config.set_gpu_acceleration(use_gpu=True, gpu_device=0)")


if __name__ == "__main__":
    main()

