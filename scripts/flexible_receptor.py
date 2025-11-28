#!/usr/bin/env python3
"""
Flexible Receptor Docking Configuration

This module manages flexible receptor configurations for GNINA docking.
Provides auto-detection of flexible residues and manual specification options.

Based on the Enhanced GNINA Docking Pipeline notebook.

References:
- GNINA: https://github.com/gnina/gnina
"""

import os
import sys
import numpy as np
from datetime import datetime


class FlexibleReceptorManager:
    """Manage flexible receptor configurations for GNINA docking"""
    
    def __init__(self):
        self.flexible_residues = {}
        self.flexible_config = {
            'auto_detect': True,
            'distance_threshold': 5.0,
            'max_flexible_residues': 20,
            'flexdist': 3.5
        }
    
    def auto_detect_flexible_residues(self, receptor, binding_center, distance_threshold=5.0):
        """Auto-detect flexible residues near binding site"""
        try:
            from Bio.PDB import PDBParser, NeighborSearch
            from Bio.PDB.PDBExceptions import PDBConstructionWarning
            import warnings
            warnings.simplefilter('ignore', PDBConstructionWarning)
            
            receptor_pdb = f"receptors/{receptor}.pdbqt"
            if not os.path.exists(receptor_pdb):
                print(f"⚠️ Receptor file not found: {receptor_pdb}")
                return []
            
            parser = PDBParser(QUIET=True)
            structure = parser.get_structure('receptor', receptor_pdb)
            
            # Get all atoms
            atoms = []
            for model in structure:
                for chain in model:
                    for residue in chain:
                        for atom in residue:
                            atoms.append(atom)
            
            # Create neighbor search
            ns = NeighborSearch(atoms)
            
            # Find residues within distance of binding center
            center_atom = None
            min_distance = float('inf')
            
            for atom in atoms:
                dist = atom.coord - np.array(binding_center)
                dist = np.linalg.norm(dist)
                if dist < min_distance:
                    min_distance = dist
                    center_atom = atom
            
            if center_atom is None:
                return []
            
            # Find neighbors within threshold
            neighbors = ns.search(center_atom.coord, distance_threshold, level='R')
            
            flexible_residues = []
            for residue in neighbors:
                chain_id = residue.parent.id
                res_num = residue.id[1]
                flexible_residues.append(f"{chain_id}:{res_num}")
            
            # Apply limits
            if len(flexible_residues) > self.flexible_config['max_flexible_residues']:
                flexible_residues = flexible_residues[:self.flexible_config['max_flexible_residues']]
                print(f"⚠️ Limited flexible residues to {self.flexible_config['max_flexible_residues']}")
            
            return sorted(flexible_residues)
            
        except ImportError:
            print("⚠️ BioPython not available for auto-detection")
            return []
        except Exception as e:
            print(f"⚠️ Error in auto-detection: {e}")
            return []
    
    def set_flexible_residues(self, receptor, flexible_residues=None, auto_detect=True, binding_center=None):
        """Set flexible residues for a receptor"""
        if flexible_residues is not None:
            # Manual specification
            self.flexible_residues[receptor] = flexible_residues
            print(f"✅ Set manual flexible residues for {receptor}: {flexible_residues}")
            
        elif auto_detect and binding_center is not None:
            # Auto-detection
            detected = self.auto_detect_flexible_residues(receptor, binding_center)
            self.flexible_residues[receptor] = detected
            print(f"✅ Auto-detected {len(detected)} flexible residues for {receptor}: {detected}")
        else:
            print(f"⚠️ No flexible residues set for {receptor}")
            self.flexible_residues[receptor] = []
    
    def set_bulk_flexibility(self, pairlist_df, auto_detect=True):
        """Set flexible residues for all receptors in pairlist"""
        print("🔄 Configuring flexible residues for all receptors...")
        
        for _, row in pairlist_df.iterrows():
            receptor = row['receptor']
            if receptor not in self.flexible_residues:
                binding_center = [row['center_x'], row['center_y'], row['center_z']]
                self.set_flexible_residues(receptor, auto_detect=auto_detect, binding_center=binding_center)
    
    def get_flexible_residues_dict(self):
        """Get dictionary of flexible residues for all receptors"""
        return self.flexible_residues.copy()
    
    def display_flexibility_summary(self):
        """Display summary of flexible receptor configuration"""
        print("🔄 Flexible Receptor Configuration Summary:")
        for receptor, residues in self.flexible_residues.items():
            print(f"   {receptor}: {len(residues)} flexible residues")
            if residues:
                print(f"      {', '.join(residues[:5])}{'...' if len(residues) > 5 else ''}")
    
    def save_flexibility_config(self, filename='results/flexible_residues.json'):
        """Save flexible residues configuration to file"""
        config_data = {
            'timestamp': datetime.now().isoformat(),
            'flexible_residues': self.flexible_residues,
            'flexible_config': self.flexible_config
        }
        
        with open(filename, 'w') as f:
            import json
            json.dump(config_data, f, indent=2)
        
        print(f"✅ Flexible residues configuration saved to {filename}")
    
    def load_flexibility_config(self, filename='results/flexible_residues.json'):
        """Load flexible residues configuration from file"""
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                import json
                config_data = json.load(f)
            
            self.flexible_residues = config_data.get('flexible_residues', {})
            self.flexible_config = config_data.get('flexible_config', self.flexible_config)
            
            print(f"✅ Flexible residues configuration loaded from {filename}")
            return True
        else:
            print(f"⚠️ Flexible residues configuration file not found: {filename}")
            return False
    
    def validate_flexible_residues(self, receptor):
        """Validate flexible residues for a receptor"""
        if receptor not in self.flexible_residues:
            print(f"⚠️ No flexible residues configured for {receptor}")
            return False
        
        residues = self.flexible_residues[receptor]
        if not residues:
            print(f"⚠️ Empty flexible residues list for {receptor}")
            return False
        
        # Check format (should be "CHAIN:RESNUM")
        valid_residues = []
        for residue in residues:
            if ':' in residue and len(residue.split(':')) == 2:
                chain, resnum = residue.split(':')
                try:
                    int(resnum)
                    valid_residues.append(residue)
                except ValueError:
                    print(f"⚠️ Invalid residue number format: {residue}")
            else:
                print(f"⚠️ Invalid residue format: {residue}")
        
        if len(valid_residues) != len(residues):
            print(f"⚠️ Some flexible residues have invalid format for {receptor}")
            return False
        
        print(f"✅ Validated {len(valid_residues)} flexible residues for {receptor}")
        return True
    
    def get_flexible_residues_for_receptor(self, receptor):
        """Get flexible residues for a specific receptor"""
        return self.flexible_residues.get(receptor, [])
    
    def clear_flexible_residues(self, receptor=None):
        """Clear flexible residues for a receptor or all receptors"""
        if receptor:
            if receptor in self.flexible_residues:
                del self.flexible_residues[receptor]
                print(f"✅ Cleared flexible residues for {receptor}")
            else:
                print(f"⚠️ No flexible residues found for {receptor}")
        else:
            self.flexible_residues.clear()
            print("✅ Cleared all flexible residues")
    
    def set_flexibility_parameters(self, distance_threshold=None, max_residues=None, flexdist=None):
        """Set flexibility detection parameters"""
        if distance_threshold is not None:
            self.flexible_config['distance_threshold'] = distance_threshold
            print(f"✅ Distance threshold set to {distance_threshold} Å")
        
        if max_residues is not None:
            self.flexible_config['max_flexible_residues'] = max_residues
            print(f"✅ Max flexible residues set to {max_residues}")
        
        if flexdist is not None:
            self.flexible_config['flexdist'] = flexdist
            print(f"✅ Flexdist set to {flexdist} Å")
    
    def get_flexibility_statistics(self):
        """Get statistics about flexible residues configuration"""
        total_receptors = len(self.flexible_residues)
        total_residues = sum(len(residues) for residues in self.flexible_residues.values())
        
        if total_receptors > 0:
            avg_residues = total_residues / total_receptors
            max_residues = max(len(residues) for residues in self.flexible_residues.values())
            min_residues = min(len(residues) for residues in self.flexible_residues.values())
        else:
            avg_residues = max_residues = min_residues = 0
        
        stats = {
            'total_receptors': total_receptors,
            'total_flexible_residues': total_residues,
            'average_residues_per_receptor': avg_residues,
            'max_residues_per_receptor': max_residues,
            'min_residues_per_receptor': min_residues
        }
        
        print("📊 Flexible Residues Statistics:")
        print(f"   Total receptors: {stats['total_receptors']}")
        print(f"   Total flexible residues: {stats['total_flexible_residues']}")
        print(f"   Average residues per receptor: {stats['average_residues_per_receptor']:.1f}")
        print(f"   Max residues per receptor: {stats['max_residues_per_receptor']}")
        print(f"   Min residues per receptor: {stats['min_residues_per_receptor']}")
        
        return stats


