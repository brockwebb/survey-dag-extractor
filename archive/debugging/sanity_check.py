#!/usr/bin/env python3
"""
Quick Database Sanity Check

Validates what we actually extracted into the database.
"""

import sys
import json
from pathlib import Path

project_root = Path(__file__).parent
sys.path.append(str(project_root))

from graph_analysis.schema_compliant_extractor import SchemaCompliantExtractor

def main():
    print("DATABASE SANITY CHECK")
    print("=" * 50)
    
    # Load from the actual database pickle (not original files)
    db_path = project_root / "surveys_db" / "htops_graph_database.pkl"
    
    if not db_path.exists():
        print(f"✗ Database not found at: {db_path}")
        return
    
    # Load the enriched database
    import pickle
    with open(db_path, 'rb') as f:
        extractor = pickle.load(f)
    
    print(f"✓ Enriched database loaded from: {db_path}")
    print(f"✓ Database contains: {len(extractor.nodes)} nodes, {extractor.graph.number_of_edges()} edges")
    
    # Check nodes with response options
    nodes_with_options = 0
    nodes_with_universe = 0
    sample_nodes = []
    
    for node in extractor.nodes:
        if 'domain' in node and 'values' in node.get('domain', {}):
            nodes_with_options += 1
            if len(sample_nodes) < 5:  # Collect samples
                sample_nodes.append({
                    'id': node['id'],
                    'type': node['type'],
                    'domain': node['domain'],
                    'universe': node.get('universe', 'None')
                })
        
        if 'universe' in node:
            nodes_with_universe += 1
    
    print(f"\nNODE ANALYSIS:")
    print(f"  Total nodes: {len(extractor.nodes)}")
    print(f"  Nodes with response options: {nodes_with_options}")
    print(f"  Nodes with universe conditions: {nodes_with_universe}")
    
    print(f"\nSAMPLE NODES WITH DATA:")
    for node in sample_nodes:
        print(f"  {node['id']} ({node['type']}):")
        print(f"    Domain: {node['domain']['kind']} - {len(node['domain'].get('values', []))} options")
        print(f"    Universe: {node['universe']}")
        print()
    
    # Check edges
    edges = extractor.get_all_edges()
    print(f"EDGE ANALYSIS:")
    print(f"  Total edges: {len(edges)}")
    
    # Sample edges
    print(f"\nSAMPLE EDGES:")
    for i, edge in enumerate(edges[:10]):
        print(f"  {edge['source']} → {edge['target']} ({edge.get('condition', 'always')})")
        if i >= 9:
            break
    
    # Check graph connectivity
    validation = extractor.validate_current_state()
    props = validation['graph_properties']
    
    print(f"\nGRAPH VALIDATION:")
    print(f"  Is DAG: {props['is_dag']}")
    print(f"  Is Connected: {props['is_connected']}")
    print(f"  Isolated nodes: {len(props['isolated_nodes'])}")
    if props['isolated_nodes']:
        print(f"    Isolated: {props['isolated_nodes'][:5]}...")
    
    # Export sample to check
    sample_export = project_root / "sanity_check_sample.json"
    with open(sample_export, 'w') as f:
        json.dump({
            'sample_nodes': sample_nodes,
            'sample_edges': edges[:10],
            'stats': {
                'total_nodes': len(extractor.nodes),
                'nodes_with_options': nodes_with_options,
                'nodes_with_universe': nodes_with_universe,
                'total_edges': len(edges),
                'is_dag': props['is_dag'],
                'isolated_count': len(props['isolated_nodes'])
            }
        }, f, indent=2)
    
    print(f"\n✓ Sample data exported to: {sample_export}")
    print(f"\n{'='*50}")
    print("DATABASE LOOKS GOOD!" if nodes_with_options > 50 else "DATABASE NEEDS MORE DATA!")

if __name__ == "__main__":
    main()
