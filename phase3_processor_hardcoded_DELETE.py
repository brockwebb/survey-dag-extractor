#!/usr/bin/env python3
"""
Phase 3: Universe Validation & Edge Creation

1. Make all universe conditions explicit ("always" vs "ASK IF...")
2. Extract routing logic from progress files
3. Create conditional edges to build DAG structure
4. Validate mathematical properties
"""

import sys
import json
import pickle
from pathlib import Path
import re

project_root = Path(__file__).parent
sys.path.append(str(project_root))

from graph_analysis.schema_compliant_extractor import SchemaCompliantExtractor

def main():
    print("PHASE 3: UNIVERSE VALIDATION & EDGE CREATION")
    print("=" * 60)
    
    # Load consolidated database
    db_path = project_root / "surveys_db" / "htops_graph_database.pkl"
    
    if not db_path.exists():
        print(f"✗ Database not found: {db_path}")
        print("Run consolidate_database.py first!")
        return
    
    with open(db_path, 'rb') as f:
        extractor = pickle.load(f)
    
    print(f"✓ Loaded database: {len(extractor.nodes)} nodes, {extractor.graph.number_of_edges()} edges")
    
    # Step 1: Make universe conditions explicit
    print(f"\nSTEP 1: UNIVERSE CONDITION ENHANCEMENT")
    print("-" * 40)
    explicit_count = make_universe_explicit(extractor)
    print(f"✓ Made {explicit_count} universe conditions explicit")
    
    # Step 2: Extract routing logic from progress files
    print(f"\nSTEP 2: ROUTING LOGIC EXTRACTION")
    print("-" * 40)
    routing_rules = extract_routing_from_progress(extractor)
    print(f"✓ Extracted {len(routing_rules)} routing rules")
    
    # Step 3: Create conditional edges
    print(f"\nSTEP 3: CONDITIONAL EDGE CREATION")
    print("-" * 40)
    edges_created = create_conditional_edges(extractor, routing_rules)
    print(f"✓ Created {edges_created} conditional edges")
    
    # Step 4: Add sequential fallthrough edges
    print(f"\nSTEP 4: SEQUENTIAL FALLTHROUGH EDGES")
    print("-" * 40)
    fallthrough_edges = add_fallthrough_edges(extractor)
    print(f"✓ Added {fallthrough_edges} fallthrough edges")
    
    # Step 5: Mathematical validation
    print(f"\nSTEP 5: MATHEMATICAL VALIDATION")
    print("-" * 40)
    validation_results = validate_dag_properties(extractor)
    print_validation_results(validation_results)
    
    # Step 6: Save Phase 3 results
    print(f"\nSTEP 6: SAVE PHASE 3 RESULTS")
    print("-" * 40)
    save_phase3_results(extractor, routing_rules, validation_results)
    
    print(f"\n" + "=" * 60)
    print("PHASE 3 COMPLETE! 🎉")
    print("=" * 60)
    
    # Final status
    extractor.print_status()

def make_universe_explicit(extractor):
    """Make all universe conditions explicit."""
    explicit_count = 0
    
    for node in extractor.nodes:
        if node['type'] in ['question', 'instruction']:
            if 'universe' not in node:
                # Add explicit "always" condition
                node['universe'] = {
                    'expression': 'always',
                    'dependencies': []
                }
                extractor.graph.nodes[node['id']]['universe'] = node['universe']
                explicit_count += 1
                print(f"  Added 'always' universe to {node['id']}")
    
    return explicit_count

def extract_routing_from_progress(extractor):
    """Extract routing logic from all progress files."""
    routing_rules = []
    
    surveys_db = project_root / "surveys_db"
    progress_files = sorted(surveys_db.glob("rich_extraction_progress_chunk_*.json"))
    
    for progress_file in progress_files:
        try:
            with open(progress_file, 'r') as f:
                progress_data = json.load(f)
            
            # Look for routing data in the progress file
            # Note: Current progress files don't store routing rules
            # This is where we'd extract them if they were saved
            print(f"  Processed {progress_file.name}")
            
        except Exception as e:
            print(f"  Warning: Error reading {progress_file.name}: {e}")
    
    # For now, we'll need to manually add some key routing rules
    # Based on what we know from the extraction
    routing_rules.extend([
        # Entry validation routing
        {'source': 'Language', 'condition': 'any', 'target': 'Q1', 'type': 'fallthrough'},
        {'source': 'Q1', 'condition': '== 1', 'target': 'ADDRESS_CONFIRM', 'type': 'branch'},
        {'source': 'Q1', 'condition': '== 2', 'target': 'NAME_CORR', 'type': 'branch'},
        {'source': 'Q1', 'condition': '== 3', 'target': 'NAME_CORR', 'type': 'branch'},
        {'source': 'NAME_CORR', 'condition': 'any', 'target': 'ADDRESS_CONFIRM', 'type': 'fallthrough'},
        {'source': 'ADDRESS_CONFIRM', 'condition': '== 1', 'target': 'LANG', 'type': 'branch'},
        {'source': 'ADDRESS_CONFIRM', 'condition': '== 2', 'target': 'GET_NAME', 'type': 'branch'},
        {'source': 'GET_NAME', 'condition': '== 1', 'target': 'LANG', 'type': 'branch'},
        {'source': 'GET_NAME', 'condition': '== 2', 'target': 'END', 'type': 'branch'},
        {'source': 'END', 'condition': 'always', 'target': 'R2a', 'type': 'terminate'},
        {'source': 'R2a', 'condition': 'always', 'target': 'SURVEY_COMPLETE', 'type': 'terminate'},
    ])
    
    return routing_rules

