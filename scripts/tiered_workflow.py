#!/usr/bin/env python3
"""
Tiered CNN Scoring Workflow Implementation

This module implements the tiered CNN scoring approach as recommended in the GNINA documentation.
Creates a funnel workflow: broad screening → focused refinement → high-accuracy validation.

Based on the Enhanced GNINA Docking Pipeline notebook.

References:
- GNINA: https://github.com/gnina/gnina
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime


class TieredCNNWorkflow:
    """
    Tiered CNN scoring workflow as recommended by GNINA documentation:
    Stage A: Fast broad screening (rescore)
    Stage B: Focused refinement (refinement) 
    Stage C: High-accuracy validation (all)
    """
    
    def __init__(self, docking_config):
        self.config = docking_config
        self.stage_results = {}
        
        # Stage configurations based on GNINA best practices
        self.stages = {
            'A': {
                'name': 'Broad Screening',
                'cnn_scoring': 'rescore',
                'exhaustiveness': 12,
                'num_modes': 8,
                'description': 'Fast broad screening with CNN rescoring',
                'cnn_score_threshold': 0.5,
                'max_ligands_per_receptor': None,
                'top_percentage': None,
                'use_case': 'Large library screening, first-pass ranking'
            },
            'B': {
                'name': 'Focused Refinement', 
                'cnn_scoring': 'refinement',
                'exhaustiveness': 24,
                'num_modes': 15,
                'description': 'Balanced refinement with CNN pose optimization',
                'cnn_score_threshold': 0.7,
                'max_ligands_per_receptor': 5,
                'top_percentage': 0.05,
                'use_case': 'Focused re-docking, pose refinement'
            },
            'C': {
                'name': 'High-Accuracy Validation',
                'cnn_scoring': 'all', 
                'exhaustiveness': 48,
                'num_modes': 20,
                'description': 'High-accuracy final screening with full CNN',
                'cnn_score_threshold': 0.8,
                'max_ligands_per_receptor': 2,
                'top_percentage': 0.01,
                'use_case': 'Final validation, small high-value sets'
            }
        }
    
    def get_stage_config(self, stage):
        """Get configuration for a specific stage"""
        if stage not in self.stages:
            raise ValueError(f"Invalid stage: {stage}. Available: {list(self.stages.keys())}")
        return self.stages[stage]
    
    def filter_ligands_for_stage(self, stage, previous_results, pairlist_df):
        """Filter ligands based on previous stage results"""
        stage_config = self.get_stage_config(stage)
        
        if stage == 'A':
            # Stage A: Use all ligands
            return pairlist_df.copy()
        
        if not previous_results:
            print(f"⚠️ No previous results for stage {stage}, using all ligands")
            return pairlist_df.copy()
        
        # Extract successful results with scores
        successful_results = []
        for result in previous_results:
            if result['status'] == 'success' and 'scores' in result:
                for score_data in result['scores']:
                    if 'cnn_score' in score_data:
                        successful_results.append({
                            'receptor': result['receptor'],
                            'ligand': result['ligand'],
                            'site_id': result['site_id'],
                            'cnn_score': score_data['cnn_score']
                        })
        
        if not successful_results:
            print(f"⚠️ No successful results with scores for stage {stage}")
            return pairlist_df.copy()
        
        # Convert to DataFrame for filtering
        results_df = pd.DataFrame(successful_results)
        
        # Apply filtering criteria
        filtered_pairs = []
        
        for _, row in pairlist_df.iterrows():
            receptor = row['receptor']
            ligand = row['ligand']
            site_id = row['site_id']
            
            # Get scores for this receptor-ligand pair
            pair_scores = results_df[
                (results_df['receptor'] == receptor) & 
                (results_df['ligand'] == ligand) &
                (results_df['site_id'] == site_id)
            ]
            
            if len(pair_scores) == 0:
                continue
            
            # Check CNN score threshold
            max_cnn_score = pair_scores['cnn_score'].max()
            if max_cnn_score < stage_config['cnn_score_threshold']:
                continue
            
            # Check top percentage
            if stage_config['top_percentage'] is not None:
                # Get all scores for this receptor
                receptor_scores = results_df[results_df['receptor'] == receptor]['cnn_score']
                threshold_score = receptor_scores.quantile(1 - stage_config['top_percentage'])
                if max_cnn_score < threshold_score:
                    continue
            
            # Check max ligands per receptor
            if stage_config['max_ligands_per_receptor'] is not None:
                receptor_ligands = results_df[results_df['receptor'] == receptor]['ligand'].unique()
                if len(receptor_ligands) > stage_config['max_ligands_per_receptor']:
                    # Keep only top ligands for this receptor
                    top_ligands = results_df[results_df['receptor'] == receptor].groupby('ligand')['cnn_score'].max().nlargest(stage_config['max_ligands_per_receptor']).index
                    if ligand not in top_ligands:
                        continue
            
            filtered_pairs.append(row)
        
        filtered_df = pd.DataFrame(filtered_pairs)
        print(f"✅ Stage {stage} filtering: {len(filtered_df)}/{len(pairlist_df)} ligands selected")
        
        return filtered_df
    
    def run_stage(self, stage, pairlist_df, previous_results=None):
        """Run a specific stage of the tiered workflow"""
        stage_config = self.get_stage_config(stage)
        
        print(f"\n🚀 Starting Stage {stage}: {stage_config['name']}")
        print(f"   Description: {stage_config['description']}")
        print(f"   CNN Scoring: {stage_config['cnn_scoring']}")
        print(f"   Exhaustiveness: {stage_config['exhaustiveness']}")
        print(f"   Num Modes: {stage_config['num_modes']}")
        print(f"   Use Case: {stage_config['use_case']}")
        
        # Filter ligands for this stage
        input_df = self.filter_ligands_for_stage(stage, previous_results, pairlist_df)
        
        if len(input_df) == 0:
            print(f"   ⚠️ No ligands to process for Stage {stage}")
            return []
        
        print(f"   Processing {len(input_df)} ligand-receptor pairs")
        
        # Update docking configuration for this stage
        self.config.set_tiered_stage(f'stage_{stage.lower()}')
        
        # Return the filtered input for processing by the main docking engine
        return input_df
    
    def get_workflow_summary(self):
        """Get summary of the tiered workflow"""
        print("📊 Tiered CNN Scoring Workflow Summary:")
        print("\nStage A - Broad Screening:")
        print("   • CNN Scoring: rescore (fast)")
        print("   • Purpose: Large library screening, first-pass ranking")
        print("   • Threshold: CNN score ≥ 0.5")
        print("   • Expected: 80-95% of ligands")
        
        print("\nStage B - Focused Refinement:")
        print("   • CNN Scoring: refinement (10x slower than rescore)")
        print("   • Purpose: Pose refinement, focused re-docking")
        print("   • Threshold: CNN score ≥ 0.7, top 5% per receptor")
        print("   • Expected: 5-20% of ligands")
        
        print("\nStage C - High-Accuracy Validation:")
        print("   • CNN Scoring: all (extremely intensive)")
        print("   • Purpose: Final validation, small high-value sets")
        print("   • Threshold: CNN score ≥ 0.8, top 1% per receptor")
        print("   • Expected: 1-5% of ligands")
        
        print("\n💡 Recommended Usage:")
        print("   • For large libraries (>1000 ligands): Use stages A → B")
        print("   • For medium libraries (100-1000): Use stages A → B → C")
        print("   • For small libraries (<100): Use stage B or C directly")
    
    def save_stage_results(self, stage, results, filename=None):
        """Save stage results to file"""
        if filename is None:
            filename = f"results/stage_{stage}_results.json"
        
        stage_data = {
            'stage': stage,
            'stage_config': self.get_stage_config(stage),
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'summary': {
                'total_pairs': len(results),
                'successful': len([r for r in results if r['status'] == 'success']),
                'failed': len([r for r in results if r['status'] != 'success'])
            }
        }
        
        with open(filename, 'w') as f:
            import json
            json.dump(stage_data, f, indent=2)
        
        print(f"✅ Stage {stage} results saved to {filename}")
    
    def load_stage_results(self, stage, filename=None):
        """Load stage results from file"""
        if filename is None:
            filename = f"results/stage_{stage}_results.json"
        
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                import json
                stage_data = json.load(f)
            
            print(f"✅ Stage {stage} results loaded from {filename}")
            return stage_data['results']
        else:
            print(f"⚠️ Stage {stage} results file not found: {filename}")
            return []
    
    def analyze_stage_progression(self, all_stage_results):
        """Analyze progression through stages"""
        print("\n📊 Stage Progression Analysis:")
        
        for stage, results in all_stage_results.items():
            if not results:
                continue
                
            successful = [r for r in results if r['status'] == 'success']
            if successful:
                # Extract CNN scores
                all_scores = []
                for result in successful:
                    if 'scores' in result:
                        for score_data in result['scores']:
                            if 'cnn_score' in score_data:
                                all_scores.append(score_data['cnn_score'])
                
                if all_scores:
                    print(f"\nStage {stage}:")
                    print(f"   Processed: {len(results)} pairs")
                    print(f"   Successful: {len(successful)}")
                    print(f"   Success rate: {len(successful)/len(results)*100:.1f}%")
                    print(f"   CNN scores - Mean: {np.mean(all_scores):.3f}")
                    print(f"   CNN scores - Max: {np.max(all_scores):.3f}")
                    print(f"   CNN scores - Min: {np.min(all_scores):.3f}")
        
        # Overall progression
        total_processed = sum(len(results) for results in all_stage_results.values())
        total_successful = sum(len([r for r in results if r['status'] == 'success']) 
                             for results in all_stage_results.values())
        
        print(f"\nOverall Progression:")
        print(f"   Total processed: {total_processed}")
        print(f"   Total successful: {total_successful}")
        print(f"   Overall success rate: {total_successful/total_processed*100:.1f}%")


def main():
    """Main function for testing tiered workflow"""
    print("🚀 Tiered CNN Workflow Module")
    print("=" * 50)
    
    # Import config
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from config import GNINADockingConfig
    
    # Initialize configuration and workflow
    config = GNINADockingConfig()
    workflow = TieredCNNWorkflow(config)
    
    # Display workflow information
    workflow.get_workflow_summary()
    
    print("\n🔧 Usage Examples:")
    print("   # Run Stage A (broad screening)")
    print("   stage_a_input = workflow.run_stage('A', pairlist_df)")
    print("   ")
    print("   # Run Stage B (focused refinement)")
    print("   stage_b_input = workflow.run_stage('B', pairlist_df, stage_a_results)")
    print("   ")
    print("   # Run Stage C (high-accuracy validation)")
    print("   stage_c_input = workflow.run_stage('C', pairlist_df, stage_b_results)")
    print("   ")
    print("   # Save stage results")
    print("   workflow.save_stage_results('A', stage_a_results)")
    print("   ")
    print("   # Load stage results")
    print("   stage_a_results = workflow.load_stage_results('A')")
    print("   ")
    print("   # Analyze progression")
    print("   workflow.analyze_stage_progression({'A': stage_a_results, 'B': stage_b_results})")


if __name__ == "__main__":
    main()
