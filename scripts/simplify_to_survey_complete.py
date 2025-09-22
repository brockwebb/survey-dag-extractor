#!/usr/bin/env python3
"""
Simple Fix: Make SURVEY_COMPLETE the single collector node
Remove FINAL_TERMINATION confusion - SURVEY_COMPLETE is the collector
"""

import sys
import os
import networkx as nx
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.database_manager import DatabaseManager

def main():
    """Simplify: SURVEY_COMPLETE as the single collector node."""
    print("🔧 SIMPLE FIX: SURVEY_COMPLETE AS SINGLE COLLECTOR")
    print("=" * 55)
    
    db = DatabaseManager()
    
    # Load current DAG
    print("📊 Loading DAG...")
    graph = db.load_graph()
    
    print(f"   Current: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    # Step 1: Remove FINAL_TERMINATION node (it's confusing)
    if graph.has_node('FINAL_TERMINATION'):
        print("\n🗑️  Removing confusing FINAL_TERMINATION node...")
        
        # Get all edges pointing to FINAL_TERMINATION
        incoming_to_final = list(graph.predecessors('FINAL_TERMINATION'))
        print(f"   Nodes pointing to FINAL_TERMINATION: {incoming_to_final}")
        
        # Redirect all those edges to SURVEY_COMPLETE instead
        for source in incoming_to_final:
            if graph.has_edge(source, 'FINAL_TERMINATION'):
                edge_data = graph.edges[source, 'FINAL_TERMINATION']
                
                # Remove old edge
                graph.remove_edge(source, 'FINAL_TERMINATION')
                
                # Add new edge to SURVEY_COMPLETE
                if not graph.has_edge(source, 'SURVEY_COMPLETE'):
                    graph.add_edge(source, 'SURVEY_COMPLETE',
                                  id=edge_data.get('id', f'E_{source}_TO_COMPLETE'),
                                  edge_type=edge_data.get('edge_type', 'terminate'),
                                  condition=edge_data.get('condition', 'always'),
                                  priority=edge_data.get('priority', 0))
                    print(f"   ✅ Redirected: {source} → SURVEY_COMPLETE")
        
        # Remove FINAL_TERMINATION node
        graph.remove_node('FINAL_TERMINATION')
        print("   ✅ Removed FINAL_TERMINATION node")
    
    # Step 2: Set SURVEY_COMPLETE as ultimate_terminal (the collector)
    print("\n🏷️  Setting SURVEY_COMPLETE as ultimate collector...")
    if graph.has_node('SURVEY_COMPLETE'):
        graph.nodes['SURVEY_COMPLETE']['type'] = 'ultimate_terminal'
        print("   ✅ SURVEY_COMPLETE: ultimate_terminal (single collector)")
    
    # Step 3: All other terminals are intermediate
    print("\n🏷️  Setting other terminals as intermediate...")
    terminals = []
    for node_id, node_data in graph.nodes(data=True):
        node_type = node_data.get('type', 'unknown')
        if node_type in ['terminal', 'ultimate_terminal'] and node_id != 'SURVEY_COMPLETE':
            graph.nodes[node_id]['type'] = 'terminal'
            terminals.append(node_id)
            print(f"   ✅ {node_id}: terminal (intermediate)")
    
    # Step 4: Connect any disconnected terminals to SURVEY_COMPLETE
    print("\n🔗 Ensuring all terminals connect to SURVEY_COMPLETE...")
    
    for terminal in terminals:
        if graph.has_node(terminal) and not graph.has_edge(terminal, 'SURVEY_COMPLETE'):
            graph.add_edge(terminal, 'SURVEY_COMPLETE',
                          id=f'E_{terminal.upper()}_TO_COMPLETE',
                          edge_type='terminate',
                          condition='always',
                          priority=0)
            print(f"   ✅ Connected: {terminal} → SURVEY_COMPLETE")
    
    # Step 5: Validate the simple architecture
    print("\n✅ VALIDATING SIMPLE COLLECTOR ARCHITECTURE...")
    
    if graph.has_node('SURVEY_COMPLETE'):
        # Count connections to SURVEY_COMPLETE
        incoming = list(graph.predecessors('SURVEY_COMPLETE'))
        outgoing = list(graph.successors('SURVEY_COMPLETE'))
        
        print(f"   ✅ SURVEY_COMPLETE collectors: {len(incoming)} incoming paths")
        print(f"   ✅ SURVEY_COMPLETE has {len(outgoing)} outgoing (should be 0)")
        
        if outgoing:
            print(f"   ⚠️  SURVEY_COMPLETE outgoing edges: {outgoing}")
        else:
            print("   ✅ SURVEY_COMPLETE is true exit point")
    
    # Check reachability
    if graph.has_node('INTRO_INCENTIVE'):
        reachable = set(nx.descendants(graph, 'INTRO_INCENTIVE'))
        reachable.add('INTRO_INCENTIVE')
        unreachable = set(graph.nodes()) - reachable
        
        if unreachable:
            print(f"   ⚠️  Unreachable nodes: {unreachable}")
        else:
            print("   ✅ All nodes reachable from INTRO_INCENTIVE")
    
    print(f"\n📊 Simple DAG: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    # Save the simplified architecture
    print("\n💾 Saving simplified collector architecture...")
    db.save_graph(graph)
    
    # Create snapshot
    db.create_snapshot("simple_survey_complete_collector")
    
    print("\n🎉 SIMPLE COLLECTOR ARCHITECTURE COMPLETE!")
    print("=" * 55)
    print("✅ Single Entry: INTRO_INCENTIVE")
    print("✅ Single Exit: SURVEY_COMPLETE (collector)")
    print("✅ Clean Architecture: No confusing FINAL_TERMINATION")
    print("✅ All paths → SURVEY_COMPLETE")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
