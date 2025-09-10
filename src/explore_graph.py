#!/usr/bin/env python3
"""
NetworkX Graph Explorer for HTOPS Survey
Interactive tool to explore and validate survey DAG
"""

import pickle
import networkx as nx
import json
from pathlib import Path

def load_survey_graph():
    """Load the survey graph from pickle file"""
    graph_file = Path('data/htops_survey_graph.pkl')
    if not graph_file.exists():
        print("ERROR: Graph file not found. Run create_networkx_graph.py first.")
        return None
    
    with open(graph_file, 'rb') as f:
        return pickle.load(f)

def graph_summary(G):
    """Display graph summary statistics"""
    print("HTOPS Survey Graph Summary")
    print("=" * 40)
    print(f"Nodes: {G.number_of_nodes()}")
    print(f"Edges: {G.number_of_edges()}")
    print(f"Is DAG: {nx.is_directed_acyclic_graph(G)}")
    print(f"Is Connected: {nx.is_weakly_connected(G)}")
    
    # Node types
    node_types = {}
    for _, data in G.nodes(data=True):
        node_type = data['type']
        node_types[node_type] = node_types.get(node_type, 0) + 1
    
    print("\nNode Types:")
    for node_type, count in sorted(node_types.items()):
        print(f"  {node_type}: {count}")
    
    # Blocks
    blocks = {}
    for _, data in G.nodes(data=True):
        block = data['block']
        blocks[block] = blocks.get(block, 0) + 1
    
    print("\nBlocks:")
    for block, count in sorted(blocks.items()):
        print(f"  {block}: {count}")

def show_node_details(G, node_id):
    """Show detailed information about a specific node"""
    if node_id not in G:
        print(f"Node '{node_id}' not found")
        return
    
    data = G.nodes[node_id]
    print(f"\nNode: {node_id}")
    print("-" * 40)
    print(f"Type: {data['type']}")
    print(f"Block: {data['block']}")
    print(f"Order Index: {data['order_index']}")
    print(f"In Degree: {G.in_degree(node_id)}")
    print(f"Out Degree: {G.out_degree(node_id)}")
    
    # Predecessors and successors
    preds = list(G.predecessors(node_id))
    succs = list(G.successors(node_id))
    
    if preds:
        print(f"Predecessors: {', '.join(preds)}")
    if succs:
        print(f"Successors: {', '.join(succs)}")
    
    # Text preview
    text = data['text']
    if len(text) > 100:
        text = text[:100] + "..."
    print(f"Text: {text}")

def show_survey_flow(G, limit=20):
    """Show survey flow in order"""
    nodes_by_order = sorted(G.nodes(data=True), key=lambda x: x[1]['order_index'])
    
    print(f"\nSurvey Flow (first {limit} nodes):")
    print("-" * 70)
    print("Idx  Node ID         Type        Block")
    print("-" * 70)
    
    for i, (node_id, data) in enumerate(nodes_by_order[:limit]):
        print(f"{data['order_index']:3d}. {node_id:15} {data['type']:11} {data['block']}")

def show_block_nodes(G, block_name):
    """Show all nodes in a specific block"""
    block_nodes = [(node_id, data) for node_id, data in G.nodes(data=True) 
                   if data['block'] == block_name]
    
    if not block_nodes:
        print(f"No nodes found in block: {block_name}")
        return
    
    # Sort by order_index
    block_nodes.sort(key=lambda x: x[1]['order_index'])
    
    print(f"\nBlock: {block_name} ({len(block_nodes)} nodes)")
    print("-" * 60)
    
    for node_id, data in block_nodes:
        print(f"{data['order_index']:3d}. {node_id:15} [{data['type']:11}]")

def find_paths(G, start_node, end_node):
    """Find all paths between two nodes"""
    try:
        paths = list(nx.all_simple_paths(G, start_node, end_node))
        if paths:
            print(f"\nPaths from {start_node} to {end_node}:")
            for i, path in enumerate(paths[:5], 1):  # Show first 5 paths
                print(f"  Path {i}: {' -> '.join(path)}")
            if len(paths) > 5:
                print(f"  ... and {len(paths) - 5} more paths")
        else:
            print(f"No path found from {start_node} to {end_node}")
    except nx.NetworkXNoPath:
        print(f"No path exists from {start_node} to {end_node}")
    except nx.NodeNotFound as e:
        print(f"Node not found: {e}")

def export_for_visualization(G, filename):
    """Export graph in format suitable for D3.js visualization"""
    
    # Create nodes array
    nodes = []
    for node_id, data in G.nodes(data=True):
        nodes.append({
            'id': node_id,
            'type': data['type'],
            'block': data['block'],
            'order_index': data['order_index'],
            'text': data['text'][:100] + '...' if len(data['text']) > 100 else data['text']
        })
    
    # Create edges array
    edges = []
    for source, target, data in G.edges(data=True):
        edges.append({
            'source': source,
            'target': target,
            'type': data.get('edge_type', 'sequential')
        })
    
    # Export
    export_data = {
        'nodes': nodes,
        'edges': edges,
        'meta': {
            'node_count': G.number_of_nodes(),
            'edge_count': G.number_of_edges(),
            'is_dag': nx.is_directed_acyclic_graph(G)
        }
    }
    
    with open(filename, 'w') as f:
        json.dump(export_data, f, indent=2)
    print(f"Graph exported for D3.js visualization: {filename}")

def interactive_mode(G):
    """Interactive exploration mode"""
    print("\nInteractive Mode (type 'help' for commands)")
    
    while True:
        try:
            cmd = input("\n> ").strip()
            
            if cmd.lower() in ['quit', 'exit']:
                break
            elif cmd == 'help':
                print("\nCommands:")
                print("  summary           - Show graph summary")
                print("  flow [N]          - Show survey flow (first N nodes)")
                print("  node <id>         - Show node details")
                print("  block <name>      - Show all nodes in block")
                print("  path <from> <to>  - Find paths between nodes")
                print("  export <file>     - Export for D3.js visualization")
                print("  quit              - Exit")
            elif cmd == 'summary':
                graph_summary(G)
            elif cmd.startswith('flow'):
                parts = cmd.split()
                limit = int(parts[1]) if len(parts) > 1 else 20
                show_survey_flow(G, limit)
            elif cmd.startswith('node '):
                node_id = cmd[5:].strip()
                show_node_details(G, node_id)
            elif cmd.startswith('block '):
                block_name = cmd[6:].strip()
                show_block_nodes(G, block_name)
            elif cmd.startswith('path '):
                parts = cmd[5:].split()
                if len(parts) >= 2:
                    find_paths(G, parts[0], parts[1])
                else:
                    print("Usage: path <from_node> <to_node>")
            elif cmd.startswith('export '):
                filename = cmd[7:].strip()
                export_for_visualization(G, filename)
            else:
                print("Unknown command. Type 'help' for available commands.")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

def main():
    """Main exploration interface"""
    G = load_survey_graph()
    if not G:
        return
    
    graph_summary(G)
    show_survey_flow(G, 10)
    
    try:
        response = input("\nEnter interactive mode? (y/n): ")
        if response.lower().startswith('y'):
            interactive_mode(G)
    except KeyboardInterrupt:
        pass
    
    print("\nDone.")

if __name__ == "__main__":
    main()
