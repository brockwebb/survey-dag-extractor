#!/usr/bin/env python3
"""
Graph Database Setup and Initialization

Loads 133 extracted survey nodes into NetworkX graph database
with v1.1 schema compliance and mathematical validation.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.append(str(project_root))

def main():
    print("Survey DAG Graph Database Setup (v1.1)")
    print("=" * 45)
    
    # 1: Initialize graph database system
    try:
        from graph_analysis.schema_compliant_extractor import SchemaCompliantExtractor
        print("✓ Graph database system loaded")
    except Exception as e:
        print(f"✗ Database system failed to load: {e}")
        return
    
    # 2: Verify data files
    schema_path = project_root / "data" / "survey_dag_schema_v1.1.json"
    nodes_path = project_root / "data" / "htops_complete_nodes_minimal.json"
    
    if not schema_path.exists():
        print(f"✗ Schema file missing: {schema_path}")
        return
    print(f"✓ Schema found: survey_dag_schema_v1.1.json")
    
    if not nodes_path.exists():
        print(f"✗ Nodes file missing: {nodes_path}")
        return
    print(f"✓ Node data found: htops_complete_nodes_minimal.json")
    
    # 3: Initialize graph database
    try:
        print("\nInitializing graph database...")
        extractor = SchemaCompliantExtractor(schema_path, nodes_path)
        print(f"✓ Graph database initialized with {len(extractor.nodes)} nodes")
        
        # Show database status
        extractor.print_status()
        
        # Save graph database to surveys_db/
        db_path = project_root / "surveys_db" / "htops_graph_database.pkl"
        db_path.parent.mkdir(exist_ok=True)  # Create directory if needed
        print(f"\nSaving graph database to: {db_path}")
        
        import pickle
        with open(db_path, 'wb') as f:
            pickle.dump(extractor.graph, f)
        print("✓ Graph database saved")
        
        print("\n" + "=" * 45)
        print("GRAPH DATABASE SETUP COMPLETE!")
        print("=" * 45)
        print("\nDatabase ready for:")
        print("  • Phase 2: Response options extraction")
        print("  • Phase 3: Universe conditions & routing logic")
        print("  • Mathematical validation & analysis")
        print("\nNext step: python graph_analysis/interactive_phase2.py")
        
        return True
        
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n✗ Setup failed")
        sys.exit(1)
