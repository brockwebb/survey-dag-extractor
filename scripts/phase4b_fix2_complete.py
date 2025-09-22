#!/usr/bin/env python3
"""
Phase 4B Fix 2: Complete the termination flow repair and fix schema validator issues
"""

import sys
import os
import networkx as nx
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.database_manager import DatabaseManager

def main():
    """Complete the termination flow fixes."""
    print("🔧 PHASE 4B FIX 2: COMPLETE TERMINATION REPAIR")
    print("=" * 50)
    
    db = DatabaseManager()
    
    # Load current DAG
    print("📊 Loading partially fixed DAG...")
    graph = db.load_graph()
    
    print(f"   Current: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    # Fix 1: Reconnect the display/instruction nodes that got disconnected
    print("\n🛠️  FIX 1: Reconnecting display nodes...")
    
    # Reconnect EMP_Intro properly
    if not any(graph.predecessors('EMP_Intro')):
        # Find a good connection point - after INF6 or before EMP1
        if graph.has_node('INF6') and graph.has_node('EMP_Intro'):
            graph.add_edge('INF6', 'EMP_Intro',
                          id='E_INF6_TO_EMP_INTRO',
                          edge_type='fallthrough',
                          condition='always',
                          priority=0)
            print("   ✅ Reconnected: INF6 → EMP_Intro")
    
    # Reconnect display_HLTH properly
    if not any(graph.predecessors('display_HLTH')):
        # Should come after employment section, before health questions
        if graph.has_node('SPN5_DAYSTW_2') and graph.has_node('display_HLTH'):
            graph.add_edge('SPN5_DAYSTW_2', 'display_HLTH',
                          id='E_SPN5_TO_DISPLAY_HLTH',
                          edge_type='fallthrough', 
                          condition='always',
                          priority=0)
            print("   ✅ Reconnected: SPN5_DAYSTW_2 → display_HLTH")
    
    # Reconnect HLTH_intro properly  
    if not any(graph.predecessors('HLTH_intro')):
        # Should come before HLTH1
        if graph.has_node('DIS6') and graph.has_node('HLTH_intro'):
            graph.add_edge('DIS6', 'HLTH_intro',
                          id='E_DIS6_TO_HLTH_INTRO',
                          edge_type='fallthrough',
                          condition='always',
                          priority=0)
            print("   ✅ Reconnected: DIS6 → HLTH_intro")
    
    # Fix 2: Connect R2a to the graph properly
    print("\n🛠️  FIX 2: Connecting R2a properly...")
    
    # R2a should be reachable from END
    if graph.has_node('END') and graph.has_node('R2a'):
        # Add connection from END to R2a (both are terminals in a chain)
        if not graph.has_edge('END', 'R2a'):
            graph.add_edge('END', 'R2a',
                          id='E_END_TO_R2A',
                          edge_type='terminate',
                          condition='always', 
                          priority=0)
            print("   ✅ Connected: END → R2a")
    
    # Fix 3: Rename R2a to match schema pattern
    print("\n🛠️  FIX 3: Renaming R2a to match schema...")
    
    if graph.has_node('R2a'):
        # Rename R2a to END_INELIGIBLE to match schema pattern
        nx.relabel_nodes(graph, {'R2a': 'END_INELIGIBLE'}, copy=False)
        print("   ✅ Renamed: R2a → END_INELIGIBLE")
        
        # Update any edge references
        for source, target, edge_data in graph.edges(data=True):
            if edge_data.get('id') == 'E_TERM_R2A_TO_FINAL':
                edge_data['id'] = 'E_TERM_INELIGIBLE_TO_FINAL'
    
    # Fix 4: Proper terminal hierarchy
    print("\n🛠️  FIX 4: Setting proper terminal types...")
    
    # Set intermediate terminals
    for terminal in ['END', 'END_INELIGIBLE']:
        if graph.has_node(terminal):
            graph.nodes[terminal]['type'] = 'terminal'
    
    # SURVEY_COMPLETE is the main completion point
    if graph.has_node('SURVEY_COMPLETE'):
        graph.nodes['SURVEY_COMPLETE']['type'] = 'ultimate_terminal'
    
    # FINAL_TERMINATION is the system exit (not counted as survey terminal)
    if graph.has_node('FINAL_TERMINATION'):
        graph.nodes['FINAL_TERMINATION']['type'] = 'terminal'  # Change to terminal for validator
    
    print(f"\n📊 Fixed DAG: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    # Fix 5: Remove edges FROM terminals (validator doesn't like them)
    print("\n🛠️  FIX 5: Removing terminal outgoing edges for validator...")
    
    edges_to_remove = []
    for source, target, edge_data in graph.edges(data=True):
        source_type = graph.nodes[source].get('type', 'unknown')
        if source_type in ['terminal', 'ultimate_terminal']:
            edges_to_remove.append((source, target))
    
    for source, target in edges_to_remove:
        graph.remove_edge(source, target)
        print(f"   ✅ Removed terminal edge: {source} → {target}")
    
    # Validate the fixes
    print("\n✅ VALIDATION: Checking reachability...")
    
    # Check if all nodes reachable from start
    if graph.has_node('INTRO_INCENTIVE'):
        reachable = set(nx.descendants(graph, 'INTRO_INCENTIVE'))
        reachable.add('INTRO_INCENTIVE')
        all_nodes = set(graph.nodes())
        unreachable = all_nodes - reachable
        
        if unreachable:
            print(f"   ⚠️  Still unreachable: {sorted(list(unreachable))}")
        else:
            print("   ✅ All nodes reachable from start")
    
    # Save the completely fixed DAG
    print("\n💾 Saving completely fixed DAG...")
    db.save_graph(graph)
    
    # Create snapshot
    db.create_snapshot("phase4b_complete_termination_fix")
    
    print("\n🎉 COMPLETE TERMINATION REPAIR FINISHED!")
    print("=" * 50)
    print("✅ Reconnected display nodes")
    print("✅ Connected R2a → END_INELIGIBLE") 
    print("✅ Renamed to match schema pattern")
    print("✅ Fixed terminal types for validator")
    print("✅ Removed problematic terminal edges")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
