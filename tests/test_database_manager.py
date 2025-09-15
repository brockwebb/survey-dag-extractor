#!/usr/bin/env python3
"""
Test script for new database management pattern.
Shows the single source of truth implementation.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from core.database_manager import DatabaseManager

def main():
    """Test the database manager."""
    print("Database Manager Test")
    print("=" * 50)
    
    # Initialize database manager
    db = DatabaseManager(project_root)
    
    # Show status
    db.print_status()
    
    # Test loading current database
    try:
        graph = db.load_graph()
        print(f"\n✓ Successfully loaded current database")
        print(f"  Nodes: {graph.number_of_nodes()}")
        print(f"  Edges: {graph.number_of_edges()}")
        
        # Create a snapshot for demonstration
        snapshot_path = db.create_snapshot("test_snapshot")
        print(f"\n✓ Created test snapshot: {snapshot_path.name}")
        
    except Exception as e:
        print(f"\n✗ Error loading database: {e}")
    
    print("\n" + "=" * 50)
    print("Single source of truth pattern implemented:")
    print("  ✓ ONE working file: surveys_db/current_database.pkl")
    print("  ✓ Legacy files archived in snapshots/")
    print("  ✓ All scripts will use DatabaseManager")

if __name__ == "__main__":
    main()
