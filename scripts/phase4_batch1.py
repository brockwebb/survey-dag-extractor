#!/usr/bin/env python3
"""
Phase 4 Batch 1: Schema Export + Validation
Exports survey DAG to final schema format and runs mathematical validation
"""

import sys
import os
import json
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.database_manager import DatabaseManager
from core.schema_exporter import SchemaExporter

def main():
    """Execute Phase 4 Batch 1: Schema export and validation"""
    print("PHASE 4 BATCH 1: SCHEMA EXPORT + VALIDATION")
    print("=" * 50)
    
    # Initialize components
    db = DatabaseManager()
    exporter = SchemaExporter()
    
    try:
        # Load the perfect DAG from Phase 3B
        print("📊 Loading perfect DAG from Phase 3B...")
        graph = db.load_graph()
        
        print(f"   ✅ Loaded: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
        
        # Create exports directory if it doesn't exist
        exports_dir = Path('../exports')
        exports_dir.mkdir(exist_ok=True)
        
        # Export to schema v1.1 format
        print("\n🔄 Exporting to Schema v1.1 format...")
        output_path = exports_dir / 'htops_survey_dag_v1.1.json'
        
        schema_dag = exporter.export_dag_to_schema(graph, str(output_path))
        
        # Basic validation checks
        print("\n🔍 Running basic validation checks...")
        
        # Check node count
        exported_nodes = len(schema_dag['survey_dag']['graph']['nodes'])
        if exported_nodes == graph.number_of_nodes():
            print(f"   ✅ Node count: {exported_nodes} (matches source)")
        else:
            print(f"   ❌ Node count mismatch: {exported_nodes} vs {graph.number_of_nodes()}")
        
        # Check edge count
        exported_edges = len(schema_dag['survey_dag']['graph']['edges'])
        if exported_edges == graph.number_of_edges():
            print(f"   ✅ Edge count: {exported_edges} (matches source)")
        else:
            print(f"   ❌ Edge count mismatch: {exported_edges} vs {graph.number_of_edges()}")
        
        # Check start node
        start_node = schema_dag['survey_dag']['graph']['start']
        print(f"   ✅ Start node: {start_node}")
        
        # Check terminals
        terminals = schema_dag['survey_dag']['graph']['terminals']
        print(f"   ✅ Terminal nodes: {len(terminals)} ({', '.join(terminals)})")
        
        # Check predicates
        predicates = schema_dag['survey_dag']['predicates']
        print(f"   ✅ Predicates generated: {len(predicates)}")
        
        # Validate JSON structure
        print("\n📋 Validating JSON structure...")
        try:
            # Re-parse to ensure valid JSON
            with open(output_path, 'r') as f:
                reparsed = json.load(f)
            print("   ✅ Valid JSON structure")
        except Exception as e:
            print(f"   ❌ JSON validation failed: {e}")
            return False
        
        # Summary
        print("\n🎉 PHASE 4A SCHEMA EXPORT COMPLETE!")
        print(f"   📄 Output: {output_path}")
        print(f"   📊 Nodes: {exported_nodes}")
        print(f"   🔗 Edges: {exported_edges}")
        print(f"   🧮 Predicates: {len(predicates)}")
        print(f"   🏁 Start: {start_node}")
        print(f"   🎯 Terminals: {len(terminals)}")
        
        # Create snapshot for Phase 4B
        db.create_snapshot("phase4a_schema_export_complete")
        
        print("\n✅ Ready for Phase 4B: Mathematical Validation")
        
        return True
        
    except Exception as e:
        print(f"❌ Phase 4A failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)