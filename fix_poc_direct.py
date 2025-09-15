#!/usr/bin/env python3
"""
POC_display Quick Fix - Direct approach
"""
import sys
import pickle
import networkx as nx
from pathlib import Path

def main():
    print("POC_display DIRECT FIX")
    print("=" * 30)
    
    # Load database directly
    db_path = Path('/Users/brock/Documents/GitHub/survey-dag-extractor/surveys_db/current_database.pkl')
    
    with open(db_path, 'rb') as f:
        data = pickle.load(f)
    
    # Handle both graph and extractor objects
    if hasattr(data, 'graph'):
        graph = data.graph
    else:
        graph = data
    
    print(f"✅ Loaded: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    # Quick investigation of POC_display
    if graph.has_node('POC_display'):
        poc_data = graph.nodes['POC_display']
        poc_order = poc_data.get('order_index', 999)
        
        print(f"📋 POC_display order: {poc_order}")
        
        # Find predecessors by order
        candidates = []
        for node_id, node_data in graph.nodes(data=True):
            node_order = node_data.get('order_index', 999)
            if node_order < poc_order and node_order > poc_order - 5:
                successors = list(graph.successors(node_id))
                candidates.append((node_id, node_order, successors))
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        if candidates:
            prev_node = candidates[0][0]
            print(f"🔗 Connecting {prev_node} → POC_display")
            
            if not graph.has_edge(prev_node, 'POC_display'):
                edge_id = f"E_{graph.number_of_edges():08d}"
                graph.add_edge(prev_node, 'POC_display', 
                              id=edge_id, 
                              condition='always', 
                              edge_type='fallthrough')
                print(f"✅ Added edge")
                
                # Save back
                with open(db_path, 'wb') as f:
                    pickle.dump(data, f)  # Save the original data structure
                
                # Final check
                components = nx.number_weakly_connected_components(graph)
                isolated = list(nx.isolates(graph))
                
                all_nodes = list(graph.nodes())
                start_node = 'INTRO_INCENTIVE'
                reachable = set(nx.descendants(graph, start_node))
                reachable.add(start_node)
                unreachable = set(all_nodes) - reachable
                
                print(f"\n🎯 FINAL RESULT:")
                print(f"   Components: {components}")
                print(f"   Isolated: {len(isolated)}")
                print(f"   Unreachable: {len(unreachable)}")
                
                if len(unreachable) == 0 and components == 1 and len(isolated) == 0:
                    print(f"\n🏆 100% CONNECTIVITY ACHIEVED!")
                    print(f"   ✅ Phase 3B.3 COMPLETE!")
                    print(f"   ✅ Ready for Phase 4!")
                else:
                    print(f"   Remaining issues: {list(unreachable) if unreachable else 'none'}")
        else:
            print("❌ No predecessor candidates found")
    else:
        print("❌ POC_display not found")

if __name__ == "__main__":
    main()