def create_conditional_edges(extractor, routing_rules):
    """Create conditional edges from routing rules."""
    edges_created = 0
    
    for rule in routing_rules:
        source = rule['source']
        target = rule['target']
        condition = rule['condition']
        edge_type = rule.get('type', 'branch')
        
        # Check if both nodes exist
        if not extractor.graph.has_node(source):
            print(f"  Warning: Source node {source} not found")
            continue
        if not extractor.graph.has_node(target):
            print(f"  Warning: Target node {target} not found")
            continue
        
        # Create the edge
        try:
            edge_id = extractor.add_conditional_edge(source, target, condition, edge_type)
            if edge_id:
                edges_created += 1
                print(f"  Created edge: {source} → {target} ({condition})")
        except Exception as e:
            print(f"  Error creating edge {source} → {target}: {e}")
    
    return edges_created

def add_fallthrough_edges(extractor):
    """Add sequential fallthrough edges where no explicit routing exists."""
    fallthrough_edges = 0
    
    # Get questions in order
    questions = [n for n in extractor.nodes if n['type'] == 'question']
    questions.sort(key=lambda x: x['order_index'])
    
    for i, question in enumerate(questions[:-1]):
        current_id = question['id']
        
        # Check if this question already has outgoing edges
        outgoing_edges = list(extractor.graph.successors(current_id))
        
        if not outgoing_edges:
            # No routing defined, add fallthrough to next question
            next_question = questions[i + 1]
            next_id = next_question['id']
            
            try:
                edge_id = extractor.add_conditional_edge(current_id, next_id, 'always', 'fallthrough')
                if edge_id:
                    fallthrough_edges += 1
                    print(f"  Added fallthrough: {current_id} → {next_id}")
            except Exception as e:
                print(f"  Error adding fallthrough {current_id} → {next_id}: {e}")
    
    return fallthrough_edges

def validate_dag_properties(extractor):
    """Validate mathematical properties of the DAG."""
    validation = extractor.validate_current_state()
    
    # Additional DAG-specific checks
    import networkx as nx
    
    results = {
        'basic_properties': validation['graph_properties'],
        'survey_validation': validation.get('survey_validation', {}),
        'dag_specific': {
            'is_acyclic': nx.is_directed_acyclic_graph(extractor.graph),
            'node_count': extractor.graph.number_of_nodes(),
            'edge_count': extractor.graph.number_of_edges(),
            'isolated_nodes': list(nx.isolates(extractor.graph)),
            'strongly_connected_components': list(nx.strongly_connected_components(extractor.graph))
        }
    }
    
    # Check reachability from start
    questions = [n for n in extractor.nodes if n['type'] == 'question']
    if questions:
        start_node = min(questions, key=lambda x: x['order_index'])['id']
        reachable = set(nx.descendants(extractor.graph, start_node))
        reachable.add(start_node)
        
        results['reachability'] = {
            'start_node': start_node,
            'reachable_count': len(reachable),
            'unreachable_nodes': [n['id'] for n in extractor.nodes if n['id'] not in reachable]
        }
    
    return results

def print_validation_results(results):
    """Print validation results in a readable format."""
    dag_props = results['dag_specific']
    
    print(f"  Is Acyclic: {dag_props['is_acyclic']}")
    print(f"  Nodes: {dag_props['node_count']}")
    print(f"  Edges: {dag_props['edge_count']}")
    print(f"  Isolated nodes: {len(dag_props['isolated_nodes'])}")
    
    if 'reachability' in results:
        reach = results['reachability']
        print(f"  Start node: {reach['start_node']}")
        print(f"  Reachable nodes: {reach['reachable_count']}")
        print(f"  Unreachable: {len(reach['unreachable_nodes'])}")

def save_phase3_results(extractor, routing_rules, validation_results):
    """Save Phase 3 results."""
    # Save updated database
    db_path = project_root / "surveys_db" / "htops_phase3_database.pkl"
    with open(db_path, 'wb') as f:
        pickle.dump(extractor, f)
    print(f"✓ Phase 3 database saved: {db_path}")
    
    # Save routing rules and validation
    results_path = project_root / "surveys_db" / "phase3_results.json"
    results = {
        'routing_rules': routing_rules,
        'validation_results': validation_results,
        'phase3_stats': {
            'total_nodes': len(extractor.nodes),
            'total_edges': extractor.graph.number_of_edges(),
            'explicit_universe_conditions': len([n for n in extractor.nodes if 'universe' in n]),
            'routing_rules_applied': len(routing_rules)
        }
    }
    
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"✓ Phase 3 results saved: {results_path}")

if __name__ == "__main__":
    main()
