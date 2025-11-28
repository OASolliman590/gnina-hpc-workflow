#!/usr/bin/env python3
"""
Post-Docking Analysis: Visualization and Quality Control

This module provides comprehensive analysis tools for docking results including
visualization dashboards and quality control validation.

Based on the Enhanced GNINA Docking Pipeline notebook.
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

# Try to import plotly for interactive visualizations
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import plotly.offline as pyo
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("⚠️ Plotly not available. Interactive visualizations will be disabled.")


class DockingAnalysisDashboard:
    """Comprehensive analysis dashboard for docking results"""
    
    def __init__(self):
        self.setup_plotting_style()
        
        # Ensure output directories exist
        os.makedirs('visualizations', exist_ok=True)
        os.makedirs('enhanced_analysis', exist_ok=True)
    
    def setup_plotting_style(self):
        """Setup plotting style for visualizations"""
        plt.style.use('default')
        sns.set_palette("husl")
    
    def create_score_distribution_plot(self, results):
        """Create score distribution visualization"""
        successful_results = [r for r in results if r['status'] == 'success']
        
        if not successful_results:
            print("⚠️ No successful results to visualize")
            return
        
        # Extract all CNN scores
        all_scores = []
        for result in successful_results:
            if 'scores' in result:
                for score_data in result['scores']:
                    if 'cnn_score' in score_data:
                        all_scores.append(score_data['cnn_score'])
        
        if not all_scores:
            print("⚠️ No CNN scores found in results")
            return
        
        # Create visualization
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Docking Results Analysis', fontsize=16)
        
        # Score distribution histogram
        axes[0, 0].hist(all_scores, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
        axes[0, 0].set_title('CNN Score Distribution')
        axes[0, 0].set_xlabel('CNN Score')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].axvline(np.mean(all_scores), color='red', linestyle='--', label=f'Mean: {np.mean(all_scores):.3f}')
        axes[0, 0].legend()
        
        # Box plot by receptor
        receptor_scores = {}
        for result in successful_results:
            receptor = result['receptor']
            if receptor not in receptor_scores:
                receptor_scores[receptor] = []
            if 'scores' in result:
                for score_data in result['scores']:
                    if 'cnn_score' in score_data:
                        receptor_scores[receptor].append(score_data['cnn_score'])
        
        if receptor_scores:
            receptor_data = [scores for scores in receptor_scores.values() if scores]
            receptor_labels = [receptor for receptor, scores in receptor_scores.items() if scores]
            
            axes[0, 1].boxplot(receptor_data, labels=receptor_labels)
            axes[0, 1].set_title('CNN Scores by Receptor')
            axes[0, 1].set_ylabel('CNN Score')
            axes[0, 1].tick_params(axis='x', rotation=45)
        
        # Success rate by receptor
        receptor_stats = {}
        for result in results:
            receptor = result['receptor']
            if receptor not in receptor_stats:
                receptor_stats[receptor] = {'total': 0, 'success': 0}
            receptor_stats[receptor]['total'] += 1
            if result['status'] == 'success':
                receptor_stats[receptor]['success'] += 1
        
        receptors = list(receptor_stats.keys())
        success_rates = [receptor_stats[r]['success']/receptor_stats[r]['total']*100 for r in receptors]
        
        axes[1, 0].bar(receptors, success_rates, color='lightgreen', alpha=0.7)
        axes[1, 0].set_title('Success Rate by Receptor')
        axes[1, 0].set_ylabel('Success Rate (%)')
        axes[1, 0].tick_params(axis='x', rotation=45)
        
        # Top scoring ligands
        top_ligands = []
        for result in successful_results:
            if 'scores' in result:
                max_score = max([s.get('cnn_score', 0) for s in result['scores']], default=0)
                top_ligands.append({
                    'ligand': result['ligand'],
                    'receptor': result['receptor'],
                    'max_score': max_score
                })
        
        if top_ligands:
            top_ligands = sorted(top_ligands, key=lambda x: x['max_score'], reverse=True)[:10]
            ligand_names = [f"{l['ligand']}\n({l['receptor']})" for l in top_ligands]
            scores = [l['max_score'] for l in top_ligands]
            
            axes[1, 1].barh(range(len(ligand_names)), scores, color='orange', alpha=0.7)
            axes[1, 1].set_yticks(range(len(ligand_names)))
            axes[1, 1].set_yticklabels(ligand_names, fontsize=8)
            axes[1, 1].set_title('Top 10 Scoring Ligands')
            axes[1, 1].set_xlabel('Max CNN Score')
        
        plt.tight_layout()
        plt.savefig('visualizations/docking_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        # Print summary statistics
        print("\n📊 Docking Results Summary:")
        print(f"   Total results: {len(results)}")
        print(f"   Successful: {len(successful_results)}")
        print(f"   Failed: {len(results) - len(successful_results)}")
        print(f"   Success rate: {len(successful_results)/len(results)*100:.1f}%")
        print(f"   CNN scores - Mean: {np.mean(all_scores):.3f}, Std: {np.std(all_scores):.3f}")
        print(f"   CNN scores - Min: {np.min(all_scores):.3f}, Max: {np.max(all_scores):.3f}")
    
    def create_interactive_dashboard(self, results):
        """Create interactive Plotly dashboard"""
        if not PLOTLY_AVAILABLE:
            print("⚠️ Plotly not available. Skipping interactive dashboard.")
            return
        
        successful_results = [r for r in results if r['status'] == 'success']
        
        if not successful_results:
            print("⚠️ No successful results for interactive dashboard")
            return
        
        # Prepare data
        dashboard_data = []
        for result in successful_results:
            if 'scores' in result:
                for i, score_data in enumerate(result['scores']):
                    if 'cnn_score' in score_data:
                        dashboard_data.append({
                            'Receptor': result['receptor'],
                            'Ligand': result['ligand'],
                            'Site_ID': result['site_id'],
                            'Pose_ID': i + 1,
                            'CNN_Score': score_data['cnn_score'],
                            'CNN_Affinity': score_data.get('cnn_affinity', score_data['cnn_score'])
                        })
        
        if not dashboard_data:
            print("⚠️ No score data for interactive dashboard")
            return
        
        df = pd.DataFrame(dashboard_data)
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('CNN Score Distribution', 'Scores by Receptor', 
                          'Top Ligands', 'Score vs Affinity'),
            specs=[[{"type": "histogram"}, {"type": "box"}],
                   [{"type": "bar"}, {"type": "scatter"}]]
        )
        
        # Score distribution
        fig.add_trace(
            go.Histogram(x=df['CNN_Score'], name='CNN Score Distribution', nbinsx=30),
            row=1, col=1
        )
        
        # Box plot by receptor
        for receptor in df['Receptor'].unique():
            receptor_data = df[df['Receptor'] == receptor]['CNN_Score']
            fig.add_trace(
                go.Box(y=receptor_data, name=receptor),
                row=1, col=2
            )
        
        # Top ligands
        top_ligands = df.groupby('Ligand')['CNN_Score'].max().nlargest(10)
        fig.add_trace(
            go.Bar(x=top_ligands.index, y=top_ligands.values, name='Top Ligands'),
            row=2, col=1
        )
        
        # Score vs Affinity
        fig.add_trace(
            go.Scatter(x=df['CNN_Score'], y=df['CNN_Affinity'], 
                      mode='markers', name='Score vs Affinity',
                      text=df['Ligand'], hovertemplate='Ligand: %{text}<br>Score: %{x}<br>Affinity: %{y}'),
            row=2, col=2
        )
        
        fig.update_layout(height=800, showlegend=False, title_text="Interactive Docking Analysis Dashboard")
        fig.show()
        
        # Save as HTML
        fig.write_html('visualizations/interactive_dashboard.html')
        print("✅ Interactive dashboard saved to visualizations/interactive_dashboard.html")


class QualityControlValidator:
    """Quality control validation for docking results"""
    
    def __init__(self):
        self.validation_results = {}
    
    def validate_docking_results(self, results):
        """Comprehensive validation of docking results"""
        print("🔍 Validating docking results...")
        
        validation_results = {
            'total_results': len(results),
            'successful_dockings': 0,
            'failed_dockings': 0,
            'quality_issues': [],
            'score_distribution': {},
            'receptor_analysis': {},
            'recommendations': []
        }
        
        successful_results = [r for r in results if r['status'] == 'success']
        validation_results['successful_dockings'] = len(successful_results)
        validation_results['failed_dockings'] = len(results) - len(successful_results)
        
        if successful_results:
            # Analyze score distribution
            all_scores = []
            for result in successful_results:
                if 'scores' in result:
                    for score_data in result['scores']:
                        if 'cnn_score' in score_data:
                            all_scores.append(score_data['cnn_score'])
            
            if all_scores:
                validation_results['score_distribution'] = {
                    'mean': np.mean(all_scores),
                    'std': np.std(all_scores),
                    'min': np.min(all_scores),
                    'max': np.max(all_scores),
                    'median': np.median(all_scores),
                    'q25': np.percentile(all_scores, 25),
                    'q75': np.percentile(all_scores, 75)
                }
                
                # Quality checks
                if np.mean(all_scores) < 0.3:
                    validation_results['quality_issues'].append("Low average CNN scores (< 0.3)")
                    validation_results['recommendations'].append("Consider increasing exhaustiveness or using refinement mode")
                
                if np.std(all_scores) < 0.1:
                    validation_results['quality_issues'].append("Low score variance - possible convergence issues")
                    validation_results['recommendations'].append("Check binding site coordinates and box size")
                
                if np.max(all_scores) < 0.5:
                    validation_results['quality_issues'].append("No high-scoring poses found")
                    validation_results['recommendations'].append("Review ligand preparation and binding site definition")
        
        # Receptor-specific analysis
        receptor_stats = {}
        for result in results:
            receptor = result['receptor']
            if receptor not in receptor_stats:
                receptor_stats[receptor] = {'total': 0, 'success': 0, 'scores': []}
            receptor_stats[receptor]['total'] += 1
            if result['status'] == 'success':
                receptor_stats[receptor]['success'] += 1
                if 'scores' in result:
                    for score_data in result['scores']:
                        if 'cnn_score' in score_data:
                            receptor_stats[receptor]['scores'].append(score_data['cnn_score'])
        
        for receptor, stats in receptor_stats.items():
            success_rate = stats['success'] / stats['total'] * 100
            validation_results['receptor_analysis'][receptor] = {
                'total_pairs': stats['total'],
                'successful_pairs': stats['success'],
                'success_rate': success_rate,
                'avg_score': np.mean(stats['scores']) if stats['scores'] else 0,
                'max_score': np.max(stats['scores']) if stats['scores'] else 0
            }
            
            if success_rate < 50:
                validation_results['quality_issues'].append(f"Low success rate for {receptor} ({success_rate:.1f}%)")
                validation_results['recommendations'].append(f"Check receptor preparation for {receptor}")
        
        # Overall success rate check
        overall_success_rate = validation_results['successful_dockings'] / validation_results['total_results'] * 100
        if overall_success_rate < 70:
            validation_results['quality_issues'].append(f"Low overall success rate ({overall_success_rate:.1f}%)")
            validation_results['recommendations'].append("Review input structures and docking parameters")
        
        self.validation_results = validation_results
        return validation_results
    
    def generate_quality_report(self):
        """Generate comprehensive quality control report"""
        if not self.validation_results:
            print("⚠️ No validation results available. Run validate_docking_results() first.")
            return
        
        print("\n📊 Quality Control Report:")
        print(f"   Total Results: {self.validation_results['total_results']}")
        print(f"   Successful: {self.validation_results['successful_dockings']}")
        print(f"   Failed: {self.validation_results['failed_dockings']}")
        print(f"   Success Rate: {self.validation_results['successful_dockings']/self.validation_results['total_results']*100:.1f}%")
        
        if self.validation_results['score_distribution']:
            dist = self.validation_results['score_distribution']
            print(f"\n   Score Distribution:")
            print(f"     Mean: {dist['mean']:.3f}")
            print(f"     Std: {dist['std']:.3f}")
            print(f"     Range: {dist['min']:.3f} - {dist['max']:.3f}")
            print(f"     Median: {dist['median']:.3f}")
        
        if self.validation_results['quality_issues']:
            print(f"\n   ⚠️ Quality Issues ({len(self.validation_results['quality_issues'])}):")
            for issue in self.validation_results['quality_issues']:
                print(f"     - {issue}")
        
        if self.validation_results['recommendations']:
            print(f"\n   💡 Recommendations ({len(self.validation_results['recommendations'])}):")
            for rec in self.validation_results['recommendations']:
                print(f"     - {rec}")
        
        # Save report
        with open('enhanced_analysis/quality_control_report.json', 'w') as f:
            json.dump(self.validation_results, f, indent=2)
        
        print("\n✅ Quality control report saved to enhanced_analysis/quality_control_report.json")
    
    def save_validation_results(self, filename='enhanced_analysis/validation_results.json'):
        """Save validation results to file"""
        validation_data = {
            'timestamp': datetime.now().isoformat(),
            'validation_results': self.validation_results
        }
        
        with open(filename, 'w') as f:
            json.dump(validation_data, f, indent=2)
        
        print(f"✅ Validation results saved to {filename}")
    
    def load_validation_results(self, filename='enhanced_analysis/validation_results.json'):
        """Load validation results from file"""
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                validation_data = json.load(f)
            
            self.validation_results = validation_data.get('validation_results', {})
            print(f"✅ Validation results loaded from {filename}")
            return True
        else:
            print(f"⚠️ Validation results file not found: {filename}")
            return False


def main():
    """Main function for testing analysis tools"""
    print("🚀 Post-Docking Analysis Tools Module")
    print("=" * 50)
    
    # Initialize analysis tools
    analysis_dashboard = DockingAnalysisDashboard()
    qc_validator = QualityControlValidator()
    
    print("✅ Post-docking analysis tools initialized")
    
    print("\n🔧 Usage Examples:")
    print("   # Create visualizations")
    print("   analysis_dashboard.create_score_distribution_plot(results)")
    if PLOTLY_AVAILABLE:
        print("   analysis_dashboard.create_interactive_dashboard(results)")
    print("   ")
    print("   # Quality control validation")
    print("   qc_validator.validate_docking_results(results)")
    print("   qc_validator.generate_quality_report()")
    print("   ")
    print("   # Save/load validation results")
    print("   qc_validator.save_validation_results()")
    print("   qc_validator.load_validation_results()")
    
    print("\n💡 Analysis Features:")
    print("   • Score distribution analysis")
    print("   • Receptor-specific performance metrics")
    print("   • Top scoring ligand identification")
    print("   • Quality control validation")
    print("   • Interactive visualizations (if Plotly available)")
    print("   • Comprehensive reporting")
    print("   • Export capabilities")


if __name__ == "__main__":
    main()
