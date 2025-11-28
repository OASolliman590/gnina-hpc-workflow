#!/usr/bin/env python3
"""
Example Usage of Enhanced GNINA Docking Pipeline

This script demonstrates how to use the various components of the pipeline.
"""

import sys
import os
import pandas as pd

# Add scripts directory to path
sys.path.append('scripts')

# Import all modules
from config import GNINADockingConfig
from docking_engine import GNINADockingEngine
from tiered_workflow import TieredCNNWorkflow
from flexible_receptor import FlexibleReceptorManager
from covalent_docking import CovalentDockingConfig, CovalentDockingEngine
from analysis_tools import DockingAnalysisDashboard, QualityControlValidator
from main_workflow import run_complete_workflow, load_and_validate_pairlist


def example_standard_docking():
    """Example of standard docking workflow"""
    print("=" * 60)
    print("EXAMPLE: Standard Docking Workflow")
    print("=" * 60)
    
    # Load pairlist
    pairlist_df = load_and_validate_pairlist()
    if pairlist_df is None:
        print("❌ Failed to load pairlist. Please check pairlist.csv")
        return
    
    # Run standard docking
    results = run_complete_workflow(
        pairlist_df, 
        'standard', 
        use_flexible=True, 
        cnn_mode='rescore'
    )
    
    print(f"✅ Standard docking completed with {len(results)} results")


def example_tiered_workflow():
    """Example of tiered workflow"""
    print("=" * 60)
    print("EXAMPLE: Tiered Workflow")
    print("=" * 60)
    
    # Load pairlist
    pairlist_df = load_and_validate_pairlist()
    if pairlist_df is None:
        print("❌ Failed to load pairlist. Please check pairlist.csv")
        return
    
    # Run tiered workflow
    results = run_complete_workflow(
        pairlist_df, 
        'tiered', 
        stages=['A', 'B'], 
        use_flexible=True
    )
    
    print(f"✅ Tiered workflow completed with {len(results)} results")


def example_covalent_docking():
    """Example of covalent docking"""
    print("=" * 60)
    print("EXAMPLE: Covalent Docking")
    print("=" * 60)
    
    # Load pairlist
    pairlist_df = load_and_validate_pairlist()
    if pairlist_df is None:
        print("❌ Failed to load pairlist. Please check pairlist.csv")
        return
    
    # Run covalent docking
    results = run_complete_workflow(
        pairlist_df, 
        'covalent', 
        covalent_residue='A:123', 
        covalent_atom='SG',
        use_flexible=True
    )
    
    print(f"✅ Covalent docking completed with {len(results)} results")


def example_individual_components():
    """Example of using individual components"""
    print("=" * 60)
    print("EXAMPLE: Individual Components")
    print("=" * 60)
    
    # 1. Configuration
    print("\n1. Configuration Setup:")
    config = GNINADockingConfig()
    config.set_cnn_mode('refinement')
    config.set_performance_params(exhaustiveness=48, num_modes=20)
    config.display_configuration()
    
    # 2. Flexible Receptor Management
    print("\n2. Flexible Receptor Management:")
    flexible_manager = FlexibleReceptorManager()
    flexible_manager.set_flexibility_parameters(distance_threshold=5.0, max_residues=15)
    flexible_manager.get_flexibility_statistics()
    
    # 3. Docking Engine
    print("\n3. Docking Engine:")
    engine = GNINADockingEngine(config, max_workers=4)
    print(f"   Engine initialized with {engine.max_workers} workers")
    
    # 4. Analysis Tools
    print("\n4. Analysis Tools:")
    dashboard = DockingAnalysisDashboard()
    qc_validator = QualityControlValidator()
    print("   Analysis tools initialized")


def example_custom_workflow():
    """Example of custom workflow"""
    print("=" * 60)
    print("EXAMPLE: Custom Workflow")
    print("=" * 60)
    
    # Load pairlist
    pairlist_df = load_and_validate_pairlist()
    if pairlist_df is None:
        print("❌ Failed to load pairlist. Please check pairlist.csv")
        return
    
    # Custom configuration
    config = GNINADockingConfig()
    config.set_cnn_mode('refinement')
    config.set_performance_params(exhaustiveness=64, num_modes=30)
    config.set_gpu_acceleration(use_gpu=True, gpu_device=0)
    
    # Custom flexible receptor setup
    flexible_manager = FlexibleReceptorManager()
    flexible_manager.set_bulk_flexibility(pairlist_df, auto_detect=True)
    flexible_residues_dict = flexible_manager.get_flexible_residues_dict()
    
    # Custom docking engine
    engine = GNINADockingEngine(config, max_workers=8)
    
    # Run custom docking
    print("Running custom docking workflow...")
    results = engine.run_parallel_docking(pairlist_df, flexible_residues_dict)
    
    # Custom analysis
    dashboard = DockingAnalysisDashboard()
    qc_validator = QualityControlValidator()
    
    dashboard.create_score_distribution_plot(results)
    qc_validator.validate_docking_results(results)
    qc_validator.generate_quality_report()
    
    print(f"✅ Custom workflow completed with {len(results)} results")


def main():
    """Main function to run examples"""
    print("🚀 Enhanced GNINA Docking Pipeline - Examples")
    print("=" * 60)
    
    # Check if required files exist
    if not os.path.exists('pairlist.csv'):
        print("❌ pairlist.csv not found. Please create this file first.")
        print("   See README.md for the required format.")
        return
    
    if not os.path.exists('ligands') or not os.path.exists('receptors'):
        print("❌ ligands/ or receptors/ directories not found.")
        print("   Please create these directories and add your PDBQT files.")
        return
    
    print("✅ Required files and directories found.")
    print("\nChoose an example to run:")
    print("1. Standard Docking Workflow")
    print("2. Tiered Workflow")
    print("3. Covalent Docking")
    print("4. Individual Components")
    print("5. Custom Workflow")
    print("6. Run All Examples")
    
    choice = input("\nEnter your choice (1-6): ").strip()
    
    if choice == '1':
        example_standard_docking()
    elif choice == '2':
        example_tiered_workflow()
    elif choice == '3':
        example_covalent_docking()
    elif choice == '4':
        example_individual_components()
    elif choice == '5':
        example_custom_workflow()
    elif choice == '6':
        example_standard_docking()
        example_tiered_workflow()
        example_covalent_docking()
        example_individual_components()
        example_custom_workflow()
    else:
        print("❌ Invalid choice. Please run the script again.")
    
    print("\n✅ Examples completed!")
    print("Check the results/, visualizations/, and enhanced_analysis/ directories for outputs.")


if __name__ == "__main__":
    main()
