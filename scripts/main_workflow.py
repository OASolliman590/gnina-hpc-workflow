#!/usr/bin/env python3
"""
Main Execution and Workflow Orchestration

This module provides easy-to-use functions for running different workflow types
and orchestrating the complete GNINA docking pipeline.

Based on the Enhanced GNINA Docking Pipeline notebook.

References:
- GNINA: https://github.com/gnina/gnina
- PDB Preparation Wizard: https://github.com/OASolliman590/pdb-prepare-wizard
"""

import os
import sys
import pandas as pd
import json
from datetime import datetime

# Add scripts directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import all modules
from config import GNINADockingConfig
from docking_engine import GNINADockingEngine
from tiered_workflow import TieredCNNWorkflow
from flexible_receptor import FlexibleReceptorManager
from covalent_docking import CovalentDockingConfig, CovalentDockingEngine
from analysis_tools import DockingAnalysisDashboard, QualityControlValidator


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
        df = pd.read_csv('pairlist.csv')
        
        # Normalize column names
        df.columns = df.columns.str.lower().str.replace(' ', '_')
        
        # Validate required columns
        required_cols = ['receptor', 'ligand', 'center_x', 'center_y', 'center_z', 
                        'size_x', 'size_y', 'size_z']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"❌ Missing required columns: {missing_cols}")
            return None
        
        # Validate numeric columns
        coord_cols = ['center_x', 'center_y', 'center_z', 'size_x', 'size_y', 'size_z']
        for col in coord_cols:
            if not pd.api.types.is_numeric_dtype(df[col]):
                print(f"❌ Column {col} must be numeric")
                return None
        
        # Add site_id if missing
        if 'site_id' not in df.columns:
            df['site_id'] = 'site_1'
            print("⚠️ Added default site_id column")
        
        print(f"✅ Pairlist loaded: {len(df)} entries")
        return df
        
    except Exception as e:
        print(f"❌ Error loading pairlist: {e}")
        return None


def run_standard_docking(pairlist_df, use_flexible=False, cnn_mode='rescore'):
    """
    Run standard GNINA docking workflow
    
    Args:
        pairlist_df: DataFrame with receptor-ligand pairs and coordinates
        use_flexible: Whether to use flexible receptor docking
        cnn_mode: CNN scoring mode ('none', 'rescore', 'refinement', 'all')
    """
    print(f"🚀 Starting Standard Docking Workflow")
    print(f"   Flexible receptors: {'Enabled' if use_flexible else 'Disabled'}")
    print(f"   CNN mode: {cnn_mode}")
    
    # Initialize components
    config = GNINADockingConfig()
    engine = GNINADockingEngine(config, max_workers=4)
    analysis_dashboard = DockingAnalysisDashboard()
    qc_validator = QualityControlValidator()
    
    # Configure CNN mode
    config.set_cnn_mode(cnn_mode)
    
    # Configure flexible receptors if requested
    flexible_residues_dict = None
    if use_flexible:
        flexible_manager = FlexibleReceptorManager()
        flexible_manager.set_bulk_flexibility(pairlist_df, auto_detect=True)
        flexible_residues_dict = flexible_manager.get_flexible_residues_dict()
        flexible_manager.display_flexibility_summary()
    
    # Run docking
    results = engine.run_parallel_docking(pairlist_df, flexible_residues_dict)
    
    # Generate analysis
    print("\n📊 Generating analysis...")
    analysis_dashboard.create_score_distribution_plot(results)
    qc_validator.validate_docking_results(results)
    qc_validator.generate_quality_report()
    
    # Save results
    save_workflow_results(results, 'standard_docking', {
        'use_flexible': use_flexible,
        'cnn_mode': cnn_mode,
        'config': config.active_config
    })
    
    return results


