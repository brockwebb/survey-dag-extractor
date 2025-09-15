#!/usr/bin/env python3
"""
Quick test of the fixed database manager
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from database_manager import DatabaseManager

def main():
    print("TESTING FIXED DATABASE MANAGER")
    print("=" * 40)
    
    db = DatabaseManager()
    
    try:
        graph = db.load_graph()
        print(f"✅ SUCCESS!")
        print(f"   Graph loaded with {graph.number_of_nodes()} nodes")
        print(f"   Graph has {graph.number_of_edges()} edges")
        
        # Now run connectivity check
        import networkx as nx
        
        # Check connectivity
        components = nx.number_weakly_connected_components(graph)
        isolated = list(nx.isolates(graph))
        
        print(f"📊 Components: {components}")
        print(f"📊 Isolated: {len(isolated)}")
        
        if isolated:
            print(f"   Isolated nodes: {isolated}")
        
        # Find unreachable nodes from start
        all_nodes = list(graph.nodes())
        question_nodes = [(n, graph.nodes[n].get('order_index', 999)) 
                         for n in all_nodes 
                         if graph.nodes[n].get('type') == 'question']
        
        if question_nodes:
            start_node = min(question_nodes, key=lambda x: x[1])[0]
            reachable = set(nx.descendants(graph, start_node))
            reachable.add(start_node)
            
            unreachable = set(all_nodes) - reachable
            
            print(f"🎯 Start: {start_node}")
            print(f"🎯 Reachable: {len(reachable)}/{len(all_nodes)}")
            print(f"🎯 Unreachable: {len(unreachable)}")
            
            if unreachable:
                print("🎯 ROGUE NODES FOUND:")
                for node_id in list(unreachable)[:3]:
                    node_data = graph.nodes[node_id]
                    print(f"   {node_id}: {node_data.get('type', 'unknown')}, order {node_data.get('order_index', 'N/A')}")
            else:
                print("🎉 All nodes are reachable!")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
