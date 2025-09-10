#!/usr/bin/env python3
"""
HTOPS Survey NetworkX Setup - Complete Pipeline
Creates NetworkX graph from extracted nodes
"""

import subprocess
import sys
from pathlib import Path

def check_dependencies():
    """Check if required packages are available"""
    try:
        import networkx as nx
        print(f"✓ NetworkX version {nx.__version__} found")
        return True
    except ImportError:
        print("ERROR: NetworkX not found. Install with: pip install networkx")
        return False

def run_script(script_name):
    """Run a Python script and return success status"""
    print(f"\nRunning {script_name}...")
    try:
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=True, text=True, cwd=Path.cwd())
        
        if result.returncode == 0:
            print(result.stdout)
            return True
        else:
            print(f"ERROR in {script_name}:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"Failed to run {script_name}: {e}")
        return False

def main():
    """Complete NetworkX graph setup pipeline"""
    print("HTOPS Survey NetworkX Graph Setup")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        return False
    
    # Check if data file exists
    data_file = Path('data/htops_complete_nodes_minimal.json')
    if not data_file.exists():
        print(f"ERROR: {data_file} not found")
        print("Make sure the extraction has been completed first.")
        return False
    
    # Run graph creation
    if not run_script('create_networkx_graph.py'):
        print("Graph creation failed. Stopping.")
        return False
    
    print("\nNetworkX graph setup complete!")
    print("\nFiles created:")
    print("  data/htops_survey_graph.pkl - Pickled NetworkX graph")
    print("  data/htops_graph_summary.json - Graph summary for inspection")
    print("\nNext steps:")
    print("  python explore_graph.py - Interactive graph exploration")
    print("  python create_networkx_graph.py - Recreate graph")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\nSetup failed. Check errors above.")
    sys.exit(0 if success else 1)