def run_tiered_workflow(pairlist_df, stages=['A', 'B'], use_flexible=False):
    """
    Run tiered CNN scoring workflow
    
    Args:
        pairlist_df: DataFrame with receptor-ligand pairs and coordinates
        stages: List of stages to run ['A', 'B', 'C']
        use_flexible: Whether to use flexible receptor docking
    """
    print(f"🎯 Starting Tiered CNN Workflow")
    print(f"   Stages: {stages}")
    print(f"   Flexible receptors: {'Enabled' if use_flexible else 'Disabled'}")
    
    # Initialize components
    config = GNINADockingConfig()
    engine = GNINADockingEngine(config, max_workers=4)
    workflow = TieredCNNWorkflow(config)
    analysis_dashboard = DockingAnalysisDashboard()
    qc_validator = QualityControlValidator()
    
    # Configure flexible receptors if requested
    flexible_residues_dict = None
    if use_flexible:
        flexible_manager = FlexibleReceptorManager()
        flexible_manager.set_bulk_flexibility(pairlist_df, auto_detect=True)
        flexible_residues_dict = flexible_manager.get_flexible_residues_dict()
    
    all_results = []
    previous_results = None
    
    for stage in stages:
        print(f"\n{'='*60}")
        print(f"STAGE {stage}: {workflow.get_stage_config(stage)['name']}")
        print(f"{'='*60}")
        
        # Get input for this stage
        stage_input = workflow.run_stage(stage, pairlist_df, previous_results)
        
        if len(stage_input) == 0:
            print(f"⚠️ No ligands to process for Stage {stage}")
            continue
        
        # Run docking for this stage
        stage_results = engine.run_parallel_docking(stage_input, flexible_residues_dict)
        
        # Add stage information
        for result in stage_results:
            result['stage'] = stage
            result['stage_config'] = workflow.get_stage_config(stage)
        
        all_results.extend(stage_results)
        previous_results = stage_results
        
        # Save stage results
        workflow.save_stage_results(stage, stage_results)
        
        # Stage summary
        successful = len([r for r in stage_results if r['status'] == 'success'])
        print(f"\n📊 Stage {stage} Summary:")
        print(f"   Processed: {len(stage_input)} pairs")
        print(f"   Successful: {successful}")
        print(f"   Success rate: {successful/len(stage_input)*100:.1f}%")
    
    # Final analysis
    print(f"\n{'='*60}")
    print("FINAL ANALYSIS")
    print(f"{'='*60}")
    
    analysis_dashboard.create_score_distribution_plot(all_results)
    qc_validator.validate_docking_results(all_results)
    qc_validator.generate_quality_report()
    
    # Analyze stage progression
    stage_results_dict = {stage: [r for r in all_results if r.get('stage') == stage] 
                         for stage in stages}
    workflow.analyze_stage_progression(stage_results_dict)
    
    # Save results
    save_workflow_results(all_results, 'tiered_workflow', {
        'stages': stages,
        'use_flexible': use_flexible,
        'config': config.active_config
    })
    
    return all_results


def run_covalent_docking(pairlist_df, covalent_residue, covalent_atom='SG', use_flexible=False):
    """
    Run covalent docking workflow
    
    Args:
        pairlist_df: DataFrame with receptor-ligand pairs and coordinates
        covalent_residue: Residue ID for covalent bond (e.g., 'A:123')
        covalent_atom: Atom name for covalent bond (e.g., 'SG' for cysteine)
        use_flexible: Whether to use flexible receptor docking
    """
    print(f"🔗 Starting Covalent Docking Workflow")
    print(f"   Covalent residue: {covalent_residue}:{covalent_atom}")
    print(f"   Flexible receptors: {'Enabled' if use_flexible else 'Disabled'}")
    
    # Initialize components
    config = GNINADockingConfig()
    covalent_config = CovalentDockingConfig(config)
    covalent_engine = CovalentDockingEngine(covalent_config, max_workers=4)
    analysis_dashboard = DockingAnalysisDashboard()
    qc_validator = QualityControlValidator()
    
    # Configure covalent parameters
    covalent_config.set_covalent_residue(covalent_residue, covalent_atom)
    covalent_config.display_covalent_configuration()
    
    # Run covalent docking
    results = covalent_engine.run_covalent_docking(pairlist_df, covalent_residue, covalent_atom)
    
    # Generate analysis
    print("\n📊 Generating covalent docking analysis...")
    analysis_dashboard.create_score_distribution_plot(results)
    qc_validator.validate_docking_results(results)
    qc_validator.generate_quality_report()
    
    # Save results
    covalent_engine.save_covalent_results(results)
    save_workflow_results(results, 'covalent_docking', {
        'covalent_residue': covalent_residue,
        'covalent_atom': covalent_atom,
        'use_flexible': use_flexible,
        'config': covalent_config.covalent_config
    })
    
    return results


