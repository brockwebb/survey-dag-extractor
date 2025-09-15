#!/usr/bin/env python3
"""
POC_display Investigation & Fix - Final unreachable node
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from database_manager import DatabaseManager

def main():
    print("POC_display FINAL FIX")
    print("=" * 30)
    
    db = DatabaseManager()
    graph = db.load_graph()
    
    # Investigate POC_display
    if graph.has_node('POC_display'):
        poc_data = graph.nodes['POC_display']
        print(f"📋 POC_display:")
        print(f"   Type: {poc_data.get('type', 'unknown')}")
        print(f"   Order: {poc_data.get('order_index', 'N/A')}")
        print(f"   Text: {poc_data.get('text', '')[:60]}...")
        
        # Check connections
        predecessors = list(graph.predecessors('POC_display'))
        successors = list(graph.successors('POC_display'))
        
        print(f"   In-edges: {len(predecessors)} {predecessors}")
        print(f"   Out-edges: {len(successors)} {successors}")
        
        # Find what should connect to POC_display
        # POC_display is "contact information" - should come at end of survey
        print(f"\n🔍 SEARCHING FOR NODES THAT SHOULD CONNECT TO POC_display:")
        
        # Check nodes around order index 121 (POC_display is 121)
        poc_order = poc_data.get('order_index', 999)
        candidates = []
        
        for node_id, node_data in graph.nodes(data=True):
            node_order = node_data.get('order_index', 999)
            if node_order < poc_order and node_order > poc_order - 10:
                candidates.append((node_id, node_order, node_data.get('type', 'unknown')))
        
        # Sort by order
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        print(f"   Candidates (nodes just before POC_display):")
        for node_id, order, node_type in candidates[:5]:
            successors = list(graph.successors(node_id))
            print(f"     {node_id} (order {order}, {node_type}) → {successors}")
        
        # Apply the fix - connect the node just before POC_display
        if candidates:
            # Get the highest order node before POC_display
            prev_node = candidates[0][0]
            
            print(f"\n🔧 APPLYING FIX:")
            print(f"   Connecting {prev_node} → POC_display")
            
            if not graph.has_edge(prev_node, 'POC_display'):
                edge_id = f"E_{graph.number_of_edges():08d}"
                graph.add_edge(prev_node, 'POC_display', 
                              id=edge_id, 
                              condition='always', 
                              edge_type='fallthrough')
                print(f"   ✅ Added: {prev_node} → POC_display")
                
                # Save and verify
                db.save_graph(graph)
                
                # Final verification
                import networkx as nx
                components = nx.number_weakly_connected_components(graph)
                isolated = list(nx.isolates(graph))
                
                all_nodes = list(graph.nodes())
                start_node = 'INTRO_INCENTIVE'
                reachable = set(nx.descendants(graph, start_node))
                reachable.add(start_node)
                unreachable = set(all_nodes) - reachable
                
                print(f"\n🎉 ULTIMATE VERIFICATION:")
                print(f"   Components: {components}")
                print(f"   Isolated: {len(isolated)}")
                print(f"   Reachable: {len(reachable)}/{len(all_nodes)}")
                print(f"   Unreachable: {len(unreachable)}")
                
                if len(unreachable) == 0 and components == 1 and len(isolated) == 0:
                    print(f"\n🏆 PERFECT CONNECTIVITY ACHIEVED!")
                    print(f"   ✅ 100% COMPLETE!")
                    print(f"   ✅ Ready for Phase 4!")
                    
                    db.create_snapshot("100_percent_connectivity")
                else:
                    print(f"\n❌ Still have: unreachable={list(unreachable)}, isolated={isolated}")
            else:
                print(f"   Connection already exists")
    
    print(f"\n" + "=" * 30)

if __name__ == "__main__":
    main()
