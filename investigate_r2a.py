#!/usr/bin/env python3
"""
R2a Investigation - Why is this terminal isolated?
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from database_manager import DatabaseManager

def main():
    print("R2a ISOLATION INVESTIGATION")
    print("=" * 40)
    
    db = DatabaseManager()
    graph = db.load_graph()
    
    # Focus on R2a
    print(f"🔍 ANALYZING R2a:")
    
    if graph.has_node('R2a'):
        r2a_data = graph.nodes['R2a']
        print(f"   Type: {r2a_data.get('type', 'unknown')}")
        print(f"   Order: {r2a_data.get('order_index', 'N/A')}")
        print(f"   Text: {r2a_data.get('text', '')[:50]}...")
        
        # Check connections
        predecessors = list(graph.predecessors('R2a'))
        successors = list(graph.successors('R2a'))
        
        print(f"   In-edges: {len(predecessors)} {predecessors}")
        print(f"   Out-edges: {len(successors)} {successors}")
        
        if len(predecessors) == 0:
            print(f"   🚨 R2a is isolated - no incoming edges!")
            
            # Look for nodes that should connect to R2a
            print(f"\n🔍 SEARCHING FOR EXIT DECISION POINTS:")
            
            # Check GET_NAME specifically
            if graph.has_node('GET_NAME'):
                get_name_data = graph.nodes['GET_NAME']
                get_name_successors = list(graph.successors('GET_NAME'))
                print(f"   GET_NAME → {get_name_successors}")
                print(f"   GET_NAME text: {get_name_data.get('text', '')[:100]}...")
                
                # Check if there's an END node it connects to instead
                for succ in get_name_successors:
                    succ_data = graph.nodes[succ]
                    if succ_data.get('type') == 'terminal':
                        print(f"   GET_NAME connects to terminal: {succ}")
                        print(f"   {succ} text: {succ_data.get('text', '')[:50]}...")
            
            # Look for any node with "end survey" or similar logic
            print(f"\n🔍 SEARCHING FOR 'END SURVEY' LOGIC:")
            for node_id, node_data in graph.nodes(data=True):
                node_text = node_data.get('text', '').lower()
                if 'end survey' in node_text or 'exit' in node_text:
                    successors = list(graph.successors(node_id))
                    print(f"   {node_id} (contains exit logic) → {successors}")
                    print(f"     Text: {node_data.get('text', '')[:70]}...")
        
        # Check what universe condition R2a has
        universe = r2a_data.get('universe', {})
        if universe:
            print(f"\n📋 R2a Universe Condition:")
            print(f"   Expression: {universe.get('expression', 'none')}")
            print(f"   Dependencies: {universe.get('dependencies', [])}")
    
    else:
        print(f"❌ R2a node not found in graph!")
    
    print(f"\n" + "=" * 40)

if __name__ == "__main__":
    main()
