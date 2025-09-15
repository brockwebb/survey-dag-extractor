#!/usr/bin/env python3
"""
Final Node Fixer - Targeted fixes for the 5 unreachable nodes
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from database_manager import DatabaseManager

def main():
    print("FINAL NODE FIXER - TARGETED REPAIR")
    print("=" * 50)
    
    db = DatabaseManager()
    
    # Create checkpoint
    db.create_snapshot("before_final_fix")
    
    try:
        graph = db.load_graph()
        print(f"✅ Loaded: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    except Exception as e:
        print(f"❌ Failed to load: {e}")
        return
    
    # Apply targeted fixes
    fixes_applied = 0
    
    print(f"\n🔧 APPLYING TARGETED FIXES:")
    print("=" * 40)
    
    # Fix 1: Connect the intro sequence
    if graph.has_node('INTRO_INCENTIVE') and graph.has_node('Continue'):
        if not graph.has_edge('INTRO_INCENTIVE', 'Continue'):
            edge_id = f"E_{graph.number_of_edges():08d}"
            graph.add_edge('INTRO_INCENTIVE', 'Continue', 
                          id=edge_id, condition='always', edge_type='fallthrough')
            print(f"✅ Fix 1: INTRO_INCENTIVE → Continue")
            fixes_applied += 1
    
    # Fix 2: Connect Continue to PRA
    if graph.has_node('Continue') and graph.has_node('PRA'):
        if not graph.has_edge('Continue', 'PRA'):
            edge_id = f"E_{graph.number_of_edges():08d}"
            graph.add_edge('Continue', 'PRA', 
                          id=edge_id, condition='always', edge_type='fallthrough')
            print(f"✅ Fix 2: Continue → PRA")
            fixes_applied += 1
    
    # Fix 3: Connect PRA to Language (current start)
    if graph.has_node('PRA') and graph.has_node('Language'):
        if not graph.has_edge('PRA', 'Language'):
            edge_id = f"E_{graph.number_of_edges():08d}"
            graph.add_edge('PRA', 'Language', 
                          id=edge_id, condition='always', edge_type='fallthrough')
            print(f"✅ Fix 3: PRA → Language")
            fixes_applied += 1
    
    # Fix 4: Connect R2a terminal (ineligible users)
    # R2a should be reachable from GET_NAME when user selects "End survey"
    if graph.has_node('GET_NAME') and graph.has_node('R2a'):
        # Check if there's already a connection to END
        has_end_connection = False
        for target in graph.successors('GET_NAME'):
            if graph.nodes[target].get('type') == 'terminal':
                has_end_connection = True
                break
        
        if not has_end_connection:
            edge_id = f"E_{graph.number_of_edges():08d}"
            graph.add_edge('GET_NAME', 'R2a', 
                          id=edge_id, condition='== 2', edge_type='terminate')
            print(f"✅ Fix 4: GET_NAME → R2a (end survey path)")
            fixes_applied += 1
    
    # Fix 5: Check for any other isolated nodes and connect them
    import networkx as nx
    isolated = list(nx.isolates(graph))
    if isolated:
        print(f"⚠️  Still isolated after fixes: {isolated}")
    
    # Save fixes
    if fixes_applied > 0:
        db.save_graph(graph)
        print(f"\n💾 Saved {fixes_applied} fixes to database")
        
        # Verify the fixes
        print(f"\n🔍 VERIFICATION:")
        print("=" * 40)
        
        components = nx.number_weakly_connected_components(graph)
        isolated = list(nx.isolates(graph))
        
        # Check reachability from new start
        all_nodes = list(graph.nodes())
        if graph.has_node('INTRO_INCENTIVE'):
            start_node = 'INTRO_INCENTIVE'
        else:
            question_nodes = [(n, graph.nodes[n].get('order_index', 999)) 
                             for n in all_nodes 
                             if graph.nodes[n].get('type') == 'question']
            start_node = min(question_nodes, key=lambda x: x[1])[0] if question_nodes else None
        
        if start_node:
            reachable = set(nx.descendants(graph, start_node))
            reachable.add(start_node)
            unreachable = set(all_nodes) - reachable
            
            print(f"📊 New start: {start_node}")
            print(f"📊 Components: {components}")
            print(f"📊 Isolated: {len(isolated)}")
            print(f"📊 Reachable: {len(reachable)}/{len(all_nodes)}")
            print(f"📊 Unreachable: {len(unreachable)}")
            
            if len(unreachable) == 0 and components == 1:
                print(f"\n🎉 SUCCESS! All nodes connected!")
                print(f"Graph is ready for final validation!")
                db.create_snapshot("fully_connected")
            else:
                print(f"\n⚠️  Still need work:")
                if unreachable:
                    print(f"   Unreachable: {list(unreachable)[:5]}")
                if components > 1:
                    print(f"   Multiple components: {components}")
    else:
        print(f"\n⚠️  No fixes could be applied")
    
    print(f"\n" + "=" * 50)
    print("FINAL NODE FIXER COMPLETE")

if __name__ == "__main__":
    main()