def run_complete_workflow(pairlist_df, workflow_type='standard', **kwargs):
    """
    Run complete workflow with all options
    
    Args:
        pairlist_df: DataFrame with receptor-ligand pairs and coordinates
        workflow_type: 'standard', 'tiered', 'covalent'
        **kwargs: Additional parameters for specific workflows
    """
    print(f"🎯 Starting Complete GNINA Workflow: {workflow_type.upper()}")
    print(f"   Total pairs: {len(pairlist_df)}")
    
    # Validate project structure
    if not validate_project_structure():
        print("Please ensure all required files and directories are present")
        return None
    
    # Load and validate pairlist
    if pairlist_df is None:
        pairlist_df = load_and_validate_pairlist()
        if pairlist_df is None:
            return None
    
    # Check GPU availability
    config = GNINADockingConfig()
    print(f"   GPU acceleration: {'Enabled' if config.base_config.get('use_gpu', False) else 'Disabled'}")
    
    if workflow_type == 'standard':
        return run_standard_docking(
            pairlist_df, 
            use_flexible=kwargs.get('use_flexible', False),
            cnn_mode=kwargs.get('cnn_mode', 'rescore')
        )
    
    elif workflow_type == 'tiered':
        return run_tiered_workflow(
            pairlist_df,
            stages=kwargs.get('stages', ['A', 'B']),
            use_flexible=kwargs.get('use_flexible', False)
        )
    
    elif workflow_type == 'covalent':
        return run_covalent_docking(
            pairlist_df,
            covalent_residue=kwargs.get('covalent_residue', 'A:123'),
            covalent_atom=kwargs.get('covalent_atom', 'SG'),
            use_flexible=kwargs.get('use_flexible', False)
        )
    
    else:
        print(f"❌ Unknown workflow type: {workflow_type}")
        return None


def save_workflow_results(results, workflow_type, metadata):
    """Save workflow results to file"""
    results_data = {
        'timestamp': datetime.now().isoformat(),
        'workflow_type': workflow_type,
        'metadata': metadata,
        'results': results,
        'summary': {
            'total_pairs': len(results),
            'successful': len([r for r in results if r['status'] == 'success']),
            'failed': len([r for r in results if r['status'] != 'success'])
        }
    }
    
    filename = f"results/{workflow_type}_results.json"
    with open(filename, 'w') as f:
        json.dump(results_data, f, indent=2)
    
    print(f"✅ Workflow results saved to {filename}")


def load_workflow_results(workflow_type):
    """Load workflow results from file"""
    filename = f"results/{workflow_type}_results.json"
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            results_data = json.load(f)
        
        print(f"✅ Workflow results loaded from {filename}")
        return results_data['results']
    else:
        print(f"⚠️ Workflow results file not found: {filename}")
        return []


def main():
    """Main function for testing workflow orchestration"""
    print("🚀 Enhanced GNINA Docking Pipeline Ready!")
    print("=" * 60)
    
    # Validate project structure
    if not validate_project_structure():
        print("Please ensure all required files and directories are present")
        return
    
    # Load pairlist
    pairlist_df = load_and_validate_pairlist()
    if pairlist_df is None:
        return
    
    print("\n📋 Available Workflow Types:")
    print("   1. Standard Docking - Single-stage docking with configurable CNN mode")
    print("   2. Tiered Workflow - Multi-stage funnel approach (A → B → C)")
    print("   3. Covalent Docking - Specialized covalent bond formation")
    
    print("\n🔧 Quick Start Examples:")
    print("\n# Standard Docking (Recommended for most users)")
    print("results = run_complete_workflow(pairlist_df, 'standard', use_flexible=True)")
    print("")
    print("# Tiered Workflow (For large libraries)")
    print("results = run_complete_workflow(pairlist_df, 'tiered', stages=['A', 'B'], use_flexible=True)")
    print("")
    print("# Covalent Docking (For covalent inhibitors)")
    print("results = run_complete_workflow(pairlist_df, 'covalent', covalent_residue='A:123', covalent_atom='SG')")
    
    print("\n💡 Configuration Tips:")
    print("   • GPU acceleration is automatically prioritized over CPU (10-50x speedup)")
    print("   • Use flexible receptors for better accuracy (15-25% improvement)")
    print("   • Start with 'rescore' CNN mode for speed, use 'refinement' for accuracy")
    print("   • For large libraries (>1000 ligands): Use tiered workflow")
    print("   • For covalent inhibitors: Use covalent docking with appropriate reactive residue")
    print("   • CPU cores are used as fallback when GPU is unavailable")
    
    print("\n📊 Analysis and Visualization:")
    print("   • All workflows automatically generate comprehensive analysis")
    print("   • Interactive dashboards saved to visualizations/")
    print("   • Quality control reports saved to enhanced_analysis/")
    print("   • Resume capability: Interrupted runs can be resumed automatically")
    
    print("\n🔗 References:")
    print("   • GNINA: https://github.com/gnina/gnina")
    print("   • PDB Preparation Wizard: https://github.com/OASolliman590/pdb-prepare-wizard")
    print("   • CNN Scoring Modes: See GNINA documentation for detailed explanations")
    
    print("\n✅ Ready to run! Choose your workflow and execute the appropriate function above.")


if __name__ == "__main__":
    main()
