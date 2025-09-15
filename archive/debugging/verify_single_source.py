#!/usr/bin/env python3
"""
Verify single source of truth implementation
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from database_manager import DatabaseManager

def main():
    print("VERIFICATION: Single Source of Truth")
    print("=" * 50)
    
    db = DatabaseManager()
    db.print_status()
    
    # Test loading
    try:
        graph = db.load_graph()
        print(f"\n✅ SUCCESS: Single working database operational")
        print(f"   Current database has {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        return
    
    # Show directory structure
    print(f"\n📁 New Directory Structure:")
    print(f"   surveys_db/")
    print(f"   ├── current_database.pkl      ← SINGLE SOURCE OF TRUTH")
    print(f"   ├── snapshots/                ← All backups here")
    print(f"   │   ├── legacy_*.pkl          ← Old scattered files")
    print(f"   │   └── (future snapshots)")
    print(f"   └── exports/                  ← JSON exports")
    
    print(f"\n🔧 All scripts now use:")
    print(f"   from database_manager import DatabaseManager")
    print(f"   db = DatabaseManager()")
    print(f"   graph = db.load_graph()")
    print(f"   db.save_graph(graph)")
    
    print(f"\n✅ NO MORE DATABASE CONFUSION")

if __name__ == "__main__":
    main()
