#!/usr/bin/env python3
"""
HTOPS Survey NetworkX Graph Ingestion
Loads nodes into NetworkX directed graph for DAG operations
"""

import json
import networkx as nx
import pickle
from pathlib import Path

def create_survey_graph():
    """Create directed graph for survey DAG"""
    return nx.DiGraph()

def load_nodes_to_graph(json_file):
    """Load nodes from JSON into NetworkX graph"""
    
    # Load the JSON data
    with open(json_file, 'r') as f:
        nodes = json.load(f)
    
    # Create directed graph
    G = create_survey_graph()
    
    # Add all nodes with attributes
    for node in nodes:
        G.add_node(
            node['id'],
            type=node['type'],
            block=node['block'],
            order_index=node['order_index'],
            text=node['text'],
            response_options=None,  # Phase 2
            universe_condition=None  # Phase 3
        )
    
    print(f"Added {len(nodes)} nodes to graph")
    return G

def add_sequential_edges(G):
    """Add basic sequential flow edges based on order_index"""
    
    # Get nodes sorted by order_index
    nodes_by_order = sorted(G.nodes(data=True), key=lambda x: x[1]['order_index'])
    
    # Add sequential edges (will be refined in Phase 3 with skip logic)
    for i in range(len(nodes_by_order) - 1):
        current_node = nodes_by_order[i][0]
        next_node = nodes_by_order[i + 1][0]
        
        # Don't create edges TO terminals (they're endpoints)
        if G.nodes[next_node]['type'] != 'terminal':
            G.add_edge(current_node, next_node, edge_type='sequential')
    
    print(f"Added {G.number_of_edges()} sequential edges")
    return G

def validate_graph(G):
    """Validate graph structure"""
    
    print("\nGraph Validation:")
    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Edges: {G.number_of_edges()}")
    
    # Check node types
    node_types = {}
    for node_id, data in G.nodes(data=True):
        node_type = data['type']
        node_types[node_type] = node_types.get(node_type, 0) + 1
    
    print("\nNode types:")
    for node_type, count in sorted(node_types.items()):
        print(f"    {node_type}: {count}")
    
    # Check for isolated nodes (no edges)
    isolated = list(nx.isolates(G))
    if isolated:
        print(f"\nWARNING: {len(isolated)} isolated nodes: {isolated[:5]}...")
    
    # Check DAG properties
    if nx.is_directed_acyclic_graph(G):
        print("✓ Graph is a valid DAG")
    else:
        cycles = list(nx.simple_cycles(G))
        print(f"WARNING: Graph has {len(cycles)} cycles")
    
    # Check connectivity
    if nx.is_weakly_connected(G):
        print("✓ Graph is weakly connected")
    else:
        components = list(nx.weakly_connected_components(G))
        print(f"WARNING: Graph has {len(components)} disconnected components")

def save_graph(G, filename):
    """Save graph to pickle file"""
    with open(filename, 'wb') as f:
        pickle.dump(G, f)
    print(f"Graph saved to {filename}")

def load_graph(filename):
    """Load graph from pickle file"""
    with open(filename, 'rb') as f:
        return pickle.load(f)

def export_graph_summary(G, filename):
    """Export graph summary as JSON for inspection"""
    
    summary = {
        'meta': {
            'nodes': G.number_of_nodes(),
            'edges': G.number_of_edges(),
            'is_dag': nx.is_directed_acyclic_graph(G),
            'is_connected': nx.is_weakly_connected(G)
        },
        'nodes': []
    }
    
    for node_id, data in G.nodes(data=True):
        node_summary = {
            'id': node_id,
            'type': data['type'],
            'block': data['block'],
            'order_index': data['order_index'],
            'in_degree': G.in_degree(node_id),
            'out_degree': G.out_degree(node_id)
        }
        summary['nodes'].append(node_summary)
    
    # Sort by order_index
    summary['nodes'].sort(key=lambda x: x['order_index'])
    
    with open(filename, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"Graph summary exported to {filename}")

def main():
    """Main ingestion process"""
    print("HTOPS Survey NetworkX Graph Ingestion")
    print("=" * 45)
    
    # Check input file
    data_file = Path('data/htops_complete_nodes_minimal.json')
    if not data_file.exists():
        print(f"ERROR: {data_file} not found")
        return False
    
    # Load nodes into graph
    print(f"Loading nodes from {data_file}...")
    G = load_nodes_to_graph(data_file)
    
    # Add sequential edges
    print("Adding sequential flow edges...")
    G = add_sequential_edges(G)
    
    # Validate
    validate_graph(G)
    
    # Save graph
    graph_file = Path('data/htops_survey_graph.pkl')
    save_graph(G, graph_file)
    
    # Export summary
    summary_file = Path('data/htops_graph_summary.json')
    export_graph_summary(G, summary_file)
    
    print(f"\n✓ Successfully created NetworkX graph with {G.number_of_nodes()} nodes")
    print(f"✓ Graph saved as {graph_file}")
    print(f"✓ Summary exported as {summary_file}")
    
    return True

if __name__ == "__main__":
    main()