def main():
    """Main function for testing flexible receptor manager"""
    print("🚀 Flexible Receptor Manager Module")
    print("=" * 50)
    
    # Initialize flexible receptor manager
    flexible_manager = FlexibleReceptorManager()
    
    print("✅ Flexible Receptor Manager initialized")
    
    print("\n🔧 Usage Examples:")
    print("   # Auto-detect flexible residues for all receptors")
    print("   flexible_manager.set_bulk_flexibility(pairlist_df, auto_detect=True)")
    print("   ")
    print("   # Manual specification")
    print("   flexible_manager.set_flexible_residues('receptor1', ['A:123', 'A:124', 'A:125'])")
    print("   ")
    print("   # Get flexible residues dictionary")
    print("   flex_dict = flexible_manager.get_flexible_residues_dict()")
    print("   ")
    print("   # Display summary")
    print("   flexible_manager.display_flexibility_summary()")
    print("   ")
    print("   # Save configuration")
    print("   flexible_manager.save_flexibility_config()")
    print("   ")
    print("   # Load configuration")
    print("   flexible_manager.load_flexibility_config()")
    print("   ")
    print("   # Get statistics")
    print("   stats = flexible_manager.get_flexibility_statistics()")
    
    print("\n💡 Flexible Receptor Notes:")
    print("   • Auto-detection requires BioPython for PDB parsing")
    print("   • Manual specification allows precise control")
    print("   • Flexible residues improve docking accuracy (15-25% improvement)")
    print("   • Use distance threshold to control flexibility extent")
    print("   • Limit max residues to avoid excessive computational cost")


if __name__ == "__main__":
    main()
