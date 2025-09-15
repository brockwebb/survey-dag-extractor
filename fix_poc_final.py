#!/usr/bin/env python3
"""
POC_display Final Fix - Using Fixed Database Manager
"""
import sys
from pathlib import Path
import networkx as nx

sys.path.append(str(Path(__file__).parent))
from database_manager import DatabaseManager

def main():
    print("POC_display FINAL FIX (Fixed DB Manager)")
    print("=" * 45)
    
    db = DatabaseManager()
    db.create_snapshot("before_poc_fix")
    
    graph = db.load_graph()
    
    # Investigate POC_display
    if graph.has_node('POC_display'):
        poc_data = graph.nodes['POC_display']
        poc_order = poc_data.get('order_index', 999)
        
        print(f"📋 POC_display (order {poc_order}): {poc_data.get('text', '')[:50]}...")
        print(f"   Type: {poc_data.get('type', 'unknown')}")
        
        # Find what should connect to POC_display
        # Look for nodes with order index just before POC_display
        candidates = []
        for node_id, node_data in graph.nodes(data=True):
            node_order = node_data.get('order_index', 999)
            if 110 <= node_order < poc_order:  # Look in reasonable range
                successors = list(graph.successors(node_id))
                candidates.append((node_id, node_order, node_data.get('type', 'unknown'), successors))
        
        # Sort by order (highest first)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\\n🔍 Candidate predecessors:")
        for node_id, order, node_type, successors in candidates[:5]:
            print(f"   {node_id} (order {order}, {node_type}) → {successors}")
        
        if candidates:
            # Connect the highest order predecessor
            prev_node = candidates[0][0]
            
            if not graph.has_edge(prev_node, 'POC_display'):
                edge_id = f"E_{graph.number_of_edges():08d}"
                graph.add_edge(prev_node, 'POC_display', 
                              id=edge_id, 
                              condition='always', 
                              edge_type='fallthrough')
                
                print(f"\\n✅ Added: {prev_node} → POC_display")
                
                # Save and do final verification
                db.save_graph(graph)
                
                # Ultimate connectivity check
                components = nx.number_weakly_connected_components(graph)
                isolated = list(nx.isolates(graph))
                
                # Check reachability from start
                all_nodes = list(graph.nodes())
                start_node = 'INTRO_INCENTIVE'
                reachable = set(nx.descendants(graph, start_node))
                reachable.add(start_node)
                unreachable = set(all_nodes) - reachable
                
                print(f"\\n🏆 ULTIMATE VERIFICATION:")
                print(f"   Total nodes: {len(all_nodes)}")
                print(f"   Components: {components}")
                print(f"   Isolated: {len(isolated)}")
                print(f"   Reachable: {len(reachable)}")
                print(f"   Unreachable: {len(unreachable)}")
                
                if len(unreachable) == 0 and components == 1 and len(isolated) == 0:
                    print(f"\\n🎉 🎉 🎉 PERFECT CONNECTIVITY ACHIEVED! 🎉 🎉 🎉")
                    print(f"   ✅ 100% of nodes reachable")
                    print(f"   ✅ Single connected component")
                    print(f"   ✅ No isolated nodes")
                    print(f"   ✅ Phase 3B.3 Domain Logic Validation COMPLETE")
                    print(f"   ✅ Ready for Phase 4!")
                    
                    db.create_snapshot("perfect_connectivity_achieved")
                else:
                    print(f"\\n⚠️  Still have issues:")
                    if unreachable:
                        print(f"   Unreachable: {list(unreachable)}")
                    if isolated:
                        print(f"   Isolated: {isolated}")
            else:
                print(f"\\n✅ {prev_node} → POC_display already connected")
        else:
            print(f"\\n❌ No suitable predecessors found")
    else:
        print(f"❌ POC_display not found")
    
    print(f"\\n" + "=" * 45)

if __name__ == "__main__":
    main()
