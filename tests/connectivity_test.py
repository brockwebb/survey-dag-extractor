#!/usr/bin/env python3
"""
Connectivity Test - Check for final unreachable node
"""
import pickle
import networkx as nx
from pathlib import Path

def main():
    print("CONNECTIVITY TEST - HUNTING ROGUE NODE")
    print("=" * 50)
    
    # Load the database
    db_path = Path('surveys_db/current_database.pkl')
    try:
        with open(db_path, 'rb') as f:
            extractor = pickle.load(f)
        print(f"✅ Database loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load database: {e}")
        return
    
    graph = extractor.graph
    print(f"📊 Database: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    # Check connectivity
    components = nx.number_weakly_connected_components(graph)
    isolated = list(nx.isolates(graph))
    
    print(f"📊 Components: {components}")
    print(f"📊 Isolated: {len(isolated)}")
    
    if isolated:
        print(f"   Isolated nodes: {isolated}")
        for node_id in isolated:
            node_data = next((n for n in extractor.nodes if n['id'] == node_id), {})
            print(f"     {node_id}: {node_data.get('type', 'unknown')}")
    
    # Find unreachable nodes
    questions = [(n['id'], n.get('order_index', 999)) for n in extractor.nodes if n['type'] == 'question']
    if questions:
        start_node = min(questions, key=lambda x: x[1])[0]
        reachable = set(nx.descendants(graph, start_node))
        reachable.add(start_node)
        
        all_nodes = set(graph.nodes())
        unreachable = all_nodes - reachable
        
        print(f"🎯 Start: {start_node}")
        print(f"🎯 Reachable: {len(reachable)}/{len(all_nodes)}")
        print(f"🎯 Unreachable: {len(unreachable)}")
        
        if unreachable:
            print("❗ ROGUE NODES FOUND:")
            for node_id in list(unreachable):
                node_data = next((n for n in extractor.nodes if n['id'] == node_id), {})
                node_type = node_data.get('type', 'unknown')
                order_idx = node_data.get('order_index', 'N/A')
                text = node_data.get('text', '')[:60]
                
                print(f"   🔍 {node_id}")
                print(f"      Type: {node_type}")
                print(f"      Order: {order_idx}")
                print(f"      Text: {text}...")
                
                # Check connections
                predecessors = list(graph.predecessors(node_id))
                successors = list(graph.successors(node_id))
                print(f"      In: {predecessors}")
                print(f"      Out: {successors}")
                print()
                
                # Suggest fix based on type and context
                if node_type == 'question':
                    print(f"      💡 FIX: Connect from previous question in sequence")
                elif node_type == 'instruction':
                    print(f"      💡 FIX: Connect to next question in same block")
                elif node_type in ['terminal', 'ultimate_terminal']:
                    print(f"      💡 FIX: Connect from completion path")
                print()
        
        # Summary
        if unreachable:
            print(f"🚨 ACTION NEEDED: {len(unreachable)} nodes need connectivity fixes")
            print("Run: python hunt_final_node.py")
        else:
            print("🎉 SUCCESS: All nodes are reachable!")
            print("Graph is ready for final validation!")
    
    print(f"\n💾 Database: {db_path}")

if __name__ == "__main__":
    main()
