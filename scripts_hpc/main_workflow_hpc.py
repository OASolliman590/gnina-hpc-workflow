#!/usr/bin/env python3
"""
HPC-Optimized Main Workflow Orchestration

This module provides simplified workflow orchestration for the GNINA docking pipeline
optimized for HPC environments with minimal dependencies.

Minimal dependencies - only uses standard Python libraries.
References: https://github.com/gnina/gnina
"""

import os
import sys
import csv
import time
from datetime import datetime

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config_hpc import HPCGNINAConfig
from docking_engine_hpc import HPCGNINAEngine


def validate_project_structure():
    """Validate that required files and directories exist"""
    required_files = ['pairlist.csv']
    required_dirs = ['ligands', 'receptors']
    
    missing_files = [f for f in required_files if not os.path.exists(f)]
    missing_dirs = [d for d in required_dirs if not os.path.exists(d)]
    
    if missing_files or missing_dirs:
        print("❌ Missing required files/directories:")
        for item in missing_files + missing_dirs:
            print(f"   - {item}")
        return False
    
    print("✅ Project structure validated")
    return True


def load_and_validate_pairlist():
    """Load and validate pairlist.csv file"""
    try:
        # Load pairlist
        with open('pairlist.csv', 'r') as f:
            reader = csv.DictReader(f)
            pairs = list(reader)
        
        if not pairs:
            print("❌ No pairs found in pairlist.csv")
            return None
        
        # Validate required columns
        required_cols = ['receptor', 'ligand', 'center_x', 'center_y', 'center_z', 
                        'size_x', 'size_y', 'size_z']
        missing_cols = [col for col in required_cols if col not in pairs[0].keys()]
        
        if missing_cols:
            print(f"❌ Missing required columns: {missing_cols}")
            return None
        
        # Add site_id if missing
        for pair in pairs:
            if 'site_id' not in pair:
                pair['site_id'] = 'site_1'
        
        print(f"✅ Pairlist loaded: {len(pairs)} entries")
        return pairs
        
    except Exception as e:
        print(f"❌ Error loading pairlist: {e}")
        return None


def run_standard_docking(pairs=None, use_flexible=False, cnn_mode='rescore'):
    """
    Run standard GNINA docking workflow
    
    Args:
        pairs: List of receptor-ligand pairs (if None, loads from pairlist.csv)
        use_flexible: Whether to use flexible receptor docking (not implemented in HPC version)
        cnn_mode: CNN scoring mode ('none', 'rescore', 'refinement', 'all')
    """
    print(f"🚀 Starting Standard Docking Workflow")
    print(f"   Flexible receptors: {'Enabled' if use_flexible else 'Disabled (not supported in HPC version)'}")
    print(f"   CNN mode: {cnn_mode}")
    
    # Initialize components
    config = HPCGNINAConfig()
    engine = HPCGNINAEngine(max_workers=4)
    
    # Configure CNN mode
    config.set_cnn_mode(cnn_mode)
    
    # Load pairs if not provided
    if pairs is None:
        pairs = load_and_validate_pairlist()
        if pairs is None:
            return None
    
    # Run docking
    results = engine.run_batch_docking()
    
    # Generate simple analysis
    print("\n📊 Generating analysis...")
    generate_simple_analysis(results)
    
    return results


def run_score_only(pairs=None):
    """
    Run score-only mode for existing poses
    
    Args:
        pairs: List of receptor-ligand pairs (if None, loads from pairlist.csv)
    """
    print(f"🔍 Starting Score-Only Mode")
    
    # Initialize engine
    engine = HPCGNINAEngine(max_workers=4)
    
    # Load pairs if not provided
    if pairs is None:
        pairs = load_and_validate_pairlist()
        if pairs is None:
            return None
    
    # Run score-only
    results = engine.run_score_only()
    
    # Generate simple analysis
    print("\n📊 Generating analysis...")
    generate_simple_analysis(results)
    
    return results


def generate_simple_analysis(results):
    """Generate simple analysis of results"""
    if not results:
        print("⚠️ No results to analyze")
        return
    
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] != 'success']
    
    print(f"\n📊 Results Analysis:")
    print(f"   Total results: {len(results)}")
    print(f"   Successful: {len(successful)}")
    print(f"   Failed: {len(failed)}")
    print(f"   Success rate: {len(successful)/len(results)*100:.1f}%")
    
    if successful:
        # Extract CNN scores
        all_scores = []
        for result in successful:
            if 'scores' in result:
                for score_data in result['scores']:
                    if 'cnn_score' in score_data:
                        all_scores.append(score_data['cnn_score'])
        
        if all_scores:
            print(f"   CNN scores - Mean: {sum(all_scores)/len(all_scores):.3f}")
            print(f"   CNN scores - Min: {min(all_scores):.3f}")
            print(f"   CNN scores - Max: {max(all_scores):.3f}")
            
            # Top scoring pairs
            top_pairs = []
            for result in successful:
                if 'scores' in result:
                    max_score = max([s.get('cnn_score', 0) for s in result['scores']], default=0)
                    top_pairs.append((result['receptor'], result['ligand'], max_score))
            
            top_pairs.sort(key=lambda x: x[2], reverse=True)
            
            print(f"\n🏆 Top 5 Scoring Pairs:")
            for i, (receptor, ligand, score) in enumerate(top_pairs[:5], 1):
                print(f"   {i}. {receptor}-{ligand}: {score:.3f}")
    
    # Save analysis
    save_analysis_report(results, successful, failed)


