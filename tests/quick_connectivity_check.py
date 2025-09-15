#!/usr/bin/env python3
"""Quick check of current database connectivity"""

import sys
from pathlib import Path
import networkx as nx
import pickle

# Load the current database directly
db_path = Path('/Users/brock/Documents/GitHub/survey-dag-extractor/surveys_db/current_database.pkl')

try:
    with open(db_path, 'rb') as f:
        extractor = pickle.load(f)
    
    graph = extractor.graph
    print(f"Database loaded: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    # Check connectivity
    components = nx.number_weakly_connected_components(graph)
    isolated = list(nx.isolates(graph))
    
    print(f"Components: {components}")
    print(f"Isolated nodes: {len(isolated)}")
    
    if isolated:
        print(f"Isolated: {isolated}")
    
    # Check reachability from start
    questions = [(n['id'], n.get('order_index', 999)) for n in extractor.nodes if n['type'] == 'question']
    if questions:
        start_node = min(questions, key=lambda x: x[1])[0]
        reachable = set(nx.descendants(graph, start_node))
        reachable.add(start_node)
        
        all_nodes = set(graph.nodes())
        unreachable = all_nodes - reachable
        
        print(f"Start node: {start_node}")
        print(f"Reachable: {len(reachable)}/{len(all_nodes)}")
        print(f"Unreachable: {len(unreachable)}")
        
        if unreachable:
            print(f"Unreachable nodes: {list(unreachable)}")
            
            # Check what each unreachable node is
            for node_id in list(unreachable)[:5]:  # Show first 5
                node_data = next((n for n in extractor.nodes if n['id'] == node_id), {})
                node_type = node_data.get('type', 'unknown')
                order_idx = node_data.get('order_index', 'N/A')
                print(f"  {node_id}: {node_type}, order {order_idx}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
