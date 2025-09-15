#!/usr/bin/env python3
"""
R2a Fix - Connect END terminal to R2a for ineligible completion
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from database_manager import DatabaseManager

def main():
    print("R2a FINAL CONNECTION FIX")
    print("=" * 40)
    
    db = DatabaseManager()
    db.create_snapshot("before_r2a_fix")
    
    graph = db.load_graph()
    
    print(f"Current: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    # The correct fix: END → R2a
    if graph.has_node('END') and graph.has_node('R2a'):
        if not graph.has_edge('END', 'R2a'):
            edge_id = f"E_{graph.number_of_edges():08d}"
            graph.add_edge('END', 'R2a', 
                          id=edge_id, 
                          condition='always', 
                          edge_type='terminate')
            print(f"✅ Added: END → R2a (ineligible completion path)")
            
            # Save the fix
            db.save_graph(graph)
            
            # Verify final connectivity
            import networkx as nx
            
            components = nx.number_weakly_connected_components(graph)
            isolated = list(nx.isolates(graph))
            
            # Check reachability from start
            all_nodes = list(graph.nodes())
            start_node = 'INTRO_INCENTIVE' if graph.has_node('INTRO_INCENTIVE') else 'Language'
            reachable = set(nx.descendants(graph, start_node))
            reachable.add(start_node)
            unreachable = set(all_nodes) - reachable
            
            print(f"\n🎯 FINAL VERIFICATION:")
            print(f"   Start: {start_node}")
            print(f"   Components: {components}")
            print(f"   Isolated: {len(isolated)}")
            print(f"   Reachable: {len(reachable)}/{len(all_nodes)}")
            print(f"   Unreachable: {len(unreachable)}")
            
            if len(unreachable) == 0 and components == 1 and len(isolated) == 0:
                print(f"\n🎉 SUCCESS! PERFECT CONNECTIVITY ACHIEVED!")
                print(f"   ✅ All nodes connected")
                print(f"   ✅ Single component") 
                print(f"   ✅ No isolated nodes")
                print(f"   ✅ Ready for Phase 4!")
                
                db.create_snapshot("perfect_connectivity")
            else:
                print(f"\n⚠️  Still have issues:")
                if unreachable:
                    print(f"   Unreachable: {list(unreachable)}")
                if isolated:
                    print(f"   Isolated: {isolated}")
                if components > 1:
                    print(f"   Components: {components}")
        else:
            print(f"✅ END → R2a connection already exists")
    else:
        print(f"❌ END or R2a nodes not found")
    
    print(f"\n" + "=" * 40)
    print("R2a FIX COMPLETE")

if __name__ == "__main__":
    main()
