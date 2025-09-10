#!/usr/bin/env python3
"""
Simple test to verify graph_analysis setup
"""

import sys
from pathlib import Path

# Add current directory to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def test_basic_import():
    """Test basic imports work"""
    try:
        from graph_analysis.schema_compliant_extractor import SchemaCompliantExtractor
        from graph_analysis.dag_validator import DAGValidator
        from graph_analysis.coverage_analyzer import CoverageAnalyzer
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_file_paths():
    """Test required files exist"""
    schema_path = project_root / "data" / "survey_dag_schema_v1.1.json"
    nodes_path = project_root / "data" / "htops_complete_nodes_minimal.json"
    
    if schema_path.exists():
        print(f"✓ Schema file found: {schema_path}")
    else:
        print(f"✗ Schema file missing: {schema_path}")
        return False
        
    if nodes_path.exists():
        print(f"✓ Nodes file found: {nodes_path}")
    else:
        print(f"✗ Nodes file missing: {nodes_path}")
        return False
        
    return True

def test_extractor_init():
    """Test extractor initialization"""
    try:
        schema_path = project_root / "data" / "survey_dag_schema_v1.1.json"
        nodes_path = project_root / "data" / "htops_complete_nodes_minimal.json"
        
        from graph_analysis.schema_compliant_extractor import SchemaCompliantExtractor
        extractor = SchemaCompliantExtractor(schema_path, nodes_path)
        
        print(f"✓ Extractor initialized with {len(extractor.nodes)} nodes")
        print(f"✓ Graph has {extractor.graph.number_of_nodes()} nodes, {extractor.graph.number_of_edges()} edges")
        return True
    except Exception as e:
        print(f"✗ Extractor initialization failed: {e}")
        return False

if __name__ == "__main__":
    print("Graph Analysis Module Test")
    print("=" * 30)
    
    tests = [
        test_basic_import,
        test_file_paths, 
        test_extractor_init
    ]
    
    passed = 0
    for test in tests:
        print(f"\nRunning {test.__name__}...")
        if test():
            passed += 1
        else:
            print("Test failed, stopping")
            break
    
    print(f"\nResults: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("\n✓ Graph analysis module is ready!")
        print("\nNext step: Use the extractor for Phase 2 (response options)")
    else:
        print("\n✗ Setup incomplete - check errors above")
