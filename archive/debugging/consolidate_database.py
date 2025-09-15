#!/usr/bin/env python3
"""
Database Consolidation Script

Consolidates all progress files back into the main database.
Two-stage pipeline: Progress files → Consolidated database
"""

import sys
import json
import pickle
from pathlib import Path

project_root = Path(__file__).parent
sys.path.append(str(project_root))

from graph_analysis.schema_compliant_extractor import SchemaCompliantExtractor

def main():
    print("DATABASE CONSOLIDATION")
    print("=" * 50)
    
    # Load original database
    schema_path = project_root / "data" / "survey_dag_schema_v1.1.json"
    nodes_path = project_root / "data" / "htops_complete_nodes_minimal.json"
    
    try:
        extractor = SchemaCompliantExtractor(schema_path, nodes_path)
        print(f"✓ Original database loaded: {len(extractor.nodes)} nodes")
    except Exception as e:
        print(f"✗ Failed to load original database: {e}")
        return
    
    # Find all progress files
    surveys_db = project_root / "surveys_db"
    progress_files = sorted(surveys_db.glob("rich_extraction_progress_chunk_*.json"))
    
    if not progress_files:
        print("✗ No progress files found")
        return
        
    print(f"✓ Found {len(progress_files)} progress files")
    
    # Track consolidation stats
    total_nodes_updated = 0
    total_universe_added = 0
    nodes_with_domains = 0
    
    # Process each progress file
    for progress_file in progress_files:
        print(f"  Processing {progress_file.name}...")
        
        try:
            with open(progress_file, 'r') as f:
                progress_data = json.load(f)
            
            chunk_nodes = progress_data['nodes_updated']
            
            # Update nodes with extracted data
            for update_node in chunk_nodes:
                node_id = update_node['id']
                
                # Find corresponding node in extractor
                target_node = None
                for node in extractor.nodes:
                    if node['id'] == node_id:
                        target_node = node
                        break
                
                if target_node is None:
                    print(f"    Warning: Node {node_id} not found in database")
                    continue
                
                # Update domain (response options)
                if 'domain' in update_node:
                    target_node['domain'] = update_node['domain']
                    extractor.graph.nodes[node_id]['domain'] = update_node['domain']
                    nodes_with_domains += 1
                
                # Update universe conditions
                if 'universe' in update_node:
                    target_node['universe'] = update_node['universe']
                    extractor.graph.nodes[node_id]['universe'] = update_node['universe']
                    total_universe_added += 1
                
                total_nodes_updated += 1
                
        except Exception as e:
            print(f"    ✗ Error processing {progress_file.name}: {e}")
            continue
    
    print(f"\nCONSOLIDATION SUMMARY:")
    print(f"  Progress files processed: {len(progress_files)}")
    print(f"  Nodes updated: {total_nodes_updated}")
    print(f"  Nodes with domains: {nodes_with_domains}")
    print(f"  Universe conditions added: {total_universe_added}")
    
    # Save consolidated database
    consolidated_db_path = project_root / "surveys_db" / "htops_consolidated_database.pkl"
    
    try:
        with open(consolidated_db_path, 'wb') as f:
            pickle.dump(extractor, f)
        print(f"✓ Consolidated database saved: {consolidated_db_path}")
        
        # Update the main database file too
        main_db_path = project_root / "surveys_db" / "htops_graph_database.pkl"
        with open(main_db_path, 'wb') as f:
            pickle.dump(extractor, f)
        print(f"✓ Main database updated: {main_db_path}")
        
    except Exception as e:
        print(f"✗ Failed to save consolidated database: {e}")
        return
    
    # Run final sanity check
    print(f"\nFINAL VALIDATION:")
    validation = extractor.validate_current_state()
    props = validation['graph_properties']
    node_counts = validation['node_counts']
    
    print(f"  Total nodes: {node_counts['total']}")
    print(f"  Questions: {node_counts['questions']}")
    print(f"  Edges: {extractor.graph.number_of_edges()}")
    print(f"  Is DAG: {props['is_dag']}")
    print(f"  Isolated nodes: {len(props['isolated_nodes'])}")
    
    # Create consolidated export
    export_path = project_root / "surveys_db" / "consolidated_extraction_summary.json"
    summary = {
        'consolidation_stats': {
            'progress_files_processed': len(progress_files),
            'nodes_updated': total_nodes_updated,
            'nodes_with_domains': nodes_with_domains,
            'universe_conditions_added': total_universe_added
        },
        'final_state': {
            'total_nodes': len(extractor.nodes),
            'total_edges': extractor.graph.number_of_edges(),
            'is_dag': props['is_dag'],
            'isolated_nodes': len(props['isolated_nodes'])
        },
        'sample_enriched_nodes': []
    }
    
    # Add sample of enriched nodes
    for node in extractor.nodes[:10]:
        if 'domain' in node or 'universe' in node:
            sample = {
                'id': node['id'],
                'has_domain': 'domain' in node,
                'has_universe': 'universe' in node
            }
            if 'domain' in node:
                sample['domain_values_count'] = len(node['domain'].get('values', []))
            summary['sample_enriched_nodes'].append(sample)
    
    with open(export_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"✓ Consolidation summary saved: {export_path}")
    print(f"\n{'='*50}")
    print("CONSOLIDATION COMPLETE! 🎉")
    print("Your extracted data is now in the main database.")

if __name__ == "__main__":
    main()