def save_analysis_report(results, successful, failed):
    """Save analysis report to file"""
    try:
        with open('results/analysis_report.txt', 'w') as f:
            f.write(f"GNINA Docking Analysis Report\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Summary:\n")
            f.write(f"  Total results: {len(results)}\n")
            f.write(f"  Successful: {len(successful)}\n")
            f.write(f"  Failed: {len(failed)}\n")
            f.write(f"  Success rate: {len(successful)/len(results)*100:.1f}%\n\n")
            
            if successful:
                # Extract CNN scores
                all_scores = []
                for result in successful:
                    if 'scores' in result:
                        for score_data in result['scores']:
                            if 'cnn_score' in score_data:
                                all_scores.append(score_data['cnn_score'])
                
                if all_scores:
                    f.write(f"CNN Score Statistics:\n")
                    f.write(f"  Mean: {sum(all_scores)/len(all_scores):.3f}\n")
                    f.write(f"  Min: {min(all_scores):.3f}\n")
                    f.write(f"  Max: {max(all_scores):.3f}\n\n")
            
            f.write(f"Failed Pairs:\n")
            for result in failed:
                f.write(f"  {result['receptor']}-{result['ligand']}: {result['status']}\n")
                if 'error' in result:
                    f.write(f"    Error: {result['error']}\n")
        
        print("✅ Analysis report saved to results/analysis_report.txt")
    except Exception as e:
        print(f"⚠️ Error saving analysis report: {e}")


def run_complete_workflow(workflow_type='standard', **kwargs):
    """
    Run complete workflow with all options
    
    Args:
        workflow_type: 'standard', 'score-only'
        **kwargs: Additional parameters for specific workflows
    """
    print(f"🎯 Starting Complete GNINA Workflow: {workflow_type.upper()}")
    
    # Validate project structure
    if not validate_project_structure():
        print("Please ensure all required files and directories are present")
        return None
    
    # Load and validate pairlist
    pairs = load_and_validate_pairlist()
    if pairs is None:
        return None
    
    print(f"   Total pairs: {len(pairs)}")
    
    # Check GPU availability
    config = HPCGNINAConfig()
    print(f"   GPU acceleration: {'Enabled' if config.base_config.get('use_gpu', False) else 'Disabled'}")
    
    if workflow_type == 'standard':
        return run_standard_docking(
            pairs, 
            use_flexible=kwargs.get('use_flexible', False),
            cnn_mode=kwargs.get('cnn_mode', 'rescore')
        )
    
    elif workflow_type == 'score-only':
        return run_score_only(pairs)
    
    else:
        print(f"❌ Unknown workflow type: {workflow_type}")
        print("Available types: 'standard', 'score-only'")
        return None


def main():
    """Main function for testing workflow orchestration"""
    print("🚀 HPC GNINA Docking Pipeline Ready!")
    print("=" * 60)
    
    # Validate project structure
    if not validate_project_structure():
        print("Please ensure all required files and directories are present")
        return
    
    # Load pairlist
    pairs = load_and_validate_pairlist()
    if pairs is None:
        return
    
    print("\n📋 Available Workflow Types:")
    print("   1. Standard Docking - Single-stage docking with configurable CNN mode")
    print("   2. Score-Only Mode - Score existing poses")
    
    print("\n🔧 Quick Start Examples:")
    print("\n# Standard Docking (Recommended for most users)")
    print("results = run_complete_workflow('standard', cnn_mode='rescore')")
    print("")
    print("# Score-Only Mode (For existing poses)")
    print("results = run_complete_workflow('score-only')")
    
    print("\n💡 Configuration Tips:")
    print("   • GPU acceleration is automatically prioritized over CPU (10-50x speedup)")
    print("   • Start with 'rescore' CNN mode for speed, use 'refinement' for accuracy")
    print("   • CPU cores are used as fallback when GPU is unavailable")
    print("   • Resume capability: Interrupted runs can be resumed automatically")
    
    print("\n🔗 References:")
    print("   • GNINA: https://github.com/gnina/gnina")
    print("   • CNN Scoring Modes: See GNINA documentation for detailed explanations")
    
    print("\n✅ Ready to run! Choose your workflow and execute the appropriate function above.")


if __name__ == "__main__":
    # If a workflow type is provided, run it; otherwise show the interactive banner
    if len(sys.argv) > 1:
        workflow = sys.argv[1]
        run_complete_workflow(workflow)
    else:
        main()
