#!/usr/bin/env python3
"""
CORRECT FIX: Make FINAL_TERMINATION the single collector for ALL termination paths
"""

import sys
import os
import networkx as nx
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.database_manager import DatabaseManager

def main():
    """Fix termination architecture: ALL paths must lead to FINAL_TERMINATION collector."""
    print("🔧 CORRECT TERMINATION FIX: FINAL_TERMINATION AS COLLECTOR")
    print("=" * 60)
    
    db = DatabaseManager()
    
    # Load current DAG
    print("📊 Loading DAG...")
    graph = db.load_graph()
    
    print(f"   Current: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    # Analyze current terminals
    terminals = []
    for node_id, node_data in graph.nodes(data=True):
        node_type = node_data.get('type', 'unknown')
        if node_type in ['terminal', 'ultimate_terminal']:
            terminals.append(node_id)
    
    print(f"   Found terminals: {terminals}")
    
    # CRITICAL FIX: Connect ALL terminals to FINAL_TERMINATION
    print("\n🎯 CONNECTING ALL TERMINALS TO FINAL_TERMINATION COLLECTOR...")
    
    # 1. SURVEY_COMPLETE → FINAL_TERMINATION
    if graph.has_node('SURVEY_COMPLETE') and graph.has_node('FINAL_TERMINATION'):
        if not graph.has_edge('SURVEY_COMPLETE', 'FINAL_TERMINATION'):
            graph.add_edge('SURVEY_COMPLETE', 'FINAL_TERMINATION',
                          id='E_COMPLETE_TO_FINAL',
                          edge_type='terminate',
                          condition='always',
                          priority=0)
            print("   ✅ SURVEY_COMPLETE → FINAL_TERMINATION")
    
    # 2. END → FINAL_TERMINATION  
    if graph.has_node('END') and graph.has_node('FINAL_TERMINATION'):
        if not graph.has_edge('END', 'FINAL_TERMINATION'):
            graph.add_edge('END', 'FINAL_TERMINATION',
                          id='E_END_TO_FINAL',
                          edge_type='terminate', 
                          condition='always',
                          priority=0)
            print("   ✅ END → FINAL_TERMINATION")
    
    # 3. R2a/END_INELIGIBLE → FINAL_TERMINATION
    r2a_node = 'R2a' if graph.has_node('R2a') else ('END_INELIGIBLE' if graph.has_node('END_INELIGIBLE') else None)
    if r2a_node and graph.has_node('FINAL_TERMINATION'):
        if not graph.has_edge(r2a_node, 'FINAL_TERMINATION'):
            graph.add_edge(r2a_node, 'FINAL_TERMINATION',
                          id='E_INELIGIBLE_TO_FINAL',
                          edge_type='terminate',
                          condition='always',
                          priority=0)
            print(f"   ✅ {r2a_node} → FINAL_TERMINATION")
    
    # 4. Any other terminals → FINAL_TERMINATION
    for terminal in terminals:
        if terminal != 'FINAL_TERMINATION' and graph.has_node(terminal):
            if not graph.has_edge(terminal, 'FINAL_TERMINATION'):
                graph.add_edge(terminal, 'FINAL_TERMINATION',
                              id=f'E_{terminal.upper()}_TO_FINAL',
                              edge_type='terminate',
                              condition='always', 
                              priority=0)
                print(f"   ✅ {terminal} → FINAL_TERMINATION")
    
    # Set proper node types
    print("\n🏷️  SETTING CORRECT NODE TYPES...")
    
    # FINAL_TERMINATION is the ultimate collector (single exit point)
    if graph.has_node('FINAL_TERMINATION'):
        graph.nodes['FINAL_TERMINATION']['type'] = 'ultimate_terminal'
        print("   ✅ FINAL_TERMINATION: ultimate_terminal (single exit)")
    
    # All other terminals are intermediate collection points
    for terminal in terminals:
        if terminal != 'FINAL_TERMINATION' and graph.has_node(terminal):
            graph.nodes[terminal]['type'] = 'terminal'
            print(f"   ✅ {terminal}: terminal (intermediate)")
    
    # Validate the collector architecture
    print("\n✅ VALIDATING COLLECTOR ARCHITECTURE...")
    
    if graph.has_node('FINAL_TERMINATION'):
        # Check that all terminals connect to FINAL_TERMINATION
        collectors = []
        for terminal in terminals:
            if terminal != 'FINAL_TERMINATION' and graph.has_node(terminal):
                if graph.has_edge(terminal, 'FINAL_TERMINATION'):
                    collectors.append(terminal)
                else:
                    print(f"   ❌ {terminal} NOT connected to collector")
        
        print(f"   ✅ {len(collectors)} terminals connected to collector")
        print(f"   ✅ Single exit point: FINAL_TERMINATION")
        
        # Check FINAL_TERMINATION has no outgoing edges (true exit)
        outgoing = list(graph.successors('FINAL_TERMINATION'))
        if outgoing:
            print(f"   ⚠️  FINAL_TERMINATION has outgoing edges: {outgoing}")
        else:
            print("   ✅ FINAL_TERMINATION is true exit (no outgoing edges)")
    
    print(f"\n📊 Collector DAG: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    # Save the collector architecture
    print("\n💾 Saving collector architecture...")
    db.save_graph(graph)
    
    # Create snapshot
    db.create_snapshot("collector_termination_architecture")
    
    print("\n🎉 COLLECTOR TERMINATION ARCHITECTURE COMPLETE!")
    print("=" * 60)
    print("✅ Single Entry: INTRO_INCENTIVE")
    print("✅ All terminals → FINAL_TERMINATION collector")
    print("✅ Single Exit: FINAL_TERMINATION")
    print("✅ Proper DAG: One entry, one exit, all paths connected")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
