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
from core.dag_validator import MathematicalValidator

def main():
    """Execute Phase 4 Batch 1: Schema export and validation"""
    print("PHASE 4 BATCH 1: SCHEMA EXPORT + VALIDATION")
    print("=" * 50)
    
    # Initialize components
    db = DatabaseManager()
    exporter = SchemaExporter()
    
    # Path to FIXED schema for validation
    schema_path = Path('../data/survey_dag_schema_v1.1_fixed.json')
    validator = MathematicalValidator(str(schema_path) if schema_path.exists() else None)
    
    try:
        # Load the perfect DAG from Phase 3B
        print("📊 Loading perfect DAG from Phase 3B...")
        graph = db.load_graph()
        
        print(f"   ✅ Loaded: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
        
        # Create exports directory if it doesn't exist
        exports_dir = Path('../exports')
        exports_dir.mkdir(exist_ok=True)
        
        # Export to schema v1.1 format
        print("\n🔄 PHASE 4A: Exporting to Schema v1.1 format...")
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
        
        print("\n🎉 PHASE 4A COMPLETE!")
        
        # PHASE 4B: Mathematical Validation
        print("\n🔄 PHASE 4B: Mathematical Validation...")
        
        validation_result = validator.validate_survey_dag(schema_dag)
        
        # Print detailed validation summary
        validator.print_validation_summary(validation_result)
        
        # Save updated schema with validation results
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(schema_dag, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Updated schema file with validation results: {output_path}")
        
        # Final summary
        print("\n" + "=" * 60)
        print("🎉 PHASE 4A + 4B COMPLETE! SCHEMA EXPORT + VALIDATION")
        print("=" * 60)
        print(f"   📄 Output: {output_path}")
        print(f"   📊 Nodes: {exported_nodes}")
        print(f"   🔗 Edges: {exported_edges}")
        print(f"   🧮 Predicates: {len(predicates)}")
        print(f"   🏁 Start: {start_node}")
        print(f"   🎯 Terminals: {len(terminals)}")
        print(f"   📋 Validation: {validation_result['status']}")
        print(f"   😨 Gates: {sum(1 for v in validation_result['gates'].values() if v)}/{len(validation_result['gates'])}")
        
        # Create snapshot for Phase 4C
        db.create_snapshot("phase4ab_export_and_validation_complete")
        
        # Check if ready for Phase 4C
        if validation_result['status'] in ['OK', 'OK_WITH_WARNINGS']:
            print(f"\n✅ Ready for Phase 4C: Coverage Analysis")
        else:
            print(f"\n⚠️  Validation issues found - review before Phase 4C")
        
        return validation_result['status'] != 'FAIL'
        
    except Exception as e:
        print(f"❌ Phase 4A+4B failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)